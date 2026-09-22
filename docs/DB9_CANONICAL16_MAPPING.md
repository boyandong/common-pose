# DB9 → canonical16 mapping

**Session 3 deliverable.** Owner: Session 3 (DB9 side).
The emg2pose side is frozen by Session 2 in
`representation/canonical_hand.py`, `representation/canonical16_schema.json`,
`docs/CANONICAL16_CONTRACT.md`, and is **not** re-derived or reinterpreted here.

Machine-readable counterparts:

| artifact | contents |
|---|---|
| `representation/db9_to_canonical16.py` | the adapter (single source of truth) |
| `representation/db9_canonical16_schema.json` | generated schema; matches the module |
| `representation/tests/test_db9_to_canonical16.py` | 18 tests, all passing |
| `docs/DB9_FILE_AUDIT.json` | PHASE 0 real-file audit (44 files) |
| `docs/DB9_EMG2POSE_ZERO_COMPATIBILITY.json` | PHASE 1B zero/axis check |

Evidence tags used below: `[REAL-FILE]` measured from the official archives,
`[OFFICIAL-DOC]` stated in the DB9 page or paper, `[GEOMETRY]` derived from the
official UmeTrack model by forward kinematics.

> **Provenance status of the one non-trivial transformation.** DB9's
> `thumb_cmc_ab_adduction` is sign-flipped into the emg2pose-oriented frame. The
> **sign** correspondence is frozen on geometric and documented-anatomical
> evidence (§4.2). It is **not** claimed that DB9's `CMC1_A` and UmeTrack's
> `THUMB_CMC_AA` are proven to be identical rotation axes in magnitude or
> geometry — they are not, and that residual uncertainty is precisely why
> `canonical15_noThumbAA` exists as a pre-registered robustness control. This is
> the single internally consistent statement of that provenance; nothing else in
> this repository asserts otherwise.

---

## 1. Source files and what is actually in them

`[REAL-FILE]` PHASE 0 audited **44 `.mat` files across 22 archive slots**
(subjects 1–16 from DB1, 68–73 from DB5), 6 504 215 samples total.

| property | value |
|---|---|
| MATLAB variables present | `subject, exercise, glove, angles, inclin?, restimulus, rerepetition, repetition, stimulus, order_of_angles` |
| `angles` shape | `(N, 22)`, dtype `float64` |
| `order_of_angles` | **present in every file, identical in all 44** |
| `stimulus` / `repetition` | present, but 7 samples longer than `angles` in exercise-C files |
| `inclin` | **absent in every file** (no inclinometer in DB1/DB5-derived archives) |
| NaN columns | exactly one, `6:MCP2_a`, in every file |
| repetitions per movement | **6**, counted from `rerepetition` (never assumed from the docs) |
| rest fraction | 60.87 % of samples carry `restimulus == 0` |
| hand side | **no side field exists.** The protocol instructed all participants to perform the movements with the **right hand**; the DB9 page's "Handedness" column is the participant's own handedness, not the recording side `[OFFICIAL-DOC]` |

### 1.1 The official 22-channel vocabulary `[REAL-FILE]`

Read verbatim from `order_of_angles`:

```
 1:CMC1_f   2:CMC1_a   3:MCP1    4:IP1     5:MCP2_f  6:MCP2_a  7:PIP2
 8:MCP3_f   9:PIP3    10:MCP4_f 11:MCP4_a 12:PIP4   13:CMC5   14:MCP5_f
15:MCP5_a  16:PIP5    17:DIP2   18:DIP3   19:DIP4   20:DIP5   21:WRIST_F
22:WRIST_A
```

This ordering is **not** "5 fingers × 4 joints". It runs thumb → the finger
flexion chains interleaved with their abduction sensors → all four DIP sensors
together → wrist. Consecutive index is a different joint every time.

### 1.2 Subject identity — a real conflict, resolved explicitly

`[REAL-FILE]` Each source database restarted its own subject numbering from 1, so
a DB5-derived file in archive slot 68 records `subject = 1`. Using that field as
the identity would **silently merge six DB5 participants with six DB1
participants**, turning a cross-subject experiment into a partly within-subject
one.

**Authority: the DB9 archive slot.** The official DB9 table lists one row per
slot, and all 22 slots in this corpus are distinct, so the slots are 22 distinct
participants. The in-file `subject` field is recorded for audit only. A further
official-release defect is on record: `[REAL-FILE]` slot 69 records
`subject = 11` where the source database's own numbering predicts 2. It is
reported, not "fixed", and the slot remains unambiguous.

---

