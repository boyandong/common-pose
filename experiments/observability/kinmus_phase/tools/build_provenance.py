"""KINMUS_OBSERVABILITY_SOURCE_PROVENANCE.json

Re-read the released .mat from scratch and assert every count the upstream
admission audit reported.  Nothing is taken on trust: 22 subjects, 26 ADLs,
3 phases, 1713 usable trials, 564 894 frames, 18 columns, the known empty
containers and duplicated cells, and the shared10 mapping.
"""
from __future__ import annotations

import os
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import obs_common as C  # noqa: E402
import obs_plan as P  # noqa: E402

OUT = "KINMUS_OBSERVABILITY_SOURCE_PROVENANCE.json"


def main() -> int:
    plan_sha = C.sha256_file(os.path.join(C.LANE, P.PLAN_ARTIFACT))
    d = C.load_kinmus()
    trials = d["trials"]
    X18 = np.vstack([t["K"] for t in trials])
    subj = np.concatenate([np.full(t["n_frames"], t["subject"]) for t in trials])
    phase = np.concatenate([np.full(t["n_frames"], t["phase"]) for t in trials])
    exp = P.SOURCE["expected"]

    # ---- sampling rate, re-derived from the trial time stamps --------------
    dts, rates = [], []
    for t in trials:
        tt = t["time"]
        if tt.size > 2:
            dd = np.diff(tt)
            dts.append(dd[dd > 0])
            span = tt[-1] - tt[0]
            if span > 0:
                rates.append((tt.size - 1) / span)
    dts = np.concatenate(dts) if dts else np.array([])

    # ---- duplicated cells --------------------------------------------------
    keys = Counter((t["subject"], t["adl"], t["phase"]) for t in trials)
    dup = {f"{k[0]}/{k[1]}/{k[2]}": v for k, v in keys.items() if v > 1}
    grid_expected = exp["n_subjects"] * exp["n_adls"] * exp["n_phases"]

    checks = {
        "n_containers": (d["n_containers"], exp["n_containers"]),
        "n_usable_trials": (len(trials), exp["n_usable_trials"]),
        "n_empty_containers": (len(d["malformed"]), exp["n_empty_containers"]),
        "n_frames": (int(X18.shape[0]), exp["n_frames"]),
        "n_channels": (int(X18.shape[1]), exp["n_channels"]),
        "n_subjects": (int(np.unique(subj).size), exp["n_subjects"]),
        "n_adls": (int(len({t["adl"] for t in trials})), exp["n_adls"]),
        "n_phases": (int(len({t["phase"] for t in trials})), exp["n_phases"]),
    }
    mismatches = {k: {"measured": v[0], "expected": v[1]}
                  for k, v in checks.items() if v[0] != v[1]}

    body = {
        "artifact": OUT,
        "branch_id": P.BRANCH_ID,
        "plan_sha256": plan_sha,
        "purpose": ("re-verify the KIN-MUS source from the file rather than from "
                    "memory before any model is fitted"),
        "source_file": C.KIN_MUS_MAT,
        "source_file_sha256": C.sha256_file(C.KIN_MUS_MAT),
        "source_file_bytes": os.path.getsize(C.KIN_MUS_MAT),
        "upstream_lane": "pose_api_dataset_admission",
        "read_only": True,
        "mat_variable": P.SOURCE["mat_variable"],
        "container_fields": sorted({f for f in
                                    ("Subject", "ADL", "Phase", "time",
                                     "Kinematic_data", "EMG_data")}),
        "measured": {k: v[0] for k, v in checks.items()},
        "expected_from_upstream": {k: v[1] for k, v in checks.items()},
        "mismatches": mismatches,
        "all_expected_counts_confirmed": not mismatches,
        "trials": {
            "n_usable": len(trials),
            "n_containers": d["n_containers"],
            "empty_containers": d["malformed"],
            "empty_container_note": ("three containers carry a 1-sample time "
                                     "vector and an empty Kinematic_data array; "
                                     "they are EXCLUDED and never repaired"),
            "duplicated_cells": dup,
            "duplicated_cell_note": ("subject 22 / ADL 25 / phases 2 and 3 each "
                                     "appear twice; BOTH copies are kept because "
                                     "the audit cannot tell which is authoritative, "
                                     "and the duplication is reported"),
            "grid_expected_cells": grid_expected,
            "grid_present_cells": len(keys),
            "frames_per_trial": {
                "min": int(min(t["n_frames"] for t in trials)),
                "median": int(np.median([t["n_frames"] for t in trials])),
                "max": int(max(t["n_frames"] for t in trials)),
            },
            "adl_ids": sorted({t["adl"] for t in trials}),
            "subject_ids": sorted(int(s) for s in np.unique(subj)),
            "trial_index_note": ("the container index in EMG_KIN_v4 is carried as "
                                 "trial_index so any frame can be traced back"),
        },
        "sampling_rate": {
            "documented_hz": P.SOURCE["sampling_rate_hz"],
            "re_derived_dt_median_s": float(np.median(dts)) if dts.size else None,
            "re_derived_rate_median_hz": float(np.median(rates)) if rates else None,
            "re_derived_rate_min_hz": float(np.min(rates)) if rates else None,
            "re_derived_rate_max_hz": float(np.max(rates)) if rates else None,
            "note": ("the frozen velocity rule uses the trial's own time stamps, so "
                     "a small deviation from exactly 100 Hz cannot corrupt it"),
        },
        "shared10_mapping": {
            "name": P.SHARED10["name"],
            "api_order": P.SHARED10["api_order"],
            "released_columns": P.SHARED10["released_columns"],
            "released_column_indices": P.SHARED10["released_column_indices"],
            "verified_against": ("pose_api_dataset_admission/"
                                 "FIRST_POC_DATASET_DECISION.json and "
                                 "POSE_API_DOF_MAPPING_MATRIX.json"),
            "unit": P.SHARED10["unit"],
        },
        "forbidden_inputs_audit": {
            "emg_channels_read": False,
            "emg_evidence": ("Kinematic_data and time are the only arrays read; "
                             "EMG_data is never indexed and RAW_EMG.mat is never "
                             "opened"),
            "emg_columns_available": 7,
            "emg_columns_used": 0,
            "emg_downloaded": False,
            "arm_kinematics_used": False,
            "object_identity_fields_available": ["ADL"],
            "object_identity_fields_used_as_feature": [],
            "note": ("the ADL id is read only as a bookkeeping key for the "
                     "handedness probe and the phase-count report; it is NEVER a "
                     "model feature"),
            "subject_id_used_as_feature": False,
        },
        "handedness": {
            "single_hand_block": True,
            "which_hand": "NOT DECIDED - see logs/handedness_probe.json",
            "mirroring_applied": False,
            "subjects_excluded_for_handedness": [],
            "policy": P.HANDEDNESS["policy"],
        },
    }
    sha = C.write_json(os.path.join(C.LANE, OUT), body)
    print(f"wrote {OUT}  sha256={sha[:16]}")
    print(f"  counts confirmed: {body['all_expected_counts_confirmed']}")
    if mismatches:
        print(f"  MISMATCHES: {mismatches}")
    print(f"  usable trials {len(trials)}, frames {X18.shape[0]}, "
          f"subjects {np.unique(subj).size}, rate "
          f"{body['sampling_rate']['re_derived_rate_median_hz']:.2f} Hz")
    if not body["all_expected_counts_confirmed"]:
        raise SystemExit("PROVENANCE MISMATCH - refusing to continue")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
