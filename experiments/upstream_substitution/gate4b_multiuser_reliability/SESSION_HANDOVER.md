# Common Pose / Gate4B session handover — 2026-09-22

Recommended new task name: `COMMON-POSE-GATE4B-20260922-COHORT-FREEZE`

The preceding task is an incident/forensic record: one remote tool call was aborted and the next returned an unknown process ID. A later SSH login succeeded, and a read-only process check found no Gate4B or residual network-check process. Recheck all external state in the new task.

## Objective

Execute Phase 2 / Gate4B multi-user reliability ranking confirmation from the user's pasted specification at `<USER_HOME>\.codex\attachments\b7af1508-1c7f-4784-88f2-22ee5d88a348\已粘贴的文本.txt`. First freeze `GATE4B_PLAN.md` and `COHORT_MANIFEST.json` with SHA256 files before any Gate4B inference, Fisher target, or candidate/outcome analysis. The main confirmation target is the Gate4A task-error predictor; TEMP and TTA are frozen comparators.

## Frozen decisions

- Gate4A is closed. Its verifier passed 921 checks with zero failures and `VERIFY_GATE4A: PASS`.
- Gate4A plan SHA256: `ba6a13ea938f8102b9b143caeaccc719c544de7f9435a978a9f967c944d93a8b`.
- Gate4A verifier SHA256: `8db00b9da87c3dfc8a38029064c5ca68c498376c833b892c7536ced9acb0b9d3`.
- Gate4A decision: proceed to a multi-user cohort; no final gate, threshold, conformal guarantee, or cross-user validity was established.
- Gate4B discovery exclusion: `d387095792` must appear in no split.
- Gate4B target split: DEV 20, CALIBRATION_LOCKED 10, VALIDATION 8, FINAL_TEST_LOCKED 10. Only DEV and VALIDATION may be opened scientifically in Gate4B.
- Frozen upstream checkpoint SHA256: `748b1d1ef0ce1985f6fc07225d97eebfb370243429af803b4997d28ecce2424e`.
- Frozen DB9 trusted-8 head SHA256: `b0ef8caf8e390a480fa2a3b448f79ccf14f75c71265ef925ee299a5e9e660386`.
- Trusted-8 source indices: `[2, 3, 5, 6, 9, 13, 17, 18]`. Gate4A score definitions, Fisher transform/scales, coverage points, AURC grid, and decile ranking rule remain authoritative.

## Verified state and scientific evidence

- No Gate4B plan, cohort manifest, acquisition, inference, fitting, target calculation, or outcome analysis was completed in this task. No Gate4B scientific result exists.
- An official metadata CSV exists at `<HISTORICAL_WORKSPACE>\data\official\emg2pose_dataset_mini\metadata.csv`; its MD5 is `c3f48fd51576fa7752d455f2751c8b99`, matching the previously documented official S3 ETag. It has 25,253 file rows and 193 users; 158 users occur in `split=train`, 35 are marked `held_out_user=True`. Discovery user `d387095792` is in the held-out set, not the train set. These are metadata facts, not Gate4B eligibility counts.
- The local checkpoint at `<HISTORICAL_WORKSPACE>\checkpoints\emg2pose_model_checkpoints\regression_vemg2pose.ckpt` and the new remote instance copy both match the frozen SHA256.
- The official emg2pose repo defaults to `full_split`, and `emg2pose.utils.load_splits` reads the metadata `split` column. The checkpoint's `hyper_parameters` contains model/optimizer/loss settings but no data split, training session IDs, or training user IDs. Therefore checkpoint training membership has **not** been proven. Record `UPSTREAM_TRAIN_MEMBERSHIP = UNRESOLVED` unless new direct evidence resolves it; do not equate the repository default with this checkpoint's actual training membership.

## Unknown or contaminated state

