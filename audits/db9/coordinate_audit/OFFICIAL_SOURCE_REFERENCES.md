# OFFICIAL SOURCE REFERENCES

Primary sources consulted for the definition of every canonical16 dimension, in the priority order the audit brief specifies: official source code and dataset documentation first, then papers, then project-frozen derivation notes.  Secondary descriptions were used only where a primary source is silent, and that is stated.

## 1. Ninapro DB9 — dataset documentation and source data

* **Official DB9 page** — <https://ninapro.hevs.ch/instructions/DB9.html>
  * documents the released variables: `glove` (22 columns, *uncalibrated*), `angles` (22 columns, *calibrated* "by applying the post-processing calibration procedure"), `inclin`, `restimulus`, `rerepetition`, `order of angles`.
  * states the one exclusion: *"Sensor 11 (which corresponds to MCP2-3_A) was not included into the calibrated data due to noise problems."*
  * states the DIP caveat quoted verbatim in the audit report §4: DIP sensors *"provide reliable angles when subject hand size is big … they may provide partial results when the hand of the subject is small. Therefore, attention should be taken when using their information."*
  * lists the 77 participants with the **participant's own handedness** (not the recording side) and hosts the per-slot archives.
* **Jarque-Bou, Atzori & Müller, _A large calibrated database of hand movements and grasps kinematics_, Scientific Data 7:12 (2020)** — doi:[10.1038/s41597-019-0349-2](https://doi.org/10.1038/s41597-019-0349-2), PMC6952409.
  * Table 6 ("Sign criteria considered"): `DIP(2-5)_F, PIP(2-5)_F, IP1_F, MCP(1-5)_F` = **Flexion+/Extension−**; `CMC1_F` = Flexion+/Extension−; `CMC1_A` = **Abduction+/Adduction−**.
  * calibration section: *"the sensor signals were transformed according to the outputs relative to a reference posture. The reference posture was chosen as the central part of movement 11 in exercise B, corresponding to the hand resting on the table with the fingers closed together and extended."*
  * Methods: the calibration protocol was recorded on **10 subjects**, and those gains were then applied to compute the joint angles **for all subjects**.
  * Results: the database is the *harmonisation* of three previously released datasets (DB1, DB2, DB5).
  * full text consulted locally at `data/ninapro_db9/docs/db9_paper_fulltext.xml`.
* **Atzori et al. 2014** — the reference for the exercise/movement protocol, consulted locally at `data/ninapro_db9/docs/atzori2014_fulltext.txt`.
  * Table 1 establishes the source-database protocol numbering that the audit's file-selection rule depends on: DB1 exercise 1 = A(12), 2 = B(17), 3 = C(23); **DB2/DB5 exercise 1 = B(17)**, 2 = C(23), 3 = D(9).
  * the 17-movement exercise lists 8 hand configurations followed by 9 wrist movements, which is the order the audit's movement-stream check tests against the data.

## 2. emg2pose — official source code and documentation

* **Official repository** — <https://github.com/facebookresearch/emg2pose>, cloned at commit `5f6f62b1a0a08426adffe55900842e75a8adb38c` (clean).
  * `emg2pose/constants.py` defines `NUM_JOINTS = 20` and the ordered `JOINTS` list with explicit indices 0–19.  This ordering is load-bearing (`metrics.py` selects axes by `[j.index for j in JOINTS if finger in j.groups]`).
  * `emg2pose/UmeTrack/lib/common/hand_skinning.py::_joint_local_transform` computes `angle_axis = rotation_axis * joint_angle` then `rot_mat = so3_exp_map(angle_axis)`, so the stored number is a **rotation magnitude in radians about a fixed joint-specific axis**.
  * `emg2pose/utils.py::get_ik_failures_mask` encodes an IK failure as an **all-zero row**, not NaN.
  * `emg2pose/UmeTrack/dataset/generic_hand_model.json` holds `joint_limits` for the 22-DOF model; the emg2pose output is 20 of them (the two wrist DOF are excluded and re-inserted as zeros by `kinematics.forward_kinematics`).
* **Project-frozen derivation notes** (read as the project's own record, distinguished from primary sources):
  * `docs/joint_angle_definition.md` — the 20D ordering table, units, the `[VERIFIED-EXEC]` FK result that 15/15 FE joints are flexion-positive, the per-finger AA polarity finding, the official joint-limit table, and the IK-failure semantics.
  * `docs/CANONICAL16_CONTRACT.md` — the frozen 20D → 16D contract, the resolved source-index vector, and the explicit statement that canonical16 is a lossy projection.
  * `docs/DB9_CANONICAL16_MAPPING.md` — the frozen DB9-side mapping, the degrees→radians conversion, the Table 6 sign criteria, the reference posture, and the single frozen thumb-AA sign flip with its evidence.
  * `data/db9_posture16/thumb_web_sign_evidence.json`, `thumb_zero_alignment.json`, `thumb_axis_resolution.json` — the geometry behind that one sign flip.

## 3. Where a primary source is silent

* **The unit symbol is never written next to the DB9 numbers.** The paper quotes a calibration precision "below 5 degrees" and Atzori 2014 describes the CyberGlove as returning values "for an average resolution of less than one degree", and the measured corpus range (−322 … +173) is only physically sensible in degrees — but the unit is **inferred with converging evidence**, not quoted.  Recorded as such by the frozen mapping document and carried here.
* **No per-channel calibration coefficients are published.** The released archives contain only `glove` (raw) and `angles` (calibrated); the gains and offsets that connect them are not distributed.  The audit therefore *recovers* the implied per-channel linear map from the data (see `LARGE_OFFSET_FORENSICS.json`), which is a measurement, not a quotation.
* **No recording-side field exists in DB9.** The page's Handedness column is the participant's own handedness; the protocol instructed the right hand.  This is why criterion I is recorded as UNCERTAIN rather than PASS.
* **The emg2pose zero pose is a model-construction artefact**, not a documented calibration trial.  That its FK pose is a fingers-extended hand is established by project forward-kinematics checks, not by an official statement.

