# S6 FORMAL — PRE-REGISTERED HUMAN SEMANTIC ANALYSIS

**Status: PRE-REGISTERED before either annotator labelled a single formal item.**
Binding on the analysis. Nothing in this document has been computed; no formal label exists yet.

Companion records: `ONTOLOGY_FREEZE.json` (the frozen ontology and the frozen benchmark),
`FORMAL_S6_RUNBOOK.md` (operation), `logs/` (the verification evidence).

---

## 0. Instrument

* Two independent human annotators, **A** and **C**, each label **396** displayed items:
  360 unique Naturalistic windows + 36 hidden duplicates.
* A receives the frozen formal **lane-1** presentation order; C receives the frozen formal **lane-2**
  order. Both orders, both blind-id sets and every GT payload value are frozen and byte-verified
  against `ONTOLOGY_FREEZE.json`.
* The **frozen ontology** (protocol `s6-formal-human-semantic-v2`) is the Pilot-3 wording: long-finger
  distal-phalanx rules, thumb judged at the **thumb base and first web space**, CLASS_1 vs CLASS_6
  decided by the thumb base, CLASS_4 carrying a hard fist exclusion.
* Storage is per-annotator (`s6_formal_annotation_v1_A` / `_C`); exports are
  `s6_formal_labels_annotator_A.json` / `_C.json`.

**The ontology is frozen.** No future formal disagreement may be used to revise it. Remaining
ambiguity is accepted as genuine annotation uncertainty.

---

## 1. Step 1 — HUMAN DATA ONLY

The first analysis after both exports are frozen uses **only** the two human label files and the
frozen duplicate map. No model artifact is opened at this step, and the step is completed and
recorded before Step 2 begins.

### 1a. The 360 unique Naturalistic windows

| quantity | definition |
|---|---|
| exact agreement | items where A's code equals C's code, out of 360 |
| raw agreement | that count / 360 |
| Cohen's κ | nominal, over the nine stored codes, with observed marginals |
| per-label counts | how often each of the nine codes was used, per annotator |
| primary–primary disagreements | both codes in {CLASS_1, CLASS_2, CLASS_3, CLASS_6, CLASS_7}, but different |
| primary–UNKNOWN | one primary, the other `UNKNOWN` |
| primary–AMBIGUOUS | one primary, the other `AMBIGUOUS` |
| UNJUDGEABLE prevalence | per annotator |
| CLASS_4 prevalence | per annotator, reported separately and never pooled |
| fraction assigned the same primary class | items where both codes are in the primary five and are equal, / 360 |

**κ caveat, fixed in advance.** 360 items over nine codes with an unbalanced marginal gives a wide
interval. κ is reported with its interval and **no hard threshold is imposed**; a point estimate is
never presented as a pass/fail.

### 1b. The 36 hidden duplicates — intra-rater reliability, reported SEPARATELY

For **each annotator independently** (A, then C), the duplicate item's code is compared to the code
that annotator gave its hidden original:

| quantity | per annotator |
|---|---|
| self-consistency | duplicates where the annotator gave the same code to the duplicate and to its original |
| intra-rater exact agreement | that count / 36 |
| intra-rater κ | nominal, over the nine codes |
| per-annotator duplicate disagreement list | duplicate id, original id, the two codes |

**Duplicates never enter the downstream semantic analysis.** They exist only to measure each
annotator's own consistency, and they are excluded from every other statistic in this document,
including κ in §1a and every model comparison in §2.

### 1c. Item-level output

Alongside the summary statistics, the full per-item table is reported: `blind_id`, A's code, C's
code, agreement flag, and for duplicates the original's id. The item-level structure is the primary
diagnostic — it shows *where* the two annotators diverge, which a summary coefficient hides.

---

## 2. Step 2 — FREEZE THE PRIMARY HUMAN SEMANTIC SET (before any unblinding)

Defined **now**, before model outputs are seen. It is the reference against which the decoder will be
scored, and it is not adjusted afterwards.

