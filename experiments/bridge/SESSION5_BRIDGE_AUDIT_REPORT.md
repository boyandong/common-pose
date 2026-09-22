# SESSION 5 — CROSS-DATASET BRIDGE AUDIT

**emg2pose → canonical16 → frozen DB9 posture decoder**

**Lane:** Session 5 (new hypothesis branch). Sessions 1–4 untouched.
**Date:** 2026-09-18 · **Status:** audit complete; **documentation-corrected after
independent audit; S5 CLOSED / FROZEN** (see §23).
**Run:** `bridge_audit/run_bridge_audit.py`, exit 0, 737.8 s wall, single process, CPU only.
**Independent audit:** `_audit_s5/S5_INDEPENDENT_AUDIT_REPORT.md` — 42/42 headline
claims reproduced at the reported precision; two interpretation-level errors found and
corrected in §23 without changing any number.

---

## 0. The question, and what it is not

> Does wrist-EMG pose estimation preserve the frozen posture-relevant kinematic
> geometry well enough that a DB9-trained decoder behaves consistently with an
> oracle-GT-pose decoder?

**It is not** gesture recognition, posture accuracy, or a Session-3 re-analysis.
emg2pose carries no frame-level ground-truth labels for the six DB9 postures, and
emg2pose `stage` was **never** used as posture truth anywhere in this audit. The
GT-pose decoder output is an **ORACLE-POSE REFERENCE**, not ground truth.

### Final conclusion (the seven statements S5 stands on)

1. The frozen Session-3 decoder was **reconstructed exactly** (1548/1548 identical
   decisions, scaler diff 0.0).
2. VEMG2Pose prediction error is **substantial in canonical angle space** (~19.7° MAE).
3. Despite this, GT-pose and predicted-pose decoder decisions **agree ~76.5 %** of the
   time — a self-consistency statistic, not an accuracy.
4. The overall emg2pose mini **natural-pose distribution is largely outside the
   deliberately narrow support** of the six DB9 posture classes (77.04 % beyond a
   DB9-only p95 threshold).
5. This is **NOT evidence of coordinate incompatibility** — the audit found positive
   evidence of *partial* coordinate compatibility (§16b).
6. Prediction error contributes additional downstream instability, but current evidence
   points more strongly to **error magnitude relative to decision margin** than to a
   uniquely harmful error direction.
7. **Semantic posture accuracy cannot be established** without an independent semantic
   posture ground truth.

**Headline:** the evidence supports **CASE C in its narrow, distributional sense**,
with a measurable secondary contribution from the pose estimator. See §16.

---

## 1. Exact artifacts and code reused from S2 and S3

| Purpose | Artifact | Reuse |
|---|---|---|
| 20D → canonical16 | `representation/canonical_hand.py` + `canonical16_schema.json` (S2, FROZEN) | imported, never re-derived |
| EMG → 20D pose | `inference/predict_pose.py` (S2) + `checkpoints/emg2pose_model_checkpoints/regression_vemg2pose.ckpt` | imported; **inference only** |
| DB9 → canonical16 | `representation/db9_to_canonical16.py` (S3, FROZEN) — used for the representation index subsets only | imported |
| Frozen posture data | `data/db9_posture16/representative_postures_77.npz` (7854 × 16, S3) | consumed verbatim |
| Cohort partition | `docs/CONFIRMATORY_COHORTS.json` (34 / 43) | loaded, never hard-coded |
| Frozen spec | `docs/FROZEN_CONFIRMATORY_SPEC.json` | read |
| Frozen Tier-A result | `data/db9_posture16/full_db9_results.json::primary_confirmatory` | **read-only handshake target** |
| Frozen policy | `posture_decoder/experiments/confirmatory_policy.py` (PRIMARY_MODEL / config / normalisation) | imported |
| Class vocabulary / names | `posture_decoder/db9/labels.py` | imported |
| Visualiser FK | `hand_visualizer/tools/hand_kinematics_np.py` (S4) | imported read-only (PHASE 9) |

No S1–S4 file was modified. `baseline/emg2pose` HEAD = `5f6f62b1a0a08426adffe55900842e75a8adb38c`, **clean**. All Session-5 output is written under `bridge_audit/`.

---

## 2. Exact downstream decoder reconstruction (PHASE 1)

