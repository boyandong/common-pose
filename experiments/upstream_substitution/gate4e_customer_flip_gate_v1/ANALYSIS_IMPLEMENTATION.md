# Gate4E implementation lock — before Gate4E comparative outcomes

`analysis/gate4e_flip_gate.py` implements the frozen customer Flip target, 36-dimensional deployment-safe feature vector, eight fixed candidate scores, five subject-grouped outer folds, user-weighted direct model fitting, fold-local Gaussian diagnostic, rank-based and calibration-threshold evaluation, frozen method selection and final DEV-only gate fit. The exact scientific choices are in `GATE4E_PLAN.md`, `CUSTOMER_FAILURE_DEFINITION.md`, `FEATURE_MANIFEST.json`, `METHOD_MANIFEST.json`, and `COHORT_MANIFEST.json`.

It imports the already-sealed Gate4D loader only to reuse verified Gate4C paired outputs, frozen head geometry and 654 four-view TTA results; it performs no neural inference. All new result JSON files are written once with SHA256 sidecars. Any implementation defect must receive a separately hashed mechanical amendment before rerun. No Gate4E comparative result was inspected to choose the definitions above.
