"""
bridge_audit/run_bridge_audit.py -- SESSION 5 CROSS-DATASET BRIDGE AUDIT.

    emg2pose  --(official pretrained VEMG2Pose, INFERENCE ONLY)-->  predicted 20D pose
    emg2pose GT 20D --------------------------------------------------+
                                                                      |
                          frozen Session-2 canonical16 adapter --------+
                                                                      |
                    +-------------------------------------------------+
                    |
        GT canonical16            predicted canonical16
                    |                       |
          frozen DB9 decoder (reconstructed in PHASE 1, handshake-verified)
                    |                       |
        oracle-pose reference        predicted-pose decision
                    \                      /
                     DOWNSTREAM DECODER STABILITY

THE QUESTION
------------
Does wrist-EMG pose estimation preserve the frozen posture-relevant kinematic
geometry well enough that a DB9-trained decoder behaves consistently with an
oracle-GT-pose decoder?

WHAT THIS IS NOT
----------------
Not gesture recognition. emg2pose provides no frame-level ground-truth labels for
the six DB9 postures, and emg2pose ``stage`` is never used as posture truth. The
GT-pose decoder output is an ORACLE-POSE REFERENCE, not ground truth.

HARD CONSTRAINTS RESPECTED
--------------------------
* no training of any kind (the only model run is the official pretrained
  checkpoint, in eval mode, torch.no_grad)
* no modification of any Session 1-4 artifact; all outputs go to bridge_audit/
* canonical16 is consumed, never altered; no canonical18; the frozen thumb-AA
  sign mapping is consumed, never re-derived
* no tuning of the decoder, the OOD threshold, or any emg2pose-facing parameter
* the 43 outcome-unseen DB9 subjects are never used to refit the bridge decoder;
  they are only used, read-only, as the PHASE-1 exactness handshake target

Usage
-----
    python run_bridge_audit.py --out-dir <dir> [--limit N] [--no-2khz]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import platform
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import decoder as D  # noqa: E402
from _common import (  # noqa: E402
    ASCII_ROOT, BASELINE_DIR, CANON12_IDX, CANON15_IDX, CANON16, CHECKPOINT_DIR,
    COHORTS, DB9_DATA_DIR, DOCS_DIR, DOF_GROUPS, FROZEN_SPEC, FULL_DB9_RESULTS,
    INFERENCE_DIR, MINI_DIR, REPS_77, REPS_77_META, ROOT, ch, cp, describe,
    hash_artifacts, jstep, sha256_file, sha256_json,
)

EMG_RATE = 2000               # Hz, official
POSE_STRIDE = 40              # 2000 / 50 -> the model's native 50 Hz update cadence
REP_FRAME_BATCH = 200_000     # rows per decoder call (memory guard)


# ---------------------------------------------------------------------------
# PHASE 2/3 -- one emg2pose session -> paired GT / predicted canonical16
# ---------------------------------------------------------------------------
def resolve_native_grid(P: np.ndarray, n_probe: int = 400, tolerances=(1e-9, 1e-10, 1e-11)) -> dict:
    """Empirically locate the model's native pose-update nodes inside the 2 kHz output.

    The model rolls out at 50 Hz and linearly interpolates to 2 kHz, so the
    returned series is piecewise linear with 40-sample segments.  A node is
    identified by |second difference| collapsing relative to the median.
    This is a *measurement*, not an assumption, and it is what justifies treating
    the 2 kHz output as ~50 Hz of independent information.
    """
    n_probe = min(n_probe, P.shape[0] - 2)
    A = P[: n_probe + 2]
    d2 = np.abs(np.diff(A, n=2, axis=0))
    med = float(np.median(d2))
    out: dict = {"median_abs_second_difference": med, "n_probe": int(n_probe)}
    for tol in tolerances:
        nodes = np.flatnonzero(d2.max(axis=1) < tol)
        phase = sorted(set(int(i) % POSE_STRIDE for i in nodes)) if nodes.size else []
        frac = float(nodes.size) / float(n_probe)
        out[f"tol_{tol:g}"] = {
            "n_nodes": int(nodes.size),
            "expected_nodes": int(np.ceil(n_probe / POSE_STRIDE)),
            "fraction_of_positions": frac,
            "phases_mod_40": phase[:8],
        }
    # distance from index 0 to the first detected node, and the modal node phase
    nodes = np.flatnonzero(d2.max(axis=1) < 1e-10)
    if nodes.size:
        phase_counts = np.bincount(nodes % POSE_STRIDE, minlength=POSE_STRIDE)
        out["modal_phase_mod_40"] = int(phase_counts.argmax())
        out["modal_phase_fraction"] = float(phase_counts.max() / nodes.size)
    # stride sensitivity at the same tolerance
    out["stride_profile_median_abs_d2"] = {
        str(s): float(np.median(d2.max(axis=1)[s::s])) for s in (38, 39, 40, 41, 42)
    }
    return out


def load_session(path: str):
    """Official HDF5 -> (emg, gt_20d, time, metadata). No re-derivation of schema."""
    from emg2pose.data import Emg2PoseSessionData

    sess = Emg2PoseSessionData(hdf5_path=path)
    ts = sess[0 : len(sess)]
    emg = np.asarray(ts["emg"], dtype=np.float32)
    gt20 = np.asarray(ts["joint_angles"], dtype=np.float32)
    t = np.asarray(ts["time"], dtype=np.float64)
    md = dict(sess.metadata)
    del sess
    return emg, gt20, t, md


def process_session(path: str, model, *, save_2khz: bool, out_dir: str) -> dict:
    from emg2pose.utils import get_ik_failures_mask

    stem = os.path.splitext(os.path.basename(path))[0]
    emg, gt20_all, t_all, md = load_session(path)
    T = emg.shape[0]

    t0 = time.time()
    P20 = model.predict(emg)                      # (T - 1790, 20), radians, INFERENCE ONLY
    infer_s = time.time() - t0
    lc = int(model.left_context)

    n_pose = P20.shape[0]
    if n_pose != T - lc:
        raise SystemExit(f"{stem}: unexpected prediction length {n_pose} vs T-lc={T-lc}")

    # ---- alignment (Session-2 frozen semantics) --------------------------
    gt20 = gt20_all[lc:T]                         # identical slicing as the frozen smoke test
    t_pose = t_all[lc:T]

    # ---- validity (frozen Session-2 semantics) ---------------------------
    gt_valid = get_ik_failures_mask(gt20)         # True = usable GT pose
    pred_zero = np.all(np.isclose(P20, 0.0), axis=-1)
    pred_finite = np.isfinite(P20).all(axis=1)

    # ---- frozen adapter: 20D -> canonical16 (consumed, never re-derived) --
    gt16, gt_valid_adapter = ch.to_canonical16(gt20, return_validity=True)
    pr16, pr_valid_adapter = ch.to_canonical16(P20, return_validity=True)
    gt16 = np.asarray(gt16, dtype=np.float64)
    pr16 = np.asarray(pr16, dtype=np.float64)
    if not np.array_equal(gt_valid, gt_valid_adapter):
        raise SystemExit(f"{stem}: S2 adapter validity disagrees with official IK mask")
    if not np.array_equal(pred_zero, ~pr_valid_adapter):
        raise SystemExit(f"{stem}: adapter validity does not flag all-zero predictions")

    # ---- PHASE 3: the model's native 50 Hz cadence -----------------------
    # The model rolls out at 50 Hz and linearly interpolates to 2 kHz, so the
    # returned series carries ~1/40 of its values as independent information.
    # Rather than guess where the interpolation fencepost sits inside each
    # 40-sample block (a sub-sample question), each non-overlapping 20 ms block is
    # reduced to ONE value by averaging, for GT and prediction alike. That is
    # symmetric, phase-robust, and cannot manufacture independent samples.
    grid = resolve_native_grid(P20)
    n_blocks = n_pose // POSE_STRIDE
    usable = n_blocks * POSE_STRIDE
    idx = np.arange(0, usable)
    eff_rate = EMG_RATE / POSE_STRIDE

    def block_mean(A):
        return A[:usable].reshape(n_blocks, POSE_STRIDE, A.shape[1]).mean(axis=1)

    gt16_2k, pr16_2k = gt16, pr16
    gt16 = block_mean(gt16_2k)
    pr16 = block_mean(pr16_2k)
    # a block is GT-valid only if every sample in it is (no mixing across an IK gap)
    gt_valid = gt_valid[:usable].reshape(n_blocks, POSE_STRIDE).all(axis=1)
    pred_zero = pred_zero[:usable].reshape(n_blocks, POSE_STRIDE).any(axis=1)
    pred_finite = pred_finite[:usable].reshape(n_blocks, POSE_STRIDE).all(axis=1)
    n_pose = n_blocks
    t_pose = t_pose[:usable].reshape(n_blocks, POSE_STRIDE).mean(axis=1)

    # within-block variation: how much hand motion one 20 ms bin can hide
    within_block_motion_deg = float(
        np.degrees(np.abs(
            gt20_all[lc + np.arange(usable)].reshape(n_blocks, POSE_STRIDE, 20)
            - gt20_all[lc + np.arange(usable)].reshape(n_blocks, POSE_STRIDE, 20).mean(axis=1, keepdims=True)
        )[gt_valid].mean())
    ) if gt_valid.any() else float("nan")

    # ---- secondary diagnostics on the full 2 kHz timeline (GT-valid only) --
    g2 = gt16_2k[:, CANON12_IDX]
    p2 = pr16_2k[:, CANON12_IDX]
    _gt_full = np.asarray(get_ik_failures_mask(gt20))
    full_abs_err_rad = (
        float(np.abs(p2[_gt_full] - g2[_gt_full]).mean()) if _gt_full.any()
        else float("nan"))

    # ---- lag sanity check (evidence, not a correction) -------------------
    lag_check = cross_correlation_lag(gt16_2k, pr16_2k, _gt_full)

    # ---- decoder-facing artefacts (native 50 Hz cadence) -----------------
    gt_v = gt_valid
    pred_ok_50 = (~pred_zero) & pred_finite
    if os.environ.get("BRIDGE_DEBUG"):
        print(f"    [debug] pred_all_zero={pred_zero.mean():.4f} "
              f"pred_finite={pred_finite.mean():.4f} "
              f"pred_usable={pred_ok_50.mean():.4f} gt_v={gt_v.mean():.4f} "
              f"n_blocks={n_blocks} usable={usable} n_pose_2k={P20.shape[0]}")
    n_gt_valid = int(gt_v.sum())
    n_both = int((gt_v & pred_ok_50).sum())

    rec = {
        "session": stem,
        "file": os.path.basename(path),
        "side": str(md.get("side", "")),
        "stage": str(md.get("stage", "")),
        "user": str(md.get("user", "")),
        "session_name": str(md.get("session_name", "")),
        "n_samples_2khz": int(T),
        "n_pose_samples_2khz": int(P20.shape[0]),
        "left_context": lc,
        "duration_s": float(T / EMG_RATE),
        "inference_seconds": float(infer_s),
        "realtime_factor": float((T / EMG_RATE) / infer_s),
        "native_grid": grid,
        "native_block": POSE_STRIDE,
        "native_grid_usable_samples": int(usable),
        "native_grid_discarded_samples": int(P20.shape[0] - usable),
        "n_pose_samples_50hz": int(n_blocks),
        "effective_pose_rate_hz": float(eff_rate),
        "n_gt_valid_50hz": n_gt_valid,
        "n_pred_valid_50hz": int(pred_ok_50.sum()),
        "n_paired_valid_50hz": n_both,
        "gt_ik_failure_fraction_2khz": float((~_gt_full).mean()),
        "gt_ik_failure_fraction_50hz": float((~gt_v).mean()),
        "predicted_all_zero_fraction_2khz": float(
            np.all(np.isclose(P20, 0.0), axis=-1).mean()),
        "predicted_all_zero_fraction_50hz": float(pred_zero.mean()),
        "predicted_nonfinite_fraction_50hz": float((~pred_finite).mean()),
        "within_block_gt_motion_deg_mean_abs": within_block_motion_deg,
        "full_2khz_canonical12_mae_rad_masked": full_abs_err_rad,
        "full_2khz_canonical12_mae_deg_masked": float(np.degrees(full_abs_err_rad)),
        "lag_check": lag_check,
    }

    # ---- persist the paired canonical16 for audit / PHASE 9 --------------
    # Stored at native cadence with the validity masks, so every downstream
    # count is recomputable from the artifact rather than trusted.
    os.makedirs(out_dir, exist_ok=True)
    np.savez_compressed(
        os.path.join(out_dir, f"{stem}.paired50hz.npz"),
        gt16=gt16.astype(np.float32),
        pred16=pr16.astype(np.float32),
        gt_valid=gt_v,
        pred_valid=pred_ok_50,
        time=t_pose,
        block=np.int32(POSE_STRIDE),
    )
    if save_2khz:
        np.savez_compressed(
            os.path.join(out_dir, f"{stem}.paired2khz.npz"),
            gt16=gt16_2k[_gt_full].astype(np.float32),
            pred16=pr16_2k[_gt_full].astype(np.float32),
        )
    return rec


def cross_correlation_lag(gt16: np.ndarray, pr16: np.ndarray, valid: np.ndarray,
                          max_lag_s: float = 0.02, step: int = 10) -> dict:
    """Does an alternative GT/prediction time offset explain the error?

    Descriptive sanity check on the FROZEN alignment only. If a nonzero lag
    substantially reduced the canonical16 error, the frozen Session-2 alignment
    would be in question -- that would be a structural finding, not something to
    silently correct. No correction is applied anywhere.
    """
    m = valid.copy()
    x = gt16[::step]
    y = pr16[::step]
    m = m[::step]
    x = x[m]
    y = y[m]
    if x.shape[0] < 2000:
        return {"evaluated": False, "reason": "too few valid samples"}
    max_lag = int(round(max_lag_s * (EMG_RATE / step)))
    lags = list(range(-max_lag, max_lag + 1))
    errs = []
    for k in lags:
        if k > 0:
            a, b = x[k:], y[:-k]
        elif k < 0:
            a, b = x[:k], y[-k:]
        else:
            a, b = x, y
        errs.append(float(np.abs(a - b).mean()))
    errs = np.asarray(errs)
    best = int(np.argmin(errs))
    zero_at = lags.index(0)
    return {
        "evaluated": True,
        "lag_s_at_min_error": float(lags[best] * step / EMG_RATE),
        "mae_at_zero_lag": float(errs[zero_at]),
        "mae_at_min_error_lag": float(errs[best]),
        "relative_improvement_at_best_lag": float(errs[zero_at] / errs[best] - 1.0),
        "interpretation": (
            "diagnostic only; the frozen zero offset is used everywhere. A large "
            "improvement here would indicate an alignment problem, not a fixable metric."
        ),
    }


# ---------------------------------------------------------------------------
# PHASE 4 -- pose estimation error in canonical space
# ---------------------------------------------------------------------------
def pose_error_block(gt16: np.ndarray, pr16: np.ndarray, valid: np.ndarray,
                     per_session: list[dict] | None = None) -> dict:
    g = gt16[valid]
    p = pr16[valid]
    err_deg = np.degrees(p - g)
    abs_deg = np.abs(err_deg)

    def block(cols, names):
        a = abs_deg[:, cols]
        return {
            "names": names,
            "MAE_deg_per_dof": [float(v) for v in a.mean(axis=0)],
            "median_abs_error_deg_per_dof": [float(v) for v in np.median(a, axis=0)],
            "MAE_deg_overall": float(a.mean()),
            "RMSE_deg_overall": float(np.sqrt((err_deg[:, cols] ** 2).mean())),
            "p95_abs_error_deg_overall": float(np.percentile(a, 95)),
            "max_abs_error_deg_overall": float(a.max()),
            "mean_bias_deg_per_dof": [float(v) for v in err_deg[:, cols].mean(axis=0)],
            "median_abs_error_deg_per_dof_pooled": [
                float(np.median(abs_deg[:, c])) for c in cols
            ],
        }

    out = {
        "n_valid_samples": int(valid.sum()),
        "unit": "degrees (converted from canonical16 radians; the representation is "
                "never converted in place)",
        "canonical16": block(list(range(16)), list(CANON16)),
        "canonical15_noThumbAA": block(
            list(range(15)),
            [n for i, n in enumerate(CANON16) if i != 1]),
        "canonical12_noDIP": block(
            list(range(12)),
            [CANON16[i] for i in CANON12_IDX]),
        "descriptive_role": (
            "BRIDGE diagnostics only. These are not a representation-selection "
            "competition and no design decision is taken from them."
        ),
    }
    if per_session is not None:
        out["per_session"] = per_session
    return out


# ---------------------------------------------------------------------------
# PHASE 6/7/8 -- decision-level analysis
# ---------------------------------------------------------------------------
def decision_analysis(gt16: np.ndarray, pr16: np.ndarray, valid: np.ndarray,
                      dec: D.FrozenDecoder, geom: D.DomainGeometry,
                      session_ids: np.ndarray) -> dict:
    g = gt16[valid]
    p = pr16[valid]
    sid = session_ids[valid]
    n = g.shape[0]

    # ---- decision values / probabilities ---------------------------------
    Vg = np.empty((n, len(dec.classes)))
    Vp = np.empty_like(Vg)
    Pg = np.empty_like(Vg)
    Pp = np.empty_like(Vg)
    for a in range(0, n, REP_FRAME_BATCH):
        b = min(a + REP_FRAME_BATCH, n)
        Vg[a:b] = dec.decision(g[a:b])
        Vp[a:b] = dec.decision(p[a:b])
        Pg[a:b] = dec.predict_proba(g[a:b])
        Pp[a:b] = dec.predict_proba(p[a:b])

    top_g = Vg.argmax(axis=1)
    top_p = Vp.argmax(axis=1)
    agree = top_g == top_p

    # ---- PHASE 5 statistic on both sides (no threshold was fitted on these)
    dist_g = geom.min_mahalanobis(dec.z(g), geom.centroids, geom.precision)
    dist_p = geom.min_mahalanobis(dec.z(p), geom.centroids, geom.precision)
    pct_g = geom.reference_percentile_of(dist_g)
    pct_p = geom.reference_percentile_of(dist_p)
    thr95 = geom.thresholds["p95"]

    # ---- PHASE 6 metrics -------------------------------------------------
    abs_pd = np.abs(Pg - Pp)
    l2_pd = np.sqrt(((Pg - Pp) ** 2).sum(axis=1))
    jsd = jstep(Pg, Pp)
    sorted_g = np.sort(Vg, axis=1)[:, ::-1]
    sorted_p = np.sort(Vp, axis=1)[:, ::-1]
    margin_g = sorted_g[:, 0] - sorted_g[:, 1]
    margin_p = sorted_p[:, 0] - sorted_p[:, 1]

    # ---- PHASE 7 -- discriminant subspace of the frozen LDA geometry -----
    # The between-class scatter has rank 5 for six balanced classes; its column
    # space is the complete set of directions in which class means differ, so the
    # LDA's decision is a function of the data through that subspace.
    U = geom.discriminant_dirs                       # (16, 5)
    dz = dec.z(p) - dec.z(g)                         # error in z-space
    total_sq = (dz ** 2).sum(axis=1)
    disc_sq = ((dz @ U) ** 2).sum(axis=1)
    orth_sq = np.maximum(total_sq - disc_sq, 0.0)
    disc_frac = np.where(total_sq > 0, disc_sq / np.maximum(total_sq, 1e-30), 0.0)

    # ---- PHASE 8 -- per-DOF attribution of the decision margin -----------
    # For each sample the operative decision boundary is the pair
    #   {top-1, top-2 of the GT-pose decision}  x  {top-1, top-2 of the
    #   predicted-pose decision};
    # i.e. every boundary either side is actually comparing.  For that pair the
    # signed margin is  m(x) = v_a(x) - v_b(x)  with v the frozen LDA decision
    # function, and because v is LINEAR in z-space the change
    #   Delta m = m(pred) - m(gt) = (z_p - z_g) . (coef_a - coef_b)
    # decomposes EXACTLY into one linear contribution per canonical DOF.  Nothing
    # is approximated, and the decoder is not modified in any way.
    ord_g = np.argsort(-Vg, axis=1)
    ord_p = np.argsort(-Vp, axis=1)
    pair_set = np.stack([ord_g[:, 0], ord_g[:, 1], ord_p[:, 0], ord_p[:, 1]], axis=1)
    same_pair = (ord_g[:, :2] == ord_p[:, :2]).all(axis=1)
    pair_changed = ~same_pair

    margin_delta = np.zeros(n)
    contrib = np.zeros((n, 16))
    normals = np.asarray(dec.lda.coef_, dtype=np.float64)   # (C, 16)
    uniq_rows = np.unique(pair_set, axis=0)
    assigned = np.zeros(n, dtype=bool)
    for row in uniq_rows:
        a, b = int(row[0]), int(row[1])
        if a == b:
            continue
        m = np.all(pair_set == row, axis=1)
        nrm = normals[a] - normals[b]
        d1 = Vg[m, a] - Vg[m, b]
        d2 = Vp[m, a] - Vp[m, b]
        margin_delta[m] = d2 - d1
        contrib[m] = dz[m] * nrm[None, :]
        assigned[m] = True
    if not assigned.all():
        # any frame whose union-pair had a==b is genuinely on no boundary: its
        # margin change is identically zero and contributes nothing.
        pass

    # attribution of the *decision change*: |Delta margin| decomposed by DOF
    abs_contrib = np.abs(contrib)
    denom = np.maximum(abs_contrib.sum(axis=1, keepdims=True), 1e-30)
    share = abs_contrib / denom
    dominant = share.argmax(axis=1)

    def group_share(mask):
        if mask.sum() == 0:
            return {}
        out = {}
        for gname, cols in DOF_GROUPS.items():
            out[gname] = float(share[mask][:, cols].sum(axis=1).mean())
        return out

    disagree = ~agree

    # ---- stratification --------------------------------------------------
    def stratify(by: np.ndarray, label: str, edges: list[float]):
        rows = {}
        for lo, hi in zip(edges[:-1], edges[1:]):
            m = (by >= lo) & (by < hi)
            if m.sum() == 0:
                rows[f"{label}[{lo:g},{hi:g})"] = {"n": 0}
                continue
            rows[f"{label}[{lo:g},{hi:g})"] = {
                "n": int(m.sum()),
                "top1_agreement": float(agree[m].mean()),
                "boundary_pair_changed": float(pair_changed[m].mean()),
                "mean_abs_prob_diff": float(abs_pd[m].mean()),
                "mean_jsd": float(jsd[m].mean()),
            }
        return rows

    q_g = np.percentile(margin_g, [0, 25, 50, 75, 100])
    q_d = np.percentile(dist_g, [0, 25, 50, 75, 100])

    out = {
        "n_samples": int(n),
        "n_sessions": int(len(np.unique(sid))),
        "oracle_pose_reference": (
            "decoder(GT emg2pose kinematic pose). NOT gesture ground truth: "
            "emg2pose supplies no frame-level labels for the six DB9 postures and "
            "emg2pose `stage` is never used as posture truth."
        ),
        "naming": "DOWNSTREAM DECODER STABILITY / GT-POSE vs PREDICTED-POSE DECODER AGREEMENT",
        "top1_agreement": float(agree.mean()),
        "top1_disagreement": float(disagree.mean()),
        "n_disagree": int(disagree.sum()),
        "boundary_pair_changed_rate": float(pair_changed.mean()),
        "probability_difference": {
            "mean_abs_prob_diff": float(abs_pd.mean()),
            "median_abs_prob_diff": float(np.median(abs_pd)),
            "mean_l2_prob_diff": float(l2_pd.mean()),
            "max_abs_prob_diff": float(abs_pd.max()),
        },
        "jsd": describe(jsd, prefix="jsd_"),
        "confidence": {
            "gt_mean_top1_prob": float(Pg.max(axis=1).mean()),
            "pred_mean_top1_prob": float(Pp.max(axis=1).mean()),
            "gt_mean_margin": float(margin_g.mean()),
            "pred_mean_margin": float(margin_p.mean()),
            "mean_margin_change": float((margin_p - margin_g).mean()),
            "median_margin_change": float(np.median(margin_p - margin_g)),
            "mean_abs_margin_change": float(np.abs(margin_p - margin_g).mean()),
        },
        "domain_distance": {
            "metric": geom.to_json()["metric_primary"],
            "db9_reference": geom.to_json()["reference_distribution_on_DB9_training"],
            "threshold_p95_from_db9_only": thr95,
            "gt": {**describe(dist_g, prefix="gt_"),
                   "median_reference_percentile": float(np.median(pct_g)),
                   "fraction_beyond_db9_p95": float((dist_g > thr95).mean())},
            "predicted": {**describe(dist_p, prefix="pred_"),
                          "median_reference_percentile": float(np.median(pct_p)),
                          "fraction_beyond_db9_p95": float((dist_p > thr95).mean())},
            "predicted_minus_gt_median": float(np.median(dist_p) - np.median(dist_g)),
            "predicted_farther_fraction": float((dist_p > dist_g).mean()),
        },
        "discriminant_error": {
            "space": "frozen decoder z-space; basis = orthonormal eigenvectors of the "
                     "between-class scatter of the 6 DB9 classes (rank 5)",
            "mean_total_error_z": float(np.sqrt(total_sq).mean()),
            "median_total_error_z": float(np.median(np.sqrt(total_sq))),
            "mean_discriminant_error_z": float(np.sqrt(disc_sq).mean()),
            "mean_orthogonal_error_z": float(np.sqrt(orth_sq).mean()),
            "mean_discriminant_energy_fraction": float(disc_frac.mean()),
            "median_discriminant_energy_fraction": float(np.median(disc_frac)),
            "fraction_of_samples_over_50pct_discriminant": float((disc_frac > 0.5).mean()),
            "per_direction_rms_error_z": [
                float(np.sqrt(((dz @ U[:, k]) ** 2).mean())) for k in range(U.shape[1])
            ],
            "db9_within_class_discriminant_energy_fraction": None,  # filled by caller
            "interpretation_note": (
                "If the error energy fraction in the discriminant subspace were at "
                "the level of ordinary within-class DB9 variation, the error would "
                "be 'parallel to harmless within-class variation'; above that level "
                "it lies along class-separating directions."
            ),
        },
        "stratified": {
            "by_gt_margin_quartile": stratify(margin_g, "gt_margin", list(q_g)),
            "by_db9_domain_distance_quartile": stratify(dist_g, "gt_dist", list(q_d)),
        },
        "attribution": {
            "definition": (
                "margin = decision(top1) - decision(top2) under the frozen LDA, on "
                "the union of the GT-pose and predicted-pose top-2 pairs. Because "
                "the LDA decision function is linear in z-space, "
                "Delta margin = (z_pred - z_gt) . (coef_a - coef_b) decomposes "
                "exactly into one linear contribution per canonical DOF. The "
                "decoder is not modified."
            ),
            "n_disagreement_frames": int(disagree.sum()),
            "mean_abs_margin_change": float(np.abs(margin_delta).mean()),
            "median_abs_margin_change": float(np.median(np.abs(margin_delta))),
            "mean_abs_margin_change_on_disagreement": (
                float(np.abs(margin_delta[disagree]).mean()) if disagree.any() else None
            ),
            "mean_abs_margin_change_on_agreement": (
                float(np.abs(margin_delta[agree]).mean()) if agree.any() else None
            ),
            "units": "z-units (the frozen decoder's own standardized canonical16 space)",
            "mean_abs_contribution_per_dof_all": [
                float(v) for v in abs_contrib.mean(axis=0)
            ],
            "mean_abs_contribution_per_dof_disagreement": (
                [float(v) for v in abs_contrib[disagree].mean(axis=0)]
                if disagree.any() else None
            ),
            "mean_contribution_share_per_dof_disagreement": (
                [float(v) for v in share[disagree].mean(axis=0)] if disagree.any() else None
            ),
            "dominant_dof_counts_disagreement": (
                {CANON16[i]: int((dominant[disagree] == i).sum()) for i in range(16)}
                if disagree.any() else None
            ),
            "group_share_all": group_share(np.ones(n, bool)),
            "group_share_disagreement": group_share(disagree) if disagree.any() else None,
            "group_share_agreement": group_share(agree) if agree.any() else None,
            "representation_views": representation_attribution_views(abs_contrib, share, disagree),
        },
        # raw per-frame arrays are returned separately for session aggregation
        "_arrays": {
            "agree": agree, "pair_changed": pair_changed, "dist_g": dist_g, "dist_p": dist_p,
            "margin_g": margin_g, "margin_p": margin_p, "abs_pd": abs_pd,
            "jsd": jsd, "disc_frac": disc_frac, "margin_delta": margin_delta,
            "abs_contrib": abs_contrib, "share": share, "sid": sid,
            "total_err_z": np.sqrt(total_sq), "disc_err_z": np.sqrt(disc_sq),
            "orth_err_z": np.sqrt(orth_sq), "pct_g": pct_g, "pct_p": pct_p,
            "canon16_abs_err_deg": np.degrees(np.abs(pr16[valid] - gt16[valid])),
        },
    }
    return out


def representation_attribution_views(abs_contrib, share, disagree) -> dict:
    """Descriptive canonical16 / canonical15_noThumbAA / canonical12_noDIP views.

    POST-CONFIRMATORY BRIDGE DIAGNOSTICS. Deliberately NOT a representation
    competition: nothing here selects or ranks a representation, and the DB9
    decoder is never refit on a subset.
    """
    m = disagree if disagree.any() else np.ones(len(disagree), bool)
    a = abs_contrib[m].mean(axis=0)
    s = share[m].mean(axis=0)
    views = {
        "canonical16": {
            "n_dof": 16,
            "mean_abs_contribution_per_dof": [float(v) for v in a],
            "mean_contribution_share_per_dof": [float(v) for v in s],
            "total_mean_abs_contribution": float(a.sum()),
        },
        "canonical15_noThumbAA": {
            "n_dof": 15,
            "dropped": ["thumb_cmc_ab_adduction"],
            "mean_abs_contribution_per_dof": [
                float(v) for i, v in enumerate(a) if i != 1],
            "total_mean_abs_contribution": float(a[[i for i in range(16) if i != 1]].sum()),
        },
        "canonical12_noDIP": {
            "n_dof": 12,
            "dropped": [CANON16[i] for i in CANON12_IDX[12:]] if len(CANON12_IDX) > 12 else
                       ["index_dip_flexion", "middle_dip_flexion",
                        "ring_dip_flexion", "pinky_dip_flexion"],
            "mean_abs_contribution_per_dof": [float(a[i]) for i in CANON12_IDX],
            "total_mean_abs_contribution": float(a[CANON12_IDX].sum()),
        },
        "group_decomposition": {
            gname: float(a[cols].sum()) for gname, cols in DOF_GROUPS.items()
        },
        "policy": (
            "descriptive only; no representation is selected, ranked or preferred "
            "on the basis of these numbers, and no decoder is refit"
        ),
    }
    return views


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--limit", type=int, default=None, help="process only the first N sessions")
    ap.add_argument("--episodes-dir", default=None,
                    help="where the per-session paired arrays go (default <out>/sessions)")
    ap.add_argument("--no-2khz", action="store_true",
                    help="skip the 2 kHz GT-valid pairing dump (50 Hz is the reported grid)")
    args = ap.parse_args()

    out_dir = os.path.abspath(args.out_dir)
    sess_dir = args.episodes_dir or os.path.join(out_dir, "sessions")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(sess_dir, exist_ok=True)

    t_start = time.time()
    results: dict = {"stage": "SESSION 5 -- CROSS-DATASET BRIDGE AUDIT"}

    results["question"] = (
        "Does wrist-EMG pose estimation preserve the frozen posture-relevant "
        "kinematic geometry well enough that a DB9-trained decoder behaves "
        "consistently with an oracle-GT-pose decoder?"
    )
    results["explicitly_not"] = [
        "gesture recognition / gesture accuracy",
        "posture accuracy against true action labels (emg2pose has none at frame level)",
        "a Session-3 re-analysis or new Session-3 evidence",
        "a claim about the 43 outcome-unseen DB9 subjects (used only as the PHASE-1 handshake target)",
    ]

    # ---------------- provenance ------------------------------------------
    prov_paths = [
        REPS_77, REPS_77_META, COHORTS, FROZEN_SPEC, FULL_DB9_RESULTS,
        os.path.join(DOCS_DIR, "CANONICAL16_CONTRACT.md"),
        os.path.join(ROOT, "representation", "canonical_hand.py"),
        os.path.join(ROOT, "representation", "canonical16_schema.json"),
        os.path.join(ROOT, "representation", "db9_to_canonical16.py"),
        os.path.join(ROOT, "inference", "predict_pose.py"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "decoder.py"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_bridge_audit.py"),
        os.path.join(CHECKPOINT_DIR, "regression_vemg2pose.ckpt"),
        os.path.join(MINI_DIR, "metadata.csv"),
    ]
    results["provenance"] = {
        "artifact_hashes_sha256": hash_artifacts(prov_paths),
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "cwd_policy": "ASCII junction <PROJECT_ROOT> used for all data paths",
        },
        "git": git_state(),
        "no_training": (
            "The only model executed is the official pretrained regression_vemg2pose "
            "checkpoint, loaded read-only in eval() mode under torch.no_grad(). "
            "No parameter was updated anywhere in this audit. The only fitting is "
            "the closed-form StandardScaler + LDA refit of the frozen DB9 decoder."
        ),
    }
    try:
        import sklearn
        import torch
        results["provenance"]["environment"]["sklearn"] = sklearn.__version__
        results["provenance"]["environment"]["torch"] = torch.__version__
    except Exception:  # noqa: BLE001
        pass

    # ---------------- PHASE 1 ---------------------------------------------
    print("=" * 78)
    print("PHASE 1 -- reconstruct the frozen Session-3 primary decoder")
    print("=" * 78)
    dec = D.reconstruct(verbose=True)
    geom = dec.geometry
    results["phase1_decoder_reconstruction"] = {
        "representation": "canonical16 (frozen Session-2 adapter)",
        "classes": [int(c) for c in dec.classes],
        "class_names": db9_class_names(dec.classes),
        "model": "LinearDiscriminantAnalysis(solver='lsqr', shrinkage='auto')",
        "normalization": "StandardScaler fitted on TRAIN samples only (train-only z-score)",
        "train_subjects": dec.train_subjects,
        "n_train_subjects": len(dec.train_subjects),
        "test_subjects_used_for_handshake_only": dec.test_subjects,
        "training_artifact": os.path.relpath(REPS_77, ROOT).replace("\\", "/"),
        "cohort_artifact": os.path.relpath(COHORTS, ROOT).replace("\\", "/"),
        "selection": (
            "NOT selected, NOT tuned, and NOT re-fitted on emg2pose data. The "
            "classifier is reconstructed by identity from the frozen Session-3 "
            "configuration; the emg2pose corpus never enters its fitting."
        ),
        "handshake_vs_frozen_tier_A": dec.handshake,
        "handshake_source_artifact": os.path.relpath(FULL_DB9_RESULTS, ROOT).replace("\\", "/"),
        "serialized_parameters": {
            "scaler_mean": dec.scaler.mean_.tolist(),
            "scaler_scale": dec.scaler.scale_.tolist(),
            "scaler_var": dec.scaler.var_.tolist(),
            "lda_classes": [int(c) for c in dec.classes],
            "lda_coef": dec.lda.coef_.tolist(),
            "lda_intercept": dec.lda.intercept_.tolist(),
            "lda_priors": [float(v) for v in np.atleast_1d(dec.lda.priors_)],
            "lda_solver": dec.lda.solver,
            "lda_shrinkage_setting": dec.lda.shrinkage,
            "lda_shrinkage_used_per_class_recomputed": dec.geometry.per_class_shrinkage,
            "canonical16_names": list(CANON16),
            "note": (
                "class order = ascending class id (1,2,3,4,6,7), matching "
                "LinearDiscriminantAnalysis.classes_"
            ),
        },
    }
    geom_json = geom.to_json()
    geom_json["class_order"] = [int(c) for c in dec.classes]
    geom_json["class_names"] = db9_class_names(dec.classes)
    results["phase5_db9_geometry"] = geom_json

    # DB9-internal discriminant-energy reference (what ordinary within-class
    # variation looks like in the same subspace) -- computed from DB9 train only.
    train = D.load_training_representation()
    cls_list = [int(c) for c in dec.classes]
    tr_mask = np.isin(train["subject"], dec.train_subjects) & np.isin(
        train["movement"], cls_list)
    te_mask = np.isin(train["subject"], dec.test_subjects) & np.isin(
        train["movement"], cls_list)
    Ztr = dec.z(train["X16"][tr_mask])
    dz_train = Ztr - geom.centroids[
        [cls_list.index(int(m)) for m in train["movement"][tr_mask]]
    ]
    tot = (dz_train ** 2).sum(axis=1)
    dsc = ((dz_train @ geom.discriminant_dirs) ** 2).sum(axis=1)
    results["phase5_db9_geometry"]["db9_within_class_discriminant_energy_fraction"] = {
        "mean": float((dsc / np.maximum(tot, 1e-30)).mean()),
        "median": float(np.median(dsc / np.maximum(tot, 1e-30))),
        "mean_total_error_z": float(np.sqrt(tot).mean()),
        "mean_discriminant_error_z": float(np.sqrt(dsc).mean()),
        "role": (
            "the DB9-only yardstick for 'error parallel to harmless within-class "
            "variation'. Computed from DB9 training data only."
        ),
    }

    # ---- PHASE 5 calibration of the distance statistic on DB9 itself ------
    # The 95th-percentile threshold is DEFINED on DB9 training, so it must by
    # construction flag 5% of DB9 training samples.  What is genuinely
    # informative is how it behaves on the DB9 held-out (outcome-unseen)
    # samples, and how the statistic decomposes per class.  Both are computed
    # here, before any emg2pose value is looked at.
    results["phase5_db9_geometry"]["db9_internal_calibration"] = {
        "policy": (
            "the distance statistic is calibrated on DB9 ONLY. This block is what "
            "makes an emg2pose number interpretable; it never sees emg2pose."
        ),
        "train_samples": int(tr_mask.sum()),
        "heldout_samples": int(te_mask.sum()),
        "train_fraction_beyond_p95": float(
            (geom.reference_distance > geom.thresholds["p95"]).mean()),
        "heldout_distance": describe(
            geom.min_mahalanobis(dec.z(train["X16"][te_mask]), geom.centroids,
                                 geom.precision),
            prefix="db9_heldout_min_maha_"),
        "heldout_fraction_beyond_train_p95": float(
            (geom.min_mahalanobis(dec.z(train["X16"][te_mask]), geom.centroids,
                                  geom.precision) > geom.thresholds["p95"]).mean()),
        "per_class_train_min_maha": {
            str(c): describe(
                geom.min_mahalanobis(dec.z(train["X16"][tr_mask & (train["movement"] == c)]),
                                     geom.centroids, geom.precision),
                prefix="")
            for c in cls_list
        },
        "per_class_heldout_min_maha": {
            str(c): describe(
                geom.min_mahalanobis(dec.z(train["X16"][te_mask & (train["movement"] == c)]),
                                     geom.centroids, geom.precision),
                prefix="")
            for c in cls_list
        },
        "interpretation": (
            "A sample whose distance is at or below this threshold is inside the "
            "region the six DB9 classes occupy at the 95% level; beyond it, the "
            "frozen decoder is extrapolating."
        ),
    }

    # ---- frozen-decoder quality reference on DB9 (context, not evidence) --
    results["phase1_decoder_reconstruction"]["db9_heldout_reference"] = {
        "accuracy_on_the_43_outcome_unseen_subjects": dec.handshake["accuracy_frozen"],
        "role": (
            "CONTEXT ONLY. This is the frozen Session-3 Tier-A number, reproduced "
            "here solely to prove the reconstructed decoder is the same object. It "
            "is not new Session-3 evidence and no Session-3 claim is re-made."
        ),
    }

    # ---------------- PHASE 2/3 -------------------------------------------
    print()
    print("=" * 78)
    print("PHASE 2/3 -- VEMG2Pose inference on the official mini corpus, paired with GT")
    print("=" * 78)
    files = sorted(glob.glob(os.path.join(MINI_DIR, "*.hdf5")))
    if args.limit:
        files = files[: args.limit]
    if not files:
        raise SystemExit(f"no official mini-corpus sessions under {MINI_DIR}")

    from predict_pose import PredictPose  # S2 frozen wrapper

    model = PredictPose(experiment="regression_vemg2pose", device="cpu")
    desc = model.describe()
    print(f"  model: {desc['experiment']}  left_context={desc['left_context']}  "
          f"right_context={desc['right_context']}  provide_initial_pos={desc['provide_initial_pos']}")

    session_recs = []
    for i, f in enumerate(files, 1):
        t0 = time.time()
        rec = process_session(f, model, save_2khz=not args.no_2khz, out_dir=sess_dir)
        session_recs.append(rec)
        print(f"  [{i:2d}/{len(files)}] {rec['session'][-46:]:<48} "
              f"T={rec['n_samples_2khz']:>7d}  paired50Hz={rec['n_paired_valid_50hz']:>6d}  "
              f"GTvalid={1-rec['gt_ik_failure_fraction_50hz']:.3f}  "
              f"{rec['realtime_factor']:.1f}x RT  {time.time()-t0:.1f}s")

    results["phase2_3_corpus"] = {
        "dataset": "official emg2pose mini corpus (data/official/emg2pose_dataset_mini)",
        "model": desc,
        "checkpoint": os.path.relpath(
            os.path.join(CHECKPOINT_DIR, "regression_vemg2pose.ckpt"), ROOT).replace("\\", "/"),
        "n_sessions": len(session_recs),
        "users": sorted({r["user"] for r in session_recs}),
        "stages": sorted({r["stage"] for r in session_recs}),
        "sides": sorted({r["side"] for r in session_recs}),
        "sessions": session_recs,
        "inference_only": (
            "no fine-tuning, no training, no parameter update; eval() + torch.no_grad()"
        ),
        "model_identity_evidence": model_identity_evidence(),
    }

    total_50hz = int(sum(r["n_gt_valid_50hz"] for r in session_recs))
    total_paired = int(sum(r["n_paired_valid_50hz"] for r in session_recs))
    total_2khz = int(sum(r["n_samples_2khz"] for r in session_recs))
    eff = [r["effective_pose_rate_hz"] for r in session_recs]
    results["phase3_pseudoreplication_control"] = {
        "native_block": POSE_STRIDE,
        "reduction": (
            "non-overlapping 20 ms blocks of the 2 kHz series reduced to ONE value "
            "by averaging, applied identically to GT and to the prediction; a block "
            "is GT-valid only if every one of its 40 samples is GT-valid"
        ),
        "rationale": (
            "Session 2 established (VERIFIED-EXEC) that the returned trajectory is "
            "aligned to the 2 kHz EMG timeline but holds only ~50 Hz of independent "
            "pose estimates. Every bridge statistic is computed at that native "
            "cadence; the 2 kHz timeline is never treated as independent N."
        ),
        "native_grid_measurement": {
            "method": "|second difference| of the returned 2 kHz series "
                      "(piecewise-linear interpolation detection) on the first 400 samples",
            "honest_limitation": (
                "the interpolation is carried out in float32, so a node's |second "
                "difference| is dominated by rounding (~1e-7) and does NOT collapse "
                "to zero. This measurement therefore CANNOT pin the fencepost phase, "
                "which is why the block-mean reduction above is used instead of "
                "picking a stride phase. It does confirm the series is smooth at the "
                "sample-to-sample scale (median |d2| ~1.5e-8 on the raw prediction)."
            ),
            "median_abs_second_difference_prediction": [
                r["native_grid"]["median_abs_second_difference"] for r in session_recs],
            "median_abs_second_difference_by_stride": [
                r["native_grid"]["stride_profile_median_abs_d2"] for r in session_recs],
        },
        "counts": {
            "sessions": len(session_recs),
            "samples_2khz_total": total_2khz,
            "pose_samples_2khz_total": int(sum(r["n_pose_samples_2khz"] for r in session_recs)),
            "pose_samples_at_native_cadence_total": int(
                sum(r["n_pose_samples_50hz"] for r in session_recs)),
            "native_cadence_samples_discarded_total": int(
                sum(r["native_grid_discarded_samples"] for r in session_recs)),
            "gt_valid_paired_samples_native_cadence": total_50hz,
            "gt_valid_and_pred_valid_samples_native_cadence": total_paired,
        },
        "effective_pose_sampling_rate_hz": {
            "derived": float(EMG_RATE / POSE_STRIDE),
            "median_over_sessions_timestamp_derived": float(np.median(eff)),
            "min": float(np.min(eff)),
            "max": float(np.max(eff)),
        },
        "aggregation_unit": "SESSION (primary); frame-level values are secondary",
    }
    print(f"  -> {total_50hz} GT-valid paired samples at ~50 Hz "
          f"({total_paired} of them also predicted-valid) over {len(session_recs)} "
          f"sessions; the 2 kHz timeline holds {total_2khz} samples and is NOT used as N")

    # ---------------- assemble paired arrays ------------------------------
    print()
    print("[aggregate] loading paired session arrays")
    G, P, V, S = [], [], [], []
    for r in session_recs:
        z = np.load(os.path.join(sess_dir, f"{r['session']}.paired50hz.npz"))
        G.append(z["gt16"].astype(np.float64))
        P.append(z["pred16"].astype(np.float64))
        V.append(z["gt_valid"].astype(bool))
        S.append(np.full(z["gt16"].shape[0], r["session"], dtype=object))
    gt16 = np.concatenate(G)
    pr16 = np.concatenate(P)
    valid = np.concatenate(V)
    sid = np.concatenate(S)

    # ---------------- PHASE 4 ---------------------------------------------
    print()
    print("=" * 78)
    print("PHASE 4 -- pose estimation error in canonical space (BRIDGE diagnostic)")
    print("=" * 78)
    per_session_err = []
    for r in session_recs:
        m = (sid == r["session"]) & valid
        e = np.abs(np.degrees(pr16[m] - gt16[m]))
        per_session_err.append({
            "session": r["session"], "stage": r["stage"], "side": r["side"],
            "n": int(m.sum()),
            "canonical16_MAE_deg": float(e.mean()),
            "canonical16_median_abs_deg": float(np.median(e)),
            "canonical15_noThumbAA_MAE_deg": float(e[:, CANON15_IDX].mean()),
            "canonical12_noDIP_MAE_deg": float(e[:, CANON12_IDX].mean()),
        })
    errv = np.array([r["canonical16_MAE_deg"] for r in per_session_err])
    results["phase4_pose_error"] = pose_error_block(gt16, pr16, valid, per_session_err)
    results["phase4_pose_error"]["per_session_summary"] = {
        "canonical16_MAE_deg": describe(errv, prefix="sess_"),
        "unit_of_aggregation": "session",
    }
    e16 = results["phase4_pose_error"]["canonical16"]
    print(f"  canonical16 MAE = {e16['MAE_deg_overall']:.3f} deg  "
          f"(median |err| {np.median(np.abs(np.degrees(pr16[valid]-gt16[valid]))):.3f} deg), "
          f"per-session MAE {errv.min():.2f}-{errv.max():.2f} deg")

    # ---------------- PHASE 5/6/7/8 ---------------------------------------
    print()
    print("=" * 78)
    print("PHASE 5/6/7/8 -- domain compatibility, decoder stability, discriminant error")
    print("=" * 78)
    dec_out = decision_analysis(gt16, pr16, valid, dec, geom, sid)
    A = dec_out.pop("_arrays")

    results["phase5_domain_compatibility"] = {
        "threshold_frozen_before_emg2pose_inspection": True,
        "threshold_source": "DB9 development-training samples only (n=1224)",
        "p95_threshold": geom.thresholds["p95"],
        "db9_reference_percentiles": geom.thresholds,
        "emg2pose_gt": dec_out["domain_distance"]["gt"],
        "emg2pose_predicted": dec_out["domain_distance"]["predicted"],
        "interpretation_rule": (
            "If emg2pose GT itself lies strongly outside DB9 support, decoder "
            "outputs on it must be treated as extrapolation, not as semantic "
            "posture predictions."
        ),
        "per_session": per_session_table(A, session_recs, geom),
    }
    print(f"  DB9 p95 distance threshold (DB9-only) = {geom.thresholds['p95']:.3f}; "
          f"emg2pose GT median = {np.median(A['dist_g']):.3f} "
          f"({100*np.mean(A['dist_g']>geom.thresholds['p95']):.1f}% beyond), "
          f"predicted median = {np.median(A['dist_p']):.3f} "
          f"({100*np.mean(A['dist_p']>geom.thresholds['p95']):.1f}% beyond)")

    results["phase6_decoder_stability"] = {k: v for k, v in dec_out.items()
                                           if k not in ("attribution", "discriminant_error")}
    results["phase7_discriminant_error"] = dec_out["discriminant_error"]
    results["phase7_discriminant_error"]["db9_within_class_reference"] = (
        results["phase5_db9_geometry"]["db9_within_class_discriminant_energy_fraction"])
    results["phase8_attribution"] = dec_out["attribution"]
    results["phase6_decoder_stability"]["per_session"] = per_session_table(
        A, session_recs, geom)

    print(f"  top-1 agreement (GT-pose vs predicted-pose) = "
          f"{100*dec_out['top1_agreement']:.3f}%  ({dec_out['n_disagree']} of "
          f"{dec_out['n_samples']} frames differ)")
    print(f"  mean |dP| = {dec_out['probability_difference']['mean_abs_prob_diff']:.4f}, "
          f"mean JSD = {np.mean(A['jsd']):.4f}")
    de = dec_out["discriminant_error"]
    print(f"  discriminant-subspace error energy fraction = "
          f"{de['mean_discriminant_energy_fraction']:.4f} "
          f"(DB9 within-class reference "
          f"{results['phase5_db9_geometry']['db9_within_class_discriminant_energy_fraction']['mean']:.4f})")

    # ---------------- session-level variability ---------------------------
    results["phase13_session_level_variability"] = session_variability(
        A, session_recs, geom)

    # ---------------- artefacts -------------------------------------------
    os.makedirs(os.path.join(out_dir, "figures"), exist_ok=True)
    results["artifacts"] = {
        "out_dir": out_dir,
        "sessions_dir": sess_dir,
        "elapsed_seconds": None,
    }
    results["artifacts"]["elapsed_seconds"] = float(time.time() - t_start)

    main_path = os.path.join(out_dir, "bridge_audit_results.json")
    with open(main_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, default=_jsonable)
    print(f"\n[written] {main_path}")

    # compact summary
    summary = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "question": results["question"],
        "phase1_handshake_PASS": dec.handshake["PASS"],
        "sessions": len(session_recs),
        "paired_valid_samples_50hz": total_50hz,
        "effective_rate_hz": results["phase3_pseudoreplication_control"][
            "effective_pose_sampling_rate_hz"]["derived"],
        "canonical16_MAE_deg": e16["MAE_deg_overall"],
        "db9_p95_threshold": geom.thresholds["p95"],
        "gt_median_db9_distance": float(np.median(A["dist_g"])),
        "gt_fraction_beyond_db9_p95": dec_out["domain_distance"]["gt"]["fraction_beyond_db9_p95"],
        "pred_median_db9_distance": float(np.median(A["dist_p"])),
        "pred_fraction_beyond_db9_p95": dec_out["domain_distance"]["predicted"]["fraction_beyond_db9_p95"],
        "top1_decoder_agreement": dec_out["top1_agreement"],
        "mean_abs_prob_diff": dec_out["probability_difference"]["mean_abs_prob_diff"],
        "mean_jsd": float(np.mean(A["jsd"])),
        "discriminant_energy_fraction": de["mean_discriminant_energy_fraction"],
        "db9_within_class_discriminant_energy_fraction":
            results["phase5_db9_geometry"]["db9_within_class_discriminant_energy_fraction"]["mean"],
    }
    with open(os.path.join(out_dir, "BRIDGE_AUDIT_SUMMARY.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=_jsonable)
    print(f"[written] {os.path.join(out_dir, 'BRIDGE_AUDIT_SUMMARY.json')}")
    return 0


def per_session_table(A: dict, session_recs: list[dict], geom) -> list[dict]:
    sid = A["sid"]
    thr95 = geom.thresholds["p95"]
    rows = []
    for r in session_recs:
        m = sid == r["session"]
        if m.sum() == 0:
            continue
        rows.append({
            "session": r["session"], "stage": r["stage"], "side": r["side"],
            "n": int(m.sum()),
            "canonical16_MAE_deg": float(A["canon16_abs_err_deg"][m].mean()),
            "canonical16_median_abs_err_deg": float(np.median(A["canon16_abs_err_deg"][m])),
            "top1_agreement": float(A["agree"][m].mean()),
            "boundary_pair_changed_rate": float(A["pair_changed"][m].mean()),
            "mean_abs_prob_diff": float(A["abs_pd"][m].mean()),
            "mean_jsd": float(A["jsd"][m].mean()),
            "gt_mean_margin": float(A["margin_g"][m].mean()),
            "mean_margin_change": float(A["margin_delta"][m].mean()),
            "gt_median_db9_dist": float(np.median(A["dist_g"][m])),
            "pred_median_db9_dist": float(np.median(A["dist_p"][m])),
            "gt_fraction_beyond_db9_p95": float((A["dist_g"][m] > thr95).mean()),
            "pred_fraction_beyond_db9_p95": float((A["dist_p"][m] > thr95).mean()),
            "mean_discriminant_energy_fraction": float(A["disc_frac"][m].mean()),
        })
    return rows


def session_variability(A: dict, session_recs: list[dict], geom) -> dict:
    tab = per_session_table(A, session_recs, geom)
    ag = np.array([r["top1_agreement"] for r in tab])
    return {
        "unit": "session",
        "n_sessions": len(tab),
        "top1_agreement": describe(ag, prefix="sess_"),
        "sessions_at_100pct_agreement": int((ag >= 1.0 - 1e-12).sum()),
        "sessions_below_95pct_agreement": int((ag < 0.95).sum()),
        "worst_session": tab[int(np.argmin(ag))] if tab else None,
        "best_session": tab[int(np.argmax(ag))] if tab else None,
        "canonical16_MAE_deg": describe(
            np.array([r["canonical16_MAE_deg"] for r in tab]), prefix="sess_"),
        "mean_abs_prob_diff": describe(
            np.array([r["mean_abs_prob_diff"] for r in tab]), prefix="sess_"),
        "mean_jsd": describe(np.array([r["mean_jsd"] for r in tab]), prefix="sess_"),
        "gt_fraction_beyond_db9_p95": describe(
            np.array([r["gt_fraction_beyond_db9_p95"] for r in tab]), prefix="sess_"),
        "pred_fraction_beyond_db9_p95": describe(
            np.array([r["pred_fraction_beyond_db9_p95"] for r in tab]), prefix="sess_"),
        "table": tab,
    }


def db9_class_names(classes) -> list[str]:
    from db9 import labels  # S3 frozen label module, read-only

    out = []
    for c in classes:
        try:
            out.append(str(labels.movement_name(1, int(c))))
        except Exception:  # noqa: BLE001
            out.append(str(int(c)))
    return out


def model_identity_evidence() -> dict:
    meta = os.path.join(MINI_DIR, "metadata.csv")
    ev: dict = {"checkpoint_sha256": sha256_file(
        os.path.join(CHECKPOINT_DIR, "regression_vemg2pose.ckpt"))}
    try:
        import pandas as pd

        df = pd.read_csv(meta)
        # NOTE: metadata.csv lists ``filename`` WITHOUT the .hdf5 extension, while
        # the on-disk files carry it. Joining on the raw name silently matches
        # nothing, which is exactly the kind of failure this audit must not hide,
        # so both forms are tried and the join size is reported.
        mini_files = {os.path.basename(p) for p in glob.glob(os.path.join(MINI_DIR, "*.hdf5"))}
        raw = df["filename"].astype(str)
        sub = df[raw.isin(mini_files) | raw.isin({os.path.splitext(f)[0] for f in mini_files})]
        ev["mini_corpus_metadata"] = {
            "hdf5_files_on_disk": len(mini_files),
            "metadata_rows_matched": int(len(sub)),
            "join_key": "metadata.filename vs on-disk basename, with and without '.hdf5'",
            "users": sorted(sub["user"].unique().tolist()),
            "split_values": sorted(sub["split"].unique().tolist()),
            "generalization_values": sorted(sub["generalization"].unique().tolist()),
            "held_out_user_values": sorted(bool(v) for v in sub["held_out_user"].unique()),
            "held_out_stage_values": sorted(bool(v) for v in sub["held_out_stage"].unique()),
            "note": (
                "the mini corpus is a single user whose metadata rows are marked "
                "held_out_user=True and split='val'; we additionally confirm the "
                "user does not occur in any train-split row. The released "
                "checkpoint predates the public dataset release, so this is the "
                "strongest available evidence about the model's exposure to this "
                "user, not an absolute guarantee. The SAME user appears on both the "
                "left and right side and in every stage, so side/stage variability "
                "is within-subject only -- it is NOT cross-subject evidence."
            ),
        }
        ev["mini_user_in_train_split_rows"] = int(
            df[(df["user"].isin(sub["user"].unique())) & (df["split"] == "train")].shape[0])
        ev["checkpoint_predates_dataset_release"] = (
            "UNVERIFIED-HERE: the checkpoint's mtime predates the public dataset "
            "release (observed locally), but the training split of the released "
            "checkpoint could not be re-derived in this session."
        )
    except Exception as exc:  # noqa: BLE001
        ev["metadata_error"] = repr(exc)
    return ev


def git_state() -> dict:
    import subprocess

    out = {"project_root_is_git_repo": os.path.isdir(os.path.join(ROOT, ".git"))}
    for name, cwd in (("baseline_emg2pose", BASELINE_DIR),):
        try:
            r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True,
                               text=True, timeout=20)
            out[f"{name}_head"] = r.stdout.strip() or None
            r2 = subprocess.run(["git", "status", "--porcelain"], cwd=cwd,
                                capture_output=True, text=True, timeout=20)
            out[f"{name}_dirty"] = bool(r2.stdout.strip())
        except Exception as exc:  # noqa: BLE001
            out[f"{name}_error"] = repr(exc)
    return out


def _jsonable(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


if __name__ == "__main__":
    raise SystemExit(main())
