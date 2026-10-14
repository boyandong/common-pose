# Research status — evidence ledger

Every claim this project makes, with the artifact it came from and how strong the evidence
is. **This file is the authoritative record of whether an old artifact is still current.
The repository deliberately preserves superseded and negative artifacts; their presence
does not mean their conclusions still hold.**

**Current as of the 77-participant DB9 final validation**
(`audits/db9/channel_forensic/FINAL_VALIDATION.md`, SHA-256
`4fa700dc26d0d50f243c72372b2c1a67ee9749b4964757e529b8212839fd2b81`).

**Evidence grades**

| grade | meaning |
|---|---|
| `EXECUTED` | a real command ran on real data and the artifact is preserved |
| `SUPERSEDED` | ran and was preserved, but a later artifact replaces its conclusion |
| `INVALIDATED` | the claim is wrong; the artifact is kept as provenance |
| `WITHDRAWN` | previously claimed, now retracted |
| `INFERENCE` | a reading of evidence, explicitly not a measurement |
| `DESIGNED` | implemented and syntax-checked, not run end-to-end |

> **Read §E first if you only read one section.** The negative and superseded results are
> where this project's claims were narrowed, and they are the most informative part.

---

## A. Validated / established

### A1. A physically audited DB9 representation, revalidated at 77/77

`EXECUTED`. Frozen plan SHA-256
`4c618b562903d0d364d03bb8a997ef6b4140bd9e09d0f2475f1b008ad80c8793`; subset frozen
**before any classifier ran**; subset SHA-256
`e51dde6e63941fd080c84f3896a98cf50fba9e17d5f9cebe909253d5465782d1`.

* **8 KEEP:** `MCP1`, `IP1`, `MCP2_f`, `PIP2`, `MCP3_f`, `MCP4_f`, `MCP5_f`, `PIP5`
* **DROP:** `MCP2_a` (vendor-excluded, all-NaN), `CMC5`, `MCP5_a`, `DIP3`, `DIP5`, `WRIST_A`,
  and under the already-frozen rules now also `PIP3` and `DIP4`
* **INCONCLUSIVE:** `CMC1_f`, `CMC1_a`, `PIP4`, `DIP2`, `WRIST_F`

Selected by physical validity rules with **no reference to classification performance**.

**Coverage is 77 of 77 participants** — DB1 27, DB2 40, DB5 10. The earlier 37-participant
coverage was a **loader selection artifact**, not a property of the release: the loader
picked the protocol by filename exercise code, and DB2 stores the same 17-movement protocol
under a different exercise number. Selection now identifies the protocol **from the data**
(movement ids 1..17, reference movement 11, fist movement 6).

**77-subject revalidation under the same frozen rules: 0 of 8 KEEP channels changed.**
13 of 15 verdicts reproduce exactly. The two differences are `PIP3` and `DIP4`, both moving
`INCONCLUSIVE → DROP` because the larger sample pushes their magnitude ratio below the
frozen floor. **Both changes are strictly more conservative** — no channel moved in the
permissive direction. The trusted-8 is 77-subject stable and the file was verified
byte-identical after revalidation.

→ `audits/db9/trusted_pose/`, `audits/db9/channel_forensic/FINAL_VALIDATION.md`

### A2. The frozen downstream posture baseline (official DB9 Exercise B)

`EXECUTED`. The valid DB9 posture task is the **official hand configurations, movement ids
1–8 only**. Movement 17 is a wrist movement and is **not** a hand-shape class.

77 participants, leave-one-subject-out, global participant identity parsed from archive
identity, train-fold-only standardisation, one shared LDA per fold, radians.

