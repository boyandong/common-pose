# SESSION HANDOVER — Session 5

**Session name (recommended for successor):**
`EMG2POSE-BRIDGE-20260918-CROSS-DATASET-AUDIT`

**Lane:** Session 5 — cross-dataset bridge audit
(emg2pose → canonical16 → frozen DB9 posture decoder). Sessions 1–4 are frozen
and were not modified.

**Date:** 2026-09-18
**Status:** **audit complete; documentation-corrected after independent audit;
S5 CLOSED / FROZEN.** No background process left running.

> **Note on this file.** `docs/SESSION_HANDOVER.md` is Session 1's handover and
> belongs to a frozen lane, so this session's handover is written here, beside its
> own artifacts. A one-line pointer was appended to the root handover.

> **INDEPENDENT AUDIT OUTCOME (read this first).**
> `_audit_s5/S5_INDEPENDENT_AUDIT_REPORT.md` is an independent read-only audit that
> rebuilt the decoder and the geometry from scratch without importing any
> `bridge_audit` module. It reproduced **42/42 headline claims at the reported
> precision** and found no fabricated number, no leakage, no wrong-cohort refit and
> no arithmetic error on the load-bearing path. It found **two interpretation-level
> errors**, both now corrected in the report and in the artifacts by
> `bridge_audit/tools/apply_audit_corrections.py`:
> 1. the claim that sklearn centres LDA class covariances by the **global** mean is
>    **FALSE** — `lda.covariance_` *is* the correctly centred pooled within-class
>    matrix (agreement 0.0); the ~0.0576 figure is the **shrinkage effect**;
> 2. the 13.24 % held-out DB9 exceedance is primarily **source-database/cohort
>    distribution shift** (development-exposed = DB1+DB5, outcome-unseen = DB2+DB5),
>    not a family-wise property of the support statistic (within-subject split-half
>    gives 4.74 % against a nominal 5 %).
>
> **No numeric result changed in that round** — mechanically verified by hashing
> every protected result block before and after the correction.

---

## 1. Objective and outcome

**Asked:** does wrist-EMG pose estimation preserve the frozen posture-relevant
kinematic geometry well enough that a DB9-trained decoder behaves consistently
with an oracle-GT-pose decoder?

**Answered:** **CASE C** in its **narrow, distributional sense only** — the overall
emg2pose mini natural-pose distribution is largely outside the support of the six DB9
posture classes — with a **measured secondary contribution** from the pose estimator.
77.04 % of GT frames lie beyond a DB9-only p95 threshold.

**Do NOT phrase CASE C as coordinate-system incompatibility.** The independent audit
found positive evidence of **partial** coordinate compatibility (per-DOF scale
correlation r = +0.551; inter-joint correlation structure agrees on 84/120 signs; a
single affine map removes 54.7 % of the nearest-neighbour mismatch; discriminant-energy
fraction 0.271, below the DB9 within-class reference 0.326). These are diagnostics,
not proof of coordinate equivalence.

Full report: `bridge_audit/SESSION5_BRIDGE_AUDIT_REPORT.md` (§0 final conclusion,
§16 case determination, §16b compatibility diagnostics, §23 corrections, §19 risks).

## 2. VERIFIED state (executed, not inferred)

| item | evidence |
|---|---|
| Frozen S3 decoder reconstructed **exactly** | 1548/1548 identical Tier-A decisions, scaler diff 0.0, max \|ΔP\| 5.1e-15, `handshake.PASS = true` |
| Full official mini corpus processed | 30/30 sessions, exit 0, 737.8 s, `logs/bridge_audit_run.log` |
| Paired native-cadence samples | 86,858 GT-valid (and prediction-valid) from 4,165,056 pose samples |
| canonical16 GT-vs-predicted MAE | 19.673° (median 14.374°) |
| DB9-only p95 threshold | 5.5159 (frozen before emg2pose inspection) |
| DB9 held-out exceedance of that threshold | **13.243 %** (n=1548) — **primarily source-database/cohort shift** (development-exposed = DB1 27 + DB5 7; outcome-unseen = DB2 40 + DB5 3); within-subject split-half diagnostic 4.74 % vs nominal 5 % |
| emg2pose GT outside DB9 support | 77.04 % beyond p95; median at the **97.22nd percentile** of the DB9 held-out distribution |
| Decoder agreement | **0.7646273** top-1 (20,444 disagreements); per session 0.4165–1.0000 |
| sklearn covariance identity | `lda.covariance_` == this audit's shrunk pooled within-class == `_class_cov(...)`, all pairwise **0.0** (verified 3 ways by the audit) |
| Verification tests | **28 passed** (`pytest bridge_audit/tests`) |
| Documentation corrections applied | `tools/apply_audit_corrections.py` — protected result blocks hashed before/after: **no block changed** |
| Upstream repo untouched | `baseline/emg2pose` HEAD `5f6f62b…`, `git status --porcelain` empty |
| Frozen S3 lane untouched | `data/db9_posture16/*` mtimes unchanged; no writes outside `bridge_audit/` |

