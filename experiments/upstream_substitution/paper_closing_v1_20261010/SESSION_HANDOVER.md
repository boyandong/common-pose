# CommonPose closing and seed reproduction handover, 2026-10-10

## Objective — preserve full active goal

User authorized: local paper closing → recover cloned-cache access and complete
20-seed robustness → choose score-only based on positioning → new-user frozen
strong-baseline confirmation. User explicitly chose limited empirical selective
preservation, prioritizing closing and new-user confirmation; defer score-only.
The active goal is NOT complete. Do not reduce it to local table generation.

## Frozen decisions

V1 and the 20261009 supplement remain unchanged. All work here is post-V1.
U ordinary / B original seven-method fixed-common reference-class risk; same
accepted counts; no best-seed selection; seeds 20261009..20261028. Preserve all
original class sets and support omissions. Examined FINAL cannot independently
confirm a revised method. Flip is consumer-output mismatch, not semantic accuracy.
No no-TTA adoption, method tuning, protected-cohort access or new user selection.

## Verified state

- `local_closing.py --freeze-inputs` completed; `verify_local.py` PASS.
- 400 shared-user curve-support points; 546 user/method target-risk areas;
  468 paired area effects; 24 area summary medians/sign counts agree with the
  preexisting independent audit. 34 original transfer hashes still match.
- Fixed-user 30%-100% curves use all 19 DEV / 20 FINAL users. Dense diagnostics
  explicitly vary their shared-user count and leave zero-user risks undefined.
- FINAL U/B corrected figures visually inspected, including the support panels.
- Detailed user effects, class service/support, original seven-threshold user
  and class tables, reconstructed deployment rows, target area tables, and
  reproduction lineage are in `results/`. Original and reconstructed sources
  are named separately. Manuscript-ready narrative and fixed Git release remain
  unfinished.
- New cloned server connected and scientific cache audit PASS: 39 feature NPZs,
  382113110 bytes, all sidecar seals and shape/label checks; 34 scientific artifact
  hashes; original frozen U/B model hashes. See REMOTE_CACHE_VERIFICATION.json.
- Remote private backup generated: private_cache_backup_20261010.tar.gz,
  384382955 bytes, SHA256
  79241d7fdf9006b2c6cb95c6a88ac9f85ba19519931ce9e0097b53dcce25283cc,
  104 members. It is NOT downloaded locally yet. CACHE_BACKUP_MANIFEST.json is
  local; do not confuse the manifest with a local completed backup.

## Scientific evidence / incomplete seed experiment

`seed_robustness.py` seals its spec/code and gates seed analysis on canonical
20261009 30% risk agreement with original tables to 1e-12. FINAL uses already
sealed model instances. DEV refits original fold specifications separately and
records this different identity because old fold scores/models were not saved.

Attempt 1 failed before fitting due to a CSV UTF-8 BOM/header issue. It was fixed
using utf-8-sig before new seed outcomes. Log preserved as seed_run_attempt1.log.
Attempt 2 fitted the DEV fold models, then failed canonical admission:

    FINAL B, user 299b130307, class_model, ordinary_risk:
    recovered minus original = 0.00010944511327570794 (0.0109445 pp)

No 20-seed results, summary or completed progress receipt were produced. Do not
report robustness complete. The new fold model files in remote seed_results are
partial attempt artifacts, not original fold instances or validated results.

## Unknown / contaminated state and likely cause to test

Hash equality does not guarantee matching numerical scoring/sort order. Crucially,
the old tools/run_pipeline.sh exports OMP_NUM_THREADS=8,
OPENBLAS_NUM_THREADS=8, MKL_NUM_THREADS=8. This seed attempt used OMP=1 and
OPENBLAS=1 (MKL not explicitly set). That departure was an execution mistake.
Class-only logistic scores can be sensitive to tiny numerical differences within
equal predicted-class inputs; this is a working hypothesis, NOT a verified cause.

Next session must first restore original numerical settings and inspect same-class
score uniqueness/precision and canonical score ordering. Do not round scores,
collapse class scores, loosen admission thresholds or silently change tie rules
to obtain agreement. Any such method correction needs separate disclosed identity.
If original scores remain unrecoverable, retain an explicit reconstruction drift
analysis and establish an appropriate prospective rule before any new confirmation.

Original cache byte identity is unavailable. Upstream checkpoint training user
membership and current untouched-user inventory remain unresolved. The historical
164-candidate list predates opening the 20-person FINAL and cannot be reused intact.

## External runtime state — successor MUST reverify

- SSH root@connect.westc.seetacloud.com port 47514, user-provided password kept
  only in conversation, not saved in scripts/files.
