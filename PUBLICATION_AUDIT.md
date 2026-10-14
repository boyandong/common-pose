# Publication audit

Pre-publication audit of this repository. Every verdict below is produced by a script in
`scripts/` and is reproducible from this checkout, not asserted.

**Audit date:** 2026-09-22
**Repository:** `boyandong/common-pose`
**Scope audited:** the tracked tree at the canonicalization commit

## Reproduce this audit

```bash
python scripts/verify_curated_tree.py     # compile, JSON parse, encoding, local paths
python scripts/publication_scan.py        # secret / path / size / data / personal scans
python scripts/check_readme_claims.py     # README claim and stale-wording audit
python -m pytest tests/ -q                # software and research-contract invariants
```

Both `verify_curated_tree.py` and `check_readme_claims.py` exit non-zero on any failure, so
they can gate a build.

---

## Summary

| check | verdict |
|---|---|
| `SECRET_SCAN` | **PASS** |
| `ABSOLUTE_PATH_SCAN` | **PASS** |
| `LARGE_FILE_SCAN` | **PASS** (1 file > 1 MB, reviewed below; none > 10 MB) |
| `THIRD_PARTY_DATA_SCAN` | **PASS** |
| `PERSONAL_DATA_SCAN` | **PASS** |
| `README_CLAIM_AUDIT` | **PASS** — see below |
| `STALE_CLAIM_SCAN` | **PASS** for the public-facing layer; **retained by design** in frozen artifacts — see below |
| `LICENSE_REVIEW` | **PENDING** — see `docs/licensing.md` |

Curation integrity: every curated file carries a source SHA-256 and a target SHA-256 in
`provenance/CURATION_MANIFEST.json`. The historical research workspace is re-hashed at the
end of every build: a drift fails the build, so no historical file is modified.

---

## SECRET_SCAN: PASS

All tracked text files scanned for credential-shaped strings: OpenAI / Anthropic / GitHub /
AWS / Google / Slack / Hugging Face key formats, private-key blocks, SSH public keys,
basic-auth URLs, and password / API-key / token assignments.

**0 findings.** The only long-hex matches in the tree are SHA-256 digests, which are
checksums rather than secrets and are allow-listed by shape, with each allow-listing logged
by the scanner.

## ABSOLUTE_PATH_SCAN: PASS

Scanned for a user-profile directory path, any drive-letter path with a real segment, a
POSIX root home, a POSIX user home, and UNC paths.

**0 findings** after curation. This required real work rather than a clean initial state:
the historical artifacts contained 240 machine-local path references across 66 files,
including a username in both literal UTF-8 and JSON `\uXXXX`-escaped form, a local Anaconda
installation path, and Windows UNC forms. Each was replaced by a role-named placeholder
(`<PROJECT_ROOT>`, `<DB9_DATA_ROOT>`, `<EMG2POSE_VENV>`, …).

Two classes of match are deliberately **not** findings, and the reason is recorded in the
scanner:

* **Placeholders.** `<PROJECT_ROOT>\data` contains drive-letter-shaped text only when read
  out of context; the scanner requires a non-`<` character before the drive letter.
* **Windows path grammar examples in prose.** Comments such as `("C:\..." contains ':')`
  describe path syntax and name nothing on a machine. The scanner requires a real path
  segment after the separators.

## LARGE_FILE_SCAN: PASS

All tracked files, **under 10 MB total**.

| bucket | count |
|---|---|
| > 100 MB | 0 |
| > 50 MB | 0 |
| > 10 MB | 0 |
| > 1 MB | 1 |

Largest files:

| size | path |
|---|---|
| ~1.46 MB | `experiments/db9_posture/results/posture16_results.json` |
| ~0.88 MB | `docs/REPETITION_AUDIT.json` |
| ~0.72 MB | `experiments/db9_posture/results/full_db9_results.json` |
| ~0.57 MB | `audits/db9/channel_forensic/artifacts/VERDICTS.json` |
| ~0.51 MB | `docs/DB9_FILE_AUDIT.json` |
| ~0.38 MB | `docs/CORPUS_GATE.json` |

The single file above 1 MB was reviewed rather than waved through: it is the per-subject and
per-class result record for the historical DB9 posture run, with no raw data, no
per-participant identifiers, and no third-party content. It is superseded as a *benchmark*
by `artifacts/FINAL_VALIDATION.json` (77 participants, official 8 configurations) but is kept
because it is the evidence for the historical arm.

`audits/db9/channel_forensic/artifacts/FINAL_VALIDATION.json` is the 77-participant
revalidation record and is the largest file added during canonicalization. It contains
per-channel agreement statistics and confusion matrices — aggregate results, no raw signals.

## THIRD_PARTY_DATA_SCAN: PASS

0 files with a data or vendor-artifact extension (`*.mat`, `*.h5`, `*.hdf5`, `*.npz`,
`*.npy`, `*.pkl`, `*.ckpt`, `*.pth`, `*.pt`, `*.safetensors`, `*.onnx`, `*.zip`, `*.tar`,
`*.xlsx`, `*.pdf`, `*.png`, `*.mp4`, …).