| field | value |
|---|---|
| representation | `canonical16` (frozen S2 adapter) |
| classes | `(1, 2, 3, 4, 6, 7)` |
| model | `LinearDiscriminantAnalysis(solver='lsqr', shrinkage='auto')` |
| normalisation | `StandardScaler` fitted on **train samples only** |
| train subjects | the **34 `development_exposed`** subjects, loaded from `CONFIRMATORY_COHORTS.json` |
| train samples | 1224 (= the frozen run's `n_train_samples`) |
| test subjects | 43 `outcome_unseen` — **used only as the handshake target, never for refitting** |
| tuning | none. No hyperparameter, no threshold, no emg2pose data. |

### Exactness handshake — `bridge_audit/results/bridge_audit_results.json::phase1_decoder_reconstruction.handshake_vs_frozen_tier_A`

| check | result |
|---|---|
| test-subject order matches the frozen run | **True** |
| scaler mean max abs diff | **0.0** |
| scaler scale max abs diff | **0.0** |
| decisions identical to the frozen run | **1548 / 1548** |
| max abs probability difference | **5.1e-15** |
| accuracy | 0.9780361757105943 vs frozen 0.9780361757105943 |
| **PASS** | **True** (hard abort if false) |

Serialised for deployment: scaler `mean_`/`scale_`/`var_`, `lda.coef_`, `lda.intercept_`, `classes_`, class order, training-subject IDs, and SHA-256 of every source artifact (`results/bridge_audit_results.json::provenance.artifact_hashes_sha256`).

> This refit exists so the bridge can call the decision function on new data. It is **not** new Session-3 evidence and no Session-3 claim is re-made.

---

## 3. emg2pose sessions included (PHASE 2)

**All 30 files of the official mini corpus** (`data/official/emg2pose_dataset_mini/`), the complete set:

* one user (`d387095792` / session tag `e3096`), 15 stages × 2 sides (15 left, 15 right);
* 4,218,756 EMG samples at 2 kHz (≈35.2 min per side);
* metadata join: 30/30 rows matched; every row `split='val'`, `held_out_user=True`; **0 rows for this user in any `train` split** (the join key needed the `.hdf5` suffix stripped — the first attempt silently matched 0 rows and that is recorded in the artifact);
* per-session inference 2.7–3.4× realtime on CPU; `left_context=1790`, `right_context=0`, `provide_initial_pos=False`.

**Limitation, stated plainly:** the mini corpus is a **single subject**. Everything below is a within-subject bridge audit. Side and stage variability here are **not** cross-subject evidence. The released checkpoint predates the public dataset release, so `held_out_user=True` is the strongest available evidence about model exposure to this user, not an absolute guarantee.

---

## 4. Paired valid samples and effective sampling rate (PHASE 3)

| quantity | value |
|---|---|
| sessions | **30** |
| 2 kHz EMG samples | 4,218,756 |
| returned pose samples (2 kHz) | 4,165,056 |
| **native-cadence (50 Hz) samples** | **104,112** |
| discarded (incomplete final 20 ms block) | 576 total (0.014 %) |
| GT IK-failures at 2 kHz | 14.8 % (per session 0 – 47.5 %) |
| **GT-valid paired samples at 50 Hz** | **86,858** |
| of those, also prediction-valid | **86,858** (0 all-zero and 0 non-finite predictions) |
| effective pose rate | **50.0 Hz** (derived 2000/40; timestamp-derived 50.0, min = max = 50.0) |

**Sanity of the 20 ms reduction.** Mean absolute within-block GT motion is **0.357°**
(median; per-session 0.158 – 1.268°), i.e. one 20 ms block contains roughly 2 % of
one DOF's typical error. Block-averaging therefore cannot be hiding material motion.

**How the 50 Hz reduction is done.** Each non-overlapping 20 ms block of the 2 kHz series is reduced to **one** value by averaging, applied identically to GT and to the prediction. A block is GT-valid only if **all 40** of its samples are. This is symmetric, phase-robust and cannot manufacture independent samples.

**Honest limitation, recorded in the artifact.** The interpolation fencepost phase inside each 40-sample block could **not** be pinned: the interpolation runs in float32, so a node's `|second difference|` is dominated by rounding (~1.5e-8 median) and does not collapse to zero. The measurement cannot distinguish stride phases, and the artifact says so rather than asserting a phase it does not have. This is why block means are used instead of a stride. Cross-check: the full-2 kHz canonical12 MAE (median over sessions 17.88°) agrees with the 50 Hz value (17.79° median, 19.39° pooled), so the reduction is not distorting the result.

**Aggregation unit: SESSION.** Frame-level numbers are secondary everywhere.

**Alignment sanity (frozen Session-2 offset, not corrected).** Cross-correlation over ±20 ms found the minimum-error lag at 0.0 to ±15 ms with a maximum relative improvement of **0.22 %** over zero lag. The frozen alignment is sound; no correction was applied anywhere.

---

## 5. canonical16 GT-vs-predicted pose error (PHASE 4)

Bridge diagnostic only. No design decision is taken from these numbers.

| metric | value |
|---|---|
| **canonical16 MAE** | **19.673°** |
| canonical16 RMSE | 26.808° |
| canonical16 median \|error\| | **14.374°** |
| canonical16 p95 \|error\| | 56.64° |
| per-session MAE | median **17.79°**, mean 18.72°, sd 5.37°, min 9.37°, max 28.45° |

This is consistent with the official emg2pose regression baseline's published error scale for VEMG2Pose. It is **not** an anomaly; it is the estimator's real accuracy, and it is large.

---

## 6. Per-DOF error (degrees)

| canonical DOF | MAE | median abs | mean bias |
|---|---|---|---|
| thumb_cmc_flexion | 9.98 | 7.78 | −5.54 |
| thumb_cmc_ab_adduction | 9.41 | 7.68 | +4.62 |
| thumb_mcp_flexion | 20.60 | 18.08 | **+17.06** |
| thumb_ip_flexion | 20.39 | 17.36 | −9.82 |
| index_mcp_flexion | 13.32 | 10.74 | −3.67 |
| index_pip_flexion | 22.01 | 16.25 | +8.43 |
| index_dip_flexion | 17.05 | 12.86 | +1.26 |
| middle_mcp_flexion | 20.88 | 16.29 | +10.67 |
| middle_pip_flexion | **28.34** | 21.62 | −16.37 |
| middle_dip_flexion | 22.03 | 15.47 | −11.50 |
| ring_mcp_flexion | 21.72 | 17.78 | −11.34 |
| ring_pip_flexion | 26.93 | 20.02 | −3.49 |
| ring_dip_flexion | 19.26 | 12.89 | +7.72 |
| pinky_mcp_flexion | 18.37 | 15.20 | −3.29 |
| pinky_pip_flexion | 21.98 | 17.26 | −1.31 |
| pinky_dip_flexion | 22.50 | 15.98 | +2.37 |

Largest systematic bias: `thumb_mcp_flexion` +17.06° (the estimator over-flexes the thumb MCP). Smallest errors are the two thumb CMC axes, the two axes the DB9 mapping is least certain about — a caution, not a reassurance.

---

## 7. DB9-domain / OOD comparison — **emg2pose GT** (PHASE 5)

> **Corrected after the independent S5 audit** (see §23). Two statements in this
> section were wrong and are withdrawn: the sklearn covariance explanation, and
> the primary explanation of the 13.2 % held-out figure. No number changed.

Geometry (all frozen-decoder z-space, DB9-train only): 6 class centroids; pooled **within-class** covariance, Ledoit-Wolf shrunk (coefficient 0.1245) toward the scaled identity; metric `d(x) = min_c sqrt((z−μ_c)′Σ⁻¹(z−μ_c))`.

**Covariance identity (corrected).** This reproduces sklearn's own `LDA.covariance_` **exactly** — max abs difference **0.0**. That is not a coincidence and it is not a correction of a sklearn defect: sklearn's `_class_cov` hands each class subset `X[y == group]` to `_cov`, which centres by **that subset's own mean, i.e. the class mean**, so `lda.covariance_` **is** the correctly centred pooled within-class covariance. The audit verified the three objects are the same matrix: this audit's shrunk pooled estimate, `sklearn.discriminant_analysis._class_cov(...)`, and the fitted `lda.covariance_` (all pairwise max abs difference 0.0; an explicit class-mean-centred pooled computation agrees to 1.1e-16).

An earlier version of this section claimed sklearn centres each class by the *global* mean and that `lda.covariance_` is therefore "between-class inflated", citing a 0.0576 difference as evidence. **That claim was false.** The 0.0576 quantity is the **shrinkage effect** — the unshrunk pooled within-class covariance versus the shrunk estimate — and says nothing about sklearn's centring. The metric actually used was always the correct one; only the explanation was wrong. The original note is retained in the artifact, marked `_STALE`, with the correction alongside it (`phase5_db9_geometry.sklearn_lda_covariance_note_CORRECTED`).

Reference, **computed from DB9 only, before any emg2pose value was inspected**:

| reference | value |
|---|---|
| DB9 training (n=1224) median d | 3.604 |
| DB9 training **p95 threshold (frozen)** | **5.516** |
| DB9 training fraction beyond p95 | 5.07 % (by construction) |
| **DB9 held-out (43 outcome-unseen, n=1548) median d** | 3.979 |
| **DB9 held-out fraction beyond the p95 threshold** | **13.24 %** |

**Why the held-out figure is 13.2 % and not ~5 % (corrected).** The previous explanation — a family-wise statistic over six class regions making the threshold "conservative, not over-tight" — over-emphasised a secondary effect. The audit's decomposition:

* **The support statistic itself is approximately unbiased.** A within-subject split-half diagnostic on the same 34 subjects (random half of each subject-class repetition pool as the estimator, the other half held out) gives a held-out exceedance of **4.74 %** against a nominal 5 %. So the gap is **not** an in-sample/out-of-sample artefact of the estimator.
* **The primary cause is source-database / cohort distribution shift.** From the frozen subject manifest, the 34 `development_exposed` subjects are **DB1 (27) + DB5 (7)**; the 43 outcome-unseen subjects are **DB2 (40) + DB5 (3)**. **Not one DB2 subject is in the training cohort.** The "held-out false-alarm rate" therefore measures between-database domain shift as much as subject sampling. Audit diagnostics: per-subject median distance 4.04 (sd 0.71) held-out vs 3.68 (sd 0.54) training, subject-level **permutation p = 0.0158**, subject-bootstrap 95 % CI for the 13.2 % = **[8.5 %, 18.6 %]**; per-class held-out exceedance ranges from 5.4 % (movement 4) to 34.1 % (movement 6), i.e. class-specific rather than a uniform mis-calibration.
* **The family-wise effect is real but secondary.** A single 16-dof χ² at this threshold would give 1.59 %, so the min-over-six structure does widen the tail — but it is not the dominant term.

**Correct scientific message:**

> The 13.2 % held-out exceedance is substantially influenced by source-database
> distribution shift. The support statistic itself behaves close to the nominal
> 5 % level in a within-subject split-half diagnostic.

This is a **descriptive calibration observation, not a new confirmatory statistical claim**.

Robustness views give the same conclusion for the emg2pose comparison (unshrunk pooled: median 3.673, p95 5.700; diagonal metric: median 3.614, p95 5.817).

**emg2pose GT against that reference:**

| quantity | value |
|---|---|
| median d | **7.063** |
| mean d | 6.919 (sd 1.593), min 3.203, p05 4.315, p95 9.311, max 16.99 |
| **fraction beyond the DB9 p95 threshold** | **77.04 %** |
| fraction beyond the DB9 *held-out* p95 | 61.5 % |
| **median percentile position in the DB9 held-out distribution** | **97.22nd** |
| frames inside the DB9 held-out **median** distance | **1.70 %** |
| per-session fraction beyond p95 | median **86.7 %**, mean 79.0 %, sd 23.8 %, range 14.7 – 100 % |
| sessions with > 90 % of frames outside | **13 / 30** |
| sessions with 0 frames inside | **5 / 30** |

**Reading — and the scope of this claim.** The correct statement is:

> The overall natural-pose distribution in the emg2pose mini corpus is poorly
> covered by the deliberately narrow support object defined from six DB9 posture
> classes.

The support object contains only: the **frozen six posture classes**, their
**representative postures** (central third of each repetition, median-pooled), and
the **frozen DB9 training/reference population**. It is a min-over-six-centroids
Mahalanobis ball fitted on 1224 representative postures from six movements in 34
subjects.

It does **not** mean, and this report does **not** claim:

* that DB9 and emg2pose coordinates are incompatible;
* that the 15 aligned flexion coordinates failed to align;
* that emg2pose poses are invalid;
* that DB9 poses in general do not overlap emg2pose.

Even the most favourable 5 % of emg2pose frames sit at the DB9 threshold, and only 1.7 % are closer to any DB9 class than the *median* DB9 held-out posture. Measured against the same z-space, the emg2pose GT cloud's nearest-DB9-sample distance is 2.97 z-units against a 0.63 z DB9 within-class nearest-neighbour scale: the gap is real, but a large part of the 77 % is a property of how narrow the frozen support object is.

---

## 8. DB9-domain / OOD comparison — **predicted pose**

| quantity | GT | predicted |
|---|---|---|
| median d | 7.063 | **7.601** |
| fraction beyond DB9 p95 | 77.0 % | **86.6 %** |
| median percentile in DB9 held-out dist. | 97.2nd | **98.8nd** |
| per-session fraction beyond p95 | 86.7 % median | **92.5 % median** |

The prediction drifts **further** from the DB9 class regions in 64.2 % of frames (median +0.538 z-units). This is expected — VEMG2Pose is fitted to reproduce joint trajectories, not to stay inside DB9's class regions — and it is recorded as a fact, not as a defect.

---

## 9. GT-pose vs predicted-pose decoder top-1 agreement (PHASE 6)

**DOWNSTREAM DECODER STABILITY / GT-POSE vs PREDICTED-POSE DECODER AGREEMENT** —
*not* accuracy.

| metric | value |
|---|---|
| **top-1 agreement** | **0.76463** (76.46 %) |
| disagreements | **20,444 / 86,858** |
| per-session agreement | median **0.8047**, mean 0.7796, sd 0.1740, range **0.4165 – 1.0000** |
| sessions at 100 % agreement | **1 / 30** |
| sessions below 95 % agreement | **23 / 30** |

**Stratified by DB9 domain distance (GT)** — monotone, which is the key result:

| GT distance quartile | n | top-1 agreement | mean \|ΔP\| | mean JSD |
|---|---|---|---|---|
| 3.20 – 5.66 (closest) | 21,715 | **0.963** | 0.0123 | 0.0228 |
| 5.66 – 7.06 | 21,714 | 0.823 | 0.0602 | 0.1084 |
| 7.06 – 8.10 | 21,714 | 0.660 | 0.1124 | 0.2054 |
| 8.10 – 16.99 (farthest) | 21,714 | **0.612** | 0.1264 | 0.2269 |

**Stratified by GT decoder margin** — also monotone:

| GT margin quartile | n | top-1 agreement | mean \|ΔP\| | mean JSD |
|---|---|---|---|---|
| 0.00000008 – 6.23 (narrowest) | 21,715 | **0.442** | 0.1810 | 0.3140 |
| 6.23 – 14.24 | 21,714 | 0.755 | 0.0831 | 0.1592 |
| 14.24 – 22.03 | 21,714 | 0.897 | 0.0350 | 0.0674 |
| 22.03 – 41.78 (widest) | 21,714 | **0.965** | 0.0123 | 0.0228 |

Agreement is worst exactly where the auditor should be most suspicious: far outside DB9 support, and where the oracle decoder itself was barely decided.

### What 76.46 % is — and what it is not

It is **GT-POSE vs PREDICTED-POSE DECODER AGREEMENT**, equivalently
**DOWNSTREAM DECODER STABILITY**. It is **not** gesture accuracy, **not** posture
accuracy against semantic truth, and **not** end-to-end classification accuracy.
There is no accuracy to be had here in either direction, because the GT-side
operand is itself an extrapolation.

**Imbalance limitation, stated explicitly.** The oracle-pose label distribution on
this mini corpus is highly imbalanced — movement/class **4 dominates at 68.6 %**,
movement 1 at 17.5 %, movement 6 at 6.4 %, movement 7 at 4.4 %, movement 2 at
**1.9 %** and movement 3 at **1.3 %**, against a balanced 16.7 % design. Therefore
**76.46 % is a self-consistency statistic under the natural emg2pose mini pose
distribution, not a balanced six-class semantic score**, and it must not be read
as one. A balanced six-class figure is not defined here, because no semantic
posture ground truth exists for these frames.

The two stratifications above are descriptive marginal associations. The audit
established that they are **not** a dose–response: within GT-distance or GT-margin
strata the effect of prediction drift changes sign, and
Spearman(agreement, |Δd|) = **−0.176** (larger predicted drift goes with *higher*
agreement, because drift co-occurs with larger margins). See §16 and §23.

---

## 10. Probability, JSD and margin differences

| metric | value |
|---|---|
| mean \|ΔP\| (per class, per frame) | 0.0778 |
| **median \|ΔP\|** | **8.7e-10** |
| mean L2 (ΔP) | 0.3214 |
| max \|ΔP\| | 1.0000 |
| mean JSD | 0.1409 (sd 0.2477, **median 5.0e-5**, p75 0.1531, p95 0.6916) |
| GT mean top-1 probability | 0.9634 |
| predicted mean top-1 probability | **0.9715** |
| GT mean margin | 14.420 |
| predicted mean margin | 14.178 |
| mean signed margin change | −0.242 |
| mean \|margin change\| | 7.053 |

**The distributions are extremely bimodal**: the median frame is essentially unaffected (median JSD 5e-5), while a substantial minority changes almost completely (p95 JSD 0.69 of a maximum 0.693). "Mean JSD 0.141" describes a mixture of two very different populations, not a uniform blur.

**A diagnostic worth stating explicitly:** the predicted pose is *more* confident than the GT pose (0.9715 vs 0.9634 mean top-1 probability). A DB9 classifier produces confident probabilities far outside its training support, and this audit demonstrates it on real data. **Confidence is not evidence of semantic validity.**

---

## 11. Discriminant-direction error analysis (PHASE 7)

Basis: orthonormal eigenvectors of the between-class scatter of the six DB9 classes (rank 5 — the complete set of directions in which class means differ, so the LDA decision is a function of the data only through that subspace). All quantities in the frozen decoder's z-space.

| metric | emg2pose | DB9 within-class reference |
|---|---|---|
| mean total error magnitude | 3.169 | 2.531 |
| mean discriminant-subspace component | 1.572 | 1.373 |
| mean orthogonal component | 2.705 | — |
| **mean discriminant energy fraction** | **0.2714** | **0.3259** |
| median discriminant energy fraction | 0.2508 | 0.3041 |
| frames with > 50 % discriminant energy | **7.05 %** | — |

**Answer to the PHASE-7 question.** The VEMG2Pose error is **not** preferentially aligned with class-separating directions: only 27.1 % of its squared error energy lies in the discriminant subspace, **below** the 32.6 % that ordinary DB9 within-class variation occupies there. It is a large, largely non-discriminant perturbation — closer to "parallel to harmless within-class variation" in *direction*, while being far larger in *magnitude* (total 3.17 vs 2.53 z-units) and, crucially, displaced far outside the DB9 regions altogether.

The direction is favourable; the magnitude and the location are not.

**Consequence for the mechanism claim (added after the independent S5 audit).** Because
the error is *not* preferentially class-separating, this report must **not** claim that
the VEMG2Pose error is especially harmful because it points along posture-discriminant
directions. The audit quantified this directly: replacing the real error directions with
random directions of the **same magnitudes** yields agreement **0.7507** (sd 0.0003)
versus the observed **0.7646** — i.e. the directional structure of the error is worth
only ~1.4 percentage points. The supported mechanism is **error magnitude relative to
available decision margin**, not error direction.

---

## 12. Dominant DOFs behind boundary crossings (PHASE 8)

**Method, exact.** `margin = decision(top1) − decision(top2)` under the frozen LDA. The LDA is linear, so
`Δmargin = (z_pred − z_gt) · (coef_a − coef_b)` decomposes **exactly** into one linear contribution per canonical DOF (the intercept cancels). The decoder is not modified. Because the top-2 *pair* changes often far out of domain, the operative pair is the **union** of the GT-pose and predicted-pose top-2 sets.

**Exact definition of the reported shares** (this is what the numbers mean, and the
only thing they mean):

```
contrib_dof  = (z_pred − z_gt)_dof · (coef_a − coef_b)_dof        [signed]
share_dof    = |contrib_dof| / Σ_over_all_16_DOF |contrib|        [per frame]
reported     = mean over the 20,444 disagreeing frames of share_dof
```

* **Numerator**: one DOF's absolute contribution to the exact linear decomposition of
  the change in the operative LDA score margin, for that frame.
* **Denominator**: the sum of **absolute** contributions over **all 16** canonical DOFs
  of that same frame. It is *not* the margin change (which is signed and can be near
  zero) and *not* an error count. Verified: `Σ_dof mean(share) = 1.000000000000001`.
* **Cancellation**: contributions are signed and do cancel across frames; the share is
  built from `|·|` **before** the share is formed, so cancellation does not inflate the
  figure. Measured for thumb-AA: `mean(signed) = −3.402` vs `mean(|·|) = +5.413`.
* **Averaging order**: `|·|` per frame first, each frame's share vector normalised to
  sum to 1, then averaged over frames. A per-DOF `mean|contrib| / Σ mean|contrib|`
  would be a different (also defensible) number; it is **not** what is computed.
* **Operative pair caveat**: because the top-2 order is near-degenerate far out of
  domain, different frames use different boundary normals `coef_a − coef_b`. The
  decomposition is exact per frame, but the reported share is an average over a
  **mixture of boundary normals**, so cross-frame share comparisons are
  cross-boundary comparisons.
* Decomposition exactness: max abs residual **6.04e-14** over all 86,858 frames.

**Group shares on disagreeing frames** (and, for contrast, on agreeing frames):

| group | disagree | agree |
|---|---|---|
| thumb CMC flexion | 0.024 | 0.036 |
| **thumb CMC ab/adduction** | **0.186** | 0.115 |
| **thumb MCP + IP** | **0.195** | 0.179 |
| **finger MCP (×4)** | **0.335** | 0.411 |
| finger PIP (×4) | 0.136 | 0.125 |
| finger DIP (×4) | 0.123 | 0.134 |

**What the thumb-AA figure means — exact statement.** On the 20,444 frames where the
GT-pose and predicted-pose top-1 decoder labels differ, the thumb CMC ab/adduction
axis accounts on average for **18.6 %** of the total **absolute** per-DOF
contributions to the exact linear decomposition of the change in the operative LDA
score margin — where each frame's contribution is normalised by the sum of absolute
contributions over all 16 canonical DOFs of that same frame.

It is an **attribution mass over decision-margin shift**, averaged over frames, on
disagreeing frames only. It is explicitly **not**:

* "18.6 % of classification mistakes are caused by thumb-AA" — the computation
  contains **no error count** in its numerator or denominator;
* a causal share — the decomposition is linear-algebraic, not causal;
* a statement that thumb-AA is badly estimated — its GT pose error is among the
  *smallest* of the 16 (9.41° MAE, rank 2).

**The thumb's 4 DOF account for 40.6 % of this attribution mass**, more than the four
fingers' MCP joints combined. Per-DOF, the largest is `thumb_cmc_ab_adduction` (share
**0.1865**, dominant in **6,000 / 20,444** disagreement frames) — the one canonical
variable whose cross-dataset sign/magnitude correspondence Session 3 flagged as
uncertain. Its decision-relevance is out of proportion to its absolute error.

