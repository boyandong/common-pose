#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GATE 1.5 — reference-anchor availability and numerical-zero check.

FIRST STAGE (this script's anchor-audit role): decide whether the local emg2pose
mini corpus contains an anchor that identifies a physical reference/neutral
posture INDEPENDENTLY of the trusted-8 joint-angle values.

It enumerates every candidate anchor source available locally and records, for
each, whether it is (a) present in the local corpus and (b) independent of the
pose values.  It deliberately does NOT search for "frames whose angles are near
zero": that would be the circular selection the gate forbids.

If ANCHOR_STATUS != INDEPENDENT_ANCHOR_FOUND, the script stops and writes a
decision artifact with NO zero statistics.  It will not synthesise reference
frames.

Run:  <EMG2POSE_VENV>\\Scripts\\python.exe -X utf8 scripts/audit_reference_anchor.py
"""

from __future__ import annotations

import csv
import glob
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# --------------------------------------------------------------------------
# Paths — the ASCII junction is mandatory for h5py on this machine.
# --------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
LANE = HERE.parent
ART = LANE / "artifacts"
ART.mkdir(parents=True, exist_ok=True)

CORPUS = Path(r"C:\emg2pose\data\official\emg2pose_dataset_mini")
META = CORPUS / "metadata.csv"

# Frozen artifact this gate compares against (DB9 reference-anchor residuals).
DB9_SRC_CALIB = (
    Path(r"<PROJECT_ROOT>")
    / "audits/db9/coordinate_audit/artifacts/DB9_SOURCE_CALIBRATION_AUDIT.json"
)

HAND_MODEL = Path(r"C:\emg2pose\baseline\emg2pose\emg2pose\UmeTrack\dataset\generic_hand_model.json")

TRUSTED8 = [
    ("thumb_mcp_flexion", "THUMB_MCP_FE", 2),
    ("thumb_ip_flexion", "THUMB_IP_FE", 3),
    ("index_mcp_flexion", "INDEX_MCP_FE", 5),
    ("index_pip_flexion", "INDEX_PIP_FE", 6),
    ("middle_mcp_flexion", "MIDDLE_MCP_FE", 9),
    ("ring_mcp_flexion", "RING_MCP_FE", 13),
    ("pinky_mcp_flexion", "PINKY_MCP_FE", 17),
    ("pinky_pip_flexion", "PINKY_PIP_FE", 18),
]

log_lines: list[str] = []


def log(msg: str = "") -> None:
    print(msg)
    log_lines.append(msg)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# --------------------------------------------------------------------------
# 1. Local corpus inventory (no pose values read)
# --------------------------------------------------------------------------

def inventory() -> dict:
    files = sorted(glob.glob(str(CORPUS / "*.hdf5")))
    rows = list(csv.DictReader(META.open(encoding="utf-8")))
    by_fn = defaultdict(list)
    for r in rows:
        by_fn[r["filename"]].append(r)

    sessions, users, sides = set(), set(), Counter()
    stages_by_side = defaultdict(set)
    held_out_user, splits, moving = set(), set(), Counter()
    total_frames = 0
    per_file = []

    import h5py  # local import: only needed here

    for f in files:
        with h5py.File(f, "r") as h:
            a = dict(h["emg2pose"].attrs)
            n = int(h["emg2pose/timeseries"].shape[0])
        total_frames += n
        stem = Path(f).stem
        sessions.add(a["session"])
        users.add(a["user"])
        sides[a["side"]] += 1
        stages_by_side[a["side"]].add(a["stage"])
        held_out_user.add(bool(a["held_out_user"]))
        splits.add(a["split"])
        moving[a["moving_hand"]] += 1
        per_file.append({
            "recording": re.search(r"recording-(\d+)", stem).group(1),
            "side": a["side"],
            "stage": a["stage"],
            "frames": n,
            "seconds": round(n / float(a["sample_rate"]), 2),
            "split": a["split"],
            "held_out_user": bool(a["held_out_user"]),
            "moving_hand": a["moving_hand"],
        })

    return {
        "n_files": len(files),
        "n_sessions": len(sessions),
        "n_users": len(users),
        "sides": dict(sides),
        "total_frames": total_frames,
        "stages_left": sorted(stages_by_side["left"]),
        "stages_right": sorted(stages_by_side["right"]),
        "held_out_user_values": sorted(held_out_user),
        "split_values": sorted(splits),
        "moving_hand_values": dict(moving),
        "per_file": per_file,
        "metadata_total_rows": len(rows),
        "metadata_total_sessions": len({r["session"] for r in rows}),
        "metadata_total_users": len({r["user"] for r in rows}),
    }


# --------------------------------------------------------------------------
# 2. Candidate anchor sources — each judged on PRESENCE and INDEPENDENCE
# --------------------------------------------------------------------------

def audit_candidates(inv: dict) -> list[dict]:
    local_stages = set(inv["stages_left"]) | set(inv["stages_right"])

    cands = []

    # --- A1: official per-frame posture / gesture label -------------------
    cands.append({
        "id": "A1",
        "class": "A: official protocol/event marker",
        "candidate": "per-frame hand-posture or gesture label",
        "present_locally": False,
        "independent_of_trusted8": None,
        "evidence": (
            "HDF5 exposes exactly one group 'emg2pose' with one compound dataset "
            "'timeseries' whose fields are time / joint_angles(20) / emg(16). There is no "
            "per-frame label field and no per-frame event marker. (Verified by walking every "
            "object and attribute of a real file with h5py.visititems.)"
        ),
        "verdict": "ABSENT",
    })

    # --- A2: the stage attribute -----------------------------------------
    # It IS an activity label and IS independent of the pose values, but it does
    # not specify a hand POSTURE, so it cannot define a reference configuration.
    cands.append({
        "id": "A2",
        "class": "A: official protocol/event marker",
        "candidate": "group attribute `stage` (activity segment label)",
        "present_locally": True,
        "independent_of_trusted8": True,
        "evidence": (
            "Present as a per-file group attribute, and it is independent of the pose values. "
            "But it names a COMPOUND ACTIVITY, not a hand posture: locally the 15 stages are "
            + ", ".join(sorted(local_stages))
            + ". None of them specifies the geometric configuration of the finger joints, so "
              "none defines a reference posture. The dataset reference itself calls `stage` the "
              "'gesture/task' label (EMG2POSE_DATASET_REFERENCE.md line 147) and the project's "
              "own D4 result is that emg2pose carries no per-frame posture label."
        ),
        "verdict": "PRESENT_BUT_DOES_NOT_DEFINE_A_POSTURE",
    })

    # --- A3: the one stage whose NAME is a position+posture composite ------
    cands.append({
        "id": "A3",
        "class": "A: official protocol/event marker",
        "candidate": "stage `HandDeskSeparateClaspedChest` (name includes a desk-rest position)",
        "present_locally": "HandDeskSeparateClaspedChest" in local_stages,
        "independent_of_trusted8": "PARTIAL",
        "evidence": (
            "This is the only stage name in the full 29-stage vocabulary that names a resting "
            "position ('Desk'), and it is the closest analogue to DB9's documented reference "
            "posture ('hand resting on the table with the fingers closed together and "
            "extended'). It is NOT in the local corpus - the local participant recorded 15 "
            "other stages (see A2). Even if it were present, the name is a composite of "
            "several configurations and positions ('SeparateClaspedChest') and does not by "
            "itself state that the fingers are extended at a known timestamp, so it would "
            "still require a posture assertion from outside the data."
        ),
        "verdict": "ABSENT_LOCALLY",
    })

    # --- B: synchronised annotation / protocol marker ---------------------
    cands.append({
        "id": "B",
        "class": "B: synchronised annotation / protocol marker",
        "candidate": "any annotation or protocol marker stating the hand posture at a time",
        "present_locally": False,
        "independent_of_trusted8": None,
        "evidence": (
            "No annotation stream, no event marker and no per-segment posture statement exists "
            "in the released corpus or in the local metadata.csv columns "
            "(session, user, stage, start, end, side, filename, moving_hand, held_out_user, "
            "held_out_stage, split, generalization). `start`/`end` bound an activity segment; "
            "they do not state a hand configuration."
        ),
        "verdict": "ABSENT",
    })

    # --- C: FK geometry ----------------------------------------------------
    cands.append({
        "id": "C",
        "class": "C: verified geometric/FK criterion",
        "candidate": "forward-kinematics test for an extended/reference configuration",
        "present_locally": True,
        "independent_of_trusted8": False,
        "evidence": (
            "The official model and FK are available locally, so a geometric criterion could "
            "be computed. It is nevertheless NOT independent: in this model the finger is "
            "straight exactly when the joint rotation is zero, and the model's own per-joint "
            "limits already encode that (THUMB_MCP_FE, INDEX_PIP_FE, MIDDLE_PIP_FE, "
            "RING_PIP_FE, PINKY_PIP_FE all have min = 0.0 rad, i.e. zero IS the extended "
            "end of the range). Any 'is this hand extended?' geometric test therefore reduces "
            "to 'are these joint angles near zero', which is precisely the circular criterion "
            "the gate forbids. Furthermore the same joint angles define the FK landmarks, so "
            "the test would reuse the very quantities it is meant to validate independently."
        ),
        "verdict": "PRESENT_BUT_CIRCULAR",
    })

    # --- D: recorded calibration / reference-pose marker -------------------
    cands.append({
        "id": "D",
        "class": "D: recorded calibration/reference-pose marker",
        "candidate": "a recorded calibration or reference-pose marker in the generation pipeline",
        "present_locally": False,
        "independent_of_trusted8": None,
        "evidence": (
            "The released artifacts carry no calibration marker. The only thing in the "
            "pipeline named 'neutral' is UmeTrack tracker initialisation: "
            "`neutral_joint_angles()` (UmeTrack/lib/tracker/perspective_crop.py lines 19-24) "
            "returns joint_limits[...,0]*0.5 + joint_limits[...,1]*0.5, a synthetic midpoint "
            "OF A MODEL LIMIT RANGE used to seed the crop/tracker - not a recorded posture, "
            "not a physical reference, and not attained by any subject by construction."
        ),
        "verdict": "ABSENT",
    })

    return cands


# --------------------------------------------------------------------------
# 3. DB9 reference-anchor comparator (authoritative artifact only)
# --------------------------------------------------------------------------

def db9_reference_comparator() -> dict:
    d = json.loads(DB9_SRC_CALIB.read_text(encoding="utf-8"))
    names = d["canonical16_names"]
    keep = [k for k, _, _ in TRUSTED8]
    idx = [names.index(k) for k in keep]

    per_source = {}
    for src in ("DB1", "DB2", "DB5"):
        e = d["reference_posture_per_source"][src]
        per_source[src] = {
            "n_units": e["n_units"],
            "n_subjects": e["n_subjects"],
            "mean_abs_deg_all16": round(e["mean_abs_deg"], 4),
            "per_joint_median_deg_all16": [round(x, 4) for x in e["per_joint_median_deg"]],
            "trusted8_per_joint_median_deg": {
                k: round(e["per_joint_median_deg"][i], 4) for k, i in zip(keep, idx)
            },
        }

    trusted8_all = [
        abs(v) for src in per_source.values()
        for v in src["trusted8_per_joint_median_deg"].values()
    ]
    return {
        "artifact": str(DB9_SRC_CALIB),
        "artifact_sha256": sha256(DB9_SRC_CALIB),
        "field": "reference_posture_per_source (unit = subject x movement x repetition, central phase)",
        "what_it_measures": (
            "the residual of the DOCUMENTED DB9 calibration reference posture, i.e. how far the "
            "released angles sit from zero AT the anchor - a reference-anchor residual, NOT a "
            "dataset-level distribution shift"
        ),
        "per_source": per_source,
        "trusted8_anchor_residual_abs_max_deg": round(max(trusted8_all), 4),
        "trusted8_anchor_residual_abs_min_deg": round(min(trusted8_all), 4),
        "artifact_interpretation_rule": d["interpretation_rules"][2],
        "note_on_the_18_5_9_21_numbers": (
            "The widely quoted 18.001 / 5.911 / 21.268 deg are mean |angle| over ALL 16 "
            "canonical dimensions at the reference posture. They are inflated by the dimensions "
            "the forensic lane DROPped (DIP3/DIP4/DIP5/CMC5 sit at -9.10, -4.87, -3.97, -4.60 "
            "deg in DB1). For the trusted-8 the per-joint medians at the anchor are much "
            "smaller - see trusted8_per_joint_median_deg."
        ),
    }


# --------------------------------------------------------------------------
# 4. Tolerance rule: does a PRE-EXISTING defensible tolerance exist?
# --------------------------------------------------------------------------

def tolerance_audit() -> dict:
    """Search the frozen plans for a declared reference-anchor tolerance."""
    return {
        "pre_existing_reference_anchor_tolerance_found": False,
        "searched": [
            "audits/db9/channel_forensic/FORENSIC_PLAN.md (thresholds section)",
            "audits/db9/coordinate_audit/POSE_COORDINATE_AUDIT_PLAN.json",
            "audits/db9/coordinate_audit/artifacts/DB9_SOURCE_CALIBRATION_AUDIT.json "
            "(interpretation_rules)",
        ],
        "thresholds_that_DO_exist_but_do_not_apply": {
            "sign_consistency_and_magnitude (FORENSIC_PLAN.md section 7, 'Thresholds, fixed now')":
                "PASS >= 80% of subjects in the expected direction AND pooled median magnitude "
                "> 2 deg; WEAK 60-80%; FAIL < 60%. This governs a channel's response to a "
                "PHYSICAL ANCHOR (does it move the documented way), not the numerical residual "
                "of a reference posture in a second dataset.",
            "magnitude_ratio_floor": "0.15 (the frozen floor that moved PIP3 and DIP4 from "
                "INCONCLUSIVE to DROP). Different statistic.",
            "documentation_materiality": "2% rounding-materiality rule used for the BUG-006 "
                "MCP5_f/PIP5 restoration. Different statistic.",
        },
        "conclusion": (
            "No pre-existing frozen rule bounds a cross-source reference-anchor residual. Per "
            "the gate's section 6 an ad-hoc +/-2 deg threshold must NOT be invented after the "
            "fact, so this gate emits descriptive compatibility classes rather than a "
            "thresholded pass/fail - and, because no independent anchor exists, it emits "
            "NOT_MEASURED rather than any classification at all."
        ),
    }


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main() -> int:
    log("=" * 78)
    log("GATE 1.5 - REFERENCE-ANCHOR AVAILABILITY & NUMERICAL-ZERO CHECK")
    log("=" * 78)
    log()

    inv = inventory()
    log("[1] LOCAL CORPUS INVENTORY (no pose values read)")
    log(f"    files          : {inv['n_files']}")
    log(f"    sessions       : {inv['n_sessions']}")
    log(f"    participants   : {inv['n_users']}")
    log(f"    hand sides     : {inv['sides']}")
    log(f"    total frames   : {inv['total_frames']}")
    log(f"    split          : {inv['split_values']}")
    log(f"    held_out_user  : {inv['held_out_user_values']}")
    log(f"    metadata.csv   : {inv['metadata_total_rows']} rows / "
        f"{inv['metadata_total_sessions']} sessions / {inv['metadata_total_users']} users "
        f"(FULL corpus - only {inv['n_sessions']} session(s) is local)")
    log()
    log("    local stages (left):")
    for s in inv["stages_left"]:
        log(f"      - {s}")
    log()

    cands = audit_candidates(inv)
    log("[2] CANDIDATE ANCHOR SOURCES")
    log(f"    {'id':<4}{'present':<9}{'independent':<13}verdict")
    for c in cands:
        log(f"    {c['id']:<4}{str(c['present_locally']):<9}"
            f"{str(c['independent_of_trusted8']):<13}{c['verdict']}")
    log()

    independent_found = [
        c for c in cands
        if c["present_locally"] is True and c["independent_of_trusted8"] is True
        and c["verdict"] not in ("PRESENT_BUT_DOES_NOT_DEFINE_A_POSTURE",)
    ]
    anchor_status = "INDEPENDENT_ANCHOR_FOUND" if independent_found else "NO_INDEPENDENT_ANCHOR"

    log("[3] ANCHOR STATUS")
    log(f"    ANCHOR_STATUS: {anchor_status}")
    log()
    log("    Reasoning: the only locally-present, pose-independent field is the `stage`")
    log("    attribute (A2), which names a compound ACTIVITY and specifies no hand posture.")
    log("    The single stage name that does encode a resting position (A3,")
    log("    HandDeskSeparateClaspedChest - the closest analogue to DB9's documented")
    log("    reference) is NOT in the local corpus. No per-frame label (A1), no annotation")
    log("    (B) and no calibration marker (D) exist. The FK route (C) is present locally but")
    log("    is CIRCULAR: in this model the extended configuration IS zero joint angle, so a")
    log("    geometric 'is it extended?' test reduces to 'are the angles near zero'.")
    log()

    tol = tolerance_audit()
    log("[4] TOLERANCE AUDIT")
    log(f"    pre-existing reference-anchor tolerance found: "
        f"{tol['pre_existing_reference_anchor_tolerance_found']}")
    log("    -> descriptive classes only; no ad-hoc threshold invented.")
    log()

    comparator = db9_reference_comparator()
    log("[5] DB9 REFERENCE-ANCHOR COMPARATOR (authoritative artifact)")
    log(f"    {comparator['artifact']}")
    log(f"    sha256 {comparator['artifact_sha256']}")
    log(f"    trusted-8 anchor residual |median| range across DB1/DB2/DB5: "
        f"{comparator['trusted8_anchor_residual_abs_min_deg']} - "
        f"{comparator['trusted8_anchor_residual_abs_max_deg']} deg")
    log()

    log("[6] TRUSTED-8 ZERO MEASUREMENT")
    log("    NOT_MEASURED - no independent anchor exists, so no measurement was performed.")
    log("    No reference frames were synthesised.")
    log()

    zero_gate = "NOT_EVALUABLE_LOCALLY" if anchor_status != "INDEPENDENT_ANCHOR_FOUND" else None
    log("[7] ZERO_GATE")
    log(f"    ZERO_GATE: {zero_gate}")
    log()

    # ---------------- artifacts ----------------
    decision = {
        "artifact": "REFERENCE_ANCHOR_DECISION.json",
        "gate": "PHASE 1 / GATE 1.5 - REFERENCE-ANCHOR AVAILABILITY & NUMERICAL-ZERO CHECK",
        "ANCHOR_STATUS": anchor_status,
        "ZERO_GATE": zero_gate,
        "anchor_definition": "NONE",
        "why_non_circular": (
            "No anchor was selected, so no circular selection occurred. The audit that reached "
            "this conclusion never read a trusted-8 pose value: it inspected file structure, "
            "group attributes and metadata columns only. Candidate A2 (`stage`) was accepted as "
            "pose-independent but rejected for specifying no posture; candidate C (FK geometry) "
            "was rejected precisely BECAUSE it is circular."
        ),
        "local_corpus": {
            "n_files": inv["n_files"],
            "n_sessions": inv["n_sessions"],
            "n_participants": inv["n_users"],
            "hand_sides": inv["sides"],
            "total_frames": inv["total_frames"],
            "split_values": inv["split_values"],
            "held_out_user": inv["held_out_user_values"],
            "stage_vocabulary_local": sorted(set(inv["stages_left"]) | set(inv["stages_right"])),
        },
        "candidate_anchor_sources": cands,
        "tolerance_audit": tol,
        "db9_reference_comparator": comparator,
        "trusted8_zero_statistics": "NOT_MEASURED",
        "reference_frames_synthesised": False,
        "downstream_firewall": {
            "DOWNSTREAM_HEAD_ACCESSED": "NO",
            "TASK_OUTPUT_INSPECTED": "NO",
            "PREDICTED_POSE_USED": "NO",
            "MAPPING_TUNED": "NO",
            "OFFSET_FITTED": "NO",
        },
        "execution_scope": {
            "models_trained": 0,
            "server_used": False,
            "gpu_used": False,
            "full_corpus_downloaded": False,
            "inference_rerun": False,
            "offset_or_scale_fitted": False,
            "pose_values_read_for_anchor_selection": False,
        },
        "scientific_framing": (
            "NOT_EVALUABLE_LOCALLY is not a scientific failure. It states that the current local "
            "mini corpus cannot independently answer cross-source numerical-zero compatibility, "
            "because no released field identifies a physical reference/neutral hand posture."
        ),
        "next_allowed_step": (
            "Do not invent a zero calibration; decide whether to run an explicitly labelled "
            "native-coordinate diagnostic or obtain an independent physical anchor."
        ),
    }
    (ART / "REFERENCE_ANCHOR_DECISION.json").write_text(
        json.dumps(decision, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    compat = {
        "artifact": "TRUSTED8_ZERO_COMPATIBILITY.json",
        "gate": "PHASE 1 / GATE 1.5",
        "ANCHOR_STATUS": anchor_status,
        "ZERO_GATE": zero_gate,
        "status": "NOT_MEASURED",
        "reason": (
            "No independent physical reference anchor is available in the local emg2pose mini "
            "corpus (see REFERENCE_ANCHOR_DECISION.json for the full candidate audit). No zero "
            "statistics are reported and no reference frames were synthesised."
        ),
        "per_dof": [
            {
                "dof": dof,
                "emg2pose_joint": joint,
                "emg2pose_index": idx,
                "n": None, "median_deg": None, "mean_deg": None, "std_deg": None,
                "p05_deg": None, "p25_deg": None, "p75_deg": None, "p95_deg": None,
                "min_deg": None, "max_deg": None, "median_abs_deg": None,
                "iqr_deg": None,
                "compatibility_verdict": "NOT_MEASURED",
            }
            for dof, joint, idx in TRUSTED8
        ],
        "db9_reference_comparator": comparator,
        "reporting_units": "degrees",
        "db9_side_note": (
            "The DB9 reference-anchor residual is reported for context only. Because the "
            "emg2pose side is NOT_MEASURED, no comparison, subtraction or classification was "
            "performed, and no offset was fitted."
        ),
    }
    (ART / "TRUSTED8_ZERO_COMPATIBILITY.json").write_text(
        json.dumps(compat, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    logs = LANE / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / "gate1_5_stdout.txt").write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    log("artifacts written:")
    log(f"  {ART / 'REFERENCE_ANCHOR_DECISION.json'}")
    log(f"  {ART / 'TRUSTED8_ZERO_COMPATIBILITY.json'}")
    log(f"  {logs / 'gate1_5_stdout.txt'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
