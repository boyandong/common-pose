# SEGMENTATION VALIDATION

**Frozen plan SHA-256:** `4c618b562903d0d364d03bb8a997ef6b4140bd9e09d0f2475f1b008ad80c8793`  **Commit:** COMMIT PENDING

## Verdict: **SEGMENTATION VALIDATED**

---
## 1. Exact source files

| | |
|---|---|
| released `.mat` files | 99 |
| by exercise | {'E2': 37, 'E3': 22, 'E1': 40} |
| raw archives | 22 |
| extracted root | `<DB9_DATA_ROOT>\extracted` |

Exercise codes: **E2 = Exercise B = 17 basic movements of the fingers/wrist** (restimulus 0..17), **E3 = Exercise C = 23 grasping and functional movements** (restimulus 0..23). `[OFFICIAL]`

---
## 2. Vector alignment - the extraction trap

| relation | files where it holds |
|---|---|
| `glove==angles` | 99/99 |
| `glove==restimulus` | 99/99 |
| `glove==rerepetition` | 99/99 |
| `glove==stimulus` | 75/99 |
| `glove==repetition` | 75/99 |

**24 of 99 files have `stimulus`/`repetition` of a DIFFERENT length from `glove`/`angles`.** Those two vectors are the **pre-relabelling** acquisition labels; `restimulus`/`rerepetition` are the a-posteriori refined ones and are the only pair aligned with the kinematics. Any pipeline that segments on `stimulus` or `repetition` is segmenting misaligned labels - a silent off-by-N that moves whole movement boundaries. `[EMPIRICAL]`

| file | glove/angles | stimulus | repetition |
|---|---|---|---|
| `S11_E3_A1.mat` | 150379 | 150982 | 150982 |
| `S13_E2_A1.mat` | 85231 | 85600 | 85600 |
| `S13_E3_A1.mat` | 135046 | 135680 | 135680 |
| `S14_E3_A1.mat` | 139962 | 140487 | 140487 |
| `S15_E2_A1.mat` | 86146 | 86288 | 86288 |
| `S15_E3_A1.mat` | 154019 | 154918 | 154918 |
| `S16_E2_A1.mat` | 85180 | 85560 | 85560 |
| `S18_E2_A1.mat` | 85348 | 86005 | 86005 |
| `S19_E2_A1.mat` | 85686 | 85694 | 85694 |
| `S1_E3_A1.mat` | 149838 | 149845 | 149845 |
| `S20_E2_A1.mat` | 86443 | 86454 | 86454 |
| `S21_E2_A1.mat` | 86274 | 86370 | 86370 |
| `S22_E2_A1.mat` | 86313 | 86317 | 86317 |
| `S24_E2_A1.mat` | 85829 | 86181 | 86181 |
| `S25_E2_A1.mat` | 86140 | 86296 | 86296 |
| ... 9 more | | |

---
## 3. Segment validity `[EMPIRICAL]`

| file | frames | segments | rest frames | movement frames | stimulus | reps |
|---|---|---|---|---|---|---|
| `S28_E1_A1.mat` | 1808331 | 102 | 1064608 | 743723 | 18 | [0, 1, 2, 3, 4, 5, 6] |
| `S34_E1_A1.mat` | 1796292 | 102 | 586478 | 1209814 | 18 | [0, 1, 2, 3, 4, 5, 6] |
| `S40_E1_A1.mat` | 1801392 | 102 | 1057055 | 744337 | 18 | [0, 1, 2, 3, 4, 5, 6] |
| `S46_E1_A1.mat` | 1797147 | 102 | 736421 | 1060726 | 18 | [0, 1, 2, 3, 4, 5, 6] |
| `S52_E1_A1.mat` | 1804722 | 102 | 1040502 | 764220 | 18 | [0, 1, 2, 3, 4, 5, 6] |
| `S58_E1_A1.mat` | 1771088 | 102 | 635936 | 1135152 | 18 | [0, 1, 2, 3, 4, 5, 6] |
| `S10_E2_A1.mat` | 85810 | 102 | 47503 | 38307 | 18 | [0, 1, 2, 3, 4, 5, 6] |
| `S16_E2_A1.mat` | 85180 | 102 | 56370 | 28810 | 18 | [0, 1, 2, 3, 4, 5, 6] |
| `S21_E2_A1.mat` | 86274 | 102 | 47920 | 38354 | 18 | [0, 1, 2, 3, 4, 5, 6] |
| `S27_E2_A1.mat` | 85973 | 102 | 48924 | 37049 | 18 | [0, 1, 2, 3, 4, 5, 6] |
| `S69_E2_A1.mat` | 203945 | 102 | 135383 | 68562 | 18 | [0, 1, 2, 3, 4, 5, 6] |
| `S74_E2_A1.mat` | 209024 | 102 | 130701 | 78323 | 18 | [0, 1, 2, 3, 4, 5, 6] |
| `S10_E3_A1.mat` | 137062 | 138 | 80828 | 56234 | 24 | [0, 1, 2, 3, 4, 5, 6] |
| `S13_E3_A1.mat` | 135046 | 138 | 85810 | 49236 | 24 | [0, 1, 2, 3, 4, 5, 6] |
| `S16_E3_A1.mat` | 135778 | 138 | 87024 | 48754 | 24 | [0, 1, 2, 3, 4, 5, 6] |
| `S3_E3_A1.mat` | 146959 | 138 | 90823 | 56136 | 24 | [0, 1, 2, 3, 4, 5, 6] |
| `S68_E3_A1.mat` | 258372 | 138 | 150557 | 107815 | 24 | [0, 1, 2, 3, 4, 5, 6] |
| `S70_E3_A1.mat` | 260036 | 138 | 160297 | 99739 | 24 | [0, 1, 2, 3, 4, 5, 6] |

Anomalies found: **0**.

`restimulus Ã— rerepetition` therefore forms clean, non-overlapping single-action segments, and 17 movements Ã— 6 repetitions + rest is reproduced exactly (103 segments for `S1_E2_A1.mat`). `[EMPIRICAL]`

---
## 4. Reference posture - identified from the data, not assumed

the DB9 paper: 'The reference posture was chosen as the central part of movement 11 in exercise B (Fig. 2), corresponding to the hand resting on the table with the fingers closed together and extended.' `[OFFICIAL]`

Frozen rule: minimise mean over channels of |glove - S_ref(implied)|

| restimulus | mean&nbsp;|Î”| over the recovered channels |
|---|---|
| **11** | 4.33 |
| **12** | 6.84 |
| **9** | 6.92 |
| **17** | 7.44 |
| **10** | 7.84 |
| **16** | 8.35 |
| **14** | 10.14 |
| **13** | 11.14 |

Best restimulus = **11**, i.e. the data independently confirms the paper's movement 11. `[EMPIRICAL]` + `[OFFICIAL]`

---
## 5. The old extraction logic versus the correct logic

| | old audit logic | this lane's logic |
|---|---|---|
| segmentation key | `repetition` (and in one place a count of containers) | `(restimulus, rerepetition)` |
| why it fails | `repetition` is the PRE-relabelling vector; it is longer than `glove`/`angles` in 24 of 99 files, so indexing kinematics with it shifts every boundary; and its value 0 does not coincide with `restimulus == 0` | `restimulus`/`rerepetition` are length-identical to `glove`/`angles` in **every** file |
| reference posture | taken on trust | re-identified from the release and then checked against the paper |
| channel order | taken from a secondary document | read from the `order_of_angles` field stored inside each `.mat` |

This is the mechanism by which a correct detector can be made to report a wrong channel: the physiology never changed, the index did. `[INFERENCE]`

