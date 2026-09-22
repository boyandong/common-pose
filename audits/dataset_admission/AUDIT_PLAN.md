# DATASET ADMISSION & COORDINATE PROVENANCE AUDIT — FROZEN PLAN

**Lane:** `<DATA_ROOT>set_admission_audit_v1\`
**Branch id:** `S7-DATASET-ADMISSION-COORDINATE-AUDIT`
**Plan version:** 1
**Status when written:** frozen **BEFORE** any measurement or statistic of this audit was run
**Write discipline:** `encoding='utf-8', newline='\n'`, no BOM; the file is hashed as raw bytes and is never re-serialised.

---

## 0. What this plan is, and what it is not

This is a **DATASET ADMISSION / COORDINATE PROVENANCE AUDIT**.

It is **not** model work, not tuning, not a benchmark. No neural network, no LDA, no SVM, no classifier of
any kind is trained or evaluated anywhere in this lane. No existing downstream result is read in order to
choose a column, a sign, an offset, a scale, a transform or a channel subset.

The single failure mode this audit exists to prevent is:

> "the numbers classify well, therefore they must be the anatomical joint angles we think they are."

A prior lane (`pose_coordinate_audit/`) is the historical origin of that lesson. Nothing in this audit reuses,
repairs or overwrites its artifacts.

---

## 1. Questions this audit answers, and the questions it refuses

**Answers (A–F):**

| id | question |
|---|---|
| A | what, exactly, is each candidate channel of each dataset |
| B | are its unit, direction, zero, calibration source and measured/derived status trustworthy |
| C | can the datasets be mapped into one physical API |
| D | are the labels themselves suitable as pose-based downstream targets |
| E | what is ADMIT / RESTRICT / DROP / INCONCLUSIVE per dataset and per channel |
| F | do the **physical-semantic** interpretations of our previous KIN-MUS `shared10_poc_v1` results still hold |

**Refuses to answer:** which model is better; whether a phase classifier can be improved; grasp-classifier
accuracy; final EMG→pose quality; whether the Common Hand Pose API ultimately succeeds.

---

## 2. Hard rules (binding on every script in this lane)

1. No deep-learning training. No formal downstream classifier. No model fitting of any kind.
2. No existing downstream performance is consulted when deciding any mapping.
3. Column, sign, offset, scale, transform and channel subset are decided **only** from: official schema,
   official paper/README, official calibration code, raw data structure, and physical movement anchors.
4. Where official sources conflict: **do not guess**. Record `DOCUMENTATION_CONFLICT`.
5. Where the released data cannot be independently reproduced from public files: never write `VERIFIED`.
   Write `TRANSFORM_NOT_INDEPENDENTLY_REPRODUCIBLE`.
6. A missing DOF stays missing. Prohibited substitutions include `PIP ≈ DIP`, `abduction ≈ flexion`,
   `derived ≈ measured`, and `this glove's CMC-abduction ≈ that glove's CMC-flexion`.
7. A channel with a wrong physical anchor direction is DROP/QUARANTINE however repeatable it is.
8. Old experimental results may be **re-interpreted** after this audit; they may never be used to justify a
   new semantic mapping.
9. No existing lane, result, manifest, checkpoint or artifact is modified. This lane is append-only and
   reads every other lane read-only.
10. Local machine: file inspection, hashing, metadata/schema parsing, light numpy/pandas statistics, plotting,
    parity scripts only. **No DL training, local or otherwise.**

---

## 3. Evidence tagging

Every substantive claim carries exactly one tag:

| tag | meaning |
|---|---|
| `[DOC]` | from official documentation / paper / README / licence |
| `[EMPIRICAL]` | measured by this audit directly from the raw/released data |
| `[INFERENCE]` | a reasoned conclusion from `[DOC]` + `[EMPIRICAL]` |
| `[UNRESOLVED]` | could not be established with the artefacts available |

`[DOC]` is never presented as `[EMPIRICAL]`. In particular: *the authors report that the calibration is
validated* is `[DOC]`; *this audit reproduced channel c of file f to within ε* is `[EMPIRICAL]`.

A claim that a transform is reproduced requires a number produced by a script in this lane.

---

## 4. Sources, in strict priority order

1. official dataset files actually present on disk or downloaded by this lane;
2. official dataset code (calibration / conversion);
3. the dataset's own peer-reviewed paper and its supplement;
4. the authors' own guide / README;
5. the dataset record (DOI landing page) metadata.

Third-party blogs, tutorials, mirrors and forum posts are **never** authoritative schema. Any such source, if
used at all, is tagged `[UNRESOLVED]` and cannot support a KEEP.

---

## 5. Directory contract

```
dataset_admission_audit_v1/
  README.md
  AUDIT_PLAN.md                 <- this file (frozen)
  PLAN_SHA256.txt               <- raw-byte SHA-256 of AUDIT_PLAN.md
  BUGFIX_LOG.md
  DATASET_MANIFEST.csv
  SOURCE_PROVENANCE.md
  SCHEMA_AUDIT.md
  COORDINATE_LEDGER.csv
  PHYSICAL_QC.md
  LABEL_AUDIT.md
  SYNC_AUDIT.md
  SHARED10_PROVENANCE_AUDIT.md
  COMMON_API_MAPPING_MATRIX.csv
  LABEL_ADMISSION_MATRIX.csv
  ADMISSION_DECISION.md
  ARTIFACT_MANIFEST.json
  scripts/      numbered, deterministic, re-runnable drivers
  artifacts/    machine-readable JSON/CSV outputs
  figures/      PNG evidence
  logs/         captured stdout of every driver
  raw/          downloaded official files (never modified after hash)
  raw_meta/     paper PDFs / extracted text
