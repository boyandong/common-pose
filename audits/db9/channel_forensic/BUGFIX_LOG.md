# BUGFIX LOG - S8 DB9 channel forensic lane

**Frozen plan SHA-256:** `4c618b562903d0d364d03bb8a997ef6b4140bd9e09d0f2475f1b008ad80c8793`

---

## BUG-001 - over-strict rest/repetition equivalence check

* **Symptom.** driver 01 reported 10 segmentation anomalies and failed its gate with
  "rerepetition==0 is not equivalent to restimulus==0".
* **Root cause.** The required relation is ONE-DIRECTIONAL. `rerepetition == 0` does imply
  `restimulus == 0` in every file, but a rest frame may still carry a non-zero
  `rerepetition` index. Requiring equivalence was a checker defect, not a data defect.
* **Files changed.** `scripts/01_segmentation.py` - the check now requires only the
  implication, and rest frames carrying a repetition index are recorded as a **finding**
  rather than as an anomaly.
* **Measured results already inspected?** The gate had produced only the anomaly list.
* **Rerun invalidates previous artifacts?** No; nothing had been written.

## BUG-002 - best-fit search compared the intercept instead of the residual

* **Symptom.** driver 02 reported "composite (best single-column residual 45.5 on col 0)"
  for channels that the reconnaissance had already shown to be exactly single-column affine.
* **Root cause.** `best = (glove_col, a, b, r)` but the comparison used `r < best[2]`, i.e.
  the intercept. The wrong column was retained, and the whole transform-recovery table plus
  the raw-column lookup used downstream were consequently wrong.
* **Files changed.** `scripts/02_forensic_core.py` - explicit
  `best_gj, best_a, best_b, best_r` with `r < best_r`.
* **Measured results already inspected?** The buggy table had printed. It is superseded in
  full by the rerun.
* **Rerun invalidates previous artifacts?** Yes, for driver 02's transform table and every
  derivative. No artifact of this lane had been frozen at that point.

## BUG-003 - the composite objective did not remove the constant offset

* **Symptom.** CMC1_f, CMC1_a and WRIST_A were reported "NOT EXACT" with residuals of tens
  of degrees.
* **Root cause.** The objective was `max |angle - f(glove)|`. Every released angle is
  `f(glove) - f(glove_reference)`, so the residual carries a constant equal to
  `f(glove_reference)`; the objective must be the PEAK-TO-PEAK of the residual.
* **Files changed.** `scripts/02_forensic_core.py` - composite and polynomial searches now
  minimise peak-to-peak.
* **Measured results already inspected?** Yes; corrected values (residuals 0.02-0.07 deg)
  supersede.
* **Rerun invalidates previous artifacts?** Only driver 02's composite rows.

## BUG-004 - the `subject` field used as an identity key

* **Symptom.** the anchor analysis covered 27 subjects although 37 Exercise B files exist.
* **Root cause.** `fx_common.load` used the in-file `subject` field. That field is
  **source-database local**: `S68_E2_A1.mat` reports `subject == 1`, colliding with
  `S1_E2_A1.mat`, so ten files overwrote ten others. There are 10 such collisions among the
  37 Exercise B files.
* **Files changed.** `scripts/fx_common.py` - the archive slot parsed from the **filename**
  is now the primary `subject`; the in-file value is kept separately as `subject_field`.
* **Measured results already inspected?** Yes. Every subject-level count changed from 27 to
  37 and all anchor statistics were recomputed.
* **Rerun invalidates previous artifacts?** Yes for all anchor numbers; no artifact was
  frozen yet.

## BUG-005 - pooling movement 6 with movement 17 diluted the fist anchor

* **Symptom.** after BUG-004 was fixed, MCP2_f's median Δraw fell from +70.5 to +18.0 and
  agreement from 1.00 to 0.81.
* **Root cause.** the anchor had been widened to movements {6, 17} without checking that
  movement 17 is a closed hand. The data-driven movement probe shows movement 17 produces
  **no** hand-shape change at all (median Δraw -0.52 counts).
* **Files changed.** `scripts/03_verdicts.py` - the frozen anchor is movement 6 only, exactly
  as the frozen plan's anchor table specifies; the probe is retained as evidence and
  movement 17's null response is reported.
* **Measured results already inspected?** Yes; the pooled numbers were discarded before any
  verdict was produced.
* **Rerun invalidates previous artifacts?** No verdict had been written.

## BUG-006 - rounding-level gain differences classified as documentation conflicts

* **Symptom.** MCP5_f (0.61 % difference) and PIP5 (0.12 % difference) were assigned
  `CASE_D_DOCUMENTATION_CONFLICT` and removed from the trusted subset.
* **Root cause.** the conflict list had no materiality threshold. The published gains are
  quoted to two or three significant figures, so a difference inside the rounding interval
  cannot be evidence of a conflict.
* **Files changed.** `scripts/03_verdicts.py` - a **2 %** materiality threshold is now
  applied; differences inside it are recorded as `ROUNDING_ONLY`, differences above it as
  `CONFLICT`. The threshold is stated in the artifact.
* **Measured results already inspected?** Yes. This is the one change in this lane that
  altered a verdict after a number was seen, so it is stated plainly here: the rule was
  incomplete rather than inconvenient. No threshold that determines CASE_A, CASE_C, CASE_B
  or CASE_E was touched, and no channel was added back to reach a target dimension - the
  two channels concerned passed the anchor test at 37/37 before and after.
* **Rerun invalidates previous artifacts?** It changes two verdicts from INCONCLUSIVE to
  KEEP; the trusted subset was re-frozen and the hash recorded after the change.

## Final state

driver 03: 8 KEEP, 6 DROP, 8 INCONCLUSIVE.
