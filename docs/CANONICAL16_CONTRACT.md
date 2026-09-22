# canonical16 Contract

**Status: FROZEN (v1.0.0)** · Owner: Session 2 (emg2pose side only)
**Applies to:** `emg2pose_handstate/representation/canonical_hand.py`

---

## 0. Scope and the central warning

`canonical16` is the first cross-dataset hand representation: the **16 kinematic
variables we currently intend to match reliably between emg2pose and NinaPro DB9.**

> ### ⚠️ canonical16 does NOT fully describe hand geometry.
>
> `emg2pose 20D → canonical16` **drops four variables by design**: the
> abduction/adduction DOF of the index, middle, ring and pinky MCP joints.
>
> This is a **lossy** projection. A canonical16 vector is **not** a complete hand
> pose, and nothing downstream may describe it as one. Two different emg2pose
> poses that differ only in those four DOF map to the **same** canonical16
> vector — the mapping is genuinely non-injective in that subspace.
>
> This module owns the **emg2pose side only**. `DB9 → canonical16` is **not**
> implemented here; Session 3 owns it.

This module is the single authoritative adapter. Do not re-derive the mapping
anywhere else.

---

## 1. Exact 20D → 16D mapping

Selection is **by official emg2pose joint name**, resolved at runtime against
`emg2pose/constants.py::JOINTS`. **No numeric indices are hard-coded** — they are
resolved by name and then validated (`assert_official_layout()` fails loudly if
the official layout ever moves).

```
canonical16[..., i] = emg2pose20[..., source_index[i]]
```

| canonical idx | canonical variable | source emg2pose joint | source idx | anatomical meaning | unit |
|---|---|---|---|---|---|
| 0 | `thumb_cmc_flexion` | `THUMB_CMC_FE` | 0 | Thumb carpometacarpal flexion/extension | radians |
| 1 | `thumb_cmc_ab_adduction` | `THUMB_CMC_AA` | 1 | Thumb carpometacarpal abduction/adduction | radians |
| 2 | `thumb_mcp_flexion` | `THUMB_MCP_FE` | 2 | Thumb metacarpophalangeal flexion/extension | radians |
| 3 | `thumb_ip_flexion` | `THUMB_IP_FE` | 3 | Thumb interphalangeal flexion/extension | radians |
| 4 | `index_mcp_flexion` | `INDEX_MCP_FE` | 5 | Index MCP flexion/extension | radians |
| 5 | `index_pip_flexion` | `INDEX_PIP_FE` | 6 | Index proximal interphalangeal F/E | radians |
| 6 | `index_dip_flexion` | `INDEX_DIP_FE` | 7 | Index distal interphalangeal F/E | radians |
| 7 | `middle_mcp_flexion` | `MIDDLE_MCP_FE` | 9 | Middle MCP flexion/extension | radians |
| 8 | `middle_pip_flexion` | `MIDDLE_PIP_FE` | 10 | Middle proximal interphalangeal F/E | radians |
| 9 | `middle_dip_flexion` | `MIDDLE_DIP_FE` | 11 | Middle distal interphalangeal F/E | radians |
| 10 | `ring_mcp_flexion` | `RING_MCP_FE` | 13 | Ring MCP flexion/extension | radians |
| 11 | `ring_pip_flexion` | `RING_PIP_FE` | 14 | Ring proximal interphalangeal F/E | radians |
| 12 | `ring_dip_flexion` | `RING_DIP_FE` | 15 | Ring distal interphalangeal F/E | radians |
| 13 | `pinky_mcp_flexion` | `PINKY_MCP_FE` | 17 | Pinky MCP flexion/extension | radians |
| 14 | `pinky_pip_flexion` | `PINKY_PIP_FE` | 18 | Pinky proximal interphalangeal F/E | radians |
| 15 | `pinky_dip_flexion` | `PINKY_DIP_FE` | 19 | Pinky distal interphalangeal F/E | radians |

Resolved source-index vector (runtime-validated):

```
[0, 1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15, 17, 18, 19]
```

### Dropped by design (4 variables)

| source emg2pose joint | source idx | why dropped |
|---|---|---|
| `INDEX_MCP_AA` | 4 | non-thumb MCP ab/adduction — not currently matchable against DB9 |
| `MIDDLE_MCP_AA` | 8 | " |
| `RING_MCP_AA` | 12 | " |
| `PINKY_MCP_AA` | 16 | " |

Retained + dropped = all 20 official dimensions, disjointly (test-enforced).

Note the only **ab/adduction** variable retained is the **thumb's** `THUMB_CMC_AA`.
All 15 other retained variables are flexion/extension.

---

## 2. Canonical ordering

```
 0 thumb_cmc_flexion         8 middle_pip_flexion
 1 thumb_cmc_ab_adduction    9 middle_dip_flexion
 2 thumb_mcp_flexion        10 ring_mcp_flexion
 3 thumb_ip_flexion         11 ring_pip_flexion
 4 index_mcp_flexion        12 ring_dip_flexion
 5 index_pip_flexion        13 pinky_mcp_flexion
 6 index_dip_flexion        14 pinky_pip_flexion
 7 middle_mcp_flexion       15 pinky_dip_flexion
```

