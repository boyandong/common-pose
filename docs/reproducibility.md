# Reproducibility

## 1. What this repository does and does not ship

**Does ship:** source code, analysis protocols as executable definitions, frozen plans with
hashes, machine-readable audit verdicts, curated provenance manifests, and contract tests
that run without any dataset.

**Does not ship:** any third-party dataset, any model checkpoint, any large experiment
output. Nothing under `audits/` is raw data — it is verdicts, ledgers and hashes.

## 2. Datasets

Every dataset is fetched from its official source. `datasets/`, `data/`, `checkpoints/` and
the data-shaped extensions (`*.mat`, `*.h5`, `*.hdf5`, `*.npz`, `*.npy`, `*.ckpt`, `*.pth`,
`*.zip`, `*.tar`) are ignored repository-wide.

| dataset | used for | official source | licence |
|---|---|---|---|
| **Ninapro DB9** | calibrated CyberGlove-II kinematics; the physical audit and the posture task | <https://ninapro.hevs.ch/instructions/DB9.html> · Jarque-Bou, Atzori & Müller, *Sci Data* **7**:12 (2020), [doi:10.1038/s41597-019-0349-2](https://doi.org/10.1038/s41597-019-0349-2) · URL pattern `https://ninapro.hevs.ch/files/DB9/<source_db>/s_<n>_angles.zip` | see the official site; redistribution terms are not stated there, so the data is **not** mirrored here |
| **emg2pose** | sEMG → pose front end; UmeTrack hand model and joint ordering | <https://github.com/facebookresearch/emg2pose> · dataset <https://fb-ctrl-oss.s3.amazonaws.com/emg2pose/emg2pose_dataset.tar> | CC-BY-NC-SA-4.0 (bundled UmeTrack CC-BY-NC-4.0) — **not redistributed here** |
| **KIN-MUS UJI** | external pose source with a task-phase label | [doi:10.5281/zenodo.3469380](https://doi.org/10.5281/zenodo.3469380) | CC-BY-4.0 |
| **KINE-ADL BE-UJI** | external ADL kinematics | [doi:10.17632/8mf4y2srgh.4](https://doi.org/10.17632/8mf4y2srgh.4) | CC-BY-4.0 |
| **MyoKi** | external pose + sEMG + IMU corpus | see `audits/dataset_admission/pose_api_admission/OFFICIAL_SOURCE_REFERENCES.md` | recorded per record in that file |
| **HUST** | **rejected** — paper retracted, data unobtainable | [retraction notice](https://doi.org/10.1371/journal.pone.0151685) | n/a |

Source-level detail — including access dates, HTTP outcomes of every download attempt, and
what each source does *not* establish — is in
[`audits/dataset_admission/pose_api_admission/OFFICIAL_SOURCE_REFERENCES.md`](../audits/dataset_admission/pose_api_admission/OFFICIAL_SOURCE_REFERENCES.md).
Nothing there is cited from memory.

## 3. Running without any data

```bash
python -m pip install -r requirements.txt
python -m pytest tests/ -q
```

58 tests, no dataset, no GPU, no network. `tests/test_db9_adapter_synthetic.py` builds its
own minimal `.mat` in a temp directory, so the full adapter path — channel-order resolution,
the segmentation-trap refusal, verdict-driven validity, utility-protocol segmentation — is
exercised without touching any third-party release.

## 4. Running with DB9

```bash
export COMMON_POSE_DB9_RAW=/path/to/ninapro_db9/raw
export COMMON_POSE_DB9_ROOT=/path/to/ninapro_db9          # containing extracted/
export COMMON_POSE_DB9_OUT=/path/to/scratch/out           # NOT the published audits/ path
```

> **Point `COMMON_POSE_DB9_OUT` at a scratch directory.** The audit drivers write into it,
> and re-running against `audits/db9/channel_forensic/` overwrites the frozen artifacts
> published here.

Driver order matters: `verdicts.py` freezes the trusted subset and `utility.py` asserts
against that frozen subset, so 03 must run before 04. See
[`db9_trusted_subset.md`](db9_trusted_subset.md) §7 for the full command list.

Environment notes recorded because they are traps rather than preferences:

* DB9's released `.mat` files are read with `scipy.io`. On a Windows checkout under a
  non-ASCII path, `h5py` cannot open HDF5 files at all (`mbcs` codec failure) — use an ASCII
  junction and do **not** call `Path.resolve()` on it, which silently follows the junction
  and undoes the workaround.
* `repetition` is **not** the per-movement cycle counter. `rerepetition` is. See
  `docs/db9_trusted_subset.md` §4.5.

## 5. Running with emg2pose

The baseline is not vendored, for licensing and packaging reasons.

```bash
git clone https://github.com/facebookresearch/emg2pose
# Python 3.10 is pinned by its environment.yml; kinematics.py fails at import on 3.11
export COMMON_POSE_EMG2POSE_BASELINE=/path/to/emg2pose
```

The adapter locates the checkout through that variable and raises with instructions rather
than guessing, because a wrong path there yields a silently different joint ordering. It
also cross-checks its own IK-failure mask against the official
`emg2pose.utils.get_ik_failures_mask` on the recording's ground truth and **refuses to emit
validity if they disagree**.

## 6. Reproducibility properties this project actually enforces

| property | mechanism |
|---|---|
| audit rules cannot be adjusted after seeing the outcome | each lane freezes a plan SHA-256 **before** running; the artifacts record it |
| the trusted subset was not selected on performance | the artifact records `frozen_before_any_classifier: true`, and the utility arm runs afterwards and asserts against the frozen hash |
| curated code is the code that produced the artifact | `provenance/*.json` records source path, source SHA-256 and target SHA-256 per file |
| a metric cannot be read without its protocol | `ClassificationReport` carries n, n_classes, chance, per-class recall and a missing-class list |
| subject leakage is not silently introduced | normalisation is train-fold-only by construction; metrics take opaque subject ids; docs forbid DB9's in-file `subject` field |
| a defective released channel is not silently re-adopted | verdicts are carried on the vocabulary; adapters declare whether the DB9 verdicts are authoritative for their source |

## 7. Known reproducibility limits

Stated plainly, because a reproducibility section that only lists strengths is marketing.

1. **`COMMIT PENDING` throughout the historical record.** The research workspaces predate
   version control. Their provenance is content-hash based. This repository starts a clean
   history and does not carry the old one.
2. **Raw gauges are unpublished for DB9, KIN-MUS and KINE-ADL.** For DB9, 16 of 22 released
   columns were recovered exactly as affine/affine-quadratic functions of a single raw
   column — that validates the transform *form*, not its scale generalisation from the 10
   calibration subjects to the other 67. Full raw→processed parity is unclosable on any of
   these corpora without the authors' gains.
3. **Two corpora were never obtained.** MyoKi (145 GB) and KINE-ADL (`BE_UJI_DATASET.mat`,
   644 185 378 B, sha256 `808f0dab…`). Statements about them are document-level, not
   value-level.
4. **The full emg2pose corpus (431 GiB) was never downloaded.** It exceeds local free space
   by ~582 GiB and the measured network path would take ~685 days. A verified server runbook
   exists instead.
5. **The trusted DB9 subset is PROVISIONAL.** The utility arm covers 37 Exercise-B subjects;
   the final full-DB9 validation did not complete (`tools/final_validation.py` exists in the
   port, its captured log is 0 bytes).
6. **The human-annotation lane's pre-registered endpoint is not recoverable.** Its formal
   round was interrupted by a diagnostic model-unblinding at 200 of 396 items. See
   [`../audits/human_semantic_validation/README.md`](../audits/human_semantic_validation/README.md) §4.
7. **No deep-learning training is reproducible from this repository**, by design: training
   does not run on a local workstation under this project's standing policy, and no
   training artifact is shipped. The downstream posture task is classical (one LDA per fold)
   and is reproducible.
