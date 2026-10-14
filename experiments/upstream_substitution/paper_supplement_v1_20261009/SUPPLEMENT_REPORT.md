# CommonPose supplementary baseline and feature-ablation results

All comparisons were specified after V1 results were known. DEV uses the original disjoint-user outer folds; FINAL is a supplementary analysis on an already examined cohort. Neither is a new independent confirmation of an altered method.

Inference was reconstructed because the original cache was unavailable. REPRODUCTION_ADMISSION.json reports aggregate drift against original V1 receipts. Aggregate agreement does not establish per-block identity.

Positive paired effects mean the full gate has lower risk than the comparator. Confidence intervals resample users, not frames. Requirement B uses the same per-user common reference-class set across all methods; omitted classes and empty sets remain visible.

| Cohort | Contract | Comparator | Median extra reduction [95% CI], pp | Positive / defined users | Holm p |
|---|---|---|---:|---:|---:|
| DEV | U | class_empirical | 9.71 [7.53, 10.89] | 18 / 19 | 0.0002288818359375 |
| DEV | U | no_tta | 0.66 [-0.08, 1.02] | 13 / 19 | 0.334136962890625 |
| DEV | B | class_empirical | 36.18 [31.42, 40.40] | 19 / 19 | 1.52587890625e-05 |
| DEV | B | no_tta | -0.00 [-0.22, 0.42] | 9 / 19 | 1.0 |
| FINAL | U | class_empirical | 10.70 [8.64, 13.58] | 20 / 20 | 7.62939453125e-06 |
| FINAL | U | no_tta | 0.28 [-0.42, 0.80] | 12 / 20 | 0.5263519287109375 |
| FINAL | B | class_empirical | 37.99 [32.21, 42.97] | 20 / 20 | 7.62939453125e-06 |
| FINAL | B | no_tta | -0.19 [-0.30, 0.10] | 7 / 20 | 0.5263519287109375 |

## Within predicted-class selection

Each method accepts the same 30% within each predicted class. This controls class composition. The following effects compare full scoring against the predicted-class-only empirical control; these are descriptive secondary analyses.

| Cohort | Contract | Median ordinary risk reduction [95% CI], pp | Positive users |
|---|---|---:|---:|
| DEV | U | 10.96 [9.04, 11.85] | 19/19 |
| DEV | B | 9.14 [7.82, 10.37] | 19/19 |
| FINAL | U | 11.89 [10.78, 13.82] | 20/20 |
| FINAL | B | 9.11 [6.98, 10.88] | 20/20 |

## Limits and reporting rules

- The final cohort was previously examined; do not call these tests prospectively independent confirmation.
- Flip is mismatch between the same frozen consumer on predicted versus measured pose. It is not independent human semantic gesture error.
- Dynamic class-balanced metrics change the supported-class denominator. Fixed-common comparisons condition on class support and do not establish service for omitted classes.
- Full-baseline-class-set bounds expose no-service classes; sparse risks and every user/class remain in the detailed tables.
- Fixed thresholds are evaluated separately from per-user rank selection. Original full thresholds are unchanged. Baseline/ablation thresholds use DEV calibration users only.
- No method, features or threshold are selected from these new outcomes. A revised method would need a new untouched user cohort.

Detailed evidence: SUMMARY.json, SPLITS.json, PAIRED_EFFECTS.csv, CLASSWISE_DENSE_ROWS.csv, CLASSWISE_30_ROWS.csv, DEPLOYMENT_30_ROWS.csv and CLASS_ONLY_TIE_SENSITIVITY.csv. Original seven-threshold results and original-record user-effect confidence intervals are separately preserved in existing_record_analysis/.

TTA runtime evidence is in TTA_COST.json when measured. Four upstream views contain the identity plus three perturbations; statistical benefit must be assessed against no_tta without attributing all gain to TTA.
