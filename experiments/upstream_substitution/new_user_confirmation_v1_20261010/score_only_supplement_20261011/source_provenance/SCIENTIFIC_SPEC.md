# Matched learned consumer-score control, 2026-10-10

## Objective and authorization

The user requested the experiment pictured as a same-family, same-weight
consumer-score-only gate. This request supersedes historical deferral of this
control, but does not amend any prospective new-user protocol. This separate
post-V1 lane compares full gates with a learned consumer-score control on the
existing 19 DEV / 20 examined FINAL users. FINAL is not independent confirmation.
No new-user files, running controllers, upstream inference or remote jobs enter.

## Frozen decisions before fitting

Use feature columns 0:19 (Python exclusive upper bound): predicted-class one-hot
8, frozen-consumer decision scores 8, margin 1, entropy 1, nearest boundary
distance 1. Exclude predicted pose8, Fisher7 and TTA2 (columns 19:36). This follows
the later MINIMUM_EXPERIMENT_PLAN_ZH.md, rather than the earlier three-scalar
feasibility suggestion. Fit exactly this one input group; no feature search.

U: HistGradientBoostingClassifier(max_iter=100, max_depth=3, learning_rate=0.1,
l2_regularization=1, random_state=0). B: StandardScaler then LogisticRegression
(C=1, solver=lbfgs, max_iter=300, random_state=0). Reuse the sealed supplement's
weights() and fit() functions: same user lists, deterministic linspace sampling
(up to 5000 blocks per user), U equal-user/equal-Flip-state and B equal-user/
equal-reference-class/equal-Flip-state weights. Hyperparameters and model family
match; feature dimensionality and logistic coefficient count necessarily differ.
No model selection, hyperparameter tuning, threshold optimization or FINAL fit.

Reuse SPLITS.json's five DEV outer folds; fit only their train users, calibrate
only their calibration users, score only their test users. Reuse the final full
instance's 15 training / 4 calibration DEV users for the final score-only model.
Full FINAL models and full DEV fold instances from the completed seed-reproduction
lane are hash-verified and never refitted. DEV full instances are historical
same-spec reconstructions, not original V1 fold models. Freeze new instances and
their 30% calibrated thresholds before evaluating score-only FINAL outcomes.

## Evaluation and missing support

Primary descriptive comparison: global 30% acceptance, ceil(0.30*n) for each
user/method, lower score accepted first, common SHA256 ties using seed 20261009.
U endpoint: ordinary Flip risk. B endpoint: risk averaged over each user's
original seven-method common reference-class set from the sealed summary. Do not
redefine that set after adding the control. Report support below 30 and zero
support; fixed-set risk is undefined if the set is empty or any member is absent.
Also report all-eight-class supports, full-baseline-class missing-risk bounds,
and the two-method supported intersection as a diagnostic only.

Effect = score-only risk minus full risk; positive favors full. User is the
statistical unit. Report all user effects, median/IQR/range, positive/zero users,
20000-draw paired-user percentile bootstrap 95% intervals (seed 20261009), and
descriptive two-sided sign tests. Intervals/p-values are post-hoc descriptive;
no new confirmatory hypothesis or multiplicity-adjusted success claim.

Secondary: 1%-100% risk curves; per-user target-risk area at saved 1% grid from
30%-100%, raw integral and integral/0.70; actual risk/coverage under fixed 30%
calibration thresholds; within-predicted-class 30% acceptance; all 20 predeclared
tie seeds 20261009..20261028 at global 30%. Missing areas remain missing. Report
every seed; seeds are not independent users and no best seed is selected.

## Admission, runtime and provenance

Verify all 39 caches against REMOTE_CACHE_VERIFICATION.json and sidecar seals;
verify full models against instance hashes and DEV models against the completed
seed manifest. Use NumPy 1.26.4 / sklearn 1.5.2 in a separate local Windows
environment, eight BLAS/OpenMP threads. Record Python/SciPy/joblib/platform/thread
pools; this local runtime differs from the historical Linux host. Before fitting,
rescore full models and require canonical 30% ordinary/fixed-common/dynamic risks
to agree with sealed supplementary rows within 1e-12, with identical null status.
Also check full dense curves. A failed admission is an explicit stop, not a reason
to round scores, loosen tolerance, modify models or refit full gates.

Record source/code/spec/environment hashes, sampled training-row and weight
digests, instances, model hashes, cached per-user score vectors and output seals.
An independent verifier recomputes ranks, risks, supports, effects and summaries
from verified feature caches and saved scores; it also checks model predictions.
Refuse overwrite of existing execution outputs. Preserve negative outcomes.

## Interpretation and Do NOT

Flip means preservation of one frozen consumer's reference output, not human
gesture accuracy. Superiority over this control only establishes an increment
over this specified learned score input group; it does not isolate pose versus
TTA, establish independent information sources, or validate a general algorithm.
If full does not win, report that consumer-score learning can explain the present
increment. Do not adopt the new model, revise new-user protocols, edit manuscript
claims automatically, tune on FINAL, touch protected cohorts or alter frozen lanes.

## Session health

This is a fresh local execution phase with no remote background work. Recommend
COMMON-POSE-SCORECONTROL-20261010-MATCHED for a future handover. Follow AGENTS.md's
incident stop and session-health rules, and write a complete handover on closure.
