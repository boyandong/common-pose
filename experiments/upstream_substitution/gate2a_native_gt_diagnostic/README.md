# GATE 2A — native-coordinate GT-only frozen-head diagnostic

**Gate:** PHASE 1 / GATE 2A · **Class: EXPLORATORY DIAGNOSTIC** · local only, no server, no GPU,
no predicted pose, no calibration fitting, no semantic accuracy claim.

| | |
|---|---|
| `GATE2A_DECISION` | **`STRUCTURED_NONDEGENERATE`** |
| plan | `GATE2A_PLAN.md`, SHA-256 `9fc91ea7b34fdfdc08791d9ebcba8922aa253b826edf89fa54222b6d1eb46ce7` |
| frozen-head replication | **EXACT** (12/12 frozen numbers reproduced) |
| analysis samples | 88 019 GT-valid samples at 50 Hz |
| degenerate triggers | **none** |
| ambiguous triggers | **none** |

---

## The one question, and the one answer

> Does the frozen DB9 posture head's output on **native-coordinate emg2pose ground-truth pose**
> exhibit at least structured, non-degenerate, further-studyable task behaviour — with no
> cross-source calibration fitting?

**Yes, descriptively.** The head produces a spread, side-consistent, temporally coherent and
stage-differentiated output. **It does not mean the output is correct**; this gate cannot and does
not establish that.

## Headline numbers

| diagnostic | emg2pose GT (native units) | DB9 comparator |
|---|---|---|
| class occupancy 1…8 | 0.0404 · 0.0471 · 0.0002 · 0.1998 · 0.0729 · 0.1533 · 0.0234 · **0.4629** | max 0.1863 |
| occupancy entropy | **2.1929 bits** (max 3.0) | 2.9584 bits |
| maximum-class fraction | 0.4629 (class 8) | 0.1863 |
| margin median / IQR | **0.8465** / [0.3684, 1.7015] | 1.9875 |
| margin ≤ 0 | **0.0000** | — |
| switch rate (per 20 ms sample) | **0.0762** | 0.0458 |
| median dwell | 6 blocks = **0.120 s** | 9 frames |
| class-4 fraction | 0.1998 | (DB9 recall 0.4947) |
| top-2 pair = {4,5} | **0.0678** | — |
| dominant class per stage | 3 distinct (2, 4, 6, 8 across 15 stages) | — |
| dominant class per side | 8 on both sides | — |

The occupancy is **not** collapsed: entropy 2.19 bits, no class above 47 %, and class 3 at 0.0002 is
the one genuine near-absence. The switch rate is ~1.7× the DB9 head's own rate at a comparable
cadence and still implies a ~120 ms median dwell — frame-to-frame instability is not present. The
known weak class-4/5 boundary takes 27 % of mass combined but only 6.8 % of samples have it as their
top-2 pair, so behaviour is **not** dominated by that fragile region.

## How the frozen head was instantiated

**No serialized head exists.** The workspace was searched for `.joblib/.pkl/.pickle/.onnx/.pt/.pth/
.sav` model files and for `*lda*`/`*frozen_head*`/`*posture_head*` artifacts; the only DB9 LDA
stores belong to other lanes and are not the official 8-posture task. Reconstruction was therefore
required — and is explicitly authorised by the gate — under the **identical frozen protocol**,
mirrored line-for-line from `final_validation.py` / `fx_common.py`:

Exercise-B movement ids 1–8 · central 60 % of each `restimulus × rerepetition` segment ·
`SEG_CAP = 200` via `np.linspace` · `np.deg2rad` · train-fold z-score with the `sd > 0` guard ·
`sklearn LinearDiscriminantAnalysis()` with **all defaults** (`solver=svd`, `shrinkage=None`) ·
leave-one-subject-out on the archive-slot global key.

**Proof that no tuning occurred:** the reconstruction reproduces the frozen record
`FINAL_VALIDATION.json .Q4_posture8.results.B_TRUSTED_DB9_POSE_v1` **exactly** on all twelve
quantities — `n_frames` 123 200, `n_subjects` 77, accuracy 0.747914, BA 0.747914, macro-F1 0.745980,
and per-class recall 0.86026 / 0.691364 / 0.875584 / 0.49474 / 0.902857 / 0.750974 / 0.829026 /
0.578506.

