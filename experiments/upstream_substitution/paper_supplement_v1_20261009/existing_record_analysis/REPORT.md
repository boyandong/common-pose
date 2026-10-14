# Original V1 records: supplementary statistical analysis

Computed from the original 20 sealed user receipts. No data acquisition, model fitting, threshold changes or reconstructed inference entered these results.
The following confidence intervals are post-V1 supplementary user-bootstrap estimates, conditional on this fixed cohort.

| Gate | Ordinary paired reduction, median [95% CI] | Dynamic balanced reduction | Fixed common-class reduction [95% CI] |
|---|---:|---:|---:|
| Gate4E_Requirement_U | 17.08 [16.36, 20.00] pp | -1.94 pp | -4.36 [-7.34, -1.24] pp |
| Gate4F_Requirement_B | -3.69 [-5.65, 4.43] pp | 16.11 pp | 14.77 [12.29, 16.58] pp |

Fixed common sets here compare each full gate at 100% and 30%; the all-method common-set comparison awaits the new baseline/ablation execution. Membership and missing/sparse classes are explicit in USER_EFFECTS.csv. Support conditioning does not establish reliability for omitted classes.

The original dynamic metric excludes classes below 30 accepted samples separately at every coverage. Full-baseline-set sensitivity and missing-class bounds are included in SUMMARY.json; zero accepted samples mean no service.

DEPLOYMENT_USER_ROWS.csv and CLASSWISE_ROWS.csv report every user, threshold and reference class. The curves above contain only the seven originally evaluated points; the new dense curves require reconstructed scores.

Full vs class-only and full vs no-TTA remain NOT_RUN in this original-record analysis. Do not infer sample-level incremental gate benefit from these statistics alone.
