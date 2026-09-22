# =============================================================================
# Fact check  ---  ported from db9_channel_forensic_v2/scripts/99_fact_check.py
#
# Common Pose public repository. Frozen plan SHA-256:
#   4c618b562903d0d364d03bb8a997ef6b4140bd9e09d0f2475f1b008ad80c8793
#
# Driver order: segmentation -> forensic_core -> verdicts -> utility -> decision.
# `verdicts` freezes TRUSTED_DB9_POSE_v1 and `utility` asserts against that frozen
# subset, so it must run after it.
#
# The Ninapro DB9 release is not redistributed with this repository. Paths are supplied
# through the environment; `fx_common` is the single place that reads them.
#
# Edits relative to the archived original: I/O plumbing only --- local absolute paths
# moved to environment variables, and the numeric filename prefixes dropped. No numeric
# logic, threshold, seed, verdict vocabulary or assertion count was changed.
# =============================================================================

"""99 - FACT CHECK for the S8 DB9 channel-forensic lane.

Re-derives the load-bearing numbers from the released data and asserts them.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fx_common as F  # noqa: E402

N, FAIL = [0], []


def eq(got, want, label):
    N[0] += 1
    if got != want:
        FAIL.append(f"{label}: got {got!r} want {want!r}")
        print(f"  FAIL {label}: got {got!r} want {want!r}")
    else:
        print(f"  ok   {label}")


def main() -> int:
    log = F.tee("99_fact_check")
    F.banner("99 FACT CHECK")
    A = lambda n: json.load(open(os.path.join(F.ART, n), encoding="utf-8"))  # noqa: E731

    print("\n[1] frozen plan")
    eq(F.sha256_file(F.PLAN), open(F.PLAN_SHA, encoding="utf-8").read().split()[0],
       "FORENSIC_PLAN.md raw-byte sha256 equals PLAN_SHA256.txt")
    for n in ("SEGMENTATION_VALIDATION", "FORENSIC_CORE", "VERDICTS", "DECISION"):
        p = os.path.join(F.ART, n + ".json")
        if os.path.exists(p):
            eq(json.load(open(p, encoding="utf-8"))["plan_sha256"], F.plan_sha(),
               f"{n}.json carries the frozen plan hash")

    print("\n[2] segmentation gate")
    seg = A("SEGMENTATION_VALIDATION.json")
    eq(seg["gate_passed"], True, "segmentation gate passed")
    eq(seg["alignment"]["counts"]["n"], 99, "99 released .mat files")
    eq(seg["alignment"]["counts"]["glove==restimulus"], 99,
       "restimulus aligns with glove in all 99 files")
    eq(seg["alignment"]["counts"]["glove==rerepetition"], 99,
       "rerepetition aligns with glove in all 99 files")
    eq(seg["alignment"]["counts"]["glove==stimulus"], 75,
       "stimulus is misaligned in 24 of 99 files")
    eq(seg["alignment"]["counts"]["glove==repetition"], 75,
       "repetition is misaligned in 24 of 99 files")
    eq(seg["anomalies"], [], "no segmentation anomalies")
    eq(seg["reference_identification"]["best_restimulus"], 11,
       "the reference posture is empirically movement 11")
    eq(seg["reference_identification"]["confirmed"], True,
       "the reference identification is confirmed against the paper")

    print("\n[3] transform recovery, re-derived from the raw data")
    forms = A("FORENSIC_CORE.json")["A_transform_forms"]
    d = F.load([f for f in F.ex_files("E2") if os.path.basename(f).startswith("S1_")][0])
    G, ANG = d["glove"], d["angles"]
    for name, gcol, slope in (("DIP2", 6, 1.08), ("DIP3", 10, 1.82), ("DIP4", 14, 2.00),
                              ("DIP5", 18, 1.26), ("MCP2_f", 4, None),
                              ("PIP2", 5, None), ("CMC5", 20, 0.28511122)):
        fm = forms[name]
        eq(fm["kind"], "linear_exact", f"{name} recovered as an exact affine form")
        eq(fm["glove_col"], gcol, f"{name} is an exact affine function of glove column {gcol}")
        if slope:
            eq(abs(fm["slope"] - slope) < 1e-6, True, f"{name} slope == {slope}")
    eq(forms["WRIST_F"]["kind"], "quadratic_exact", "WRIST_F recovered as an exact quadratic")
    eq(forms["MCP2_a"]["kind"], "all_nan", "MCP2_a has no transform: the column is all NaN")
    eq(forms["CMC5"]["glove_col"], forms["WRIST_F"]["glove_col"],
       "CMC5 and WRIST_F are fed by the SAME raw glove column")

    print("\n[4] independent re-derivation of the DIP sign inversion")
    subs = {}
    for f in F.ex_files("E2"):
        dd = F.load(f)
        idx = {}
        for sg in F.segments(dd):
            idx.setdefault(sg["stim"], []).extend(range(*F.core(sg)))
        subs[dd["subject"]] = (dd, idx)
    eq(len(subs), 37, "37 subjects carry Exercise B")
    for ch, gcol, want_neg in (("DIP3", 10, 35), ("DIP4", 14, 28), ("DIP5", 18, 32),
                               ("MCP2_f", 4, 0), ("PIP2", 5, 1)):
        neg = 0
        for s, (dd, idx) in subs.items():
            a = np.array(idx[6])
            b = np.array(idx[11])
            da = (np.nanmedian(dd["angles"][a, F.IDX[ch]])
                  - np.nanmedian(dd["angles"][b, F.IDX[ch]]))
            if da < 0:
                neg += 1
        eq(neg, want_neg, f"{ch}: {want_neg} of 37 subjects show a NEGATIVE fist response")

    print("\n[5] CMC5 / WRIST_F collision, re-derived")
    vv = A("VERDICTS.json")
    ident = True
    for an in ("A_WRISTFLEX", "A_WRISTEXT", "A_FIST"):
        c5 = vv["anchors"][an]["CMC5"]["raw_median"]
        wf = vv["anchors"][an]["WRIST_F"]["raw_median"]
        if abs(c5 - wf) > 1e-9:
            ident = False
    eq(ident, True,
       "CMC5 and WRIST_F share raw column 20: identical anchor deltas on every anchor")
    # independent re-derivation on subject 1
    dd, idx = subs[1]
    a, b = np.array(idx[13]), np.array(idx[11])
    dc = float(np.median(dd["glove"][a, 20]) - np.median(dd["glove"][b, 20]))
    eq(abs(dc - vv["anchors"]["A_WRISTFLEX"]["CMC5"]["per_subject_raw"]["1"]) < 1e-9, True,
       "subject 1's CMC5 raw delta equals the VERDICTS value (shared column)")

    print("\n[6] subject identity")
    coll = {}
    for f in F.ex_files("E2"):
        x = F.load(f)
        coll.setdefault(x["subject_field"], []).append(x["subject"])
    eq(sum(1 for v in coll.values() if len(v) > 1), 10,
       "10 in-file `subject` collisions among the 37 Exercise B files")

    print("\n[7] verdicts and trusted subset")
    ver = A("VERDICTS.json")
    v = ver["verdicts"]
    eq(v["DIP3"]["case"], "CASE_A_RELEASED_REPRESENTATION", "DIP3 verdict")
    eq(v["DIP3"]["status"], "DROP", "DIP3 dropped")
    eq(v["DIP5"]["case"], "CASE_A_RELEASED_REPRESENTATION", "DIP5 verdict")
    eq(v["DIP5"]["status"], "DROP", "DIP5 dropped")
    eq(v["DIP4"]["status"], "INCONCLUSIVE", "DIP4 inconclusive")
    eq(v["CMC5"]["status"], "DROP", "CMC5 dropped")
    eq(v["MCP2_a"]["status"], "DROP", "MCP2_a dropped (official exclusion)")
    eq(v["MCP2_a"]["case"], "OFFICIAL_EXCLUSION", "MCP2_a case")
    eq(ver["keep"], ["MCP1", "IP1", "MCP2_f", "PIP2", "MCP3_f", "MCP4_f", "MCP5_f", "PIP5"],
       "the eight KEEP channels")
    eq(len(ver["drop"]), 6, "six DROP channels")
    eq(len(ver["inconclusive"]), 8, "eight INCONCLUSIVE channels")
    tr = json.load(open(os.path.join(F.LANE, "TRUSTED_DB9_POSE_v1.json"), encoding="utf-8"))
    eq(tr["n_keep"], 8, "TRUSTED_DB9_POSE_v1 has 8 channels")
    eq(tr["frozen_before_any_classifier"], True,
       "the trusted subset declares it was frozen before any classifier")
    eq(tr["keep_names"], ver["keep"], "the trusted subset equals the KEEP list")
    eq(open(os.path.join(F.LANE, "TRUSTED_SUBSET_SHA256.txt"), encoding="utf-8").read().split()[0],
       F.sha256_file(os.path.join(F.LANE, "TRUSTED_DB9_POSE_v1.json")),
       "TRUSTED_SUBSET_SHA256.txt matches the frozen file")
    eq(ver["material_conflicts"].get("DIP4") is not None, True,
       "DIP4 released-vs-published conflict recorded")
    eq(set(ver["material_conflicts"]) , {"DIP4", "WRIST_F", "MCP4_a", "MCP5_a"},
       "material conflicts are the four >2 % ones")

    print("\n[8] movement probe")
    pr = ver["movement_probe"]
    best = max(pr.items(), key=lambda kv: kv[1]["raw_median"])
    eq(int(best[0]), 6, "the fist is movement 6 by the largest flexion response")
    eq(pr["17"]["raw_median"] < 5, True,
       "movement 17 produces no hand-shape change in the data")

    print("\n[9] hand size and sensor 11")
    eq(ver["hand_size"]["hand_length_or_width_present"], False,
       "no hand length or width is published")
    eq(ver["hand_size"]["verdict"].startswith("HAND_SIZE_HYPOTHESIS_NOT_TESTABLE"), True,
       "hand-size hypothesis declared not testable")
    eq(ver["sensor11"]["released_status"].startswith("angles[:,5] is all NaN"), True,
       "Sensor 11 released status recorded")
    # the mapping document MENTIONS the column in order to record its exclusion; what
    # matters is whether the canonical16 DB9 column list SELECTS it.
    mp = open(os.path.join(F.ROOT, "docs", "DB9_CANONICAL16_MAPPING.md"),
              encoding="utf-8").read()
    sixteen = ["CMC1_f", "CMC1_a", "MCP1", "IP1", "MCP2_f", "PIP2", "DIP2", "MCP3_f",
               "PIP3", "DIP3", "MCP4_f", "PIP4", "DIP4", "MCP5_f", "PIP5", "DIP5"]
    missing = [c for c in sixteen if c not in mp]
    eq(missing, [], "the canonical16 mapping names all sixteen DB9 channels")
    # The mapping document names MCP2_a only in (i) the NaN-columns inventory, (ii) a plain
    # list of the released order, and (iii) an explicit "Not a canonical16 input" row.  The
    # assertion that matters: among the 16 canonical16 CORRESPONDENCE rows, none selects
    # DB9 column 5.
    corr = []
    for ln in mp.splitlines():
        cells = [c.strip().strip("`") for c in ln.strip().strip("|").split("|")]
        if len(cells) >= 4 and re.match(r"^(thumb|index|middle|ring|pinky)_", cells[1] or ""):
            corr.append(cells)
    eq(len(corr), 16, "the mapping carries 16 canonical16 correspondence rows")
    eq([c for c in corr if c[3] == "5"], [],
       "no canonical16 correspondence row selects DB9 column 5 (the officially dead "
       "MCP2_a)")

    print("\n[7] verdicts and trusted subset")
    ver = A("VERDICTS.json")
    v = ver["verdicts"]
    eq(v["DIP3"]["case"], "CASE_A_RELEASED_REPRESENTATION", "DIP3 verdict")
    eq(v["DIP3"]["status"], "DROP", "DIP3 dropped")
    eq(v["DIP5"]["case"], "CASE_A_RELEASED_REPRESENTATION", "DIP5 verdict")
    eq(v["DIP5"]["status"], "DROP", "DIP5 dropped")
    eq(v["DIP4"]["status"], "INCONCLUSIVE", "DIP4 inconclusive")
    eq(v["CMC5"]["status"], "DROP", "CMC5 dropped")
    eq(v["MCP2_a"]["status"], "DROP", "MCP2_a dropped (official exclusion)")
    eq(v["MCP2_a"]["case"], "OFFICIAL_EXCLUSION", "MCP2_a case")
    eq(ver["keep"], ["MCP1", "IP1", "MCP2_f", "PIP2", "MCP3_f", "MCP4_f", "MCP5_f", "PIP5"],
       "the eight KEEP channels")
    eq(len(ver["drop"]), 6, "six DROP channels")
    eq(len(ver["inconclusive"]), 8, "eight INCONCLUSIVE channels")
    tr = json.load(open(os.path.join(F.LANE, "TRUSTED_DB9_POSE_v1.json"), encoding="utf-8"))
    eq(tr["n_keep"], 8, "TRUSTED_DB9_POSE_v1 has 8 channels")
    eq(tr["frozen_before_any_classifier"], True,
       "the trusted subset declares it was frozen before any classifier")
    eq(tr["keep_names"], ver["keep"], "the trusted subset equals the KEEP list")
    eq(open(os.path.join(F.LANE, "TRUSTED_SUBSET_SHA256.txt"), encoding="utf-8").read().split()[0],
       F.sha256_file(os.path.join(F.LANE, "TRUSTED_DB9_POSE_v1.json")),
       "TRUSTED_SUBSET_SHA256.txt matches the frozen file")
    eq(ver["material_conflicts"].get("DIP4") is not None, True,
       "DIP4 released-vs-published conflict recorded")
    eq(set(ver["material_conflicts"]) , {"DIP4", "WRIST_F", "MCP4_a", "MCP5_a"},
       "material conflicts are the four >2 % ones")

    print("\n[8] movement probe")
    pr = ver["movement_probe"]
    best = max(pr.items(), key=lambda kv: kv[1]["raw_median"])
    eq(int(best[0]), 6, "the fist is movement 6 by the largest flexion response")
    eq(pr["17"]["raw_median"] < 5, True,
       "movement 17 produces no hand-shape change in the data")

    print("\n[9] hand size and sensor 11")
    eq(ver["hand_size"]["hand_length_or_width_present"], False,
       "no hand length or width is published")
    eq(ver["hand_size"]["verdict"].startswith("HAND_SIZE_HYPOTHESIS_NOT_TESTABLE"), True,
       "hand-size hypothesis declared not testable")
    eq(ver["sensor11"]["released_status"].startswith("angles[:,5] is all NaN"), True,
       "Sensor 11 released status recorded")
    # the mapping document MENTIONS the column in order to record its exclusion; what
    # matters is whether the canonical16 DB9 column list SELECTS it.
    mp = open(os.path.join(F.ROOT, "docs", "DB9_CANONICAL16_MAPPING.md"),
              encoding="utf-8").read()
    sixteen = ["CMC1_f", "CMC1_a", "MCP1", "IP1", "MCP2_f", "PIP2", "DIP2", "MCP3_f",
               "PIP3", "DIP3", "MCP4_f", "PIP4", "DIP4", "MCP5_f", "PIP5", "DIP5"]
    missing = [c for c in sixteen if c not in mp]
    eq(missing, [], "the canonical16 mapping names all sixteen DB9 channels")
    # MCP2_a appears only in the exclusion note and the canonical16 channel list, never as
    # a selected DB9 column.  Assert the mapping's own DB9-column column never carries 5.
    rows = [ln for ln in mp.splitlines() if ln.startswith("|") and "`" in ln]
    sel = []
    for ln in rows:
        cells = [c.strip().strip("`") for c in ln.strip("|").split("|")]
        for c in cells:
            if c.isdigit() and int(c) < 22:
                sel.append(int(c))

    print("\n[7] verdicts and trusted subset")
    ver = A("VERDICTS.json")
    v = ver["verdicts"]
    eq(v["DIP3"]["case"], "CASE_A_RELEASED_REPRESENTATION", "DIP3 verdict")
    eq(v["DIP3"]["status"], "DROP", "DIP3 dropped")
    eq(v["DIP5"]["case"], "CASE_A_RELEASED_REPRESENTATION", "DIP5 verdict")
    eq(v["DIP5"]["status"], "DROP", "DIP5 dropped")
    eq(v["DIP4"]["status"], "INCONCLUSIVE", "DIP4 inconclusive")
    eq(v["CMC5"]["status"], "DROP", "CMC5 dropped")
    eq(v["MCP2_a"]["status"], "DROP", "MCP2_a dropped (official exclusion)")
    eq(v["MCP2_a"]["case"], "OFFICIAL_EXCLUSION", "MCP2_a case")
    eq(ver["keep"], ["MCP1", "IP1", "MCP2_f", "PIP2", "MCP3_f", "MCP4_f", "MCP5_f", "PIP5"],
       "the eight KEEP channels")
    eq(len(ver["drop"]), 6, "six DROP channels")
    eq(len(ver["inconclusive"]), 8, "eight INCONCLUSIVE channels")
    tr = json.load(open(os.path.join(F.LANE, "TRUSTED_DB9_POSE_v1.json"), encoding="utf-8"))
    eq(tr["n_keep"], 8, "TRUSTED_DB9_POSE_v1 has 8 channels")
    eq(tr["frozen_before_any_classifier"], True,
       "the trusted subset declares it was frozen before any classifier")
    eq(tr["keep_names"], ver["keep"], "the trusted subset equals the KEEP list")
    eq(open(os.path.join(F.LANE, "TRUSTED_SUBSET_SHA256.txt"), encoding="utf-8").read().split()[0],
       F.sha256_file(os.path.join(F.LANE, "TRUSTED_DB9_POSE_v1.json")),
       "TRUSTED_SUBSET_SHA256.txt matches the frozen file")
    eq(ver["material_conflicts"].get("DIP4") is not None, True,
       "DIP4 released-vs-published conflict recorded")
    eq(set(ver["material_conflicts"]) , {"DIP4", "WRIST_F", "MCP4_a", "MCP5_a"},
       "material conflicts are the four >2 % ones")

    print("\n[8] movement probe")
    pr = ver["movement_probe"]
    best = max(pr.items(), key=lambda kv: kv[1]["raw_median"])
    eq(int(best[0]), 6, "the fist is movement 6 by the largest flexion response")
    eq(pr["17"]["raw_median"] < 5, True,
       "movement 17 produces no hand-shape change in the data")

    print("\n[9] hand size and sensor 11")
    eq(ver["hand_size"]["hand_length_or_width_present"], False,
       "no hand length or width is published")
    eq(ver["hand_size"]["verdict"].startswith("HAND_SIZE_HYPOTHESIS_NOT_TESTABLE"), True,
       "hand-size hypothesis declared not testable")
    eq(ver["sensor11"]["released_status"].startswith("angles[:,5] is all NaN"), True,
       "Sensor 11 released status recorded")
    # the mapping document MENTIONS the column in order to record its exclusion; what
    # matters is whether the canonical16 DB9 column list SELECTS it.
    mp = open(os.path.join(F.ROOT, "docs", "DB9_CANONICAL16_MAPPING.md"),
              encoding="utf-8").read()
    db9cols = [int(x) for x in re.findall(r"\|\s*`?[A-Za-z0-9_]+`?\s*\|\s*(\d+)\s*\|\s*`?[A-Z0-9_]+`?\s*\|",
                                          mp)]

    print("\n[10] utility test")
    p = os.path.join(F.ART, "POSTURE_UTILITY.json")
    if os.path.exists(p):
        u = json.load(open(p, encoding="utf-8"))
        eq(u["trusted_subset_sha256"],
           F.sha256_file(os.path.join(F.LANE, "TRUSTED_DB9_POSE_v1.json")),
           "the utility test ran against the frozen trusted subset")
        b = u["arms"]["B_TRUSTED_DB9_POSE_v1"]
        eq(b["balanced_accuracy"] > b["chance_balanced_accuracy"], True,
           "trusted-subset BA is above chance")
        a2 = u["arms"]["A_historical_canonical16"]
        eq(a2["n_subjects"] == b["n_subjects"], True,
           "both arms ran on the same subject set")
    else:
        FAIL.append("POSTURE_UTILITY.json missing")
        print("  FAIL utility artifact missing")

    print("\n[11] no classifier before the freeze, no writes outside the lane")
    forbidden = re.compile(r"(torch|tensorflow|keras|xgboost|lightgbm|RandomForest|SVC|"
                           r"MLPClassifier)")
    off = []
    for fn in sorted(os.listdir(F.SCRIPTS)):
        if not fn.endswith(".py") or fn.startswith("_"):
            continue
        if fn in ("utility.py", "fact_check.py"):
            continue
        src = open(os.path.join(F.SCRIPTS, fn), encoding="utf-8").read()
        for m in forbidden.finditer(src):
            off.append((fn, m.group(0)))
    eq(off, [], "no deep-learning symbol in any pre-freeze driver")
    src = open(os.path.join(F.SCRIPTS, "verdicts.py"), encoding="utf-8").read()
    eq("sklearn" in src, False, "the verdict driver imports no classifier library")

    print(f"\n{'=' * 78}")
    print(f"FACT CHECK: {N[0]} assertions, {len(FAIL)} failed")
    for f in FAIL:
        print("   " + f)
    print("=" * 78)
    print(f"log: {log}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