Next largest: `middle_mcp_flexion` (0.1424, dominant 5,019), `thumb_mcp_flexion` (0.1413, dominant 3,393), `pinky_mcp_flexion` (0.1117, dominant 2,256), `index_pip_flexion` (0.0814, dominant 2,135). Zero frames were dominated by `index_dip_flexion` or `pinky_pip_flexion`.

**An exact-boundary reading** (see §16 for why the naive version is misleading):

| quantity | value |
|---|---|
| predicted label overtakes the GT runner-up (GT top-1 vs top-2 boundary) | **17.64 %** of all frames |
| top-1 label differs | **23.54 %** of all frames |
| — of the disagreements, the runner-up is overtaken | 74.9 % |
| — the remainder (25.1 %) | a **third** class takes the top slot |
| median margin, disagreeing frames | 4.597 |
| median margin, agreeing frames | **17.180** |
| median of per-frame \|score shift\|/margin, all frames | 0.620 (a median of per-frame ratios, **not** a ratio of medians, which is 0.518) |

The decoder's margin on disagreeing frames is **3.74× smaller** than on agreeing frames
(17.180 / 4.597). The margin and the pose error are of comparable size on those frames —
which is a statement about **magnitude versus margin**, not about the error's direction
(§11, §23).

---

## 13. Session-level variability