Block structure: **thumb (4)**, then index / middle / ring / pinky at **3 each**,
each block ordered proximal → distal MCP, PIP, DIP.

This ordering is defined by the tuple `CANONICAL16_SOURCE_JOINTS` in
`canonical_hand.py`. Changing it is a breaking schema change.

---

## 3. Unit and sign conventions

- **Unit: radians**, unchanged from the official emg2pose representation. No
  degree conversion anywhere. `[VERIFIED-EXEC]` — see
  `docs/joint_angle_definition.md` §2.
- **Flexion/extension (15 of the 16 canonical variables): positive = flexion,
  negative = extension.** `[VERIFIED-EXEC]` by forward kinematics (15/15 FE
  joints move the fingertip toward the palm centre at their `+limit`).
- **`thumb_cmc_ab_adduction` (canonical idx 1) has NO globally meaningful sign
  rule.** The emg2pose ab/adduction polarity is per-finger; the thumb's positive
  direction is opposite to the four non-thumb MCP AA joints. Only the thumb's AA
  variable is retained here, so this affects exactly one canonical dimension.
  `[VERIFIED-EXEC]` — see `docs/joint_angle_definition.md` §3.2.
  **A DB9-side mapping must handle this dimension explicitly and must not assume
  "positive = abduction".**
- The four dropped MCP AA variables are the ones whose per-finger sign ambiguity
  would have been most awkward — dropping them removes that hazard, which is a
  deliberate secondary benefit of the canonical16 choice.

### What the adapter does NOT do to values

Explicitly and by contract: **no** clipping, **no** anatomy projection, **no**
normalisation, **no** scaling, **no** smoothing, **no** interpolation, **no**
sign correction, **no** reordering beyond the name-based selection above. Values
pass through bit-identically (test-enforced).

Official `joint_limits` exist in `generic_hand_model.json` but **the emg2pose
baselines never clamp to them**, and neither does this adapter. Consumers that
want a clamped/valid pose must do so explicitly and document it.

---

## 4. IK-failure behaviour

Official emg2pose encodes an **IK failure as an all-zero `joint_angles` row**
(not NaN). Helper: `emg2pose.utils.get_ik_failures_mask`. **Such a row is an
invalid pose, not a neutral/relaxed hand.**

The adapter **preserves these semantics** and never launders an invalid frame
into a legitimate-looking canonical16 posture:

- `validity_mask(x)` → `(...)` bool, `True` where the frame is a **valid** pose.
- `to_canonical16(x, return_validity=True)` → `(canonical16, valid)`.
- `extract(x)` → `Canonical16(values, valid)` with `.n_invalid`.
- Invalid frames' **values are returned verbatim** (as 16 zeros) but are
  **flagged invalid**. Consumers MUST filter on the mask before computing any
  pose statistic, training signal, probability model, or visualisation.
- `DB9 → canonical16` (Session 3) must expose its own validity mask on the same
  contract; the two masks compose by logical AND when data is paired.

### Measured caveat: flagged frames are not always *bit*-exact zeros

`[VERIFIED-EXEC]` — on the official mini dataset, of 109 439 flagged frames in
`...recording-13_right.hdf5`, **109 437 were bit-exact zeros and 2 carried
float-epsilon noise** (`max |value| = 1.11e-16`, ≈2 ULP). The official mask uses
`np.isclose(v, 0)` and therefore correctly classifies these as failures — they
are numerically zero. The adapter uses an absolute tolerance of `1e-8` by
default (tighter than the official relative tolerance) and agrees with the
official helper on **100 % of 4 218 756 samples across all 30 files**.

Contamination measured on the official mini dataset: **659 172 / 4 218 756 =
15.625 %** of frames are IK failures (per-session range 0.03 %–46.94 %).
Unfiltered pose statistics are therefore meaningless.

---

## 5. API

```python
import sys; sys.path.insert(0, r"<REPRESENTATION_ROOT>")
import canonical_hand as ch

# simple: (..., 20) -> (..., 16), radians, raw values
canon = ch.to_canonical16(emg2pose_angles)

# with the IK-failure mask
canon, valid = ch.to_canonical16(emg2pose_angles, return_validity=True)

# or as a record
res = ch.extract(emg2pose_angles)      # res.values (...,16), res.valid (...), res.n_invalid

# inverse (partial; dropped dims -> NaN by default so they cannot look real)
back20 = ch.from_canonical16(canon)

# introspection
ch.canonical16_names()                 # 16 canonical names, canonical order
ch.canonical16_source_joint_names()    # 16 official emg2pose joint names
ch.assert_official_layout()            # raises if the official layout moved
ch.build_schema()                      # full schema dict
```

