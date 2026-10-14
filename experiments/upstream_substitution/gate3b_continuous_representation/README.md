# PHASE 1 / GATE 3B — CONTINUOUS DOWNSTREAM REPRESENTATION PRESERVATION

**Evidence status: POST-HOC MOTIVATED, PROSPECTIVELY FROZEN BEFORE CONTINUOUS-REPRESENTATION
OUTCOME INSPECTION.** Gate3B was motivated by the Gate3 hard-decision result, so it was **not**
preregistered before Gate3. It was frozen before any Fisher/score-space similarity value was computed.

---

## Question

> Gate3's frozen DB9 LDA assigns GT pose and EMG-predicted pose **different top-1 classes** most of the
> time. But how similar are they in the DB9 **task-relevant continuous representation**?

Two mechanisms are separated:

| | |
|---|---|
| **A. REPRESENTATION LOSS** | GT and Pred already differ *in the task-relevant embedding*, so hard disagreement reflects real information loss |
| **B. BOUNDARY FRAGILITY** | GT and Pred stay *close in the embedding* but sit near LDA decision boundaries, so small continuous changes cause many argmax flips |

Gate3 is **not** modified, re-run, or reinterpreted. Its hard-decision numbers are reused as tertiary
context and as a reproduction check.

---

## Representation hierarchy

| level | space | role |
|---|---|---|
| **L0** | DB9-standardised trusted-8 pose `(pose − mu)/sd` | physical control |
| **L1** | **Fisher discriminant embedding** `z = lda.transform(x)`, **7-D** | **PRIMARY** |
| **L2** | centred 8-class affinity scores | secondary |
| **L3** | native `predict_proba` | secondary |
| **L4** | argmax class | **tertiary** |

L1 is primary because it is supervised by DB9 posture labels, sits **upstream of the argmax**, and is
not dominated by an arbitrary decision boundary.

### Frozen head geometry (measured)

| property | value |
|---|---|
| solver / shrinkage | `svd` / `None` |
| `scalings_` | (8, 7) → **Fisher dimension 7** = `min(8, 8−1)` |
| `xbar_` | ≈ 0; `transform(x) == (x − xbar_) @ scalings_` verified, max abs diff 0.0 |
| `explained_variance_ratio_` | `[0.456352, 0.295608, 0.171739, 0.064159, 0.009040, 0.002469, 0.000633]`, sum 1.0 |

All 7 components are used. No component is selected after seeing outcomes.

---

## Normalisation — DB9 only

Raw Fisher components have unequal scale. **Every** normalisation constant is derived from the frozen
**DB9** training corpus (123 200 frames, 77 participants), never from emg2pose GT or Pred:

```
sigma_DB9_j  = std( lda.transform(DB9_standardised_pose)[:, j] )        (ddof = 0)
d_norm       = sqrt( sum_j ( (z_PRED_j − z_GT_j) / sigma_DB9_j )^2 )
```

Score space uses the head's own 8-class log-likelihood geometry
(`score_k = −0.5·Mahalanobis_k + log prior_k`; sklearn's `decision_function` exposes only 7 columns),
scaled by the DB9 per-class score sigmas. DB9 corpus reconstruction is checked against the frozen
head's `mu`, `sd` and frame count before any scale is trusted.

---

## Data

The **exact** Gate3 eligible population: **86 833** samples at **50 Hz**, 1 participant
(`d387095792`), 1 session, 15 L + 15 R recordings, alignment `prediction[i] ↔ GT[1790+i]` verified by
exact timestamp-array equality. The Gate3 predicted stream was persisted, so **no new inference was
run**. If reconstruction yields any count other than 86 833, the gate stops.

**No filtering** by class, margin, similarity, pose error, stage, side or downstream output.

---

## Analyses

Per-frame Fisher cosine (with a declared `EPS = 1e-12` norm rule — invalid frames are counted and
reported, never silently set to 1) · DB9-normalised and raw Fisher distance · per-component Pearson /
Spearman / MAE / RMSE / descriptive OLS · DB9-weighted component correlation · centred score-space
cosine, row-Pearson and DB9-normalised distance · **SAME vs FLIP** group statistics ·
similarity→agreement decile curves (distance-ranked and cosine-ranked) · pose→Fisher→flip descriptive
rank relationships · zero-lag temporal and **within-record derivative** correlations · LEFT / RIGHT and
stage stratification · linear CKA (secondary).

---

## Firewall

```
NEW_INFERENCE_RUN = NO     MODEL_RETRAINED = NO       CALIBRATION_FITTED = NO
SMOOTHING_APPLIED = NO     GATE_CREATED = NO          UNKNOWN_CLASS = NO
HUMAN_LABELS_USED = NO     LAG_SEARCH_PERFORMED = NO  DOF_INTERVENTION_PERFORMED = NO
SAMPLE_FILTERING_APPLIED = NO                         POPULATION_CHANGED = NO
GATE3_ARTIFACTS_MODIFIED = NO                         SCALING_FROM_EMG2POSE = NO
```

No DOF-replacement counterfactual is run here. That is a later branch, and only if the Fisher
representation itself is shown to be meaningfully degraded.

---

## Claim boundary

**May support:** "task-relevant continuous representation is more strongly preserved than final
discrete class identity", or "upstream substitution substantially distorts the task-relevant Fisher
representation, so low hard agreement is not merely a decision-boundary artefact".

**Cannot establish:** true emg2pose gesture accuracy; semantic correctness of DB9 classes on natural
poses; cross-user generalization; universal Common Pose validity. No human labels are used. The
Gate1.5 cross-source numerical calibration gap remains unresolved.

## Next allowed step

Decide the reliability-gate direction from the mechanism reading. **No gate is designed in this gate.**
