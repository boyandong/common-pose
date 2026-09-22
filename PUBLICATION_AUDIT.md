# Publication audit

Pre-publication audit of this repository, run before the initial public push. Every
verdict below is produced by a script in `scripts/` and is reproducible from this
checkout, not asserted.

**Audit date:** 2026-09-22
**Repository:** `boyandong/common-pose`
**Scope audited:** the entire tracked tree at first commit

## Reproduce this audit

```bash
python scripts/verify_curated_tree.py     # compile, JSON parse, encoding, local paths
python scripts/publication_scan.py        # secret / path / size / data / personal scans
```

`verify_curated_tree.py` exits non-zero on any failure, so it can gate a build.

---

## Summary

| check | verdict |
|---|---|
| `SECRET_SCAN` | **PASS** |
| `ABSOLUTE_PATH_SCAN` | **PASS** |
| `LARGE_FILE_SCAN` | **PASS** (1 file > 1 MB, reviewed below; none > 10 MB) |
| `THIRD_PARTY_DATA_SCAN` | **PASS** |
| `PERSONAL_DATA_SCAN` | **PASS** |
| `LICENSE_REVIEW` | **PENDING** — see `docs/licensing.md` |
| `README_CLAIM_AUDIT` | **PASS** — see below |

Curation integrity: **214 files** copied, each with its source SHA-256 and target
SHA-256 recorded in `provenance/CURATION_MANIFEST.json`. The source workspace was
re-hashed at the end of the build: **0 drifted**, so no historical file was modified.

---

## SECRET_SCAN: PASS

242 text files scanned for credential-shaped strings: OpenAI / Anthropic / GitHub /
AWS / Google / Slack / Hugging Face key formats, private-key blocks, SSH public keys,
basic-auth URLs, and password / API-key / token assignments.

**0 findings.** The only long-hex matches anywhere in the tree are SHA-256 digests, which
are checksums, not secrets — they are allow-listed by shape and each allow-listing is
logged by the scanner.

## ABSOLUTE_PATH_SCAN: PASS

Scanned for a user-profile directory path, any drive-letter path with a real segment, a
POSIX root home, a POSIX user home, and UNC paths.

**0 findings** after curation. This required real work rather than a clean initial state:
the historical artifacts contained **240 machine-local path references across 66 files**,
including a username in both literal UTF-8 and JSON `\uXXXX`-escaped form, a local
Anaconda installation path, and Windows UNC forms. Each was replaced by a role-named
placeholder (`<PROJECT_ROOT>`, `<DB9_DATA_ROOT>`, `<EMG2POSE_VENV>`, …).

Two classes of match are deliberately **not** findings, and the reason is recorded in the
scanner:

* **Placeholders.** `<PROJECT_ROOT>\data` still contains `C:`-shaped text only when read
  out of context; the scanner requires a non-`<` character before the drive letter.
* **Windows path grammar examples in prose.** Comments such as `("C:\..." contains ':')`
  describe path syntax and name nothing on a machine. The scanner requires a real path
  segment after the separators.

## LARGE_FILE_SCAN: PASS

249 files, **8.96 MB total**.

| bucket | count |
|---|---|
| > 100 MB | 0 |
| > 50 MB | 0 |
| > 10 MB | 0 |
| > 1 MB | 1 |

Largest ten files:

| size | path |
|---|---|
| 1.46 MB | `experiments/db9_posture/results/posture16_results.json` |
| 0.86 MB | `docs/REPETITION_AUDIT.json` |
| 0.72 MB | `experiments/db9_posture/results/full_db9_results.json` |
| 0.55 MB | `audits/db9/channel_forensic/artifacts/VERDICTS.json` |
| 0.49 MB | `docs/DB9_FILE_AUDIT.json` |
| 0.37 MB | `docs/CORPUS_GATE.json` |
| 0.22 MB | `audits/db9/channel_forensic/artifacts/FORENSIC_CORE.json` |
| 0.13 MB | `experiments/observability/kinmus_phase/results/real_results_cache.json` |
| 0.12 MB | `audits/dataset_admission/artifacts/COORDINATE_LEDGER.json` |
| 0.12 MB | `audits/db9/coordinate_audit/artifacts/PHYSICAL_ANCHOR_AUDIT.json` |

The single file above 1 MB was reviewed rather than waved through: it is the per-subject
and per-class result record for the frozen DB9 posture task, with no raw data, no
per-participant identifiers, and no third-party content. It is the evidence for the
headline utility numbers, so it belongs in the repository.

## THIRD_PARTY_DATA_SCAN: PASS

0 files with a data or vendor-artifact extension (`*.mat`, `*.h5`, `*.hdf5`, `*.npz`,
`*.npy`, `*.pkl`, `*.ckpt`, `*.pth`, `*.pt`, `*.safetensors`, `*.onnx`, `*.zip`, `*.tar`,
`*.xlsx`, `*.pdf`, `*.png`, `*.mp4`, …).

**No third-party dataset, model checkpoint, or large experiment output is redistributed.**
`.gitignore` blocks these categories repository-wide, including the data directories and
the project-specific scratch prefixes (`_patch*.py`, `_recon_*.py`, `_audit_s*/`).

Datasets used by the project — Ninapro DB9, emg2pose, KIN-MUS UJI, KINE-ADL BE-UJI,
MyoKi — are referenced by official source, DOI and access date only. See
`docs/reproducibility.md` and
`audits/dataset_admission/pose_api_admission/OFFICIAL_SOURCE_REFERENCES.md`.

