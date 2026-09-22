# DB9 CHANNEL FORENSIC + TRUSTED-SUBSET VALIDATION — FROZEN PLAN

**Lane:** `<PROJECT_ROOT>\db9_channel_forensic_v2\`
**Branch id:** `S8-DB9-CHANNEL-FORENSIC`
**Plan version:** 1, frozen **before** any formal measurement of this lane was run
**Write discipline:** `utf-8`, `newline='\n'`, no BOM; hashed as raw bytes; never re-serialised.

---

## 0. The two questions, and nothing else

**Q1.** Are the DB9 channels that we or an independent paper suspected of being physically
broken *really* broken, or were the anomalies an artefact of our own extraction / QC?

**Q2.** After excluding untrustworthy channels using **no reference whatsoever to
classification performance**, do the remaining TRUSTED physical channels still support DB9
posture classification?

Out of scope and explicitly not done here: new dataset audits, model optimisation, open-set
rescue, and any re-research of KIN-MUS / MyoKi / KINE-ADL. No deep learning.

---

## 1. Hard rules

1. Physical validity is established **first**. Until `TRUSTED_DB9_POSE_v1.json` is frozen,
   **no classification performance of this lane may be looked at**.
2. ACC / BA / F1 may never decide a sign, an offset, a transform, a calibration correction,
   or a channel's KEEP/DROP status.
3. "This channel raises accuracy, so keep it" is forbidden.
4. No post-hoc sign flip, affine alignment, offset correction, Procrustes or learned
   coordinate transform — unless the correction is derivable from the official
   device / calibration specification. Even then, this lane **records** the problem and does
   not silently repair released data.
5. No historical result directory is modified. This lane is append-only and reads every
   other lane read-only.
6. Lightweight numpy / scipy / sklearn only. No DL.
7. Every bug is recorded in `BUGFIX_LOG.md` **before** the rerun; nothing is silently
   overwritten.
8. If segmentation cannot be validated, **STOP** and issue no channel verdict.

---

## 2. Evidence vocabulary

`[OFFICIAL]` Ninapro DB9 instructions or the DB9 paper.
`[OFFICIAL-CODE]` the published calibration formulas / gain tables.
`[LITERATURE]` the independent 2024 study.
`[EMPIRICAL]` measured by this lane from the released `.mat` files.
`[INFERENCE]` / `[UNRESOLVED]`.

`[LITERATURE]` is never promoted to `KNOWN_BAD`. The four channels the 2024 paper flags are
labelled **`LITERATURE_FLAGGED`** and this lane's job is to independently reproduce or refute
that flag.

---

## 3. Sources

| id | source | role |
|---|---|---|
| OFF-1 | `https://ninapro.hevs.ch/instructions/DB9.html` | official usage notes: Sensor 11 exclusion; DIP hand-size caveat; variable definitions |
| OFF-2 | Jarque-Bou, Atzori, Müller, Múller, Sci Data 7:12 (2020), `doi:10.1038/s41597-019-0349-2` | the dataset's own paper: acquisition, calibration protocol, **reference posture**, **sign criteria**, gain tables 2–5, sensor figure |
| OFF-3 | `order_of_angles` field inside every released `.mat` | the authoritative released channel order |
| OFF-4 | `setup_cyberglove.png` (official Fig. 1, 22-sensor layout) | sensor numbering |
| LIT-1 | "Reducing Hand Kinematics by Introducing Grasp-Oriented Intra-Finger Dependencies", Robotics 2024, 13(6), 82 | the independent flag on DIP3, DIP4, DIP5, CMC5 |

---

## 4. Data facts fixed at freeze time

Established by reconnaissance and re-derived by driver 02:

* released files: `S{N}_E{ex}_A1.mat`, `ex ∈ {1,2,3}`; **exercise 2 = Exercise B = 17 basic
  movements of the fingers/wrist**, exercise 3 = Exercise C = 23 grasping and functional
  movements; exercise 1 is present for 40 subjects, exercise 2 for 37, exercise 3 for 22.
* variables: `glove (N,22)` **raw** sensor counts, `angles (N,22)` calibrated degrees,
  `restimulus`, `rerepetition`, `stimulus`, `repetition`, `order_of_angles (22,)`.
* `glove`, `angles`, `restimulus`, `rerepetition` are **always the same length**.
  `stimulus`/`repetition` are the **pre-relabelling** vectors and are longer in some files.
  Therefore **only `restimulus × rerepetition` may be used for segmentation.**
