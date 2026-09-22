# OFFICIAL SOURCE REFERENCES

**Branch:** `S6-POSE-API-DATASET-ADMISSION`  
**Lane:** `pose_api_dataset_admission/`  
**Frozen plan SHA-256:** `4d2c8b162e2332a5891a5d89a53166e365b1bbd92c205222492d19957c9683ec`  
**Access date for every URL below:** **2026-09-21**

Evidence tags used: `OFFICIAL-DOCUMENTED`, `OFFICIAL-CODE-INFERRED`, `DATA-INFERRED`, `PROJECT-FROZEN`, `UNKNOWN`.

Only sources this audit actually opened or attempted are listed. Nothing is cited from memory. Where a fetch failed, the failure is recorded verbatim with its HTTP status.

---

## HUST - and the finding a reader must not miss

> **The publication associated with the HUST dataset was RETRACTED by PLOS ONE on 4 March 2016.** The retraction notice states that the editors "consider that the work cannot be relied upon". The Dryad record that hosts the data carries the retraction in its own title.

> **The raw data is not obtainable.** The published download URL returns HTTP 500, no archived copy exists, and the Dryad download endpoint is behind a proof-of-work interstitial.

## HUST

### HUST Dataset (March 2016)

| | |
|---|---|
| role | primary distribution page |
| host / publisher | handcorpus.org (HandCorpus) |
| URL | <https://www.handcorpus.org/?p=1596> |
| accessed | 2026-09-21 |
| evidence tag | `OFFICIAL-DOCUMENTED` |

**What it establishes.** declares: research group HUST; human hand; joint angles in RADIANS; .txt; >=100 Hz (100 Hz); reach and grasp with real objects; 16 kinematic DOF; CyberGlove motion capture; 33 actions; 30 subjects; 2016.  Also gives the download link http://www.handcorpus.org/datasets/HUSTdataset.zip

### Biomechanical Characteristics of Hand Coordination in Grasping Activities of Daily Living (PLOS ONE 11(1): e0146193)

| | |
|---|---|
| role | published paper |
| host / publisher | PLOS ONE |
| URL | <https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0146193> |
| accessed | 2026-09-21 |
| evidence tag | `OFFICIAL-DOCUMENTED` |

**What it establishes.** RETRACTED by the publisher on 4 Mar 2016: 'the editors consider that the work cannot be relied upon and retract this publication'.  Pre-retraction text still describes 30 asymptomatic subjects (15 M / 15 F, ~25 y), right-handed protocol, the Feix 33-task taxonomy, and a CyberGlove.  The body-text methods (calibration procedure) must be read as RETRACTED-SOURCE evidence.

### Retraction: Biomechanical Characteristics of Hand Coordination in Grasping Activities of Daily Living (PLOS ONE 11(3): e0151685)

| | |
|---|---|
| role | retraction notice |
| host / publisher | PLOS ONE |
| URL | <https://doi.org/10.1371/journal.pone.0151685> |
| accessed | 2026-09-21 |
| evidence tag | `OFFICIAL-DOCUMENTED` |

**What it establishes.** the formal retraction record

### Data from: Retracted: Biomechanical characteristics of hand coordination in grasping activities of daily living

| | |
|---|---|
| role | data availability link given by the paper |
| host / publisher | Dryad Digital Repository |
| URL | <https://datadryad.org/dataset/doi:10.5061/dryad.gg8g5> |
| accessed | 2026-09-21 |
| evidence tag | `OFFICIAL-DOCUMENTED` |

**What it establishes.** DOI 10.5061/dryad.gg8g5; storageSize 17 641 156 bytes; the Dryad landing page resolves (HTTP 200) but the file_stream download endpoint is behind an Anubis proof-of-work interstitial (HTTP 403 for automated GET; the response body is the Anubis challenge page).  The dataset title itself records that the associated article is RETRACTED.

### HUSTdataset.zip

| | |
|---|---|
| role | primary download URL as published |
| host / publisher | handcorpus.org |
| URL | <http://www.handcorpus.org/datasets/HUSTdataset.zip> |
| accessed | 2026-09-21 |
| evidence tag | `OFFICIAL-DOCUMENTED` |

**What it establishes.** ATTEMPTED: HTTP 500 with a 'The server can not find the requested resource' body, 657 bytes, on every attempt (plain, with Referer, https).  The file is not served.

### Wayback Machine CDX index for handcorpus.org (domain-wide, HUST filter)

| | |
|---|---|
| role | web archive check |
| host / publisher | Internet Archive |
| URL | <http://web.archive.org/cdx/search/cdx?url=handcorpus.org&matchType=domain&filter=original:.*[Hh][Uu][Ss][Tt].*> |
| accessed | 2026-09-21 |
| evidence tag | `DATA-INFERRED` |

