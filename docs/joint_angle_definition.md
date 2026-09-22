# emg2pose Hand Joint Angle Definition

**Purpose:** authoritative reference for the 20 hand joint angles produced by the
official `emg2pose` baselines. Written for downstream consumers (Sessions 3 & 4)
that need to know *exactly* what each output number means.

**Status of every claim below** is marked as one of:

| Tag | Meaning |
|---|---|
| `[OFFICIAL-CODE]` | Read directly from the official repository source. |
| `[OFFICIAL-DATA]` | Measured from the official downloadable dataset / checkpoints. |
| `[VERIFIED-EXEC]` | Produced by executing code in this workspace; artifact recorded. |
| `[DERIVED]` | Follows from the above by geometry/arithmetic; reasoning shown. |
| `[UNKNOWN]` | Not determinable from official material; do not guess. |

Primary evidence artifacts:
- `docs/joint_convention_verification.txt` — FK-based sign/unit verification
- `docs/smoke_test_report.txt` — real inference run on official data
- `docs/smoke_test_evidence.json` — machine-readable results

---

## 1. Output ordering — the single most important table

`N_joint = 20`. `[OFFICIAL-CODE]` — `emg2pose/constants.py::NUM_JOINTS = 20` and
the `JOINTS` list, which defines the index order. `[OFFICIAL-DATA]` — confirmed
empirically: every official HDF5 file stores `joint_angles` with shape `(T, 20)`.

| # | Name | Finger | Joint | Motion axis | Group |
|---|---|---|---|---|---|
| 0 | `THUMB_CMC_FE` | thumb | CMC (carpometacarpal) | flexion / extension | proximal |
| 1 | `THUMB_CMC_AA` | thumb | CMC | abduction / adduction | proximal |
| 2 | `THUMB_MCP_FE` | thumb | MCP (metacarpophalangeal) | flexion / extension | mid |
| 3 | `THUMB_IP_FE` | thumb | IP (interphalangeal) | flexion / extension | distal |
| 4 | `INDEX_MCP_AA` | index | MCP | abduction / adduction | proximal |
| 5 | `INDEX_MCP_FE` | index | MCP | flexion / extension | proximal |
| 6 | `INDEX_PIP_FE` | index | PIP (proximal interphalangeal) | flexion / extension | mid |
| 7 | `INDEX_DIP_FE` | index | DIP (distal interphalangeal) | flexion / extension | distal |
| 8 | `MIDDLE_MCP_AA` | middle | MCP | abduction / adduction | proximal |
| 9 | `MIDDLE_MCP_FE` | middle | MCP | flexion / extension | proximal |
| 10 | `MIDDLE_PIP_FE` | middle | PIP | flexion / extension | mid |
| 11 | `MIDDLE_DIP_FE` | middle | DIP | flexion / extension | distal |
| 12 | `RING_MCP_AA` | ring | MCP | abduction / adduction | proximal |
| 13 | `RING_MCP_FE` | ring | MCP | flexion / extension | proximal |
| 14 | `RING_PIP_FE` | ring | PIP | flexion / extension | mid |
| 15 | `RING_DIP_FE` | ring | DIP | flexion / extension | distal |
| 16 | `PINKY_MCP_AA` | pinky | MCP | abduction / adduction | proximal |
| 17 | `PINKY_MCP_FE` | pinky | MCP | flexion / extension | proximal |
| 18 | `PINKY_PIP_FE` | pinky | PIP | flexion / extension | mid |
| 19 | `PINKY_DIP_FE` | pinky | DIP | flexion / extension | distal |

`FE` = flexion/extension, `AA` = abduction/adduction. `[OFFICIAL-CODE]` — comment
in `constants.py`: `# AA: abduction, adduction` / `# FE: flexion, extension`.

> **This ordering was established from official source, not assumed.** Session 1
> flagged that the representation must not be guessed as "5 fingers × 4 angles";
> the table above is the literal, index-by-index enumeration from
> `emg2pose/constants.py::JOINTS`, cross-checked against the released data
> (`(T, 20)` in every one of the 30 official mini-dataset HDF5 files).
>
> **Machine-readable version for codegen:** `docs/joint_reference_table.json`
> (auto-generated from official source by `inference/make_joint_reference.py`,
> so it cannot drift). Human-readable: `docs/joint_reference_table.md`.

