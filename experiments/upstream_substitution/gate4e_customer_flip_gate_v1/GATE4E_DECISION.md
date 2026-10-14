# Gate4E DB9 customer Flip gate — DEV decision, 2026-09-24

**GATE4E DEV METHOD DEVELOPMENT COMPLETE — DB9 CUSTOMER GATE FROZEN — READY FOR SEPARATE UNTOUCHED SYSTEM CONFIRMATION.** This is a DEV-only method and instance fit, not prospective confirmation. The 19 exact Gate4D DEV users and 654 files were used; no Gate4C VALIDATION or protected user was opened. The frozen customer is DB9 trusted-8 LDA, SHA256 `b0ef8caf8e390a480fa2a3b448f79ccf14f75c71265ef925ee299a5e9e660386`. The primary target is `Flip = 1[y_API != y_GT]`, with both outputs from that same frozen consumer. No semantic human gesture label is involved.

The pooled DEV block Flip prevalence is **0.3972**, descriptive only. Across users it ranges from **0.2077** (`47c605ad6f`) to **0.5553** (`54c854b839`); every user's support and prevalence are in `artifacts/FLIP_TARGET_SUMMARY.json`. Reference-output classes are strongly imbalanced: class 4 supplies 984,620 blocks and has pooled Flip rate 0.2100, whereas classes 1, 2, 5 and 7 have pooled Flip rates 0.9074, 0.8901, 0.8154 and 0.7897. These are behavioral preservation results, not semantic accuracy.

All eight frozen candidates ran on five disjoint-user outer folds. The selection statistic is the median of **per-user** Flip-risk area under the coverage curve from 30% to 100%; lower is better. The table also shows user-median Flip risk at 30% accepted coverage and the number of users whose 30% risk is lower than their own 100% risk.

| Gate | Median user Flip-risk AUC | Median user Flip risk at 30% | Improved users |
| --- | ---: | ---: | ---: |
| Consumer margin | 0.225438 | 0.2793 | 19/19 |
| Probability entropy | 0.218308 | 0.2481 | 19/19 |
| Nearest boundary distance | 0.222493 | 0.2135 | 19/19 |
| Four-view TTA dispersion | 0.278674 | 0.3840 | 12/19 |
| Direct weighted logistic | 0.202488 | **0.1737** | 19/19 |
| **Direct weighted hist-GBDT** | **0.201031** | 0.1775 | **19/19** |
| Analytic boundary safety | 0.243982 | 0.3124 | 17/19 |
| Gaussian boundary crossing | 0.219127 | 0.2136 | 19/19 |

**Frozen-rule selection: hist-GBDT.** The AUC edge over logistic is **0.001457**, so do not claim a large or independently confirmed superiority. Logistic is slightly better at 30% coverage but AUC is the frozen first criterion. All-user median Flip risk is 0.4034 at 100% and 0.1775 at 30% for hist-GBDT. Its weakest 30% improvement is user `f1b6a408bf` (0.2977 → 0.2635); user `9b8c99cdc2` remains high-risk (0.5022 → 0.4272). All difficult users remain included.

The result has a material class-composition limit. Median user balanced customer-output preservation **falls from 0.3184 to 0.2910** at 30% under hist-GBDT, while hard preservation rises. Accepted samples concentrate in reference classes 4 and 6: median preservation at 30% is about 0.984 and 0.962 there, but approximately 0.000, 0.005, 0.016, 0.000 and 0.004 for classes 1, 2, 5, 7 and 8 among users meeting the class-support floor. Class 3 has only one user with ≥30 accepted blocks, so its selected-subset median is not a stable cross-user summary. This gate is **not** evidence of uniform classwise service.

The boundary-aware hypothesis was not supported as a winner here. The Gaussian crossing candidate passed the preregistered training-fold distribution check, but AUC 0.219127 did not beat the direct predictors; analytic safety was weaker still. Fisher error remains a secondary mechanism: its association with Flip is positive in all 19 users (per-user Spearman range about 0.099–0.477), but Fisher error is not the selection target. The four small/large Fisher × Flip categories are in `FISHER_MECHANISTIC_ANALYSIS.json`.

User-grouped empirical threshold calibration was evaluated separately from within-user ranking. At nominal 50% acceptance, achieved held-out coverage averaged 0.514 across 19 users, range 0.383–0.723; nominal 30% yielded mean 0.319, range 0.213–0.527. No formal clustered conformal guarantee is claimed.

The final DB9-customer instance was fit deterministically using 15 DEV training users and 4 DEV calibration users fixed in the preregistration. `artifacts/FINAL_GATE_MODEL.joblib` SHA256 **`ca06d630e40fc44687bec5ac12c83d9b20aa7c48fe200d89e48d583f9d09f035`** and `artifacts/FINAL_GATE_INSTANCE.json` SHA256 **`246924fe79d09b24641f037c4558e051902df5c36aa596f6fefaf0811712fb38`** freeze model, features, scoring orientation and empirical acceptance thresholds. This artifact is a customer-specific candidate, not a universal HumanEngine gate. No GT-derived quantity entered its deployment features. One pre-outcome mechanical repair corrected a 35-versus-36 feature-count assertion; no scientific contract changed after outcome inspection.

**Next scientific action:** stop this branch. A separate PI-authorized, genuinely untouched system-confirmation cohort must be prospectively frozen before opening data. The final test must use the same upstream, customer, selected Gate and thresholds without modification, and must inspect per-user and classwise preservation as well as overall Flip risk. The already-seen Gate4C VALIDATION users cannot be described as fresh confirmation.
