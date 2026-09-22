# Session 3 report — DB9 → canonical16 posture identifiability

**Question (frozen by the research lead).**

> Can hand posture be recognized across unseen subjects using only the shared
> 16-dimensional hand kinematic representation?

**Answer: yes, for the six exercise-B hand configurations that canonical16 can
describe — 98.36 % ± 3.90 % leave-one-subject-out accuracy over all 22 subjects
(6-class chance = 16.67 %).** The result survives five independent attempts to
falsify it (§9.3). It says nothing yet about the 23 object grasps in exercise C,
about crossed wrist movements, or about the cross-dataset chain. The one
blocking sign question is now RESOLVED and frozen (§16.1).

Everything below is `[REAL-FILE]` (measured from the official archives) unless
tagged otherwise. No deep model was trained. No emg2pose stage label was used.
canonical18 was not added. FRL was not used.

---

## 1. DB9 real-file schema audit

`docs/DB9_FILE_AUDIT.json` — **44 `.mat` files, 22 archive slots** (subjects
1–16 from DB1, 68–73 from DB5), **6 504 215 samples**.

| property | value |
|---|---|
| `angles` shape | `(N, 22)` float64 |
| `order_of_angles` | present in **all** files; **1 distinct vocabulary**; matches the official table exactly |
| `glove` | `(N, 22)` uncalibrated, present |
| `restimulus` | 0–17 in exercise B files, 0–23 in exercise C files |
| `rerepetition` | 0–6 |
| **repetitions per movement** | **6**, counted from `rerepetition` — not taken from documentation |
| `inclin` (inclinometer) | **absent from every file** |
| NaN / Inf | exactly one all-NaN column, `6:MCP2_a`, identical across all 44 files; **zero** non-finite values in any live channel |
| sampling | 85 180–297 209 samples/file; nominal 100 Hz (DB1) or 200 Hz (DB5) |
| hand side | **no side field exists**; the protocol instructed all participants to use the **right hand** `[OFFICIAL-DOC]` |

### 1.1 Two source-identity defects found and handled

* **Slots 68–73 record `subject = 1…6`**, because DB5 restarted its own
  numbering. Using that field verbatim would have merged six DB5 participants
  with six DB1 participants and silently made the cross-subject claim partly
  within-subject. **Authority is the DB9 archive slot**; the in-file field is
  recorded for audit only, and a corpus-level injectivity check enforces it.
* **Slot 69 records `subject = 11`** where the source numbering predicts 2 —
  an inconsistency in the official metadata. Reported, not "repaired"; the slot
  stays unambiguous.

---

## 2. Exact DB9 → canonical16 mapping

Full document: **`docs/DB9_CANONICAL16_MAPPING.md`**. Machine-readable:
`representation/db9_canonical16_schema.json`. Adapter:
`representation/db9_to_canonical16.py`.

Resolved DB9 column vector, selected **by channel name** (proven not to be a
positional prefix by a test):

```
canonical16  ->  DB9 cols [0, 1, 2, 3, 4, 6, 16, 7, 8, 17, 9, 11, 18, 13, 15, 19]
canonical12_noDIP -> [0, 1, 2, 3, 4, 6, 7, 8, 9, 11, 13, 15]
```

| canonical | DB9 channel | col | canonical | DB9 channel | col |
|---|---|---|---|---|---|
| `thumb_cmc_flexion` | `CMC1_f` | 0 | `middle_dip_flexion` | `DIP3` | 17 |
| `thumb_cmc_ab_adduction` | `CMC1_a` | 1 | `ring_mcp_flexion` | `MCP4_f` | 9 |
| `thumb_mcp_flexion` | `MCP1` | 2 | `ring_pip_flexion` | `PIP4` | 11 |
| `thumb_ip_flexion` | `IP1` | 3 | `ring_dip_flexion` | `DIP4` | 18 |
| `index_mcp_flexion` | `MCP2_f` | 4 | `pinky_mcp_flexion` | `MCP5_f` | 13 |
| `index_pip_flexion` | `PIP2` | 6 | `pinky_pip_flexion` | `PIP5` | 15 |
| `index_dip_flexion` | `DIP2` | 16 | `pinky_dip_flexion` | `DIP5` | 19 |