| metric | median | mean | sd | min | max |
|---|---|---|---|---|---|
| canonical16 MAE (°) | 17.79 | 18.72 | 5.37 | 9.37 | 28.45 |
| top-1 agreement | **0.805** | 0.780 | 0.174 | **0.417** | **1.000** |
| mean \|ΔP\| | 0.0655 | 0.0731 | 0.0563 | 0.0033 | 0.1954 |
| mean JSD | 0.1091 | 0.1322 | 0.1049 | 0.0035 | 0.3790 |
| fraction of GT frames beyond DB9 p95 | 0.867 | 0.790 | 0.238 | 0.147 | 1.000 |

| | session | stage | side | MAE | agreement | GT frac. outside |
|---|---|---|---|---|---|---|
| best | `…recording-15_left` | unconstrained | left | 9.37° | **1.000** | 100 % |
| worst | `…recording-12_right` | HookEmHornsOKScissors | right | — | **0.417** | 99.4 % |

**The best and the worst session are equally far outside the DB9 domain** (both 100 % / 99.4 % of frames beyond the threshold) yet differ by 58 percentage points in agreement. Domain distance alone does not predict decoder stability. This is the clearest single piece of evidence that distance is not the whole story.

**Correction to the mechanism stated here previously.** An earlier version of this
section concluded "…the *error magnitude relative to the local decision margin* does".
The audit showed that gloss is only **partly** supported: the two marginal
stratifications in §9 are real monotone associations, but they are not a dose–response.
Conditionally on GT distance or GT margin the effect of prediction drift **changes
sign**, and a direction-shuffled error null reproduces the agreement to within 1.4
percentage points. What survives is the weaker and more careful statement: on
disagreeing frames the decoder's margin (4.60) and the prediction error's projection
(median |shift| 12.25 z-units) are of the same order, so the label moves without the
decision geometry having changed. The specific mechanism behind the
best-vs-worst-session gap is **not** established by this audit.