## 3. INFERENCE / NOT VERIFIED — do not treat as established

* **Single-subject corpus.** The official mini corpus is one user (`d387095792`,
  `e3096`), 30 sessions, 15 stages × 2 sides. Every number is within-subject.
  **S5 is a mechanism/bridge diagnostic, not cross-subject bridge validation.**
  Nothing here bounds cross-subject behaviour.
* The checkpoint's actual training split could not be re-derived. `split='val'`,
  `held_out_user=True`, and 0 train-split rows are the available evidence. If the
  checkpoint nevertheless saw this user, the pose error is optimistic — which
  would *strengthen* CASE C.
* The 50 Hz interpolation **fencepost phase was not measured** (float32 rounding
  masks it). Block-mean reduction was used precisely to avoid asserting a phase;
  the full-2 kHz cross-check agrees within ~1.5°. The audit's independent
  phase estimate (phase 21 mod 40, weak instrument) is not offered as a correction,
  and is irrelevant to the pairing because both sides use identical indices.
* The DB9 support region is defined by *representative postures only* (central
  third of each repetition). A continuous-DB9 definition would give a different,
  probably smaller, OOD fraction.
* No confidence intervals, no significance tests (none pre-registered; adding one
  is a `WHAT COUNTS` decision). The audit's bootstrap CI [8.5 %, 18.6 %] and
  permutation p = 0.0158 for the 13.243 % figure are **audit diagnostics**, not
  confirmatory inference on a pre-registered endpoint.
* **The best-vs-worst-session gap is unexplained.** The audit showed the
  "error magnitude vs margin" gloss is not a dose–response (conditional drift
  effect changes sign; direction-shuffled null 0.7507 vs observed 0.7646, i.e.
  error direction worth ~1.4 pp). Do not assert a mechanism for the 58-point
  session spread.
* **Partial coordinate compatibility is a diagnostic, not proof** of coordinate
  equivalence.

## 4. Environment changes made by this session

* **Installed into `<EMG2POSE_VENV>`: `scikit-learn==1.5.2` (+ `threadpoolctl`)
  and `matplotlib`.** Neither was present before; both were required (LDA refit,
  figures). This is the only change to the shared environment.
* No other dependency, path or config change.

## 5. External processes

**None left running.** The audit ran as one foreground-equivalent process that
exited 0. No downloads, no servers, no background jobs.

## 6. Contaminated / discarded results

* The full 30-session run was executed **once**; the earlier 2-session smoke run
  was deleted. No result in the report comes from the smoke run.
* **Two bugs were found and fixed before the reported run:** the predicted-pose
  validity mask used `pred_finite` where `~pred_zero` was meant (it reported every
  prediction as invalid), and the metadata.csv filename join silently matched 0
  rows because the CSV omits the `.hdf5` suffix. Both are described in the report
  and the join is now self-reporting in the artifact.
* **Two false analytic identities were asserted and rejected.** The
  `domain_depth.py` boundary-algebra block went through two wrong drafts
  (`mg == −dz·nrm`, which would force every predicted score difference to zero)
  before the verified form. The rejected identity is recorded in the artifact's
  `rejected_false_identity` field and is now guarded by a test. **This is the
  single most important thing for a successor to know about this lane: the
  algebraic sign conventions here are counter-intuitive and the numeric
  self-check is what makes them trustworthy.**
* Development probe scripts (`_probe_*.py`) were removed after use; the checks
  they performed now live in `tests/test_bridge_audit.py`.
* **Five stale statements were corrected after the independent audit** (see §11
  below). No numeric result changed. The two substantive ones were the sklearn
  covariance note and the 13.2 % explanation; the corrected text supersedes the
  original in the report and in `decoder.py` / `domain_depth.py`.

## 7. Runtime state a successor must re-verify (do not assume)

1. `<PROJECT_ROOT>` and `<EMG2POSE_VENV>` are **junctions**; if either is missing,
   recreate with `cmd /c mklink /J` (h5py cannot open the non-ASCII real path).
2. `sklearn` and `matplotlib` must still be importable from
   `<EMG2POSE_VENV>\Scripts\python.exe`.
3. `bridge_audit/results/` must still contain `bridge_audit_results.json`,
   `domain_depth_supplement.json` and the 30 files in `results/sessions/`; the
   test suite skips its artifact-based tests silently if they are absent, so
   **run pytest and confirm 28 tests actually ran**, not 15.
4. `python bridge_audit/tools/apply_audit_corrections.py --check` must report
   `corrections_present: true`.

## 8. First concrete actions for the successor session

1. Read `bridge_audit/SESSION5_BRIDGE_AUDIT_REPORT.md` §0 (final conclusion),
   §16 (case determination + compatibility diagnostics), §19 (risks) and **§23
   (the correction record)**. Do not re-run the audit to "confirm" it — re-running
   is only needed if an input artifact hash changed.
2. **Read §23 before quoting anything about sklearn's covariance, the 13.2 %
   figure, or the error mechanism**, and prefer the corrected formulations.
3. If continuing: the report's §22 contains **one unstarted proposal** whose
   premise the audit partly weakened. It remains a proposal awaiting a research
   decision, **not an authorised task**.