**Notable structural facts:**

- **The wrist is NOT in the outputs.** `[OFFICIAL-CODE]` — the paper states
  "We do not regress to wrist angles, which were not recorded for this dataset."
  The underlying hand model has 22 DOF (20 hand + 2 wrist); `emg2pose.kinematics.
  forward_kinematics` **appends two zeros** for the wrist. `[OFFICIAL-CODE]`
  The 20 outputs are therefore all *finger* joints.
- **The thumb is modelled differently from the other four fingers.** The thumb
  uses CMC + MCP + IP (3 joints, 3 DOF). Each other finger uses MCP + PIP + DIP,
  and **only the MCP carries the extra abduction DOF**, giving 4 DOF per finger.
  `[OFFICIAL-CODE]` — paper: "each joint had a degree of freedom for flexion and
  extension, while each MCP joint had an additional degree of freedom for
  abduction and adduction."
- **Total** = 3 (thumb) + 4×4 (index/middle/ring/pinky) = **19**… but the
  official list has 20 because the thumb MCP is split into two DOF
  (`THUMB_CMC_FE`, `THUMB_CMC_AA`, `THUMB_MCP_FE`, `THUMB_IP_FE` = 4 thumb DOF).
  Reconciled: thumb 4 + 4 fingers × 4 = 20. `[DERIVED]`

There is **no separate finger ordering ambiguity**: the order is explicitly
enumerated in `constants.py`, index-by-index, and the paper confirms
"thumb, followed by the index, middle, ring, and pinky fingers". `[OFFICIAL-CODE]`

---

## 2. Units — RADIANS

**The baseline outputs joint angles in RADIANS.** `[VERIFIED-EXEC]`

Evidence chain:

1. `emg2pose/UmeTrack/lib/common/hand_skinning.py::_joint_local_transform`
   computes `angle_axis = rotation_axis * joint_angle`, then
   `rot_mat = so3_exp_map(angle_axis)`. `[OFFICIAL-CODE]`
2. `so3_exp_map` is the Rodrigues exponential map, which takes radians.
   `[OFFICIAL-CODE]`
3. `[VERIFIED-EXEC]` `so3_exp_map(pi * ẑ)` returns
   `[[-1,0,0],[0,-1,0],[0,0,1]]` — i.e. an input of `pi` produces a 180° rotation.
   This confirms the input is interpreted as radians.
4. `[OFFICIAL-DATA]` The observed prediction range is
   `[-0.57, +1.60]` rad = `[-32.8°, +91.9°]` for a real session
   (`docs/smoke_test_report.txt`). Interpreting these numbers as degrees would
   imply a 1.6° hand range of motion, which is anatomically impossible.

**Do not pass these values to a degree-expecting API without conversion.**
`numpy.degrees(angles)` converts.

---

## 3. Sign convention and per-joint range

### 3.1 Flexion/extension (the 15 `*_FE` joints): **positive = flexion**

`[VERIFIED-EXEC]` — full forward-kinematics test in
`inference/verify_joint_conventions.py`, output in
`docs/joint_convention_verification.txt`:

> **15/15 FE joints move the fingertip landmark TOWARD the palm centre at their
> +limit ⟹ POSITIVE = FLEXION, NEGATIVE = EXTENSION.**

Converging supporting evidence `[OFFICIAL-DATA]` — the official `joint_limits`
stored inside `generic_hand_model.json` are strongly asymmetric toward positive
for the `FE` joints, e.g.:

| Joint | min | max |
|---|---|---|
| `INDEX_PIP_FE` | 0.00° | **+107.86°** |
| `INDEX_DIP_FE` | 0.00° | **+82.14°** |
| `MIDDLE_PIP_FE` | 0.00° | **+107.86°** |
| `RING_PIP_FE` | 0.00° | **+107.86°** |
| `PINKY_PIP_FE` | 0.00° | **+107.86°** |
| `THUMB_MCP_FE` | 0.00° | **+73.75°** |

A joint whose reachable range is `[0°, +108°]` can only be a flexion-positive
joint, since physiologically the PIP joint flexes to ~100-110° and cannot extend
past 0°.

### 3.2 Abduction/adduction (the 5 `*_AA` joints): **NO single global sign**

`[VERIFIED-EXEC]` — rotation of the finger's proximal segment about the palm
normal (right-hand rule) at each joint's `+limit`:

| Joint | Rotation at `+limit` about palm normal | Magnitude |
|---|---|---|
| `THUMB_CMC_AA` | **CW** (negative) | 13.78° |
| `INDEX_MCP_AA` | CCW (positive) | 7.70° |
| `MIDDLE_MCP_AA` | CCW (positive) | 5.09° |
| `RING_MCP_AA` | CCW (positive) | 4.94° |
| `PINKY_MCP_AA` | CCW (positive) | 7.05° |

**Consequence:** the polarity is *per-finger*; fingers that fan out on opposite
sides of the hand's midline necessarily rotate in opposite directions for the
anatomically identical motion ("abduct"). A blanket "positive = abduction" rule
for all five AA joints is **WRONG**.

**Practical guidance for downstream consumers:** treat the five `AA` channels as
**signed** quantities tied to that joint's own rotation axis in
`generic_hand_model.json`. If you need anatomically labelled abduction, either
(a) consume the values through the official FK (which is what they are defined
against), or (b) fit the per-finger mapping empirically against FK output.
Do **not** apply a single global sign flip. `[DERIVED]`

### 3.3 Are the values angles about anatomically-aligned axes?

**No, not exactly.** `[OFFICIAL-DATA]` — the rotation axes are unit vectors that
are *approximately but not exactly* canonical:

| Joint | axis (x, y, z) | dominant component |
|---|---|---|
| `INDEX_PIP_FE` | (-0.052, +0.013, **-0.999**) | ≈ -z |
| `MIDDLE_PIP_FE` | (-0.117, -0.034, **-0.993**) | ≈ -z |
| `RING_PIP_FE` | (-0.281, -0.156, **-0.947**) | ≈ -z |
| `PINKY_PIP_FE` | (-0.394, -0.278, **-0.876**) | ≈ -z |
| `INDEX_MCP_AA` | (-0.043, **-0.999**, +0.018) | ≈ -y |
| `THUMB_CMC_FE` | (+0.875, +0.476, -0.084) | oblique (thumb is out-of-plane) |

So each value is a **rotation magnitude in radians about a fixed, joint-specific
axis**, not a rotation about a global x/y/z axis. This matters if you plan to
re-derive kinematics yourself rather than using the official FK.

---

## 4. Official per-joint limits (radians and degrees)

> ⚠️ **§4a below is mandatory reading before using ground-truth `joint_angles`.**

### 4a. IK failures are all-zero rows — MASK THEM

`[OFFICIAL-CODE]` `[VERIFIED-EXEC]` — the official helper is
`emg2pose.utils.get_ik_failures_mask`:

```python
zeros = np.zeros_like(joint_angles)
is_zero = np.isclose(joint_angles, zeros)
return ~np.all(is_zero, axis=-1)     # True where the row is NOT all-zero
```

So an **IK failure is encoded as a row of 20 exact zeros, not NaN**. Such a row
is an *invalid pose*, **not a neutral/relaxed hand**. Any code that treats it as
a pose is silently wrong.

**Measured contamination `[VERIFIED-EXEC]`** — across all 30 official mini-dataset
HDF5 files (4 218 756 samples):

| | |
|---|---|
| total samples | 4 218 756 |
| **IK-failure (all-zero) samples** | **659 172 = 15.625 %** |
| worst single session | 46.94 % of its samples |
| verified | official `get_ik_failures_mask` reproduces the all-zero-row mask **exactly** on every file |

Per-session rates range from 0.03 % to 46.94 %, so this is **not** negligible and
varies wildly by session.

**Consequences (binding for Sessions 3 & 4):**
- Exclude IK-failure rows from **all** pose statistics, probability models,
  validation, visualisation presets, training and evaluation.
- The official dataloader already does this via `skip_ik_failures=True`.
- If you compute an angular error without masking, it is **inflated**. Measured on
  one session: unmasked MAE 16.09° vs masked MAE 12.48° — a 3.6° artefact purely
  from all-zero rows. `[VERIFIED-EXEC]`

### 4b. Per-joint limits (generic hand model)

`[OFFICIAL-DATA]` — read from `generic_hand_model.json::joint_limits`, rows 0-19.
These are the **generic** hand model's limits used for FK/metric computation;
they are *not* a guarantee about any individual user's anatomy, and **the
baseline does not clamp its predictions to them** (`[VERIFIED-EXEC]`: 1.7% of
predicted joint-time samples fell outside these limits in a real run).

