# PHASE 1 / GATE 4A — SINGLE-USER RELIABILITY-SCORE FEASIBILITY SCREEN

**Evidence level: SINGLE-USER FEASIBILITY SCREEN ONLY.**
**This is NOT a formal gate. NOT conformal validation. NOT threshold selection.**
**NOT a downstream classifier experiment. NOT a class-accuracy experiment.**

---

## Question

At deployment we do not see GT. Can a score `u_t`, computed only from deployment-visible
information (the EMG stream and the official upstream prediction stream), **rank** the true
task-relevant representation error `r_t`?

```
deployment:   EMG ─► official emg2pose estimator ─► Pred pose ─► u_t      (GT never used)
research:     r_t = DB9-normalised Fisher displacement between z_PRED and z_GT
      goal:   u_t large  ⟹  r_t large
```

`r_t` is used only to fit the exploratory task-error predictor and to evaluate candidate
scores. It is never a deployment feature, never enters TTA inference, never selects a
perturbation, and never enters the temporal baseline.

---

## Data (frozen, unchanged from Gate3 / Gate3B)

| item | value |
|---|---|
| population | **86 833** samples, 50 Hz |
| participant / session | `d387095792` / `2022-12-06-1670313600-e3096-cv-emg-pose-train@2` |
| records | 30 (15 left + 15 right), 15 stages |
| Pred source | frozen Gate3 stream `/root/work/gate3_work/pred_pose/*_pred.npz` |
| GT source | `/root/data/emg2pose_dataset_mini/*.hdf5` → `emg2pose/timeseries/joint_angles` |
| frozen head | `frozen_db9_trusted8_lda.joblib` sha256 `b0ef8caf…` |
| checkpoint | `regression_vemg2pose.ckpt` sha256 `748b1d1e…` |
| alignment | `prediction[i] ↔ GT[1790+i]`, exact timestamp equality asserted per record |
| filtering | NONE beyond the frozen Gate3 eligibility rule |

---

## Target

```
x   = (pose − mu_DB9) / sd_DB9                (trusted-8 [2,3,5,6,9,13,17,18])
z   = lda.transform(x)                         (7-D frozen Fisher embedding)
r_t = sqrt( sum_j ( (z_PRED,t,j − z_GT,t,j) / sigma_DB9,j )^2 )
```

`sigma_DB9` is DB9-only (77 participants, 123 200 frames). Reproduction of the Gate3B record is
asserted to 1e-9 before anything else runs.

---

## Candidates

| id | score | deployment-visible input |
|---|---|---|
| 0 | `u_TEMP` = DB9-normalised within-record Fisher volatility | `z_PRED` |
| 1 | `u_TTA` = DB9-normalised dispersion across the frozen electrode-band TTA views | EMG → frozen model |
| 2 | `u_ERR` = stage-grouped OOF `GradientBoostingRegressor(loss="quantile", alpha=0.90)` | predicted pose/Fisher + causal differences + hand side |

TTA transform set (frozen from official code): `k ∈ {0, +1, −1}` electrode-band shift, i.e. exactly
the support of the official `emg2pose.transforms.RotationAugmentation` used to train this
checkpoint. `k = 0` must reproduce the frozen Gate3 stream **bit-exactly**.

---

## Findings

See `artifacts/GATE4A_DECISION.json` for the machine-readable summary and
`logs/gate4a_verify_stdout.txt` for the independent verification.

**No threshold is selected and no gate is chosen in this lane.**

---

## Reproduce

```bash
ENV=/root/miniconda3/envs/emg2pose-gate3
$ENV/bin/python -X utf8 scripts/audit_tta_transforms.py
$ENV/bin/python -X utf8 scripts/run_tta_inference.py
$ENV/bin/python -X utf8 scripts/run_task_error_predictor.py
$ENV/bin/python -X utf8 scripts/build_reliability_scores.py
$ENV/bin/python -X utf8 scripts/evaluate_gate_scores.py
$ENV/bin/python -X utf8 scripts/verify_gate4a.py
```

## Claim boundary

**May support:** "on one participant/session, a deployment-visible score of type X shows (no)
useful ranking information about true task-relevant Fisher representation error."

**Cannot establish:** cross-user reliability, calibration, a conformal guarantee, a deployment-ready
threshold, a population-level effect, or scientific superiority of any gate.

## Runtime

The frozen 3-view TTA round (30 records × 3 views = 90 views) runs in about a minute; see
`artifacts/TTA_SCORE_SUMMARY.json` → `runtime_documentation`. Performance optimization was
explicitly out of scope.

## History

* Last allowed step of Gate3B: decide the reliability-gate direction. **No gate is designed there.**
* Gate4A is a **feasibility screen**, not a gate. It can eliminate candidates early; it cannot
  select one.
