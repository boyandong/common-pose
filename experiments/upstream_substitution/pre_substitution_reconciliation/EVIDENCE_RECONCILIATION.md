# EVIDENCE RECONCILIATION — TRUSTED_DB9_POSE_v1 ↔ emg2pose GT

**Phase:** PRE-SUBSTITUTION EVIDENCE RECONCILIATION
**Frozen representation:** `TRUSTED_DB9_POSE_v1`
**Frozen subset SHA-256:** `e51dde6e63941fd080c84f3896a98cf50fba9e17d5f9cebe909253d5465782d1`
(verified byte-identical by `build_reconciliation.py` during this round)
**Method:** reconciliation of already-published artifacts. No model trained, no forensic re-run,
no trusted channel re-selected, no downstream head called, no label or probability inspected,
no mapping parameter fitted.
**Decision:** `CONDITIONAL_GO` — see §13.

---

## 1. What this document does and does not do

It answers one question:

> For each of the 8 frozen DB9 trusted DOFs, what does the **existing** evidence establish about
> whether the corresponding emg2pose GT DOF is the *same physical variable under a defensible
> Common Pose interpretation*?

It explicitly does **not** re-open:

* whether the 8 DB9 channels are physically valid **inside DB9** — that is CLOSED
  (`FINAL_VALIDATION.md`, 77/77, 0 of 8 KEEP changed);
* whether the subset should contain different channels — FROZEN;
* whether the mapping should be re-derived — the index vector is verified bit-exact.

The distinction that organises the whole document:

| | question | status |
|---|---|---|
| **A** | Is each DB9 channel the named physical quantity, measured on DB9's own anchors? | **CLOSED** (column A) |
| **B** | Is the corresponding emg2pose DOF the same physical variable at the same physical scale? | **THIS DOCUMENT** (column B) |

Column A being closed does **not** transfer to column B. A channel can be a flawless measurement
of "index MCP flexion, in DB9's calibration" and still not be numerically interchangeable with
"index MCP flexion, in emg2pose's calibration".

---

## 2. Evidence sources, with content hashes

Every number in `artifacts/TRUSTED8_EVIDENCE_MATRIX.json` is copied programmatically from these
files by `build_reconciliation.py`; none is hand-transcribed.

| role | path | SHA-256 |
|---|---|---|
| frozen subset (the artifact under review) | `audits/db9/trusted_pose/TRUSTED_DB9_POSE_v1.json` | `e51dde6e…5782d1` |
| 77-participant revalidation | `audits/db9/channel_forensic/FINAL_VALIDATION.md` | `4fa700dc…9fd2b81` |
| per-channel, per-source verdicts | `audits/db9/channel_forensic/artifacts/FINAL_VALIDATION.json` | `cd54572a…fc8abe4` |
| cross-dataset coordinate audit | `audits/db9/coordinate_audit/POSE_COORDINATE_AUDIT_REPORT.md` | `a46afe77…0ee86c` |
| its frozen plan | `audits/db9/coordinate_audit/POSE_COORDINATE_AUDIT_PLAN.json` | `5dc3e42d…c114753` |
| audit API verdict | `…/artifacts/COMMON_POSE_API_VERDICT.json` | `5f132440…7501e14` |
| per-dimension criteria A–J | `…/artifacts/SOURCE_DEFINITION_AUDIT.json` | `f99d249d…5a7319f7` |
| per-dimension confidence class | `…/artifacts/DIMENSION_CONFIDENCE_CLASSIFICATION.json` | `68a293c9…7fd547788` |
| DB9↔emg2pose zero/axis geometry | `docs/DB9_EMG2POSE_ZERO_COMPATIBILITY.json` | `53e48fae…137f769` |
| emg2pose real-data verification | `docs/canonical_emg2pose_verification.json` | `c80c0871…d1a667cc` |
| canonical16 DB9 mapping | `docs/DB9_CANONICAL16_MAPPING.md` | `20ccedae…42abdf5` |
| frozen canonical16 contract | `docs/CANONICAL16_CONTRACT.md` | `68c2d007…638f17` |
| current capability registry | `src/common_pose/api/dof.py` | `05c043aa…9680e3` |
| public evidence ledger | `docs/research_status.md` | `b0b1c6e4…bd61c4b7` |
| public trusted-subset record | `docs/db9_trusted_subset.md` | `01ecc86f…ee99a4` |

Two further evidence files live outside this repository (the pre-git emg2pose lane) and were read
read-only:

| path | SHA-256 | why |
|---|---|---|
| `emg2pose_handstate/docs/joint_convention_verification.txt` | `ed2c6513…1ad30d0` | the per-joint FK sign test |
| `emg2pose_handstate/baseline/emg2pose/emg2pose/UmeTrack/dataset/generic_hand_model.json` | `96649ddf…ce07564` | official joint limits + rotation axes |

The hand-model hash **matches the reference recorded in `docs/DB9_EMG2POSE_ZERO_COMPATIBILITY.json`**,
so the geometric evidence chain runs against the exact same model bytes as the original check.

### 2.1 A provenance discrepancy that was checked and resolved in favour of the evidence

`POSE_COORDINATE_AUDIT_PLAN.json` pins content hashes for the docs it read. Two of them do not
match the current `common-pose/docs/` files:

| doc | audit pin | `common-pose/docs` now | audit-era copy |
|---|---|---|---|
| `docs/joint_angle_definition.md` | `87e9f922…a03befe` | `eb8b17b2…91abc38` | `emg2pose_handstate/docs/joint_angle_definition.md` = **`87e9f922…a03befe`** ✔ |
| `docs/CANONICAL16_CONTRACT.md` | `14f6d46d…3197e6bf` | `68c2d007…6638f17` | `emg2pose_handstate/docs/CANONICAL16_CONTRACT.md` = **`14f6d46d…3197e6bf`** ✔ |
| `docs/DB9_CANONICAL16_MAPPING.md` | `20ccedae…42abdf5` | `20ccedae…42abdf5` ✔ | — |

The audit-era copies were located and **hash-matched**, then diffed against the current ones.
The complete drift is **8 changed lines**, all of them path placeholders in the environment /
reproducibility sections (`C:\emg2pose` → `<PROJECT_ROOT>`, `C:\emg2pose-venv` → `<EMG2POSE_VENV>`,
and the equivalent in the Python `sys.path` example). **No substantive line moved** — not units,
not signs, not zero semantics, not limits, not joint conventions.