| # | Name | min (rad) | max (rad) | min (°) | max (°) | range (°) |
|---|---|---|---|---|---|---|
| 0 | `THUMB_CMC_FE` | -0.7873 | +1.2873 | -45.11 | +73.75 | 118.86 |
| 1 | `THUMB_CMC_AA` | -0.6118 | +0.6118 | -35.05 | +35.05 | 70.10 |
| 2 | `THUMB_MCP_FE` | 0.0000 | +1.2873 | 0.00 | +73.75 | 73.75 |
| 3 | `THUMB_IP_FE` | -0.2585 | +1.0873 | -14.81 | +62.30 | 77.11 |
| 4 | `INDEX_MCP_AA` | -0.3373 | +0.4873 | -19.32 | +27.92 | 47.24 |
| 5 | `INDEX_MCP_FE` | -0.2873 | +1.3373 | -16.46 | +76.62 | 93.08 |
| 6 | `INDEX_PIP_FE` | 0.0000 | +1.8825 | 0.00 | +107.86 | 107.86 |
| 7 | `INDEX_DIP_FE` | 0.0000 | +1.4337 | 0.00 | +82.14 | 82.14 |
| 8 | `MIDDLE_MCP_AA` | -0.4873 | +0.2873 | -27.92 | +16.46 | 44.38 |
| 9 | `MIDDLE_MCP_FE` | -0.2873 | +1.4373 | -16.46 | +82.35 | 98.81 |
| 10 | `MIDDLE_PIP_FE` | 0.0000 | +1.8825 | 0.00 | +107.86 | 107.86 |
| 11 | `MIDDLE_DIP_FE` | 0.0000 | +1.4337 | 0.00 | +82.14 | 82.14 |
| 12 | `RING_MCP_AA` | -0.2873 | +0.2873 | -16.46 | +16.46 | 32.92 |
| 13 | `RING_MCP_FE` | -0.2873 | +1.5373 | -16.46 | +88.08 | 104.54 |
| 14 | `RING_PIP_FE` | 0.0000 | +1.8825 | 0.00 | +107.86 | 107.86 |
| 15 | `RING_DIP_FE` | 0.0000 | +1.4337 | 0.00 | +82.14 | 82.14 |
| 16 | `PINKY_MCP_AA` | -0.6873 | +0.4873 | -39.38 | +27.92 | 67.30 |
| 17 | `PINKY_MCP_FE` | -0.4873 | +1.6373 | -27.92 | +93.81 | 121.73 |
| 18 | `PINKY_PIP_FE` | 0.0000 | +1.8825 | 0.00 | +107.86 | 107.86 |
| 19 | `PINKY_DIP_FE` | 0.0000 | +1.4337 | 0.00 | +82.14 | 82.14 |

Rows 20 and 21 of the model are the two **wrist** DOF (±45° each, axes +y and
+z). They are **not** part of the emg2pose output. `[OFFICIAL-CODE]`

---

## 5. Inter-joint coupling

**There is no explicit coupling term, constraint, or synergy model.**
`[OFFICIAL-CODE]` `[DERIVED]`

- The 20 outputs are produced as 20 independent channels by a linear layer
  (VEMG2Pose decoder: `nn.Linear(hidden, 40)` split into 20 position + 20
  velocity; NeuroPose: `nn.Linear(32, 20)`). No output-space constraint links
  them.
- `joint_limits` is **never applied** as a clamp anywhere in the baseline
  inference or training code — verified by reading the full pipeline and by the
  observed 1.7% out-of-range rate.

**However, coupling exists implicitly** in two ways that matter:

1. **Autoregressive state conditioning** — in VEMG2Pose, the decoder at each
   step receives the *previous predicted* 20-vector as input. Errors therefore
   couple across joints and can accumulate over time. `[OFFICIAL-CODE]`
2. **Learned statistics** — the model is trained on real hands, so outputs are
   correlated in practice, but nothing *enforces* a consistent (kinematically
   realizable) pose.

**Do not assume the 20 outputs form a valid hand pose.** If you need a valid
pose, run them through `emg2pose.kinematics.forward_kinematics`. `[DERIVED]`

---

## 6. Input contract

