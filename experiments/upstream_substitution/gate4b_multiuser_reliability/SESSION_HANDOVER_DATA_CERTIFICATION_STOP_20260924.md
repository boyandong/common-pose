# Gate4B data certification stop — 2026-09-24

Recommended next task: `COMMON-POSE-INCIDENT-20260924-GATE4B-STRUCTURAL-FAILURE`.

## Objective and frozen decisions

Certify the exact frozen 964 DEV/VALIDATION HDF5 files before Gate4B inference. The cohort is 20 DEV and 8 VALIDATION sessions; CALIBRATION_LOCKED, FINAL_TEST_LOCKED, and discovery users remain unopened. The frozen plan is `GATE4B_PLAN.md` SHA256 `908b5bdbe90e8f9713f85bd886f18a1bcecaa304db575582582c8801e6cb9555`; cohort SHA256 is `def6c5e70773241389101d1789df5e389146ed748b1d5e0b87b336a3e82af96f`. Do not replace a file, record, session, or user after a structural failure. Do not run upstream inference, fit a predictor, or calculate Gate4B outcomes in this stopped branch.

## Verified state and scientific evidence

- The local relay reached 964/964 at `2026-09-24T03:08:31`, released the remote writer lock, and removed its temporary SSH key. A fresh restricted key was prepared on 2026-09-24 for independent remote inspection.
- Independent remote manifest inspection found `task_status=ACQUIRED_REMOTE_PENDING_STRUCTURAL_VERIFICATION`, 964 rows with both local and remote acquisition status `COMPLETE`, and zero `.partial` files in `/root/autodl-tmp/gate4b_data`.
- The original `scripts/verify_gate4b_data.py` stopped after 180 verified files with `AssertionError: enough source rows` on `2022-04-07-1649318400-a9a00-cv-emg-pose-demonstration@2-recording-16_left.hdf5`. See `logs/structural_verify_stdout_20260924.txt`. It did **not** complete 964-file HDF5 qualification or produce a successful `STRUCTURAL_QUALIFICATION.json`.
- A separate full read-only inventory checked exact official HDF5 membership, all 964 sizes and SHA256 hashes, HDF5 structure, timestamp order, and the 28-session inventory. All 964 files match their manifest sizes and SHA256 hashes. Actual and expected bytes both equal 17,820,612,952. There are 20 DEV and 8 VALIDATION sessions. No global membership or identity issue was found.
- Local independent readback of the sealed report and frozen cohort confirmed the plan/cohort hashes, all 964 rows belong to authorized sessions, 964 unique source members, each source name matches its frozen session and hand, and each of the 28 sessions has its frozen record count.
- Four structurally failing files belong to one frozen DEV session, participant `29ddab35d7`, session `2022-04-07-1649318400-a9a00-cv-emg-pose-demonstration@2`: recording 16 left has 1209 rows; recording 16 right has 1787 rows, both below the frozen `>1830` requirement. Recording 19 left has 231 repeated adjacent timestamps; recording 19 right has 498. Their hashes and byte sizes match the manifest. Thus the failure is in the acquired source contents, not an observed transport corruption.
- The hash-sealed full report is `artifacts/DATA_MANIFEST.json`, SHA256 `7123357b984aea9e39c79bae32289279af5c1db8775fda6fc6a85f543b8dd880`, with `artifacts/DATA_MANIFEST.sha256`. Its status is `STRUCTURAL_FAILURE`, file failures 4, session failures 1. The local copy and remote copy both passed the sidecar hash check. Both remote files are mode 444; the local copies are read-only; the script refuses to overwrite an existing manifest.
- Four old downloader partial files remain under remote `gate4b_relay_staging/legacy_partials` with recorded size/SHA256. They are outside the official root and are preserved as recovery evidence; no active relay stage partial was found. Do not delete them during this incident audit.
- A fresh remote check found the acquisition lock free and no matching Gate4B acquisition/verification process. This is a runtime snapshot to reverify later.

## Unknown or contaminated state

- No complete independent HDF5 structural qualification exists, and final eligible frame counts remain unknown because the frozen rule also requires prediction-valid rows. The structural failure blocks that inference in this branch.
- `DATA_MANIFEST.json` is a sealed **failure inventory**, not a scientific admission certificate. `DATA_ACQUISITION_MANIFEST.json` may still contain transport completion status; transport completion does not supersede the structural stop.
- The frozen `GATE4B_PLAN.md` defines a multi-user ranking test of the Gate4A task-error predictor. The later six-stage requested substitution analysis adds output-preservation and error-chain questions that are not frozen in that plan. Resolve their contract prospectively in a new branch if desired; do not add them after inspecting Gate4B outcomes.
- `CONTRACT_GAP_AUDIT_20260924.md` maps the sealed plan to the later six-stage objective and lists the decisions that a new substitution branch would have to freeze before inference. It contains no outcome analysis.

## External runtime and worktree state

- Last verified remote host route: `root@connect.westd.seetacloud.com`, port 47633; lane `/root/work/common-pose/experiments/upstream_substitution/gate4b_multiuser_reliability`; official data root `/root/autodl-tmp/gate4b_data`.
- A new restricted temporary SSH key was prepared under `D:\Temp\gate4b_local_relay\ssh` for this audit and removed after remote inspection at `2026-09-24T08:23:25`. Fresh authentication is needed for later remote access. The SSH password was not stored in repo files or logs.
- The common-pose worktree was already dirty with unrelated changes and the Gate4B lane was untracked. The diagnostic script `scripts/build_gate4b_data_manifest.py`, report, seal, verifier log, and this handover were added without resetting unrelated work. No commit or push was made.

## Next actions and do not

1. Preserve the frozen 964-file manifest, failed source bytes, full failure inventory, and logs. Recheck report SHA256 and remote runtime at the start of the next task.
2. Decide whether to close this frozen Gate4B cohort as a structural failure or authorize a **new prospectively frozen** acquisition/cohort branch. Any new branch needs its own manifest, eligibility contract, and identity freeze before outcomes. This stopped branch cannot silently drop the four files or replace the session.
3. If a separate substitution study is pursued, freeze the head, adapter, shared DOFs, validity masks, exclusions, metrics, and error-chain analysis before model outputs are inspected. Preserve the old Gate4B ranking plan as its own frozen record.

Do not run inference, retrain the frozen head, compute VALIDATION outcomes, alter the 964-file list, patch timestamps, trim short records, or use this failure inventory to replace a user within the frozen branch.
