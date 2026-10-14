# CommonPose final joint confirmation — completed handover, 2026-09-24

## Objective

Run the frozen upstream and Gate4E Requirement-U / Gate4F Requirement-B gates once on 20 users untouched by CommonPose development, without retraining or retuning. The upstream checkpoint's own training-user membership remains unknown; do not claim upstream-unseen transfer.

## Frozen decisions

`FINAL_RUN_PLAN.md` was sealed before data access. `FINAL_COHORT_MANIFEST.json` SHA256 `8820158c3942c56432a900bb809e1e17ad6b4332183b273ea0b01b0bf38d8afe` fixes 20 users (10 prior `FINAL_TEST_LOCKED` reservations plus 10 deterministic metadata-hash selections), 702 exact official tar members, and 12,687,690,000 bytes. `CALIBRATION_LOCKED` was unused. The frozen upstream and Gate4E/F model identities and evaluation plan were preserved.

## Verified state and scientific evidence

Transport completed with 702/702 remote SHA256 receipts. Structural qualification passed 702 files and 20 users. Inference completed 702/702; evaluation completed 20/20. The remote pipeline logged `FINAL_INFERENCE_COMPLETE` and `FINAL_EVALUATION_COMPLETE`. Results, structural qualification, logs, and all 20 user receipts were copied to this lane locally. Both aggregate JSON files and all user JSON files match their SHA256 sidecars; result cohort/plan hashes and all receipt hashes match; user-level positive counts and exact sign-test p values were independently checked.

`FINAL_REPORT.md` is the concise interpretation. At fixed 30% coverage, Gate4E Requirement-U median within-user ordinary Flip risk reduction is 17.08 percentage points; Gate4F Requirement-B median within-user class-balanced Flip risk reduction is 16.11 points. Each has 20/20 positive users and Holm-adjusted one-sided sign p = 1.9073486328125e-6. These are distinct customer contracts; cross-contract secondary risks and absolute risk remain important. The report also makes ordinary ACC (`1 - Flip risk`) explicit: full-coverage pooled ACC is 65.19%; selective pooled ACC on the accepted 30% is 83.42% for Gate4E and 64.09% for Gate4F. Full per-user effects and limitations are in the report and machine-readable artifacts.

## Unknown and claim boundary

The frozen upstream checkpoint's actual training-user exposure remains unresolved. The supported claim is generalization of the frozen combined system to users untouched by CommonPose development. The cohort is fixed and deterministic, not a population-representative sample. Do not infer upstream-unseen transfer or low absolute risk in every reference class.

## External runtime — reverify if revisited

Remote host `root@connect.westd.seetacloud.com:30584`, repository `/root/work/common-pose`, data `/root/autodl-tmp/common_pose_final_data`. Remote pipeline finished successfully; no inference or evaluation process remained at the completion check. The Windows Scheduled Task `CommonPoseFinalRelay` completed with result 0 and was unregistered after artifact retrieval. Temporary SSH key: `D:\Temp\gate4b_local_relay\ssh\gate4b_relay_ed25519`; do not print credentials. External runtime is a historical snapshot; reverify before any future work.

## Worktree and next actions

Local HEAD was `05574b6` at handover; `experiments/upstream_substitution/final_joint_confirmation_v1/` remained untracked. Preserve the frozen lane and use `FINAL_REPORT.md`, `FINAL_CONFIRMATION_RESULTS.json`, `STRUCTURAL_QUALIFICATION.json`, `artifacts/users/`, and the four stdout logs as evidence. The follow-up heartbeat is being deleted after final reporting. Further interpretation or deployment decisions should start a new session from these repository artifacts. Do not retrain, retune, replace users/files, use `CALIBRATION_LOCKED`, or claim upstream-unseen status.

Recommended new session: `COMMON-POSE-POSTFINAL-20260924-INTERPRETATION`.
