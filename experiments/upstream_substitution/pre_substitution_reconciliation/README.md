# Pre-substitution evidence reconciliation

**Phase:** PRE-SUBSTITUTION EVIDENCE RECONCILIATION
**Status:** complete · **Decision:** `CONDITIONAL_GO`
**Frozen representation:** `TRUSTED_DB9_POSE_v1`
`e51dde6e63941fd080c84f3896a98cf50fba9e17d5f9cebe909253d5465782d1`

---

## What this lane is

A reconciliation of **existing** evidence. It asks one question:

> Before attaching the frozen DB9 posture head to an independent upstream pose source, for each of
> the 8 frozen DB9 trusted DOFs, what do the artifacts **already** establish about whether the
> corresponding emg2pose GT DOF is the *same physical variable under a defensible Common Pose
> interpretation*?

It is **column B** of that question only — *cross-source variable compatibility*. Column A,
*DB9-internal physical validity*, is CLOSED (77/77 revalidation, 0 of 8 KEEP channels changed) and
is not re-adjudicated here.

## What this lane is not

Not a new experiment. Not a mapping re-run. Not a task-head evaluation. Not emg2pose transfer.
Not a DB9 forensic re-audit. Nothing was trained, no forensic tool was re-run, no trusted channel
was re-selected, `TRUSTED_DB9_POSE_v1` was not modified, the frozen downstream head was not called,
and no task probability, margin or label was inspected.

## Files

| file | role |
|---|---|
| `EVIDENCE_RECONCILIATION.md` | **the deliverable.** Full reconciliation: validity classification of every historical claim, the superseded-evidence register, zero/handedness/calibration treatment, and the decision rationale. |
| `artifacts/TRUSTED8_EVIDENCE_MATRIX.csv` | one row per frozen DOF, 45 columns, every required status and its evidence string. |
| `artifacts/TRUSTED8_EVIDENCE_MATRIX.json` | same rows plus per-DOF measured diagnostics and the SHA-256 of every evidence source. |
| `artifacts/RECONCILIATION_DECISION.json` | machine-readable `CONDITIONAL_GO`, closed facts, partially-closed items, superseded evidence, true remaining blockers, the specified next minimal check, and the downstream-firewall flags. |
| `build_reconciliation.py` | regenerates the three artifacts from the published evidence. Reads only; measures nothing. |

## Headline result

All 8 frozen DB9 DOFs correspond to the intended emg2pose GT DOF as the **same physical
variable** — same joint, same unit, same positive direction, same zero *definition*, same angle
convention, no per-finger sign hazard. None is established as **numerically interchangeable**.

| DOF | DB9 | interchangeability |
|---|---|---|
| `thumb_mcp_flexion` | `MCP1` | `SEMANTICALLY_MATCHED_BUT_CALIBRATION_UNCERTAIN` |
| `thumb_ip_flexion` | `IP1` | `INTERCHANGEABLE_WITH_KNOWN_CONVENTION` |
| `index_mcp_flexion` | `MCP2_f` | `SEMANTICALLY_MATCHED_BUT_CALIBRATION_UNCERTAIN` |
| `index_pip_flexion` | `PIP2` | `INTERCHANGEABLE_WITH_KNOWN_CONVENTION` |
| `middle_mcp_flexion` | `MCP3_f` | `SEMANTICALLY_MATCHED_BUT_CALIBRATION_UNCERTAIN` |
| `ring_mcp_flexion` | `MCP4_f` | `INTERCHANGEABLE_WITH_KNOWN_CONVENTION` |
| `pinky_mcp_flexion` | `MCP5_f` | `SEMANTICALLY_MATCHED_BUT_CALIBRATION_UNCERTAIN` |
| `pinky_pip_flexion` | `PIP5` | `INTERCHANGEABLE_WITH_KNOWN_CONVENTION` |

The calibration question split in two, which is the most useful thing this round established:

* **within-source (DB9) provenance: CLOSED.** Every trusted channel's released angle is an exact
  single-column affine map of the raw glove signal (residual ≤ 1.6e-11°), and the recovered slope
  reproduces the *published* calibration gain to within **0.61 %**. DB9's ruler is fully known, and
  the release is already subject-normalised to the documented reference posture.
* **cross-source provenance: OPEN.** That still does not establish that emg2pose uses the same
  ruler, and criterion J fails for exactly this reason.

Three remaining blockers, all non-task-derived: no cross-source calibration record; numerical zero
interchangeability `NOT_ESTABLISHED`; and source-database level shifts inside DB9 for 5 of the 8
DOFs.

Two items are escalated rather than resolved unilaterally:

1. `docs/research_status.md` §E5 supersedes the coordinate audit's per-source-database reference
   means on a corpus-mismatch ground that the audit's own frozen input pins and parity results
   contradict. Treated as current evidence here; the ledger is the item that should be corrected.
   See `EVIDENCE_RECONCILIATION.md` §4.4.
2. The audit's quoted "31° range disagreement" for `thumb_ip_flexion` is not reproducible from the
   preserved artifacts and appears to be a median *location* gap. Conservative in direction, so no
   status changes. See §10.

Neither is `SCIENCE-BLOCKING` under the failure taxonomy: the first concerns a status ledger
disagreeing with artifacts rather than an artifact disagreeing with reality, and no verdict in this
document depends on the disputed numbers; the second is conservative in the safe direction.

## Verification

`build_reconciliation.py` was run and the outputs were then re-validated by an independent check
script against the source artifacts: **266 assertions, 0 failures**, covering the frozen subset
SHA-256 chain, the frozen channel set and order, every copied numeric value (tolerance = the
`round(x,4)` bound, max observed deviation 4.97e-5), all ten per-dimension criteria A–J, the status
vocabulary, the CSV/JSON agreement, the required matrix columns, the three blockers, and the
downstream-firewall flags.

## Reproduce

```powershell
cd common-pose
python -X utf8 experiments\upstream_substitution\pre_substitution_reconciliation\build_reconciliation.py
```

The script re-verifies the frozen subset SHA-256, copies every number from the published
artifacts, and rewrites the three files under `artifacts/`.

## Next step

`CONDITIONAL_GO` — run **only** minimal check `N2` (specified in
`artifacts/RECONCILIATION_DECISION.json` `.next_minimal_check`, and in
`EVIDENCE_RECONCILIATION.md` §13) before any task-head evaluation. It is a GT-only,
CPU-only, no-model, no-label check on the already-local emg2pose mini corpus, with its pass and
fail criteria declared in advance.
