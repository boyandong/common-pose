# PHASE 1 / GATE 3 — FORMAL UPSTREAM SUBSTITUTION BASELINE

**Question.**

> When emg2pose ground-truth pose is replaced by pose predicted from the **same EMG** by the
> independent **official** emg2pose pose estimator, how much of the frozen downstream DB9-head
> behaviour is preserved, **without any task-specific downstream retraining**?

This is the **unconditional substitution baseline**. There is no reliability gate, no probability
cloud, no `UNKNOWN`, no rejection and no abstention in this gate — every eligible sample enters both
routes. The gate is a later, separately designed experiment.

---

## Design in one picture

```
ROUTE A — ORACLE / IDEAL UPSTREAM
  emg2pose GT 20-D pose ──► trusted-8 [2,3,5,6,9,13,17,18] ──► DB9 frozen z-score ──► frozen DB9 LDA ──► Y_GT

ROUTE B — SUBSTITUTED UPSTREAM
  same emg2pose EMG (16 ch, 2 kHz)
        └─► official regression_vemg2pose estimator ─► predicted 20-D pose
              └─► same trusted-8 ─► same DB9 frozen z-score ─► same frozen DB9 LDA ──► Y_PRED

COMPARE: Y_GT  vs  Y_PRED          (NO human gesture labels)
```

`Y_GT` is the **reference behaviour**. It is **not** semantic ground truth.
The measured quantity is **functional preservation**, not semantic correctness.

---

## Frozen objects (all verified before use)

| object | value |
|---|---|
| Representation | `TRUSTED_DB9_POSE_v1`, SHA-256 `e51dde6e…5782d1` |
| Downstream head | `LinearDiscriminantAnalysis()` all defaults, trained on all **77** DB9 participants |
| Head protocol | DB9 Exercise-B ids 1–8, `restimulus × rerepetition`, central 60 %, cap 200 via `np.linspace`, `np.deg2rad`, DB9 training z-score |
| Head reproduction | **EXACT** — 13/13 frozen quantities from `FINAL_VALIDATION.json .Q4_posture8` |
| Upstream estimator | official `regression_vemg2pose` (EMG-only regression) |
| Checkpoint | `regression_vemg2pose.ckpt`, SHA-256 `748b1d1e…424e` |
| Official repo | `facebookresearch/emg2pose` @ `5f6f62b1a0a08426adffe55900842e75a8adb38c` |
| Cohort | **1 participant** (`d387095792`), **1 session**, 30 recordings, 15 L + 15 R, 15 stages |

---

## Alignment (deterministic, not searched)

Official `emg2pose/pose_modules.py :: BasePoseModule.forward` gives `left_context = 1790`,
`right_context = 0`, predictions spanning `EMG[1790 : T]`, upsampled to the 2 kHz input grid — the
same grid as the stored GT `joint_angles`. Therefore

```
prediction[i]  ↔  GT[1790 + i]
```

verified per record by `np.array_equal(GT.time[1790:], prediction.time)`.
**No** cross-correlation or lag search was used, and no alignment decision depends on downstream output.

---

## Analysis policy

* 2 kHz aligned grid → non-overlapping **40-row block mean** → **50 Hz** analysis cadence (the frozen
  Gate2A policy, reused unchanged); trailing `< 40` remainder dropped.
* Row validity: **not** all-20-dimensions-≈-zero (official IK-failure semantics) **and** finite.
* Primary population: blocks valid in **both** routes, both sides, all stages, minus the **first block
  of each record** (the decoder's zero-initialised rollout transient — a rule fixed by published model
  semantics, applied identically to both routes, decided before any output).
* No sample is ever removed on the basis of downstream output.

---

## Outcomes

Primary: hard **downstream agreement**, **balanced preservation** over classes with Y_GT support ≥ 30,
**Cohen's κ**, and the 8×8 **DOWNSTREAM PRESERVATION MATRIX** (raw + row-normalised; *not* a semantic
confusion matrix).

Secondary: soft-output preservation (TV, Jensen–Shannon, `P_PRED[Y_GT]`), temporal preservation
(switch rate, dwell, ±1-frame transition-event match), pose-level error in **degrees** per trusted DOF,
and the **error → functional-failure curve** over pre-declared deciles of per-frame trust-8 RMSE.
Stratifications by class (1–8), hand side and activity stage.

**No binary success threshold and no categorical verdict** are emitted: none existed before this
experiment, so the deliverable is the observed **preservation profile**.

---

## Firewall

```
GATE_CREATED = NO            UNKNOWN_CLASS = NO          ABSTENTION = NO
REJECTION = NO               HUMAN_LABELS_USED = NO      CALIBRATION_FITTED = NO
TASK_SPECIFIC_RETRAINING = NO  UPSTREAM_RETRAINING = NO  SMOOTHING_APPLIED = NO
CHECKPOINT_SELECTED_ON_DOWNSTREAM_PERFORMANCE = NO
ALIGNMENT_OPTIMIZED_ON_OUTCOME = NO
SAMPLE_SELECTION_ON_DOWNSTREAM_OUTPUT = NO
SEMANTIC_ACCURACY_CLAIMED = NO
HISTORICAL_0.7646_USED_FOR_DESIGN = NO
```

The historical ≈0.7646 GT-vs-PRED agreement belongs to a **different** pipeline
(`experiments/bridge/SESSION5_BRIDGE_AUDIT_REPORT.md`: 4-DOF decoder, central-60 % windows, different
head). It was **inaccessible for the design** of this gate — not used for thresholds, alignment,
checkpoint selection, smoothing, sample selection or pass/fail.

---

## Layout

```
GATE3_PLAN.md / GATE3_PLAN.sha256    frozen plan, hashed before any outcome was computed
README.md
artifacts/                           all published machine-readable results
scripts/run_gate3_substitution.py    the analysis
scripts/verify_gate3.py              independent recomputation + firewall assertions
logs/gate3_stdout.txt                captured run log
logs/inference_stdout.txt            captured upstream inference log
models/frozen_db9_trusted8_lda.joblib   serialized frozen head (after EXACT reproduction)
```

## Reproduce

```bash
/root/miniconda3/envs/emg2pose-gate3/bin/python -X utf8 run_emg2pose_inference.py
/root/miniconda3/envs/emg2pose-gate3/bin/python -X utf8 scripts/run_gate3_substitution.py
/root/miniconda3/envs/emg2pose-gate3/bin/python -X utf8 scripts/verify_gate3.py
```

---

## Limitations (standing)

* **Single participant, single session** — a single-user proof of concept. No cross-user claim.
* **No semantic gesture ground truth** — this gate structurally cannot and does not measure posture or
  gesture accuracy; it measures agreement with the oracle-route output.
* **Cross-source numerical calibration is unresolved** (Gate 1.5 → `NO_INDEPENDENT_ANCHOR`,
  `ZERO_GATE = NOT_EVALUABLE_LOCALLY`). This does not block the gate because both routes live in the
  **same** emg2pose coordinate system; any common DB9↔emg2pose shift affects both routes identically.
* **No reliability gate yet** — this gate establishes the ungated reference point.

## Next allowed step

Design a frozen reliability/abstention gate and evaluate preservation-versus-coverage.
**Do not execute until this Gate3 result is reviewed.**