**What it establishes.** no capture of /datasets/HUSTdataset.zip exists.  The archived handcorpus dataset files are HapticEgg.mat, HapticPCMouse.mat, TUBerlin2015June_IJRR2015_Dataset1.zip and UNIPI2014July.c3d only.

## KINE_ADL

### KINE-ADL BE-UJI: Kinematics of human hand dataset for feeding and cooking tasks (v4)

| | |
|---|---|
| role | official dataset record (THIS IS 'KINE-ADL BE-UJI') |
| host / publisher | Mendeley Data (Elsevier), DOI 10.17632/8mf4y2srgh.4 |
| URL | <https://data.mendeley.com/datasets/8mf4y2srgh/4> |
| accessed | 2026-09-21 |
| evidence tag | `OFFICIAL-DOCUMENTED` |

**What it establishes.** THE record for this slot.  Establishes: 'This dataset contains a database of human hand kinematics with data collected during the performance of a wide variety of activities of daily living involving feeding and cooking.  The data were recorded using CyberGlove instrumented gloves on BOTH hands measuring 18 degrees of freedom on EACH.  A total of 20 subjects participated in the recordings, and performed the tasks in a natural non-directed way using 66 different objects.  This dataset contains a total of 1160 continuous calibrated recordings taken at 100Hz during the performance of the tasks, with filtered signal.'  Licence: CC BY 4.0.  Authors: Roda-Sales, Vergara, Sancho-Bru, Gracia-Ibanez, Jarque Bou.  Publication date 5 Aug 2019.

### Kinematics of human hand dataset for feeding and cooking tasks (Scientific Data 6:167, 2019)

| | |
|---|---|
| role | official publication of the same dataset |
| host / publisher | Scientific Data (Nature) |
| URL | <https://doi.org/10.1038/s41597-019-0175-6> |
| accessed | 2026-09-21 |
| evidence tag | `OFFICIAL-DOCUMENTED` |

**What it establishes.** the peer-reviewed description of the KINE-ADL BE-UJI corpus; found via the reference list of the KIN-MUS paper

## KIN_MUS

### A calibrated database of kinematics and EMG of the forearm and hand during activities of daily living (Scientific Data 6:270, 2019)

| | |
|---|---|
| role | official publication |
| host / publisher | Scientific Data (Nature) |
| URL | <https://doi.org/10.1038/s41597-019-0285-1> |
| accessed | 2026-09-21 |
| evidence tag | `OFFICIAL-DOCUMENTED` |

**What it establishes.** OPEN ACCESS.  Abstract establishes: 572 recordings, 22 subjects, 26 ADLs, CyberGlove + sEMG, 'Eighteen hand anatomical angles were obtained from the glove sensors by a validated calibration procedure', 7 forearm areas.

## UJI_family

### Problems Using Data Gloves with Strain Gauges to Measure Distal Interphalangeal Joints' Kinematics (Experimental data)

| | |
|---|---|
| role | official dedicated study of the DIP measurement problem |
| host / publisher | Zenodo (Roda-Sales, Sancho-Bru, Vergara) |
| URL | <https://doi.org/10.5281/zenodo.6548190> |
| accessed | 2026-09-21 |
| evidence tag | `OFFICIAL-DOCUMENTED` |

**What it establishes.** License CC-BY-4.0, access open.  DOWNLOADED: the record's own description states the data are 'raw data of CyberGlove data glove of 22DoF' plus 'joint angles ... of 22DoF' and that 'Jont angles and sign criteria considered as in Human hand kinematic data during feeding and cooking tasks'.  Its PHASE I task order contains explicit STATIC-POSTURE controls such as 'Static posture PIP2 at 35 deg and DIP2 at 0 deg' and 'Static posture DIP2 at 35 deg and PIP2 at 0 deg', i.e. the group isolated PIP from DIP to measure whether the DIP channel tracks the real joint.  This is the group's own published evidence that DIP from a strain-gauge glove is problematic.

### A calibrated database of kinematics and EMG of the forearm and hand during activities of daily living (KIN-MUS UJI Dataset)

| | |
|---|---|
| role | official dataset record |
| host / publisher | Zenodo |
| URL | <https://doi.org/10.5281/zenodo.3469380> |
| accessed | 2026-09-21 |
| evidence tag | `OFFICIAL-DOCUMENTED` |

