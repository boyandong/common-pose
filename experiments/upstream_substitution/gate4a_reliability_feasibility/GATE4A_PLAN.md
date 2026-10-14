# GATE 4A PLAN — SINGLE-USER RELIABILITY-SCORE FEASIBILITY SCREEN

**Evidence status: SINGLE-USER FEASIBILITY SCREEN ONLY.**
**This is NOT a formal gate. This is NOT conformal validation. This is NOT threshold selection.**
**This is NOT a downstream classifier experiment. This is NOT a class-accuracy experiment.**

**Phase:** PHASE 1 / GATE 4A
**Predecessor:** GATE 3B (frozen, unmodified) — `GATE3B_PLAN.md`,
SHA-256 `4aa731b8d7b15f802586e07c34dc198510e0dadc89a13831c09526cacd2cfc77`

---

## 1. The one question this screen answers

> At deployment we do not see GT. Can a **sample-dependent** reliability score `u_t`, computed only
> from deployment-visible information (the EMG stream and the official upstream prediction stream),
> **rank** the true task-relevant representation error `r_t`?

```
deployment:   EMG ──► official emg2pose estimator ──► Pred pose ──► u_t   (GT never used)
research:     r_t = DB9-normalised Fisher displacement between z_PRED and z_GT
     goal:    u_t large  ⟹  r_t large
```

`r_t` is used **only** to (i) fit the exploratory task-error predictor and (ii) evaluate candidate
scores. It is **never** a deployment feature, never enters TTA inference, never selects a perturbation,
and never enters the temporal baseline.

This screen decides only whether a score **has hope**. No final gate is selected.

---

## 2. Explicitly forbidden in this screen

* No human gesture labels. No DB9 class label as a gate target. No hard class agreement as a target.
* No GT pose or Fisher GT as a deployment feature. No `stage` label as a deployment feature.
* No tuning of TTA perturbations against `r_t`. No augmentation search.
* No downstream task retraining. No upstream pose-model retraining. No deep-model training at all.
* No zero/offset fitting; the DB9↔emg2pose numerical-zero question is **not** reopened.
* No DB9 probability-cloud rescue, no Mahalanobis-to-DB9-cloud gate, no OCSVM / GMM / SIMCA gate.
* No test-time adaptation; TTA here means *multi-view inference with frozen weights*, nothing else.
* No smoothing tuned on outcomes. No lag search.
* **No absolute distance-to-DB9-training-cloud as a primary gate.** The primary target is the paired
  relative error `z_PRED − z_GT`; a shared source offset cancels under the linear frozen Fisher
  transform, and that is intentional.
* No threshold selection of any kind: no "optimal threshold = X", no maximisation of Fisher
  preservation, class agreement, F1, coverage, or any weighted objective.
* No finite-sample conformal / calibrated-risk claim: all data come from one participant and one
  session with strong temporal dependence.
* No modification of any Gate3 / Gate3B artifact. No new upstream inference beyond the frozen TTA
  transform set of §4.

**Linearity firewall.** The frozen Fisher transform is linear. A scheme that adds the *same* fixed
residual cloud `E` to every sample gives `A(Pred + e) − A(Pred) = A(e)`, independent of `Pred`, and
therefore carries no sample-specific information. Candidate 1 therefore perturbs the **EMG input**
with a label-preserving input transform; it never adds a fixed residual in Fisher space.

---

## 3. Data — exact reuse of the Gate3 / Gate3B population

| item | value (frozen) |
|---|---|
| population | **86 833** samples |
| rate | 50 Hz (non-overlapping 40-row block mean of the 2 kHz aligned grid) |
| participant / session | `d387095792` / `2022-12-06-1670313600-e3096-cv-emg-pose-train@2` |
| records | 30 (15 left + 15 right) |
| stages | 15, each with exactly one left and one right recording |
| GT source | `/root/data/emg2pose_dataset_mini/*.hdf5`, `emg2pose/timeseries/joint_angles`, trusted-8 `[2,3,5,6,9,13,17,18]` |
| Pred source | `/root/work/gate3_work/pred_pose/*_pred.npz` (frozen Gate3 stream, reused) |
| checkpoint | `/root/models/emg2pose/regression_vemg2pose.ckpt`, sha256 `748b1d1ef0ce1985f6fc07225d97eebfb370243429af803b4997d28ecce2424e` |
| frozen head | `/root/work/gate3_work/frozen_head/frozen_db9_trusted8_lda.joblib`, sha256 `b0ef8caf8e390a480fa2a3b448f79ccf14f75c71265ef925ee299a5e9e660386` |
| alignment | `prediction[i] ↔ GT[1790+i]`, exact timestamp-array equality asserted per record |
| eligibility | GT-valid AND pred-valid full 40-row blocks; first block of each record excluded |
| filtering | **NONE** beyond the frozen Gate3 eligibility rule |

