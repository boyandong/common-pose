# DB9 trusted pose subset

**Artifact:** [`audits/db9/trusted_pose/TRUSTED_DB9_POSE_v1.json`](../audits/db9/trusted_pose/TRUSTED_DB9_POSE_v1.json)
**Subset SHA-256:** `e51dde6e63941fd080c84f3896a98cf50fba9e17d5f9cebe909253d5465782d1`
**Frozen plan SHA-256:** `4c618b562903d0d364d03bb8a997ef6b4140bd9e09d0f2475f1b008ad80c8793`
**Frozen before any classifier ran:** `true`

> ## ✅ This subset is **FROZEN** and revalidated across all 77 DB9 participants.
>
> The utility arm covers the **37 Exercise-B subjects**. It is not the final full-corpus
> validation, and it is not the 77-subject descriptive run. Treat the subset as a frozen
> *rule outcome*, not as a validated representation.

This document records the audit; it does not re-derive or re-word any verdict. The
machine-readable authority is the JSON artifact, and the reasoning is in
[`audits/db9/channel_forensic/`](../audits/db9/channel_forensic/).

---

## 1. Why DB9 was not treated as a black-box benchmark

A released "calibrated angles" array is a *claim*: that each column is a physical
anatomical angle. That claim is testable, because the DB9 protocol itself supplies
unambiguous physical anchors — a fist, a wrist flexed, the documented reference posture.
If a channel does not move the documented way on an anchor where it must, the column is not
the quantity it is named as, regardless of how well a classifier performs on it.

The audit therefore derives its verdicts from physical anchors and raw-gauge behaviour,
**never from classification performance**.

---

## 2. Verdict vocabulary

| verdict | meaning | n |
|---|---|---|
| `KEEP` | behaves as its published anatomical definition requires | 8 |
| `DROP` | evidence establishes it is not the named physical quantity | 6 |
| `INCONCLUSIVE` | evidence does not settle the question | 8 |

`DROP` and `INCONCLUSIVE` are different claims. Both remove a channel from the trusted
subset; only one asserts the channel is broken.

---

## 3. The trusted subset

**8 KEEP channels:**

`MCP1` · `IP1` · `MCP2_f` · `PIP2` · `MCP3_f` · `MCP4_f` · `MCP5_f` · `PIP5`

All eight attach to canonical DOF `thumb_mcp_flexion`, `thumb_ip_flexion`,
`index_mcp_flexion`, `index_pip_flexion`, `middle_mcp_flexion`, `ring_mcp_flexion`,
`pinky_mcp_flexion`, `pinky_pip_flexion` with high subject-level agreement
(0.919–1.000 over the 37-subject frozen cohort; 0.92–1.00 over all 77).

**No wrist channel is present, by construction** — `WRIST_A` is DROPped and `WRIST_F` is
INCONCLUSIVE. This is why the mixed 17-class Exercise-B task is not a fair evaluation of
the subset: it scores a wristless representation on a wrist-inclusive target.

### Confirmed-defective (DROP)

| channel | reason |
|---|---|
| `MCP2_a` | **OFFICIAL_EXCLUSION.** All-NaN in every recording. Ninapro: *"Sensor 11 (which corresponds to MCP2-3_A) was not included into the calibrated data due to noise problems."* |
| `CMC5` | The released column is an exact linear function (slope **0.28511** = the published 0.285) of the **same raw column** that feeds `WRIST_F`. Direct reconstruction from the released bytes therefore establishes a **released-representation defect**. The official documentation contains inconsistent sensor-number naming, but this does **not** alter the released-byte evidence, and the exact root cause (code typo, export bug or sensor-labelling mistake) remains **unknown**. CMC5 is excluded from the trusted physical subset. |
| `MCP5_a` | The released polynomial is not reproduced from the published coefficients. |
| `DIP3` | On an unambiguous fist, the raw DIP3 gauge and the released angle **decrease** in 71/77 subjects, while every MCP and PIP channel in the very same segments increases in 77/77. The transform is faithful; the direction contradicts the official "DIP(2-5)_F Flexion+/Extension−" criterion. |
| `DIP5` | The same inversion, coherent in 62/77 subjects, raw response ~6 % of the flexion-channel median. |
| `WRIST_A` | SENSOR_OR_FIT_LIMITATION. |

