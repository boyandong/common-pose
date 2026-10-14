# Claim–evidence matrix

Status labels describe evidence in this repository as of the sealed 2026-09-24 final lane. `NOT IDENTIFIABLE` means the required target/provenance was absent; it does not mean a measured zero effect.

| Claim | Supporting or contrary evidence | Status / limitation |
|---|---|---|
| Predicted-pose substitution is uniformly reliable | Gate4C eight-user median hard preservation .6571, range .1632–.7592; one included weak user | **FALSIFIED / CONTRADICTED** as a uniform claim; no fixed reliability pass threshold was preregistered. |
| Substitution risk is heterogeneous across users | Gate4C per-user table and Gate4E DEV Flip prevalence .2077–.5553 | **SUPPORTED** descriptively on observed users. |
| Deployment-visible features contain information about continuous task-space error | Gate4D grouped DEV Gate A `e_F` 2.012→1.624 at 30%, 18/19 improved; TTA weaker; margin/entropy reversed | **SUPPORTED on DEV**, not independently final-confirmed for the continuous endpoint. |
| Gate4E reduces Requirement-U selective risk on DEV | Gate4E frozen grouped user comparison, 19/19 lower ordinary risk, hist-GBDT selected by AUC | **SUPPORTED**, development selection only. |
| Gate4E survives untouched downstream confirmation | Final frozen plan and 20-user results; paired median +17.08 pp; 20/20 positive; Holm p 1.90735e-6 | **SUPPORTED** for fixed cohort and 30% within-user acceptance; checkpoint exposure unknown. |
| Gate4F reduces Requirement-B selective risk on DEV | Gate4F 19/19, median balanced risk .6816→.5066 under ≥30 accepted class-support rule | **SUPPORTED**, development selection only. |
| Gate4F survives untouched downstream confirmation | Final paired median +16.11 pp; 20/20 positive; Holm p 1.90735e-6 | **SUPPORTED** for fixed cohort/contract; median absolute balanced risk still 47.48% at 30%. |
| One universal gate optimizes every reliability objective | D continuous-vs-hard tradeoff; E balanced secondary worsens; F ordinary secondary worsens | **FALSIFIED / CONTRADICTED** for the tested gate/objective combinations; no universal-optimality theorem evaluated. |
| Full upstream generalizes to users absent from its own training | `UPSTREAM_EXPOSURE_AUDIT.json` found no checkpoint-specific training-user membership; final plan says UNKNOWN | **NOT IDENTIFIABLE**. |
| Final users were untouched by CommonPose scientific development before confirmation | 29 touched/164 untouched metadata audit, frozen final manifest selecting 20; final plan and handover | **SUPPORTED** under available CommonPose provenance, not an upstream-unseen statement. |
| Semantic gesture accuracy is established | No registered human labels in Gate4C/final; human S6 primary invalidated by interim unblinding | **NOT IDENTIFIABLE**. Customer-reference class output is not human truth. |
| 30% selective ACC is full-system accuracy | Final report: E 83.42% and F 64.09% pooled ACC among 548,481 accepted blocks each, versus full 65.19% on 1,828,243 | **FALSIFIED / CONTRADICTED**; ~70% abstained per user. |
| Frozen trusted-8 DB9 representation retains posture utility | 77-user eight-class LOSO BA .7479, macro-F1 .7460; chance .125 | **SUPPORTED** for DB9 internal task; does not prove cross-source physical equality. |
| DB9/emg2pose numeric zeros are physically equivalent | Gate1.5 no independent emg2pose reference anchor | **NOT IDENTIFIABLE**. |
| Gate4B tested multi-user reliability | Structural failure before inference; sealed failure inventory | **FALSIFIED / CONTRADICTED** as a record of completed testing; **NO SCIENTIFIC OUTCOME CLAIM**. |

Primary evidence: Gate4C/D/E/F decisions, `final_joint_confirmation_v1/{FINAL_RUN_PLAN.md,FINAL_COHORT_MANIFEST.json,FINAL_CONFIRMATION_RESULTS.json,FINAL_REPORT.md}`, `final_untouched_cohort_audit_v1/UPSTREAM_EXPOSURE_AUDIT.json`, and DB9 final validation. See `10_KEY_ARTIFACT_INDEX.md` for full relative paths.