| metric | historical 16-channel | `TRUSTED_DB9_POSE_v1` (8) | STRICT-PREFIX (6) |
|---|---|---|---|
| accuracy | 0.8556 | **0.7479** | 0.7482 |
| balanced accuracy | 0.8556 | **0.7479** | 0.7482 |
| macro-F1 | 0.8559 | **0.7460** | 0.7461 |
| median subject BA | 0.8744 | **0.7556** | 0.7450 |
| worst subject BA | 0.5850 | **0.5369** | 0.5356 |
| chance | 0.1250 | 0.1250 | 0.1250 |
| class collapse | no | no | no |

Utility loss (trusted − historical): ΔAcc **−0.1077**, ΔBA **−0.1077**, ΔMacroF1 **−0.1099**.
Trusted-8 is **5.98× chance**.

Trusted per-class recall: 1 **0.860** · 2 **0.691** · 3 **0.876** · 4 **0.495** ·
5 **0.903** · 6 **0.751** · 7 **0.829** · 8 **0.579**. Only class 4 falls below 0.5; its
error concentrates in class 5, and **class 4 must remain separately visible in future
transfer evaluation** rather than being absorbed into an aggregate.

**Declared deviation — a per-segment frame cap of 200.** The uncapped 77-participant frame
set is 11 843 312 frames, and DB2's recordings are roughly 20× longer than DB1/DB5, so an
uncapped pooled set would be dominated by DB2 purely by frame count. The cap keeps every
participant, movement and segment while removing that duration weighting. No channel,
model, split or threshold was changed by it.

→ `audits/db9/channel_forensic/FINAL_VALIDATION.md`, `artifacts/FINAL_VALIDATION.json`

### A3. CMC5 is a released-representation defect, established from the bytes

`EXECUTED`. Final case **`CASE_A` — released representation defect**.

* released `CMC5` = exact affine function of the same zero-based raw glove column as
  `WRIST_F` (max abs residual 5.3e-12°)
* released `WRIST_F` = exact quadratic function of that same column (residual 3.8e-11°)
* the published calibration assigns `CMC5` (palmar arch) and wrist flexion to **different**
  sensors, and the raw column the published `CMC5` mapping requires **does not feed the
  released `CMC5` angle**
* a raw-column plausibility check settles the direction: applying the published `WRIST_F`
  quadratic to the other candidate column would give an impossible ~250° wrist range

Therefore the released `CMC5` representation cannot safely be treated as the named physical
palmar-arch quantity. The final description supersedes the earlier
`CASE_B_SENSOR_OR_FIT_LIMITATION` label; `admission_status` is `DROP` either way.

**The documentation caveat remains.** The DB9 paper's own sensor subscripts conflict with
official Fig. 1 — both call sensor 11 the MCP2-3_A gauge while Fig. 1 places 11 at the
middle MCP, and Fig. 1's numbering does not match the gauge usage recovered from the
release for digits 3–5. The named sensor identity is a documentation conflict, and **the
defect does not depend on the numbering**: two published equations that use two different
sensors were computed from one and the same raw column.

**The exact software/export root cause is NOT known and is not claimed.** What is
established is the released-bytes relationship and its consequence for interpretation.

### A4. LOSO identity audit: PASS

`EXECUTED`. Identity key is the **archive slot parsed from the filename**, giving the
DB9-global participant number 1..77. The in-file `subject` field is source-database-local
(10 collisions among the 77 files; `S68_E2_A1.mat` reports `subject == 1`) and is **never**
used as a global key. 77 folds, one per global key; **maximum train/test global-key
intersection = 0**.

### A5. Physically unreliable released DB9 channels identified

`EXECUTED`. Not merely noisy — directionally wrong.

| finding | evidence |
|---|---|
| `DIP3` inverted | on an unambiguous fist the released angle falls in 35/37 subjects (77-subject ratio 0.06 / 0.92 opposed) |
| `DIP5` inverted | same inversion, 32/37 subjects (77-subject 0.19 / 0.81) |
| internal control | in the same segments every MCP and PIP flexion channel rises in 37/37 |
| transform recovered exactly | 16 of 22 released angle columns are exact affine or affine-quadratic functions of a single raw column, zero residual |
| released constants disagree with the published table | `DIP4` (2.00 vs 2.08), `WRIST_F` (0.00865779 vs 0.008), three of six `MCP4_a` coefficients |

