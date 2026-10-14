# GATE 2A PLAN — native-coordinate GT-only frozen-head diagnostic

**Status: FROZEN. Write this file, hash it, and only then read any head output.**
**Gate class: EXPLORATORY DIAGNOSTIC.** Not transfer validation, not semantic accuracy
evaluation, not cross-source calibration validation, not Common Pose hypothesis confirmation.

**Frozen representation:** `TRUSTED_DB9_POSE_v1`
**Subset SHA-256:** `e51dde6e63941fd080c84f3896a98cf50fba9e17d5f9cebe909253d5465782d1`
**Frozen DB9 baseline record:** `audits/db9/channel_forensic/artifacts/FINAL_VALIDATION.json`
`.Q4_posture8` (77 participants, 8 classes, trusted-8 BA = 0.7479, Macro-F1 = 0.7460)

**Upstream gate:** GATE 1.5 → `ZERO_GATE = NOT_EVALUABLE_LOCALLY`
(no independent physical reference anchor in the local emg2pose corpus).
Consequence carried into this gate: **no zero calibration is fitted or invented.**

---

## 0. The one question this gate answers

> Without any cross-source calibration fitting, does the frozen DB9 posture head's output on
> emg2pose **ground-truth** pose exhibit at least structured, non-degenerate, further-studyable
> task behaviour?

It does **not** answer whether that behaviour is *correct*. Structured output ≠ semantic
correctness.

---

## 1. What is forbidden in this gate

* No training of any new model for the diagnostic itself (the frozen head is reconstructed only
  because no serialized head artifact exists — see §2 — and it is reconstructed *identically*).
* No cross-source calibration fitting of any kind: no offset, scale, affine transform, percentile
  alignment, distribution matching, per-stage calibration, Procrustes, regression.
* No predicted pose. `PREDICTED_POSE_USED = NO`. No EMG inference. No GT-vs-PRED agreement.
* No open-set rescue: no Mahalanobis threshold, OCSVM, GMM, kNN support, conformal rejection, no
  `UNKNOWN` class, no rejection of samples, no "DB9-supported" subsetting.
* No semantic accuracy claim: no accuracy, balanced accuracy, macro-F1, sensitivity, specificity
  or transfer accuracy on emg2pose.
* No frame selection by predicted class, margin, DB9 distance, support probability, prototype
  closeness, or trusted-8 norm. No "good-looking" subset.
* No adding a new calibrated probability model.

---

## 2. Frozen head: instantiation

**No serialized head artifact exists.** Searched: the whole workspace for
`.joblib/.pkl/.pickle/.onnx/.pt/.pth/.sav` model files, and for any `*lda*`/`*frozen_head*`/
`*posture_head*` artifact. The only DB9 LDA stores are confusion matrices and prediction
archives from *other* lanes (`data/ninapro_db9/models*`, `results*`) plus
`db9_distributional_open_set/models/DB9_LDA_REFERENCE_MODEL.json`, none of which is the
official 8-posture task head. **Reconstruction is therefore required and is explicitly
authorised by the gate.**

Reconstruction uses the **exact frozen protocol**, transcribed from
`audits/db9/channel_forensic/tools/final_validation.py` (functions `load_exercise_b`, `collect`,
`loso`) and `fx_common.py` (`segments`, `core`) — mirrored, not re-designed:

| element | frozen value | source |
|---|---|---|
| task | NinaPro DB9 Exercise-B hand configurations, **movement ids 1–8 only** | `FINAL_VALIDATION.json .Q4_posture8.classes` |
| frame cap | **200 per segment**, via `np.linspace(0, n-1, 200).astype(int)` when `n > 200` | `final_validation.py` `SEG_CAP = 200`, `collect()` |
| window | **central 60 %** of each segment: `k = max(1, round(n*0.6))`, `a = start + (n-k)//2` | `fx_common.core(seg, frac=0.6)` |
| segmentation | `restimulus × rerepetition` (never `stimulus`/`repetition`) | `fx_common.segments` |
| validity | per-frame `np.isfinite(ang).all(axis=1)` on the selected channels | `collect()` |
| channels | the 8 frozen `TRUSTED_DB9_POSE_v1` channels, selected **by name**, column indices `[2, 3, 4, 6, 7, 9, 13, 15]` | frozen subset + `DB9_CANONICAL16_MAPPING.md` |
| units | degrees → radians via `np.deg2rad` | `collect()` |
| standardisation | **z-score with mean/std of the TRAINING fold**; `sd = where(sd > 0, sd, 1.0)` | `loso()` |
| classifier | `sklearn.discriminant_analysis.LinearDiscriminantAnalysis()` with **all default hyperparameters** | `loso()` |
| split | leave-one-subject-out on the archive-slot global key (1..77) | `loso()` |
| random seed | **none used** — the protocol is deterministic | — |

