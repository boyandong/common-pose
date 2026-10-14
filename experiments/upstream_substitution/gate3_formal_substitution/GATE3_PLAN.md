# GATE 3 PLAN — FORMAL UPSTREAM SUBSTITUTION BASELINE

**Status: FROZEN. Write this file, hash it, and only then compute any Y_GT vs Y_PRED comparison.**
**Gate class: FORMAL QUANTITATIVE BASELINE.** Not a semantic-accuracy evaluation, not a transfer-accuracy
claim, not an open-set/reliability gate, not a Common Pose universal-validity confirmation.

**Phase:** PHASE 1 / GATE 3
**Frozen representation:** `TRUSTED_DB9_POSE_v1`
**Frozen subset SHA-256:** `e51dde6e63941fd080c84f3896a98cf50fba9e17d5f9cebe909253d5465782d1`
**Frozen DB9 baseline record:** `audits/db9/channel_forensic/artifacts/FINAL_VALIDATION.json`
`.Q4_posture8` (77 participants, classes 1–8, BA ≈ 0.747914, Macro-F1 ≈ 0.745980)
**Predecessor:** GATE 2A → `STRUCTURED_NONDEGENERATE` (native emg2pose GT does not grossly collapse the
frozen head on this corpus).

---

## 1. The one question this gate answers

> When emg2pose ground-truth pose is replaced by pose predicted from the **same EMG** by the independent
> **official** emg2pose estimator, how much of the frozen downstream DB9-head behaviour is preserved,
> without any task-specific downstream retraining?

`Y_GT` is the **REFERENCE BEHAVIOR**, not semantic ground truth. This gate measures **functional
preservation**, not semantic correctness.

---

## 2. Frozen objects and provenance

| object | frozen value | provenance |
|---|---|---|
| Downstream head | `LinearDiscriminantAnalysis()` all defaults, trained on **all 77** DB9 participants | identical reconstruction; no serialized head existed before (Gate2A §2) |
| Head features | `TRUSTED_DB9_POSE_v1`, DB9 columns `[2,3,4,6,7,9,13,15]` | frozen subset |
| Head task | NinaPro DB9 Exercise-B, movement ids **1–8 only** | `FINAL_VALIDATION.json .Q4_posture8` |
| Head protocol | `restimulus × rerepetition`; central 60 %; cap 200 via `np.linspace`; `np.deg2rad`; DB9 training-set z-score (`sd>0` guard) | Gate2A §2 |
| Upstream estimator | official **`regression_vemg2pose`** (EMG-only regression) | `emg2pose` official repo, `config/experiment/regression_vemg2pose.yaml` |
| Checkpoint | `regression_vemg2pose.ckpt`, SHA-256 `748b1d1ef0ce1985f6fc07225d97eebfb370243429af803b4997d28ecce2424e` | matches the hash already recorded in `common-pose/docs/joint_angle_definition.md` |
| Official repo commit | `5f6f62b1a0a08426adffe55900842e75a8adb38c` (`facebookresearch/emg2pose`) | recorded at transfer |
| Trusted-8 emg2pose indices | `[2, 3, 5, 6, 9, 13, 17, 18]` | `docs/DB9_CANONICAL16_MAPPING.md`; mapping CLOSED — not re-derived here |

**Why `regression_vemg2pose`.** It is the project's already-established estimator: it is the model
executed by `experiments/bridge/run_bridge_audit.py`, it is the default of
`src/common_pose/estimators/emg2pose/predict_pose.py`, its checkpoint hash is already published in the
project's own docs, and it is the only official experiment config that is **pure EMG → pose** with no
ground-truth initial pose. The choice is made **on documented provenance, before any output**, and is
**not** informed by downstream preservation. No other checkpoint is evaluated.

**Head reproduction gate.** Before the head may be used it must reproduce the frozen record exactly.
`build_frozen_head.py` re-runs the frozen LOSO evaluation and reports the scalar quantities
(`n_frames`, `n_subjects`, `accuracy`, `balanced_accuracy`, `macro_f1`) plus all 8 per-class recalls.
If any quantity mismatches, this gate **stops**. The aggregate head is serialized to
`models/frozen_db9_trusted8_lda.joblib` and its SHA-256 recorded.

---

## 3. Cohort — frozen, not expanded

The **exact** corpus already used by Gate 1.5 / Gate 2A, verified by identity before use:

* `data/official/emg2pose_dataset_mini/*.hdf5`, **30** recordings;
* **1 participant** (`d387095792`), **1 session** (`2022-12-06-1670313600-e3096-cv-emg-pose-train@2`);
* **15 stages**, **15 left + 15 right**;
* **4 218 756** stored rows; all `split = val`, `held_out_user = True`;
* Gate2A recorded `gt_valid_rows = 3 559 584`, `ik_failure_rows = 659 172`, `analysis_samples = 88 019`
  at 50 Hz.

