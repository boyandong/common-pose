# SHARED10_poc_v1 - PROVENANCE AUDIT (P0)

**Frozen plan SHA-256:** `fba2b20623392dd809d5ed28c7850387acc721e9a91ff1611e7fba0d89fc889d`  **Commit:** COMMIT PENDING

---
## 0. Verdict, in one paragraph

> **`SHARED10-SEMANTIC-MISMATCH`.** The ten indices are correct positions for the MOVMUS-UJI guide v2.1 column order, but the KIN-MUS release stores its 18 columns in the order the KIN-MUS dataset's **own** paper gives in Table 2. The two orders differ by four swapped adjacent pairs (8 of 18 positions). Applying the frozen indices to the real array therefore selects **6 intended DOFs and 4 different ones**. Four entries are silently the wrong anatomical channel: one thumb CMC **abduction** where thumb CMC **flexion** was intended, and three relative **abductions** where index / ring / little MCP **flexion** were intended. This is a DB9-class wrong-column failure. `[EMPIRICAL]`

---
## 1. Every reference to the frozen subset in the project

29 files outside this lane mention `shared10` or the index vector. The definition chain is:

```
pose_api_dataset_admission/tools/build_mapping_and_origin.py
   -> POSE_API_DOF_MAPPING_MATRIX.json / FIRST_POC_DATASET_DECISION.json
      (api_dofs = the 10 names, released_column_indices = [0,2,4,6,7,8,9,11,13,15])
kinmus_task_observability/tools/obs_plan.py  -> SHARED10
   -> obs_common.SHARED10_COLUMNS = (0,2,4,6,7,8,9,11,13,15)
      -> build_cv.py / build_features.py / build_geometry.py
```

| file | mentions | sha256 |
|---|---|---|
| `kinmus_task_observability\tools\kinmus_task_observability_fact_check.py` | 33 | `6e9de0de3139db05...` |
| `kinmus_task_observability\tools\build_report.py` | 19 | `0be3710f66a51163...` |
| `kinmus_task_observability\tools\obs_plan.py` | 14 | `2c1ba643eba494f5...` |
| `kinmus_task_observability\KINMUS_TASK_OBSERVABILITY_REPORT.md` | 13 | `808043373d7bfdec...` |
| `kinmus_task_observability\KINMUS_TASK_OBSERVABILITY_PLAN.json` | 12 | `19da16a52d11ad15...` |
| `kinmus_task_observability\tools\build_features.py` | 12 | `832f812acd6394b1...` |
| `kinmus_task_observability\tools\build_figures.py` | 12 | `0038c2957ecd22e8...` |
| `kinmus_task_observability\tools\freeze_plan.py` | 12 | `9ff42bb9f342cc65...` |
| `kinmus_task_observability\KINMUS_TASK_OBSERVABILITY_HANDOVER.md` | 8 | `bbf89e738bacb608...` |
| `kinmus_task_observability\tools\build_provenance.py` | 7 | `3a4363195a83799f...` |
| `kinmus_task_observability\tools\build_cv.py` | 6 | `78e9761ee9e983ae...` |
| `kinmus_task_observability\tools\build_geometry.py` | 6 | `8de17a9aabeb96fd...` |
| `kinmus_task_observability\KINMUS_FULL18_DIAGNOSTIC.json` | 5 | `c9b1ee8f310d2c4d...` |
| `kinmus_task_observability\tools\obs_common.py` | 5 | `d2a41b0c073ef6e8...` |
| `kinmus_task_observability\KINMUS_TASK_OBSERVABILITY_FULL_LOG.txt` | 4 | `099a2d2f69d83a14...` |
| `kinmus_task_observability\KINMUS_TASK_OBSERVABILITY_DECISION.json` | 3 | `2f0a21d81183c002...` |
| `kinmus_task_observability\tools\assemble_log.py` | 3 | `6e621f55876a6382...` |
| `kinmus_task_observability\tools\build_decision.py` | 3 | `0d30ec878eb72e41...` |
| `pose_api_dataset_admission\DATASET_ADMISSION_HANDOVER.md` | 3 | `5947582a55ede619...` |
| `pose_api_dataset_admission\DATASET_ADMISSION_REPORT.md` | 3 | `3b5f020f38d0396f...` |
| `pose_api_dataset_admission\NEXT_POC_EXPERIMENT_PLAN.md` | 3 | `276fba2598e1d71b...` |
| `kinmus_task_observability\KINMUS_OBSERVABILITY_SOURCE_PROVENANCE.json` | 2 | `de50d96e5a4a3111...` |
| `kinmus_task_observability\KINMUS_PHASE_POSE_GEOMETRY.json` | 2 | `46553cdb74dca3ce...` |
| `pose_api_dataset_admission\DATASET_ADMISSION_FULL_LOG.txt` | 2 | `c4c3341e3d0755f9...` |
| `pose_api_dataset_admission\tools\build_next_experiment.py` | 2 | `42b552bf8eda5f5b...` |
| ... 4 more | | |