### A6. Subject-identity collision hazard

`EXECUTED`. The in-file `subject` field merges distinct people. Enforced against in code:
`per_subject_*` metrics take opaque ids and the documentation forbids passing this field.

### A7. emg2pose interface facts

`EXECUTED`. 16 sEMG channels at 2 kHz; 20 joint angles in the official order; radians with
`+` = flexion for the 15 flexion joints; left context 1790 samples; native 50 Hz output
linearly interpolated to 2 kHz; **IK failures encoded as all-zero rows, not NaN —
15.6 % of the official mini corpus**, giving 16.09° vs 12.48° MAE unmasked versus masked.

The official mini corpus covers **one** held-out user, so nothing derived from it is a
cross-user benchmark.

### A8. Cross-dataset coordinate audit

`EXECUTED`. `canonical16` is **partially** valid as a cross-dataset physical API and not as
a drop-in one. DOF identities, units, positive directions, zero definitions and angle
conventions all check out; DB9's reference posture is numerically attained to 0.854° mean
|angle|. But per-dimension numerical disagreement is 2–40° in the medians and up to 450° in
the ranges.

Load-bearing conclusion: **a shared API must carry per-channel calibration provenance, not
just the anatomical name.** → `audits/db9/coordinate_audit/`

### A9. Dataset admission audits

`EXECUTED`. KIN-MUS UJI **YELLOW** (order and hand resolved from the dataset's own paper;
12 of 16 canonical DOFs present; raw gauges unpublished so parity cannot be closed). MyoKi
**YELLOW** (bit-exact raw→calibrated chain for 16 of 18 channels; corpus not obtained; no
thumb CMC flexion channel exists). KINE-ADL BE-UJI **GRAY** (guide hash-verified; corpus not
downloaded; 15 of 40 participant keys hide an unknown cross-experiment overlap).
**HUST rejected**: paper retracted by the publisher, download URL returns HTTP 500, no
archived copy. Also `EXECUTED`: MyoKi publishes its kinematic stream on a 2 kHz grid while
it changes ~35.5 times per second — a **56.26×** inflation.

### A10. Bug-006 sensitivity: robustness report

`EXECUTED`. `MCP5_f` and `PIP5` had been restored under a post-hoc 2 % documentation-rounding
materiality rule. The STRICT-PREFIX 6-channel subset (removing both) gives BA **0.7482**
versus TRUSTED-8 **0.7479** — ΔBA **+0.0003**. The trusted utility conclusion does not
depend materially on those two restored channels. Both also pass the physical anchor at
77/77. **This is a robustness report only and changes no channel verdict.**

---

## B. In progress

* **B1.** Establish an independent source mapping for the same trusted physical DOFs
  (units, signs, physical reference, validity, calibration provenance) **without tuning that
  mapping using downstream task performance**.
* **B2.** Test the frozen downstream head under upstream substitution.
* **B3.** Separate interface / domain-shift failure from pose-estimation failure.
* **B4.** A corrected KIN-MUS representation re-run using the intended index vector
  `[1,2,5,6,7,8,10,11,14,15]` (see E2). Not authorised, not run.

**Not implemented:** adapters for MyoKi, KIN-MUS or KINE-ADL. Those corpora were audited for
admission but are not redistributable and were not all obtained.

---

## C. Proposed (not authorised, not run)

