#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GATE 4A — CANDIDATE 2: simple task-error predictor prototype (stage-grouped OOF).

Implements GATE4A_PLAN.md §8 exactly.

  features : deployment-visible, current-and-past only (plan §8.1)
  model    : sklearn GradientBoostingRegressor(loss="quantile", alpha=0.90), plan §8.2
  split    : sklearn GroupKFold(n_splits=5) on `stage` (plan §8.3)

`stage` is a grouping variable ONLY and never enters the feature matrix.
`r_t` is the training label only and never enters the feature matrix.

Run:
  /root/miniconda3/envs/emg2pose-gate3/bin/python -X utf8 scripts/run_task_error_predictor.py
"""
from __future__ import annotations

import os
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import io_common as C  # noqa: E402

from sklearn.ensemble import GradientBoostingRegressor  # noqa: E402
from sklearn.model_selection import GroupKFold  # noqa: E402

MODEL_KWARGS = dict(
    loss="quantile", alpha=0.90, n_estimators=100, learning_rate=0.1,
    max_depth=3, subsample=1.0, criterion="friedman_mse", min_samples_split=2,
    min_samples_leaf=1, max_features=None, random_state=0,
)
# NOTE: `n_jobs` is deliberately absent. It is not a constructor parameter of
# sklearn 1.5.2 GradientBoostingRegressor (it existed only up to 0.23), so the
# frozen plan's "all remaining hyperparameters at library defaults" is implemented
# by simply not passing it.
FEATURE_NAMES = (
    [f"pose_{j}" for j in range(8)]
    + [f"fisher_{j}" for j in range(7)]
    + [f"dpose_{j}" for j in range(8)]
    + [f"dfisher_{j}" for j in range(7)]
    + [f"d2pose_{j}" for j in range(8)]
    + [f"d2fisher_{j}" for j in range(7)]
    + ["side_right", "d1_valid", "d2_valid"]
)

FORBIDDEN_SUBSTRINGS = ("gt", "truth", "target", "error", "r_t", "stage",
                        "class", "label", "y_gt", "flip", "agreement")


def build_features(pop: dict, z_pr: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Deployment-visible causal feature matrix.

    Returns (X, d1_valid_mask, d2_valid_mask). Difference features are anchored to
    the record boundary: the anchor frame is the highest index in the same record
    that precedes this frame and has a defined lower-order difference.
    """
    pose = pop["P"].astype(np.float64)
    rec = pop["record"]
    n = pose.shape[0]

    d1 = np.zeros_like(pose)
    d1f = np.zeros_like(z_pr)
    d1_valid = np.zeros(n, dtype=bool)
    d2 = np.zeros_like(pose)
    d2f = np.zeros_like(z_pr)
    d2_valid = np.zeros(n, dtype=bool)

    bounds = {}
    cursor = 0
    for stem in pop["files"]:
        k = int((rec == C.record_stem(stem)).sum())
        if k:
            bounds[stem] = (cursor, cursor + k)
            cursor += k
    assert cursor == n, (cursor, n)

    for stem, (a, b) in bounds.items():
        if b - a >= 2:
            d1[a + 1:b] = pose[a + 1:b] - pose[a:b - 1]
            d1f[a + 1:b] = z_pr[a + 1:b] - z_pr[a:b - 1]
            d1_valid[a + 1:b] = True
        # Second difference anchored to the frame in this record that has a defined
        # first difference and STRICTLY PRECEDES the current frame. An index-array
        # `maximum.accumulate` would return the current frame itself, so the
        # accumulated "last defined" array is shifted by one frame before use, and
        # the sentinel for "no defined predecessor yet" is -1 (valid for the whole
        # population, not just an offset record start).
        idx = np.arange(a, b)
        last_def = np.maximum.accumulate(np.where(d1_valid[a:b], idx, -1))
        prev_def = np.empty_like(last_def)
        prev_def[0] = -1
        prev_def[1:] = last_def[:-1]
        sel = (prev_def >= 0) & d1_valid[a:b]
        if sel.any():
            d2[a:b][sel] = d1[a:b][sel] - d1[prev_def[sel]]
            d2f[a:b][sel] = d1f[a:b][sel] - d1f[prev_def[sel]]
            d2_valid[a:b][sel] = True

    side_right = (pop["side"] == "right").astype(np.float64)
    X = np.column_stack([
        pose, z_pr, d1, d1f, d2, d2f,
        side_right,
        d1_valid.astype(np.float64), d2_valid.astype(np.float64),
    ]).astype(np.float32)
    assert X.shape == (n, C.N_BACKBONE_FEATURES), X.shape
    assert np.isfinite(X).all(), "non-finite feature value"
    return X, d1_valid, d2_valid


