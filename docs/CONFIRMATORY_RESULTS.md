# Session 3 — CONFIRMATORY RUN RESULTS (frozen configuration, executed once)

**Run status:** completed, exit code 0, duration 3235.9 s (≈54 min), stderr empty.
**Executed:** 2026-09-18T03:39:18Z → 04:33:14Z.
**Corpus:** 77 subjects (DB1 27, DB2 40, DB5 10), identity assertions PASSED, corpus gate 77/77.
**Outcome exposure:** the 43-subject cohort is now **OUTCOME-EXPOSED permanently**.
This is the one and only pristine confirmatory evaluation of that cohort.

No post-outcome tuning, model selection, threshold selection, or configuration change
occurred. The frozen configuration was returned by identity, never by score.

---

## A. PRIMARY CONFIRMATORY — 34 development-exposed → 43 outcome-unseen (ONE SHOT)

| field | value |
|---|---|
| tier | A: PRIMARY CONFIRMATORY — one-shot external holdout |
| design item | `2_untouched_confirmation.a_train_exposed_test_untouched` |
| configuration | `lda__z` = LDA(solver='lsqr', shrinkage='auto') + train-only z-score + canonical16 |
| train subjects / samples | **34** / 1224 |
| test subjects / samples | **43** / 1548 |
| test evaluations | **1** |
| refit using test subjects | False |
| per-subject calibration | False |
| scaler fitted on | train subjects only |

**Frozen metrics: accuracy 0.9780, balanced accuracy 0.9780, macro-F1 0.9780 (n = 1548).**
Chance = majority-class baseline = 0.1667 (6 balanced classes).
Total errors: **34 of 1548**. Independently recomputed from the stored predictions: 0.9780361757105943 — matches.

Per source database within the held-out cohort:

| source | n | accuracy | balanced acc | macro-F1 |
|---|---|---|---|---|
| DB2 | 1440 | 0.9778 | 0.9778 | 0.9777 |
| DB5 | 108 | 0.9815 | 0.9815 | 0.9815 |

*(DB1 contributes no test subject: all 27 DB1 subjects are development-exposed.)*

Per-subject accuracy over the 43 unseen subjects: mean 0.9780, **median 1.0000**,
min 0.6667, max 1.0000, sd 0.0521. 25/43 subjects at 1.00. Only **1** subject below
0.90 (s30 = 0.667); every other subject ≥ 0.917.

Primary confusion matrix (rows = true, cols = predicted):

| true \ pred | 1 | 2 | 3 | 4 | 6 | 7 |
|---|---|---|---|---|---|---|
| 1 Thumb up | **252** | 0 | 5 | 1 | 0 | 0 |
| 2 Ext. index+middle | 0 | **242** | 8 | 4 | 2 | 2 |
| 3 Flex. ring+little | 0 | 0 | **258** | 0 | 0 | 0 |
| 4 Thumb opposes little | 0 | 0 | 0 | **258** | 0 | 0 |
| 6 Fist | 8 | 1 | 0 | 0 | **249** | 0 |
| 7 Pointing index | 0 | 2 | 0 | 1 | 0 | **255** |

Per-class recall: 1 = 0.9767, 2 = 0.9380, 3 = 1.0000, 4 = 1.0000, 6 = 0.9651, 7 = 0.9884.

**True classes 3 and 4 had 100% recall in Tier A.** They are not "perfectly separated",
however: other classes still emit false-positive predictions of them — class 3
receives 13 false positives (from class 1 ×5 and class 2 ×8), and class 4 receives 6
(from class 1 ×1, class 2 ×4, class 7 ×1).

Dominant error directions (all low-rate; 34 errors total, described as directed pairs):

| direction (true → predicted) | n |
|---|---|
| class 6 Fist → class 1 Thumb up | 8 |
| class 2 Ext. index+middle → class 3 Flex. ring+little | 8 |
| class 1 Thumb up → class 3 Flex. ring+little | 5 |
| class 2 Ext. index+middle → class 4 Thumb opposes little | 4 |
| class 7 Pointing index → class 2 Ext. index+middle | 2 |
| class 2 Ext. index+middle → class 7 Pointing index | 2 |
| class 2 Ext. index+middle → class 6 Fist | 2 |
| class 7 → class 4 · class 6 → class 2 · class 1 → class 4 | 1 each |