> Conclusion: the coordinate audit's pinned semantic contract is **intact**. Every claim this
> reconciliation draws from it remains anchored to content it actually read.

---

## 3. The trusted-8, mapped

| # | canonical DOF | DB9 channel | DB9 `order_of_angles` idx | emg2pose joint | official constants.py idx | canonical16 idx |
|---|---|---|---|---|---|---|
| 1 | `thumb_mcp_flexion` | `MCP1` | 2 | `THUMB_MCP_FE` | 2 | 2 |
| 2 | `thumb_ip_flexion` | `IP1` | 3 | `THUMB_IP_FE` | 3 | 3 |
| 3 | `index_mcp_flexion` | `MCP2_f` | 4 | `INDEX_MCP_FE` | 5 | 4 |
| 4 | `index_pip_flexion` | `PIP2` | 6 | `INDEX_PIP_FE` | 6 | 5 |
| 5 | `middle_mcp_flexion` | `MCP3_f` | 7 | `MIDDLE_MCP_FE` | 9 | 7 |
| 6 | `ring_mcp_flexion` | `MCP4_f` | 9 | `RING_MCP_FE` | 13 | 10 |
| 7 | `pinky_mcp_flexion` | `MCP5_f` | 13 | `PINKY_MCP_FE` | 17 | 13 |
| 8 | `pinky_pip_flexion` | `PIP5` | 15 | `PINKY_PIP_FE` | 18 | 14 |

Independently re-verified in this round:
`constants.py::JOINTS` was imported from the official checkout and returns exactly
`[THUMB_CMC_FE, THUMB_CMC_AA, THUMB_MCP_FE, THUMB_IP_FE, INDEX_MCP_AA, INDEX_MCP_FE,
INDEX_PIP_FE, INDEX_DIP_FE, MIDDLE_MCP_AA, MIDDLE_MCP_FE, MIDDLE_PIP_FE, MIDDLE_DIP_FE,
RING_MCP_AA, RING_MCP_FE, RING_PIP_FE, RING_DIP_FE, PINKY_MCP_AA, PINKY_MCP_FE,
PINKY_PIP_FE, PINKY_DIP_FE]` — all eight emg2pose indices are correct.
The DB9 side coincides with `TRUSTED_DB9_POSE_v1.json` and `src/common_pose/api/dof.py`.

**All 8 are single-joint flexion/extension hinge DOFs.** None is an ab/adduction variable. That
matters: the one dimension in canonical16 whose sign is not globally meaningful
(`thumb_cmc_ab_adduction`) and the four dropped non-thumb MCP-AA variables are all outside this
set, so **no per-finger polarity hazard is in scope**.

---

## 4. Validity classification of historical claims

The instruction for this round was to separate claims carefully rather than treat the old
coordinate-audit results as uniformly valid or uniformly invalid. The classification below is
established from artifacts, not from assumption.

### 4.1 `CURRENT_VALID`

| claim | where | independent corroboration found this round |
|---|---|---|
| Official emg2pose joint order and the 16-dim canonical16 index vector | `CANONICAL16_CONTRACT.md`; audit §3 | re-imported `constants.py::JOINTS` — exact match |
| DB9 22-channel vocabulary from the in-file `order_of_angles` | `DB9_CANONICAL16_MAPPING.md` §1.1; audit §3 | `TRUSTED_DB9_POSE_v1.json` + `dof.py` agree on all 8 indices |
| Units: DB9 degrees, emg2pose radians, explicit π/180 | audit §7 criterion C | parity over 77 files / 77 354 864 samples, max \|diff\| 8.88e-16 rad |
| Sign: positive = flexion on both sides for all 8 | DB9 paper Table 6; emg2pose FK | per-joint FK table for all 8 (see §6) |
| **Zero semantics** (both = extended fingers-together hand) | audit §7 criteria E/F | DB9 anchor measured 0.854°; emg2pose FK at all-zero = extended |
| Angle convention (rotation magnitudes, not interior angles) | audit §7 criterion G; §17 | PIP round-trip 0.55–0.90° |
| Range/wrapping (neither wraps) | audit §7 criterion H | — |
| DB9 physical identity of all 8 | `FINAL_VALIDATION.md` | per-channel 77-participant table extracted from the JSON artifact (§5) |
| DB9 **within-source** calibration provenance | `FORENSIC_CORE.json` `.A_transform_forms` | recovered in this round: exact single-column affine map for all 8, slopes matching published gains within 0.61 % (§9.1) |
| Code-path parity (13 paths, none disagree) | audit §5 | `canonical_hand.py` byte-identical to the hash the audit pinned |

### 4.2 `CURRENT_VALID_WITH_LIMITATION`

| claim | limitation |
|---|---|
| The audit's per-dimension numeric gaps (DB9 median vs emg2pose median, Wasserstein, support overlap) | Corpus asymmetry: DB9 is a scripted 17-movement protocol; emg2pose-mini is natural activity from **one** subject. The audit itself computed the emg2pose session/prompt spread at median **72.24°** against a cross-dataset median gap of **19.32°** — a ratio of **3.74×** — and stated that **no per-dimension cross-dataset claim in the 20–30° range is resolvable with this corpus at all**. These numbers are usable as *diagnostics*, not as calibration measurements. |
| `matched_semantic_max_abs_gap_deg` per DOF | Rests on **n = 4 / n = 6** two-rater-consensus windows, 4 not evaluable. The audit labels it descriptive. It is used here only as a corroborating flag, never as the deciding evidence. |
| `COMMON_POSE_API_VERDICT.json` groups B/C/D | This artifact was written **before** the decisive within-DB9 anchor test. Its group D ("semantically matched but numerically dataset-specific") lumps the four genuinely defective channels together with seven merely calibration-uncertain ones. Its *content* is not wrong; its *granularity* is superseded by `DIMENSION_CONFIDENCE_CLASSIFICATION.json`, which is what this reconciliation uses. |
| The `I_handedness = UNCERTAIN ×16` criterion | Contained rather than closed — see §7. |
| The DB1/DB2/DB5 reference means | See §4.4 — the ledger's status note for these is contradicted by the audit's own provenance. |

### 4.3 `SUPERSEDED` / `INVALIDATED`

