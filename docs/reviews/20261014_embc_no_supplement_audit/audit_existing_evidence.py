"""Read existing evidence; write audit outputs only. No fitting or manuscript edits."""
import csv
import hashlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PAPER = ROOT / "docs/papers/20261014_v4_5_independent_review"
IDENTITY = ROOT / "docs/reviews/20261011_identity_runtime_causality_audit"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def save_json(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    # Keep a content snapshot proving that the audit did not edit the paper.
    tracked = sorted(p for p in PAPER.rglob("*") if p.is_file())
    before = {str(p.relative_to(ROOT)): sha(p) for p in tracked}
    old = read_json(IDENTITY / "IDENTITY_SUMMARY.json")
    metadata_path = ROOT.parent / "emg2pose_handstate/data/priority_pose_subset/raw/emg2pose_metadata.csv"
    assert sha(metadata_path) == old["metadata_sha256"]
    for rel, expected in old["input_hashes"].items():
        assert sha(ROOT / rel) == expected, rel
    metadata = read_csv(metadata_path)
    by_file = {r["filename"].removesuffix(".hdf5"): r for r in metadata}
    assert len(by_file) == len(metadata) == 25253
    train = [r for r in metadata if r["split"] == "train"]
    assert len({r["user"] for r in train}) == 158
    enrollment_path = ROOT / "experiments/upstream_substitution/new_user_confirmation_v1_20261010/ENROLLMENT_MANIFEST.json"
    enrollment = read_json(enrollment_path)
    selected = []
    for r in enrollment["files"]:
        m = by_file[Path(r["source_member"]).name.removesuffix(".hdf5")]
        assert all(m[k] == r[k] for k in ["user", "session", "side"])
        assert m["split"] == r["official_split"]
        selected.append(m)
    assert len(selected) == 2768 and len({r["filename"] for r in selected}) == 2768
    train_user_set = {r["user"] for r in train}
    train_session_set = {r["session"] for r in train}
    assert len(set(enrollment["enrolled_users"]) & train_user_set) == 70
    previous_identity = read_csv(IDENTITY / "USER_IDENTITY_INTERSECTION.csv")
    n80_identity = [r for r in previous_identity if r["cohort"] == "NEW80_ID_ONLY"]
    assert {r["user"] for r in n80_identity} == set(enrollment["enrolled_users"])
    assert all(r["checkpoint_specific_seen_status"] == "UNKNOWN" for r in n80_identity)
    train_windows = defaultdict(list)
    for r in train:
        train_windows[(r["session"], r["side"])].append(r)
    temporal = []
    for r in selected:
        start, end = float(r["start"]), float(r["end"])
        hits = [x for x in train_windows[(r["session"], r["side"])]
                if min(end, float(x["end"])) > max(start, float(x["start"]))]
        temporal.append({
            "user": r["user"], "session": r["session"], "side": r["side"],
            "filename": r["filename"], "public_split": r["split"],
            "start": r["start"], "end": r["end"],
            "public_train_same_session_side_interval_hits": len(hits),
            "nonidentical_train_interval_hits": sum(x["filename"] != r["filename"] for x in hits),
            "actual_checkpoint_exposure": "UNKNOWN",
        })
    with (HERE / "N80_PUBLIC_RECIPE_RECORD_OVERLAP.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(temporal[0])); w.writeheader(); w.writerows(temporal)
    checkpoint = ROOT.parent / "emg2pose_handstate/checkpoints/emg2pose_model_checkpoints/regression_vemg2pose.ckpt"
    checkpoint_hash = sha(checkpoint) if checkpoint.exists() else None
    if checkpoint_hash:
        assert checkpoint_hash == old["checkpoint_sha256"]
    identity_result = {
        "metadata_sha256": sha(metadata_path), "enrollment_sha256": sha(enrollment_path),
        "checkpoint_current_hash_matches_archived_inspection": checkpoint_hash == old["checkpoint_sha256"],
        "checkpoint_reinspected": False,
        "N80_users": 80, "public_train_identity_intersection": 70,
        "evaluation_files": len(selected), "public_split_counts": dict(Counter(r["split"] for r in selected)),
        "evaluation_sessions": len({r["session"] for r in selected}),
        "public_train_session_intersection": len({r["session"] for r in selected} & train_session_set),
        "records_sharing_public_train_session": sum(r["session"] in train_session_set for r in selected),
        "same_session_side_time_overlap_records": sum(r["public_train_same_session_side_interval_hits"] > 0 for r in temporal),
        "nonidentical_time_overlap_records": sum(r["nonidentical_train_interval_hits"] > 0 for r in temporal),
        "actual_checkpoint_training_membership": "UNKNOWN for all 80; public recipe is conditional evidence only",
        "temporal_scope": "Public metadata half-open intervals, same session and hand side; no raw-signal duplicate audit or checkpoint training manifest",
    }

    # Hash-check the existing manuscript's source receipts and implementation copies.
    provenance = read_json(PAPER / "reproducibility/PROVENANCE_MANIFEST.json")
    for r in provenance:
        assert sha(PAPER / r["copy"]) == r["sha256"], r["copy"]
        assert sha(ROOT / r["original"]) == r["sha256"], r["original"]
    source = read_json(PAPER / "evidence/SOURCE_PROVENANCE.json")
    for r in source:
        assert sha(Path(r["path"])) == r["sha256"]
        assert sha(PAPER / "evidence" / (r["cohort"] + "_USER_COVERAGE_SERVICE.csv")) == r["sha256"]

    name_map = {
        ("db9_scoreonly_v3_20261011", "C1_primary"): "DB9 posture",
        ("db9_scoreonly_v3_20261011", "C2_primary"): "DB9 grasp",
        ("ceti_age_scoreonly_v3_20261012", "C1_primary"): "CeTI posture",
        ("ceti_age_scoreonly_v3_20261012", "C2_primary"): "CeTI grasp",
        ("show3d_scoreonly_v3_20261012", "C1_primary"): "SHOW instruction",
        ("kinmus_uji_scoreonly_v3_20261012", "C1_primary"): "KIN phase",
    }
    paired_s3 = read_csv(PAPER / "evidence/S3_DIRECT_PAIRED_SUMMARY.csv")
    s4 = {r["consumer"]: r for r in read_csv(PAPER / "evidence/S4_CLASS_FIDELITY.csv")}
    results = []; positive = {}; row_counts = {}
    for cohort, users in [("N80", 80), ("A20", 20)]:
        rows = read_csv(PAPER / "evidence" / (cohort + "_USER_COVERAGE_SERVICE.csv"))
        row_counts[cohort] = len(rows)
        lookup = {(r["lane"], r["condition"], r["user"], r["goal"], r["method"], r["mode"], r["nominal_retention"]): r for r in rows}
        assert len(lookup) == len(rows)
        gains = []; direct = []
        for (lane, condition), name in name_map.items():
            user_ids = sorted({r["user"] for r in rows if r["lane"] == lane and r["condition"] == condition})
            assert len(user_ids) == users
            for retention in ["0.1", "0.3", "0.5", "0.7"]:
                def method_rows(method):
                    return [lookup[(lane, condition, u, "U", method, "offline_equal_coverage", retention)] for u in user_ids]
                full, boundary, score = method_rows("full"), method_rows("boundary"), method_rows("score_only")
                delta_u = 100 * statistics.median(float(b["U"]) - float(f["U"]) for b, f in zip(boundary, full))
                delta_direct = 100 * statistics.median(float(s["U"]) - float(f["U"]) for s, f in zip(score, full))
                expected = next(r for r in paired_s3 if r["cohort"] == cohort and r["consumer"] == name and r["retention"] == retention)
                assert abs(delta_direct - float(expected["delta_pp"])) < 1e-10
                gains.append(delta_u); direct.append(delta_direct)
                if cohort == "N80" and retention == "0.3":
                    balanced = [100*(float(b["B"])-float(f["B"])) for b, f in zip(boundary, full) if b["B"] and f["B"]]
                    delta_b = statistics.median(balanced)
                    assert abs(delta_u - float(s4[name]["delta_U_pp"])) < 1e-10
                    assert abs(delta_b - float(s4[name]["delta_B_pp"])) < 1e-10
                    assert len(balanced) == int(s4[name]["B_users"])
                    all_rows = [lookup[(lane, condition, u, "U", "all", "deployment", "")] for u in user_ids]
                    results.append({"consumer": name, "delta_U_pp": delta_u, "U_users": users,
                        "delta_B_pp": delta_b, "B_users": len(balanced),
                        "no_gate_B_evaluable": sum(bool(r["B"]) for r in all_rows),
                        "Full30_B_evaluable": sum(bool(r["B"]) for r in full),
                        "Score_only_minus_Full_pp": delta_direct})
        positive[cohort] = {"Full_vs_Boundary": sum(x > 0 for x in gains), "Full_vs_Score_only": sum(x > 0 for x in direct), "cells": len(gains)}
    threshold_rows = read_json(ROOT / "experiments/multi_consumer/cross_threshold_audit_20261012/DEV_SELECTION_AUDIT.json")
    feasible = [r for r in threshold_rows if not r["fallback_used"]]
    balanced_feasible = [r for r in feasible if r["threshold_goal"] == "B"]
    assert len(threshold_rows) == 24 and len(feasible) == 4 and len(balanced_feasible) == 0
    physical = read_json(ROOT / "experiments/multi_consumer/physical_equivalence_audit_20261012/VERIFICATION.json")
    assert physical["no_physical_equivalence_claim"] is True
    tta = read_json(ROOT / "experiments/multi_consumer/v3_full_tta_ablation_20261012/COMBINED_RESULTS.json")
    tta_manifest = read_json(ROOT / "experiments/multi_consumer/v3_full_tta_ablation_20261012/REPORT_MANIFEST.json")
    for rel, expected in tta_manifest.items():
        assert sha(ROOT / "experiments/multi_consumer/v3_full_tta_ablation_20261012" / rel) == expected
    # Existing intervals below refer to fixed-threshold outcomes, not the main offline budgets.
    n80_summary = read_json(ROOT / "experiments/multi_consumer/n80_serialization_repair_20261012/verified_local_results/SUMMARY.json")
    cache = read_json(ROOT / "experiments/multi_consumer/n80_serialization_repair_20261012/CACHE_EXECUTION.json")
    manuscript = (PAPER / "manuscript.tex").read_text(encoding="utf-8")
    dependencies = [{"line": i, "text": line} for i, line in enumerate(manuscript.splitlines(), 1) if "Supplement" in line or "Table~S5" in line]
    after = {str(p.relative_to(ROOT)): sha(p) for p in tracked}
    assert before == after, "Paper files changed during audit"
    save_json("PAPER_UNCHANGED_HASHES.json", before)
    save_json("AUDIT_RESULTS.json", {
        "date": "2026-10-14 Asia/Shanghai", "status": "PASS_EXISTING_EVIDENCE_RECOUNT",
        "identity": identity_result, "provenance_entries_verified": len(provenance),
        "source_evaluation_tables_hash_verified": True,
        "participant_rows": row_counts, "positive_cells": positive,
        "N80_offline30_recount": results,
        "threshold_audit": {"configurations": 24, "feasible": 4, "balanced_targeted": 12, "balanced_feasible": 0, "scope": "Score-only auxiliary grid"},
        "TTA_ablation": {"existing_A20_contrasts": len(tta["primary_TTA_contrasts"]), "scope": "Fixed thresholds; Full minus its final two TTA features; not isolated ablations of every feature"},
        "existing_N80_CI_contrasts": {"count": len(n80_summary["primary_paired_contrasts"]), "scope": "Fixed-threshold outcomes; not substitutes for the main matched offline budget intervals"},
        "existing_cost": {"shared_four_view_files": cache["files"], "shared_wall_seconds": cache["GPU_elapsed_seconds"], "includes": "Read/hash/store/inference; no certified streaming per-input latency"},
        "main_supplement_dependencies": dependencies,
        "paper_files_unchanged": True, "paper_files_hashed": len(before),
        "no_training_no_inference_no_remote_access": True,
    })
    print(json.dumps({"identity": identity_result, "positive_cells": positive, "paper_unchanged": True, "provenance_checked": len(provenance)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
