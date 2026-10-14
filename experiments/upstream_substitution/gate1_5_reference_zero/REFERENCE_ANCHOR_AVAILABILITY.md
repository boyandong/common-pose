# REFERENCE-ANCHOR AVAILABILITY — GATE 1.5

**Gate:** PHASE 1 / GATE 1.5 — reference-anchor availability & numerical-zero check
**Question:** does the local emg2pose mini corpus contain a physical reference/neutral posture
that can be identified **independently of the trusted-8 joint-angle values**, and are the trusted-8
values at that posture compatible with the DB9 reference zero?

**Outcome:**

> **ANCHOR_STATUS: `NO_INDEPENDENT_ANCHOR`**
> **ZERO_GATE: `NOT_EVALUABLE_LOCALLY`**

`REFERENCE_ANCHOR_SPEC.md` was **NOT_CREATED** and no zero statistics were produced. No reference
frames were synthesised. This is a statement about what the local corpus can decide, not a
scientific failure.

Companion artifacts: `artifacts/REFERENCE_ANCHOR_DECISION.json`,
`artifacts/TRUSTED8_ZERO_COMPATIBILITY.json`, `logs/gate1_5_stdout.txt`.
Script: `scripts/audit_reference_anchor.py`.

---

## 1. Hard anti-circularity rule — stated and honoured

The forbidden selection rules were: trusted-8 angles near 0; minimum canonical16 norm; minimum
distance to a DB9 prototype; classifier output / probability / margin; downstream task label;
predicted pose; fitted offset; fitted calibration.

The audit that produced the decision in this document **never read a trusted-8 pose value**. It
inspected only: the HDF5 object/attribute structure, the group-attribute vocabulary, the
`metadata.csv` column schema, the local file inventory, and the official pipeline source. Every
candidate anchor was judged on two axes — *is it present locally* and *is it independent of the
pose values* — and neither axis required a joint angle.

---

## 2. Local corpus inventory

| property | value | source |
|---|---|---|
| files | **30** | `data/official/emg2pose_dataset_mini/*.hdf5` |
| sessions | **1** (`2022-12-06-1670313600-e3096-…`) | per-file `session` attribute |
| participants | **1** (`d387095792`) | per-file `user` attribute |
| hand sides | **left 15 / right 15** | per-file `side` attribute |
| stages | 15 per side (30 segments) | per-file `stage` attribute |
| frames | **4 218 756** | `timeseries` shape |
| `split` | all `val` | per-file attribute |
| `held_out_user` | all `True` | per-file attribute |

This reproduces the frozen figure already recorded in `docs/research_status.md` §A7 — the mini
corpus is one held-out user, so nothing derived from it is a cross-user benchmark.

**`metadata.csv` is the FULL corpus, not the local one.** It carries 25 253 rows across
**751 sessions** and **193 participants**; only one of those sessions is present on disk. This
distinction matters below: the local stage vocabulary is a strict subset of the 29-stage
vocabulary, and the gap is not random.

The 15 local stages:

`ThumbsUpDownThumbRotationsCWCCWP` · `CountingUpDownFaceSideAway` · `ThumbsSwipesWholeHand` ·
`FingerWigglingSpreading` · `FingerAbductionSeries` · `WristFlexionAbduction` ·
`FingerPinchesSingleFingerPinchesMultiple` · `FingerFreeform` · `IndividualFingerPointingSnap` ·
`HandClawGraspFlicks` · `ShakaVulcanPeace` · `HookEmHornsOKScissors` · `TwoHandedFreeStyle` ·
`OneHandedFreeStyle` · `unconstrained`

---

## 3. Candidate anchor audit

The gate asks for an anchor built from one of four source classes. Each was checked for presence
**and** independence.