**This is a SINGLE-USER PROOF OF CONCEPT.** No cohort expansion, no additional participant, no
cross-user claim. Cross-user confirmation is a later phase.

---

## 4. Temporal alignment — established from official semantics, never searched

The official `emg2pose/pose_modules.py :: BasePoseModule.forward` defines:

* `left_context = 1790` samples (≈ 895 ms at 2 kHz) are consumed as left context;
* `right_context = 0` for this architecture;
* predictions span `EMG[left_context : T − right_context]`;
* predictions are produced at `rollout_freq = 50 Hz` and upsampled by
  `interpolate(pred, n_time, mode="linear")` to `n_time = T − left_context`, i.e. **onto the 2 kHz input grid**;
* the GT `joint_angles` field is stored on that **same 2 kHz grid**.

**Alignment rule (deterministic, official):**

```
prediction[i]  ↔  GT[row_offset + i],   row_offset = left_context = 1790
```

verified **per record** by `np.array_equal(GT.time[row_offset:], prediction.time)`.

**Forbidden and not performed:** cross-correlation search, any lag optimisation, any shift chosen to
maximise `Y_GT`↔`Y_PRED` agreement, any alignment decision that depends on downstream output. The
`start`/`end` attrs are metadata only and are not used to build the alignment.

If exact timestamp equality failed for any record, this gate **stops**.

---

## 5. Validity, sampling policy and analysis population — frozen

**Row validity (2 kHz).**

* GT row: **not** all-20-dimensions-≈-zero (`np.isclose(x, 0)`, official `get_ik_failures_mask`
  semantics) **and** all values finite. All-zero GT rows are IK-invalid and are **never** read as an
  extended hand.
* Prediction row: **not** all-20-dimensions-≈-zero **and** all values finite. The estimator has no IK
  failures of its own; this rule is applied for symmetry and is reported explicitly.

**50 Hz analysis reduction — the frozen Gate2A policy, reused unchanged.**

* `n_blocks = n // 40`; the trailing `< 40` remainder is dropped;
* each non-overlapping 40-row (20 ms) block → **one** analysis sample = block **mean** of the 8 trusted
  values;
* a block is valid for a route only if **all 40** of its rows are valid for that route (no mixing across
  a gap);
* analysis rate = **50 Hz**. The 40× reduction is stated explicitly so the sample count is never
  overstated. 2 kHz interpolated pose rows are **not** counted as independent observations; the
  prediction is **not** upsampled to manufacture samples.

**Primary analysis population** = blocks valid in **both** routes, both sides, all 15 stages.

**Lead-block exclusion (declared now, before any output).** The **first block of every record** is
excluded from the primary population. Reason: the official rollout is initialised from a zero initial
pose (`provide_initial_pos = False`) at exactly `t = left_context`, so the first 20 ms of each
prediction stream is the decoder's initialisation transient and is not comparable to a settled
prediction. This rule is fixed by the published model semantics, is applied identically to both routes,
and does not depend on any outcome.

**Also reported, for accounting only:** GT-valid row count, prediction-valid row count, GT-valid-block
count, prediction-valid-block count, and the eligible-block count. No sample is ever removed on the
basis of downstream output.

---

## 6. Routes

```
ROUTE A — ORACLE
emg2pose GT 20-D pose → trusted-8 [2,3,5,6,9,13,17,18] → DB9 frozen z-score → frozen DB9 LDA → Y_GT

ROUTE B — SUBSTITUTED
emg2pose EMG (16 ch, 2 kHz) → official regression_vemg2pose estimator → predicted 20-D pose
   → same trusted-8 → same DB9 frozen z-score → same frozen DB9 LDA → Y_PRED
```

Both routes use the **same frozen head object** and the **same DB9-derived standardisation**. No
standardisation statistics are computed from emg2pose.

---

## 7. Forbidden in this gate

* **No gate of any kind.** No probability cloud, Mahalanobis threshold, OCSVM, GMM, conformal
  rejection, perturbation gate, uncertainty threshold, `UNKNOWN` class, abstention or rejection.
  **Every eligible sample enters both routes.** The reliability gate is a later, separately designed
  experiment.
* No human labels of any kind: no gesture annotations, no hand-coded postures, no DB9 semantic labels
  for emg2pose, no visual posture grading.
* No calibration fitting: no offset, scale, affine, percentile alignment, distribution matching,
  per-stage calibration, Procrustes or regression.
* No training or fine-tuning of the upstream estimator; no task-specific or test-time adaptation; no
  context-window change.
* No smoothing, filtering or resampling chosen after seeing any downstream result.
* No checkpoint selection, threshold selection, sample selection or subsetting based on downstream
  performance.
* No optimisation of the frozen DB9 head (no LDA tuning, no SVM, no neural replacement, no class-4
  rescue).
