# Licensing — PENDING REVIEW

> ## `LICENSE_PENDING_REVIEW`
>
> **No `LICENSE` file is included in this repository.** No open-source licence has been
> chosen, and that is a deliberate decision rather than an omission.

## Why no licence was chosen

Choosing a permissive licence (MIT / Apache-2.0 / BSD) would assert a grant this project
cannot currently make. Choosing a copyleft licence (GPL) would assert a compatibility
position that has not been checked. Either would be a claim about provenance that has not
been verified.

The concern is concrete:

| dependency | licence | what it constrains |
|---|---|---|
| **emg2pose baseline** | **CC-BY-NC-SA-4.0** — Attribution-NonCommercial-ShareAlike 4.0 | Non-commercial only. ShareAlike is a copyleft-style condition. If any of its code were adapted into this repository, that would constrain the whole work. |
| **UmeTrack** (bundled inside the emg2pose baseline) | **CC-BY-NC-4.0** — Attribution-NonCommercial 4.0 | Non-commercial only. |
| **BE-UJI / MOVMUS-UJI `AngleCalculation` code** | **Apache-2.0** in the current release; **CC-BY-4.0** in the earlier version (v1) | Redistributable with attribution and notice. The two releases carry *different* licences, so the specific version used matters. |
| Ninapro DB9 data | terms stated on the official site | The site does not state redistribution terms, so the data is **not** mirrored here. |
| KIN-MUS UJI, KINE-ADL BE-UJI data | CC-BY-4.0 | Redistributable with attribution — but not redistributed here regardless. |

## What this repository does about it

**No third-party code is redistributed.** Specifically:

* The emg2pose baseline is **not vendored**. `adapters/emg2pose.py` and
  `estimators/emg2pose/predict_pose.py` are wrappers that import it from a user-provided
  checkout located through `COMMON_POSE_EMG2POSE_BASELINE`. The one algorithmic rule
  reproduced from it — the IK-failure test — is reimplemented from its published definition
  in four lines of NumPy so that no third-party code is carried, and the implementation is
  cross-checked against the official helper at runtime.
* No UmeTrack file, model, or asset is copied.
* No dataset, checkpoint, or vendor-released artifact is copied.
* Per-dataset terms and access routes are recorded in
  [`reproducibility.md`](reproducibility.md), with source URLs, DOIs and access dates in
  `audits/dataset_admission/pose_api_admission/OFFICIAL_SOURCE_REFERENCES.md`.

## What still needs review before a licence can be chosen

1. **Lineage of each ported tool.** The DB9 channel-forensic drivers under
   `audits/db9/channel_forensic/tools/` were written for this project; their provenance is
   recorded file-by-file in `provenance/PORTED_TOOLS_MANIFEST.json`. This should be
   confirmed to be independent of any third-party implementation, not merely believed to be.
2. **The `canonical16` mapping's lineage.** It was derived against `emg2pose/constants.py`
   and DB9's own `order_of_angles` field. Constants and DOF names are arguably facts rather
   than expressive code, but this has not been reviewed.
3. **Whether any audit lane adapted third-party analysis code** rather than reimplementing
   it. The coordinate-audit lane consumed an externally authored mapping standard; whether
   any code was adapted from it has not been established.
4. **The `hand_visualizer` assets** used by the human-annotation lane (three.js and
   related bundles) are third-party and their redistributable status was **not verified**;
   they were excluded from the curated subset for exactly that reason.

## Until then

* The repository is public for **reading, review and collaboration**.
* It is **not** offered under an open-source licence, and no rights beyond those granted by
  GitHub's Terms of Service are extended.
* Anyone wishing to reuse code here should open an issue so the specific file's provenance
  can be checked and a decision recorded.
* When review completes, a `LICENSE` file will be added and this document replaced with the
  chosen licence and the reasoning for it.

This file is a statement of an open question, not legal advice.