| # | old claim | class | why | what replaces it |
|---|---|---|---|---|
| S1 | `DB9_EMG2POSE_ZERO_COMPATIBILITY.json` §`thumb_cmc_ab_adduction`: `emg2pose_positive_is_abduction: false`, confidence MEDIUM | **SUPERSEDED** | Probe used only ±0.3 rad **and** used the displacement vector's palm-normal component, not the elevation angle; elevation is non-monotonic and peaks near −0.44 rad | The full-range FK sweep over `[-0.6118, +0.6118]` rad in `DB9_CANONICAL16_MAPPING.md` §4.2. Not in the trusted-8 (CMC1_a is INCONCLUSIVE). |
| S2 | `TRUSTED_DB9_POSE_v1.json` `exclusion_list[CMC5].case = CASE_B_SENSOR_OR_FIT_LIMITATION` | **SUPERSEDED** | Artifact frozen before the final case was settled | `CASE_A_RELEASED_REPRESENTATION` — released `CMC5` is an exact affine function of the same raw column that feeds `WRIST_F` (`research_status.md` §A3; `db9_trusted_subset.md` §4.3) |
| S3 | `TRUSTED_DB9_POSE_v1.json` `n_subjects: 37` throughout | **SUPERSEDED** | Loader selection artifact (filename `_E2_` vs DB2's `_E1_`) | 77 of 77 participants; `FINAL_VALIDATION.md`. **0 of 8 KEEP channels changed.** |
| S4 | `PIP3` and `DIP4` at `INCONCLUSIVE` (as recorded in the frozen subset JSON) | **SUPERSEDED** | 77-participant sample pushes both below the frozen floor | Both now `DROP` — strictly more conservative. Not in the trusted-8. |
| S5 | The 179.7° grand-mean offset read as a possible cross-dataset **coordinate mismatch** | **INVALIDATED** | Audit §20: dominated by DB9's broken DIP channels, task composition, and source-database imbalance | A genuine cross-dataset disagreement that is smaller, joint-specific, differently shaped |
| S6 | "11 of 16 candidate DB9 channels fail" | **PARTIALLY OVERTURNED** | Built on the pre-relabelling `repetition` vector, length-misaligned with the kinematics in 24 of 99 released files | Correct `restimulus × rerepetition` segmentation; six suspects exonerated ≥0.90 |
| S7 | `shared10_poc_v1` contains the intended ten anatomical DOFs | **INVALIDATED** | Four columns given semantics from a different UJI column order | Corrected vector `[1,2,5,6,7,8,10,11,14,15]`. Different dataset; not in scope. |

### 4.4 The one claim in this round whose status the ledger gets **wrong** — reported, not edited

`docs/research_status.md` §E5 (`SUPERSEDED`) states:

> "The coordinate audit's reported per-source-database reference means (DB1 18.0° / DB2 5.9° /
> DB5 21.3°) were computed on a `repetition`-grouped corpus that does not match the frozen one.
> **Not current evidence.** The audit's parity claim also overstated what was verified — it
> compared an adapter against itself."

**Every one of those four assertions is contradicted by the artifacts it describes.**

| ledger assertion | evidence against it |
|---|---|
| computed on a `repetition`-grouped corpus | `POSE_COORDINATE_AUDIT_PLAN.json` `.frozen_input_pins` pins `data/db9_posture16/representative_postures_77.npz` at SHA-256 `4fba093dff0ef82925176a77358b934ebcb362bd35b262d21d2ec7611f5e8b9f`, and `repetition_trajectories_77.npz` at `d3952647…538be13`. |
| "does not match the frozen one" | Report §6: "DB9: raw `.mat` → hand-rolled conversion vs adapter, **77 files / 77 354 864 samples** — bit-exact for 76 of 77 files; worst file 8.88e-16 rad." That is the frozen 77-file Exercise-B corpus. |
| the old corpus's defining defect was still present | Report §26 bug 8: "`db9_pick_file_for_slot` initially keyed on the filename tag `_E2_` … the protocol file is now identified **from the data** … never from the filename." This is **the exact defect that separated 37 from 77**, found and fixed. |
| parity "compared an adapter against itself" | Report §5/§6 and `CANONICAL16_IMPLEMENTATION_GRAPH.json`: **13 construction paths**, emg2pose hand-rolled vs frozen adapter max \|diff\| = 0.0, DB9 hand-rolled vs adapter ≤ 1 ULP with the cause identified (divide vs multiply by π/180). A hand-rolled independent conversion is not the adapter. |
| the values are "not current evidence" | The non-zero values are exactly the ones in `SOURCE_DEFINITION_AUDIT.json` (`mean_abs_deg`: `18.001369645094872` / `5.910625352175333` / `21.268398422619146` in `DB9_SOURCE_CALIBRATION_AUDIT.json`) and those artifacts are otherwise treated as current everywhere else in the ledger. |

**One genuine nuance the ledger may be reaching for.** The report's §26 bug 8 records that the
filename-tag defect existed *initially* and was fixed *in-loop*, and the report's §2 says the plan
was hashed before results while §25 records artifacts added after the freeze. So the audit's own
history contains a period in which DB9 file selection was wrong. The audit's *published* numbers
are the post-fix ones; the report does not present pre-fix numbers as results, and §6 reports 77
files. If the ledger's author was generalising "this lane once had the 37/77 defect" into "this
lane's numbers are from the old corpus", that would explain §E5 — but it is not what the artifacts
say.

**Consequences, stated both ways.**

* If §E5 were correct, the four `INTERCHANGEABLE_WITH_KNOWN_CONVENTION` rows would lose their
  supporting cross-source diagnostics and would have to be re-derived.
* **The four `SEMANTICALLY_MATCHED_BUT_CALIBRATION_UNCERTAIN` rows stand either way**, because
  they rest on the *within-DB9, transform-free, cross-dataset-free* anchor test (audit §10a),
  which does not depend on the cross-dataset corpus at all.
* **No verdict in this document is decided by the disputed numbers.** `median_gap_deg`,
  `wasserstein_deg` and `support_overlap` are reported in the matrix as diagnostics, and §10
  states explicitly that they are confounded and are not used to decide interchangeability.

> **Status: REPORTED.** No authoritative document was edited. Per the rule for this phase, a
> contradiction between a public artifact and a report of that artifact is surfaced, not
> silently resolved. §E5 is the single item that should be corrected by the research lead, and
> the correction belongs in the ledger, not in the audit artifacts.

---

## 5. DB9 side — what the frozen evidence actually establishes

Extracted from `FINAL_VALIDATION.json` `.Q1_verdicts.ALL77` (77 participants) and
`.Q1_verdicts.DB5` (10 participants). `agreement` is the subject-level fraction whose released
angle moves in the documented direction on the fist anchor; `mag_ratio` is the released-angle
change relative to the flexion-channel median.

