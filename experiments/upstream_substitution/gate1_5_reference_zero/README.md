# GATE 1.5 — reference-anchor availability & numerical-zero check

**Gate:** PHASE 1 / GATE 1.5 · **Local only · no server · no GPU · no model · no inference**

**Outcome:**

| | |
|---|---|
| `ANCHOR_STATUS` | **`NO_INDEPENDENT_ANCHOR`** |
| `ZERO_GATE` | **`NOT_EVALUABLE_LOCALLY`** |
| `REFERENCE_ANCHOR_SPEC.md` | **NOT_CREATED** |
| trusted-8 zero statistics | **NOT_MEASURED** |
| reference frames synthesised | **no** |

---

## What this gate was for

The previous phase left three items open: **B1** cross-source calibration provenance, **B2**
numerical zero interchangeability, **B3** DB9 source-database level shifts. This gate addresses
**B2 only**:

> Does the emg2pose GT contain an *independently identifiable* physical reference/neutral posture,
> and are the trusted-8 values there compatible with the DB9 reference zero?

## Why the answer is "not evaluable" rather than "pass" or "fail"

The gate's anti-circularity rule forbids selecting reference frames by anything derived from the
trusted-8 values — including "angles near zero" and including an FK straightness test that reduces
to the same thing. An anchor must be **pose-independent *and* must state a posture**.

Audited candidate sources, all present-or-absent judged without reading a single pose value:

| id | candidate | present locally | independent | verdict |
|---|---|---|---|---|
| A1 | per-frame posture/gesture label | no | — | `ABSENT` |
| A2 | `stage` group attribute | yes | **yes** | `PRESENT_BUT_DOES_NOT_DEFINE_A_POSTURE` |
| A3 | stage `HandDeskSeparateClaspedChest` (the one resting-position name) | **no** | partial | `ABSENT_LOCALLY` |
| B | annotation / protocol marker | no | — | `ABSENT` |
| C | FK "is it extended?" criterion | yes | **no — circular** | `PRESENT_BUT_CIRCULAR` |
| D | recorded calibration marker | no | — | `ABSENT` |

The locally-present pose-independent field (`stage`) names a compound **activity**, not a hand
**posture**, so it cannot define a reference configuration. The only stage name in the entire
29-stage vocabulary that encodes a resting *position* is not in the local subset. And the FK route
is circular by construction: `generic_hand_model.json` gives `min = 0.0 rad` for `THUMB_MCP_FE` and
every PIP, i.e. **zero IS the extended pose**, so "is this hand extended?" collapses into "are these
joint angles near zero" — the forbidden criterion.

So no anchor exists, the gate stops, and no zero statistics are reported. **This is not a scientific
failure**: it states that the local mini corpus cannot independently answer the question.

## Files

| file | role |
|---|---|
| `REFERENCE_ANCHOR_AVAILABILITY.md` | **the deliverable.** Full candidate audit, tolerance audit, DB9 comparator, handedness scope, and both documentation issues. |
| `artifacts/REFERENCE_ANCHOR_DECISION.json` | machine-readable anchor decision, candidate table, tolerance audit, DB9 comparator, firewall, execution scope. |
| `artifacts/TRUSTED8_ZERO_COMPATIBILITY.json` | all 8 DOFs with `null` statistics and `compatibility_verdict: NOT_MEASURED` — the absence is machine-readable. |
| `scripts/audit_reference_anchor.py` | the audit. Reads structure/attributes/metadata only; never reads a pose value. |
| `logs/gate1_5_stdout.txt` | captured stdout of the run. |

`REFERENCE_ANCHOR_SPEC.md` / `.sha256` are intentionally absent — freezing a spec for a
non-existent anchor would manufacture a prerequisite the evidence does not support.

## Local corpus (for the record)

30 files · **1 session** · **1 participant** · 15 `left` + 15 `right` · **4 218 756 frames** · all
`split = val`, `held_out_user = True`. The bundled `metadata.csv` describes the **full** corpus
(25 253 rows / 751 sessions / 193 participants); only one session is on disk, which is why the one
usable resting-position stage is unavailable.

Because both hand sides are present, any future reference-anchor analysis on this corpus **must be
reported left and right separately** and never pooled.

## What this gate did NOT do

No model trained; no server; no GPU; no full-corpus download; no inference re-run; **GT pose never
read**; **predicted pose never read or produced**; no mapping tuned; **no offset or scale fitted**;
no percentile matching, histogram alignment, regression or Procrustes; no ad-hoc `±2°` threshold
adopted (no pre-existing reference-anchor tolerance rule exists in the frozen plans); no
authoritative public document modified.

## Documentation issues recorded

* **DOC_ISSUE_1** — `INTERCHANGEABLE_WITH_KNOWN_CONVENTION` (used in the previous phase's artifacts)
  overstates what is established, because numerical zero evidence and cross-source calibration
  provenance are both still missing on those rows. The phrase appears **only** in those gate
  artifacts, not in `README.md`, `docs/research_status.md`, `docs/common_pose_api.md` or
  `docs/db9_trusted_subset.md` — which already state the conservative position. The corrected
  wording is `SEMANTIC_MAPPING_ESTABLISHED` + `NUMERICAL_INTERCHANGEABILITY_NOT_ESTABLISHED`. The
  old artifacts were **not** modified.
* **DOC_ISSUE_2** — the 18.001 / 5.911 / 21.268 numbers are **reference-anchor residuals**
  (`reference_posture_per_source`, unit = subject × movement × repetition, central phase), **not**
  dataset-level distribution shift. They are means over all 16 dimensions, dominated by (though not
  exclusively attributable to) the already-DROPped defective DIP channels. The trusted-8 per-joint
  anchor residuals are much smaller: **≤ 4.96° (DB1), ≤ 0.75° (DB2), ≤ 3.32° (DB5)**. The artifact
  publishes no per-source dispersion at the anchor, so whether the DB1-vs-DB2 trusted-8 anchor gap
  is statistically meaningful **cannot be settled from it**.

## Reproduce

```powershell
cd common-pose\experiments\upstream_substitution\gate1_5_reference_zero
C:\emg2pose-venv\Scripts\python.exe -X utf8 scripts\audit_reference_anchor.py
```

## Next allowed step

> Do not invent a zero calibration; decide whether to run an explicitly labelled native-coordinate
> diagnostic or obtain an independent physical anchor.