Population reconstruction is the **verbatim** Gate3/Gate3B rule. If the reconstructed count is not
exactly 86 833, or any record's timestamp equality fails, this screen **stops**.

Unknown, not used in this screen: participant age/sex, sensor placement metadata, force, fatigue.

---

## 4. Candidate 1 transform set — frozen BEFORE any outcome is inspected

### 4.1 Official evidence (inspected before freezing)

| item | value |
|---|---|
| file | `/root/work/emg2pose/emg2pose/transforms.py` sha256 `15140d8a493d2e7e56c8bccdb69fd15a3c9add1ce9e233ef7d4bc39a0926e5ab` |
| class | `RotationAugmentation`: *"Rotate EMG along the channel dimension by a random integer."* `rotation = np.random.choice([-1, 0, 1]); torch.roll(data, rotation, dims=-1)` |
| config | `/root/work/emg2pose/config/transforms/rotation_augmentation.yaml` sha256 `9b73508e96459626de3897b0b15eccf106f3b3a736a6fdfd1eef0b99f8a72350`; `train: [ExtractToTensor, RotationAugmentation]`, `val: [ExtractToTensor]`, `test = val` |
| default wiring | `/root/work/emg2pose/config/base.yaml` → `defaults: transforms: rotation_augmentation`; the experiment configs add only `/pose_module` and `/network` |
| upstream repo | `https://github.com/facebookresearch/emg2pose.git` @ `5f6f62b` |
| channel count | 16 electrode channels (`emg2pose/data.py`: *"each EMG device has 16 electrode channels"*) |

Pre-freeze probe (recorded, no GT read, no target computed):
`RotationAugmentation` outputs over 200 draws = `{0, 1, 15}` ≡ shifts `{0, +1, −1}`; every draw equals
`torch.roll(x, k, dims=-1)` for `k ∈ {−1,0,1}` (verified True); repeated inference on identical input is
bitwise identical.

### 4.2 Frozen TTA transform set (K = 3, deterministic)

| view | transform |
|---|---|
| `k=0` | identity — input EMG passed unchanged (this is the frozen Gate3 stream) |
| `k=+1` | `np.roll(emg, +1, axis=1)` — circular electrode-band shift by one channel |
| `k=−1` | `np.roll(emg, −1, axis=1)` |

**Why this is target-preserving.** The transform is the official training-time augmentation of this
exact estimator: the upstream authors define it as label-preserving, and this checkpoint was trained
with it (base-config default). It is a deterministic circular shift of the *electrode* index along a
closed 16-channel arrangement, so it simulates an electrode-array rotation relative to the limb; it
changes no joint angle, needs no GT, and injects no information. The view set is exactly the support
of the official augmentation, so no view lies outside the distribution the model was trained on.
`k ∈ {−2, +2, …}` is **not** used: it is outside the official support.

The frozen Gate3 stream is reproduced by the `k=0` path with **identical inference semantics**
(`PredictPose.predict(emg)` → single pass, same checkpoint, same shapes, eval mode, `torch.no_grad()`).

### 4.3 Pre-declared TTA validity conditions

`TTA_STATUS = EVALUABLE` only if **all** hold:

1. `k=0` reproduces the frozen Gate3 prediction stream **bit-exactly** (`np.array_equal` per record).
2. every shifted view returns only finite values on all eligible samples;
3. finite and bounded perturbation response: for both shifts, median per-frame trusted-8 pose RMSE
   between the view and `k=0` is `< 15°` and `max |Δ| < 90°` on at least 29 of 30 records;
4. the view check is repeated and hashes match (determinism).

Otherwise `TTA_STATUS = NOT_EVALUABLE` with the exact failing condition recorded. No substitute
transform is invented, and no TTA artifact requiring predictions is fabricated.

---

## 5. TARGET — true Fisher error (evaluation / predictor label only)