| channel | status | agreement | opposed | coherence | mag_ratio | DB5-alone status | DB5-alone agreement |
|---|---|---|---|---|---|---|---|
| `MCP1` | KEEP | **0.9221** | 0.0779 | 1.00 | 0.549 | **INCONCLUSIVE** | **0.700** |
| `IP1` | KEEP | 1.0000 | 0.0000 | 1.00 | 1.020 | KEEP | 1.000 |
| `MCP2_f` | KEEP | 1.0000 | 0.0000 | 1.00 | 1.316 | KEEP | 1.000 |
| `PIP2` | KEEP | **0.9870** | 0.0130 | 1.00 | 1.954 | KEEP | 1.000 |
| `MCP3_f` | KEEP | 1.0000 | 0.0000 | 1.00 | 2.502 | KEEP | 1.000 |
| `MCP4_f` | KEEP | 1.0000 | 0.0000 | 1.00 | 1.760 | KEEP | 1.000 |
| `MCP5_f` | KEEP | 1.0000 | 0.0000 | 1.00 | 1.867 | KEEP | 1.000 |
| `PIP5` | KEEP | **0.9740** | 0.0260 | 1.00 | 1.000 | KEEP | 1.000 |

**Finding that is new to this reconciliation.** `MCP1` is the only one of the eight whose
physical anchor is **not** reproduced in every source database. The per-source verdicts inside
the same artifact read DB1 1.000 / DB2 0.925 / **DB5 0.700 (INCONCLUSIVE)**. The frozen rule pools
all 77 and 0.9221 clears the floor, so the `KEEP` is correct **under the frozen rule** — this is
not a contradiction and does not re-open the subset. But it does mean:

> `MCP1`'s thumb-MCP physical anchor is carried by DB1 and DB2. In DB5 — 10 of the 77
> participants — the channel does not reproduce the documented direction.

This is recorded as a limitation on `MCP1`'s sign evidence (§6) and appears in the matrix as
`db5_only_anchor_status`.

**Also worth stating plainly:** DB9's own definitions carry **no direction arrow**. The released
`angles` are `f(glove) − f(glove_reference)`; the direction comes from the paper's Table 6 and
from the observed response on the fist anchor. Both are behavioural/documented rather than
encoded, which is exactly why the per-channel agreement figure is the relevant strength measure
and not a formality.

---

## 6. Sign compatibility — ESTABLISHED for all 8, with one measured caveat

**DB9 side.** Paper Table 6 (`DB9_CANONICAL16_MAPPING.md` §3.2, tagged `[OFFICIAL-DOC]`) gives
**Flexion + / Extension −** for `DIP(2-5)_F`, `PIP(2-5)_F`, `IP1_F`, `MCP(1-5)_F`. All 8 trusted
channels are inside that list.

**emg2pose side.** Independent forward-kinematics test, per joint
(`joint_convention_verification.txt`), metric = Euclidean distance from the fingertip landmark to
`PALM_CENTER`; flexion shortens it:

| joint | d(rest) | d(+limit) | d(−limit) | verdict |
|---|---|---|---|---|
| `THUMB_MCP_FE` | 88.52 | **48.61** | 88.52 | +limit = FLEXION |
| `THUMB_IP_FE` | 88.52 | **70.77** | 90.25 | +limit = FLEXION |
| `INDEX_MCP_FE` | 99.72 | **75.80** | 102.78 | +limit = FLEXION |
| `INDEX_PIP_FE` | 99.72 | **53.36** | 99.72 | +limit = FLEXION |
| `MIDDLE_MCP_FE` | 109.85 | **79.88** | 113.86 | +limit = FLEXION |
| `RING_MCP_FE` | 103.38 | **76.46** | 107.06 | +limit = FLEXION |
| `PINKY_MCP_FE` | 88.31 | **66.12** | 93.62 | +limit = FLEXION |
| `PINKY_PIP_FE` | 88.31 | **45.26** | 88.31 | +limit = FLEXION |

**Both sides agree; the adapter applies no sign transform to any of the 8**
(`sign_transform_applied = 1.0` in `SOURCE_DEFINITION_AUDIT.json` for each). The single frozen
sign flip in the whole mapping (`thumb_cmc_ab_adduction × −1`) is outside the trusted-8.

**Caveat, stated rather than buried.** For `MCP1` the sign assertion rests on 0.9221 — not 1.0 —
of 77 participants, and on 0.700 of DB5's 10. `IP1` is the only trusted channel whose title
("IP1", not "PIP1") differs from the emg2pose naming convention (`THUMB_IP_FE`); the mapping is
correct but the nominal asymmetry is worth noting for readers. Neither affects the 7 channels at
1.000/0.987/0.974.

---

## 7. Zero and reference — the two questions that must be kept apart

### 7.1 `ZERO_SEMANTICS_ESTABLISHED` — all 8

* **DB9**: "the sensor signals were transformed according to the outputs relative to a reference
  posture. The reference posture was chosen as the central part of movement 11 in exercise B,
  corresponding to the hand resting on the table with the fingers closed together and extended."
  (`DB9_CANONICAL16_MAPPING.md` §3.3, quoting Jarque-Bou et al. 2020.)
* **emg2pose**: the official 20D zero vector. Forward kinematics of the official model at all-zero
  gives finger-chain interior angles of **179.10° / 179.45° / 179.28° / 174.85°** (proximal) and
  **168.44° / 166.68° / 172.82° / 171.36°** (distal) against 180° = perfectly straight, and the
  zero pose sits **1.06 %** of the way along the most-closed → most-spread range.
  → the zero pose **is** an extended, fingers-together hand.
* So the two datasets define their zero at **the same physical configuration**.

### 7.2 `NUMERICAL_ZERO_INTERCHANGEABILITY_ESTABLISHED` — **NOT ESTABLISHED for any of the 8**

This is the sharpest genuine gap in the whole reconciliation, and the reason it is a gap is
structural, not a missing measurement that was forgotten:

1. **The emg2pose side of the zero claim is not a measurement.** emg2pose's zero is *0 by
   construction* — it is the model's parameter origin. The hand-model `joint_limits` corroborate
   the interpretation (`THUMB_MCP_FE`, `INDEX_PIP_FE`, `MIDDLE_PIP_FE`, `RING_PIP_FE`,
   `PINKY_PIP_FE` all have `min = 0°`; no FE joint extends past 0°), but *the assertion that the
   emg2pose zero is a physically attained, hand-on-a-table pose has never been measured.*
