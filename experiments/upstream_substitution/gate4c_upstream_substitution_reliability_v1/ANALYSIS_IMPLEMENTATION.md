# Gate4C analysis implementation lock

The scientific definitions remain those in `GATE4C_PLAN.md` SHA256 `f346608139d1386947f7200c3fd80b93abcdec4e1fe385c2b647bf756eaa2332` for `COHORT_MANIFEST.json` SHA256 `db61d9c75510d78e17b3858943bc3dd052dab61aa041dc260c84e064e619bead`.

Before opening any Gate4C user-level output or outcome summary, freeze `scripts/verify_and_analyze.py` SHA256 `522e536997b6e482baed3ddc678156f8c014528ac2eca567e607d18183e9087f`. Run `--verify` first to require exact 926-file membership, sealed runner/plan/cohort identities, receipt/output SHA256, shapes, masks/counts, classes and probabilities. It writes an immutable `RESULT_INTEGRITY.json` with a SHA256 sidecar only after all checks pass. Run `--analyze` only when that report is sealed PASS.

Analysis uses stored per-file float32 trusted-8 pose, standardized API values and class probabilities, plus original integer `Y_GT`/`Y_PRED` outputs from the identical frozen head. The secondary Fisher diagnostic applies the same frozen LDA `transform` to the stored standardized API values. Within each user, pose-error deciles use stable ascending sort and ten equal-count chunks. Spearman associations are null when either variable is constant. A scalar cross-user summary and bootstrap CI are null if any planned VALIDATION user has an undefined value; no user is silently dropped. The user bootstrap has 10,000 resamples with seed 20260924. The 10,000 paired-block floor only controls the full-cohort feasibility status, not user inclusion. No result was used to choose these handling rules.

Do not edit the code or this lock after outcome review. Any actual implementation error must be recorded as a separately hashed mechanical amendment before rerun, with prior result artifacts preserved.