Recomputed independently from source, then checked **bit-for-bit** against the Gate3B record:

```
x      = (pose − mu_DB9) / sd_DB9                     # trusted-8, DB9 standardisation
z      = lda.transform(x)                             # 7-D frozen Fisher embedding
r_t    = sqrt( sum_j ( (z_PRED,t,j − z_GT,t,j) / sigma_DB9,j )^2 )
```

`sigma_DB9` is the **DB9-only** per-component scale from
`gate3b_continuous_representation/artifacts/FISHER_DB9_REFERENCE_SCALE.json` (77 DB9 participants,
123 200 frames); no emg2pose-derived scaling is used anywhere. Gate3B recorded
median `2.896259`, IQR `1.651728`, p05 `1.283626`, p95 `5.201622`; reproduction must match to
`1e-9` or this screen **stops**.

---

## 6. CANDIDATE 0 — temporal Fisher volatility baseline

Deployment-visible input: `z_PRED,t` only.

```
delta_z_t  = z_PRED,t − z_PRED,t−1          # within a continuous record only
u_TEMP,t   = sqrt( sum_j ( delta_z_t,j / sigma_DB9,j )^2 )
```

The first valid frame of each record has `u_TEMP = NA` and is excluded from all candidate-0
statistics; records are never connected across gaps. This is a **motion proxy, not uncertainty**, and
is included deliberately: if it ranks error as well as the sophisticated candidates, that is
scientifically important and must be reported.

---

## 7. CANDIDATE 1 — TTA Fisher consistency

For each frozen view `k ∈ {0, +1, −1}`, with frozen weights and no adaptation:

```
EMG ──► official estimator ──► Pred_pose^(k) ──► trusted-8 ──► frozen Fisher ──► z_t^(k)
```

Primary score (`K = 3`):

```
zbar_t  = (1/K) * sum_k z_t^(k)
u_TTA,t = sqrt( (1/K) * sum_k sum_j ( ( z_t^(k,j) − zbar_t,j ) / sigma_DB9,j )^2 )
```

Lower = more stable, higher = less stable.

Secondary (reported, **never** substituted): maximum normalized pairwise Fisher distance across the
three views. The primary score remains `u_TTA` regardless of which looks better after the outcome is
seen.

---

## 8. CANDIDATE 2 — simple task-error predictor prototype

### 8.1 Features (deployment-visible only, current-and-past)

| # | name | meaning |
|---|---|---|
| 1–8 | `pose_j` | current predicted trusted-8 pose (radians) |
| 9–15 | `fisher_j` | current predicted 7-D Fisher representation |
| 16–23 | `dpose_j` | first difference of `pose` within record |
| 24–30 | `dfisher_j` | first difference of `fisher` within record |
| 31–38 | `d2pose_j` | second difference of `pose` within record |
| 39–45 | `d2fisher_j` | second difference of `fisher` within record |
| 46 | `side_right` | 1 for right hand, 0 for left — deployment-visible metadata |
| 47 | `d1_valid` | 1 if the first difference is defined at this frame |
| 48 | `d2_valid` | 1 if the second difference is defined at this frame |

`dpose`/`dfisher` at the first valid frame of a record, and `d2*` on the first two valid frames, are
**defined as 0** and flagged by `d1_valid` / `d2_valid`. No centred or forward window is used, so no
future frame can enter any feature.

**Explicitly excluded:** GT pose, GT Fisher, `r_t`, stage, DB9 class label, hard-agreement, any
GT-derived quantity, any future frame.

### 8.2 Fixed model (no tuning)

`sklearn.ensemble.GradientBoostingRegressor(loss="quantile", alpha=0.90, n_estimators=100,
learning_rate=0.1, max_depth=3, subsample=1.0, criterion="friedman_mse", min_samples_split=2,
min_samples_leaf=1, max_features=None, random_state=0, n_jobs=1)` — i.e. **all remaining
hyperparameters at library defaults**. `random_state=0` is fixed for reproducibility only (sklearn
1.5.2 defaults it to `None`); changing it is not permitted. No hyperparameter is selected from the
folds. The output `u_ERR,t` is an estimated upper-risk score: lower = safer.

### 8.3 Grouped out-of-fold evaluation

`stage` is a **grouping variable only**, never an input feature.

