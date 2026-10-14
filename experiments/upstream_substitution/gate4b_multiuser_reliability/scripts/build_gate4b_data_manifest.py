"""One-time read-only inventory of frozen Gate4B acquisition bytes and HDF5 structure.

The output is hash-sealed and explicitly records failures. It does not qualify a
failed cohort or replace the frozen structural verifier.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

import h5py
import numpy as np


LANE = Path(__file__).resolve().parents[1]
ROOT = Path("/root/autodl-tmp/gate4b_data")
STAGE = Path("/root/autodl-tmp/gate4b_relay_staging")
PLAN_SHA = "908b5bdbe90e8f9713f85bd886f18a1bcecaa304db575582582c8801e6cb9555"
COHORT_SHA = "def6c5e70773241389101d1789df5e389146ed748b1d5e0b87b336a3e82af96f"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(4 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    output = LANE / "artifacts" / "DATA_MANIFEST.json"
    seal = LANE / "artifacts" / "DATA_MANIFEST.sha256"
    if output.exists() or seal.exists():
        raise FileExistsError("DATA_MANIFEST is already sealed; refusing overwrite")
    acquisition_path = LANE / "DATA_ACQUISITION_MANIFEST.json"
    acquisition = json.loads(acquisition_path.read_text(encoding="utf-8"))
    cohort = json.loads((LANE / "COHORT_MANIFEST.json").read_text(encoding="utf-8"))
    allowed = {(x["split"], x["participant_id"], x["session_id"]): x
               for x in cohort["selected"] if x["split"] in {"DEV", "VALIDATION"}}
    errors: list[str] = []
    if digest(LANE / "GATE4B_PLAN.md") != PLAN_SHA:
        errors.append("frozen plan SHA256 differs")
    if digest(LANE / "COHORT_MANIFEST.json") != COHORT_SHA:
        errors.append("frozen cohort SHA256 differs")
    files = acquisition["files"]
    if len(files) != 964 or len(allowed) != 28:
        errors.append("frozen file or session count differs")
    if acquisition.get("task_status") != "ACQUIRED_REMOTE_PENDING_STRUCTURAL_VERIFICATION":
        errors.append("acquisition task status differs")
    expected_paths: set[Path] = set()
    session_rows: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    audited: list[dict] = []
    for i, row in enumerate(files, 1):
        key = (row["split"], row["participant_id"], row["session_id"])
        path = ROOT / row["split"] / row["participant_id"] / Path(row["source_member"]).name
        expected_paths.add(path)
        issues: list[str] = []
        if key not in allowed:
            issues.append("unauthorized session")
        if row.get("acquisition_status") != "COMPLETE" or row.get("remote_acquisition_status") != "COMPLETE":
            issues.append("acquisition status is not COMPLETE")
        if row.get("acquired_path") != str(path) or row.get("remote_acquired_path") != str(path):
            issues.append("manifest path differs")
        actual_size = path.stat().st_size if path.is_file() else None
        actual_sha = digest(path) if actual_size is not None else None
        if actual_size != row["expected_metadata_size"] or actual_size != row.get("actual_byte_size"):
            issues.append("size differs")
        if actual_sha != row.get("sha256"):
            issues.append("SHA256 differs")
        n = None
        gt_upper = None
        if actual_size is not None:
            try:
                with h5py.File(path, "r") as h:
                    g = h["emg2pose"]
                    ts = g["timeseries"]
                    if not {"emg", "joint_angles", "time"}.issubset(ts.dtype.names or ()):
                        issues.append("required streams absent")
                    else:
                        emg, angles, times = ts["emg"], ts["joint_angles"], ts["time"]
                        n = len(times)
                        if emg.shape != (n, 16) or angles.shape != (n, 20):
                            issues.append("stream shape differs")
                        if n <= 1830:
                            issues.append("rows do not cover frozen 1790 context plus 40 block")
                        if not np.isfinite(times).all() or not np.all(np.diff(times) > 0):
                            issues.append("timestamps invalid")
                        for attr, value in (("user", row["participant_id"]),
                                            ("session", row["session_id"]), ("side", row["hand"])):
                            found = g.attrs.get(attr, "")
                            if isinstance(found, bytes):
                                found = found.decode("utf-8")
                            if str(found) != value:
                                issues.append(f"embedded {attr} differs")
                        if n > 1830 and angles.shape == (n, 20):
                            blocks = (n - 1790) // 40
                            valid = np.isfinite(angles[1790:]).all(axis=1) & ~np.all(
                                np.isclose(angles[1790:], 0.0), axis=1)
                            block_valid = valid[:blocks * 40].reshape(blocks, 40).all(axis=1)
                            block_valid[0] = False
                            gt_upper = int(block_valid.sum())
            except Exception as exc:
                issues.append(f"HDF5 parse failure: {type(exc).__name__}: {exc}")
        result = {"split": row["split"], "participant_id": row["participant_id"],
                  "session_id": row["session_id"], "hand": row["hand"],
                  "source_member": row["source_member"], "path": str(path),
                  "expected_size": row["expected_metadata_size"], "actual_size": actual_size,
                  "manifest_sha256": row.get("sha256"), "actual_sha256": actual_sha,
                  "hdf5_rows": n, "gt_valid_50hz_blocks_upper_bound": gt_upper,
                  "issues": issues}
        audited.append(result)
        session_rows[key].append(result)
        if i % 100 == 0:
            print(f"AUDITED {i}/{len(files)}", flush=True)
    present = set(ROOT.rglob("*.hdf5"))
    if present != expected_paths or len(expected_paths) != len(files):
        errors.append("official HDF5 membership differs from exact manifest")
    official_partials = sorted(str(x) for x in ROOT.rglob("*.partial"))
    if official_partials:
        errors.append("official data root contains partial files")
    stage_partials = sorted(STAGE.rglob("*.partial"))
    archived = []
    for p in stage_partials:
        archived.append({"path": str(p), "size": p.stat().st_size, "sha256": digest(p),
                         "legacy_archive": "legacy_partials" in p.parts})
    if any(not item["legacy_archive"] for item in archived):
        errors.append("active relay stage partial exists")
    sessions = []
    for key, frozen in sorted(allowed.items()):
        rows = session_rows.get(key, [])
        upper = sum(x["gt_valid_50hz_blocks_upper_bound"] or 0 for x in rows)
        issues = []
        if len(rows) != frozen["record_count"]:
            issues.append("record count differs")
        if Counter(x["hand"] for x in rows).keys() != {"left", "right"}:
            issues.append("both hands absent")
        if upper < 10_000:
            issues.append("GT-valid upper bound below 10000")
        if any(x["issues"] for x in rows):
            issues.append("one or more file structural failures")
        sessions.append({"split": key[0], "participant_id": key[1], "session_id": key[2],
                         "record_count": len(rows), "gt_valid_50hz_blocks_upper_bound": upper,
                         "issues": issues})
    file_failures = sum(bool(x["issues"]) for x in audited)
    session_failures = sum(bool(x["issues"]) for x in sessions)
    report = {"schema": "gate4b-data-manifest-v1", "status": "STRUCTURAL_FAILURE" if
              errors or file_failures or session_failures else "ACQUISITION_STRUCTURE_PASS_GT_ONLY",
              "final_eligibility_certified": False, "prediction_validity_checked": False,
              "acquisition_manifest_sha256": digest(acquisition_path), "frozen_plan_sha256": PLAN_SHA,
              "frozen_cohort_sha256": COHORT_SHA, "expected_files": 964,
              "audited_files": len(audited), "expected_bytes": sum(x["expected_size"] for x in audited),
              "actual_bytes": sum(x["actual_size"] or 0 for x in audited),
              "file_failures": file_failures, "session_failures": session_failures,
              "global_issues": errors, "official_partials": official_partials,
              "archived_stage_partials": archived, "files": audited, "sessions": sessions}
    serialized = json.dumps(report, indent=2, sort_keys=True) + "\n"
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(serialized)
    seal.write_text(f"{digest(output)}  DATA_MANIFEST.json\n", encoding="ascii")
    output.chmod(0o444)
    seal.chmod(0o444)
    print(f"DATA_MANIFEST {report['status']} files={len(audited)} "
          f"file_failures={file_failures} session_failures={session_failures} "
          f"sha256={digest(output)}", flush=True)


if __name__ == "__main__":
    main()
