# DB9 trusted pose subset

**Artifact:** [`audits/db9/trusted_pose/TRUSTED_DB9_POSE_v1.json`](../audits/db9/trusted_pose/TRUSTED_DB9_POSE_v1.json)
**Subset SHA-256:** `e51dde6e63941fd080c84f3896a98cf50fba9e17d5f9cebe909253d5465782d1`
**Frozen plan SHA-256:** `4c618b562903d0d364d03bb8a997ef6b4140bd9e09d0f2475f1b008ad80c8793`
**Frozen before any classifier ran:** `true`
**Final validation:** [`audits/db9/channel_forensic/FINAL_VALIDATION.md`](../audits/db9/channel_forensic/FINAL_VALIDATION.md)
(SHA-256 `4fa700dc26d0d50f243c72372b2c1a67ee9749b4964757e529b8212839fd2b81`), covering
**77 of 77 participants**.

> ## This subset is **FROZEN**, and was revalidated across all 77 participants with no change to the retained channels.
>
> **0 of 8 KEEP channels changed** under the frozen rules. Two channels moved
> `INCONCLUSIVE → DROP` (both strictly more conservative). The subset file was verified
> byte-identical after revalidation.
>
> **The file records `n_subjects: 37`.** That is a frozen artifact of the run that produced
> it and is preserved unmodified; the 77-participant revalidation is the addendum above.
> See §4.1.

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
| `DROP` | evidence establishes it is not the named physical quantity | 8 |
| `INCONCLUSIVE` | evidence does not settle the question | 5 |

`DROP` and `INCONCLUSIVE` are different claims. Both remove a channel from the trusted
subset; only one asserts the channel is broken.

---

## 3. The trusted subset

**8 KEEP channels:**

`MCP1` · `IP1` · `MCP2_f` · `PIP2` · `MCP3_f` · `MCP4_f` · `MCP5_f` · `PIP5`

All eight attach to canonical DOF `thumb_mcp_flexion`, `thumb_ip_flexion`,
`index_mcp_flexion`, `index_pip_flexion`, `middle_mcp_flexion`, `ring_mcp_flexion`,
`pinky_mcp_flexion`, `pinky_pip_flexion` with high subject-level agreement (0.92–1.00 over
77 participants).

**No wrist channel is present, by construction** — `WRIST_A` is DROPped and `WRIST_F` is
INCONCLUSIVE. This is why a wrist-inclusive task is not a fair evaluation of the subset.

### DROP (established not to be the named physical quantity)

| channel | status | reason |
|---|---|---|
| `MCP2_a` | DROP | **OFFICIAL_EXCLUSION.** All-NaN in every recording. Ninapro: *"Sensor 11 (which corresponds to MCP2-3_A) was not included into the calibrated data due to noise problems."* |
| `CMC5` | DROP — **`CASE_A` released representation defect** | The released `CMC5` column is an exact affine function of the **same raw column** that feeds `WRIST_F`, while the published calibration assigns these quantities to different sensors. See §4.3. |
| `MCP5_a` | DROP | The released polynomial is not reproduced from the published coefficients. |
| `DIP3` | DROP | On an unambiguous fist the raw gauge and the released angle **decrease** while every MCP and PIP channel in the same segments increases. The transform is faithful; the direction contradicts the published "DIP(2-5)_F Flexion+/Extension−" criterion. |
| `DIP5` | DROP | The same inversion, coherent in 32/37 subjects. |
| `WRIST_A` | DROP | SENSOR_OR_FIT_LIMITATION. |
| `PIP3` | DROP | Moved `INCONCLUSIVE → DROP` at 77 participants: agreement 0.45 with magnitude ratio 0.03, below the frozen floor. |
| `DIP4` | DROP | Moved `INCONCLUSIVE → DROP` at 77 participants: agreement 0.29 with magnitude ratio 0.05, below the frozen floor. |

### INCONCLUSIVE (evidence does not settle it)

| channel | why it is not settled |
|---|---|
| `CMC1_f`, `CMC1_a` | no pre-declared physical anchor in Exercise B for these channels |
| `PIP4` | agreement 0.77 at 77 participants; above the drop floor but not established |
| `DIP2` | responds in the **correct** direction (0.75 at 77 participants), unlike DIP3/DIP4/DIP5 |
| `WRIST_F` | both wrist anchors pass, so its physical behaviour is sound; the only defect is a released quadratic coefficient that disagrees with the published one |

---

## 4. Required history a reader must know

### 4.1 Coverage: 77 of 77, and why an earlier pass reported 37

The first forensic pass covered **37** participants. That was a **loader selection
artifact**, not a property of the release:

* the loader selected Exercise B by **filename exercise code** (`E2`);
* DB1 and DB5 ship the 17-movement basic finger/wrist protocol as `_E2_`;
* **DB2 ships the same protocol as `_E1_`** — its archive numbers exercises differently;
* DB2's 40 files were therefore never opened.

Selection is now made **from the data**, not from the filename: exactly the 17 movement ids
1..17, movement 11 is the reference, movement 6 is the fist. Result: **77 files, global keys
exactly 1..77**.

> The earlier statement that DB9 had only 37 usable Exercise-B participants is
> **SUPERSEDED**.

### 4.2 An earlier "many channels fail" verdict was partly overturned

An earlier lane concluded that 11 of 16 canonical channels fail. That conclusion was
produced on segmentation keyed to the **pre-relabelling `repetition` vector**, which is
length-misaligned with `glove`/`angles` in **24 of 99** released files, shifting every
movement boundary.

Under correct segmentation on `restimulus × rerepetition`, six of the earlier suspects pass
at ≥ 0.90 subject-level agreement, while five findings are confirmed or newly established.

> The physiology never changed; the index did.

### 4.3 CMC5: the released representation, established from the bytes

**Final case `CASE_A` — released representation defect.** `admission_status` is `DROP` either
way; the case label changed from the earlier `CASE_B_SENSOR_OR_FIT_LIMITATION`, which was
what the pre-declared anchor rule yields for a channel with no fist response.

| step | value |
|---|---|
| released angle order | the in-file `order_of_angles`: index 12 = `13:CMC5`, index 20 = `21:WRIST_F` |
| `CMC5` fit | `CMC5 = 0.28511122 × glove[:,20] + const`, max abs residual **5.3e-12°** |
| `WRIST_F` fit | `WRIST_F = 0.00865779 × glove[:,20]² + const`, max abs residual **3.8e-11°** |
| published | `CMC5_F = 0.285 · S20` ; `WRIST_F = 0.008 · S21² − 190.451` |
| ⇒ | both released quantities are exact functions of the **same** raw column (0-based 20), while the published `CMC5` equation requires a **different** column (0-based 19) that does not feed the released `CMC5` |

The released `CMC5` coefficient reproduces the published 0.285 to four significant figures —
the *formula* is the published one; only the sensor index is wrong. A raw-column plausibility
check settles the direction: applying the published `WRIST_F` quadratic to the other candidate
column would give an impossible ~250° wrist range, whereas the column actually used gives
145°, matching the observed `WRIST_F` range.

**Documentation caveat — remains.** The DB9 paper's own sensor subscripts conflict with
official Fig. 1: the paper and the official usage notes both call sensor 11 the MCP2-3_A
gauge, while Fig. 1 places 11 at the middle MCP, and Fig. 1's numbering does not match the
gauge usage recovered from the release for digits 3–5. The **named** sensor identity is
therefore a documentation conflict. **The defect does not depend on the numbering**: two
published equations that use two different sensors were computed from one and the same raw
column, and that is established from the released bytes alone.

**What is not claimed.** The exact software or export root cause is **not known**. What is
established is the released-bytes relationship and its consequence for interpretation.

### 4.4 Official-warning channels and root cause

The vendor's own notes carry two caveats this audit independently corroborates:

* Sensor 11 / `MCP2-3_A` was excluded from the calibrated data for noise.
* DIP gauges *"provide reliable angles when subject hand size is big … may provide partial
  results when the hand of the subject is small."*

The DIP findings are consistent with a calibration/geometry limitation rather than random
noise, but **the root cause is not separated**: wrong gain, poorly seated sensor, and sensor
defect were not distinguished.

### 4.5 Subject-identity collision risk

**The in-file `subject` field is not a valid identity key.** It is source-database-local:
`S68_E2_A1.mat` reports `subject == 1`, colliding with `S1_E2_A1.mat`. There are **10 such
collisions among the 77 Exercise-B files**.

Any grouping by that field merges distinct people. The frozen LOSO evaluation uses the
**archive slot parsed from the filename** and has **maximum train/test global-key
intersection = 0**.

### 4.6 Channel-name provenance and segmentation rule

Channel order is read from the `order_of_angles` field stored **inside each released `.mat`**,
never from a secondary document. Only `restimulus × rerepetition` is length-aligned with
`glove`/`angles` in all 99 files; `stimulus` and `repetition` are longer in 24 of 99. The
reference posture was independently re-identified from the data as movement 11, confirming
the paper's statement.

---

## 5. The official downstream posture baseline

The valid DB9 posture task is the **official hand configurations, movement ids 1–8 only**.
Movement 17 is a wrist movement and is **not** a hand-shape class.

77 participants, leave-one-subject-out, train-fold-only standardisation, one shared LDA per
fold, radians.

