# DB9 CHANNEL FORENSIC - TERMINAL REPORT

**Branch:** `S8-DB9-CHANNEL-FORENSIC`  
**Frozen plan SHA-256:** `4c618b562903d0d364d03bb8a997ef6b4140bd9e09d0f2475f1b008ad80c8793`  **Commit:** COMMIT PENDING

---
## The eight answers

### 1-4. Literature-flagged channels

| channel | answer | case | status | agreement with the official sign | opposed | magnitude ratio |
|---|---|---|---|---|---|---|
| **DIP3** | **REAL_DB9_PROBLEM** | `CASE_A_RELEASED_REPRESENTATION` | DROP | 0.05 | 0.95 | 0.59 |
| **DIP4** | **INCONCLUSIVE** | `CASE_E_INCONCLUSIVE` | INCONCLUSIVE | 0.22 | 0.76 | 0.16 |
| **DIP5** | **REAL_DB9_PROBLEM** | `CASE_A_RELEASED_REPRESENTATION` | DROP | 0.14 | 0.86 | 0.16 |
| **CMC5** | **REAL_DB9_PROBLEM** | `CASE_B_SENSOR_OR_FIT_LIMITATION` | DROP | 0.51 | 0.49 | 0.03 |

### 5. Sensor 11 / MCP2_a

released as an all-NaN column; excluded officially; NO IMPACT on any historical representation of this project

### 6. The old 'many channels fail' verdict

**PARTIALLY_OVERTURNED - the earlier 'many channels fail' verdict was produced on segmentation keyed to the PRE-relabelling `repetition` vector, which is misaligned with the kinematics in 24 of 99 files. Under correct segmentation six of the suspects pass at >= 0.90 subject-level agreement, while FIVE findings are confirmed or newly established.**

### 7. TRUSTED_DB9_POSE_v1

**8 KEEP channels:** `MCP1`, `IP1`, `MCP2_f`, `PIP2`, `MCP3_f`, `MCP4_f`, `MCP5_f`, `PIP5`

* DROP (6): `MCP2_a`, `CMC5`, `MCP5_a`, `DIP3`, `DIP5`, `WRIST_A`
* INCONCLUSIVE (8): `CMC1_f`, `CMC1_a`, `PIP3`, `MCP4_a`, `PIP4`, `DIP2`, `DIP4`, `WRIST_F`

frozen SHA-256: `e51dde6e63941fd080c84f3896a98cf50fba9e17d5f9cebe909253d5465782d1` (written before any classifier ran)

### 8. Trusted-subset posture classifier

| metric | arm A historical canonical16 | arm B trusted subset |
|---|---|---|
| Accuracy | 0.6069 | 0.4849 |
| Balanced accuracy | 0.6087 | 0.4853 |
| Macro F1 | 0.6067 | 0.4795 |
| Worst-subject BA | 0.3942 | 0.3827 |
| Median-subject BA | 0.6250 | 0.5009 |
| Chance BA | 0.0588 | 0.0588 |

* utility loss (trusted - historical): ΔAcc -0.1220, ΔBA -0.1233, ΔmacroF1 -0.1273
* classes with recall < 0.5 in arm B: [5, 8, 9, 10, 12, 14, 16, 17]
* class collapse: True

**Why the mixed task understates the subset.** Exercise B mixes 9 hand-shape movements (ids 1-8, 17) with 8 wrist movements (ids 9-16). `TRUSTED_DB9_POSE_v1` contains no wrist channel by construction (`WRIST_F` INCONCLUSIVE, `WRIST_A` DROP), so the 17-class task penalises it for a target it was never designed to carry. Re-running the identical protocol on the hand-shape movements only:

| metric | arm A (16 ch) | arm B trusted (8 ch) |
|---|---|---|
| Accuracy | 0.8555 | 0.7286 |
| Balanced accuracy | 0.8538 | 0.7254 |
| Macro F1 | 0.8560 | 0.7257 |
| Worst-subject BA | 0.5648 | 0.4794 |
| Median-subject BA | 0.8707 | 0.7347 |
| Chance BA | 0.1111 | 0.1111 |

* utility loss on the hand-shape task: dBA -0.1283 (relative 0.850)
* arm B per-class recall: {'1': 0.91, '17': 0.658, '2': 0.748, '3': 0.935, '4': 0.519, '5': 0.652, '6': 0.76, '7': 0.914, '8': 0.433}
* arm B classes with recall < 0.5: [8]; class collapse: False
* arm B balanced accuracy is 6.5x chance

---
## DB9 FINAL DECISION

# `DB9-ADMIT-REDUCED`

