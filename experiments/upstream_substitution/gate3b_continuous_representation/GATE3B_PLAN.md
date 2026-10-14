# GATE 3B PLAN — CONTINUOUS DOWNSTREAM REPRESENTATION PRESERVATION

**Evidence status: POST-HOC MOTIVATED, PROSPECTIVELY FROZEN BEFORE CONTINUOUS-REPRESENTATION OUTCOME INSPECTION.**

Gate3B was motivated by the Gate3 hard-decision result. It was therefore **not** preregistered before
Gate3. It is frozen *now*, before any Fisher/score-space similarity value, decile, or group statistic
has been computed or inspected.

**Gate class: DESCRIPTIVE MECHANISM DIAGNOSTIC.** Not a semantic-accuracy evaluation, not a
transfer-accuracy claim, not a reliability gate, not a Common Pose validity confirmation.

**Phase:** PHASE 1 / GATE 3B
**Predecessor:** GATE 3 (frozen, unmodified) — `GATE3_PLAN.md`
SHA-256 `9869d9b94ba07d916fc8accd1646f51ec3ea9a0efe5427a530f37880edcfc381`

---

## 1. The one question this gate answers

> GT pose and EMG-predicted pose frequently receive **different top-1 classes** from the frozen DB9 LDA.
> But how similar are they in the DB9 **task-relevant continuous representation**?

Two mechanisms are distinguished:

| mechanism | meaning |
|---|---|
| **A. REPRESENTATION LOSS** | GT and Pred already differ substantially *in the task-relevant embedding*, so hard-class disagreement reflects genuine information loss |
| **B. BOUNDARY FRAGILITY** | GT and Pred remain close *in the task-relevant embedding*, but sit near LDA decision boundaries, so small continuous changes produce many argmax flips |

**Gate3B does not re-run, re-interpret or modify Gate3.** Gate3's hard-decision numbers are reused as
tertiary context and as a reproduction check. They are not re-analysed as a success/failure threshold
experiment, and Gate3's artifacts are never written to.

---

## 2. What is forbidden in this gate

* No training, fine-tuning, retraining or re-fitting of anything. The frozen head is loaded read-only.
* No change to the upstream checkpoint, context length, temporal alignment, trusted-8 mapping,
  sampling policy, validity mask or analysis population.
* No smoothing, filtering, denoising or resampling of any stream.
* No calibration fitting of any kind (probability, score, Fisher, per-component, per-stage, per-side).
* **No gate, `UNKNOWN`, abstention, rejection or reliability mechanism.**
* No human labels — no gesture annotations, no hand-coded postures, no visual grading.
* No sample filtering by class, margin, embedding similarity, pose error, stage, hand side or
  downstream output. The primary analysis is the **entire** Gate3 eligible population.
* **No DOF replacement / counterfactual intervention.** That is a later branch only.
* **No lag search.** All temporal comparisons are zero-lag.
* No selection of a subset of Fisher components after seeing outcomes.

---

## 3. Data — exact reuse of the Gate3 streams

Analysis input is the **exact** Gate3 aligned pair `(GT trusted-8 pose, Pred trusted-8 pose)` on the
Gate3 eligible population:

| item | value |
|---|---|
| Population | **86 833** samples |
| Rate | **50 Hz** (non-overlapping 40-row block mean of the 2 kHz aligned grid) |
| Participant / session | `d387095792` / `2022-12-06-1670313600-e3096-cv-emg-pose-train@2` |
| Sides | 15 left + 15 right recordings, 15 stages |
| GT source | `emg2pose/timeseries/joint_angles` (20-D, radians), trusted-8 `[2,3,5,6,9,13,17,18]` |
| Pred source | Gate3 persisted prediction stream (`gate3_work/pred_pose/*_pred.npz`), official `regression_vemg2pose` |
| Checkpoint | sha256 `748b1d1ef0ce1985f6fc07225d97eebfb370243429af803b4997d28ecce2424e` |
| Alignment | `prediction[i] ↔ GT[1790+i]`, exact timestamp array equality |
| Validity | GT-valid AND pred-valid full blocks; first block of each record excluded |