---
## 2. The exact source array (question 1)

| step | value |
|---|---|
| filename | `<PROJECT_ROOT>\pose_api_dataset_admission\raw\kin_mus\KIN_MUS_UJI.mat` |
| sha256 | `530a9e51b19574b0f5dee0c9263b1a50eafc7204b14cae67b6b1bb854671c722` |
| bytes | `86661263` |
| loader | `scipy.io.loadmat(..., squeeze_me=True, struct_as_record=False)` |
| variable | `EMG_KIN_v4` |
| variable_shape | `1 x 1716 struct array` |
| element_field | `Kinematic_data` |
| element_shape | `(N_i, 18)` |
| stacked_shape | `[564894, 18]` |
| source_schema | each row is one 100 Hz sample; the 18 columns are a bare numeric matrix with NO stored column labels anywhere in the file |
| evidence | `EMPIRICAL` |

> The 18 columns are a **bare numeric matrix**. MATLAB arrays carry no column names, and the file contains no sidecar. The order is therefore a **documentation** fact, not a data fact, and the only authoritative source is the dataset's own paper. `[EMPIRICAL]`

---
## 3. Which 18-DOF order (question 2) - answer: **KIN-MUS's own (option A)**, and it is *not* the order the project used

Two authoritative orders exist for the same 18 angles, and they disagree:

| position | `H_GUIDE` MOVMUS guide v2.1 Table 4 == calibration code == KINE-ADL guide | `H_T2` KIN-MUS 2019 paper Table 2 | same? |
|---|---|---|---|
| 0 | CMC1_F | CMC1_A | **NO** |
| 1 | CMC1_A | CMC1_F | **NO** |
| 2 | MCP1_F | MCP1_F | yes |
| 3 | IP1_F | IP1_F | yes |
| 4 | MCP2_F | MCP2-3_A | **NO** |
| 5 | MCP2-3_A | MCP2_F | **NO** |
| 6 | PIP2_F | PIP2_F | yes |
| 7 | MCP3_F | MCP3_F | yes |
| 8 | PIP3_F | PIP3_F | yes |
| 9 | MCP4_F | MCP3-4_A | **NO** |
| 10 | MCP3-4_A | MCP4_F | **NO** |
| 11 | PIP4_F | PIP4_F | yes |
| 12 | PalmArch | PalmArch | yes |
| 13 | MCP5_F | MCP4-5_A | **NO** |
| 14 | MCP4-5_A | MCP5_F | **NO** |
| 15 | PIP5_F | PIP5_F | yes |
| 16 | WR_F | WR_F | yes |
| 17 | WR_A | WR_A | yes |

**8 of 18 positions differ**, i.e. four adjacent pairs are swapped.** `[DOC]`

### 3.1 The four pre-declared discrimination tests, both hypotheses reported