**Object applied to emg2pose:** one **aggregate** LDA trained on all 77 DB9 participants, so every
emg2pose frame is out-of-sample. Standardisation statistics are **DB9's only**; standardising on
emg2pose would be fitting a cross-source transform. Random seed: none used (the protocol is
deterministic).

## Sampling policy

The pose stream is stored at 2 kHz but updates at **50 Hz**, linearly interpolated to 2 kHz. This
gate reuses the project's own frozen reduction (`bridge_audit/run_bridge_audit.py`,
`POSE_STRIDE = 40`, `EMG_RATE = 2000`): each non-overlapping 40-row block → **one** analysis
sample by block mean, and a block is valid only if **all 40 rows** are GT-valid.

| | rows |
|---|---|
| stored rows | 4 218 756 |
| GT-valid rows | 3 559 584 (IK-failure 659 172 = **0.1562**) |
| total 40-row blocks | 105 468 |
| **analysis samples** | **88 019** |
| analysis rate | **50 Hz** |

Transparency note: the block rule inflates the excluded fraction from 0.1562 to **0.1654**, because
a block is dropped if *any* of its 40 rows is an IK failure. That is the deliberate consequence of
never mixing an IK gap into an analysis sample; it costs ~1 percentage point of data.

## Files

| file | role |
|---|---|
| `GATE2A_PLAN.md` / `.sha256` | the plan, frozen and hashed **before** any head output was read |
| `artifacts/GT_HEAD_BEHAVIOR.json` | full machine-readable diagnostic: occupancy, margins, temporal, side, stage, class 4/5, DB9 comparator, firewall, per-file rows |
| `artifacts/GT_HEAD_BEHAVIOR_BY_STAGE.csv` | 15 stages × occupancy / dominant class / margin / class-4 |
| `artifacts/GT_HEAD_BEHAVIOR_BY_SIDE.csv` | left vs right |
| `artifacts/GATE2A_DECISION.json` | decision, triggers, thresholds, evidence, next step |
| `scripts/run_gate2a_native_gt.py` | the run |
| `scripts/_verify_gate2a.py` | independent check of the artifacts |
| `logs/gate2a_stdout.txt` | captured stdout |

## Stage stratification is not semantics

`stage` is a compound **activity** label; it is **not** posture ground truth for the DB9 ontology.
The per-stage split is reported because it is required and because stage-wise differentiation is
itself evidence of structure (a degenerate head would look identical everywhere) — never as an
accuracy measure. Note for example `FingerPinchesSingleFingerPinchesMultiple` landing 62.4 % on
class 4, and `FingerAbductionSeries` 83.5 % on class 8. *No claim is made that natural "pinch"
poses are truly DB9 class 4.*

## What this gate does not claim

No posture accuracy, balanced accuracy, macro-F1, semantic correctness, sensitivity, specificity or
transfer accuracy on emg2pose — emg2pose carries no per-frame posture ground truth for the DB9
ontology, so none of those quantities is computable here. No cross-source calibration equivalence.
No in-distribution / out-of-distribution labelling (no DB9 quantile was used as a gate). No
`UNKNOWN`. Structured output is **not** semantic correctness.

## Firewall

```
PREDICTED_POSE_USED        = NO
GT_VS_PRED_AGREEMENT       = NOT RUN
EMG_INFERENCE_RUN          = NO
UNKNOWN_GATE_CREATED       = NO
CALIBRATION_FITTED         = NO
SEMANTIC_ACCURACY_CLAIMED  = NO
OFFSET_OR_SCALE_FITTED     = NO
SUBSET_SELECTED            = NO
MODEL_TUNED                = NO
SERVER_USED                = NO
```

## Reproduce

```powershell
cd common-pose\experiments\upstream_substitution\gate2a_native_gt_diagnostic
C:\emg2pose-venv\Scripts\python.exe -X utf8 scripts\run_gate2a_native_gt.py
C:\emg2pose-venv\Scripts\python.exe -X utf8 scripts\_verify_gate2a.py
```

## Next allowed step

> Design a fresh prospective GT semantic-applicability validation before any GT-vs-PRED substitution
> claim.