> ### PRIMARY HUMAN EVALUABLE SET
>
> The **360 unique** Naturalistic windows on which
>
> * **A's label equals C's label** — exact code equality, and
> * that agreed code is in **{CLASS_1, CLASS_2, CLASS_3, CLASS_6, CLASS_7}**
>
> The agreed code becomes that item's **primary human semantic reference label**.

Consequences, all binding:

* **Disagreement items are never forced into a class.** They are carried forward as *uncertainty* and
  are excluded from the primary semantic endpoint.
* **`CLASS_4` is excluded** from the primary five-class endpoint. It is diagnostic only. An item where
  either annotator chose `CLASS_4` is not in the evaluable set.
* **`UNKNOWN`, `AMBIGUOUS` and `UNJUDGEABLE` are never merged into a target class.** Agreement on any
  of them does not put an item in the set; disagreement involving them does not either.
* **The 36 duplicates are excluded by construction** (they are not unique windows) and additionally
  never used as semantic references.
* The set is **fixed at freeze time**. Its size and coverage are reported as:

| reported | meaning |
|---|---|
| `n_evaluable` | how many of the 360 unique windows qualify |
| `coverage` | `n_evaluable / 360` |
| `n_disagreement` | unique windows where A ≠ C, by disagreement class |
| `n_agreed_non_primary` | unique windows where A = C but the code is not one of the primary five |
| exclusions attributable to each cause | enumerated, so the shortfall is fully explained |

A **small** evaluable set is itself a result: it says the instrument's reliability limits how much of
the benchmark can carry a semantic reference, and it must be reported as such rather than repaired.

---

## 3. Step 3 — MODEL-UNBLINDED ANALYSIS (NOT EXECUTED IN THIS ROUND)

Only after both exports are frozen **and** the evaluable set is recorded does model unblinding begin.
This section is a specification, not a result. It is the moment the model-blind covenant ends, and
the order is fixed: human analysis first, evaluable set second, models third.

### 3a. Human consensus vs the frozen decoder on **GT pose**

Tests the **cross-dataset semantic validity of the frozen DB9 angle→posture decoder**: does the
decoder, given the corpus's own GT pose, produce the class humans agree on?

### 3b. Human consensus vs the frozen decoder on **VEMG2Pose-predicted pose**

Tests the **semantic validity of the complete EMG→pose→posture chain**: the decoder sees the
predicted pose instead of GT.

### 3c. Paired correctness decomposition

On the evaluable set, each item falls into one of four cells:

| | decoder(GT) correct | decoder(GT) wrong |
|---|---|---|
| **decoder(Pred) correct** | GT correct / Pred correct | GT wrong / Pred correct |
| **decoder(Pred) wrong** | GT correct / Pred wrong | GT wrong / Pred wrong |

and in particular

> **P(Pred wrong | GT correct)** — the VEMG2Pose-added semantic failure, conditional on the downstream
> decoder being semantically correct on GT pose.

This is the quantity that attributes semantic failure to the pose stage rather than the decoder stage.

### 3d. Standing rules for Step 3

* The primary reference is the frozen evaluable set. Items outside it are reported separately as
  *human-uncertain*, never silently dropped.
* `CLASS_4` is never pooled into the five-class accuracy.
* Duplicates never enter any model statistic.
* No significance test is run without also reporting the evaluable set's size, because the ceiling on
  any model accuracy is set by it.
* **No post-hoc adjudication.** A/C disagreements are never resolved after seeing model outputs, and
  no decoder prediction may influence a consensus. If an adjudication study is ever wanted, it must be
  separately designed, separately pre-registered, and model-blind.

---

## 4. What would make this analysis invalid

Recorded in advance so it can be checked afterwards:

1. the ontology, benchmark payloads, blind ids, duplicate structure or presentation orders changed
   after the freeze (guarded by `scan_formal_ac.py` §3 against `ONTOLOGY_FREEZE.json`);
2. duplicates entering a semantic statistic;
3. `CLASS_4` pooled into the primary five-class endpoint;
4. disagreement items forced into a class, or non-target codes merged into targets;
5. the evaluable set redefined after model outputs were seen;
6. any model artifact opened before both human exports were frozen.