**`D1_thumb_cmc_amplitude`** - the official calibration code gives CMC1_A a structurally smaller gain (0.267) than CMC1_F (0.802) on the dominant gauge, so the low-amplitude member of the first two columns is CMC1_A

```json
{
  "rationale": "the official calibration code gives CMC1_A a structurally smaller gain (0.267) than CMC1_F (0.802) on the dominant gauge, so the low-amplitude member of the first two columns is CMC1_A",
  "sd_col0": 5.215332934479026,
  "sd_col1": 18.326353585857735,
  "low_amplitude_column": 0,
  "H_GUIDE": "CMC1_F",
  "H_T2": "CMC1_A",
  "verdict": "H_T2",
  "evidence": "EMPIRICAL"
}
```
verdict: **H_T2**  `[EMPIRICAL]`

**`D2_same_finger_MCP_PIP`** - the MCP-flexion column of finger k must correlate more strongly with the PIP-flexion column of the SAME finger than a competing relative-abduction column does; a same-finger MCP/PIP pair must co-flex positively

```json
{
  "rationale": "the MCP-flexion column of finger k must correlate more strongly with the PIP-flexion column of the SAME finger than a competing relative-abduction column does; a same-finger MCP/PIP pair must co-flex positively",
  "per_finger": {
    "finger2": {
      "pip_col": 6,
      "corr_colA": -0.132843664190627,
      "corr_colB": 0.19324351574363144,
      "colA": 4,
      "colB": 5,
      "stronger_col": 5,
      "H_GUIDE_names_colA_as_MCP": true,
      "H_T2_names_colB_as_MCP": true
    },
    "finger4": {
      "pip_col": 11,
      "corr_colA": 0.02567297553249332,
      "corr_colB": 0.48736089151962375,
      "colA": 9,
      "colB": 10,
      "stronger_col": 10,
      "H_GUIDE_names_colA_as_MCP": true,
      "H_T2_names_colB_as_MCP": true
    },
    "finger5": {
      "pip_col": 15,
      "corr_colA": -0.43096758816999786,
      "corr_colB": 0.5574320755545149,
      "colA": 13,
      "colB": 14,
      "stronger_col": 14,
      "H_GUIDE_names_colA_as_MCP": true,
      "H_T2_names_colB_as_MCP": true
    }
  },
  "n_fingers_testable": 3,
  "H_T2_matches": 3,
  "H_GUIDE_matches": 0,
  "verdict": "H_T2",
  "evidence": "EMPIRICAL"
}
```
verdict: **H_T2**  `[EMPIRICAL]`

**`D3_paper_positive_median_largest_FROM`** - the dataset's own Technical Validation states that MCP and PIP FLEXION present a positive median with the largest functional range

```json
{
  "rationale": "the dataset's own Technical Validation states that MCP and PIP FLEXION present a positive median with the largest functional range",
  "per_hypothesis": {
    "H_GUIDE": {
      "cols": [
        2,
        4,
        7,
        9,
        13
      ],
      "medians": [
        -2.79189,
        4.021425,
        35.3107,
        6.7295549999999995,
        1.48565
      ],
      "sd": [
        9.925428406311912,
        8.746709402531339,
        23.49607649244021,
        6.167832573069403,
        5.652999973844898
      ],
      "all_positive_median": false,
      "min_sd": 5.652999973844898,
      "max_sd_of_18": 33.95526805251199
    },
    "H_T2": {
      "cols": [
        2,
        5,
        7,
        10,
        14
      ],
      "medians": [
        -2.79189,
        23.06635,
        35.3107,
        23.9263,
        21.290149999999997
      ],
      "sd": [
        9.925428406311912,
        19.160978411205626,
        23.49607649244021,
        23.04697032300618,
        25.08302880465263
      ],
      "all_positive_median": false,
      "min_sd": 9.925428406311912,
      "max_sd_of_18": 33.95526805251199
    }
  },
  "verdict": "H_T2",
  "evidence": "EMPIRICAL"
}
```
verdict: **H_T2**  `[EMPIRICAL]`