| id | class | candidate | present locally | independent of trusted-8 | verdict |
|---|---|---|---|---|---|
| **A1** | A: official protocol/event marker | per-frame hand-posture or gesture label | **no** | — | `ABSENT` |
| **A2** | A: official protocol/event marker | the `stage` group attribute | **yes** | **yes** | `PRESENT_BUT_DOES_NOT_DEFINE_A_POSTURE` |
| **A3** | A: official protocol/event marker | stage `HandDeskSeparateClaspedChest` | **no** | partial | `ABSENT_LOCALLY` |
| **B** | B: synchronised annotation / protocol marker | any annotation stating the posture at a time | **no** | — | `ABSENT` |
| **C** | C: geometric / FK criterion | FK test for an extended configuration | yes | **no** | `PRESENT_BUT_CIRCULAR` |
| **D** | D: recorded calibration marker | a reference-pose marker in the generation pipeline | **no** | — | `ABSENT` |

### 3.1 A1 — no per-frame label (independently re-confirmed)

The HDF5 was walked object-by-object. There is exactly one group, `emg2pose`, holding exactly one
compound dataset, `timeseries`, with fields `time` (`f8`), `joint_angles` (`f4`, 20) and `emg`
(`f4`, 16). **There is no per-frame label field and no per-frame event or phase marker.** This
re-confirms the frozen project result D4 ("emg2pose cannot supply posture labels") directly from
the bytes rather than by citation.

### 3.2 A2 — the `stage` attribute is independent but specifies no posture

`stage` is genuinely independent of the pose values: it is an experimenter-assigned segment label,
not a function of the kinematics. **It is nonetheless not an anchor**, because it names a compound
*activity*, not a hand *posture*. None of the 15 local stage names specifies the geometric
configuration of the finger joints. `docs/EMG2POSE_DATASET_REFERENCE.md` calls `stage` the
"gesture/task" label, and the project's D4 finding is that the 29 stages are compound activities.

> This is the decisive distinction the gate turns on: *pose-independent* is necessary but not
> sufficient. An anchor must also *state a posture*.

### 3.3 A3 — the near-miss, and why it is not usable here

Of all 29 stage names, exactly one encodes a resting *position*: **`HandDeskSeparateClaspedChest`**.
It is the closest analogue in the entire corpus to DB9's documented reference posture ("the hand
resting on the table with the fingers closed together and extended", movement 11 central phase).

It is **not in the local corpus**, and this is not bad luck: the local participant recorded a
different 15-stage subset. So the one candidate that could plausibly have served as an independent
physical anchor is unavailable locally.

Two caveats are recorded even though they are moot given the absence:

* the name is a composite of several configurations and positions (`Separate` / `Clasped` /
  `Chest`) plus a location (`Desk`), so it does not by itself state that the fingers are
  *extended* at a known timestamp;
* a stage specifies a *segment*, not *which frames within it* hold the reference pose. Even with
  the stage present, a within-segment posture assertion from outside the data would be needed.

### 3.4 C — the FK route is available but circular, and is rejected

This is the route the gate singles out, and it fails for a specific and checkable reason.

The official model and its forward kinematics are available locally, so a geometric
"is this hand extended?" test could be computed. It is **not independent**, in two compounding
ways:

1. **In this model, extended IS zero.** `joint_limits` in `generic_hand_model.json` give
   `min = 0.0 rad` for `THUMB_MCP_FE`, `INDEX_PIP_FE`, `MIDDLE_PIP_FE`, `RING_PIP_FE` and
   `PINKY_PIP_FE` — zero is the *extended end of the range*, by construction. A geometric
   straightness test therefore reduces to "are these joint angles near zero", which is exactly the
   criterion the gate forbids. The gate's own warning — *"if C ultimately amounts to 'joint angle
   near zero', then it is not independent and may not be used"* — applies literally here.
2. **The FK consumes the same quantities.** Landmarks are generated from the joint angles, so the
   test would reuse the very values it is supposed to validate independently. The independence
   failure is structural, not a matter of choosing a cleverer landmark.