**No third-party dataset, model checkpoint, or large experiment output is redistributed.**
`.gitignore` blocks these categories repository-wide. Directory patterns are anchored with a
leading `/` where they describe a project-root location, because an unanchored pattern such
as `artifacts/` or `logs/` matches at any depth and silently excludes the frozen audit
artifacts this repository exists to publish. That exact defect was caught by comparing
`git ls-files` against the working tree.

Datasets used by the project — Ninapro DB9, emg2pose, KIN-MUS UJI, KINE-ADL BE-UJI, MyoKi —
are referenced by official source, DOI and access date only. See `docs/reproducibility.md`
and `audits/dataset_admission/pose_api_admission/OFFICIAL_SOURCE_REFERENCES.md`.

The emg2pose baseline is **not vendored**: it is CC-BY-NC-SA-4.0 with a bundled UmeTrack
under CC-BY-NC-4.0, so it is located through `COMMON_POSE_EMG2POSE_BASELINE` and cloned by
the user. The one algorithmic rule reproduced from it is reimplemented in four lines of
NumPy from its published definition, and cross-checked against the official helper at
runtime.

## PERSONAL_DATA_SCAN: PASS

Scanned for mobile numbers, identity-document numbers, labelled student or participant
identifiers, name/e-mail/phone fields attached to a participant or rater, and
phone-labelled digits.

**0 findings.** The human annotation lane contributes only ontology and protocol
definitions; all per-annotator raw data, annotator identities, hidden sample manifests and
unblinding material are withheld. See
`audits/human_semantic_validation/README.md` §3 for the exclusion list and its reasoning.

Earlier revisions of this scanner produced ~2,600 false positives, because an unanchored
18-digit pattern matches ordinary floating-point numbers and an unanchored email pattern
matches version strings such as `3.11.13`. Those patterns were tightened rather than the
findings being waived; the tightening is visible in `scripts/publication_scan.py`.

## STALE_CLAIM_SCAN: PASS for the public layer, RETAINED by design in frozen artifacts

The canonicalization superseded several published claims. The public-facing layer
(`README.md`, `docs/README.md`, `docs/research_status.md`, `docs/db9_trusted_subset.md`,
`docs/reproducibility.md`, `docs/licensing.md`, `src/common_pose/tasks/posture.py`,
`src/common_pose/api/dof.py`, `tests/`) was checked by `scripts/check_readme_claims.py`
against a required/stale pattern list and is clean.

The following stale statements are **deliberately retained inside frozen artifacts**, because
rewriting a frozen artifact destroys the record of how the conclusion changed:

| artifact | retained statement | superseded by |
|---|---|---|
| `audits/db9/trusted_pose/TRUSTED_DB9_POSE_v1.json` | `n_subjects: 37` | `FINAL_VALIDATION.md` §1 (77/77) |
| `audits/db9/channel_forensic/DB9_FORENSIC_DECISION.md` | 37-subject coverage; `CMC5` = `CASE_B` | `FINAL_VALIDATION.md` §1, §2 |
| `audits/db9/channel_forensic/FLAGGED_CHANNEL_FORENSICS.md` | 37-subject figures; `CMC5` `CASE_B` | `FINAL_VALIDATION.md` §1, §2 |
| `audits/db9/channel_forensic/artifacts/DECISION.json`, `VERDICTS.json` | same, as frozen machine output | same |
| `audits/dataset_admission/**` | the withdrawn `shared10` semantics | `ADMISSION_DECISION.md` §4 records the withdrawal in the same lane |
| `audits/human_semantic_validation/**` | the pilot-era ontology wording | flagged in that lane's `README.md` §4 |

Each of these is mapped to its replacement in the table above, and
`docs/research_status.md` §E states per item whether the artifact is `SUPERSEDED`,
`INVALIDATED` or `WITHDRAWN`. The rule the repository follows is: **state the status, do not
rewrite the artifact.**

### Corrections made during canonicalization, not merely restatements

Three defects were found and fixed rather than documented around:

1. **`src/common_pose/tasks/posture.py` defined `HANDSHAPE_MOVEMENTS` as `(1,…,8,17)`** while
   its own module docstring said movement IDs 1–8 only. The official protocol names movement
   17 *"Wrist extension with closed hand"*, so it is a wrist movement. The constant now
   contains 1–8, and the excluded movements are named explicitly.
2. **`tests/test_api_contract.py` asserted the superseded task** — `movement_ids == (1,…,8,17)`,
   9 classes, chance 1/9 — while a later test in the same file asserted 8 classes. The suite
   was internally contradictory and passed only because the old constant matched the old
   assertion. The superseded assertions were updated to the authoritative 8-class definition.
   **This was a scientific-criteria correction, not a weakening:** the updated test is
   stricter, it additionally pins the frame cap and identity key, and it records in its own
   docstring why it changed.
3. **`src/common_pose/api/dof.py` contained unverifiable precision** — claims such as
   "inverted in 54 of 77 subjects" and "responds to a fist in only 35 of 77 subjects" that
   cannot be derived from `FINAL_VALIDATION.md`. Those were replaced with the figures the
   artifact actually reports (agreement and magnitude-ratio pairs), and the verdict
   *changes* (`INCONCLUSIVE → DROP` for `PIP3` and `DIP4`) are now stated directly.