The predicted stream **was** persisted by Gate3, so **no new inference is run**. Population count and
identity are re-derived from source and must equal 86 833; if they differ by even one sample, this gate
**stops** rather than proceeding on a non-identical population.

**No new filtering is applied to this population.**

---

## 4. Frozen head and the Fisher space

The frozen object is `models/frozen_db9_trusted8_lda.joblib` from the Gate3 lane
(sha256 `b0ef8caf8e390a480fa2a3b448f79ccf14f75c71265ef925ee299a5e9e660386`), which reproduced the
frozen DB9 record **exactly (13/13 quantities)**.

Measured geometry of that object (probe performed before this plan was frozen; reads no data):

| property | value |
|---|---|
| solver / shrinkage | `svd` / `None` |
| classes | 1–8 |
| `n_features_in_` | 8 |
| `scalings_` shape | (8, 7) |
| **Fisher dimension** | **7** = `min(8, 8−1)` ✔ |
| `xbar_` | ≈ 0 (max abs 0.0) |
| `transform(x) == (x − xbar_) @ scalings_` | **True**, max abs diff **0.0** |
| `explained_variance_ratio_` | `[0.45635195, 0.29560768, 0.17173923, 0.06415877, 0.00904045, 0.0024689, 0.00063303]` (sum 1.0) |

**Centering.** `lda.transform` already subtracts `xbar_`, the DB9 training feature mean. We use it
**directly** and introduce **no emg2pose-specific centering**. Because `xbar_ ≈ 0`, the difference is
numerically negligible, but the rule is stated so that the choice is explicit rather than incidental.

**Do not select a subset of Fisher components.** All 7 produced by the frozen head are used.

---

## 5. Representation hierarchy

| level | space | role |
|---|---|---|
| **L0** | DB9-standardised trusted-8 pose `x = (pose − mu)/sd` | physical control — **not** a primary representation metric |
| **L1** | **Fisher discriminant embedding** `z = lda.transform(x)` (7-D) | **PRIMARY** |
| **L2** | centred 8-class affinity scores `s − mean(s)` | secondary |
| **L3** | native `predict_proba` | secondary (Gate3 metrics reused) |
| **L4** | argmax class | **tertiary** |

L1 is primary because it is supervised by DB9 posture labels (hence task-relevant), but it sits
**upstream of the final argmax**, does not collapse information into a class identity, and is not
directly dominated by arbitrary decision boundaries.

### L2 centering rule

Only the additive per-sample common mode is removed:

```
s_centered = s − mean_over_8_classes(s)
```

This is admissible because adding the same scalar to every class score changes no LDA relative
preference and no decision. **No other rescaling of score vectors is applied.**

### L0 standardisation

`x = (pose − mu) / sd` with `mu`, `sd` the **DB9** statistics stored in the frozen head. Never derived
from emg2pose.

---

## 6. DB9-only reference scales (declared rule; values reported as output)

Raw Fisher components have unequal scale, so distance must be normalised. **All normalisation is
derived exclusively from the frozen DB9 training corpus** — the identical protocol that fitted the
head (Exercise-B ids 1–8, `restimulus × rerepetition`, central 60 %, cap 200 via `np.linspace`,
`np.deg2rad`, DB9 z-score, all 77 participants, 123 200 frames).

```
z_DB9[:, j]        = lda.transform(DB9_standardised_pose)[:, j]
sigma_DB9_j        = std(z_DB9[:, j])          (population std, ddof = 0)

d_norm = sqrt( sum_j ( (z_PRED_j − z_GT_j) / sigma_DB9_j )^2 )
```

For the score space, the reference is the per-score std of the **DB9** centred-score matrix:

