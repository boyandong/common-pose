"""build_post.py - subject stability and boundary/interior analyses.

Both read the FROZEN cached features and re-run the SAME protocol (grouped folds,
train-fold-only z-scoring, LDA) so no new choice is introduced.

  KINMUS_SUBJECT_STABILITY.json   per-subject and distributional stability
  KINMUS_BOUNDARY_ANALYSIS.json   interior vs boundary, reported separately
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
STAB_OUT = "KINMUS_SUBJECT_STABILITY.json"
BOUND_OUT = "KINMUS_BOUNDARY_ANALYSIS.json"
REPS = ("R1_POSE", "R2_POSE_VELOCITY", "R3_TRAJECTORY", "R4_POSE_PAST_ONLY",
        "R5_FULL18", "R6_FULL18_VELOCITY")


def main() -> int:
    log, fh = C.log_to(os.path.join(C.LANE, "KINMUS_TASK_OBSERVABILITY_FULL_LOG.txt"))
    plan_sha = C.sha256_file(os.path.join(C.LANE, P.PLAN_ARTIFACT))
    z = np.load(CACHE, allow_pickle=False)
    y, subj = z["phase"], z["subject"]
    interior = z["boundary_interior"]
    fold_of = folds_of(subj)
    margin = P.BOUNDARY["margin_frames"]

    # ------------------------------------------------------------- STABILITY
    log("")
    log("=" * 78)
    log("STAGE 9 - SUBJECT STABILITY")
    log("=" * 78)
    res = {}
    for rep in REPS:
        X, ok = z[rep], z[rep + "_ok"]
        r = run_cv(X, ok, y, subj, interior, ["LDA"], fold_of, verbose=False)
        m = r["LDA"]["metrics"]
        vals = np.array([v["balanced_accuracy"]
                         for v in m["per_subject_balanced_accuracy"].values()],
                        dtype=np.float64)
        n = vals.size
        res[rep] = {
            "n_features": int(X.shape[1]),
            "pooled_balanced_accuracy": m["balanced_accuracy"],
            "mean_subject_balanced_accuracy": float(np.nanmean(vals)),
            "sd_subject_balanced_accuracy": float(np.nanstd(vals, ddof=1)),
            "median_subject_balanced_accuracy": float(np.nanmedian(vals)),
            "worst_subject_balanced_accuracy": float(np.nanmin(vals)),
            "best_subject_balanced_accuracy": float(np.nanmax(vals)),
            "n_subjects_ba_ge_0.50": int((vals >= 0.50).sum()),
            "n_subjects_ba_ge_0.60": int((vals >= 0.60).sum()),
            "n_subjects_ba_lt_0.45": int((vals < 0.45).sum()),
            "n_subjects": int(n),
            "per_subject": m["per_subject_balanced_accuracy"],
            "per_fold": m["per_fold"],
            "mean_fold_balanced_accuracy": m["mean_fold_ba"],
            "sd_fold_balanced_accuracy": m["sd_fold_ba"],
        }
        # class-specific variability: per-subject recall spread
        yhat = r["LDA"]["yhat"]
        keep = r["LDA"]["keep"]
        yk, sk, yhk = y[keep], subj[keep], yhat[keep]
        cls = {}
        for c in C.PHASES:
            v = []
            for s in np.unique(sk):
                sel = (sk == s) & (yk == c)
                if sel.sum() >= 5:
                    v.append(float((yhk[sel] == c).mean()))
            cls[C.PHASE_NAME[c]] = {
                "n_subjects_with_ge5_frames": len(v),
                "mean_subject_recall": float(np.mean(v)) if v else None,
                "sd_subject_recall": float(np.std(v, ddof=1)) if len(v) > 1 else None,
                "min_subject_recall": float(np.min(v)) if v else None,
            }
        res[rep]["per_class_recall_variability"] = cls
        log(f"  {rep:<22} pooled BA {m['balanced_accuracy']:.4f} | "
            f"subject mean {np.nanmean(vals):.4f} sd {np.nanstd(vals, ddof=1):.4f} "
            f"| worst {np.nanmin(vals):.4f} | >=0.50 "
            f"{int((vals >= 0.50).sum())}/{n} | <0.45 {int((vals < 0.45).sum())}/{n}")

    # pooled-vs-mean discrepancy matters: pooled BA can hide a bad subject
    body = {
        "artifact": STAB_OUT, "branch_id": P.BRANCH_ID, "plan_sha256": plan_sha,
        "why": ("a task that works only for a subset of subjects is weak evidence "
                "for a portable interface"),
        "protocol": P.VALIDATION,
        "evaluation_stratum": "INTERIOR",
        "by_representation": res,
        "decision_relevant": {
            "SUBJECT_CONSISTENCY_definition":
                P.DECISION["thresholds"]["SUBJECT_CONSISTENCY"],
            "SEVERE_SUBJECT_INSTABILITY_definition":
                P.DECISION["thresholds"]["SEVERE_SUBJECT_INSTABILITY"],
        },
        "note_bootstrap": ("subject-level bootstrap intervals for the pooled BA "
                           "are reported in the results artifacts; frames are "
                           "never the resampling unit"),
    }
    sha = C.write_json(os.path.join(C.LANE, STAB_OUT), body)
    log(f"  wrote {STAB_OUT}  sha256={sha[:16]}")

    # ------------------------------------------------------------- BOUNDARY
    log("")
    log("=" * 78)
    log("STAGE 10 - BOUNDARY vs INTERIOR")
    log("=" * 78)
    bound = ~interior
    out = {
        "artifact": BOUND_OUT, "branch_id": P.BRANCH_ID, "plan_sha256": plan_sha,
        "margin_frames": margin, "margin_ms": P.BOUNDARY["margin_ms"],
        "definition": P.BOUNDARY["definition"],
        "primary_stratum": "INTERIOR",
        "strata_counts": {
            "interior": int(interior.sum()),
            "boundary": int(bound.sum()),
            "interior_by_phase": {C.PHASE_NAME[c]: int(((y == c) & interior).sum())
                                  for c in C.PHASES},
            "boundary_by_phase": {C.PHASE_NAME[c]: int(((y == c) & bound).sum())
                                  for c in C.PHASES},
        },
        "boundary_samples_are_deleted": False,
        "by_representation": {},
    }
    for rep in REPS:
        X, ok = z[rep], z[rep + "_ok"]
        entry = {"n_features": int(X.shape[1])}
        for name, mask in (("interior", interior), ("boundary", bound)):
            r = run_cv(X, ok, y, subj, mask, ["LDA"], fold_of, verbose=False)
            m = r["LDA"]["metrics"]
            entry[name] = {
                "n": m["n"],
                "balanced_accuracy": m["balanced_accuracy"],
                "accuracy": m["accuracy"],
                "macro_f1": m["macro_f1"],
                "per_phase_recall": {k: v["value"] for k, v in
                                     m["confusion"]["per_class_recall"].items()},
                "directional_error": m["directional_error"],
            }
        entry["interior_minus_boundary_balanced_accuracy"] = float(
            entry["interior"]["balanced_accuracy"]
            - entry["boundary"]["balanced_accuracy"])
        out["by_representation"][rep] = entry
        log(f"  {rep:<22} interior BA "
            f"{entry['interior']['balanced_accuracy']:.4f} (n="
            f"{entry['interior']['n']})  boundary BA "
            f"{entry['boundary']['balanced_accuracy']:.4f} (n="
            f"{entry['boundary']['n']})  delta "
            f"{entry['interior_minus_boundary_balanced_accuracy']:+.4f}")

    out["interpretation"] = {
        "why_it_matters": (
            "if interior performance is much better than boundary performance, the "
            "residual difficulty is largely an ANNOTATION-TRANSITION problem; if "
            "both are equally weak, the limitation is more fundamental"),
        "reading_rule": ("a large positive interior-minus-boundary gap means the "
                         "phase labels are least reliable exactly where two phases "
                         "meet, which is a labelling property, not necessarily a "
                         "pose-information property"),
    }
    sha = C.write_json(os.path.join(C.LANE, BOUND_OUT), out)
    log(f"  wrote {BOUND_OUT}  sha256={sha[:16]}")
    fh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