| metric | historical 16-channel | `TRUSTED_DB9_POSE_v1` (8) | STRICT-PREFIX (6) |
|---|---|---|---|
| accuracy | 0.8556 | **0.7479** | 0.7482 |
| balanced accuracy | 0.8556 | **0.7479** | 0.7482 |
| macro-F1 | 0.8559 | **0.7460** | 0.7461 |
| median-subject BA | 0.8744 | **0.7556** | 0.7450 |
| worst-subject BA | 0.5850 | **0.5369** | 0.5356 |
| chance | 0.1250 | 0.1250 | 0.1250 |
| class collapse | no | no | no |

* utility loss (trusted − historical): ΔAcc **−0.1077**, ΔBA **−0.1077**, ΔMacroF1 **−0.1099**
* trusted-8 is **5.98×** chance and shows **no class collapse**
* trusted per-class recall: 1 **0.860** · 2 **0.691** · 3 **0.876** · 4 **0.495** ·
  5 **0.903** · 6 **0.751** · 7 **0.829** · 8 **0.579**
* only class 4 falls below 0.5; its error concentrates in class 5, and it must stay
  separately visible in future transfer evaluation

**Declared deviation — per-segment frame cap of 200.** The uncapped 77-participant frame set is
11 843 312 frames, and DB2's recordings are ~20× longer than DB1/DB5, so an uncapped pooled
set is dominated by DB2 by frame count. The cap keeps every participant, movement and segment
while removing that duration weighting. No channel, model, split or threshold was changed.

Both arms are always reported together. Omitting the loss would hide the price of the audit;
omitting the second number would hide that the surviving subset is genuinely usable.

### BUG-006 sensitivity (robustness only)

`MCP5_f` and `PIP5` had been restored under a post-hoc 2 % documentation-rounding materiality
rule. The STRICT-PREFIX 6-channel subset removing both gives BA **0.7482** against TRUSTED-8
**0.7479** — ΔBA **+0.0003**. The trusted utility conclusion does **not** depend materially on
those two restored channels; both also pass the physical anchor at 77/77. This report changes
**no** channel verdict.

---

## 6. What may and may not be claimed

**Permitted:** the Exercise-B hand configurations **1–8** recovered by the frozen trusted
subset under subject-held-out evaluation, with the utility loss against the historical arm
stated alongside.

**Not permitted:** any claim about DIP angles, about the palmar arch, or about wrist
deviation as measured physical quantities. Those dimensions are either established-defective
or not established, and the trusted subset does not contain them.

**Also not claimed:** that the subset is a validated *interface*; that these DOFs are
numerically comparable with another dataset's; or that a task head trained here survives an
upstream estimator substitution. See `docs/research_status.md` §F.

---

## 7. Reproducing the audit

The ported drivers are in
[`audits/db9/channel_forensic/tools/`](../audits/db9/channel_forensic/tools/), in numeric
order. `verdicts.py` freezes the subset; `utility.py` asserts against that frozen subset, so
`verdicts` must run before `utility`. `final_validation.py` is the lean 77-participant
revalidation that produced `FINAL_VALIDATION.md` and `artifacts/FINAL_VALIDATION.json`.

```bash
export COMMON_POSE_DB9_RAW=/path/to/ninapro_db9/raw
export COMMON_POSE_DB9_ROOT=/path/to/ninapro_db9
export COMMON_POSE_DB9_OUT=/path/to/scratch/out     # NOT the published audits/ path

python audits/db9/channel_forensic/tools/segmentation.py
python audits/db9/channel_forensic/tools/forensic_core.py
python audits/db9/channel_forensic/tools/verdicts.py
python audits/db9/channel_forensic/tools/utility.py
python audits/db9/channel_forensic/tools/utility_posture_only.py
python audits/db9/channel_forensic/tools/decision.py
python audits/db9/channel_forensic/tools/final_validation.py
python audits/db9/channel_forensic/tools/fact_check.py
```

**Point `COMMON_POSE_DB9_OUT` at a scratch directory.** Re-running against the published
output path overwrites the frozen artifacts in this repository, including
`TRUSTED_DB9_POSE_v1.json`.

Ninapro DB9 is not redistributed here; obtain it from
[ninapro.hevs.ch](https://ninapro.hevs.ch/instructions/DB9.html). See
[`reproducibility.md`](reproducibility.md).

The full forensic chain is in `FLAGGED_CHANNEL_FORENSICS.md`,
`SEGMENTATION_VALIDATION.md`, `SENSOR11_IMPACT.md`, `DIP_HANDSIZE_ANALYSIS.md`,
`DB9_CHANNEL_LEDGER.csv` and the `FINAL_VALIDATION.md` addendum, with captured stdout under
`logs/`.
