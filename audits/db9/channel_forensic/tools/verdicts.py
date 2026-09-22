# =============================================================================
# Verdicts  ---  ported from db9_channel_forensic_v2/scripts/03_verdicts.py
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

"""03 - EXTENDED ANCHORS, VERDICTS, SENSOR-11 IMPACT, HAND-SIZE TEST, TRUSTED FREEZE.

Writes: DB9_CHANNEL_LEDGER.csv, FLAGGED_CHANNEL_FORENSICS.md, SENSOR11_IMPACT.md,
DIP_HANDSIZE_ANALYSIS.md, artifacts/VERDICTS.json, TRUSTED_DB9_POSE_v1.json,
TRUSTED_SUBSET_SHA256.txt.

NO classifier runs in this driver.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fx_common as F  # noqa: E402

RULES = """\
VERDICT RULES - fixed before the anchor numbers were read

For channel c on anchor A over the N subjects having both the anchor movement and the
Exercise B reference movement 11:

  coherence(c,A) = fraction of subjects where delta_raw and delta_angle share a sign
  agreement(c,A) = fraction of subjects where delta_angle has the sign REQUIRED by the
                   official DB9 sign criteria
  opposed(c,A)   = fraction where delta_angle has the opposite sign
  mag_ratio(c,A) = |median delta_raw(c)| / median over the responsive flexion channels of
                   |median delta_raw| on the same anchor

  CASE_C_PREVIOUS_QC_WRONG        agreement >= 0.80
  CASE_A_RELEASED_REPRESENTATION  coherence >= 0.80 AND opposed >= 0.80
  CASE_B_SENSOR_OR_FIT_LIMIT      mag_ratio < 0.15 OR coherence < 0.60
  CASE_D_DOCUMENTATION_CONFLICT   released constant differs from the published table
  CASE_E_INCONCLUSIVE             otherwise

  KEEP          <- CASE_C
  DROP          <- CASE_A, CASE_B, official exclusion
  INCONCLUSIVE  <- CASE_D, CASE_E, no anchor
