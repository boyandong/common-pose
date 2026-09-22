# Human semantic validation lane — curated public-safe subset

This directory is a **deliberately partial** mirror of an internal research lane (the
"Observer / S6" lane) that collected **human annotations of rendered hand poses**. It
preserves the lane's own definitions and protocol documents verbatim, apart from
machine-local paths in documented shell commands, which were replaced by placeholders.
No computed number, threshold, label definition or protocol statement was altered.

The lane's own records remain the long-term source of truth. Where this note states a
status, it states what was observed in the artefacts, not what the lane's summary
documents assert.

---

## 1. What the lane studies

**Question.** Given a hand pose produced by a pose pipeline, does it land in the
semantically intended posture — and when it does not, is the failure in the
*cross-dataset semantic decoder* or in the *pose estimator upstream of it*?

Those two mechanisms cannot be told apart once a model's behaviour is known, so the lane
builds an instrument that separates them: a human-labelled semantic reference set. Human
annotators label which posture a rendered pose shows, and the model chain is scored
against that reference afterwards.

## 2. Design

**Instrument.** 360 unique "Naturalistic" windows drawn from a 30-session, single-subject
corpus, plus **36 hidden duplicates** (the same pose data replayed under a fresh blind id),
giving **396 displayed items per annotator**. Each item is a 0.60 s animation of 31
ground-truth pose vectors at 50 Hz with the centre frame pinned; the annotator labels the
posture at the pinned centre frame only.

**Two independent annotators**, same 396 items, same blind ids, **two independently
randomised presentation orders**. The two arms are served from physically separate
document roots; neither arm has a route to the other's payload or answers.

**What the annotator sees: only the rendering.** No joint-angle numbers, no model output,
no stage name, no source filename, no timestamp, no hand side, no validity banner, and no
indication which items are the hidden repeats. The rendering path uses ground-truth
kinematics only — no EMG, no model, no prediction.

**Label vocabulary.** Five **primary** classes (`CLASS_1`, `CLASS_2`, `CLASS_3`,
`CLASS_6`, `CLASS_7`) enter the primary semantic endpoint. `CLASS_4` is **diagnostic
only** and is never pooled into the primary metric. `UNKNOWN`, `AMBIGUOUS` and
`UNJUDGEABLE` are three *distinct* non-target codes and are never merged into a target
class or into a single "other" figure. Confidence (1–3) is recorded and is never used to
drop a sample from the primary analysis.

The ontology is **palm-relative throughout**: the representation carries no wrist or
forearm degree of freedom, so a world-referenced "up" is not representable and is never
asked for. No label depends on physical contact — the rendered hand is a generic mesh
with no soft-tissue or force model.

### Gates and controls

| control | what it protects against |
|---|---|
| Selection uses only session identity, recorded time position and the official ground-truth-validity boolean | a sample chosen to suit a model outcome |
| Model output, decoder probabilities/margins, support/OOD distance, predicted pose, stage names and gestures are excluded from selection and from both annotator arms | the answer key leaking into the instrument |
| Fixed, non-rotatable camera; exactly two views; constant zoom | view and framing becoming a confound, and a closed fist being scaled to look like an open hand |
| Left-hand items rendered from an analytic mirror of the frozen hand geometry, by a derived and separately proved rule | left-hand poses showing the thumb on the wrong side of the palm |
| 36 hidden duplicates placed in the far half of the item order from their original | inflating intra-rater reliability by positional proximity |
| Annotator-facing payload contains exactly `{blind_id, position, frames}`; the served tree is a per-annotator staging vault, not the repository | evaluator manifests being reachable over HTTP |
| Sampling reproducible by seed, with a drift check that refuses to run if the algorithm changed | silent resampling |
| Human analysis ordered strictly **before** model unblinding | post-hoc adjustment of the reference set |

### Freeze points

* The **label ontology** is frozen: no later disagreement may revise it, and remaining
  ambiguity is accepted as genuine annotation uncertainty.
* The **primary evaluable set** is defined *before* unblinding: unique windows where both
  annotators gave the **same** code **and** that code is one of the five primary classes.
  Disagreement items are never forced into a class.
* The **36 duplicates** measure each annotator's own consistency and never enter a
  semantic statistic.
* No **post-hoc adjudication**: disagreements are never resolved after model outputs have
  been seen, and no prediction may influence a consensus.

## 3. Deliberately withheld — and why

The following are excluded on purpose. They are not missing by accident.