| Property | Value | Source |
|---|---|---|
| Modality | surface EMG (sEMG), wrist band | `[OFFICIAL-CODE]` |
| Channels | **16** | `[OFFICIAL-CODE]` `[OFFICIAL-DATA]` (`num_channels` attr = 16; every HDF5 `emg` array is `(T,16)`) |
| Sample rate | **2000 Hz** | `[OFFICIAL-CODE]` `EMG_SAMPLE_RATE = 2000`; `[OFFICIAL-DATA]` `sample_rate` attr = 2000.0 |
| Pre-filtering | band-pass, -3 dB at 20 Hz and 850 Hz before digitisation; dataset stored high-pass filtered at 40 Hz | `[OFFICIAL-CODE]` (paper) |
| Scaling | **rescaled such that the noise floor has std ≈ 1** | `[OFFICIAL-CODE]` (paper) |
| Left-hand handling | sign of left-hand EMG is **flipped** in the released data to account for band polarity | `[OFFICIAL-CODE]` (paper) |
| Normalisation in code | **none** — `RotationAugmentation` (train only) then `ExtractToTensor`; no mean/std normalisation anywhere | `[OFFICIAL-CODE]` `config/transforms/*.yaml` |
| Tensor layout | model takes **(B, C=16, T)**; the HDF5 stores **(T, 16)** | `[OFFICIAL-CODE]` |
| Minimum length | `left_context + 1` = **1791 samples** (0.896 s) | `[VERIFIED-EXEC]` |
| Recommended length | official eval uses 5 s trajectories = `10000 + 1790` = **11790 samples** | `[OFFICIAL-CODE]` `config/experiment/*_vemg2pose.yaml` |

⚠️ **The released dataset's EMG is already filtered and scaled.** If you feed raw
sensor data you must replicate: band-pass filtering and the noise-floor-std-1
scaling, and the left/right polarity convention. `[DERIVED]` — this is an
inference from the documented preprocessing, **not** something we validated by
re-deriving the scaling from raw recordings (we have no raw recordings).

---

## 7. Output contract and temporal alignment

| Property | Value | Source |
|---|---|---|
| Shape | `(T_pose, 20)` where `T_pose = T_in - 1790` | `[VERIFIED-EXEC]` |
| First output sample | corresponds to input index **1790** | `[VERIFIED-EXEC]` `[OFFICIAL-CODE]` |
| Units | radians | `[VERIFIED-EXEC]` §2 |
| Output sample rate | 2000 Hz *nominally* | `[OFFICIAL-CODE]` |
| **Native output resolution** | **50 Hz only** — the 2 kHz output is a linear interpolation | `[OFFICIAL-CODE]` `[VERIFIED-EXEC]` |

### 7.1 The model is causal but NOT streaming

`[OFFICIAL-CODE]`: `TdsNetwork.right_context = 0` → no look-ahead, so the model is
**causal**. But `left_context = 1790` means it needs ~0.9 s of *past* EMG and
must be re-run over a window; there is **no incremental/stateful API** for
streaming. The LSTM hidden state is reset on every `forward()` call
(`SequentialLSTM.reset_state()`), so each call is independent.

`[VERIFIED-EXEC]` throughput on CPU: **8.5× realtime** (0.69 s to process
11 790 samples for a 10 000-sample prediction).

### 7.2 ⚠️ Temporal resolution is much coarser than it appears

`[OFFICIAL-CODE]` `[VERIFIED-EXEC]`: the TDS featurizer downsamples 2 kHz → 50 Hz;
the LSTM decoder rolls out at 50 Hz; predictions are then linearly up-sampled
back to 2 kHz. Verified numerically: for `T_pose = 10000`, the internal rollout
has exactly **250 steps** (ratio 40.0), constant across window sizes.

> **The `(T_pose, 20)` array contains only `T_pose / 40` independent values.**
> Reporting it as "2 kHz joint angle data" is misleading. Treat the effective
> output bandwidth as **50 Hz (20 ms)**.

This is important for any downstream controller or for computing velocities.
`[DERIVED]`

### 7.3 Effective latency / temporal offset

`[DERIVED]` — not directly documented by the authors, so treat as a modelling
caveat rather than a measured constant:

