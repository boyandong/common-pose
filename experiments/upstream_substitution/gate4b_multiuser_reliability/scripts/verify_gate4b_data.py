"""Independent read-only HDF5 audit of frozen Gate4B DEV/VALIDATION inputs.

The frozen eligible population also requires prediction-valid rows. As prediction
is forbidden in this task, GT-valid blocks are only an upper bound on eligibility.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

import h5py
import numpy as np


LANE = Path(__file__).resolve().parents[1]
PLAN_SHA = "908b5bdbe90e8f9713f85bd886f18a1bcecaa304db575582582c8801e6cb9555"
COHORT_SHA = "def6c5e70773241389101d1789df5e389146ed748b1d5e0b87b336a3e82af96f"
GATE4A_SHA = "ba6a13ea938f8102b9b143caeaccc719c544de7f9435a978a9f967c944d93a8b"
CKPT_SHA = "748b1d1ef0ce1985f6fc07225d97eebfb370243429af803b4997d28ecce2424e"
HEAD_SHA = "b0ef8caf8e390a480fa2a3b448f79ccf14f75c71265ef925ee299a5e9e660386"
DISCOVERY = "d387095792"
DEST = Path("/root/autodl-tmp/gate4b_data")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 << 20), b""):
            h.update(block)
    return h.hexdigest()


def attr(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=DEST)
    parser.add_argument("--checkpoint", type=Path,
                        default=Path("/root/models/emg2pose/regression_vemg2pose.ckpt"))
    parser.add_argument("--head", type=Path,
                        default=Path("/root/work/gate3_work/frozen_head/frozen_db9_trusted8_lda.joblib"))
    args = parser.parse_args()
    data_root = args.data_root.resolve()
    checks = 0

    def check(condition: bool, description: str) -> None:
        nonlocal checks
        checks += 1
        if not condition:
            raise AssertionError(description)

    check(sha(LANE / "GATE4B_PLAN.md") == PLAN_SHA, "Gate4B plan hash")
    check(sha(LANE / "COHORT_MANIFEST.json") == COHORT_SHA, "cohort hash")
    check(sha(LANE.parent / "gate4a_reliability_feasibility/GATE4A_PLAN.md") == GATE4A_SHA,
          "Gate4A plan hash")
    check(sha(args.checkpoint) == CKPT_SHA,
          "official checkpoint hash")
    check(sha(args.head) == HEAD_SHA,
          "frozen DB9 head hash")
    cohort = json.loads((LANE / "COHORT_MANIFEST.json").read_text(encoding="utf-8"))
    mpath = LANE / "DATA_ACQUISITION_MANIFEST.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    selected = cohort["selected"]
    check(len(selected) == 48, "48 reserved identities")
    check(Counter(x["split"] for x in selected) == {
        "DEV": 20, "CALIBRATION_LOCKED": 10, "VALIDATION": 8, "FINAL_TEST_LOCKED": 10
    }, "frozen split counts")
    check(len({x["participant_id"] for x in selected}) == 48, "unique users")
    check(DISCOVERY not in {x["participant_id"] for x in selected}, "discovery absent")
    allowed = {(x["split"], x["participant_id"], x["session_id"]): x
               for x in selected if x["split"] in {"DEV", "VALIDATION"}}
    locked = {x["participant_id"] for x in selected if "LOCKED" in x["split"]}
    check(len(allowed) == 28, "28 exact authorized sessions")
    check(manifest["gate4b_plan_sha256"] == PLAN_SHA and
          manifest["cohort_manifest_sha256"] == COHORT_SHA, "manifest frozen hashes")
    check(manifest["CALIBRATION_LOCKED_ACCESSED"] is False and
          manifest["FINAL_TEST_LOCKED_ACCESSED"] is False and
          manifest["discovery_user_accessed"] is False, "access firewall declarations")
    files = manifest["files"]
    check(len(files) == manifest["expected_files"] ==
          sum(x["record_count"] for x in allowed.values()), "exact file count")
    check(all((f["split"], f["participant_id"], f["session_id"]) in allowed for f in files),
          "all file identities authorized")
    check(all(f["participant_id"] not in locked | {DISCOVERY} for f in files),
          "no locked/discovery user in file manifest")
    complete = [f for f in files if f["acquisition_status"] == "COMPLETE"]
    for f in complete:
        path = Path(f["acquired_path"])
        expected_path = data_root / f["split"] / f["participant_id"] / Path(f["source_member"]).name
        check(path.resolve() == expected_path.resolve() and
              path.stem.startswith(f["session_id"] + "-recording-") and
              path.stem.endswith("_" + f["hand"]), f"completed path authorized: {path.name}")
        check(path.is_file() and path.stat().st_size == f["expected_metadata_size"] ==
              f["actual_byte_size"], f"completed size: {path.name}")
        check(sha(path) == f["sha256"], f"completed SHA256: {path.name}")
    if len(complete) != len(files):
        partial_result = {
            "task": "COMMON-POSE-GATE4B-20260922-DATA-ACQUISITION",
            "status": "PARTIAL", "assertions": checks, "failures": 0,
            "acquisition_complete": False, "files_complete": len(complete),
            "files_expected": len(files), "sessions_assessed": 0,
            "session_qualifications": [],
            "reason": "Full structural and GT-valid session qualification requires all frozen files.",
            "actual_eligible_frame_count_known": False,
            "upstream_inference_run": False, "scientific_outcome_computed": False,
            "calibration_locked_accessed": False, "final_test_locked_accessed": False,
            "discovery_user_accessed": False
        }
        artifacts = LANE / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        (artifacts / "STRUCTURAL_QUALIFICATION.json").write_text(
            json.dumps(partial_result, indent=2) + "\n", encoding="utf-8")
        print(f"VERIFY_GATE4B_DATA: PARTIAL | {checks} checks | 0 failures | "
              f"acquisition incomplete: {len(complete)}/{len(files)} files; "
              "full structural qualification not run", flush=True)
        raise SystemExit(2)
    file_paths = {Path(f["acquired_path"]) for f in files}
    check(len(file_paths) == len(files), "unique file paths")
    check(all(p.resolve().is_relative_to(data_root) for p in file_paths), "paths within acquired root")
    present = {p for p in data_root.rglob("*.hdf5")} if data_root.exists() else set()
    check(present == file_paths, "acquired directory contains exactly authorized HDF5 files")
    check(not list(data_root.rglob("*.partial")), "no active partial files")
    forbidden_names = ("pred", "fisher", "score", "model", "risk", "aurc", "tta", "temp")
    for area in (LANE / "artifacts", LANE / "logs"):
        if area.exists():
            check(not any(any(token in p.name.lower() for token in forbidden_names)
                          for p in area.iterdir() if p.is_file()), "no scientific output artifact")

    by_file = []
    grouped = defaultdict(list)
    for i, f in enumerate(files, 1):
        key = (f["split"], f["participant_id"], f["session_id"])
        path = Path(f["acquired_path"])
        check(f["acquisition_status"] == "COMPLETE", f"acquisition complete: {path.name}")
        check(path.is_file() and path.stat().st_size == f["expected_metadata_size"] ==
              f["actual_byte_size"], f"size: {path.name}")
        check(sha(path) == f["sha256"], f"SHA256: {path.name}")
        check(path.name == Path(f["source_member"]).name and
              path.name.startswith(f["session_id"] + "-recording-") and
              path.stem.endswith("_" + f["hand"]), f"file identity: {path.name}")
        with path.open("rb") as raw, h5py.File(raw, "r") as h:
            check("emg2pose" in h and "timeseries" in h["emg2pose"], f"schema: {path.name}")
            g = h["emg2pose"]
            ts = g["timeseries"]
            check(all(name in (ts.dtype.names or ()) for name in ("emg", "joint_angles", "time")),
                  f"required streams: {path.name}")
            emg = ts["emg"]
            angles = ts["joint_angles"]
            times = ts["time"]
            check(len(emg.shape) == 2 and emg.shape[1] == 16,
                  f"official EMG 16 channels: {path.name}")
            check(len(angles.shape) == 2 and angles.shape[1] == 20,
                  f"official 20 pose angles: {path.name}")
            check(len(times.shape) == 1 and emg.shape[0] == angles.shape[0] == times.shape[0],
                  f"coherent lengths: {path.name}")
            check(all(ds.dtype.kind in "fi" for ds in (emg, angles, times)),
                  f"numeric floating/integer streams: {path.name}")
            n = int(times.shape[0])
            check(n > 1790 + 40, f"enough source rows: {path.name}")
            check(all(attr(g.attrs.get(k, "")) == value for k, value in (
                ("user", f["participant_id"]), ("session", f["session_id"]),
                ("side", f["hand"]))), f"embedded identity: {path.name}")
            e = emg
            a = angles
            t = times
        check(bool(np.isfinite(t).all()), f"finite time: {path.name}")
        check(bool(np.all(np.diff(t) > 0)), f"strictly increasing time: {path.name}")
        aligned = n - 1790
        blocks = aligned // 40
        check(blocks >= 2 and len(t[1790:]) == aligned, f"official offset/blocks: {path.name}")
        emg_finite = np.isfinite(e)
        angle_finite = np.isfinite(a)
        gt_valid = np.isfinite(a[1790:]).all(axis=1) & \
            ~np.all(np.isclose(a[1790:], 0.0), axis=1)
        gt_blocks = gt_valid[:blocks * 40].reshape(blocks, 40).all(axis=1)
        gt_blocks[0] = False
        row = {
            "split": f["split"], "participant_id": f["participant_id"],
            "session_id": f["session_id"], "hand": f["hand"], "file": path.name,
            "raw_rows": n, "emg_channels": 16, "angle_dimensions": 20,
            "emg_finite_fraction": float(emg_finite.mean()),
            "emg_nan_count": int(np.isnan(e).sum()), "emg_inf_count": int(np.isinf(e).sum()),
            "emg_all_zero_rows": int(np.all(e == 0, axis=1).sum()),
            "emg_constant_channels": int(np.sum(np.all(e == e[0], axis=0))),
            "angle_finite_fraction": float(angle_finite.mean()),
            "angle_nan_count": int(np.isnan(a).sum()), "angle_inf_count": int(np.isinf(a).sum()),
            "angle_all_zero_rows": int(np.all(a == 0, axis=1).sum()),
            "structurally_alignable_rows": aligned, "total_50hz_blocks": blocks,
            "gt_valid_50hz_blocks_upper_bound": int(gt_blocks.sum()),
            "actual_eligible_50hz_frames": "PENDING_PRED_VALIDITY",
            "parse_status": "PASS", "timestamp_status": "PASS", "alignment_status": "PASS"
        }
        by_file.append(row)
        grouped[key].append(row)
        f["parse_status"] = "PASS"
        f["structural_integrity_status"] = "PASS_GT_ONLY"
        if i % 20 == 0:
            print(f"VERIFIED {i}/{len(files)} files", flush=True)

    by_session = []
    structural_failures = []
    for key, frozen in allowed.items():
        rows = grouped[key]
        check(len(rows) == frozen["record_count"], f"record count: {key}")
        hands = Counter(r["hand"] for r in rows)
        check(hands["left"] > 0 and hands["right"] > 0, f"both hands: {key}")
        gt_upper = sum(r["gt_valid_50hz_blocks_upper_bound"] for r in rows)
        checks += 1
        qualification = ("READY_FOR_UPSTREAM_ELIGIBILITY_CHECK" if gt_upper >= 10_000
                         else "STRUCTURAL_FAILURE")
        if qualification == "STRUCTURAL_FAILURE":
            structural_failures.append({"split": key[0], "participant_id": key[1],
                                        "session_id": key[2], "gt_valid_50hz_blocks": gt_upper,
                                        "reason": "GT-valid upper bound below 10000"})
        by_session.append({
            "split": key[0], "participant_id": key[1], "session_id": key[2],
            "left_records": hands["left"], "right_records": hands["right"],
            "records": len(rows), "raw_rows": sum(r["raw_rows"] for r in rows),
            "structurally_alignable_rows": sum(r["structurally_alignable_rows"] for r in rows),
            "total_50hz_blocks": sum(r["total_50hz_blocks"] for r in rows),
            "left_gt_valid_50hz_upper_bound": sum(r["gt_valid_50hz_blocks_upper_bound"]
                                                  for r in rows if r["hand"] == "left"),
            "right_gt_valid_50hz_upper_bound": sum(r["gt_valid_50hz_blocks_upper_bound"]
                                                   for r in rows if r["hand"] == "right"),
            "gt_valid_50hz_upper_bound": gt_upper,
            "actual_eligible_50hz_frames": "PENDING_PRED_VALIDITY",
            "parse_status": "PASS", "timestamp_status": "PASS", "alignment_status": "PASS",
            "qualification": qualification
        })
    check(len(by_session) == 28 and Counter(r["split"] for r in by_session) ==
          {"DEV": 20, "VALIDATION": 8}, "all 28 exact sessions represented")
    by_session.sort(key=lambda r: (r["split"], r["participant_id"]))
    artifacts = LANE / "artifacts"
    write_csv(artifacts / "DATA_INTEGRITY_BY_FILE.csv", by_file, list(by_file[0]))
    write_csv(artifacts / "DATA_INTEGRITY_BY_SESSION.csv", by_session, list(by_session[0]))
    result = {
        "task": "COMMON-POSE-GATE4B-20260922-DATA-ACQUISITION",
        "status": "STOPPED" if structural_failures else "PARTIAL",
        "assertions": checks, "failures": len(structural_failures),
        "sessions_ready_for_upstream_eligibility_check": 28 - len(structural_failures),
        "structural_failures": structural_failures,
        "final_eligibility_certified": False,
        "qualification_blocker": "Prediction-valid rows are part of the frozen eligible-frame rule; "
                                 "upstream inference is prohibited in this task.",
        "actual_eligible_frame_count_known": False,
        "gt_valid_block_count_is_upper_bound_only": True,
        "upstream_inference_run": False, "scientific_outcome_computed": False,
        "calibration_locked_accessed": False, "final_test_locked_accessed": False,
        "discovery_user_accessed": False
    }
    (artifacts / "STRUCTURAL_QUALIFICATION.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8")
    tmp = mpath.with_suffix(".json.partial")
    tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, mpath)
    print(f"VERIFY_GATE4B_DATA: {result['status']} | {checks} checks | "
          f"{len(structural_failures)} failures | "
          f"{28-len(structural_failures)} READY_FOR_UPSTREAM_ELIGIBILITY_CHECK; "
          "final eligible counts require prediction-valid rows", flush=True)
    if structural_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