`sklearn.model_selection.GroupKFold(n_splits=5)` on `groups = stage`, so every sample of a stage lands
in exactly one fold and **both hands of a stage stay in the same fold**. Plain `GroupKFold` is used
(no `shuffle`) because the installed sklearn 1.5.2 `GroupKFold` accepts only `n_splits`; the
assignment is therefore deterministic by construction, and the realised fold→stage map is written to
the artifact. Each fold trains on the held-out stage groups of the other folds only. Every eligible
sample receives exactly one out-of-fold `u_ERR`; a score from a model that saw the sample's own stage
is a hard failure.

---

## 9. Candidate evaluation metrics

For every candidate score `u ∈ {u_TEMP, u_TTA, u_ERR}` (lower = safer), against `r_t`:

1. **Primary:** Spearman ρ(u, r) and Kendall τ(u, r) on the pooled eligible set. No frame-level
   p-values.
2. **Group consistency (per record).** For each of the 30 records: `n`, Spearman ρ; then median,
   IQR, min, max, and the fraction of records with ρ > 0. Also summarised descriptively by hand side.
   This is weighted more heavily than any pooled statistic.
3. **Risk–coverage.** Rank ascending by `u`; accept the lowest-risk subset at fixed coverage
   `{100 %, 90 %, 75 %, 50 %, 25 %}`. Report mean, median and p90 of `r_t` among accepted samples.
   Coverage points are frozen here and are never optimised. No class accuracy is reported.
4. **AURC.** Coverage grid `0.10 → 1.00` step `0.01` (91 points, exactly the included points, no
   interpolation); risk = mean `r_t` among accepted. Lower AURC = better ranking.
5. **Monotonicity.** 10 equal-count deciles by ascending `u`; per decile report median `u`, median
   `r_t`, mean `r_t`, p90 `r_t`. Approximate monotonicity is expected; perfect monotonicity is not
   required.

### 9.1 References

* **NO-GATE:** 100 % coverage, risk = pooled mean `r_t`. This also serves as the random-ranking
  expectation reference.
* **ORACLE:** identical risk–coverage and AURC computation with the ordering taken from `r_t` itself.
  Impossible at deployment; a ceiling reference only, never described as a candidate gate.

### 9.2 Pre-declared exploratory feasibility bands

Computed **after** freezing, applied mechanically from the pooled Spearman ρ (`rho`), the per-record
consistency, and AURC:

| band | rule |
|---|---|
| `MOST_PROMISING_FOR_MULTIUSER` | ρ ≥ 0.50, median per-record ρ ≥ 0.40, fraction of records with ρ > 0 ≥ 0.9, AURC < no-gate AURC |
| `PROMISING` | ρ ≥ 0.30, median per-record ρ ≥ 0.20, fraction of records with ρ > 0 ≥ 0.8, AURC < no-gate AURC |
| `WEAK` | ρ ≥ 0.10 and fraction of records with ρ > 0 ≥ 0.6 |
| `NO_VISIBLE_SIGNAL` | otherwise |

These bands are **description labels for a single-user screen**, not thresholds, not a gate, and not a
scientific superiority claim. Every candidate is labelled.

---

## 10. No formal conformal, no threshold, no winner

No finite-sample coverage guarantee is attached to anything here. One participant and one session
with strong temporal and within-subject dependence cannot support calibration. Future formal design
uses development users → calibration users → held-out test users, then conformal calibration / LTT /
CRC (reserved for that stage). **No final threshold is selected and no final gate is chosen.**

---

## 11. Deferred candidates (documented, NOT executed)

* **Deep Ensemble → Fisher uncertainty** — needs ≥ 3 independently trained upstream models
  (GPU-days, new training); better placed in the multi-user stage where between-user variance is the
  quantity of interest; conditional on this screen showing that model-instability signals carry
  information at all.
* **Multivariate conformal uncertainty region → Fisher uncertainty** — needs a genuinely multivariate
  predictor with calibrated per-sample regions and enough exchangeable units; one session cannot
  supply them; conditional on a defensible uncertainty source being identified here.
* **LTT / Conformal Risk Control** — reserved for **threshold calibration** in the multi-user stage;
  not a score generator and not run here.

---

## 12. Firewall assertions (must all hold)