### Single-subject limitation (repeated here because it governs §9, §12 and this section)

The mini corpus contains **30 sessions — and only one unique subject**
(`d387095792` / session `2022-12-06-1670313600-e3096-cv-emg-pose-train@2`), 15 stages ×
2 sides. **S5 is therefore a mechanism/bridge diagnostic, not cross-subject bridge
validation.** Every number in this report — MAE, domain fraction, agreement,
attribution — is within-subject. Side and stage variability here must not be upgraded
into cross-subject evidence anywhere.

---

## 14. canonical15 / canonical12 descriptive robustness

Post-confirmatory bridge diagnostics. **Not** a representation-selection competition; nothing here selects, ranks or prefers a representation, and no decoder was refit on a subset.

| representation | MAE | median \|error\| | total attribution mass on disagreements |
|---|---|---|---|
| canonical16 (16 DOF) | **19.673°** | 14.374° | 31.68 |
| canonical15_noThumbAA (15) | 19.485° | 16.252° | 26.26 |
| canonical12_noDIP (12) | 19.388° | 16.271° | 27.808 |

Dropping the four DIP variables or the thumb-AA variable changes the pose error by under 0.3°. The pose-estimation error is **not** concentrated in the variables the representation ablations remove — consistent with §11's finding that the error is broadly non-discriminant.

---

## 15. Representative visual examples (PHASE 9)

Eight figures in `bridge_audit/results/figures/`, selection rule pre-declared and quantile-based, **at most one frame per session**, chosen deterministically; emg2pose `stage` names play no part in the selection:

* 2 × `A_low_error_agreement` (agreement and MAE ≤ p05)
* 2 × `B_moderate_error_agreement` (agreement and p25 ≤ MAE ≤ p50)
* 2 × `C_boundary_crossing` (labels differ, nearest the median disagreement error)
* 2 × `D_confident_output_far_outside_db9` (agreement and GT distance ≥ p99)

Rendered with the frozen Session-4 forward kinematics (official 21-landmark model, two 3D viewpoints). Metadata, incl. exact frame index, session, time, MAE, both labels, and the domain distance, in `results/phase9_visual_examples.json`.

**Stated on every figure:** canonical16 is a lossy projection; the four non-thumb MCP ab/adduction DOF are absent from it and are drawn as zero — identically on the GT and the predicted side — so they cannot create a visual difference between the two hands.

The two `C_boundary_crossing` pairs are instructive, and this sentence describes the
**first** of them (`decoder_gt = 1` → `decoder_pred = 6`, canonical16 MAE 21.59°):
GT pose → decoder says *thumb up*; predicted pose → decoder says *fist*. The two hand
geometries are visibly similar; the decision changed because the margin was narrow, not
because the pose became a different posture. The **second** C pair has
`decoder_gt = 4` → `decoder_pred = 1`. Both pairs and their metadata are in
`results/phase9_visual_examples.json`. (Clarified after the independent audit noted
this sentence did not say which of the two pairs it described.)

---

## 16. Which case the evidence supports

> **Corrected after the independent S5 audit** (see §23). CASE C is retained **only in
> its narrow distributional sense** and must not be phrased as coordinate-system
> incompatibility. The estimator-mechanism sentences have been softened: the evidence
> supports error **magnitude relative to decision margin**, not a uniquely harmful
> error **direction**.

### **CASE C — narrow sense only — with a measured secondary contribution from the pose estimator.**

Per the pre-declared interpretation rule:

> **CASE C:** even emg2pose GT lies strongly outside DB9 six-class support. Then the
> DB9→emg2pose semantic bridge itself is not established. Do **not** blame
> VEMG2Pose or rescue the decoder.

**How CASE C may be stated (and only how):**

> The overall emg2pose natural-pose distribution is largely outside the six-class DB9
> posture support.

**How CASE C must NOT be stated:** as coordinate-system incompatibility, as a failure of
the 15 aligned flexion coordinates to align, as emg2pose poses being invalid, or as
"DB9 poses in general do not overlap emg2pose". See §16b for the positive evidence of
*partial* coordinate compatibility.

**Evidence for CASE C (narrow sense):**
1. 77.04 % of emg2pose **GT** frames exceed the DB9-only p95 threshold; the DB9 held-out false-alarm rate for that same threshold is 13.24 %, substantially a source-database shift effect (§7).
2. The **median emg2pose GT frame sits at the 97.22nd percentile** of the DB9 held-out distance distribution; only 1.7 % of frames are inside the DB9 held-out median distance.
3. 13/30 sessions have > 90 % of frames outside; 5/30 have none inside.
4. The oracle-pose decoder's own labels are **degenerate**, which is what an out-of-support 6-class LDA looks like: movement 4 takes **68.6 %** of frames, movements 2 and 3 only 1.9 % and 1.3 %, against a balanced design of 16.7 % each — yet the mean top-1 probability is **0.963**. The decoder is emitting confident labels, and those labels do not have the distribution the frozen task guarantees.
5. The best-agreeing session and the worst-agreeing session are equally far outside the domain (§13).

**Evidence for the secondary (estimator) contribution:**
6. Top-1 agreement is 76.46 % — well above the 16.7 % chance level, so the frozen decoder's decisions on GT-pose and on predicted-pose are **not** independent; the DB9 decoder keys on something VEMG2Pose preserves.
7. Agreement falls monotonically across GT domain-distance quartiles (0.963 → 0.612) and rises monotonically across GT-margin quartiles (0.442 → 0.965) (§9). These are **marginal associations**, not dose–response relations.
8. On disagreeing frames the decoder's margin is **3.74× narrower** than on agreeing frames (4.597 vs 17.180) (§12).
9. The average pose error (19.67° MAE; 3.17 z mean total error) is large relative to the margins the decoder operates with (median margin 14.24 z, median |score shift| 7.37 z) (§12).

**Therefore: the dominant, formally sufficient reason for the disagreement is CASE C in
the narrow, distributional sense — the overall emg2pose natural-pose distribution is
largely outside the six-class DB9 posture support.** VEMG2Pose is not the cause; it is a
measurable secondary contributor operating on an already out-of-support input (§8, §12).

**Mechanism, stated at the strength the evidence supports.** The counter-hypothesis
"the pose error is specifically distorting class-separating geometry" is **not
supported**: the discriminant energy fraction is 0.271, *below* the 0.326 DB9
within-class reference (§11), and a direction-shuffled error null reproduces the
observed agreement to within 1.4 percentage points (0.7507 vs 0.7646). The supported
statement is:

> VEMG2Pose prediction error contributes downstream decision instability, but the
> current evidence suggests that error **magnitude relative to available decision
> margin** is more important than a uniquely harmful error direction.

**Do not** claim that discriminant-direction error is the primary bottleneck.

**A rejected reading, recorded for honesty.** A naive "boundary pair changed" counter runs at 61.8 % even in frames where the top-1 label is identical, because the top-2 *order* is nearly degenerate far out of domain. It is reported for transparency and explicitly labelled as **not** a stability metric. Two earlier drafts of this audit's own boundary algebra asserted a false identity (`mg == −dz·nrm`, which would force every predicted score difference to zero); both were caught by the numeric self-check now embedded in the artifact and in the test suite, and the rejected identity is recorded in `domain_depth_supplement.json`. The verified identity, at **5.68e-14** residual over all 86,858 frames, is
`[Vg_A − Vg_B] + (z_pred − z_gt)·(coef_A − coef_B) == Vp_A − Vp_B`
with crossing-predicate agreement 1.000000.

