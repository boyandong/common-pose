# Common Pose Gate4F handover — 2026-09-24

## Objective and frozen decisions

Gate4F is the class-balanced DB9 customer Flip gate, a strict derivative of closed Gate4E. Its only scientific change is Requirement-B: equal importance for supported reference-output classes. The same 19 DEV users/654 files, upstream, canonical16 adapter, DB9 head, features, candidate families, hyperparameters, folds, and protected-user boundary were retained. Support is at least 30 accepted blocks per user/class. Training weights, grouped calibration, method-selection statistic and tie-breaks are in the sealed `GATE4F_PLAN.md` and `BALANCED_CUSTOMER_REQUIREMENT.md`.

## Verified scientific evidence

The remote DEV run completed: `GATE4F_DEV_METHOD_DEVELOPMENT_COMPLETE logistic`. All eight candidate methods ran; Gaussian suitability passed all folds. Median user balanced Flip-risk AUC selected logistic (0.4184). For logistic, median user balanced Flip risk changed from .6816 at 100% fixed coverage to .5066 at 30%; 19/19 users improved. Class 3 was supported in only 2/19 users at 30%, and class 4 preservation worsened. Ordinary usage-weighted risk is secondary. Full result and limits are in `GATE4F_FINAL_REPORT.md` and `artifacts/`.

The final 15-train/4-calibration model SHA256 is `535828304087d511402c8224ea0276d55e58e0a0c1cba0562bafe7d2d1147b66`. The joblib file holds a dictionary with `method`, `model`, and `gaussian_coefficients`; for selected logistic, the fitted estimator is its `model` member. JSON sidecars and model hash passed local verification after download. Gate4E's frozen analysis script still hashes to `8ffdff86a6ccd065ab0b3e945b764eaa858d62d2233fb494a9c4a3a824cff62`.

## Unknown and external runtime

No untouched joint confirmation has been run, so system-level prospective performance is unknown. Class-3 and other sparsely supported class outcomes must not be generalized. The remote clone used `root@connect.westd.seetacloud.com:30584`, repository `/root/work/common-pose`, and the completed Gate4F lane at the matching relative path. A successor must reverify remote availability, process state, hashes and protected-cohort authorization; this handover is not live runtime truth.

## Worktree and next action

Local new Gate4F lane contains sealed plan/manifests/code, downloaded artifacts, plots, this handover and final report. Gate4E remains closed. Next scientific phase, only with separate PI authorization under the pasted Gate4F contract: freeze one joint Gate4E/Gate4F untouched system-confirmation protocol before accessing any confirmation user. Preserve the distinct Requirement-U and Requirement-B endpoints, report both without a universal winner, and do not retune either gate from confirmation outcomes.

**Do not** reopen Gate4C VALIDATION or other protected users as convenient confirmation, change upstream/head/features, rescue poor classes/users, rerun TTA, or alter frozen DEV decisions.

Recommended new session: `COMMON-POSE-JOINT-CONFIRMATION-20260924-GATE4E-GATE4F`.
