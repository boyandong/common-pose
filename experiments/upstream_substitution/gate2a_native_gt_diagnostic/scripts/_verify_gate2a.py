#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Independent verification of the GATE 2A lane artifacts.

Checks the frozen plan hash, the exact replication of the frozen DB9 record, internal
consistency of every reported statistic, the decision rule as declared in the plan, and
the firewall. Not part of the deliverable set.

Run: <EMG2POSE_VENV>\\Scripts\\python.exe -X utf8 scripts/_verify_gate2a.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
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


def close(a, b, tol=1e-9):
    return a is not None and b is not None and abs(a - b) <= tol


b = json.loads(Path("artifacts/GT_HEAD_BEHAVIOR.json").read_text(encoding="utf-8"))
d = json.loads(Path("artifacts/GATE2A_DECISION.json").read_text(encoding="utf-8"))
frozen_rec = json.loads(Path(
    r"<PROJECT_ROOT>\audits\db9\channel_forensic"
    r"\artifacts\FINAL_VALIDATION.json").read_text(encoding="utf-8"))["Q4_posture8"]["results"]["B_TRUSTED_DB9_POSE_v1"]

# ---- plan hash chain ----
plan_sha = hashlib.sha256(Path("GATE2A_PLAN.md").read_bytes()).hexdigest()
sidecar = Path("GATE2A_PLAN.sha256").read_text(encoding="ascii").split()[0]
chk(plan_sha == sidecar, "plan sha != sidecar")
chk(b["plan_sha256"] == plan_sha, "GT_HEAD_BEHAVIOR plan sha mismatch")
chk(d["plan_sha256"] == plan_sha, "DECISION plan sha mismatch")

# ---- frozen subset identity ----
chk(b["frozen_subset_sha256"] ==
    "e51dde6e63941fd080c84f3896a98cf50fba9e17d5f9cebe909253d5465782d1", "frozen subset sha")

# ---- replication of the frozen DB9 record ----
rc = b["replication_check"]
chk(rc["exact"] is True, "replication not exact")
rep = rc["reconstructed"]
chk(rep["n_frames"] == frozen_rec["n_frames"], "n_frames")
chk(rep["n_subjects"] == frozen_rec["n_subjects"], "n_subjects")
chk(close(round(rep["accuracy"], 6), round(frozen_rec["accuracy"], 6)), "accuracy")
chk(close(round(rep["balanced_accuracy"], 6), round(frozen_rec["balanced_accuracy"], 6)), "BA")
chk(close(round(rep["macro_f1"], 6), round(frozen_rec["macro_f1"], 6)), "macroF1")
for c in range(1, 9):
    # JSON round-trips the int keys to strings
    chk(close(round(rep["per_class_recall"][str(c)], 6),
              round(frozen_rec["per_class_recall"][str(c)], 6)), f"recall {c}")
chk(b["class_occupancy"]["entropy_bits"] > 0, "entropy positive")
chk(b["head"]["tuning_performed"] is False, "tuning flag")
chk(b["head"]["random_seed"] is None, "seed should be None")

# ---- occupancy internal consistency ----
occ = b["class_occupancy"]["fractions"]
chk(len(occ) == 8, "8 classes")
tot = sum(occ.values())
chk(close(tot, 1.0, 1e-6), f"occupancy sums to {tot}")
chk(close(max(occ.values()), b["class_occupancy"]["max_class_fraction"], 1e-12), "max frac")
import math
ent = -sum(p * math.log2(p) for p in occ.values() if p > 0)
chk(close(ent, b["class_occupancy"]["entropy_bits"], 1e-9), "entropy recompute")

# ---- decision rule re-applied from the reported evidence ----
th = d["declared_thresholds"]
ev = d["evidence"]
cls_sorted = sorted(occ.values(), reverse=True)
collapse = sum(cls_sorted[:th["collapse_max_classes"]]) > th["collapse_frac"]
degen = (collapse and ev["n_distinct_stage_dominant_classes"] <= 2
         and ev["n_side_dominant_classes"] <= 2) \
    or (ev["switch_rate_per_sample"] > th["switch_rate"]) \
    or (ev["margin_frac_le_zero"] > th["bad_margin_frac"]) \
    or (ev["top2_pair_4_5_fraction"] > th["class45_frac"])
