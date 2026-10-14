# CommonPose closing and twenty-seed release

This is post-V1 reporting on 19 DEV / 20 already examined FINAL users. It preserves
the original confirmation, supplement, frozen models, support definitions and
failed-attempt evidence. It does not constitute new-user confirmation. Score-only
learning is deferred under the user's limited empirical positioning.

The manuscript-facing document is `manuscript_closing/MANUSCRIPT_CLOSING.md`.
`CURRENT_STATUS_ZH.md` is the current status; historical handovers remain intact.
The source-release receipt identifies the fixed Git commit separately.

## Recompute reporting tables and figures

The narrow source release includes the hash-identified reporting inputs needed by
`local_closing.py`. Generated PNG/PDF files follow Git ignore policy. The complete
34-file supplementary transfer also contains large generated outputs and model
instances that are external/private inputs. Restore those from the verified
private reporting archive before running the full 34-file verification.

```powershell
python experiments/upstream_substitution/paper_closing_v1_20261010/local_closing.py --output scratch/NEW_REPORT_OUTPUT
python experiments/upstream_substitution/paper_closing_v1_20261010/verify_local.py --output scratch/NEW_REPORT_OUTPUT --receipt scratch/NEW_REPORT_VERIFICATION.json
python experiments/upstream_substitution/paper_closing_v1_20261010/build_manuscript.py
```

Reporting runtime: Python 3.11.13, NumPy 1.26.4, pandas 2.3.2 and matplotlib 3.10.6.
Figure byte hashes can depend on plotting/runtime versions; statistical inputs,
user sets and integration definitions are independently verified. A fresh output
directory can be supplied to `local_closing.py --output`; preserve historical
results. The default source and sealed INPUT_MANIFEST identify the original inputs.

## Reproduce scores and seed analysis

Use the recorded Linux numerical environment: Python 3.10.13, NumPy 1.26.4,
SciPy 1.13.1, sklearn 1.5.2, joblib 1.4.2 and threadpoolctl 3.7.0. OpenMP and both
OpenBLAS runtimes were verified at eight threads; exact library builds and CPU
architecture are in the canonical diagnosis and independent-verifier receipts.
Model hash identity alone is insufficient for matching floating score ordering.

Restore private external files without overwriting existing bytes:

```powershell
python experiments/upstream_substitution/paper_closing_v1_20261010/restore_private_cache.py
```

`private_cache_backup_20261010.tar.gz` contains 104 sealed feature/model members.
`REPORTING_SEED_BACKUP_MANIFEST.json` identifies a second private archive containing
all 34 reporting transfer files, 20 DEV refit models and the focused control score
vectors. Verify its archive and member hashes and restore members relative to
`experiments/upstream_substitution`, rejecting unsafe paths and existing byte
differences. Neither archive, raw features, checkpoints nor model instances are
redistributed in Git. The prospective stage additionally needs its upstream
checkpoint and consumer instance; their hashes and availability must be rechecked.

In a new attempt directory with the sealed external inputs restored:

```bash
export OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8
python experiments/upstream_substitution/paper_closing_v1_20261010/diagnose_canonical.py --out NEW_ATTEMPT/canonical
python experiments/upstream_substitution/paper_closing_v1_20261010/run_seed_attempt.py --attempt NEW_ATTEMPT
python experiments/upstream_substitution/paper_closing_v1_20261010/verify_seed_independent.py --attempt NEW_ATTEMPT
```

The entry point uses the unmodified sealed `seed_robustness.py` in a new output
directory. It never fits FINAL models; DEV fold refits have a separate identity.
Strict canonical admission is required before seed outcomes. No rounding, tie
rule changes, tolerance relaxation, class-set substitution or best-seed selection.

Verified attempt: `reproduction_attempt3_8threads`. Its independent receipt verifies
4,680 user-risk rows, 37,440 class-support rows, 3,120 effects, 1,560 support
intersections, 160 conditional user-bootstrap summaries and 702 canonical endpoints
with maximum risk difference zero. The 1-thread diagnostic intentionally fails
canonical admission and is preserved as a numerical control, not as an alternative
seed result. The focused control's JSON serialization failure and saved-vector
recovery are disclosed in the manuscript and score-order receipt.

## Prospective stage

`prospective_inventory/` is metadata-only audit and conditional sample-size
planning. The user authorized resource planning for 80 enrolled users, not an
assumption of 80 valid nonzero pairs or a sealed enrollment decision. A complete
source/cache/backup/inference budget and historical-access/data-integrity preflight
must be confirmed before protocol sealing and new-user outcomes. Do not add,
replace or select users based on effects. Report positive and negative outcomes.
