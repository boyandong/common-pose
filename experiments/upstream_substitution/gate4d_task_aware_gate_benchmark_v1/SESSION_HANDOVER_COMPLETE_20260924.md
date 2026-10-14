# Gate4D completed handover — 2026-09-24

## Objective and frozen decisions

DEV-only comparison of confidence gates for continuous Fisher-task preservation under the same frozen Gate4C upstream substitution. Frozen plan SHA256 `08a17402bf438cff514fef85ca00d9971c9790d9903a72f48f43b72a4d46e276`; layer selection `865af659007b7b219fa120e62c06e3f1acc252d18326e7e0522b51cb40fcc292`; exact 19-user/654-file DEV cohort `159a51fecca2caa7f14f1cf3d0db2b9c4acbfcb7a6ab038e3897cd02e99034be`; analysis implementation lock `d68d9e7d928b8cc6a5fb207b26cb661d175b408520a94262b9acc5d5acd1c0f7`. Output-only mechanical repair `IMPLEMENTATION_REPAIR_001.md` SHA256 `f380af9dfb1f2a4c65efdd7748c805b8c0eca38b372d7e70d50ad3cd2368ba69`; repaired analysis script SHA256 `fea112d6d62bac6dd6e915004137089b18b12a96011f11914c802ab400879f8c`. No scientific contract changed after outcome inspection.

## Verified state and scientific evidence

- New cloned runtime: `root@connect.westd.seetacloud.com:30584`, host `autodl-container-790b4aac6e-40d41fd3`, RTX 4090. Remote lane `/root/work/common-pose/experiments/upstream_substitution/gate4d_task_aware_gate_benchmark_v1`. Reverify external runtime before any later action. Detached `run_gate4d.sh` completed both terminal markers: `GATE4D_TTA_COMPLETE 654/654` and `GATE4D_DEV_BENCHMARK_COMPLETE`. The original background PID 2510 has exited.
- Exact 654 TTA output paths and all 654 receipts were checked against the frozen DEV manifest; each output SHA256 matched its receipt. Six analysis JSON sidecars passed on both remote and local copies. `GATE_RISK_COVERAGE.json` has 532 rows and `GATE_RANKING_METRICS.json` has 76 rows. Five compact plots were copied locally.
- `GATE4D_DECISION.md` records the interpretation. Gate A improves median Fisher error at 30% coverage in 18/19 held-out DEV users; TTA in 17/19. Margin and entropy each improve only 2/19 on that primary metric despite improving hard-output preservation. This is DEV method development, not untouched validation or formal conformal coverage.
- Local artifacts: `artifacts/ANALYSIS_SUMMARY.json` SHA256 `33b0860dca2f97721a520c79e5a7736a68077480bc315af09a49a66c5178d2be`; `GATE_RISK_COVERAGE.json` `648190b94a000e1d504d45a44adde1ca6f548a6e8063f53735d63c6d519e53a8`; `GATE_RANKING_METRICS.json` `98d7c7c0f51940269eb913f6dfdffb97f4e7610795f3d3db214578148b82e547`. Other JSON and plots are in the same directory with sidecars for JSON.

## Unknowns, worktree, next actions, and do not

No new confirmation cohort is authorized. The already observed Gate4C VALIDATION users are not a fresh independent confirmation set. Upstream checkpoint training-user membership remains unresolved; do not claim upstream-unseen users. Human gesture task labels are absent, so semantic task accuracy is not identifiable. Gate A's grouped empirical calibration has no formal finite-sample clustered-data guarantee.

The Gate4D lane is untracked in a repository with unrelated pre-existing modifications. Do not stage or commit unrelated files, modify closed Gate4C, rerun base upstream inference, tune the frozen Gate4D gate on held-out users, or open protected data. Next scientific action is to preregister and freeze the final DEV train/calibration allocation and model, then obtain authorization for a genuinely untouched validation cohort. Recommended next session: `COMMON-POSE-GATE4D-20260924-PROSPECTIVE-VALIDATION-DESIGN`.
