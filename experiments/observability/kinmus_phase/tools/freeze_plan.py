"""Freeze KINMUS_TASK_OBSERVABILITY_PLAN.json and pin what it rests on.

Run order in this branch:

    1. freeze_plan.py               <- you are here (FREEZE BEFORE ANY FIT)
    2. probe_handedness.py          (already run; result recorded in the plan)
    3. inspect_handedness_clusters.py
    4. build_provenance.py          (KINMUS_OBSERVABILITY_SOURCE_PROVENANCE.json)
    5. build_phase_counts.py        (KINMUS_PHASE_COUNTS.json)
    6. build_geometry.py            (NOTE: this fits NO classifier; pure geometry)
    7. build_features.py            (frozen representations, cached)
    8. build_cv.py                  (subject-grouped CV: baselines, nulls, real)
    9. build_stability.py           (KINMUS_SUBJECT_STABILITY.json)
   10. build_boundary.py            (KINMUS_BOUNDARY_ANALYSIS.json)
   11. build_full18.py              (KINMUS_FULL18_DIAGNOSTIC.json)
   12. build_decision.py            (KINMUS_TASK_OBSERVABILITY_DECISION.json)
   13. build_figures.py
   14. build_manifest.py
   15. assemble_log.py
   16. kinmus_task_observability_fact_check.py

The hash of the RAW BYTES of the plan JSON is authoritative.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import obs_common as C  # noqa: E402
import obs_plan as P  # noqa: E402


def main() -> int:
    plan = P.build_plan()

    # ---- pin the upstream artifacts the plan rests on ---------------------
    pins = {}
    for rel in ("pose_api_dataset_admission/KIN_MUS_SOURCE_AUDIT.json",
                "pose_api_dataset_admission/FIRST_POC_DATASET_DECISION.json",
                "pose_api_dataset_admission/POSE_API_DOF_MAPPING_MATRIX.json",
                "pose_api_dataset_admission/DATASET_ADMISSION_PLAN.json",
                "pose_api_dataset_admission/raw/kin_mus/KIN_MUS_UJI.mat",
                "pose_api_dataset_admission/raw/docs/"
                "MOVMUS_UJI_DATASET_GUIDE_v2_1.txt"):
        p = os.path.join(C.ROOT, rel.replace("/", os.sep))
        pins[rel] = {"exists": bool(os.path.exists(p)),
                     "sha256": C.sha256_file(p) if os.path.exists(p) else None,
                     "bytes": os.path.getsize(p) if os.path.exists(p) else None}
    plan["frozen_input_pins"] = pins

    # ---- assert the shared10 mapping against the upstream decision --------
    dec = C.load_json(os.path.join(C.ADMISSION_LANE,
                                   "FIRST_POC_DATASET_DECISION.json"))
    rep = dec["decision"]["the_representation_this_choice_implies"]
    assert rep["api_dofs"] == P.SHARED10["api_order"], \
        "shared10_poc_v1 order drifted from the upstream decision"
    assert rep["n_dof"] == 10

    mp = C.load_json(os.path.join(C.ADMISSION_LANE,
                                  "POSE_API_DOF_MAPPING_MATRIX.json"))
    idxs = []
    for api in P.SHARED10["api_order"]:
        row = next(r for r in mp["rows"]
                   if r["dataset"].startswith("KIN_MUS") and r["api_dof"] == api)
        assert row["confidence"] == "HIGH", f"{api} is not HIGH upstream"
        idxs.append(row["source_index"])
    assert idxs == P.SHARED10["released_column_indices"], \
        f"shared10 column indices drifted: {idxs}"
    cols = [C.UJI18[i] for i in idxs]
    assert cols == P.SHARED10["released_columns"], \
        f"shared10 released columns drifted: {cols}"

    plan["shared10_verified_at_freeze_time"] = {
        "api_order": P.SHARED10["api_order"],
        "released_columns": cols,
        "released_column_indices": idxs,
        "upstream_confidence": "HIGH for all ten",
        "source_artifact": ("pose_api_dataset_admission/"
                            "FIRST_POC_DATASET_DECISION.json + "
                            "POSE_API_DOF_MAPPING_MATRIX.json"),
    }

    # ---- assert the handedness resolution actually ran --------------------
    hp = os.path.join(C.LOGS, "handedness_probe.json")
    if not os.path.exists(hp):
        raise SystemExit("probe_handedness.py must be run before freezing the plan")
    h = C.load_json(hp)
    plan["handedness_resolved_before_freeze"] = {
        "single_hand_block": h["verdict"]["single_hand_block"],
        "handedness_identified": h["verdict"]["handedness_identified"],
        "what_is_decided": h["verdict"]["what_is_decided"],
        "what_is_NOT_decided": h["verdict"]["what_is_NOT_decided"],
        "consequence": h["verdict"]["consequence_for_this_branch"],
        "evidence": "logs/handedness_probe.json + "
                    "logs/handedness_cluster_inspection.json",
    }
    assert h["verdict"]["single_hand_block"] is True, (
        "the handedness probe did not conclude a single-hand block; the primary "
        "subset rule in the plan would then have to be applied and the plan "
        "re-frozen BEFORE any fit")

    out = os.path.join(C.LANE, P.PLAN_ARTIFACT)
    sha = C.write_json(out, plan)
    sidecar = os.path.join(C.LANE, "KINMUS_TASK_OBSERVABILITY_PLAN.sha256")
    with open(sidecar, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"{sha}  {P.PLAN_ARTIFACT}\n")

    print("FROZEN PRE-RESULT PLAN")
    print(f"  path   : {out}")
    print(f"  bytes  : {os.path.getsize(out)}")
    print(f"  sha256 : {sha}")
    print()
    print("  shared10_poc_v1 verified against the upstream decision:")
    for api, col, i in zip(P.SHARED10["api_order"], cols, idxs):
        print(f"    {api:<24s} <- {col:<8s} idx {i}")
    print()
    print("  handedness: single-hand block = "
          f"{h['verdict']['single_hand_block']}; which hand = NOT DECIDED")
    print("  representations: "
          + ", ".join(P.REPRESENTATIONS.keys()))
    print(f"  validation: grouped 5-fold over 22 subjects, train-fold-only "
          f"z-scoring, seed {P.VALIDATION and '20260101'}")
    print("  pinned inputs:")
    for rel, rec in sorted(pins.items()):
        flag = "OK " if rec["exists"] else "MISSING"
        print(f"    {flag} {(rec['sha256'] or '-')[:16]}  {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
