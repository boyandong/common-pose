# Research status — evidence ledger

Every claim this project makes, with the artifact it came from and how strong the evidence
is. Written so that a reader can reconstruct what is established, what is provisional, and
what has been **withdrawn** — without reading a conversation or a session log.

**Evidence grades**

| grade | meaning |
|---|---|
| `EXECUTED` | a real command ran on real data and the artifact is preserved |
| `EXECUTED-PARTIAL` | ran, but on a subset of the intended population |
| `DESIGNED` | implemented and syntax-checked, not run end-to-end |
| `INFERENCE` | a reading of evidence, explicitly not a measurement |
| `WITHDRAWN` | previously claimed, now retracted — kept deliberately |

> **Read §E first if you only read one section.** The negative results are where this
> project's claims were narrowed, and they are the most informative part of the ledger.

---

## A. Completed with evidence

### A0. DB9 physical audit and the frozen trusted posture baseline

**Claim that is now closed, and only this one:** *a physically audited reduced DB9
representation has been established and it retains usable subject-held-out information
for the official 8 hand configurations.*

* `TRUSTED_DB9_POSE_v1`, 8 channels, frozen **before** any classifier ran;
  SHA-256 `e51dde6e63941fd080c84f3896a98cf50fba9e17d5f9cebe909253d5465782d1`.
* Revalidated across **all 77 DB9 participants** (DB1 27, DB2 40, DB5 10) under the
  already-frozen rules. **The 8-channel subset did not change.**
* Official posture task: Exercise B hand configurations, **movement IDs 1–8 only**.
  77 subjects, leave-one-subject-out, global identity from the archive filename,
  train-fold-only standardisation, per-segment frame cap 200.
* Trusted **BA 0.7479** (5.98× chance 0.1250), macro-F1 0.7460, no class collapse;
  historical 16-channel arm BA 0.8556. Utility loss ΔBA −0.1077.
* Evidence: `audits/db9/channel_forensic/FINAL_VALIDATION.md` and
  `audits/db9/channel_forensic/artifacts/FINAL_VALIDATION.json`.

**This closes the DB9 task source only.** Cross-dataset interoperability, upstream
substitution, emg2pose → DB9 transfer, open-set transfer, human-semantic transfer and the
Common Pose API itself all remain open (see §B, §C, §E, §F).

### A1. emg2pose baseline bring-up and joint-convention verification

`EXECUTED`. The official model was loaded and run on the official mini corpus.

| claim | method | result |
|---|---|---|
| 16 EMG channels at 2 kHz | official HDF5 attrs + shapes | verified on 30/30 files |
| 20 joint angles, official order | `constants.py` + every official HDF5 | verified |
| radians, `+` = flexion for the 15 flexion joints | `so3_exp_map(pi·ẑ)` → 180° rotation; fingertip moves toward palm at `+limit` | 15/15 verified |
| left context = 1790 samples | loaded model attribute | matches config |
| native output 50 Hz, interpolated to 2 kHz | internal rollout = `T/40` steps | verified |
| IK failures are **all-zero rows, not NaN** | official `get_ik_failures_mask` reproduces it on 30/30 files | **15.625 %** of samples |
| all 30 sessions usable | full mini-dataset pass | 61× realtime |

**Consequence carried into the interface:** unmasked MAE 16.09° versus masked 12.48° on one
held-out session. Treating a zero row as a pose is a silent, large error.
→ `docs/joint_angle_definition.md`, `src/common_pose/estimators/emg2pose/`

**Caveat:** the official mini corpus covers **one** held-out user. Every number computed on
it is within-subject, and none of the emg2pose-side numbers here is a benchmark result.

### A2. emg2pose full-dataset facts, and a split finding

`EXECUTED`. Derived from the official `metadata.csv`, MD5-confirmed against the official S3
ETag `c3f48fd51576fa7752d455f2751c8b99`.

25 253 HDF5 files · 193 users · 751 sessions · 29 stages.

