# NEXT POC EXPERIMENT — PLAN ONLY, NOT EXECUTED

**Branch that produced this plan:** `S6-POSE-API-DATASET-ADMISSION`  
**Frozen plan SHA-256:** `4d2c8b162e2332a5891a5d89a53166e365b1bbd92c205222492d19957c9683ec`  
**Status:** **DESIGN ONLY.** No model was trained, no pose was scored, no threshold was fitted in the session that wrote this file.

---

## 0. What this experiment would test, in one sentence

> Can a task model learned **entirely from an independent kinematic dataset** — using pose alone, with **no task-specific EMG** — be applied to frozen emg2pose GT hand poses through a shared physical representation, and produce a task output that is better than chance and honestly abstains where it should?

This is the first half of the long-term architecture:

```
KIN-MUS UJI  (pose + pose-defined label)
      |  shared10_poc_v1  (radians)
      v
frozen task model
      |
      v
emg2pose GT pose  --same shared10_poc_v1-->  external task output
```

**No emg2pose EMG is used to build the model.** The model never sees EMG.
The downstream EMG->pose head is a *later*, separate experiment and is out of scope here.

---

## 1. The exact common representation

**`shared10_poc_v1` — 10 DOF, all HIGH confidence.**

| # | API DOF | KIN-MUS column | source index |
|---|---|---|---|
| 1 | `thumb_cmc_flexion` | `CMC1_F` | 0 |
| 2 | `thumb_mcp_flexion` | `MCP1_F` | 2 |
| 3 | `index_mcp_flexion` | `MCP2_F` | 4 |
| 4 | `index_pip_flexion` | `PIP2_F` | 6 |
| 5 | `middle_mcp_flexion` | `MCP3_F` | 7 |
| 6 | `middle_pip_flexion` | `PIP3_F` | 8 |
| 7 | `ring_mcp_flexion` | `MCP4_F` | 9 |
| 8 | `ring_pip_flexion` | `PIP4_F` | 11 |
| 9 | `pinky_mcp_flexion` | `MCP5_F` | 13 |
| 10 | `pinky_pip_flexion` | `PIP5_F` | 15 |

**The ONLY transform applied is degrees → radians.** No offset, no scale, no fitted affine, no sign choice made on any outcome. This is admissible under the frozen plan's `DOCUMENTED_TRANSFORM` class.

**Why not more DOFs.** `thumb_cmc_ab_adduction` and `thumb_ip_flexion` are MEDIUM and are excluded on purpose; the four DIP axes do not exist in the data as measurements. A 12-D or 16-D version would look better on a coverage table and be worse on physical trustworthiness — the plan's principal rule forbids preferring count over semantic equivalence.

---

## 2. Exact source labels

**Primary label: the movement phase** — `Phase ∈ {1 reaching, 2 manipulation, 3 release}`.

Why this and not the 26 ADL identities:

* the phase label **is** pose-observable. In the released data the pooled MCP+PIP flexion sum in manipulation exceeds reaching in **22/22 subjects** (median **+66.44°**). The signal exists in pose alone, before any model is fitted.
* the 26 ADL labels are goal- and object-defined ("open a container"). They are **not** pose-sufficient and are classified `NOT-POSE-SUFFICIENT` under the frozen plan. They are **out of scope for the first POC**.

**Task form for v1: a 3-class phase classifier over a single frame or a short local window**, learned on KIN-MUS and applied to emg2pose GT poses.
The single-frame form is tried FIRST because a frame-level model needs no temporal alignment between datasets.

---

## 3. Exact source subject split

* 22 subjects, IDs 1..22 in the released struct.
* Split by **subject**, never by row: development = 11 subjects, held-out = 11 subjects.
* The split is frozen **by subject id** before any fitting and is recorded in the run manifest. Subject identity is the archive `Subject` field, which is the dataset's own identity authority.
* **Cells that must be excluded and reported:** the three empty trials (subject 21 ADL 25 phase 1; subject 22 ADL 25 phases 2 and 3) and the two duplicated cells (subject 22 ADL 25 phases 2 and 3). These are removed, counted, and never repaired.

---

## 4. Simple baseline classifier — the minimum, not a search

Exactly two models, both classical, both frozen before scoring:

1. **Shrinkage LDA** on the 10-D feature vector, `solver='lsqr'`, `shrinkage='auto'`, train-only z-scoring — the project's own frozen closed-set baseline configuration, reused verbatim for comparability.
2. **Nearest-class-centroid with a distance reject option**, calibrated on the development subjects only, at a fixed operating point.

**Explicitly NOT run:** any deep network, any AutoML, any Gaussian/SIMCA/GMM/OCSVM model search, any Gate architecture, kNN, conformal prediction, OpenMax, PROSER, energy-based OSR or prototype OSR. Those belong to the separate Gate problem and the frozen plan forbids them here.

---

## 5. UNKNOWN / reject strategy

The phase label is a **partition** (every frame has one phase), so in-distribution there is no UNKNOWN. The reject option is needed only on the **external** side, where emg2pose poses may fall outside the source manifold. The strategy:

