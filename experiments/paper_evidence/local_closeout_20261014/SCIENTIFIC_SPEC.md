# Local paper-evidence closeout — frozen before analysis

Date:2026-10-14 Asia/Shanghai. User authorized completing locally runnable experiments and leaving server work. This is a new supplementary analysis lane. No manuscript edits, remote actions, publication, model replacement, calibration, threshold search or new independent-confirmation claims.

## Inputs and units
Use the hash-verified A20/N80 USER_COVERAGE_SERVICE tables in docs/papers/20261014_v4_5_independent_review/evidence, the six primary consumer conditions, original U/B/support definitions and existing frozen registries. Retain all participants and all signed outcomes; no post-result method/consumer/budget selection. Cohorts are previously examined; this is retrospective exploratory evidence. Participants, not frames, are the statistical units.

## Paired statistical analysis
Primary budget0.30. Report0.10/0.50/0.70 as secondary descriptive budgets. Fixed risk-training goal U for main offline analysis. Contrasts expressed as A minus B risk, positive favoring B: Boundary−Full; Score-only−Full; Full_no_TTA−Full; Score-only−Full_no_TTA. First two are main-method contrasts; last two are matched exploratory TTA and joint pose/Fisher feature-block contrasts, not independent-field attribution.

For each cohort/consumer/budget report median participant-paired differences for U and B. U uses all participants with both defined values. B requires defined B under both methods under original full-class support rules. No dropping a class, no zero filling, no changing support30. Record individual values and sample size. For Boundary−Full also compare U on its joint-B support subset, reporting both original full-cohort U and same-subset U/B. Never replace the main population with this subset.

CI algorithm:10000 participant bootstrap draws, numpy default_rng PCG64, masterseed20261014, percentile95% with NumPy linear quantiles. Cache draws per exact cohort/ordered-user subset using seed derived from SHA256 of `20261014|cohort|user1|...`; identical subsets share draws across methods/consumers/budgets. Resample paired participant differences, never individual frames or separate methods. These are pointwise descriptive intervals, with no simultaneous significance or independent-repetition claim. B is conditional on each fixed jointly evaluable set. For n<10 mark LOW_SUPPORT; for DB9 posture n3 retain raw differences and do not generalize to80users. Undefined comparisons remain undefined.

## Missing-reference bounds
For every existing primary participant row, p=accepted_paired_n,m=accepted_GT_missing_n,a=accepted_runtime_n. Verify a=p+m. Recover observedflip f by rounding U*p and check tolerance1e-6 on the integer count. Bounds on all accepted inputs are[f/a,(f+m)/a] ifa>0; paired-only U is not substituted for all-input risk. Save participant bounds and per-cell medians. Actual unknown flips are not estimated or zero-filled.

## Existing fixed-threshold/TTA/cost evidence
Recount development-selected U/B Full and Score-only threshold feasibility from frozen registry. Describe evaluation risk/coverage/support without selecting new thresholds. Extract existing training cost receipts from verified local archives, preserving reusedfitseconds0 as reuse accounting rather than true zero development cost. TTA contrast from offline tables remains separate from fixed-threshold contrast. All original model hashes recorded, no refits to improve outcomes.

## Local source LOSO reproduction
Six admitted source arrays are locally available. Refit only the original source LOSO learning procedures in a new output directory:training-only StandardScaler,SVD LDA; empirical priorsDB9posture/grasp, uniformpriorsCeTI/SHOW/KIN. DB9/CeTI sample/block predictions; SHOW/KIN mean class scores within original user/trial scored units. Hold out entire source participants. PrimaryCeTI uses all6trials. Compare OOF predictions/confusions and pooledBA to archived primary receipts; do not refit or replace production heads, select labels, tune parameters or claim a new independent test cohort. Environmentnumpy1.26.4/sklearn1.5.2, numericalthreads2.

## Local code-time diagnostic
Reproduce whole-record linear resampling length dependence using a fixed synthetic prefix,ramp/impulse and NumPy explicit grid formulas matching align_cornersTrue and half-pixelalign_cornersFalse. Read/hash frozen source proving these options. This verifies index algebra and future/length dependency, not real optical synchronization, physical calibration, trained-pose error or streaming latency.

## Reproduction and verification
Prepare a standalone numerical reproduction bundle with copied input tables, sealed source receipts/configuration, dependency/version requirements, and the locally executable analysis. Execute it in a separate directory, compare all deterministic CSV hashes. Verify independently with alternative sorted-median/percentile arithmetic, originalS3/S4, count identities, and frozen sourceOOF comparisons. Preserve full before/after hashes of the paper directory. No need to rebuild the manuscript during this evidence phase.

## Deferred requirements
New feature-group training needs six-consumerDEV nativepose/four-view caches currently referenced on the server. Upstream model inference/retraining, raw-timewindow/lag experiments and a new strictly incremental pipeline require further data/runtime preflight. Actual checkpointtrainmanifest, independent physical anchors, fresh semantic labels and independent human reader tests are external evidence requirements, not solved merely by GPU access. Do not silently turn missing inputs into a failed experiment.

## Stop rule
Unexpected input/hash/population/protocol mismatch stops the affected analysis and records evidence; do not patch parameters or discard samples to rescue results. Outputnegative intervals and unsupported cells. This spec/code/input seal precedes numerical analysis. No scientific interpretation is selected from interval sign.