### 16b. Partial coordinate compatibility — audit diagnostics (evidence AGAINST incompatibility)

The independent audit ran compatibility tests that S5 had not run. They are **diagnostics,
not proof of complete coordinate equivalence**, and they positively argue against a
coordinate-incompatibility reading:

| test | result | reading |
|---|---|---|
| units | both datasets in **radians**, canonical16 by official joint name | no unit mismatch |
| per-DOF **sd** correlation across the 16 axes | r = **+0.551** | comparable measurement scale |
| per-DOF mean correlation | r = **+0.141** (Spearman +0.282) | not an anti-correlation; only 3/16 means have opposite sign |
| inter-joint correlation-matrix agreement (120 off-diagonal pairs) | r = **+0.500**; sign agrees on **84/120** | shared structure, partly re-ordered — neither a scramble nor an identity |
| single 16×16 affine map (ridge, fitted on 15 sessions, evaluated on the other 15) | nearest-neighbour mismatch **2.956 → 1.352 z-units (−54.7 %)** | a large linear component exists; a simple affine mapping removes a substantial fraction of the distribution mismatch |
| discriminant-energy fraction | **0.271**, *below* the DB9 within-class reference 0.326 | no pathological distortion of decision directions |
| residual after every affine map | 1.352 z vs 0.634 z DB9 within-class NN diameter (≈ 2.1×) | a large residual survives — the distributions genuinely differ |

**Conclusion on the claim boundary:** the evidence supports *"the overall emg2pose pose
distribution is largely outside the six DB9 posture regions"* and does **not** support
*"the coordinate systems are incompatible"*. The honest description is **partially
compatible coordinates, materially disjoint posture distributions, on a narrow support**.
The word "incompatible" appears nowhere in this report as a claim and must not be
introduced.

---

## 17. Exact claims now supported

