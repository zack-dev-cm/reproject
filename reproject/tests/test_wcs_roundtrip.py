import numpy as np
import pytest
from astropy import units as u
from astropy.wcs.utils import pixel_to_pixel
from astropy.wcs.wcsapi import BaseLowLevelWCS, HighLevelWCSWrapper, SlicedLowLevelWCS

from reproject import reproject_interp
from reproject._wcs_utils import pixel_to_pixel_chunked


class PartialInverseWCS(BaseLowLevelWCS):
    """Identity coordinates with a configurable, partially defined inverse."""

    pixel_n_dim = 2
    world_n_dim = 2
    world_axis_physical_types = ("custom:fixture.x", "custom:fixture.y")
    world_axis_units = ("pix", "pix")
    world_axis_object_components = (("x", 0, "value"), ("y", 0, "value"))
    world_axis_object_classes = {
        "x": (u.Quantity, (), {"unit": u.pix}),
        "y": (u.Quantity, (), {"unit": u.pix}),
    }
    axis_correlation_matrix = np.eye(2, dtype=bool)

    def __init__(self, axis=0, limit=None, invalid=np.nan, offset=0.0):
        self.axis = axis
        self.limit = limit
        self.invalid = invalid
        self.offset = offset

    def pixel_to_world_values(self, x, y):
        return tuple(np.broadcast_arrays(np.asarray(x, dtype=float), np.asarray(y, dtype=float)))

    def world_to_pixel_values(self, x, y):
        values = [value.copy() for value in self.pixel_to_world_values(x, y)]
        if self.limit is not None:
            values[self.axis] = np.where(
                values[self.axis] > self.limit, self.invalid, values[self.axis]
            )
        values[self.axis] += self.offset
        return tuple(values)


@pytest.mark.parametrize("axis", [0, 1])
@pytest.mark.parametrize("invalid", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("chunk_size", [1, 3, 200_000])
@pytest.mark.parametrize("roundtrip", [False, True])
def test_roundtrip_partial_inverse(axis, invalid, chunk_size, roundtrip):
    target = HighLevelWCSWrapper(PartialInverseWCS(axis=axis, limit=2.5, invalid=invalid))
    source = HighLevelWCSWrapper(PartialInverseWCS())
    coords = np.arange(5.0)

    # Check the WCS contract independently of the chunked transformation.
    forward = pixel_to_pixel(target, source, coords, coords)
    inverse = pixel_to_pixel(source, target, *forward)
    np.testing.assert_array_equal(forward, [coords, coords])
    np.testing.assert_array_equal(inverse[axis][:3], coords[:3])
    assert not np.isfinite(inverse[axis][3:]).any()

    result = pixel_to_pixel_chunked(
        target, source, coords, coords, roundtrip=roundtrip, chunk_size=chunk_size
    )
    expected = [0, 1, 2, np.nan, np.nan] if roundtrip else coords
    for values in result:
        np.testing.assert_array_equal(values, expected)


@pytest.mark.parametrize("axis", [0, 1])
@pytest.mark.parametrize("offset", [0, np.nextafter(1.0, 0.0), 1, np.nextafter(1.0, 2.0)])
def test_roundtrip_tolerance(axis, offset):
    target = HighLevelWCSWrapper(PartialInverseWCS(axis=axis, offset=offset))
    source = HighLevelWCSWrapper(PartialInverseWCS())
    coords = np.zeros(5)
    result = pixel_to_pixel_chunked(target, source, coords, coords, roundtrip=True, chunk_size=3)
    expected = np.full(5, np.nan) if offset > 1 else coords
    for values in result:
        np.testing.assert_array_equal(values, expected)


def test_roundtrip_noncontiguous_output():
    target = HighLevelWCSWrapper(PartialInverseWCS(limit=2.5))
    source = HighLevelWCSWrapper(PartialInverseWCS())
    x = np.arange(10.0).reshape(5, 2).T
    y = np.broadcast_to(np.arange(5.0), (2, 5))
    output = [np.full((2, 5), -999.0).T for _ in range(2)]

    returned = pixel_to_pixel_chunked(
        target, source, x, y, roundtrip=True, output=output, chunk_size=3
    )

    assert returned is output
    for observed, reference in zip(returned, (x, y), strict=True):
        expected = np.where(x > 2.5, np.nan, reference)
        np.testing.assert_array_equal(observed.ravel(), expected.ravel())
    np.testing.assert_array_equal(x, np.arange(10.0).reshape(5, 2).T)
    np.testing.assert_array_equal(y, np.broadcast_to(np.arange(5.0), (2, 5)))


def test_roundtrip_partial_inverse_1d():
    target = HighLevelWCSWrapper(SlicedLowLevelWCS(PartialInverseWCS(limit=2.5), (0, slice(None))))
    source = HighLevelWCSWrapper(SlicedLowLevelWCS(PartialInverseWCS(), (0, slice(None))))
    (result,) = pixel_to_pixel_chunked(target, source, np.arange(5.0), roundtrip=True, chunk_size=3)
    np.testing.assert_array_equal(result, [0, 1, 2, np.nan, np.nan])


@pytest.mark.parametrize("coords", [np.array([]), np.array(1.0), np.array(4.0)])
def test_roundtrip_empty_and_scalar(coords):
    target = HighLevelWCSWrapper(PartialInverseWCS(limit=2.5))
    source = HighLevelWCSWrapper(PartialInverseWCS())
    result = pixel_to_pixel_chunked(target, source, coords, coords, roundtrip=True)
    for values in result:
        assert values.shape == coords.shape
        np.testing.assert_array_equal(values, np.where(coords > 2.5, np.nan, coords))


def test_roundtrip_nonfinite_forward():
    target = HighLevelWCSWrapper(PartialInverseWCS())
    source = HighLevelWCSWrapper(PartialInverseWCS(limit=2.5))
    result = pixel_to_pixel_chunked(
        target, source, np.arange(5.0), np.arange(5.0), roundtrip=True, chunk_size=3
    )
    for values in result:
        np.testing.assert_array_equal(values, [0, 1, 2, np.nan, np.nan])


@pytest.mark.parametrize("axis", [0, 1])
@pytest.mark.parametrize("roundtrip", [False, True])
@pytest.mark.parametrize("block_size", [None, (2, 2)])
def test_reproject_interp_partial_inverse(axis, roundtrip, block_size):
    source = PartialInverseWCS()
    target = PartialInverseWCS(axis=axis, limit=1.5)
    data = np.arange(15.0).reshape(3, 5) + 10
    output, footprint = reproject_interp(
        (data, source),
        target,
        shape_out=data.shape,
        order="nearest-neighbor",
        roundtrip_coords=roundtrip,
        block_size=block_size,
        parallel=False,
    )
    y, x = np.indices(data.shape)
    valid = (x if axis == 0 else y) < 2 if roundtrip else np.ones(data.shape, dtype=bool)
    np.testing.assert_array_equal(output, np.where(valid, data, np.nan))
    np.testing.assert_array_equal(footprint, valid.astype(float))