```
NEW_UPSTREAM_TRAINING_RUN   = NO       UPSTREAM_MODEL_RETRAINED  = NO
DOWNSTREAM_TASK_RETRAINED   = NO       DEEP_MODEL_TRAINED        = NO
CALIBRATION_FITTED          = NO       THRESHOLD_SELECTED        = NO
HUMAN_LABELS_USED           = NO       DB9_CLASS_TARGET_USED     = NO
ABSOLUTE_DB9_SUPPORT_GATE   = NO       OCSVM_GMM_SIMCA_RESCUE    = NO
ZERO_OFFSET_FITTED          = NO       LAG_SEARCH_PERFORMED      = NO
SMOOTHING_TUNED_ON_OUTCOME  = NO       TEST_TIME_ADAPTATION      = NO
TTA_PERTURBATION_TUNED_ON_TARGET = NO  AUGMENTATION_SEARCH       = NO
GT_AS_DEPLOYMENT_FEATURE    = NO       R_T_AS_DEPLOYMENT_FEATURE = NO
STAGE_AS_DEPLOYMENT_FEATURE = NO       FUTURE_FRAME_FEATURE      = NO
CONFORMAL_GUARANTEE_CLAIMED = NO       POPULATION_CHANGED        = NO
GATE3_ARTIFACTS_MODIFIED    = NO       GATE3B_ARTIFACTS_MODIFIED = NO
SCALING_FROM_EMG2POSE       = NO
```

`MODEL_FITTING_PERFORMED = YES` refers **only** to the Candidate-2 exploratory
`GradientBoostingRegressor` (stage-grouped OOF) and to nothing else. No deep network is trained or
retrained anywhere in this screen.

---

## 13. Outputs

```
GATE4A_PLAN.md / GATE4A_PLAN.sha256 / README.md
scripts/io_common.py
scripts/audit_tta_transforms.py      logs/tta_transform_audit_stdout.txt
scripts/run_tta_inference.py         logs/tta_inference_stdout.txt
scripts/run_task_error_predictor.py  logs/task_error_predictor_stdout.txt
scripts/build_reliability_scores.py  logs/gate4a_stdout.txt
scripts/evaluate_gate_scores.py
scripts/verify_gate4a.py             logs/gate4a_verify_stdout.txt

artifacts/GATE4A_DATA_LINK.json
artifacts/TRUE_FISHER_ERROR_TARGET.json
artifacts/TEMPORAL_BASELINE_SUMMARY.json
artifacts/TTA_TRANSFORM_AUDIT.json
artifacts/TTA_SCORE_SUMMARY.json
artifacts/TASK_ERROR_PREDICTOR_SPEC.json
artifacts/TASK_ERROR_PREDICTOR_OOF.csv
artifacts/TASK_ERROR_PREDICTOR_SUMMARY.json
artifacts/CANDIDATE_CORRELATIONS.csv
artifacts/CANDIDATE_BY_RECORD.csv
artifacts/CANDIDATE_RISK_COVERAGE.csv
artifacts/CANDIDATE_AURC.csv
artifacts/CANDIDATE_DECILES.csv
artifacts/DEFERRED_GATE_CANDIDATES.md
artifacts/GATE4A_DECISION.json

work/population_index.csv
work/tta_fisher_views.npz
```

`work/` holds the score-level intermediates needed for independent verification; it is derived data,
not part of the claim surface. No Gate3 / Gate3B artifact is written to.

---

## 14. Reproduce

```bash
/root/miniconda3/envs/emg2pose-gate3/bin/python -X utf8 scripts/audit_tta_transforms.py
/root/miniconda3/envs/emg2pose-gate3/bin/python -X utf8 scripts/run_tta_inference.py
/root/miniconda3/envs/emg2pose-gate3/bin/python -X utf8 scripts/run_task_error_predictor.py
/root/miniconda3/envs/emg2pose-gate3/bin/python -X utf8 scripts/build_reliability_scores.py
/root/miniconda3/envs/emg2pose-gate3/bin/python -X utf8 scripts/evaluate_gate_scores.py
/root/miniconda3/envs/emg2pose-gate3/bin/python -X utf8 scripts/verify_gate4a.py
```

## 15. Claim boundary

**May support:** "on one participant/session, a deployment-visible score of type X shows (no) useful
ranking information about true task-relevant Fisher representation error."

**Cannot establish:** cross-user reliability, calibration, a conformal guarantee, a deployment-ready
threshold, a population-level effect, or scientific superiority of any gate. Class-based endpoints and
absolute DB9 support are outside this screen entirely.
