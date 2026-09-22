# PHYSICAL QC

**Frozen plan SHA-256:** `fba2b20623392dd809d5ed28c7850387acc721e9a91ff1611e7fba0d89fc889d`  **Commit:** COMMIT PENDING

Every anchor below had its expected direction fixed BEFORE it was computed. The unit of consistency is the SUBJECT, never a frame. Thresholds (frozen plan section 9): PASS >= 80 % of subjects, WEAK 60-80 %, FAIL < 60 %.

---
## 1. KIN-MUS - scored anchors

Anchor: the median of the pooled channels in MANIPULATION minus REACHING, per subject, over all 26 ADLs.  `[EMPIRICAL]`

| anchor | expected | subjects in the expected direction | fraction | Wilson 95 % | median delta (deg) | verdict |
|---|---|---|---|---|---|---|
| PIP flexion rises from REACHING (1) to MANIPULATION (2) | positive | 22/22 | 1.0000 | [0.851, 1.000] | +13.082 | **PASS** |
| MCP flexion rises from REACHING (1) to MANIPULATION (2) | positive | 22/22 | 1.0000 | [0.851, 1.000] | +17.792 | **PASS** |
| MCP+PIP flexion sum rises from REACHING to MANIPULATION | positive | 22/22 | 1.0000 | [0.851, 1.000] | +18.000 | **PASS** |
| relative abduction FALLS from REACHING to MANIPULATION (fingers come t | negative | 14/22 | 0.6364 | [0.430, 0.803] | -0.590 | **WEAK** |
| thumb MCP + IP flexion rises from REACHING to MANIPULATION | positive | 18/22 | 0.8182 | [0.615, 0.927] | +1.962 | **PASS** |
| thumb CMC flexion rises from REACHING to MANIPULATION | positive | 22/22 | 1.0000 | [0.851, 1.000] | +6.867 | **PASS** |
| thumb CMC abduction rises from REACHING to MANIPULATION (REPORTED, NOT | positive | 22/22 | 1.0000 | [0.851, 1.000] | +2.065 | **PASS** |

**Reported, not scored.**  The relative-abduction anchor (A3) is WEAK at 14/22.  The direction of a relative abduction during a grasp is genuinely ambiguous from the documentation - a cylindrical grasp can either bring the metacarpals together or spread them - so it is reported with its full distribution rather than treated as a pass or a failure.  Note the magnitudes: the median is -0.59 deg, i.e. essentially nil, which is the honest reading.  `[EMPIRICAL]`

### 1.1 The degeneracy guard

The frozen plan requires that an anchor cannot be passed by a channel that never moves. Every row above reports the full statistic, not only a boolean, and the per-channel ranges are in `artifacts/KINMUS_SPECIAL.json` `D_anchors.per_channel_range`. `[EMPIRICAL]`

### 1.2 Wrist channels leave the physiological envelope

REPORTED, NOT SCORED.  WR_F reaches -156.53 deg of extension and +115.75 deg of flexion; WR_A reaches -90.66 deg.  The commonly cited goniometer maxima are +79 flexion / -63 extension / -19 radial / +35 ulnar.  The wrist channels therefore leave the physiological envelope by a factor of ~1.5-2.5.  The dataset's own Usage Notes attribute extreme WRIST_F values to 'cables underneath the glove', and the release's wrist gains are not published.  This is a flag on the wrist channels, not a measurement of them.

| channel | observed range (deg) | commonly cited goniometer maxima |
|---|---|---|
| WR_F | [-156.53, 115.75] | +79 flexion / -63 extension |
| WR_A | [-90.66, 25.68] | +35 ulnar / -19 radial |

---
## 2. MyoKi - nominal anchor at n = 1 recording, NOT scored

Anchor: rest (task 0) -> fist (task 1) inside the official synchronisation recording. `[EMPIRICAL]`

| channel | expected | median delta fist - rest (deg) | direction |
|---|---|---|---|
| MCP Index (col 5) | positive (a fist flexes this joint) | +64.528 | OK |
| PIP Index (col 6) | positive (a fist flexes this joint) | +111.236 | OK |
| MCP Middle (col 7) | positive (a fist flexes this joint) | +66.600 | OK |
| PIP Middle (col 8) | positive (a fist flexes this joint) | +79.200 | OK |
| MCP Ring (col 10) | positive (a fist flexes this joint) | +58.333 | OK |
| PIP Ring (col 11) | positive (a fist flexes this joint) | +68.211 | OK |
| MCP Little (col 13) | positive (a fist flexes this joint) | +59.760 | OK |
| PIP Little (col 14) | positive (a fist flexes this joint) | +62.571 | OK |

All eight MCP/PIP flexion channels move in the documented flexion-positive direction, with large magnitudes (+58 to +111 deg). **NOT COMPUTABLE: this file is ONE recording. The frozen plan's anchor protocol counts SUBJECTS, not frames, so no sign-consistency rate can be produced from it. n = 1 recording is reported and nothing is scored.**

### 2.1 The real MyoKi anchor result is the PARITY test, not the fist test

* equation: `angle = angle1 + (sensor_value - sensor_value1) * gain, gain = (angle2 - angle1)/(sensor_value2 - sensor_value1)`
* matching calibration sheet: **female**
* maximum absolute error over channels 1-16: **0.000e+00 deg**
* channels reproduced BIT-EXACTLY for 100 % of samples: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
* channels NOT reproduced: [17, 18] (the two wrist channels, which the paper says were calibrated per participant; their slope matches neither published sheet)
* verdict: **TRANSFORM_INDEPENDENTLY_REPRODUCIBLE for channels 1-16 and TRANSFORM_NOT_INDEPENDENTLY_REPRODUCIBLE for the two wrist channels 17-18**

---
## 3. KINE-ADL

* no physical anchor could be computed: the corpus was not downloaded. `[UNRESOLVED]`
* the guide carries per-DOF AROM for every subject in `SUBJECT_DATA`, so a range-based QC is possible once the corpus is obtained. `[DOC]`

---
## 4. Cross-dataset statement

No physical anchor in this audit compares two datasets numerically. Every anchor is WITHIN one dataset, because the zero definitions differ (a recorded reference posture for the UJI family, a calibration posture for MyoKi, the rig convention for emg2pose) and at least one documented sign convention conflicts. Cross-dataset numeric equivalence is `UNVERIFIED` everywhere. `[INFERENCE]`

