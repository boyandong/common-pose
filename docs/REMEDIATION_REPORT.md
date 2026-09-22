# Session 3 — confirmatory pipeline remediation report

**Scope:** fixes required by the independent Work audit, before the 77-subject
confirmatory run. **The 77-subject classification experiment was NOT run**, and
**no new-subject classification outcome was inspected**.

Status of the two standing gates:

| gate | state |
|---|---|
| do not run the 77-subject replication | **honoured** — not run |
| do not inspect new-subject classification outcomes | **honoured** — see §11 |

Acquisition state at the time of writing: **40/77** (DB1 27, DB2 6, DB5 7);
outcome-unseen so far = DB2 28–33. Fetcher alive.

---

## 1. Files / functions changed

| file | change |
|---|---|
| `posture_decoder/experiments/confirmatory_policy.py` | **new.** Primary lock (`PRIMARY_MODEL`, `primary_run_key`, `select_primary`, `assert_no_score_based_primary_selection`); cache validity key + `cache_is_usable`; cohort record writer; hard identity assertions (`assert_corpus_identity`, `IdentityAssertionError`, `expected_slots`, `source_db_of`). |
| `posture_decoder/experiments/run_full_db9.py` | primary obtained via `cp.select_primary` (no `max`); `loso_best` removed; confusion now reported for the **primary** configuration with a tier label; forced rebuild with automatic quarantine of any pre-existing cache; `assert_corpus_identity(..., require_full=True)` gate; drift controls relabelled and annotated. |
| `posture_decoder/experiments/run_posture16.py` | new pure helpers `central_third_bounds` and `select_central_valid`; extraction reordered so boundaries are fixed on the **original** interval before invalid frames are removed; `unusable` repetitions are collected and reported; `MIN_VALID_CENTRAL_FRAMES` added; the silent `central.size < 5 → central = idx` substitution removed. |
| `posture_decoder/tools/fetch_db9_member.py` | `archive_size` → `archive_head` (Content-Length + ETag + Last-Modified); `_loads_as_exercise_b` → `_validate_exercise_b` (CRC recomputed locally, size, exercise letter, full label set, 6 repetitions per movement); reuse path now runs the full validation; remote-version stability re-checked after fetching; **manifest write is fatal and atomic**. |
| `posture_decoder/tools/audit_db9_files.py` | misleading "recorded-field collision" semantics replaced with the correct `(source_database, recorded_subject)` injectivity check plus an explicit statement that equal in-file ids across source databases are expected. |
| `posture_decoder/tools/freeze_confirmatory_spec.py` | BOM-aware log decoding; also emits the machine-derived cohort record. |
| `posture_decoder/tools/make_confirmatory_manifest.py` | **new.** `--mode prepare` / `--mode finalize` provenance manifest. |
| `posture_decoder/tools/verify_corpus_integrity.py` | **new.** corpus-wide integrity check, incl. the cross-source decimation check. |
| `representation/db9_to_canonical16.py` | provenance text cleaned; `cross_dataset_polarity_confidence` → `"FROZEN (sign)"`; new `cross_dataset_axis_identity_confidence` = `"NOT PROVEN (magnitude/geometry)"`; schema summary keys updated. |
| `docs/DB9_CANONICAL16_MAPPING.md`, `posture_decoder/report.md` | stale "unresolved" / "no sign flipping" statements removed; single consistent provenance statement added. |
| `posture_decoder/tests/test_confirmatory_pipeline.py` | **new.** 41 tests. |

## 2. Test results

```
posture_decoder/tests + representation/tests/test_db9_to_canonical16.py
65 passed
```

41 new confirmatory-pipeline tests covering all ten required properties:
77 = 27+40+10 assertions (incl. 5 parametrised incompleteness cases, duplicates,
wrong source, conflicting recorded ids); source-tuple injectivity and the
expected cross-source id reuse; **primary model cannot be selected from score**;
old/incomplete cache cannot be silently reused; thumb-AA frozen sign; canonical15
= canonical16 − exactly thumb AA; canonical12 = canonical16 − exactly four DIP;
central-third boundaries computed before invalid removal; acquisition CRC
re-check on reused members; manifest generation.

Two of these are designed to be able to fail:
`test_primary_cannot_be_displaced_by_a_higher_scoring_secondary` (a competitor at
0.99 must not displace the primary at 0.60) and
`test_static_guard_actually_catches_an_offender`.

The central-third test is the sharpest: with 40 invalid frames at the *start* of a
300-frame interval, the correct implementation selects frames 100–199, whereas
removing invalid frames first would have selected 126–186. The test asserts the
former and explicitly asserts it is *not* the latter.