The emg2pose baseline is **not vendored**. It is CC-BY-NC-SA-4.0 with a bundled UmeTrack
under CC-BY-NC-4.0, so it is located through `COMMON_POSE_EMG2POSE_BASELINE` and cloned by
the user. The one algorithmic rule reproduced from it is reimplemented in four lines of
NumPy from its published definition, and cross-checked against the official helper at
runtime.

## PERSONAL_DATA_SCAN: PASS

Scanned for mobile numbers, identity-document numbers, labelled student or participant
identifiers, annotator/participant name-email-phone fields, and phone-labelled digits.

**0 findings.** The human annotation lane contributes only ontology and protocol
definitions; all per-annotator raw data, annotator identities, hidden sample manifests and
unblinding material are withheld. See
`audits/human_semantic_validation/README.md` §3 for the exclusion list and its reasoning.

Earlier revisions of this scanner produced ~2,600 false positives, because an unanchored
18-digit pattern matches ordinary floating-point numbers and an unanchored email pattern
matches version strings such as `3.11.13`. Those patterns were tightened rather than the
findings being waived; the tightening is visible in `scripts/publication_scan.py`.

## LICENSE_REVIEW: PENDING

**No LICENSE file is included and no open-source licence has been chosen.** This is a
deliberate outcome, not an omission: several dependencies carry non-commercial and
share-alike terms whose implications for this repository's lineage have not been reviewed.
Full reasoning, the dependency table and the four open questions are in
`docs/licensing.md`.

Consequence: the repository is public for reading, review and collaboration, and extends
no rights beyond GitHub's Terms of Service. Anyone wishing to reuse code should open an
issue so the specific file's provenance can be checked and a decision recorded.

## README_CLAIM_AUDIT: PASS

Every quantitative claim in `README.md` was traced to a preserved artifact. The claims
that are **not** made were checked just as deliberately.

### Claims and their evidence

| README claim | artifact |
|---|---|
| 8 KEEP / 6 DROP / 8 INCONCLUSIVE channels; named membership | `audits/db9/trusted_pose/TRUSTED_DB9_POSE_v1.json` |
| subset frozen before any classifier ran | artifact field `frozen_before_any_classifier: true` |
| subset SHA-256 `e51dde6e…` | `audits/db9/trusted_pose/TRUSTED_SUBSET_SHA256.txt` |
| DIP3 inverted in 35/37, DIP5 in 32/37, MCP/PIP correct in 37/37 | `audits/db9/channel_forensic/FLAGGED_CHANNEL_FORENSICS.md`, `artifacts/VERDICTS.json` |
| CMC5 slope 0.28511 = published 0.285, same raw column as WRIST_F | `audits/db9/channel_forensic/artifacts/VERDICTS.json` |
| earlier "many channels fail" verdict partly overturned; `repetition` misaligned in 24 of 99 files | `audits/db9/channel_forensic/SEGMENTATION_VALIDATION.md` |
| in-file `subject` collides; 10 collisions in 37 Exercise-B files | `audits/db9/channel_forensic/DB9_FORENSIC_DECISION.md` |
| arm A BA 0.8538 / arm B BA 0.7254, chance 0.1111, 544 556 frames, 37 subjects | `audits/db9/channel_forensic/artifacts/POSTURE_UTILITY_POSTURE_ONLY.json` |
| mixed 17-class arm B BA 0.4853 | same artifact, mixed-task block |
| emg2pose IK failures 15.6 %; 16.09° vs 12.48° MAE | `docs/joint_angle_definition.md`, `docs/smoke_test_evidence.json` |
| cross-dataset disagreement 2–40° medians, up to 450° ranges | `audits/db9/coordinate_audit/artifacts/COMMON_POSE_API_VERDICT.json` |
| reference posture attained to 0.854° mean | same artifact |
| 16 of 22 released columns recovered exactly | `audits/db9/channel_forensic/artifacts/FORENSIC_CORE.json` |
| 58 tests | `python -m pytest tests/ -q` |

`tests/test_api_contract.py::test_frozen_utility_record_is_self_consistent` re-derives the
published utility ratios from the transcribed numbers, so a transcription error in a
README table fails the suite rather than propagating.

### Claims deliberately not made

The README states, in three places and without hedging, that the project has **not**
demonstrated: universal task transfer; universal cross-dataset numerical coordinate
equivalence; a deployment-grade or frozen API; arbitrary downstream task support; or that
any downstream head survives upstream estimator substitution. The trusted subset is
labelled **PROVISIONAL** with the reason (37 Exercise-B subjects, not the final
full-corpus validation). `docs/research_status.md` §E keeps the withdrawn and negative
results, including three retracted claims.

### Known residual risks

1. **`COMMIT PENDING` in historical provenance.** Several frozen artifacts record
   `COMMIT PENDING` because the research workspaces predate version control. This
   repository starts a clean history and does not carry the old one. The strings are
   accurate and were not upgraded.
2. **The trusted subset is provisional.** The DB9 final-validation driver is included at
   `audits/db9/channel_forensic/tools/final_validation.py`, but its captured log in the
   historical workspace is 0 bytes — it did not complete. The README and
   `docs/db9_trusted_subset.md` both say so.
3. **The human-annotation endpoint is not recoverable.** Its formal round was interrupted
   by a diagnostic model-unblinding at 200 of 396 items. No endpoint is published anywhere
   in this repository, and the reason is recorded in the lane's README.
4. **Curated artifacts were edited by curation.** 66 of the 214 copied files differ from
   their sources, all by path substitution. `provenance/CURATION_MANIFEST.json` records,
   per file, whether it was altered and which placeholder classes were substituted, so the
   difference is visible rather than assumed away.