## LICENSE_REVIEW: PENDING

**No LICENSE file is included and no repository-wide open-source licence has been chosen.**
This is a deliberate outcome, not an omission: several dependencies carry non-commercial and
share-alike terms whose implications for this repository's lineage have not been reviewed.

The wording in `docs/licensing.md` was tightened during canonicalization. It previously
stated an absolute — *"No third-party code is redistributed"* — while file-level lineage
review is still unresolved. It now reads:

> No known third-party code is intentionally redistributed in this curated repository;
> repository-wide licensing remains pending provenance review.

The hedge is deliberate: several curated files come from a historical workspace whose
individual file lineage has not been traced to a third-party origin, and the negative claim
is the strongest statement the evidence supports. It is not a claim that every line has been
proven original.

---

## README_CLAIM_AUDIT: PASS

Enforced mechanically by `scripts/check_readme_claims.py`, which asserts both the presence of
required content and the absence of stale or unsupported wording.

### Claims and their evidence

| README claim | artifact |
|---|---|
| 8 KEEP / DROP / INCONCLUSIVE channel membership | `audits/db9/trusted_pose/TRUSTED_DB9_POSE_v1.json` |
| subset frozen before any classifier ran | artifact field `frozen_before_any_classifier: true` |
| subset SHA-256 `e51dde6e…` | `audits/db9/trusted_pose/TRUSTED_SUBSET_SHA256.txt` |
| revalidated across **all 77 participants**, 0 of 8 KEEP changed | `audits/db9/channel_forensic/FINAL_VALIDATION.md` §1 |
| official task = movement IDs 1–8 only; movement 17 is a wrist movement | `FINAL_VALIDATION.md` §4 |
| historical 0.8556 / trusted 0.7479 / chance 0.1250 / macro-F1 0.7460 | `artifacts/FINAL_VALIDATION.json` |
| class 4 recall 0.495, kept separately visible | `FINAL_VALIDATION.md` §4 |
| CMC5 shares the raw column used by `WRIST_F` | `FINAL_VALIDATION.md` §2 |
| emg2pose IK failures 15.6 %; 16.09° vs 12.48° MAE | `docs/joint_angle_definition.md`, `docs/smoke_test_evidence.json` |
| four `shared10` columns had wrong semantics | `audits/dataset_admission/ADMISSION_DECISION.md` §4 |
| S6 formal endpoint interrupted at 200/396 | `audits/human_semantic_validation/README.md` §4 |
| 60 tests | `python -m pytest tests/ -q` |

`tests/test_api_contract.py::test_frozen_utility_record_is_self_consistent` re-derives the
published utility ratios from the transcribed numbers, so a transcription error in a README
table fails the suite rather than propagating.

### Claims deliberately not made

Every bullet in the README's "What Is Not Yet Demonstrated" section is checked for presence
by the claim script. The README states, without hedging, that the project has **not**
demonstrated: upstream-estimator substitution; cross-dataset numerical coordinate
equivalence; arbitrary or universal downstream task reuse; reliable cross-dataset open-set
rejection; a deployment-grade or frozen Common Pose API; or multi-user end-to-end
EMG → Common Pose → task generalisation.

`docs/research_status.md` §D and §E preserve the negative and superseded results, including
the branch where DB9 channel cleaning *increased* false acceptance and the three
independently withdrawn claims.

### Known residual risks

1. **`COMMIT PENDING` in historical provenance.** Several frozen artifacts record it because
   the research workspaces predate version control. This repository starts a clean history
   and does not carry the old one. The strings are accurate and were not upgraded.
2. **The trusted subset artifact still says `n_subjects: 37`.** It is frozen and preserved
   unmodified; `FINAL_VALIDATION.md` is the addendum, and both `docs/research_status.md` §E1
   and `docs/db9_trusted_subset.md` §4.1 explain the discrepancy at the point of use.
3. **The human-annotation endpoint is not recoverable.** Its formal round was interrupted by
   a diagnostic model-unblinding at 200 of 396 items. No endpoint is published anywhere in
   this repository, and the reason is recorded in the lane's README.
4. **Curated artifacts were edited by curation.** Path substitution changed the bytes of some
   copied files. `provenance/CURATION_MANIFEST.json` records, per file, whether it was altered
   and which placeholder classes were substituted. Byte identity is claimed only where it
   actually holds — the two `FINAL_VALIDATION` artifacts are byte-identical to source; the
   ported driver is not, because curation adds a provenance header.
5. **The DB9 `DROP`/`INCONCLUSIVE` split is artifact-frozen, not re-derived here.** The
   revalidation reports that `PIP3` and `DIP4` move to `DROP` at 77 participants under the
   frozen rules. Those two changed verdicts are **not** written back into
   `TRUSTED_DB9_POSE_v1.json`; they are recorded in `FINAL_VALIDATION.md` and in
   `docs/research_status.md` §A1, and the frozen artifact's own exclusion lists remain as
   produced. A consumer that reads only the artifact will see the 37-participant verdicts.