def main() -> int:
    C.ensure_dirs()
    t = C.Tee(os.path.join(C.LOGS, "task_error_predictor_stdout.txt"))
    C.banner(t, "GATE 4A — CANDIDATE 2: task-error predictor (stage-grouped OOF)")

    t.log("[1] population + frozen target + deployment features")
    pop = C.build_population(require_expected=True)
    head, mu, sd = C.load_frozen_head()
    sigma = C.load_db9_sigma()
    z_gt = C.pose_fisher(head, mu, sd, pop["G"])
    z_pr = C.pose_fisher(head, mu, sd, pop["P"])
    r = C.fisher_error(z_pr, z_gt, sigma)
    t.log(f"    population n     : {pop['n']}")
    t.log(f"    target r median  : {np.median(r):.6f}  (Gate3B record "
          f"{C.GATE3B_TARGET_RECORD['median']:.6f})")

    X, d1_valid, d2_valid = build_features(pop, z_pr)
    t.log(f"    feature matrix   : {X.shape} dtype {X.dtype}")
    t.log(f"    d1 defined       : {int(d1_valid.sum())} / {pop['n']} "
          f"(anchors excluded: {int((~d1_valid).sum())})")
    t.log(f"    d2 defined       : {int(d2_valid.sum())} / {pop['n']} "
          f"(2nd-frame excluded: {int((~d2_valid).sum())})")

    leak = [n for n in FEATURE_NAMES
            if any(s in n.lower() for s in FORBIDDEN_SUBSTRINGS)]
    t.log(f"    forbidden-name scan: {leak if leak else 'CLEAN'}")
    assert not leak
    assert "stage" not in [s.lower() for s in FEATURE_NAMES]

    t.log()
    t.log("[2] stage-grouped folds (GroupKFold, no shuffle -> deterministic)")
    groups = pop["stage"]
    stage_list = sorted(set(groups.tolist()))
    t.log(f"    n groups (stages): {len(stage_list)}  "
          f"(expected {C.EXPECTED_STAGES})")
    assert len(stage_list) == C.EXPECTED_STAGES

    gkf = GroupKFold(n_splits=5)
    fold_of = np.full(pop["n"], -1, dtype=np.int64)
    fold_assign = []
    for f, (tr, te) in enumerate(gkf.split(np.zeros(pop["n"]), groups=groups)):
        fold_of[te] = f
        tr_stages = sorted(set(groups[tr].tolist()))
        te_stages = sorted(set(groups[te].tolist()))
        assert not (set(tr_stages) & set(te_stages)), "fold stages overlap -> STOP"
        fold_assign.append({
            "fold": f, "n_train": int(tr.size), "n_test": int(te.size),
            "train_stages": tr_stages, "test_stages": te_stages,
        })
        t.log(f"    fold {f}: train {tr.size:>6} ({len(tr_stages)} stages)  "
              f"test {te.size:>6} ({len(te_stages)} stages)")
    assert (fold_of >= 0).all(), "some sample received no fold"
    stage_fold = {}
    for s in stage_list:
        fs = sorted(set(fold_of[groups == s].tolist()))
        assert len(fs) == 1, f"stage {s} spans folds {fs}"
        stage_fold[s] = int(fs[0])
    t.log(f"    stage -> fold map: {stage_fold}")

    t.log()
    t.log("[3] out-of-fold fitting (no hyperparameter selection from folds)")
    oof = np.full(pop["n"], np.nan, dtype=np.float64)
    models = []
    n_converged = 0
    for f in range(5):
        te = np.flatnonzero(fold_of == f)
        tr = np.flatnonzero(fold_of != f)
        assert not (set(groups[tr].tolist()) & set(groups[te].tolist()))
        t0 = time.time()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            model = GradientBoostingRegressor(**MODEL_KWARGS)
            model.fit(X[tr], r[tr])
            conv = [str(w.message) for w in caught
                    if "converge" in str(w.message).lower()]
        assert not conv, (
            f"fold {f}: quantile booster did not converge under the frozen fixed "
            f"configuration -> CANDIDATE 2 NOT EVALUABLE AS SPECIFIED: {conv[:2]}")
        n_converged += 1
        oof[te] = model.predict(X[te])
        models.append({
            "fold": f, "n_train": int(tr.size), "n_test": int(te.size),
            "test_stages": fold_assign[f]["test_stages"],
            "seconds": float(time.time() - t0),
            "converged": True,
        })
        t.log(f"    fold {f}: fit {tr.size:>6} -> predict {te.size:>6}  "
              f"{time.time() - t0:6.1f}s  converged=True")

    assert np.isfinite(oof).all(), "OOF score has non-finite values"
    assert int(np.isfinite(oof).sum()) == pop["n"]

    # proof that no score came from a model that saw its own stage
    for s in stage_list:
        m = groups == s
        f_own = stage_fold[s]
        tr_mask = fold_of != f_own
        assert not (tr_mask & m).any(), f"stage {s} used in its own training fold"
    t.log(f"    OOF coverage     : {int(np.isfinite(oof).sum())} / {pop['n']} "
          f"(no sample double-scored, no sample unscored)")

    t.log()
    t.log("[4] leakage self-checks")
    corr_stage = np.corrcoef(fold_of.astype(np.float64), r)[0, 1]
    t.log(f"    corr(fold_index, r) = {corr_stage:+.6f} (fold index is not a "
          f"feature; shown only to document fold balance)")
    t.log(f"    feature/target correlation maxima (top 5):")
    cors = []
    for j, name in enumerate(FEATURE_NAMES):
        xj = X[:, j].astype(np.float64)
        if xj.std() > 0:
            cors.append((abs(float(np.corrcoef(xj, r)[0, 1])), name))
    cors.sort(reverse=True)
    for v, name in cors[:5]:
        t.log(f"        {name:<14} |corr| = {v:.4f}")
    t.log("    (high single-feature correlation is allowed and expected: these are "
          "deployment-visible inputs, not the target)")

    C.write_csv(
        os.path.join(C.ART, "TASK_ERROR_PREDICTOR_OOF.csv"),
        [{"idx": int(i), "record": str(pop["record"][i]), "side": str(pop["side"][i]),
          "stage": str(pop["stage"][i]), "fold": int(fold_of[i]),
          "u_ERR": float(oof[i]), "r_true": float(r[i])}
         for i in range(pop["n"])],
        ["idx", "record", "side", "stage", "fold", "u_ERR", "r_true"],
    )

    summary = {
        "artifact": "TASK_ERROR_PREDICTOR_SUMMARY.json",
        "plan_sha256": C.sha256_file(os.path.join(C.LANE, "GATE4A_PLAN.md")),
        "role": "exploratory feasibility score generator; NOT conformalized; "
                "NOT a gate; NOT calibrated",
        "n_samples": pop["n"],
        "features": FEATURE_NAMES,
        "n_features": len(FEATURE_NAMES),
        "n_backbone_features_expected": C.N_BACKBONE_FEATURES,
        "model": {"class": "sklearn.ensemble.GradientBoostingRegressor",
                  "kwargs": MODEL_KWARGS,
                  "hyperparameters_tuned": "NO"},
        "folds": fold_assign,
        "stage_to_fold": stage_fold,
        "n_models_converged": n_converged,
        "oof_coverage": int(np.isfinite(oof).sum()),
        "oof_stats": C.qstats(oof),
        "target_stats": C.qstats(r),
        "anchoring_rule": {
            "d1": "first frame of each record excluded (d1_valid=0), feature set to 0",
            "d2": "second frame of each record excluded (d2_valid=0), feature set to 0",
            "no_centered_or_forward_window": True,
            "future_frame_used": "NO",
        },
        "stage_used_as": "GROUPING VARIABLE ONLY",
        "group_stage_disjointness_asserted": True,
        "gt_in_features": "NO",
        "target_in_features": "NO",
    }
    C.write_json(os.path.join(C.ART, "TASK_ERROR_PREDICTOR_SUMMARY.json"), summary)

    spec = {
        "artifact": "TASK_ERROR_PREDICTOR_SPEC.json",
        "plan_sha256": summary["plan_sha256"],
        "purpose": "feature/model/split specification of CANDIDATE 2, frozen before "
                   "any score-vs-target relationship was computed",
        "deployment_visible_features": {
            "A_current_predicted_trusted8_pose": FEATURE_NAMES[0:8],
            "B_current_predicted_fisher": FEATURE_NAMES[8:15],
            "C_within_record_first_differences": FEATURE_NAMES[15:30],
            "D_within_record_second_differences": FEATURE_NAMES[30:45],
            "E_hand_side_metadata": ["side_right"],
            "F_difference_validity_flags": ["d1_valid", "d2_valid"],
        },
        "explicitly_excluded_features": [
            "GT pose", "GT Fisher", "r_t / any target", "stage label",
            "DB9 class label", "hard class agreement", "Y_GT",
            "any future sample", "any GT-derived quantity",
        ],
        "feature_count": len(FEATURE_NAMES),
        "model": {"class": "sklearn.ensemble.GradientBoostingRegressor",
                  "loss": "quantile", "alpha": 0.90, "kwargs": MODEL_KWARGS},
        "grouping_scheme": {
            "group_variable": "stage (activity label)",
            "n_groups": len(stage_list),
            "cv": "sklearn.model_selection.GroupKFold(n_splits=5)",
            "shuffle": False,
            "both_hands_of_a_stage_share_a_fold": True,
            "stage_used_as_feature": False,
            "hyperparameter_selection_from_folds": "NONE",
        },
        "oof_guarantee": "every eligible sample is scored by a model trained only on "
                         "the other folds' stage groups; asserted in code",
    }
    C.write_json(os.path.join(C.ART, "TASK_ERROR_PREDICTOR_SPEC.json"), spec)

    np.savez_compressed(os.path.join(C.WORK, "task_error_oof.npz"),
                        oof=oof, fold_of=fold_of, r=r)
    t.log()
    t.log("wrote artifacts/TASK_ERROR_PREDICTOR_OOF.csv, "
          "TASK_ERROR_PREDICTOR_SUMMARY.json, TASK_ERROR_PREDICTOR_SPEC.json, "
          "work/task_error_oof.npz")
    t.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
