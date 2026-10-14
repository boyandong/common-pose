# CommonPose frozen N80 confirmation

Direct human approval: “确认，按草案封存并执行”; subsequent transport instruction: “下载采用本地中转”. The approved scientific protocol is `SCIENTIFIC_SPEC.md`, exact enrolled users/sessions/source members are in `ENROLLMENT_MANIFEST.json`. N80 means enrollment, not eighty valid nonzero pairs.

Frozen enrollment contains 80 of the scoped 127-candidate pool, 2,768 source members and 50,213,536,592 bytes. The public tar has pinned ETag and exact byte ranges; official per-member hashes are unavailable. Local D acquisition establishes SHA256 receipts; remote qualification independently rehashes every complete file.

Primary comparisons: U full versus boundary_distance ordinary flip risk; B full versus class_model fixed common-class flip risk, both canonical 30%. Two-sided exact sign tests each alpha .025; positive direction and both endpoints required. Any missing major endpoint means full-cohort evidence_insufficient; no replenishment. Upstream checkpoint training membership unresolved. Flip preserves a frozen consumer output and is not independent gesture accuracy.

Prior manuscript/reproducible reporting release remains Git `1fc75512698c92d4bd11cf52e660c8814b1ac127`. Prescribed old-cohort 20-seed independent verification is complete. New N80 outcomes are still untested until the execution sequence below completes.

## Frozen seals and execution order

1. `FROZEN_EXECUTION_MANIFEST.json`: source acquisition/qualification code, authorized protocol/cohort and parent/checkpoint dependencies. `ANALYSIS_CODE_SEAL.json`: inference, support, analysis and independent verifier before any new prediction. Both have self-excluding external SHA256 sidecars.
2. `acquire_sources.py` runs locally in Windows Python, writing only `D:/CommonPose_confirmation_N80_20261010/source`. Hidden background process/creation time and logs are recorded in `DURABLE_DOWNLOAD_LAUNCH_RECEIPT.json`. No neural inference or scientific fitting occurs here. Preserve completed files/receipts and partial files; never restart on a stale progress file alone. Verify exact live process first.
3. `relay_completed_sources.py` now runs concurrently with acquisition: each complete local source is rehashed, uploaded, then independently SHA256-checked on the server. Password enters stdin only. Target: `/root/autodl-tmp/common_pose_confirmation_N80_20261010/source`; pinned SSH host key is mandatory. Download and relay have separate process/progress files. The original sealed batch `relay_sources.py` is retained. `STREAM_RELAY_CODE_SEAL.json` and the dated transport amendment document this orchestration change; scientific protocol/cohort remain unchanged.
4. Transfer local relay receipt and all sealed execution files to the new remote lane. Reverify external runtime and space, then run `run_stage_job.py qualification` using `/root/miniconda3/envs/commonpose-supplement/bin/python`, OMP/OPENBLAS/MKL=8. Stop and report any frozen source/validity failure, with no replacement.
5. After successful terminal qualification, run durable stages in sequence: `reconstruction`, `support`, `analysis`, `verification`. Each gets a unique `jobs/<stage>/LAUNCH.json` with real process handles and `TERMINAL.json` with exit status/log hash. The stage controller itself is sealed. Launch with detached subprocess whose stdin/stdout/stderr are redirected; do not rely on shell backgrounding that can retain an SSH output channel.
6. Support stage fixes B/U class sets before effect analysis. Analysis never fits or calibrates. Verification separately rescores frozen models and independently checks ordering, risk/counts, 20 seeds, effects, exact-sign statistics, bootstrap intervals, support sets, labels and cache lineage. Both positive and negative/incomplete results must be reported.
7. After all stages terminal with exit zero and independent PASS, `export_backup_manifest.py` enumerates immutable caches, dependencies and results; fetch the manifest and use `backup_runtime_to_D.py` with stdin credentials. It hashes copied files and rehashes every retained local source. Complete the prospective report and paper update only from verified results.

Numeric runtime: Python3.10.13, NumPy1.26.4, SciPy1.13.1, sklearn1.5.2, joblib1.4.2, threadpoolctl3.7.0; numerical threads all8. Neural runtime uses the previously checked torch2.8.0+cu128/RTX5090D. Dependencies and upstream tracked tree must match exact seals before prediction. Current 200 GiB remote quota satisfies full-retention planning, but each long stage must recheck live capacity.

`OLD_CACHE_EXECUTION_VALIDATION.json` PASS validates 840 canonical seven-method risk values on old FINAL only, exact ordering, exhaustive small-n signs and zero/missing/negative/alpha edge cases. It is an implementation control, not prospective evidence. No old users overlap N80.

## Limits

Local history scope does not certify unsaved, outside-root or private remote access absent. The approved narrower claim retains that limitation and unknown upstream membership. Sampled source metadata PASS is not full-source validity PASS. Cached sources/models are private and remain outside Git; do not redistribute. This phase is incomplete while acquisition/inference/verification/backup/reporting remains outstanding.
