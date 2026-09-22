# SOURCE PROVENANCE

**Branch:** `S7-DATASET-ADMISSION-COORDINATE-AUDIT`  
**Frozen plan SHA-256:** `fba2b20623392dd809d5ed28c7850387acc721e9a91ff1611e7fba0d89fc889d`  
**Access date for every URL below:** 2026-09-21  
**Commit:** COMMIT PENDING - the project root is not a git repository; provenance is content-hash based.

Evidence tags: `[DOC]` official documentation; `[EMPIRICAL]` measured by this audit; `[INFERENCE]`; `[UNRESOLVED]`.

---

## 0. What was already on this machine, and what this audit had to fetch

| dataset | status before this audit | corpus size | downloaded by this audit |
|---|---|---|---|
| MyoKi | **absent** - the string `MyoKi` did not occur anywhere in the project | 145 463 536 055 B | 49 077 777 B of official metadata/code + sync test |
| KIN-MUS UJI | present, audited by the upstream admission lane | 86 661 263 B | 0 B |
| KINE-ADL BE-UJI | record known, **corpus absent** | 1 070 355 215 B | 1 815 639 B official guide |

The frozen plan's rule is applied: small official metadata / schema / calibration files are fetched; the large body of data is **not** pulled and is recorded as an explicit download requirement instead (section 4 below).

---

## MyoKi

| | |
|---|---|
| dataset_name | MyoKi: A database of multimodal myography and hand kinematics during realistic daily life activities |
| version | figshare v1 (10.6084/m9.figshare.28696778.v1), published 2025-08-29 |
| doi | 10.6084/m9.figshare.28696778 |
| paper | Scientific Data 12:1507 (2025), doi:10.1038/s41597-025-05852-6; Andreas D, Werner D, Hou Z, Dwivedi A, Castellini C, Beckerle P |
| download_location | https://doi.org/10.6084/m9.figshare.28696778 |
| licence | CC BY 4.0 |
| access_right | open, no registration |
| local root | `<DATA_ROOT>set_admission_audit_v1\raw\myoki` |
| corpus | 41 file(s), 145463536055 B |

**Files actually present and hashed by this audit**

| label | bytes | sha256 | evidence | role |
|---|---|---|---|---|
| `Synchronicity_test.mat` | 48961776 | `7bc35b0dff5159e4127dec38...` | `[EMPIRICAL]` | official single-recording synchronisation test; SAME variable set and shapes as a participant file |
| `Glove_calibration.xlsx` | 12503 | `9719e26ffa6fff3552ab220e...` | `[DOC]` | official calibration data (male + female sheets, 13 channels each) |
| `Task_categorization.xlsx` | 21143 | `effe2e7c989e88aaf5ee5098...` | `[DOC]` | official 74-task table and its grasp mapping |
| `Participant_information.xlsx` | 12908 | `94f5dc9b614a3942b596ff34...` | `[DOC]` | official participant metadata incl. acquisition-anomaly notes |
| `Database_comparison.xlsx` | 10557 | `0fe1fe3cdecbff03f7778030...` | `[DOC]` | official per-participant decoder R2 table (used for provenance only) |
| `Database_comparison.py` | 3944 | `7ede8a62a11758835a5a06ad...` | `[DOC]` | official code that produced Database_comparison.xlsx |
| `dlr_myography_kinematics_s41597-025-05852-6.pdf` | 4005665 | `a765e2c6c801a52ac194ee6a...` | `[DOC]` | the MyoKi dataset's own paper (Sci Data 12:1507) |
| `dlr_myography_kinematics_s41597-025-05852-6.txt` | 63644 | `e0de9cbed3da2149a8e50b76...` | `[EMPIRICAL]` | extracted paper text |

**Documentation inventory**

| artefact | available |
|---|---|
| paper | yes (open access) |
| readme | in paper 'Data records' |
| data_dictionary | in paper 'Data records' |
| calibration_documentation | paper Methods + Glove_calibration.xlsx |
| calibration_code | NONE PUBLISHED - only the equation (Eq. 1) and the two calibration tables |
| known_issue_documentation | Participant_information.xlsx 'Notes' column + paper Usage Notes |

