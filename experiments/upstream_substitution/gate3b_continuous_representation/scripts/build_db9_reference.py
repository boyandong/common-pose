#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GATE 3B — build the DB9-only Fisher reference scales and freeze LDA geometry.

This derives normalization constants EXCLUSIVELY from the frozen DB9 training
corpus (the exact corpus used to fit the aggregate frozen head).  It never reads
emg2pose data and never inspects any Gate3B outcome.

Outputs (written to the Gate3B lane's artifacts/):
    FISHER_DB9_REFERENCE_SCALE.json

Run:
  /root/miniconda3/envs/emg2pose-gate3/bin/python -X utf8 build_db9_reference.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import joblib
import numpy as np
import scipy.io as sio

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
ART = os.path.join(LANE, "artifacts")
os.makedirs(ART, exist_ok=True)

DB9_EXTRACTED = "/root/data/ninapro_db9/extracted"
FROZEN_SUBSET = ("/root/work/common-pose/audits/db9/trusted_pose/"
                 "TRUSTED_DB9_POSE_v1.json")
FROZEN_HEAD = "/root/work/gate3_work/frozen_head/frozen_db9_trusted8_lda.joblib"

SEG_CAP = 200
CORE_FRAC = 0.6
AGREE_IDS = (1, 2, 3, 4, 5, 6, 7, 8)

DB9_ORDER = ["CMC1_f", "CMC1_a", "MCP1", "IP1", "MCP2_f", "MCP2_a", "PIP2",
             "MCP3_f", "PIP3", "MCP4_f", "MCP4_a", "PIP4", "CMC5", "MCP5_f",
             "MCP5_a", "PIP5", "DIP2", "DIP3", "DIP4", "DIP5", "WRIST_F", "WRIST_A"]
TRUSTED8_DB9_COLS = [DB9_ORDER.index(n) for n in
                     ["MCP1", "IP1", "MCP2_f", "PIP2", "MCP3_f", "MCP4_f",
                      "MCP5_f", "PIP5"]]

log_lines: list[str] = []


def log(m: str = "") -> None:
    print(m, flush=True)
    log_lines.append(m)


def segments(stim, rerep, exclude_rest=True):
    ks, rs = np.asarray(stim).ravel(), np.asarray(rerep).ravel()
    n = min(ks.size, rs.size)
    out, start = [], 0
    for i in range(1, n + 1):
        if i == n or ks[i] != ks[start] or rs[i] != rs[start]:
            st, rp = int(ks[start]), int(rs[start])
            if not (exclude_rest and (st == 0 or rp == 0)):
                out.append({"stim": st, "rep": rp, "start": start, "end": i - 1,
                            "n": i - start})
            start = i
    return out


def core(seg, frac=CORE_FRAC):
    n = seg["n"]
    k = max(1, int(round(n * frac)))
    a = seg["start"] + (n - k) // 2
    return a, a + k


def load_mat(path):
    m = sio.loadmat(path, squeeze_me=True, struct_as_record=False)
    base = os.path.basename(path)
    d = {k: m[k] for k in ("angles", "glove", "restimulus", "rerepetition",
                           "stimulus", "repetition", "subject", "exercise") if k in m}
    d["global_key"] = int(base.split("_")[0].lstrip("Ss"))
    d["name"] = base
    return d


def load_exercise_b():
    import glob
    files = sorted(glob.glob(os.path.join(DB9_EXTRACTED, "s_*_angles", "*.mat")))
    keep = []
    for f in files:
        d = load_mat(f)
        segs = segments(d["restimulus"], d["rerepetition"])
        stims = sorted({s["stim"] for s in segs})
        if stims != list(range(1, 18)):
            continue
        idx = {}
        for sg in segs:
            idx.setdefault(sg["stim"], []).extend(range(*core(sg)))
        if 6 not in idx or 11 not in idx:
            continue
        keep.append({"name": d["name"], "subject": d["global_key"],
                     "angles": d["angles"], "idx": idx})
    return keep


def collect(fl, cols, keep_ids):
    Xs, ys, ss = [], [], []
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
    return (np.vstack(Xs), np.concatenate(ys), np.concatenate(ss))


def main() -> int:
    t0 = time.time()
    log("=" * 78)
    log("GATE 3B — DB9-ONLY FISHER REFERENCE SCALES")
    log("=" * 78)

    bundle = joblib.load(FROZEN_HEAD)
    head, mu, sd = bundle["head"], bundle["mu"], bundle["sd"]
    meta = bundle["meta"]

    log("[1] frozen head geometry")
    log(f"    solver            : {head.solver}")
    log(f"    shrinkage         : {head.shrinkage}")
    log(f"    classes           : {list(head.classes_)}")
    log(f"    n_features_in_    : {head.n_features_in_}")
    log(f"    scalings_ shape   : {getattr(head, 'scalings_', np.zeros((0, 0))).shape}")
    log(f"    xbar_ present     : {hasattr(head, 'xbar_')}")
    evr = getattr(head, "explained_variance_ratio_", None)
    log(f"    explained_variance_ratio_ : "
        f"{None if evr is None else np.round(evr, 8).tolist()}")
    log(f"    sum evr           : {None if evr is None else float(np.sum(evr))}")

    # empirical Fisher dimensionality check on a tiny probe
    probe = np.zeros((3, 8), dtype=np.float64)
    z_probe = head.transform(probe)
    log(f"    transform dim     : {z_probe.shape[1]}")
    n_features = int(head.n_features_in_)
    n_classes = len(head.classes_)
    expected_dim = min(n_features, n_classes - 1)
    log(f"    expected dim      : min({n_features}, {n_classes}-1) = {expected_dim}")
    if z_probe.shape[1] != expected_dim:
        log("    !! Fisher dimension does not match expectation")

    # centering check: transform(x) == (x - xbar_) @ scalings_
    if hasattr(head, "xbar_") and hasattr(head, "scalings_"):
        x = np.random.RandomState(0).randn(5, 8)
        a = head.transform(x)
        b = (x - head.xbar_) @ head.scalings_
        log(f"    transform == (x - xbar_) @ scalings_ : "
            f"{bool(np.allclose(a, b, atol=1e-12))}  "
            f"max|diff| {float(np.abs(a - b).max()):.3e}")
        log(f"    xbar_ (DB9 feature mean) : {np.round(head.xbar_, 6).tolist()}")
    log()

    log("[2] rebuild the frozen DB9 training corpus (identical protocol)")
    fl = load_exercise_b()
    X, y, s = collect(fl, TRUSTED8_DB9_COLS, AGREE_IDS)
    log(f"    files {len(fl)}  X={X.shape}  classes={sorted(set(y.tolist()))}  "
        f"subjects={len(set(s.tolist()))}")
    if X.shape[0] != meta["train_frames"]:
        log(f"    !! frame count {X.shape[0]} != frozen head train_frames "
            f"{meta['train_frames']}")
    if not np.allclose(X.mean(0), meta["standardisation_mu"], atol=1e-12):
        log("    !! DB9 feature mean does not match frozen head standardisation_mu")
    if not np.allclose(X.std(0), meta["standardisation_sd"], atol=1e-12):
        log("    !! DB9 feature std does not match frozen head standardisation_sd")
    log("    corpus/mu/sd consistency: "
        f"{bool(np.allclose(X.mean(0), meta['standardisation_mu'], atol=1e-12))} / "
        f"{bool(np.allclose(X.std(0), meta['standardisation_sd'], atol=1e-12))}")
    log()

    log("[3] DB9 Fisher reference")
    Xz = (X - mu) / sd
    z_db9 = head.transform(Xz)
    log(f"    z_DB9 shape       : {z_db9.shape}")
    sigma_db9 = z_db9.std(axis=0, ddof=0)
    sigma_db9_ddof1 = z_db9.std(axis=0, ddof=1)
    log(f"    sigma_DB9 (ddof=0): {np.round(sigma_db9, 8).tolist()}")
    log(f"    sigma_DB9 (ddof=1): {np.round(sigma_db9_ddof1, 8).tolist()}")
    log(f"    z_DB9 per-component mean: {np.round(z_db9.mean(0), 8).tolist()}")

    # DB9 score-space reference.
    # The plan's class-affinity profile is the head's own 8-class log-likelihood
    # geometry:  score_k(x) = -0.5 * ||x @ scalings_ - class_means_[k]||^2 + log prior_k.
    # This is computed here (not via decision_function, which exposes only 7 columns)
    # so that the score reference and the analysis use exactly the same construction.
    scal = head.scalings_
    cmeans = head.means_ @ scal
    logpri = np.log(head.priors_)

    def class_scores(xz: np.ndarray) -> np.ndarray:
        z = xz @ scal
        d2 = ((z[:, None, :] - cmeans[None, :, :]) ** 2).sum(-1)
        return -0.5 * d2 + logpri[None, :]

    scores_db9 = class_scores(Xz)
    log(f"    DB9 affinity score matrix : {scores_db9.shape}")
    _chk = np.argmax(scores_db9, axis=1)
    _direct = np.array([int(np.flatnonzero(head.classes_ == c)[0])
                        for c in head.predict(Xz)])
    log(f"    affinity argmax == head.predict : {bool(np.array_equal(_chk, _direct))}")

    score_sigma_db9 = scores_db9.std(axis=0, ddof=0)
    log(f"    DB9 per-class score sigma (ddof=0): "
        f"{np.round(score_sigma_db9, 8).tolist()}")
    log(f"    DB9 per-class score sigma (ddof=1): "
        f"{np.round(scores_db9.std(axis=0, ddof=1), 8).tolist()}")
    log(f"    DB9 per-class score mean          : "
        f"{np.round(scores_db9.mean(0), 8).tolist()}")

    # class means in Fisher space (descriptive geometry reference)
    class_means = {int(c): np.round(z_db9[y == c].mean(0), 6).tolist()
                   for c in sorted(set(y.tolist()))}
    log()

    art = {
        "artifact": "FISHER_DB9_REFERENCE_SCALE.json",
        "role": "DB9-only Fisher and score reference scales for GATE 3B",
        "provenance": {
            "source": "frozen DB9 training corpus, identical protocol to the frozen head",
            "frozen_head_joblib": FROZEN_HEAD,
            "frozen_subset": FROZEN_SUBSET,
            "emg2pose_data_used": "NO",
            "gate3b_outcome_inspected": "NO",
            "db9_files": len(fl),
            "db9_frames": int(X.shape[0]),
            "db9_subjects": int(len(set(s.tolist()))),
            "db9_classes": sorted(int(c) for c in set(y.tolist())),
        },
        "frozen_head_geometry": {
            "lda_solver": head.solver,
            "lda_shrinkage": head.shrinkage,
            "classes": [int(c) for c in head.classes_],
            "n_features_in": n_features,
            "fisher_dimension": int(z_probe.shape[1]),
            "fisher_dimension_expected": int(expected_dim),
            "scalings_shape": list(getattr(head, "scalings_", np.zeros((0, 0))).shape),
            "xbar_present": bool(hasattr(head, "xbar_")),
            "xbar": (head.xbar_.tolist() if hasattr(head, "xbar_") else None),
            "explained_variance_ratio":
                (evr.tolist() if evr is not None else None),
            "explained_variance_ratio_sum":
                (float(np.sum(evr)) if evr is not None else None),
            "transform_is_x_minus_xbar_times_scalings":
                bool(hasattr(head, "xbar_") and hasattr(head, "scalings_") and
                     np.allclose(head.transform(np.random.RandomState(0).randn(5, 8)),
                                 (np.random.RandomState(0).randn(5, 8) - head.xbar_)
                                 @ head.scalings_, atol=1e-9)),
        },
        "db9_corpus_consistency": {
            "frames_match_frozen_head": int(X.shape[0]) == meta["train_frames"],
            "mu_matches": bool(np.allclose(X.mean(0), meta["standardisation_mu"],
                                           atol=1e-12)),
            "sd_matches": bool(np.allclose(X.std(0), meta["standardisation_sd"],
                                           atol=1e-12)),
        },
        "fisher_component_sigma_db9": sigma_db9.tolist(),
        "fisher_component_sigma_db9_ddof1": sigma_db9_ddof1.tolist(),
        "fisher_component_mean_db9": z_db9.mean(0).tolist(),
        "fisher_class_means_db9": class_means,
        "score_centered_sigma_db9": score_sigma_db9.tolist(),
        "score_centered_sigma_db9_ddof1": scores_db9.std(axis=0, ddof=1).tolist(),
        "score_mean_db9": scores_db9.mean(0).tolist(),
        "score_construction": "score_k(x) = -0.5 * ||x @ scalings_ - "
                              "class_means_[k]||^2 + log prior_k  (the frozen head's "
                              "own 8-class log-likelihood geometry; decision_function "
                              "exposes only n_classes-1 = 7 columns)",
        "score_classes_order": [int(c) for c in head.classes_],
        "score_argmax_matches_head_predict": bool(np.array_equal(_chk, _direct)),
        "normalization_rule": {
            "fisher_distance": "d_norm = sqrt( sum_j ((z_PRED_j - z_GT_j) / "
                               "sigma_DB9_j)^2 ), sigma from DB9 training only",
            "score_distance": "normalized L2 using per-score DB9 centered-score "
                              "sigma",
            "epsilon_declared": 1e-12,
            "emg2pose_derived_scaling": "NONE",
        },
        "sha256_of_this_file_note": "hash recorded separately in the plan",
    }
    out = os.path.join(ART, "FISHER_DB9_REFERENCE_SCALE.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, ensure_ascii=False)
    h = hashlib.sha256(open(out, "rb").read()).hexdigest()
    log(f"[4] wrote {out}")
    log(f"    sha256 {h}")
    log(f"elapsed {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