* `angles[:,5]` (`MCP2_a`) is **all NaN** — the official Sensor-11 exclusion.
* the reference posture is **the central part of Exercise B movement 11** `[OFFICIAL]`; this
  lane verifies that against the data rather than assuming it.

---

## 5. Segmentation validation (gate)

Before any channel verdict:

1. every segment is `(restimulus, rerepetition)`; report frame counts, start/end indices;
2. verify that no two segments overlap and that the label is constant inside a segment;
3. verify the alignment of `glove`/`angles`/`restimulus`/`rerepetition` by length;
4. identify the reference segment **empirically** and check it against movement 11.

Identification rule for the reference segment, fixed before running: for every angular
channel whose exact affine form has been recovered from the raw glove, the implied reference
raw value is `S_ref = -intercept / slope`. The reference segment is the one minimising the
mean over channels of `|glove[:,col] - S_ref|`. If the minimising `restimulus` value is not
11, the reference identification is `INCONCLUSIVE` and every anchor that depends on the
reference is downgraded.

---

## 6. Transform protocol

`PHYSICAL MOVEMENT → RAW GLOVE → OFFICIAL CALIBRATION TRANSFORM → OUR RECONSTRUCTION →
RELEASED DB9 ANGLE`

1. transcribe Tables 2–5 of the DB9 paper and the official movement list verbatim;
2. **recover** the transform from the data: for every released angle column, fit
   `angle = α·glove[:,j] + β` for all `j` and record the maximum absolute residual. A
   residual at machine precision identifies an exact dependency. Report the pair, the fitted
   `α`, and the published gain side by side;
3. same for the quadratic wrist form;
4. same for the multi-sensor composite forms, searching the sensor combination with the
   published coefficient vector;
5. report `max |error|`, `median |error|`, `p95 |error|`, correlation and the bit-exactness
   rate between the reconstruction and the release;
6. if a calibration constant is unavailable, write `TRANSFORM_NOT_FULLY_REPRODUCIBLE`.
   Never guess a constant.

A published gain that disagrees with the fitted gain is a **finding**, not a licence to
adjust anything.

---

## 7. Physical anchors

All anchors come from Exercise B, whose movement list is official and unambiguous.

| anchor | movement | expected |
|---|---|---|
| `A_FIST` | B6 "Fingers flexed together in fist" | **every** MCP/PIP/DIP flexion channel rises |
| `A_EXT` | B11 central part (reference posture) | the reference, all flexion channels = 0 |
| `A_WRIST_FLEX` | B13 "Wrist flexion" | WRIST_F rises |
| `A_WRIST_EXT` | B14 "Wrist extension" | WRIST_F falls |
| `A_ABD` | B5 "Abduction of all fingers" | MCP2-3_A / MCP3-4_A / MCP4-5_A rise |
| `A_ADDUCT` | B8 "Adduction of extended fingers" | the same channels fall |

Statistics, per subject and per repetition:

* `Δraw = median(raw in the flexed segment) − median(raw in the reference segment)`;
* `Δangle` likewise;
* report N subjects, N repetitions, median and IQR of Δ, positive/negative/zero counts, and
  the **subject-level** sign-consistency rate with a Wilson 95 % interval.

Thresholds, fixed now:

| verdict | criterion |
|---|---|
| `PASS` | ≥ 80 % of subjects in the expected direction and the pooled median magnitude > 2° |
| `WEAK` | 60–80 % of subjects |
| `FAIL` | < 60 % of subjects |
| `NOT_COMPUTABLE` | fewer than 5 subjects, or the anchor is undefined for that channel |

A degenerate-anchor guard applies: a channel that never moves cannot pass, and every anchor
reports its full distribution, not only a boolean.

---

## 8. Flagged-channel verdicts (closed set)

Each of DIP3, DIP4, DIP5, CMC5 receives exactly one:

| verdict | meaning |
|---|---|
| `CASE_A_RELEASED_REPRESENTATION_PROBLEM` | the raw sensor behaves coherently but the official/released transformation produces a physically reversed or implausible angle, and our reconstruction matches the release |
| `CASE_B_SENSOR_OR_FIT_LIMITATION` | the raw sensor itself is direction-unstable across subjects, or fit/hand-size dependent, or unresponsive; not fixable by a sign flip |
| `CASE_C_PREVIOUS_QC_WRONG` | with correct segmentation both raw and calibrated angle obey the official convention, and the earlier failure traces to our extraction/QC |
| `CASE_D_DOCUMENTATION_CONFLICT` | official sources disagree on name / sign / formula / index |
| `CASE_E_INCONCLUSIVE` | evidence insufficient |

