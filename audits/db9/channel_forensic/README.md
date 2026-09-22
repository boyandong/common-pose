# DB9 CHANNEL FORENSIC + TRUSTED-SUBSET VALIDATION — `db9_channel_forensic_v2`

**Branch:** `S8-DB9-CHANNEL-FORENSIC`
**Frozen plan:** `FORENSIC_PLAN.md`, SHA-256 `4c618b562903d0d364d03bb8a997ef6b4140bd9e09d0f2475f1b008ad80c8793`
**Commit:** COMMIT PENDING (the project root is not a git repository; provenance is content-hash based)

---

## The two questions

**Q1.** Are the DB9 channels that we or an independent paper suspected of being physically
broken *really* broken, or were the anomalies an artefact of our own extraction / QC?

**Q2.** After excluding untrustworthy channels with **no reference at all to classification
performance**, do the remaining trusted physical channels still support DB9 posture
classification?

## Headline answers

* **DIP3 and DIP5: `REAL_DB9_PROBLEM`.** On an unambiguous fist the raw DIP gauge and the
  released angle move together and *opposite* to the published "flexion +" criterion in
  35/37 and 32/37 subjects, while every MCP and PIP channel in the very same segments moves
  the documented way in 37/37.
* **CMC5: `REAL_DB9_PROBLEM`, and not for the reason the literature gave.** The released
  CMC5 column is an exact linear function (slope 0.28511 = the published 0.285) of the *same
  raw sensor* that feeds `WRIST_F`. One sensor cannot be both the palmar arch and the wrist.
* **DIP4: `INCONCLUSIVE`** — inverted in only 28/37 subjects and with a raw response 16 % of
  the flexion-channel median.
* **Sensor 11 / MCP2_a: `NO IMPACT`** — released as an all-NaN column and never selected by
  any representation in this project.
* **The old "many channels fail" verdict: `PARTIALLY_OVERTURNED`.** It was produced on
  segmentation keyed to the **pre-relabelling** `repetition` vector, which is misaligned with
  the kinematics in **24 of 99** files. Under correct segmentation eight channels are
  exonerated.
* **`TRUSTED_DB9_POSE_v1` = 8 channels**, frozen before any classifier ran.
* **Trusted-subset classifier on the hand-shape task: BA 0.7254** (arm A historical 16-channel
  reference: 0.8538; chance 0.1111; no class collapse).
* **Final decision: `DB9-ADMIT-REDUCED`.**

## How to re-run

```powershell
cd <PROJECT_ROOT>\db9_channel_forensic_v2
$py = "<EMG2POSE_VENV>\Scripts\python.exe"
& $py scripts\01_segmentation.py
& $py scripts\02_forensic_core.py
& $py scripts\03_verdicts.py          # freezes TRUSTED_DB9_POSE_v1
& $py scripts\04_utility.py           # slow: ~4 min
& $py scripts\04b_utility_posture_only.py
& $py scripts\05_decision.py
& $py scripts\99_fact_check.py
```

Scripts starting with `_` are reconnaissance or one-shot patchers and are **excluded from the
evidence chain** (frozen plan section 17). Drivers must run in numeric order; 03 must run
before 04, because 04 asserts against the frozen subset.

## Files

| file | content |
|---|---|
| `FORENSIC_PLAN.md` / `PLAN_SHA256.txt` | the frozen rules, thresholds and verdict vocabulary |
| `SEGMENTATION_VALIDATION.md` | the gate: alignment, segment validity, reference identification |
| `DB9_CHANNEL_LEDGER.csv` | 22 rows, one per released channel |
| `FLAGGED_CHANNEL_FORENSICS.md` | the full forensic chain for DIP3/4/5 and CMC5 |
| `SENSOR11_IMPACT.md` | Sensor 11 released status and historical impact |
| `DIP_HANDSIZE_ANALYSIS.md` | the hand-size hypothesis |
| `TRUSTED_DB9_POSE_v1.json` / `TRUSTED_SUBSET_SHA256.txt` | the frozen trusted subset |
| `BUGFIX_LOG.md` | every bug, with root cause and artifact-invalidation status |
| `DB9_FORENSIC_DECISION.md` | the terminal report |
| `artifacts/`, `figures/`, `logs/` | machine-readable outputs, figures, captured stdout |

## What this lane did NOT do

No deep learning, no model optimisation, no open-set rescue, no new dataset audit, no
re-research of KIN-MUS / MyoKi / KINE-ADL. No historical result directory was modified; every
other lane is opened read-only. No sign flip, offset, affine alignment or rescaling was
applied to any released array.