**`D4_abduction_sign_pattern`** - relative-abduction channels of adjacent metacarpals must be negatively coupled to the MCP flexion of the metacarpals they span, and all four same-finger MCP/PIP flexion pairs must co-flex positively; a naming that requires a negative same-finger MCP-PIP correlation is anatomically indefensible

```json
{
  "rationale": "relative-abduction channels of adjacent metacarpals must be negatively coupled to the MCP flexion of the metacarpals they span, and all four same-finger MCP/PIP flexion pairs must co-flex positively; a naming that requires a negative same-finger MCP-PIP correlation is anatomically indefensible",
  "per_hypothesis": {
    "H_GUIDE": {
      "abduction_to_spanned_MCP_flexion": [
        {
          "abduction": "MCP2-3_A",
          "abd_col": 5,
          "partner": "MCP2_F",
          "col": 4,
          "r": -0.6004158904645663
        },
        {
          "abduction": "MCP2-3_A",
          "abd_col": 5,
          "partner": "MCP3_F",
          "col": 7,
          "r": 0.8197895281112113
        },
        {
          "abduction": "MCP3-4_A",
          "abd_col": 10,
          "partner": "MCP3_F",
          "col": 7,
          "r": 0.8896616447391864
        },
        {
          "abduction": "MCP3-4_A",
          "abd_col": 10,
          "partner": "MCP4_F",
          "col": 9,
          "r": -0.46612424447702977
        },
        {
          "abduction": "MCP4-5_A",
          "abd_col": 14,
          "partner": "MCP4_F",
          "col": 9,
          "r": -0.21857707077559455
        },
        {
          "abduction": "MCP4-5_A",
          "abd_col": 14,
          "partner": "MCP5_F",
          "col": 13,
          "r": -0.7952631300893104
        }
      ],
      "n_negative": 4,
      "n_pairs": 6,
      "same_finger_MCP_PIP": [
        {
          "finger": 2,
          "r": -0.132843664190627
        },
        {
          "finger": 3,
          "r": 0.3154105436006948
        },
        {
          "finger": 4,
          "r": 0.02567297553249332
        },
        {
          "finger": 5,
          "r": -0.43096758816999786
        }
      ],
      "n_positive_of_4": 2,
      "min_same_finger_r": -0.43096758816999786
    },
    "H_T2": {
      "abduction_to_spanned_MCP_flexion": [
        {
          "abduction": "MCP2-3_A",
          "abd_col": 4,
          "partner": "MCP2_F",
          "col": 5,
          "r": -0.6004158904645663
        },
        {
          "abduction": "MCP2-3_A",
          "abd_col": 4,
          "partner": "MCP3_F",
          "col": 7,
          "r": -0.4861091050186132
        },
        {
          "abduction": "MCP3-4_A",
          "abd_col": 9,
          "partner": "MCP3_F",
          "col": 7,
          "r": -0.47737022109758226
        },
        {
          "abduction": "MCP3-4_A",
          "abd_col": 9,
          "partner": "MCP4_F",
          "col": 10,
          "r": -0.46612424447702977
```
verdict: **H_T2**  `[EMPIRICAL]`

### 3.2 Resolution

Verdicts were ['H_T2', 'H_T2', 'H_T2', 'H_T2']. Under the frozen rule (no conflict and at least three positive tests) the released array follows **`H_T2`**.

`H_T2` is the order of the KIN-MUS dataset's own paper. That is also what the paper states in words: *'Angles (18 columns): Calibrated anatomical angles in the following order (Table 2)'*. `[DOC]` + `[EMPIRICAL]`

---
## 4. Per-index table (question 3)