| idea | motivation | minimal experiment | risk |
|---|---|---|---|
| separate the DIP defect's root cause | wrong gain vs poorly-seated sensor vs sensor defect were **not** distinguished | compare recovered transform residuals across participants against anchor reproducibility | may be unidentifiable without raw gauges, which are unpublished |
| hand-size hypothesis for the DIP failures | DB9's own documentation names hand size as the DIP caveat | correlate the surviving DIP inversion against a hand-size proxy | hand size is not recorded in the release; a proxy is a proxy |
| `CommonPoseSubset_v2_candidate` | 11 DOFs from the dataset-admission lane, tier 1 available in three external datasets | admit tier 1 only; evaluate on KIN-MUS | a **proposal** — not frozen, not run, and not the trusted subset |
| cross-user emg2pose bridge | the current bridge is within one participant | obtain held-out-user data from the full corpus on a server | needs the 431 GiB corpus and a server |

---

## D. Negative results that remain visible

Retained deliberately. These define what the project is currently allowed to claim.

### D1. `NEGATIVE` — distributional / open-set transfer from DB9 did not bridge to emg2pose

Simple DB9 distribution/open-set support transfer **did not provide a reliable bridge** to
natural emg2pose pose. The branch reproduced its own frozen internal numbers exactly and
then failed externally (external ground-truth UNKNOWN fraction 0.8057 → 0.6422).

### D2. `NEGATIVE` — channel cleaning did not rescue that branch, and was actively harmful

| metric | V0 (frozen) | V1 (cleaned) |
|---|---|---|
| internal closed-set LDA | 0.9780 | 0.7694 |
| external GT UNKNOWN fraction | 0.8057 | 0.6422 |
| external human false acceptance | 0.0769 | **0.3590** |

DifferentialRescue **−0.2821**. Cleaning removed useful signal along with the defective
channels, and **increased false acceptance**. The branch **stopped** rather than adding a
gate, kNN, conformal prediction, a neural open-set model, an affine bridge, a hand-corrected
DIP value, or a favourable-gesture subset.

### D3. `NEGATIVE` — KIN-MUS phase was not a clean single-frame pose task

The phase-observability branch established that single-frame information over the ten
frozen columns is not sufficient, and that temporal windows add measurable information. Its
physical *interpretation* is separately downgraded — see E2.

### D4. `NEGATIVE` — emg2pose cannot supply posture labels

Adopting emg2pose as a source of posture labels was rejected on a dataset fact: the official
HDF5 files carry only `time`, `joint_angles` and `emg`, with **no per-frame gesture label**;
the only official label is the `stage` attribute, whose 29 stages are compound activities.
`P(hand state | fist)` cannot be fitted from emg2pose without inventing labels.

### D5. `NEGATIVE` — HUST rejected

Paper retracted; data unobtainable. See A9.

### D6. `NEGATIVE / NOT ESTABLISHED` — the absolute-frequency target shift

The distributional open-set branch's absolute-frequency result did not hold up. Recorded
rather than re-tuned.

---

## E. Invalidated / superseded claims

### E1. `SUPERSEDED` — "the trusted DB9 subset is provisional because only 37 subjects were validated"

**Superseded by the 77/77 validation.** The 37-participant coverage was a **loader artifact**:
the loader selected Exercise B by filename exercise code `E2`, but DB1 and DB5 ship the
17-movement protocol as `_E2_` while DB2 ships the same protocol as `_E1_`, so DB2's 40 files
were never opened. Selection by **data content** recovered the full cohort. The subset file
was verified byte-identical after revalidation and remains
`e51dde6e63941fd080c84f3896a98cf50fba9e17d5f9cebe909253d5465782d1`.

*Artifact note:* `DB9_FORENSIC_DECISION.md`, `FLAGGED_CHANNEL_FORENSICS.md` and
`TRUSTED_DB9_POSE_v1.json` still carry the 37-participant figures and the `n_subjects: 37`
field, because they are frozen artifacts of the run that produced them and are preserved
unmodified. `FINAL_VALIDATION.md` is the addendum that supersedes those coverage statements.

### E2. `INVALIDATED` — "`shared10_poc_v1` contains the intended ten anatomical DOFs"

