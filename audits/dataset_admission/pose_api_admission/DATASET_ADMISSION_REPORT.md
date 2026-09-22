# DATASET ADMISSION AUDIT — HUST / KINE-ADL / KIN-MUS

**Branch:** `S6-POSE-API-DATASET-ADMISSION`
**Lane:** `<PROJECT_ROOT>\pose_api_dataset_admission\` (new; no other lane written to)
**Classification:** DATASET-SELECTION / REPRESENTATION-COMPATIBILITY AUDIT
**Frozen plan SHA-256:** `4d2c8b162e2332a5891a5d89a53166e365b1bbd92c205222492d19957c9683ec`
**Access date for every source:** 2026-09-21
**Fact check:** `tools/dataset_admission_fact_check.py`

---

## 0. THE DECISION

| dataset | status |
|---|---|
| **HUST** | **REJECT** |
| **KINE-ADL BE-UJI** | **CONDITIONAL** |
| **KIN-MUS UJI** | **ADMIT** |

> # FIRST_POC_DATASET = **KIN-MUS UJI**
> **DOI 10.5281/zenodo.3469380** · CC-BY-4.0 · 22 subjects · 26 ADLs · 3 phases ·
> 564 894 usable frames

**The representation this choice implies: `shared10_poc_v1` — 10 API DOFs, all at
HIGH confidence** (the four non-thumb MCP flexions, the four non-thumb PIP
flexions, thumb CMC flexion, thumb MCP flexion).

**No model was trained. No pose was scored. No threshold was fitted.** The next
experiment is designed and *not* executed.

---

## 1. Objective

Answer one question: **which external kinematic dataset is technically qualified
to become the first serious source dataset for the Common Pose API?** The
long-term architecture (wearable EMG → frozen EMG→pose head → Common Physical
Pose API → downstream task model from an independent kinematic dataset) is **not**
tested here. Only the dataset choice is.

DB9 is closed (`DB9-DROP`) and appears in this audit **only** as historical
context and as the origin of two criteria: the minimum-shared-DOF gate and the
rule that semantic names are not evidence.

---

## 2. Branch classification and pre-registration

`DATASET-SELECTION / REPRESENTATION-COMPATIBILITY AUDIT`. Not a Gate session, not
a training session, not a DB9 rescue, not domain adaptation.

The plan was written and hashed **before** any candidate was compared, before any
shared-DOF count existed, and before any status was assigned. It froze: the
candidate set and the backup rule, the source-of-truth hierarchy and the five
evidence tags, the API DOF set recovered from the project's own adapter, the
mapping rules and confidence classes, the admission and rejection criteria, the
`MIN_COMMON_DOFS = 8` (≥ 6 HIGH) and `MIN_SUBJECTS = 15` gates, the quality
gates, the anchor tiers, the label-suitability classes and the selection priority
order. **No criterion was changed after any dataset looked favourable.**

---

## 3. Headline provenance findings

Three findings a reader must not learn anywhere else.

**(a) The publication behind HUST was RETRACTED by PLOS ONE on 4 March 2016.** The
notice states the editors "consider that the work cannot be relied upon" and that
the evaluation "confirmed concerns with the scientific rationale, presentation and
language, which were not adequately addressed during peer review." The Dryad
record that hosts the data carries the retraction **in its own title**.

**(b) HUST's raw data is not obtainable.** Three independent routes were tried:
the published download URL returns **HTTP 500** with a "resource not found" body;
the **Wayback Machine holds no capture** of `HUSTdataset.zip`; and the Dryad
download endpoint is behind an **Anubis proof-of-work interstitial** (HTTP 403 to
an automated GET). No bytes were obtained.

**(c) "KINE-ADL BE-UJI" is real and was located.** It is the Mendeley Data record
`10.17632/8mf4y2srgh.4`, *"KINE-ADL BE-UJI: Kinematics of human hand dataset for
feeding and cooking tasks"*, CC BY 4.0 — 20 subjects, 1160 continuous calibrated
recordings at 100 Hz, CyberGlove, **18 DoF on each hand**, 66 objects.

---

## 4. Data sources and official references

Full detail with URLs and access dates: `OFFICIAL_SOURCE_REFERENCES.md`.

| source | what it establishes | tag |
|---|---|---|
| handcorpus HUST page | 16 DOF, radians, 100 Hz, CyberGlove, 33 Feix tasks, 30 subjects, right hand | OFFICIAL-DOCUMENTED |
| PLOS ONE `10.1371/journal.pone.0146193` | **RETRACTED**; pre-retraction protocol text | OFFICIAL-DOCUMENTED |
| Dryad `10.5061/dryad.gg8g5` | 17 641 156 B, title records the retraction | OFFICIAL-DOCUMENTED |
| Mendeley `10.17632/8mf4y2srgh.4` | KINE-ADL BE-UJI: 20 subjects, 1160 recordings, 18 DoF/hand, CC BY 4.0 | OFFICIAL-DOCUMENTED |
| Zenodo `10.5281/zenodo.3469380` | KIN-MUS UJI: 86 661 263 B, CC-BY-4.0, structure and phase semantics | OFFICIAL-DOCUMENTED |
| Scientific Data `10.1038/s41597-019-0285-1` | 572 recordings, 22 subjects, 26 ADLs, "eighteen hand anatomical angles … by a validated calibration procedure" | OFFICIAL-DOCUMENTED |
| MOVMUS-UJI guide v2.1 (72 pp) | the 18-angle layout, sign criteria, reference posture, filtering, outlier procedure, channel malfunction disclosure | OFFICIAL-DOCUMENTED |
| BE-UJI `AngleCalculation.zip` (**downloaded and read**) | `gains_identification.m`, `obtain_angles_RL_abd_rel.m` — the actual gain/angle formulas | OFFICIAL-CODE-INFERRED |
| Zenodo `10.5281/zenodo.6548190` (**downloaded**) | the group's own study of the DIP measurement problem, with PIP/DIP static-posture controls | OFFICIAL-DOCUMENTED |
| project `canonical_hand.py` + contract | the API DOF set, units, sign rules, validity semantics | PROJECT-FROZEN |

**Network caveat recorded for reproducibility:** this host's resolver answers
`zenodo.org` with `0.0.0.0`; the audit resolves it through an explicit public
resolver and passes the address to `curl --resolve`. That is a local DNS
workaround for a name that resolves publicly — not a bypass of any access control.
Every file fetched is open access under the licence recorded above.

---

## 5. Access + licence status

`DATASET_ACCESS_AND_LICENSE.json` — availability established by **attempt**, not by
a paper's claim.

| | HUST | KINE-ADL | KIN-MUS |
|---|---|---|---|
| downloadable today | **NO** | yes (metadata verified) | **YES (86 661 263 B fetched)** |
| license | **UNKNOWN** (no licence field retrievable) | CC BY 4.0 | **CC-BY-4.0** |
| registration | none | none | none |
| empirical QC | **NOT POSSIBLE** | PARTIAL | **DONE** |
| documentation audit | COMPLETE | COMPLETE | COMPLETE |

**Bounded-download compliance:** 97.5 MB of raw evidence total. Explicitly *not*
downloaded: `MOVMUS-UJI_DATASET.zip` (4.59 GB), `CALIBRATED_KINEMATIC_DB_v2.zip`
(6.50 GB), `RAW_EMG.mat` (128 MB — EMG is irrelevant to a pose-admission
decision).

---

## 6. The Common Pose API requirement

`COMMON_POSE_API_REQUIREMENTS.json` — recovered from `canonical_hand.py`,
`canonical16_schema.json`, `CANONICAL16_CONTRACT.md` and
`joint_angle_definition.md`, all SHA-256-pinned in the frozen plan. **Nothing is
reconstructed from memory.**

* **canonical16** = 16 variables: thumb (CMC-FE, CMC-AA, MCP-FE, IP-FE), then
  index/middle/ring/pinky at MCP, PIP, DIP.
* unit **radians**; **positive = flexion** for the 15 F/E variables;
  `thumb_cmc_ab_adduction` has **NO globally meaningful sign rule**.
* It is **lossy**: the four non-thumb MCP-AA axes are dropped by design, so
  canonical16 is **not** a complete hand pose.
* An IK failure is an **all-zero row, not NaN**; the mask must be applied.
* `canonical18` (two finger spreads) is **RESERVED_DISABLED**; no spread formula
  exists anywhere in the repository.

**The decision this audit had to make — API-16 or a smaller rigorously shared
subset — was made as: a smaller subset, on physical semantic grounds.**

---

## 7. HUST audit

`HUST_SOURCE_AUDIT.json`, `HUST_QUALITY_AUDIT.json`,
`HUST_PHYSICAL_ANCHOR_AUDIT.json`

| item | finding |
|---|---|
| exact title/version | "HUST Dataset (March 2016)", handcorpus.org |
| official source | `handcorpus.org/datasets/HUSTdataset.zip` (HTTP 500) ; Dryad `gg8g5` (PoW-blocked) |
| claimed ~16 DOF structure | **16 DOF confirmed as a COUNT only** — the page publishes no joint list |
| exact joint list | **UNAVAILABLE** |
| anatomical or glove-derived | **UNKNOWN** (CyberGlove named; procedure unobtainable) |
| units | page claims **radians**; unverifiable |
| zero convention | **UNKNOWN** |
| laterality | right hand only (page: subjects placed their right arm on the table) |
| subject count | claims 30 |
| Feix mapping | 33 task types claimed |
| continuous transition samples | the protocol describes reach→grasp; whether the release separates them is UNKNOWN |
| comparability to emg2pose DOFs | **0 of 16 establishable** |
| access/license | inaccessible; licence UNKNOWN |
| publication integrity | **RETRACTED** |

**Status: REJECT** on criteria 1, 2, 3, 5, 6, 7 (untestable), 8. Ten criteria
lines are enumerated in `FIRST_POC_DATASET_DECISION.json`; the verdict is not an
opinion.

---

## 8. KINE-ADL BE-UJI audit

`KINE_ADL_SOURCE_AUDIT.json`, `KINE_ADL_QUALITY_AUDIT.json`,
`KINE_ADL_PHYSICAL_ANCHOR_AUDIT.json`

| item | finding |
|---|---|
| exact record | Mendeley Data `10.17632/8mf4y2srgh.4`, CC BY 4.0 |
| acquisition hardware | **CyberGlove instrumented gloves, BOTH hands** |
| how sensors→angles | the published Gracia-Ibáñez across-subject calibration protocol, implemented in the released BE-UJI MATLAB code — **this audit downloaded and read the code** |
| per-subject vs global calibration | **PER GLOVE UNIT, applied across subjects.** The code hard-codes the UJI lab's own gains and says in a comment: *"Gains values should be completed with own glove gains"* |
| exact zero/reference | **recorded reference posture**: hands flat on the table, fingers and thumb together, middle fingers aligned with the forearms |
| units/sign | degrees; full published sign-criteria list (flexion+, abduction+, separation+, ulnar deviation+) |
| task hierarchy | activity / task / object, with **66 objects**; 1160 continuous recordings at 100 Hz |
| pose-observable labels | plausible for the ADL family but **not established**: the corpus was not downloaded, so segmentation is unverified |
| subjects | 20 |
| handedness | both hands |
| license/access | CC BY 4.0, accessible |

**Status: CONDITIONAL.** The pipeline is documented and auditable — a genuine
advance over DB9 — but **the corpus itself has not been measured** and it is **not
independent physical evidence** (§12). The promotion path is exact and cheap:
download the corpus, confirm its channel list against the documented 18, and
re-run this branch's anchor and quality builders *unchanged*.

---

## 9. KIN-MUS UJI audit

`KIN_MUS_SOURCE_AUDIT.json`, `KIN_MUS_QUALITY_AUDIT.json`,
`KIN_MUS_PHYSICAL_ANCHOR_AUDIT.json`

| item | finding |
|---|---|
| exact record | Zenodo `10.5281/zenodo.3469380`, CC-BY-4.0, `KIN_MUS_UJI.mat` (86 661 263 B) |
| 18-angle representation | confirmed: `Kinematic_data` is **(N, 18)**, matching the documented layout |
| kinematics same as KINE-ADL? | **YES — same group, same glove family, same BE-UJI code, same calibration protocol** |
| subjects | 22 |
| structure measured | 1716 trial containers = 22 × 26 ADLs × 3 phases; **1713 usable**; 564 894 frames |
| phase semantics | 1 reaching, 2 manipulation, 3 release |
| EMG | 7 channels present; **NOT downloaded and irrelevant to this decision** |
| can EMG be ignored for Task-Head construction | **YES** |
| later EMG validation arm | **YES** — the same corpus carries 7 sEMG spots, so a later EMG→pose arm can be run on the same source data |
| pose-observability | **the phase label is pose-observable; the 26 ADL identities are not** |
| licensing/access | CC-BY-4.0, open, fetched today |

**Measured data quality:**

* **no NaNs, no constant channels, no aliased channels, no artefactual saturation**
* **3 of 1716 trials are empty containers** (subjects 21/22, ADL 25) and **2 cells
  are duplicated** — recorded, excluded, never repaired
* temporal steps are smooth; the largest single-frame jumps sit at the documented
  5 Hz two-way low-pass filter's expectation
* units corroborated as degrees by range plausibility

**Status: ADMIT** — all eleven ADMIT criteria pass, and the limitations below are
**named** rather than hidden.

---

## 10. Angle-origin comparison — the decisive criterion

`ANGLE_ORIGIN_AND_CALIBRATION_AUDIT.json`

| | HUST | KINE-ADL | KIN-MUS |
|---|---|---|---|
| category | instrumented glove (procedure UNKNOWN) | **GLOVE + CALIBRATION TRANSFORM** | **GLOVE + CALIBRATION TRANSFORM** |
| calibration documented | **UNKNOWN** | published protocol + released code | published protocol + released code |
| per-subject calibration | UNKNOWN | **NO — per glove unit** | **NO — per glove unit** |
| cross-talk | UNKNOWN | **YES, explicitly modelled** | **YES, explicitly modelled** |
| DIP | UNKNOWN | **derived from PIP, clipped affine** | **not released at all** |
| quality metrics | UNKNOWN | partial | partial |
| verdict | **INDETERMINATE** | documented, two concrete limits | documented, two concrete limits |

**What "GLOVE + CALIBRATION TRANSFORM" means here, from the code itself.** Every
angle is `(raw_gauge − raw_reference_gauge) × gain`, with:
a 2×2 cross-coupling mix for `CMC1_F`/`CMC1_A`; quadratic-plus-interaction models
for the three relative abduction channels; a quadratic-plus-cross term for the
wrist; and **`DIP = 0.87·PIP − 25.27`, floored at 0** for the 18-sensor glove. The
thumb IP channel reuses `RG_PIP(1)`.

**No audited candidate uses motion capture.** All three are strain-gauge glove
datasets, while emg2pose is an **inverse-kinematics fit of a generic hand model to
motion capture**. That metrological gap is the same one that broke DB9, and it is
**not closed by this audit** — it is measured and named.

**Why the UJI family is nevertheless materially better than DB9:** the calibration
protocol is published and the code is released, so the transform is *auditable*;
cross-coupling is explicitly *modelled*; the reference posture is documented with
a figure; sign criteria are published per channel; the outlier procedure and its
exact counts are disclosed; and a malfunctioning channel was detected and
**disclosed** rather than shipped.

**What remains weak, stated plainly:**
* calibration is per glove unit, not per subject, and the group **itself** links a
  small-hand subject to an outlier cluster — the same failure axis DB9 documented;
* DIP carries **no independent information**;
* the released KIN-MUS block is **one hand and does not label which**.

---

## 11. DOF compatibility matrix

`POSE_API_DOF_MAPPING_MATRIX.{csv,json}` — one row per API DOF per dataset, plus an
18-entry **release inventory** so every released column is accounted for exactly
once.

| confidence | UJI family | HUST |
|---|---|---|
| **HIGH** | **10** | 0 |
| MEDIUM | 2 | 0 |
| LOW | 0 | 0 |
| **NONE** | 4 | 16 |
| **HIGH + MEDIUM** | **12** | **0** |
| gate (8, ≥6 HIGH) | **PASS** | FAIL |

**HIGH (10):** `thumb_cmc_flexion`, `thumb_mcp_flexion`, `index_mcp_flexion`,
`index_pip_flexion`, `middle_mcp_flexion`, `middle_pip_flexion`,
`ring_mcp_flexion`, `ring_pip_flexion`, `pinky_mcp_flexion`, `pinky_pip_flexion`.

**MEDIUM (2), excluded from the POC:** `thumb_cmc_ab_adduction` (cross-dataset
axis correspondence unproven — the project's own contract flags it) and
`thumb_ip_flexion` (the code reuses a PIP gain constant).

**NONE (4):** all four DIPs — **no released column exists**, and the code derives
DIP from PIP.

### Three matches that were REFUSED

| tempting match | why refused |
|---|---|
| `MCP2-3_A`, `MCP3-4_A`, `MCP4-5_A` → the four dropped MCP-AA axes | they are **relative inter-finger spreads**, not per-finger MCP abduction; mapping them would inflate the shared-DOF count on a false premise |
| `DIP2..DIP5` → index/middle/ring/pinky DIP | no DIP column is released; a clipped surrogate is not an independent measurement |
| `PalmArch` | no canonical16 counterpart |

**Six released UJI columns have no API counterpart** (three spreads, the palmar
arch, and two wrist angles). They are reported, not discarded.

---

## 12. Physical-anchor results

`KIN_MUS_PHYSICAL_ANCHOR_AUDIT.json` — **the test that exists to prevent another
DB9 failure.** Tier is recorded for every anchor; frames are never
pseudo-replicated as subjects.

| anchor | tier | result |
|---|---|---|
| **manipulation vs reaching flexion** | WEAK | **PASS — 22/22 subjects positive**, median **+66.44°** flexion-sum; PIP +13.08°, MCP +0.57° |
| **reference-posture zero** | STRONG | **PASS** — no channel shows a large uniform offset relative to its documented sign range |
| **homologous fingers** | WEAK | **PASS** — no homologous channel is an outlier |
| **open hand on the low side of range** | STRONG | **PASS** — the p5 of every MCP/PIP flexion channel is at or below the reference posture |

> **The DB9 contrast, stated once.** On DB9 the analogous documented-direction test
> failed in **100 % of subjects** for three DIP channels. Here the analogous test
> passes in **every subject** for every mapped channel. This is the single most
> important empirical difference between the two source datasets.

For HUST the anchor tiers cannot even be assigned: sign conventions, zero, and the
channel list are all UNKNOWN. For KINE-ADL the tests are specified and listed, but
not run.

---

## 13. Repeatability / data quality results

| | HUST | KINE-ADL | KIN-MUS |
|---|---|---|---|
| NaNs | not testable | not measured | **0** |
| constant channels | not testable | not measured | **0** |
| aliased / duplicated channels | not testable | not measured | **0** |
| artefactual saturation | not testable | not measured | **none found** |
| discontinuities | not testable | not measured | smooth; consistent with the documented 5 Hz filter |
| unit consistency | not testable | pipeline-level yes | **degrees corroborated** |
| within-subject repeatability | not testable | **UNKNOWN** | **not computable** |
| malformed trials | not testable | not measured | **3 of 1716 (0.17 %)** |
| subject-specific failures | not testable | not measured | 2 subjects, both ADL 25 |

**On repeatability, stated honestly:** KIN-MUS records each subject × ADL × phase
**once**. There are no repeated trials, so **no within-subject repeatability
statistic can be computed** — and the audit does **not** substitute an
across-frame statistic and call it repeatability. What is reported instead is
within-trial temporal smoothness and across-subject agreement on the same ADL.

---

## 14. Task-label suitability

`DATASET_TASK_STRUCTURE.json` — grasp type, object identity, activity label and
action primitive are **never** collapsed into the word "gesture".

| | HUST | KINE-ADL | KIN-MUS |
|---|---|---|---|
| ontology | **grasp taxonomy** (Feix, 33) | **ADL activity + object** (66 objects) | **ADL activity (26) + movement phase (3)** |
| labels pose-determined? | plausible | partly | phase: **yes**; ADL: no |
| classification | UNCERTAIN (unverifiable) | POSE-MOSTLY-SUFFICIENT (unverified) | phase = **POSE-SUFFICIENT**; ADL = **NOT-POSE-SUFFICIENT** |
| needs force/object/contact/intention | likely object + contact | **object identity, environment** | ADL: object + intention; **phase: none** |

**Static vs temporal.** KIN-MUS's phase label admits a single-frame form, which is
why it was chosen first. A phase is a movement segment, so a short local temporal
context is a legitimate future refinement — but the first POC deliberately starts
with the single-frame form, which needs **no temporal alignment between datasets**.

---

## 15. Dataset independence

`DATASET_INDEPENDENCE_MATRIX.json`

**KINE-ADL vs KIN-MUS: NOT INDEPENDENT.** Of the seven plan dimensions, **five are
effectively shared** — research group, hardware family, calibration method, hand
model, preprocessing code. Only the task ontology and the specific subject sample
differ. A physical defect in the CyberGlove + BE-UJI pipeline would appear in
**both**.

> **The central limitation of the whole candidate pool.** Across all three
> candidates there is exactly **one physical pipeline family** (CyberGlove + a
> linear/quadratic gain calibration) and at most two independent instances of it.
> There is **no motion-capture-derived candidate at all**, while emg2pose itself
> is IK-over-motion-capture. A second *independent* physical source must come from
> a different sensor family (motion capture, IMU fusion, or vision-based hand
> pose) before any claim that the physical coordinates are *right*, rather than
> that one glove pipeline is self-consistent.
>
> **This audit did not expand the candidate list to find such a source.** The
> frozen backup rule triggers only if all three primaries are REJECT, and one is
> ADMIT. DLR and UNIPI were therefore **not** audited — a deliberate rule
> application, recorded so the omission is visible.

---

## 16. External emg2pose test feasibility

`EXTERNAL_TEST_FEASIBILITY.json` — **planning only; nothing was scored.**

* **Pose source:** the frozen GT canonical16 corpus,
  `bridge_audit/results/sessions/*.paired50hz.npz :: gt16` — 30 sessions,
  86 858 valid rows. **No new inference, no VEMG2Pose prediction, no new sampling.**
* **The decisive feasibility point:** the only candidate whose external test needs
  **no new human annotation and no task-specific EMG** is the one whose source
  labels are **pose-defined**. KIN-MUS's phase label is close to that.
* **Scope caveat carried into every number:** the mini corpus is **one subject**
  over 30 sessions. Every external result is **within-subject**.
* **Official generalization axes** (`none`, `stage`, `user`, `user_stage`) are
  available on the *full* dataset and would be required for any cross-subject
  claim later. They are not available in the mini corpus.

---

## 17. Admission decision

| | HUST | KINE-ADL | KIN-MUS |
|---|---|---|---|
| **Access** | ✗ HTTP 500 / PoW / no archive | ✓ | ✓ 86.7 MB fetched |
| **License** | ✗ UNKNOWN | ✓ CC BY 4.0 | ✓ CC-BY-4.0 |
| **Subjects** | claim 30, unverifiable | 20 | **22** |
| **Raw pose quality** | not testable | not measured | **clean** |
| **Angle origin** | ✗ UNKNOWN | ✓ documented+code | ✓ documented+code |
| **DOF clarity** | ✗ count only, no list | ✓ 18 named | ✓ 18 named, (N,18) |
| **Unit clarity** | claim only | ✓ degrees | ✓ degrees |
| **Sign clarity** | ✗ UNKNOWN | ✓ published | ✓ published |
| **Zero clarity** | ✗ UNKNOWN | ✓ recorded reference | ✓ recorded reference |
| **Calibration quality** | ✗ UNKNOWN | ~ per glove unit; modelled cross-talk | ~ per glove unit; modelled cross-talk |
| **Shared DOFs** | ✗ 0 | ✓ 12 (10 HIGH) | ✓ **12 (10 HIGH)** |
| **Handedness** | right only | both | **~ one hand, unlabelled** |
| **Repeatability** | not testable | UNKNOWN | **not computable (no repeats)** |
| **Physical anchors** | not assignable | not run | **all PASS, 22/22** |
| **Pose-observable labels** | plausible, unverifiable | partial | ✓ **phase yes** |
| **Temporal requirement** | unknown | segmentation needed | **single-frame possible** |
| **Independence** | unresolvable | **NOT independent** | **NOT independent** |
| **External-test feasibility** | ✗ | needs segmentation agreement | ✓ **no new annotation** |
| **Overall status** | **REJECT** | **CONDITIONAL** | **ADMIT** |
| **Main risk** | data unobtainable + retracted article | unmeasured corpus; shares KIN-MUS's pipeline | glove-derived absolute coordinates; DIP absent; handedness unlabelled |

---

## 18. FIRST_POC_DATASET and why it won

**`FIRST_POC_DATASET = KIN-MUS UJI`** (Zenodo `10.5281/zenodo.3469380`).

Ranked against the frozen priority order:

1. **physical-coordinate trustworthiness** — the only candidate with a *readable*
   calibration pipeline, published sign criteria, a documented reference posture,
   a measured clean channel set, and anchors passing in every subject.
2. **compatibility with emg2pose** — 12 shared DOFs, 10 at HIGH, needing only
   degrees→radians.
3. **task pose-observability** — the **phase** label is pose-observable, and the
   manipulation-vs-reaching signal exists in pose *before* any model is fitted.
4. **sufficient subjects** — 22 ≥ 15.
5. **external-test feasibility** — no new annotation, no task-specific EMG, the
   frozen GT pose corpus is sufficient.
6. **independence** — weakest dimension, shared with KINE-ADL; reported, not
   hidden.
7. **ease of implementation** — one 87 MB `.mat`, already parsed.

**The tradeoff is stated rather than hidden.** KIN-MUS and KINE-ADL are **not**
close competitors: they are two task sets over one physical pipeline. Choosing
KIN-MUS over KINE-ADL is a choice of **which task** — made because KIN-MUS's phase
label is pose-observable today while KINE-ADL's activity label needs segmentation
agreement first.

**Anti-bias attestation.** HUST received no priority for having been discussed
first; it was rejected on access and provenance. KINE-ADL received no priority for
having "more interesting" labels; it is CONDITIONAL on an unrun measurement.
KIN-MUS received **no credit for containing EMG** — its EMG channels were not
downloaded and played no part in the decision.

---

## 19. The exact Common Pose representation for the first POC

**`shared10_poc_v1` — 10 DOFs, all HIGH confidence:**

| # | API DOF | KIN-MUS column | index |
|---|---|---|---|
| 1 | `thumb_cmc_flexion` | `CMC1_F` | 0 |
| 2 | `thumb_mcp_flexion` | `MCP1_F` | 2 |
| 3 | `index_mcp_flexion` | `MCP2_F` | 4 |
| 4 | `index_pip_flexion` | `PIP2_F` | 6 |
| 5 | `middle_mcp_flexion` | `MCP3_F` | 7 |
| 6 | `middle_pip_flexion` | `PIP3_F` | 8 |
| 7 | `ring_mcp_flexion` | `MCP4_F` | 9 |
| 8 | `ring_pip_flexion` | `PIP4_F` | 11 |
| 9 | `pinky_mcp_flexion` | `MCP5_F` | 13 |
| 10 | `pinky_pip_flexion` | `PIP5_F` | 15 |

**The only transform is degrees → radians.**

**Why not 12 or 16.** A 12-DOF version would add the two MEDIUM thumb axes, importing
the axis-identity uncertainty the project already flagged and a channel that
reuses a PIP gain. A 16-DOF version would add four variables that **do not exist
as measurements**. The plan's principal rule — physical semantic equivalence
outranks dimensional count — decides this.

---

## 20. Exact next experiment — **NOT EXECUTED**

Full specification: `NEXT_POC_EXPERIMENT_PLAN.md`.

**Question.** Can a task model learned **entirely from an independent kinematic
dataset**, using **pose alone with no task-specific EMG**, be applied to frozen
emg2pose GT poses through the shared representation and produce an output better
than chance that honestly abstains?

* **Source:** KIN-MUS, `shared10_poc_v1`, degrees→radians only.
* **Label:** the **movement phase** (reaching / manipulation / release).
* **Split:** by **subject** — 11 development / 11 held-out, frozen by subject id.
  The 3 empty trials and 2 duplicated cells are excluded and counted.
* **Models:** exactly two — shrinkage LDA (`lsqr`, `shrinkage='auto'`,
  train-only z-scoring, the project's frozen configuration) and nearest-class-
  centroid with a distance reject option calibrated at 95 % per-class coverage by
  subject-grouped LOSO. **Nothing else.**
* **Reject strategy:** per-phase Gaussian support at 95 % coverage; zero accepting
  regions → `OUTSIDE`, more than one → `AMBIGUOUS`; both reported, never
  tie-broken in the primary report.
* **External population:** the frozen GT canonical16 corpus,
  `gt_valid == True`, 86 858 rows, one subject, with the scope caveat attached.
* **Primary metric:** the **manipulation share**, against a session-level
  bootstrap interval.
* **Mandatory control:** the identical pipeline refit with the phase label
  **permuted within each subject** — preserving the flexion distribution while
  destroying the label. **If real ≈ permuted, the result is negative regardless of
  internal accuracy.** This control exists because DB9 taught that a lower
  rejection rate can mean the model accepts garbage.
* **Success:** (1) source-internal held-out balanced accuracy materially above
  1/3; (2) external manipulation share above the pose-null control by a margin
  surviving the bootstrap on most sessions; (3) `OUTSIDE` reported and not total.
* **Failure:** any one of near-chance internal accuracy, real ≈ permuted, or
  `OUTSIDE` ≈ 100 % is **decisive** — the third would be the same
  outside-support failure that closed DB9.
* **Prerequisite:** confirm the handedness of the released KIN-MUS block. It is
  one hand and does not say which; if it is the left hand a **documented**
  mirroring step is required, never a fitted one.

---

## 21. What this audit proves

1. **Which dataset is the best current candidate**, and on what evidence:
   KIN-MUS UJI, `ADMIT`, on documented+code-verifiable angle provenance, a
   measured clean channel set, and anchors passing in 22/22 subjects.
2. **That the DB9 failure mode is absent from the chosen source** — the
   documented-direction anchor test passes in every subject for every mapped
   channel, whereas it failed in 100 % of subjects for three DB9 channels.
3. **That the candidate pool has exactly one physical pipeline family**, and that
   no candidate is motion-capture-derived.
4. **That HUST cannot be used**, on access and publication-integrity grounds that
   required no measurement to establish.
5. **A V0 admission contract** sufficient to judge these datasets, and a concrete
   minimum shared representation.

---

## 22. What this audit does NOT prove

* **Not** that the Common Pose API works, or that the architecture is validated.
* **Not** that this dataset will transfer to emg2pose.
* **Not** that KIN-MUS's absolute physical coordinates are correct — only that
  they are internally consistent, auditable, and internally clean. The
  strain-gauge-glove vs IK-over-motion-capture metrological gap is **not** closed.
* **Not** that KINE-ADL is admissible: it is CONDITIONAL on a measurement this
  session did not run.
* **Not** any cross-subject external claim: one emg2pose subject.
* **Not** that a documentation audit substitutes for an empirical one — for HUST
  and for KINE-ADL's corpus, the empirical half is explicitly missing.

---

## 23. Limitations

1. **KINE-ADL's corpus was not downloaded** (bounded-download rule). Its quality
   and anchors are specified but unrun, and **no KIN-MUS measurement is presented
   as a KINE-ADL measurement.**
2. **HUST's empirical half is impossible**, not merely undone.
3. **The released KIN-MUS block is one unlabelled hand.** This is a real
   prerequisite, not a footnote.
4. **No within-subject repeatability exists** in the chosen source; the audit
   declines to substitute a different statistic.
5. **4 of 16 API variables are unavailable** in the leading candidate.
6. **The per-subject calibration gains actually used for KIN-MUS are not
   published**; the code ships one lab's gains as placeholders and says so.
7. **The MOVMUS guide's palmar-arch disclosure is contradicted by the KIN-MUS
   data**: the guide says the right palmar-arch DoF "is not reported", while the
   KIN-MUS release carries a live 18th column that is neither constant nor an
   alias of any other channel (median 28.3°, 331 194 distinct values, max |r| with
   any other column 0.397). **This is a documentation-versus-data contradiction
   and it is reported as such, unresolved.** It does not affect the POC
   representation, which excludes `PalmArch`.
8. **`OUTSIDE` denominators** (per session vs pooled) must be fixed before the
   next experiment scores anything.

---

## 24. Deviations

| # | deviation | why | effect |
|---|---|---|---|
| 1 | **`loadmat` is used** to read the KIN-MUS `.mat` | it is the only released format; the plan's prohibition is on *training*, not on reading data | none |
| 2 | **DB9 artifact paths appear in the plan's pin list** | the plan records the prior branch's handover as a pinned *input* for the lesson it carries | none; no DB9 data is read |
| 3 | **DLR and UNIPI were NOT audited** | the frozen backup rule triggers only if all three primaries are REJECT | none; recorded explicitly |
| 4 | **`PalmArch` is in the 18-column inventory** although the MOVMUS guide says it is not reported | the KIN-MUS release contains it and omitting it would misrepresent the released shape | reported as an unresolved contradiction |
| 5 | **The KINE-ADL corpus was not downloaded** | bounded-download rule; the record's metadata and the pipeline code were obtained instead | KINE-ADL is CONDITIONAL rather than decided |

---

## 25. Bugs encountered

| # | bug | consequence | fix |
|---|---|---|---|
| 1 | `uji_row`'s IP1 mapping initially used `RG_PIP(1)` without noticing | would have silently called a reused gain constant "HIGH" | caught while reading the code; `thumb_ip_flexion` demoted to **MEDIUM** |
| 2 | `numpy.ndarray.median()` does not exist | `AttributeError` | `np.median` |
| 3 | `probe_kinmus.py` vstacked a `(N,)`-shaped trial | `ValueError`; three empty trial containers were discovered | guard on `ndim == 2 and shape[1] == 18`; the malformed trials are now *reported* |
| 4 | composite evidence tags like `"A + B"` | rejected by the tag validator | added `tag_multi`, which records the strongest class plus `also_supported_by` |
| 5 | `api_dof: None` for non-API rows | the fact check's membership test treated `None` as an API match; CSV/JSON disagreed | explicit `"(no API DOF)"` marker |
| 6 | fact check counted API rows wrongly | false failures | separated the **mapping rows** from the **release inventory** — a better artifact |
| 7 | the "no writes outside the lane" check included `db9_channel_validity/` | matched the *previous* session's own lane, producing 60 false positives | that lane is excluded with a comment explaining why |
| 8 | the "no training" and "no DB9" checks were plain substring scans | flagged prohibition *lists* and pinned provenance *paths* | rewritten as import/call checks |
| 9 | the fact checker scanned its own source | self-match on its own literal strings | self excluded |

Bugs 1 and 3 changed **findings** (a confidence demotion and a discovered data
defect); the rest were tooling.

---

## 26. Artifacts + SHA-256

Full inventory with sizes and hashes, plus the freeze-order hash chain:
`ARTIFACT_MANIFEST.json` (38 files, 581 KB). Downloaded third-party evidence:
112 files, 97.5 MB, hashed separately and **never treated as this branch's
output**.

| artifact | SHA-256 |
|---|---|
| `DATASET_ADMISSION_PLAN.json` | `4d2c8b162e2332a5891a5d89a53166e365b1bbd92c205222492d19957c9683ec` |
| `COMMON_POSE_API_REQUIREMENTS.json` | `ec748c61451c9ccdbb048ca318d34fb4667e1434322d028e97a170d7f0101b3a` |
| `OFFICIAL_SOURCE_REFERENCES.md` | `899855f933bf8a80fde009ffd36a6cf57ec2c2536f1eedd6a5865db00083b2f9` |
| `DATASET_ACCESS_AND_LICENSE.json` | `cce71dc10483552e37aa31ec78d684a5c87b523c64be02b69e9c7bc4227b28cd` |
| `POSE_API_DOF_MAPPING_MATRIX.json` | `0bda06c4860fee7c972a03deb0ef1cd80420cc7d7bd9b478489fa89361e96fd3` |
| `ANGLE_ORIGIN_AND_CALIBRATION_AUDIT.json` | `64cdecda9bdcec1da595d2fce86ce5f03f83bbe8293e71ab7d24d7069dedada8` |
| `KIN_MUS_QUALITY_AUDIT.json` | `f9785cea039cc302…` |
| `KIN_MUS_PHYSICAL_ANCHOR_AUDIT.json` | `af2b8aeaea0327b2…` |
| `DATASET_TASK_STRUCTURE.json` | `e9871a656926feef…` |
| `DATASET_INDEPENDENCE_MATRIX.json` | `307fefe8e30406c0…` |
| `EXTERNAL_TEST_FEASIBILITY.json` | `6ceea72163393924…` |
| `COMMON_POSE_API_ADMISSION_CONTRACT_V0.md` | `05216d792b0e63f0…` |
| `FIRST_POC_DATASET_DECISION.json` | `4daba251326b7857…` |
| `NEXT_POC_EXPERIMENT_PLAN.md` | `276fba2598e1d71b…` |

---

## 27. Fact-check result

`tools/dataset_admission_fact_check.py` — run it last; a failure is a non-zero
exit. It verifies: no DB9 rescue (no adapter call, no DB9 module import); no model
training (no learning import, no model constructor, no `.fit()`); no external
outcome tuning (no pose, label or score loaded — the only paired-corpus use is a
**file count**); the frozen plan hash and sidecar; that ≥15 source URLs and an
access date per source are recorded; that every evidence tag is legal; that every
mandatory mapping field is complete or explicitly UNKNOWN; that the mapping
inventory matches the released 18 columns exactly once; that no coarse or derived
name was promoted to a one-to-one match; that the same criteria drive all three
statuses; that all three primaries were evaluated; that the POC choice follows the
frozen selection rule; that nothing outside the lane was written; manifest
integrity including the third-party evidence; and that the report's numbers equal
the JSON artifacts.

**Result: 399 assertions passed, 0 failed.**

---

## 28. Stop-rule compliance

The frozen stop rule: *at least one dataset is ADMIT → choose FIRST_POC_DATASET
and stop.* One dataset is ADMIT (KIN-MUS). The dataset was chosen, DLR/UNIPI were
not audited, **no model was trained**, and the next experiment exists as a plan
only. The session answers *"which dataset deserves to be the first real test of
the Common Pose API?"* and stops there.
