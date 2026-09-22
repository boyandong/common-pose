# S6 — FUTURE ANALYSIS PLAN (pre-registered)

**Status: PRE-REGISTERED, NOT EXECUTED.** Written and frozen **before any human label exists**
and **before any model output for these windows has been computed**. This round (S6 Stage A)
computes none of the quantities below.

Order of operations once annotation is complete is binding:

```
labels frozen  ->  reliability + adjudication (no model output yet)  ->  enrichment decision
   ->  THEN model outputs are computed for the first time  ->  primary semantic metrics
```

The order is the pre-registration. Computing a model output before the labels are frozen and
adjudicated would destroy the benchmark's purpose: the whole point is to distinguish two
failure mechanisms that cannot be separated once the model's behaviour is known.

Notation: `N_unique = 360`, `N_items = 396` per annotator (360 unique + 36 hidden duplicates).

---

## 0. What this analysis can and cannot establish

**Can:** whether the frozen DB9 semantic decoder (and the full EMG→pose→decoder chain)
agrees with human semantic judgement *on this corpus*, and how much semantic error is added by
the pose estimator over the decoder's own cross-dataset error.

**Cannot:** anything population-level. The mini corpus is **one subject** (user `e3096`,
`d387095792`), 30 sessions, 15 stages × 2 sides. Every number is **within-subject**. Where an
interval is reported it is a **within-subject / across-session stability interval**, never a
population confidence interval (see §7).

---

## 1. Stage 1 — Human reliability (NO model output yet)

Computed on the frozen label files only.

| quantity | definition |
|---|---|
| **Raw inter-annotator agreement** | fraction of the 360 unique items where A and B chose the same label id; reported over all items and over the five primary classes only |
| **Cohen's κ (A vs B)** | on the categorical label set, computed twice: (a) the full 9-label set, (b) restricted to items where both annotators gave a primary label. κ is reported with its raw agreement and the marginal distributions, never alone |
| **Hidden-duplicate intra-rater agreement, per annotator** | over the 36 duplicate pairs: fraction where the same annotator gave the same label to both copies. This is the honest ceiling on label noise |
| **Disagreement matrix** | 9×9 contingency of A's label against B's label, plus the 36-pair self-agreement matrix per annotator |
| **Duplicate-position audit** | confirm the realized presentation separation (`hidden/hidden_duplicate_map.json`) and check intra-rater agreement does not depend on it |

**Adjudication** — only if the reliability numbers require it. Adjudication rules must be
fixed **before** the disagreement set is inspected against model behaviour:
1. items where A and B agree → that label is the consensus label;
2. items where they disagree → an adjudication step (third pass by one or both annotators,
   with the disagreement shown and no model information available) produces a consensus label;
3. if adjudication cannot resolve an item, the consensus label is `AMBIGUOUS` and the item is
   excluded from the primary metric but retained in the prevalence tables.

**No adjudication may use model output**, and no item may be dropped from the primary metric
because a model gets it wrong. Any item dropped is dropped for a label-side reason only, and
the drop is reported with its count.

---

## 2. Stage 2 — Naturalistic Set endpoints (prevalence)

Computed on the 360 unique windows, using the consensus labels.

**Pre-registered endpoints (exactly these five, in this order):**

1. fraction **PRIMARY-5** (consensus label ∈ {CLASS_1, CLASS_2, CLASS_3, CLASS_6, CLASS_7})
2. fraction **diagnostic CLASS_4**
3. fraction **UNKNOWN**
4. fraction **AMBIGUOUS**
5. fraction **UNJUDGEABLE**

**Two denominators, both always reported:**

* **all 360 sampled windows** (`/360`) — the naturalistic prevalence denominator;
* **judgeable windows only** — that is, excluding UNJUDGEABLE where the endpoint is about
  posture, and additionally excluding AMBIGUOUS where the endpoint is about a specific class.
  Which denominator is used must be stated in every table; the `/360` figure is the default
  and the judgeable-denominator figure is a secondary, clearly labelled view.

Additional reported (not pre-registered endpoints, descriptive only): the per-class breakdown
of the PRIMARY-5 fraction, and the three non-target fractions as separate numbers (never
merged into one "other").

**Sanity anchor, to be reported alongside:** the corresponding fractions computed separately
for the **left-hand** and **right-hand** source sessions (§5). This is descriptive
stratification, not a hypothesis test.

---

## 3. Stage 3 — Confirmed-posture enrichment decision (still NO model output)

Executed **after the consensus labels are frozen** and **before any decoder / VEMG2Pose output
is revealed** for these windows.

```
count consensus examples per PRIMARY-5 class over the 360 unique windows
if any class has < 20 consensus examples:
    build the CONFIRMED POSTURE ENRICHMENT SET
```

**Candidate generation is restricted to GT kinematics and pose stability.** Allowed:

* low angular-velocity candidate centres (settled regions of the recorded GT timeline);
* session and time diversity (spread across sessions, minimum temporal separation);
* the same GT-validity gate as the Naturalistic set (the whole window must be GT-valid).

**Forbidden** — identical to the Naturalistic set's forbidden list: DB9 decoder output,
decoder confidence, DB9 support/OOD distance, VEMG2Pose predictions, stage labels, and any
semantic or model-derived quantity. Enrichment candidates are human-annotated under the same
blinding as Stage 1.

**Targets:** minimum 20, preferably 25–30, consensus examples per PRIMARY class, **where the
mini corpus permits**. If the corpus does not contain enough clear examples of a class, the
shortfall is reported as the result — the class is then simply under-powered, and that is a
finding about the corpus, not something to be fixed.

