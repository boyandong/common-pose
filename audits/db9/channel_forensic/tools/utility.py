# =============================================================================
# Utility  ---  ported from db9_channel_forensic_v2/scripts/04_utility.py
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

"""04 - POSTURE UTILITY TEST and REMOVAL ATTRIBUTION.

Runs ONLY after TRUSTED_DB9_POSE_v1.json was frozen.  The frozen subset is read from disk
and never modified here.

Protocol, deliberately simple and matched between arms:
  * target  : the Exercise B movement id (restimulus 1..17) of the frame
  * frames  : the central 60 % of every (restimulus, rerepetition) segment
  * split   : SUBJECT-HELD-OUT (leave-one-subject-out)
  * scaling : standardisation fitted on the training subjects only
  * model   : LinearDiscriminantAnalysis, one shared model per fold
  * units   : radians, converted from the released degrees

Arm A = the historical canonical16 representation (a historical utility reference only).
Arm B = TRUSTED_DB9_POSE_v1.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fx_common as F  # noqa: E402

from sklearn.discriminant_analysis import LinearDiscriminantAnalysis  # noqa: E402
from sklearn.metrics import (accuracy_score, balanced_accuracy_score,  # noqa: E402
                             confusion_matrix, f1_score, recall_score)


def load_meta():
    p = os.path.join(F.ROOT, "data", "ninapro_db9", "dataset.meta.json")
    return json.load(open(p, encoding="utf-8"))


def build_dataset(cols):
    """Return X, y, subject arrays over the Exercise B core windows."""
    Xs, ys, ss = [], [], []
    for f in F.ex_files("E2"):
        d = F.load(f)
        for sg in F.segments(d):
            a, b = F.core(sg)
            ang = d["angles"][a:b, :][:, cols]
            ok = np.isfinite(ang).all(axis=1)
            if not ok.any():
                continue
            Xs.append(np.deg2rad(ang[ok]))
            ys.append(np.full(int(ok.sum()), sg["stim"]))
            ss.append(np.full(int(ok.sum()), d["subject"]))
    return np.vstack(Xs), np.concatenate(ys), np.concatenate(ss)


def loso(X, y, s):
    pred = np.full(y.shape, -1, dtype=int)
    for held in np.unique(s):
        tr, te = s != held, s == held
        if not te.any() or len(np.unique(y[tr])) < 2:
            continue
        mu, sd = X[tr].mean(0), X[tr].std(0)
        sd = np.where(sd > 0, sd, 1.0)
        m = LinearDiscriminantAnalysis()
        m.fit((X[tr] - mu) / sd, y[tr])
        pred[te] = m.predict((X[te] - mu) / sd)
    return pred


def evaluate(pred, y, s, name):
    ok = pred >= 0
    y2, p2, s2 = y[ok], pred[ok], s[ok]
    classes = np.unique(y2)
    cm = confusion_matrix(y2, p2, labels=classes)
    rec = recall_score(y2, p2, labels=classes, average=None, zero_division=0)
    per_sub = {}
    for su in np.unique(s2):
        m = s2 == su
        per_sub[int(su)] = float(balanced_accuracy_score(y2[m], p2[m]))
    per_class = {int(c): float(r) for c, r in zip(classes, rec)}
    out = {
        "arm": name, "n_frames": int(y2.size), "n_subjects": int(np.unique(s2).size),
        "n_classes": int(classes.size),
        "accuracy": float(accuracy_score(y2, p2)),
        "balanced_accuracy": float(balanced_accuracy_score(y2, p2)),
        "macro_f1": float(f1_score(y2, p2, average="macro", zero_division=0)),
        "chance_balanced_accuracy": float(1.0 / classes.size),
        "per_class_recall": per_class,
        "confusion_matrix": cm.tolist(), "confusion_labels": [int(c) for c in classes],
        "per_subject_balanced_accuracy": per_sub,
        "worst_subject_balanced_accuracy": float(min(per_sub.values())),
        "best_subject_balanced_accuracy": float(max(per_sub.values())),
        "median_subject_balanced_accuracy": float(np.median(list(per_sub.values()))),
        "classes_with_recall_below_0_5": [c for c, r in per_class.items() if r < 0.5],
        "classes_with_recall_below_0_2": [c for c, r in per_class.items() if r < 0.2],
        "class_collapse": bool(min(per_class.values()) < 0.10),
        "top5_subject_share_of_correct": None,
    }
    return out


def main() -> int:
    log = F.tee("04_utility")
    F.banner("04 POSTURE UTILITY TEST (post-freeze)")
    meta = load_meta()
    # The historical canonical16 representation, expressed in DB9 channel names.  Taken
    # from docs/DB9_CANONICAL16_MAPPING.md (read-only), which is the project's single
    # source of truth for the DB9 <-> canonical16 correspondence.
    canon = ["CMC1_f", "CMC1_a", "MCP1", "IP1", "MCP2_f", "PIP2", "DIP2", "MCP3_f",
             "PIP3", "DIP3", "MCP4_f", "PIP4", "DIP4", "MCP5_f", "PIP5", "DIP5"]
    print(f"historical canonical16 representation in DB9 channels ({len(canon)}): {canon}")
    print("  source: docs/DB9_CANONICAL16_MAPPING.md (read-only)")

    tr = json.load(open(os.path.join(F.LANE, "TRUSTED_DB9_POSE_v1.json"), encoding="utf-8"))
    trusted_names = tr["keep_names"]
    print(f"TRUSTED_DB9_POSE_v1 ({tr['n_keep']} channels, frozen before this driver ran): "
          f"{trusted_names}")

    def cols_of(names):
        out, used = [], []
        for n in names:
            n2 = n.replace("_F", "_f")
            for cand in (n, n2):
                if cand in F.IDX and np.isfinite(
                        F.load(F.ex_files("E2")[0])["angles"][:200, F.IDX[cand]]).any():
                    out.append(F.IDX[cand])
                    used.append(cand)
                    break
        return sorted(set(out)), used

    ca, ua = cols_of(canon)
    cb, ub = cols_of(trusted_names)
    print(f"  arm A columns ({len(ca)}): {ua}")
    print(f"  arm B columns ({len(cb)}): {ub}")

    results = {}
    for arm, cols, used in (("A_historical_canonical16", ca, ua),
                            ("B_TRUSTED_DB9_POSE_v1", cb, ub)):
        X, y, s = build_dataset(cols)
        print(f"\n  arm {arm}: X={X.shape} classes={len(np.unique(y))} "
              f"subjects={len(np.unique(s))}")
        pred = loso(X, y, s)
        r = evaluate(pred, y, s, arm)
        r["columns"] = used
        results[arm] = r
        print(f"    Acc={r['accuracy']:.4f}  BA={r['balanced_accuracy']:.4f}  "
              f"macroF1={r['macro_f1']:.4f}  chance={r['chance_balanced_accuracy']:.4f}")
        print(f"    per-class recall: "
              f"{ {k: round(v, 3) for k, v in sorted(r['per_class_recall'].items())} }")
        print(f"    worst subject BA={r['worst_subject_balanced_accuracy']:.4f} "
              f"median={r['median_subject_balanced_accuracy']:.4f} "
              f"best={r['best_subject_balanced_accuracy']:.4f}")
        print(f"    classes with recall <0.5: {r['classes_with_recall_below_0_5']}  "
              f"<0.2: {r['classes_with_recall_below_0_2']}  collapse: "
              f"{r['class_collapse']}")

    # ------------------------------------------------- removal attribution
    F.banner("removal attribution (descriptive only; cannot change the trusted subset)")
    removed_groups = {
        "official_warning_and_excluded": ["MCP2_a"],
        "literature_flagged": ["DIP3", "DIP4", "DIP5", "CMC5"],
        "qc_failed_here": ["DIP3", "DIP5", "CMC5", "MCP5_a", "WRIST_A", "MCP2_a"],
        "trusted_dropped_union": sorted(set(tr["drop_names"])),
    }
    attr = {}
    for gname, drop in removed_groups.items():
        keepc = [n for n in ua if n not in drop]
        cols, used = cols_of(keepc)
        if len(cols) < 2:
            attr[gname] = {"skipped": True, "kept": used}
            continue
        X, y, s = build_dataset(cols)
        pred = loso(X, y, s)
        r = evaluate(pred, y, s, gname)
        attr[gname] = {"removed": drop, "kept_columns": used,
                       "n_kept": len(used),
                       "accuracy": r["accuracy"], "balanced_accuracy": r["balanced_accuracy"],
                       "macro_f1": r["macro_f1"],
                       "delta_balanced_accuracy_vs_arm_A":
                           r["balanced_accuracy"] - results["A_historical_canonical16"][
                               "balanced_accuracy"]}
        print(f"  remove {gname:<32} -> {len(used):>2} channels kept, "
              f"BA={r['balanced_accuracy']:.4f} "
              f"(delta {attr[gname]['delta_balanced_accuracy_vs_arm_A']:+.4f})")

    hist_ref = historical_reference()
    print(f"\n  quoted historical S3 reference (NOT like-for-like): {hist_ref}")

    out = {"artifact": "POSTURE_UTILITY.json", "plan_sha256": F.plan_sha(),
           "trusted_subset_sha256":
               F.sha256_file(os.path.join(F.LANE, "TRUSTED_DB9_POSE_v1.json")),
           "task": "Exercise B movement id (restimulus 1..17)",
           "frames": "central 60 % of every (restimulus, rerepetition) segment",
           "split": "leave-one-subject-out", "scaling": "train-fold only",
           "model": "LinearDiscriminantAnalysis (shared per fold)",
           "units": "radians",
           "arms": results,
           "removal_attribution": attr,
           "historical_reference_not_like_for_like": hist_ref,
           "utility_loss": {
               "delta_accuracy": results["B_TRUSTED_DB9_POSE_v1"]["accuracy"]
                                 - results["A_historical_canonical16"]["accuracy"],
               "delta_balanced_accuracy":
                   results["B_TRUSTED_DB9_POSE_v1"]["balanced_accuracy"]
                   - results["A_historical_canonical16"]["balanced_accuracy"],
               "delta_macro_f1": results["B_TRUSTED_DB9_POSE_v1"]["macro_f1"]
                                 - results["A_historical_canonical16"]["macro_f1"],
               "relative_balanced_accuracy": results["B_TRUSTED_DB9_POSE_v1"][
                   "balanced_accuracy"] / results["A_historical_canonical16"][
                   "balanced_accuracy"],
           },
           "evidence": F.EMPIRICAL}
    sha = F.write_json(os.path.join(F.ART, "POSTURE_UTILITY.json"), out)
    print(f"\nartifacts/POSTURE_UTILITY.json sha256={sha}")
    print(f"log: {log}")
    return 0


def historical_reference():
    """Quote, not recompute, the historical closed-set number."""
    cands = [
        os.path.join(F.ROOT, "db9_channel_validity", "DB9_INTERNAL_CLEAN_RESULTS.json"),
        os.path.join(F.ROOT, "data", "ninapro_db9", "results_v", "baseline_results.json"),
    ]
    for p in cands:
        if os.path.exists(p):
            try:
                j = json.load(open(p, encoding="utf-8"))
                txt = json.dumps(j)
                return {"source": os.path.relpath(p, F.ROOT),
                        "sha256": F.sha256_file(p),
                        "note": "read-only quote; computed by another lane under a different "
                                "protocol (different subjects, different label set) and "
                                "therefore NOT like-for-like with the numbers here",
                        "excerpt_keys": list(j)[:12] if isinstance(j, dict) else None}
            except Exception:
                continue
    return {"source": None, "note": "no historical results file found"}


if __name__ == "__main__":
    raise SystemExit(main())