**Which head is applied to emg2pose.** The frozen baseline is a LOSO *evaluation*, not a single
deployable object. emg2pose is wholly unseen data that is in no DB9 fold. Therefore the head
applied is **one aggregate head trained on all 77 DB9 participants** using the identical
protocol, so that every emg2pose frame is out-of-sample. This is chosen **now**, before any
output, and does not depend on results.

**DB9-side standardisation.** The z-score statistics are DB9's (the head's own), never
emg2pose's. Standardising on emg2pose would be fitting a cross-source transform, which the gate
forbids.

**No tuning.** No hyperparameter is searched or adjusted; the class list is the official fixed
1–8; no feature is added, dropped or transformed beyond the frozen protocol. The only
"verification" permitted on the DB9 side is a **bit-for-bit replication check**: re-running the
frozen LOSO evaluation must reproduce the recorded trusted-8 numbers (BA 0.7479, Macro-F1
0.7460, per-class recall, 123 200 frames, 77 subjects). That is a reproduction check, not tuning,
and it is reported either way.

---

## 3. emg2pose input

**Ground truth only.** Field `emg2pose/timeseries.joint_angles` (20-D, radians). The predicted
pose is never read. No EMG inference is run.

Local corpus: 30 files, 1 session, 1 participant (`d387095792`), 15 stages per side,
**15 left + 15 right**, 4 218 756 stored rows, all `split = val`, `held_out_user = True`.

**Channel selection:** canonical16 name-based selection (`canonical_hand.py` mapping,
source indices `[0,1,2,3,5,6,7,9,10,11,13,14,15,17,18,19]`), then the trusted-8 columns
`thumb_mcp_flexion, thumb_ip_flexion, index_mcp_flexion, index_pip_flexion,
middle_mcp_flexion, ring_mcp_flexion, pinky_mcp_flexion, pinky_pip_flexion`
(canonical16 indices `[2,3,4,5,7,10,13,14]` → emg2pose indices `[2,3,5,6,9,13,17,18]`).
Values are passed through **natively**; the only operations are ordering and the radians unit
already in use. No offset, no scale, no re-reference.