The two datasets index the same anatomy differently — `index_dip_flexion` is
emg2pose #7 but DB9 column 16 — so a 22→20 or 20→16 index mapping is invalid.

---

## 3. Units, signs, zero/reference

| | DB9 | canonical16 |
|---|---|---|
| unit | **degrees** `[REAL-FILE]` (+ converging documented evidence) | radians |
| conversion | explicit and named (`DEGREES_PER_RADIAN`) | — |
| 15 flexion DOF | **Flexion + / Extension −** (DB9 paper Table 6) `[OFFICIAL-DOC]` | positive = flexion — **agrees** |
| thumb CMC ab/adduction | **Abduction + / Adduction −** (Table 6) | polarity **FROZEN: DB9 negated** (§4, §16.1) |
| zero | reference posture = "hand resting on the table with the fingers closed together and extended" `[OFFICIAL-DOC]` | UmeTrack rest pose |

**Independent data-side confirmation of the zero:** averaging `|canonical16|`
over the central third of every repetition, the exercise-B movement closest to
all-zero is *Wrist supination (axis: little finger)* at **0.059 rad**, versus
**1.183 rad** for the fist. Wrist-rotation movements have almost no
finger-flexion content, so their central thirds land on the finger zero — exactly
what the documented reference predicts.

No clipping, no per-subject centring, no offset correction and no normalisation
are applied in the adapter; each is test-enforced. The only sign change is the
**single frozen, pre-registered flip** of `thumb_cmc_ab_adduction` (§16.1) —
every other variable keeps its DB9 polarity.

---

## 4. DB9 vs UmeTrack zero-pose compatibility check

`docs/DB9_EMG2POSE_ZERO_COMPATIBILITY.json`. Derived from geometry only — no
offset was ever tuned against classification accuracy.

**The 15 flexion DOF share a compatible zero.** Forward kinematics of the
official UmeTrack model at all-zero joint angles gives finger-chain interior
angles of 174.9–179.5° (proximal) and 166.7–172.8° (distal), i.e. an **extended**
hand; and the zero pose sits **1 %** of the way from the most-closed to the
most-spread pose reachable with the official ab/adduction limits, i.e. **fingers
together**. That is the same configuration DB9 calibrates as zero.
**No offset is required.**

A side result worth recording: this check had to discover the ab/adduction
polarity first, because driving all four MCP AA DOF to the *same* sign does not
produce a spread hand. The sign that opens the finger is **positive for the
index and negative for middle, ring and pinky**, confirming the frozen
contract's per-finger-polarity warning on real geometry.

**`thumb_cmc_ab_adduction`**thumb_cmc_ab_adduction — RESOLVED AND FROZEN.** See §16.1 for the
full-range sweep that supersedes the ±0.3 rad probe originally written here.
Positive emg2pose THUMB_CMC_AA both closes the first web space (thumb↔index tip
153.90 → 93.57) and brings the thumb down toward the palm plane (elevation
+45.70° → +8.94°), so the in-plane and out-of-plane criteria AGREE that positive
is adduction, while DB9 documents CMC1_A as abduction-positive. DB9 is therefore
**sign-flipped** in the DB9 adapter (FROZEN_DB9_SIGN), and zero alignment was
verified separately, making it a pure sign flip with no offset. Session 2’s
emg2pose adapter is untouched. The earlier claim that the two criteria disagree
came from using the thumb tip’s displacement-vector palm-normal component instead
of the elevation angle; elevation is non-monotonic over the range.

---

## 5. Selected primary posture classes and rationale

canonical16 deliberately removes the four non-thumb MCP ab/adduction DOF, so
classes whose defining information is inter-finger spread cannot be silently
treated as ordinary canonical16 classes.

**Pre-registered before test evaluation** (`results.json → pre_registration`):

| role | movements |
|---|---|
| **Primary vocabulary (6)** | B1 *Thumb up*, B2 *Extension of index and middle, flexion of the others*, B3 *Flexion of ring and little finger, extension of the others*, B4 *Thumb opposing base of little finger*, B6 *Fingers flexed together / fist*, B7 *Pointing index* |
| **Negative control (2)** | B5 *Abduction of all fingers*, B8 *Adduction of extended fingers* — both defined by the removed DOF; option **B**, kept as an explicit expected-hard control rather than silently excluded |
| Excluded by design | B9–B17 (wrist/forearm — the protocol reserves those), and all 23 exercise-C object grasps |

