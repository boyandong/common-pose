"""build_matched.py - the LIKE-FOR-LIKE representation comparison.

Why this exists (a real threat to validity found during the run):

  R3's 500 ms CENTRED window requires 50 frames on each side of the centre, so by
  construction R3 is defined ONLY on frames that lie at least 50 frames inside a
  trial.  R1/R2/R5/R6 are defined on every frame.  Comparing R3's 0.6172 against
  R1's 0.4273 therefore compares DIFFERENT FRAME SETS, not different
  representations.

This tool removes that confound by restricting EVERY representation to the exact
frame set on which R3 is defined, and re-running the identical protocol.  It is
not a new representation and not a post-hoc selection: it is the overlap set where
all representations exist.

Writes results/matched_subset.json and appends a `matched_subset` block to the
single-frame, velocity and trajectory artifacts.
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import obs_common as C  # noqa: E402
import obs_plan as P  # noqa: E402
from build_cv import folds_of, run_cv  # noqa: E402

CACHE = os.path.join(C.RESULTS, "features.npz")


def main() -> int:
    log, fh = C.log_to(os.path.join(C.LANE, "KINMUS_TASK_OBSERVABILITY_FULL_LOG.txt"))
    log("")
    log("=" * 78)
    log("STAGE 11 - MATCHED-SUBSET COMPARISON (removes the window-definition "
        "confound)")
    log("=" * 78)
    plan_sha = C.sha256_file(os.path.join(C.LANE, P.PLAN_ARTIFACT))
    z = np.load(CACHE, allow_pickle=False)
    y, subj = z["phase"], z["subject"]
    interior = z["boundary_interior"]
    fold_of = folds_of(subj)

    # the frame set where EVERY representation is defined
    common = interior.copy()
    for rep in ("R1_POSE", "R2_POSE_VELOCITY", "R3_TRAJECTORY",
                "R4_POSE_PAST_ONLY", "R5_FULL18", "R6_FULL18_VELOCITY"):
        common &= z[rep + "_ok"]
    log(f"  matched frame set: {int(common.sum())} rows "
        f"(interior {int(interior.sum())}; R3-valid {int(z['R3_TRAJECTORY_ok'].sum())})")

    out = {}
    for rep in ("R1_POSE", "R2_POSE_VELOCITY", "R3_TRAJECTORY",
                "R4_POSE_PAST_ONLY", "R5_FULL18", "R6_FULL18_VELOCITY"):
        r = run_cv(z[rep], z[rep + "_ok"], y, subj, common, ["LDA"], fold_of,
                   verbose=False)
        m = r["LDA"]["metrics"]
        pr = m["confusion"]["per_class_recall"]
        out[rep] = {
            "n": m["n"],
            "balanced_accuracy": m["balanced_accuracy"],
            "macro_f1": m["macro_f1"],
            "accuracy": m["accuracy"],
            "per_phase_recall": {k: v["value"] for k, v in pr.items()},
            "directional_error": m["directional_error"],
            "across_subject_mean_ba": m.get("across_subject_mean_ba"),
            "across_subject_sd_ba": m.get("across_subject_sd_ba"),
            "n_subjects_ba_ge_0.50": m.get("n_subjects_ba_ge_0.50"),
            "n_subjects": m.get("n_subjects_scored"),
        }
        log(f"  {rep:<22} BA {m['balanced_accuracy']:.4f}  "
            f"acc {m['accuracy']:.4f}  F1 {m['macro_f1']:.4f}  n={m['n']}")

    deltas = {
        "R2_minus_R1": out["R2_POSE_VELOCITY"]["balanced_accuracy"]
        - out["R1_POSE"]["balanced_accuracy"],
        "R3_minus_R1": out["R3_TRAJECTORY"]["balanced_accuracy"]
        - out["R1_POSE"]["balanced_accuracy"],
        "R4_minus_R1": out["R4_POSE_PAST_ONLY"]["balanced_accuracy"]
        - out["R1_POSE"]["balanced_accuracy"],
        "R5_minus_R1": out["R5_FULL18"]["balanced_accuracy"]
        - out["R1_POSE"]["balanced_accuracy"],
    }
    body = {
        "artifact": "matched_subset.json",
        "branch_id": P.BRANCH_ID,
        "plan_sha256": plan_sha,
        "why": ("R3's 500 ms centred window is defined only on frames at least 50 "
                "frames inside a trial, so the naive R3-vs-R1 comparison uses "
                "DIFFERENT FRAME SETS.  This block restricts every representation "
                "to the exact frame set where all of them are defined, which "
                "removes the confound.  It is the overlap set, not a post-hoc "
                "selection"),
        "matched_frame_count": int(common.sum()),
        "interior_frame_count": int(interior.sum()),
        "r3_defined_frame_count": int(z["R3_TRAJECTORY_ok"].sum()),
        "protocol": "identical to the primary run (grouped 5-fold, train-only "
                    "z-scoring, LDA)",
        "by_representation": out,
        "deltas_vs_pose_only": {k: float(v) for k, v in deltas.items()},
        "reading_rule": (
            "the NAIVE (unmatched) deltas are larger than these matched deltas "
            "because part of the apparent gain is the easier frame set, not the "
            "representation.  The matched deltas are the honest effect of adding "
            "temporal information"),
    }
    sha = C.write_json(os.path.join(C.RESULTS, "matched_subset.json"), body)

    # append the matched block to the three primary artifacts so a reader of any
    # one of them sees the fair comparison
    for fname, key in (("KINMUS_SINGLE_FRAME_RESULTS.json", "R1_POSE"),
                       ("KINMUS_VELOCITY_RESULTS.json", "R2_POSE_VELOCITY"),
                       ("KINMUS_TRAJECTORY_RESULTS.json", "R3_TRAJECTORY")):
        art = C.load_json(os.path.join(C.LANE, fname))
        art["matched_subset_comparison"] = {
            "why": body["why"],
            "matched_frame_count": body["matched_frame_count"],
            "this_representation": out[key],
            "all_representations": out,
            "deltas_vs_pose_only": body["deltas_vs_pose_only"],
            "note": ("the primary numbers in this artifact use the full INTERIOR "
                     "stratum, which is valid for this representation; the "
                     "matched block is the fair cross-representation comparison"),
        }
        C.write_json(os.path.join(C.LANE, fname), art)

    log("")
    log(f"  matched deltas vs pose-only: "
        + ", ".join(f"{k}={v:+.4f}" for k, v in deltas.items()))
    log(f"  wrote results/matched_subset.json sha256={sha[:16]}")
    fh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