2. **The DB9 side is source-database dependent.** At the documented anchor, mean |angle| is
   **DB1 18.001° / DB2 5.911° / DB5 21.268°**. DB2 is essentially exactly zero; DB1 and DB5 are
   not. The audit's reading is that the deviations are per-joint and **not** a common translation
   (median +0.84°, range −11.18° … +5.27°, concentrated on `ring_dip_flexion` −11.18°,
   `middle_dip_flexion` −5.70°, `pinky_mcp_flexion` +5.27°), with centred-profile Pearson
   r = +0.909 / +0.933. So the zero *definition* is shared; the zero's *numerical realisation*
   is not a single constant even inside DB9.
3. **The only available cross-source statistic is confounded.** The per-dimension median gaps
   (this set: 10.56°–31.23°) compare a scripted protocol against natural activity, and the
   audit measured the emg2pose session spread at **3.74×** the cross-dataset median gap.

> **Explicit statement, as required:** the zero *semantics* match; the **numeric cross-source
> zero remains dataset-specific and unverified**. The old repetition-grouped offset values are not
> used anywhere here — see §4.4 for why the 18.001/5.911/21.268 numbers are in fact current.

---

## 8. Handedness — contained, not closed

The coordinate audit set criterion **I (handedness) = UNCERTAIN ×16** and carried it forward as
the one unresolved item:

> "DB9 is a right-hand protocol; the emg2pose mini corpus contains 15 left and 15 right
> recordings, and no handedness transform is applied anywhere. The project's frozen contract
> treats the 20D vector as model-frame, and this audit did not establish whether the UmeTrack
> model frame is handedness-invariant for the left recordings."

What the artifacts *do* establish:

| fact | source |
|---|---|
| DB9 has **no side field**; the protocol instructed the right hand, and the DB9 page's "Handedness" column is the participant's own handedness, **not** the recording side | `DB9_CANONICAL16_MAPPING.md` §1 |
| DB9 recording side: **right** | `src/common_pose/api/dof.py` (`handedness="right"` on all 8) |
| emg2pose does not mirror the joint angles for left sessions; it "flips the EMG sign for left hands" — joint angles are in the one model frame | `CANONICAL16_EQUIVALENCE_MATRIX.csv` column 11, corroborated by `joint_angle_definition.md` |
| emg2pose-mini = 15 left + 15 right recordings, **all one subject** | `EMG2POSE_SESSION_CALIBRATION_AUDIT.json`; audit §14 |

**Assessment for the trusted-8.** `UNCERTAIN ×16` is correct as an audit-level statement and is
carried into the matrix as `ESTABLISHED_WITH_LIMITATION`, not as `ESTABLISHED`. But it is
**contained** for this specific set, for three reasons:

1. all 8 are single-joint **flexion hinge magnitudes**, so a chirality permutation cannot change
   *which joint* a value describes, only which hand it is drawn on;
2. no handedness transform is applied on either side, so no meaning-changing transform is in
   scope to get wrong;
3. the limitation that actually matters for substitution is a *comparison* hazard — pooling the
   15 left and 15 right emg2pose sessions could contaminate a numerical comparison — and that is
   a property of how a future evaluation is run, not of the mapping.

**Residual, honestly stated.** The strict formulation "emg2pose joint angles are flipped into a
single right-hand model frame" is the coordinate audit's own **rendering**, recorded in its
artifacts; it was **not** located as a first-party statement inside the official emg2pose release
by this round (the official `hand.py` / `data.py` were not read in full). Per the instruction not
to re-run S4 renderer work, no render was performed. The claim is therefore carried as the audit's
rendering rather than as an official statement.

---

## 9. Calibration provenance — the load-bearing gap, and how far it was closed this round

### 9.1 `WITHIN_SOURCE` provenance for DB9 is **ESTABLISHED**, recovered from the bytes

The strongest calibration evidence in the corpus had not been carried into the matrix by any
earlier document, so it is stated here. `FORENSIC_CORE.json` `.A_transform_forms` recovers the
released calibration for **all 8** trusted channels as an exact affine map of **one** raw glove
column:

| channel | raw `glove` col | released `angles` col | recovered slope | published gain | slope / published | max residual | implied `S_ref` |
|---|---|---|---|---|---|---|---|
| `MCP1` | 1 | 2 | 0.562292 | 0.562 | **1.00052** | 1.03e-11° | 114.81 |
| `IP1` | 2 | 3 | 1.190877 | 1.19 | **1.00074** | 3.79e-12° | 94.49 |
| `MCP2_f` | 4 | 4 | 0.912878 | 0.91 | **1.00316** | 1.07e-11° | 112.41 |
| `PIP2` | 5 | 6 | 0.908574 | 0.91 | **0.99843** | 1.04e-11° | 48.05 |
| `MCP3_f` | 8 | 7 | 0.952650 | 0.95 | **1.00279** | 7.45e-12° | 73.61 |
| `MCP4_f` | 12 | 9 | 0.970040 | 0.97 | **1.00004** | 1.15e-11° | 76.41 |
| `MCP5_f` | 16 | 13 | 1.066439 | 1.06 | **1.00607** | 7.76e-12° | 63.36 |
| `PIP5` | 17 | 15 | 0.891060 | 0.89 | **1.00119** | 1.55e-11° | 63.84 |

Two conclusions follow, and both matter:

1. **The released DB9 calibration is auditable and faithful.** Every recovered slope reproduces
   the *published* calibration gain to within **0.61 %**, and each channel's released angle is a
   single-column affine function with residual ≤ 1.6e-11°.
2. **The zero is per-subject by construction.** `S_ref_implied` is the subject's own raw gauge
   value at the reference posture, and the released angle is
   `slope × (glove − S_ref)`. So the released `angles` are already *subject-normalised to the
   documented reference posture* — there is no additional per-subject centring for a Common Pose
   consumer to apply, and no hidden per-subject constant left inside the number.

*Provenance caveat:* `FORENSIC_CORE.json` is from the frozen **37-participant** run. Its
per-channel *agreement* figures are superseded by the 77-participant revalidation (§5), but the
recovered transform coefficients are properties of the **released calibration**, not of the
sample. The two are not interchangeable and are not conflated here.

