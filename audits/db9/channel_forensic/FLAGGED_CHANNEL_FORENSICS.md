# FLAGGED CHANNEL FORENSICS

**Frozen plan SHA-256:** `4c618b562903d0d364d03bb8a997ef6b4140bd9e09d0f2475f1b008ad80c8793`  **Commit:** COMMIT PENDING

Channels flagged by the independent 2024 study are labelled `LITERATURE_FLAGGED`, never `KNOWN_BAD`. This document reproduces or refutes the flag from the data.

## The forensic chain

```
PHYSICAL MOVEMENT  (Exercise B movement 6 'fingers flexed together in fist',
                    movement 17 'wrist extension with closed hand')
      |
RAW GLOVE SENSOR   glove[:, g]        <- the exact column is recovered, not guessed
      |
OFFICIAL TRANSFORM angle = gain * (raw - raw_reference), gains from the DB9 paper
      |
OUR RECONSTRUCTION reproduced to machine precision (see TRANSFORM_REPRODUCTION)
      |
RELEASED DB9 ANGLE angles[:, a]
```

## 1. The anchor, subject by subject

| channel | n subjects | median Î”raw (counts) | raw +/âˆ’ | median Î”angle (deg) | angle +/âˆ’ | coherence | agreement with the official sign | verdict |
|---|---|---|---|---|---|---|---|---|
| **DIP2** | 37 | +65.65 | 28/9 | +96.12 | 28/9 | 1.000 | 0.757 | **CASE_E_INCONCLUSIVE** |
| **DIP3** | 37 | -32.58 | 2/35 | -47.32 | 2/35 | 1.000 | 0.054 | **CASE_A_RELEASED_REPRESENTATION** |
| **DIP4** | 37 | -8.88 | 8/28 | -32.00 | 8/28 | 1.000 | 0.216 | **CASE_E_INCONCLUSIVE** |
| **DIP5** | 37 | -9.12 | 5/32 | -25.20 | 5/32 | 1.000 | 0.135 | **CASE_A_RELEASED_REPRESENTATION** |
| **CMC5** | 37 | +1.92 | 19/18 | +0.55 | 19/18 | 1.000 | 0.514 | **CASE_B_SENSOR_OR_FIT_LIMITATION** |

## 2. Internal controls - the same segments, the same subjects

This is the evidence that the segment is not inverted and the trial is not mis-labelled: within the very same fist segments the MCP and PIP channels move in the documented direction in essentially every subject.

| channel | family | median Î”raw | raw +/âˆ’ | median Î”angle | angle +/âˆ’ | agreement |
|---|---|---|---|---|---|---|
| `MCP2_f` | MCP index | +70.50 | 37/0 | +67.48 | 37/0 | 1.000 |
| `PIP2` | PIP index | +128.00 | 36/1 | +122.66 | 36/1 | 0.973 |
| `DIP2` | DIP index | +65.65 | 28/9 | +96.12 | 28/9 | 0.757 |
| `MCP3_f` | MCP middle | +122.69 | 37/0 | +110.55 | 37/0 | 1.000 |
| `PIP3` | PIP middle | +9.92 | 20/17 | +17.51 | 20/17 | 0.541 |
| `DIP3` | DIP middle | -32.58 | 2/35 | -47.32 | 2/35 | 0.054 |
| `MCP4_f` | MCP ring | +82.00 | 37/0 | +79.54 | 37/0 | 1.000 |
| `PIP4` | PIP ring | +49.00 | 28/9 | +93.10 | 28/9 | 0.757 |
| `DIP4` | DIP ring | -8.88 | 8/28 | -32.00 | 8/28 | 0.216 |
| `MCP5_f` | MCP little | +120.00 | 37/0 | +134.37 | 37/0 | 1.000 |
| `PIP5` | PIP little | +61.55 | 37/0 | +71.22 | 37/0 | 1.000 |
| `DIP5` | DIP little | -9.12 | 5/32 | -25.20 | 5/32 | 0.135 |
| `MCP1` | MCP thumb | +32.24 | 34/3 | +18.13 | 34/3 | 0.919 |
| `IP1` | IP thumb | +48.56 | 37/0 | +52.40 | 37/0 | 1.000 |

**Reading.** For every digit the MCP and the PIP channel of the same finger move positively, while the DIP channel of digits 3, 4 and 5 moves negatively. The reversal is therefore specific to the DIP gauges, not to the movement, the segment, the reference or the trial label. `[EMPIRICAL]`