Because the model is trained end-to-end to map a window of EMG to the pose
labelled at the corresponding time, but must *emit* that pose only after
consuming its context, the output at index `i` is best interpreted as the pose at
time `i/2000` s **within the window** — i.e. no explicit offset is introduced by
the API. However the **minimal achievable latency** for an online system is
`left_context / 2000` = **895 ms** of required history, plus compute.

**Action item for a real-time application:** measure the actual
cross-correlation lag between predictions and ground truth on official data
before trusting the alignment. Not yet done. `[UNKNOWN]`

---

## 8. Evaluation window / trajectory

`[OFFICIAL-CODE]`: "We evaluate on 5 second trajectories and report test set mean
absolute joint angular error (°) and mean (Euclidean) landmark distance (mm)."

`[OFFICIAL-CODE]`: official val/test window length is **11790 samples**
(= 10000 = 5 s of predicted span + 1790 left context).

---

## 9. Known limitations to carry forward

1. **Wrist pose is not predicted.** Only 20 finger DOF. A full hand pose needs
   the 2 wrist DOF supplied externally.
2. **AA sign is per-finger** (§3.2) — a common source of silent sign errors.
3. **Output is 50 Hz native**, up-sampled to 2 kHz (§7.2).
4. **No kinematic consistency guarantee** — outputs are 20 independent channels
   and are not clamped to `joint_limits` (§5).
5. **15.6 % of the released joint-angle labels are IK failures encoded as
   all-zero rows** and must be masked (§4a). Never interpret them as a neutral
   hand.
6. **Cross-user generalisation is the hard part, and `split` alone cannot
   measure it.** `[PROJECT CONSTRAINT, from Session 1]` Many users appear in both
   `split=train` and `split=test`, so a plain `split`-based claim of cross-user
   generalisation is invalid. Use the metadata **`generalization`** axis
   (`user`, `stage`, `user_stage`) via `held_out_user` / `held_out_stage`.
   The mini dataset is entirely held-out users (`generalization ∈ {user,
   user_stage}`, `held_out_user: True`), so it exercises the hard axis.
7. **Generic hand model bias.** Landmark metrics use a single generic hand model,
   so FK-based evaluation is biased against users whose anatomy differs.
   `[OFFICIAL-CODE]` (paper acknowledges this).
8. **Positioning/placement sensitivity.** The paper notes both held-out-user
   scenarios involve new device placements, varying across sessions.

---

## 10. Provenance

**Filesystem note `[PROJECT CONSTRAINT, from Session 1]`:** on this Windows
machine, access dataset files through the ASCII junction **`<PROJECT_ROOT>`**
(→ this project). Do **not** call `Path.resolve()` on it — that dereferences the
junction back to the non-ASCII `<USER_PROFILE>\...` path and breaks `h5py`.
`predict_pose.py` deliberately uses `Path(__file__).absolute()`, not `.resolve()`.

| Item | Value |
|---|---|
| Official repo | https://github.com/facebookresearch/emg2pose |
| Cloned commit | `5f6f62b` (Merge PR #2) |
| Checkpoints | `emg2pose_model_checkpoints.tar.gz` (248 072 445 B, sha256 `164e0bcbb52c25b116e77b799d8eb81c59994090608c73de3946c87e34c3db66`); `regression_vemg2pose.ckpt` sha256 `748b1d1ef0ce1985f6fc07225d97eebfb370243429af803b4997d28ecce2424e`. All hashes: `docs/artifact_hashes.json` |
| Mini dataset | `emg2pose_dataset_mini.tar` (647 198 208 B, sha256 `d7400e98508ccbb2139c2d78e552867b23501f637456546fd6680f3fe7fec50d`), 30 HDF5 files, 4 218 756 samples |
| Hand model | `emg2pose/UmeTrack/dataset/generic_hand_model.json` (510 280 B) |
| Env | `<EMG2POSE_VENV>` (ASCII junction) — Python 3.10.13, torch 2.3.1+cpu, pytorch-lightning 2.2.2, hydra-core 1.3.2 (matches official `environment.yml`) |

Verification commands:
```
<EMG2POSE_VENV>\Scripts\python.exe <INFERENCE_ROOT>\verify_joint_conventions.py
<EMG2POSE_VENV>\Scripts\python.exe <INFERENCE_ROOT>\smoke_test_inference.py
<EMG2POSE_VENV>\Scripts\python.exe <INFERENCE_ROOT>\make_joint_reference.py
```