## 2. The exact mapping

Selection is **by channel name**, never by position, and is proven not to be a
positional prefix by a test.

| canonical idx | canonical16 variable | DB9 channel | DB9 col | DB9 anatomical name | emg2pose idx |
|---|---|---|---|---|---|
| 0 | `thumb_cmc_flexion` | `CMC1_f` | 0 | `CMC1_F` | 0 |
| 1 | `thumb_cmc_ab_adduction` | `CMC1_a` | 1 | `CMC1_A` | 1 |
| 2 | `thumb_mcp_flexion` | `MCP1` | 2 | `MCP1_F` | 2 |
| 3 | `thumb_ip_flexion` | `IP1` | 3 | `IP1_F` | 3 |
| 4 | `index_mcp_flexion` | `MCP2_f` | 4 | `MCP2_F` | 5 |
| 5 | `index_pip_flexion` | `PIP2` | 6 | `PIP2_F` | 6 |
| 6 | `index_dip_flexion` | `DIP2` | **16** | `DIP2_F` | 7 |
| 7 | `middle_mcp_flexion` | `MCP3_f` | 7 | `MCP3_F` | 9 |
| 8 | `middle_pip_flexion` | `PIP3` | 8 | `PIP3_F` | 10 |
| 9 | `middle_dip_flexion` | `DIP3` | **17** | `DIP3_F` | 11 |
| 10 | `ring_mcp_flexion` | `MCP4_f` | 9 | `MCP4_F` | 13 |
| 11 | `ring_pip_flexion` | `PIP4` | 11 | `PIP4_F` | 14 |
| 12 | `ring_dip_flexion` | `DIP4` | **18** | `DIP4_F` | 15 |
| 13 | `pinky_mcp_flexion` | `MCP5_f` | 13 | `MCP5_F` | 17 |
| 14 | `pinky_pip_flexion` | `PIP5` | 15 | `PIP5_F` | 18 |
| 15 | `pinky_dip_flexion` | `DIP5` | **19** | `DIP5_F` | 19 |

Resolved DB9 column vector:

```
[0, 1, 2, 3, 4, 6, 16, 7, 8, 17, 9, 11, 18, 13, 15, 19]
```

