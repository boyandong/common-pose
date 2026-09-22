# SESSION HANDOVER — S6 POSE COORDINATE AUDIT

**Recommended successor session name:**
`EMG2POSE-S6COORD-20260921-DB9-CHANNEL-VALIDITY`

**Lane:** `<PROJECT_ROOT>\pose_coordinate_audit\` (new; no other lane was modified)
**Date:** 2026-09-20
**Status:** **BRANCH COMPLETE.** Decision gate **COORD-D — MIXED COORDINATE MISMATCH.**
Use the ASCII junction `<PROJECT_ROOT>` for all tooling.

> **Read this first.** The audit answered its question and the answer relocates the
> problem rather than closing it. The *coordinate conventions* are sound; **four
> DB9 channels are not measuring their joints**, and that defect has been sitting
> inside every cross-dataset canonical16 result the project has produced.Do **not**
> repair the transform. Repair the measurement — see §4.

---

## 0. Headline

| | |
|---|---|
| Question | Are DB9 and emg2pose merely using the same anatomical DOF *names*, or numerically calibrated to the same physical coordinate system? |
| Answer | **Same DOFs, units, signs, zero, reference pose and angle convention. Four dimensions fail on per-channel calibration — inside DB9.** |
| Frozen plan | `POSE_COORDINATE_AUDIT_PLAN.json`, SHA-256 **`c59fe01370d48aedeed56ef7a4103506d14a298edb794723be3720531edd62c6`** |
| Parity | emg2pose selection **bit-exact**; DB9 conversion **≤ 1 ULP**; DB9 central-third median reproduced to **4.4e-16 rad**; paired-artifact containment **100 %** |
| Code paths | **13 enumerated, none disagree.** The top-priority check is clean. |
| Reference posture | DB9's documented calibration zero is numerically attained: **mean \|angle\| = 0.854°** vs 21.14° to other movements (ratio 0.040) |
| The defect | **4 dimensions** — `middle_pip_flexion`, `middle_dip_flexion`, `ring_dip_flexion`, `pinky_dip_flexion` |
| Decisive test | DB9 channel change, documented extended anchor → flexed anchor: **MCP +54.9/+96.2/+70.0/+123.8° (all correct)**; **DIP +41.0/−34.5/−22.0/−15.3° (only the index is correct)** |
| Exonerated | **`pinky_mcp_flexion`** — the third dimension the previous branch flagged is **healthy**; its offset was a source-database + heavy-tail artifact |
| Broken-channel contribution | removing the 4 dimensions lowers the reconstructed UNKNOWN rate 0.9609 → **0.8861** (−7.5 pts): **real but PARTIAL.** The 0.8057 was **not** an artifact of the broken channels, and this audit does not claim it was. |
| Verification | `tools/pose_coordinate_fact_check.py` — **312 assertions, all pass** |

## 1. What this branch did NOT do

No classifier was trained. No deep-learning training was run anywhere. No
transform was tuned on any human label. No frozen artifact was modified. No write
occurred outside the branch lane. `canonical15_noThumbAA` was **not** run (it drops
a different dimension and would be a rescue). No deployed transform is emitted.

## 2. Verified state (executed, not inferred)

| item | evidence |
|---|---|
| Frozen plan | hashed before any new cross-dataset numerical outcome; sidecar agrees; no BOM |
| canonical16 mapping | verified against **both** adapters at freeze time; DB9 columns `[0,1,2,3,4,6,16,7,8,17,9,11,18,13,15,19]` |
| Parity, emg2pose | hand-rolled selection vs frozen adapter, 4 218 756 samples — **max \|diff\| = 0.0** |
| Parity, DB9 | 77 files / 77 354 864 samples — **max \|diff\| = 8.88e-16 rad**, cause identified (divide vs multiply by π/180) |
| Parity, central-third median | 42/42 cells re-derived, **max \|diff\| = 4.44e-16 rad** |
| Cross-path agreement | 13 construction paths, **none disagree** |
| Reference posture | movement 11 central phase, **mean \|angle\| = 0.854°**, ratio 0.040 to other movements |
| Anchor test | per-finger MCP/PIP/DIP changes, pooled and per source database |
| Movement stream | 16/17 movements match their documented class; movement 15 is anomalous |
| Source databases | DB2−DB1 gap with subject-level bootstrap CI, 11/16 dimensions exclude 0 |
| Matched semantics | 4 CLASS_1 / 6 CLASS_6 / 39 NON_TARGET human windows, 4 not evaluable |
| Structural test | alignment-invariant configuration geometry, Spearman ρ = +0.059 |
| Round-trip | emg2pose kept dimensions bit-exact; **no inverse fabricated** |
| Fact check | **303 assertions, all pass** |
| Repo integrity | `baseline/emg2pose` HEAD `5f6f62b1…`, `git status --porcelain` empty |

## 3. The finding in one paragraph

The DB9 → canonical16 mapping is arithmetically **exact**, and every *semantic*
criterion — anatomical DOF, indexing, unit, positive direction (with the one frozen
thumb-AA flip), zero definition, reference pose, angle convention, range/wrapping —
**passes for all 16 dimensions**. Criterion **J (preprocessing/calibration
semantics)** fails: DB9's numbers come from a per-channel linear sensor calibration
whose gains were derived on 10 subjects and applied to 77, while emg2pose's come
from an inverse-kinematics fit of a generic hand model. That shows up as four DB9
channels that do not track their joints: **the middle, ring and pinky DIP channels
move in the wrong direction when the finger flexes**, and the middle PIP channel is
broken at the calibration level (its raw glove value changes by 107 units during
fist closure while the released angle changes by −5.6°). The official DB9 page warns
about exactly this: DIP sensors "may provide partial results when the hand of the
subject is small".

**A quantitative bound on how much this explains.** A post-hoc magnitude check
(`BROKEN_CHANNEL_CONTRIBUTION.json`) re-derives a per-gesture Gaussian/Mahalanobis
model from the frozen DB9 representative postures and applies it to the 86 858
frozen paired emg2pose GT frames: **0.9609 UNKNOWN with all 16 dimensions, 0.8861
with the four POSSIBLE OFFSET dimensions removed** — a 7.5-point improvement,
against the previous branch's fitted 0.8057. So the broken channels are a **real but
partial** contributor, and the previous branch's headline was **not** merely an
artifact of them. Only the *difference* between the two columns is interpretable
(a plain sample covariance over-rejects relative to the frozen shrinkage pipeline),
and the check was run after the verdict, changing nothing.

## 4. Recommended next branch (do NOT skip the ordering)

> **Branch: "is a physically valid DB9 sub-corpus recoverable?"**
> 1. **DB9-internal repeatability.** 6 repetitions per movement per subject exist.
>    Estimate within-subject, within-movement repeatability per channel. This
>    separates "between-subject calibration-gain failure" from "unrepeatable
>    measurement" and **has never been computed**.
> 2. **Subject-level channel screening on DB9 alone** — e.g. "does the channel
>    change in the correct direction between the two documented anchors, by a
>    plausible amount?" **Freeze the gate before any external scoring.** Do not fit
>    it to emg2pose.
> 3. **Re-derive the six-gesture corpus from eligible subjects only** and re-run the
>    closed-set DB9 internal validation as a control (it should barely move: 0.978).
> 4. **Only then** re-run the external distributional readout, against both the old
>    and the screened corpus so the cost of screening is visible.
> 5. **Separately and cheaply:** re-estimate Session-5's **77.04 % beyond-p95**
>    figure using only eligible channels. That is the cleanest existing measurement
>    of genuine distribution shift and it has never been computed without the broken
>    channels.

**Do not** run `canonical15_noThumbAA` as a rescue. **Do not** deploy a
per-dimension offset. **Do not** re-open the open-set architecture before the
measurement is clean.

## 5. INFERENCE / NOT VERIFIED — do not treat as established

* **Handedness (criterion I) is UNCERTAIN on all 16 dimensions.** DB9 is a
  right-hand protocol; the emg2pose mini corpus has 15 left + 15 right recordings
  and no handedness transform is applied anywhere. Whether the UmeTrack model frame
  is handedness-invariant for the left recordings is **not established**. Cheap
  follow-up.
* **Movement 15's root cause is UNRESOLVED.** It is documented as wrist radial
  deviation but is finger-dominant in 59/77 recordings with a profile correlating
  +0.668 with hand configurations vs +0.435 with wrist movements. Relabelling vs
  protocol-numbering difference is **not distinguished**. It is not in the
  six-gesture vocabulary, so no canonical16 result is affected.
* **The failing channels' root cause is not separated.** The over-audit does not
  distinguish a wrong per-channel gain from a poorly-seated sensor from a sensor
  defect. `DIP4`'s raw sensor *decreases* during fist closure (points at
  seating/defect); `DIP3`'s sensor moves +41 units while its angle moves −30°
  (points at gain).
* **Reference-posture repeatability is not decomposed.** DB2's reference is nearly
  exact (mean \|angle\| 5.911°) while DB1's is 18.001° and DB5's 21.268°. Whether
  that is anatomy, protocol compliance, or gain is **not determined**; the
  within-subject repetition structure exists but was not exploited.
* **emg2pose is one subject.** Session/prompt per-dimension spread has median
  **72.24°** against a cross-dataset median gap of **19.32°** (ratio 3.74), so **no
  per-dimension cross-dataset claim in the 20–30° range is resolvable with this
  corpus at all.**
* **Matched semantics rest on n = 4 and n = 6** two-rater-consensus windows, 4 of
  which are not evaluable. Descriptive only.
* **The S4/UmeTrack cross-check measures interior angles**, which equal joint angles
  only for in-plane rotation. The PIP round-trip (≤ 0.9°) confirms the convention;
  the DIP residuals (7–14°) are the expected out-of-plane component and are **not**
  evidence about DB9.

## 6. Contaminated / discarded results

**None.** No number in the report comes from a partial run. One rewrite is recorded:
the first draft of `pca_large_offset.py` materialised an
(n_frames × n_prototypes × n_dims) broadcast requiring **> 11 GB**; the process was
killed and the tool rewritten to read the cached movement medians and make one
bounded pass over the raw files. **No result was lost** — the per-finger anchor test
was already computed independently by `pca_dip_validity.py`.

Four other bugs were found and fixed in-loop (numpy 1.26 has no `np.trapezoid`; a
148 GiB KDE temporary; an all-NaN joint-identity test from an `Inf` overflow; a
dict-comprehension key referencing its own value variable; the human-consensus
endpoint vocabulary being `CLASS_1`/`CLASS_6`/`NON_TARGET` rather than the
`HUMAN_*` spelling). The last one now **hard-fails** rather than emitting an empty
cohort. Also: `db9_pick_file_for_slot` originally keyed on the filename tag `_E2_`,
which is a **source-database naming artefact** (DB1/DB5 use `_E2_`, DB2 uses
`_E1_`); it now identifies the protocol file **from the data**.

## 7. Open housekeeping item (not fixed, by the no-write rule)

`data/ninapro_db9/dataset.npz::X_can16` is a **stale second DB9 canonical16 store**
whose mtime (2026-09-17 23:31) predates the frozen adapter (2026-09-18 00:31). On
matched movement labels it disagrees with a from-scratch run on 10 of 16 dimensions.
**No current code reads it** (verified by repository-wide search), and every frozen
result derives from `representative_postures_77.npz`, which this audit reproduces to
4.4e-16 rad — so it is an **ORPHANED / STALE ARTIFACT**, not a live conflicting
definition. Recommendation for a future branch: quarantine it to
`data/ninapro_db9/_invalidated/` (matching the existing convention in
`data/db9_posture16/_invalidated/`) or regenerate it with the frozen adapter.
**This branch did neither.**

## 8. External runtime state — re-verify, do not assume

* **No servers were started and none is needed.** CPU-only: descriptive statistics,
  classical linear algebra, classical variance decompositions.
* No background process was left running. `<PROJECT_ROOT>` and `<EMG2POSE_VENV>` are
  junctions; if missing, recreate with `cmd /c mklink /J`.
* Use `<EMG2POSE_VENV>\Scripts\python.exe` (sklearn 1.5.2). The Anaconda
  interpreter (sklearn 1.7.1) was **not** used.
* A read-only, time-boxed web fetch of the **official Ninapro DB9 page** was made to
  verify the DIP-sensor caveat and the released-variable semantics; the URL and the
  quoted caveat are recorded in `OFFICIAL_SOURCE_REFERENCES.md`. No other external
  source was consulted.
* Other python processes seen on this machine belong to a different project and were
  not touched.

## 9. First concrete actions for the successor session

1. **Do not continue this branch.** If the PI wants the repair, start a new lane
   with its own frozen plan per §4.
2. Reproduce: `python tools/pose_coordinate_fact_check.py` first (it re-hashes the
   frozen plan, re-derives the mapping from both adapters, and checks 303
   assertions). If it passes, the state is intact.
3. Full re-run order is in `POSE_COORDINATE_AUDIT_FULL_LOG.txt`. Note that
   `pca_db9_cache.py` caches the movement medians (keyed on the SHA-256 of all 77
   `.mat` files), so the raw passes are cheap after the first build.
4. To regenerate figures only: `python tools/pca_figures.py` (reads artifacts only).
5. **Do not** re-serialise JSON before hashing, and do not round-trip source files
   through PowerShell (it silently prepends a BOM).
6. **Do not** tune anything against the 53 scored or 49 paired windows.