**The pre-registration was wrong, and the diagnostics say why.** B5 vs B8 scored
**98.9 % LOSO**, not chance. Per-channel profiling shows they differ chiefly in
**DIP extension** (B5: −62°/−98°/−49° on pinky/ring/middle DIP versus B8:
+8°/+12°/+15°; |Cohen's d| ≈ 3.3) and in **thumb CMC ab/adduction** (B5 +9.5° vs
B8 −2.7°, |d| = 2.9) — none of which are the removed spread DOF. So the two
movements are separated by wrist-finger extension and thumb posture that
canonical16 *does* contain. Recorded as a corrected expectation, not quietly
dropped.

---

## 6. Subjects and independent repetitions per class

| | |
|---|---|
| subjects | **22** (DB1: 1–16, DB5: 68–73) |
| repetitions per (subject, movement) | **6**, from `rerepetition` |
| representative postures | 2 244 (= 22 × 17 movements × 6) |
| **primary 6-class samples** | **792** (= 22 × 6 × 6) |
| per class | 132 (18 in the test split) |
| unit of analysis | **subject × movement × repetition** — published frames are *not* independent (the glove ran at <25 Hz and DB9 super-sampled it), so frame counts are never reported as sample counts |
| test split | 108 repetitions (3 subjects × 6 movements × 6 reps) |

Movement order was not randomised, so repetitions were isolated (nothing from a
neighbouring movement is used), absolute experiment time is not a feature, and
movement order/index is never a feature.

---

## 7. Frozen subject split

Written to disk (`data/db9_posture16/subject_split.json`) **before** the test set
was evaluated; stratified by source database; ~70/15/15.

| split | subjects | n |
|---|---|---|
| train | 1, 2, 3, 4, 5, 7, 8, 9, 11, 14, 15, 16, 69, 71, 72, 73 | 16 |
| val | 6, 13, 70 | 3 |
| test | **10, 12, 68** | 3 |

Asserted disjoint. No random frame split. Mapping, class set, preprocessing and
model choices were all frozen before test evaluation.

---

## 8. Extraction of the representative posture

For every (subject, movement, repetition):

1. take the labelled interval (`restimulus == label`, `rerepetition == repetition`);
2. split it into **thirds**;
3. use the **central third** — the DB9 paper states the central parts are "the
   ones that are statistically expected to correspond the most to the target
   posture", the first third being the reach and the last the return;
4. take the **median** of that central third as the one representative
   canonical16 posture.

The segmentation is fixed at exactly one third and was never tuned per class or
against accuracy. **Full repetition trajectories are preserved** for future work
in `repetition_trajectories.npz` and are **not** used by the classifier. The
"reach-in / return" artefact is not hypothetical: it is the cause of the dominant
error in §12.

---

## 9. canonical16 classification results

### 9.1 Frozen test split (3 subjects, n = 108)

Preprocessing (z-score) fitted on TRAIN subjects only. **No per-subject
normalisation of test subjects** — that would require subject-specific
calibration a deployed decoder would not have.

| model | z-scored | raw (degrees-as-radians) |
|---|---|---|
| nearest centroid (Euclidean) | **1.0000** | 0.8889 |
| nearest centroid (Mahalanobis) | 0.9815 | 0.9815 |
| LDA | 0.9907 | 0.9907 |
| logistic regression | 0.9907 | **1.0000** |
| random forest | 0.9537 | 0.9537 |
| majority class / uniform chance | 0.1667 | — |

Validation split (reference only): 0.9907–1.0000.

### 9.2 Leave-one-subject-out — the headline number

Three test subjects is a small sample, so the claim rests on LOSO over **all 22
subjects**, each held out exactly once:

| representation | LOSO accuracy |
|---|---|
| **canonical16** | **0.9836 ± 0.0390** |
| canonical12_noDIP | 0.9798 ± 0.0412 |

