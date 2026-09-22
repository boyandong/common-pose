# Common Pose API — interface philosophy

This document states what the interface is for and what it refuses to do. It deliberately
does **not** freeze a schema: the one frozen thing in this project is a physical-validity
*result* (the DB9 trusted channel subset), and freezing the wire format before the research
question is settled would be a different kind of mistake.

---

## 1. The problem the interface exists to solve

Two datasets can agree on every anatomical name, every unit and every sign convention, and
still disagree numerically. The cross-dataset audit measured per-dimension disagreement of
**2–40°** in the medians and up to **450°** in the ranges between sources whose DOF
identities, units, positive directions and zero definitions all checked out.

> **Semantic anatomical correspondence ≠ numerical coordinate equivalence.**

Two datasets having a joint called `index_pip_flexion` does not mean their two numbers can
be concatenated, averaged, or used interchangeably. They were produced by different
metrological processes. The load-bearing conclusion of that audit was therefore:

> A shared pose API must carry **per-channel calibration provenance**, not just the
> anatomical name.

That is why provenance is a first-class field here and not a comment.

A second failure class is structural rather than metrological. An audit found a ten-column
"shared pose" subset whose index vector had been taken from a **later guide describing a
different dataset**, mislabelling four of ten channels — including naming a thumb
abduction channel as thumb flexion. Every classification metric computed on it was
unchanged and correct; the physical interpretation was wrong for four of ten. No metric can
detect this. Only the provenance and semantics can.

---

## 2. What every dimension must eventually answer

| field | required answer | failure mode if unanswered |
|---|---|---|
| **anatomical DOF** | which joint, which rotation axis | a name is not a joint; `thumb_cmc_flexion` was applied to an abduction channel |
| **unit** | degrees or radians, stated | a silent factor of 57.3 in every downstream statistic |
| **positive direction** | flexion? abduction? extension? | DIP3 is sign-inverted in the release relative to its own published criterion |
| **zero / reference definition** | what 0 means, and how it was physically established | one source's zero is a recorded posture, another's is a model artefact — both named "extended hand" |
| **handedness convention** | left / right, and mirroring rule | pooled statistics silently mix two mirrored coordinate systems |
| **calibration provenance** | where the scale came from, and whether it is independently closable | 2–40° median disagreement with no way to attribute it |
| **validity / confidence** | may *this sample* of *this dimension* be interpreted as the named quantity | IK failures are encoded as all-zero rows; zero is a legal angle |

The registry model is a *vocabulary*, not an API freeze. Members are expected to gain
information as audits complete; the code reports which fields are still unanswered rather
than defaulting them.

---

## 3. Validity is three-valued, and that is not pedantry

```python
class Validity(str, Enum):
    VALID            # may be interpreted as the named physical quantity
    INVALID          # established NOT interpretable
    NOT_ESTABLISHED  # no evidence either way
```

A boolean `is_valid` flag forces `NOT_ESTABLISHED` into one of the other two, and both
directions have already caused damage here:

* collapsing to **valid** re-adopts a dropped channel as a physical measurement;
* collapsing to **invalid** discards a channel that is merely unaudited, and quietly
  changes what a representation can express.

The same distinction runs through the dataset-level vocabulary:

| verdict | meaning | consequence |
|---|---|---|
| `KEEP` | the channel behaves as its published definition requires | in the trusted subset |
| `DROP` | established not to be the named physical quantity | excluded, and *asserted broken* |
| `INCONCLUSIVE` | the evidence does not settle the question | excluded, and **not** asserted broken |

`DROP` and `INCONCLUSIVE` both remove a channel, and they are not interchangeable
statements. `MCP2_a` is DROPped by the vendor (all-NaN, excluded for noise). `DIP4` is
INCONCLUSIVE because it is inverted in only 28 of 37 subjects with a raw response ~11–16 %
of the flexion-channel median — suggestive, not established.

---

## 4. Container shape

`PoseStream` is a time-stamped sequence; `PoseFrame` is one instant. Both carry the same
semantics so a head can accept either without losing the ability to refuse a value.

```
timestamps_s   (T,)        strictly increasing; a pose stream without a time base
                           cannot be aligned with anything, which is the whole point
values         (T, D)      float64; units are uniform across the frame
validity       (T, D)      int8 codes; supplied by the adapter, NEVER inferred from values
registry                  the vocabulary the columns are in
provenance                where the numbers came from
native_rate_hz            the rate the upstream estimator actually updates at,
                           when it is lower than the sampling rate
```

Four properties enforced in code:

1. **No bare-angle accessor.** `PoseFrame.get(name)` returns `(value, validity)`. There is
   no method that returns a number on its own.
2. **Validity is never inferred.** A default is `NOT_ESTABLISHED`, never `VALID`.
3. **Validity is stored as int8 codes, not as an object array.** NumPy applies its own
   string conversion to `str`-mixin enum members inside object arrays, silently degrading
   `Validity.VALID` to the Python string `'Valid'`. That would then read as neither valid
   nor invalid. The container stores codes and decodes at the boundary; the test suite
   pins this behaviour so it cannot be "simplified" back.
4. **Shape and vocabulary must agree.** A `(T, 16)` array with a registry of 8 raises,
   because a mismatch there means the vocabulary and the array are describing different
   things.

Sample rate honesty is part of the container: emg2pose emits a `(T, 20)` array at what looks
like 2 kHz, but only `T/40` of those rows are independent — the internal rollout runs at
50 Hz and the rest is linear interpolation. `declared_rate_hz` and `native_rate_hz` are both
carried; choosing a window length on the declared rate would be choosing it on interpolation.

---

## 5. What the API is not

* **Not a wildcard.** It does not accept a bare array and a list of names. An adapter must
  state which source and which version it read.
* **Not a repair layer.** No sign flip, offset, affine alignment or rescaling is applied to
  any released array here. Where a released representation is established-defective, the
  verdict says so and the value is emitted as `INVALID` — it is not silently corrected into
  looking like a good measurement.
* **Not frozen.** The container will change. Only the DB9 trusted subset and each lane's
  frozen plan are frozen.
* **Not a transfer claim.** Support for attaching a task head to a *different* upstream
  estimator is a research question here, not a feature.

---

## 6. Contract enforcement

Adapters implement `PoseAdapter.validate()`. It asserts, for the emitted stream:

1. every column has a registry entry with complete physical semantics;
2. every dimension's dataset-level audit verdict is known, not assumed;
3. validity was supplied by the adapter rather than derived from the values;
4. a `DROP`ped channel is not emitted silently **from the source that verdict is about**.

Point 4 is scoped deliberately. The frozen DB9 verdicts describe the **released DB9
CyberGlove columns**. Applying `DIP3 is DROP` to an emg2pose column of the same anatomical
DOF would be a category error — that column is a different measurement with its own,
separately unresolved calibration provenance. Adapters declare
`db9_verdicts_are_authoritative` so the check cannot be applied to the wrong source.

A `validate()` that returns a non-empty list is not automatically fatal, but a caller that
treats it as non-fatal is making a scientific choice and should say so at the call site.