The fist/thumb-up confusion is **unidirectional in Tier A**: fist → thumb-up = 8,
thumb-up → fist = **0**. The single largest confusion is therefore a one-way collapse of
fist onto thumb-up, not a symmetric merge. Total off-diagonal mass = 34, matching the
reported error count.

---

## B. SECONDARY CONFIRMATORY — 43-subject LOSO

Cohort peers participate in training in every fold; **not** an untouched external holdout.

**accuracy 0.9839, balanced accuracy 0.9839, macro-F1 0.9838 (n = 1548).**
DB2 0.9826 (n=1440) · DB5 1.0000 (n=108).

The higher value than Tier A is expected: within-cohort LOSO leaks cohort-specific
structure through the training folds. It is reported as supportive evidence only and
may never be substituted for Tier A.

---

## C. DESCRIPTIVE — full-77 LOSO

Development-exposed subjects are inside this evaluation. **Not the primary result.**

**accuracy 0.9780, balanced accuracy 0.9780, macro-F1 0.9779 (n = 2772).**
DB1 0.9743 (n=972) · DB2 0.9785 (n=1440) · DB5 0.9861 (n=360).
Per-class recall: 1 = 0.9719, 2 = 0.9610, 3 = 1.0000, 4 = 1.0000, 6 = 0.9545, 7 = 0.9805.

All ten configurations, reported without ranking (`lda__z` chosen by identity):

| configuration | accuracy |
|---|---|
| nearest_centroid_euclidean__z | 0.9708 |
| nearest_centroid_euclidean__raw | 0.8806 |
| nearest_centroid_mahalanobis__z | 0.9780 |
| nearest_centroid_mahalanobis__raw | 0.9780 |
| **lda__z (frozen primary)** | **0.9780** |
| lda__raw | 0.9780 |
| logreg__z | 0.9870 |
| logreg__raw | 0.9816 |
| random_forest__z | 0.9787 |
| random_forest__raw | 0.9787 |

`logreg__z` scores higher (0.9870) and did **not** displace the primary. The conclusion
does not rest on one inductive bias: eight of ten configurations land in 0.971–0.987.

---

## D. PRE-REGISTERED REPRESENTATION CONTROLS — **evaluated in full-77 LOSO only**

**Scope: the two ablations were NOT evaluated in the pristine Tier-A 34 → 43 holdout.**
Tier A used `canonical16` on the frozen configuration and nothing else
(`primary_confirmatory.representation = canonical16`, n_test = 1548). The ablation
numbers below come from the **full-77 LOSO** descriptive pass (n = 2772), and their
frozen tier label is *"C: secondary/exploratory comparison — pre-registered
representation controls on the full-77 LOSO corpus. NOT the primary confirmatory arm."*
No claim here is a Tier-A claim.

Full-77 LOSO, frozen configuration `lda__z`:

| representation | accuracy | n | Δ vs canonical16 |
|---|---|---|---|
| canonical16 (PRIMARY) | **0.9780** | 2772 | — |
| canonical15_noThumbAA | **0.9722** | 2772 | −0.0058 |
| canonical12_noDIP | **0.9758** | 2772 | −0.0022 |

Per source: canonical16 DB1/DB2/DB5 = 0.9743 / 0.9785 / 0.9861;
noThumbAA = 0.9733 / 0.9750 / 0.9583 (−0.0278 on DB5, the largest single effect);
noDIP = 0.9691 / 0.9764 / 0.9917.

Neither removal materially changes the full-77 LOSO result. canonical16 remains primary
by pre-registration. Whether these ablations would behave the same in the untouched 43
is **untested** — extending Tier A to the control representations is a new analysis and
was deliberately not run (proposal only).

---

## E. SOURCE-DATASET ANALYSES

Primary-movement samples: DB1 972 (27 subj), DB2 1440 (40 subj), DB5 360 (10 subj).
Total representative postures extracted: 7854; primary-class subset 2772.

Frozen source-held-out (train two sources → test the third), frozen configuration `lda__z`:
DB1 0.9671 · DB2 0.9778 · DB5 0.9861. The same pattern holds across models
(0.9671–0.9944), i.e. transfer is comparable in every direction.

---

## F. CONTROLS

**Permutation (leakage-free):** mean 0.1655 ± 0.0077 over 20 permutations,
against chance 0.1667 — no evidence of label leakage.

**Drift (ORACLE / TEST-SUBJECT-CALIBRATED UPPER BOUND, `leakage_free = false`):**
drift-only 0.4892; canonical16 0.9780; drift-corrected 0.9711 (Δ = −0.0069).

