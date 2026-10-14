# V1 local archival commit record

Prepared 2026-09-24 from HEAD `05574b6f104017de001c88ecf1a07b7600bcb882`. This record describes the **local commit and annotated tag** requested after the repository synthesis; it does not authorize publication, remote push, a new experiment, or changes to frozen scientific content.

## Inclusion decision

- Archive the 323 selected files under `experiments/upstream_substitution/`: frozen plans, manifests, decisions, analysis and user-level JSON/CSV, SHA256 identity sidecars, scientific scripts, completion/closure notes, and captured scientific stdout. They form the auditable Gate1.5–Final chain, including the Gate4B structural negative. Preserve each byte unchanged.
- Archive the 12 synthesis files previously added under `docs/v1_repository_synthesis_20260924/`, plus this archival record. Their registry and claim matrix explicitly mark historical contradictions and unresolved provenance.
- Do **not** stage any of the 11 pre-existing modified tracked files: `PUBLICATION_AUDIT.md`, `README.md`, `docs/db9_trusted_subset.md`, `docs/licensing.md`, `docs/reproducibility.md`, `docs/research_status.md`, `scripts/publication_scan.py`, `scripts/verify_curated_tree.py`, `src/common_pose/api/dof.py`, `src/common_pose/tasks/posture.py`, `tests/test_api_contract.py`. Their local changes were not part of this final-evidence audit and some root status prose predates the final result.
- Do **not** stage the other pre-existing untracked files `docs/README.md`, `scripts/check_links.py`, or `scripts/check_readme_claims.py`.

## Exclusions from the 388-file experiment tree

- 43 format/cache/operational files: 18 Python bytecode caches, 19 PNG plots, three `.joblib` model binaries, two PID markers and one PowerShell relay launcher. The repository's existing `.gitignore` excludes bytecode, plots and model binaries. Frozen model **hashes and instance manifests** are archived; the local model bytes were independently hash-checked against the final result but are not placed in Git. JSON/CSV artifacts preserve the chart data.
- 22 transport or interim files: relay script/sidecar/logs, pipeline launcher/sidecar, Gate4B acquisition and relay probe scripts, intermediate acquisition/relay handovers, and two `SESSION_HANDOVER_RUNNING` notes. The frozen cohort manifests, source failure inventory, completion/closure records, structural qualification, scientific pipeline stdout, and final result remain in the archive.
- Nothing was deleted, moved, renamed, or rewritten. Excluded files remain in the working tree.

## Evidence check before staging

All 116 `.sha256` sidecars in the experiment tree matched their existing targets. `FINAL_CONFIRMATION_RESULTS.json` matched the frozen plan and cohort hashes; it reports 20 users, 702 files, 20 user receipts, no upstream/gate retuning, and no opening of candidates outside the cohort. Both final gate model binaries matched the SHA256 values in that final result. Both user-level primary effects are positive for 20/20 users with Holm-adjusted one-sided sign p = 1.9073486328125e-6. This was metadata/result verification only; no model, raw signal processing, or scientific inference ran.

The entire 388-file experiment tree had a pre-staging path-and-SHA256 fingerprint `65340a342fc8f6536005cdc39f09dfeefd0f011fe97d9f93d0c3933423a82013`. Recompute it after the commit to verify no experiment content changed. This digest covers excluded files too and is a local audit checksum, not a replacement for individual scientific sidecars.

The staged JSON files parsed successfully (92/92 including the synthesis registry), and all 336 staged paths were inside the two allowlisted directories. A Git whitespace check with CRLF treated as a valid line ending found only blank final lines in two captured historical stdout files (`gate1_5_stdout.txt` and `gate2a_stdout.txt`). Those logs were intentionally left byte-for-byte unchanged.