| Function | Contract |
|---|---|
| `to_canonical16(x, *, return_validity=False, repo_root=None, atol=1e-8)` | `(...,20)`→`(...,16)`; rejects wrong final dim with `ValueError`; numpy array, torch tensor or array-like |
| `validity_mask(x, *, atol=1e-8)` | `(...,20)`→`(...)` bool; matches official helper |
| `extract(x)` | → `Canonical16(values, valid)` |
| `from_canonical16(x, *, fill_dropped=nan)` | `(...,16)`→`(...,20)`; dropped slots filled with `fill_dropped` |
| `resolve_source_indices()` | 16-tuple of official indices, resolved by name |
| `resolve_dropped_indices()` | 4-tuple of official indices |
| `assert_official_layout()` | raises `CanonicalMappingError` on any drift |
| `build_schema()` / `write_schema(path)` | authoritative schema dict / JSON |

Inputs may be numpy arrays or torch tensors; **output is always numpy**.
Arbitrary leading dimensions are supported (`(T,20)`, `(B,T,20)`, …).

---

## 6. Tests

```powershell
<EMG2POSE_VENV>\Scripts\python.exe -m pytest <REPRESENTATION_ROOT>\tests -v
<EMG2POSE_VENV>\Scripts\python.exe <REPRESENTATION_ROOT>\verify_canonical16_on_real_data.py
```

Coverage (37 tests, all passing):

| Area | What is enforced |
|---|---|
| Official layout resolution | resolved indices equal those read from `constants.py` by name; `Joint.index` agrees with list position |
| **Ordering fingerprint** | the exact tuple `[0,1,2,3,5,6,7,9,10,11,13,14,15,17,18,19]` is pinned; any reorder fails |
| **Unique-value extraction** | a 20-vector with a unique value per official dimension is checked slot-by-slot against the official name→index map, so a swap anywhere cannot pass |
| Not-a-prefix guard | asserts `to_canonical16(v) != v[:16]`, i.e. selection is genuinely name-based, not positional |
| Value preservation | bit-exact equality incl. values far outside anatomical limits, ±1e12, dtype preserved |
| No clipping | out-of-range inputs pass through unchanged |
| Dimension rejection | `(19,) (21,) (16,) (0,) (2,19) (2,21)` and scalars all raise |
| IK failure | all-zero → invalid; float-epsilon (2 ULP) → invalid; tiny-but-real → valid; mask shape for batched input; mask agrees with official `get_ik_failures_mask`; masked extraction does not shift values |
| Round trip | kept columns restored exactly; dropped columns NaN by default; zero-fill only opt-in |
| torch | torch tensor in → numpy out, correct values |
| Schema | schema matches resolved indices; on-disk `canonical16_schema.json` is not stale; canonical18 is reserved and `to_canonical18` does **not** exist |

---

## 7. Real-data verification

`[VERIFIED-EXEC]` — `representation/verify_canonical16_on_real_data.py`, entire
official mini dataset (30 sessions, 4 218 756 samples):

| Check | Result |
|---|---|
| shape contract `(T,20) → (T,16)` | PASS, all 30 files |
| retained values bit-identical to official source columns | **PASS** |
| validity mask == official `get_ik_failures_mask` | **PASS**, 30/30 files, 4 218 756/4 218 756 samples |
| canonical16 is not a positional prefix | **PASS** (name-based selection confirmed on real data) |
| round trip restores kept cols / NaNs dropped cols | **PASS** |
| IK-failure rate | 659 172 frames = **15.625 %**, all numerically zero |

Evidence: `docs/canonical16_real_data_evidence.json`,
`docs/canonical16_real_data_verification.txt`.

---

## 8. Reserved: canonical18 (DISABLED)

`canonical18` would append two variables:

| canonical idx | reserved variable | status |
|---|---|---|
| 16 | `middle_ring_spread` | `RESERVED_DISABLED` |
| 17 | `ring_pinky_spread` | `RESERVED_DISABLED` |

**No spread formula is defined or implemented anywhere in this repository.**
`to_canonical18` does not exist, and a test asserts that it does not, so it
cannot be enabled by accident.

Enabling canonical18 requires, per the research lead's instruction:

1. the DB9 ↔ emg2pose spread mapping to be **independently validated**;
2. an explicit research decision to unfreeze — not an engineering choice;
3. the spread definition (which landmarks/joints, which axis, what sign) to be
   specified from official sources, not invented.

Until then, any code needing a 17th/18th variable must fail rather than guess.

---

## 9. Provenance

| Item | Value |
|---|---|
| Adapter | `emg2pose_handstate/representation/canonical_hand.py` |
| Schema | `emg2pose_handstate/representation/canonical16_schema.json` (generated; stale-checked by a test) |
| Tests | `emg2pose_handstate/representation/tests/test_canonical_hand.py` |
| Real-data verifier | `emg2pose_handstate/representation/verify_canonical16_on_real_data.py` |
| Ordering authority | `emg2pose/constants.py::JOINTS` @ commit `5f6f62b` |
| Underlying joint semantics | `docs/joint_angle_definition.md` (Session 2) |
| Machine-readable joint reference | `docs/joint_reference_table.json` |