the trusted physical subset is real and the posture task remains usable, but on a reduced channel set and/or with a measurable utility loss. Permitted claims: the Exercise B movement classes recovered by the frozen trusted subset under subject-held-out evaluation. Not permitted: any claim about DIP angles, the palmar arch, or wrist deviation as measured physical quantities.

---
## Most important evidence

* **Movement probe.** Pooled MCP flexion response by movement id identifies restimulus 6 as the fist (median Δraw +99.2 counts) with no other movement close; the anchor is therefore validated from the data, not from the movement list.
* **Internal control.** In the same fist segments MCP2_f/MCP3_f/MCP4_f/MCP5_f move positively in 37/37 subjects while DIP3 moves negatively in 35/37, DIP5 in 32/37 and DIP4 in 28/37. The reversal is specific to the DIP gauges.
* **Transform recovered exactly.** 16 of the 22 released angle columns are exact affine or affine-quadratic functions of a single raw glove column, recovered with zero residual; the composite channels are recovered as well.
* **CMC5 collision.** The released CMC5 column is an exact linear function (slope 0.28511 = the published 0.285) of the SAME raw column that feeds WRIST_F: in the wrist anchors both move by exactly the same raw amount, 37/37 subjects.
* **Segmentation trap.** `stimulus`/`repetition` are 7 samples longer than `glove`/`angles` in 24 of 99 files; only `restimulus` x `rerepetition` align in all 99.
* **Reference posture confirmed from data.** Movement 11 minimises the distance to the reference implied by the released transform, independently confirming the paper's statement.
* **Subject-identity collision.** The in-file `subject` field is source-database local: `S68_E2_A1.mat` reports `subject == 1`; 10 collisions among the 37 Exercise-B files.
* **DIP4 is inverted in only 28/37 subjects** and its raw response is 16 % of the flexion-channel median - which is why it is held INCONCLUSIVE rather than DROPped.
* **PIP3 does not respond to a fist** (20/37, raw magnitude 18 % of the median) even though it is not flagged by anyone.
* **Released constants disagree with the published table** for DIP4 (2.00 vs 2.08), WRIST_F (0.00865779 vs 0.008) and MCP4_a (three of six polynomial coefficients).

---
## Old result impact

| branch | class | why |
|---|---|---|
| S3 posture decoder (`posture_decoder/`) | **NUMERICALLY_VALID_BUT_SEMANTICALLY_DOWNGRADED** | the numbers describe the DB9 released `angles` array, and that array is unchanged. But the historical canonical16 representation includes the four DIP channels, and this audit shows DIP3 and DIP5 are sign-inverted relative to the published sign criteria. Any claim of the form 'the decoder recovers physiological finger pose' is therefore unsupported for the DIP components; the classification numbers themselves stand. |
| S5 bridge (`bridge_audit/`) | **NEEDS_REINTERPRETATION** | the bridge compares DB9 against emg2pose. emg2pose supplies genuine DIP flexion; DB9's DIP3/DIP5 are inverted and its CMC5 column is the wrist channel. Any bridge conclusion that leans on those channels must be re-read. |
| DB9 distributional open-set (`db9_distributional_open_set/`) | **UNCHANGED** | the open-set work is about the distribution of the released representation. This audit does not change the release, the frames or the labels it used. |
| DB9 channel validity (`db9_channel_validity/`) | **PARTIALLY_OVERTURNED** | its segmentation used `repetition`, which is the PRE-relabelling vector and is misaligned with `glove`/`angles` in 24 of 99 files; and it grouped by a container count in places. Its per-channel statistics are therefore computed on shifted boundaries. This audit re-derives the same questions on `restimulus x rerepetition` and reaches a partly different answer: six of its suspects are exonerated at >= 0.90 subject-level agreement, while DIP3/DIP5/CMC5 are confirmed bad and DIP4/PIP3/PIP4/DIP2 are held INCONCLUSIVE. |
| coordinate audit (`pose_coordinate_audit/`) | **UNCHANGED by this lane; its own outstanding items remain open** | the earlier finding that part of that lane compared the adapter against itself, and that its PCA scripts grouped by `repetition`, is independent of this audit and is neither fixed nor re-opened here. This audit independently confirms the `repetition`-vs-`rerepetition` defect class: `repetition` is misaligned in 24 of 99 files. |
| the in-file `subject` field as an identity key (anywhere) | **INVALID** | the in-file `subject` field is source-database-local. `S68_E2_A1.mat` reports `subject == 1`, colliding with `S1_E2_A1.mat`; 10 such collisions exist among the 37 Exercise B files. Any grouping by that field merges distinct people. |