| pos | index | intended DOF | column name if guide order | column name if T2 order | ACTUAL DOF | motion | unit | sign | zero | measured/derived | confidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 | `thumb_cmc_flexion` | CMC1_F | CMC1_A | **`CMC1_A`** | abduction | deg | abduction + / adduction - | mean of the recorded reference posture | measured (transpose mix of the same two gauges) | `NONE` |
| 2 | 2 | `thumb_mcp_flexion` | MCP1_F | MCP1_F | **`MCP1_F`** | flexion | deg | flexion + / extension - | reference posture | measured | `HIGH` |
| 3 | 4 | `index_mcp_flexion` | MCP2_F | MCP2-3_A | **`MCP2-3_A`** | relative abduction | deg | separated + / together - | reference posture | measured (linear + quadratic + interaction model in the MCP2 and MCP3 flexion gauges) | `NONE` |
| 4 | 6 | `index_pip_flexion` | PIP2_F | PIP2_F | **`PIP2_F`** | flexion | deg | flexion + / extension - | reference posture | measured | `HIGH` |
| 5 | 7 | `middle_mcp_flexion` | MCP3_F | MCP3_F | **`MCP3_F`** | flexion | deg | flexion + / extension - | reference posture | measured | `HIGH` |
| 6 | 8 | `middle_pip_flexion` | PIP3_F | PIP3_F | **`PIP3_F`** | flexion | deg | flexion + / extension - | reference posture | measured | `HIGH` |
| 7 | 9 | `ring_mcp_flexion` | MCP4_F | MCP3-4_A | **`MCP3-4_A`** | relative abduction | deg | separated + / together - | reference posture | measured (same model form, sign-negated) | `NONE` |
| 8 | 11 | `ring_pip_flexion` | PIP4_F | PIP4_F | **`PIP4_F`** | flexion | deg | flexion + / extension - | reference posture | measured | `HIGH` |
| 9 | 13 | `pinky_mcp_flexion` | MCP5_F | MCP4-5_A | **`MCP4-5_A`** | relative abduction | deg | separated + / together - | reference posture | measured (same model form, sign-negated) | `NONE` |
| 10 | 15 | `pinky_pip_flexion` | PIP5_F | PIP5_F | **`PIP5_F`** | flexion | deg | flexion + / extension - | reference posture | measured | `HIGH` |

### 4.1 The mismatch, stated plainly

| pos | what we thought it was | what it actually is |
|---|---|---|
| 1 | `thumb_cmc_flexion` (`CMC1_F`) | **`CMC1_A`** - thumb CMC abduction |
| 3 | `index_mcp_flexion` (`MCP2_F`) | **`MCP2-3_A`** - index-middle metacarpals relative abduction |
| 7 | `ring_mcp_flexion` (`MCP4_F`) | **`MCP3-4_A`** - middle-ring metacarpals relative abduction |
| 9 | `pinky_mcp_flexion` (`MCP5_F`) | **`MCP4-5_A`** - ring-little metacarpals relative abduction |

The four affected channels are precisely the four *non*-shared positions of the two orders: positions 0/1, 4/5, 9/10 and 13/14.

**The index vector that would select the intended 10 DOFs is `[1, 2, 5, 6, 7, 8, 10, 11, 14, 15]`**, not `[0, 2, 4, 6, 7, 8, 9, 11, 13, 15]`. `[INFERENCE]`

---
## 5. Side-by-side KIN-MUS vs KINE-ADL (question 4)

The two UJI releases published in 2019 do **not** share a column order. Positional mapping between them is therefore forbidden.