## 3. Independent second anchor

Movements 2 and 3 ('extension of index and middle, flexion of the others' and 'flexion of ring and little finger, extension of the others') engage the ring and little digits specifically.

| channel | n | median Î”raw | coherence | verdict |
|---|---|---|---|---|
| `PIP4` | 37 | -12.75 | 1.000 | CASE_E_INCONCLUSIVE |
| `DIP4` | 37 | -82.41 | 1.000 | CASE_E_INCONCLUSIVE |
| `PIP5` | 37 | +14.00 | 1.000 | CASE_C_PREVIOUS_QC_WRONG |
| `DIP5` | 37 | -1.98 | 1.000 | CASE_A_RELEASED_REPRESENTATION |

## 4. CMC5 - a released-representation collision

the released CMC5 column is an exact linear function (slope 0.28511, matching the published 0.285) of the SAME raw column that feeds WRIST_F.  In the wrist flexion anchor both move by exactly the same raw amount (+9.96 counts, 37/37); in the wrist extension anchor both move by -19.41 counts (37/37).  One raw sensor cannot be both the palmar arch and the wrist.  In the fist anchor CMC5 does not move at all (19/18). `[EMPIRICAL]`

| anchor | CMC5 median Î”raw | WRIST_F median Î”raw | identical? |
|---|---|---|---|
| wrist flexion (movement 13) | +9.46 | +9.46 | YES - same sensor |
| wrist extension (movement 14) | -22.54 | -22.54 | YES - same sensor |
| fist (movements 6+17) | +1.92 | +1.92 | YES - same sensor |

## 5. Verdicts

### DIP3: `CASE_A_RELEASED_REPRESENTATION` -> **DROP** (confidence HIGH)

* anchor `A_FIST`, n = 37 subjects
* coherence 1.000, agreement with the official sign 0.054, opposed 0.946, magnitude ratio 0.589
* on an unambiguous fist (Exercise B movements 6 and 17) the raw DIP3 gauge DECREASES in 35 of 37 subjects and the released DIP3 angle decreases with it, while in the very same segments every MCP and PIP flexion channel increases. The transform is faithful; the direction contradicts the official 'DIP(2-5)_F Flexion+/Extension-' criterion.

### DIP4: `CASE_E_INCONCLUSIVE` -> **INCONCLUSIVE** (confidence LOW)

* anchor `A_FIST`, n = 37 subjects
* coherence 1.000, agreement with the official sign 0.216, opposed 0.757, magnitude ratio 0.161
* the same inversion, but coherent in only 28 of 37 subjects and with a raw response 11 % of the flexion-channel median.
* released vs published: released constant 2.0 vs published 2.08 (3.8 % difference, above the 2 % materiality threshold)

### DIP5: `CASE_A_RELEASED_REPRESENTATION` -> **DROP** (confidence HIGH)

* anchor `A_FIST`, n = 37 subjects
* coherence 1.000, agreement with the official sign 0.135, opposed 0.865, magnitude ratio 0.165
* the same inversion, coherent in 32 of 37 subjects, raw response 11 % of the flexion-channel median.

### CMC5: `CASE_B_SENSOR_OR_FIT_LIMITATION` -> **DROP** (confidence MEDIUM)

* anchor `A_FIST`, n = 37 subjects
* coherence 1.000, agreement with the official sign 0.514, opposed 0.486, magnitude ratio 0.035
* the released CMC5 column is an exact linear function (slope 0.28511, matching the published 0.285) of the SAME raw column that feeds WRIST_F.  In the wrist flexion anchor both move by exactly the same raw amount (+9.96 counts, 37/37); in the wrist extension anchor both move by -19.41 counts (37/37).  One raw sensor cannot be both the palmar arch and the wrist.  In the fist anchor CMC5 does not move at all (19/18).

## 6. What is NOT claimed

* No sign flip, offset, affine alignment or rescaling was applied. The released arrays were never modified.
* The DIP gauges are not claimed to be dead: DIP2 responds correctly and DIP3/4/5 respond coherently, just with the opposite polarity to the published criterion and at roughly a tenth of the MCP/PIP magnitude.
* The literature flag on `CMC5` is *refuted as stated* and replaced by a stronger finding: CMC5 is not a bad palmar-arch channel, it is the wrist channel. `[EMPIRICAL]`
