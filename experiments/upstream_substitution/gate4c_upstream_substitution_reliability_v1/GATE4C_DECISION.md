# Gate4C frozen result and decision — 2026-09-24

## Status and evidence boundary

**DESCRIPTIVE COMPLETE.** This is the prespecified frozen inference and downstream substitution experiment, not model training. The old Gate4B remains closed for source-authentic structural failure before outcomes. Gate4C uses the prospectively selected 27-user, 926-file cohort (19 DEV, 8 VALIDATION); the entire structurally failed Gate4B session was excluded before Gate4C inference, with no replacement. The 8 VALIDATION users are the primary units of inference. No head, upstream model, adapter, threshold, class mapping, or cohort was changed after outcome inspection.

The remote runner reported `GATE4C_ACQUISITION_COMPLETE 926/926` and `GATE4C_PROGRESS 926/926` on 2026-09-24. The independent receipt/output and frozen-identity audit returned `RESULT_INTEGRITY.status = PASS` for exactly 926 files and 27 users. All 27 users exceed the prospectively set 10,000 paired-valid 50-Hz block floor; the VALIDATION insufficient-user fraction is 0. The analysis implementation was hash-sealed before outcomes were inspected and generated `ANALYSIS_SUMMARY.status = DESCRIPTIVE_COMPLETE` only after that integrity check passed.

| Frozen evidence | SHA256 |
| --- | --- |
| `GATE4C_PLAN.md` | `f346608139d1386947f7200c3fd80b93abcdec4e1fe385c2b647bf756eaa2332` |
| `COHORT_MANIFEST.json` | `db61d9c75510d78e17b3858943bc3dd052dab61aa041dc260c84e064e619bead` |
| `ANALYSIS_IMPLEMENTATION.md` | `c49b9351cce828ec25de4208cc49f36b96887823561906b2e16e4e3c393d610e` |
| `scripts/verify_and_analyze.py` | `522e536997b6e482baed3ddc678156f8c014528ac2eca567e607d18183e9087f` |
| `artifacts/RESULT_INTEGRITY.json` | `8fcdb1d44e7d2f78c7d03a962cff8c772bfe23047954c3e007ce8cad06694c96` |
| `artifacts/USER_METRICS.json` | `87a02645698322d7f7e01b1afb19067104d8d175f4abbc4fc77ff6a0985ec8ef` |
| `artifacts/ERROR_CHAIN_DECILES.json` | `4c03ff117484f7416d86c611cdb26f2c7996d11e4e08285e8bb98db456f22a7e` |
| `artifacts/ANALYSIS_SUMMARY.json` | `81dce686d7cf4ad07717fd01f48da761da2d25a8a94918c9455b6d5ac204e283` |

## Preregistered VALIDATION endpoints

Hard output preservation is agreement of the frozen downstream consumer's class output using predicted pose versus its class output using measured GT pose, on the same paired-valid blocks. Across 8 users, the user median is **0.6571**, IQR **0.5533–0.7042**, range **0.1632–0.7592**. The prespecified 10,000-resample user-bootstrap 95% percentile interval for the user median is **0.4908–0.7438**. No agreement pass threshold was preregistered, so this is not a binary pass/fail claim.

Valid coverage (`paired_valid_blocks / GT_valid_blocks`) is **1.0000 for every VALIDATION user**; its user-median bootstrap interval is **1.0000–1.0000**. This only means prediction validity did not remove additional GT-valid blocks. It does not mean every raw frame or record was GT-valid. Every VALIDATION user passed the paired-block feasibility floor, including the lowest-coverage user with 10,712 paired blocks.

| VALIDATION user | Paired blocks | Hard preservation |
| --- | ---: | ---: |
| `737fb9d2eb` | 60,464 | 0.7592 |
| `76932c8337` | 110,197 | 0.7438 |
| `8e69533c16` | 95,010 | 0.6658 |
| `92f25d4f36` | 66,665 | 0.6484 |
| `9e7c5def0b` | 103,866 | 0.5742 |
| `ab228f34a5` | 10,712 | 0.1632 |
| `b6fa6cd36f` | 55,820 | 0.6910 |
| `e86f1eaf2f` | 97,800 | 0.4908 |

## Secondary evidence and judgement

The VALIDATION median balanced preservation against the GT-path output is **0.3331** (IQR **0.3280–0.3389**); median Cohen kappa is **0.3695**; median user total-variation distance between native class-probability vectors is **0.2260**. These are secondary descriptive measures. GT-path class support is markedly imbalanced in several users, so overall hard agreement alone gives an incomplete account of preservation. For `ab228f34a5`, the hard preservation is 0.1632, kappa 0.0026, and only 10,712 GT-valid blocks remain, although it clears the registered floor. This user remains in the primary analysis. No post-outcome exclusion or threshold change is justified.

Within every VALIDATION user, the highest trusted-8 pose-error decile has a higher decision-flip rate than the lowest decile; the respective ranges across users are approximately **0.50–0.89** and **0.03–0.29**. User-level Spearman associations of pose error with flip are positive, approximately **0.24–0.39**. These observations locate a descriptive error chain, but do not establish whether upstream prediction quality, probability calibration, or the frozen decision boundary is the independent cause of any user's result.

**Scientific judgement:** the frozen substitution is computationally feasible and preserves the reference consumer's hard output to a heterogeneous degree across the eight primary users. Reliability is weak for at least one included user; a uniform cross-user reliability claim is unsupported by these results. No claim of semantic task accuracy, balanced task accuracy, macro-F1, or task-performance delta is identifiable because this cohort has no registered human task labels. The official upstream checkpoint's training-user membership remains unresolved, so these users must not be described as upstream-unseen. The current Gate4C branch is closed descriptively, without tuning or rescue. Any further upstream model, calibration, adapter, shared-DOF, threshold, or task comparison requires a new prospective branch and frozen plan.