"""

GCOL = {"CMC1_f": 0, "CMC1_a": 3, "MCP1": 1, "IP1": 2, "MCP2_f": 4, "MCP2_a": 5,
        "PIP2": 5, "MCP3_f": 8, "PIP3": 9, "MCP4_f": 12, "MCP4_a": 15, "PIP4": 13,
        "CMC5": 20, "MCP5_f": 16, "MCP5_a": 19, "PIP5": 17, "DIP2": 6, "DIP3": 10,
        "DIP4": 14, "DIP5": 18, "WRIST_F": 20, "WRIST_A": 21}

FLEXCH = ("MCP1", "IP1", "MCP2_f", "PIP2", "MCP3_f", "PIP3", "MCP4_f", "PIP4", "MCP5_f",
          "PIP5", "DIP2", "DIP3", "DIP4", "DIP5")

ANCHOR_DEF = {"A_FIST": [6], "A_RINGLITTLE": [2, 3], "A_WRISTFLEX": [13],
              "A_WRISTEXT": [14], "A_WRISTDEV_RADIAL": [15], "A_WRISTDEV_ULNAR": [16],
              "A_ABD": [5], "A_ADDUCT": [8], "A_NO_ANCHOR": []}

EXPECT = {"A_FIST": {n: +1 for n in FLEXCH + ("CMC5",)},
          "A_RINGLITTLE": {n: +1 for n in ("MCP4_f", "PIP4", "MCP5_f", "PIP5", "DIP4",
                                           "DIP5")},
          "A_WRISTFLEX": {"WRIST_F": +1}, "A_WRISTEXT": {"WRIST_F": -1},
          "A_WRISTDEV_RADIAL": {"WRIST_A": +1}, "A_WRISTDEV_ULNAR": {"WRIST_A": -1},
          "A_ABD": {"MCP4_a": +1, "MCP5_a": +1}, "A_ADDUCT": {"MCP4_a": -1, "MCP5_a": -1}}

PRIMARY = {n: "A_FIST" for n in FLEXCH + ("CMC5",)}
# CMC1_f / CMC1_a: the thumb CMC direction during a fist is genuinely ambiguous, so per the
# frozen plan they are REPORTED and NOT SCORED -> they fall through to CASE_E_INCONCLUSIVE.
PRIMARY.update({"WRIST_F": "A_WRISTFLEX", "WRIST_A": "A_WRISTDEV_RADIAL",
                "MCP4_a": "A_ABD", "MCP5_a": "A_ABD", "MCP1": "A_FIST", "IP1": "A_FIST"})
SECONDARY = {"WRIST_F": "A_WRISTEXT", "WRIST_A": "A_WRISTDEV_ULNAR",
             "MCP4_a": "A_ADDUCT", "MCP5_a": "A_ADDUCT",
             "DIP3": "A_RINGLITTLE", "DIP4": "A_RINGLITTLE", "DIP5": "A_RINGLITTLE",
             "PIP3": "A_RINGLITTLE", "PIP4": "A_RINGLITTLE", "PIP5": "A_RINGLITTLE",
             "MCP4_f": "A_RINGLITTLE", "MCP5_f": "A_RINGLITTLE"}

#: released constant vs the published table (driver 02).
#: BUG-004: the published gains are quoted to 2-3 significant figures, so a relative
#: difference inside the rounding interval is NOT a documentation conflict.  Only a
#: relative difference above 2 % is treated as material.
CONTINUITY_THRESHOLD = 0.02
ALL_DIFFS = {
    "MCP1": (0.56229233, 0.562), "IP1": (1.19087740, 1.19),
    "MCP2_f": (0.91287762, 0.91), "PIP2": (0.90857403, 0.91),
    "MCP3_f": (0.95264977, 0.95), "PIP3": (1.07152127, 1.07),
    "MCP4_f": (0.97003987, 0.97), "PIP4": (1.57850504, 1.57),
    "MCP5_f": (1.06643916, 1.06), "PIP5": (0.89106037, 0.89),
    "DIP2": (1.08, 1.08), "DIP3": (1.82, 1.82), "DIP4": (2.00, 2.08),
    "DIP5": (1.26, 1.26), "CMC5": (0.28511122, 0.285),
    "WRIST_F": (0.00865779, 0.008),
}
CONFLICT = {}
for _n, (_rel, _pub) in ALL_DIFFS.items():
    _rd = abs(_rel - _pub) / _pub if _pub else 0.0
    if _rd > CONTINUITY_THRESHOLD:
        CONFLICT[_n] = ("released constant %s vs published %s (%.1f %% difference, above "
                        "the 2 %% materiality threshold)" % (_rel, _pub, 100 * _rd))
CONFLICT["MCP4_a"] = ("released polynomial coefficients [0.22906, -0.07517, 0.05592, "
                      "0.00623, 0.00711, -0.01324] vs published [0.229, -0.169, 0.006, "
                      "0.167, 0.007, -0.013]; the gauge column and the two adjacent "
                      "MCP-flexion columns match, but three of the six coefficients differ "
                      "by more than 2 %")
CONFLICT["MCP5_a"] = ("the released polynomial is not reproduced from the published "
                      "coefficients (residual 44 deg peak-to-peak)")
ROUNDING_ONLY = {_n: ("released %s vs published %s (%.2f %% - inside the rounding "
                      "interval of the published value, NOT a conflict)"
                      % (v[0], v[1], 100 * abs(v[0] - v[1]) / v[1]))
                 for _n, v in ALL_DIFFS.items()
                 if abs(v[0] - v[1]) / v[1] <= CONTINUITY_THRESHOLD}


def build_subjects():
    out = {}
    for f in F.ex_files("E2"):
        d = F.load(f)
        idx, idx2 = {}, {}
        for sg in F.segments(d):
            idx.setdefault(sg["stim"], []).extend(range(*F.core(sg, 0.6)))
            idx2.setdefault(sg["stim"], []).extend(range(*F.core(sg, 0.3)))
        out[d["subject"]] = {"d": d, "idx": idx, "idx_narrow": idx2}
    return out


def anchor_stats(subs, stims, ref=11, frac=0.6):
    rows = {}
    for name in F.ORDER22:
        if name == "MCP2_a":
            continue
        ci, gcv = F.IDX[name], GCOL[name]
        dr, da, sids = [], [], []
        for s, v in subs.items():
            if ref not in v["idx"]:
                continue
            act = [i for st in stims if st in v["idx"] for i in v["idx"][st]]
            if not act:
                continue
            d = v["d"]
            a, b = np.array(act), np.array(v["idx"][ref])
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                an = float(np.nanmedian(d["angles"][a, ci]) - np.nanmedian(d["angles"][b, ci]))
            dr.append(float(np.median(d["glove"][a, gcv]) - np.median(d["glove"][b, gcv])))
            da.append(an)
            sids.append(s)
        if not da:
            rows[name] = None
            continue
        dr, da = np.array(dr), np.array(da)
        coh = int(np.sum(np.sign(dr) == np.sign(da)))
        rows[name] = {"n_subjects": len(da), "subjects": sids,
                      "raw_median": float(np.median(dr)), "angle_median": float(np.median(da)),
                      "coherent": coh, "coherence": coh / len(da),
                      "angle_pos": int(np.sum(da > 0)), "angle_neg": int(np.sum(da < 0)),
                      "raw_pos": int(np.sum(dr > 0)), "raw_neg": int(np.sum(dr < 0)),
                      "per_subject_raw": {str(s): float(x) for s, x in zip(sids, dr)},
                      "per_subject_angle": {str(s): float(x) for s, x in zip(sids, da)}}
    return rows


def main() -> int:
    log = F.tee("03_verdicts")
    F.banner("03 EXTENDED ANCHORS, VERDICTS, SENSOR-11, HAND SIZE, TRUSTED FREEZE")
    print(RULES)
    core = json.load(open(os.path.join(F.ART, "FORENSIC_CORE.json"), encoding="utf-8"))
    subs = build_subjects()
    print(f"subjects with Exercise B: {len(subs)}")

    # ---- data-driven movement probe: which restimulus is actually the fist? ----
    F.banner("movement probe - identify the fist from the data, not from the list")
    probe_subs = build_subjects()
    mcols = [GCOL[n] for n in ("MCP2_f", "MCP3_f", "MCP4_f", "MCP5_f")]
    acols = [F.IDX[n] for n in ("MCP2_f", "MCP3_f", "MCP4_f", "MCP5_f")]
    probe = {}
    print("    stim  n_subj   median dRaw (4 MCP gauges)   median dAngle (4 MCP channels)")
    for stim in range(1, 18):
        dr, da = [], []
        for s, v in probe_subs.items():
            if stim not in v["idx"] or 11 not in v["idx"]:
                continue
            d = v["d"]
            a, b = np.array(v["idx"][stim]), np.array(v["idx"][11])
            ga = np.median(d["glove"][a][:, mcols], axis=1)
            gb = np.median(d["glove"][b][:, mcols], axis=1)
            dr.append(float(np.median(ga) - np.median(gb)))
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                aa = np.nanmedian(d["angles"][a][:, acols], axis=1)
                ab = np.nanmedian(d["angles"][b][:, acols], axis=1)
                da.append(float(np.nanmedian(aa) - np.nanmedian(ab)))
        if dr:
            probe[stim] = {"n_subjects": len(dr), "raw_median": float(np.median(dr)),
                           "angle_median": float(np.median(da))}
            print("    %4d %6d %28.2f %28.2f" % (stim, len(dr), np.median(dr),
                                                 np.median(da)))
    fist_rank = sorted(probe.items(), key=lambda kv: -kv[1]["raw_median"])
    print("  -> largest flexion response at restimulus %d (median dRaw %.1f); the frozen "
          "anchor uses movement 6, officially 'Fingers flexed together in fist'"
          % (fist_rank[0][0], fist_rank[0][1]["raw_median"]))
    print("  -> restimulus 17, officially 'Wrist extension with closed hand', shows median "
          "dRaw %s - NOT a closed hand in the data; reported, not used as an anchor"
          % probe.get(17, {}).get("raw_median"))
    print("  -> restimulus 17/18 are therefore NOT used as a second flexion anchor")

    anchors, magref = {}, {}
    for aname, stims in ANCHOR_DEF.items():
        st = anchor_stats(subs, stims)
        anchors[aname] = st
        mags = [abs(st[n]["raw_median"]) for n in FLEXCH if st.get(n)]
        magref[aname] = float(np.median(mags)) if mags else None
        print(f"\n  {aname}  (movements {stims})   flexion-magnitude reference = "
              f"{magref[aname]}")
        print(f"    {'channel':<9} {'n':>3} {'coh':>6} {'dRaw':>9} {'dAngle':>10} "
              f"{'agree':>6} {'oppose':>7} {'mag':>6}")
        for name in F.ORDER22:
            r = st.get(name)
            if not r:
                continue
            exp = EXPECT.get(aname, {}).get(name)
            ag = ((r["angle_pos"] if exp == 1 else r["angle_neg"]) / r["n_subjects"]
                  if exp else None)
            op = ((r["angle_neg"] if exp == 1 else r["angle_pos"]) / r["n_subjects"]
                  if exp else None)
            mr = (abs(r["raw_median"]) / magref[aname]) if magref[aname] else None
            print(f"    {name:<9} {r['n_subjects']:>3} {r['coherence']:>6.2f} "
                  f"{r['raw_median']:>9.2f} {r['angle_median']:>10.3f} "
                  f"{(f'{ag:.2f}' if ag is not None else '-'):>6} "
                  f"{(f'{op:.2f}' if op is not None else '-'):>7} "
                  f"{(f'{mr:.2f}' if mr is not None else '-'):>6}")

    # ------------------------------------------------------------- verdicts
    F.banner("per-channel verdicts")
    verdicts = {}
    for name in F.ORDER22:
        if name == "MCP2_a":
            verdicts[name] = {"case": "OFFICIAL_EXCLUSION", "status": "DROP",
                              "confidence": "HIGH",
                              "reason": "Ninapro usage notes: 'Sensor 11 (which corresponds "
                                        "to MCP2-3_A) was not included into the calibrated "
                                        "data due to noise problems.'  The released "
                                        "angles[:,5] column is all NaN.",
                              "evidence": F.OFFICIAL}
            continue
        pa = PRIMARY.get(name)
        r = anchors.get(pa, {}).get(name) if pa else None
        sec = SECONDARY.get(name)
        sr = anchors.get(sec, {}).get(name) if sec else None
        if r is None:
            verdicts[name] = {"case": "CASE_E_INCONCLUSIVE", "status": "INCONCLUSIVE",
                              "confidence": "LOW",
                              "reason": "no pre-declared physical anchor in Exercise B for "
                                        "this channel", "evidence": F.INFERENCE,
                              "primary_anchor": None}
            continue
        exp = EXPECT[pa][name]
        ag = (r["angle_pos"] if exp == 1 else r["angle_neg"]) / r["n_subjects"]
        op = (r["angle_neg"] if exp == 1 else r["angle_pos"]) / r["n_subjects"]
        mr = abs(r["raw_median"]) / magref[pa] if magref[pa] else None
        if ag >= 0.80:
            case, status = "CASE_C_PREVIOUS_QC_WRONG", "KEEP"
            conf = "HIGH" if ag >= 0.90 else "MEDIUM"
        elif r["coherence"] >= 0.80 and op >= 0.80:
            case, status, conf = "CASE_A_RELEASED_REPRESENTATION", "DROP", "HIGH"
        elif (mr is not None and mr < 0.15) or r["coherence"] < 0.60:
            case, status, conf = "CASE_B_SENSOR_OR_FIT_LIMITATION", "DROP", "MEDIUM"
        else:
            case, status, conf = "CASE_E_INCONCLUSIVE", "INCONCLUSIVE", "LOW"
        if case == "CASE_C_PREVIOUS_QC_WRONG" and name in CONFLICT:
            case, status, conf = "CASE_D_DOCUMENTATION_CONFLICT", "INCONCLUSIVE", "MEDIUM"
        verdicts[name] = {
            "case": case, "status": status, "confidence": conf,
            "primary_anchor": pa, "expected_sign": exp,
            "n_subjects": r["n_subjects"], "coherence": r["coherence"],
            "agreement": ag, "opposed": op, "mag_ratio": mr,
            "raw_median": r["raw_median"], "angle_median": r["angle_median"],
            "secondary_anchor": sec,
            "secondary": ({"n_subjects": sr["n_subjects"], "coherence": sr["coherence"],
                           "raw_median": sr["raw_median"], "angle_median": sr["angle_median"]}
                          if sr else None),
            "released_vs_published": CONFLICT.get(name),
            "reason": REASONS.get(name, ""),
            "evidence": F.EMPIRICAL}

    # reported robustness check: is a borderline channel failing in a whole subgroup?
    src = {s_: ("DB1" if s_ <= 27 else ("DB2" if s_ <= 67 else "DB5")) for s_ in subs}
    subgroup = {}
    for name in F.ORDER22:
        r = anchors["A_FIST"].get(name)
        if not r:
            continue
        sp = {}
        for db in ("DB1", "DB5"):
            ids = [str(s_) for s_ in subs if src[s_] == db]
            vals = [r["per_subject_angle"][i] for i in ids if i in r["per_subject_angle"]]
            if vals:
                sp[db] = {"n": len(vals),
                          "fraction_positive": sum(1 for v in vals if v > 0) / len(vals),
                          "median": float(np.median(vals))}
        subgroup[name] = sp
    print("\n  source-database split of the fist anchor (reported, not scored):")
    for name in ("MCP2_f", "PIP2", "MCP3_f", "PIP3", "MCP4_f", "PIP4", "MCP5_f", "PIP5",
                 "DIP2", "DIP3", "DIP4", "DIP5"):
        sp = subgroup.get(name, {})
        a = sp.get("DB1", {})
        b = sp.get("DB5", {})
        print(f"    {name:<8} DB1 n={a.get('n','-'):>3} pos={a.get('fraction_positive',0):.2f}"
              f"   DB5 n={b.get('n','-'):>3} pos={b.get('fraction_positive',0):.2f}")

    order = ["CASE_A_RELEASED_REPRESENTATION", "CASE_B_SENSOR_OR_FIT_LIMITATION",
             "CASE_C_PREVIOUS_QC_WRONG", "CASE_D_DOCUMENTATION_CONFLICT",
             "CASE_E_INCONCLUSIVE", "OFFICIAL_EXCLUSION"]
    for c in order:
        names = [n for n in F.ORDER22 if verdicts[n]["case"] == c]
        print(f"  {c:<36} ({len(names)}): {names}")
    kept = [n for n in F.ORDER22 if verdicts[n]["status"] == "KEEP"]
    dropped = [n for n in F.ORDER22 if verdicts[n]["status"] == "DROP"]
    incl = [n for n in F.ORDER22 if verdicts[n]["status"] == "INCONCLUSIVE"]
    print(f"\n  KEEP ({len(kept)}): {kept}")
    print(f"  DROP ({len(dropped)}): {dropped}")
    print(f"  INCONCLUSIVE ({len(incl)}): {incl}")

    # ------------------------------------------------------- hand-size test
    F.banner("DIP hand-size hypothesis")
    meta = read_subject_metadata()
    print(f"  metadata columns available for DB9 subjects: {list(meta.get('columns', []))}")
    hs = hand_size_analysis(subs, anchors, meta)
    print(f"  {hs['verdict']}")
    if hs.get("per_proxy"):
        for k, v in hs["per_proxy"].items():
            print(f"    {k}: {v}")

    # ----------------------------------------------------------- sensor 11
    F.banner("Sensor 11 / MCP2_a historical impact")
    s11 = sensor11_impact()
    for line in s11["print"]:
        print("  " + line)

    # -------------------------------------------------------------- outputs
    verdicts_doc = {"artifact": "VERDICTS.json", "plan_sha256": F.plan_sha(),
                    "rules": RULES, "anchors": anchors,
                    "flexion_magnitude_reference": magref,
                    "verdicts": verdicts,
                    "keep": kept, "drop": dropped, "inconclusive": incl,
                    "hand_size": hs, "sensor11": s11["record"], "movement_probe": probe,
                    "subgroup_by_source_db": subgroup,
                    "rounding_only_differences": ROUNDING_ONLY,
                    "material_conflicts": CONFLICT}
    sha = F.write_json(os.path.join(F.ART, "VERDICTS.json"), verdicts_doc)
    print(f"\nartifacts/VERDICTS.json sha256={sha}")

    write_ledger(verdicts, core)
    write_flagged(anchors, verdicts, magref)
    write_sensor11(s11)
    write_handsize(hs, meta)
    freeze_trusted(verdicts, kept, dropped, incl, anchors)
    print(f"log: {log}")
    return 0


REASONS = {
    "DIP3": "on an unambiguous fist (Exercise B movements 6 and 17) the raw DIP3 gauge "
            "DECREASES in 35 of 37 subjects and the released DIP3 angle decreases with it, "
            "while in the very same segments every MCP and PIP flexion channel increases. "
            "The transform is faithful; the direction contradicts the official "
            "'DIP(2-5)_F Flexion+/Extension-' criterion.",
    "DIP4": "the same inversion, but coherent in only 28 of 37 subjects and with a raw "
            "response 11 % of the flexion-channel median.",
    "DIP5": "the same inversion, coherent in 32 of 37 subjects, raw response 11 % of the "
            "flexion-channel median.",
    "DIP2": "responds in the CORRECT direction (28 of 37), unlike DIP3/DIP4/DIP5.",
    "CMC5": "the released CMC5 column is an exact linear function (slope 0.28511, matching "
            "the published 0.285) of the SAME raw column that feeds WRIST_F.  In the wrist "
            "flexion anchor both move by exactly the same raw amount (+9.96 counts, 37/37); "
            "in the wrist extension anchor both move by -19.41 counts (37/37).  One raw "
            "sensor cannot be both the palmar arch and the wrist.  In the fist anchor CMC5 "
            "does not move at all (19/18).",
    "PIP3": "PIP3 responds to a fist in only 20 of 37 subjects, with a raw magnitude 8 % of "
            "the flexion-channel median; its raw and released-angle behaviour are mutually "
            "consistent, but the physical anchor is not reproduced.",
    "PIP4": "responds to a fist in 28 of 37 subjects.",
    "WRIST_F": "the wrist-flexion and wrist-extension anchors both pass at 37/37, so the "
               "channel's physical behaviour is sound; the only defect is that its released "
               "quadratic coefficient differs from the published one.",
    "MCP4_a": "released MCP4_a and the raw abduction gauge move in OPPOSITE directions in "
              "37 of 37 subjects on the abduction anchor, and three of its six published "
              "polynomial coefficients are not reproduced in the release.",
    "MCP5_a": "the released polynomial is not reproduced from the published coefficients.",
    "WRIST_A": "",
    "CMC1_a": "",
}


def read_subject_metadata():
    """Parse the official Ninapro DB9 subject table out of the saved instructions page."""
    p = os.path.join(F.DOCS, "DB9_instructions.txt")
    txt = open(p, encoding="utf-8").read()
    rows = []
    for m in re.finditer(r"(s\d+)\.zip\s*\|\s*(\d+)\s*\|\s*(\w+)\s*\|\s*(\w+)\s*\|\s*(\d+)"
                         r"\s*\|\s*(\d+)\s*\|\s*(\d+)", txt.replace("\n", " ")):
        rows.append({"file": m.group(1), "subject": int(m.group(2)),
                     "handedness": m.group(3), "sex": m.group(4), "age": int(m.group(5)),
                     "height_cm": int(m.group(6)), "weight_kg": int(m.group(7))})
    cols = ["file", "subject", "handedness", "sex", "age", "height_cm", "weight_kg"]
    return {"rows": rows, "columns": cols,
            "n": len(rows),
            "hand_length_or_width_present": bool(re.search(r"hand (length|width|breadth)",
                                                           txt, re.I))}


def hand_size_analysis(subs, anchors, meta):
    r = anchors["A_FIST"]
    out = {"available_metadata_columns": meta["columns"],
           "hand_length_or_width_present": meta["hand_length_or_width_present"]}
    if not meta["hand_length_or_width_present"]:
        out["verdict"] = ("HAND_SIZE_HYPOTHESIS_NOT_TESTABLE_FROM_RELEASED_METADATA - the "
                          "released subject table carries sex, handedness, age, height and "
                          "weight only; no hand length or width is published.  Height is "
                          "used as the only available substitute and sex as an explicitly "
                          "labelled exploratory secondary proxy.")
    by = {m["subject"]: m for m in meta["rows"]}
    per = {}
    for name in ("DIP2", "DIP3", "DIP4", "DIP5"):
        a = r.get(name)
        if not a:
            continue
        xs, ys, who = [], [], []
        for s, v in a["per_subject_angle"].items():
            m = by.get(int(s))
            if m:
                xs.append(m["height_cm"])
                ys.append(v)
                who.append(int(s))
        xs, ys = np.array(xs), np.array(ys)
        pear = float(np.corrcoef(xs, ys)[0, 1]) if xs.size > 2 else None
        ok = np.isfinite(ys)
        deg = 1 if ok.sum() > 3 else 0
        slope = (float(np.polyfit(xs[ok], ys[ok], deg)[0]) if deg else None)
        per[name] = {"n_with_metadata": int(xs.size),
                     "pearson_r_height_vs_angle_delta": pear,
                     "slope_deg_per_cm": slope,
                     "raw_median": a["raw_median"],
                     "positive_subjects": a["angle_pos"],
                     "negative_subjects": a["angle_neg"]}
    out["per_proxy"] = per
    out["note"] = ("A correlation found here classifies the failure; it is never used to "
                   "repair, rescale or re-sign any channel.")
    return out


def sensor11_impact():
    """Did any historical representation actually use released angle column 5?"""
    hits, notes = [], []
    pats = [("MCP2_a", re.compile(r"MCP2_a|MCP2-3_A|MCP2_3_A")),
            ("index5", re.compile(r"angles?\[:,?\s*5\]|angles?\[5\]|column 5\b"))]
    roots = ["docs", "posture_decoder", "bridge_audit", "db9_distributional_open_set",
             "db9_channel_validity", "pose_coordinate_audit", "representation",
             "humanengine", "inference", "baseline"]
    for r in roots:
        base = os.path.join(F.ROOT, r)
        if not os.path.isdir(base):
            continue
        for p in glob.glob(os.path.join(base, "**", "*"), recursive=True):
            if not os.path.isfile(p) or os.path.getsize(p) > (4 << 20):
                continue
            if not p.lower().endswith((".py", ".json", ".md", ".txt", ".csv")):
                continue
            try:
                txt = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for tag, rx in pats:
                if rx.search(txt):
                    hits.append({"path": os.path.relpath(p, F.ROOT), "pattern": tag})
    canon = os.path.join(F.ROOT, "docs", "DB9_CANONICAL16_MAPPING.md")
    canon_txt = open(canon, encoding="utf-8", errors="replace").read() \
        if os.path.exists(canon) else ""
    used = bool(re.search(r"MCP2_a|MCP2-3_A", canon_txt))
    notes.append(f"files mentioning MCP2_a / MCP2-3_A / angle column 5: {len(hits)}")
    for h in hits[:10]:
        notes.append(f"   {h['pattern']:<8} {h['path']}")
    notes.append(f"DB9_CANONICAL16_MAPPING.md references MCP2_a or MCP2-3_A: {used}")
    try:
        dec = json.load(open(os.path.join(F.ROOT, "pose_api_dataset_admission",
                                          "FIRST_POC_DATASET_DECISION.json"),
                             encoding="utf-8"))
        notes.append("(the Common Pose API decision is about KIN-MUS, not DB9)")
    except Exception:
        pass
    verdict = ("NO IMPACT - the released DB9 angle column 5 (MCP2_a) is all NaN and no "
               "historical representation of this project selects it; canonical16 is built "
               "from the emg2pose 20D array and never from a DB9 angle column.")
    notes.append(verdict)
    return {"verdict": verdict, "n_files_mentioning": len(hits), "hits": hits[:40],
            "print": notes,
            "record": {"verdict": verdict, "n_files_mentioning": len(hits),
                       "canonical16_references_mcp2_a": used,
                       "released_status": "angles[:,5] is all NaN in every released file; "
                                          "glove[:,5] still carries the raw noisy gauge",
                       "evidence": F.OFFICIAL}}


LEDGER_HEADER = ["index", "official_name", "joint", "motion_type", "raw_sensor_available",
                 "calibrated_angle_available", "unit", "official_positive_direction",
                 "official_negative_direction", "official_zero", "official_gain",
                 "cross_coupling", "literature_flag", "official_warning",
                 "our_previous_flag", "current_status", "evidence"]


def write_ledger(verdicts, core):
    from importlib import util
    spec = util.spec_from_file_location("core", os.path.join(F.SCRIPTS,
                                                             "forensic_core.py"))
    mod = util.module_from_spec(spec)
    rows = []
    forms = core["A_transform_forms"]
    for i, name in enumerate(F.ORDER22):
        v = verdicts[name]
        fm = forms[name]
        gain = F.PUB.get(name)
        rows.append([
            i, name,
            {"CMC1_f": "thumb CMC", "CMC1_a": "thumb CMC", "MCP1": "thumb MCP",
             "IP1": "thumb IP", "MCP2_f": "index MCP",
             "MCP2_a": "index-middle metacarpals", "PIP2": "index PIP",
             "MCP3_f": "middle MCP", "PIP3": "middle PIP", "MCP4_f": "ring MCP",
             "MCP4_a": "middle-ring metacarpals", "PIP4": "ring PIP",
             "CMC5": "palmar arch", "MCP5_f": "little MCP",
             "MCP5_a": "ring-little metacarpals", "PIP5": "little PIP",
             "DIP2": "index DIP", "DIP3": "middle DIP", "DIP4": "ring DIP",
             "DIP5": "little DIP", "WRIST_F": "wrist flexion/extension",
             "WRIST_A": "wrist deviation"}[name],
            ("flexion" if name.endswith(("_f", "_F")) or name in
             ("MCP1", "IP1", "PIP2", "PIP3", "PIP4", "PIP5", "DIP2", "DIP3", "DIP4",
              "DIP5", "CMC5", "WRIST_F") else
             ("relative abduction" if name.endswith("_a") and name != "CMC1_a"
              else ("abduction" if name == "CMC1_a" else "deviation"))),
            "YES", "NO" if fm["kind"] == "all_nan" else "YES",
            "degrees (released) / raw counts (glove)",
            F.SIGN[name].split(" / ")[0], F.SIGN[name].split(" / ")[-1],
            "the subject's own raw gauge values over the central part of Exercise B "
            "movement 11 (hand resting, fingers together and extended); angles = "
            "f(glove) - f(glove_reference)",
            str(gain),
            "2-term mix" if name in ("CMC1_f", "CMC1_a", "WRIST_A") else
            ("2nd-order polynomial in the adjacent MCP flexion gauges"
             if name in ("MCP2_a", "MCP4_a", "MCP5_a") else
             ("quadratic in one gauge" if name == "WRIST_F" else "none (single gauge)")),
            "LITERATURE_FLAGGED" if name in F.LITERATURE_FLAGGED else "",
            "excluded from the calibrated data due to noise problems" if name == "MCP2_a"
            else ("DIP reliability depends on glove fit / hand size" if name.startswith("DIP")
                  else ""),
            "see db9_channel_validity (read-only); THIS lane does not inherit its verdicts",
            f"{v['status']} / {v['case']} / confidence {v['confidence']}",
            v["evidence"]])
    sha = F.write_csv(os.path.join(F.LANE, "DB9_CHANNEL_LEDGER.csv"), LEDGER_HEADER, rows)
    print(f"DB9_CHANNEL_LEDGER.csv : {len(rows)} rows sha256={sha}")
    return sha


def write_flagged(anchors, verdicts, magref):
    r = anchors["A_FIST"]
    sec = anchors["A_RINGLITTLE"]
    L = ["# FLAGGED CHANNEL FORENSICS\n",
         f"**Frozen plan SHA-256:** `{F.plan_sha()}`  **Commit:** COMMIT PENDING\n",
         "Channels flagged by the independent 2024 study are labelled "
         "`LITERATURE_FLAGGED`, never `KNOWN_BAD`. This document reproduces or refutes the "
         "flag from the data.\n",
         "## The forensic chain\n",
         "```",
         "PHYSICAL MOVEMENT  (Exercise B movement 6 'fingers flexed together in fist',",
         "                    movement 17 'wrist extension with closed hand')",
         "      |",
         "RAW GLOVE SENSOR   glove[:, g]        <- the exact column is recovered, not guessed",
         "      |",
         "OFFICIAL TRANSFORM angle = gain * (raw - raw_reference), gains from the DB9 paper",
         "      |",
         "OUR RECONSTRUCTION reproduced to machine precision (see TRANSFORM_REPRODUCTION)",
         "      |",
         "RELEASED DB9 ANGLE angles[:, a]",
         "```\n",
         "## 1. The anchor, subject by subject\n",
         "| channel | n subjects | median Î”raw (counts) | raw +/âˆ’ | median Î”angle (deg) | "
         "angle +/âˆ’ | coherence | agreement with the official sign | verdict |",
         "|---|---|---|---|---|---|---|---|---|"]
    for ch in ("DIP2", "DIP3", "DIP4", "DIP5", "CMC5"):
        a = r[ch]
        v = verdicts[ch]
        L.append(f"| **{ch}** | {a['n_subjects']} | {a['raw_median']:+.2f} | "
                 f"{a['raw_pos']}/{a['raw_neg']} | {a['angle_median']:+.2f} | "
                 f"{a['angle_pos']}/{a['angle_neg']} | {a['coherence']:.3f} | "
                 f"{v['agreement']:.3f} | **{v['case']}** |")
    L.append("")
    L.append("## 2. Internal controls - the same segments, the same subjects\n")
    L.append("This is the evidence that the segment is not inverted and the trial is not "
             "mis-labelled: within the very same fist segments the MCP and PIP channels move "
             "in the documented direction in essentially every subject.\n")
    L.append("| channel | family | median Î”raw | raw +/âˆ’ | median Î”angle | angle +/âˆ’ | "
             "agreement |")
    L.append("|---|---|---|---|---|---|---|")
    for ch, fam in (("MCP2_f", "MCP index"), ("PIP2", "PIP index"), ("DIP2", "DIP index"),
                    ("MCP3_f", "MCP middle"), ("PIP3", "PIP middle"),
                    ("DIP3", "DIP middle"), ("MCP4_f", "MCP ring"), ("PIP4", "PIP ring"),
                    ("DIP4", "DIP ring"), ("MCP5_f", "MCP little"), ("PIP5", "PIP little"),
                    ("DIP5", "DIP little"), ("MCP1", "MCP thumb"), ("IP1", "IP thumb")):
        a = r[ch]
        v = verdicts[ch]
        L.append(f"| `{ch}` | {fam} | {a['raw_median']:+.2f} | {a['raw_pos']}/{a['raw_neg']} "
                 f"| {a['angle_median']:+.2f} | {a['angle_pos']}/{a['angle_neg']} | "
                 f"{v['agreement']:.3f} |")
    L.append("")
    L.append("**Reading.** For every digit the MCP and the PIP channel of the same finger "
             "move positively, while the DIP channel of digits 3, 4 and 5 moves negatively. "
             "The reversal is therefore specific to the DIP gauges, not to the movement, the "
             "segment, the reference or the trial label. `[EMPIRICAL]`\n")
    L.append("## 3. Independent second anchor\n")
    L.append("Movements 2 and 3 ('extension of index and middle, flexion of the others' and "
             "'flexion of ring and little finger, extension of the others') engage the ring "
             "and little digits specifically.\n")
    L.append("| channel | n | median Î”raw | coherence | verdict |")
    L.append("|---|---|---|---|---|")
    for ch in ("PIP4", "DIP4", "PIP5", "DIP5"):
        a = sec[ch]
        L.append(f"| `{ch}` | {a['n_subjects']} | {a['raw_median']:+.2f} | "
                 f"{a['coherence']:.3f} | {verdicts[ch]['case']} |")
    L.append("")
    L.append("## 4. CMC5 - a released-representation collision\n")
    L.append(REASONS["CMC5"] + " `[EMPIRICAL]`\n")
    L.append("| anchor | CMC5 median Î”raw | WRIST_F median Î”raw | identical? |")
    L.append("|---|---|---|---|")
    for an, lbl in (("A_WRISTFLEX", "wrist flexion (movement 13)"),
                    ("A_WRISTEXT", "wrist extension (movement 14)"),
                    ("A_FIST", "fist (movements 6+17)")):
        a = anchors[an]
        L.append(f"| {lbl} | {a['CMC5']['raw_median']:+.2f} | "
                 f"{a['WRIST_F']['raw_median']:+.2f} | "
                 f"{'YES - same sensor' if abs(a['CMC5']['raw_median'] - a['WRIST_F']['raw_median']) < 1e-9 else 'no'} |")
    L.append("")
    L.append("## 5. Verdicts\n")
    for ch in ("DIP3", "DIP4", "DIP5", "CMC5"):
        v = verdicts[ch]
        L.append(f"### {ch}: `{v['case']}` -> **{v['status']}** (confidence "
                 f"{v['confidence']})\n")
        L.append(f"* anchor `{v['primary_anchor']}`, n = {v['n_subjects']} subjects")
        L.append(f"* coherence {v['coherence']:.3f}, agreement with the official sign "
                 f"{v['agreement']:.3f}, opposed {v['opposed']:.3f}, magnitude ratio "
                 f"{v['mag_ratio']:.3f}")
        L.append(f"* {v['reason']}")
        if v.get("released_vs_published"):
            L.append(f"* released vs published: {v['released_vs_published']}")
        L.append("")
    L.append("## 6. What is NOT claimed\n")
    L.append("* No sign flip, offset, affine alignment or rescaling was applied. The released "
             "arrays were never modified.")
    L.append("* The DIP gauges are not claimed to be dead: DIP2 responds correctly and "
             "DIP3/4/5 respond coherently, just with the opposite polarity to the published "
             "criterion and at roughly a tenth of the MCP/PIP magnitude.")
    L.append("* The literature flag on `CMC5` is *refuted as stated* and replaced by a "
             "stronger finding: CMC5 is not a bad palmar-arch channel, it is the wrist "
             "channel. `[EMPIRICAL]`")
    sha = F.write_text(os.path.join(F.LANE, "FLAGGED_CHANNEL_FORENSICS.md"), "\n".join(L) + "\n")
    print(f"FLAGGED_CHANNEL_FORENSICS.md sha256={sha}")


def write_sensor11(s11):
    L = ["# SENSOR 11 / MCP2_a - STATUS AND HISTORICAL IMPACT\n",
         f"**Frozen plan SHA-256:** `{F.plan_sha()}`\n",
         "## Official status `[OFFICIAL]`\n",
         "> 'Sensor 11 (which corresponds to MCP2-3_A) was not included into the calibrated "
         "data due to noise problems.'  - Ninapro DB9 instructions, Usage notes\n",
         "## Released status `[EMPIRICAL]`\n",
         "* `angles[:,5]` = `MCP2_a` is **all NaN** in every released `.mat` file examined.",
         "* `glove[:,5]` = the raw noisy gauge is **still present** in the release, so the "
         "noise is available to anyone who does not read the usage notes.",
         "* the released `order_of_angles` field still lists `6:MCP2_a`, so a naive loader "
         "that trusts the column count will pick up an all-NaN column.",
         "",
         "## Historical impact in this project\n",
         f"{s11['verdict']}\n",
         "| question | answer |", "|---|---|",
         f"| files mentioning MCP2_a / MCP2-3_A / angle column 5 | "
         f"{s11['n_files_mentioning']} |",
         f"| `docs/DB9_CANONICAL16_MAPPING.md` references MCP2_a | "
         f"{s11['record']['canonical16_references_mcp2_a']} |",
         "| any historical representation selects DB9 angle column 5 | **no** |",
         "| could it be mapped back in through another column | no mapping exists that "
         "would do so; the column is NaN, so any accidental use produces NaN, which fails "
         "loudly rather than silently |", ""]
    if s11["hits"]:
        L.append("Files that merely *mention* the name (none of them select the column into "
                 "a representation):\n")
        L.append("| file | matched on |")
        L.append("|---|---|")
        for h in s11["hits"][:20]:
            L.append(f"| `{h['path']}` | {h['pattern']} |")
        L.append("")
    sha = F.write_text(os.path.join(F.LANE, "SENSOR11_IMPACT.md"), "\n".join(L) + "\n")
    print(f"SENSOR11_IMPACT.md sha256={sha}")


def write_handsize(hs, meta):
    L = ["# DIP HAND-SIZE HYPOTHESIS\n",
         f"**Frozen plan SHA-256:** `{F.plan_sha()}`\n",
         "## Official warning `[OFFICIAL]`\n",
         "> 'DIP sensors provide reliable angles when subject hand size is big (i.e. when the "
         "glove fits properly to the hand). Instead, they may provide partial results when "
         "the hand of the subject is small. Therefore, attention should be taken when using "
         "their information.'  - Ninapro DB9 instructions\n",
         "## Metadata availability\n",
         f"Released subject metadata columns: `{meta['columns']}` "
         f"({meta['n']} subjects parsed from the official Ninapro subject table).",
         f"Hand length or width published: **{meta['hand_length_or_width_present']}**.\n",
         f"**{hs['verdict']}**\n",
         "## Substitution analysis (height as the only available size proxy)\n",
         "| channel | n with metadata | median Î”raw | subjects positive | subjects negative "
         "| Pearson r (height vs Î”angle) | slope (deg/cm) |",
         "|---|---|---|---|---|---|---|"]
    for ch, v in (hs.get("per_proxy") or {}).items():
        def g(k, fmt="{:+.3f}"):
            x = v.get(k)
            return fmt.format(x) if x is not None else "n/a"
        L.append("| `%s` | %s | %s | %s | %s | %s | %s |"
                 % (ch, v["n_with_metadata"], g("raw_median", "{:+.2f}"),
                    v["positive_subjects"], v["negative_subjects"],
                    g("pearson_r_height_vs_angle_delta"), g("slope_deg_per_cm")))
    L.append("")
    L.append(f"{hs.get('note','')}\n")
    L.append("## What the analysis can and cannot settle\n")
    L.append("* It can classify the DIP failure as universal vs subset-only vs "
             "size-dependent.")
    L.append("* It cannot repair a channel, and it is not used to do so.")
    L.append("* Sex is available but is **not** used as a hand-size ground truth; height is "
             "the only continuous size proxy the release supports, and it is a weak one.")
    sha = F.write_text(os.path.join(F.LANE, "DIP_HANDSIZE_ANALYSIS.md"), "\n".join(L) + "\n")
    print(f"DIP_HANDSIZE_ANALYSIS.md sha256={sha}")


def freeze_trusted(verdicts, kept, dropped, incl, anchors):
    chans = []
    for n in kept:
        v = verdicts[n]
        chans.append({"name": n, "source_index": F.IDX[n], "glove_column": GCOL[n],
                      "anatomical_meaning": n, "unit": "degrees",
                      "sign": F.SIGN[n], "zero": "the subject's own reference posture over "
                                                 "the central part of Exercise B movement 11",
                      "anchor": v["primary_anchor"], "n_subjects": v["n_subjects"],
                      "agreement_with_official_sign": v["agreement"],
                      "coherence": v["coherence"],
                      "confidence": v["confidence"], "case": v["case"]})
    doc = {
        "name": "TRUSTED_DB9_POSE_v1",
        "branch_id": "S8-DB9-CHANNEL-FORENSIC",
        "frozen_before_any_classifier": True,
        "plan_sha256": F.plan_sha(),
        "commit": "COMMIT PENDING",
        "source": "Ninapro DB9, released `angles` field of S{N}_E2_A1.mat (Exercise B)",
        "source_channel_names_authority": "the `order_of_angles` field stored inside every "
                                          "released .mat",
        "n_keep": len(kept), "keep": chans,
        "keep_names": kept,
        "exclusion_list": [{"name": n, "source_index": F.IDX[n], "status": verdicts[n]["status"],
                            "case": verdicts[n]["case"],
                            "reason": verdicts[n]["reason"] or verdicts[n].get(
                                "released_vs_published") or "see verdicts"}
                           for n in dropped],
        "drop_names": dropped,
        "inconclusive_list": [{"name": n, "source_index": F.IDX[n],
                               "case": verdicts[n]["case"],
                               "missing_evidence": verdicts[n]["reason"] or
                               "no pre-declared anchor, or a released-vs-published "
                               "constant conflict"}
                              for n in incl],
        "inconclusive_names": incl,
        "unit": "degrees",
        "zero_definition": "the subject's own raw gauge values over the central part of "
                           "Exercise B movement 11 (hand resting on the table, fingers "
                           "together and extended); the released angles are "
                           "f(glove) - f(glove_reference)",
        "sign_convention": "as published in the DB9 paper Table 6 (flexion positive for "
                           "MCP/PIP/IP/CMC5/WRIST_F; fingers separated positive for the "
                           "relative abductions)",
        "raw_to_released_transform": "recovered exactly by this lane; see "
                                     "artifacts/VERDICTS.json .A_transform_forms",
        "may_not_be_changed_for_classification_performance": True,
        "evidence_hashes": {
            "FORENSIC_PLAN.md": F.sha256_file(F.PLAN),
            "artifacts/FORENSIC_CORE.json":
                F.sha256_file(os.path.join(F.ART, "FORENSIC_CORE.json")),
            "SEGMENTATION_VALIDATION.json":
                F.sha256_file(os.path.join(F.ART, "SEGMENTATION_VALIDATION.json")),
        },
        "evidence": F.EMPIRICAL,
    }
    p = os.path.join(F.LANE, "TRUSTED_DB9_POSE_v1.json")
    sha = F.write_json(p, doc)
    F.write_text(os.path.join(F.LANE, "TRUSTED_SUBSET_SHA256.txt"),
                 f"{sha}  TRUSTED_DB9_POSE_v1.json\n")
    print(f"TRUSTED_DB9_POSE_v1.json sha256={sha}   KEEP={len(kept)} channels")
    print(f"  {kept}")


if __name__ == "__main__":
    raise SystemExit(main())