- No participant has been certified as Gate4B structurally eligible. Metadata alone does not prove the required 10,000 eligible 50-Hz frames after the frozen GT and prediction validity rules.
- The pasted specification requires cohort freeze before confirmation-user inference, but also requires a 10,000-frame eligibility check involving the frozen prediction-validity rule. Resolve this without outcome-driven selection: define an outcome-blind structural preflight before freeze and fail closed after freeze if a chosen user cannot meet the full eligibility contract. Never replace a frozen user after inspecting outcomes.
- The specified global hash order for the first 48 eligible users must be respected. The preference for upstream-unseen users in non-DEV splits cannot silently override that exact assignment rule; document any limitation if the frozen hash assignment includes upstream-trained or unknown users.
- The official HDF5 corpus is packaged in a ~431 GiB tar, while the new instance data disk has 50 GiB free. Selective acquisition feasibility and storage budget for up to 28 DEV/VALIDATION sessions have not been established. Do not download the whole corpus.
- A remote `curl -I` check was interrupted before its outcome was known. No Gate4B science ran as part of that check. On reconnect, no matching process was active.

## External runtime state — successor MUST reverify

- Last successful SSH route: `ssh -p 48046 root@connect.westd.seetacloud.com`. Obtain the current credential from the user; never write it to a file. The older port 37554 refused connections twice.
- Last observed host: `autodl-container-cuhm49ja78-f60f025b`, NVIDIA GeForce RTX 4090, driver 580.105.08, reported driver CUDA 13.0, Python 3.10.13, torch 2.3.1+cu121, torch CUDA 12.1 available.
- Last observed free disk: 18 GiB on `/` and 50 GiB on `/root/autodl-tmp`.
- Last verified remote paths: `/root/work/common-pose`, `/root/work/emg2pose`, `/root/models/emg2pose/regression_vemg2pose.ckpt`, `/root/work/gate3_work/frozen_head/frozen_db9_trusted8_lda.joblib`, and `/root/data/emg2pose_dataset_mini/metadata.csv`.
- The upstream repository HEAD was `5f6f62b1a0a08426adffe55900842e75a8adb38c`. Its worktree showed many modified files, likely requiring byte-level or `git show HEAD:` comparison before treating the worktree as official source. Do not discard or reset any of those changes.
- A read-only `ps` check after reconnect found no running Gate4B process. This is a snapshot, not a guarantee for the next task.

## Worktree state

- Local and remote `common-pose` were dirty before Gate4B: multiple pre-existing modified documentation/source/test files and untracked `experiments/upstream_substitution/` content. Preserve all unrelated changes.
- This handover is the only Gate4B file created in the local workspace in the incident task. No frozen Gate4B plan or cohort manifest was written.

## Next actions

1. Start a new task using the recommended name and read this handover, the pasted Gate4B instruction, Gate4A plan/specification, relevant Gate3/3B artifacts, and current git state.
2. Reverify SSH host, GPU/runtime, free disk, checkpoint/head hashes, metadata identity, and whether any Gate4B process or file appeared since this snapshot.
3. Complete the upstream checkpoint provenance audit and write its evidence-backed artifact. Keep membership `UNRESOLVED` unless the checkpoint's actual training cohort can be established.
4. Resolve the outcome-blind structural eligibility and selective acquisition contracts before freezing the cohort. If fewer than 48 users are proven eligible, stop without shrinking or substituting the cohort.
5. Freeze plan and cohort manifest with their hashes before any confirmation-user inference or outcome computation. Then execute only the authorized DEV and VALIDATION work, with locked cohorts untouched.

## Do NOT

- Do not reopen Gate4A, change its plan, scores, candidate definitions, or scientific artifacts.
- Do not infer checkpoint train membership from `split=train` alone.
- Do not select or replace users using prediction quality, Fisher error, score, or any downstream outcome.
- Do not access CALIBRATION_LOCKED or FINAL_TEST_LOCKED scientifically in Gate4B.
- Do not download the full corpus, retrain the upstream model, tune the frozen predictor, select a gate threshold, or claim formal conformal coverage.
