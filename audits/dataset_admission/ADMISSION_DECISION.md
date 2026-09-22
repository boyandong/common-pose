# ADMISSION DECISION

**Branch:** `S7-DATASET-ADMISSION-COORDINATE-AUDIT`  
**Frozen plan SHA-256:** `fba2b20623392dd809d5ed28c7850387acc721e9a91ff1611e7fba0d89fc889d`  **Commit:** COMMIT PENDING

---
# EXECUTIVE SUMMARY (one page)

## TERMINAL STATUS: **PASS (the audit completed); with one SCIENCE-BLOCKING finding escalated - shared10_poc_v1 is a SHARED10-SEMANTIC-MISMATCH**

Three datasets were audited for admission into the Common Hand Pose API, and the frozen representation `shared10_poc_v1` was audited for physical provenance. Four of the ten frozen index positions select a DIFFERENT anatomical degree of freedom than the one they are named as.

**The finding.** The ten indices `[0,2,4,6,7,8,9,11,13,15]` are the correct positions of the intended ten DOFs in the **MOVMUS-UJI guide v2.1** column order. But the released `KIN_MUS_UJI.mat` stores its 18 columns in the order the KIN-MUS dataset's **own paper** gives in Table 2, and the two orders differ by four swapped adjacent pairs. Applied to the real array, the ten indices yield:

| shared10 name | what the column actually is |
|---|---|
| `thumb_cmc_flexion` | **CMC1_A** (thumb CMC abduction) |
| `index_mcp_flexion` | **MCP2-3_A** (index-middle metacarpals relative abduction) |
| `ring_mcp_flexion` | **MCP3-4_A** (middle-ring metacarpals relative abduction) |
| `pinky_mcp_flexion` | **MCP4-5_A** (ring-little metacarpals relative abduction) |

The four independent, model-free discrimination tests in the frozen plan all resolve to the KIN-MUS Table 2 order, and the dataset's own paper states that order in words.

## Dataset grades

| dataset | grade | one-line reason |
|---|---|---|
| MyoKi | **YELLOW** | raw->calibrated chain reproduced BIT-EXACTLY for 16 of 18 channels, but the 145 GB corpus was not obtained and the thumb has no CMC flexion channel |
| KIN-MUS UJI | **YELLOW** | order and hand now resolved from the dataset's own paper; 12 of 16 canonical16 DOFs present; raw gauges unpublished so parity cannot be closed |
| KINE-ADL BE-UJI | **GRAY** | guide authentic and informative, but the corpus is absent and 15 of 40 participant keys hide an unknown cross-experiment overlap |

## SHARED10_poc_v1 VERDICT: **SHARED10-SEMANTIC-MISMATCH**

| consequence | status |
|---|---|
| the old phase NUMBERS | **still valid** - same columns, same arithmetic |
| the old phase PHYSICAL INTERPRETATION | **invalid for 4 of 10 channels** |
| the `shared10_poc_v1` index vector | **must be corrected** to `[1, 2, 5, 6, 7, 8, 10, 11, 14, 15]` |
| the KIN-MUS dataset admission | **unaffected** |

## CommonPoseSubset_v2_candidate: 11 DOFs

* **tier 1 (8)**: `index_mcp_flexion`, `index_pip_flexion`, `middle_mcp_flexion`, `middle_pip_flexion`, `ring_mcp_flexion`, `ring_pip_flexion`, `pinky_mcp_flexion`, `pinky_pip_flexion`
* **tier 2 (3)**: `thumb_cmc_flexion`, `thumb_mcp_flexion`, `thumb_ip_flexion`

Everything else in canonical16 is excluded: the four DIPs are absent from all three external datasets, and `thumb_cmc_ab_adduction` has no globally meaningful sign convention.

---
# 1. MyoKi

