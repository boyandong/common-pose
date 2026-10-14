#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Independent verification of the GATE 1.5 lane artifacts.

Not part of the deliverable set; used to check the lane mechanically.
Run:  <EMG2POSE_VENV>\\Scripts\\python.exe -X utf8 scripts/_verify_gate1_5.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

LANE = Path(__file__).resolve().parent.parent
os.chdir(LANE)

fails: list[str] = []
n = [0]


def chk(cond, msg: str) -> None:
    n[0] += 1
    if not cond:
        fails.append(msg)


dec = json.loads(Path("artifacts/REFERENCE_ANCHOR_DECISION.json").read_text(encoding="utf-8"))
com = json.loads(Path("artifacts/TRUSTED8_ZERO_COMPATIBILITY.json").read_text(encoding="utf-8"))

# --- decision ---
chk(dec["ANCHOR_STATUS"] == "NO_INDEPENDENT_ANCHOR", "ANCHOR_STATUS")
chk(dec["ZERO_GATE"] == "NOT_EVALUABLE_LOCALLY", "ZERO_GATE")
chk(dec["anchor_definition"] == "NONE", "anchor_definition")
chk(dec["trusted8_zero_statistics"] == "NOT_MEASURED", "zero stats flag")
chk(dec["reference_frames_synthesised"] is False, "synth flag")
for k, v in dec["downstream_firewall"].items():
    chk(v == "NO", f"firewall {k}")
for k, v in dec["execution_scope"].items():
    chk(v in (0, False), f"scope {k}={v}")
chk(dec["execution_scope"]["pose_values_read_for_anchor_selection"] is False, "pose read for selection")

# --- candidate table ---
cands = {c["id"]: c for c in dec["candidate_anchor_sources"]}
chk(set(cands) == {"A1", "A2", "A3", "B", "C", "D"}, "candidate id set")
chk(cands["A2"]["present_locally"] is True and cands["A2"]["independent_of_trusted8"] is True, "A2 axes")
chk("DOES_NOT_DEFINE_A_POSTURE" in cands["A2"]["verdict"], "A2 verdict")
chk(cands["C"]["independent_of_trusted8"] is False, "C independence")
chk("CIRCULAR" in cands["C"]["verdict"], "C verdict")
chk(cands["A3"]["present_locally"] is False, "A3 absent locally")
for cid in ("A1", "B", "D"):
    chk(cands[cid]["present_locally"] is False, f"{cid} absent")

# --- tolerance audit ---
chk(dec["tolerance_audit"]["pre_existing_reference_anchor_tolerance_found"] is False, "no pre-existing tol")

# --- DB9 comparator traced to source ---
src = json.loads(
    Path(
        r"<PROJECT_ROOT>"
        r"\audits\db9\coordinate_audit\artifacts\DB9_SOURCE_CALIBRATION_AUDIT.json"
    ).read_text(encoding="utf-8")
)
idx = {nm: i for i, nm in enumerate(src["canonical16_names"])}
for dobj in com["per_dof"]:
    dof = dobj["dof"]
    for s in ("DB1", "DB2", "DB5"):
        exp = round(src["reference_posture_per_source"][s]["per_joint_median_deg"][idx[dof]], 4)
        got = dec["db9_reference_comparator"]["per_source"][s]["trusted8_per_joint_median_deg"][dof]
        chk(abs(exp - got) < 1e-9, f"{dof}/{s} anchor residual {got} != {exp}")

# --- zero compatibility artifact ---
chk(com["status"] == "NOT_MEASURED", "compat status")
chk(com["ZERO_GATE"] == "NOT_EVALUABLE_LOCALLY", "compat gate")
chk(com["ANCHOR_STATUS"] == "NO_INDEPENDENT_ANCHOR", "compat anchor status")
chk(len(com["per_dof"]) == 8, "8 DOF rows")
stat_fields = ["n", "median_deg", "mean_deg", "std_deg", "p05_deg", "p25_deg",
               "p75_deg", "p95_deg", "min_deg", "max_deg", "median_abs_deg", "iqr_deg"]
for r in com["per_dof"]:
    for f in stat_fields:
        chk(r[f] is None, f"{r['dof']} {f} must be None")
    chk(r["compatibility_verdict"] == "NOT_MEASURED", f"{r['dof']} verdict")
chk(com["reporting_units"] == "degrees", "units")

# --- spec must NOT exist ---
chk(not Path("REFERENCE_ANCHOR_SPEC.md").exists(), "spec must not exist")
chk(not Path("REFERENCE_ANCHOR_SPEC.sha256").exists(), "spec sha must not exist")

# --- required lane files ---
for f in ["README.md", "REFERENCE_ANCHOR_AVAILABILITY.md",
          "artifacts/REFERENCE_ANCHOR_DECISION.json",
          "artifacts/TRUSTED8_ZERO_COMPATIBILITY.json",
          "scripts/audit_reference_anchor.py", "logs/gate1_5_stdout.txt"]:
    chk(Path(f).exists(), f"missing {f}")

# --- the audit script reads no pose values: import surface + no angle indexing ---
script = Path("scripts/audit_reference_anchor.py").read_text(encoding="utf-8")
imports = re.findall(r"^\s*(?:import|from)\s+([A-Za-z_][\w.]*)", script, re.M)
allowed = {"__future__", "csv", "glob", "hashlib", "json", "os", "re", "sys",
           "collections", "pathlib", "h5py"}
extra = [i for i in imports if i.split(".")[0] not in allowed]
chk(not extra, f"unexpected imports: {extra}")
chk("joint_angles'" not in script.replace("joint_angles(20)", ""), "no joint_angles field read")

print(f"assertions: {n[0]}  failures: {len(fails)}")
for f in fails:
    print(f"  - {f}")
print()
print("RESULT:", "PASS" if not fails else "FAIL")
sys.exit(0 if not fails else 1)