### 3.5 D — the only "neutral" in the pipeline is a tracker initialiser, not a pose

The pipeline does contain something named `neutral`. It is
`neutral_joint_angles()` in `UmeTrack/lib/tracker/perspective_crop.py` (lines 19–24):

```python
return joint_limits[..., 0] * lower_factor + joint_limits[..., 1] * (1 - lower_factor)
```

with `lower_factor = 0.5`. This is the **midpoint of each joint's limit range** — a synthetic
starting pose for the crop/tracker. It is not a recorded posture, not a physical reference, and by
construction it is a pose no subject was asked to hold. It is not an anchor, and it is deliberately
**not** used as one.

### 3.6 B — no annotation layer exists

The `metadata.csv` schema is `session, user, stage, start, end, side, filename, moving_hand,
held_out_user, held_out_stage, split, generalization`. `start`/`end` bound an activity segment;
they state a time, not a hand configuration. No annotation stream or event marker exists in the
release.

---

## 4. Anchor availability decision

> **ANCHOR_STATUS: `NO_INDEPENDENT_ANCHOR`**

The locally-present, pose-independent field (`stage`) specifies no posture. The one stage name that
does encode a resting position (`HandDeskSeparateClaspedChest`) is absent locally. No per-frame
label, annotation, or calibration marker exists. The FK route is present but circular.

Per the gate, when the status is `NO_INDEPENDENT_ANCHOR` the audit **stops**: no numerical-zero
measurement is performed and no reference frames are synthesised.

**`REFERENCE_ANCHOR_SPEC.md` — `NOT_CREATED`.** Creating and SHA-256 freezing a spec for an anchor
that does not exist would manufacture a prerequisite the evidence does not support.

---

## 5. Tolerance audit — no ad-hoc threshold invented

Before any threshold could be applied, the gate requires establishing whether a *pre-existing*
defensible tolerance exists. It does not.

| rule that exists | value | why it does NOT apply |
|---|---|---|
| sign consistency + magnitude (`FORENSIC_PLAN.md` §7, "Thresholds, fixed now") | `PASS` ≥ 80 % of subjects in the expected direction **and** pooled median magnitude > 2°; `WEAK` 60–80 %; `FAIL` < 60 % | governs whether a channel *moves the documented way on a DB9 physical anchor*. It is not a cross-source reference-posture residual tolerance. |
| magnitude-ratio floor | 0.15 | the frozen floor that moved `PIP3` and `DIP4` `INCONCLUSIVE → DROP`. Different statistic. |
| documentation materiality | 2 % | the rounding-materiality rule used for the BUG-006 `MCP5_f`/`PIP5` restoration. Different statistic. |

No pre-existing frozen rule bounds a **cross-source reference-anchor residual**. Accordingly the
`±2°` figure that appeared in the earlier phase's proposal was **not** adopted as a preregistered
threshold. The gate's descriptive classes (`COMPATIBLE_WITH_DB9_REFERENCE` / `POSSIBLE_ZERO_SHIFT` /
`CLEAR_ZERO_SHIFT` / `INCONCLUSIVE`) were available as the fallback, but they are **moot** here
because the anchor itself does not exist — every DOF is reported `NOT_MEASURED`.

---

## 6. Trusted-8 zero measurement

**NOT_MEASURED.** No `n`, median, mean, std, p05/p25/p75/p95, min, max or median-absolute-value is
reported for any of the eight DOFs, and no compatibility class is assigned. Reporting any of those
numbers would require reference frames, and selecting them would require the circular criterion
this gate forbids.

`artifacts/TRUSTED8_ZERO_COMPATIBILITY.json` records all 8 rows with null statistics and
`compatibility_verdict: NOT_MEASURED`, so the absence is machine-readable and cannot be mistaken
for an omission.

Ground-truth pose was never read. No predicted pose was read or produced.

---

## 7. DB9 reference comparator (context only, no comparison performed)