**physical coordinate admission.** PARTIAL and STRONG where it exists. The channel table is official and names all 18 channels in order, and this audit reproduced the raw->calibrated chain BIT-EXACTLY for channels 1-16 (max abs error 0.000e+00 deg over 83 267 samples) from `glove` + the official calibration workbook. Channels 17-18 are exactly affine but on unpublished per-participant constants. The thumb has no CMC FLEXION channel at all: channel 1 is an abduction/opposition channel and may not be substituted.

**emg pose suitability.** GOOD IN PRINCIPLE, NOT MEASURABLE HERE. 12 sEMG channels at 2000 Hz, 27+27 IMU channels, 24 FMG channels (subset 2) and a fully released raw glove stream, all on one time base from a common time server. But the audit holds ONE 41.6 s recording; no subject-level or task-level statement is possible.

**downstream task suitability.** RESTRICTED. `grasp` is a task-metadata lookup, constant over a task segment, and is NOT frame-wise ground truth.

**Grade: `YELLOW`**

### strongest safe channels
* MCP Index/PIP Index (cols 5,6)
* MCP Middle/PIP Middle (cols 7,8)
* MCP Ring/PIP Ring (cols 10,11)
* MCP Little/PIP Little (cols 13,14)
* MCP Thumb (col 2)
* IP Thumb (col 3)
* the three relative abductions (cols 9,12,15) as abduction, not flexion

### unsafe channels
* col 17 wrist flexion/extension - per-participant constants not published
* col 18 wrist deviation - same, and no polarity is stated anywhere
* col 1 'Abduction Thumb to Palm' - posture wording, no ISB name, no stated polarity, and it is NOT thumb CMC flexion
* col 4 'Abduction Thumb - Index flat on table' - same objection
* col 16 palmar arch - different calibration reference from every other channel

### unresolved blockers
* the participant corpus (35 x 3.17-4.95 GB, 145 463 536 055 B total) is required for every subject-level claim: nothing about MyoKi generalisation is established by this audit
* participant P20's EMG channels 7 and 8 are documented as detached and unusable; P05 is missing repetition 2 of task 67
* the per-participant wrist calibration constants are not published, so the wrist channels can never be recovered to absolute angles

**recommended role:** a later, SECOND external geometry source and a label-provenance stress test; not the first POC source, because the corpus is 145 GB, its labels are task-derived, and its thumb CMC flexion is absent

### The parity result, in full

* equation `angle = angle1 + (sensor_value - sensor_value1) * gain, gain = (angle2 - angle1)/(sensor_value2 - sensor_value1)` reproduced from the official workbook
* sheet **female**, maximum absolute error **0.000e+00 deg** over 83 267 samples
* bit-exact channels: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
* not reproduced: [17, 18]

### The sampling result, in full

| stream | distinguishable rate | inflation |
|---|---|---|
| `glove` | 35.548 Hz | 56.26x |
| `glove_calibrated` | 35.548 Hz | 56.26x |
| `emg` | 1999.978 Hz | 1.00x |
| `acc` | 148.030 Hz | 13.51x |
| `gyro` | 148.030 Hz | 13.51x |
| `fmg` | 86.205 Hz | 23.20x |
| `task` | 0.024 Hz | 83267.00x |
| `timestamp` | 1999.978 Hz | 1.00x |

---
# 2. KIN-MUS UJI

