# COMMON POSE API — ADMISSION CONTRACT V0

**Branch:** `S6-POSE-API-DATASET-ADMISSION`  
**Frozen plan SHA-256:** `4d2c8b162e2332a5891a5d89a53166e365b1bbd92c205222492d19957c9683ec`  
**Status:** a research artifact written to judge these three datasets. It is **not** a software standard and **not** a novelty claim.

---

## 0. Why this exists

DB9 was dropped because channel *names* were right and the *numbers* were not. Names are therefore not admissible evidence. This contract states what a dataset must be able to say about every variable before the variable may enter a common physical pose API.

---

## 1. The admission record for one API variable

Every variable in the API carries a record with these fields. A field may be `UNKNOWN`, but an `UNKNOWN` in a **mandatory** field blocks ADMIT for that variable.

| field | mandatory | meaning |
|---|---|---|
| `anatomical_identity` | yes | which joint, which axis, in words a physiotherapist would accept |
| `unit` | yes | degrees or radians, and whether the conversion is exact |
| `sign` | yes | which physical direction is positive, and the source that says so |
| `physical_zero` | yes | what configuration the zero denotes, and how it is established (nominal anatomical zero vs a recorded reference posture) |
| `handedness` | yes | which hand, and how a mirror is defined if both occur |
| `acquisition_provenance` | yes | the sensor or model the number comes from |
| `calibration_provenance` | yes | how raw units became angles; per subject or per device; cross-coupling modelled or ignored |
| `quality_status` | yes | tested for: constant / saturated / aliased / out-of-range / directionally inconsistent across subjects |
| `confidence` | yes | HIGH / MEDIUM / LOW / NONE, with the reason |
| `derivation` | yes | MEASURED or DERIVED-FROM-ANOTHER-VARIABLE (and if derived, from which) |

---

## 2. The three admissibility rules that follow from DB9

**R1 — Semantic naming is not evidence.** A column called `PIP2_F` is admissible only if a source states the sign criterion, the zero and the calibration. Otherwise it is `UNKNOWN` regardless of how it is named.

**R2 — A derived variable is not an independent measurement.** If the source itself computes variable *y* from variable *x* (for example DIP from PIP), then *y* may enter the API only as an explicitly flagged derived variable, and a representation relying on it must say so. It may never be counted as independent evidence that the joint is covered.

**R3 — Cross-dataset matching is by anatomy, not by name and not by count.** A dataset that says "index flexion" without distinguishing MCP/PIP/DIP matches none of them. Two datasets that both expose sixteen columns are not thereby compatible.

---

## 3. What may be transformed, and what may not

**Allowed**, because the physics or the documentation justifies it:

* degrees → radians;
* a documented sign reversal;
* a documented axis reorder;
* left/right anatomical mirroring;
* an explicitly documented neutral-zero transform.

**Not allowed**, because it would fit the representation to an outcome:

* an offset fitted so that two datasets' distributions line up;
* an affine transform fitted using target outcomes;
* a sign chosen because it improves downstream classification;
* a manual distribution shift;
* a coordinate transform chosen using human labels.

---

## 4. The reference-posture requirement

A physical zero must be **one of two legally distinct things**, and the API must say which:

1. **NOMINAL ANATOMICAL ZERO** — a defined joint configuration (for example the fully extended finger), independent of any recording.
2. **RECORDED REFERENCE POSTURE** — a specific posture captured in the session and subtracted. This is legitimate and is what the UJI pipeline does, but it makes the zero *session-dependent*, so the API record must name the reference posture in words, as the UJI guide does.

A dataset that cannot say which of the two applies does not admit the variable.

---

## 5. Minimum coverage

An admitted source representation must cover **at least 8 API variables**, of which **at least 6 at HIGH confidence**. The threshold is derived from the DB9 outcome: a 5-variable surviving set destroyed the internal task (closed-set balanced accuracy 0.978 → 0.769; correct singleton 0.593 → 0.330; ambiguity 0.324 → 0.594). It is an a-priori round number, not a fitted one.

**Physical semantic equivalence outranks dimensional count.** A 10-variable HIGH-confidence representation is preferred to a 16-variable one in which four variables do not exist in the data.

---

## 6. What V0 deliberately does NOT do

* it does not define a file format, a serialisation or a wire protocol;
* it does not prescribe a classifier, a Gate or a rejection rule;
* it does not require a temporal context model (it only requires that a source say whether single-frame pose suffices for its own task);
* it does not attempt to be a standard for anyone outside this project.

---

## 7. Admission statuses

| status | meaning |
|---|---|
| `ADMIT` | every mandatory field is sourced, coverage and quality gates pass, and the labels support a pose-observable task |
| `CONDITIONAL` | promising, with named solvable gaps; the exact evidence or action that would promote it is stated |
| `REJECT` | a strong version of: no physical angle definitions, inadequate calibration provenance, too few common variables, severe quality defects, labels not inferable from hand state, data inaccessible, or a mapping that would need target-driven fitting |