> **The `split` column alone cannot support a cross-subject claim: all 158 train users also
> appear in test.** Held-out structure lives in the `generalization` axis
> (`user` / `stage` / `user_stage`). Any single "emg2pose test accuracy" reported without
> naming that axis is not interpretable.

The 431 GiB full corpus was **not** downloaded: it exceeds total local free space by
~582 GiB, and the measured China→S3 path was 1–8 KB/s (projected ~685 days). A verified
one-command server acquisition runbook was produced instead.
→ `docs/EMG2POSE_DATASET_REFERENCE.md`, `docs/SERVER_ACQUISITION_RUNBOOK.md`,
`docs/DATASET_ACCESS_DECISION.md`

### A3. DB9 segmentation validated, and the extraction trap identified

`EXECUTED` over all 99 released Exercise-B/C `.mat` files.

| relation | files where it holds |
|---|---|
| `glove == angles` | 99/99 |
| `glove == restimulus` | 99/99 |
| `glove == rerepetition` | 99/99 |
| `glove == repetition` | **75/99** |
| `glove == stimulus` | **75/99** |

`repetition` and `stimulus` are the **pre-relabelling** acquisition vectors and are 7 samples
longer in 24 of 99 files. Segmenting on them shifts every movement boundary. Anomalies under
correct segmentation: **0**.

The DB9 reference posture was **re-identified from the data** as movement 11, independently
confirming the paper's statement.
→ `audits/db9/channel_forensic/SEGMENTATION_VALIDATION.md`

### A4. DB9 per-channel physical audit and the frozen trusted subset

`EXECUTED`. Frozen plan SHA-256
`4c618b562903d0d364d03bb8a997ef6b4140bd9e09d0f2475f1b008ad80c8793`; subset frozen
**before any classifier ran**; subset SHA-256
`e51dde6e63941fd080c84f3896a98cf50fba9e17d5f9cebe909253d5465782d1`.

* **8 KEEP:** `MCP1`, `IP1`, `MCP2_f`, `PIP2`, `MCP3_f`, `MCP4_f`, `MCP5_f`, `PIP5`
* **6 DROP:** `MCP2_a`, `CMC5`, `MCP5_a`, `DIP3`, `DIP5`, `WRIST_A`
* **8 INCONCLUSIVE:** `CMC1_f`, `CMC1_a`, `PIP3`, `MCP4_a`, `PIP4`, `DIP2`, `DIP4`, `WRIST_F`

Selected by physical validity rules with **no reference to classification performance**.
→ `audits/db9/trusted_pose/`, `docs/db9_trusted_subset.md`

### A5. Physically unreliable released DB9 channels identified

`EXECUTED`. Not "noisy" — directionally wrong.

| finding | evidence |
|---|---|
| `DIP3` inverted | raw gauge and released angle both fall on an unambiguous fist, 71/77 subjects |
| `DIP5` inverted | same inversion, coherent in 32/37 |
| internal control | in the same segments MCP2_f/MCP3_f/MCP4_f/MCP5_f move positively in **37/37** |
| `CMC5` sensor collision | released column is an exact linear function (slope 0.28511 = published 0.285) of the **same raw column** as `WRIST_F` |
| transform recovered exactly | 16 of 22 released angle columns are exact affine or affine-quadratic functions of a single raw column, zero residual |
| released constants disagree with the published table | `DIP4` (2.00 vs 2.08), `WRIST_F` (0.00865779 vs 0.008), three of six `MCP4_a` polynomial coefficients |

→ `audits/db9/channel_forensic/FLAGGED_CHANNEL_FORENSICS.md`, `artifacts/VERDICTS.json`

### A6. Subject-identity collision hazard

`EXECUTED`. The in-file `subject` field is source-database-local: `S68_E2_A1.mat` reports
`subject == 1`, colliding with `S1_E2_A1.mat`. **10 collisions among the 37 Exercise-B
files.** Grouping by this field merges distinct people. This is a live leakage hazard and is
enforced against in code: `per_subject_*` metrics take opaque ids and the docs say not to
pass this field.