Per-class LOSO recall (canonical16): *Thumb up* 0.992, *Extension of index and
middle…* 0.977, *Flexion of ring and little…* 1.000, *Thumb opposing base of
little finger* 1.000, *fist* **0.932**, *Pointing index* 1.000. Worst subject
0.83; 19 of 22 subjects at 1.00.

### 9.3 Falsification attempts — all passed

| probe | result | reading |
|---|---|---|
| **D1** leave-one-subject-out | 0.9836 ± 0.0390 over 22 subjects | not an artefact of the 3-subject test set |
| **D2** single-channel LOSO | best channel `index_pip_flexion` 0.4482; worst 0.1957 | the task is genuinely 16-dimensional; no one channel carries it |
| **D3/D6** session-drift confound | drift-corrected LOSO **0.9672** (Δ −0.0164) | removing drift entirely costs 1.6 pp — drift is **not** the driver |
| **D7** drift-only predictor | 0.4419 ± 0.1178 | bounds the session-time shortcut; real and non-trivial, but far below 0.98 |
| **D4** label permutation | 0.1699 ± 0.0143 vs chance 0.1667 | no leakage through the pipeline |

The drift probes matter because the DB9 protocol was **not randomised**: movement
identity is confounded with position in the session, and the rest posture does
drift measurably (median drift ≈ 45 % of the between-movement spread). That
confound is real — a classifier reading only drift reaches 44 % — but it explains
at most a small fraction of the 98 %.

### 9.4 Confidence and probability behaviour

Full evidence: `data/db9_posture16/confidence_report.json`. The protocol asks for
"confidence/probability where supported"; every model in the grid exposes
`predict_proba`, so the stored posteriors were turned into separation,
selective-prediction and calibration numbers.

Pooled LOSO (n = 792, the reliable basis):

| quantity | value |
|---|---|
| accuracy | 0.9836 |
| mean max-posterior, all | 0.9952 |
| mean max-posterior when **correct** | 0.9961 |
| mean max-posterior when **wrong** | 0.9386 |
| separation gap | 0.0576 |
| **expected calibration error** (10 bins) | **0.0164** |

**The decoder can say "unknown" rather than guess.** Answering only when the max
posterior ≥ 0.957 covers **97.3 %** of inputs at **99.22 %** accuracy on the
answered set, flagging 2.7 % as unknown. Exact rules: `max posterior >= t, else
"unknown"`.

**A caution the accuracy column alone hides.** On the frozen test split the
*most accurate* model is nearest-centroid with z-scoring (100 %), and it is also
by far the *worst calibrated* (ECE **0.628**, mean confidence 0.372 on correct
predictions). Its softmax-over-distance scores are rank-correct but not
probabilities. LDA reaches 99.07 % with ECE **0.0081**. So for any downstream use
that consumes a probability, **the model with the best accuracy is not the right
one** — this is a concrete argument for reporting calibrated likelihoods rather
than picking the top accuracy row.

---

## 10. canonical12_noDIP control results

Pre-registered robustness control for DB9's documented caveat that DIP sensors
degrade for subjects whose hands fit the glove poorly.

| | canonical16 | canonical12_noDIP | Δ |
|---|---|---|---|
| **LOSO overall** | 0.9836 | 0.9798 | **+0.0038** |
| frozen test, nearest centroid | 1.0000 | 0.9907 | +0.0093 |
| frozen test, LDA | 0.9907 | 0.9815 | +0.0093 |
| frozen test, random forest | 0.9537 | 0.9815 | −0.0278 |
| frozen test, NCM raw | 0.8889 | 0.9074 | −0.0185 |

**Per-class LOSO Δ** (canonical16 − noDIP): *Thumb up* +0.008, *Extension of index
and middle* +0.008, *Pointing index* +0.008; the other three classes **0.000**.

**Per-subject Δ**: 20 of 22 subjects differ by **0.000**; only s10 (+0.056) and
s16 (+0.028) gain anything.

> **Reading: the four DIP channels contribute essentially nothing (≈0.4 pp). The
> result does not rest on the least reliable sensors.** This is *not* evidence
> that canonical16 is superior — the differences are far too small to support
> that, and in two of five test models the noDIP control is actually better.

---

## 11. Confusion matrix