### Not established (INCONCLUSIVE) — 6 channels at the final 77-subject sample

> At the final 77-subject sample, under the **already-frozen rules** and with no rule made
> more permissive, `PIP3` and `DIP4` moved from `INCONCLUSIVE` to `DROP` because their
> magnitude ratio fell below the frozen 0.15 responsiveness floor. They are listed below
> with their final status. **The 8-channel frozen subset did not change.**

| channel | why it is not settled |
|---|---|
| `CMC1_f`, `CMC1_a` | no pre-declared physical anchor in Exercise B for these channels |
| `PIP3` | responds to a fist in only 35/77 subjects, raw magnitude ~3 % of the flexion-channel median, below the frozen responsiveness floor; `DROP` at 77 subjects (`INCONCLUSIVE` at 37) |
| `MCP4_a` | released `MCP4_a` and the raw abduction gauge move in **opposite** directions in every subject tested, and three of six published polynomial coefficients are not reproduced |
| `PIP4` | responds to a fist in 59/77 subjects |
| `DIP2` | responds in the **correct** direction (58/77), unlike DIP3/DIP4/DIP5 |
| `WRIST_F` | both wrist anchors pass 77/77, so its physical behaviour is sound; the only defect is a released quadratic coefficient that disagrees with the published one |

---

## 4. Required history a reader must know

These are recorded because they change how earlier numbers should be read. They are not
re-argued here.

### 4.1 An earlier "many channels fail" verdict was partly overturned

An earlier lane concluded that 11 of 16 canonical channels fail. That conclusion was
produced on segmentation keyed to the **pre-relabelling `repetition` vector**, which is
length-misaligned with `glove`/`angles` in **24 of 99** released files. Indexing kinematics
with a misaligned vector shifts every movement boundary.

Under correct segmentation on `restimulus × rerepetition`, six of the earlier suspects pass
at ≥ 0.90 subject-level agreement, while five findings are confirmed or newly established.

> The physiology never changed; the index did.

### 4.2 Official-warning channels

The vendor's own notes carry two caveats this audit independently corroborates:

* Sensor 11 / `MCP2-3_A` was excluded from the calibrated data for noise — consistent with
  `angles[:, 5]` being all-NaN and the only such column.
* DIP gauges *"provide reliable angles when subject hand size is big … may provide partial
  results when the hand of the subject is small."* The audit's DIP findings are consistent
  with a calibration/geometry limitation rather than random noise. **The root cause is not
  separated**: wrong gain, poorly seated sensor, and sensor defect were not distinguished.

### 4.3 Subject-identity collision risk

**The in-file `subject` field is not a valid identity key.** It is source-database-local:
`S68_E2_A1.mat` reports `subject == 1`, colliding with `S1_E2_A1.mat`. There are **10 such
collisions among the 37 Exercise-B files**.

Any grouping by that field merges distinct people. Subject-held-out splits must be built
from the archive/subject identity, not from this field. This is a live leakage hazard
independent of every other finding here.

### 4.4 Channel-name provenance

Channel order is read from the `order_of_angles` field stored **inside each released
`.mat`**, not from a secondary document. This is a direct consequence of the defect class
that mislabelled four of ten columns in a downstream representation.

### 4.5 Segmentation rule

Only `restimulus × rerepetition` is length-aligned with `glove`/`angles` in all 99 files.
`stimulus` and `repetition` are 7 samples longer in 24 of 99 files. The DB9 reference
posture was independently re-identified from the data as movement 11, confirming the
paper's statement.

---

## 5. Utility result — the official DB9 posture baseline (FROZEN)

Both arms, always together. **Task: NinaPro DB9 Exercise B hand configurations, official
movement IDs 1–8.** Movement IDs 9–17 are wrist movements and are **not** part of the
posture task; movement 17 is a wrist movement, not a hand-shape class.

**77 subjects**, leave-one-subject-out, global participant identity from the archive
filename, train-fold-only standardisation, one shared LDA per fold, radians, central 60 %
of every segment with a fixed per-segment frame cap of 200 (123 200 frames).