An emg2pose-20 index vector cannot be reused here: the two datasets index the
same anatomy differently (`index_dip_flexion` is emg2pose #7 but DB9 column 16).

### 2.1 DB9 channels not used, and why

| DB9 channel | col | status |
|---|---|---|
| `MCP2_a` | 5 | **all-NaN in every file.** `[OFFICIAL-DOC]` "Sensor 11 (which corresponds to MCP2-3_A) was not included into the calibrated data due to noise problems." Not a canonical16 input, so it does not invalidate frames. |
| `MCP4_a` | 10 | index-MCP abduction of ring/middle web — the DOF canonical16 drops |
| `MCP5_a` | 14 | dropped with the other non-thumb MCP ab/adduction DOF |
| `CMC5` | 12 | pinky CMC (palmar arch side) — no emg2pose counterpart |
| `WRIST_F` | 20 | wrist flexion/extension — emg2pose does not regress the wrist |
| `WRIST_A` | 21 | wrist deviation — same |

---

## 3. Units, signs, and the zero reference

### 3.1 Units: DB9 publishes degrees `[REAL-FILE]`

canonical16 is **radians**; DB9 `angles` are **degrees**. The conversion is
explicit and named in the adapter (`DEGREES_PER_RADIAN`), never implicit.

Evidence chain:
1. `[REAL-FILE]` measured global range across the corpus is **−322 … +173**.
   Interpreted as radians this would be ~50 full turns — physically impossible.
2. `[OFFICIAL-DOC]` Atzori et al. 2014 describe the CyberGlove as returning
   values "for an average resolution of less than one degree".
3. `[OFFICIAL-DOC]` the DB9 paper quotes calibration precision "below 5 degrees".

The DB9 paper never writes the unit symbol next to the numbers, so this is
recorded as **inferred with converging evidence**, not as a verbatim quotation.

### 3.2 Signs — the DB9 paper's own Table 6 `[OFFICIAL-DOC]`

The paper's Table 6 ("Sign criteria considered") states:

| DB9 variable | criterion |
|---|---|
| `DIP(2-5)_F`, `PIP(2-5)_F`, `IP1_F`, `MCP(1-5)_F` | **Flexion + / Extension −** |
| `WRIST_F` | Flexion + / Extension − |
| `WRIST_D` | Radial deviation + / Cubital deviation − |
| `MCP(2-3, 3-4, 4-5)_A` | Fingers separated + / Fingers together − |
| `P_Arch (CMC5_F)` | Flexion + / Extension − |
| `CMC1_F` | Flexion + / Extension − |
| **`CMC1_A`** | **Abduction + / Adduction −** |

So DB9's **15 flexion variables already agree in sign** with canonical16's
"positive = flexion" convention. No flip is applied to them, and a test asserts
that no sign correction happens anywhere in the adapter.

### 3.3 Zero reference `[OFFICIAL-DOC]` + `[REAL-FILE]`

> "In order to do this, the sensor signals were transformed according to the
> outputs relative to a reference posture. The reference posture was chosen as
> the central part of movement 11 in exercise B, corresponding to **the hand
> resting on the table with the fingers closed together and extended**."
> — Jarque-Bou et al. 2020, calibration section

**Independent data-side confirmation `[REAL-FILE]`.** Averaging `|canonical16|`
over the central third of every repetition, the exercise-B movement closest to
all-zero is `Wrist supination (axis: little finger)` at **0.059 rad**, while the
fist sits at **1.183 rad**. The wrist-rotation movements have essentially no
finger-flexion content, so their central thirds sit at the finger zero — which
is exactly what a "fingers extended, zero flexion" reference predicts. The
documented reference and the data agree.

---

## 4. PHASE 1B — cross-dataset zero / axis compatibility

Full evidence: `docs/DB9_EMG2POSE_ZERO_COMPATIBILITY.json`. Everything is
derived from geometry; **no offset was ever tuned against classification
accuracy**.

### 4.1 The 15 flexion DOF share a compatible zero `[GEOMETRY]`

Forward kinematics of the official UmeTrack model at **all-zero joint angles**:

| finger | proximal chain angle | distal chain angle |
|---|---|---|
| index | 179.10° | 168.44° |
| middle | 179.45° | 166.68° |
| ring | 179.28° | 172.82° |
| pinky | 174.85° | 171.36° |

(180° = perfectly straight.) The emg2pose zero pose is an **extended** hand.
Measuring inter-fingertip spacing from the most-closed to the most-spread pose
reachable with the official ab/adduction limits, the zero pose sits **1 %** of
the way along that range.

> **Verdict: the emg2pose zero pose is "fingers extended and together", i.e. the
> same configuration DB9's calibration calls zero. No offset is required for the
> 15 flexion variables.**

One caveat is worth recording: this check had to discover the per-finger
ab/adduction polarity first, because driving all four MCP AA DOF to the *same*
sign does **not** produce a spread hand. `[GEOMETRY]` the sign that opens the
finger is positive for the index and negative for middle, ring and pinky —
confirming the frozen contract's warning that the polarity is per-finger.

### 4.2 `thumb_cmc_ab_adduction` — FROZEN: DB9 is sign-flipped

**Decision (research lead, from geometry and documented anatomy):** DB9's
`CMC1_A` is negated when converting into the emg2pose-oriented canonical16 frame.
Applied in `representation/db9_to_canonical16.py` only —
`FROZEN_DB9_SIGN = {"thumb_cmc_ab_adduction": -1.0}`. **Session 2's emg2pose
adapter is not modified.**

Evidence — forward kinematics of the official UmeTrack model swept over
`THUMB_CMC_AA`'s full official limit range `[-0.6118, +0.6118]` rad
(`tools/thumb_web_sign_test.py`;
`data/db9_posture16/thumb_web_sign_evidence.json`;
`figures/posture16/thumb_web_sign_test.png`):

| `THUMB_CMC_AA` | first web angle | thumb↔index tip | out-of-plane elevation |
|---|---|---|---|
| −0.6118 | 69.38° | 153.90 | **+45.70°** |
| 0.0000 | 52.02° | 114.83 | +32.45° |
| +0.6118 | 50.42° | 93.57 | **+8.94°** |

Positive emg2pose `CMC_AA` **both closes the first web space and brings the thumb
down toward the palm plane**. Both readings — the in-plane separation criterion
and the out-of-plane "away from the palm" criterion — therefore agree that
positive is **adduction**. DB9 documents `CMC1_A` as abduction-positive, so the
two are opposite and DB9 must be negated.

> **Correction to an earlier statement in this document.** The first version of
> this check probed only ±0.3 rad and reported the thumb moving *dorsally* under
> positive `CMC_AA`, then reasoned that the two criteria disagreed. That used the
> *displacement vector's* palm-normal component, which is not the elevation
> angle; elevation is non-monotonic over the range and peaks near −0.44 rad. The
> full-range sweep above supersedes it, and the criteria agree.

**Zero alignment for this dimension — verified separately, as required**
(`tools/thumb_zero_alignment.py`, `data/db9_posture16/thumb_zero_alignment.json`).
At the anchor the paper names — the central third of exercise-B movement 11:

| channel | value at anchor | between-movement spread | ratio |
|---|---|---|---|
| `thumb_cmc_ab_adduction` | **−0.23°** | 28.33° | **0.008** |
| `index_pip_flexion` (control) | −0.30° | 137.29° | 0.002 |
| `middle_mcp_flexion` (control) | −0.21° | 128.92° | 0.002 |
| `pinky_pip_flexion` (control) | −0.16° | 92.62° | 0.002 |

The anchor is confirmed to be the extended reference posture by the controls
(three pure flexion joints all ≈ 0), and the thumb channel is ≈ 0 there too.
emg2pose's `THUMB_CMC_AA` is 0 at its rest pose by construction, and that rest
pose was independently verified to be an extended, fingers-together hand (§4.1).

> **Both datasets place this variable's zero at the same physical
> configuration, so the correction is a PURE SIGN FLIP with no offset.**

**Documented negative result.** The first probe tried here was `restimulus == 0`,
assuming the protocol's post-repetition rest intervals are the reference posture.
That is **wrong**, and the control channels prove it: at `restimulus == 0`,
index PIP sits at **+52.63°** and middle MCP at **+44.35°**, which a
fingers-extended hand cannot be. `restimulus` is the *a-posteriori refined*
label, which marks as 0 everything not confidently inside a movement and so
mixes true rest with the reach-in and return transitions. Recorded so the invalid
probe is not reused.

**Caveat carried alongside the decision** (does not change the sign): emg2pose's
`THUMB_CMC_AA` is not the dominant in-plane web channel. `THUMB_CMC_FE` moves the
in-plane web angle about **3× more strongly per radian** (`resolve_thumb_axis.py`;
`data/db9_posture16/thumb_axis_resolution.json`). The flip corrects a *sign* on a
channel whose *magnitude* semantics only approximately match DB9's `CMC1_A`, and
the naive `CMC_FE↔CMC1_F`, `CMC_AA↔CMC1_A` pairing is therefore approximate at
the DOF level, not merely at the sign level.

---

## 5. What the adapter does not do

Mirroring the frozen emg2pose contract, and test-enforced:

* no clipping
* no per-subject centring
* no offset correction
* no sign change **other than the one frozen, pre-registered flip** of
  `thumb_cmc_ab_adduction` recorded in `FROZEN_DB9_SIGN` (§4.2). Every other
  variable keeps its DB9 polarity, which agrees with emg2pose's for the 15
  flexion variables.
* no normalisation or scaling
* no smoothing or interpolation
* no reordering beyond name-based selection

The only transformations are (a) name-based column selection, (b) degrees →
radians, and (c) that single frozen sign flip. Everything else passes through
unchanged, including values far outside any anatomical range.

### Validity contract

`db9_validity_mask(x)` returns `True` where every canonical16 source channel is
finite. The officially dead `MCP2_a` channel is not such a channel, so it never
invalidates a frame — which is precisely why it must not be fed in by position.
This mask composes with the emg2pose IK-failure mask by logical AND, as the
frozen contract requires.

---

## 6. The control representation

`canonical12_noDIP` = canonical16 minus the four DIP variables
(`index/middle/ring/pinky_dip_flexion`), DB9 columns
`[0, 1, 2, 3, 4, 6, 7, 8, 9, 11, 13, 15]`.

It exists because DB9 warns that DIP sensors "provide reliable angles when
subject hand size is big … may provide partial results when the hand of the
subject is small". It is a **pre-registered robustness control**, not a search
over representations.

---

## 7. Reproducing the evidence

```bash
cd emg2pose_handstate/posture_decoder

python -X utf8 tools/audit_db9_files.py \
       --extracted ../data/ninapro_db9/extracted --out ../docs/DB9_FILE_AUDIT.json

python -X utf8 tools/check_zero_pose_compatibility.py \
       --out ../docs/DB9_EMG2POSE_ZERO_COMPATIBILITY.json \
       --extracted ../data/ninapro_db9/extracted

python -X utf8 -c "import sys; sys.path.insert(0,'../representation'); \
import db9_to_canonical16 as m; m.write_schema('../representation/db9_canonical16_schema.json')"

cd .. && python -X utf8 -m pytest representation/tests/test_db9_to_canonical16.py -v
```