Figures: `figures/posture16/confusion__primary6__canonical16__test.png` and
`..._canonical12_noDIP_test.png`; per-class bars alongside them.

Pooled LOSO confusion (all 22 subjects, 792 repetitions, 13 errors) in
`data/db9_posture16/phase7_loso_confusion.json`:

```
           1     2     3     4     6     7
    1    131     0     0     0     1     0
    2      0   129     0     2     1     0
    3      0     0   132     0     0     0
    4      0     0     0   132     0     0
    6      9     0     0     0   123     0
    7      0     0     0     0     0   132
```

---

## 12. Angle-unidentifiable / canonical16-unidentifiable posture pairs

**One dominant confusion: fist (B6) → *Thumb up* (B1), 9 of 13 errors = 6.8 % of
all fists.** The remaining 4 errors are scattered (B2→B4 ×2, B2→B6 ×1,
B1→B6 ×1). Everything else is perfect.

Attribution against the four protocol categories:

| candidate | verdict |
|---|---|
| **1. canonical16 intentionally missing a needed DOF** | **No.** A fist and a thumb-up differ mainly in *thumb* posture and finger flexion — all of which canonical16 contains, and which no ab/adduction DOF would add. |
| **2. DB9 sensor / calibration / labelling limitation** | **Primary cause.** The DB9 paper states directly: *"When the fist is closed (exercise B, movement 6) there is no full correspondence between the original movement and the computed average model. The central part of the movement may in a few cases involve parts of the reaching phase, as well as of the phase in which the hand gets back to the rest position."* The central third is therefore not always the held fist for this one movement. |
| **3. two postures genuinely having similar kinematics** | Contributory. In a relaxed fist the thumb is not tightly wrapped, so the thumb channels can resemble a thumb-up. |
| **4. classifier limitation** | **No.** The error persists across nearest-centroid, LDA, logistic regression and random forest, at 792 samples and 16 clean features. |

> **Scientific finding, recorded rather than engineered away:** canonical16 is not
> the limiting factor for the fist/thumb-up pair; the DB9 label-to-posture
> correspondence for movement 6 is. Any downstream claim about fist recognition
> should quote this caveat. No architecture change was made to rescue it.

No posture pair was found for which canonical16 is *fundamentally* unable to
separate the postures — with the caveat that B5 and B8, the pair pre-registered
as expected-hard, turned out to be separable after all (§5), so the
representation was never actually stress-tested on pure inter-finger spread.

---

## 13. Unresolved risks

1. ~~**Thumb CMC ab/adduction polarity (§4) — the blocker for the cross-dataset
   chain.**~~ **RESOLVED AND FROZEN — see §16.** The sign question was settled
   from geometry over the DOF's full official limit range and the zero was
   verified separately, so DB9's `CMC1_A` is now sign-flipped in the DB9 adapter
   (`FROZEN_DB9_SIGN`). The residual risk is no longer the sign but the
   *magnitude* semantics of the pairing, which `canonical15_noThumbAA` bounds.
2. **Cross-dataset validity is NOT claimed.** All results here are DB9-only and
   within a single measurement modality. Zero-pose compatibility was verified
   for the 15 flexion DOF, but the mapping has never been exercised end-to-end.
3. **Small test split.** 3 test subjects (108 repetitions) is thin; the LOSO
   figure over 22 subjects is the number to quote.
4. **Session drift is real.** The rest posture drifts by ≈45 % of the
   between-movement spread over a session, and movement order is fixed. A
   drift-only classifier reaches 44 %. It does not explain this result, but any
   *frame-level* or *time-resolved* analysis on DB9 must control for it.
5. **Only DB1 and DB5 subjects are present.** DB2 (subjects 28–67, ~171 MB each)
   was not downloaded; DB2 contributes 40 of the 77 DB9 participants and uses a
   2 kHz super-sampled rate. Source-database balance is therefore uneven and
   DB2-specific behaviour is untested.
6. **Normalisation matters and is an open choice.** The frozen test set moves
   between 0.889 and 1.000 depending on z-scoring, and z-scoring helped most
   models. It was fitted on train subjects only, as required — but the
   representation's sensitivity to it is worth noting.
