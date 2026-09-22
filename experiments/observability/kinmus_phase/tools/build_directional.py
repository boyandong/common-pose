"""build_directional.py - the restricted two-class REACHING-vs-RELEASING test.

Why it exists.  The three-class confusion matrix cannot answer the directional
question cleanly, because the dominant MANIPULATION class absorbs most errors and
one class can be collapsed entirely: with R1 (pose only) the model predicts
REACHING for 57 of 31 547 reaching frames and for ZERO releasing frames, so the
predeclared `releasing_as_reaching` rate is exactly 0 by construction and the
"smaller of the two" statistic is degenerate.

This tool isolates the question the branch actually asks:

    can REACHING and RELEASING be told apart from each other?

by restricting to frames labelled REACHING or RELEASING and re-running the
identical protocol with a two-class model.  It is a POST-HOC derived metric (the
frozen plan did not predeclare it) and is labelled as such everywhere it appears;
it does not replace any predeclared gate and it changes no representation.

Also reports, per representation, the confusion-matrix collapse indicators so the
reader can see when a class is not being predicted at all.
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import obs_common as C  # noqa: E402
import obs_plan as P  # noqa: E402
from build_cv import folds_of, metrics, run_cv  # noqa: E402

CACHE = os.path.join(C.RESULTS, "features.npz")
OUT = "KINMUS_DIRECTIONAL_ANALYSIS.json"


def collapse_indicators(m) -> dict:
    """How badly does the model fail to use each class?"""
    cm = np.array(m["confusion"]["matrix_true_x_pred"], dtype=np.int64)
    pred_tot = cm.sum(axis=0)
    true_tot = cm.sum(axis=1)
    out = {}
    for i, name in enumerate(("REACHING", "MANIPULATION", "RELEASING")):
        out[name] = {
            "true_count": int(true_tot[i]),
            "predicted_count": int(pred_tot[i]),
            "recall": float(cm[i, i] / true_tot[i]) if true_tot[i] else None,
            "share_of_all_predictions": float(pred_tot[i] / pred_tot.sum())
            if pred_tot.sum() else None,
            "never_predicted": bool(pred_tot[i] == 0),
        }
    out["n_predicted_classes"] = int((pred_tot > 0).sum())
    return out


def main() -> int:
    log, fh = C.log_to(os.path.join(C.LANE, "KINMUS_TASK_OBSERVABILITY_FULL_LOG.txt"))
    log("")
    log("=" * 78)
    log("STAGE 11b - RESTRICTED TWO-CLASS DIRECTIONAL TEST (post-hoc derived)")
    log("=" * 78)
    plan_sha = C.sha256_file(os.path.join(C.LANE, P.PLAN_ARTIFACT))
    z = np.load(CACHE, allow_pickle=False)
    y, subj = z["phase"], z["subject"]
    interior = z["boundary_interior"]
    fold_of = folds_of(subj)

    matched = C.load_json(os.path.join(C.RESULTS, "matched_subset.json"))
    common = interior.copy()
    for rep in ("R1_POSE", "R2_POSE_VELOCITY", "R3_TRAJECTORY",
                "R4_POSE_PAST_ONLY", "R5_FULL18", "R6_FULL18_VELOCITY"):
        common &= z[rep + "_ok"]

    results = {}
    for rep in ("R1_POSE", "R2_POSE_VELOCITY", "R3_TRAJECTORY",
                "R4_POSE_PAST_ONLY", "R5_FULL18"):
        X = z[rep]
        ok = z[rep + "_ok"]
        entry = {}
        for basis, mask in (("matched", common), ("interior", interior)):
            m_directional = mask & ok & np.isin(y, (1, 3))
            pred = np.full(y.size, -1, dtype=np.int64)
            for f in sorted(set(fold_of.values())):
                te_s = {s for s, k in fold_of.items() if k == f}
                tr = np.array([s not in te_s for s in subj])
                te = np.array([s in te_s for s in subj])
                sel_tr = tr & m_directional
                sel_te = te & m_directional
                if sel_tr.sum() == 0 or sel_te.sum() == 0:
                    continue
                from build_cv import fit_predict, zscore_fit
                mu, sd = zscore_fit(X[sel_tr])
                p = fit_predict("LDA", (X[sel_tr] - mu) / sd, y[sel_tr],
                                (X[sel_te] - mu) / sd)
                pred[np.flatnonzero(sel_te)] = p
            keep = pred >= 0
            yk, pk, sk = y[keep], pred[keep], subj[keep]
            # two-class balanced accuracy over {REACHING, RELEASING}
            rec_r = float((pk[yk == 1] == 1).mean()) if (yk == 1).any() else None
            rec_l = float((pk[yk == 3] == 3).mean()) if (yk == 3).any() else None
            ba2 = float(np.mean([v for v in (rec_r, rec_l) if v is not None]))
            entry[basis] = {
                "n_frames": int(yk.size),
                "n_reaching": int((yk == 1).sum()),
                "n_releasing": int((yk == 3).sum()),
                "two_class_balanced_accuracy": ba2,
                "reaching_recall": rec_r,
                "releasing_recall": rec_l,
                "reaching_as_releasing": float((pk[yk == 1] == 3).mean())
                if (yk == 1).any() else None,
                "releasing_as_reaching": float((pk[yk == 3] == 1).mean())
                if (yk == 3).any() else None,
                "per_subject_two_class_ba": {
                    str(int(s)): float(np.mean([
                        (pk[(sk == s) & (yk == 1)] == 1).mean()
                        if ((sk == s) & (yk == 1)).any() else np.nan,
                        (pk[(sk == s) & (yk == 3)] == 3).mean()
                        if ((sk == s) & (yk == 3)).any() else np.nan]))
                    for s in np.unique(sk)},
            }
            if basis == "matched":
                vals = np.array(list(entry[basis][
                    "per_subject_two_class_ba"].values()), dtype=np.float64)
                vals = vals[np.isfinite(vals)]
                entry[basis]["across_subject_mean"] = float(vals.mean())
                entry[basis]["across_subject_sd"] = float(vals.std(ddof=1))
                entry[basis]["n_subjects_ge_0.60"] = int((vals >= 0.60).sum())
        results[rep] = entry
        log(f"  {rep:<22} matched 2-class BA "
            f"{entry['matched']['two_class_balanced_accuracy']:.4f}  "
            f"(reach {entry['matched']['reaching_recall']:.4f} / "
            f"rel {entry['matched']['releasing_recall']:.4f})  "
            f"interior {entry['interior']['two_class_balanced_accuracy']:.4f}")

    # ---- collapse indicators from the predeclared three-class runs ---------
    collapse = {}
    for rep, art in (("R1_POSE", C.load_json(os.path.join(
            C.LANE, "KINMUS_SINGLE_FRAME_RESULTS.json"))["primary"]),
            ("R2_POSE_VELOCITY", C.load_json(os.path.join(
                C.LANE, "KINMUS_VELOCITY_RESULTS.json"))["primary"]),
            ("R3_TRAJECTORY", C.load_json(os.path.join(
                C.LANE, "KINMUS_TRAJECTORY_RESULTS.json"))["primary"])):
        collapse[rep] = collapse_indicators(art)
        ci = collapse[rep]
        log(f"  {rep:<22} predicted classes {ci['n_predicted_classes']}/3  "
            f"REACHING predictions {ci['REACHING']['predicted_count']}  "
            f"RELEASING predictions {ci['RELEASING']['predicted_count']}")

    body = {
        "artifact": OUT,
        "branch_id": P.BRANCH_ID,
        "plan_sha256": plan_sha,
        "epistemic_status": (
            "POST-HOC DERIVED METRIC.  The frozen plan did not predeclare a "
            "restricted two-class test.  It is added because the three-class "
            "confusion matrix cannot answer the directional question when a class "
            "is collapsed entirely.  It replaces no predeclared gate, it changes "
            "no representation, and no threshold is derived from it"),
        "why_needed": (
            "with R1 (pose only) the model predicts REACHING for 57 of 31 547 "
            "reaching frames and for ZERO releasing frames, so the predeclared "
            "'releasing_as_reaching' rate is exactly 0 by construction and the "
            "'smaller of the two' statistic is degenerate"),
        "method": ("restrict to frames labelled REACHING or RELEASING, run the "
                   "identical grouped 5-fold protocol with train-only z-scoring "
                   "and LDA, and score two-class balanced accuracy"),
        "by_representation": results,
        "three_class_collapse_indicators": collapse,
        "headline": {
            "R1_two_class_matched_ba": results["R1_POSE"]["matched"][
                "two_class_balanced_accuracy"],
            "R3_two_class_matched_ba": results["R3_TRAJECTORY"]["matched"][
                "two_class_balanced_accuracy"],
            "gain_R3_over_R1": float(
                results["R3_TRAJECTORY"]["matched"][
                    "two_class_balanced_accuracy"]
                - results["R1_POSE"]["matched"][
                    "two_class_balanced_accuracy"]),
            "R4_causal_two_class_matched_ba": results["R4_POSE_PAST_ONLY"][
                "matched"]["two_class_balanced_accuracy"],
            "reading": ("this is the cleanest available answer to 'can reaching "
                        "and releasing be told apart at all': the question is "
                        "answered on its own two classes, without the dominant "
                        "MANIPULATION class or a collapsed label diluting it"),
        },
    }
    sha = C.write_json(os.path.join(C.LANE, OUT), body)
    log("")
    log(f"  RESTRICTED 2-CLASS matched: R1 {body['headline']['R1_two_class_matched_ba']:.4f}"
        f" -> R3 {body['headline']['R3_two_class_matched_ba']:.4f}"
        f"  ({body['headline']['gain_R3_over_R1']:+.4f})")
    log(f"  wrote {OUT}  sha256={sha[:16]}")
    fh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