```
s_DB9_centered = s_DB9 − mean_over_classes(s_DB9)
tau_DB9_k      = std(s_DB9_centered[:, k])     (ddof = 0)

score_dist_norm = sqrt( sum_k ( (s_PRED_k − s_GT_k) / tau_DB9_k )^2 )
```

**Forbidden:** deriving any normalisation from emg2pose GT or Pred distributions. The DB9 statistics
depend only on DB9 and are inspectable in `artifacts/FISHER_DB9_REFERENCE_SCALE.json`; they carry no
emg2pose outcome information. A consistency check must confirm the rebuilt DB9 corpus reproduces the
frozen head's `mu`, `sd` and 123 200-frame count exactly.

---

## 7. PRIMARY — Fisher-space metrics

### 7.1 Per-frame Fisher cosine

```
cos_t = <z_GT,t , z_PRED,t> / (||z_GT,t|| ||z_PRED,t||)
```

**Numerical epsilon rule (declared now): `EPS = 1e-12`.** A frame is counted as a **valid cosine
frame** iff `||z_GT,t|| > EPS` **and** `||z_PRED,t|| > EPS`. Frames failing this are **counted and
reported**, excluded from cosine statistics, and are **never** silently assigned `cos = 1`.

Report: `n_valid_cosine_frames`, and the median / mean / IQR (p25–p75) / p05 / p25 / p75 / p95 /
min / max, plus the fraction `< 0`, `> 0.5`, `> 0.8`, `> 0.9`.
These threshold fractions are **descriptive only** and are **not** called PASS/FAIL.

### 7.2 DB9-normalised Fisher distance

Per §6. Report median / mean / IQR / p05 / p95, plus the **raw Euclidean** Fisher distance
(`||z_PRED − z_GT||`, no scaling) for transparency, and the per-component DB9 sigmas.

### 7.3 Fisher component preservation

For each of the 7 components, comparing `z_GT[:,j]` with `z_PRED[:,j]`:
Pearson r, Spearman ρ, MAE, RMSE, and descriptive OLS slope/intercept of `z_PRED ~ z_GT`.
The OLS fit is **descriptive only** and is **never** used to calibrate or transform predictions.

---

## 8. Discriminative importance of components

`explained_variance_ratio_` is taken verbatim from the frozen LDA (§4). **No component importance is
estimated from emg2pose outcomes.**

Per component, report: DB9 variance weight, GT↔Pred Pearson r, GT↔Pred standardised error.

One fixed summary is computed **only if all 7 weights are available from the frozen object** (they are):

```
DB9_WEIGHTED_COMPONENT_CORRELATION = sum_j ( w_j * Pearson_r_j ),
        w_j = explained_variance_ratio_j / sum_l explained_variance_ratio_l
```

Weights are **not** redefined, renormalised differently, or chosen from outcomes.

---

## 9. Class-score space metrics

On the centred 8-D score vectors of §5, per frame:

* **A** cosine similarity
* **B** Pearson correlation across the 8 relative scores (reported only where numerically valid —
  i.e. both vectors must have non-zero variance; the valid count is reported)
* **C** DB9-normalised L2 difference (§6), plus raw Euclidean for transparency

Report median / IQR / p05 / p95 for each.

---

## 10. Representation versus hard-class flip

Samples are split **for description only**:

* **GROUP SAME** — `Y_GT == Y_PRED`
* **GROUP FLIP** — `Y_GT != Y_PRED`

For each group report median / IQR of: Fisher cosine, DB9-normalised Fisher distance, score-space
cosine, TV, JS, and pose MAE / RMSE (degrees).

**No classifier is fitted to predict flips.** The diagnostic reading:

* flips with **high** continuous similarity ⇒ supports **boundary fragility**;
* flips with **already-low** Fisher similarity ⇒ supports **genuine representation loss**.

Both groups are reported in full; the SAME-group statistics are never used to redefine the population.

---

## 11. Similarity → hard agreement curve