**DOWNLOAD REQUIREMENT (not fetched)**

* needed for: grasp-label audit, physical-anchor audit at scale, cross-subject calibration consistency, per-participant anomaly notes verification
* minimum: P01.mat .. P35.mat, 3 166 867 904 .. 4 949 415 072 B each, 3 816 461 856 B for P01.mat
* total if all: 145463536055 B
* why withheld: the frozen plan forbids pulling the large body of data without an explicit requirement; the small official metadata/code set plus the 48 961 776 B synchronisation file were downloaded instead

---

## KIN-MUS

| | |
|---|---|
| dataset_name | A calibrated database of kinematics and EMG of the forearm and hand during activities of daily living (KIN-MUS UJI) |
| version | Zenodo concept 10.5281/zenodo.3469380, version 10.5281/zenodo.3337890 |
| doi | 10.5281/zenodo.3469380 |
| paper | Scientific Data 6:270 (2019), doi:10.1038/s41597-019-0285-1; Jarque-Bou NJ, Vergara M, Sancho-Bru JL, Gracia-Ibanez V, Roda-Sales A |
| download_location | https://doi.org/10.5281/zenodo.3469380 |
| licence | CC-BY-4.0 |
| access_right | open, no registration |
| local root | `<PROJECT_ROOT>\pose_api_dataset_admission\raw\kin_mus` |
| corpus | 1 file(s), 86661263 B |

**Files actually present and hashed by this audit**

| label | bytes | sha256 | evidence | role |
|---|---|---|---|---|
| `KIN_MUS_UJI.mat` | 86661263 | `530a9e51b19574b0f5dee0c9...` | `[EMPIRICAL]` | released kinematic+EMG corpus |
| `MOVMUS_UJI_DATASET_GUIDE_v2_1.pdf` | 4022963 | `393e38ca7e7f67750b187340...` | `[DOC]` | official guide of the larger MOVMUS-UJI descendant |
| `MOVMUS_UJI_DATASET_GUIDE_v2_1.txt` | 102636 | `e067c3969a8a26898aa7ee40...` | `[EMPIRICAL]` | extracted guide text (upstream lane) |
| `AngleCalculation.zip` | 322730 | `332d9ecea74771432c05579e...` | `[DOC]` | official BE-UJI angle-calculation code, current DOI |
| `obtain_angles_RL_abd_rel.m` | 10957 | `83ac9e505798fc11ffd9abcc...` | `[DOC]` | official calibration code - column order + cross-coupling model |
| `gains_identification.m` | 4714 | `58d2bdad66768bbcbad07576...` | `[DOC]` | official gains; lab's own glove gains as placeholders |
| `check_distal_values.m` | 494 | `ed1c2eaeb50cc7a871b92b21...` | `[DOC]` | 18- vs 22-sensor glove identification |
| `KINMUS_2019.pdf` | 2261144 | `cacbfdce4b1369ce7d02790d...` | `[DOC]` | the KIN-MUS dataset's own paper (Sci Data 6:270) |
| `KINMUS_2019.txt` | 35849 | `e38926c0b30ff117bc804dfc...` | `[EMPIRICAL]` | extracted paper text |

**Documentation inventory**