4. Do **not** modify Sessions 1–4 artifacts, canonical16, the class vocabulary,
   the cohort partition, or the frozen decoder to make the bridge look better.
   Per the audit's own CASE-C rule, the decoder is not to be rescued.
5. Do **not** introduce the word "incompatible" about the two coordinate systems.
6. If a larger corpus becomes available, the natural extension is a *second
   subject* — the single-subject limitation is the largest unquantified risk.

## 9. Open scientific questions for the PI

* **Is CASE C (narrow sense) the end of this branch, or does it motivate a
  different bridge?** The finding is that the six DB9 *representative postures* are
  poorly covered by emg2pose's natural pose distribution — not that the coordinate
  systems disagree. Whether to (a) drop the DB9→emg2pose bridge, (b) define a
  continuous DB9 support region instead of six discrete postures, or (c) look for
  an emg2pose stage whose GT kinematics *do* fall inside DB9 support, is a
  research decision.
* **What to do about thumb CMC ab/adduction.** It carries the largest share of the
  per-DOF margin-shift attribution mass (18.65 %; dominant DOF in 29 % of
  disagreement frames) and is the one variable whose cross-dataset correspondence
  Session 3 already flagged as uncertain. Resolving that axis empirically (rather
  than by sign convention) would be a well-scoped study. Note the shape of the
  claim: attribution mass over margin shift, **not** "18.65 % of errors".
* **Is an emg2pose-side posture vocabulary worth defining?** emg2pose has clean
  stage-level semantics but no frame-level posture labels. Building one would be a
  labelling project, not an engineering one.

## 10. Provenance

* Project root is **not** a git repository → this lane has **no commit**.
  `COMMIT PENDING`. Provenance is file-content based: SHA-256 of every input and
  source file is in `bridge_audit/results/bridge_audit_results.json`
  (`provenance.artifact_hashes_sha256`), and the official repo is pinned at
  `5f6f62b1a0a08426adffe55900842e75a8adb38c` (clean).
* Primary outputs: `bridge_audit/SESSION5_BRIDGE_AUDIT_REPORT.md`,
  `bridge_audit/results/bridge_audit_results.json`,
  `bridge_audit/results/domain_depth_supplement.json`,
  `bridge_audit/results/phase9_visual_examples.json`,
  `bridge_audit/results/figures/`, `bridge_audit/results/sessions/`.
* Independent audit of this lane: `../_audit_s5/S5_INDEPENDENT_AUDIT_REPORT.md`.
* Correction tool + record: `bridge_audit/tools/apply_audit_corrections.py`;
  the audit report's path and SHA-256, the correction list, and the SHA-256 of
  every protected result block at correction time are stored in
  `bridge_audit_results.json::documentation_corrections`.

---

## 11. Documentation-correction round (2026-09-18) — what changed

Triggered by the independent audit. **Documentation only.** No inference, no model
fit, no new prediction, no recomputed statistic; **no saved numeric result changed**
(mechanically verified by hashing every protected result block before and after).

| # | Statement corrected | Where |
|---|---|---|
| 1 | "sklearn centres each class by the GLOBAL mean → `lda.covariance_` is between-class inflated (diff 0.0576)" — **FALSE** | report §7, `decoder.py` comment + verbose print + `to_json` note, test docstring |
| 2 | 13.2 % held-out exceedance explained primarily as a family-wise statistic — **wrong primary cause**; it is source-database/cohort shift | report §7, `domain_depth.py`, report §17.3 |
| 3 | "error magnitude relative to margin" asserted as a mechanism — **not a dose–response** | report §13, §16, `domain_depth.py` |
| 4 | CASE C phrasing that could read as a coordinate/bridge failure | report §0, §16, §16b (new) |
| 5 | domain-support claim not scoped to the narrow support object | report §7 |
| 6 | 76.46 % without the label-imbalance caveat | report §9 |
| 7 | thumb-AA 18.6 % without an explicit numerator/denominator | report §12, §17.9 |
| 8 | §15 visual prose did not name which of the two C pairs it described | report §15 |
| 9 | single-subject status not repeated at the point of use | report §13 |
| 10 | §22 proposal motivation stated at full strength | report §22 |

Corrected formulations to use going forward:

* sklearn's `_class_cov` centres per class by **that class's own mean**;
  `lda.covariance_` **is** the correctly centred pooled within-class covariance and
  equals this audit's shrunk estimate to **0.0**. The ~0.0576 figure is the
  **shrinkage effect**.
* "The 13.2 % held-out exceedance is substantially influenced by source-database
  distribution shift. The support statistic itself behaves close to the nominal 5 %
  level in a within-subject split-half diagnostic."
* "VEMG2Pose prediction error contributes downstream decision instability, but the
  current evidence suggests that error **magnitude relative to available decision
  margin** is more important than a uniquely harmful error direction."
* CASE C applies **only** as: "the overall emg2pose natural-pose distribution is
  largely outside the six-class DB9 posture support."

**S5 is CLOSED / FROZEN.**