| withheld | why |
|---|---|
| Hidden sample manifests and hidden duplicate maps | evaluator-only; they identify repeats and encode source session / frame / side |
| Unblinding keys, unblinding scripts, and any file whose purpose is to reveal S6 outcomes | would defeat the blinding the lane is built on |
| The selective-head prospective arm | a separate endpoint. It was **excluded because it is now unblinded** and contains prospectively collected human labels plus model endpoints — not because it is pending |
| Per-annotator raw label exports, per-annotator directories and payloads | per-rater raw data; publishing them would also expose the reference labels item by item |
| Annotator identities, names, addresses, machine names, participant information | personal and identifying data |
| Per-annotator distribution bundles and localised annotation packages | contain per-annotator payloads and a localised launcher page |
| Bundled third-party JavaScript and 3-D assets | redistributable status not verified; a licensing question, not a curation preference |
| Archives, screenshots, per-annotator HTML captures, machine-readable witness files | operational evidence containing per-rater or per-machine detail |
| The operational runbook and sampler/build tools | operational rather than definitional, and they carry local environment paths |

## 4. Status of the lane as observed

**The formal round did not conclude as pre-registered, and this subset publishes no
semantic endpoint.**

What the artefacts show:

* This curatorial review found **no per-annotator export in the lane's own drop
  directory** — it holds only its placeholder file.
* The lane nevertheless contains a frozen **interim checkpoint** of the two formal
  annotator exports at **200 of 396 labelled items each**, with recorded hashes and export
  timestamps.
* A **diagnostic model-unblinding** was executed on that checkpoint, and its own record
  states that it **broke the model-blindness covenant** to do so.
* That diagnostic is marked diagnostic-only, is **not** the final 360-window estimate and
  is **not** the pre-registered endpoint. Its agreement figures are computed on the
  *overlap* of two partially-labelled subsets, an overlap that is not a random sample of
  the benchmark.
* The lane's own pre-registration requires **both** annotators to finish **all 396 items**
  before any model output is computed. Running a diagnostic at 200/396 means the
  pre-registered human-only step was **not** completed as specified before unblinding.

> **Consequence.** The pre-registered primary endpoint cannot be produced by the
> pre-registered pipeline. Any later full-set figure would be a post-unblinding secondary
> analysis, not the pre-registered primary result.

Whether the two formal annotators ever reached 396/396 is **not established** by these
artefacts: no post-checkpoint export is present and the runbook still describes the round
as awaiting annotators. Recorded as unresolved rather than inferred.

**Therefore no number from the withheld material is upgraded to a finished public result
here, and no semantic endpoint is stated.** Because the reference labels are withheld, the
endpoint is not independently reproducible from this subset alone.

### Staleness warning about the copied documents

The copied files are frozen snapshots and some predate the lane's final state:

* `LABEL_DEFINITIONS.md` is the **Pilot-1-era** statement. The frozen **formal** ontology
  is the later Pilot-3 wording (thumb judged at the **thumb base / first web space**;
  `CLASS_1` vs `CLASS_6` decided by the thumb base; `CLASS_4` carrying a **hard fist
  exclusion**). That wording is described, with its content hash, in
  `formal_s6/ONTOLOGY_FREEZE.json`, which is the authoritative record here.
* The two analysis documents are the full 360-window plans. The formal round's operative
  pre-registration is `formal_s6/FORMAL_ANALYSIS_PREREGISTRATION.md`;
  `FUTURE_ANALYSIS_PLAN.md` is the earlier plan for the same instrument.

## 5. Contents

| path | role |
|---|---|
| `README.md` | this curation note (written for this mirror; not a lane source file) |
| `LABEL_DEFINITIONS.md` | label definitions, discriminators, machine label codes |
| `ANNOTATION_PROTOCOL.md` | annotator instructions, operator procedure, rendering contract |
| `BLINDING_SPEC.md` | what is hidden, how it is enforced, how the blinding claim is checked |
| `FUTURE_ANALYSIS_PLAN.md` | the earlier pre-registered endpoint plan for the 360-window set |
| `formal_s6/FORMAL_ANALYSIS_PREREGISTRATION.md` | the formal round's registration (human step → evaluable-set freeze → model unblinding) |
| `formal_s6/ONTOLOGY_FREEZE.json` | the frozen formal ontology, its content hash and the standing commitments |

## 6. What a reader would need from the authors to reproduce the endpoint

This subset defines the instrument; it cannot reproduce the endpoint. Reproducing it would
require, from the authors:

1. the two frozen formal annotator exports (396 labelled items each) with their recorded
   SHA-256 values and export timestamps;
2. the hidden duplicate map, needed for the intra-rater statistics and for excluding
   duplicates from every semantic statistic;
3. the evaluator-side sample manifest (source session, frame indices, hand side per item),
   needed for the handedness stratification the plan requires in every table;
4. the sampling specification and seed, so the 360-window draw can be re-derived;
5. the corpus-integrity record for the underlying recordings;
6. the frozen decoder and pose-estimator checkpoints, the canonical mapping between them,
   and the decoder handshake evidence;
7. the executed analysis code, so the pre-registered statistics can be recomputed rather
   than taken on trust;
8. a decision record on how the 200/396 interim unblinding affects the status of the
   formal endpoint, since it post-dates the pre-registration's ordering requirement.

Recipes in the copied documents may reference lane-local tool paths; those are operational
details of the original environment and are intentionally not reproduced as instructions.