| position | KIN-MUS 2019 Table 2 | KINE-ADL guide | MOVMUS guide v2.1 | agree? |
|---|---|---|---|---|
| 0 | CMC1_A | CMC1_F | CMC1_F | **NO** |
| 1 | CMC1_F | CMC1_A | CMC1_A | **NO** |
| 2 | MCP1_F | MCP1_F | MCP1_F | yes |
| 3 | IP1_F | IP1_F | IP1_F | yes |
| 4 | MCP2-3_A | MCP2_F | MCP2_F | **NO** |
| 5 | MCP2_F | MCP2-3_A | MCP2-3_A | **NO** |
| 6 | PIP2_F | PIP2_F | PIP2_F | yes |
| 7 | MCP3_F | MCP3_F | MCP3_F | yes |
| 8 | PIP3_F | PIP3_F | PIP3_F | yes |
| 9 | MCP3-4_A | MCP4_F | MCP4_F | **NO** |
| 10 | MCP4_F | MCP3-4_A | MCP3-4_A | **NO** |
| 11 | PIP4_F | PIP4_F | PIP4_F | yes |
| 12 | PalmArch | PalmArch | PalmArch | yes |
| 13 | MCP4-5_A | MCP5_F | MCP5_F | **NO** |
| 14 | MCP5_F | MCP4-5_A | MCP4-5_A | **NO** |
| 15 | PIP5_F | PIP5_F | PIP5_F | yes |
| 16 | WR_F | WR_F | WR_F | yes |
| 17 | WR_A | WR_A | WR_A | yes |

Reordered to expose the difference as a permutation:

```
KIN-MUS (Table 2)  : CMC1_A CMC1_F MCP1_F IP1_F MCP2-3_A MCP2_F PIP2_F MCP3_F PIP3_F MCP3-4_A MCP4_F PIP4_F PalmArch MCP4-5_A MCP5_F PIP5_F WR_F WR_A
KINE-ADL (guide)   : CMC1_F CMC1_A MCP1_F IP1_F MCP2_F MCP2-3_A PIP2_F MCP3_F PIP3_F MCP4_F MCP3-4_A PIP4_F PalmArch MCP5_F MCP4-5_A PIP5_F WR_F WR_A
```

---
## 6. Wrist-deviation sign convention (question 5)

| document | WR_A convention |
|---|---|
| KIN-MUS 2019 paper Table 3 | WR_A: Radial deviation + / Ulnar deviation - |
| KINE-ADL 2019 paper sign criteria | WR_A: Ulnar deviation + / Radial deviation - |
| MOVMUS-UJI guide v2.1 section 4.3 | WR_A: Ulnar deviation + / Radial deviation - |

**`DOCUMENTATION_CONFLICT`.** DOCUMENTATION_CONFLICT unresolved in one direction. Two of the three official documents, and the sibling KINE-ADL release published the same year, say ulnar+; the KIN-MUS paper says radial+ and its own result text agrees with radial+. The two datasets must therefore NOT be numerically merged on the wrist-deviation channel without an independent anchor. `[DOC]`

Self-consistency check on the KIN-MUS release itself: the KIN-MUS paper's own Technical Validation says the wrist shows 'a negative median value (ulnar deviation)', which is only consistent with radial+/ulnar- ; the measured median of column 17 is -12.26 deg `[EMPIRICAL]`

---
## 7. Root cause

The upstream admission lane named the KIN-MUS release's 18 columns from the MOVMUS-UJI guide v2.1 Table 4. That guide documents the LARGER, LATER MOVMUS-UJI dataset (2023), not the 2019 KIN-MUS release, and its column order differs from the KIN-MUS paper's own Table 2 at 4 of 18 positions. The shared10 indices are correct positions for the guide order and were then applied to an array stored in Table 2 order.

---
## 8. What is NOT claimed here

* This audit did **not** re-run any classifier. The old *numbers* are untouched by this finding - see `ADMISSION_DECISION.md` for the per-result re-classification.
* The order was resolved from documentation plus four model-free correlation tests. A residual possibility remains that the released array uses some third order; `[UNRESOLVED]`, but no third order is documented anywhere and no third order reproduces the observed same-finger MCP/PIP co-flexion.
* No sign, offset, scale or column was chosen to improve any result. The correction direction here is fixed by the documentation, not by performance.
