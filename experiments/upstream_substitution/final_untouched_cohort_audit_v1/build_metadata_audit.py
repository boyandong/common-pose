#!/usr/bin/env python3
"""Build metadata-only prospective cohort audit; never opens candidate HDF5."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
LANE = Path(__file__).resolve().parent
BASE = ROOT / "experiments/upstream_substitution"
METADATA = Path(r"C:\Users\董伯言\Desktop\fingers\emg2pose_handstate\data\official\emg2pose_dataset_mini\metadata.csv")
B = BASE / "gate4b_multiuser_reliability"
C = BASE / "gate4c_upstream_substitution_reliability_v1"
D = BASE / "gate4d_task_aware_gate_benchmark_v1"
E = BASE / "gate4e_customer_flip_gate_v1"
F = BASE / "gate4f_class_balanced_flip_gate_v1"
G3 = BASE / "gate3_formal_substitution/artifacts/GATE3_DATA_MANIFEST.json"
DISCOVERY = "d387095792"
N_VALUES = (8, 10, 12, 15, 20, 25, 30)


def read(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def digest(p: Path):
    h = hashlib.sha256()
    with p.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def save(name: str, value):
    p = LANE / name
    if p.exists():
        raise RuntimeError(f"refuse overwrite: {p}")
    p.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def wilson(successes: int, n: int):
    z = 1.959963984540054
    p = successes / n
    a = 1 + z * z / n
    center = (p + z * z / (2 * n)) / a
    radius = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / a
    return [center - radius, center + radius]


def dev_deltas(p: Path, method: str, field: str):
    x = read(p)
    users = sorted({r["user"] for r in x["rows"] if r["method"] == method})
    out = {}
    for user in users:
        rows = {r["coverage"]: r for r in x["rows"] if r["method"] == method and r["user"] == user}
        out[user] = float(rows[1.0][field] - rows[0.3][field])
    return out


def main():
    b = read(B / "COHORT_MANIFEST.json")
    acquired = read(B / "artifacts/DATA_MANIFEST.json")
    b_acquisition = read(B / "DATA_ACQUISITION_MANIFEST.json")
    c = read(C / "COHORT_MANIFEST.json")
    d = read(D / "COHORT_MANIFEST.json")
    e = read(E / "COHORT_MANIFEST.json")
    f = read(F / "COHORT_MANIFEST.json")
    g3 = read(G3)
    provenance = read(B / "artifacts/UPSTREAM_CHECKPOINT_PROVENANCE.json")
    assert digest(METADATA) == b["source"]["metadata_csv_sha256"]
    assert provenance["classification"] == "UPSTREAM_TRAIN_MEMBERSHIP_UNRESOLVED"
    assert b_acquisition["CALIBRATION_LOCKED_ACCESSED"] is False
    assert b_acquisition["FINAL_TEST_LOCKED_ACCESSED"] is False
    assert all(x["protected_splits_opened"] is False for x in (c, d, e, f))

    official = defaultdict(list)
    with METADATA.open("r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            official[row["user"]].append(row)
    assert len(official) == 193 and sum(map(len, official.values())) == 25253
    candidate = {row["participant_id"]: row for row in b["candidate_order"]}
    assert set(candidate) == set(official) - {DISCOVERY}
    selected = {row["participant_id"]: row for row in b["selected"]}
    exposed_b = {u for u, row in selected.items() if row["split"] in ("DEV", "VALIDATION")}
    assert len(exposed_b) == 28
    touched = exposed_b | {DISCOVERY}
    assert len(touched) == 29
    acquired_by_user = defaultdict(list)
    for row in acquired["files"]:
        acquired_by_user[row["participant_id"]].append(row)
    assert set(acquired_by_user) == exposed_b
    c_users = {row["participant_id"] for row in c["selected_sessions"]}
    d_users = set(d["users"])
    assert len(c_users) == 27 and c_users <= exposed_b
    assert d_users == set(e["users"]) == set(f["users"]) and len(d_users) == 19
    assert d_users <= c_users
    assert g3["participant"] == [DISCOVERY]

    touched_rows = []
    for user in sorted(touched):
        records = official[user]
        if user == DISCOVERY:
            sessions = g3["session"]
            files = int(g3["n_files"])
            events = [{"branch": "bridge/early mini-emg2pose + Gate3", "role": "DIAGNOSTIC/MANUAL_INSPECTION",
                       "session_ids": sessions, "file_count": files}]
            reason = "mini discovery user used in CommonPose bridge/upstream diagnostic"
        else:
            own = acquired_by_user[user]
            sessions = sorted({row["session_id"] for row in own})
            files = len(own)
            b_role = "DEV" if selected[user]["split"] == "DEV" else "VALIDATION"
            events = [{"branch": "Gate4B acquisition/structural qualification", "role": b_role,
                       "session_ids": sessions, "file_count": files}]
            if user in c_users:
                events.append({"branch": "Gate4C upstream substitution", "role": b_role})
            if user in d_users:
                events.extend({"branch": branch, "role": "DEV/TRAIN/CALIBRATION/METHOD_SELECTION"}
                              for branch in ("Gate4D", "Gate4E", "Gate4F"))
            reason = ("acquired for structural scientific development; Gate4C excluded after source defects"
                      if user not in c_users else "used in scientific development/validation")
        touched_rows.append({"user_id": user, "official_session_count": len({r["session"] for r in records}),
                             "official_recording_count": len(records), "touched_session_ids": sessions,
                             "touched_file_count": files, "exposure_events": events,
                             "ineligible_reason": reason})
    save("TOUCHED_USER_REGISTRY.json", {"schema": "final-cohort-touched-v1", "user_count": len(touched),
         "metadata_sha256": digest(METADATA), "users": touched_rows,
         "classification_note": "metadata-only reservation is not scientific exposure; acquired structural failure is diagnostic exposure"})

    eligible = sorted(set(official) - touched)
    assert len(eligible) == 164 and set(eligible) <= set(candidate)
    eligible_rows = []
    for user in eligible:
        records = official[user]
        preflight = candidate[user]
        official_sessions = sorted({r["session"] for r in records})
        official_splits = sorted({r["split"] for r in records})
        selected_split = selected[user]["split"] if user in selected else None
        eligible_rows.append({"user_id": user, "official_session_count": len(official_sessions),
                              "official_session_ids": official_sessions,
                              "official_recording_count": len(records),
                              "official_split_labels": official_splits,
                              "official_held_out_user": all(r["held_out_user"] == "True" for r in records),
                              "preflight_eligible_session_count": preflight["eligible_session_count"],
                              "preflight_session_id": preflight["session_id"],
                              "preflight_session_recording_count": preflight["record_count"],
                              "preflight_session_archive_bytes": preflight["archive_bytes"],
                              "all_session_total_bytes": None,
                              "existing_Gate4B_reservation": selected_split,
                              "upstream_exposure_group": "C_UNKNOWN", "known_local_candidate_HDF5": False,
                              "download_required_if_selected": True,
                              "paired_emg_gt_metadata_status": "official archive has named positive-size HDF5 recordings for both hands; stream presence unverified",
                              "structurally_confirmed_paired_data": False})
    save("ELIGIBLE_USER_REGISTRY.json", {"schema": "final-cohort-eligible-metadata-v1",
         "identity_untouched_candidate_count": len(eligible), "official_total_user_count": len(official),
         "official_total_session_count": len({(u, r["session"]) for u, rows in official.items() for r in rows}),
         "official_total_recording_count": sum(map(len, official.values())),
         "metadata_sha256": digest(METADATA), "tar_index_sha256": b["source"]["tar_index_jsonl_sha256"],
         "all_session_total_bytes_available": False,
         "known_local_scope": "official mini contains discovery user; Gate4B acquisition contains 28 already-touched users only",
         "users": eligible_rows})

    locked = []
    for split in ("CALIBRATION_LOCKED", "FINAL_TEST_LOCKED"):
        values = [row for row in b["selected"] if row["split"] == split]
        ids = {row["participant_id"] for row in values}
        assert len(values) == 10 and not ids & touched
        locked.append({"cohort": split, "verdict": "ELIGIBLE_UNTOUCHED", "user_count": len(ids),
                       "reserved_session_count": len(values),
                       "reserved_recording_count": sum(row["record_count"] for row in values),
                       "reserved_archive_bytes": sum(row["archive_bytes"] for row in values),
                       "users": sorted(ids), "overlap_with_touched_users": 0,
                       "scientific_data_accessed_according_to_provenance": False,
                       "upstream_training_membership": "UNKNOWN",
                       "paired_stream_structure": "NOT_VERIFIED_FROM_METADATA"})
    save("LOCKED_COHORT_STATUS.json", {"schema": "final-cohort-locked-status-v1", "cohorts": locked,
         "caveat": "identity reservation is intact in available provenance; actual upstream membership and paired streams remain unverified"})

    split_profiles = Counter("/".join(row["official_split_labels"]) for row in eligible_rows)
    save("UPSTREAM_EXPOSURE_AUDIT.json", {"schema": "final-cohort-upstream-exposure-v1",
         "checkpoint_sha256": provenance["checkpoint_sha256"],
         "checkpoint_specific_training_membership": "UNRESOLVED",
         "known_group_A_unseen_to_both": 0, "known_group_B_seen_by_upstream": 0,
         "group_C_unknown_upstream_membership": len(eligible),
         "official_split_profiles_descriptive_only": dict(sorted(split_profiles.items())),
         "official_split_is_checkpoint_training_proof": False,
         "evidence": provenance["evidence"],
         "strong_unseen_upstream_claim_ready": False})

    effects = {}
    for name, path, method, field in (
        ("Gate4E_Requirement_U", E / "artifacts/FLIP_RISK_COVERAGE.json", "hist_gbdt", "flip_risk"),
        ("Gate4F_Requirement_B", F / "artifacts/BALANCED_RISK_COVERAGE.json", "logistic", "balanced_flip_risk"),
    ):
        deltas = dev_deltas(path, method, field)
        assert len(deltas) == 19 and all(v > 0 for v in deltas.values())
        effects[name] = {"method": method, "source_sha256": digest(path),
                         "per_user_improvement_100_to_30": deltas,
                         "dev_median": float(np.median(list(deltas.values()))),
                         "dev_min": min(deltas.values()), "dev_max": max(deltas.values())}
    rows = []
    for n in N_VALUES:
        item = {"n_users": n, "wilson95_user_improved_proportion":
                {str(k): wilson(n-k, n) for k in range(0, min(3, n)+1)},
                "failure_users_sensitivity": {str(k): (n-k)/n for k in range(0, min(3, n)+1)},
                "empirical_dev_bootstrap_median_interval_95": {}}
        for offset, (name, value) in enumerate(effects.items()):
            rng = np.random.default_rng(20260924 + offset)
            draw = rng.choice(np.array(list(value["per_user_improvement_100_to_30"].values())),
                              size=(20000, n), replace=True)
            medians = np.median(draw, axis=1)
            item["empirical_dev_bootstrap_median_interval_95"][name] = [float(x) for x in np.quantile(medians, [.025, .975])]
        rows.append(item)
    save("SAMPLE_SIZE_PLANNING.json", {"schema": "final-cohort-prospective-sample-size-v1",
         "unit": "user", "endpoint": "within-user risk reduction from fixed 100% to 30% coverage",
         "not_formal_guaranteed_power": True,
         "bootstrap_interpretation": "20,000 resampled N-user medians from empirical 19-user DEV effect distribution, deterministic seed 20260924; ignores DEV-to-future distribution shift",
         "wilson_interpretation": "two-sided 95% Wilson intervals for proportion improved given 0, 1, 2 or 3 failure users",
         "dev_effects": effects, "planning_rows": rows,
         "recommendation": {"minimum_defensible_n": 15, "preferred_n": 20, "maximum_practical_n": 30}})

    bytes_per_user = np.array([candidate[u]["archive_bytes"] for u in eligible], dtype=np.int64)
    files_per_user = np.array([candidate[u]["record_count"] for u in eligible], dtype=np.int64)
    med_bytes = float(np.median(bytes_per_user)); med_files = float(np.median(files_per_user))
    storage = []
    for n in (15,20,30):
        raw = round(n * med_bytes)
        storage.append({"n_users": n, "approx_recordings_one_session_per_user": round(n * med_files),
                        "approx_download_bytes_one_session_per_user": raw,
                        "approx_raw_storage_bytes": raw,
                        "operational_storage_with_25pct_headroom_bytes": round(raw * 1.25),
                        "additional_identities_beyond_existing_FINAL_TEST_10": max(0,n-10),
                        "downloads_if_all_selected_user_HDF5_absent": n})
    save("DOWNLOAD_STORAGE_PLANNING.json", {"schema": "final-cohort-download-storage-v1",
         "basis": "frozen Gate4B candidate-order selected preflight session only; not a final cohort selection",
         "eligible_identity_count": len(eligible),
         "per_candidate_session_archive_bytes_median": med_bytes,
         "per_candidate_session_archive_bytes_q25_q75": [float(x) for x in np.quantile(bytes_per_user, [.25,.75])],
         "per_candidate_session_recordings_median": med_files,
         "all_official_session_sizes_available": False,
         "FINAL_TEST_LOCKED_10_exact_reserved_bytes": next(x["reserved_archive_bytes"] for x in locked if x["cohort"]=="FINAL_TEST_LOCKED"),
         "headroom_is_operational_assumption_not_measured_need": True,
         "plans": storage})
    print("AUDIT_METADATA_BUILD_COMPLETE", len(official), len(touched), len(eligible))


if __name__ == "__main__":
    main()
