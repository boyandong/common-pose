# CommonPose V1 final joint confirmation

Completed 2026-09-24 on the frozen 20-user, 702-file cohort. Remote transport receipts, structural qualification, inference, and Gate4E/F evaluation completed. Local copies of the final artifacts and all 20 user receipts passed their SHA256 sidecars; the result cohort hash, plan hash, receipt hashes, and reported positive-user/sign-test counts were independently checked.

## Prespecified primary endpoints

Each effect is the **within-user** risk at 100% coverage minus risk after the frozen gate selects the lowest-risk 30% of eligible blocks. Positive values mean lower risk at 30%. The table summarizes the 20 paired user effects in percentage points.

| Contract | Median improvement | IQR | Range | Positive users | Holm-adjusted one-sided sign p |
|---|---:|---:|---:|---:|---:|
| Gate4E_Requirement_U | 17.08% | 16.04%–20.42% | 7.75%–27.23% | 20/20 | 1.9073486e-06 |
| Gate4F_Requirement_B | 16.11% | 12.29%–18.07% | 2.49%–20.38% | 20/20 | 1.9073486e-06 |

Both prespecified primary tests pass familywise 0.05. The exact raw one-sided sign p is 9.536743e-7 for each; Holm adjustment across the two contracts gives 1.907349e-6. No user was omitted from either primary test.

## Absolute risk at fixed coverage

| Gate and metric | 100% coverage median user risk | 30% coverage median user risk |
|---|---:|---:|
| Gate4E ordinary Flip (Requirement U) | 32.86% | 14.19% |
| Gate4E class-balanced Flip (secondary) | 65.29% | 68.40% |
| Gate4F class-balanced Flip (Requirement B) | 65.29% | 47.48% |
| Gate4F ordinary Flip (secondary) | 32.86% | 34.88% |

These are medians of absolute user risks at each coverage; subtracting the two medians does not equal the median paired user effect above. The cross-contract secondary medians do not support a universal gate winner. Gate4F still has a median class-balanced Flip risk of 47.48% at 30% coverage.

## Descriptive classification ACC

Here `Flip = (predicted reference class != ground-truth reference class)`, so ordinary classification ACC is `1 - Flip risk`. The gates keep or abstain on blocks; they do not change the predicted class. These ACC values are derived from the frozen per-user records, with no new fitting or threshold selection.

| Evaluated blocks | Correct / accepted | Pooled ACC | Median user ACC | Median user class-balanced ACC |
|---|---:|---:|---:|---:|
| All eligible blocks, before either gate (100% coverage) | 1,191,758 / 1,828,243 | 65.19% | 67.14% | 34.71% |
| Gate4E accepted blocks (30% per user) | 457,554 / 548,481 | 83.42% | 85.81% | 31.60% |
| Gate4F accepted blocks (30% per user) | 351,508 / 548,481 | 64.09% | 65.12% | 52.52% |

The 30% rows describe **selective accuracy on accepted blocks**; about 70% of eligible blocks per user were not served. Full-coverage accuracy remains the 100% row. Pooled ACC weights users by their number of blocks and is descriptive; the prespecified inference uses paired user-level effects. Gate4F's class-balanced ACC averages only ground-truth classes with at least 30 accepted blocks per user, following its frozen support rule.

## Individual user effects

| User | Gate4E ordinary Flip improvement | Gate4F class-balanced Flip improvement |
|---|---:|---:|
| 513ba531ad | 7.75% | 15.67% |
| cdd070e9c3 | 10.78% | 14.68% |
| 1152814359 | 16.98% | 16.55% |
| 2cefcf6cba | 16.85% | 14.11% |
| ec05871b7c | 16.50% | 20.12% |
| 76bfc2d385 | 14.85% | 10.96% |
| 2942949786 | 15.53% | 2.49% |
| f51770da75 | 25.35% | 12.28% |
| b27941d454 | 20.63% | 20.38% |
| af1317ea3d | 24.64% | 19.89% |
| 831cb06e26 | 21.79% | 17.87% |
| 16923056b7 | 18.32% | 16.73% |
| 299b130307 | 19.66% | 6.79% |
| fba9f08c33 | 17.07% | 18.66% |
| 0ba89d682e | 18.56% | 16.69% |
| 495869fa89 | 27.23% | 19.97% |
| 1896997952 | 20.35% | 12.35% |
| 0625995630 | 17.09% | 16.60% |
| 18449b9c12 | 16.21% | 8.68% |
| ec7f7bbbcd | 15.05% | 12.29% |

## Scope and limits

- The 20 users were untouched by CommonPose scientific development. The frozen upstream checkpoint’s own training-user membership is unresolved, so this does **not** establish upstream-unseen generalization.
- The 10 previously reserved final users and 10 metadata-hash-selected additional users were frozen before final signal/outcome access. No upstream or gate retraining, retuning, user replacement, or threshold selection used these outcomes.
- These are user-level results on this fixed cohort. They do not prove population-wide performance or low absolute risk for every reference class. At 30% coverage, Gate4F supports at least six reference classes per user under its prespecified minimum-count rule.
- Full coverage curves, threshold behavior, per-class support, AUROC/AUPRC where defined, and diagnostics remain in the machine-readable user and aggregate artifacts.

## Evidence

- `FINAL_COHORT_MANIFEST.json`: SHA256 `8820158c3942c56432a900bb809e1e17ad6b4332183b273ea0b01b0bf38d8afe`.
- `FINAL_RUN_PLAN.md`: SHA256 `b4de5b8dc827e1fd4b349ed59c9f97d8448eb48b6878dc916d6a46eeec93d155`.
- `STRUCTURAL_QUALIFICATION.json`: 702 files and 20 sessions passed.
- `FINAL_CONFIRMATION_RESULTS.json`: SHA256 `9a4b81447b529b96aab7d76ba3b7861a43ee37f7695b3519e450b790fe1d721b`.
- `artifacts/users/`: 20 per-user JSON records and SHA256 sidecars; all hashes match the aggregate result.
- `pipeline_stdout.txt`, `structural_stdout.txt`, `inference_stdout.txt`, and `evaluation_stdout.txt` record successful completion.