7. **Exercise-C grasps are untested.** 23 of the 40 DB9 movements, including 10
   that differ chiefly by the object held, were not evaluated.
8. **`stimulus`/`repetition` are 7 samples longer than `angles`** in exercise-C
   files. Harmless here (only `restimulus`/`rerepetition` are used) but it is an
   official-release inconsistency.

---

## 14. Paths of all code, schemas and reports

**Deliverables**

| path | contents |
|---|---|
| `docs/DB9_CANONICAL16_MAPPING.md` | exact mapping, units/signs/zero, compatibility result |
| `representation/db9_to_canonical16.py` | the DB9 → canonical16 adapter (single source of truth) |
| `representation/db9_canonical16_schema.json` | generated schema |
| `representation/tests/test_db9_to_canonical16.py` | 18 tests, all passing |
| `docs/DB9_FILE_AUDIT.json` | PHASE 0 real-file audit |
| `docs/DB9_EMG2POSE_ZERO_COMPATIBILITY.json` | PHASE 1B zero/axis evidence |
| `posture_decoder/report.md` | this report |

**Code**

| path | role |
|---|---|
| `posture_decoder/tools/fetch_db9.py` | resumable parallel downloader (drives curl) |
| `posture_decoder/tools/unpack_db9.py` | CRC-verified extraction + manifest |
| `posture_decoder/tools/inspect_db9.py` | per-file inspector |
| `posture_decoder/tools/audit_db9_files.py` | PHASE 0 audit |
| `posture_decoder/tools/check_zero_pose_compatibility.py` | PHASE 1B |
| `posture_decoder/db9/labels.py` | official movement vocabulary + families |
| `posture_decoder/db9/loader.py` | `.mat` reader, exercise/subject resolution |
| `posture_decoder/db9/canonical.py` | canonical vocabulary (Session 3 working copy) |
| `posture_decoder/db9/quality.py` | flag-not-delete quality checks |
| `posture_decoder/experiments/run_posture16.py` | PHASES 2–7 driver |
| `posture_decoder/experiments/diagnose_posture16.py` | D1–D5 falsification |
| `posture_decoder/experiments/diagnose_drift.py` | D6–D8 drift + DIP follow-ups |

**Data artifacts**

| path | contents |
|---|---|
| `data/ninapro_db9/raw/` | 22 verified archives + `manifest.json` (sha256 per file) |
| `data/ninapro_db9/extracted/` | 44 `.mat` files + `unpack_manifest.json` |
| `data/db9_posture16/representative_postures.npz` | 2 244 representative postures |
| `data/db9_posture16/repetition_trajectories.npz` | full trajectories (unused by the classifier) |
| `data/db9_posture16/subject_split.json` | the frozen split |
| `data/db9_posture16/results.json` | all metrics |
| `data/db9_posture16/diagnostics.json`, `diagnostics_drift.json`, `phase7_loso_confusion.json` | falsification evidence |
| `data/db9_posture16/confidence_report.json` | posteriors, calibration, reject-option curve |
| `figures/posture16/` | confusion matrices, per-class bars, diagnostics |

**Reproduce**

```bash
cd emg2pose_handstate/posture_decoder

python -X utf8 tools/fetch_db9.py --out ../data/ninapro_db9/raw --subjects "1-16;68-73" --workers 6
python -X utf8 tools/unpack_db9.py --raw ../data/ninapro_db9/raw --out ../data/ninapro_db9/extracted
python -X utf8 tools/audit_db9_files.py --extracted ../data/ninapro_db9/extracted --out ../docs/DB9_FILE_AUDIT.json

python -X utf8 experiments/run_posture16.py --extracted ../data/ninapro_db9/extracted \
       --data-dir ../data/db9_posture16 --fig-dir ../figures/posture16 --results-dir ../data/db9_posture16
python -X utf8 experiments/diagnose_posture16.py --data-dir ../data/db9_posture16 \
       --extracted ../data/ninapro_db9/extracted --out ../data/db9_posture16/diagnostics.json
python -X utf8 experiments/diagnose_drift.py --data-dir ../data/db9_posture16 \
       --extracted ../data/ninapro_db9/extracted --out ../data/db9_posture16/diagnostics_drift.json
python -X utf8 experiments/confidence_report.py --data-dir ../data/db9_posture16 \
       --results ../data/db9_posture16/results.json --out ../data/db9_posture16/confidence_report.json

python -X utf8 tools/check_zero_pose_compatibility.py \
       --out ../docs/DB9_EMG2POSE_ZERO_COMPATIBILITY.json --extracted ../data/ninapro_db9/extracted

cd .. && python -X utf8 -m pytest representation/tests/test_db9_to_canonical16.py -v
```

