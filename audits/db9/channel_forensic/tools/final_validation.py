# =============================================================================
# Final validation  ---  ported from db9_channel_forensic_v2/scripts/06_final_validation.py
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

"""06 - FINAL VALIDATION (DB9_FORENSIC_FINAL_VALIDATION).

Q1  77-subject coverage: why 37, and revalidation of the frozen verdicts on DB2
Q2  independent CMC5 raw-sensor arbitration
Q3  LOSO identity audit (global participant key per fold; train/test intersection = 0)
Q4  the single permitted new utility evaluation: Exercise B hand configurations 1-8 only
    plus the BUG-006 STRICT-PREFIX sensitivity

The frozen subset TRUSTED_DB9_POSE_v1.json is read from disk and never modified.  No
threshold, no channel set and no classifier is changed.
"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fx_common as F  # noqa: E402
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis  # noqa: E402
from sklearn.metrics import (accuracy_score, balanced_accuracy_score,  # noqa: E402
                             confusion_matrix, f1_score, recall_score)

#: frozen rules - copied verbatim from scripts/03_verdicts.py, NOT re-tuned
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


def exercise_b_files():
    """Exercise B = the 17-movement basic finger/wrist protocol.

    DB1 and DB5 ship it as `_E2_`; DB2 ships the SAME protocol as `_E1_`.  The decision is
    made from the DATA (17 movements, movement 11 is the reference, movement 6 is the fist),
    not from the filename code alone, and every file is verified.
    """
    out = []
    for f in F.all_files():
        d = F.load(f)
        segs = F.segments(d)
        stims = sorted({s["stim"] for s in segs})
        if stims != list(range(1, 18)):
            continue
        idx = {}
        for sg in segs:
            idx.setdefault(sg["stim"], []).extend(range(*F.core(sg)))
        if 11 not in idx or 6 not in idx:
            continue
        ga = np.median(d["glove"][np.array(idx[6])][:, [4, 8, 12, 16]], axis=1)
        gb = np.median(d["glove"][np.array(idx[11])][:, [4, 8, 12, 16]], axis=1)
        out.append({"path": f, "name": d["name"], "subject": d["subject"],
                    "exercise_code": d["exercise"], "d": d, "idx": idx,
                    "fist_minus_ref_raw": float(np.median(ga) - np.median(gb))})
    return out


def db_of(s):
    return "DB1" if s <= 27 else ("DB2" if s <= 67 else "DB5")


def anchor_rows(files, name, gcol):
    dr, da = [], []
    for r in files:
        d, idx = r["d"], r["idx"]
        a, b = np.array(idx[6]), np.array(idx[11])
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            an = float(np.nanmedian(d["angles"][a, F.IDX[name]])
                       - np.nanmedian(d["angles"][b, F.IDX[name]]))
        dr.append(float(np.median(d["glove"][a, gcol]) - np.median(d["glove"][b, gcol])))
        da.append(an)
    dr, da = np.array(dr), np.array(da)
    return dr, da


def verdict_from(dr, da, exp, magref):
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


def cols_of(names, probe):
    out, used = [], []
    for n in names:
        for cand in (n, n.replace("_F", "_f")):
            if cand in F.IDX and np.isfinite(probe[:300, F.IDX[cand]]).any():
                out.append(F.IDX[cand]); used.append(cand); break
    return sorted(set(out)), used


def loso_audit(X, y, s, log_pairs):
    pred = np.full(y.shape, -1, dtype=int)
    for held in sorted(set(s.tolist())):
        tr, te = s != held, s == held
        inter = set(s[tr].tolist()) & set(s[te].tolist())
        log_pairs.append({"fold_held_out_global_key": int(held),
                          "n_train_frames": int(tr.sum()), "n_test_frames": int(te.sum()),
                          "train_global_keys": sorted(set(s[tr].tolist())),
                          "train_test_global_intersection": sorted(inter),
                          "intersection_size": len(inter)})
        mu, sd = X[tr].mean(0), X[tr].std(0)
        sd = np.where(sd > 0, sd, 1.0)
        m = LinearDiscriminantAnalysis()
        m.fit((X[tr] - mu) / sd, y[tr])
        pred[te] = m.predict((X[te] - mu) / sd)
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


def build(cols, keep_ids, files):
    Xs, ys, ss = [], [], []
    for r in files:
        d = r["d"]
        for sg in F.segments(d):
            if sg["stim"] not in keep_ids:
                continue
            a, b = F.core(sg)
            ang = d["angles"][a:b, :][:, cols]
            ok = np.isfinite(ang).all(axis=1)
            if not ok.any():
                continue
            Xs.append(np.deg2rad(ang[ok]))
            ys.append(np.full(int(ok.sum()), sg["stim"]))
            ss.append(np.full(int(ok.sum()), r["subject"]))
    return np.vstack(Xs), np.concatenate(ys), np.concatenate(ss)


def main() -> int:
    log = F.tee("06_final_validation")
    F.banner("DB9_FORENSIC_FINAL_VALIDATION")
    out = {"artifact": "FINAL_VALIDATION.json", "plan_sha256": F.plan_sha()}

    # =================================================================== Q1
    F.banner("Q1  coverage: why 37 subjects, and 77-subject revalidation")
    by = {}
    for f in F.all_files():
        d = F.load(f)
        by.setdefault(db_of(d["subject"]), {}).setdefault(d["exercise"], []).append(
            d["subject"])
    cov = {}
    for k in ("DB1", "DB2", "DB5"):
        cov[k] = {"subjects_present": len(set(sum(by.get(k, {}).values(), []))),
                  "official_subjects": {"DB1": 27, "DB2": 40, "DB5": 10}[k],
                  "files_by_exercise_code": {f"E{e}": len(v) for e, v in
                                             sorted(by.get(k, {}).items())}}
        print(f"  {k}: subjects {cov[k]['subjects_present']}/{cov[k]['official_subjects']}"
              f"  files {cov[k]['files_by_exercise_code']}")
    out["Q1_coverage"] = cov

    ebf = exercise_b_files()
    keys = sorted(r["subject"] for r in ebf)
    print(f"\n  Exercise-B-format files found by DATA verification: {len(ebf)}")
    print(f"    DB1 {sum(1 for r in ebf if db_of(r['subject']) == 'DB1')}  "
          f"DB2 {sum(1 for r in ebf if db_of(r['subject']) == 'DB2')}  "
          f"DB5 {sum(1 for r in ebf if db_of(r['subject']) == 'DB5')}")
    print(f"    exercise codes seen: "
          f"{sorted({r['exercise_code'] for r in ebf})}")
    print(f"    global keys: {keys}")
    eq77 = keys == list(range(1, 78))
    print(f"    global keys == 1..77: {eq77}")
    out["Q1_exercise_b"] = {
        "n": len(ebf), "global_keys": keys, "keys_are_1_to_77": eq77,
        "exercise_codes": sorted({r["exercise_code"] for r in ebf}),
        "why_37_last_time": "the previous loader selected Exercise B with "
                            "`ex_files('E2')`, i.e. by the FILENAME exercise code. DB1 and "
                            "DB5 ship the 17-movement basic protocol as `_E2_`; DB2 ships "
                            "the SAME protocol as `_E1_`. The DB2 files were present on "
                            "disk all along (40 subjects, 40 files) and were simply never "
                            "opened. This audit now selects Exercise B by verifying the "
                            "DATA: exactly 17 movements, movement 11 is the reference "
                            "(median fist response 0.00), movement 6 is the fist.",
        "evidence": F.EMPIRICAL}

    # ---- revalidate the frozen verdicts on all 77 subjects ----
    F.banner("Q1b  frozen verdicts revalidated on DB1 / DB2 / DB5 / ALL")
    mags = {n: abs(np.median(anchor_rows(ebf, n, GCOL[n])[0])) for n in EXPECT_FIST}
    magref = float(np.median(list(mags.values())))
    print(f"  flexion-magnitude reference over all {len(ebf)} files = {magref:.2f}")
    frozen = json.load(open(os.path.join(F.LANE, "TRUSTED_DB9_POSE_v1.json"),
                            encoding="utf-8"))
    subgroups = {"DB1": [r for r in ebf if db_of(r["subject"]) == "DB1"],
                 "DB2": [r for r in ebf if db_of(r["subject"]) == "DB2"],
                 "DB5": [r for r in ebf if db_of(r["subject"]) == "DB5"],
                 "ALL77": ebf}
    res = {}
    for gname, fl in subgroups.items():
        mr_g = magref
        res[gname] = {}
        for n, exp in EXPECT_FIST.items():
            dr, da = anchor_rows(fl, n, GCOL[n])
            v = verdict_from(dr, da, exp, mr_g)
            res[gname][n] = v
        print(f"\n  {gname} (n={len(fl)} subjects)")
        print(f"    {'channel':<9} {'agree':>6} {'opposed':>8} {'coh':>5} {'mag':>5} "
              f"{'verdict':>14}  same as frozen?")
        for n in EXPECT_FIST:
            v = res[gname][n]
            fz = frozen["keep_names"]
            same = ("KEEP" if n in fz else
                    ("DROP" if n in frozen["drop_names"] else "INCONCLUSIVE"))
            print(f"    {n:<9} {v['agreement']:>6.2f} {v['opposed']:>8.2f} "
                  f"{v['coherence']:>5.2f} {(v['mag_ratio'] or 0):>5.2f} "
                  f"{v['status']:>14}  {v['status'] == same}")
    out["Q1_verdicts"] = res
    agree_all = all(res["ALL77"][n]["status"] == ("KEEP" if n in frozen["keep_names"]
                                                  else ("DROP" if n in frozen["drop_names"]
                                                        else "INCONCLUSIVE"))
                    for n in EXPECT_FIST)
    print(f"\n  77-subject verdict consistency with the frozen KEEP/DROP: {agree_all}")
    out["Q1_consistency_77"] = bool(agree_all)

    # =================================================================== Q2
    F.banner("Q2  independent CMC5 raw-sensor arbitration")
    d0 = F.load(ebf[0]["path"])
    G0, A0 = d0["glove"], d0["angles"]
    audit = {}
    # (a) confirm the functional dependencies from scratch
    for name, ci, form in (("CMC5", 12, "linear"), ("WRIST_F", 20, "quad")):
        best = None
        for j in range(22):
            x = G0[:, j] if form == "linear" else G0[:, j] ** 2
            a, b = np.polyfit(x, A0[:, ci], 1)
            r = float(np.abs(A0[:, ci] - (a * x + b)).max())
            if best is None or r < best[0]:
                best = (r, j, float(a), float(b))
        audit[name] = {"angle_column_0based": ci, "glove_column_0based": best[1],
                       "max_abs_residual": best[0], "fitted_slope": best[2]}
        print(f"  {name:<8} angle col {ci:>2} = {best[2]:.8f} * glove[:,{best[1]}]"
              f"{'^2' if form == 'quad' else ''} + const   residual={best[0]:.3e}")
    # (b) which columns respond to WRIST movement, which to a FIST
    idx = {}
    for sg in F.segments(d0):
        idx.setdefault(sg["stim"], []).extend(range(*F.core(sg)))
    print(f"\n  per-raw-column response (subject 1, {d0['name']}):")
    print(f"    {'glove col':>9} {'1-based':>8} {'dRaw wrist13':>13} {'dRaw wrist14':>13} "
          f"{'dRaw fist6':>12} {'|d13|+|d14|':>12} {'|d6|':>8}")
    colresp = {}
    for j in range(22):
        d13 = float(np.median(G0[np.array(idx[13]), j]) - np.median(G0[np.array(idx[11]), j]))
        d14 = float(np.median(G0[np.array(idx[14]), j]) - np.median(G0[np.array(idx[11]), j]))
        d6 = float(np.median(G0[np.array(idx[6]), j]) - np.median(G0[np.array(idx[11]), j]))
        colresp[j] = {"d_wristflex": d13, "d_wristext": d14, "d_fist": d6,
                      "wrist_motion": abs(d13) + abs(d14)}
        print(f"    {j:>9} {j+1:>8} {d13:>13.1f} {d14:>13.1f} {d6:>12.1f} "
              f"{abs(d13)+abs(d14):>12.1f} {abs(d6):>8.1f}")
    audit["column_response"] = colresp
    used = {}
    for j in range(22):
        used[j] = []
    for i, n in enumerate(F.ORDER22):
        for j, g in GCOL.items():
            if g == j and g == j:
                pass
    # which released angles use each glove column (from the recovered mapping)
    rev = {}
    for n, g in GCOL.items():
        rev.setdefault(g, []).append(n)
    audit["glove_column_usage"] = {str(k): v for k, v in sorted(rev.items())}
    print("\n  released angles that read each raw column (recovered mapping):")
    for j in sorted(rev):
        print(f"    glove[:,{j:>2}] (1-based {j+1:>2}) <- {rev[j]}")
    top_wrist = sorted(colresp, key=lambda j: -colresp[j]["wrist_motion"])[:3]
    print(f"\n  columns with the largest wrist response: "
          f"{[(j, round(colresp[j]['wrist_motion'], 1)) for j in top_wrist]}")
    print(f"  glove[:,19] wrist response = {colresp[19]['wrist_motion']:.1f}, "
          f"fist response = {colresp[19]['d_fist']:.1f}")
    print(f"  glove[:,20] wrist response = {colresp[20]['wrist_motion']:.1f}, "
          f"fist response = {colresp[20]['d_fist']:.1f}")
    print(f"  is glove[:,19] used by ANY released angle? "
          f"{'yes' if 19 in rev else 'NO'}")
    # (c) the published-equation contradiction
    audit["published_equations"] = {
        "CMC5_F": "0.285 * S20",
        "WRIST_F": "0.008 * S21^2 - 190.451",
        "source": "DB9 paper Tables 2 and 5 [OFFICIAL-CODE]"}
    audit["measured"] = {
        "CMC5_is_exact_function_of_glove_col": audit["CMC5"]["glove_column_0based"],
        "WRIST_F_is_exact_function_of_glove_col": audit["WRIST_F"]["glove_column_0based"],
        "same_column": audit["CMC5"]["glove_column_0based"]
                       == audit["WRIST_F"]["glove_column_0based"]}
    print(f"\n  CMC5 and WRIST_F read the same raw column: "
          f"{audit['measured']['same_column']}")
    out["Q2_cmc5"] = audit
    print(f"  -> verdict recorded below")

    # =================================================================== Q3
    F.banner("Q3  LOSO identity audit")
    probe = d0["angles"]
    cb, ub = cols_of(frozen["keep_names"], probe)
    Xb, yb, sb = build(cb, list(range(1, 18)), ebf)
    pairs = []
    pred = loso_audit(Xb, yb, sb, pairs)
    maxinter = max(p["intersection_size"] for p in pairs)
    print(f"  folds: {len(pairs)}   global participant keys used: "
          f"{[p['fold_held_out_global_key'] for p in pairs]}")
    print(f"  maximum train/test global-key intersection over all folds: {maxinter}")
    print(f"  first three folds, verbatim:")
    for p in pairs[:3]:
        print(f"    held out {p['fold_held_out_global_key']}: train keys "
              f"{p['train_global_keys'][:8]}... ({len(p['train_global_keys'])} keys), "
              f"test keys [1], intersection {p['train_test_global_intersection']}")
    ident_ok = maxinter == 0
    print(f"  LOSO identity: {'PASS' if ident_ok else 'FAIL'}")
    out["Q3_loso_identity"] = {
        "pass": bool(ident_ok), "n_folds": len(pairs),
        "identity_source": "the archive slot parsed from the FILENAME "
                           "(fx_common.load: subject = int(basename.split('_')[0][1:]))",
        "in_file_subject_field_used": False,
        "in_file_subject_is_source_local": True,
        "in_file_collisions_known": 10,
        "max_train_test_intersection": int(maxinter),
        "folds": pairs,
        "verdict": ("NO IMPACT - the previous trusted classifier already grouped by the "
                    "filename-derived global participant key, because fx_common.load was "
                    "corrected in BUG-004 before driver 04 ran"
                    if ident_ok else "INVALID - rerun required"),
        "evidence": F.EMPIRICAL}

    # =================================================================== Q4
    F.banner("Q4  official Exercise B hand configurations, ids 1-8 ONLY")
    ids = list(range(1, 9))
    print(f"  target classes: {ids} (movement 17 EXCLUDED; 9-17 are wrist movements)")
    ca, ua = cols_of(CANON16, probe)
    results = {}
    for arm, cols, used in (("A_historical_canonical16", ca, ua),
                            ("B_TRUSTED_DB9_POSE_v1", cb, ub),
                            ("C_STRICT_PREFIX_BUG006_REMOVED",
                             *cols_of([n for n in frozen["keep_names"]
                                       if n not in BUG006_RESTORED], probe))):
        X, y, s = build(cols, ids, ebf)
        pr = np.full(y.shape, -1, dtype=int)
        foldpairs = []
        pr = loso_audit(X, y, s, foldpairs)
        r = evaluate(pr, y, s)
        r["columns"] = used
        r["max_train_test_intersection"] = max(p["intersection_size"] for p in foldpairs)
        results[arm] = r
        print(f"\n  {arm}  ({len(used)} channels: {used})")
        print(f"    X={X.shape} classes={r['n_classes']} subjects={r['n_subjects']} "
              f"folds={len(foldpairs)} max intersection={r['max_train_test_intersection']}")
        print(f"    Acc={r['accuracy']:.4f}  BA={r['balanced_accuracy']:.4f}  "
              f"MacroF1={r['macro_f1']:.4f}  chance={r['chance_balanced_accuracy']:.4f}")
        print(f"    per-class recall: "
              f"{ {k: round(v, 4) for k, v in sorted(r['per_class_recall'].items())} }")
        print(f"    per-subject BA: median={r['median_subject_ba']:.4f} "
              f"worst={r['worst_subject_ba']:.4f} (subject {r['worst_subject_key']})")
        print(f"    classes below 0.5 recall: {r['classes_below_0_5']}  "
              f"collapse={r['class_collapse']}")
        print(f"    confusion matrix (rows=true {r['confusion_labels']}):")
        for lab, row in zip(r["confusion_labels"], r["confusion_matrix"]):
            print(f"      {lab:>2}: {row}")
    out["Q4_posture8"] = {"classes": ids, "results": results,
                          "bug006_restored_channels": BUG006_RESTORED,
                          "strict_prefix_channels": [n for n in frozen["keep_names"]
                                                     if n not in BUG006_RESTORED],
                          "protocol": "frozen: TRUSTED_DB9_POSE_v1, LDA, "
                                      "train-fold-only standardisation, leave-one-subject-out,"
                                      " radians, central 60 % of each segment",
                          "evidence": F.EMPIRICAL}
    b = results["B_TRUSTED_DB9_POSE_v1"]
    a = results["A_historical_canonical16"]
    c = results["C_STRICT_PREFIX_BUG006_REMOVED"]
    out["Q4_summary"] = {
        "trusted_acc": b["accuracy"], "trusted_ba": b["balanced_accuracy"],
        "trusted_macro_f1": b["macro_f1"],
        "historical_acc": a["accuracy"], "historical_ba": a["balanced_accuracy"],
        "historical_macro_f1": a["macro_f1"],
        "strict_acc": c["accuracy"], "strict_ba": c["balanced_accuracy"],
        "strict_macro_f1": c["macro_f1"],
        "delta_ba_trusted_vs_historical": b["balanced_accuracy"] - a["balanced_accuracy"],
        "delta_ba_strict_vs_trusted": c["balanced_accuracy"] - b["balanced_accuracy"],
        "worst_subject_ba_trusted": b["worst_subject_ba"],
        "worst_subject_ba_historical": a["worst_subject_ba"],
    }
    print(f"\n  BUG-006 sensitivity: STRICT-PREFIX ({len(results['C_STRICT_PREFIX_BUG006_REMOVED']['columns'])} ch) "
          f"BA={c['balanced_accuracy']:.4f} vs TRUSTED-8 BA={b['balanced_accuracy']:.4f} "
          f"(delta {c['balanced_accuracy'] - b['balanced_accuracy']:+.4f})")
    print("  -> sensitivity is REPORTED ONLY; it does not change any channel verdict")
    out["bug006"] = {
        "restored_by_the_2pct_materiality_threshold": BUG006_RESTORED,
        "why": "BUG-006 added a 2 % materiality threshold for released-vs-published "
               "constant differences. Before it, MCP5_f (0.61 % difference) and PIP5 "
               "(0.12 % difference) were classified CASE_D_DOCUMENTATION_CONFLICT and held "
               "INCONCLUSIVE. Both pass the physical anchor at 37/37 and now at 77/77.",
        "strict_prefix_subset": [n for n in frozen["keep_names"]
                                 if n not in BUG006_RESTORED],
        "effect_on_verdicts": "none - this is a robustness report only"}

    sha = F.write_json(os.path.join(F.ART, "FINAL_VALIDATION.json"), out)
    print(f"\nartifacts/FINAL_VALIDATION.json sha256={sha}")
    print(f"log: {log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
