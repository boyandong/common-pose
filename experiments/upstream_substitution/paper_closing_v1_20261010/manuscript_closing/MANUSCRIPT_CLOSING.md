# CommonPose manuscript closing: selective preservation of a frozen consumer

## Study identity and claim boundary

We evaluated selective preservation of the decisions of one frozen consumer when its input pose was replaced by an upstream estimate. Flip denotes disagreement with the same consumer on measured pose; it is not independently labelled gesture error. The original frozen confirmation and the later supplement are distinct evidence sources. Baseline and ablation comparisons were specified after V1 results were known, and the 20 FINAL users had already been examined. These comparisons therefore provide supplementary empirical evidence, not a new independent confirmation.

DEV comparisons use 19 users in disjoint outer folds. Original per-block DEV scores and fold instances were not retained; later fold refitting must be described separately. FINAL scoring uses the sealed full instances and DEV-only supplementary class models. No feature, method or threshold is selected from these results.

## Thirty-percent rank selection: absolute target risks

Each method accepts the same ceiling of 30% of each user’s blocks. U uses ordinary Flip risk. B uses each user’s original common reference-class set with at least 30 accepted blocks under every one of the seven methods at 30%; this set is fixed for the supplementary comparisons. It conditions on supported classes and does not establish service for omitted classes. All intervals resample users (20,000 draws, seed 20261009). Risks and differences below are in percentage points.

| Method | FINAL U risk [95% CI], pp | FINAL B fixed-common risk [95% CI], pp |
| --- | --- | --- |
| class_empirical | 26.26 [21.21, 32.82] | 85.71 [83.33, 85.71] |
| class_model | 26.26 [21.21, 32.82] | 58.10 [54.74, 61.98] |
| margin | 23.63 [18.25, 26.73] | 57.25 [52.68, 65.28] |
| entropy | 24.08 [16.60, 27.07] | 55.74 [51.24, 64.84] |
| boundary_distance | 17.38 [13.25, 20.68] | 63.51 [51.99, 68.53] |
| full | 14.18 [11.27, 20.10] | 47.20 [41.32, 52.87] |
| no_tta | 14.10 [11.42, 19.49] | 46.37 [40.62, 53.24] |

## Paired incremental benefits and TTA

Positive effects mean comparator risk minus full-gate risk. The empirical class baseline and no-TTA comparison were the designated supplementary tests; other comparator results are descriptive. The later proposed new-cohort primary contrasts are U versus boundary distance and B versus the matched class model. They are not retroactively promoted to primary tests in the old cohort.

| Comparator | U extra reduction [95% CI], pp | U positive/defined | B extra reduction [95% CI], pp | B positive/defined |
| --- | --- | --- | --- | --- |
| class_empirical | 10.70 [8.64, 13.58] | 20/20 | 37.99 [32.21, 42.97] | 20/20 |
| class_model | 10.70 [8.64, 13.58] | 20/20 | 9.66 [6.60, 13.67] | 19/20 |
| margin | 7.10 [4.87, 10.68] | 18/20 | 11.16 [7.90, 13.68] | 20/20 |
| entropy | 5.44 [4.14, 10.62] | 18/20 | 11.11 [6.06, 13.69] | 20/20 |
| boundary_distance | 2.77 [1.01, 4.96] | 16/20 | 13.66 [8.76, 17.81] | 19/20 |
| no_tta | 0.28 [-0.42, 0.80] | 12/20 | -0.19 [-0.30, 0.10] | 7/20 |

Full versus no-TTA does not provide clear evidence of an extra benefit: U 0.28 [-0.42, 0.80] pp and B -0.19 [-0.30, 0.10] pp. This is not an equivalence result and does not authorize replacing the frozen gate. On one prespecified DEV recording, warmed CUDA-synchronized inference medians were 0.369 s for the base view and 1.474 s for four views (4.00 times). This measurement does not represent all recordings or deployment latency.

## Sample selection within predicted classes

Accepting 30% separately inside each predicted class controls class composition. Relative to the empirical class gate, FINAL ordinary-risk reductions were:

| Gate | Median reduction [95% CI], pp | Positive/defined users |
| --- | --- | --- |
| U | 11.89 [10.78, 13.82] | 20/20 |
| B | 9.11 [6.98, 10.88] | 20/20 |

These descriptive comparisons support sample-level selection beyond choosing easy predicted classes; they do not establish semantic recognition accuracy.

