# SENSOR 11 / MCP2_a - STATUS AND HISTORICAL IMPACT

**Frozen plan SHA-256:** `4c618b562903d0d364d03bb8a997ef6b4140bd9e09d0f2475f1b008ad80c8793`

## Official status `[OFFICIAL]`

> 'Sensor 11 (which corresponds to MCP2-3_A) was not included into the calibrated data due to noise problems.'  - Ninapro DB9 instructions, Usage notes

## Released status `[EMPIRICAL]`

* `angles[:,5]` = `MCP2_a` is **all NaN** in every released `.mat` file examined.
* `glove[:,5]` = the raw noisy gauge is **still present** in the release, so the noise is available to anyone who does not read the usage notes.
* the released `order_of_angles` field still lists `6:MCP2_a`, so a naive loader that trusts the column count will pick up an all-NaN column.

## Historical impact in this project

NO IMPACT - the released DB9 angle column 5 (MCP2_a) is all NaN and no historical representation of this project selects it; canonical16 is built from the emg2pose 20D array and never from a DB9 angle column.

| question | answer |
|---|---|
| files mentioning MCP2_a / MCP2-3_A / angle column 5 | 19 |
| `docs/DB9_CANONICAL16_MAPPING.md` references MCP2_a | True |
| any historical representation selects DB9 angle column 5 | **no** |
| could it be mapped back in through another column | no mapping exists that would do so; the column is NaN, so any accidental use produces NaN, which fails loudly rather than silently |

Files that merely *mention* the name (none of them select the column into a representation):

| file | matched on |
|---|---|
| `docs\canonical_emg2pose_verification.json` | MCP2_a |
| `docs\DB9_CANONICAL16_MAPPING.md` | MCP2_a |
| `docs\DB9_FILE_AUDIT.json` | MCP2_a |
| `docs\REMEDIATION_REPORT.md` | MCP2_a |
| `posture_decoder\README.md` | MCP2_a |
| `posture_decoder\report.md` | MCP2_a |
| `posture_decoder\db9\canonical.py` | MCP2_a |
| `posture_decoder\db9\loader.py` | MCP2_a |
| `posture_decoder\db9\quality.py` | MCP2_a |
| `pose_coordinate_audit\OFFICIAL_SOURCE_REFERENCES.md` | MCP2_a |
| `pose_coordinate_audit\POSE_COORDINATE_AUDIT_REPORT.md` | MCP2_a |
| `pose_coordinate_audit\SYNTHETIC_ROUNDTRIP_RESULTS.json` | MCP2_a |
| `pose_coordinate_audit\tools\pca_docs_manifest.py` | MCP2_a |
| `pose_coordinate_audit\tools\pca_verdict.py` | MCP2_a |
| `representation\db9_canonical16_schema.json` | MCP2_a |
| `representation\db9_to_canonical16.py` | MCP2_a |
| `representation\tests\test_db9_to_canonical16.py` | MCP2_a |
| `representation\tests\test_db9_to_canonical16.py` | index5 |
| `baseline\emg2pose\emg2pose\tests\test_visualization.py` | index5 |

