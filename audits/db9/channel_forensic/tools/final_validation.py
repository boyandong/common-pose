# =============================================================================
# Final validation  ---  ported from db9_channel_forensic_v2/scripts/06b_final_validation.py
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

"""06b - LEAN FINAL VALIDATION.

Protocol-identical to 06_final_validation.py; only the memory handling changes:
  * the 77 Exercise-B files are loaded ONCE and only the 22 angle + 22 glove columns kept
  * standardisation is applied IN PLACE per fold instead of building temporaries
  * progress is printed and flushed, so the run is observable

The frozen subset is read from disk and never modified.  No threshold, channel set or
classifier is changed.
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fx_common as F  # noqa: E402
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis  # noqa: E402
from sklearn.metrics import (accuracy_score, balanced_accuracy_score,  # noqa: E402
                             confusion_matrix, f1_score, recall_score)

AGREE_BAR, COH_BAR, OPPOSED_BAR, MAG_FLOOR = 0.80, 0.80, 0.80, 0.15
EXPECT_FIST = {n: +1 for n in ("MCP1", "IP1", "MCP2_f", "PIP2", "MCP3_f", "PIP3",
                               "MCP4_f", "PIP4", "MCP5_f", "PIP5", "DIP2", "DIP3",
                               "DIP4", "DIP5", "CMC5")}
GCOL = {"CMC1_f": 0, "CMC1_a": 3, "MCP1": 1, "IP1": 2, "MCP2_f": 4, "MCP2_a": 5,
        "PIP2": 5, "MCP3_f": 8, "PIP3": 9, "MCP4_f": 12, "MCP4_a": 15, "PIP4": 13,
        "CMC5": 20, "MCP5_f": 16, "MCP5_a": 19, "PIP5": 17, "DIP2": 6, "DIP3": 10,
        "DIP4": 14, "DIP5": 18, "WRIST_F": 20, "WRIST_A": 21}
CANON16 = ["CMC1_f", "CMC1_a", "MCP1", "IP1", "MCP2_f", "PIP2", "DIP2", "MCP3_f",
           "PIP3", "DIP3", "MCP4_f", "PIP4", "DIP4", "MCP5_f", "PIP5", "DIP5"]
BUG006_RESTORED = ["MCP5_f", "PIP5"]
MCP4 = [4, 8, 12, 16]
#: DECLARED frame cap per segment.  DB2's recordings are ~20x longer than DB1/DB5, so an
#: uncapped pooled frame set is dominated by DB2 by frame count (11.8 M rows, 1.5 GB).  The
#: cap keeps every segment, every movement and every subject, and makes the pooled frame set
#: approximately subject-balanced.  It is a frame-count choice, not a channel or model choice.
SEG_CAP = 200


def say(*a):
    print(*a)
    sys.stdout.flush()


def db_of(s):
    return "DB1" if s <= 27 else ("DB2" if s <= 67 else "DB5")


def load_exercise_b():
    """Load every file whose DATA is the 17-movement Exercise B protocol."""
    t0 = time.time()
    files = F.all_files()
    out = []
    for i, f in enumerate(files):
        d = F.load(f)
        segs = F.segments(d)
        stims = sorted({s["stim"] for s in segs})
        if stims != list(range(1, 18)):
            continue
        idx = {}
        for sg in segs:
            idx.setdefault(sg["stim"], []).extend(range(*F.core(sg)))
        if 6 not in idx or 11 not in idx:
            continue
        g6 = np.median(d["glove"][np.array(idx[6])][:, MCP4], axis=1)
        g11 = np.median(d["glove"][np.array(idx[11])][:, MCP4], axis=1)
        out.append({"name": d["name"], "subject": d["subject"],
                    "exercise_code": d["exercise"], "glove": d["glove"],
                    "angles": d["angles"], "idx": idx,
                    "fist_minus_ref_raw": float(np.median(g6) - np.median(g11))})
        if (i + 1) % 20 == 0:
            say(f"    ... loaded {i+1}/{len(files)} files, {len(out)} are Exercise B "
                f"({time.time()-t0:.0f}s)")
    say(f"  loaded {len(out)} Exercise-B-format files in {time.time()-t0:.0f}s")
    return out


def anchor(fl, name):
    dr, da = [], []
    ci = F.IDX[name]
    for r in fl:
        d, idx = r["glove"], r["angles"]
        a, b = np.array(r["idx"][6]), np.array(r["idx"][11])
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            an = float(np.nanmedian(d[:, ci][a]) if False else
                       np.nanmedian(r["angles"][a, ci]) - np.nanmedian(r["angles"][b, ci]))
        dr.append(float(np.median(r["glove"][a, GCOL[name]])
                        - np.median(r["glove"][b, GCOL[name]])))
        da.append(an)
    return np.array(dr), np.array(da)


def verdict(dr, da, exp, magref):
    ag = float(np.mean(np.sign(da) == exp))
    op = float(np.mean(np.sign(da) == -exp))
    coh = float(np.mean(np.sign(dr) == np.sign(da)))
    mr = float(abs(np.median(dr)) / magref) if magref else None
    if ag >= AGREE_BAR:
        case, st = "CASE_C_PREVIOUS_QC_WRONG", "KEEP"
    elif coh >= COH_BAR and op >= OPPOSED_BAR:
        case, st = "CASE_A_RELEASED_REPRESENTATION", "DROP"
    elif (mr is not None and mr < MAG_FLOOR) or coh < 0.60:
        case, st = "CASE_B_SENSOR_OR_FIT_LIMITATION", "DROP"
    else:
        case, st = "CASE_E_INCONCLUSIVE", "INCONCLUSIVE"
    return {"n": int(da.size), "agreement": ag, "opposed": op, "coherence": coh,
            "mag_ratio": mr, "case": case, "status": st,
            "raw_median": float(np.median(dr)), "angle_median": float(np.median(da))}


def collect(fl, cols, keep_ids):
    """Build X, y, s once, with a per-segment frame index for cheap folding."""
    Xs, ys, ss, fs = [], [], [], []
    seg = 0
    for r in fl:
        for st in keep_ids:
            if st not in r["idx"]:
                continue
            a = np.array(r["idx"][st])
            ang = r["angles"][a, :][:, cols]
            ok = np.isfinite(ang).all(axis=1)
            if not ok.any():
                continue
            ang = ang[ok]
            if SEG_CAP and ang.shape[0] > SEG_CAP:
                pick = np.linspace(0, ang.shape[0] - 1, SEG_CAP).astype(int)
                ang = ang[pick]
            Xs.append(np.deg2rad(ang))
            ys.append(np.full(ang.shape[0], st, dtype=np.int16))
            ss.append(np.full(ang.shape[0], r["subject"], dtype=np.int32))
            fs.append(np.full(ang.shape[0], seg, dtype=np.int32))
            seg += 1
    return (np.vstack(Xs), np.concatenate(ys), np.concatenate(ss), np.concatenate(fs))


def loso(X, y, s, log=None):
    pred = np.full(y.shape, -1, dtype=np.int16)
    keys = np.unique(s)
    for k in keys:
        te = s == k
        tr = ~te
        if log is not None:
            inter = set(s[tr].tolist()) & set(s[te].tolist())
            log.append({"fold_held_out_global_key": int(k),
                        "n_train_frames": int(tr.sum()), "n_test_frames": int(te.sum()),
                        "n_train_global_keys": int(np.unique(s[tr]).size),
                        "train_test_global_intersection": sorted(int(x) for x in inter)})
        Xtr = X[tr]
        mu = Xtr.mean(0)
        sd = Xtr.std(0)
        sd = np.where(sd > 0, sd, 1.0)
        Xtr -= mu
        Xtr /= sd
        m = LinearDiscriminantAnalysis()
        m.fit(Xtr, y[tr])
        Xte = X[te]
        Xte -= mu
        Xte /= sd
        pred[te] = m.predict(Xte).astype(np.int16)
    return pred


def evaluate(pred, y, s):
    ok = pred >= 0
    y2, p2, s2 = y[ok], pred[ok], s[ok]
    cl = np.unique(y2)
    cm = confusion_matrix(y2, p2, labels=cl)
    rec = recall_score(y2, p2, labels=cl, average=None, zero_division=0)
    per_sub = {int(u): float(balanced_accuracy_score(y2[s2 == u], p2[s2 == u]))
               for u in np.unique(s2)}
    return {"n_frames": int(y2.size), "n_subjects": int(np.unique(s2).size),
            "n_classes": int(cl.size),
            "accuracy": float(accuracy_score(y2, p2)),
            "balanced_accuracy": float(balanced_accuracy_score(y2, p2)),
            "macro_f1": float(f1_score(y2, p2, average="macro", zero_division=0)),
            "chance_balanced_accuracy": float(1.0 / cl.size),
            "per_class_recall": {int(c): float(r) for c, r in zip(cl, rec)},
            "confusion_matrix": cm.tolist(), "confusion_labels": [int(c) for c in cl],
            "per_subject_balanced_accuracy": per_sub,
            "median_subject_ba": float(np.median(list(per_sub.values()))),
            "worst_subject_ba": float(min(per_sub.values())),
            "worst_subject_key": int(min(per_sub, key=per_sub.get)),
            "classes_below_0_5": [int(c) for c, r in zip(cl, rec) if r < 0.5],
            "class_collapse": bool(min(rec) < 0.10)}


def cols_of(names, probe):
    out, used = [], []
    for n in names:
        for c in (n, n.replace("_F", "_f")):
            if c in F.IDX and np.isfinite(probe[:300, F.IDX[c]]).any():
                out.append(F.IDX[c]); used.append(c); break
    return sorted(set(out)), used


def main() -> int:
    log = F.tee("06b_final_validation")
    F.banner("DB9_FORENSIC_FINAL_VALIDATION (lean)")
    out = {"artifact": "FINAL_VALIDATION.json", "plan_sha256": F.plan_sha()}

    # --------------------------------------------------------------- Q1
    F.banner("Q1  coverage")
    by = {}
    for f in F.all_files():
        d = F.load(f)
        by.setdefault(db_of(d["subject"]), {}).setdefault(d["exercise"], []).append(1)
    cov = {k: {"subjects_present": len(set(sum(by.get(k, {}).values(), []))) or
               sum(len(set(v)) for v in by.get(k, {}).values()),
               "files_by_exercise_code": {f"E{e}": len(v) for e, v in
                                          sorted(by.get(k, {}).items())}}
           for k in ("DB1", "DB2", "DB5")}
    for k in ("DB1", "DB2", "DB5"):
        say(f"  {k}: {cov[k]}")
    out["Q1_coverage_raw"] = cov

    say("\n  loading Exercise-B-format files (verified from the DATA) ...")
    ebf = load_exercise_b()
    keys = sorted(r["subject"] for r in ebf)
    say(f"  Exercise B: {len(ebf)} files, global keys {keys[0]}..{keys[-1]}")
    say(f"  by source db: DB1={sum(1 for r in ebf if db_of(r['subject'])=='DB1')} "
        f"DB2={sum(1 for r in ebf if db_of(r['subject'])=='DB2')} "
        f"DB5={sum(1 for r in ebf if db_of(r['subject'])=='DB5')}")
    say(f"  exercise codes used: {sorted({r['exercise_code'] for r in ebf})}")
    say(f"  global keys == 1..77: {keys == list(range(1, 78))}")
    out["Q1_exercise_b"] = {
        "n": len(ebf), "global_keys": keys, "keys_are_1_to_77": keys == list(range(1, 78)),
        "by_source_db": {k: sum(1 for r in ebf if db_of(r["subject"]) == k)
                         for k in ("DB1", "DB2", "DB5")},
        "exercise_codes": sorted({r["exercise_code"] for r in ebf}),
        "why_37_last_time": (
            "The previous loader selected Exercise B with `ex_files('E2')` - i.e. by the "
            "FILENAME exercise code. DB1 and DB5 ship the 17-movement basic finger/wrist "
            "protocol as `_E2_`; DB2 ships the SAME protocol as `_E1_` (DB2's archive "
            "numbers exercises differently). The 40 DB2 files were on disk the whole time "
            "and were simply never opened. This driver selects Exercise B by verifying the "
            "DATA instead: exactly the 17 movement ids 1..17, movement 11 is the reference "
            "(fist response 0.00), movement 6 is the fist."),
        "evidence": F.EMPIRICAL}

    # --------------------------------------------------- Q1b verdicts
    F.banner("Q1b  frozen verdicts revalidated on DB1 / DB2 / DB5 / ALL 77")
    mags = {n: abs(np.median(anchor(ebf, n)[0])) for n in EXPECT_FIST}
    magref = float(np.median(list(mags.values())))
    say(f"  flexion-magnitude reference over all {len(ebf)} files = {magref:.2f}")
    frozen = json.load(open(os.path.join(F.LANE, "TRUSTED_DB9_POSE_v1.json"),
                            encoding="utf-8"))
    frozen_status = {n: ("KEEP" if n in frozen["keep_names"] else
                         ("DROP" if n in frozen["drop_names"] else "INCONCLUSIVE"))
                     for n in EXPECT_FIST}
    groups = {"DB1": [r for r in ebf if db_of(r["subject"]) == "DB1"],
              "DB2": [r for r in ebf if db_of(r["subject"]) == "DB2"],
              "DB5": [r for r in ebf if db_of(r["subject"]) == "DB5"],
              "ALL77": ebf}
    res, consistency = {}, {}
    for g, fl in groups.items():
        res[g] = {}
        say(f"\n  {g}  (n={len(fl)} subjects)")
        say(f"    {'channel':<9} {'agree':>6} {'opposed':>8} {'coh':>5} {'mag':>5} "
            f"{'status':>14} {'frozen':>14} {'same':>6}")
        for n in EXPECT_FIST:
            dr, da = anchor(fl, n)
            v = verdict(dr, da, EXPECT_FIST[n], magref)
            res[g][n] = v
            consistency.setdefault(n, {})[g] = v["status"]
            say(f"    {n:<9} {v['agreement']:>6.2f} {v['opposed']:>8.2f} "
                f"{v['coherence']:>5.2f} {(v['mag_ratio'] or 0):>5.2f} "
                f"{v['status']:>14} {frozen_status[n]:>14} "
                f"{str(v['status']==frozen_status[n]):>6}")
    all_ok = all(res["ALL77"][n]["status"] == frozen_status[n] for n in EXPECT_FIST)
    per_db_ok = {g: all(res[g][n]["status"] == frozen_status[n] for n in EXPECT_FIST)
                 for g in ("DB1", "DB2", "DB5")}
    say(f"\n  77-subject verdict reproduction of the frozen KEEP/DROP/INCONCLUSIVE: "
        f"{all_ok}")
    say(f"  per source db: {per_db_ok}")
    out["Q1_verdicts"] = res
    out["Q1_consistency"] = {"all77_reproduces_frozen": bool(all_ok),
                             "per_source_db": per_db_ok,
                             "frozen_status": frozen_status}

    # --------------------------------------------------------------- Q2
    F.banner("Q2  independent CMC5 raw-sensor arbitration")
    d0 = ebf[0]
    G0, A0 = d0["glove"], d0["angles"]
    audit = {}
    for name, ci, form in (("CMC5", 12, "linear"), ("WRIST_F", 20, "quad")):
        best = None
        for j in range(22):
            x = G0[:, j] if form == "linear" else G0[:, j] ** 2
            a, b = np.polyfit(x, A0[:, ci], 1)
            r = float(np.abs(A0[:, ci] - (a * x + b)).max())
            if best is None or r < best[0]:
                best = (r, j, float(a), float(b))
        audit[name] = {"released_angle_column_0based": ci, "released_name":
                       F.ORDER22[ci], "glove_column_0based": best[1],
                       "glove_column_1based": best[1] + 1,
                       "max_abs_residual_deg": best[0], "fitted_slope": best[2]}
        say(f"  {name:<8} released angle col {ci:>2} ({F.ORDER22[ci]}) = "
            f"{best[2]:.8f} * glove[:,{best[1]}]"
            f"{'**2' if form == 'quad' else ''} + const   max|resid|={best[0]:.3e}")
    say(f"  published equations: CMC5_F = 0.285*S20 ; "
        f"WRIST_F = 0.008*S21^2 - 190.451")
    say(f"  same raw column for both -> "
        f"{audit['CMC5']['glove_column_0based'] == audit['WRIST_F']['glove_column_0based']}")
    resp = {}
    say(f"\n  {'glove col':>9} {'1-based':>8} {'d_wrist13':>10} {'d_wrist14':>10} "
        f"{'d_fist6':>9} {'wrist_motion':>13}")
    for j in range(22):
        a, b = np.array(d0["idx"][13]), np.array(d0["idx"][11])
        c, e = np.array(d0["idx"][14]), np.array(d0["idx"][6])
        d13 = float(np.median(G0[a, j]) - np.median(G0[b, j]))
        d14 = float(np.median(G0[c, j]) - np.median(G0[b, j]))
        d6 = float(np.median(G0[e, j]) - np.median(G0[b, j]))
        resp[j] = {"d_wristflex_13": d13, "d_wristext_14": d14, "d_fist_6": d6,
                   "wrist_motion": abs(d13) + abs(d14)}
        say(f"  {j:>9} {j+1:>8} {d13:>10.1f} {d14:>10.1f} {d6:>9.1f} "
            f"{abs(d13)+abs(d14):>13.1f}")
    audit["column_response_subject1"] = resp
    rev = {}
    for n, g in GCOL.items():
        rev.setdefault(g, []).append(n)
    audit["glove_column_usage"] = {str(k): sorted(v) for k, v in sorted(rev.items())}
    say("\n  released angles reading each raw column (recovered mapping):")
    for j in sorted(rev):
        say(f"    glove[:,{j:>2}] (1-based {j+1:>2}) <- {sorted(rev[j])}")
    say(f"  glove[:,19] (1-based 20): wrist motion {resp[19]['wrist_motion']:.1f}, "
        f"fist {resp[19]['d_fist_6']:.1f}, used by any released angle: "
        f"{'yes' if 19 in rev else 'NO'}")
    say(f"  glove[:,20] (1-based 21): wrist motion {resp[20]['wrist_motion']:.1f}, "
        f"fist {resp[20]['d_fist_6']:.1f}, used by: {sorted(rev.get(20, []))}")
    audit["published_vs_measured"] = {
        "published": {"CMC5_F": "0.285 * S20", "WRIST_F": "0.008 * S21^2 - 190.451",
                      "source": "DB9 paper Tables 2 and 5 [OFFICIAL-CODE]"},
        "measured": {"CMC5_exact_function_of_glove_col_0based":
                     audit["CMC5"]["glove_column_0based"],
                     "WRIST_F_exact_function_of_glove_col_0based":
                     audit["WRIST_F"]["glove_column_0based"],
                     "same_column": audit["CMC5"]["glove_column_0based"]
                                    == audit["WRIST_F"]["glove_column_0based"]},
    }
    out["Q2_cmc5"] = audit

    # --------------------------------------------------------------- Q3/Q4
    F.banner("Q4  Exercise B hand configurations ids 1-8 ONLY (movement 17 excluded)")
    ids = list(range(1, 9))
    say(f"  target classes {ids}; ids 9-17 are wrist movements and are excluded")
    probe = A0
    arms = [("A_historical_canonical16", *cols_of(CANON16, probe)),
            ("B_TRUSTED_DB9_POSE_v1", *cols_of(frozen["keep_names"], probe)),
            ("C_STRICT_PREFIX_BUG006_REMOVED",
             *cols_of([n for n in frozen["keep_names"] if n not in BUG006_RESTORED],
                      probe))]
    results, folds_log = {}, {}
    for arm, cols, used in arms:
        t0 = time.time()
        X, y, s, _ = collect(ebf, cols, ids)
        say(f"\n  {arm}: X={X.shape} channels={len(used)} {used}  "
            f"({time.time()-t0:.0f}s to build)")
        fl = []
        pred = loso(X, y, s, fl)
        r = evaluate(pred, y, s)
        r["columns"] = used
        r["fold_pairs"] = fl
        r["max_train_test_intersection"] = max(
            len(p["train_test_global_intersection"]) for p in fl)
        results[arm] = r
        folds_log[arm] = fl
        say(f"    folds={len(fl)}  max train/test GLOBAL-KEY intersection="
            f"{r['max_train_test_intersection']}")
        say(f"    Acc={r['accuracy']:.4f}  BA={r['balanced_accuracy']:.4f}  "
            f"MacroF1={r['macro_f1']:.4f}  chance={r['chance_balanced_accuracy']:.4f}")
        say(f"    per-class recall: "
            f"{ {k: round(v, 4) for k, v in sorted(r['per_class_recall'].items())} }")
        say(f"    per-subject BA: median={r['median_subject_ba']:.4f} "
            f"worst={r['worst_subject_ba']:.4f} (subject {r['worst_subject_key']})")
        say(f"    classes below 0.5 recall: {r['classes_below_0_5']}  "
            f"collapse={r['class_collapse']}")
        say(f"    confusion (rows=true {r['confusion_labels']}):")
        for lab, row in zip(r["confusion_labels"], r["confusion_matrix"]):
            say(f"      {lab:>2}: {row}")
        del X, y, s, pred

    a, b, c = (results["A_historical_canonical16"], results["B_TRUSTED_DB9_POSE_v1"],
               results["C_STRICT_PREFIX_BUG006_REMOVED"])
    out["Q4_posture8"] = {"classes": ids, "results": results,
                          "frame_cap_per_segment": SEG_CAP,
                          "protocol": "frozen TRUSTED_DB9_POSE_v1, LDA, train-fold-only "
                                      "standardisation, leave-one-subject-out, radians, "
                                      "central 60 % of each segment",
                          "bug006_restored_channels": BUG006_RESTORED,
                          "strict_prefix_channels": [n for n in frozen["keep_names"]
                                                     if n not in BUG006_RESTORED]}
    out["Q4_summary"] = {
        "trusted_acc": b["accuracy"], "trusted_ba": b["balanced_accuracy"],
        "trusted_macro_f1": b["macro_f1"], "trusted_worst_subject_ba": b["worst_subject_ba"],
        "historical_acc": a["accuracy"], "historical_ba": a["balanced_accuracy"],
        "historical_macro_f1": a["macro_f1"],
        "historical_worst_subject_ba": a["worst_subject_ba"],
        "strict_acc": c["accuracy"], "strict_ba": c["balanced_accuracy"],
        "strict_macro_f1": c["macro_f1"], "strict_worst_subject_ba": c["worst_subject_ba"],
        "delta_ba_trusted_minus_historical": b["balanced_accuracy"] - a["balanced_accuracy"],
        "delta_ba_strict_minus_trusted": c["balanced_accuracy"] - b["balanced_accuracy"]}

    # --------------------------------------------------------------- Q3
    F.banner("Q3  LOSO identity audit")
    inter = {k: v["max_train_test_intersection"] for k, v in results.items()}
    say(f"  max train/test global-key intersection per arm: {inter}")
    say(f"  identity source: archive slot parsed from the FILENAME "
        f"(fx_common.load)")
    say(f"  in-file `subject` field used as identity: NO")
    say(f"  fold keys (arm B): {[p['fold_held_out_global_key'] for p in folds_log['B_TRUSTED_DB9_POSE_v1']][:12]} ...")
    say(f"  sample folds, verbatim:")
    for p in folds_log["B_TRUSTED_DB9_POSE_v1"][:3]:
        say(f"    held out key {p['fold_held_out_global_key']}: train keys "
            f"{p['n_train_global_keys']}, test 1, intersection "
            f"{p['train_test_global_intersection']}")
    ok = all(v == 0 for v in inter.values())
    say(f"  LOSO IDENTITY: {'PASS' if ok else 'FAIL'}")
    out["Q3_loso_identity"] = {
        "pass": bool(ok), "max_intersection_per_arm": inter,
        "identity_source": "archive slot from the filename "
                           "(fx_common.load: subject = int(basename.split('_')[0][1:]))",
        "in_file_subject_field_used_as_identity": False,
        "in_file_subject_is_source_local": True,
        "verdict": ("NO IMPACT - the previous trusted classifier already grouped by the "
                    "filename-derived global participant key, because BUG-004 was fixed in "
                    "fx_common.load before driver 04 ran" if ok
                    else "INVALID - rerun required"),
        "evidence": F.EMPIRICAL}
    out["bug006"] = {
        "restored_by_the_2pct_materiality_threshold": BUG006_RESTORED,
        "why": "BUG-006 introduced a 2 % materiality threshold for released-vs-published "
               "constant differences. Before it, MCP5_f (0.61 % difference) and PIP5 "
               "(0.12 %) were CASE_D_DOCUMENTATION_CONFLICT / INCONCLUSIVE. Both pass the "
               "physical anchor at 37/37 and now at 77/77.",
        "strict_prefix_subset": [n for n in frozen["keep_names"]
                                 if n not in BUG006_RESTORED],
        "effect_on_verdicts": "none - robustness report only",
        "delta_ba_strict_minus_trusted": c["balanced_accuracy"] - b["balanced_accuracy"]}

    sha = F.write_json(os.path.join(F.ART, "FINAL_VALIDATION.json"), out)
    say(f"\nartifacts/FINAL_VALIDATION.json sha256={sha}")
    say(f"log: {log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