## Every FINAL user: the proposed strong-baseline contrasts

| User | U vs boundary distance, pp | B vs matched class model, pp |
| --- | --- | --- |
| 0625995630 | -0.36 | 7.50 |
| 0ba89d682e | 5.48 | 12.03 |
| 1152814359 | 3.80 | 19.50 |
| 16923056b7 | 3.66 | 8.22 |
| 18449b9c12 | 14.14 | 6.82 |
| 1896997952 | 1.30 | 8.81 |
| 2942949786 | -0.76 | -0.05 |
| 299b130307 | 0.72 | 13.59 |
| 2cefcf6cba | 0.42 | 5.59 |
| 495869fa89 | 11.38 | 15.49 |
| 513ba531ad | -4.46 | 15.65 |
| 76bfc2d385 | 8.08 | 5.42 |
| 831cb06e26 | 6.44 | 6.39 |
| af1317ea3d | 6.84 | 16.94 |
| b27941d454 | 2.69 | 10.52 |
| cdd070e9c3 | 2.85 | 3.46 |
| ec05871b7c | 2.42 | 13.75 |
| ec7f7bbbcd | -4.25 | 24.44 |
| f51770da75 | 4.43 | 12.99 |
| fba9f08c33 | 2.32 | 3.90 |

## Reference-class service at 30%

The following table separates baseline support from accepted support. “No service” counts only users who had at least 30 baseline reference blocks but zero accepted blocks; absent baseline classes are not added to that count. Sparse means 1–29 accepted blocks among baseline-supported users. Each cell is baseline-supported / accepted-supported / no-service / sparse users; the cohort contains 20 users.

| Reference class | U full | B full |
| --- | --- | --- |
| 1 | 20/17/0/3 | 20/20/0/0 |
| 2 | 20/17/0/3 | 20/20/0/0 |
| 3 | 4/1/1/2 | 4/2/0/2 |
| 4 | 20/20/0/0 | 20/20/0/0 |
| 5 | 20/20/0/0 | 20/20/0/0 |
| 6 | 20/20/0/0 | 20/20/0/0 |
| 7 | 20/18/1/1 | 20/19/0/1 |
| 8 | 20/20/0/0 | 20/20/0/0 |

Complete user/class counts, risks, coverage and omissions are in results/CLASSWISE_30_REFERENCE_DETAIL.csv and CLASS_SUPPORT_30_SUMMARY.csv. Classes omitted from the B common set cannot be interpreted as having zero risk.

## Frozen-threshold deployment, original confirmation records

Fixed thresholds need not deliver the nominal coverage for each user. The table below uses the original frozen confirmation records, not reconstructed supplementary scores. U ordinary and B dynamic supported-class risks are reported with their distinct identities; the B column is not a fixed-common metric.

| Gate | Nominal coverage % | Median actual coverage % | Actual coverage range % | Median target risk % | Worst-user target risk % |
| --- | --- | --- | --- | --- | --- |
| U | 30.00 | 31.74 | 6.88–54.43 | 14.57 | 32.89 |
| U | 50.00 | 49.10 | 13.81–66.30 | 17.40 | 39.17 |
| U | 60.00 | 57.07 | 21.66–72.88 | 18.67 | 41.61 |
| U | 70.00 | 66.54 | 34.91–83.85 | 22.17 | 46.49 |
| U | 80.00 | 75.61 | 48.69–92.83 | 24.89 | 49.04 |
| U | 90.00 | 87.24 | 65.64–99.40 | 28.48 | 52.02 |
| U | 100.00 | 100.00 | 99.95–100.00 | 32.85 | 59.26 |
| B | 30.00 | 30.95 | 13.78–51.76 | 49.08 | 66.53 |
| B | 50.00 | 51.40 | 28.70–68.99 | 54.50 | 69.42 |
| B | 60.00 | 60.54 | 39.70–76.35 | 56.38 | 70.45 |
| B | 70.00 | 75.54 | 60.12–85.97 | 58.84 | 71.51 |
| B | 80.00 | 83.59 | 73.32–91.98 | 59.95 | 72.12 |
| B | 90.00 | 92.59 | 88.41–97.12 | 61.75 | 72.74 |
| B | 100.00 | 99.99 | 99.92–100.00 | 65.28 | 73.58 |

