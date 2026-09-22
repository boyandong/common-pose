# posture_decoder — joint angles → hand posture (Ninapro DB9)

**Role in the project.** This is the decoupled half of the intended pipeline:

```
emg2pose wrist EMG ──> emg2pose pose model ──> canonical hand state ──┐
                                                                      ├─> posture decoder
                                   Ninapro DB9 ground-truth angles ───┘
```

Only the right-hand side is built here. **No EMG, no deep networks.** The
question this stage answers is deliberately narrow and falsifiable:

> Given only hand joint angles, which labelled hand postures can be reliably
> recognized across subjects?

If that question has no useful answer, the EMG side is not worth connecting yet.

---

## 1. Why Ninapro DB9 and not emg2pose

emg2pose was investigated first and **rejected as a source of posture labels**.
The reason is a fact about the dataset, not a preference:

* The official HDF5 files contain only `time`, `joint_angles` (T, 20) and `emg`.
  There is **no per-frame gesture label**.
* The only official label is the `stage` attribute, and the 29 stages are
  **compound activities** (`DoorknobFingerGraspFistGrab`, `PokePinchCloseFar`,
  `ShakaVulcanPeace`, …), not single postures. This was cross-checked against
  NEMAR's BIDS re-host of emg2pose, whose `events.tsv` files carry only the
  stage name plus `BAD_IK` intervals.

So `P(hand state | fist)` cannot be fitted from emg2pose without inventing
labels. Ninapro DB9 does have explicit, synchronized posture labels, so it is
used for the decoder. emg2pose is retained only for (a) the UmeTrack joint
representation and (b) the canonical mapping — both verified against the
official hand model, using the already-local official mini dataset.

---

## 2. Data of record