**IK-validity:** a frame is valid iff **not all 20 joint angles are ~zero**
(`np.isclose(x, 0)` all-zero row test, identical to the official `get_ik_failures_mask`
semantics; the project's adapter agrees with the official helper on 4 218 756/4 218 756 samples).
Invalid rows are excluded.

---

## 4. Sampling policy — frozen before any head output

**The frozen reduction is the project's own, not a new choice.** The emg2pose pose stream is
stored at 2 kHz but the pose information updates at **50 Hz**, linearly interpolated to 2 kHz.
`bridge_audit/run_bridge_audit.py` already established this and encodes it as
`EMG_RATE = 2000`, `POSE_STRIDE = 40` ("2000 / 50 -> the model's native 50 Hz update
cadence"), with `resolve_native_grid()` *measuring* the native nodes inside the 2 kHz output
rather than assuming them, and reducing each non-overlapping 40-sample (20 ms) block to one
value **by averaging** — "symmetric, phase-robust, and cannot manufacture independent samples".

This gate reuses exactly that reduction:

* `n_blocks = n_rows // 40`; the trailing `< 40` remainder is dropped;
* each block → **one** analysis sample = block **mean** of the 8 channel values;
* **a block is GT-valid only if every one of its 40 rows is GT-valid**
  (no mixing across an IK gap);
* analysis sampling rate = **50 Hz**;
* global block index is retained to define per-file contiguity for temporal statistics.

**Why this rate.** It is the model's native pose-update cadence, recovered from the official
pipeline and independently measured by the project. It is *not* chosen for class balance, and no
alternative rate is evaluated. Reporting both the stored-row count and the analysis-sample count
is mandatory; the 40× reduction is stated explicitly so the sample count is never overstated.

---

## 5. Analysis population

**All valid emg2pose GT analysis samples**, both hand sides, all 15 stages, no exception. No
subsampling to a "good-looking" subset. Left and right are analysed together for the primary
numbers and reported separately as a stratification.

---

## 6. Head outputs used

| output | used | definition |
|---|---|---|
| predicted class 1–8 | yes | `LinearDiscriminantAnalysis.predict` |
| native discriminant scores | yes | `decision_function` (one column per class) |
| **primary margin** | yes | `top1_score − top2_score` in native discriminant units |
| secondary margin (reference only) | yes | difference of DB9-prior softmax scores, reported for comparability with any prior figure and **not** used for any verdict |

**Class priors for the secondary figure** are the DB9 head's own training-fold class
frequencies — never derived from emg2pose.

No `UNKNOWN` is created. No sample is rejected.

---

## 7. Required diagnostics

**A. Class occupancy** — fraction assigned to each class 1–8; Shannon entropy of the occupancy
vector in **bits** (`-Σ p log2 p`, max 3.0); maximum-class fraction.

**B. Margin structure** — median, IQR (p25/p75), p05, p95 of the primary margin. Reported
overall, per side, and per stage.

**C. Temporal behaviour** — over each file's contiguous block sequence:
class-switch rate (`n_switches / n_contiguous_transitions`, transitions per analysis sample,
i.e. per 20 ms); median dwell run-length in blocks and in seconds; and the same computed for the
**DB9 side** on its own frame sequences as the comparator, because a switch rate is meaningless
without one.

**D. Hand-side stratification** — left and right reported separately.

**E. Stage stratification** — per official stage: sample count, class occupancy, dominant class,
dominant-class fraction, median margin. **Stage names are activity labels, not posture ground
truth, and are never treated as such.**

---

## 8. DB9 comparator — descriptive only

Recomputed from the reconstructed head's LOSO predictions on DB9 itself, using the same code
paths as the emg2pose side where the quantity is comparable:

* class occupancy under true DB9 posture data;
* per-class recall (already frozen) and the **predicted**-class occupancy, which is the
  like-for-like counterpart of the emg2pose occupancy;
* the same margin definition;
* the same switch-rate and dwell statistics on DB9's own frame sequences within the frozen
  200-frame segments.

Purpose: identify whether emg2pose GT is obviously operating in a radically different numerical
region of the frozen head. **No new support threshold is created. DB9 quantiles are NOT used as
an `UNKNOWN` gate. Nothing is labelled in-distribution or out-of-distribution.**

---

## 9. Class 4 — explicit

Class 4 is the frozen head's known weak region (DB9 recall 0.4947; most errors → class 5).
Reported separately: fraction of emg2pose GT assigned class 4; class-4 margin distribution;
class-4 ↔ class-5 score separation (difference of their discriminant columns, and the fraction of
samples whose top-2 pair is exactly {4,5}); stage-wise class-4 occupancy. High class-4 occupancy
is **not** interpreted as evidence that natural poses are truly class 4.

---

## 10. Decision rule — declared before any output

Exactly three outcomes, decided on descriptive evidence, with **no invented optimisation
criterion**:

* **`DEGENERATE`** if any of:
  1. one class (or ≤2 classes) takes **> 90 %** of occupancy *and* the same collapse holds in
     every stage and both sides; or
  2. the class-switch rate exceeds **0.5 switches per analysis sample** (i.e. a median dwell
     below 2 analysis samples, ≈40 ms), which is inconsistent with the smoothness of GT pose; or
  3. the top-2 margin is **zero or negative for > 10 %** of samples (pathological ties or
     rank inversions); or
  4. behaviour is dominated by the known weak class-4/5 boundary, defined as **> 50 %** of all
     samples having their top-2 pair = {4,5}.
* **`AMBIGUOUS`** if none of the `DEGENERATE` conditions hold but the structural picture is
  internally inconsistent — specifically if occupancy entropy is **< 1.0 bit**, or the dominant
  class differs between the left and right halves of the corpus, or the stage-wise dominant class
  is identical for **all 15** stages.
* **`STRUCTURED_NONDEGENERATE`** otherwise: sufficiently varied and temporally coherent behaviour
  to justify a separately designed semantic validation step.

These numbers are fixed now. If implementation reveals that the *scientific plan* must change
after seeing output, this gate **stops** and reports rather than adapting.

---

## 11. Firewall assertions (must all hold)

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
GPU_USED                   = NO
FULL_CORPUS_DOWNLOADED     = NO
```

Do not proceed to upstream substitution from this gate regardless of outcome.

---

## 12. Outputs

```
GATE2A_PLAN.md / GATE2A_PLAN.sha256      this plan, hashed before any head output
README.md
artifacts/GT_HEAD_BEHAVIOR.json          full machine-readable diagnostic
artifacts/GT_HEAD_BEHAVIOR_BY_STAGE.csv  per-stage stratification
artifacts/GT_HEAD_BEHAVIOR_BY_SIDE.csv   per-side stratification
artifacts/GATE2A_DECISION.json           decision, evidence, firewall
scripts/run_gate2a_native_gt.py          the run
logs/gate2a_stdout.txt                   captured stdout
```

---

## 13. Reproduce

```powershell
cd common-pose\experiments\upstream_substitution\gate2a_native_gt_diagnostic
C:\emg2pose-venv\Scripts\python.exe -X utf8 scripts\run_gate2a_native_gt.py
```