The authoritative artifact for the DB9 side is
`audits/db9/coordinate_audit/artifacts/DB9_SOURCE_CALIBRATION_AUDIT.json`
(SHA-256 `c186e817c1611a48c0626266268cfb41aabfec8c72f6850c7310bf04235f387e`), field
`reference_posture_per_source`, unit = *subject × movement × repetition, central phase*.

**The trusted-8 per-joint median residual at the documented DB9 reference posture (degrees):**

| DOF | DB1 (27 subj) | DB2 (40 subj) | DB5 (10 subj) |
|---|---|---|---|
| `thumb_mcp_flexion` | −0.13 | +0.26 | −2.29 |
| `thumb_ip_flexion` | +1.10 | −0.17 | +2.31 |
| `index_mcp_flexion` | +3.21 | −0.16 | +3.21 |
| `index_pip_flexion` | +4.20 | −0.75 | +2.50 |
| `middle_mcp_flexion` | +3.39 | −0.46 | +2.25 |
| `ring_mcp_flexion` | +1.44 | −0.39 | +2.11 |
| `pinky_mcp_flexion` | +4.96 | −0.31 | +3.32 |
| `pinky_pip_flexion` | +1.48 | +0.43 | +0.36 |
| **max abs** | **4.96** | **0.75** | **3.32** |

Absolute range across all 24 cells: **0.13° – 4.96°**.

This is reported for context only. Because the emg2pose side is `NOT_MEASURED`, **no comparison,
subtraction or classification was performed and no offset was fitted.**

---

## 8. Handedness scope check

The local corpus contains **both** hand sides — 15 `left` and 15 `right` recordings, from the same
single participant. Per the gate's §7 this is the "both sides present" case, so had a measurement
been possible it would have had to be reported **per hand side**, never pooled.

Because no anchor exists, no per-side measurement was made. Recorded here so that whichever future
route supplies an anchor inherits the requirement: **any reference-anchor analysis on this corpus
must be reported left and right separately.**

---

## 9. Cross-source calibration — explicitly not attempted

Nothing was fitted, aligned or matched. Specifically, none of the following was performed: scale
fit, offset fit, percentile matching, affine mapping, histogram alignment, regression, Procrustes
alignment. No non-zero offset was observed (nothing was measured), so no scientific finding about
an offset is recorded either way.

---

## 10. Firewall

| flag | value | basis |
|---|---|---|
| `DOWNSTREAM_HEAD_ACCESSED` | **NO** | no task-head module imported or executed |
| `TASK_OUTPUT_INSPECTED` | **NO** | no label, probability or margin read |
| `PREDICTED_POSE_USED` | **NO** | GT pose was never read; no inference was run |
| `MAPPING_TUNED` | **NO** | no mapping parameter touched |
| `OFFSET_FITTED` | **NO** | no offset/scale fitted |

Execution scope: 0 models trained; no server; no GPU; no full-corpus download; no inference re-run.
The only imported third-party module by the audit script is `h5py`, used to read HDF5 structure and
attributes.

---

## 11. Documentation issues

Per the gate, no authoritative public document was modified. Both issues are recorded here with
their evidence.

### DOC_ISSUE_1 — `INTERCHANGEABLE_WITH_KNOWN_CONVENTION` overstates what is established

**Finding.** In the previous phase's reconciliation artifacts the label
`INTERCHANGEABLE_WITH_KNOWN_CONVENTION` was assigned to 4 of the 8 DOFs (`IP1`, `PIP2`, `MCP4_f`,
`PIP5`) while the same artifacts state, on the same rows, that numerical zero evidence is
`NOT_ESTABLISHED` and cross-source calibration provenance is absent. The two statements pull in
opposite directions: "interchangeable" asserts substitutability, while the accompanying evidence
establishes only that the measurement is sound within DB9 and that its movement profile matches.