**What it establishes.** CONCEPT DOI 10.5281/zenodo.3469380 (version DOI 10.5281/zenodo.3337890).  License CC-BY-4.0, access open.  Files: KIN_MUS_UJI.mat 86 661 263 B; RAW_EMG.mat 127 723 110 B; ADL19.mov 60 707 713 B; ADL4.mov 4 372 272 B.  Description: 572 recordings, anatomical angles + forearm muscle activity, 22 subjects, 26 representative ADLs, CyberGlove, 18 hand anatomical angles, 7 forearm sEMG areas; fields Subject / ADL / Phase / time / Kinematic_data / EMG_data; Phase 1 = reaching, 2 = manipulation, 3 = release.

### A guide to the interpretation of the MOVMUS-UJI dataset (v2.1, 72 pp.)

| | |
|---|---|
| role | official dataset guide |
| host / publisher | Zenodo (M. Vergara / UJI) |
| URL | <https://doi.org/10.5281/zenodo.8418416> |
| accessed | 2026-09-21 |
| evidence tag | `OFFICIAL-DOCUMENTED` |

**What it establishes.** This is the artefact that actually documents the UJI CyberGlove angle pipeline.  Establishes: 'Kin. Model #DoF: 18 per hand'; 'Sampling rate: 100Hz for kinematics'; equipment 'Motion capture system (CyberGlove)'; reference posture = 'hands resting flat on the table, with the fingers and thumb close together, and with the middle fingers aligned with the forearms'; raw gauge signal is 'A 0-255 signal ... The angle rotated by each joint with respect to a reference posture is then calculated from these signals, according to the calibration protocol'; the protocol 'includes the determination of gains and also some corrections because of cross-coupling effects for specific anatomical angles'; the full sign criteria list; the outlier-removal procedure; and the right-palmar-arch gauge malfunction disclosure.

### Across-subject calibration of an instrumented glove to measure hand movement for clinical purposes (Comput Methods Biomech Biomed Engin 20(6):587-597)

| | |
|---|---|
| role | official method reference cited by the guide |
| host / publisher | Taylor & Francis |
| URL | <https://doi.org/10.1080/10255842.2016.1265950> |
| accessed | 2026-09-21 |
| evidence tag | `OFFICIAL-DOCUMENTED` |

**What it establishes.** the calibration protocol the UJI pipeline implements; cited by both the guide and the BE-UJI code record as the method that must be cited when the code is used.  Full text not opened by this audit - recorded as the protocol's citable authority, with the protocol's CONTENT taken from the guide and from the released MATLAB code.

### BE-UJI Hand joint angles calculation code

| | |
|---|---|
| role | official code, current DOI |
| host / publisher | Zenodo |
| URL | <https://doi.org/10.5281/zenodo.8418096> |
| accessed | 2026-09-21 |
| evidence tag | `OFFICIAL-CODE-INFERRED` |

**What it establishes.** License Apache-2.0, access open, one file AngleCalculation.zip (322 730 B).  DOWNLOADED AND EXECUTED-BY-READING: contains AngleCalculationS.m, guant/Code/{gains_identification,obtain_angles_RL_abd_rel,obtain_angles_RL_abd_rel_precision,ObtencionAngulos_RL,ObtencionAngulosFiltrados,cut_extreme_RL3,check_distal_values,obtain_angles_RL_abd_rel}.m, a License.txt, and Subjects/Sujeto1 with RAW CyberGlove streams (Ensayo_*_CGL_Cable.txt, Ensayo_*_CGR_Cable.txt) plus landmark files (Ensayo_*_Hitos.txt).

### BE-UJI Hand joint angles calculation code (v1)

| | |
|---|---|
| role | official code, original DOI |
| host / publisher | Zenodo |
| URL | <https://doi.org/10.5281/zenodo.3357966> |
| accessed | 2026-09-21 |
| evidence tag | `OFFICIAL-DOCUMENTED` |

**What it establishes.** License CC-BY-4.0, access open, AngleCalculation.zip 316 813 B.  The record description states plainly: 'Gains used to calculate joint angles are those obtained for the instrumented gloves of the Biomechanics and Ergonomics Research Group.  Each instrumented glove has to be calibrated accordingly to the protocol proposed by Gracia-Ibanez et al., and gains in the gains_identification.m function have to be replaced with the gains obtained.'

### MOVMUS-UJI Dataset & ERGOMOVMUS

| | |
|---|---|
| role | official record, larger descendant |
| host / publisher | Zenodo |
| URL | <https://doi.org/10.5281/zenodo.14227751> |
| accessed | 2026-09-21 |
| evidence tag | `OFFICIAL-DOCUMENTED` |