**A check that this round did not over-read.** The same artifact also carries
`A2_reconstruction_parity` with `max_over_all = 2213.67` and `median_of_per_file_max = 57.40`
degrees — far larger than the per-channel residuals above. These measure different things: the
per-channel residual is the fit of one channel's released-angle column to one raw column, whereas
the reconstruction parity carries a per-file maximum across channels. The reconciliation does
**not** claim the small residuals imply a small whole-vector reconstruction error; the gap is
recorded as unexplained rather than assumed benign. It does not affect any status here, because
nothing in this document depends on whole-vector reconstruction.

### 9.2 `CROSS_SOURCE` provenance is **NOT ESTABLISHED** — this is the real gap

| | DB9 | emg2pose |
|---|---|---|
| what the number is | a per-channel **linear sensor calibration** from the raw CyberGlove signal to anatomical degrees | the output of an **inverse-kinematics fit** of a generic hand model to motion capture |
| where the gains come from | a calibration protocol on **10 subjects**, then applied to all **77** | no sensor calibration; no per-subject/per-session calibration record |
| vendor caveat | official page: DIP sensors "provide reliable angles when subject hand size is big … may provide partial results when the hand of the subject is small" | — |

Criterion **J** is the **only** one of the ten that FAILS, and it fails for all 16 dimensions.
`canonical16` as consumed **silently mixes** a well-measured subset with a subset that is not
measuring what it claims. The audit's own conclusion is that a shared API must carry
**per-channel calibration provenance, not just the anatomical name**.

**The precise statement of the gap, now that §9.1 is in hand.** Knowing DB9's ruler exactly does
**not** establish that emg2pose uses the same ruler. For the trusted-8:

* `SAME_ANATOMICAL_VARIABLE` — **ESTABLISHED** for all 8;
* `NUMERICALLY_CALIBRATED_TO_SAME_PHYSICAL_SCALE` — **UNRESOLVED for all 8**.

**Two inferences this round explicitly refuses to make**, per the phase rules:

* similar distributions ⇒ calibration equivalence — **refused** (the corpora do not share a pose
  distribution, so similar marginals would not imply a shared scale);