**Root cause.** The verb was inherited from the audit's class name (`VERIFIED NUMERICALLY
EQUIVALENT`, meaning "correct response to flexion **and** its own counterpart is the best-matching
dimension"). That is a statement about *structural correspondence on DB9's own anchors*, not about
numerical substitutability across sources.

**Scope of impact — the conflict is internal, not public.** The phrase appears **only** inside the
previous phase's gate artifacts
(`experiments/upstream_substitution/pre_substitution_reconciliation/`: `EVIDENCE_RECONCILIATION.md`,
`README.md`, and the two matrix artifacts). It does **not** appear in `README.md`,
`docs/research_status.md`, `docs/common_pose_api.md` or `docs/db9_trusted_subset.md`. Those
authoritative documents already state the conservative position:

* root `README.md`: "A joint name matching across two datasets is not sufficient evidence that their
  numeric coordinates are interchangeable."
* `docs/common_pose_api.md`: different sources' numbers "were produced by different…" processes and
  must not be "used interchangeably".

**Terminology clarification (recorded, not applied to the old artifacts).** For all 8 DOFs the
conservative and correct pair of statements is:

> `SEMANTIC_MAPPING_ESTABLISHED`
> `NUMERICAL_INTERCHANGEABILITY_NOT_ESTABLISHED`

This gate's own artifacts use the conservative wording. The old reconciliation artifacts were
**not** modified, per instruction.

### DOC_ISSUE_2 — what the 18.001 / 5.911 / 21.268 numbers actually are

**Question raised.** Are "DB9 zero is source-database dependent (18.001° / 5.911° / 21.268°)" zero
*anchor* values or *dataset-level distribution shift*?

**Answer from the artifacts: they are reference-ANCHOR residuals, aggregated over all 16
dimensions — not dataset-level distribution shift.**

Evidence:

* They live under `DB9_SOURCE_CALIBRATION_AUDIT.json` → `reference_posture_per_source` →
  `{DB1, DB2, DB5}` → `mean_abs_deg`, i.e. the *reference-posture* section of the artifact;
* the artifact's own unit string describes this section as *"subject × movement × repetition,
  central phase"* — the central phase of movement 11, which is the documented reference posture;
* the artifact's third declared interpretation rule reads: *"a reference-posture mean|angle| that is
  small in every source database means the documented calibration zero IS attained everywhere and
  is therefore not a source-specific artefact"* — it is explicitly a statement about the zero, not
  about distributions;
* the neighbouring whole-corpus `per_dimension` statistics (e.g. the DB1/DB2 medians of
  +56.22 / +4.19 for `pinky_mcp_flexion`) are the *distribution-level* numbers, and they live in a
  different field.

**Important qualifier: the three numbers are means over all 16 dimensions, and they are NOT the
trusted-8 numbers.** They are `mean |angle|` across the full canonical16 vector, so they are pulled
up by whichever dimensions sit furthest from zero at the anchor. Those dimensions are:

| source | largest anchor residuals (dimension, deg) |
|---|---|
| DB1 | `ring_dip_flexion` −9.10 · `pinky_mcp_flexion` +4.96 · `middle_dip_flexion` −4.87 · `index_pip_flexion` +4.20 · `thumb_cmc_flexion` +4.07 · `pinky_dip_flexion` −3.97 |
| DB2 | `ring_dip_flexion` +2.08 · `middle_dip_flexion` +0.83 · `index_pip_flexion` −0.75 · `middle_mcp_flexion` −0.46 · `pinky_dip_flexion` +0.44 |
| DB5 | `middle_dip_flexion` −4.79 · `pinky_dip_flexion` −4.60 · `ring_dip_flexion` −4.16 · `pinky_mcp_flexion` +3.32 · `index_mcp_flexion` +3.21 |

The dominant contributors in DB1 and DB5 are the **already-DROPped defective DIP channels** —
consistent with the forensic lane's finding that those channels do not track their joints. But the
attribution is **not exclusively** defective channels: two of the certified-trusted DOFs also appear
in the top ranks (`pinky_mcp_flexion` +4.96 in DB1, +3.32 in DB5; `index_pip_flexion` +4.20 in DB1,
+2.50 in DB5). For the trusted-8 the per-joint anchor residuals are nevertheless much smaller than
the headline means: **≤ 4.96° in DB1, ≤ 0.75° in DB2, ≤ 3.32° in DB5** (§7).

**So the accurate statement is narrower than the one in the previous phase.** It is not that the
zero *definition* differs by source, and not that the trusted-8 zero is source-dependent to the
tune of 18–21°. It is that:

1. the *documented* DB9 calibration zero is **attained in every source database** — no missing zero;
2. the *precision* with which it is attained varies by source, driven mainly by the already-DROPped
   defective channels;
3. the trusted-8 anchor residuals are **sub-5° everywhere**, so on the DB9 side alone the reference
   zero is well behaved for the DOFs this project actually uses.

**Residual limitation, stated.** `reference_posture_per_source` publishes only central tendencies
(`per_joint_median_deg`, `max_abs_joint_median_deg`). It carries **no dispersion, no per-source CI
and no per-dimension CI at the anchor**. Whether the DB1-vs-DB2 trusted-8 anchor gap is statistically
meaningful therefore **cannot be settled from this artifact**, and this gate does not claim it is.
That is a documentation/measurement gap on the DB9 side, not a cross-source finding.

---

## 12. Why `NOT_EVALUABLE_LOCALLY` is the correct outcome

The gate's third branch is the honest one here. The local mini corpus cannot independently answer
cross-source numerical-zero compatibility, for a reason that is structural rather than incidental:
**the emg2pose release contains no field that identifies a physical reference posture.** The
dataset provides activity segments, EMG, and IK-fitted joint angles — nothing that states "the hand
was in configuration X at time T". The one stage name that describes a resting position is not in
the local subset, and the only locally computable geometric route is circular by construction
because the model defines zero as the extended pose.

Neither B1 (cross-source calibration provenance) nor B3 (DB9 source-database levels) is addressed by
this round either, by design. **B2 (numerical zero interchangeability) remains open — now with a
sharper statement of why:** it is not that the measurement was skipped, it is that the anchor it
requires does not exist in the data that is available locally.

---

## 13. Reproduce

```powershell
cd common-pose\experiments\upstream_substitution\gate1_5_reference_zero
C:\emg2pose-venv\Scripts\python.exe -X utf8 scripts\audit_reference_anchor.py
```

Writes `artifacts/REFERENCE_ANCHOR_DECISION.json`,
`artifacts/TRUSTED8_ZERO_COMPATIBILITY.json` and `logs/gate1_5_stdout.txt`. Exit code 0.

---

## 14. Scientific interpretation

* **No independent physical reference anchor exists in the local emg2pose corpus.** Its only
  pose-independent field, `stage`, names a compound activity and specifies no hand posture; the one
  stage name that does encode a resting position is absent from the local 15-stage subset.
* **The geometric/FK route is unusable by construction**, because in this model the extended
  configuration *is* zero joint angle (`min = 0.0 rad` at every PIP and at `THUMB_MCP_FE`), so any
  straightness test reduces to the forbidden "angles near zero" criterion.
* **Numerical-zero interchangeability therefore remains unestablished**, and this round adds no
  evidence either way. Reporting zero statistics would have required circular frame selection.
* **No pre-existing tolerance rule was found**, so no `±2°`-style threshold was adopted; the fallback
  descriptive classes were prepared but are moot without an anchor.
* **The DB9 side of the zero is well behaved for the trusted-8** (anchor residuals ≤ 4.96° in every
  source database), and the widely quoted 18.001/5.911/21.268 numbers are reference-anchor residuals
  over all 16 dimensions — dominated by, though not exclusively attributable to, the already-DROPped
  defective channels — not trusted-8 values.