| | |
|---|---|
| Dataset | **Ninapro DB9** — calibrated CyberGlove-II kinematics |
| Official page | https://ninapro.hevs.ch/instructions/DB9.html |
| Paper | Jarque-Bou, Atzori & Müller, *Sci Data* **7**:12 (2020), [doi:10.1038/s41597-019-0349-2](https://doi.org/10.1038/s41597-019-0349-2) |
| URL pattern | `https://ninapro.hevs.ch/files/DB9/<source_db>/s_<n>_angles.zip` |
| Subject → source DB | DB1 = 1–27, DB2 = 28–67, DB5 = 68–77 (transcribed from the DB9 page) |
| Contents | 77 subjects, 22 CyberGlove-II channels, **40 movements** + rest |
| Label variable | `restimulus` (a-posteriori refined movement label) |
| Repetition variable | `rerepetition` |

**40 movements = Ninapro Exercise B (17) + Exercise C (23).** This is stated in
the 2020 paper ("*40 hand movements plus rest … correspond to exercise B and C*")
and is confirmed in the data: exercise-B files carry `restimulus` 0–17, exercise-C
files carry 0–23.

### 2.1 Exercise numbering is a trap — verified, not assumed

Each archive keeps the **source database's own** exercise numbering, which
differs between DB1 and DB2/DB5:

| | exercise B | exercise C |
|---|---|---|
| DB1 subjects (1–27) | file `S<n>_E2_A1.mat` | file `S<n>_E3_A1.mat` |
| DB2/DB5 subjects | exercise field 1 | exercise field 2 |

`db9.loader.ninapro_letter()` therefore resolves B/C from
`(source_db, exercise_field)` **and cross-checks against `max(restimulus)`**,
which must be 17 for B and 23 for C. A disagreement raises rather than
silently mislabelling every sample.

---

## 3. The canonical anatomical representation

`db9/canonical.py`. This is the piece that lets emg2pose and DB9 talk to each
other, and the place where an index-based 22→20 mapping would go silently wrong.

**The two orderings are structurally different:**

* **emg2pose (20 DOF)**: thumb `[CMC_FE, CMC_AA, MCP_FE, IP_FE]`, then per finger
  `[MCP_AA, MCP_FE, PIP_FE, DIP_FE]` for index → pinky.
* **DB9 CyberGlove (22 channels)**, read verbatim from each recording's own
  `order_of_angles` variable:

  ```
   1:CMC1_f   2:CMC1_a   3:MCP1    4:IP1     5:MCP2_f  6:MCP2_a  7:PIP2
   8:MCP3_f   9:PIP3    10:MCP4_f 11:MCP4_a 12:PIP4   13:CMC5   14:MCP5_f
  15:MCP5_a  16:PIP5    17:DIP2   18:DIP3   19:DIP4   20:DIP5   21:WRIST_F
  22:WRIST_A
  ```

  Consecutive index ≠ same joint. For example `INDEX_DIP_FE` is emg2pose #7 but
  DB9 channel #17; `RING_MCP_AA` is emg2pose #12 but DB9 channel #11.

**Result — exactly 18 canonical DOF are observable in both datasets:**

| canonical DOF | emg2pose | DB9 channel |
|---|---|---|
| `THUMB_CMC_FE` | 0 | `CMC1_f` |
| `THUMB_CMC_AA` | 1 | `CMC1_a` |
| `THUMB_MCP_FE` | 2 | `MCP1` |
| `THUMB_IP_FE` | 3 | `IP1` |
| `INDEX_MCP_FE` | 5 | `MCP2_f` |
| `INDEX_PIP_FE` | 6 | `PIP2` |
| `INDEX_DIP_FE` | 7 | `DIP2` |
| `MIDDLE_MCP_FE` | 9 | `MCP3_f` |
| `MIDDLE_PIP_FE` | 10 | `PIP3` |
| `MIDDLE_DIP_FE` | 11 | `DIP3` |
| `RING_MCP_AA` | 12 | `MCP4_a` |
| `RING_MCP_FE` | 13 | `MCP4_f` |
| `RING_PIP_FE` | 14 | `PIP4` |
| `RING_DIP_FE` | 15 | `DIP4` |
| `PINKY_MCP_AA` | 16 | `MCP5_a` |
| `PINKY_MCP_FE` | 17 | `MCP5_f` |
| `PINKY_PIP_FE` | 18 | `PIP5` |
| `PINKY_DIP_FE` | 19 | `DIP5` |

**Missing / non-equivalent DOF, with reasons:**

| canonical DOF | status | reason |
|---|---|---|
| `INDEX_MCP_AA` | in emg2pose, **unusable in DB9** | channel `6:MCP2_a` is all-NaN. Official docs: "*Sensor 11 (which corresponds to MCP2-3_A) was not included into the calibrated data due to noise problems.*" Verified: it is the only all-NaN column, in every file examined. |
| `MIDDLE_MCP_AA` | in emg2pose, **absent in DB9** | The 22-channel glove has abduction sensors for index, ring and pinky only. There is no middle-finger abduction channel. |
| `PINKY_CMC_FE` | **DB9 only** | No pinky CMC in emg2pose's 20 outputs. |
| `WRIST_FE`, `WRIST_DEV` | **DB9 only** | emg2pose deliberately does not regress the wrist. |

**Units differ and are converted explicitly:** DB9 calibrated `angles` are in
**degrees** (measured global range −322…+173 over subject 1 — only sensible in
degrees); emg2pose outputs **radians**.

Channels are verified, not assumed: `canonical.verify_db9_order()` compares each
recording's own `order_of_angles` against the official table and reports any
mismatch instead of repairing it. `canonical.verify_emg2pose_order()` asserts the
mapping reproduces `emg2pose/constants.py::JOINTS` exactly.

---

## 4. Movement families — the axis the science turns on

`db9/labels.py`. The 40 movements are not 40 independent postures. They are
typed by what the movement physically *is*, which predicts how much of it joint
angles can carry:

| family | count | observable in the 22 angles? |
|---|---|---|
| `posture` | 8 | yes — static hand shapes (Exercise B 1–8) |
| `wrist` | 5 | yes in DB9 (`WRIST_F` / `WRIST_A`); **never** in emg2pose |
| `forearm_rot` | 4 | **no** — pronation/supination is forearm rotation, not a hand DOF; no glove channel measures it |
| `grasp` | 23 | partially — 10 of them differ mainly by the object held |

Movement names are transcribed from Ninapro's official labelled figure
(`SData_Movements.png`, sha256 `f240dfcf…c45b`), read directly rather than
recalled.

---

## 5. Layout

```
posture_decoder/
├── db9/
│   ├── labels.py       official movement vocabulary + identifiability families
│   ├── loader.py       official .mat -> validated arrays; exercise resolution
│   ├── canonical.py    shared canonical hand representation (18 DOF)
│   └── quality.py      flag-not-delete data-quality checks
├── tools/
│   ├── fetch_db9.py    resumable parallel downloader (drives curl)
│   ├── unpack_db9.py   CRC-verified extraction, manifest
│   ├── inspect_db9.py  what is actually in a file
│   └── verify_canonical_emg2pose.py   emg2pose half of the mapping, on local data
├── experiments/
│   ├── build_dataset.py   .mat -> compact auditable .npz
│   └── run_baseline.py    subject-independent baselines + figures
└── report.md           results
```

---

## 6. Running it

```bash
cd emg2pose_handstate/posture_decoder

# 1. download (resumable, ~385 MB, verified by size + sha256)
python -X utf8 tools/fetch_db9.py --out ../data/ninapro_db9/raw \
       --subjects "1-16;68-73" --workers 6

# 2. CRC-verified extraction
python -X utf8 tools/unpack_db9.py --raw ../data/ninapro_db9/raw \
       --out ../data/ninapro_db9/extracted

# 3. sanity-check one file (channel names, labels, units, NaN columns)
python -X utf8 tools/inspect_db9.py --extracted ../data/ninapro_db9/extracted --limit 1

# 4. build the frame table
python -X utf8 experiments/build_dataset.py --extracted ../data/ninapro_db9/extracted \
       --out ../data/ninapro_db9/dataset.npz --stride sensor

# 5. baselines + figures
python -X utf8 experiments/run_baseline.py --dataset ../data/ninapro_db9/dataset.npz \
       --out-dir ../data/ninapro_db9/results --fig-dir ../data/ninapro_db9/figures \
       --model-dir ../data/ninapro_db9/models

# (no network) verify the emg2pose half of the canonical mapping
python -X utf8 tools/verify_canonical_emg2pose.py \
       --mini-dir <DATA_ROOT>/official/emg2pose_dataset_mini \
       --hand-model <BASELINE_ROOT>/emg2pose/emg2pose/UmeTrack/dataset/generic_hand_model.json \
       --out ../docs/canonical_emg2pose_verification.json
```

`--stride sensor` keeps one sample per ~25 Hz, i.e. the CyberGlove's true link
rate. DB9 super-sampled that to 100 Hz (DB1) / 200 Hz (DB5) / 2 kHz (DB2), so
keeping every sample would over-count temporally correlated frames by 4–80×.
Trials are never discarded; only interpolated duplicates are.

---

## 7. Standing caveats carried into any result

1. **Rest dominates the sample count.** Measured on subjects 1–2: **63% of
   frames** carry `restimulus == 0`. The refined labelling trims each 5 s
   prompted movement to ~3 s of confident movement. Rest is excluded from
   classification but sets the base rate.
2. **The glove is a ~25 Hz device.** Everything above that is interpolation.
3. **DIP sensors are hand-size dependent.** Official note: they "provide
   reliable angles when subject hand size is big … may provide partial results
   when the hand of the subject is small."
4. **No inclinometer in DB1-derived files.** `inclin` is absent, so the only
   wrist information is the glove's own `WRIST_F` / `WRIST_A`.
5. **Anatomical limits are not asserted.** DB9's calibrated scale is
   subject-specific, so external anatomical joint limits cannot be applied to
   these numbers without a calibration mapping the release does not provide.
   `db9/quality.py` emits an explicit `TODO` rather than inventing constants.
6. **`subject_z` normalization is unsupervised adaptation.** It uses the test
   subject's own unlabelled samples. It is reported separately and never mixed
   into the headline number.