**No "good similarity threshold" is chosen.** Two independent descriptive views:

1. rank all samples by **DB9-normalised Fisher distance** → 10 equal-count deciles → per decile:
   median Fisher distance, median Fisher cosine, hard agreement, balanced preservation (computed only
   over Y_GT classes with support ≥ 30 **within that decile**; reported as `None` if fewer than two
   such classes exist), median pose error;
2. rank all samples by **Fisher cosine** (descending) → 10 equal-count deciles → hard agreement.

Deciles are formed by a stable ascending sort; tie handling is deterministic. No cutoff is optimised.

---

## 12. Pose error → Fisher error → hard flip

Descriptive only, zero-lag, no causal claim:

* **A** per-frame trusted-8 pose RMSE (degrees) vs DB9-normalised Fisher distance — Spearman ρ
* **B** DB9-normalised Fisher distance vs hard-flip indicator — Spearman ρ, and the SAME/FLIP medians
  of §10
* **C** per-frame trusted-8 pose RMSE vs hard-flip indicator — Gate3's existing value
  (ρ ≈ +0.162) is quoted for comparison and **not recomputed as a new result**

**No causal claims.** Frame-level p-values are not presented: one participant, temporally correlated
frames. All rank statistics are labelled descriptive.

---

## 13. Counterfactual interventions — explicitly NOT run

No DOF replacement, no GT/Pred mixing, no partial-substitution experiment. Gate3B only establishes
**whether representation loss exists**. A frozen per-DOF counterfactual sensitivity analysis is a
**later** branch, and only if Fisher representation itself is shown to be meaningfully degraded.

---

## 14. Temporal representation preservation

Per Fisher component, on the **already-assembled** sample sequence (equal weighting, no subsampling):

* **zero-lag** Pearson r between `z_GT[:,j]` and `z_PRED[:,j]`;
* **zero-lag** Spearman ρ;
* frame-to-frame **derivative** correlation, computed **only within continuous record boundaries**:

```
Δz_GT[t]   = z_GT[t]   − z_GT[t−1]
Δz_PRED[t] = z_PRED[t] − z_PRED[t−1]
```

Transitions are dropped wherever the two frames do not belong to the same contiguous valid block
sequence (i.e. at record and gap boundaries). The count of retained derivative pairs is reported.

**No lag optimisation of any kind.** This addresses the Gate3 observation that the predicted pose
stream appears temporally over-smoothed (switch rate 0.0200 vs 0.0773 per sample; median dwell 12 vs 6
frames).

---

## 15. Side and stage stratification (secondary, descriptive)

For **LEFT** and **RIGHT** separately: n, median Fisher cosine, median DB9-normalised Fisher distance,
median score-space cosine, hard agreement.

For each activity **stage**: the same quantities.

**Stage is an activity label and NOT posture ground truth.** No stage-specific normalisation, no
stage-specific tuning, no semantic stage claim. Side and stage counts must each sum to 86 833.

---

## 16. Representational CKA (secondary, optional)

If straightforward and memory-safe: **linear CKA** between the full eligible `Z_GT` and `Z_PRED`
matrices (86 833 × 7).

**Deterministic subsample rule, declared now, in case memory requires one:** if the full computation is
not feasible, use the **first 40 000 eligible samples in frozen population order** (no shuffling, no
random seed, no outcome dependence). The actual path taken (full or subsampled) must be stated in the
artifact.

CKA is **secondary**: it is more invariant than direct substitution requires (it ignores rotation and
isotropic scaling), so a high CKA **must not** override poor per-frame preservation. If not computed,
report `NOT_RUN`.

---

## 17. Mechanism decision frame — descriptive, no arbitrary thresholds

No PASS/FAIL thresholds are defined. At most one of the following labels is emitted, and **only if
clearly supported by the joint evidence**; otherwise `MIXED_OR_AMBIGUOUS`:

