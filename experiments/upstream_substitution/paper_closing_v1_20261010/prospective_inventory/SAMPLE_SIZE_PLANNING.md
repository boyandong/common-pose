# Strong-baseline new-user planning — not enrollment

The primary proposed comparisons are U versus boundary distance and B versus the matched class model. Each endpoint uses a two-sided sign test at alpha .025; positive direction is required. The two endpoint family uses a conservative Bonferroni allocation. The old full-versus-full-coverage effect is not used.

| Defined nonzero users | Positive probability | Endpoint positive-direction power | Both-endpoint lower bound |
| --- | --- | --- | --- |
| 30 | 0.65 | 0.225 | 0.000 |
| 30 | 0.70 | 0.432 | 0.000 |
| 30 | 0.80 | 0.871 | 0.743 |
| 70 | 0.65 | 0.603 | 0.207 |
| 70 | 0.70 | 0.879 | 0.757 |
| 70 | 0.80 | 0.999 | 0.999 |
| 80 | 0.65 | 0.641 | 0.282 |
| 80 | 0.70 | 0.908 | 0.817 |
| 80 | 0.80 | 1.000 | 1.000 |
| 100 | 0.65 | 0.770 | 0.540 |
| 100 | 0.70 | 0.966 | 0.932 |
| 100 | 0.80 | 1.000 | 1.000 |

These are conditional binomial scenarios, not evidence that N=80 is sufficient. At probability .70, 80 nonzero defined users give endpoint power 0.908 and a both-endpoint success lower bound 0.817 regardless of endpoint dependence. If either effect is weaker, or pairs are missing/zero, power is lower. An enrolled N of 80 does not guarantee 80 nonzero defined pairs.

Magnitude precision is separately illustrated by 20,000 draws from each already examined FINAL strong-baseline effect distribution. ILLUSTRATIVE_MAGNITUDE_PRECISION.csv records its medians and sampling quantiles; this assumes the old distribution represents future users and can be optimistic. It is not a guarantee of confidence-interval width, an independent confirmation or an effect-selection rule.

134 users remain metadata candidates before the full historical-access and structural audits. The source-file total for any 80-user subset lies between 43.57 and 55.41 GB according to the existing metadata. This excludes derived outputs, backup space and inference time. No user subset has been selected for this estimate.

The enrollment size/budget must be resolved before candidate enrollment, protocol sealing or outcome access. N=30 is a feasible budget scenario but has only 0.432 endpoint power at probability .70, and cannot silently inherit the stronger precision/power claim of an 80-user design. Both positive and negative results must be reported.

Methods: [SciPy binomtest](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binomtest.html), [SciPy binomial survival function](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binom.html).