---

## 9. Sensor 11 / MCP2_a

Report the exact released status, then grep the historical lanes (`canonical16`, the DB9
adapter, `shared10`-style representations, `posture_decoder`, `bridge_audit`,
`db9_distributional_open_set`, `db9_channel_validity`, `pose_coordinate_audit`) for any
actual use of that column. If none, write `NO IMPACT`.

---

## 10. DIP hand-size hypothesis

Metadata check first. The Ninapro subject table carries **sex, height, weight and handedness
but not hand length or width**; the DB9 paper's Table 1 carries age, sex, laterality, height,
weight. If no direct hand-size variable exists, write
`HAND_SIZE_HYPOTHESIS_NOT_TESTABLE_FROM_RELEASED_METADATA` and treat height (and, as a
clearly-labelled exploratory secondary proxy only, sex) as the available substitutes.
A correlation found this way may **never** be used to repair a channel; it may only classify
the failure as universal / subset-only / size-dependent / no evidence.

---

## 11. Trusted-subset freeze

`TRUSTED_DB9_POSE_v1.json` + `TRUSTED_SUBSET_SHA256.txt` are written **before** any
classifier of this lane is executed. They contain the exact channel names, source indices,
anatomical meanings, unit, sign, zero, the exclusion list with reasons, the inconclusive list,
and the evidence hash. After that moment the subset may not change because of any
classification performance.

Per-channel verdict vocabulary: `KEEP` / `DROP` / `INCONCLUSIVE`, with
`confidence ∈ {HIGH, MEDIUM, LOW}`.

**No channel is added back to reach a target dimension.** Eight trustworthy channels beat
sixteen confused ones.

---

## 12. Posture utility test (only after the freeze)

Deliberately simple and as close as possible to the historical S3 protocol: subject-held-out
evaluation, train-fold-only normalisation, the same target posture ontology, the same
metrics. No new model family.

* **A** = the historical full / canonical representation — a *historical utility reference
  only*, never a trusted physical baseline;
* **B** = `TRUSTED_DB9_POSE_v1`.

Report Accuracy, Balanced Accuracy, Macro-F1, per-class recall, the confusion matrix and
per-subject performance, and explicitly examine class collapse, any class with unusable
recall, whether the score rests on a few subjects, and cross-subject stability.

No pass line is chosen after seeing the numbers. The questions are only: is it clearly above
chance, do all key classes retain usable recall, and is subject-held-out performance stable.

---

## 13. Removal attribution (descriptive only)

After the trusted classifier exists, and only then, remove the literature-confirmed bad, the
officially warned and the QC-failed channels one group at a time from the historical
representation and report how much of the historical discriminability they carried. This is
an explanation, not a selection procedure, and it may not modify the trusted subset.

---

## 14. Old-result impact

Each of S3 posture decoder, S5 bridge, DB9 distributional open-set, DB9 channel-validity and
coordinate audit is classified `UNCHANGED` / `NUMERICALLY_VALID_BUT_SEMANTICALLY_DOWNGRADED`
/ `NEEDS_REINTERPRETATION` / `NEEDS_RERUN` / `INVALID`. No blanket "everything is void".

---

## 15. Terminal decision (closed set)

`DB9-ADMIT` · `DB9-ADMIT-REDUCED` · `DB9-TASK-ONLY` · `DB9-REJECT` · `DB9-INCONCLUSIVE`.

---

## 16. Fail-closed

The goal is neither to clear DB9 nor to condemn it. The goal is a frozen, physically
defensible, explainable `TRUSTED_DB9_POSE_v1` that can interface with emg2pose — or an honest
statement that no such subset exists. Success is **not** keeping 0.978.

---

## 17. Reconstruction disclosure

Reconnaissance ran before this plan was written: file inventories, extraction of the official
instructions and paper, and short exploratory scripts (`probe_*.py`, `residual_matrix.py`,
`solve_transform.py`). Those are **reconnaissance, not evidence**. Every number that appears
in an artifact of this lane is recomputed by a numbered driver in `scripts/` with its stdout
captured in `logs/`, and re-derived by `scripts/99_fact_check.py`.

No admission rule, threshold or verdict rule above is a function of any measured value, and
none of them was informed by any classification performance — no classifier of this lane has
been run at the time of writing.