Not counted: one pre-existing Session 2 test
(`test_validity_matches_official_get_ik_failures_mask`) fails because the
official `emg2pose` package is not importable in this interpreter — it requires
Session 2's `.venv-emg2pose310`. Unrelated to these changes.

## 3. Acquisition-integrity changes

* Reuse is never accepted on size alone, nor on "the MAT loads", nor on
  `max(restimulus) == 17` alone. Every reused member now has its **CRC-32
  recomputed locally** and compared with the value the archive's central
  directory declares, plus uncompressed length, the source-aware exercise letter,
  the full movement label set 1–17, and exactly 6 repetitions per movement.
* **Remote version identity.** The archive is HEADed once for ETag and
  Last-Modified; if neither is exposed the fetch is refused
  (`NO_VERSION_IDENTITY`); after fetching, the archive is HEADed again and a
  change yields `REMOTE_VERSION_CHANGED` with the result rejected, so ranges can
  never be silently combined across two uploads.
* **Manifest writes are fatal and atomic** (temp file + `fsync` + `os.replace`);
  the previous silent `except: pass` is gone.
* Corpus integrity (`docs/CORPUS_INTEGRITY.json`, 38 subjects at the time): one
  channel vocabulary matching the official table, one NaN pattern (`[5]` =
  `MCP2_a`), 102 repetitions per subject in every source database, no problems.

## 4. Subject-identity assertions

`cp.assert_corpus_identity(..., require_full=True)` runs before any experiment
and raises `IdentityAssertionError` unless: total 77; DB1 = slots 1–27, DB2 =
28–67, DB5 = 68–77, each exactly once; no duplicate and no missing global slot;
each slot reports exactly one in-file id; and `(source_database,
recorded_subject)` is injective.

The archive slot is the identity. The in-file `subject` field is provenance
metadata only. The previous misleading check — which treated equal local ids from
different source databases as a "collision" — is fixed: with 40 subjects
acquired, DB1 slot 1, DB2 slot 28 and DB5 slot 68 **all record `subject = 1`**,
and that is now reported as expected rather than as a defect.

## 5. Cache policy

The confirmatory driver **ignores existing representative-posture caches
entirely** and rebuilds unconditionally from the validated raw Exercise-B files.
Any pre-existing cache is moved to `_invalidated/<name>.<timestamp>` rather than
deleted, so the invalidation is visible and reversible.

Existing 22-subject caches were quarantined by hand into
`data/db9_posture16/_invalidated/` with a README recording exactly why: they
predate both the frozen thumb-AA sign transformation and the central-third
ordering fix.

For any future opt-in caching, `cp.cache_validity_key` requires the exact input
file list with per-file size and SHA-256, the DB9→canonical schema hash, the
extraction-code hash, the frozen-spec hash, the representation name and a cache
schema version. `cp.cache_is_usable` returns not-usable for a missing metadata
file, a metadata file with no `validity_key` (which is how a pre-policy cache
looks), or any field mismatch — there is no partial-trust path.

## 6. Primary-model lock

```
PRIMARY_MODEL          = "lda"
PRIMARY_MODEL_CONFIG   = {"solver": "lsqr", "shrinkage": "auto"}
PRIMARY_NORMALIZATION  = "train_only_zscore"
PRIMARY_REPRESENTATION = "canonical16"
```

`cp.select_primary(results)` returns the frozen key **by identity** and contains
no `max`, `argmax` or ranking. If the primary configuration is absent it returns
`(key, None)` and the driver raises rather than falling back. `loso_best` and the
`max(..., key=...accuracy...)` selection were deleted. Verified: with a
competitor at 0.99 the primary still returns 0.60.

`cp.assert_no_score_based_primary_selection` is a static guard run by a test
against the driver source; it flags `best_key`, `best_model`, `winner`, and
`max(..., key=lambda ... accuracy)` patterns. It is itself tested against a
positive control so it cannot silently pass everything.

## 7. Central-third extraction fix

Order of operations is now: (1) labelled interval in original sample
coordinates; (2) central-third boundaries from its length; (3) select frames
inside those boundaries; (4) *then* drop invalid frames; (5) require at least
`MIN_VALID_CENTRAL_FRAMES = 5` valid frames.

If too few valid frames remain the repetition is **reported as unusable** in
`meta["unusable_repetitions"]` with `n_original`, `n_central` and
`n_valid_central`. The old behaviour — silently substituting the full interval
when the central third was too small (`if central.size < 5: central = idx`) — is
removed, so the target interval can no longer be quietly redefined.

