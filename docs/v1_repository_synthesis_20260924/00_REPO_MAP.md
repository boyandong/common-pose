# V1 repository map and audit method

Read-only source audit on 2026-09-24, root `<PROJECT_ROOT>`, HEAD `05574b6f104017de001c88ecf1a07b7600bcb882`. The existing worktree was dirty before this synthesis. No existing file was edited. The scan covered the root, `src`, `audits`, `experiments`, `docs`, `provenance`, `scripts`, and `tests`; generated caches and large binary payloads were inventoried by path, not opened. `rg --files` returned 602 nonexcluded files; this is a file count, not an experiment count. The untracked `experiments/upstream_substitution` tree is part of the present scientific record, even though it is absent from HEAD.

| Area | Role | Key evidence |
|---|---|---|
| `src/common_pose/api`, `adapters`, `representation`, `estimators`, `tasks`, `evaluation` | Interface, DB9/emg2pose mappings, pose estimator wrapper, posture head, metrics | `docs/architecture.md`, `docs/common_pose_api.md`, source files |
| `audits/dataset_admission` | Candidate dataset admission, physical and label provenance | `ADMISSION_DECISION.md`, `pose_api_admission/DATASET_ADMISSION_REPORT.md` |
| `audits/db9/channel_forensic`, `coordinate_audit`, `trusted_pose` | Physical-channel and coordinate contract | `FINAL_VALIDATION.md`, `POSE_COORDINATE_AUDIT_REPORT.md`, `TRUSTED_DB9_POSE_v1.json` |
| `audits/human_semantic_validation` | Annotation protocol and interrupted formal semantic lane | `formal_s6/FORMAL_ANALYSIS_PREREGISTRATION.md`, `docs/research_status.md` §E7 |
| `experiments/db9_posture` | Historical canonical16 posture baseline | `results/full_db9_results.json`, `docs/CONFIRMATORY_RESULTS.md` |
| `experiments/bridge` | Historical single-user cross-dataset bridge | `SESSION5_BRIDGE_AUDIT_REPORT.md` |
| `experiments/observability/kinmus_phase` | Phase observability diagnostic | `KINMUS_TASK_OBSERVABILITY_REPORT.md`, decision JSON |
| `experiments/upstream_substitution` | Reconciliation; Gate1.5, 2A, 3, 3B, 4A–4F; cohort audit; final confirmation | Branch plan, decision, manifests, analyses, handovers, sidecars |
| `docs` | Older design, baseline evidence, status ledger | Some root docs are historically stale relative to 2026-09-24 frozen final artifacts |
| `provenance` | Curated-copy content/source identity | `CURATION_MANIFEST.json` and SHA256 |

Experiment units group each branch's plan, scripts, logs, artifacts, and handover; `__pycache__`, plots, receipts, and duplicate transport logs are not separate experiments. `artifacts/users` contains 20 final user records, not 20 branches. Existing SHA256 sidecars were checked for the final plan, cohort, aggregate result, Gate4E/F instances, and Gate4C summary; all six matched. Remaining sidecars are indexed but were not exhaustively rehashed. Protected or otherwise untouched outcomes outside the completed final confirmation were not opened.

Evidence precedence: sealed plan/manifest/result and matching sidecar; final handover; formal analysis; logs; code; branch notes; early design. Historical documents remain evidence of what was believed at that time. `README.md` and `docs/research_status.md` still say substitution has not been demonstrated; Gate4C and final sealed artifacts supersede that temporal status, within their stated claim boundary.
