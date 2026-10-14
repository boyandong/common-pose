"""Freeze Gate4B identity reservations from structural metadata only.

This never opens HDF5 payloads, predictions, GT values, or scientific outcomes.
The resulting reservation is fail-closed if full validity later falls short.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path, PurePosixPath


DISCOVERY = "d387095792"
USER_PREFIX = "COMMON_POSE_GATE4B_USER_V1|"
SESSION_PREFIX = "COMMON_POSE_GATE4B_SESSION_V1|"
SPLITS = (("DEV", 20), ("CALIBRATION_LOCKED", 10), ("VALIDATION", 8), ("FINAL_TEST_LOCKED", 10))
TAR_ETAG = '"62df27ac9a04800702061bac0ac1af32-6897"'
TAR_LENGTH = 462824048640


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def derive(metadata: Path, tar_index: Path) -> dict:
    members = {}
    with tar_index.open("r", encoding="utf-8") as f:
        for line in f:
            member = json.loads(line)
            name = PurePosixPath(member["name"]).name
            if not name.endswith(".hdf5"):
                continue
            stem = name.removesuffix(".hdf5")
            if stem in members:
                raise ValueError(f"duplicate archive member: {stem}")
            members[stem] = member

    sessions = defaultdict(list)
    filenames = set()
    with metadata.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"user", "session", "filename", "side", "start", "end"}
        if not required.issubset(reader.fieldnames or ()):
            raise ValueError("metadata missing required structural columns")
        for row in reader:
            user, session, filename = (row[k].strip() for k in ("user", "session", "filename"))
            if not user or not session or not filename or filename in filenames:
                raise ValueError("blank identity or duplicate filename")
            filenames.add(filename)
            if row["side"] not in {"left", "right"}:
                raise ValueError(f"invalid hand side: {filename}")
            start, end = float(row["start"]), float(row["end"])
            if not math.isfinite(start) or not math.isfinite(end) or end <= start:
                raise ValueError(f"invalid recording interval: {filename}")
            member = members.get(filename)
            if member is None or member.get("typeflag") not in {"0", "\0"} or int(member["size"]) <= 0:
                raise ValueError(f"missing/empty tar member: {filename}")
            sessions[(user, session)].append((row["side"], end - start, int(member["size"])))

    if len(filenames) != len(members):
        raise ValueError("metadata and tar index have different HDF5 member sets")

    candidates = defaultdict(list)
    for (user, session), rows in sessions.items():
        sides = {side for side, _, _ in rows}
        nominal = sum(max(0, math.floor((duration * 2000 - 1790) / 40) - 1) for _, duration, _ in rows)
        if sides != {"left", "right"} or nominal < 10_000:
            continue
        candidates[user].append({
            "session_id": session,
            "session_hash": hash_text(f"{SESSION_PREFIX}{user}|{session}"),
            "record_count": len(rows),
            "hands": ["left", "right"],
            "nominal_50hz_capacity_proxy": nominal,
            "archive_bytes": sum(size for _, _, size in rows),
        })

    candidates.pop(DISCOVERY, None)
    if len(candidates) < 48:
        raise ValueError(f"only {len(candidates)} metadata-preflight participants; need 48")
    ranked = []
    for user, session_list in candidates.items():
        session = min(session_list, key=lambda s: (s["session_hash"], s["session_id"]))
        ranked.append({"participant_id": user, "user_hash": hash_text(USER_PREFIX + user),
                       "eligible_session_count": len(session_list), **session})
    ranked.sort(key=lambda x: (x["user_hash"], x["participant_id"]))
    selected = []
    split_names = [name for name, count in SPLITS for _ in range(count)]
    for rank, (candidate, split) in enumerate(zip(ranked[:48], split_names), 1):
        selected.append({"rank": rank, "split": split, **candidate})

    return {
        "schema_version": 1,
        "task": "COMMON-POSE-GATE4B-20260922-COHORT-FREEZE",
        "cohort_status": "PROSPECTIVE_METADATA_PREFLIGHT_FROZEN_FULL_VALIDITY_PENDING",
        "discovery_participant_excluded": DISCOVERY,
        "source": {
            "metadata_csv_sha256": sha(metadata),
            "tar_index_jsonl_sha256": sha(tar_index),
            "tar_url": "https://fb-ctrl-oss.s3.amazonaws.com/emg2pose/emg2pose_dataset.tar",
            "tar_etag": TAR_ETAG,
            "tar_content_length": TAR_LENGTH,
            "metadata_file_rows": len(filenames),
            "archive_hdf5_members": len(members),
        },
        "preflight_criteria": [
            "nonempty participant and session IDs",
            "finite positive start/end interval for every metadata recording",
            "every named recording occurs once as a positive-size official tar HDF5 member",
            "both left and right recording metadata are present",
            "nominal 50-Hz capacity proxy >= 10000 after 1790-row context and first-block exclusion per record",
        ],
        "unverified_before_inference": [
            "per-file HDF5 parseability and EMG/joint-angle stream presence",
            "exact per-record timestamp alignment",
            "GT-valid and prediction-valid complete 40-row block counts",
            "actual >=10000 eligible 50-Hz frames per frozen session",
        ],
        "failure_policy": "stop without cohort replacement, session replacement, or reordering",
        "preflight_participant_count": len(ranked),
        "preflight_session_count": sum(len(v) for v in candidates.values()),
        "candidate_order": ranked,
        "selected": selected,
        "split_counts": dict(SPLITS),
        "scientific_outcomes_inspected": False,
        "locked_scientific_data_accessed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--tar-index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = derive(args.metadata, args.tar_index)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print("metadata rows:", manifest["source"]["metadata_file_rows"])
    print("tar HDF5 members:", manifest["source"]["archive_hdf5_members"])
    print("preflight participants:", manifest["preflight_participant_count"])
    print("preflight sessions:", manifest["preflight_session_count"])
    print("frozen reservations:", len(manifest["selected"]))
    print("split counts:", manifest["split_counts"])
    print("actual eligible-frame count: PENDING; stop without replacement if short")
    print("scientific outcomes inspected: NO")


if __name__ == "__main__":
    main()