**Withdrawn.** Four of the ten columns were assigned semantics from a **different UJI column
order** (the MOVMUS-UJI guide v2.1 order) and then applied to an array stored in the KIN-MUS
paper's Table 2 order. The numbers were unchanged — same columns, same arithmetic — but the
physical interpretation was wrong for four of ten, including naming a **thumb CMC abduction**
channel as thumb CMC flexion. Corrected vector: `[1,2,5,6,7,8,10,11,14,15]`.

> This is the failure mode the interface design is built against: **no metric can detect it.**

### E3. `WITHDRAWN` — "the Common Pose subset loses only +0.0342 BA against full18"

True of those ten columns; it says **nothing** about the intended ten-DOF subset, because
those columns were not the intended DOFs.

### E4. `PARTIALLY OVERTURNED` — "11/16 candidate DB9 channels fail, therefore DB9 should be dropped"

The earlier screen used segmentation keyed to the **pre-relabelling `repetition` vector**,
which is length-misaligned with the kinematics in **24 of 99** released files, so every
movement boundary was shifted. Under correct `restimulus × rerepetition` segmentation, six
of the earlier suspects are exonerated at ≥ 0.90 subject-level agreement while five findings
are confirmed or newly established.

> The physiology never changed; the index did.

### E5. `SUPERSEDED` — old DB1/DB2/DB5 large reference-offset conclusions

The coordinate audit's reported per-source-database reference means (DB1 18.0° / DB2 5.9° /
DB5 21.3°) were computed on a `repetition`-grouped corpus that does not match the frozen one.
**Not current evidence.** The audit's parity claim also overstated what was verified — it
compared an adapter against itself. Its own outstanding corrections were **not repaired and
not re-opened** by later lanes.

### E6. `INVALIDATED` — the in-file `subject` field as a global participant key

Source-database-local; 10 collisions among the 77 Exercise-B files. Any grouping by it
merges distinct people. See A4.

### E7. `INVALIDATED AS A PRIMARY ENDPOINT` — the formal S6 human semantic endpoint

Model unblinding occurred at an **interim 200/396 checkpoint** before the preregistered
human-only stage completed, so the pre-registration's ordering requirement was not met.
**No completed S6 semantic endpoint is reported.** Any later full-set figure would be a
post-unblinding secondary analysis. See
`audits/human_semantic_validation/README.md` §4.

### E8. `NEGATIVE` — `canonical16` is not a proven drop-in cross-dataset coordinate system

`PARTIALLY` valid, and the failure is not a convention mismatch: the two numbers are produced
by different metrological processes. An earlier reading of a 179.7° grand-mean offset as a
possible coordinate mismatch was **relocated** — the offset is dominated by DB9's own broken
DIP calibration, and the genuinely cross-dataset disagreement is smaller and differently
shaped. Dropping the DIP DOF concedes a **data defect**, not a convention question.

---

## F. Explicitly not yet demonstrated

Common Pose has **not** established:

* that a frozen downstream task head survives **substitution of the upstream pose estimator**;
* **cross-dataset numerical coordinate equivalence**;
* **arbitrary or universal downstream task reuse**;
* **reliable cross-dataset open-set rejection**;
* a **deployment-grade or frozen Common Pose API** — the container is explicitly evolving,
  and the frozen artifact in this project is the DB9 trusted channel subset, not the API;
* **multi-user end-to-end EMG → Common Pose → task generalisation**;
* a **universal hand-state interface**.

The software infrastructure should not be read as evidence for any of these.

---

## G. How to check any number in this repository

1. Find the claim's artifact under `audits/` or `experiments/`.
2. Confirm the artifact's recorded `plan_sha256` against the frozen plan in the same lane.
   The plan was hashed **before** the run.
3. For curated copies, `provenance/CURATION_MANIFEST.json` records the source path and both
   the source and target SHA-256, plus whether curation altered the bytes.
4. Where no commit hash exists the record says `COMMIT PENDING` — the research history
   predates version control, and that is stated rather than papered over.
5. **If an artifact and this ledger disagree about current status, this ledger is
   authoritative and the artifact is historical.**
