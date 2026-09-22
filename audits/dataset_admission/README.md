# DATASET ADMISSION & COORDINATE PROVENANCE AUDIT â€” `dataset_admission_audit_v1`

**Branch:** `S7-DATASET-ADMISSION-COORDINATE-AUDIT`
**Frozen plan:** `AUDIT_PLAN.md`, SHA-256 `fba2b20623392dd809d5ed28c7850387acc721e9a91ff1611e7fba0d89fc889d`
**Commit:** COMMIT PENDING â€” the project root is not a git repository; provenance is content-hash based.

---

## What this lane is

A DATASET ADMISSION / COORDINATE PROVENANCE AUDIT of three kinematic datasets â€” **MyoKi**,
**KIN-MUS UJI** and **KINE-ADL BE-UJI** â€” plus a P0 audit of the frozen representation
`shared10_poc_v1`.

It is **not** model work. No neural network, LDA, SVM or any other classifier was trained or
evaluated anywhere in this lane. No existing downstream result was consulted when deciding a
column, a sign, an offset, a scale, a transform or a channel subset. The one guarantee the
lane is built around is:

> "the numbers classify well" is never accepted as evidence that "the numbers are the
> anatomical joint angles we think they are".

## Headline result

`shared10_poc_v1` is a **`SHARED10-SEMANTIC-MISMATCH`**. Four of its ten frozen index
positions select a different anatomical degree of freedom than the one they are named as:

| shared10 name | column index | what the column actually is |
|---|---|---|
| `thumb_cmc_flexion` | 0 | `CMC1_A` â€” thumb CMC **abduction** |
| `index_mcp_flexion` | 4 | `MCP2-3_A` â€” index/middle relative **abduction** |
| `ring_mcp_flexion` | 9 | `MCP3-4_A` â€” middle/ring relative **abduction** |
| `pinky_mcp_flexion` | 13 | `MCP4-5_A` â€” ring/little relative **abduction** |

The correct index vector for the ten intended DOFs is `[1, 2, 5, 6, 7, 8, 10, 11, 14, 15]`.

**Root cause.** The indices are correct positions in the **MOVMUS-UJI guide v2.1 (2023)**
column order, but `KIN_MUS_UJI.mat` stores its 18 columns in the order the KIN-MUS dataset's
**own paper** (Sci Data 6:270, 2019, Table 2) gives â€” and the two orders differ by four
swapped adjacent pairs (8 of 18 positions).

See `SHARED10_PROVENANCE_AUDIT.md` and `ADMISSION_DECISION.md`.

## Grades

| dataset | grade | role |
|---|---|---|
| MyoKi | **YELLOW** | later second external geometry source; corpus (145 GB) not obtained |
| KIN-MUS UJI | **YELLOW** | first POC task source for the phase label, with a corrected representation |
| KINE-ADL BE-UJI | **GRAY** | needs `BE_UJI_DATASET.mat` before anything can be confirmed |

## How to re-run

```powershell
cd <DATA_ROOT>set_admission_audit_v1
$py = "<EMG2POSE_VENV>\Scripts\python.exe"
foreach ($s in @("01_source_freeze","02_schema_audit","03_shared10_provenance",
                 "04_myoki_special","05_kinmus_special","06_kineadl_special",
                 "07_coordinate_ledger","08_common_api_matrix","09_label_admission",
                 "10_sync_physical_qc","11_figures","12_decision","13_manifest",
                 "99_fact_check_audit")) { & $py "scripts\$s.py" }
```

Drivers are deterministic and idempotent: each overwrites only its own artifacts. Files
whose names start with `_` are exploratory reconnaissance and are **excluded from the
evidence chain** (frozen plan section 17).

`13_manifest.py` must run before `99_fact_check_audit.py`, because the fact check asserts
against the manifest.

## Deliverables

| file | content |
|---|---|
| `AUDIT_PLAN.md` / `PLAN_SHA256.txt` | the frozen rules, thresholds and vocabularies |
| `SOURCE_PROVENANCE.md` | every source, its bytes, its SHA-256, what was and was not downloaded |
| `DATASET_MANIFEST.csv` | machine-readable version of the above |
| `SCHEMA_AUDIT.md` | actual schema of each dataset, with the documented-vs-empirical discrepancies |
| `SHARED10_PROVENANCE_AUDIT.md` | the P0 finding, all four discrimination tests, both hypotheses |
| `COORDINATE_LEDGER.csv` | 72 rows: one per kinematic channel of the three datasets |
| `PHYSICAL_QC.md` | physical anchors, subject as the unit, with full distributions |
| `LABEL_AUDIT.md` / `LABEL_ADMISSION_MATRIX.csv` | label provenance and admission |
| `SYNC_AUDIT.md` | real update rates and representation inflation |
| `COMMON_API_MAPPING_MATRIX.csv` | 16 canonical16 DOFs Ã— 5 dataset columns |
| `ADMISSION_DECISION.md` | the terminal report |
| `BUGFIX_LOG.md` | every bug and whether it invalidated an artifact |
| `ARTIFACT_MANIFEST.json` | every path and SHA-256 |
| `figures/` | six evidence figures |

## The four evidence tags

`[DOC]` official documentation Â· `[EMPIRICAL]` measured here Â· `[INFERENCE]` Â· `[UNRESOLVED]`.
`[DOC]` is never presented as `[EMPIRICAL]`. In particular, *the authors report that their
calibration is validated* is `[DOC]`; *this audit reproduced channels 1â€“16 bit-exactly* is
`[EMPIRICAL]`.

## Nothing in this lane modifies anything else

Every other lane is opened read-only. The only files this lane creates live under
`dataset_admission_audit_v1/`. `99_fact_check_audit.py` asserts this mechanically.

