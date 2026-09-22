# CANONICAL16 CODE PROVENANCE

Frozen plan: `c59fe01370d48aedeed56ef7a4103506d14a298edb794723be3720531edd62c6`

## Authority

canonical16 has exactly ONE authority per side: representation/canonical_hand.py for emg2pose and representation/db9_to_canonical16.py for DB9.  Every other file either imports one of them or consumes a stored artifact.

## Every construction path found by a repository-wide search

| id | kind | file | symbol | transformation | outputs |
|---|---|---|---|---|---|
| `P1_emg2pose_adapter` | transform | `representation/canonical_hand.py` | `to_canonical16` | name-resolved column selection; no unit change; no sign change | canonical16 (16, radians); validity mask |
| `P2_emg2pose_extract` | wrapper | `representation/canonical_hand.py` | `extract` | calls P1 | Canonical16(values, valid) |
| `P3_bridge_common` | consumer | `bridge_audit/_common.py` | `(import)` | imports P1; no local re-derivation | canonical16 |
| `P4_visual_inverse` | inverse | `bridge_audit/visual_check.py` | `embed_canonical16_in_official20` | scatter canonical16 back into 20D; the 4 dropped DOF set to 0.0 | 20D with MCP-AA = 0 |
| `P5_stageh_inverse` | inverse | `human_semantic_validation/tools/s6_h_eval_core.py::embed16_in_20` | `embed16_in_20` | same convention as P4 (MCP-AA = 0) | 20D with MCP-AA = 0 |
| `P6_distributional_consumers` | consumer | `db9_distributional_open_set/tools/*` | `(multiple)` | consume stored canonical16; no re-derivation | model scores |
| `P7_stored_emg2pose` | artifact | `bridge_audit/results/sessions/*.paired50hz.npz` | `gt16 / pred16` | ACTUAL PATH: official 20D -> P1 -> 40-sample block mean at 50 Hz -> stored float32 | stored canonical16 (float32) |
| `P8_db9_adapter` | transform | `representation/db9_to_canonical16.py` | `to_canonical16` | name-resolved column selection; degrees -> radians; ONE frozen sign flip on thumb_cmc_ab_adduction | canonical16 (16, radians); validity mask |
| `P9_db9_canonical12` | transform | `representation/db9_to_canonical16.py` | `to_canonical12_noDIP` | P8 then drop the four DIP columns | canonical12 |
| `P10_db9_canonical15` | transform | `representation/db9_to_canonical16.py` | `to_canonical15_noThumbAA` | P8 then drop thumb_cmc_ab_adduction | canonical15 |
| `P11_posture16_builder` | builder | `posture_decoder/experiments/run_posture16.py` | `extract_representatives` | apply P8, then median over the central third of each labelled repetition; unit = subject x movement x repetition | representative_postures_77.npz |
| `P12_stored_db9_reps` | artifact | `data/db9_posture16/representative_postures_77.npz` | `X_canonical16` | ACTUAL PATH: raw .mat -> P8 -> central-third median -> stored float64 | 7854 x 16 canonical16 (float64) |
| `P13_stored_db9_frames` | artifact | `data/ninapro_db9/dataset.npz` | `X_can16` | ACTUAL PATH: raw .mat -> P8 (frame level, no median) -> stored float32 | 1 266 058 x 16 canonical16 (float32) |

## Edges

```
P1_emg2pose_adapter  ->  P2_emg2pose_extract
P1_emg2pose_adapter  ->  P3_bridge_common
P1_emg2pose_adapter  ->  P7_stored_emg2pose
P4_visual_inverse  ->  P7_stored_emg2pose
P5_stageh_inverse  ->  P7_stored_emg2pose
P7_stored_emg2pose  ->  P6_distributional_consumers
P8_db9_adapter  ->  P9_db9_canonical12
P8_db9_adapter  ->  P10_db9_canonical15
P8_db9_adapter  ->  P11_posture16_builder
P11_posture16_builder  ->  P12_stored_db9_reps
P8_db9_adapter  ->  P13_stored_db9_frames
P12_stored_db9_reps  ->  P6_distributional_consumers
```

## Cross-path numerical agreement

* emg2pose, hand-rolled selection vs the frozen adapter: **max |diff| = 0.000e+00** (bit-exact = True)
* emg2pose, `extract` wrapper vs `to_canonical16`: **max |diff| = 0.000e+00**
* DB9, hand-rolled conversion vs the adapter over 77 files: **max |diff| = 8.882e-16 rad** (within float64 roundoff = True)

**No two paths construct canonical16 differently on the same input.** The only non-zero difference anywhere is the DB9 adapter dividing by `DEGREES_PER_RADIAN` where the hand-rolled reconstruction multiplies by `pi/180`: the same operation, a different floating-point sequence, at most one ULP.

## The second DB9 store

`data/ninapro_db9/dataset.npz::X_can16` is a second DB9 canonical16 store.

* stored mtime: 2026-09-17T23:31:56 (Windows local)
* adapter mtime: 2026-09-18T00:31:49 (Windows local)
* worst per-dimension median difference on matched movement labels: 3.903 rad
* classification: **ORPHANED / STALE ARTIFACT.  A scale-blocking housekeeping item, not a science-blocking finding: it must not be read as a canonical16 source, and it is left untouched per the audit's no-write rule.**

the stored corpus PREDATES the current frozen DB9 adapter by about one hour.  Six of the sixteen dimensions agree exactly (difference 0.0) while ten do not, and the non-matching differences are systematic rather than random -- the signature of a different conversion applied to part of the vector, not of a striding artefact.

a repository-wide search finds NO current code that reads data/ninapro_db9/dataset.npz.  The confirmatory DB9 lane (posture_decoder/experiments/run_full_db9.py) quarantines pre-existing caches and REBUILDS representative postures from the raw files, and every frozen result in this project is derived from representative_postures_77.npz (P12), which was regenerated after the adapter was frozen and which this audit independently reproduces to 4.4e-16 rad.

Recommendation: a future branch should either quarantine it into data/ninapro_db9/_invalidated/ (matching the existing convention in data/db9_posture16/_invalidated/) or regenerate it with the frozen adapter.  This audit does neither.

## What this means for the audit

The audit's top-priority check — *if two code paths differ numerically, that is a high-priority finding* — is **clean**. The coordinate question is therefore not a software defect; it is a data-calibration question, which is where the rest of this branch looks.