- Host key SHA256 (same as cloned old host):
  962677eaf342b0d70d757796b387fe83964884f33f66284ff37e2fc6cf1496a7.
- Repo /root/work/common-pose; base experiments/upstream_substitution.
- Source lane paper_supplement_v1_20261009; this lane paper_closing_v1_20261010.
- Runtime interpreter /root/miniconda3/envs/commonpose-supplement/bin/python,
  Python 3.10.13, NumPy 1.26.4, sklearn 1.5.2. Generic `python` absent from PATH;
  /root/miniconda3/bin/python is available (3.12.3).
- Attempt-2 PID 1916 definitively absent from /proc at final inspection;
  seed_run.log ends in AssertionError. This is a terminal failed run, not a
  transient observation timeout. No automatic restart was performed after it.
- Main local SSH transport session closed normally. Unauthenticated second
  transport was deliberately cancelled before any backup download.
- Do not trust old handles. Reverify /proc, log, receipts and hashes before
  deciding to resume/restart. Preserve current partial seed_results and logs.

## Worktree state

HEAD before this work: 76f0e9e1f0334a90f72def9d9adc4bc95e1243c6. Existing unrelated
modifications remain. New closing lane is untracked; no commit or push. Figures
and model/archive outputs follow Git ignore policy. Do not force-add private
cache/raw data/checkpoints or bulk-stage the working tree.

## Next actions

1. Reverify cloned endpoint and frozen inputs. Download and hash-check the private
   cache backup so another clone/outage cannot erase the only feature copy.
2. Preserve failed attempts. Restore original 8-thread numerical environment;
   diagnose canonical class-model score/order mismatch in a separately named
   reproduction attempt before generating seed outcomes. Do not re-fit FINAL.
3. Complete 20-seed user/support results and independently verify canonical risks,
   all per-seed effect denominators, frozen class sets and same accepted counts.
4. Finish manuscript tables/narrative and narrow reproducible Git commit, clearly
   labeling late AUC, original confirmation, reconstruction and DEV refitting.
5. Score-only decision is already made: defer under limited empirical positioning.
6. Audit identities/access including all old FINAL users and protected sets;
   reverify metadata/tar-index hashes and frozen upstream evidence. Plan sample size
   around U vs boundary distance and B vs matched class model, not full-vs-coverage.
   Before any new outcomes freeze a separate new-cohort protocol and instances.

### Sample-size planning observation (not a registered enrollment target)

Read-only conservative sign-test scenarios used two-sided alpha .025 per endpoint
for two comparisons. If the true positive-user probability is .70, estimated
power at N=30 is .4315, N=70 .8787, N=80 .9084; at probability .80, N=30 .8713.
These are conditional binomial scenarios, not proof of sufficient sample size,
not magnitude/CI precision planning, and not an enrollment decision. Both-endpoint
success needs separate joint-power consideration. Discuss budget/precision after
auditing eligible counts; do not silently select 20–30 based on optimistic effects.

## Do NOT

Do not retry in this incident session; hide the canonical failure or alter
scientific tolerances; overwrite frozen lanes or failed-attempt evidence; treat
DEV refits as original fixed-score sensitivity; report cached metadata as scores;
use seeds as independent users; impute absent classes as zero; tune or replace
users based on confirmation outcomes; call downstream-unexposed upstream-unseen.

## Session health and recommended successor

Repeated execution repairs and the newly discovered numerical reproduction issue
trigger the repository's Session Hygiene Protocol. This session now serves as
forensic record. Handover instead of another seed retry here; the overall goal
remains unfinished and active. Recommended new session:

COMMON-POSE-CLOSING-20261010-SEED-REPRODUCTION

Recommended incident record name:
COMMON-POSE-INCIDENT-20261010-CANONICAL-SCORE-DRIFT

Suggested successor prompt: Continue the full authorized closing → seed robustness
→ limited-paper decision (score-only deferred) → new-user confirmation objective.
Read this SESSION_HANDOVER.md, AGENTS.md and CLOSING_SPEC.md. Reverify external
state and first investigate canonical score/order reproduction under the original
8-thread environment. Preserve every frozen artifact and failed attempt.

## Forensic addendum after successor dispatch

Execution successor: 01a123d4-c876-7ed3-9d94-f466f725a2ad. See
SUCCESSOR_DISPATCH.json. The prose backup hash above has a transcription error;
use CACHE_BACKUP_MANIFEST.json and FORENSIC_ERRATUM_20261010.md instead. That erratum
also explains authorized source-credential retrieval if read_thread omits user
message bodies. The source session performs only forensic record maintenance and
read-only successor monitoring; it does not retry scientific execution.
