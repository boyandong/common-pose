# Gate4D implementation lock — before Gate4D outcome inspection

`analysis/gate4d_analysis.py` is the sole frozen implementation for new four-view TTA inference, Gate4C DEV paired-output reuse, subject-grouped five-fold Gate A fitting/calibration, four-gate evaluation, physical diagnostics, JSON artifacts and compact plots. The algorithmic choices are in `GATE4D_PLAN.md`; the continuous layer is in `LAYER_SELECTION.md`; exact DEV membership is in `COHORT_MANIFEST.json`.

The script checks those hashes and the frozen Gate4C plan/cohort/head identities. Every Gate4C result has a receipt/output SHA256 check. Every new TTA file has a source identity, atomic output, and receipt check. No Gate4D outcome was inspected to select these definitions. Any later mechanical fix must be documented separately without silently changing the frozen scientific contract.
