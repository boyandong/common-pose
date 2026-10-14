# Gate4B prospective multi-user reliability plan

**Status:** prospective identity freeze on 2026-09-22; no Gate4B scientific outcome has been computed. The cohort manifest is a metadata-only structural preflight. Full Gate3 row/block validity and prediction validity cannot be certified before inference. If a frozen session fails those checks later, stop without replacement or reordering.

## Question and scope

Does the Gate4A-selected, deployment-visible task-error predictor retain useful ranking of true task-relevant Fisher error on new participants? TEMP and TTA are frozen comparators. Gate4B provides multi-user ranking evidence from VALIDATION only. It does not select a gate, threshold, calibration rule, conformal guarantee, or final test result.

Gate4A is closed: `GATE4A_PLAN.md` SHA256 `ba6a13ea938f8102b9b143caeaccc719c544de7f9435a978a9f967c944d93a8b`, verifier 921 checks and zero failures. The Gate4A discovery participant `d387095792` is permanently excluded. Do not modify Gate3, Gate3B, or Gate4A artifacts.

## Frozen upstream identities and provenance

- Official `regression_vemg2pose.ckpt`: SHA256 `748b1d1ef0ce1985f6fc07225d97eebfb370243429af803b4997d28ecce2424e`.
- Frozen DB9 trusted-8 head: SHA256 `b0ef8caf8e390a480fa2a3b448f79ccf14f75c71265ef925ee299a5e9e660386`.
- Gate4A predictor specification: `artifacts/TASK_ERROR_PREDICTOR_SPEC.json` in the Gate4A lane, SHA256 `987546dfc962077ae2da18049646ca4d7e7ac81c561a391cebe07ec66731c864`.
- DB9-only Fisher component scales: `gate3b_continuous_representation/artifacts/FISHER_DB9_REFERENCE_SCALE.json`, SHA256 `d15997aa56e5264bdede56c10727a910f94b2c7e32ab8137a6e8e9e45c39c667`.
- Trusted-8 source indices: `[2, 3, 5, 6, 9, 13, 17, 18]`.
- Upstream checkpoint train membership is **UNRESOLVED**. Repository default `full_split` and metadata `split` are not proof of the checkpoint's actual training cohort. Future claims are limited to reliability-score transfer across participants relative to a frozen upstream checkpoint. Do not claim the upstream estimator has never seen these participants.

## Prospective cohort construction

Use the official metadata CSV and the matching complete official tar index. Inspect only participant/session IDs, file names, hands, start/end times, tar membership, and member sizes. Do not read GT values, model predictions, reliability scores, class output, Fisher error, or any downstream outcome to choose participants. The tar object identity and input hashes are recorded in `COHORT_MANIFEST.json`.

The metadata preflight accepts a session only if its participant ID and session ID are present, rows have finite positive durations, every named HDF5 file has one positive-size member in the official tar, both left and right records are represented, and its nominal 50 Hz capacity is at least 10,000. Per record, nominal capacity is `max(0, floor(((end-start)*2000 - 1790)/40) - 1)`; this is only a conservative accounting proxy for the official 1790-row left context, 40-row blocks, and first-block exclusion. It does **not** prove HDF5 parseability, stream presence, exact timestamp equality, GT-valid blocks, prediction-valid blocks, or actual eligible-frame count. The full structural and data-integrity check is mandatory in the next task before any scientific interpretation. A failure stops the experiment; no replacement or revised assignment is permitted.

For every preflight-eligible session of a participant, compute `SHA256("COMMON_POSE_GATE4B_SESSION_V1|" + participant_id + "|" + session_id)` and choose the lexicographically smallest hash. Exclude `d387095792` before user ordering. For every remaining preflight-eligible participant compute `SHA256("COMMON_POSE_GATE4B_USER_V1|" + participant_id)`, sort ascending, and reserve the first 48. Ranks 1–20 are DEV, 21–30 CALIBRATION_LOCKED, 31–38 VALIDATION, and 39–48 FINAL_TEST_LOCKED. The hash order is authoritative; checkpoint training-membership preferences cannot reorder it. If fewer than 48 preflight-eligible participants exist, stop. Never select or replace anyone using outcomes.

CALIBRATION_LOCKED and FINAL_TEST_LOCKED are identity reservations only. No inference, GT-value read, Fisher target, candidate score, performance summary, or scientific data acquisition is allowed for those users in Gate4B. Prefer to leave their HDF5 files undownloaded.

## Frozen future data and target rules