* No semantic accuracy claim. The words *gesture accuracy*, *posture accuracy*, *transfer accuracy* and
  *cross-dataset classification accuracy* are forbidden. Permitted wording: *downstream agreement*,
  *balanced preservation*, *functional preservation*, *behaviour preservation under upstream
  substitution*.
* **The historical ≈0.7646 GT-vs-PRED agreement is inaccessible for design.** It is not used for
  thresholds, pass/fail, alignment, checkpoint selection, smoothing, sample selection, or expectation
  setting. It may be mentioned only after the current Gate3 results are frozen, and only as a
  non-comparable prior-stage reference from a different pipeline.

---

## 8. Primary outcomes

**8.1 Hard downstream agreement** — `AGREEMENT = mean(Y_PRED == Y_GT)`, overall, with the disagreement
count reported.

**8.2 Balanced preservation** — for each reference class `c`,
`Preservation_c = P(Y_PRED = c | Y_GT = c)`; then
`BALANCED_PRESERVATION = mean over classes with sufficient observed Y_GT support`.
A class is **sufficient** when its Y_GT support is **≥ 30** analysis samples. This floor is fixed now
and is independent of outcome. All 8 class-conditioned values are reported with their support;
classes below the floor are reported explicitly and are **not** silently dropped, and they are excluded
only from the balanced average.

**8.3 Cohen's κ(Y_GT, Y_PRED)** — unweighted, computed from the 8×8 count matrix.

**8.4 DOWNSTREAM PRESERVATION MATRIX** — 8×8, rows `Y_GT`, columns `Y_PRED`, reported as raw counts and
row-normalised. It is **not** a semantic confusion matrix and is never called one.

---

## 9. Soft-output preservation

The **same** frozen LDA object is used for both routes; `predict_proba` is the native sklearn LDA
posterior on the frozen head. No probability calibration is fitted, and the frozen head is not altered.

* per-sample total variation `TV = 0.5 · Σ_k |P_GT,k − P_PRED,k|` → median, IQR, p05, p95;
* Jensen–Shannon divergence (base 2) → median, IQR, p05, p95;
* reference-class probability preservation: the distribution of `P_PRED[Y_GT]`.

---

## 10. Temporal preservation

Per-route, over each record's contiguous valid block sequence: switch rate (switches per analysis
sample, i.e. per 20 ms), median dwell in frames and seconds, plus p25/p75 dwell.

**Transition-event preservation** uses a tolerance of **±1 analysis frame = ±20 ms**, declared here from
the 50 Hz grid and not optimised from outcomes. For each `Y_GT` transition (destination frame, from-class,
to-class) we ask whether `Y_PRED` shows a transition to the **same destination class** at any frame
within ±1 of the destination frame. Reported: event count, same-destination-within-tolerance count and
fraction, and same-destination-at-exact-frame count and fraction.

---

## 11. Pose-level error

`err = degrees(predicted trusted-8 − GT trusted-8)`, on the frozen analysis population. Reported
overall as trusted-8 RMSE and MAE, per frame (RMSE) and per DOF: **MAE, median absolute error, RMSE,
p90 absolute error, p95 absolute error**, plus mean signed bias. Units: **degrees**. These errors are
never used to optimise anything downstream.

---

## 12. Error → functional failure relationship

Downstream failure `D_t = 1` iff `Y_PRED,t ≠ Y_GT,t`. Per-frame pose error is the trusted-8 RMSE in
degrees.

**Binning is declared now:** `N_DECILES = 10` equal-count deciles of the per-frame pose-error
distribution of the eligible population, formed by a stable ascending sort. For each decile: `n`, median
and mean pose error, disagreement count and disagreement rate. This yields the
**error → functional preservation curve**.

Per-DOF descriptive association with `D_t`: median absolute error conditioned on `D_t = 1` vs `D_t = 0`,
and Spearman rank correlation between that DOF's absolute error and `D_t`.

**Inferential caveat, declared now:** the data are temporally correlated and come from **one**
participant. Frame-level p-values are **not** presented and **no** population-level significance is
claimed. Spearman values are **descriptive** and are labelled as such. Effect sizes are reported, not
significance tests.

---

## 13. Stratifications (descriptive only)

**Class-conditional** — per `Y_GT` class 1–8: support, support fraction, preservation, error count,
main error destination with count and fraction-of-errors, median per-frame pose error, median TV,
median JS, median `P_PRED[Y_GT]`. Classes 4 and 5 are explicitly visible (class 4 is the known weak
DB9 region) but receive **no** special rescue treatment.

**Hand side** — LEFT and RIGHT separately: `n`, file count, agreement, balanced preservation, κ,
median TV, pose MAE and RMSE, per-route switch rate, per-class preservation and support. No separate
transform and no separate threshold is fitted per side.