```

Naming: numbered `NN_name.py` drivers, never `final_v2`. One driver per artifact. Every driver writes its
own stdout to `logs/`.

---

## 6. The three datasets

| dataset | local status at freeze time |
|---|---|
| **MyoKi** | NOT present before this audit. Corpus is 145 463 536 055 B over 35 participant files on figshare (`10.6084/m9.figshare.28696778`, CC BY 4.0). This lane downloads ONLY the small official metadata/code set plus `Synchronicity_test.mat` (48 961 776 B), and records the remaining corpus as an explicit download requirement. |
| **KIN-MUS UJI** | present at `pose_api_dataset_admission/raw/kin_mus/KIN_MUS_UJI.mat`, 86 661 263 B, read-only. |
| **KINE-ADL / BE-UJI** | corpus NOT downloaded. This lane downloads only the official guide/data-dictionary inside the public Mendeley record if it is small; the main corpus stays a recorded download requirement. |

Download rule applied: if only small official metadata / schema / calibration code is missing, download it;
if the large body of data would be needed, **STOP and record a download requirement** rather than pull it.

---

## 7. Channel-order provenance protocol (the P0 question)

The exact chain to be established for `shared10_poc_v1`:

```
file name -> loader -> variable name -> exact source array -> shape -> schema/order -> index -> DOF
```

The order of a released numeric MATLAB array is **not** self-describing. Therefore, for every dataset, the
column order must be established from an authoritative source, and where two authoritative sources disagree
the conflict is recorded and an explicit discrimination procedure is executed.

**Pre-declared order hypotheses for the KIN-MUS 18-column block:**

* `H_GUIDE` — the order of the MOVMUS-UJI guide v2.1 (2023) Table 4 `ANGLES` block, right hand.
* `H_T2` — the order of the KIN-MUS dataset's **own** paper (Sci Data 6:270, 2019) Table 2
  ("Anatomical angles order (from top to bottom)"), which the paper explicitly attaches to the released
  `Angles (18 columns)` field.

**Pre-declared discrimination tests** (all model-free, all decided before seeing the numbers, all reported
for both hypotheses whether or not they agree):

| id | test | expectation |
|---|---|---|
| `D1` | the official calibration code gives `CMC1_A` a structurally smaller gain on the dominant gauge than `CMC1_F`; therefore the low-amplitude member of the first two columns is `CMC1_A` | a hypothesis that places `CMC1_F` on the low-amplitude column conflicts |
| `D2` | same-finger `MCP`↔`PIP` co-flexion: the MCP-flexion column of finger *k* must correlate more strongly with `PIP_k` than the competing abduction column does | the hypothesis naming the stronger partner `MCP_k_F` wins |
| `D3` | the dataset's own Technical Validation states that MCP and PIP **flexion** channels have a positive median and the largest range of motion | the hypothesis under which the four `MCP_k_F` columns have positive medians and large spread wins |
| `D4` | relative-abduction channels of adjacent fingers form a mutually positive block and are **negatively** coupled to the MCP flexion of the metacarpals they span | the hypothesis reproducing a physiologically coherent sign pattern wins |

Resolution rule: a hypothesis is accepted only if **no** test conflicts with it and at least three tests
positively favour it. Otherwise the order is `INCONCLUSIVE` and every dependent conclusion is downgraded.

Ties are not broken by "which one makes the downstream result look better". Downstream results are not read.

---

## 8. Confidence and admission vocabularies (closed sets)

`mapping_confidence` ∈ {`HIGH`, `MEDIUM`, `LOW`, `NONE`}

| value | criterion |
|---|---|
| `HIGH` | official source names the channel and its order unambiguously; unit and sign stated; order additionally corroborated by an independent empirical discriminator; no unresolved conflict |
| `MEDIUM` | official source names the channel; unit and sign stated; order corroborated by at most one weak empirical check, or a documented conflict exists but is resolvable in one direction |
| `LOW` | channel identity requires inference (e.g. position inferred from a numbered list that stops short of it); or sources conflict unresolved |
| `NONE` | no official basis for the identity, or the identity is contradicted by evidence |

`admission_status` ∈ {`KEEP`, `RESTRICT`, `DROP`, `INCONCLUSIVE`}

| value | criterion |
|---|---|
| `KEEP` | `HIGH` confidence, no known artifact, not silently derived, and physical-anchor test passes if one exists |
| `RESTRICT` | usable but with a named limitation that must travel with every downstream use |
| `DROP` | identity wrong, sign unverifiable, physically reversed, or derived-from-another-joint |
| `INCONCLUSIVE` | insufficient evidence to place in any of the above |

`dataset grade` ∈ {`GREEN`, `YELLOW`, `RED`, `GRAY`}

| value | criterion |
|---|---|
| `GREEN` | may enter the next phase, with explicitly named permitted uses |
| `YELLOW` | valuable but must be restricted; the restriction is named |
| `RED` | not suitable for the Common Pose API in its current role |
| `GRAY` | evidence insufficient; extra files or author data required |

A grade is never forced. `GRAY` is a legitimate terminal answer.

---

## 9. Physical-anchor protocol

For every candidate channel with a documented anatomical direction:

1. define the anchor action, its expected sign, and the population statistic **before** computing it;
2. compute the per-subject median delta;
3. report the sign-consistency rate with a Wilson 95 % interval;
4. frames are pooled **within** a subject; a subject is the unit of the consistency count, never a frame;
5. pass thresholds, pre-declared:

| outcome | criterion |
|---|---|
| anchor `PASS` | ≥ 80 % of subjects show the expected sign and the pooled median |delta| exceeds 2° |
| anchor `WEAK` | 60–80 % of subjects show the expected sign |
| anchor `FAIL` | < 60 % of subjects show the expected sign |

An anchor that is `FAIL` forces `DROP` or `QUARANTINE` for that channel's expected direction.
Anchors whose expected direction is genuinely ambiguous from the documentation are **reported, not scored**,
and are tagged `[UNRESOLVED]`.

Degenerate-anchor guard: an anchor whose expected direction is satisfied by a channel that never changes is
not a pass. Every anchor reports the full statistic, not only a boolean, so a reader can see the degeneracy.

---

## 10. Sampling-rate / synchronisation protocol

For every released continuous stream:

1. count the rows on the released grid;
2. count the number of rows that differ from their immediate predecessor (the **distinguishable-state
   count**);
3. report the ratio — the **representation inflation factor**;
4. an inflated stream may never be treated as independent samples: all rates, statistics and windows are
   computed on the distinguishable-state sequence or on a correctly resampled stream;
5. the distinguishable-state count is a **lower bound** on the true native rate (two consecutive acquisitions
   may carry identical values); it is never reported as the native rate.

Any conclusion that depends on treating repeated rows as independent is void.

---

## 11. Label protocol

Every label is classified on:

`annotation provenance` (frame-wise human / trial-level human / task-metadata lookup / continuous
segmentation / unknown), `frame-wise or trial-wise`, `pose-observable?`, `requires temporal context?`,
`requires object/context?`, `boundary reliability`, `subject coverage`, `class balance`, `known ambiguity`,
`recommended role`, `decision`.

Rules:

* a task-derived label is marked `LABEL_NOT_FRAMEWISE_GROUND_TRUTH` and may not be used as frame-wise truth;
* no trimming / windowing rule may be selected by classifier accuracy. Any trimming rule must follow from
  kinematic stability or from the documented protocol, and must be frozen before any classifier exists;
* a label whose definition depends on object identity or scene context is not a pose-based target.

`decision` ∈ {`ADMIT`, `RESTRICT`, `REJECT`, `INCONCLUSIVE`}

---

## 12. Common API protocol

Two questions are kept strictly separate for every cell:

* **semantic anatomical correspondence** — is this the same anatomical DOF?
* **numerical coordinate equivalence** — are the two numbers on the same unit / zero / calibration?

If the joint name matches but zero or calibration equivalence cannot be demonstrated, the cell is
`semantic = YES`, `numeric = UNVERIFIED`. The word *equivalent* is reserved for cells with a demonstrated
shared zero and unit.

`CommonPoseSubset_v2_candidate` membership requires **all nine**:

1. anatomical identity clear; 2. unit clear; 3. sign clear; 4. zero/reference sufficiently understood;
5. not known broken; 6. not silently derived from another joint; 7. available in at least two target
datasets; 8. physical-anchor behaviour reasonable; 9. calibration provenance documented.

Preference order: `MCP flexion`, `PIP flexion` first; `thumb CMC`, `abduction`, `wrist`, `DIP` more
conservatively. Eight trustworthy DOFs is preferred over sixteen semantically confused ones.
Selection is **not** informed by any downstream result.

---

## 13. Mandatory STOP conditions

Any one of these stops that dataset entering a model phase; it does not stop the audit:

source array schema unconfirmable; column order untraceable; unit unconfirmable; key sign convention in
unresolvable conflict; an expected-and-available raw→processed parity fails; a candidate channel's physical
anchor is plainly reversed; subject IDs with unexcludable leakage; label provenance different from our
assumption; a task label plainly dependent on object/context rather than pose; most key Common-API channels
only `LOW`/`NONE`; dataset file version undeterminable.

A STOP restricts the source's role. It is not a project failure.

---

## 14. Old-result re-classification protocol

For every prior result that touched the audited channels, exactly one class is assigned:

* `A — numerical-feature result still valid`: the exact same numbers were used; the statistics are unchanged.
* `B — physical-DOF interpretation invalid`: the numbers stand, the anatomical naming does not.
* `C — both invalid`: the numbers themselves depended on the wrong identity (e.g. a subset chosen by DOF).
* `NEEDS_RERUN` / `UNCHANGED` / `INTERPRETATION_DOWNGRADED` / `INVALIDATED` for the summary line.

A blanket "everything is void" is forbidden; so is a blanket "nothing changed".

---

## 15. Reproducibility

Every artifact records: source file path, source byte size, source SHA-256, the driver that produced it, the
frozen plan SHA-256, and the date. Where a git commit is unavailable for the project root (this project root
is not a git repository) every artifact states `COMMIT PENDING` and provenance is content-hash based.

`scripts/fact_check_audit.py` re-derives the load-bearing numbers from the artifacts and asserts them; it is
run last. A green fact check is the only accepted completion evidence.

---

## 16. Deliverable

`ADMISSION_DECISION.md`, opening with a one-page executive summary, then per dataset:

`physical coordinate admission`, `EMG→pose suitability`, `downstream task suitability`, `strongest safe
channels`, `unsafe channels`, `unresolved blockers`, `recommended role`, `grade`.

Then the `SHARED10_poc_v1` verdict with an explicit, per-claim list of what must be retracted, what is
downgraded, and what is untouched.

---

## 17. Reconstruction disclosure (honesty clause)

Reconnaissance was performed before this plan was written: directory inventories, hashes, paper/guide
extraction, and short exploratory scripts (`scripts/_probe_*.py`, `scripts/_pdf_coords*.py`,
`scripts/_guide_coords*.py`). Those scripts are **reconnaissance, not evidence**. They are retained for
traceability and are explicitly excluded from the audit's evidence chain.

Consequences, stated plainly:

* the plan's vocabularies, thresholds and decision rules were written after that reconnaissance, but they
  were written **without reference to any downstream or model performance number** — none was computed;
* every number that appears in an artifact of this audit is recomputed by a numbered driver in `scripts/`,
  whose output is captured in `logs/`, and re-derived by `fact_check_audit.py`;
* the reconnaissance did surface the KIN-MUS column-order question. That question is a documentation
  question, not a results question, and the four discrimination tests in §7 plus their resolution rule are
  recorded here so that a reader can see they do not depend on any outcome. The tests are re-run by the
  numbered drivers and reported in full for **both** hypotheses.

No admission rule in this plan is a function of a measured value.