* different means ⇒ incompatibility — **refused** (task composition alone can produce the
  observed median gaps; the audit's own §15 showed that matching the gesture *increased* the
  disagreement, which is evidence about DB9's channels, not about a scale factor).

---

## 10. The audit's "already trustworthy" shortlist is NOT "cross-source interchangeable"

This is the single most important reconciliation in this document, and it is a correction of
*scope*, not of fact.

`POSE_COORDINATE_AUDIT_REPORT.md` §22B names four dimensions as "already trustworthy":
`thumb_ip_flexion`, `index_pip_flexion`, `ring_mcp_flexion`, `pinky_pip_flexion`, classified
**VERIFIED NUMERICALLY EQUIVALENT**. A reader could take that as "these four are safe to
substitute". The artifacts do not support that reading:

| the audit says | the audit does not say |
|---|---|
| the channel responds correctly to flexion **and** its movement-to-movement profile matches its own emg2pose counterpart | that the two numbers share a physical scale |
| `thumb_ip_flexion` → **`empirical_range_compatibility: LOW`**, §18 status "NOT YET SAFE (range disagreement 31°)" | that the range question is resolved for it |
| criterion J fails ×16 | that these four escaped the calibration-provenance failure |
| — | that any DOF is `DIRECTLY_INTERCHANGEABLE` |

The four are also the four with `joint_identity_diagonal_winner = true`, i.e. their own
counterpart is the best-matching emg2pose dimension. That is a genuinely stronger structural
result and is why they are `INTERCHANGEABLE_WITH_KNOWN_CONVENTION` here rather than
`..._CALIBRATION_UNCERTAIN`. It is not a licence to treat them as numerically identical.

**One audit-internal figure that this round could not reproduce — reported, not resolved.**
`thumb_ip_flexion`'s §18 cell reads "range disagreement **31°**", and `empirical_range_compatibility`
is `LOW` only for that DOF among the trusted-8. But:

* `DIMENSION_CONFIDENCE_CLASSIFICATION.json` and `CANONICAL16_EQUIVALENCE_MATRIX.csv` both carry
  **`empirical_range_compatibility: LOW`** for `thumb_ip_flexion` and the value `31.2328` appears in
  both as **`median_difference_deg`** — the *median location* gap, not a range/span gap;
* the official emg2pose limits for `THUMB_IP_FE` are `−14.81° … +62.30°` and DB9's median is
  `+6.89°` — neither yields a 31° *range* disagreement from the evidence in this repository;
* the construction rule for `empirical_range_compatibility` is **not present** in
  `common-pose` (the audit's tooling lives in the pre-git lane), so the figure is not
  independently reproducible from what is preserved here.

Most likely the cited 31° is the median gap, and the field name overstates what it measures. Because
the direction of the resulting verdict is **conservative** (`LOW` / "NOT YET SAFE" is a caution, not
a clearance), this does not change any status assigned here — `thumb_ip_flexion` is still
`INTERCHANGEABLE_WITH_KNOWN_CONVENTION` with `db9_anchor_change_deg` unrecorded and no
`DIRECTLY_INTERCHANGEABLE` claim. It is recorded so that the 31° is not quoted as a range fact.

**Not a contradiction, and therefore not a stop condition.** `docs/db9_trusted_subset.md` §6
already states that the project does **not** claim "that these DOFs are numerically comparable
with another dataset's". The audit and the ledger agree. The risk was only that a shortlist label
could be over-read; this document pins the reading down.

---

## 11. Per-DOF evidence matrix (summary of the authoritative artifact)

Full machine-readable rows: `artifacts/TRUSTED8_EVIDENCE_MATRIX.csv` / `.json` (45 columns).
`anchor` = signed DB9 change from the extended anchor to the flexed anchor, where recorded.

| DOF | DB9 | agreement @77 | median gap | matched-semantic gap | anchor | diag. winner | src-DB dep. | cal. provenance | audit class | interchangeability |
|---|---|---|---|---|---|---|---|---|---|---|
| `thumb_mcp_flexion` | `MCP1` | 0.9221 | 10.56° | 10.57° | *n/r* | no | not detected | WITHIN est. / CROSS no | SEMANTIC, CAL. UNCERTAIN | SEMANTICALLY_MATCHED_BUT_CALIBRATION_UNCERTAIN |
| `thumb_ip_flexion` | `IP1` | 1.0000 | 31.23° | 4.40° | *n/r* | **yes** | not detected | WITHIN est. / CROSS no | **NUMERICALLY EQUIVALENT** | INTERCHANGEABLE_WITH_KNOWN_CONVENTION |
| `index_mcp_flexion` | `MCP2_f` | 1.0000 | 14.69° | 7.08° | +54.89° | no | **YES** | WITHIN est. / CROSS no | SEMANTIC, CAL. UNCERTAIN | SEMANTICALLY_MATCHED_BUT_CALIBRATION_UNCERTAIN |
| `index_pip_flexion` | `PIP2` | 0.9870 | 27.85° | 52.03° | +106.98° | **yes** | **YES** | WITHIN est. / CROSS no | **NUMERICALLY EQUIVALENT** | INTERCHANGEABLE_WITH_KNOWN_CONVENTION |
| `middle_mcp_flexion` | `MCP3_f` | 1.0000 | 20.69° | 26.95° | +96.18° | no | **YES** | WITHIN est. / CROSS no | SEMANTIC, CAL. UNCERTAIN | SEMANTICALLY_MATCHED_BUT_CALIBRATION_UNCERTAIN |
| `ring_mcp_flexion` | `MCP4_f` | 1.0000 | 17.96° | 4.51° | +70.01° | **yes** | **YES** | WITHIN est. / CROSS no | **NUMERICALLY EQUIVALENT** | INTERCHANGEABLE_WITH_KNOWN_CONVENTION |
| `pinky_mcp_flexion` | `MCP5_f` | 1.0000 | 14.70° | 59.47° | +123.79° | no | **YES** | WITHIN est. / CROSS no | SEMANTIC, CAL. UNCERTAIN | SEMANTICALLY_MATCHED_BUT_CALIBRATION_UNCERTAIN |
| `pinky_pip_flexion` | `PIP5` | 0.9740 | 23.97° | 73.56° | +36.12° | **yes** | not detected | WITHIN est. / CROSS no | **NUMERICALLY EQUIVALENT** | INTERCHANGEABLE_WITH_KNOWN_CONVENTION |

*n/r = not recorded.* The audit's per-finger anchor table (§10a) covers index/middle/ring/pinky;
`DIMENSION_CONFIDENCE_CLASSIFICATION.json` stores `db9_anchor_change_deg = null` for both thumb
channels. Their directional evidence is the `A_FIST` anchor at 77 participants (0.9221 and
1.0000). **This is a genuinely thin spot for `MCP1` and `IP1`** and is recorded as such rather
than filled in by inference.

`matched-semantic gap` rests on n = 4/6 windows and is **descriptive only**; it is not used to
decide any status (see §4.2).

---

## 12. "What is actually left?"

### A. CLOSED — no more work needed

* Anatomical correspondence for all 8 DOFs (criteria A, B PASS ×16).
* DB9 and emg2pose source indices (independently re-verified this round).
* Units, with explicit π/180 and bit-level parity over 77 354 864 samples.
* Sign: positive = flexion on both sides; zero sign transforms applied. *(caveat: `MCP1` at
  DB5-only 0.700 — see B.)*
* Zero **semantics**: both zero at the extended, fingers-together hand; DB9 anchor attained to
  0.854°; emg2pose zero FK-confirmed extended.
* Angle convention: rotation magnitudes about fixed joint-specific axes.
* Range/wrapping: neither side wraps or clamps (the adapter is contractually forbidden to clamp).
* DB9 physical identity of all 8: 77/77, 0 of 8 KEEP changed.
* **DB9 within-source calibration provenance**: all 8 released angles are exact single-column
  affine maps (residual ≤ 1.6e-11°), slopes reproduce the published gains to within 0.61 %, and
  the release is already subject-normalised to the documented reference posture.
* The 8 are disjoint from every DOF the audit found directionally defective.
* No per-finger AA polarity hazard in scope.

### B. PARTIALLY CLOSED

* **Numerical interchangeability**: 4 of 8 `INTERCHANGEABLE_WITH_KNOWN_CONVENTION`
  (`IP1`, `PIP2`, `MCP4_f`, `PIP5`); 4 of 8 `SEMANTICALLY_MATCHED_BUT_CALIBRATION_UNCERTAIN`
  (`MCP1`, `MCP2_f`, `MCP3_f`, `MCP5_f`). **None is `DIRECTLY_INTERCHANGEABLE`.**
* **`MCP1` sign/physical anchor**: 0.9221 pooled; DB5-alone 0.700 (INCONCLUSIVE).
* **Range compatibility**: `thumb_ip_flexion` is `LOW` / "NOT YET SAFE" — but the quoted "31°"
  range disagreement is not reproducible from the preserved artifacts and appears to be the
  *median location* gap (31.23°), not a span gap; see §10. `thumb_mcp_flexion`'s anchor change is
  not recorded at all.
* **Source-database independence**: 5 of 8 show a DB2−DB1 subject-level CI excluding zero
  (`MCP2_f` −15.54°, `PIP2` −29.64°, `MCP3_f` −40.08°, `MCP4_f` −13.64°, `MCP5_f` −52.04°).
* **`NUMERICAL_ZERO_INTERCHANGEABILITY`**: NOT ESTABLISHED for all 8.
* **Handedness**: criterion I UNCERTAIN ×16; contained, not closed.
* **emg2pose official-limit adherence**: 0.05 %–20.97 % of mini-corpus frames lie outside the
  official UmeTrack limits per DOF, and the frozen contract forbids clamping — so the
  "defensible range" of an emg2pose value is wider than the model's nominal limits.

### C. TRUE REMAINING BLOCKERS

Three, all non-task-derived, all characterisable without outcome fitting:

| id | blocker | affects | nature |
|---|---|---|---|
| **B1** | No **cross-source** calibration record: the DB9 ruler is fully known (recovered from the bytes) but emg2pose's is not, and the frozen head's decision boundaries were learned on DB9 scales. "Same physical variable" does not yet imply "same physical scale". | all 8 | needs **one minimal pre-declared check** (N2) |
| **B2** | `NUMERICAL_ZERO_INTERCHANGEABILITY` NOT ESTABLISHED — the emg2pose zero is a construction fact, not a measurement. | all 8 | same check as B1 |
| **B3** | Source-database level shifts inside DB9 (5 of 8 DOFs) mean "DB9" is not one calibration; a substitution result cannot be attributed to upstream substitution alone unless source-database identity is carried as metadata. | `MCP2_f`, `PIP2`, `MCP3_f`, `MCP4_f`, `MCP5_f` | **metadata requirement — no new measurement needed** |

**Explicitly not blockers** (already-solved or out-of-scope historical problems): the 37-participant
loader artifact; the `_E2_`/`_E1_` filename selection defect; the `repetition` length-misalignment;
the broken DIP channels; `CMC5`; the 179.7° grand-mean offset; the `shared10_poc_v1` column-order
error; the thumb-AA sign question. All are superseded, closed, or outside the trusted-8.

---

## 13. Decision: `CONDITIONAL_GO`

Against the stated criteria:

| GO_TO_GATE2 requires | verdict |
|---|---|
| all 8 DOFs have established semantic/anatomical mapping | **YES** — criteria A/B PASS ×16, verified independently |
| units/sign/order are closed | **YES** |
| no unresolved handedness issue can change physical meaning | **YES** (contained — §8) |
| remaining calibration uncertainty can be characterised **without** outcome-driven fitting | **NO** — not with the existing artifacts |

Against `NO_GO`:

| NO_GO trigger | verdict |
|---|---|
| at least one required trusted DOF lacks defensible physical correspondence | **NO** — all 8 have ESTABLISHED anatomical correspondence, unit compatibility, sign compatibility and zero *semantics* |
| numerical comparability would require arbitrary fitted alignment | **NO** — no fitted alignment is required to *state* the mapping; the open question is measurement equivalence, not identity |

> **`CONDITIONAL_GO`.** Proceed only after the single minimal, pre-declared, outcome-free
> physical-compatibility check below. This is not a stalled position: it is the difference
> between "we know what these numbers mean" (true) and "we know they are the same ruler" (not yet
> established).

### NEXT MINIMAL CHECK — `N2` (specified, **NOT executed**)

| field | value |
|---|---|
| **question** | On the local emg2pose mini corpus, at frames realising the DB9 documented reference posture (hand resting on the table, fingers closed together and extended), what is the per-DOF distribution of the 8 canonical16 values? |
| **why it is new** | The audit verified the **DB9** side of the anchor (0.854°) and asserted the emg2pose side is 0 *by construction*. It never **measured** the emg2pose side at an equivalent physical posture. That is the single missing term in the zero claim. |
| **why it is not outcome-driven** | GT joint angles + the official hand model only. No head, no labels, no probabilities, no margins, no accuracy, no fitted parameter. The pass/fail rule is declared below before anything runs. |
| **data required** | local `data/official/emg2pose_dataset_mini/*.hdf5` (30 sessions, already present) + `generic_hand_model.json` (`96649ddf…ce07564`, hash-verified this round) |
| **local data sufficient?** | **YES** |
| **server needed?** | **NO** — CPU-only, no GPU, no training |
| **expected scope** | one pass over ~4.2 M already-local 20D frames; select frames by proximity to the DB9 reference-posture prototype in canonical16 space; report per-DOF median and p05/p95. Minutes. |
| **pass criterion** | for **every** one of the 8 DOFs the emg2pose value at reference-posture frames lies within **±2°** of 0 — i.e. consistent with the DB9 anchor's own per-joint residuals (absolute range 0.00°–1.94°). This establishes numerical zero interchangeability. |
| **fail criterion** | any DOF whose reference-posture frames sit at a non-zero level exceeding the DB9 anchor residual by more than the anchor's own movement-to-movement spread ⇒ a per-DOF zero offset, which is a hard blocker for head substitution and must be reported as a **negative** result. |
| **must not do** | if the natural mini corpus does not contain the reference posture, the check is **NOT_EVALUABLE LOCALLY** and must be reported as such — it must **not** be rescued by synthesising the pose from the model, because that would assume the model's zero equals the physical zero. |

---

## 14. Downstream firewall

| flag | value |
|---|---|
| `DOWNSTREAM_HEAD_ACCESSED` | **NO** |
| `TASK_LABELS_GENERATED` | **NO** |
| `TASK_PROBABILITIES_INSPECTED` | **NO** |
| `GT_VS_PRED_PRESERVATION_RUN` | **NO** |
| `MAPPING_TUNED_USING_TASK_OUTPUT` | **NO** |

Execution scope this round: 0 models trained; DB9 forensic not re-run; trusted channels not
re-selected; `TRUSTED_DB9_POSE_v1` not modified; no new heavy data files; no deep learning; no
server; no network.

One upstream-lane file was **read** for independent verification
(`emg2pose_handstate/baseline/.../constants.py`, `generic_hand_model.json`,
`docs/joint_convention_verification.txt`). All reads were read-only; nothing in that lane was
modified.

---

## 15. Reproducing this reconciliation

```powershell
cd common-pose
python -X utf8 experiments\upstream_substitution\pre_substitution_reconciliation\build_reconciliation.py
```

The script reads only published artifacts, copies every number from them, re-verifies the frozen
subset SHA-256, and rewrites the three files under `artifacts/`. It measures nothing.

---

## 16. Scientific interpretation — what this does and does not support

* **Supports:** for all 8 frozen DB9 DOFs, the corresponding emg2pose GT DOF is the *same named
  physical variable* under a defensible Common Pose interpretation — same joint, same unit, same
  positive direction, same zero *definition*, same angle convention, no per-finger sign hazard.
* **Supports:** the coordinate audit's semantic layer (criteria A–H) is intact and its pinned
  semantic contract is byte-identical in substance to the current docs (drift = path placeholders
  only, verified by hash-matching the audit-era copies).
* **Does not support:** that any of the 8 is *numerically* interchangeable. 4 are
  `INTERCHANGEABLE_WITH_KNOWN_CONVENTION`; 4 are
  `SEMANTICALLY_MATCHED_BUT_CALIBRATION_UNCERTAIN`. The word "trustworthy" in the audit's
  shortlist means "correctly measured on DB9's own anchors", not "same ruler as emg2pose".
* **Does not support:** numerical zero interchangeability, for any of the 8. The emg2pose zero is
  a construction fact; the DB9 zero is source-database dependent (18.001°/5.911°/21.268°).
* **Does not support:** that the frozen head will survive substitution. That is Gate 2 and has not
  been evaluated. Nothing here predicts its outcome in either direction.
* **Reports an unresolved provenance conflict:** `docs/research_status.md` §E5 classifies the
  coordinate audit's reference means as superseded on a corpus-mismatch ground that the audit's own
  frozen pins and parity results contradict. The audit's numbers are treated as current here, and
  the conflict is escalated rather than resolved unilaterally. No verdict in this document depends
  on the disputed numbers.
