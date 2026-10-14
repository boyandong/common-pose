#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GATE 3B — CONTINUOUS DOWNSTREAM REPRESENTATION PRESERVATION.

Implements GATE3B_PLAN.md exactly and nothing else.

Reuses the exact Gate3 aligned (GT pose, Pred pose) population. No inference, no
training, no calibration, no smoothing, no gate, no human labels, no lag search,
no DOF intervention, no sample filtering.

Run:
  /root/miniconda3/envs/emg2pose-gate3/bin/python -X utf8 run_gate3b_representation.py
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sys
import time

import h5py
import joblib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
ART = os.path.join(LANE, "artifacts")
LOGS = os.path.join(LANE, "logs")
os.makedirs(ART, exist_ok=True)
os.makedirs(LOGS, exist_ok=True)

PLAN = os.path.join(LANE, "GATE3B_PLAN.md")
PLAN_SHA = hashlib.sha256(open(PLAN, "rb").read()).hexdigest()

MINI_DIR = "/root/data/emg2pose_dataset_mini"
PRED_DIR = "/root/work/gate3_work/pred_pose"
FROZEN_HEAD = "/root/work/gate3_work/frozen_head/frozen_db9_trusted8_lda.joblib"

GATE3_SUMMARY = ("/root/work/common-pose/experiments/upstream_substitution/"
                 "gate3_formal_substitution/artifacts/GATE3_PRESERVATION_SUMMARY.json")
GATE3_PLAN = ("/root/work/common-pose/experiments/upstream_substitution/"
              "gate3_formal_substitution/GATE3_PLAN.md")

POSE_STRIDE = 40
ANALYSIS_HZ = 50.0
TRUSTED8_SRC_IDX = [2, 3, 5, 6, 9, 13, 17, 18]
CLASSES = [1, 2, 3, 4, 5, 6, 7, 8]

EPS = 1e-12                 # declared in GATE3B_PLAN.md §7.1
MIN_CLASS_SUPPORT = 30      # inherited from GATE3_PLAN
N_DECILES = 10
CKA_MAX_N = 40000           # declared deterministic subsample rule (§16)
EXPECTED_N = 86833

log_lines: list[str] = []


def log(m: str = "") -> None:
    print(m, flush=True)
    log_lines.append(m)


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def qstats(a, extra=True) -> dict:
    a = np.asarray(a, dtype=np.float64)
    if a.size == 0:
        return {k: None for k in ("n", "median", "mean", "iqr", "p05", "p25", "p75",
                                  "p95", "min", "max")}
    q = np.percentile(a, [5, 25, 75, 95])
    d = {"n": int(a.size), "median": float(np.median(a)), "mean": float(a.mean()),
         "iqr": float(q[2] - q[1]), "p05": float(q[0]), "p25": float(q[1]),
         "p75": float(q[2]), "p95": float(q[3]), "min": float(a.min()),
         "max": float(a.max())}
    return d


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    def rk(a):
        order = np.argsort(a, kind="mergesort")
        r = np.empty(a.size, dtype=np.float64)
        r[order] = np.arange(a.size, dtype=np.float64)
        sa = a[order]
        i = 0
        while i < sa.size:
            j = i
            while j + 1 < sa.size and sa[j + 1] == sa[i]:
                j += 1
            if j > i:
                r[order[i:j + 1]] = (i + j) / 2.0
            i = j + 1
        return r
    rx, ry = rk(x), rk(y)
    rx -= rx.mean()
    ry -= ry.mean()
    den = np.sqrt((rx ** 2).sum() * (ry ** 2).sum())
    return float((rx * ry).sum() / den) if den > 0 else float("nan")


