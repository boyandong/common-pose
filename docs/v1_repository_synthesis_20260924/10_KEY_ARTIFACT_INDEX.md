# Key artifact index and conflict ledger

Relative paths are from repository root. Frozen artifacts are cited as evidence, never rewritten by this synthesis.

| Question | Highest-value artifacts |
|---|---|
| Original architecture and historical status | `docs/architecture.md`; `README.md`; `docs/research_status.md` |
| DB9 source and customer baseline | `audits/db9/channel_forensic/FINAL_VALIDATION.md`; `audits/db9/channel_forensic/artifacts/FINAL_VALIDATION.json`; `audits/db9/trusted_pose/TRUSTED_DB9_POSE_v1.json`; `docs/CONFIRMATORY_RESULTS.md` |
| Physical/coordinate and dataset admission | `audits/db9/coordinate_audit/POSE_COORDINATE_AUDIT_REPORT.md`; `audits/dataset_admission/ADMISSION_DECISION.md`; `experiments/upstream_substitution/pre_substitution_reconciliation/artifacts/RECONCILIATION_DECISION.json` |
| Early substitution | `experiments/upstream_substitution/gate1_5_reference_zero/artifacts/REFERENCE_ANCHOR_DECISION.json`; `gate2a_native_gt_diagnostic/artifacts/GATE2A_DECISION.json`; `gate3_formal_substitution/artifacts/GATE3_DECISION.json`; `gate3b_continuous_representation/artifacts/GATE3B_DECISION.json` (all latter paths below `experiments/upstream_substitution/`) |
| Gate4B stop | `experiments/upstream_substitution/gate4b_multiuser_reliability/GATE4B_PLAN.md`; `COHORT_MANIFEST.json`; `artifacts/DATA_MANIFEST.json`; `experiments/upstream_substitution/gate4c_upstream_substitution_reliability_v1/GATE4B_CLOSURE.md` |
| Gate4C substitution | `experiments/upstream_substitution/gate4c_upstream_substitution_reliability_v1/GATE4C_PLAN.md`; `COHORT_MANIFEST.json`; `GATE4C_DECISION.md`; `artifacts/{RESULT_INTEGRITY,USER_METRICS,ANALYSIS_SUMMARY}.json` |
| Gate4D continuous reliability | `experiments/upstream_substitution/gate4d_task_aware_gate_benchmark_v1/GATE4D_PLAN.md`; `GATE4D_DECISION.md`; `artifacts/ANALYSIS_SUMMARY.json` |
| Gate4E Requirement-U | `experiments/upstream_substitution/gate4e_customer_flip_gate_v1/GATE4E_PLAN.md`; `GATE4E_DECISION.md`; `COHORT_MANIFEST.json`; `artifacts/{FINAL_GATE_INSTANCE,ANALYSIS_SUMMARY,DEPLOYMENT_THRESHOLD_METRICS}.json` |
| Gate4F Requirement-B | `experiments/upstream_substitution/gate4f_class_balanced_flip_gate_v1/GATE4F_PLAN.md`; `GATE4F_FINAL_REPORT.md`; `COHORT_MANIFEST.json`; `artifacts/{FINAL_GATE_INSTANCE,ANALYSIS_SUMMARY,DEPLOYMENT_THRESHOLD_METRICS}.json` |
| Untouched eligibility and upstream exposure | `experiments/upstream_substitution/final_untouched_cohort_audit_v1/{AUDIT_SUMMARY.md,TOUCHED_USER_REGISTRY.json,ELIGIBLE_USER_REGISTRY.json,UPSTREAM_EXPOSURE_AUDIT.json}` |
| Final confirmation | `experiments/upstream_substitution/final_joint_confirmation_v1/{FINAL_RUN_PLAN.md,FINAL_COHORT_MANIFEST.json,FINAL_CONFIRMATION_RESULTS.json,FINAL_REPORT.md,STRUCTURAL_QUALIFICATION.json,SESSION_HANDOVER.md}`; `artifacts/users/` holds 20 sealed user JSON records |
| Historical negative/semantic | `experiments/bridge/SESSION5_BRIDGE_AUDIT_REPORT.md`; `experiments/observability/kinmus_phase/KINMUS_TASK_OBSERVABILITY_REPORT.md`; `audits/human_semantic_validation/formal_s6/FORMAL_ANALYSIS_PREREGISTRATION.md`; `docs/research_status.md` §E |

## Conflicts and precedence

1. Root `README.md` and `docs/research_status.md` say frozen upstream substitution has not yet been demonstrated. They describe the state before the untracked Gate4C–Final branch. The sealed 2026-09-24 plan/manifest/results and final report outrank those older status sentences. The corrected claim is selective customer Flip reduction on the fixed development-untouched final cohort, with upstream exposure unknown; the older prose remains a historical snapshot.
2. Early trusted-subset JSON stores `n_subjects=37`; final validation and corpus identity audit show 77/77, with no KEEP verdict change. Treat 37 as the interim loader artifact, not a second cohort result.
3. Historical S5 agreement ~.765, Gate3 agreement .3645 and Gate4C median .6571 are different heads, cohorts, validity/alignment contracts and aggregation units. None overwrites another or can be combined into one trend.
4. The metadata-only cohort audit initially proposed a proven upstream-unseen Group-A gate and reported zero proven Group-A users. The later final plan explicitly authorized a narrower CommonPose-development untouched claim despite unknown upstream membership. The audit's provenance finding remains true; its old proposed stop condition is superseded only for the narrower final run.
5. Gate4A `README.md` references a decision JSON, ranking summaries and verification log not retained in the current `gate4a_reliability_feasibility/artifacts` directory (only `DEFERRED_GATE_CANDIDATES.md` is present there). The plan and deferred list establish method scope, but this repository synthesis cannot reproduce numerical Gate4A rankings. `UNRESOLVED / INSUFFICIENT REPOSITORY EVIDENCE` for those numbers; later Gate4D numbers are not substituted.
6. Reconciliation flagged older coordinate-audit wording that treated a 31.23° median location gap as a range gap, and the older 179.7° grand-offset reading was invalidated. See `pre_substitution_reconciliation/artifacts/RECONCILIATION_DECISION.json`; do not merge these into a new numeric equivalence verdict.

## Integrity scope

Local SHA256 recomputation matched existing sidecars for final plan `b4de5b8d…`, final cohort `8820158c…`, final result `9a4b8144…`, Gate4E final instance `246924fe…`, Gate4F final instance `f0fa280b…`, and Gate4C analysis summary `81dce686…`. The final handover reports all 20 individual receipt checks at run completion; this synthesis did not repeat each receipt check. No raw signal, checkpoint, protected unused outcome or remote runtime was accessed. Git HEAD and the pre-existing dirty status are recorded in `00_REPO_MAP.md`.
