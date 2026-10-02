# Round-trip test and coverage validation

The [validation workflow](../.github/workflows/validate-roundtrip-coverage.yml)
checks two pinned source commits on Linux with Python 3.12. It runs the complete
installed-package and documentation test suite through the repository's existing
`py312-test` tox environment, including optional test dependencies and remote data.

| Source | Expected result |
| --- | --- |
| Submitted PR head `2ecb4b18997b9435f3c518f4462a34e68cffd4aa` | The inverse-coordinate regression passes; only `test_coadd_solar_map` fails |
| Reference repair `28cf7bfe3849f60fd138ac7db5c0f9e7954e9a2d` | The full suite passes with the corrected solar reference |

The [successful validation run](https://github.com/zack-dev-cm/reproject/actions/runs/36973929134)
verifies these outcomes with the [tested workflow source](https://github.com/zack-dev-cm/reproject/blob/fc9d310c5e252cec527e209780a4340fe923a961/.github/workflows/validate-roundtrip-coverage.yml):

| Source | Passed | Skipped | Failed | Coverage XML |
| --- | ---: | ---: | ---: | --- |
| Submitted `2ecb4b18` | 2,145 | 467 | 1, the solar comparison | Exported |
| Reference repair `28cf7bfe` | 2,146 | 467 | 0 | Exported |

The [Windows/Python 3.12 validation run](https://github.com/zack-dev-cm/reproject/actions/runs/36977616533)
independently verifies the same two source commits using the
[tested Windows workflow](https://github.com/zack-dev-cm/reproject/blob/53e750a15c0e0ff7569147a6213aac3378101ca8/.github/workflows/validate-roundtrip-windows.yml).
Both Windows profiles have the same test totals and export coverage XML.
The remote-FITS download timeout recorded in the earlier upstream Windows job
does not recur in either profile. That original upstream job remains unchanged.

The two sources have identical production code, regression tests and CI setup.
Their only difference is the solar-reference FITS file. The submitted PR retains
the original reference pending agreement about the intended output.

Coverage is installed before tox starts, matching the submitted CI correction's
`toxdeps: 'coverage[toml]'`. Both profiles must produce coverage XML, even when the
submitted source's solar comparison fails. The workflow verifies the expected
test outcome, the inverse-coordinate regression, the source commit, and coverage
for `_wcs_utils.py`. Any additional test failure, collection error, missing report
or unexpected outcome fails validation.

A successful workflow means these two declared scenarios were verified. It does
not mean the submitted PR's full test suite passes: that source is expected to
retain one solar comparison failure. It does not establish acceptance of the
reference change or passing coverage on every supported platform.

Each artifact includes the full tox log, pytest XML, coverage XML, the coverage
database and a JSON summary with the exact source commit and test totals.