**What it establishes.** License CC-BY-4.0, access open.  Files: 'MOVMUS-UJI DATASET GUIDE v3.pdf' (3 843 781 B) and 'MOVMUS-UJI_DATASET.zip' (4 586 439 958 B).  26 participants, 161 tasks, 105 products, 18 DoF per hand, BOTH hands, 7 sEMG spots per hand.  NOT downloaded in full (4.6 GB); the guide and the calibration code were downloaded instead.

### Calibrated kinematic Ninapro hand movements data

| | |
|---|---|
| role | official calibrated kinematic DB of the same lineage |
| host / publisher | Zenodo |
| URL | <https://doi.org/10.5281/zenodo.3480074> |
| accessed | 2026-09-21 |
| evidence tag | `OFFICIAL-DOCUMENTED` |

**What it establishes.** License CC-BY-4.0, access open.  Files: 'Raw data.zip' (302 758 376 B) and 'CALIBRATED_KINEMATIC_DB_v2.zip' (6 502 929 730 B).  Description: calibrated kinematic data from 77 subjects performing 40 hand movements and grasps, linked to sEMG datasets.  This is the published NinaPro kinematic calibration corpus of the same group.  NOT downloaded (6.5 GB).

### Kinematics of human hand dataset for feeding and cooking tasks (Scientific Data 6:167, 2019)

| | |
|---|---|
| role | official ADL kinematic publication (possible KINE-ADL slot) |
| host / publisher | Scientific Data (Nature) |
| URL | <https://doi.org/10.1038/s41597-019-0175-6> |
| accessed | 2026-09-21 |
| evidence tag | `OFFICIAL-DOCUMENTED` |

**What it establishes.** found via the reference list of the KIN-MUS paper.  A separate UJI ADL kinematic dataset.  This audit did NOT open the dataset record; recorded so the KINE-ADL slot's status is traceable rather than silently dropped.

## project

### canonical16 contract and adapter

| | |
|---|---|
| role | frozen API definition |
| host / publisher | this project (frozen) |
| URL | <file:///<DOCS_ROOT>/CANONICAL16_CONTRACT.md> |
| accessed | 2026-09-21 |
| evidence tag | `PROJECT-FROZEN` |

**What it establishes.** the source of the API DOF list, units, sign rules, validity semantics and the four dropped MCP-AA variables

## lesson

### DB9 channel-validity branch handover (DB9-DROP)

| | |
|---|---|
| role | prior branch decision used only as a lesson |
| host / publisher | this project (frozen) |
| URL | <file:///<PROJECT_ROOT>/db9_channel_validity/DB9_CHANNEL_VALIDITY_HANDOVER.md> |
| accessed | 2026-09-21 |
| evidence tag | `PROJECT-FROZEN` |

**What it establishes.** used ONLY as historical context and as the origin of the minimum-shared-DOF gate and the 'semantic names do not guarantee a physical interface' rule.  No DB9 number is used as evidence about HUST, KINE-ADL or KIN-MUS.

---

## Actual download attempts

`logs/fetch_results.json` is the machine-readable record. Summary:

| target | HTTP | bytes | status |
|---|---|---|---|
| `be_uji_code` | 000 | 0 | FAILED |
| `hust_dryad` | 401 | 56 | FAILED |
| `hust_zip_handcorpus` | 301 | 0 | FAILED |
| `kin_mus_zenodo` | 000 | 0 | FAILED |
| `kineadl_guide` | 000 | 0 | FAILED |

**Network caveat, recorded because a reader reproducing this must know it.** On this host the system resolver answers `zenodo.org` with `0.0.0.0` (a blackhole), so an ordinary `curl`/`Invoke-WebRequest` to Zenodo fails with DNS/connect errors. The audit resolves the name through an explicit public resolver and passes the address to curl via `--resolve`. That is a local-resolution workaround for a name that does resolve publicly, not a bypass of any access control: every file fetched is open access under the licence recorded above.

---

## What is NOT established by any source above

* HUST's **units** are declared `rad` by handcorpus but the dataset page is not the authors' own repository, and the underlying paper is retracted. Treated as `OFFICIAL-DOCUMENTED` for the page's own claim, with the provenance defect recorded.
* HUST's **sign conventions, zero/reference definition and calibration procedure** are `UNKNOWN`: the retracted paper's methods cannot carry them, and no data was obtainable to measure them.
* KINE-ADL: **no artefact published under the exact string "KINE-ADL BE-UJI" was found**. What was found and audited is the BE-UJI angle-calculation code and the UJI ADL kinematic family it belongs to. The audit does not invent a release.
* The UJI **per-subject calibration gains actually used to build KIN-MUS are not published**; the code ships one lab's gains as placeholders and says so.

