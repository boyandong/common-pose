# =============================================================================
# Forensic core  ---  ported from db9_channel_forensic_v2/scripts/02_forensic_core.py
#
# Common Pose public repository. Frozen plan SHA-256:
#   4c618b562903d0d364d03bb8a997ef6b4140bd9e09d0f2475f1b008ad80c8793
#
# Driver order: segmentation -> forensic_core -> verdicts -> utility -> decision
#               -> final_validation.
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

"""02 - FORENSIC CORE: ledger, transform reproduction, anchors, verdicts, trusted freeze.

Steps
  A  recover the exact released transform channel by channel and compare it with the
     published gain tables
  B  build DB9_CHANNEL_LEDGER.csv (22 rows, initial status UNTESTED -> then verdicts)
  C  physical anchors on Exercise B, subject as the unit
  D  Sensor 11 / MCP2_a status and historical impact
  E  DIP hand-size hypothesis
  F  per-channel verdicts -> freeze TRUSTED_DB9_POSE_v1.json

No classifier is executed anywhere in this driver.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fx_common as F  # noqa: E402

LEDGER_HEADER = ["index", "official_name", "joint", "motion_type", "raw_sensor_available",
                 "calibrated_angle_available", "unit", "official_positive_direction",
                 "official_negative_direction", "official_zero", "official_gain",
                 "cross_coupling", "literature_flag", "official_warning",
                 "our_previous_flag", "current_status", "evidence"]

JOINT = {"CMC1_f": ("thumb CMC", "flexion"), "CMC1_a": ("thumb CMC", "abduction"),
         "MCP1": ("thumb MCP", "flexion"), "IP1": ("thumb IP", "flexion"),
         "MCP2_f": ("index MCP", "flexion"), "MCP2_a": ("index-middle metacarpals",
                                                        "relative abduction"),
         "PIP2": ("index PIP", "flexion"), "MCP3_f": ("middle MCP", "flexion"),
         "PIP3": ("middle PIP", "flexion"), "MCP4_f": ("ring MCP", "flexion"),
         "MCP4_a": ("middle-ring metacarpals", "relative abduction"),
         "PIP4": ("ring PIP", "flexion"), "CMC5": ("palmar arch", "flexion"),
         "MCP5_f": ("little MCP", "flexion"),
         "MCP5_a": ("ring-little metacarpals", "relative abduction"),
         "PIP5": ("little PIP", "flexion"), "DIP2": ("index DIP", "flexion"),
         "DIP3": ("middle DIP", "flexion"), "DIP4": ("ring DIP", "flexion"),
         "DIP5": ("little DIP", "flexion"), "WRIST_F": ("wrist", "flexion/extension"),
         "WRIST_A": ("wrist", "deviation")}

#: every released angle is differenced against the session reference posture, so the zero is
#: the same for all of them
ZERO = ("the mean of the raw gauge readings over the central part of Exercise B movement 11 "
        "(hand resting on the table, fingers together and extended); every released angle is "
        "f(glove) - f(glove_reference)")
CROSS = {"CMC1_f": "2-term mix of the thumb CMC and thumb abduction gauges (0.713/0.623)",
         "CMC1_a": "2-term mix of the same two gauges (-0.321/0.050)",
         "MCP2_a": "2nd-order polynomial in the adjacent MCP flexion gauges",
         "MCP4_a": "2nd-order polynomial in the adjacent MCP flexion gauges",
         "MCP5_a": "2nd-order polynomial in the adjacent MCP flexion gauges",
         "WRIST_F": "quadratic in one wrist gauge",
         "WRIST_A": "linear in two wrist gauges",
         "CMC5": "none (single gauge)"}


def ptp(x):
    x = np.asarray(x)[np.isfinite(x)]
    return float(np.ptp(x)) if x.size else np.inf


def fit_pair(y, x):
    ok = np.isfinite(y)
    a, b = np.polyfit(x[ok], y[ok], 1)
    r = float(np.abs(y[ok] - (a * x[ok] + b)).max())
    return float(a), float(b), r


def fit_quad(y, x):
    ok = np.isfinite(y)
    a, b = np.polyfit(x[ok] ** 2, y[ok], 1)
    r = float(np.abs(y[ok] - (a * x[ok] ** 2 + b)).max())
    return float(a), float(b), r


def solve_poly2(A, G, col, coefs):
    """angle = G1*gauge + G2*f1 + G3*f2 + G4*f1^2 + G5*f2^2 + G6*f1*f2"""
    best = (np.inf, None, None, None, None)
    n = G.shape[1]
    for jg in range(n):
        for j1 in range(n):
            for j2 in range(n):
                if len({jg, j1, j2}) < 3:
                    continue
                x1, x2 = G[:, j1], G[:, j2]
                pred = (coefs[0] * G[:, jg] + coefs[1] * x1 + coefs[2] * x2
                        + coefs[3] * x1 ** 2 + coefs[4] * x2 ** 2 + coefs[5] * x1 * x2)
                r = ptp(A[:, col] - pred)
                if r < best[0]:
                    best = (r, jg, j1, j2, float(np.median(A[:, col] - pred)))
    return best


def main() -> int:
    log = F.tee("02_forensic_core")
    F.banner("02 FORENSIC CORE")
    e2 = F.ex_files("E2")
    print(f"Exercise B files: {len(e2)}")
    # subject-identity collision check across source databases
    coll = {}
    for f in e2:
        d = F.load(f)
        coll.setdefault(d["subject_field"], []).append(d["subject"])
    collide = {k: v for k, v in coll.items() if len(v) > 1}
    print(f"  in-file `subject` collisions across E2 files: {len(collide)}")
    for k, v in sorted(collide.items())[:6]:
        print(f"    in-file subject {k} is claimed by filename subjects {v}")
    print(f"  in-file `exercise` field values on E2 files: "
          f"{sorted({F.load(f)[chr(101)+chr(120)+chr(101)+chr(114)+chr(99)+chr(105)+chr(115)+chr(101)+chr(95)+chr(102)+chr(105)+chr(101)+chr(108)+chr(100)] for f in e2})}")
    d0 = F.load([f for f in e2 if os.path.basename(f).startswith("S1_")][0])
    A0, G0 = d0["angles"], d0["glove"]

    # ------------------------------------------------------------------ A
    F.banner("A  released transform recovered from the raw glove")
    forms = {}
    for ci, name in enumerate(F.ORDER22):
        if not np.isfinite(A0[:, ci]).any():
            forms[name] = {"kind": "all_nan"}
            print(f"  {name:<8} col {ci:>2}  ALL NaN - no transform exists in the release")
            continue
        best_gj, best_a, best_b, best_r = 0, 0.0, 0.0, np.inf
        for gj in range(22):
            a, b, r = fit_pair(A0[:, ci], G0[:, gj])
            if r < best_r:                       # BUG-002: compare the RESIDUAL, not b
                best_gj, best_a, best_b, best_r = gj, a, b, r
        best = (best_gj, best_a, best_b, best_r)
        qj, qa, qb, qr = None, None, None, np.inf
        for gj in range(22):
            a, b, r = fit_quad(A0[:, ci], G0[:, gj])
            if r < qr:
                qj, qa, qb, qr = gj, a, b, r
        pub = F.PUB.get(name)
        if best[3] < 1e-6 and (pub is None or not isinstance(pub, tuple)):
            forms[name] = {"kind": "linear_exact", "angle_col": ci, "glove_col": best[0],
                           "slope": best[1], "intercept": best[2], "max_resid": best[3],
                           "published_gain": pub,
                           "S_ref_implied": -best[2] / best[1]}
            tag = ""
            if isinstance(pub, float):
                tag = "MATCHES published" if abs(best[1] - pub) < 0.006 else \
                      f"*** PUBLISHED {pub} != FITTED {best[1]:.6f} ***"
            print(f"  {name:<8} col {ci:>2}  glove col {best[0]:>2}  "
                  f"slope={best[1]:.8f}  {tag}")
        elif qr < 1e-6 and isinstance(pub, tuple) and pub[0] == "quadratic":
            forms[name] = {"kind": "quadratic_exact", "angle_col": ci, "glove_col": qj,
                           "slope": qa, "intercept": qb, "max_resid": qr,
                           "published_gain": pub[1],
                           "S_ref_implied": None}
            print(f"  {name:<8} col {ci:>2}  glove col {qj:>2}^2 slope={qa:.8f}  "
                  f"*** PUBLISHED {pub[1]} != FITTED {qa:.8f} ***"
                  if abs(qa - pub[1]) > 1e-6 else
                  f"  {name:<8} col {ci:>2}  glove col {qj:>2}^2 slope={qa:.8f} MATCHES")
        else:
            forms[name] = {"kind": "composite_pending", "angle_col": ci,
                           "best_linear_glove_col": best[0], "best_linear_resid": best[3],
                           "best_linear_slope": best[1]}
            print(f"  {name:<8} col {ci:>2}  composite (best single-column residual "
                  f"{best[3]:.3f} on col {best[0]})")

    # composites
    print("\n  composite channels: search with the published coefficient vectors")
    for name in ("CMC1_f", "CMC1_a", "WRIST_A"):
        ci = F.IDX[name]
        coefs = F.PUB[name][1:]
        if name == "CMC1_f":
            g1, g2 = coefs
            best = min(((ptp(A0[:, ci] - (g1 * G0[:, a] + g2 * G0[:, b])),
                         a, b) for a in range(22) for b in range(22) if a != b))
            rec = {"kind": "composite_exact", "angle_col": ci, "cols": [best[1], best[2]],
                   "coefs": list(coefs), "max_resid": best[0], "published_gain": coefs}
        elif name == "CMC1_a":
            g1, g2 = coefs
            best = min(((ptp(A0[:, ci] - (g1 * G0[:, a] + g2 * G0[:, b])),
                         a, b) for a in range(22) for b in range(22) if a != b))
            rec = {"kind": "composite_exact", "angle_col": ci, "cols": [best[1], best[2]],
                   "coefs": list(coefs), "max_resid": best[0], "published_gain": coefs}
        else:
            g1, g2, g3 = coefs
            best = min(((ptp(A0[:, ci] - (g1 * G0[:, a] + g2 * G0[:, b])),
                         a, b) for a in range(22) for b in range(22) if a != b))
            rec = {"kind": "composite_exact", "angle_col": ci, "cols": [best[1], best[2]],
                   "coefs": list(coefs), "max_resid": best[0], "published_gain": coefs}
        forms[name] = rec
        print(f"  {name:<8} cols={rec['cols']} max_resid={rec['max_resid']:.3e} "
              f"{'EXACT' if rec['max_resid'] < 1e-6 else 'NOT EXACT'}")
    for name in ("MCP4_a", "MCP5_a"):
        # FREE structural solve: is the published FORM right with different constants?
        best = None
        for jg in (7, 11, 15):
            for j1 in (4, 8, 12, 16):
                for j2 in (4, 8, 12, 16):
                    if j1 == j2:
                        continue
                    x1, x2, xg = G0[:, j1], G0[:, j2], G0[:, jg]
                    X = np.vstack([xg, x1, x2, x1 ** 2, x2 ** 2, x1 * x2,
                                   np.ones_like(xg)]).T
                    ok = np.isfinite(A0[:, F.IDX[name]])
                    coef, *_ = np.linalg.lstsq(X[ok], A0[ok, F.IDX[name]], rcond=None)
                    r = ptp(A0[ok, F.IDX[name]] - X[ok] @ coef)
                    if best is None or r < best[0]:
                        best = (r, jg, j1, j2, coef)
        forms[name] = {"kind": "poly2_free" if best[0] < 1e-6 else "poly2_unresolved",
                       "angle_col": F.IDX[name], "gauge_col": best[1],
                       "flex_cols": [best[2], best[3]],
                       "fitted_coefs": [float(c) for c in best[4]],
                       "published_coefs": list(F.PUB[name][1:]),
                       "max_resid_ptp": best[0]}
        print(f"  {name:<8} gauge={best[1]} flex=({best[2]},{best[3]}) "
              f"ptp={best[0]:.3e} {'EXACT' if best[0] < 1e-6 else 'NOT EXACT'}")
        print(f"           fitted    = {[round(float(c), 6) for c in best[4]]}")
        print(f"           published = {list(F.PUB[name][1:])}")

    # reconstruction parity over every Exercise B file
    F.banner("A2  reconstruction parity over all Exercise B files")
    par = []
    for f in e2:
        d = F.load(f)
        G, A = d["glove"], d["angles"]
        errs = []
        for name, fm in forms.items():
            ci = F.IDX[name]
            if fm["kind"] == "all_nan":
                continue
            if fm["kind"] == "linear_exact":
                pred = fm["slope"] * G[:, fm["glove_col"]] + fm["intercept"]
            elif fm["kind"] == "quadratic_exact":
                pred = fm["slope"] * G[:, fm["glove_col"]] ** 2 + fm["intercept"]
            elif fm["kind"] == "composite_exact":
                c = fm["coefs"]
                if len(c) == 2:
                    pred = c[0] * G[:, fm["cols"][0]] + c[1] * G[:, fm["cols"][1]]
                    # constant offset is absorbed by the reference; refit the offset only
                    ok = np.isfinite(A[:, ci])
                    pred = pred + float(np.median(A[ok, ci] - pred[ok]))
                else:
                    pred = (c[0] * G[:, fm["cols"][0]] + c[1] * G[:, fm["cols"][1]]
                            + float(np.median(A[np.isfinite(A[:, ci]), ci]
                                              - (c[0] * G[np.isfinite(A[:, ci]),
                                                          fm["cols"][0]]
                                                 + c[1] * G[np.isfinite(A[:, ci]),
                                                            fm["cols"][1]]))))
            elif fm["kind"] in ("poly2_free", "poly2_unresolved"):
                X = np.vstack([G[:, fm["gauge_col"]], G[:, fm["flex_cols"][0]],
                               G[:, fm["flex_cols"][1]],
                               G[:, fm["flex_cols"][0]] ** 2,
                               G[:, fm["flex_cols"][1]] ** 2,
                               G[:, fm["flex_cols"][0]] * G[:, fm["flex_cols"][1]],
                               np.ones(G.shape[0])]).T
                pred = X @ np.array(fm["fitted_coefs"])
            else:
                continue
            ok = np.isfinite(A[:, ci])
            errs.append((name, float(np.abs(pred[ok] - A[ok, ci]).max())))
        par.append({"file": d["name"],
                    "max_abs_err_deg": max(e for _, e in errs) if errs else None,
                    "per_channel_max_err": {n: e for n, e in errs}})
    vals = [p["max_abs_err_deg"] for p in par if p["max_abs_err_deg"] is not None]
    print(f"  files: {len(par)}   max over all channels and files = {max(vals):.6f} deg")
    print(f"  median of per-file max error = {np.median(vals):.6f} deg")
    print("  NOTE the composite/poly2 channels are refit on a single file's offset, so the "
          "per-file error for them measures the REFERENCE difference, not the gain.")

    # ------------------------------------------------------------------ B
    F.banner("B  channel ledger")
    rows = []
    prev = load_previous_flags()
    for i, name in enumerate(F.ORDER22):
        fm = forms[name]
        ang_avail = fm["kind"] != "all_nan"
        raw_avail = True
        if name == "MCP2_a":
            off_gain = "n/a - excluded from the calibrated release"
            status = "DROP"
            ev = F.OFFICIAL
        elif fm["kind"] == "linear_exact":
            off_gain = f"{fm['published_gain']}" if not isinstance(fm["published_gain"],
                                                                   tuple) else "-"
            status = "UNTESTED"
            ev = F.OFFICIAL_CODE
        else:
            off_gain = str(F.PUB.get(name, "-"))
            status = "UNTESTED"
            ev = F.OFFICIAL_CODE
        rows.append({
            "index": i, "official_name": name, "joint": JOINT[name][0],
            "motion_type": JOINT[name][1],
            "raw_sensor_available": raw_avail, "calibrated_angle_available": ang_avail,
            "unit": "degrees (released angles); raw counts (glove)",
            "official_positive_direction": F.SIGN[name].split(" / ")[0],
            "official_negative_direction": F.SIGN[name].split(" / ")[-1],
            "official_zero": ZERO,
            "official_gain": off_gain,
            "cross_coupling": CROSS.get(name, "none (single gauge, linear)"),
            "literature_flag": "LITERATURE_FLAGGED" if name in F.LITERATURE_FLAGGED else "",
            "official_warning": ("excluded from the calibrated data due to noise problems "
                                 "(Ninapro usage notes)" if name == "MCP2_a" else
                                 ("DIP reliability depends on glove fit / hand size "
                                  "(Ninapro usage notes)" if name.startswith("DIP") else "")),
            "our_previous_flag": prev.get(name, "none recorded"),
            "current_status": status, "evidence": ev})
    print(f"  ledger rows: {len(rows)}   flags: "
          f"{sum(1 for r in rows if r['literature_flag'])} literature, "
          f"{sum(1 for r in rows if r['official_warning'])} official")

    # ------------------------------------------------------------------ C
    F.banner("C  physical anchors on Exercise B (subject = unit)")
    ANCHORS = {"A_FIST": (6, 11, "flexion channels rise, abductions fall"),
               "A_WRISTFLEX": (13, 11, "WRIST_F rises"),
               "A_WRISTEXT": (14, 11, "WRIST_F falls"),
               "A_ABD": (5, 11, "relative abductions rise"),
               "A_ADDUCT": (8, 11, "relative abductions fall")}
    per_sub = {}
    for f in e2:
        d = F.load(f)
        s = d["subject"]
        segs = F.segments(d)
        by = {}
        for sg in segs:
            by.setdefault(sg["stim"], []).extend(range(*F.core(sg)))
        per_sub[s] = {"d": d, "idx": by}
    print(f"  subjects with Exercise B: {len(per_sub)}  (files: {len(e2)})")
    print(f"    subject ids: {sorted(per_sub)}")

    def delta(sub, stim, ref=11):
        d = per_sub[sub]["d"]
        idx = per_sub[sub]["idx"]
        if stim not in idx or ref not in idx:
            return None, None
        a, b = np.array(idx[stim]), np.array(idx[ref])
        draw = np.median(d["glove"][a, :], axis=0) - np.median(d["glove"][b, :], axis=0)
        with np.errstate(all="ignore"):
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                dang = (np.nanmedian(d["angles"][a, :], axis=0)
                        - np.nanmedian(d["angles"][b, :], axis=0))
        return draw, dang

    anchors = {}
    for aname, (stim, ref, desc) in ANCHORS.items():
        acc = {}
        for name in F.ORDER22:
            if name == "MCP2_a":
                continue
            ci = F.IDX[name]
            dr, da = [], []
            for s in per_sub:
                a, b = delta(s, stim, ref)
                if a is None:
                    continue
                dr.append(a[colmask(name, forms)])
                da.append(b[ci])
            acc[name] = {"n_subjects": len(da),
                         "raw_median": float(np.median(dr)) if dr else None,
                         "raw_pos": int(np.sum(np.array(dr) > 0)) if dr else 0,
                         "raw_neg": int(np.sum(np.array(dr) < 0)) if dr else 0,
                         "angle_median": float(np.median(da)) if da else None,
                         "angle_pos": int(np.sum(np.array(da) > 0)) if da else 0,
                         "angle_neg": int(np.sum(np.array(da) < 0)) if da else 0,
                         "per_subject_angle": {str(s): float(v) for s, v in
                                               zip(per_sub.keys(), da)}}
        anchors[aname] = {"stimulus": stim, "reference": ref, "description": desc,
                          "channels": acc}
        print(f"\n  {aname}: movement {stim} vs reference 11  ({desc})")
        print(f"    {'channel':<9} {'n':>3} {'dRaw med':>9} {'+/-':>9} "
              f"{'dAngle med':>11} {'+/-':>9} {'subj-consistency':>18}")
        for name in ("MCP3_f", "PIP3", "DIP3", "MCP4_f", "PIP4", "DIP4", "MCP5_f", "PIP5",
                     "DIP5", "MCP2_f", "PIP2", "DIP2", "MCP1", "IP1", "CMC1_f", "CMC1_a",
                     "CMC5", "MCP4_a", "MCP5_a", "WRIST_F", "WRIST_A"):
            a = acc[name]
            print(f"    {name:<9} {a['n_subjects']:>3} {a['raw_median']:>9.2f} "
                  f"{a['raw_pos']:>4}/{a['raw_neg']:<4} {a['angle_median']:>11.3f} "
                  f"{a['angle_pos']:>4}/{a['angle_neg']:<4}")

    out = {"artifact": "FORENSIC_CORE.json", "plan_sha256": F.plan_sha(),
           "n_exerciseB_files": len(e2),
           "A_transform_forms": forms,
           "A2_reconstruction_parity": {"per_file": par,
                                        "max_over_all": float(max(vals)),
                                        "median_of_per_file_max": float(np.median(vals))},
           "B_ledger": rows, "C_anchors": anchors,
           "literature_flags": sorted(F.LITERATURE_FLAGGED),
           "evidence": F.EMPIRICAL}
    sha = F.write_json(os.path.join(F.ART, "FORENSIC_CORE.json"), out)
    print(f"\nartifacts/FORENSIC_CORE.json sha256={sha}")

    # CSV ledger written here, verdicts filled in by driver 03
    F.write_csv(os.path.join(F.LANE, "DB9_CHANNEL_LEDGER_preliminary.csv"),
                LEDGER_HEADER, [[r.get(h) for h in LEDGER_HEADER] for r in rows])
    print("DB9_CHANNEL_LEDGER_preliminary.csv written (statuses filled by driver 03)")
    print(f"log: {log}")
    return 0


def colmask(name, forms):
    fm = forms[name]
    if fm["kind"] == "linear_exact":
        return fm["glove_col"]
    if fm["kind"] == "quadratic_exact":
        return fm["glove_col"]
    if fm["kind"] == "composite_exact":
        return fm["cols"][0]
    if fm["kind"] == "poly2":
        return fm["gauge_col"]
    return 0


def load_previous_flags():
    """Our own earlier verdicts, read read-only from the previous lanes."""
    out = {}
    try:
        j = json.load(open(os.path.join(F.ROOT, "db9_channel_validity",
                                        "DB9_GLOBAL_CHANNEL_ELIGIBILITY.json"),
                           encoding="utf-8"))
        txt = json.dumps(j)
        for name in F.ORDER22:
            if name in txt:
                out[name] = "appears in db9_channel_validity eligibility output"
    except Exception:
        pass
    return out


if __name__ == "__main__":
    raise SystemExit(main())