**physical coordinate admission.** PARTIAL. The dataset's OWN paper pins the 18-column order (Table 2) and the hand (RIGHT). 12 of the 16 canonical16 DOFs are present; all four DIPs are absent and must stay absent. Four channels are RESTRICT: the two wrists (cable artifact, envelope violation, unpublished gains, and a sign convention that conflicts across the family's own documents), the palmar arch (the group's later guide discloses the right palmar-arch gauge is malfunctioning), and the three relative abductions plus CMC1_A are semantically valid but weakly anchored. The released block is already reference-differenced and the raw gauges are not published, so the transform is TRANSFORM_NOT_INDEPENDENTLY_REPRODUCIBLE.

**emg pose suitability.** GOOD. The same containers carry 7 normalised and 7 raw sEMG channels; no new collection is needed for a later EMG->pose arm.

**downstream task suitability.** the phase label is the only label that passed; ADL identity is rejected

**Grade: `YELLOW`**

### strongest safe channels
* MCP2_F, MCP3_F, MCP4_F, MCP5_F (indices 5,7,10,14)
* PIP2_F, PIP3_F, PIP4_F, PIP5_F (indices 6,8,11,15)
* MCP1_F (index 2) and IP1_F (index 3) with a documented 18/22 anchor
* CMC1_F (index 1) with a 22/22 anchor but only two datasets

### unsafe channels
* WR_F (index 16) - RESTRICT
* WR_A (index 17) - RESTRICT, sign conflict
* PalmArch (index 12) - RESTRICT, malfunctioning right gauge disclosed
* CMC1_A, MCP2-3_A, MCP3-4_A, MCP4-5_A - usable as abduction only, weak anchor

### unresolved blockers
* the raw CyberGlove streams and the per-glove gains actually used are not published: parity can never be closed on this corpus
* which of the 18 columns is the right palmar arch was never confirmed against the malfunction disclosure

**recommended role:** FIRST POC TASK SOURCE for the phase label, provided the interface carries temporal state and the representation is redefined with the CORRECT index vector [1, 2, 5, 6, 7, 8, 10, 11, 14, 15]

### Physical anchors (scored, subject = unit)

| anchor | subjects | fraction | median delta | verdict |
|---|---|---|---|---|
| PIP flexion rises from REACHING (1) to MANIPULATION (2) | 22/22 | 1.0000 | +13.082 | **PASS** |
| MCP flexion rises from REACHING (1) to MANIPULATION (2) | 22/22 | 1.0000 | +17.792 | **PASS** |
| MCP+PIP flexion sum rises from REACHING to MANIPULATION | 22/22 | 1.0000 | +18.000 | **PASS** |
| relative abduction FALLS from REACHING to MANIPULATION (fingers co | 14/22 | 0.6364 | -0.590 | **WEAK** |
| thumb MCP + IP flexion rises from REACHING to MANIPULATION | 18/22 | 0.8182 | +1.962 | **PASS** |
| thumb CMC flexion rises from REACHING to MANIPULATION | 22/22 | 1.0000 | +6.867 | **PASS** |
| thumb CMC abduction rises from REACHING to MANIPULATION (REPORTED, | 22/22 | 1.0000 | +2.065 | **PASS** |

---
# 3. KINE-ADL BE-UJI

**physical coordinate admission.** DOCUMENTED BUT UNCONFIRMED. The official guide names all 36 angle columns (18 right, 18 left) in an order that DIFFERS from KIN-MUS at 8 of 18 positions, so positional mapping between the two is forbidden and an explicit semantic map is mandatory. The guide's SHA-256 equals the publisher's published hash. But the corpus was not downloaded, so no identity was confirmed against real values, and the gains actually used are not published.

**emg pose suitability.** NOT APPLICABLE - KINE-ADL carries no EMG.

**downstream task suitability.** INCONCLUSIVE. 178 elementary tasks over 2 experiments, but no trajectory was inspected.

**Grade: `GRAY`**

### strongest safe channels
* the same 12 non-DIP canonical16 DOFs per hand, at MEDIUM confidence, pending value-level confirmation

### unsafe channels
* all four DIPs: absent
* WR_F / WR_A: the guide itself warns that wrist angles are missing for some subjects because of improper sensor fitting

### unresolved blockers
* BE_UJI_DATASET.mat (644 185 378 B, sha256 808f0dab...) is required to confirm the column order against real values AND to resolve which 15 of the 40 (experiment, subject) keys are the same people
* until SUBJECT_DATA is available, NO grouped split that crosses experiments may be constructed: 15 of 20+20 participants are shared and the overlap set is unknown
* gains actually used are not published

**recommended role:** a later second-hand coordination source, and the natural second dataset once the corpus is obtained; not admissible for the first POC today

---
# 4. SHARED10_poc_v1 VERDICT

## `SHARED10-SEMANTIC-MISMATCH`

The upstream admission lane named the KIN-MUS release's 18 columns from the MOVMUS-UJI guide v2.1 Table 4. That guide documents the LARGER, LATER MOVMUS-UJI dataset (2023), not the 2019 KIN-MUS release, and its column order differs from the KIN-MUS paper's own Table 2 at 4 of 18 positions. The shared10 indices are correct positions for the guide order and were then applied to an array stored in Table 2 order.

| pos | index | intended | column name if guide order | column name if Table 2 order | ACTUAL | confidence |
|---|---|---|---|---|---|---|
| 1 | 0 | `thumb_cmc_flexion` | CMC1_F | CMC1_A | **`CMC1_A`** | `NONE` |
| 2 | 2 | `thumb_mcp_flexion` | MCP1_F | MCP1_F | **`MCP1_F`** | `HIGH` |
| 3 | 4 | `index_mcp_flexion` | MCP2_F | MCP2-3_A | **`MCP2-3_A`** | `NONE` |
| 4 | 6 | `index_pip_flexion` | PIP2_F | PIP2_F | **`PIP2_F`** | `HIGH` |
| 5 | 7 | `middle_mcp_flexion` | MCP3_F | MCP3_F | **`MCP3_F`** | `HIGH` |
| 6 | 8 | `middle_pip_flexion` | PIP3_F | PIP3_F | **`PIP3_F`** | `HIGH` |
| 7 | 9 | `ring_mcp_flexion` | MCP4_F | MCP3-4_A | **`MCP3-4_A`** | `NONE` |
| 8 | 11 | `ring_pip_flexion` | PIP4_F | PIP4_F | **`PIP4_F`** | `HIGH` |
| 9 | 13 | `pinky_mcp_flexion` | MCP5_F | MCP4-5_A | **`MCP4-5_A`** | `NONE` |
| 10 | 15 | `pinky_pip_flexion` | PIP5_F | PIP5_F | **`PIP5_F`** | `HIGH` |

## 4.1 Do the old phase results still hold?

| question | answer |
|---|---|
| are the NUMBERS still valid | **YES.** The ten index positions were not changed by this audit; the same ten columns were used and the same arithmetic was performed. Balanced accuracies, the permutation null, the boundary stratification and the velocity-negation control are all unchanged. |
| is the PHYSICAL interpretation still valid | **NO, for four of the ten channels.** They are relative-abduction channels, not MCP flexion channels, and the first is thumb CMC abduction, not thumb CMC flexion. |
| does OBS-B survive | **PROVISIONALLY YES, and it is now UNTESTED for the intended DOF set.** OBS-B was decided on these ten columns; whether the ten intended flexion DOFs behave the same way is exactly the open question. |

## 4.2 Claims that must be withdrawn or downgraded

1. **Withdraw:** any statement that `shared10_poc_v1` is ten anatomical *flexion* DOFs. It is six flexion plus four relative-abduction channels.
2. **Withdraw:** the identification `thumb_cmc_flexion` for column 0. Column 0 is `CMC1_A`, thumb CMC abduction.
3. **Downgrade:** "the Common Pose subset loses only +0.0342 balanced accuracy against full18". That is true of these ten columns; it says nothing about the intended ten-DOF subset.
4. **Downgrade:** every per-channel statement in `KINMUS_FULL18_DIAGNOSTIC.json` and `KIN_MUS_PHYSICAL_ANCHOR_AUDIT.json` that names columns 0, 4, 9 or 13.
5. **Unchanged:** the KIN-MUS dataset admission verdict, the DB9 lane in full, and every number in the observability lane.

---
# 5. DB9-LIKE FAILURE CHECK

| category | found? |
|---|---|
| wrong_column | YES - 4 of 10 shared10 columns select a different anatomical DOF than they are named |
| wrong_sign | YES, a documentation conflict on the UJI wrist-deviation channel: KIN-MUS paper radial+, KINE-ADL paper and MOVMUS guide ulnar+. Not resolved in one direction. |
| wrong_zero | NO contradiction found. All three families state a reference posture; the UJI family uses a recorded reference posture and MyoKi a calibration posture. They are DIFFERENT zeros, so numeric equivalence is UNVERIFIED, but no zero is wrong. |
| wrong_calibration_assumption | YES, one qualified case: MyoKi channels 17-18 are on per-participant constants that are not published, and the released array does NOT use the published generic rows. Also the UJI gains actually used for KIN-MUS/KINE-ADL are the lab's placeholders in the public code. |
| subject_leakage | YES, latent, not yet realised: KINE-ADL shares 15 of 20+20 participants across experiments A and B and the overlap set lives in an undownloaded file. No split has been run, so nothing is contaminated; the hazard is that a subject-grouped split LOOKS correct and is not. |
| label_semantic_mismatch | YES, one: MyoKi `grasp` is a task-metadata lookup presented as a per-sample array, i.e. task identity relabelled, not frame-wise ground truth. |
| fake_sampling_inflation | YES, severe: MyoKi publishes every modality on one declared 2000 Hz grid while the kinematic stream changes only ~35.5 times per second - a 56.26x inflation with 98.22 % duplicated rows. |
| measured_derived_confusion | NO new case in the released arrays. All four DIPs are absent from KIN-MUS, MyoKi and KINE-ADL, and this audit proved by exact-formula test that no released column is a derived DIP. The UJI pipeline DOES derive DIP from PIP, and that derivation stays excluded from the API. |

---
# 6. OLD RESULT IMPACT

### `kinmus_task_observability/ KINMUS_TASK_OBSERVABILITY_DECISION.json and _REPORT.md (R1_POSE 0.4051, R2 0.4237, R3 0.6172, R4 0.4955, matched frame set; R5_FULL18 0.4238)`

* **class** A + B - **INTERPRETATION_DOWNGRADED**
* why: the ten index positions are unchanged, so every NUMBER is exactly the same computation on exactly the same columns. But four of the ten columns are not the anatomical DOFs they were named as: the representation is six flexion channels plus four relative-abduction channels, not ten flexion channels. Every sentence that names those four as MCP flexion or as thumb CMC flexion must be rewritten.
* survives:
  * the balanced-accuracy values themselves
  * the N1 permutation null and the frame-majority share
  * the R3 temporal-window gain and the velocity-negation control
  * the boundary-vs-interior stratification
  * the statement that single-frame information over these ten columns is not sufficient (OBS-B)
* must be restated:
  * 'shared10 pose' -> 'the ten frozen columns (6 flexion + 4 abduction)'
  * 'thumb_cmc_flexion' -> CMC1_A (abduction)
  * 'index_mcp_flexion' -> MCP2-3_A, 'ring_mcp_flexion' -> MCP3-4_A, 'pinky_mcp_flexion' -> MCP4-5_A
  * any claim that the Common Pose SUBSET loses only +0.0342 vs full18: true of these ten columns, not of the intended ten flexion DOFs

### `kinmus_task_observability/ KINMUS_FULL18_DIAGNOSTIC.json`

* **class** A + B - **INTERPRETATION_DOWNGRADED**
* why: it uses all 18 columns, so its numbers stand; but it NAMES them in the guide order, which is wrong at the same four swapped pairs
* survives:
  * the full18 balanced accuracy and its comparison to the ten-column run
* must be restated:
  * the per-column names in its `vs_shared10` block

### `kinmus_task_observability/ KINMUS_OBSERVABILITY_SOURCE_PROVENANCE.json (the `shared10_mapping` block)`

* **class** B - **INVALIDATED (naming only)**
* why: it asserts api_order == the ten intended DOF names for those indices
* survives:
  * the file hash and the corpus structure it records
* must be restated:
  * the api_order list

### `pose_api_dataset_admission/ FIRST_POC_DATASET_DECISION.json, POSE_API_DOF_MAPPING_MATRIX.{csv,json} (the KIN-MUS rows), KIN_MUS_SOURCE_AUDIT.json`

* **class** C for the representation, A for the dataset choice - **NEEDS_RERUN (representation definition only)**
* why: the DATASET verdict (KIN-MUS ADMIT, HUST REJECT, KINE-ADL CONDITIONAL) is not affected: it was decided on corpus properties, not on column indices. What is wrong is the frozen representation `shared10_poc_v1`: its index vector is correct for the guide order and wrong for the real array.
* survives:
  * the dataset admission verdicts
  * the 18-angle name list (the names are right; only the order was taken from the wrong document)
* must be restated:
  * `shared10_poc_v1.columns` must become [1, 2, 5, 6, 7, 8, 10, 11, 14, 15]
  * the KIN-MUS rows of the DOF mapping matrix for the four swapped pairs

### `pose_api_dataset_admission/ KIN_MUS_PHYSICAL_ANCHOR_AUDIT.json`

* **class** A + B - **INTERPRETATION_DOWNGRADED**
* why: its per-channel statistics are correct for the indices it used, and its anchor directions (flexion rises in manipulation) remain TRUE under the corrected naming - indeed this audit reproduced them independently at 22/22 subjects, and additionally at 22/22 for CMC1_F. Only the channel labels change.
* survives:
  * every number
  * the anchor verdicts
* must be restated:
  * the channel names in per_channel_median_deg and per_channel_p5_deg

### `db9_channel_validity/ (all artifacts)`

* **class** unchanged - **UNCHANGED**
* why: the DB9 lane works on the NinaPro DB9 array and on canonical16; it never touches a UJI column. The shared10 finding does not reach it.
* survives:
  * everything

### `pose_coordinate_audit/ (all artifacts)`

* **class** unchanged by THIS audit - **UNCHANGED / its own corrections still outstanding**
* why: the earlier lane's open items (a replication claim that compared the adapter against itself, and a `repetition` grouping error confined to its pca_*.py) are independent of the UJI column-order question. This audit neither fixed nor re-opened them; the PI decision on them is still open.
* survives:
  * everything not already flagged

---
# 7. COMMON API CANDIDATE

`CommonPoseSubset_v2_candidate` contains **11 DOFs**:

* **tier 1 (8)** - `index_mcp_flexion`, `index_pip_flexion`, `middle_mcp_flexion`, `middle_pip_flexion`, `ring_mcp_flexion`, `ring_pip_flexion`, `pinky_mcp_flexion`, `pinky_pip_flexion`
* **tier 2 (3)** - `thumb_cmc_flexion`, `thumb_mcp_flexion`, `thumb_ip_flexion`

tier 1 rationale: available in THREE external datasets (MyoKi, KIN-MUS, KINE-ADL) and the MCP and PIP flexion groups each passed a per-subject physical anchor in 22/22 subjects (median +17.79 deg for MCP, +13.08 deg for PIP, reaching -> manipulation)

tier 2 rationale: the thumb channels: identity and unit are clear, the thumb MCP+IP anchor passed 18/22 subjects (0.818, just above the 0.80 threshold) and the CMC flexion anchor 22/22, but thumb_cmc_flexion exists in only TWO external datasets (MyoKi has no thumb CMC flexion channel at all) and the whole thumb CMC complex carries the nomenclature caveat the KINE-ADL paper itself raises

Recommendation: admit only if the downstream task genuinely needs the thumb; otherwise ship tier 1 alone

Every member carries the same restriction: **semantic correspondence YES, numeric coordinate equivalence UNVERIFIED.** No two of these datasets share a demonstrated zero or unit, so the API is at best a *partially calibrated physical* interface, and an honest name for its first version is a **semantic hand-state interface**.

---
# 8. BLOCKERS

| id | owner | what |
|---|---|---|
| B1 | PI | decide the remediation for shared10_poc_v1 and for the artifacts listed in the old-result re-classification |
| B2 | PI | decide whether a corrected ten-column run (same pipeline, index vector [1, 2, 5, 6, 7, 8, 10, 11, 14, 15]) is authorised; it is a model run and was therefore NOT performed here |
| B3 | PI/data | download MyoKi P01.mat (3 816 461 856 B) or the whole corpus (145 463 536 055 B) to lift every MyoKi subject-level statement out of UNRESOLVED |
| B4 | PI/data | download KINE-ADL BE_UJI_DATASET.mat (644 185 378 B, sha256 808f0dab...) to resolve the global_person_id map and confirm the column order against real values |
| B5 | external | the per-glove CyberGlove gains actually used by the UJI group and by the MyoKi authors: without them no raw->processed parity is closable on either corpus |
| B6 | PI | the UJI wrist-deviation sign conflict cannot be resolved from documents; it needs either author confirmation or a raw-glove anchor |

---
# 9. NEXT EXPERIMENT

**Exactly one, not started.** A CORRECTED KIN-MUS REPRESENTATION RE-RUN, authorised by the PI.

* what: re-execute the ALREADY FROZEN kinmus_task_observability pipeline unchanged, with the single edit that R1's column vector becomes [1, 2, 5, 6, 7, 8, 10, 11, 14, 15] (the ten intended flexion DOFs) instead of [0, 2, 4, 6, 7, 8, 9, 11, 13, 15]; R5_FULL18 is untouched.
* why this one: it is the cheapest experiment that resolves the largest open uncertainty: whether the OBS-B conclusion survives when the representation really is the ten intended anatomical DOFs. It needs no new data, no new code beyond one index vector, and no GPU.
* cost: one CPU re-run of an existing pre-registered pipeline
* must be frozen first: the corrected index vector and its provenance must be pre-registered and hashed before the re-run, exactly as the original run was
* no training of any kind was performed or started by this audit

---
# 10. ARTIFACTS

Every path and SHA-256 is in `ARTIFACT_MANIFEST.json`. The load-bearing ones are:

* `AUDIT_PLAN.md` - sha256 `fba2b20623392dd809d5ed28c7850387acc721e9a91ff1611e7fba0d89fc889d`
* `PLAN_SHA256.txt` - sha256 `4cf71c6b9c7e51847c6c7820ac15c9e1a9372afe0e91dc77314ecfb8524421e7`
* `SOURCE_PROVENANCE.md` - sha256 `cad73b8768a3c1a6440b9d9ace033faab00b1bfb078665333ed63b8c152a10b6`
* `DATASET_MANIFEST.csv` - sha256 `befac6871b3457294079511686f718b7bb71e91eae5fd21cf252daff85b8cdd7`
* `SCHEMA_AUDIT.md` - sha256 `4a570616974f4c844576a4bcb977c81ad0e12e9b909e22e2c045f818eabd9cb6`
* `SHARED10_PROVENANCE_AUDIT.md` - sha256 `2a0f7b899f9b8745f9d72a9c4bb963a1ea31ee8aec6b2bda9c1bccf1aa9ce1ca`
* `COORDINATE_LEDGER.csv` - sha256 `3d738e7fc3e1b3a35ace3e2e9f65ad1ace453297189408ec107387c82dfe9b3b`
* `PHYSICAL_QC.md` - sha256 `bd2c508359f114b3db272d05a31cac8ea44d807406e4dc132e533aa791508f9e`
* `LABEL_AUDIT.md` - sha256 `34912b502732ee6d6541841745448a4272acec747c709a239cd3cde3f0119327`
* `SYNC_AUDIT.md` - sha256 `4b0f7ce5cdbd3a59dbd0bcb4db18ad53e8af747c6c732db81de1914f5b817e0e`
* `COMMON_API_MAPPING_MATRIX.csv` - sha256 `06c9c811b2bf72203da18bd81f869afc36ce2482c0de79a3780c5399a7c613b6`
* `LABEL_ADMISSION_MATRIX.csv` - sha256 `8a1d851b88a7c69d05b2f7a7b761a1625373cad5c85fcb335d6507a268cc4b57`
* `BUGFIX_LOG.md` - sha256 `43572641204ad305b737a0bc92607861dec1d877c232f4b2a46ba3b791ba87ad`