| metric | arm A — historical canonical16 (16 ch) | arm B — trusted subset (8 ch) |
|---|---|---|
| accuracy | 0.8556 | 0.7479 |
| balanced accuracy | **0.8556** | **0.7479** |
| macro F1 | 0.8559 | 0.7460 |
| worst-subject BA | 0.5850 | 0.5369 |
| median-subject BA | 0.8744 | 0.7556 |
| chance BA | 0.1250 | 0.1250 |
| class collapse | no | no |
| classes with recall < 0.5 | none | `[4]` |

* utility loss: ΔAcc **−0.1077**, ΔBA **−0.1077**, ΔMacroF1 **−0.1099**
* arm B is **5.98×** chance
* **per-class recall, arm B:** 1 `0.860`, 2 `0.691`, 3 `0.876`, 4 **`0.495`**, 5 `0.903`,
  6 `0.751`, 7 `0.829`, 8 `0.579`

> **Class 4 is the weakest posture class (recall 0.495) and most of its errors go to class
> 5.** It stays in the official internal result. The aggregate 8-class BA must not be used
> later to hide class-4 weakness during cross-dataset or human-semantic transfer;
> class-4 thumb/opposition-like behaviour requires separate reporting there.

### Why the frame cap is part of the protocol

DB2 recordings are much longer than DB1/DB5 recordings. An uncapped frame-level evaluation
would therefore weight the DB2 source database simply because it contains more frames per
segment. A fixed per-segment frame cap preserves every participant, every movement and
every segment while preventing recording duration from defining evaluation weight. It is a
declared frame-count choice — not a random balancing step — and it changes no channel,
model, split or threshold.

### The earlier 37-subject, 9-class run

The first utility arm covered only the 37 DB1/DB5 Exercise-B participants, because the
loader then selected Exercise B by **filename exercise code** (`_E2_`); DB2 ships the same
basic finger/wrist protocol as `_E1_` and its 40 files were never opened. That run also
counted movement 17 as a hand-shape class. It is retained as
`HISTORICAL_MIXED_TASK_UTILITY` in `src/common_pose/tasks/posture.py` and is **not** the
official benchmark.

Utility was computed **after** the subset was frozen, on a protocol that used no wrist
channel and could not select on performance.

---

## 6. What may and may not be claimed

**Permitted:** the **official Exercise B hand configurations 1–8** recovered by the frozen
trusted subset under subject-held-out evaluation over all 77 participants, with the utility
loss against the historical arm stated alongside.

**Not permitted:** any claim about DIP angles, about the palmar arch, or about wrist
deviation as measured physical quantities. Those dimensions are either established-defective
or not established, and the trusted subset does not contain them.

---

## 7. Reproducing the audit

The ported drivers are in
[`audits/db9/channel_forensic/tools/`](../audits/db9/channel_forensic/tools/), in numeric
order. `03_verdicts.py` freezes the subset; `04_utility.py` asserts against that frozen
subset, so 03 must run before 04.

```bash
export COMMON_POSE_DB9_RAW=/path/to/ninapro_db9/raw
export COMMON_POSE_DB9_ROOT=/path/to/ninapro_db9
export COMMON_POSE_DB9_OUT=./audits/db9/channel_forensic   # use a scratch dir to re-run

python audits/db9/channel_forensic/tools/segmentation.py
python audits/db9/channel_forensic/tools/forensic_core.py
python audits/db9/channel_forensic/tools/verdicts.py
python audits/db9/channel_forensic/tools/utility.py
python audits/db9/channel_forensic/tools/utility_posture_only.py
python audits/db9/channel_forensic/tools/decision.py
python audits/db9/channel_forensic/tools/fact_check.py
```

**Point `COMMON_POSE_DB9_OUT` at a scratch directory.** Re-running the drivers against the
published output path overwrites the frozen artifacts in this repository, including
`TRUSTED_DB9_POSE_v1.json`.

Ninapro DB9 is not redistributed here; obtain it from
[ninapro.hevs.ch](https://ninapro.hevs.ch/instructions/DB9.html). See
[`reproducibility.md`](reproducibility.md).

The full forensic chain is in `FLAGGED_CHANNEL_FORENSICS.md`,
`SEGMENTATION_VALIDATION.md`, `SENSOR11_IMPACT.md`, `DIP_HANDSIZE_ANALYSIS.md` and
`DB9_CHANNEL_LEDGER.csv`, with captured stdout under `logs/`.