### A7. DB9 posture task and frozen confirmatory result

`EXECUTED`. Subject-held-out, one shared LDA per fold, train-fold-only standardisation,
central third / central 60 % of each segment, no EMG, no deep learning.

| arm | BA (hand-shape task) | BA (mixed 17-class) |
|---|---|---|
| historical `canonical16` | 0.8538 | 0.6087 |
| `TRUSTED_DB9_POSE_v1` | 0.7254 | 0.4853 |
| chance | 0.1111 | 0.0588 |

→ `experiments/db9_posture/results/`, `artifacts/POSTURE_UTILITY_POSTURE_ONLY.json`

### A8. Cross-dataset coordinate audit

`EXECUTED`. `canonical16` is **partially** valid as a cross-dataset physical API and not as a
drop-in one. DOF identities, units, positive directions, zero definitions and angle
conventions all check out; the reference posture is numerically attained in DB9 to 0.854°
mean |angle|. But per-dimension numerical disagreement is 2–40° in the medians, up to 450° in
the ranges.

* already trustworthy: `thumb_ip_flexion`, `index_pip_flexion`, `ring_mcp_flexion`,
  `pinky_pip_flexion`
* needs an explicit convention transform: `thumb_cmc_ab_adduction`
* semantically matched but numerically dataset-specific: 11 further dimensions

Load-bearing conclusion: **a shared API must carry per-channel calibration provenance, not
just the anatomical name.** → `audits/db9/coordinate_audit/`

### A9. Dataset admission audits for three external corpora

`EXECUTED` (document-level; corpora largely not obtained).

| dataset | grade | one-line reason |
|---|---|---|
| KIN-MUS UJI | **YELLOW** | order and hand resolved from the dataset's own paper; 12 of 16 canonical DOFs present; raw gauges unpublished so parity cannot be closed |
| MyoKi | **YELLOW** | raw→calibrated chain reproduced **bit-exactly** for 16 of 18 channels (max abs error 0.000e+00° over 83 267 samples); 145 GB corpus not obtained; no thumb CMC flexion channel exists |
| KINE-ADL BE-UJI | **GRAY** | guide authentic and hash-verified, but the corpus was not downloaded and 15 of 40 participant keys hide an unknown cross-experiment overlap |

Also `EXECUTED`: MyoKi's kinematic stream changes only ~35.5 times per second while being
published on a declared 2 kHz grid — a **56.26×** inflation with 98.22 % duplicated rows.
→ `audits/dataset_admission/`

### A10. HUST rejected on documented grounds

`EXECUTED`. The dataset's associated publication was **retracted** by PLOS ONE on 4 March
2016 (`doi:10.1371/journal.pone.0151685`); the published download URL returns HTTP 500; no
archived copy exists; the Dryad endpoint is behind a proof-of-work interstitial. Unit and
sign provenance were already `UNKNOWN`. **Rejected.**
→ `audits/dataset_admission/pose_api_admission/OFFICIAL_SOURCE_REFERENCES.md`

---

## B. Implemented, not fully validated

| item | status | what is missing |
|---|---|---|
| **`pose_coordinate_audit` — own corrections outstanding** | `EXECUTED-PARTIAL` | that lane's parity claim overstates what was verified (it compared an adapter against itself), and its DB1/DB2/DB5 reference-offset numbers were computed on a `repetition`-grouped corpus that does not match the frozen one. Confined to `pca_*.py`; the frozen downstream pipeline is correct. **Not repaired, not re-opened.** |
| **Bridge audit (emg2pose pose ↔ DB9 pose)** | `EXECUTED-PARTIAL` | needs reinterpretation: it compares DB9 (DIP3/DIP5 inverted, CMC5 is the wrist channel) against emg2pose, so any conclusion leaning on those channels must be re-read. Also **within one subject** — the official mini corpus is a single held-out user. |
| **KIN-MUS task-phase observability** | `EXECUTED-PARTIAL` | numbers stand for the ten columns used, but **four of the ten are not the DOFs they were named as** (see C2). Interpretation downgraded; a corrected re-run is outstanding. |
| **MyoKi admission** | `EXECUTED-PARTIAL` | parity proven on **one 41.6 s recording**. No subject-level or task-level statement is possible. The 145 GB corpus is required for every generalisation claim. |
| **KINE-ADL admission** | `EXECUTED-PARTIAL` | the corpus was not downloaded, so column order is documented but unconfirmed against real values, and the 15-of-40 subject overlap is unresolved. |
| **Common Pose adapters (MyoKi / KIN-MUS / KINE-ADL)** | `NOT IMPLEMENTED` | audited for admission; no adapter is shipped, because the corpora are not redistributable and were not all obtained. |

