"""ARTIFACT_MANIFEST.json - SHA-256 of every artifact in this lane.

Records the freeze-order hash chain so the plan -> provenance -> features ->
results -> decision ordering is verifiable from the manifest alone.
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import obs_common as C  # noqa: E402
import obs_plan as P  # noqa: E402

OUT = "ARTIFACT_MANIFEST.json"
EXCLUDE_DIRS = {"__pycache__"}
#: results/ holds large binary caches; they are hashed but listed separately.
CACHE_DIR = "results"


def main() -> int:
    plan_sha = C.sha256_file(os.path.join(C.LANE, P.PLAN_ARTIFACT))
    files, caches = [], []
    for root, dirs, names in os.walk(C.LANE):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for n in sorted(names):
            if n == OUT:
                continue
            p = os.path.join(root, n)
            rel = os.path.relpath(p, C.LANE).replace("\\", "/")
            rec = {"path": rel, "bytes": os.path.getsize(p),
                   "sha256": C.sha256_file(p),
                   "mtime_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                              time.gmtime(os.path.getmtime(p)))}
            if rel.startswith(CACHE_DIR + "/"):
                caches.append(rec)
            else:
                files.append(rec)
    files.sort(key=lambda r: r["path"])
    caches.sort(key=lambda r: r["path"])
    by = {r["path"]: r["sha256"] for r in files + caches}

    chain = {
        "1_frozen_plan": {"path": P.PLAN_ARTIFACT,
                          "sha256": by.get(P.PLAN_ARTIFACT)},
        "2_source_provenance": {
            "path": "KINMUS_OBSERVABILITY_SOURCE_PROVENANCE.json",
            "sha256": by.get("KINMUS_OBSERVABILITY_SOURCE_PROVENANCE.json")},
        "3_phase_counts": {"path": "KINMUS_PHASE_COUNTS.json",
                           "sha256": by.get("KINMUS_PHASE_COUNTS.json")},
        "4_pose_geometry": {"path": "KINMUS_PHASE_POSE_GEOMETRY.json",
                            "sha256": by.get("KINMUS_PHASE_POSE_GEOMETRY.json")},
        "5_velocity_geometry": {
            "path": "KINMUS_PHASE_VELOCITY_GEOMETRY.json",
            "sha256": by.get("KINMUS_PHASE_VELOCITY_GEOMETRY.json")},
        "6_single_frame": {"path": "KINMUS_SINGLE_FRAME_RESULTS.json",
                           "sha256": by.get("KINMUS_SINGLE_FRAME_RESULTS.json")},
        "7_velocity": {"path": "KINMUS_VELOCITY_RESULTS.json",
                       "sha256": by.get("KINMUS_VELOCITY_RESULTS.json")},
        "8_trajectory": {"path": "KINMUS_TRAJECTORY_RESULTS.json",
                         "sha256": by.get("KINMUS_TRAJECTORY_RESULTS.json")},
        "9_full18_secondary": {"path": "KINMUS_FULL18_DIAGNOSTIC.json",
                               "sha256": by.get("KINMUS_FULL18_DIAGNOSTIC.json")},
        "10_null_control": {
            "path": "KINMUS_OBSERVABILITY_NULL_CONTROL.json",
            "sha256": by.get("KINMUS_OBSERVABILITY_NULL_CONTROL.json")},
        "11_boundary": {"path": "KINMUS_BOUNDARY_ANALYSIS.json",
                        "sha256": by.get("KINMUS_BOUNDARY_ANALYSIS.json")},
        "12_stability": {"path": "KINMUS_SUBJECT_STABILITY.json",
                         "sha256": by.get("KINMUS_SUBJECT_STABILITY.json")},
        "13_decision": {"path": "KINMUS_TASK_OBSERVABILITY_DECISION.json",
                        "sha256": by.get("KINMUS_TASK_OBSERVABILITY_DECISION.json")},
        "14_report": {"path": "KINMUS_TASK_OBSERVABILITY_REPORT.md",
                      "sha256": by.get("KINMUS_TASK_OBSERVABILITY_REPORT.md")},
    }

    body = {
        "artifact": OUT,
        "branch_id": P.BRANCH_ID,
        "plan_sha256": plan_sha,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_files": len(files),
        "total_bytes": sum(r["bytes"] for r in files),
        "files": files,
        "large_caches": {
            "n_files": len(caches),
            "total_bytes": sum(r["bytes"] for r in caches),
            "files": caches,
            "note": ("features.npz and predictions.npz are rebuildable caches, "
                     "hashed here so a reviewer can confirm the analysis ran on "
                     "the same bytes.  They are NOT results."),
        },
        "freeze_order_hash_chain": chain,
        "notes": [
            "the hash of the RAW BYTES of a JSON artifact is authoritative; no "
            "artifact is re-serialised after being written",
            "COMMIT PENDING: the project root is not a git repository",
            "no file outside kinmus_task_observability/ was written by this branch",
            "the KIN-MUS .mat is READ-ONLY from the pose_api_dataset_admission "
            "lane and is not copied here",
        ],
        "do_not_delete": [
            "KINMUS_TASK_OBSERVABILITY_PLAN.json (the pre-registration)",
            "KINMUS_TASK_OBSERVABILITY_DECISION.json (the decision)",
            "results/features.npz (rebuildable but slow)",
        ],
    }
    sha = C.write_json(os.path.join(C.LANE, OUT), body)
    print(f"wrote {OUT}  files={len(files)} bytes={body['total_bytes']} "
          f"caches={len(caches)} ({body['large_caches']['total_bytes']} bytes)")
    print(f"  sha256={sha}")
    for k, v in chain.items():
        print(f"  {k:<26} {(v['sha256'] or '-')[:16]}  {v['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