**Stage** — per activity stage: `n`, sides, agreement, balanced preservation, pose MAE, dominant `Y_GT`
class and fraction, dominant `Y_PRED` class and fraction, median TV.
**Stage names are activity labels and are NOT posture ground truth.** No stage is ever interpreted as a
posture label.

---

## 14. Decision rule — declared before any output

This gate has **NO binary success threshold** and **NO categorical verdict**, because no such threshold
existed before this experiment. In particular, no rule of the form "agreement > X means PASS" is
invented here. `GATE3_DECISION.json` therefore records the **observed quantitative preservation
profile** and states explicitly that no categorical label was emitted, together with the firewall flags
and the historical-reference status.

The result is the **preservation profile**: agreement, balanced preservation, κ, the preservation matrix,
soft-output divergences, temporal preservation, pose error, and the error→failure curve, each with its
stratifications.

Any finding of weak preservation is a **scientific outcome**, not an implementation failure, and is
**not** to be rescued by tuning, calibration, smoothing, gating or model substitution. Weak preservation
is to be interpreted through the pose-error analysis as one of: upstream estimator bottleneck (large pose
error + flips), downstream boundary fragility (small pose error + frequent flips), representation/task
sensitivity (specific DOFs dominate), or temporal mismatch (alignment/estimator temporal behaviour).

---

## 15. Firewall assertions (must all hold)

```
GATE_CREATED                     = NO
UNKNOWN_CLASS                    = NO
ABSTENTION                       = NO
REJECTION                        = NO
HUMAN_LABELS_USED                = NO
CALIBRATION_FITTED               = NO
TASK_SPECIFIC_RETRAINING         = NO
UPSTREAM_RETRAINING              = NO
SMOOTHING_APPLIED                = NO
CHECKPOINT_SELECTED_ON_DOWNSTREAM_PERFORMANCE = NO
ALIGNMENT_OPTIMIZED_ON_OUTCOME   = NO
SAMPLE_SELECTION_ON_DOWNSTREAM_OUTPUT = NO
SEMANTIC_ACCURACY_CLAIMED        = NO
HISTORICAL_0.7646_USED_FOR_DESIGN = NO
FULL_CORPUS_DOWNLOADED           = NO
```

---

## 16. What this gate will and will not support

**Will support (if preservation is strong):** the frozen downstream function is robust to replacement of
oracle GT pose by the independently estimated pose stream **on this single-user corpus**.

**Will not support:** semantic gesture accuracy; universal Common Pose validity; cross-user
generalization; universal numerical coordinate equivalence; any claim about the reliability of
individual predictions.

**Standing limitation:** cross-source numerical zero/calibration equivalence is **NOT** established
(Gate 1.5 → `NO_INDEPENDENT_ANCHOR`, `ZERO_GATE = NOT_EVALUABLE_LOCALLY`). This does not block this gate
because both routes live inside the **same** emg2pose coordinate system and any common DB9↔emg2pose
coordinate shift affects both routes identically. The claim is functional preservation, not semantic
accuracy, and no calibration is fitted to close the gap.

---

## 17. Outputs

```
GATE3_PLAN.md / GATE3_PLAN.sha256
README.md
artifacts/GATE3_DATA_MANIFEST.json
artifacts/GATE3_ALIGNMENT_AUDIT.json
artifacts/GATE3_POSE_ERROR.json
artifacts/GATE3_PRESERVATION_SUMMARY.json
artifacts/GATE3_PRESERVATION_MATRIX.csv            (row-normalised)
artifacts/GATE3_PRESERVATION_MATRIX_COUNTS.csv     (raw counts)
artifacts/GATE3_PRESERVATION_BY_CLASS.csv
artifacts/GATE3_PRESERVATION_BY_SIDE.csv
artifacts/GATE3_PRESERVATION_BY_STAGE.csv
artifacts/GATE3_ERROR_PRESERVATION_CURVE.csv
artifacts/GATE3_DECISION.json
scripts/run_gate3_substitution.py
scripts/verify_gate3.py
logs/gate3_stdout.txt
logs/inference_stdout.txt
models/frozen_db9_trusted8_lda.joblib + SHA-256
```

## 18. Reproduce

```bash
# server
/root/miniconda3/envs/emg2pose-gate3/bin/python -X utf8 run_emg2pose_inference.py
/root/miniconda3/envs/emg2pose-gate3/bin/python -X utf8 run_gate3_substitution.py
/root/miniconda3/envs/emg2pose-gate3/bin/python -X utf8 verify_gate3.py
```

## 19. Next phase — NOT executed here

If Gate3 produces interpretable preservation results, the next phase is **RELIABILITY / ABSTENTION GATE
DESIGN**: the coverage ↔ functional-preservation tradeoff without human labels. Gate3 must be reviewed
first. Nothing in this plan authorises executing that phase.