**Hard rules**

* no relabelling of ambiguous poses to manufacture balance;
* the enrichment set estimates **conditional** semantic performance on clearly human-confirmed
  target postures;
* it does **not** estimate natural prevalence;
* **Naturalistic and Enrichment results are never pooled into a single prevalence estimate.**
  They may be reported side by side, always labelled.

---

## 4. Stage 4 — Semantic evaluation (FIRST time model output is computed)

**Only after Stages 1–3 are complete and frozen.** On **consensus PRIMARY-5 samples** only
(consensus label ∈ {CLASS_1, CLASS_2, CLASS_3, CLASS_6, CLASS_7}); class 4 and the three
non-target labels are never part of these metrics.

### A. GT-decoder semantic performance (failure mechanism A)

```
human consensus label   vs   emg2pose GT canonical pose  ->  frozen DB9 decoder
```

Metrics: **accuracy · balanced accuracy · macro-F1 · per-class recall · confusion matrix**
(rows = human consensus class, columns = decoder class, with per-cell counts).

This measures **cross-dataset decoder semantic generalisation**: can the frozen decoder, which
performs well inside DB9, correctly map emg2pose GT kinematics onto the intended semantic
posture?

### B. Full-chain semantic performance (mechanisms A + B together)

```
human consensus label   vs   EMG -> frozen VEMG2Pose -> frozen canonical mapping -> frozen DB9 decoder
```

The **same** metric set.

### C. VEMG2Pose incremental semantic loss

```
delta accuracy          = acc(GT-decoder)  - acc(full chain)
delta balanced accuracy = bacc(GT-decoder) - bacc(full chain)
delta macro-F1          = F1(GT-decoder)   - F1(full chain)
```

and, more importantly, the **paired 2×2 correctness decomposition**:

|                       | pred decoder correct | pred decoder wrong |
|---|---|---|
| **GT decoder correct** | whole-chain success | **VEMG2Pose-added error** |
| **GT decoder wrong**   | accidental recovery | persistent decoder/domain failure |

**Primary pre-registered statistic:**

```
P( predicted decoder wrong | GT decoder correct )
```

This is the primary measure of semantic loss added by EMG→pose estimation **once the
downstream decoder is known to understand the GT posture**. It is reported with its numerator
and denominator (`k` of `n`), never as a bare proportion, and with a session-block stability
interval (§7).

The other three cells are reported as counts and as a decomposition of the total error; the
"accidental recovery" cell is reported but is not evidence of anything good, and must not be
described as a benefit.

**Never computed here:** any metric on class 4 pooled with primary classes; any threshold
tuned on the primary metric; any hypothesis test added after seeing the results.

---

## 5. Handedness stratification (descriptive, pre-registered)

The mini corpus is 15 left / 15 right sessions. Hand side stays hidden from annotators, but the
**evaluator-side** manifest records it, and every Stage-2/4 table is additionally reported
stratified by:

* left-hand source sessions;
* right-hand source sessions.

Purpose: **detect rendering/handedness-specific effects** (the S6 renderer uses an analytic
mirror for left-hand items, so a systematic left/right difference in the endpoints is
diagnostically informative).

Rules:

* **no tuning of labels or models by side** — stratification is descriptive only;
* no hypothesis test on the left/right difference is pre-registered; if one is added later it
  is reported as post-hoc;
* **class 4 remains diagnostic** throughout, because handedness materially affects its visual
  interpretation (it is intrinsically a statement about the ulnar side of the palm).

---

## 6. Confidence handling (pre-registered)

Annotators may record confidence 1–3 per item. It is **never** used to remove a sample from the
primary analysis.

* **Primary analysis = all consensus PRIMARY-5 labels**, regardless of confidence.
* **High-confidence-only analysis = secondary, descriptive only.**
* No confidence threshold may be tuned using decoder performance.
* Confidence is also reported as its own descriptive table: distribution by label, by annotator,
  and agreement rate by confidence level of the two annotators (a calibration-style check on the
  labels themselves, with no model information involved).

---

## 7. Uncertainty reporting (pre-registered)

Because the corpus is **one subject with 30 sessions**:

* **no population / cross-subject uncertainty may be claimed**;
* where an interval is reported, it is a **session-level resampling interval**: resample the 30
  sessions with replacement (fixed seed, recorded), recompute the metric on the resampled set,
  and report the 2.5th/97.5th percentiles;
* every such interval is labelled **"within-subject / across-session stability interval"**,
  explicitly **NOT a population confidence interval**;
* paired statistics (Stage 4C) are resampled **by session**, preserving the pairing;
* the resampling seed and the number of replicates are fixed and recorded before computation.

**No hypothesis tests are added after seeing the outcomes.** If any test is run, it is reported
as post-hoc and exploratory, with the number of tests disclosed.

---

## 8. Reporting rules that apply to every table

1. Class 4 is always reported separately; primary metrics never contain it.
2. UNKNOWN, AMBIGUOUS and UNJUDGEABLE are always three separate numbers.
3. Naturalistic and Enrichment results are never pooled into one prevalence figure.
4. Every rate carries its numerator and denominator.
5. Every table states its denominator convention (all sampled windows vs judgeable windows).
6. Consensus-label counts are reported next to every per-class metric, because a class with
   3 examples must not look like a class with 30.
7. Left/right stratification accompanies every Stage-2 and Stage-4 table.
8. Any deviation from this plan is recorded as a deviation with its reason and its timing
   relative to seeing the results.
