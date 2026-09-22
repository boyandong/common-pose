# SCHEMA AUDIT

**Frozen plan SHA-256:** `fba2b20623392dd809d5ed28c7850387acc721e9a91ff1611e7fba0d89fc889d`  
**Commit:** COMMIT PENDING

Every statement is tagged `[DOC]`, `[EMPIRICAL]`, `[INFERENCE]` or `[UNRESOLVED]`.

---
## 1. KIN-MUS UJI

**Source array** `[EMPIRICAL]`: `KIN_MUS_UJI.mat` -> variable `EMG_KIN_v4` (1 x 1716 struct array) -> field `.Kinematic_data`, one `(N_i, 18)` array per container; stacked = `564894 x 18`.  SHA-256 `530a9e51b19574b0f5dee0c9...`

| quantity | value |
|---|---|
| subjects | 22 (1..22) |
| ADLs | 26 |
| phases | [1, 2, 3] = REACHING / MANIPULATION / RELEASING |
| trial containers | 1716 |
| usable trials | 1713 |
| unique kinematic shapes | 497 (['[96, 18]', '[121, 18]', '[119, 18]']...) |
| grid cells expected / present | 1716 / 1714 |
| duplicate cells | {'22|25|2': 2, '22|25|3': 2} |
| empty containers | 3 |
| malformed containers | 3 |
| NaN / Inf in the stacked matrix | 0 / 0 |
| constant channels | [] |
| bit-identical channel pairs | [] |
| |r| > 0.985 channel pairs | 0 |
| non-monotonic timestamp trials | 0 |
| implied sampling rate (median over trials) | 100.0000 Hz (documented 100 Hz) |

### 1.1 The documented missing cell is NOT a NaN in the file

> paper Usage Notes: 'For ADL #25 of subject #22, all the data were lost. In this case, a Not a Number (NaN) value was presented.'  `[DOC]`

> 3 trial container(s) are EMPTY arrays, not NaN-bearing arrays; the stacked matrix contains 0 NaN value(s)  `[EMPIRICAL]`

**DOCUMENTATION vs DATA: the paper describes a NaN; the released file represents the loss as an empty container. Both mean the same missing cell, but a loader that expects NaN will not detect it. This is a real trap for anyone reusing the corpus.**  `[INFERENCE]`

### 1.2 Empty containers, verbatim `[EMPIRICAL]`

```
subject=21 adl=25 phase=1 shape=[]
subject=22 adl=25 phase=2 shape=[]
subject=22 adl=25 phase=3 shape=[]
```
### 1.3 Duplicate grid cells, verbatim `[EMPIRICAL]`

```
(subject|adl|phase)=22|25|2  count=2
(subject|adl|phase)=22|25|3  count=2
```
---
## 2. MyoKi

The participant corpus is 35 files of 3.17-4.95 GB. This audit downloaded the official metadata/code set and `Synchronicity_test.mat` (48 961 776 B), whose variable set and per-variable shapes are identical to a participant file `[EMPIRICAL]`:

| variable | shape | dtype |
|---|---|---|
| `frequency` | [] | int32 |
| `repetition` | [83267] | int32 |
| `emg` | [83267, 12] | float32 |
| `gyro` | [83267, 27] | float32 |
| `acc` | [83267, 27] | float32 |
| `fmg` | [83267, 24] | float32 |
| `glove` | [83267, 18] | float32 |
| `timestamp` | [83267] | float32 |
| `task` | [83267] | int32 |
| `glove_calibrated` | [83267, 18] | float64 |

* `frequency` field = **2000** - one scalar for the whole file, i.e. the file is declared to be on a single 2000 Hz grid `[EMPIRICAL]`.
* measured grid rate = 2000.002 Hz over 41.633 s `[EMPIRICAL]`.
* non-positive timestamp steps = 0 `[EMPIRICAL]`.
* the per-modality truth of that single declared rate is audited in `SYNC_AUDIT.md` - it is **not** the same for every modality.

### 2.1 Documented participant schema `[DOC]`

* **subsets**: subset 1 P01..P25 (no FMG), subset 2 P26..P35 (with FMG)
* **n_participants**: 35
* **excluded_from_38**: 3 excluded for corrupted task labels
* **n_tasks**: 74
* **n_repetitions**: 6
* **arm**: right arm only ('data is collected exclusively from the participant's right arm')
* **variables**: ['task', 'grasp', 'repetition', 'frequency', 'timestamp', 'emg(12)', 'acc(27)', 'gyro(27)', 'glove(18)', 'glove_calibrated(18)', 'fmg(24, subset 2 only)']
* **label_zero**: task 0 and grasp 0 mark the transition phase between tasks
* **evidence**: DOC

---
## 3. KINE-ADL BE-UJI

The corpus (644 185 378 B `BE_UJI_DATASET.mat` + 424 354 198 B `CSV DATA.zip`) was **not** downloaded. The 1 815 639 B official guide was, and its local SHA-256 equals the hash published by the Mendeley public API exactly `[EMPIRICAL]`, so the schema document is authentic.

| quantity | value |
|---|---|
| experiments | A and B |
| subjects per experiment | 20 and 20 |
| people in both | 15 |
| unique people | 25 |
| recordings | RECORD 101..199 (A), 201..279 (B) |
| tasks / elementary tasks | 58 / 178 (99 in A, 79 in B) |
| ANGLES width | 36 = 18 R_ then 18 L_ |
| rate | 100 Hz |
| gloves | CyberGlove II right, CyberGlove III left, 18 gauges each |

### 3.1 Subject identity and the grouped-split hazard `[INFERENCE]`

**Risk level: UNRESOLVABLE WITHOUT THE CORPUS.**

the mapping from (EXPERIMENT, SUBJECT) to a person is inside SUBJECT_DATA of BE_UJI_DATASET.mat, which was NOT downloaded. 15 people appear in both experiments.

no grouped split that crosses experiment A and B may be constructed until SUBJECT_DATA is available; a split by experiment is safe, a split by SUBJECT-within-experiment silently leaks 15 people across the folds

`kine_global_subject_map.csv` therefore lists all 40 (experiment, subject) keys with `global_person_id = UNKNOWN`, rather than inventing one. A split by experiment is safe; a split by subject **within** experiment is not. `[UNRESOLVED]` until `BE_UJI_DATASET.mat` is obtained.

### 3.2 Wrist channels `[DOC]`

guide marks both WR_F and WR_A with '*Some wrist angles are missing because of improper fitting of the wrist sensors to some subjects' hands.' [DOC]

