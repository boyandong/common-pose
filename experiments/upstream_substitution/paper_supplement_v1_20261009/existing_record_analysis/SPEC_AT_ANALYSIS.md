# CommonPose paper supplementary analysis: frozen protocol, 2026-10-09

## Objective and evidence status

Test whether full Gate4E/U and Gate4F/B gates add sample-level reliability beyond
predicted-class selection, and whether TTA adds benefit. V1 outcomes were already
known when this protocol was written. All new comparisons are **post-V1
supplementary analyses**, not fresh confirmatory endpoints or a method-selection
exercise. No features, family, hyperparameters, thresholds, users or task are
selected from final outcomes. No new human semantic endpoint is claimed.

## Frozen inputs and cohorts

Use exactly the 19 DEV users/654 files in Gate4E/F COHORT_MANIFEST.json and the
20 final users/702 files in FINAL_COHORT_MANIFEST.json, without accessing protected
CALIBRATION_LOCKED or Gate4C VALIDATION users. Preserve upstream checkpoint,
trusted-8 adapter, frozen eight-class DB9 LDA, 40-row blocks, 1790-row offset,
validity masks, first-block exclusion, file order and source hashes.

Use cached paired outputs/TTA when available. Current server is a new empty
instance. If reconstruction is necessary, it is a separately identified
reproduction; verify checkpoint/head/helper/adapter/source hashes and compare
reconstructed supports, predictions and frozen gate endpoints against V1 before
any result is interpreted as reproducing V1. Hardware/runtime differences must
be reported. If exact paired outputs are unavailable, do not silently substitute
new ones for the original experiment.

## Fixed methods, separately for U and B

1. `class_empirical`: per predicted class, mean of conditional Flip rates across
   training users with that class, with Jeffreys 0.5/1 count smoothing per user;
   missing training classes use 0.5. Only predicted class is available at scoring.
2. `margin`: negative top-two frozen downstream decision-score margin.
3. `entropy`: probability entropy of the frozen downstream on predicted pose.
4. `boundary_distance`: negative nearest normalized LDA decision-boundary distance.
5. `full`: original selected family (U hist-GBDT, B logistic), all 36 features.
6. `no_tta`: same family/hyperparameters/weighting on columns 0:34; remove exactly
   dispersion and projected TTA SD, refit using DEV training users only.
7. `class_model`: same family/hyperparameters/weighting on columns 0:8 (predicted
   class one-hot); controls for the training objective and model family.

No candidate selection or tuning. Use original U/B training weights, 5000 evenly
spaced blocks per training user, original five disjoint-user folds with three
fold-local calibration users, and original final 15-train/4-calibration allocation.
For final full scores use the original frozen models, never refit them. The two
new ablations and empirical baseline are fit on the same 15 DEV training users.
Final supplemental baseline thresholds use only the original 4 DEV calibration
users and the original U/B grouped calibration formula. Record every split.

## Acceptance, ties and risk

Flip = 1[consumer(predicted pose) != consumer(measured pose)]. Primary comparisons
use equal within-user accepted count ceil(0.30*N), same eligible blocks for all
methods. Secondary curves use 1% through 100% in 1% steps, with no risk at zero
accepted samples. Trapezoidal AUC on 30%-100% and exact ordinary AURC on all ranks
are secondary. Resolve equal scores by a deterministic SHA256 permutation of
split/user/block position, shared across methods and independent of outcome.
Report class-only tie sensitivity with 20 predefined seeds (20261009..20261028),
and a stable-original-order diagnostic. Do not choose the best seed.

Reproduce original frozen stable-order full-gate 30% and seven-point results as
a separate integrity check; supplemental tie policy does not overwrite V1.

## Class-composition and sample-level controls

At each point save counts, risk and class coverage for both y_GT reference class
and y_pred predicted class. Never equate them. Report supported-user counts per
class and minimum accepted support 30. Dynamic supported-class balanced risk is
the historical metric and must be labelled as changing its class denominator.

For paired balanced comparisons freeze each user's common class set to reference
classes supported (>=30) at 30% by ALL seven methods and at 100%; use that exact
set at every coverage. Report set membership and users with an empty set; do not
silently drop them. This intersection is a support-conditioned sensitivity,
not evidence about omitted classes. Also report full-baseline-class-set bounds:
retain all reference classes supported at 100%, assign missing accepted risks
the interval [0,1], report accepted sparse risks separately, and report missing
class counts. A class with zero accepted samples is no service, never zero risk.

Separately select 30% WITHIN EACH predicted class using each method. This fixes
predicted-class composition, directly tests within-class selection, and reports
per-user ordinary/equal-predicted-class risk and classwise effects. Class-only
scores are constant within class; their hashed ranking is an outcome-independent
selection control. Report same-class full vs class_empirical effects and support.

## User-level statistics

User is the sampling unit; no pooled-block p-values or frame bootstrap. Report
all per-user paired effects, median/IQR/range, number positive, two-sided exact
sign test and 95% percentile bootstrap CI of paired-user median (20000 draws,
seed 20261009). The four designated comparisons are U and B full vs
class_empirical and full vs no_tta. Holm-adjust the four two-sided sign tests;
label all as supplementary and cohort-conditional. Full vs class_model and
confidence baselines, class analyses, within-class effects, curve points and
threshold results are secondary descriptive analyses, without per-class hunting.

For B primary comparison use the fixed common reference-class set; also report
ordinary and historical dynamic-balanced metrics for both contracts. An
undefined user effect remains explicit and prevents a complete-cohort test.
A positive median alone is not stable incremental benefit: report CI, individual
signs and denominator/support limits before interpreting.

## Deployment and TTA cost

Report original frozen full thresholds unchanged at all seven original nominal
coverages, with achieved coverage, ordinary/balanced risk, every user, worst user,
class support/coverage and worst supported class. Do not recalibrate full gates.
New methods' thresholds remain DEV-only calibrated and supplementary. Compare
fixed-threshold deployment separately from per-user ranking.

TTA requires four upstream views total (identity plus three perturbations). Report
measured incremental wall time only if a benchmark can be run on the metadata-first
DEV file, with model warm-up, CUDA synchronization, and five repeated timings;
otherwise label runtime NOT_MEASURED, and only report structural inference count.

## No rescue and outputs

No new user acquisition, method tuning, semantic relabelling, downstream tasks,
upstream models, protected-user access, original artifact edits, or negative-result
rescue. If reconstruction fails verification, report that limitation and keep
existing-record analyses separate. Produce sealed provenance/runtime manifests,
analysis code, detailed CSV/JSON tables, static figures, a candid final report and
SESSION_HANDOVER.md. Freeze spec/code before comparative supplementary outcomes.