| artefact | available |
|---|---|
| paper | yes (open access) |
| readme | paper 'Data Records' |
| data_dictionary | paper 'Data Records' + paper Table 2 (column ORDER) |
| calibration_documentation | paper Methods; guide v2.1 sections 2.1/3.1/4.3 |
| calibration_code | BE-UJI AngleCalculation.zip (Zenodo 8418096) |
| known_issue_documentation | paper Usage Notes (ADL#25/subject#22 data lost; WRIST_F cable artifact in ADL#7 and #11) |

---

## KINE-ADL

| | |
|---|---|
| dataset_name | KINE-ADL BE-UJI: Kinematics of human hand dataset for feeding and cooking tasks, v4 |
| version | Mendeley Data v4 (5 Aug 2019), DOI 10.17632/8mf4y2srgh.4 |
| doi | 10.17632/8mf4y2srgh.4 |
| paper | Scientific Data 6:167 (2019), doi:10.1038/s41597-019-0175-6; Roda-Sales A, Vergara M, Sancho-Bru JL, Gracia-Ibanez V, Jarque-Bou NJ |
| download_location | https://data.mendeley.com/datasets/8mf4y2srgh/4 |
| licence | CC BY 4.0 |
| access_right | open, no registration |
| local root | `<DATA_ROOT>set_admission_audit_v1\raw\kine_adl` |
| corpus | 3 file(s), 1070355215 B |

**Files actually present and hashed by this audit**

| label | bytes | sha256 | evidence | role |
|---|---|---|---|---|
| `KINE-ADL_BE-UJI_DATASET_Guide.pdf` | 1815639 | `f1598d641c31cc7e8805cad0...` | `[DOC]` | official dataset guide / data dictionary |
| `KINE-ADL_GUIDE.txt` | 48251 | `1f675b93b71847dadd1f5f1e...` | `[EMPIRICAL]` | extracted guide text |
| `KINEADL_2019.pdf` | 1772499 | `f7dfc65af86d2d084a5dc3ee...` | `[DOC]` | the KINE-ADL dataset's own paper (Sci Data 6:167) |
| `KINEADL_2019.txt` | 36121 | `974765004cdfabceae63887b...` | `[EMPIRICAL]` | extracted paper text |

**Documentation inventory**

| artefact | available |
|---|---|
| paper | yes (open access) |
| readme | guide (downloaded) |
| data_dictionary | guide KINEMATIC_DATA / SUBJECT_DATA sections |
| calibration_documentation | paper Methods; guide section 2 |
| calibration_code | BE-UJI AngleCalculation.zip (shared with KIN-MUS) |
| known_issue_documentation | guide: some wrist angles missing for some subjects (improper wrist-sensor fit) |

**DOWNLOAD REQUIREMENT (not fetched)**

* needed for: 18-column order verification against real values, Experiment A/B subject-overlap resolution (global_person_id), measured/anomaly QC, kinematic trajectory inspection for task observability
* minimum: BE_UJI_DATASET.mat, 644 185 378 B, sha256 808f0dabb529e5a98af3ba075023e9430e5b80eb26cf296a4874ae3ad7762b61
* total if all: 1070355215 B
* why withheld: the frozen plan forbids pulling the large body of data without an explicit requirement; the 1 815 639 B official guide (the schema document) was downloaded instead and its SHA-256 matches the published hash

---

## Record file inventories captured at freeze time

These are read from the publishers' own APIs, so the sizes and hashes are the publishers' values, not ours. `[DOC]`

### MyoKi

| filename | bytes | sha256 (publisher) |
|---|---|---|
| `Participant_information.xlsx` | 12908 | (not published) |
| `Task_categorization.xlsx` | 21143 | (not published) |
| `Glove_calibration.xlsx` | 12503 | (not published) |
| `Database_comparison.xlsx` | 10557 | (not published) |
| `Database_comparison.py` | 3944 | (not published) |
| `Synchronicity_test.mat` | 48961776 | (not published) |
| `NinaproDB7_replica.mat` | 1908493416 | (not published) |
| `P01.mat` | 3816461856 | (not published) |
| `P35.mat` | 4307345464 | (not published) |

### KINE-ADL

| filename | bytes | sha256 (publisher) |
|---|---|---|
| `BE_UJI_DATASET.mat` | 644185378 | `808f0dabb529e5a98af3ba075023e9430e5b80eb26cf296a4874ae3ad7762b61` |
| `CSV DATA.zip` | 424354198 | `fe4498b0cc8f646c0f8a2e9546d8ce0060602e2bcbc40351c5c2de881d2082ec` |
| `KINE-ADL BE-UJI DATASET_Guide.pdf` | 1815639 | `f1598d641c31cc7e8805cad076e4c2c84ae76afd3ade768cd30e2486a547654a` |

## Network caveat carried forward from the upstream lane

On this host the system resolver answers `zenodo.org` with `0.0.0.0` (a blackhole). The upstream admission lane therefore resolved the name through an explicit public resolver and passed the address to `curl --resolve`. `figshare.com`, `ndownloader.figshare.com`, `api.figshare.com`, `data.mendeley.com` and `www.nature.com` resolve normally here. [EMPIRICAL]