---

## 15. What this does and does not support

**Supported.** For the six exercise-B hand configurations that canonical16 can
describe, ground-truth hand kinematics alone identify the posture across unseen
subjects with 98.4 % accuracy (22-subject LOSO), and the result is not an
artefact of a single channel, of label leakage, of session drift, or of the
choice of classifier. The emg2pose and DB9 zero references are compatible for
the 15 flexion variables, with no offset required.

**Not supported.** Cross-dataset transfer. emg2pose-derived posteriors. The 23
exercise-C object grasps. Any wrist or forearm-rotation movement. Any claim that
canonical16 is *necessary* — canonical12_noDIP matches it, so the DIP channels
are not doing the work and the representation's minimal sufficient subset remains
untested.

**Stop condition observed.** No emg2pose predicted angles were connected, no deep
model was trained locally, canonical18 was not added, no emg2pose stage label was
used, no cross-dataset offset was tuned on classification accuracy, and no
cross-dataset end-to-end experiment was run.

---

## 16. Addendum — thumb axis resolved; status of this report

> **This report is the 22-subject EXPLORATORY result.** Per the research lead it
> is development evidence, and its frozen test split has already been inspected
> so it is no longer confirmatory. The confirmatory run is the full-77 replication
> (`run_full_db9.py`), reported separately.

### 16.1 Thumb CMC ab/adduction — resolution supersedes §4.2 and risk 1

The polarity question left open in §4.2 is **closed**. Swept over the DOF's full
official limit range (not the ±0.3 rad probe used in §4.2), forward kinematics of
the official UmeTrack model gives:

| `THUMB_CMC_AA` | first web angle | thumb↔index tip | out-of-plane elevation |
|---|---|---|---|
| −0.6118 | 69.38° | 153.90 | +45.70° |
| 0.0000 | 52.02° | 114.83 | +32.45° |
| +0.6118 | 50.42° | 93.57 | **+8.94°** |

Positive emg2pose `CMC_AA` **both closes the first web space and brings the thumb
down toward the palm plane**, so the in-plane and out-of-plane criteria agree that
positive is adduction — while DB9 documents `CMC1_A` as abduction-positive. DB9
is therefore negated: `FROZEN_DB9_SIGN = {"thumb_cmc_ab_adduction": -1.0}`, applied
in the DB9 adapter only. **The earlier §4.2 claim that the two criteria disagree
was wrong** — it used the thumb tip's *displacement-vector* palm-normal component
rather than the elevation angle, and elevation is non-monotonic over the range.
`docs/DB9_CANONICAL16_MAPPING.md` §4.2 carries the corrected analysis.

Zero alignment was verified separately, as required. The first probe tried
(`restimulus == 0`) was **invalid and is documented as a negative result**:
pure-flexion control channels sit at +52.6° (index PIP) and +44.4° (middle MCP)
there, which a fingers-extended hand cannot be. Using the anchor the paper names
(central third of exercise-B movement 11), thumb AA = **−0.23°** with all three
flexion controls ≈ 0 — so the correction is a **pure sign flip with no offset**.

### 16.2 Pre-registered robustness control: `canonical15_noThumbAA`

canonical16 minus exactly one variable, `thumb_cmc_ab_adduction` (column 1,
resolved by name), so the 15 retained columns are bit-identical to canonical16's.
It is reported alongside canonical16 and canonical12_noDIP and is **never used to
select or tune the primary model**.

On a 34-subject smoke run of the replication it costs **−0.0172 to +0.0008**
across ten model/normalisation combinations — i.e. removing the one axis carrying
residual cross-dataset uncertainty moves accuracy by **≤1.7 pp**, so that
uncertainty does not materially drive the result. To be re-measured on all 77.