Reconstructed thresholds are kept separately in results/RECONSTRUCTED_DEPLOYMENT_30.csv. For B full at the 30% threshold, reconstructed fixed-common risk has median 46.24% and worst user 66.52%; its class set was established in the rank comparison, not in the original confirmation. Do not merge original and reconstructed endpoints.

## Late-delivered target-risk area, 30%–100%

For each user and method we integrated the target risk by trapezoids on the saved 1% grid from 0.30 to 1.00, then formed comparator-minus-full paired areas. This late-delivered secondary analysis does not change the original confirmation or introduce a new primary hypothesis. It is neither full-rank ordinary AURC nor the area under a median-user curve. The main curves retain all 19 DEV or 20 FINAL users across all methods and grid points. Dense low-coverage diagnostics use pointwise common users and show the changing denominator; FINAL B at 1% has zero common users and no risk value.

| Gate | Comparator | Paired raw area [95% CI] | Area/0.70 reduction, pp [95% CI] | Positive/defined users |
| --- | --- | --- | --- | --- |
| U | class_empirical | 0.03030 [0.02302, 0.03500] | 4.328 [3.289, 5.000] | 20/20 |
| U | class_model | 0.03053 [0.02309, 0.03484] | 4.362 [3.298, 4.977] | 20/20 |
| U | margin | 0.03359 [0.02176, 0.04117] | 4.799 [3.109, 5.881] | 17/20 |
| U | entropy | 0.02688 [0.02312, 0.04142] | 3.840 [3.302, 5.918] | 17/20 |
| U | boundary_distance | 0.01495 [0.00977, 0.02444] | 2.135 [1.396, 3.491] | 16/20 |
| U | no_tta | -0.00062 [-0.00315, 0.00033] | -0.088 [-0.451, 0.047] | 7/20 |
| B | class_empirical | 0.14236 [0.12090, 0.18604] | 20.337 [17.272, 26.578] | 20/20 |
| B | class_model | 0.03229 [0.02677, 0.04033] | 4.612 [3.824, 5.762] | 20/20 |
| B | margin | 0.04559 [0.03699, 0.05772] | 6.513 [5.285, 8.245] | 20/20 |
| B | entropy | 0.03502 [0.02420, 0.04956] | 5.003 [3.457, 7.080] | 19/20 |
| B | boundary_distance | 0.04663 [0.03554, 0.06342] | 6.661 [5.077, 9.060] | 20/20 |
| B | no_tta | 0.00046 [0.00003, 0.00185] | 0.066 [0.004, 0.264] | 14/20 |

Detailed per-user areas, paired effects and all DEV/FINAL summaries remain in results/TARGET_AREA_*.

TTA findings depend on endpoint and coverage: the designated 30% comparison does not establish an extra benefit, while the late B area comparison has a small positive paired interval. The latter is secondary and does not justify changing the frozen gate or promoting a new primary hypothesis.

## Reproduction identity and numerical environment

Against original V1 FINAL receipts, the reconstructed frozen-model analysis has maximum aggregate risk drift 0.1734 pp across 280 endpoints. This is an aggregate admission result, not evidence of identical per-block predictions or cache bytes. DEV refitting differences are recorded separately in results/REPRODUCTION_LINEAGE.json; their causes cannot be separated from the existing records, and the FINAL drift bound does not apply to them.

The original supplement exports OMP, OPENBLAS and MKL thread counts as 8. Restoring that environment reproduced all 702 canonical risk endpoints exactly, including separately identified DEV refits; this does not prove equality of unavailable historical score vectors. All 39 cache files, 34 source-artifact hashes and frozen FINAL instances were verified. The preserved 1-thread control reproduced the prior failure on FINAL B class_model user 299b130307, whereas 8 threads matched every FINAL endpoint. Eight scores changed by at most 1.11e-16; sorting floating score strata before SHA256 ties changed three accepted blocks in each direction and increased accepted Flip count by two, producing the 0.0109445 pp ordinary-risk difference. Scores were not rounded and ordering/tolerance were not changed. The class-only comparator is therefore sensitive to numerical score strata; reproducibility requires the recorded runtime as well as model hashes.

The focused control first saved its score vectors and then failed to serialize NumPy integer block indices to JSON. Its failed log is preserved; the receipt was recovered by summarizing the saved vectors locally, without rescoring or fitting. The separate-process 1-thread and 8-thread diagnoses and the seed experiment were unaffected.

## All twenty prespecified tie seeds