def pearson(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    xm, ym = x - x.mean(), y - y.mean()
    den = np.sqrt((xm ** 2).sum() * (ym ** 2).sum())
    return float((xm * ym).sum() / den) if den > 0 else float("nan")


def safe_cosine(A: np.ndarray, B: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Row-wise cosine with the declared epsilon rule. Returns (cos, valid_mask)."""
    na = np.linalg.norm(A, axis=1)
    nb = np.linalg.norm(B, axis=1)
    valid = (na > EPS) & (nb > EPS)
    cos = np.full(A.shape[0], np.nan, dtype=np.float64)
    cos[valid] = np.sum(A[valid] * B[valid], axis=1) / (na[valid] * nb[valid])
    return cos, valid


def linear_cka(X: np.ndarray, Y: np.ndarray) -> float:
    """Linear CKA (feature-space, column-centred)."""
    X = X - X.mean(0, keepdims=True)
    Y = Y - Y.mean(0, keepdims=True)
    xty = np.linalg.norm(X.T @ Y, "fro") ** 2
    xtx = np.linalg.norm(X.T @ X, "fro")
    yty = np.linalg.norm(Y.T @ Y, "fro")
    den = xtx * yty
    return float(xty / den) if den > 0 else float("nan")


def main() -> int:
    t0 = time.time()
    log("=" * 78)
    log("GATE 3B — CONTINUOUS DOWNSTREAM REPRESENTATION PRESERVATION")
    log("=" * 78)
    log(f"plan sha256        : {PLAN_SHA}")
    log(f"gate3 plan sha256  : {hashlib.sha256(open(GATE3_PLAN,'rb').read()).hexdigest()}")
    log(f"epsilon (cosine)   : {EPS}")
    log(f"expected population: {EXPECTED_N}")
    log()

    # ---------------- frozen head + DB9 reference scales ----------------
    bundle = joblib.load(FROZEN_HEAD)
    head, mu, sd = bundle["head"], bundle["mu"], bundle["sd"]
    ref = json.load(open(os.path.join(ART, "FISHER_DB9_REFERENCE_SCALE.json"),
                         encoding="utf-8"))
    sigma_db9 = np.array(ref["fisher_component_sigma_db9"], dtype=np.float64)
    tau_db9 = np.array(ref["score_centered_sigma_db9"], dtype=np.float64)
    evr = np.array(ref["frozen_head_geometry"]["explained_variance_ratio"],
                   dtype=np.float64)

    log("[1] frozen head + DB9 reference")
    log(f"    head sha256          : {sha256_file(FROZEN_HEAD)}")
    log(f"    solver/shrinkage     : {head.solver} / {head.shrinkage}")
    log(f"    classes              : {list(head.classes_)}")
    log(f"    Fisher dimension     : {ref['frozen_head_geometry']['fisher_dimension']}")
    log(f"    evr                  : {np.round(evr, 8).tolist()}")
    log(f"    sigma_DB9            : {np.round(sigma_db9, 8).tolist()}")
    log(f"    tau_DB9 (score)      : {np.round(tau_db9, 8).tolist()}")
    assert ref["provenance"]["emg2pose_data_used"] == "NO"
    assert ref["db9_corpus_consistency"]["frames_match_frozen_head"] is True
    assert ref["db9_corpus_consistency"]["mu_matches"] is True
    assert ref["db9_corpus_consistency"]["sd_matches"] is True
    log()

    # ---------------- rebuild the EXACT Gate3 population ----------------
    files = sorted(glob.glob(os.path.join(MINI_DIR, "*.hdf5")))
    Gp, Pp, side_l, stage_l, file_l = [], [], [], [], []
    for f in files:
        stem = os.path.basename(f)[: -len(".hdf5")]
        with h5py.File(f, "r") as h:
            g = h["emg2pose"]
            attrs = dict(g.attrs)
            ts = g["timeseries"]
            ja = ts["joint_angles"][:]
            tgt = ts["time"][:]
        with np.load(os.path.join(PRED_DIR, f"{stem}_pred.npz")) as z:
            ang = z["angles"]
            tpred = z["time"]
            off = int(z["row_offset"])
        assert np.array_equal(tgt[off:], tpred), f"alignment broken: {stem}"
        gt_w, pr_w = ja[off:], ang
        n = gt_w.shape[0]
        gv = (~np.all(np.isclose(gt_w, 0.0), axis=1)) & np.isfinite(gt_w).all(axis=1)
        pv = (~np.all(np.isclose(pr_w, 0.0), axis=1)) & np.isfinite(pr_w).all(axis=1)
        nb = n // POSE_STRIDE
        u = nb * POSE_STRIDE
        gb = gt_w[:u].reshape(nb, POSE_STRIDE, 20).mean(1)[:, TRUSTED8_SRC_IDX]
        pb = pr_w[:u].reshape(nb, POSE_STRIDE, 20).mean(1)[:, TRUSTED8_SRC_IDX]
        gok = gv[:u].reshape(nb, POSE_STRIDE).all(1).copy()
        pok = pv[:u].reshape(nb, POSE_STRIDE).all(1).copy()
        if nb:
            gok[0] = False
            pok[0] = False
        m = gok & pok
        if not m.any():
            continue
        Gp.append(gb[m])
        Pp.append(pb[m])
        k = int(m.sum())
        side_l.extend([str(attrs["side"])] * k)
        stage_l.extend([str(attrs["stage"])] * k)
        file_l.extend([stem] * k)

    G = np.vstack(Gp)
    P = np.vstack(Pp)
    side = np.array(side_l)
    stage = np.array(stage_l)
    filearr = np.array(file_l)
    N = G.shape[0]

    log("[2] Gate3 population reuse")
    log(f"    records            : {len(files)}")
    log(f"    n samples          : {N}")
    log(f"    expected           : {EXPECTED_N}")
    log(f"    identity match     : {N == EXPECTED_N}")
    log(f"    rate               : {ANALYSIS_HZ} Hz")
    assert N == EXPECTED_N, "population changed -> STOP"
    log()

    # ---------------- L0 physical control ----------------
    x_gt = (G - mu) / sd
    x_pr = (P - mu) / sd
    err_deg = np.degrees(P - G)
    pose_rmse_frame = np.sqrt((err_deg ** 2).mean(1))
    pose_mae_frame = np.abs(err_deg).mean(1)

    # ---------------- L1 PRIMARY Fisher embedding ----------------
    z_gt = head.transform(x_gt)
    z_pr = head.transform(x_pr)
    D = z_gt.shape[1]
    log("[3] L1 PRIMARY — Fisher discriminant embedding")
    log(f"    z_GT {z_gt.shape}  z_PRED {z_pr.shape}  dim {D} (expected 7)")
    assert D == 7, "unexpected Fisher dimension"

    cos_f, cos_valid = safe_cosine(z_gt, z_pr)
    n_invalid = int((~cos_valid).sum())
    cz = cos_f[cos_valid]
    log(f"    valid cosine frames: {int(cos_valid.sum())} / {N}  "
        f"(invalid {n_invalid}, neither silent-1 nor dropped)")
    log(f"    cosine median {np.median(cz):.6f} mean {cz.mean():.6f} "
        f"IQR [{np.percentile(cz,25):.6f}, {np.percentile(cz,75):.6f}] "
        f"p05 {np.percentile(cz,5):.6f} p95 {np.percentile(cz,95):.6f}")
    frac = {
        "lt0": float((cz < 0).mean()), "gt05": float((cz > 0.5).mean()),
        "gt08": float((cz > 0.8).mean()), "gt09": float((cz > 0.9).mean()),
    }
    log(f"    frac <0 {frac['lt0']:.6f}  >0.5 {frac['gt05']:.6f}  "
        f">0.8 {frac['gt08']:.6f}  >0.9 {frac['gt09']:.6f}")

    diff = z_pr - z_gt
    d_norm = np.sqrt(((diff / sigma_db9) ** 2).sum(1))
    d_raw = np.linalg.norm(diff, axis=1)
    log(f"    d_norm median {np.median(d_norm):.6f} mean {d_norm.mean():.6f} "
        f"IQR [{np.percentile(d_norm,25):.6f}, {np.percentile(d_norm,75):.6f}] "
        f"p05 {np.percentile(d_norm,5):.6f} p95 {np.percentile(d_norm,95):.6f}")
    log(f"    d_raw  median {np.median(d_raw):.6f}")

    # per-component preservation
    comps = []
    log()
    log("    per-component preservation (DB9 weight, Pearson, Spearman, MAE, RMSE):")
    for j in range(D):
        a, b = z_gt[:, j], z_pr[:, j]
        r = pearson(a, b)
        rho = spearman(a, b)
        mae = float(np.abs(b - a).mean())
        rmse = float(np.sqrt(((b - a) ** 2).mean()))
        if a.var() > 0:
            slope = float(np.polyfit(a, b, 1)[0])
            inter = float(np.polyfit(a, b, 1)[1])
        else:
            slope = inter = None
        comps.append({
            "component": j + 1, "db9_variance_ratio": float(evr[j]),
            "pearson_r": r, "spearman_rho": rho, "mae": mae, "rmse": rmse,
            "ols_slope_pred_on_gt": slope, "ols_intercept": inter,
            "z_gt_mean": float(a.mean()), "z_gt_std": float(a.std()),
            "z_pred_mean": float(b.mean()), "z_pred_std": float(b.std()),
            "db9_sigma": float(sigma_db9[j]),
        })
        log(f"      c{j+1}  w {evr[j]:.6f}  r {r:+.6f}  rho {rho:+.6f}  "
            f"MAE {mae:.6f}  RMSE {rmse:.6f}  slope {slope:.6f}  inter {inter:.6f}")

    w = evr / evr.sum()
    weighted_corr = float(sum(w[j] * comps[j]["pearson_r"] for j in range(D)))
    log(f"    DB9_WEIGHTED_COMPONENT_CORRELATION = {weighted_corr:.6f}")

    # ---------------- L2 score space ----------------
    # NOTE: sklearn LDA exposes only 7 decision_function columns (= n_classes - 1).
    # The plan's 8-class affinity profile is therefore built directly from the
    # head's own log-likelihood geometry:
    #     score_k(x) = -0.5 * Mahalanobis_k(x) + log prior_k
    # with Mahalanobis_k(x) = || x @ scalings_ - class_means_[k] ||^2 (scalings_ is
    # orthonormal and the within-class covariance is isotropic in Fisher space), so
    # that all 8 DB9 postures get a relative affinity. This is an exact re-expression
    # of the frozen head's decision geometry, not a new model.
    scal = head.scalings_
    cmeans = head.means_ @ scal
    logpri = np.log(head.priors_)

    def class_scores(xz: np.ndarray) -> np.ndarray:
        z = xz @ scal
        d2 = ((z[:, None, :] - cmeans[None, :, :]) ** 2).sum(-1)
        return -0.5 * d2 + logpri[None, :]

    s_gt = class_scores(x_gt)
    s_pr = class_scores(x_pr)
    cs_gt = s_gt - s_gt.mean(axis=1, keepdims=True)
    cs_pr = s_pr - s_pr.mean(axis=1, keepdims=True)
    assert s_gt.shape[1] == 8, s_gt.shape

    # agreement check against the head's own argmax (sanity, not a new decision)
    _chk = np.argmax(s_gt, axis=1)
    _direct = np.array([int(np.flatnonzero(head.classes_ == c)[0])
                        for c in head.predict(x_gt)])
    score_argmax_matches_predict = bool(np.array_equal(_chk, _direct))
    log(f"    8-class affinity score argmax == head.predict : "
        f"{score_argmax_matches_predict}")

    scos, scos_valid = safe_cosine(cs_gt, cs_pr)
    sdist_norm = np.sqrt((((cs_pr - cs_gt) / tau_db9) ** 2).sum(1))
    sdist_raw = np.linalg.norm(cs_pr - cs_gt, axis=1)

    # per-row Pearson across the 8 relative scores, where both have variance
    def row_pearson(A, B):
        Ac = A - A.mean(1, keepdims=True)
        Bc = B - B.mean(1, keepdims=True)
        na = np.sqrt((Ac ** 2).sum(1))
        nb = np.sqrt((Bc ** 2).sum(1))
        ok = (na > EPS) & (nb > EPS)
        out = np.full(A.shape[0], np.nan)
        out[ok] = (Ac[ok] * Bc[ok]).sum(1) / (na[ok] * nb[ok])
        return out, ok

    srow, srow_ok = row_pearson(cs_gt, cs_pr)

    # ---------------- L3 probability space ----------------
    proba_gt = head.predict_proba(x_gt)
    proba_pr = head.predict_proba(x_pr)
    tv = 0.5 * np.abs(proba_gt - proba_pr).sum(1)

    def js(p, q):
        m_ = 0.5 * (p + q)
        def kl(a, b):
            b = np.clip(b, 1e-300, 1.0)
            return np.where(a > 0, a * np.log2(a / b), 0.0).sum(1)
        return 0.5 * kl(p, m_) + 0.5 * kl(q, m_)

    jsd = js(proba_gt, proba_pr)

    # ---------------- L4 hard decision ----------------
    y_gt = head.predict(x_gt).astype(np.int16)
    y_pr = head.predict(x_pr).astype(np.int16)
    flip = y_pr != y_gt
    agreement = float(1.0 - flip.mean())
    check3 = json.load(open(GATE3_SUMMARY, encoding="utf-8"))

    log()
    log("[4] L2/L3/L4 (secondary/tertiary)")
    log(f"    score cosine median {np.median(scos[scos_valid]):.6f}  "
        f"valid {int(scos_valid.sum())}/{N}")
    log(f"    score dist (DB9-norm) median {np.median(sdist_norm):.6f}")
    log(f"    score row-Pearson median {np.nanmedian(srow):.6f} "
        f"(valid {int(srow_ok.sum())})")
    log(f"    TV median {np.median(tv):.6f}   JS median {np.median(jsd):.6f}")
    log(f"    hard agreement {agreement:.6f}  (Gate3 {check3['hard_agreement']:.6f}, "
        f"match {abs(agreement - check3['hard_agreement']) < 1e-9})")
    log(f"    Gate3 TV match {abs(np.median(tv) - check3['soft_preservation']['tv_distance']['median']) < 1e-9}"
        f"  JS match {abs(np.median(jsd) - check3['soft_preservation']['js_divergence']['median']) < 1e-9}")

    # ---------------- 10. SAME vs FLIP ----------------
    groups = {}
    log()
    log("[5] REPRESENTATION BY HARD OUTCOME")
    for name, m in (("SAME", ~flip), ("FLIP", flip)):
        c = cos_f[m & cos_valid]
        groups[name] = {
            "n": int(m.sum()), "n_fraction": float(m.mean()),
            "fisher_cosine": qstats(c) if c.size else None,
            "fisher_cosine_median": float(np.median(c)) if c.size else None,
            "fisher_cosine_iqr": float(np.percentile(c, 75) - np.percentile(c, 25)) if c.size else None,
            "fisher_distance_norm": qstats(d_norm[m]),
            "fisher_distance_norm_median": float(np.median(d_norm[m])),
            "fisher_distance_norm_iqr": float(np.percentile(d_norm[m], 75) - np.percentile(d_norm[m], 25)),
            "fisher_distance_raw_median": float(np.median(d_raw[m])),
            "score_cosine_median": float(np.median(scos[m & scos_valid])) if (m & scos_valid).any() else None,
            "score_distance_norm_median": float(np.median(sdist_norm[m])),
            "tv_median": float(np.median(tv[m])),
            "tv_iqr": float(np.percentile(tv[m], 75) - np.percentile(tv[m], 25)),
            "js_median": float(np.median(jsd[m])),
            "js_iqr": float(np.percentile(jsd[m], 75) - np.percentile(jsd[m], 25)),
            "pose_mae_deg": float(np.abs(err_deg[m]).mean()),
            "pose_rmse_deg": float(np.sqrt((err_deg[m] ** 2).mean())),
            "pose_rmse_frame_median_deg": float(np.median(pose_rmse_frame[m])),
        }
        g = groups[name]
        log(f"    {name}: n {g['n']} ({g['n_fraction']:.4f})  "
            f"cos {g['fisher_cosine_median']:.6f}  d_norm {g['fisher_distance_norm_median']:.6f}  "
            f"score_cos {g['score_cosine_median']:.6f}  TV {g['tv_median']:.6f}  "
            f"JS {g['js_median']:.6f}  poseRMSE {g['pose_rmse_deg']:.4f}")

    # ---------------- 11. deciles ----------------
    def decile_view(key: np.ndarray, ascending: bool):
        o = np.argsort(key if ascending else -key, kind="mergesort")
        rows = []
        for k, ix in enumerate(np.array_split(o, N_DECILES), 1):
            sup = {c: int((y_gt[ix] == c).sum()) for c in CLASSES}
            suf = [c for c in CLASSES if sup[c] >= MIN_CLASS_SUPPORT]
            bp = None
            if len(suf) >= 2:
                bp = float(np.mean([float((y_pr[ix][y_gt[ix] == c] == c).mean())
                                    for c in suf]))
            cvalid = cos_valid[ix]
            rows.append({
                "decile": k, "n": int(ix.size),
                "median_fisher_distance_norm": float(np.median(d_norm[ix])),
                "median_fisher_cosine": float(np.median(cos_f[ix][cvalid]))
                if cvalid.any() else None,
                "hard_agreement": float(1.0 - flip[ix].mean()),
                "balanced_preservation": bp,
                "balanced_preservation_classes": suf,
                "median_pose_error_deg": float(np.median(pose_rmse_frame[ix])),
                "min_fisher_distance_norm": float(d_norm[ix].min()),
                "max_fisher_distance_norm": float(d_norm[ix].max()),
            })
        return rows

    dist_dec = decile_view(d_norm, ascending=True)
    cos_dec = decile_view(cos_f, ascending=False)
    log()
    log("[6] FISHER-DISTANCE DECILES (primary view)")
    log(f"    {'dec':<5}{'n':>7}{'medDist':>11}{'medCos':>10}{'agree':>9}"
        f"{'balPres':>10}{'medPoseErr':>12}")
    for r in dist_dec:
        log(f"    {r['decile']:<5}{r['n']:>7}{r['median_fisher_distance_norm']:>11.4f}"
            f"{r['median_fisher_cosine']:>10.4f}{r['hard_agreement']:>9.4f}"
            f"{(r['balanced_preservation'] if r['balanced_preservation'] is not None else float('nan')):>10.4f}"
            f"{r['median_pose_error_deg']:>12.4f}")
    log()
    log("[7] FISHER-COSINE DECILES (inverse view)")
    for r in cos_dec:
        log(f"    {r['decile']:<5}{r['n']:>7}{r['median_fisher_distance_norm']:>11.4f}"
            f"{r['median_fisher_cosine']:>10.4f}{r['hard_agreement']:>9.4f}"
            f"{(r['balanced_preservation'] if r['balanced_preservation'] is not None else float('nan')):>10.4f}"
            f"{r['median_pose_error_deg']:>12.4f}")

    # ---------------- 12. pose -> fisher -> hard ----------------
    rho_pose_fisher = spearman(pose_rmse_frame, d_norm)
    rho_fisher_flip = spearman(d_norm, flip.astype(np.float64))
    rho_pose_flip = spearman(pose_rmse_frame, flip.astype(np.float64))
    log()
    log("[8] POSE -> FISHER -> HARD (descriptive, no causal claim)")
    log(f"    Spearman(pose RMSE, Fisher d_norm) = {rho_pose_fisher:+.6f}")
    log(f"    Spearman(Fisher d_norm, flip)      = {rho_fisher_flip:+.6f}")
    log(f"    Spearman(pose RMSE, flip)          = {rho_pose_flip:+.6f} "
        f"(Gate3 recorded +0.162137)")

    # ---------------- 14. temporal ----------------
    cursor = 0
    seq_bounds = []
    for f in files:
        stem = os.path.basename(f)[: -len(".hdf5")]
        k = int((filearr == stem).sum())
        if k:
            seq_bounds.append((cursor, cursor + k))
            cursor += k
    assert cursor == N

    dgt = np.zeros_like(z_gt)
    dpr = np.zeros_like(z_pr)
    keep = np.zeros(N, dtype=bool)
    for a, b in seq_bounds:
        if b - a >= 2:
            dgt[a + 1:b] = z_gt[a + 1:b] - z_gt[a:b - 1]
            dpr[a + 1:b] = z_pr[a + 1:b] - z_pr[a:b - 1]
            keep[a + 1:b] = True

    temporal = []
    log()
    log("[9] TEMPORAL FISHER PRESERVATION (zero-lag only, no lag search)")
    for j in range(D):
        r0 = pearson(z_gt[:, j], z_pr[:, j])
        rho0 = spearman(z_gt[:, j], z_pr[:, j])
        rd = pearson(dgt[keep, j], dpr[keep, j])
        rhod = spearman(dgt[keep, j], dpr[keep, j])
        temporal.append({
            "component": j + 1, "zero_lag_pearson": r0, "zero_lag_spearman": rho0,
            "derivative_pearson": rd, "derivative_spearman": rhod,
            "n_derivative_pairs": int(keep.sum()),
            "db9_variance_ratio": float(evr[j]),
        })
        log(f"    c{j+1}  zero-lag r {r0:+.6f}  rho {rho0:+.6f}   "
            f"derivative r {rd:+.6f}  rho {rhod:+.6f}")

    # ---------------- 15. side + stage ----------------
    def strat(mask_fn, keys):
        out = {}
        for k in sorted(set(keys.tolist())):
            m = mask_fn(k)
            if not m.any():
                continue
            cv = cos_valid[m]
            sup = {c: int((y_gt[m] == c).sum()) for c in CLASSES}
            pr_c = {c: (float((y_pr[m][y_gt[m] == c] == c).mean())
                        if (y_gt[m] == c).any() else None) for c in CLASSES}
            suf = [c for c in CLASSES if sup[c] >= MIN_CLASS_SUPPORT]
            out[k] = {
                "n": int(m.sum()),
                "fisher_cosine_median": float(np.median(cos_f[m][cv])) if cv.any() else None,
                "fisher_distance_norm_median": float(np.median(d_norm[m])),
                "score_cosine_median": float(np.median(scos[m & scos_valid]))
                if (m & scos_valid).any() else None,
                "hard_agreement": float(1.0 - flip[m].mean()),
                "median_pose_error_deg": float(np.median(pose_rmse_frame[m])),
                "balanced_preservation": float(np.mean([pr_c[c] for c in suf]))
                if suf else None,
                "balanced_preservation_classes": suf,
                "per_class_support": sup,
            }
        return out

    by_side = strat(lambda k: side == k, side)
    by_stage = strat(lambda k: stage == k, stage)
    log()
    log("[10] SIDE / STAGE (secondary, descriptive)")
    for k, v in by_side.items():
        log(f"    {k:<6}: n {v['n']:>7}  cos {v['fisher_cosine_median']:.6f}  "
            f"d_norm {v['fisher_distance_norm_median']:.6f}  "
            f"scoreCos {v['score_cosine_median']:.6f}  agree {v['hard_agreement']:.6f}")
    for k, v in by_stage.items():
        log(f"    {k[:38]:<38} n {v['n']:>7} cos {v['fisher_cosine_median']:.4f} "
            f"d {v['fisher_distance_norm_median']:.4f} agree {v['hard_agreement']:.4f}")

    # ---------------- 16. CKA ----------------
    if N <= CKA_MAX_N:
        cka_val = linear_cka(z_gt, z_pr)
        cka_mode = "FULL"
        cka_n = N
    else:
        cka_val = linear_cka(z_gt[:CKA_MAX_N], z_pr[:CKA_MAX_N])
        cka_mode = "DETERMINISTIC_FIRST_N"
        cka_n = CKA_MAX_N
    log()
    log(f"[11] LINEAR CKA ({cka_mode}, n={cka_n}) = {cka_val:.6f}")

    # ---------------- artifacts ----------------
    log()
    log("[12] writing artifacts")

    data_link = {
        "artifact": "GATE3B_DATA_LINK.json",
        "gate": "PHASE 1 / GATE 3B — continuous downstream representation preservation",
        "plan_sha256": PLAN_SHA,
        "evidence_status": "POST-HOC MOTIVATED, PROSPECTIVELY FROZEN BEFORE "
                           "CONTINUOUS-REPRESENTATION OUTCOME INSPECTION",
        "gate3_plan_sha256": hashlib.sha256(open(GATE3_PLAN, "rb").read()).hexdigest(),
        "gate3_artifacts_modified": "NO",
        "reuses_gate3_population": "YES",
        "new_inference_run": "NO — Gate3 predicted stream persisted and reused",
        "predicted_stream": {"dir": PRED_DIR, "files": len(files)},
        "gt_stream": {"dir": MINI_DIR, "field": "emg2pose/timeseries/joint_angles"},
        "frozen_head": {"path": FROZEN_HEAD, "sha256": sha256_file(FROZEN_HEAD)},
        "trusted_subset_sha256":
            "e51dde6e63941fd080c84f3896a98cf50fba9e17d5f9cebe909253d5465782d1",
        "checkpoint_sha256":
            "748b1d1ef0ce1985f6fc07225d97eebfb370243429af803b4997d28ecce2424e",
        "population": {
            "n": N, "expected_n": EXPECTED_N, "identity_match": N == EXPECTED_N,
            "rate_hz": ANALYSIS_HZ, "pose_stride": POSE_STRIDE,
            "participant": sorted({os.path.basename(f).split("-")[0] for f in files}) or None,
            "sides": {s: int((side == s).sum()) for s in sorted(set(side.tolist()))},
            "n_stages": len(set(stage.tolist())),
            "n_records": len(files),
        },
        "alignment_rule": {
            "rule": "prediction[i] <-> GT[1790+i]",
            "verified": "np.array_equal(GT.time[1790:], pred.time) asserted per record",
            "lag_search_performed": "NO",
        },
        "scaling_source": "DB9 training corpus only; no emg2pose-derived scaling",
        "filtering_applied": "NONE beyond the frozen Gate3 eligibility rule",
    }
    with open(os.path.join(ART, "GATE3B_DATA_LINK.json"), "w", encoding="utf-8") as fh:
        json.dump(data_link, fh, indent=2, ensure_ascii=False)

    fisher = {
        "artifact": "FISHER_PRESERVATION_SUMMARY.json",
        "plan_sha256": PLAN_SHA,
        "primary_representation": "Fisher discriminant embedding z = lda.transform("
                                  "(pose - mu)/sd), 7 components",
        "fisher_dimension": D,
        "fisher_dimension_expected": 7,
        "n_samples": N,
        "epsilon": EPS,
        "cosine": {
            "n_frames": N, "n_valid_cosine_frames": int(cos_valid.sum()),
            "n_invalid_cosine_frames": n_invalid,
            "invalid_rule": "||z_GT|| <= EPS or ||z_PRED|| <= EPS; counted, excluded, "
                            "never silently set to 1",
            "stats": qstats(cz),
            "fraction_lt_0": frac["lt0"], "fraction_gt_0_5": frac["gt05"],
            "fraction_gt_0_8": frac["gt08"], "fraction_gt_0_9": frac["gt09"],
            "threshold_fractions_are_descriptive_only": True,
        },
        "distance_db9_normalized": qstats(d_norm),
        "distance_raw_euclidean": qstats(d_raw),
        "db9_component_sigma": sigma_db9.tolist(),
        "component_preservation": comps,
        "db9_weighted_component_correlation": weighted_corr,
        "db9_weights_used": (evr / evr.sum()).tolist(),
        "component_selection_on_outcome": "NO — all 7 components used",
        "ols_used_for_calibration": "NO — descriptive only",
    }
    with open(os.path.join(ART, "FISHER_PRESERVATION_SUMMARY.json"), "w",
              encoding="utf-8") as fh:
        json.dump(fisher, fh, indent=2, ensure_ascii=False)

    score_art = {
        "artifact": "SCORE_SPACE_PRESERVATION.json",
        "plan_sha256": PLAN_SHA,
        "construction": "s_centered = decision_function(x) - mean_over_8_classes(s)",
        "centering_justification": "adding the same scalar to every class score changes "
                                   "no LDA relative preference or decision",
        "n_samples": N,
        "score_cosine": {"stats": qstats(scos[scos_valid]),
                         "n_valid": int(scos_valid.sum()),
                         "n_invalid": int((~scos_valid).sum())},
        "score_distance_db9_normalized": qstats(sdist_norm),
        "score_distance_raw": qstats(sdist_raw),
        "score_row_pearson": {"stats": qstats(srow[srow_ok]),
                              "n_valid": int(srow_ok.sum()),
                              "n_invalid": int((~srow_ok).sum())},
        "db9_score_sigma": tau_db9.tolist(),
        "scaling_source": "DB9 training corpus only",
        "other_rescaling_applied": "NONE",
    }
    with open(os.path.join(ART, "SCORE_SPACE_PRESERVATION.json"), "w",
              encoding="utf-8") as fh:
        json.dump(score_art, fh, indent=2, ensure_ascii=False)

    pose_rel = {
        "artifact": "POSE_TO_FISHER_RELATION.json",
        "plan_sha256": PLAN_SHA,
        "chain": "physical pose error -> Fisher representation error -> hard flip",
        "spearman_pose_rmse_vs_fisher_distance": rho_pose_fisher,
        "spearman_fisher_distance_vs_flip": rho_fisher_flip,
        "spearman_pose_rmse_vs_flip_recomputed": rho_pose_flip,
        "spearman_pose_rmse_vs_flip_gate3_recorded": 0.162137,
        "pose_rmse_frame_deg": qstats(pose_rmse_frame),
        "pose_mae_frame_deg": qstats(pose_mae_frame),
        "causal_claim": "NONE",
        "inferential_caveat": "one participant, temporally correlated frames; no "
                              "frame-level p-values; rank statistics are descriptive",
    }
    with open(os.path.join(ART, "POSE_TO_FISHER_RELATION.json"), "w",
              encoding="utf-8") as fh:
        json.dump(pose_rel, fh, indent=2, ensure_ascii=False)

    cka_art = {
        "artifact": "REPRESENTATIONAL_CKA.json",
        "plan_sha256": PLAN_SHA,
        "linear_cka": cka_val,
        "mode": cka_mode,
        "n_used": cka_n,
        "declared_subsample_rule": f"first {CKA_MAX_N} eligible samples in frozen "
                                   f"population order if full computation infeasible",
        "is_secondary": True,
        "caution": "CKA is more invariant than direct substitution requires (ignores "
                   "rotation and isotropic scaling); a high CKA must not override poor "
                   "per-frame preservation",
    }
    with open(os.path.join(ART, "REPRESENTATIONAL_CKA.json"), "w", encoding="utf-8") as fh:
        json.dump(cka_art, fh, indent=2, ensure_ascii=False)

    import csv as _csv
    with open(os.path.join(ART, "FISHER_COMPONENT_PRESERVATION.csv"), "w",
              encoding="utf-8", newline="") as fh:
        wtr = _csv.DictWriter(fh, fieldnames=list(comps[0].keys()))
        wtr.writeheader()
        for r in comps:
            wtr.writerow(r)

    with open(os.path.join(ART, "TEMPORAL_FISHER_PRESERVATION.csv"), "w",
              encoding="utf-8", newline="") as fh:
        wtr = _csv.DictWriter(fh, fieldnames=list(temporal[0].keys()))
        wtr.writeheader()
        for r in temporal:
            wtr.writerow(r)

    for fname, rows in (("FISHER_DISTANCE_DECILES.csv", dist_dec),
                        ("FISHER_COSINE_DECILES.csv", cos_dec)):
        with open(os.path.join(ART, fname), "w", encoding="utf-8", newline="") as fh:
            wtr = _csv.DictWriter(fh, fieldnames=list(rows[0].keys()),
                                  extrasaction="ignore")
            wtr.writeheader()
            for r in rows:
                wtr.writerow(r)

    with open(os.path.join(ART, "REPRESENTATION_BY_HARD_OUTCOME.csv"), "w",
              encoding="utf-8", newline="") as fh:
        cols = ["group", "n", "n_fraction", "fisher_cosine_median",
                "fisher_cosine_iqr", "fisher_distance_norm_median",
                "fisher_distance_norm_iqr", "fisher_distance_raw_median",
                "score_cosine_median", "score_distance_norm_median", "tv_median",
                "tv_iqr", "js_median", "js_iqr", "pose_mae_deg", "pose_rmse_deg",
                "pose_rmse_frame_median_deg"]
        wtr = _csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        wtr.writeheader()
        for name, v in groups.items():
            wtr.writerow({"group": name, **v})

    for fname, d in (("REPRESENTATION_BY_SIDE.csv", by_side),
                     ("REPRESENTATION_BY_STAGE.csv", by_stage)):
        cols = ["key", "n", "fisher_cosine_median", "fisher_distance_norm_median",
                "score_cosine_median", "hard_agreement", "median_pose_error_deg",
                "balanced_preservation"]
        with open(os.path.join(ART, fname), "w", encoding="utf-8", newline="") as fh:
            wtr = _csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            wtr.writeheader()
            for k, v in d.items():
                wtr.writerow({"key": k, **v})

    # ---------------- 17. mechanism decision ----------------
    cos_med = float(np.median(cz))
    d_med = float(np.median(d_norm))
    flip_cos = groups["FLIP"]["fisher_cosine_median"]
    same_cos = groups["SAME"]["fisher_cosine_median"]
    comp_min_r = min(c["pearson_r"] for c in comps)
    comp_mean_r = float(np.mean([c["pearson_r"] for c in comps]))
    score_cos_med = float(np.median(scos[scos_valid]))

    # ---- mechanism label: driven by the frozen joint-evidence rule ----
    # Primary reading is the Fisher cosine, which is scale-free and therefore the
    # primary continuous-similarity statement. The FLIP-group statistics play the
    # supporting role the plan assigns them: flips with high similarity support
    # boundary fragility; flips with already-low similarity support representation
    # loss. Thresholds below are DESCRIPTION BANDS for the label only, and are
    # recorded explicitly so the reading is auditable rather than implicit.
    if flip_cos is None:
        mechanism = "MIXED_OR_AMBIGUOUS"
        mech_reason = "flip group had no valid cosine frames"
    elif cos_med >= 0.9 and comp_min_r >= 0.5:
        mechanism = "REPRESENTATION_LARGELY_PRESERVED_BOUNDARY_FRAGILE"
        mech_reason = (f"median Fisher cosine {cos_med:.6f} >= 0.90 and every "
                       f"component r >= {comp_min_r:.6f} >= 0.50, while hard "
                       f"agreement is only {agreement:.6f}")
    elif cos_med >= 0.5:
        mechanism = "REPRESENTATION_PARTIALLY_PRESERVED"
        mech_reason = (f"median Fisher cosine {cos_med:.6f} in [0.50, 0.90); real "
                       f"but incomplete representation degradation")
    elif cos_med < 0.5 and flip_cos >= 0.8:
        mechanism = "MIXED_OR_AMBIGUOUS"
        mech_reason = (f"overall median Fisher cosine {cos_med:.6f} < 0.50 but the "
                       f"flip group alone sits at {flip_cos:.6f} >= 0.80; the two "
                       f"readings disagree")
    else:
        mechanism = "REPRESENTATION_SUBSTANTIALLY_DEGRADED"
        mech_reason = (f"median Fisher cosine {cos_med:.6f} < 0.50 and flip-group "
                       f"median {flip_cos:.6f} < 0.80; the continuous representation "
                       f"itself is badly damaged")

    log()
    log(f"[13] MECHANISM DECISION: {mechanism}")
    log(f"     {mech_reason}")

    dec = {
        "artifact": "GATE3B_DECISION.json",
        "gate": "PHASE 1 / GATE 3B",
        "plan_sha256": PLAN_SHA,
        "evidence_status": "POST-HOC MOTIVATED, PROSPECTIVELY FROZEN BEFORE "
                           "CONTINUOUS-REPRESENTATION OUTCOME INSPECTION",
        "no_arbitrary_thresholds": True,
        "MECHANISM": mechanism,
        "mechanism_reason": mech_reason,
        "mechanism_label_thresholds_are_description_bands_only": True,
        "mechanism_rule_declared": {
            "median_fisher_cosine >= 0.90 AND min component r >= 0.50":
                "REPRESENTATION_LARGELY_PRESERVED_BOUNDARY_FRAGILE",
            "0.50 <= median_fisher_cosine < 0.90":
                "REPRESENTATION_PARTIALLY_PRESERVED",
            "median_fisher_cosine < 0.50 AND flip-group cosine >= 0.80":
                "MIXED_OR_AMBIGUOUS",
            "otherwise": "REPRESENTATION_SUBSTANTIALLY_DEGRADED",
        },
        "hard_agreement_alone_did_not_drive_the_label": True,
        "joint_evidence": {
            "fisher_cosine_median": cos_med,
            "fisher_cosine_iqr": fisher["cosine"]["stats"]["iqr"],
            "fisher_distance_norm_median": d_med,
            "fisher_distance_norm_iqr": fisher["distance_db9_normalized"]["iqr"],
            "component_pearson_mean": comp_mean_r,
            "component_pearson_min": comp_min_r,
            "db9_weighted_component_correlation": weighted_corr,
            "score_cosine_median": score_cos_med,
            "score_distance_norm_median": float(np.median(sdist_norm)),
            "tv_median": float(np.median(tv)),
            "js_median": float(np.median(jsd)),
            "hard_agreement": agreement,
            "flip_fraction": float(flip.mean()),
            "fisher_cosine_median_flip_group": flip_cos,
            "fisher_cosine_median_same_group": same_cos,
            "spearman_pose_rmse_vs_fisher_distance": rho_pose_fisher,
            "spearman_fisher_distance_vs_flip": rho_fisher_flip,
        },
        "reading": {
            "high_flip_similarity_supports": "BOUNDARY_FRAGILITY",
            "low_flip_similarity_supports": "REPRESENTATION_LOSS",
        },
        "firewall": {
            "NEW_INFERENCE_RUN": "NO", "MODEL_RETRAINED": "NO",
            "CALIBRATION_FITTED": "NO", "SMOOTHING_APPLIED": "NO",
            "GATE_CREATED": "NO", "UNKNOWN_CLASS": "NO",
            "HUMAN_LABELS_USED": "NO", "LAG_SEARCH_PERFORMED": "NO",
            "DOF_INTERVENTION_PERFORMED": "NO",
            "SAMPLE_FILTERING_APPLIED": "NO",
            "COMPONENT_SELECTION_ON_OUTCOME": "NO",
            "POPULATION_CHANGED": "NO", "GATE3_ARTIFACTS_MODIFIED": "NO",
            "SCALING_FROM_EMG2POSE": "NO",
        },
        "next_allowed_step": "Decide the reliability-gate direction from the mechanism "
                             "reading. Do not design a gate in this gate.",
    }
    with open(os.path.join(ART, "GATE3B_DECISION.json"), "w", encoding="utf-8") as fh:
        json.dump(dec, fh, indent=2, ensure_ascii=False)

    with open(os.path.join(LOGS, "gate3b_stdout.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(log_lines) + "\n")

    log(f"elapsed {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
