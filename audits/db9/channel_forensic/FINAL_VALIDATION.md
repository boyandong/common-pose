# DB9_FORENSIC_FINAL_VALIDATION

**Branch:** `S8-DB9-CHANNEL-FORENSIC` (validation addendum)
**Frozen plan SHA-256:** `4c618b562903d0d364d03bb8a997ef6b4140bd9e09d0f2475f1b008ad80c8793`
**Commit:** COMMIT PENDING
**`TRUSTED_DB9_POSE_v1` is NOT modified by this addendum.** Its SHA-256 remains
`e51dde6e63941fd080c84f3896a98cf50fba9e17d5f9cebe909253d5465782d1`.

---

## 1. FULL_DB9_COVERAGE: 77 / 77 — DB2 was never missing

| source DB | subjects present | official | E1 | E2 | E3 |
|---|---|---|---|---|---|
| DB1 | 27 | 27 | 0 | **27** | 16 |
| DB2 | 40 | 40 | **40** | 0 | 0 |
| DB5 | 10 | 10 | 0 | **10** | 6 |

**DB2 is not missing.** Its 40 files are on disk. The previous forensic covered 37 subjects
because the loader selected Exercise B by **filename exercise code** (`ex_files("E2")`):
DB1 and DB5 ship the 17-movement basic finger/wrist protocol as `_E2_`, **DB2 ships the same
protocol as `_E1_`** (DB2's archive numbers its exercises differently). The 40 DB2 files were
never opened.

Selection is now made **from the data**, not from the filename: exactly the 17 movement ids
1..17, movement 11 is the reference (fist response 0.00), movement 6 is the fist. Result:
**77 files, global keys exactly 1..77**, exercise codes `{E1, E2}`. `[EMPIRICAL]`

### 77-subject revalidation under the SAME frozen rules (no threshold changed)

| channel | DB1 (27) | DB2 (40) | DB5 (10) | **ALL77** | frozen | same? |
|---|---|---|---|---|---|---|
| MCP1 | 1.00 KEEP | 0.93 KEEP | 0.70 INCL | **0.92 KEEP** | KEEP | ✔ |
| IP1 | 1.00 KEEP | 1.00 KEEP | 1.00 KEEP | **1.00 KEEP** | KEEP | ✔ |
| MCP2_f | 1.00 KEEP | 1.00 KEEP | 1.00 KEEP | **1.00 KEEP** | KEEP | ✔ |
| PIP2 | 0.96 KEEP | 1.00 KEEP | 1.00 KEEP | **0.99 KEEP** | KEEP | ✔ |
| MCP3_f | 1.00 KEEP | 1.00 KEEP | 1.00 KEEP | **1.00 KEEP** | KEEP | ✔ |
| MCP4_f | 1.00 KEEP | 1.00 KEEP | 1.00 KEEP | **1.00 KEEP** | KEEP | ✔ |
| MCP5_f | 1.00 KEEP | 1.00 KEEP | 1.00 KEEP | **1.00 KEEP** | KEEP | ✔ |
| PIP5 | 1.00 KEEP | 0.95 KEEP | 1.00 KEEP | **0.97 KEEP** | KEEP | ✔ |
| PIP4 | 0.78 | 0.78 | 0.70 | 0.77 INCL | INCL | ✔ |
| DIP2 | 0.85 | 0.75 | 0.50 | 0.75 INCL | INCL | ✔ |
| DIP3 | 0.04 / 0.96 opp | 0.07 / 0.90 opp | 0.10 / 0.90 opp | **0.06 / 0.92 opp DROP** | DROP | ✔ |
| DIP5 | 0.11 / 0.89 opp | 0.25 / 0.75 opp | 0.20 / 0.80 opp | **0.19 / 0.81 opp DROP** | DROP | ✔ |
| CMC5 | 0.70 | 0.15 / 0.82 opp | 0.00 / 1.00 opp | **0.32 / 0.66 opp DROP** | DROP | ✔ |
| PIP3 | 0.63 | 0.38 | 0.30 | 0.45 / mag 0.03 **DROP** | INCL | ✘ |
| DIP4 | 0.22 | 0.35 | 0.20 | 0.29 / mag 0.05 **DROP** | INCL | ✘ |

**Verdict reproduction of the frozen KEEP/DROP set: 13 / 15 exact; 0 / 8 KEEP channels
changed.** The two differences are `PIP3` and `DIP4`, both moving
**INCONCLUSIVE → DROP** because the larger sample pushes their magnitude ratio below the
frozen 0.15 floor (PIP3 0.18→0.03, DIP4 0.16→0.05). **Both changes are strictly more
conservative; no channel moved in the permissive direction.** The trusted-8 is therefore
77-subject stable.

`DB5` alone (n = 10) drops `MCP1` to 0.70 agreement — small-subgroup noise; at n = 77,
`MCP1` = 0.92.

---

## 2. CMC5_VERDICT: **A — the release genuinely maps CMC5 to the wrist sensor**

Re-derived from zero:

| step | value |
|---|---|
| released angle order | the in-file `order_of_angles` field: index 12 = `13:CMC5`, index 20 = `21:WRIST_F` |
| CMC5 fit | `CMC5 = 0.28511122 × glove[:,20] + const`, max abs residual **5.3e-12 deg** |
| WRIST_F fit | `WRIST_F = 0.00865779 × glove[:,20]² + const`, max abs residual **3.8e-11 deg** |
| published | `CMC5_F = 0.285 · S20` ; `WRIST_F = 0.008 · S21² − 190.451` (DB9 paper Tables 2, 5) |
| ⇒ | **CMC5 and WRIST_F are both exact functions of the SAME raw column (0-based 20 = 1-based 21 = S21)** |
| the column the published CMC5 equation requires | 0-based 19 = 1-based 20 = S20 — **the released CMC5 does not use it** |

**Why A and not B.** The released CMC5 coefficient 0.28511122 reproduces the published 0.285
to four significant figures — the *formula* is the published one; only the sensor index is
wrong. And a raw-column plausibility check settles the direction: applying the published
WRIST_F quadratic to column 19 (span 3–177 counts) would give a **250°** wrist range, which
is impossible; column 20 (span 107–168) gives **145°**, matching the observed WRIST_F range
of 145.2°. So column 20 is the wrist sensor and the released CMC5 was computed from it.

**Documentation caveat (D, noted but not load-bearing).** The DB9 paper's own sensor
subscripts conflict with official Fig. 1 — the paper and the official usage notes both call
sensor 11 the MCP2-3_A gauge, while Fig. 1 places 11 at the middle MCP, and Fig. 1's
numbering does not match the gauge usage recovered from the release for digits 3–5. The
*named* sensor identity is therefore a documentation conflict. **The defect itself does not
depend on the numbering**: two published equations that use two different sensors have been
computed from one and the same raw column, and that is established from the released bytes
alone.

**Consequence for the case label.** `CMC5`'s frozen label was `CASE_B_SENSOR_OR_FIT_LIMITATION`
only because that is what the pre-declared anchor rule yields for a channel with no fist
response. The correct final description is **`CASE_A_RELEASED_REPRESENTATION_PROBLEM`**.
`admission_status` is unchanged: **DROP** either way.

---

## 3. LOSO_IDENTITY: **PASS**

* identity key = the archive slot parsed from the **filename** (`fx_common.load`), giving the
  DB9-global participant number 1..77;
* in-file `subject` field used as identity: **NO** (it is source-database local; 10 collisions
  among the 77 Exercise-B files — `S68_E2_A1.mat` reports `subject == 1`);
* folds = 77, one per global key; each fold: 76 training keys, 1 test key;
* **maximum train/test global-key intersection = 0** in all three arms.

**NO IMPACT.** The previous trusted classifier already grouped correctly, because
`fx_common.load` was corrected in BUG-004 *before* driver 04 ran. No rerun was required.

---

## 4. OFFICIAL 8-POSTURE RESULT (movement ids 1–8 only, 77 subjects, chance 0.1250)

Movement 17 excluded; ids 9–17 are wrist movements and do not enter the posture task.
Frozen subset, frozen LDA, train-fold-only standardisation, leave-one-subject-out, radians.

| metric | A historical canonical16 (16 ch) | **B TRUSTED_DB9_POSE_v1 (8 ch)** | C STRICT-PREFIX (6 ch) |
|---|---|---|---|
| Accuracy | 0.8556 | **0.7479** | 0.7482 |
| Balanced accuracy | 0.8556 | **0.7479** | 0.7482 |
| Macro-F1 | 0.8559 | **0.7460** | 0.7461 |
| median subject BA | 0.8744 | **0.7556** | 0.7450 |
| worst subject BA | 0.5850 (subj 26) | **0.5369** (subj 26) | 0.5356 (subj 26) |
| class collapse | no | **no** | no |

**Per-class recall, arm B:** 1: 0.860 · 2: 0.691 · 3: 0.876 · 4: 0.495 · 5: 0.903 ·
6: 0.751 · 7: 0.829 · 8: 0.579. Only class 4 falls below 0.5.

**Confusion matrix, arm B** (rows = true, columns = predicted, labels 1..8):

```
 1: [13248,    94,    17,    70,   302,  1249,   200,   220]
 2: [ 1010, 10647,  1988,   288,   188,   888,   251,   140]
 3: [  480,   909, 13484,    51,   289,    60,   105,    22]
 4: [  167,    33,     3,  7619,  4539,    18,     0,  3021]
 5: [  292,    13,     0,   667, 13904,    54,     3,   467]
 6: [ 3106,    43,     0,    73,   112, 11565,   200,   301]
 7: [  621,   177,     0,   567,    27,   726, 13065,   217]
 8: [  765,     6,     0,   280,   187,   112,    12, 14038]
```

**Utility loss (B − A):** ΔAccuracy −0.1077, ΔBA −0.1077, ΔMacroF1 −0.1099.
Trusted-8 is **5.98× chance** and shows no class collapse. Its residual error is concentrated
in class 4 (0.495; 4539 of its errors go to class 5 — the thumb-opposition configuration,
which the trusted subset represents only through `MCP1` and `IP1`).

**Declared deviation.** The uncapped 77-subject frame set is **11 843 312 frames (1.5 GB)** —
DB2's recordings are ~20× longer than DB1/DB5, so an uncapped pooled set is dominated by DB2
by frame count. A **per-segment cap of 200 frames** was applied, keeping every segment, every
movement and every subject while making the pooled frame set approximately subject-balanced
(final X = 123 200 × 16). This is a frame-count choice only: no channel, model, split or
threshold was changed. The 37-subject uncapped reference from driver 04b (ids 1–8 and 17)
gave trusted BA 0.7254 vs historical 0.8538 — the same ordering and a similar gap.

---

## 5. BUG-006_SENSITIVITY

**Channels restored by the 2 % materiality threshold: `MCP5_f` and `PIP5`.**

| | channels | Acc | BA | MacroF1 | worst-subject BA |
|---|---|---|---|---|---|
| TRUSTED-8 | MCP1, IP1, MCP2_f, PIP2, MCP3_f, MCP4_f, **MCP5_f**, **PIP5** | 0.7479 | 0.7479 | 0.7460 | 0.5369 |
| STRICT-PREFIX (removes the two post-hoc-restored channels) | MCP1, IP1, MCP2_f, PIP2, MCP3_f, MCP4_f | 0.7482 | 0.7482 | 0.7461 | 0.5356 |

**ΔBA = +0.0003.** The two channels contribute essentially no discriminability on the
official 8-posture task. Both also pass the physical anchor at 77/77 (agreement 1.00 and
0.97). **The sensitivity does not change any channel verdict** — it is a robustness report,
and it shows that BUG-006 was immaterial to the trusted subset's performance.

---

# FINAL DECISION: `DB9-ADMIT-REDUCED`

The trusted physical subset of 8 channels is real, reproduces under the frozen rules at 77
subjects, and carries the official 8-posture task at **BA 0.7479 (5.98× chance)** with no
class collapse. The permitted claim is: **the Exercise B hand configurations 1–8 recovered by
the frozen trusted subset under subject-held-out evaluation.** Not permitted: any claim about
DIP angles, the palmar arch, or wrist deviation as measured physical quantities.

### What is NOT changed by this addendum

No channel was re-selected, no threshold re-tuned, no classifier altered, and
`TRUSTED_DB9_POSE_v1.json` was not rewritten. The two 77-subject differences (PIP3, DIP4)
are reported for the PI; they would make the trusted set's complement *larger*, never the
trusted set itself.