## 8. Drift-control status

Relabelled and documented as **ORACLE / TEST-SUBJECT-CALIBRATED UPPER-BOUND
ANALYSES**, not leakage-free controls:

* `drift-corrected` subtracts a trajectory estimated from the **held-out
  subject's own rest samples** — a test-subject-derived statistic;
* `drift-only` locates measurement time using the **true movement label**;
* only `permutation` is flagged as leakage-free.

The results block carries `validity.tier`, `leakage_free: false`,
`why_not_leakage_free`, `may_be_cited_as` / `may_not_be_cited_as`, and
`primary_result_depends_on_drift_correction: false`. The primary
posture-identifiability result does not depend on drift correction, and these
analyses may not be cited in its support.

## 9. Thumb-AA provenance cleanup

Production rule unchanged and still DB9-side only:
`thumb_cmc_ab_adduction *= -1`, applied in `representation/db9_to_canonical16.py`.
Session 2's `canonical_hand.py` is untouched (a test asserts it contains no
`FROZEN_DB9_SIGN` and no `to_canonical18`).

All stale text removed — a test scans four files for `MEDIUM -- UNRESOLVED`,
`polarity_UNRESOLVED`, `no sign flipping` and `no sign flip is applied`, and
asserts none remain. The schema now carries:

```
cross_dataset_polarity_confidence      : "FROZEN (sign)"
cross_dataset_axis_identity_confidence : "NOT PROVEN (magnitude/geometry)"
```

**The claim is scoped precisely.** The *sign* correspondence is frozen with
geometric and documented-anatomical support. It is **not** claimed that DB9's
`CMC1_A` and UmeTrack's `THUMB_CMC_AA` are proven to be identical rotation axes
in magnitude or geometry — they are not (emg2pose's `THUMB_CMC_FE` moves the
in-plane web angle ≈3× more strongly per radian). That residual uncertainty is
exactly why `canonical15_noThumbAA` exists as a pre-registered control. One
statement, in `docs/DB9_CANONICAL16_MAPPING.md`, is declared authoritative.

## 10. Confirmatory-run manifest format

`posture_decoder/tools/make_confirmatory_manifest.py`:

* `--mode prepare` refuses to emit a manifest unless the corpus passes
  `assert_corpus_identity(require_full=True)` — a manifest can never describe an
  incomplete corpus. Records: manifest version, creation timestamp, exact
  command, interpreter (version/executable/platform), package versions (numpy,
  scipy, sklearn, matplotlib, h5py), `frozen_spec_sha256`,
  `db9_canonical16_schema_sha256`, `cohort_record_sha256`, SHA-256 of all 12
  pipeline code files, the primary model/config/normalisation/representation with
  its selection rule, class vocabulary, representations, extraction rule, drift
  correction, normalisation, metrics, the frozen sign transformation, cohort
  definitions, and the corpus block (n subjects, identity assertions,
  subject → source mapping, and every input file with absolute path, byte size
  and SHA-256). `result_artifacts` is null at this stage.
* `--mode finalize` appends `result_artifacts` (per-file bytes + SHA-256 for the
  data and figure directories) and a `finalized_utc` stamp.

File-level cryptographic provenance throughout; no Git initialisation required.

## 11. Confirmation: no new-subject classification outcomes inspected

**Confirmed.** No classifier was trained, no accuracy/LOSO/metric was computed,
and no prediction was produced in this remediation round. The last
result-producing run in this session was the 34-subject smoke run at
`logs/smoke77b.log` (2026-09-18T00:13), which contained no DB2 subject.

Everything done since was file- and metadata-level only:

* cohort determination (parsing run logs for which subjects entered a
  result-producing run);
* corpus integrity verification (label sets, repetition counts, NaN pattern,
  angle ranges, retained-frame counts per source);
* the DB9 file audit;
* CRC/size/version validation of acquired members;
* tests.

The DB2 subjects now acquired (28–33) have been **loaded only to read their
schema and integrity properties** — sample counts, `restimulus` label sets,
`rerepetition` counts, NaN columns, units. They are recorded in
`docs/CONFIRMATORY_COHORTS.json` as `outcome_unseen`, and separately as
`integrity_only_touched`, because touching a file for integrity is **not**
outcome exposure. Both sets are machine-derived; neither has been hand-edited.

---

## Stopping

Per the stop condition: the 77-subject classification experiment has not been
run, and this round ends here. Awaiting independent Work re-audit before any
confirmatory execution.

Acquisition continues in the background and is unaffected by these changes.

---