---

## C. Ongoing

* **C2.** A **corrected KIN-MUS representation re-run**: re-execute the already-frozen
  observability pipeline with R1's column vector changed from `[0,2,4,6,7,8,9,11,13,15]` to
  `[1,2,5,6,7,8,10,11,14,15]`. Cheapest experiment that resolves the largest open
  uncertainty; needs no new data, no GPU, and no code beyond one index vector — but the
  corrected vector must be pre-registered and hashed first.
* **C3.** EMG → pose front-end integration into the Common Pose API.
* **C4.** Upstream-substitution test on a frozen downstream task — the central open question.

---

## D. Proposed (not authorised, not run)

| idea | motivation | minimal experiment | risk |
|---|---|---|---|
| **D1. Hand-size hypothesis for the DIP failures** | DB9's own documentation names hand size as the DIP caveat, and the audit's DIP findings are consistent with a geometry/calibration limit rather than noise | correlate the surviving DIP inversion against a hand-size proxy, DB9-only, ~1 day | hand size is not recorded in the release; a proxy is a proxy |
| **D2. Separate the DIP defect's root cause** | wrong gain vs poorly-seated sensor vs sensor defect were **not distinguished** | compare recovered transform residuals across subjects against anchor reproducibility | may be unidentifiable without raw gauges, which are unpublished |
| **D3. Refine the trusted physical representation** | the current subset is 8 channels and loses 0.128 BA | re-derive on correct segmentation with additional pre-declared anchors for the 8 INCONCLUSIVE channels | must be frozen before scoring, or it is a performance-selected subset |
| **D4. `CommonPoseSubset_v2_candidate`** | 11 DOFs, tier 1 available in three external datasets | admit tier 1 only; evaluate on KIN-MUS | a **proposal** — not frozen, not run, and not the trusted subset |
| **D5. Cross-user emg2pose bridge** | the current bridge is within one subject | obtain held-out-user data from the full corpus on a server | needs the 431 GiB corpus and a server |

---

## E. Negative and withdrawn results

**Kept deliberately.** These are how the project's claims were narrowed, and several are
more informative than the positive results.

### E1. `WITHDRAWN` — "many DB9 channels fail"

An earlier lane concluded 11 of 16 canonical channels fail and issued a `DB9-DROP` verdict.
**Partly overturned.** It segmented on the pre-relabelling `repetition` vector, misaligned
with the kinematics in 24 of 99 files. Under correct segmentation, six suspects are
exonerated at ≥ 0.90 subject-level agreement.
→ `audits/db9/channel_forensic/DB9_FORENSIC_DECISION.md`

### E2. `WITHDRAWN` — `shared10_poc_v1` is ten anatomical flexion DOFs

**It is six flexion plus four relative-abduction channels.** The index vector was correct
positions for the **MOVMUS-UJI guide v2.1** column order and was then applied to an array
stored in the **KIN-MUS paper's Table 2** order; the two differ by four swapped adjacent
pairs. The numbers were unchanged — the same columns, the same arithmetic — but the physical
interpretation was wrong for four of ten, including naming a **thumb CMC abduction** channel
as thumb CMC flexion.