ambig = (ev["occupancy_entropy_bits"] < th["ambiguity_entropy_bits"]) \
    or (ev["n_side_dominant_classes"] > 1) \
    or (ev["n_distinct_stage_dominant_classes"] == 1)
expected = "DEGENERATE" if degen else ("AMBIGUOUS" if ambig else "STRUCTURED_NONDEGENERATE")
chk(d["GATE2A_DECISION"] == expected,
    f"decision {d['GATE2A_DECISION']} but rule yields {expected}")
chk(not d["degenerate_triggers"], "de degenerate triggers present")
chk(not d["ambiguous_triggers"], "de ambiguous triggers present")
chk(ev["n_stages"] == 15, "15 stages")

# ---- sampling arithmetic ----
e = b["emg2pose_input"]
chk(e["stored_rows"] == 4218756, "stored rows")
chk(e["gt_valid_rows"] + e["ik_failure_rows"] == e["stored_rows"], "row accounting")
chk(e["analysis_sampling_rate_hz"] == 50.0, "50 Hz")
chk(e["analysis_samples"] <= e["stored_rows"] // 40, "samples > blocks")
chk(close(e["ik_failure_rows"] / e["stored_rows"], 0.15624795555846321, 1e-9), "IK row frac")
chk(e["participants"] == 1 and e["sessions"] == 1, "corpus shape")
chk(e["sides"] == {"left": 15, "right": 15}, "sides")
chk("GROUND TRUTH" in e["source"], "GT-only declaration")

# ---- side / stage CSVs ----
with open("artifacts/GT_HEAD_BEHAVIOR_BY_SIDE.csv", encoding="utf-8", newline="") as fh:
    srows = list(csv.DictReader(fh))
chk(len(srows) == 2, "2 side rows")
chk({r["side"] for r in srows} == {"left", "right"}, "side values")
tot_side = sum(int(r["n_samples"]) for r in srows)
chk(tot_side == e["analysis_samples"], f"side samples {tot_side} != {e['analysis_samples']}")

with open("artifacts/GT_HEAD_BEHAVIOR_BY_STAGE.csv", encoding="utf-8", newline="") as fh:
    trows = list(csv.DictReader(fh))
chk(len(trows) == 15, "15 stage rows")
tot_stage = sum(int(r["n_samples"]) for r in trows)
chk(tot_stage == e["analysis_samples"], f"stage samples {tot_stage} != {e['analysis_samples']}")

# ---- stage class-4 occupancy matches the JSON map ----
for r in trows:
    chk(close(float(r["class4_fraction"]),
              d["evidence"]["class4_fraction"] if False else
              b["class4_class5"]["stage_wise_class4"][r["stage"]], 1e-12),
        f"stage class4 {r['stage']}")

# ---- firewall ----
fw = b["firewall"]
chk(fw == d["firewall"], "firewall mismatch between artifacts")
for k, v in fw.items():
    chk(v in ("NO", "NOT RUN"), f"firewall {k}={v}")
chk(fw["PREDICTED_POSE_USED"] == "NO", "predicted pose")
chk(fw["GT_VS_PRED_AGREEMENT"] == "NOT RUN", "gt-vs-pred")
chk(fw["UNKNOWN_GATE_CREATED"] == "NO", "unknown gate")
chk(fw["CALIBRATION_FITTED"] == "NO", "calibration")

# ---- no semantic accuracy claimed: balanced_accuracy/macro_f1 must not appear for emg2pose ----
emg_keys = set(json.dumps(b["class_occupancy"])) | set(b["margin_structure"])
chk("balanced_accuracy" not in json.dumps(b["class_occupancy"]), "no BA in emg2pose block")
chk(len(d["not_claimed"]) >= 6, "not_claimed list")
chk(any("accuracy" in s for s in d["not_claimed"]), "accuracy disclaimed")

print(f"assertions: {n[0]}  failures: {len(fails)}")
for f in fails:
    print(f"  - {f}")
print()
print("RESULT:", "PASS" if not fails else "FAIL")
sys.exit(0 if not fails else 1)