Seeds 20261009–20261028 were all reported using unchanged scoring instances and the original SHA256 tie rule. FINAL uses frozen scores; DEV uses explicitly identified same-spec fold refits followed by fixed-score sensitivity. Seeds are perturbations, not additional independent users. Across-seed ranges and counts of conditional user-bootstrap intervals are descriptive. B retains the original seven-method common reference-class sets for all seeds, even when current support becomes sparse; a zero-support class leaves the fixed-set risk undefined, never zero.

| Cohort | Gate | Comparator | Median improvement range, pp | Positive-user count range | Complete-cohort seeds /20 | Conditional CI lower >0 seeds /20 |
| --- | --- | --- | --- | --- | --- | --- |
| DEV | U | class_empirical | 9.460–10.232 | 18–18 | 20 | 20 |
| DEV | U | class_model | 8.281–9.162 | 18–18 | 20 | 20 |
| DEV | B | class_empirical | 36.184–36.184 | 19–19 | 20 | 20 |
| DEV | B | class_model | 9.839–10.203 | 19–19 | 20 | 20 |
| FINAL | U | class_empirical | 10.642–10.883 | 20–20 | 20 | 20 |
| FINAL | U | class_model | 10.642–10.883 | 20–20 | 20 | 20 |
| FINAL | B | class_empirical | 37.987–37.987 | 20–20 | 20 | 20 |
| FINAL | B | class_model | 9.568–9.862 | 19–20 | 20 | 20 |

Every seed retains 19 DEV or 20 FINAL defined effects in all four contrasts. The independent verifier recomputed 4,680 user-risk rows, 37,440 class-support rows, 3,120 paired effects, 1,560 diagnostic support intersections and 160 conditional bootstrap summaries directly from cached features and already persisted models, without importing the producer’s metric/tie/statistic functions or fitting any model. Its 702 canonical checks had maximum difference zero.

| Cohort | Gate | Method | User-seed rows | Rows with sparse frozen class | Rows with missing frozen class |
| --- | --- | --- | --- | --- | --- |
| DEV | U | full | 380 | 0 | 0 |
| DEV | U | class_empirical | 380 | 0 | 0 |
| DEV | U | class_model | 380 | 0 | 0 |
| DEV | B | full | 380 | 0 | 0 |
| DEV | B | class_empirical | 380 | 0 | 0 |
| DEV | B | class_model | 380 | 0 | 0 |
| FINAL | U | full | 400 | 0 | 0 |
| FINAL | U | class_empirical | 400 | 2 | 0 |
| FINAL | U | class_model | 400 | 2 | 0 |
| FINAL | B | full | 400 | 0 | 0 |
| FINAL | B | class_empirical | 400 | 2 | 0 |
| FINAL | B | class_model | 400 | 0 | 0 |

All eight reference-class support counts and risks are preserved in SEED_CLASS_SUPPORT.csv. Sparse flags mean fewer than 30 accepted blocks; the frozen class set is not redefined from seed-dependent support. SEED_SUPPORT_INTERSECTIONS_DIAGNOSTIC.csv reports current three-method support intersections for inspection, never as a replacement endpoint. No best seed is selected.

## Prospective confirmation and reproducibility status

Score-only learning is deferred under the limited empirical positioning. New-user confirmation requires an independent exposure/protected-cohort audit, checkpoint-specific exposure caveat, strong-baseline sample-size planning, and a separate protocol with fixed instance hashes before new outcomes. The old FINAL users cannot provide a new independent confirmation. New-cohort planning is not completed experimentation.

Reproduction entry points: local_closing.py and verify_local.py for sealed reporting tables/figures; run_seed_attempt.py and verify_seed_independent.py for the restored 8-thread seed extension; build_manuscript.py for this document. Frozen manifests identify external cache and model dependencies, which remain private and are not redistributed. The source-release receipt identifies the fixed Git version separately. New-user confirmation is still pending and cannot be replaced by this reporting package.

Source ledger: manuscript_closing/BUILD_MANIFEST.json, closing INPUT_MANIFEST.json, results/RUN_MANIFEST.json, original final_joint_confirmation_v1, and reconstructed paper_supplement_v1_20261009. Corrected figure names are results/DEV_FIXED_USERS_30_100 and results/FINAL_FIXED_USERS_30_100; low-coverage diagnostics are *_COMPARABLE_DENSE.