**The primary result does not depend on the tested drift correction.** Drift-only analysis
shows substantial session/order information exists (0.4892 against 0.1667 chance), so
session/order drift remains a **known DB9 confound**. The drift analyses are
oracle/test-subject-calibrated and are **not** confirmatory evidence; they may not be
cited in support of the primary claim. `primary_result_depends_on_drift_correction: false`
records only that the frozen primary arm was computed without any drift correction — it is
not a claim that drift is absent or neutral.

---

## Comparison with the old 22-subject exploratory result

| evidence | subjects | accuracy |
|---|---|---|
| old full-22 LOSO (descriptive, development corpus) | 22 | 98.36 % ± 3.90 % |
| old held-out test split | **3** | 99.07 % |
| **new Tier A — untouched 43** | **43** | **97.80 %** |
| new Tier C — 43-subject LOSO | 43 | 98.39 % |
| new Tier B — full-77 LOSO | 77 | 97.80 % |

## Supported scientific conclusions

1. **The six stable target postures are identifiable** from canonical16 hand kinematics
   in genuinely outcome-unseen subjects: 97.80 % against 16.67 % chance, first and only
   evaluation of that cohort.
2. **The effect survives the transition** from the 34 development-exposed to the 43
   untouched subjects. The drop from the old 22-subject LOSO (98.36 %) to the untouched
   43 (97.80 %) is 0.56 pp — the earlier result did **not** substantially overestimate
   generalization.
3. **Consistency:** median per-subject accuracy 1.000, 25/43 perfect, one outlier (0.667);
   per-source 0.9778 (DB2) vs 0.9815 (DB5); DB1/DB2/DB5 all 0.967–0.986 in source-held-out.
4. **Representation ablations (full-77 LOSO only, not Tier A):** canonical16 = **0.9780**,
   canonical15_noThumbAA = **0.9722**, canonical12_noDIP = **0.9758**, all at n = 2772.
   Within the descriptive full-77 pass, removing thumb-AA costs −0.58 pp and removing the
   four DIP variables costs −0.22 pp. **Tier A did not test either ablation** — it used
   canonical16 only — so no Tier-A claim is made about them.
5. **Dominant remaining confusions** in Tier A are directed, not symmetric:
   class 6 Fist → class 1 Thumb up (8) and class 2 Ext. index+middle → class 3
   Flex. ring+little (8), then class 1 → class 3 (5) and class 2 → class 4 (4).
   Fist → thumb-up = 8 while thumb-up → fist = **0**, so that confusion is one-way.
   True classes 3 and 4 had 100% recall (no false negatives) but did receive 13 and 6
   false positives respectively. No class collapses to chance.
6. **Leakage control:** the permutation control sits at chance (0.1655 ± 0.0077 vs 0.1667),
   with no evidence of label leakage. Drift is addressed separately in §F and is a known
   confound, not a resolved one.

## Unsupported claims / remaining risks

- **Not** continuous or streaming/online gesture recognition (stable static postures only).
- **Not** cross-dataset emg2pose → posture validity; this is DB9-internal.
- **Not** Exercise-C object-grasp recognition (Exercise B only; movement 5/8 negative
  controls are not part of the primary arm).
- **Not** canonical16 necessity or minimality — only two removals were tested, and only in
  the full-77 LOSO descriptive pass, never in Tier A.
- **Not** force / contact identifiability.
- **Session/order drift remains a known DB9 confound.** The primary result does not depend
  on the tested drift correction, but drift-only analysis reaches 0.4892 against 0.1667
  chance, so substantial session/order information exists in the representation. The drift
  analyses are oracle/test-subject-calibrated (`leakage_free = false`) and are not
  confirmatory evidence. No claim is made that drift is absent or fully controlled.
- **No confidence interval or significance test** is attached to Tier A: the frozen metric
  set is accuracy / balanced accuracy / macro-F1, and adding a metric is a `WHAT COUNTS`
  change owned by the research lead. **Proposal, not implemented.**
- **DB5 is thin** in the primary arm (3 subjects, 108 postures); its 0.9815 is less
  precise than DB2's 0.9778 over 40 subjects.
- The `canonical15_noThumbAA` DB5 dip (−0.0278, i.e. ~3 postures of 108) rests on those
  same 3 subjects and should not be over-read.
- The 43 test subjects come from DB2 slots 28–67 **minus** those used in development and
  from DB5 slots 75–77; the cohort is not a uniform random sample of the corpus.