| label | reading |
|---|---|
| `REPRESENTATION_LARGELY_PRESERVED_BOUNDARY_FRAGILE` | continuous representation clearly close while hard agreement is low |
| `REPRESENTATION_PARTIALLY_PRESERVED` | intermediate: real but incomplete representation degradation |
| `REPRESENTATION_SUBSTANTIALLY_DEGRADED` | continuous representation itself clearly badly damaged |
| `MIXED_OR_AMBIGUOUS` | evidence does not separate the mechanisms |

The decision must **jointly** consider Fisher cosine, DB9-normalised Fisher distance, component
preservation, score-space preservation, probability-space preservation and hard agreement.
**Hard agreement alone must never drive the label.**

Decision labels are qualitative readings of the reported profile, not thresholds. The reported numbers
are the primary deliverable; the label is a convenience summary and is clearly marked as such.

---

## 18. Claim boundary

Gate3B may support: *"task-relevant continuous representation is more strongly preserved than final
discrete class identity"*, or *"upstream substitution substantially distorts the task-relevant Fisher
representation, so low hard agreement is not merely a decision-boundary artefact"*.

Gate3B **cannot** establish: true emg2pose gesture accuracy; semantic correctness of DB9 classes on
natural poses; cross-user generalization; universal Common Pose validity; any reliability guarantee.
No human labels are used. Both routes remain inside the same emg2pose coordinate system, and the
Gate1.5 cross-source numerical calibration gap remains unresolved.

---

## 19. Firewall assertions (must all hold)

```
NEW_INFERENCE_RUN          = NO
MODEL_RETRAINED            = NO
CALIBRATION_FITTED         = NO
SMOOTHING_APPLIED          = NO
GATE_CREATED               = NO
UNKNOWN_CLASS              = NO
HUMAN_LABELS_USED          = NO
LAG_SEARCH_PERFORMED       = NO
DOF_INTERVENTION_PERFORMED = NO
SAMPLE_FILTERING_APPLIED   = NO
COMPONENT_SELECTION_ON_OUTCOME = NO
POPULATION_CHANGED         = NO
GATE3_ARTIFACTS_MODIFIED   = NO
SCALING_FROM_EMG2POSE      = NO
```

---

## 20. Outputs

```
GATE3B_PLAN.md / GATE3B_PLAN.sha256
README.md
artifacts/GATE3B_DATA_LINK.json
artifacts/FISHER_DB9_REFERENCE_SCALE.json
artifacts/FISHER_PRESERVATION_SUMMARY.json
artifacts/FISHER_COMPONENT_PRESERVATION.csv
artifacts/SCORE_SPACE_PRESERVATION.json
artifacts/REPRESENTATION_BY_HARD_OUTCOME.csv
artifacts/FISHER_DISTANCE_DECILES.csv
artifacts/FISHER_COSINE_DECILES.csv
artifacts/REPRESENTATION_BY_SIDE.csv
artifacts/REPRESENTATION_BY_STAGE.csv
artifacts/POSE_TO_FISHER_RELATION.json
artifacts/TEMPORAL_FISHER_PRESERVATION.csv
artifacts/GATE3B_DECISION.json
artifacts/REPRESENTATIONAL_CKA.json          (optional)
scripts/run_gate3b_representation.py
scripts/verify_gate3b.py
logs/gate3b_stdout.txt
logs/gate3b_verify_stdout.txt
```

No Gate3 artifact is modified.

## 21. Reproduce

```bash
/root/miniconda3/envs/emg2pose-gate3/bin/python -X utf8 scripts/run_gate3b_representation.py
/root/miniconda3/envs/emg2pose-gate3/bin/python -X utf8 scripts/verify_gate3b.py
```

## 22. Next phase — NOT executed here

No reliability gate is designed in this gate. Gate3B exists to answer whether task-relevant continuous
information was actually lost or merely a brittle boundary was crossed. Only after that answer should
a reliability-gate design be chosen.
