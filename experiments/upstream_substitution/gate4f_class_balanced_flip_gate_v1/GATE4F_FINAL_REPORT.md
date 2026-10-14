# Gate4F DEV result — class-balanced DB9 customer Flip gate

**Frozen: YES.** Plan SHA256 `f2cebeb2e546825ffa6fb80499037dc2dec338d36ad883bc6373056b35722a2a`. The original Gate4E script remains at its prior SHA256 `8ffdff86a6ccd065ab0b3e945b764eaa858d62d2233fbf494a9c4a3a824cff62`; Gate4E was not edited. No scientific contract changed after outcome inspection. A classwise coverage plot was generated from frozen output rows after the run, with no model or decision changes.

**Cohort and customer.** Exact 19 DEV users: `0816388460`, `13b8b5f76d`, `2132c5d085`, `2327817653`, `23b817e892`, `2be40c4380`, `32cbfe3221`, `3589743749`, `47c605ad6f`, `54c854b839`, `6a7fc66366`, `7afcdcd6be`, `87aa3b3887`, `8bd1c0ff16`, `9b8c99cdc2`, `ce52651f99`, `dd810188d9`, `f1b6a408bf`.

The frozen Gate4D/4E DB9 customer head SHA256 is `b0ef8caf8e390a480fa2a3b448f79ccf14f75c71265ef925ee299a5e9e660386`, with unchanged canonical16 adapter and Flip definition `1[C(x_hat) != C(x)]`. The exact cohort manifest contains 654 files. No GT-derived field entered deployment features. Every user/coverage balanced endpoint averages class Flip risks only for reference classes with at least 30 accepted blocks; sparse classes are reported but excluded for that user/coverage. This rule was sealed before outcome inspection.

**Target prevalence.** Across all 1,780,477 paired DEV blocks, descriptive pooled Flip prevalence is 0.3972. Reference classes 1–8 have support `36,153 / 61,709 / 1,354 / 984,620 / 186,024 / 241,710 / 51,751 / 217,156` and Flip prevalence `0.9074 / 0.8901 / 0.8663 / 0.2100 / 0.8154 / 0.2949 / 0.7897 / 0.6805`. The per-user prevalence and class support are in `BALANCED_FLIP_TARGET_SUMMARY.json`; the pooled values are descriptive and were not used as independent observations.

**All eight frozen methods executed.** The selection statistic is median across users of each user's balanced Flip-risk AUC from 30% to 100% fixed coverage (lower is better): logistic `0.4184`, hist-GBDT `0.4315`, entropy `0.4564`, margin `0.4616`, boundary safety `0.4629`, boundary distance `0.4648`, TTA dispersion `0.4658`, Gaussian crossing `0.4771`. Gaussian suitability passed all five folds. **Selected Gate4F method: logistic.**

| Fixed accepted coverage | 100% | 90% | 80% | 70% | 60% | 50% | 30% |
|---|---:|---:|---:|---:|---:|---:|---:|
| Median user balanced Flip risk | .6816 | .6460 | .6271 | .6080 | .5961 | .5561 | .5066 |
| Median user balanced preservation | .3184 | .3540 | .3729 | .3920 | .4039 | .4439 | .4934 |
| Median user ordinary Flip risk | .4034 | .4039 | .4007 | .3935 | .4073 | .4365 | .4147 |
| Median user ordinary preservation | .5966 | .5961 | .5993 | .6065 | .5927 | .5635 | .5853 |

The selected method improved balanced risk at 30% versus 100% in **19/19 held-out users**. Lower fixed coverage generally improved balanced preservation, while ordinary usage-weighted preservation did not consistently improve. The latter is secondary under Requirement-B; Gate4E optimizes the distinct Requirement-U and is not a universal competitor.

**Important class and user limits.** At 30% coverage, supported class 3 occurs in only 2/19 users, so no broad class-3 preservation claim is supported. At 30%, median supported-user preservation for classes 1–8 is `.2013 / .4857 / .0920 / .3336 / .5300 / .8662 / .5317 / .5510`; class 4 falls from `.8169` at 100% to `.3336` at 30%. Every user still has at least six supported classes at 30%. Worst balanced-risk users at 30% are `9b8c99cdc2` (.6442), `13b8b5f76d` (.6186), and `2be40c4380` (.5830). These failures were not used to revise the gate.

**Deployment calibration.** The frozen user-grouped, class-balanced quantile rule gave median achieved held-out coverage .9993, .4597, and .2362 at nominal 100%, 50%, and 30%, respectively. Corresponding median balanced Flip risks were .6706, .5415, and .4912. The full per-user achieved coverage, ordinary risk, classwise risk and support are in `DEPLOYMENT_THRESHOLD_METRICS.json`. This is empirical grouped calibration, not a finite-sample coverage guarantee.

**Final instance.** Frozen 15-train/4-calibration DEV logistic model is `artifacts/FINAL_GATE_MODEL.joblib`, SHA256 `535828304087d511402c8224ea0276d55e58e0a0c1cba0562bafe7d2d1147b66`. Exact weights, features, preprocessing, thresholds, code hashes, and allocation are in `FINAL_GATE_INSTANCE.json` and the sealed plan/manifests. Nine required JSON artifacts, their SHA256 sidecars, the model, and plots are in `artifacts/`; their downloaded hashes were checked. VALIDATION and protected/untouched users remain unopened. Gate4F and frozen Gate4E are ready for a separately authorized joint untouched system confirmation.

**Terminal status:** GATE4F DEV METHOD DEVELOPMENT COMPLETE — CLASS-BALANCED DB9 CUSTOMER GATE FROZEN — READY FOR JOINT UNTOUCHED SYSTEM CONFIRMATION WITH GATE4E.