The next task may acquire only the frozen 20 DEV and 8 VALIDATION sessions, selectively rather than the whole tar. Verify file integrity, HDF5 schema, EMG and joint-angle streams, timestamps, and exact official alignment. The official frozen checkpoint uses the Gate3 inference path without retraining, fine-tuning, lag search, fitted calibration, or added smoothing. Prediction row `i` aligns to GT row `1790+i`; timestamps must match exactly. At 2 kHz, a row is valid only if all 20 angles are finite and not all approximately zero. Form non-overlapping 40-row means of trusted-8 angles; a block is eligible only if all its GT and prediction rows are valid. Drop the first block of every record and the final incomplete block. The frozen session must yield at least 10,000 eligible 50 Hz frames. Failure is a stop, not a reason to choose a new session or user.

For each eligible frame, transform trusted-8 GT and prediction pose with the same frozen DB9 standardization and Fisher LDA. The primary target is

`r_t = sqrt(sum_j [((z_PRED,t,j - z_GT,t,j) / sigma_DB9,j)^2])`.

`sigma_DB9` comes only from the frozen Gate3B DB9 reference artifact. This is paired relative Fisher error, not distance to an absolute DB9 support cloud. GT and `r_t` are research labels only, never deployment features.

## Exactly three candidate scores

1. **TEMP:** within each continuous record, `delta_z_t = z_PRED,t - z_PRED,t-1` and `u_TEMP,t = sqrt(sum_j [(delta_z_t,j/sigma_DB9,j)^2])`. First eligible frame per record is `NA`; do not impute or connect records.
2. **TTA:** frozen official EMG channel rolls `k = 0, +1, -1` with unchanged checkpoint. `u_TTA,t` is the RMS DB9-normalized Fisher dispersion across these three predictions, exactly as in Gate4A. No perturbation search or weight adaptation.
3. **TASK-ERROR PREDICTOR (primary):** exact 48 deployment-visible Gate4A features and `GradientBoostingRegressor(loss="quantile", alpha=0.90, n_estimators=100, learning_rate=0.1, max_depth=3, subsample=1.0, criterion="friedman_mse", min_samples_split=2, min_samples_leaf=1, max_features=None, random_state=0)` with other sklearn defaults. Features are current trusted-8 predicted pose, current seven-dimensional predicted Fisher, within-record first and second differences, hand side, and difference-validity flags. The first two differences are zero-filled only at record starts with their flags. No GT, target, user ID, stage, class, downstream agreement, or future-frame feature. Do not retune the model or features.

Train the task-error predictor on DEV only. For fitting only, use all eligible feature-complete frames up to 20,000 per DEV participant. Above 20,000, take exactly 20,000 deterministic evenly spaced indices over that participant's chronologically concatenated eligible frames (`np.linspace` style); never sample using target or score. The maximum fitting set is 400,000 rows. An optional five-fold participant-grouped DEV diagnostic is engineering sanity only and cannot select hyperparameters. Fit one final model on capped DEV rows. VALIDATION never enters fitting; evaluate all eligible VALIDATION frames. CALIBRATION_LOCKED and FINAL_TEST_LOCKED remain untouched.

## Frozen VALIDATION analysis

For each of TEMP, TTA, and ERR, report pooled Spearman and Kendall, per-user Spearman (median, IQR, minimum, maximum, positive-user fraction), and no frame-level p-values. For each VALIDATION user separately, rank low score as lower risk; at coverage 100%, 90%, 75%, 50%, and 25% report mean, median, and p90 true `r_t`, then aggregate user-level values with median, IQR, minimum, and maximum. Report pooled curves descriptively. Compute per-user AURC on inclusive coverage grid 0.10–1.00 by 0.01 with no interpolation, plus pooled AURC descriptively. Use Gate4A's exact ten equal-count rank-decile helper and TEMP NaN semantics; report user-level decile medians and their cross-user median/IQR. Report NO_GATE all-frame risk and ORACLE rankings using true `r_t` solely as references. No threshold selection.

Gate4A single-user feasibility bands are not automatically cross-user decision rules. Apply their frozen wording only if directly meaningful; otherwise report `GATE4A_FEASIBILITY_BAND_NOT_DIRECTLY_TRANSFERABLE`. Interpret the Gate4A-selected ERR predictor's transfer using VALIDATION evidence, without inventing a binary success threshold. No semantic gesture task, human annotation, downstream or upstream retraining, final gate, conformal calibration, LTT, CRC, or formal coverage claim occurs in Gate4B.

## Cohort-freeze task boundary

This task ends after the plan, provenance record, cohort identity reservations, and independent hash/assignment verification. It performs no Gate4B inference, fitting, target computation, or candidate outcome analysis. The next task may acquire DEV and VALIDATION scientific data only and must stop on structural failure before evaluating outcomes.
