"""Independent, metadata-only verification of the prospective Gate4B freeze."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def check_sha_file(path: Path) -> None:
    fields = path.read_text(encoding="ascii").strip().split()
    expected = "GATE4B_PLAN.md" if path.name == "GATE4B_PLAN.sha256" else "COHORT_MANIFEST.json"
    assert len(fields) == 2 and fields[1] == expected
    assert fields[0] == digest(path.with_name(fields[1]))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--metadata", type=Path, required=True)
    p.add_argument("--tar-index", type=Path, required=True)
    p.add_argument("--lane", type=Path, required=True)
    a = p.parse_args()
    checks = 0
    for name in ("GATE4B_PLAN.sha256", "COHORT_MANIFEST.sha256"):
        check_sha_file(a.lane / name)
        checks += 2
    m = json.loads((a.lane / "COHORT_MANIFEST.json").read_text(encoding="utf-8"))
    assert m["source"]["metadata_csv_sha256"] == digest(a.metadata)
    assert m["source"]["tar_index_jsonl_sha256"] == digest(a.tar_index)
    checks += 2
    assert m["source"]["tar_etag"] == '"62df27ac9a04800702061bac0ac1af32-6897"'
    assert m["source"]["tar_content_length"] == 462824048640
    checks += 2

    archive = {}
    for line in a.tar_index.open(encoding="utf-8"):
        item = json.loads(line)
        name = PurePosixPath(item["name"]).name
        if name.endswith(".hdf5"):
            stem = name[:-5]
            assert stem not in archive and int(item["size"]) > 0
            archive[stem] = item
    assert len(archive) == m["source"]["archive_hdf5_members"]
    checks += 1

    sessions = defaultdict(list)
    seen_files = set()
    with a.metadata.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            stem = row["filename"]
            assert stem not in seen_files and stem in archive
            seen_files.add(stem)
            assert row["user"] and row["session"] and row["side"] in {"left", "right"}
            dt = float(row["end"]) - float(row["start"])
            assert math.isfinite(dt) and dt > 0
            sessions[(row["user"], row["session"])].append((row["side"], dt, int(archive[stem]["size"])))
    assert len(seen_files) == len(archive) == m["source"]["metadata_file_rows"]
    checks += 1

    by_user = defaultdict(list)
    for (user, session), records in sessions.items():
        capacity = sum(max(0, math.floor((dt * 2000 - 1790) / 40) - 1) for _, dt, _ in records)
        if {side for side, _, _ in records} != {"left", "right"} or capacity < 10_000:
            continue
        by_user[user].append({
            "participant_id": user,
            "session_id": session,
            "session_hash": text_hash(f"COMMON_POSE_GATE4B_SESSION_V1|{user}|{session}"),
            "record_count": len(records),
            "hands": ["left", "right"],
            "nominal_50hz_capacity_proxy": capacity,
            "archive_bytes": sum(size for _, _, size in records),
        })
    by_user.pop("d387095792", None)
    assert len(by_user) >= 48
    assert len(by_user) == m["preflight_participant_count"]
    assert sum(map(len, by_user.values())) == m["preflight_session_count"]
    checks += 3

    ordered = []
    for user, options in by_user.items():
        chosen = min(options, key=lambda x: (x["session_hash"], x["session_id"]))
        ordered.append({**chosen, "user_hash": text_hash(f"COMMON_POSE_GATE4B_USER_V1|{user}"),
                        "eligible_session_count": len(options)})
    ordered.sort(key=lambda x: (x["user_hash"], x["participant_id"]))
    assert ordered == m["candidate_order"]
    checks += 1

    expected_splits = ["DEV"] * 20 + ["CALIBRATION_LOCKED"] * 10 + ["VALIDATION"] * 8 + ["FINAL_TEST_LOCKED"] * 10
    selected = m["selected"]
    assert len(selected) == 48
    assert len({item["participant_id"] for item in selected}) == 48
    assert "d387095792" not in {item["participant_id"] for item in selected}
    assert Counter(item["split"] for item in selected) == Counter(expected_splits)
    checks += 4
    for rank, (actual, expected, split) in enumerate(zip(selected, ordered[:48], expected_splits), 1):
        assert actual == {"rank": rank, "split": split, **expected}
        assert actual["nominal_50hz_capacity_proxy"] >= 10_000
        checks += 2

    assert m["scientific_outcomes_inspected"] is False
    assert m["locked_scientific_data_accessed"] is False
    assert m["failure_policy"] == "stop without cohort replacement, session replacement, or reordering"
    assert m["cohort_status"] == "PROSPECTIVE_METADATA_PREFLIGHT_FROZEN_FULL_VALIDITY_PENDING"
    checks += 4
    print(f"VERIFY_COHORT: PASS | {checks} checks | 0 failures")
    print("Full HDF5, timestamp, GT-valid, and prediction-valid checks remain PENDING.")


if __name__ == "__main__":
    main()
