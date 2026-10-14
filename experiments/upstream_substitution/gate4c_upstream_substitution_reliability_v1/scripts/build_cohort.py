"""Freeze Gate4C from Gate4B's pre-outcome, hash-sealed structural inventory."""
from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from pathlib import Path


LANE = Path(__file__).resolve().parents[1]
OLD = LANE.parent / "gate4b_multiuser_reliability"
SOURCE_SHA = "7123357b984aea9e39c79bae32289279af5c1db8775fda6fc6a85f543b8dd880"
BAD_SESSION = "2022-04-07-1649318400-a9a00-cv-emg-pose-demonstration@2"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    target = LANE / "COHORT_MANIFEST.json"
    seal = LANE / "COHORT_MANIFEST.sha256"
    if target.exists() or seal.exists():
        raise FileExistsError("cohort already frozen")
    source = OLD / "artifacts" / "DATA_MANIFEST.json"
    assert sha(source) == SOURCE_SHA
    data = json.loads(source.read_text(encoding="utf-8"))
    old_cohort = json.loads((OLD / "COHORT_MANIFEST.json").read_text(encoding="utf-8"))
    allowed = {(x["split"], x["participant_id"], x["session_id"]): x
               for x in old_cohort["selected"] if x["split"] in {"DEV", "VALIDATION"}}
    assert len(allowed) == 28 and len(data["files"]) == 964
    assert data["file_failures"] == 4 and data["session_failures"] == 1
    assert {x["session_id"] for x in data["sessions"] if x["issues"]} == {BAD_SESSION}
    accepted_sessions = [x for x in data["sessions"] if not x["issues"]]
    rejected_sessions = [x for x in data["sessions"] if x["issues"]]
    assert len(accepted_sessions) == 27
    accepted_keys = {(x["split"], x["participant_id"], x["session_id"])
                     for x in accepted_sessions}
    assert accepted_keys <= set(allowed)
    assert all(x["gt_valid_50hz_blocks_upper_bound"] >= 10_000
               for x in accepted_sessions)
    accepted = [x for x in data["files"]
                if (x["split"], x["participant_id"], x["session_id"]) in accepted_keys]
    excluded = [x for x in data["files"] if x not in accepted]
    assert len(accepted) == 926 and len(excluded) == 38
    assert not any(x["issues"] for x in accepted)
    assert all(x["actual_size"] == x["expected_size"] and
               x["actual_sha256"] == x["manifest_sha256"] for x in accepted)
    assert all(x["session_id"] == BAD_SESSION for x in excluded)
    assert Counter(x["split"] for x in accepted_sessions) == {"DEV": 19, "VALIDATION": 8}
    assert len({x["participant_id"] for x in accepted_sessions}) == 27
    selected = [{"split": x["split"], "participant_id": x["participant_id"],
                 "session_id": x["session_id"], "record_count": x["record_count"],
                 "gt_valid_50hz_blocks_upper_bound": x["gt_valid_50hz_blocks_upper_bound"]}
                for x in accepted_sessions]
    selected_files = [{"split": x["split"], "participant_id": x["participant_id"],
                       "session_id": x["session_id"], "hand": x["hand"],
                       "source_member": x["source_member"], "path": x["path"],
                       "size": x["actual_size"], "sha256": x["actual_sha256"],
                       "hdf5_rows": x["hdf5_rows"]} for x in accepted]
    result = {"schema": "gate4c-cohort-v1", "status": "FROZEN_PRE_OUTCOME",
              "parent_gate4b_data_manifest_sha256": SOURCE_SHA,
              "parent_gate4b_plan_sha256": data["frozen_plan_sha256"],
              "parent_gate4b_cohort_sha256": data["frozen_cohort_sha256"],
              "rule": "Admit each of the old 28 DEV/VALIDATION sessions iff every required file has no structural issues in the sealed pre-outcome DATA_MANIFEST, both hands and frozen record count are present, and GT-valid 50-Hz upper bound >=10000. No replacement or replenishment.",
              "excluded_session": {"participant_id": "29ddab35d7", "session_id": BAD_SESSION,
                                   "reason": "four source-authentic HDF5 structural failures",
                                   "excluded_files": len(excluded)},
              "users": len(selected), "sessions": len(selected), "files": len(selected_files),
              "split_sessions": {"DEV": 19, "VALIDATION": 8},
              "expected_bytes": sum(x["size"] for x in selected_files),
              "selected_sessions": selected, "selected_files": selected_files,
              "protected_splits_opened": False, "discovery_user_opened": False}
    target.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(result, sort_keys=True, indent=2) + "\n"
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o444)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    seal.write_text(f"{sha(target)}  COHORT_MANIFEST.json\n", encoding="ascii")
    print(f"GATE4C_COHORT_FROZEN users=27 sessions=27 files=926 sha256={sha(target)}")


if __name__ == "__main__":
    main()