* fit a per-phase Gaussian support region on the development subjects at a **95 % per-class coverage** point calibrated by subject-grouped leave-one-subject-out — the same calibration discipline as the frozen DB9 branch, reused for comparability;
* a frame accepted by **zero** phase regions is reported as `OUTSIDE`; by **more than one** as `AMBIGUOUS`;
* **`OUTSIDE` and `AMBIGUOUS` are reported rates, not errors to be minimised**, and neither may be resolved by a tie-break in the primary report.
* The calibrated reject option and the primary classifier are **two separate components**; the reject threshold is NOT tuned on any external result.

---

## 6. Target external population

* **Pose source:** `bridge_audit/results/sessions/*.paired50hz.npz :: gt16`, the frozen GT canonical16 corpus — 30 sessions, 86858 valid rows.
* **Eligibility:** `gt_valid == True` (IK failures are all-zero rows and MUST be masked; they are not neutral poses).
* **Projection:** the same 10 named DOFs, converted to radians, in the same order.
* **NO new inference**, NO VEMG2Pose predicted pose, NO new emg2pose sampling, NO human labels.
* **Scope caveat carried into every number:** the mini corpus is ONE subject over 30 sessions. Every external result is **within-subject** and no cross-subject external claim may be made from it.

---

## 7. Evaluation metrics

**Source-internal (held-out 11 subjects), the control:**

* closed-set accuracy and balanced accuracy for the 3-phase task;
* per-class recall; the confusion matrix;
* the coverage actually achieved by the 95 % calibration point.

**External (emg2pose GT poses), the actual question:**

* the distribution over `{reaching, manipulation, release, AMBIGUOUS, OUTSIDE}`;
* the **manipulation share** as the primary scalar, with a session-level bootstrap interval;
* the same statistic computed on a **pose-null control** (see §9).

**Reporting rule.** A high `OUTSIDE` rate is a legitimate result and may not be suppressed. A higher manipulation share is not automatically better — it is only meaningful against the pose-null control.

---

## 8. What would count as success, and what would count as failure

**SUCCESS (all three):**

1. the source-internal held-out task is well above chance (balanced accuracy materially above 1/3) — the source task exists;
2. the external manipulation share is **higher than the pose-null control by a margin that survives the session-level bootstrap**, on the majority of the 30 sessions;
3. the `OUTSIDE` rate is reported and is not total — the source manifold actually overlaps emg2pose's natural pose cloud.

**FAILURE (any one is decisive):**

* the source-internal task itself is near chance — the label is not in the pose at all and the whole line of work stops here;
* the external share is indistinguishable from the pose-null control — the model is reading the emg2pose pose distribution, not the source task;
* `OUTSIDE` is essentially 100 % — the same outside-support failure that closed DB9, and it would mean the shared representation does not span the two datasets even when the physical mapping is clean.

**A negative result is a publishable result here.** The architecture claim is untested; this experiment exists to test it, not to confirm it.

---

## 9. The pose-null control (mandatory, and the reason it exists)

The DB9 branch's hardest lesson was that a lower rejection rate can mean *the model accepts garbage*. The analogous trap here: a model trained on a task whose classes differ in overall flexion will report 'manipulation' on any strongly flexed pose, which natural emg2pose poses contain for reasons unrelated to this source task.

**Control:** refit the identical pipeline on KIN-MUS with the phase label **permuted across trials within each subject**, so the flexion magnitude distribution is preserved but the label is destroyed. Score the same external poses. The difference between the real and permuted external manipulation shares is the *only* quantity that can support a positive claim.

If real ≈ permuted, the result is **negative**, regardless of how high the internal accuracy was.

---

## 10. What this experiment still could NOT prove

* It cannot show the API works end-to-end: **no EMG is involved at all**. That is deliberate — this is the pose half only.
* It cannot make a cross-subject external claim: one emg2pose subject.
* It cannot establish that KIN-MUS's absolute physical coordinates are correct — only that they are *internally consistent and portable enough to transfer*. The metrological gap between a calibrated strain-gauge glove and an IK fit over motion capture is not closed by a successful transfer.
* It cannot generalise beyond the 10 shared DOF or the 3-phase task.

---

## 11. Prerequisites before the experiment is run

1. **Confirm handedness of the released KIN-MUS block.** The file is one hand of 18 columns and does not label which. If it is the LEFT hand while emg2pose GT includes both, a documented mirroring step is required — and it must be documented, not fitted.
2. **Re-run the anchor and quality builders on KINE-ADL BE-UJI** if a second corpus is wanted for the task-generalisation arm. KINE-ADL is NOT independent physical evidence; it is a second task ontology.
3. **Decide the `OUTSIDE` reporting denominator** — per session or pooled — before scoring, since the two give different intervals.
4. **Nothing else.** No new data, no new annotation, no new inference.

*Source API definition recovered from `representation/canonical_hand.py`; nothing in this plan was reconstructed from memory.*