1. The frozen Session-3 primary decoder (LDA `lsqr`/`auto` + train-only z-score + canonical16, trained on the 34 development-exposed subjects) can be **reconstructed exactly**: 1548/1548 identical Tier-A decisions, scaler identical to 0.0, probabilities within 5.1e-15. Its parameters are serialised in `bridge_audit_results.json`.
2. On the official emg2pose mini corpus (30 sessions, one held-out user, 86,858 paired GT-valid samples at the model's native 50 Hz cadence), VEMG2Pose's canonical16 pose error is **MAE 19.673°, median 14.374°**, per-session median 17.79° (range 9.37–28.45°).
3. **The overall emg2pose natural-pose distribution is poorly covered by the frozen six-class DB9 support**: 77.04 % of GT frames beyond a DB9-only p95 threshold; median emg2pose frame at the 97.22nd percentile of the DB9 held-out distance distribution. The held-out DB9 exceedance of that threshold is 13.24 %, substantially a **source-database/cohort distribution shift** effect (development-exposed = DB1+DB5, outcome-unseen = DB2+DB5), with a within-subject split-half diagnostic at 4.74 % against a nominal 5 %.
4. Applying the frozen decoder to GT emg2pose poses yields a **degenerate, highly confident label distribution** (movement 4 = 68.6 % of frames, movements 2/3 < 2 %, mean top-1 probability 0.963). The oracle-pose reference is itself an extrapolation.
5. GT-pose vs predicted-pose **top-1 decoder agreement is 0.7646273** (20,444/86,858 disagreements), from 41.7 % to 100 % across sessions (median 80.5 %). This is a **self-consistency statistic under an imbalanced natural pose distribution**, not a balanced six-class semantic score.
6. Agreement falls monotonically across GT-pose domain-distance quartiles (0.963 → 0.612) and rises monotonically across GT decoder-margin quartiles (0.442 → 0.965); 23/30 sessions are below 95 % agreement.
7. The pose error's direction is **not** disproportionately discriminant: 27.1 % of its squared error energy lies in the five-dimensional between-class subspace, versus 32.6 % for ordinary DB9 within-class variation. The error **magnitude** relative to available decision margin is the supported mechanism; error **direction** is not.
8. On disagreeing frames the decoder's margin drops to 4.60 versus 17.18 on agreeing frames (3.74×), so the frozen decoder's margin and the pose error are of comparable size on the frames where the label moves.
9. **thumb CMC ab/adduction accounts for 18.65 %** of the **absolute per-DOF margin-shift attribution mass** on disagreeing frames and is the single dominant DOF in 6,000/20,444 of them — the variable Session 3 already flagged as the least certain cross-dataset correspondence. (Exact numerator/denominator: §12.)
10. Dropping the four DIP variables or thumb-AA changes the pose error by < 0.3° (§14): the estimator error is broad, not concentrated in the ablated DOFs.
11. The frozen Session-2 GT/prediction time alignment is **correct as frozen**: the best cross-correlation lag improves the error by at most 0.22 %.
12. The datasets are **not coordinate-incompatible**: both are radians on named joint axes, per-DOF scale correlation r = +0.551, inter-joint correlation structure agrees on 84/120 signs, a single affine map removes 54.7 % of the nearest-neighbour mismatch, and the discriminant-energy fraction is below the within-class reference. These are **diagnostics indicating partial coordinate compatibility**, not proof of coordinate equivalence.
13. Every arithmetic claim above is reproducible from stored artifacts. The independent audit reproduced **42/42 headline claims** at the reported precision, and the project's own 28-test suite passes.

---

## 18. Claims still unsupported

* **No gesture accuracy, posture accuracy, or end-to-end recognition claim.** emg2pose provides no frame-level labels for the six DB9 postures. `stage` labels were never used as posture truth.
* **No claim that VEMG2Pose is inadequate for its own task.** Its EMG→pose error here is consistent with the official baseline's published scale. This audit says nothing about pose-estimation quality as such.
* **No claim about the 43 outcome-unseen DB9 subjects.** They appear only as the PHASE-1 handshake target.
* **No cross-subject bridge evidence.** The official mini corpus is a single subject. Side/stage variability here is within-subject only.
* **No claim that any emg2pose frame *is* one of the six DB9 postures**, or is not. The domain statistic says the *distribution* is far outside; it does not adjudicate individual frames.
* **No representation-selection claim.** canonical15/canonical12 numbers are descriptive only.
* **No claim that the DB9 decoder is wrong, mistuned, or should be changed.** It was applied exactly as frozen; per CASE C's rule it is not to be rescued or blamed.
* **No tuning of anything against emg2pose outcomes** — no threshold, no decoder, no model, no representation, no hyperparameter.
* **No causal statement** about *why* emg2pose kinematics sit outside DB9 support (e.g. differing sensor modalities, differing pose distributions, differing subject populations). That is a new question, not answered here.
* **No coordinate-incompatibility claim.** The independent audit found positive evidence of *partial* coordinate compatibility (§16b). "Incompatible" must not be introduced by any successor document.
* **No claim that discriminant-direction error is the primary bottleneck.** The direction-shuffled null (§11, §23) does not support it.
* **No claim that the 13.24 % held-out exceedance is a confirmatory statistical finding.** It is a descriptive calibration observation substantially attributable to source-database shift.
* **No balanced six-class interpretation of 76.46 %.** The GT-decoder label distribution is imbalanced (movement 4 = 68.6 %); the figure is a self-consistency statistic under the natural emg2pose mini pose distribution.
* **No claim of cross-subject bridge validation.** 30 sessions, **one** subject (§13).

---

## 19. Unresolved risks

1. **Single-subject mini corpus.** Every number is one user. The bridge could behave differently on other users; nothing here bounds that.
2. **DB9 support is defined by representative postures only** (central third of each repetition median-pooled). A continuous-DB9-support definition would give a different, probably smaller, OOD fraction.
3. **The four MCP-AA DOF are dropped by canonical16**, so the audit cannot see error that lives only in those dimensions. If VEMG2Pose errs mainly in index/middle/ring/pinky abduction, this audit is blind to it.
4. **The thumb-AA axis correspondence is unresolved across datasets**, and it is the largest single contributor to decision-relevant error (§12). A wrong sign or magnitude mapping for that one variable would move the §12 attribution — though not the §7/§8 domain conclusions, which do not depend on it (the diagonal and unshrunk metrics agree, and removing the variable entirely changes the pose error by 0.19°).
5. **The 50 Hz fencepost phase is unmeasured** (§4). The block-mean reduction is phase-robust and cross-checked against the full 2 kHz MAE, but a different reduction could shift the MAE by a fraction of a degree.
6. **The checkpoint's training split could not be re-derived.** `held_out_user=True` and 0 train-split rows are the available evidence; if the released checkpoint saw this user anyway, the pose error here would be optimistic — which would *strengthen* CASE C, not weaken it.
7. **No confidence intervals or significance tests.** None were pre-registered, and adding one is a `WHAT COUNTS` decision owned by the research lead. (The audit's bootstrap CI and permutation p for the 13.24 % figure are **audit diagnostics**, reported descriptively; they are not confirmatory inference attached to a pre-registered endpoint.)
8. **`pass = 8`** (negative-control movement 1 of DB9) was not part of the frozen six-class vocabulary and was not evaluated.
9. **The best-vs-worst-session gap is unexplained.** The audit showed the naive "error magnitude vs margin" gloss is not a dose–response (conditional drift effect changes sign; direction-shuffled null within 1.4 pp). The cause of the 58-point spread across sessions remains open.
10. **The per-frame share denominators differ across frames.** Because the operative boundary pair is data-dependent far out of domain, the §12 attribution shares are cross-boundary comparisons; the thumb-AA figure is valid as computed but is an average over a mixture of boundary normals.
11. **The `|score shift| / margin = 0.620` figure is a median of per-frame ratios**, not a ratio of medians (which is 0.518). Stated here explicitly so it is not miscited.

---

## 20. Artifact paths

All paths relative to `emg2pose_handstate/` (also reachable as `<PROJECT_ROOT>\…`).

### Code
| path | role |
|---|---|
| `bridge_audit/_common.py` | shared primitives; **single source of truth** for pairing, hashing, JS divergence |
| `bridge_audit/decoder.py` | PHASE 1 reconstruction + handshake; PHASE 5 domain geometry |
| `bridge_audit/run_bridge_audit.py` | the audit driver (all phases) |
| `bridge_audit/domain_depth.py` | supplemental domain-depth and exact-boundary readings |
| `bridge_audit/visual_check.py` | PHASE 9 representative-pair figures |
| `bridge_audit/tools/apply_audit_corrections.py` | §23 documentation corrections (idempotent, `--check`) |
| `bridge_audit/tests/test_bridge_audit.py` | 28 verification tests |

### Results
| path | contents |
|---|---|
| `bridge_audit/results/bridge_audit_results.json` | **primary artifact**: provenance + SHA-256 hashes, PHASE 1–8 results, per-session tables |
| `bridge_audit/results/BRIDGE_AUDIT_SUMMARY.json` | one-screen summary |
| `bridge_audit/results/domain_depth_supplement.json` | domain-depth readings, oracle-label distribution, exact-boundary algebra + self-check |
| `bridge_audit/results/phase9_visual_examples.json` | selected frames, selection rule, both canonical16 vectors |
| `../_audit_s5/S5_INDEPENDENT_AUDIT_REPORT.md` | independent read-only audit of this lane (42/42 claims reproduced; source of §23 corrections) |
| `bridge_audit/results/figures/*.png` | 8 paired GT/predicted hand renders |
| `bridge_audit/results/sessions/*.paired50hz.npz` | 30 per-session paired canonical16 at native cadence + validity masks (≈10 MB total) |
| `bridge_audit/logs/bridge_audit_run.log` | full run log |

### Reproduce
```powershell
<EMG2POSE_VENV>\Scripts\python.exe <PROJECT_ROOT>\bridge_audit\run_bridge_audit.py `
    --out-dir <PROJECT_ROOT>\bridge_audit\results --no-2khz
<EMG2POSE_VENV>\Scripts\python.exe <PROJECT_ROOT>\bridge_audit\domain_depth.py `
    --results <PROJECT_ROOT>\bridge_audit\results
<EMG2POSE_VENV>\Scripts\python.exe <PROJECT_ROOT>\bridge_audit\visual_check.py `
    --results <PROJECT_ROOT>\bridge_audit\results
<EMG2POSE_VENV>\Scripts\python.exe -m pytest <PROJECT_ROOT>\bridge_audit\tests -v
```

### Environment
Python 3.10.13 · numpy 1.26.4 · scipy 1.13.1 · **scikit-learn 1.5.2 (installed into the venv for this audit)** · torch 2.3.1+cpu · h5py 3.11.0 · matplotlib 3.10.9. Data accessed exclusively through the ASCII junction `<PROJECT_ROOT>` (Session-1 constraint).

### Provenance gap
The project root is not a git repository, so this lane has **no commit**. Provenance is file-content based: SHA-256 for every input and source file is recorded in `bridge_audit_results.json::provenance.artifact_hashes_sha256`, and `provenance.git.baseline_emg2pose_head` pins the official repo. Marked **COMMIT PENDING**.

---

## 21. Stop conditions honoured

No VEMG2Pose fine-tuning · no neural training of any kind (the checkpoint ran in `eval()` under `torch.no_grad()`; the only fitting was the closed-form scaler + LDA refit) · no alteration to the Session-3 decoder, class vocabulary, cohort partition or canonical16 · no canonical18 · no invented emg2pose gesture labels · `stage` never used as posture truth · no thresholds tuned on emg2pose outcomes · no representation optimisation · no end-to-end recognition claim.

**The audit is complete and has stopped here.**

---

## 22. Proposed next step (PROPOSAL, not executed, not authorised)

> **Status update after the independent audit.** The audit partially addressed this
> proposal's premise: it showed the conditional drift effect changes sign and that a
> direction-shuffled null reproduces the agreement to within 1.4 pp, so the
> best-vs-worst-session gap is **not** explained by margin geometry alone. The proposal
> below is therefore still unstarted, but its motivation is weaker than when written.
> The audit's own compatibility diagnostics (§16b) are a better starting point for any
> continuation.

**Idea.** The audit's sharpest unexplained fact is that the *best* and *worst* sessions sit equally far outside DB9 support yet differ by 58 points in decoder agreement (§13). That points at a second-order structure — per-session margin geometry — rather than at distance alone.

**Motivation.** If per-session agreement is predictable from features computable *without* the pose estimator (e.g. the GT-pose margin distribution, the local class-region geometry), then the 76.5 % figure decomposes into an irreducible CASE-C component and a genuinely estimator-driven component, and the latter becomes the quantity worth attacking.

**Expected benefit.** A defensible decomposition of the bridge failure into "data not in support" versus "estimator noise", which is exactly what the CASE A/B/C framing cannot currently separate.

**Risk.** It is a post-hoc analysis on the same 30 sessions with no new data. It would be exploratory, not confirmatory, and must be labelled as such. It also risks being read as decoder tuning, which it is not.

**Minimal experiment.** Regress per-session decoder agreement on (a) GT median margin, (b) GT fraction beyond the p95 threshold, (c) per-session pose MAE — 30 points, descriptive only, no model selection, no new run required. Cheap, and it either shows the decomposition exists or kills the idea.

**Not started. Awaiting a research decision.**

---

## 23. DOCUMENTATION CORRECTIONS (2026-09-18) — post independent audit

An **independent read-only audit** (`_audit_s5/S5_INDEPENDENT_AUDIT_REPORT.md`) reproduced
**42/42 headline claims** of this report at the reported precision, from an independent
rebuild of the decoder and the geometry, importing none of `bridge_audit/`. It found **no
fabricated number, no leakage, no refit on the wrong cohort, and no arithmetic error on
the load-bearing path**, and it confirmed that no Session-1–4 artifact was modified.

It did find two interpretation-level errors and several smaller documentation defects.
This round is **documentation correction only**: no inference was run, no model was
fitted, no prediction was generated, and **no saved numeric result was changed**.

### 23.1 Statements corrected in this document

| # | Where | Statement withdrawn | Corrected statement |
|---|---|---|---|
| 1 | §7 (was §7 first paragraph) | "sklearn's stored matrix centres each class by the *global* mean and would have been a between-class-inflated object (max abs difference 0.0576)" | **False.** sklearn's `_class_cov` hands each class subset to `_cov`, which centres by that subset's **own** mean. `lda.covariance_` **is** the correctly centred pooled within-class covariance and equals this audit's shrunk estimate to **0.0**. The 0.0576 is the **shrinkage effect**. |
| 2 | §7 | "it is **conservative**, not over-tight, because it is a family-wise statistic over six class regions" (as the primary explanation of 13.2 %) | The **primary** cause is **source-database / cohort distribution shift** (development-exposed = DB1+DB5; outcome-unseen = DB2+DB5). A within-subject split-half diagnostic gives **4.74 %** against a nominal 5 %. The family-wise effect is real but **secondary**. |
| 3 | §13, §16 (was §16.7/§16.9) | "…the *error magnitude relative to the local decision margin* does" / "deciding inside the noise band" as a mechanism | Softened: the marginal stratifications are real but **not dose–response**. Direction-shuffled null = **0.7507** vs observed **0.7646**; Spearman(agreement, \|Δd\|) = **−0.176**. Supported mechanism: error **magnitude relative to available decision margin**, not a uniquely harmful error **direction**. |
| 4 | §16 | CASE C phrased in a way that could be read as a bridge/coordinate failure | CASE C retained **only** in the narrow distributional sense. §16b added: positive audit evidence of **partial coordinate compatibility**. |
| 5 | §7 | "emg2pose ground-truth kinematics sit essentially entirely beyond the region the six DB9 postures occupy" (unqualified) | Scoped explicitly to the **deliberately narrow support object** (frozen six classes, representative postures, frozen DB9 training/reference population). Explicitly **not** coordinate incompatibility, not an alignment failure, not invalid poses. |
| 6 | §9 | 76.46 % presented without an imbalance caveat | Added: the GT-decoder label distribution is **imbalanced (movement 4 = 68.6 %)**, so 76.46 % is a **self-consistency statistic under the natural emg2pose mini pose distribution, not a balanced six-class semantic score**. |
| 7 | §12 | "thumb CMC ab/adduction alone accounts for 18.6 % of the decision-relevant error" (ambiguous denominator) | Restated with the **exact numerator/denominator**: mean over disagreeing frames of `\|contrib_dof\| / Σ_all16 \|contrib\|`, and an explicit note that it is **not** "18.6 % of classification mistakes". |
| 8 | §15 | "The `C_boundary_crossing` pair is instructive: GT pose → *thumb up*; predicted → *fist*" (did not say which of the two pairs) | Names the **first** pair (`decoder_gt=1` → `decoder_pred=6`, MAE 21.59°) and records the second (`4` → `1`). |
| 9 | §13 | Single-subject status mentioned in §3/§18/§19 but not at the point of use | Repeated **in §13**: 30 sessions, **one** unique subject → S5 is a **mechanism/bridge diagnostic, not cross-subject bridge validation**. |
| 10 | §22 | Proposal motivation stated at full strength | Prefixed with a status note that the audit weakened its premise. |

### 23.2 Code and artifact statements corrected

| File | Statement withdrawn | Corrected |
|---|---|---|
| `bridge_audit/decoder.py` (~L275–296) | "sklearn's LDA stores `covariance_` = Σ_c prior_c · `_cov(X_c)` where `_cov` centres X_c by the **GLOBAL** feature mean … makes `covariance_` a *between-class-inflated* matrix (close to the total covariance)" | Replaced with a `CORRECTION` block recording the measured truth and warning that the 0.0576 field is the shrinkage effect. |
| `bridge_audit/decoder.py` (~L327) | comment "diagnostic: how far the flawed sklearn quantity sits from the correct one" | "This is the SHRINKAGE effect … NOT evidence about sklearn's centring." |
| `bridge_audit/decoder.py` (verbose print) | "sklearn lda.covariance_ vs correctly-centred pooled within-class … (audited: sklearn centres per class by the GLOBAL mean)" | "unshrunk pooled within-class covariance vs lda.covariance_ … -> this is the SHRINKAGE effect, not a centring error" |
| `bridge_audit/decoder.py` (`to_json`) | `sklearn_lda_covariance_note` (false) | Field **retained verbatim** and now flagged `sklearn_lda_covariance_note_STALE`; the correct explanation added as `sklearn_lda_covariance_note_CORRECTED`, plus a verified-equivalence block. |
| `bridge_audit/domain_depth.py` | "~13%, not 5%, because … a family-wise statistic … CONSERVATIVE threshold" | Rewritten: primary cause is source-database/cohort shift, with the audit's split-half 4.74 %, permutation p = 0.0158, and bootstrap CI [8.5 %, 18.6 %]; family-wise effect marked secondary. |
| `bridge_audit/domain_depth.py` | "Margins … are ~4x smaller … routinely deciding inside the noise band" | "3.74x smaller (17.18 / 4.60)"; plus the corrected magnitude-vs-direction note and the direction-shuffled null. |
| `bridge_audit/tests/test_bridge_audit.py` | docstring asserting the now-withdrawn 'global mean' claim was what made the check safe | Docstring corrected: the agreement is exact because `covariance_` genuinely *is* the correctly centred pooled within-class matrix. |
| `bridge_audit/results/bridge_audit_results.json` | `phase5_db9_geometry.sklearn_lda_covariance_note` | **Value unchanged**; marked `_STALE` and superseded by `..._CORRECTED` (+ `sklearn_lda_covariance_equivalence_verified`). A `documentation_corrections` block records the audit report and its SHA-256, the list of corrections, and the SHA-256 of every protected result block **at correction time**. |

Correction script (idempotent, verifiable):
`bridge_audit/tools/apply_audit_corrections.py` (supports `--check`).

### 23.3 Numeric invariance

**Every measured result in this report is unchanged.** No number was recomputed,
re-derived, or replaced in this round. The numbers explicitly preserved include:
1548/1548 handshake decisions identical · 30/30 sessions · 86,858 paired GT-valid
samples at ~50 Hz · canonical16 MAE 19.673° · median absolute error 14.374° · DB9
support threshold 5.5159 · held-out DB9 exceedance 13.243 % · emg2pose GT beyond
threshold 77.04 % · median emg2pose GT location at the DB9 held-out 97.22nd percentile ·
GT-pose vs predicted-pose decoder agreement 0.7646273 · disagreement count 20,444 ·
boundary-identity residual 5.68e-14.

Verified mechanically: `apply_audit_corrections.py` hashes every protected top-level
result block before and after the correction and aborts if any drifts
(**result: no block changed**). The single artifact field whose *text* changed is the
sklearn covariance note, which carries no number other than the explanatory 0.0576
figure — and that figure is **retained unchanged in the same record**.

### 23.4 Verification status after correction

* `pytest bridge_audit/tests -q` → **28 passed** (unchanged).
* `apply_audit_corrections.py --check` → corrections present.
* No model was loaded, no inference was run, no fit was performed, no prediction was
  generated in this round; no S1–S4 artifact was touched.

**S5 is CLOSED / FROZEN.**