# ADDENDUM — final blocking fix: the pre-registered primary confirmatory arm

*Sections 1–11 above are the historical record of the first remediation round and
their counts (acquisition 40/77, 65 tests) are the state at that time. This
addendum supersedes the status table and §2 counts.*

**Status of the two standing gates: still honoured.** The 77-subject
classification experiment has **NOT** been run. No real classification outcome
has been computed or inspected. Everything added below was exercised on synthetic
fixtures only, plus metadata-level assertions over the already-acquired corpus.

## A1. The defect

The independent audit found exactly one blocking defect, in section 9:

`run_full_db9.py` had **no untouched-cohort arm**. `results["primary_confirmatory"]`
was constructed from `loso_out` — the full-77 leave-one-subject-out pass — so the
development-exposed subjects sat **inside** the evaluation that was labelled
primary confirmatory. The frozen `final_evaluation_plan` designates
`2_untouched_confirmation.a_train_exposed_test_untouched` as the PRIMARY
CONFIRMATORY arm and `1_full_77_loso` as *descriptive*, so the driver was
reporting a descriptive number under a confirmatory label. Verdict at the time:
`SAFE TO RUN FINAL 77-SUBJECT CONFIRMATORY EXPERIMENT: NO`.

This was a reporting/design defect, not a numerical one: no result had been
produced, so nothing has to be retracted. Its failure mode would have been a
confirmatory claim resting on an evaluation that included its own development
subjects.

## A2. What was changed

| file | change |
|---|---|
| `posture_decoder/experiments/run_full_db9.py` | **TIER A** added: `evaluate_explicit_partition(...)` fits the scaler and the classifier on the `development_exposed` cohort only, transforms and predicts the `outcome_unseen` cohort **exactly once**, and asserts the frozen LDA configuration instead of trusting the factory. **TIER B**: the full-77 LOSO is now stored under `results["full_77_loso_descriptive"]` with an explicit descriptive tier label; the old `results["loso"]` key and the old `primary_confirmatory` assignment are gone. **TIER C**: `results["secondary_confirmatory"]` = `loso_within(...)` restricted to the outcome-unseen cohort. `results["evidence_tiers"]` records which number may carry which claim. Confusion matrices and error decompositions are produced **per tier** by a new `confusion_report(...)` helper that requires a tier key, and figures are tier-tagged (`confusion_primary_confirmatory_*.png`, `confusion_full77_loso_*.png`; the untagged `confusion_loso_*.png` name is no longer written). The cohort partition is **loaded** from the cohort record — `cp.load_cohort_record(args.cohorts)` — and re-validated against the subjects actually present. |
| `posture_decoder/experiments/confirmatory_policy.py` | `EXPECTED_EXPOSED_N = 34`, `EXPECTED_UNSEEN_N = 43`, `load_cohort_record(path)`, `assert_cohort_partition(exposed, unseen, all_subjects)`: exact sizes, disjointness, and union equal to the corpus, with no fallback path. |
| `posture_decoder/tools/make_confirmatory_manifest.py` | `--mode prepare` now **asserts the cohort partition covers the corpus** with `assert_cohort_partition` before writing, refuses to emit a manifest if the cohort record is missing, and records a `confirmatory_arms` block naming arm A (train 34 development-exposed → test 43 outcome-unseen, one shot) plus the B/C tier labels and the rule that B and C may never be substituted for A. |
| `posture_decoder/tests/test_confirmatory_pipeline.py` | 41 → **89** tests. The new ones cover: the partition is loaded and not hard-coded; the driver contains no hard-coded cohort ids; a missing cohort record is a hard error; the shipped cohort artifact partitions all 77 subjects as 34/43; overlap / wrong-size / missing-subject partitions are rejected; the scaler is fitted on train subjects only (verified numerically against the train mean, with a fixture-power check that pooled and train means differ); the primary arm is reproduced **exactly** by an independent `sklearn` recomputation; a class present only in test subjects never enters the fitted model; the primary arm is not a LOSO pass and appears at exactly one call site; the secondary arm reports its cohort and is labelled as *not* an untouched external holdout; the full-77 result is not assigned to `primary_confirmatory`; confusion matrices carry their tier and are internally consistent; figures are tier-tagged. |

## A3. Evidence — what was actually executed

```
posture_decoder/tests + representation/tests/test_db9_to_canonical16.py
89 passed in 8.36s
```

The load-bearing new test is
`test_driver_main_executes_all_three_tiers_end_to_end`. It **really runs
`main()`** with the data layer stubbed (extraction, manifest, drift and
permutation replaced by cheap fixtures, one classifier instead of five, 77
synthetic subjects × 6 postures) and then asserts against the written
`full_db9_results.json`:

* `primary_confirmatory.train_subjects` == the cohort record's
  `development_exposed`; `primary_confirmatory.test_subjects` == its
  `outcome_unseen`; 34 train / 43 test; `test_evaluations == 1`;
  `refit_using_test_subjects is False`; train ∩ test = ∅;
* `set(primary_confirmatory.subject)` == the outcome-unseen cohort — the primary
  arm evaluated exactly those 43 subjects and no others;
* `evidence_tiers.strongest_confirmatory_evidence == "A_primary_confirmatory"`;
  tier B reports 77 subjects and a `B:` label; tier C carries a `C:` label;
* three tier-keyed confusion matrices exist and the arm-A matrix sums to its own
  `n`; both tier-tagged figure families are written and no untagged
  `confusion_loso_*.png` is produced.

This upgrades the fix from *implemented* to *executed*: the tier wiring, cohort
loading, assertions, confusion reporting, figure writing and JSON emission are
observed to run, not merely inspected.

The real-data step that has been executed is metadata-level: PREPARE-mode
manifest generation ran `assert_cohort_partition` against the **77 real corpus
subjects** and passed, so the frozen partition provably covers the acquired
corpus.

```
[manifest] PREPARE -> ..\docs\CONFIRMATORY_RUN_MANIFEST.json
  subjects            : 77 {'DB1': 27, 'DB2': 40, 'DB5': 10}
  identity assertions : PASSED (complete=True)
  frozen spec sha256  : 50c338bed3bf8a346f492abb61002a3e406f45aa3606e506271d026a75dc4196
  schema sha256       : 0ede53b97908460a0700cc78674789ea30303f7f6572a129922765d683ed0f80
  code files hashed   : 12/12
  PRIMARY arm (A)     : train 34 development-exposed -> test 43 outcome-unseen (one shot)
```

The frozen-spec and schema hashes are **unchanged** from the values frozen before
this fix, so no scientific definition moved. Only code and provenance changed,
which is why the 12 pipeline code-file hashes in the manifest did change.

Code identity of the fix (SHA-256, of the exact files this addendum describes):

| file | sha256 |
|---|---|
| `posture_decoder/experiments/run_full_db9.py` | `6b5f10ae69afc667e0db983f84a0c0624870c483dbe99d483782d1bfb6d6529d` |
| `posture_decoder/experiments/confirmatory_policy.py` | `85aea12a0f63139c6df945d1258f2b5e18f1979225495d24671349172e7d50fd` |
| `posture_decoder/tools/make_confirmatory_manifest.py` | `690669045394c4074a3d1189f7904ba6e4d1c1579ae7c439732ecd5afc8a3e96` |
| `posture_decoder/tests/test_confirmatory_pipeline.py` | `265d17c8c45928510faaf70fa75772809c844e9354f9c47fc454a9876685103b` |
| `docs/CONFIRMATORY_COHORTS.json` (frozen partition) | `55a7d511198d3749ad289a3cee5b0e3b31e5cc42a10c9575108133eaf8f924fc` |

The first two are also inside the manifest's `hashes.code_files`, which was
regenerated **after** the last code edit, and all 12 recorded hashes were
re-checked against disk (12/12 match). The cohort record is unchanged from
before the fix, so the partition itself was not touched. There is no Git commit
for this repository; file content hashes are the execution provenance
(`COMMIT PENDING`).

`docs/CONFIRMATORY_RUN_MANIFEST.json` was **regenerated in `--mode prepare` and
NOT finalized** (`result_artifacts` is still null). The superseded prepare
manifest is preserved, not overwritten, at
`docs/_superseded/CONFIRMATORY_RUN_MANIFEST.json.<stamp>.prepare-before-primary-arm`.

## A4. What is deliberately NOT done

* The real 77-subject confirmatory run — **not run**, awaiting authorisation.
* No confidence interval or significance test was added to the primary arm even
  though it would be useful: the frozen metric set is accuracy /
  balanced accuracy / macro-F1, and adding a metric is a `WHAT COUNTS` change
  that belongs to the research lead. **Proposal, not implemented.**
* Tier A was not extended to the two control representations
  (`canonical12_noDIP`, `canonical15_noThumbAA`). They remain tier-C
  full-corpus comparisons exactly as pre-registered. Running them on the
  one-shot external partition would be strictly stronger evidence but is a new
  analysis. **Proposal, not implemented.**

Awaiting independent re-audit. This session does not run the experiment.