> This is the failure mode the whole interface design is built against: **no metric can
> detect it.** Corrected vector: `[1,2,5,6,7,8,10,11,14,15]`.
→ `audits/dataset_admission/ADMISSION_DECISION.md` §4

### E3. `WITHDRAWN` — "the subset loses only +0.0342 BA against full18"

True of those ten columns; it says **nothing** about the intended ten-DOF subset, because
the ten columns were not the intended DOFs.

### E4. `NEGATIVE` — `canonical16` is not a drop-in cross-dataset API

`PARTIALLY` valid, and the failure is not a convention mismatch: it is that the two numbers
are produced by different metrological processes. The earlier reading of a 179.7° grand-mean
offset as a possible coordinate mismatch was **relocated**: the offset is dominated by DB9's
own broken DIP calibration, and the genuinely cross-dataset disagreement is smaller and has
a different shape.

> The hypothesis is not weakened. **It is relocated.** An explicit physical pose API is only
> as good as the weakest channel's calibration provenance.

### E5. `NEGATIVE` — dropping the DIP DOF concedes a data defect

A shared API "should not advertise" the middle/ring DIPs, but that is dropping a broken
measurement, **not** resolving a convention question. Recording it as a convention fix would
misattribute the cause.
→ `audits/db9/coordinate_audit/artifacts/COMMON_POSE_API_VERDICT.json`

### E6. `NEGATIVE` — cleaning DB9's channels is actively harmful

After a DB9-only, outcome-blind channel screen, the surviving representation was **worse**,
not better:

| metric | V0 (frozen) | V1 (cleaned) |
|---|---|---|
| internal closed-set LDA | 0.9780 | 0.7694 |
| external GT UNKNOWN fraction | 0.8057 | 0.6422 |
| external human false acceptance | 0.0769 | 0.3590 |
| **DifferentialRescue** | — | **−0.2821** |

Cleaning removed useful signal along with the defective channels. The branch **stopped**
rather than adding a gate, kNN, conformal prediction, a neural open-set model, an affine
bridge, a hand-corrected DIP value, or a favourable-gesture subset.

### E7. `NEGATIVE` — emg2pose cannot supply posture labels

Adopting emg2pose as a source of posture labels was **rejected on a dataset fact**: the
official HDF5 files contain only `time`, `joint_angles` and `emg` — there is **no per-frame
gesture label**, and the only official label is the `stage` attribute, whose 29 stages are
compound activities, not single postures. `P(hand state | fist)` cannot be fitted from
emg2pose without inventing labels. Cross-checked against NEMAR's BIDS re-host.

### E8. `NEGATIVE` — HUST rejected

Paper retracted by the publisher; data unobtainable. See A10.

### E9. `NEGATIVE` — the absolute-frequency target shift was not demonstrated

The distributional open-set branch's absolute-frequency result did not hold up; the branch's
internal validation reproduced (0.9780 / 0.5930 / 0.9535 exactly) but the cleaned variant
regressed. Recorded rather than re-tuned.

---

## F. Explicitly not claimed

* universal task transfer
* universal cross-dataset numerical coordinate equivalence
* a deployment-grade or frozen API
* arbitrary downstream task support
* that any downstream head here survives upstream estimator substitution
* that DIP angles, the palmar arch, or wrist deviation are usable physical measurements in
  any dataset audited here
* that the **Common Pose API** is frozen — only the DB9 *task source* is frozen
* that freezing the DB9 baseline implies cross-dataset interoperability, upstream
  substitution, open-set transfer or human-semantic transfer

---

## G. How to check any number in this repository

1. Find the claim's artifact under `audits/` or `experiments/`.
2. Confirm the artifact's own recorded `plan_sha256` against the frozen plan in the same
   lane. The plan was hashed **before** the run.
3. For curated copies, `provenance/*.json` records the source path and both the source and
   target SHA-256.
4. Where no commit hash exists, the record says `COMMIT PENDING` — this project's research
   history predates version control, and that is stated rather than papered over.
