# SOURCE DEFINITION AUDIT

Frozen plan: `c59fe01370d48aedeed56ef7a4103506d14a298edb794723be3720531edd62c6`

Every criterion is tagged DOCUMENTED / CODE-INFERRED / PROJECT-INFERRED / MEASURED / UNKNOWN.  UNKNOWN stays UNKNOWN.

## Criterion-by-criterion verdicts

| # | canonical name | A DOF | B index | C unit | D sign | E zero | F ref pose | G convention | H range | I handedness | J calibration |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | `thumb_cmc_flexion` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | UNCERTAIN | FAIL |
| 1 | `thumb_cmc_ab_adduction` | PASS | PASS | PASS | CORRECTED | PASS | PASS | PASS | PASS | UNCERTAIN | FAIL |
| 2 | `thumb_mcp_flexion` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | UNCERTAIN | FAIL |
| 3 | `thumb_ip_flexion` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | UNCERTAIN | FAIL |
| 4 | `index_mcp_flexion` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | UNCERTAIN | FAIL |
| 5 | `index_pip_flexion` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | UNCERTAIN | FAIL |
| 6 | `index_dip_flexion` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | UNCERTAIN | FAIL |
| 7 | `middle_mcp_flexion` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | UNCERTAIN | FAIL |
| 8 | `middle_pip_flexion` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | UNCERTAIN | FAIL |
| 9 | `middle_dip_flexion` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | UNCERTAIN | FAIL |
| 10 | `ring_mcp_flexion` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | UNCERTAIN | FAIL |
| 11 | `ring_pip_flexion` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | UNCERTAIN | FAIL |
| 12 | `ring_dip_flexion` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | UNCERTAIN | FAIL |
| 13 | `pinky_mcp_flexion` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | UNCERTAIN | FAIL |
| 14 | `pinky_pip_flexion` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | UNCERTAIN | FAIL |
| 15 | `pinky_dip_flexion` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | UNCERTAIN | FAIL |

## Measured per-dimension summary

| # | canonical name | DB9 median (deg) | emg2pose median (deg) | median diff | Wasserstein | support overlap | identity diagonal? | best emg2pose match | DB2-DB1 gap | range compatibility |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | `thumb_cmc_flexion` | +3.86 | +7.93 | +4.08 | 5.32 | 0.833 | no | `pinky_dip_flexion` | -7.94 | HIGH |
| 1 | `thumb_cmc_ab_adduction` | -4.36 | -6.21 | -1.86 | 2.44 | 0.309 | no | `pinky_dip_flexion` | +9.08 | HIGH |
| 2 | `thumb_mcp_flexion` | +3.72 | +14.28 | +10.56 | 8.28 | 0.707 | no | `thumb_ip_flexion` | -0.07 | HIGH |
| 3 | `thumb_ip_flexion` | +6.89 | +38.12 | +31.23 | 21.52 | 0.503 | YES | `thumb_ip_flexion` | -4.26 | LOW |
| 4 | `index_mcp_flexion` | +2.27 | +16.96 | +14.69 | 11.03 | 0.744 | no | `middle_mcp_flexion` | -15.54 | HIGH |
| 5 | `index_pip_flexion` | -1.37 | +26.48 | +27.85 | 23.37 | 0.800 | YES | `index_pip_flexion` | -29.64 | MODERATE |
| 6 | `index_dip_flexion` | +0.81 | +10.93 | +10.11 | 13.40 | 0.564 | no | `pinky_pip_flexion` | -0.44 | MODERATE |
| 7 | `middle_mcp_flexion` | -0.02 | +20.67 | +20.69 | 18.56 | 0.433 | no | `ring_mcp_flexion` | -40.08 | MODERATE |
| 8 | `middle_pip_flexion` | +1.13 | +39.31 | +38.18 | 39.42 | 0.460 | no | `pinky_pip_flexion` | -1.14 | LOW |
| 9 | `middle_dip_flexion` | -9.28 | +20.81 | +30.09 | 55.22 | 0.498 | no | `pinky_dip_flexion` | +11.88 | LOW |
| 10 | `ring_mcp_flexion` | +1.25 | +19.20 | +17.96 | 13.92 | 0.599 | YES | `ring_mcp_flexion` | -13.64 | MODERATE |
| 11 | `ring_pip_flexion` | +3.63 | +43.08 | +39.45 | 34.60 | 0.518 | no | `pinky_pip_flexion` | +0.76 | LOW |
| 12 | `ring_dip_flexion` | -9.67 | +16.84 | +26.50 | 55.11 | 0.464 | no | `ring_pip_flexion` | +23.65 | MODERATE |
| 13 | `pinky_mcp_flexion` | +2.65 | +17.35 | +14.70 | 28.56 | 0.545 | no | `ring_mcp_flexion` | -52.04 | MODERATE |
| 14 | `pinky_pip_flexion` | +2.96 | +26.93 | +23.97 | 19.90 | 0.533 | YES | `pinky_pip_flexion` | -4.38 | MODERATE |
| 15 | `pinky_dip_flexion` | -5.51 | +5.62 | +11.12 | 25.58 | 0.545 | no | `ring_pip_flexion` | +7.07 | MODERATE |

## The one criterion that fails globally

**J — preprocessing/calibration semantics.**  DB9's numbers are a per-channel **linear sensor calibration** whose gains were derived from a 10-subject calibration protocol and then applied to all 77 subjects; emg2pose's numbers are the output of an **inverse-kinematics fit** of a generic hand model to motion capture.  Two different metrological processes, and the official DB9 page itself warns that DIP sensors give partial results on small hands.  Every per-dimension disagreement found in this audit traces to that criterion — see `DB9_DIP_CHANNEL_VALIDITY.json` and `LARGE_OFFSET_FORENSICS.md`.

