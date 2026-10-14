#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GATE 3 — FORMAL UPSTREAM SUBSTITUTION BASELINE (server-side analysis).

Implements GATE3_PLAN.md exactly and nothing else.

Two routes, one frozen head:
    ROUTE A (oracle)      : emg2pose GT 20-D pose -> trusted-8 -> frozen DB9 head -> Y_GT
    ROUTE B (substituted) : EMG -> official emg2pose estimator -> 20-D predicted pose
                            -> same trusted-8 -> same frozen DB9 head -> Y_PRED

NO gate, NO reliability filter, NO UNKNOWN, NO abstention, NO human labels,
NO calibration fitting, NO task-specific retraining, NO outcome-driven shift search.

Run:
  <env>/bin/python -X utf8 run_gate3_substitution.py
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sys
import time
from collections import Counter

import h5py
import joblib
import numpy as np

LANE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(LANE, "artifacts")
LOGS = os.path.join(LANE, "logs")
MODELS = os.path.join(LANE, "models")
os.makedirs(ART, exist_ok=True)
os.makedirs(LOGS, exist_ok=True)
os.makedirs(MODELS, exist_ok=True)

PLAN = os.path.join(LANE, "GATE3_PLAN.md")
PLAN_SHA = hashlib.sha256(open(PLAN, "rb").read()).hexdigest()

MINI_DIR = "/root/data/emg2pose_dataset_mini"
PRED_DIR = "/root/work/gate3_work/pred_pose"
HEAD_JOBLIB = "/root/work/gate3_work/frozen_head/frozen_db9_trusted8_lda.joblib"

POSE_STRIDE = 40          # 2000 / 50 -> native 50 Hz analysis cadence
EMG_RATE = 2000
ANALYSIS_HZ = 50.0

TRUSTED8_SRC_IDX = [2, 3, 5, 6, 9, 13, 17, 18]
TRUSTED8_NAMES = ["thumb_mcp_flexion", "thumb_ip_flexion", "index_mcp_flexion",
                  "index_pip_flexion", "middle_mcp_flexion", "ring_mcp_flexion",
                  "pinky_mcp_flexion", "pinky_pip_flexion"]
CLASSES = [1, 2, 3, 4, 5, 6, 7, 8]

# Plan-declared parameters (must match GATE3_PLAN.md)
MIN_CLASS_SUPPORT = 30
TRANSITION_TOL_FRAMES = 1
N_DECILES = 10

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


def rank_ic(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman rank correlation (ties averaged). Descriptive only."""
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
    d = np.sqrt((rx ** 2).sum() * (ry ** 2).sum())
    return float((rx * ry).sum() / d) if d > 0 else float("nan")


def js_divergence(p: np.ndarray, q: np.ndarray) -> np.ndarray:
    """Jensen-Shannon divergence, base 2, row-wise. p,q: (N,K) non-negative."""
    m = 0.5 * (p + q)
    tiny = 1e-300
    def kl(a, b):
        a = np.clip(a, 0.0, 1.0)
        b = np.clip(b, tiny, 1.0)
        term = np.where(a > 0, a * np.log2(a / b), 0.0)
        return term.sum(axis=1)
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def tv_distance(p: np.ndarray, q: np.ndarray) -> np.ndarray:
    return 0.5 * np.abs(p - q).sum(axis=1)


def qstats(a: np.ndarray) -> dict:
    if a is None or np.size(a) == 0:
        return {k: None for k in ("n", "median", "p25", "p75", "iqr", "p05", "p95",
                                  "mean")}
    a = np.asarray(a, dtype=np.float64)
    q = np.percentile(a, [5, 25, 75, 95])
    return {"n": int(a.size), "median": float(np.median(a)), "p25": float(q[1]),
            "p75": float(q[2]), "iqr": float(q[2] - q[1]), "p05": float(q[0]),
            "p95": float(q[3]), "mean": float(a.mean())}


def temporal_stats(seqs: list[np.ndarray]) -> dict:
    sw = 0
    tot = 0
    durs = []
    for p in seqs:
        if p.size < 2:
            if p.size == 1:
                durs.append(1)
            continue
        ch = np.flatnonzero(p[1:] != p[:-1]) + 1
        sw += int(ch.size)
        tot += int(p.size - 1)
        bounds = np.concatenate(([0], ch, [p.size]))
        durs.extend(np.diff(bounds).tolist())
    d = np.array(durs, dtype=np.float64) if durs else np.zeros(0)
    return {
        "n_contiguous_transitions": tot,
        "n_switches": sw,
        "switch_rate_per_sample": float(sw / tot) if tot else None,
        "n_runs": int(d.size),
        "median_dwell_frames": float(np.median(d)) if d.size else None,
        "median_dwell_s": float(np.median(d) / ANALYSIS_HZ) if d.size else None,
        "p25_dwell_frames": float(np.percentile(d, 25)) if d.size else None,
        "p75_dwell_frames": float(np.percentile(d, 75)) if d.size else None,
    }


def transition_events(pred: np.ndarray) -> list[tuple[int, int, int]]:
    """[(index_of_destination_frame, from_class, to_class)] for a contiguous seq."""
    if pred.size < 2:
        return []
    ch = np.flatnonzero(pred[1:] != pred[:-1]) + 1
    return [(int(i), int(pred[i - 1]), int(pred[i])) for i in ch]


def main() -> int:
    t0 = time.time()
    log("=" * 78)
    log("GATE 3 — FORMAL UPSTREAM SUBSTITUTION BASELINE")
    log("=" * 78)
    log(f"plan            : {PLAN}")
    log(f"plan sha256     : {PLAN_SHA}")
    log(f"analysis rate   : {ANALYSIS_HZ} Hz ({POSE_STRIDE} stored rows per block)")
    log(f"trusted-8 emg2pose idx : {TRUSTED8_SRC_IDX}")
    log()

    # ---------------- frozen head ----------------
    bundle = joblib.load(HEAD_JOBLIB)
    head, mu, sd = bundle["head"], bundle["mu"], bundle["sd"]
    fh_meta = bundle["meta"]
    log("[1] frozen head loaded")
    log(f"    train frames : {fh_meta['train_frames']}")
    log(f"    classes      : {list(head.classes_)}")
    log(f"    replication  : {fh_meta['replication_check']['exact']} "
        f"({fh_meta['replication_check']['n_quantities_checked']} quantities)")
    log(f"    mu           : {np.round(mu, 6).tolist()}")
    log(f"    sd           : {np.round(sd, 6).tolist()}")
    assert fh_meta["replication_check"]["exact"] is True, "frozen head not reproduced"
    assert list(head.classes_) == CLASSES, "class set changed"
    log()

    # ---------------- per-record assembly ----------------
    files = sorted(glob.glob(os.path.join(MINI_DIR, "*.hdf5")))
    log(f"[2] records     : {len(files)}")

    blocks = []            # each: dict with arrays + meta
    stored_rows = 0
    gt_valid_rows = 0
    pred_valid_rows = 0
    aligned_rows = 0
    manifest_files = []

    for f in files:
        stem = os.path.basename(f)[: -len(".hdf5")]
        pf = os.path.join(PRED_DIR, f"{stem}_pred.npz")
        assert os.path.isfile(pf), f"missing prediction for {stem}"
        with h5py.File(f, "r") as h:
            g = h["emg2pose"]
            attrs = dict(g.attrs)
            ts = g["timeseries"]
            ja = ts["joint_angles"][:]
            tgt = ts["time"][:]
            emg_shape = ts["emg"].shape
        with np.load(pf) as z:
            ang = z["angles"]
            tpred = z["time"]
            row_offset = int(z["row_offset"])
            T_in = int(z["T_in"])

        T = ja.shape[0]
        stored_rows += T
        assert T_in == T
        assert ang.shape == (T - row_offset, 20)
        assert tpred.shape[0] == ang.shape[0]

        # ---- exact timestamp alignment (verified, not searched) ----
        assert np.array_equal(tgt[row_offset:], tpred), "timestamp grids differ"

        gt_w = ja[row_offset:]                                  # (n,20)
        pred_w = ang                                            # (n,20)
        n = gt_w.shape[0]
        aligned_rows += n

        gt_row_valid = (~np.all(np.isclose(gt_w, 0.0), axis=1)) & np.isfinite(gt_w).all(axis=1)
        pr_row_valid = (~np.all(np.isclose(pred_w, 0.0), axis=1)) & np.isfinite(pred_w).all(axis=1)
        gt_valid_rows += int(gt_row_valid.sum())
        pred_valid_rows += int(pr_row_valid.sum())

        nb = n // POSE_STRIDE
        usable = nb * POSE_STRIDE
        gt_blk = gt_w[:usable].reshape(nb, POSE_STRIDE, 20).mean(axis=1)[:, TRUSTED8_SRC_IDX]
        pr_blk = pred_w[:usable].reshape(nb, POSE_STRIDE, 20).mean(axis=1)[:, TRUSTED8_SRC_IDX]
        gt_ok = gt_row_valid[:usable].reshape(nb, POSE_STRIDE).all(axis=1)
        pr_ok = pr_row_valid[:usable].reshape(nb, POSE_STRIDE).all(axis=1)
        # Lead-block exclusion: the official rollout is initialised from a zero
        # initial pose at exactly t = left_context, so block 0 of every record is
        # the decoder's initialisation transient. Declared in GATE3_PLAN.md §5,
        # applied identically to both routes, fixed before any outcome was seen.
        if nb:
            gt_ok = gt_ok.copy()
            pr_ok = pr_ok.copy()
            gt_ok[0] = False
            pr_ok[0] = False
        both_ok = gt_ok & pr_ok

        blocks.append({
            "file": os.path.basename(f), "stem": stem, "side": str(attrs["side"]),
            "stage": str(attrs["stage"]), "user": str(attrs["user"]),
            "session": str(attrs["session"]),
            "gt_blk": gt_blk, "pr_blk": pr_blk,
            "gt_ok": gt_ok, "pr_ok": pr_ok, "both_ok": both_ok,
            "n_rows": n, "n_blocks": nb,
        })
        manifest_files.append({
            "file": os.path.basename(f), "side": str(attrs["side"]),
            "stage": str(attrs["stage"]), "user": str(attrs["user"]),
            "session": str(attrs["session"]),
            "stored_rows": T, "aligned_rows": n, "row_offset": row_offset,
            "blocks": nb, "gt_valid_rows": int(gt_row_valid.sum()),
            "pred_valid_rows": int(pr_row_valid.sum()),
            "gt_valid_blocks": int(gt_ok.sum()), "pred_valid_blocks": int(pr_ok.sum()),
            "both_valid_blocks": int(both_ok.sum()),
            "lead_block_excluded": True,
            "hdf5_sha256": sha256_file(f),
            "pred_sha256": sha256_file(pf),
        })
        log(f"    {stem[-34:]:<34} rows {T:>7} aligned {n:>7} blocks {nb:>5} "
            f"eligible {int(both_ok.sum()):>5}")

    # NOTE: the lead-block exclusion is applied above, where each record's blocks
    # are built, so both the analysis population and the manifest counts below are
    # already post-exclusion. There is deliberately no second fix-up pass here.

    # ---------------- assemble primary population ----------------
    gt_all, pr_all, side_all, stage_all, file_all, pos_all = [], [], [], [], [], []
    for bi, b in enumerate(blocks):
        m = b["both_ok"]
        if not m.any():
            continue
        gt_all.append(b["gt_blk"][m])
        pr_all.append(b["pr_blk"][m])
        k = int(m.sum())
        side_all.extend([b["side"]] * k)
        stage_all.extend([b["stage"]] * k)
        file_all.extend([b["stem"]] * k)
        pos_all.append(np.flatnonzero(m))
    G = np.vstack(gt_all)
    P = np.vstack(pr_all)
    side_all = np.array(side_all)
    stage_all = np.array(stage_all)
    file_all = np.array(file_all)
    N = G.shape[0]
    log()
    log(f"[3] analysis population (GT-valid AND pred-valid blocks): {N} samples "
        f"at {ANALYSIS_HZ} Hz")
    log(f"    stored rows {stored_rows} | GT-valid rows {gt_valid_rows} | "
        f"pred-valid rows {pred_valid_rows} | aligned rows {aligned_rows}")

    # ---------------- two routes, same frozen head ----------------
    Gz = (G - mu) / sd
    Pz = (P - mu) / sd
    y_gt = head.predict(Gz).astype(np.int16)
    y_pr = head.predict(Pz).astype(np.int16)
    proba_gt = head.predict_proba(Gz)
    proba_pr = head.predict_proba(Pz)
    cls_list = [int(c) for c in head.classes_]

    # ---------------- 12.1 hard agreement ----------------
    D = (y_pr != y_gt)
    agreement = float(1.0 - D.mean())
    log()
    log("[4] PRIMARY FUNCTIONAL PRESERVATION")
    log(f"    agreement      : {agreement:.6f}  (disagreement {int(D.sum())}/{N})")

    # ---------------- 12.2 balanced preservation ----------------
    support = {c: int((y_gt == c).sum()) for c in CLASSES}
    pres = {}
    for c in CLASSES:
        m = y_gt == c
        pres[c] = float((y_pr[m] == c).mean()) if m.any() else None
    sufficient = [c for c in CLASSES if support[c] >= MIN_CLASS_SUPPORT]
    insufficient = [c for c in CLASSES if support[c] < MIN_CLASS_SUPPORT]
    bal_pres = float(np.mean([pres[c] for c in sufficient])) if sufficient else None
    log(f"    balanced preservation (classes with support >= {MIN_CLASS_SUPPORT}): "
        f"{bal_pres:.6f}" if bal_pres is not None else "    balanced preservation: n/a")
    log(f"    sufficient classes : {sufficient}")
    log(f"    insufficient       : {insufficient}")
    for c in CLASSES:
        log(f"      class {c}: support {support[c]:>7}  preservation "
            f"{pres[c]:.6f}" if pres[c] is not None else f"      class {c}: no support")

    # ---------------- 12.3 Cohen kappa ----------------
    n_tot = N
    cm = np.zeros((8, 8), dtype=np.int64)
    for i, a in enumerate(CLASSES):
        for j, b_ in enumerate(CLASSES):
            cm[i, j] = int(((y_gt == a) & (y_pr == b_)).sum())
    row = cm.sum(1) / n_tot
    col = cm.sum(0) / n_tot
    p_o = float(np.trace(cm) / n_tot)
    p_e = float((row * col).sum())
    kappa = (p_o - p_e) / (1.0 - p_e) if p_e < 1.0 else float("nan")
    log(f"    Cohen kappa    : {kappa:.6f}  (p_o {p_o:.6f}, p_e {p_e:.6f})")

    # ---------------- 13 soft preservation ----------------
    tv = tv_distance(proba_gt, proba_pr)
    js = js_divergence(proba_gt, proba_pr)
    idx_gt = np.array([cls_list.index(int(c)) for c in y_gt])
    idx_pr = np.array([cls_list.index(int(c)) for c in y_pr])
    ref_p = proba_pr[np.arange(N), idx_gt]
    own_pred_p = proba_pr[np.arange(N), idx_pr]
    log()
    log("[5] SOFT-OUTPUT PRESERVATION")
    log(f"    TV  : median {np.median(tv):.6f} IQR [{np.percentile(tv,25):.6f}, "
        f"{np.percentile(tv,75):.6f}] p05 {np.percentile(tv,5):.6f} "
        f"p95 {np.percentile(tv,95):.6f}")
    log(f"    JS  : median {np.median(js):.6f} IQR [{np.percentile(js,25):.6f}, "
        f"{np.percentile(js,75):.6f}] p05 {np.percentile(js,5):.6f} "
        f"p95 {np.percentile(js,95):.6f}")
    log(f"    P_PRED[Y_GT] : median {np.median(ref_p):.6f} "
        f"mean {ref_p.mean():.6f}")

    # ---------------- 14 temporal preservation ----------------
    # Rebuild per-record contiguous label sequences in the SAME order used to
    # build G/P, so index arithmetic stays consistent.
    cursor = 0
    gt_seqs, pr_seqs = [], []
    for b in blocks:
        k = int(b["both_ok"].sum())
        if k == 0:
            continue
        gt_seqs.append(y_gt[cursor:cursor + k])
        pr_seqs.append(y_pr[cursor:cursor + k])
        cursor += k
    assert cursor == N, (cursor, N)

    t_gt = temporal_stats(gt_seqs)
    t_pr = temporal_stats(pr_seqs)

    # transition-event preservation, +-1 frame tolerance (pre-declared)
    n_events = 0
    n_matched = 0
    n_dest_matched = 0
    for a, b_ in zip(gt_seqs, pr_seqs):
        ev_gt = transition_events(a)
        ev_pr = transition_events(b_)
        pr_by_idx = {}
        for i, fr, to in ev_pr:
            pr_by_idx.setdefault(i, []).append((fr, to))
        for i, fr, to in ev_gt:
            n_events += 1
            hit_dest = False
            hit_exact = False
            for d in range(-TRANSITION_TOL_FRAMES, TRANSITION_TOL_FRAMES + 1):
                for (fr2, to2) in pr_by_idx.get(i + d, []):
                    if to2 == to:
                        hit_dest = True
                        if d == 0:
                            hit_exact = True
            n_dest_matched += int(hit_dest)
            n_matched += int(hit_exact)
    log()
    log("[6] TEMPORAL PRESERVATION")
    log(f"    GT   : switch rate {t_gt['switch_rate_per_sample']:.6f}/sample "
        f"median dwell {t_gt['median_dwell_frames']} frames "
        f"({t_gt['median_dwell_s']:.4f} s)")
    log(f"    PRED : switch rate {t_pr['switch_rate_per_sample']:.6f}/sample "
        f"median dwell {t_pr['median_dwell_frames']} frames "
        f"({t_pr['median_dwell_s']:.4f} s)")
    log(f"    transition events (GT) : {n_events}")
    log(f"    same destination within +-{TRANSITION_TOL_FRAMES} frame "
        f"({int(TRANSITION_TOL_FRAMES*1000/ANALYSIS_HZ)} ms): "
        f"{n_dest_matched}/{n_events} = "
        f"{n_dest_matched/n_events:.6f}" if n_events else "    no events")
    log(f"    same destination at exact frame : {n_matched}/{n_events} = "
        f"{n_matched/n_events:.6f}" if n_events else "    no events")

    # ---------------- 15 pose-level error ----------------
    err_deg = np.degrees(P - G)                      # (N,8)
    abs_deg = np.abs(err_deg)
    overall_rmse = float(np.sqrt((err_deg ** 2).mean()))
    overall_mae = float(abs_deg.mean())
    per_dof = {}
    log()
    log("[7] POSE-LEVEL ERROR (degrees, predicted vs GT, trusted-8)")
    log(f"    overall: RMSE {overall_rmse:.6f} deg | MAE {overall_mae:.6f} deg")
    log(f"    {'DOF':<22}{'MAE':>10}{'medAE':>10}{'RMSE':>10}{'p90':>10}{'p95':>10}")
    for j, nm in enumerate(TRUSTED8_NAMES):
        e = err_deg[:, j]
        ae = abs_deg[:, j]
        per_dof[nm] = {
            "mae": float(ae.mean()), "median_absolute_error": float(np.median(ae)),
            "rmse": float(np.sqrt((e ** 2).mean())),
            "p90_absolute_error": float(np.percentile(ae, 90)),
            "p95_absolute_error": float(np.percentile(ae, 95)),
            "bias_mean": float(e.mean()),
        }
        log(f"    {nm:<22}{per_dof[nm]['mae']:>10.4f}"
            f"{per_dof[nm]['median_absolute_error']:>10.4f}"
            f"{per_dof[nm]['rmse']:>10.4f}{per_dof[nm]['p90_absolute_error']:>10.4f}"
            f"{per_dof[nm]['p95_absolute_error']:>10.4f}")

    per_frame_err = np.sqrt((err_deg ** 2).mean(axis=1))   # trusted-8 RMSE per frame
    log(f"    frame-level trusted-8 RMSE: median {np.median(per_frame_err):.4f} deg, "
        f"mean {per_frame_err.mean():.4f} deg")

    # ---------------- 16 error -> functional failure ----------------
    order = np.argsort(per_frame_err, kind="mergesort")
    decile_idx = np.array_split(order, N_DECILES)
    curve = []
    log()
    log("[8] ERROR -> FUNCTIONAL FAILURE CURVE (pre-declared deciles)")
    log(f"    {'decile':<8}{'n':>8}{'med pose err':>14}{'disagree':>12}{'rate':>10}")
    for k, ix in enumerate(decile_idx, 1):
        e = per_frame_err[ix]
        d = D[ix]
        curve.append({
            "decile": k, "n": int(ix.size),
            "median_pose_error_deg": float(np.median(e)),
            "mean_pose_error_deg": float(e.mean()),
            "min_pose_error_deg": float(e.min()), "max_pose_error_deg": float(e.max()),
            "n_disagreement": int(d.sum()), "disagreement_rate": float(d.mean()),
        })
        log(f"    {k:<8}{ix.size:>8}{np.median(e):>14.4f}{int(d.sum()):>12}"
            f"{d.mean():>10.4f}")
    rho_frame = rank_ic(per_frame_err, D.astype(np.float64))
    log(f"    Spearman(frame pose error, disagreement) = {rho_frame:.6f} "
        f"(DESCRIPTIVE ONLY; one participant, temporally correlated)")

    dof_assoc = {}
    log()
    log("    per-DOF descriptive association with disagreement:")
    for j, nm in enumerate(TRUSTED8_NAMES):
        m1 = D
        med_err_fail = float(np.median(abs_deg[m1, j])) if m1.any() else None
        med_err_ok = float(np.median(abs_deg[~m1, j]))
        rho = rank_ic(abs_deg[:, j], D.astype(np.float64))
        dof_assoc[nm] = {"median_abs_err_when_disagree": med_err_fail,
                         "median_abs_err_when_agree": med_err_ok,
                         "spearman_abs_err_vs_disagreement": float(rho)}
        log(f"      {nm:<22} medAE|D=1 {med_err_fail if med_err_fail is None else round(med_err_fail,4)}"
            f"  medAE|D=0 {med_err_ok:.4f}  rho {rho:+.4f}")

    # ---------------- 17 class-conditional ----------------
    log()
    log("[9] CLASS-CONDITIONAL (reference class = Y_GT)")
    by_class = []
    for c in CLASSES:
        m = y_gt == c
        sup = int(m.sum())
        if sup == 0:
            by_class.append({"class": c, "support": 0, "preservation": None})
            log(f"    class {c}: support 0")
            continue
        dest = Counter(y_pr[m].tolist())
        dest.pop(c, None)
        main_dest = dest.most_common(1)[0] if dest else (None, 0)
        row = {
            "class": c, "support": sup,
            "support_fraction": float(sup / N),
            "preservation": float(pres[c]),
            "n_correct": int((y_pr[m] == c).sum()),
            "n_errors": int(sup - (y_pr[m] == c).sum()),
            "main_error_destination": int(main_dest[0]) if main_dest[0] is not None else None,
            "main_error_destination_count": int(main_dest[1]),
            "main_error_destination_fraction_of_errors":
                float(main_dest[1] / (sup - (y_pr[m] == c).sum()))
                if (sup - (y_pr[m] == c).sum()) > 0 else None,
            "median_pose_error_deg": float(np.median(per_frame_err[m])),
            "median_tv": float(np.median(tv[m])),
            "median_js": float(np.median(js[m])),
            "median_ref_prob": float(np.median(ref_p[m])),
            "error_destinations": {int(k): int(v) for k, v in dest.most_common()},
        }
        by_class.append(row)
        log(f"    class {c}: support {sup:>7} ({row['support_fraction']:.4f})  "
            f"pres {pres[c]:.6f}  main err -> {row['main_error_destination']} "
            f"({row['main_error_destination_count']})  "
            f"medPoseErr {row['median_pose_error_deg']:.4f} deg  "
            f"medTV {row['median_tv']:.6f}")

    # ---------------- 18 hand side ----------------
    log()
    log("[10] HAND-SIDE STRATIFICATION (descriptive)")
    by_side = {}
    for s_ in sorted(set(side_all.tolist())):
        m = side_all == s_
        n_s = int(m.sum())
        sp = {c: int((y_gt[m] == c).sum()) for c in CLASSES}
        pr_c = {}
        for c in CLASSES:
            mm = (y_gt == c) & m
            pr_c[c] = float((y_pr[mm] == c).mean()) if mm.any() else None
        suf = [c for c in CLASSES if sp[c] >= MIN_CLASS_SUPPORT]
        bp = float(np.mean([pr_c[c] for c in suf])) if suf else None
        cm_s = np.zeros((8, 8), dtype=np.int64)
        for i, a in enumerate(CLASSES):
            for j, b_ in enumerate(CLASSES):
                cm_s[i, j] = int(((y_gt[m] == a) & (y_pr[m] == b_)).sum())
        po = float(np.trace(cm_s) / n_s)
        pe = float(((cm_s.sum(1) / n_s) * (cm_s.sum(0) / n_s)).sum())
        kp = (po - pe) / (1 - pe) if pe < 1 else float("nan")
        by_side[s_] = {
            "n": n_s, "n_files": len({f for f, ss in zip(file_all, side_all)
                                      if ss == s_}),
            "agreement": float(1.0 - D[m].mean()),
            "balanced_preservation": bp,
            "balanced_preservation_classes": suf,
            "per_class_preservation": pr_c, "per_class_support": sp,
            "cohen_kappa": float(kp),
            "median_tv": float(np.median(tv[m])),
            "median_js": float(np.median(js[m])),
            "pose_mae_deg": float(abs_deg[m].mean()),
            "pose_rmse_deg": float(np.sqrt((err_deg[m] ** 2).mean())),
            "switch_rate_gt": None, "switch_rate_pred": None,
        }
        # side temporal
        gs, ps = [], []
        cur = 0
        for b in blocks:
            k = int(b["both_ok"].sum())
            if k == 0:
                continue
            if b["side"] == s_:
                gs.append(y_gt[cur:cur + k])
                ps.append(y_pr[cur:cur + k])
            cur += k
        by_side[s_]["switch_rate_gt"] = temporal_stats(gs)["switch_rate_per_sample"]
        by_side[s_]["switch_rate_pred"] = temporal_stats(ps)["switch_rate_per_sample"]
        log(f"    {s_:<6}: n {n_s:>7}  agree {by_side[s_]['agreement']:.6f}  "
            f"balPres {bp:.6f}  kappa {kp:.6f}  medTV {by_side[s_]['median_tv']:.6f}  "
            f"poseMAE {by_side[s_]['pose_mae_deg']:.4f} deg")

    # ---------------- 19 stage stratification ----------------
    log()
    log("[11] STAGE STRATIFICATION (stage = activity label, NOT ground truth)")
    by_stage = []
    cur = 0
    stage_bounds = {}
    for b in blocks:
        k = int(b["both_ok"].sum())
        if k == 0:
            continue
        stage_bounds.setdefault(b["stage"], []).append((cur, cur + k))
        cur += k
    for st in sorted(stage_bounds):
        segs = stage_bounds[st]
        ix = np.concatenate([np.arange(a, b_) for a, b_ in segs])
        n_s = ix.size
        sp = {c: int((y_gt[ix] == c).sum()) for c in CLASSES}
        pr_c = {}
        for c in CLASSES:
            mm = y_gt[ix] == c
            pr_c[c] = float((y_pr[ix][mm] == c).mean()) if mm.any() else None
        suf = [c for c in CLASSES if sp[c] >= MIN_CLASS_SUPPORT]
        bp = float(np.mean([pr_c[c] for c in suf])) if suf else None
        dom_gt = max(sp, key=sp.get)
        occ_pr = Counter(y_pr[ix].tolist())
        dom_pr = occ_pr.most_common(1)[0][0]
        sides_s = sorted({b["side"] for b in blocks if b["stage"] == st})
        by_stage.append({
            "stage": st, "sides": "|".join(sides_s),
            "n": int(n_s),
            "agreement": float(1.0 - D[ix].mean()),
            "balanced_preservation": bp,
            "balanced_preservation_classes": suf,
            "per_class_support": sp, "per_class_preservation": pr_c,
            "pose_mae_deg": float(abs_deg[ix].mean()),
            "dominant_gt_class": int(dom_gt),
            "dominant_gt_fraction": float(sp[dom_gt] / n_s),
            "dominant_pred_class": int(dom_pr),
            "dominant_pred_fraction": float(occ_pr[dom_pr] / n_s),
            "median_tv": float(np.median(tv[ix])),
        })
        log(f"    {st[:40]:<40} n {n_s:>7} agree {by_stage[-1]['agreement']:.4f} "
            f"MAE {by_stage[-1]['pose_mae_deg']:>7.4f} domGT {dom_gt} domPRED {dom_pr}")

    # ---------------- artifacts ----------------
    log()
    log("[12] writing artifacts")

    data_manifest = {
        "artifact": "GATE3_DATA_MANIFEST.json",
        "gate": "PHASE 1 / GATE 3 — formal upstream substitution baseline",
        "plan_sha256": PLAN_SHA,
        "participant": sorted({m["user"] for m in manifest_files}),
        "session": sorted({m["session"] for m in manifest_files}),
        "sides": sorted({m["side"] for m in manifest_files}),
        "stages": sorted({m["stage"] for m in manifest_files}),
        "n_files": len(manifest_files),
        "gt_source": {
            "path": MINI_DIR, "field": "emg2pose/timeseries/joint_angles",
            "dims": 20, "units": "radians",
            "records": len(manifest_files),
            "stored_rows": stored_rows,
        },
        "emg_source": {"path": MINI_DIR, "field": "emg2pose/timeseries/emg",
                       "channels": 16, "rate_hz": EMG_RATE},
        "predicted_pose_source": {
            "path": PRED_DIR, "estimator": "regression_vemg2pose (official EMG-only)",
            "checkpoint": "/root/models/emg2pose/regression_vemg2pose.ckpt",
            "checkpoint_sha256":
                "748b1d1ef0ce1985f6fc07225d97eebfb370243429af803b4997d28ecce2424e",
            "inference_script": "run_emg2pose_inference.py",
        },
        "frozen_head": {
            "path": HEAD_JOBLIB,
            "representation": "TRUSTED_DB9_POSE_v1",
            "frozen_subset_sha256":
                "e51dde6e63941fd080c84f3896a98cf50fba9e17d5f9cebe909253d5465782d1",
            "train_frames": fh_meta["train_frames"],
            "replication_exact": fh_meta["replication_check"]["exact"],
        },
        "counts": {
            "stored_rows": stored_rows,
            "aligned_rows": aligned_rows,
            "gt_valid_rows": gt_valid_rows,
            "pred_valid_rows": pred_valid_rows,
            "analysis_rows": int(N),
            "analysis_sampling_rate_hz": ANALYSIS_HZ,
            "pose_stride": POSE_STRIDE,
        },
        "alignment_rule": {
            "gt_grid": "emg2pose/timeseries/time (2 kHz)",
            "pred_grid": "same input grid, offset by left_context=1790",
            "rule": "prediction[i] corresponds to GT[row_offset + i]; verified by "
                    "exact np.array_equal on the time arrays for all records",
            "outcome_driven_lag_search": "NO",
        },
        "validity_rule": {
            "gt_row_valid": "NOT all-20-dimensions-zero (IK-failure) AND all finite",
            "pred_row_valid": "NOT all-20-dimensions-zero AND all finite",
            "block_valid": f"all {POSE_STRIDE} rows valid within the block",
            "primary_population": "GT-valid AND pred-valid blocks (full-block "
                                  "conjunction, no mixing across gaps)",
            "lead_block": "the first block of each record is excluded (GATE3_PLAN.md "
                          "§5: decoder initialisation transient at t = left_context); "
                          "all *_blocks counts below are POST-exclusion",
        },
        "files": manifest_files,
    }
    with open(os.path.join(ART, "GATE3_DATA_MANIFEST.json"), "w", encoding="utf-8") as fh:
        json.dump(data_manifest, fh, indent=2, ensure_ascii=False)

    alignment = {
        "artifact": "GATE3_ALIGNMENT_AUDIT.json",
        "plan_sha256": PLAN_SHA,
        "estimator_temporal_semantics": {
            "source": "official emg2pose/pose_modules.py BasePoseModule.forward",
            "left_context": 1790, "right_context": 0,
            "prediction_span": "EMG[left_context : T - right_context]",
            "upsampling": "interpolate(pred, n_time, mode='linear') where "
                          "n_time = T - left_context",
            "output_grid": "the 2 kHz input grid (same grid as GT joint_angles)",
            "provide_initial_pos": False,
            "rollout_freq_hz": 50,
            "num_position_steps": 500,
        },
        "per_record_timestamp_equality": "np.array_equal(GT.time[1790:], pred.time) "
                                         "asserted for every record -> exact",
        "records_checked": len(manifest_files),
        "row_offsets": sorted({m["row_offset"] for m in manifest_files}),
        "shift_applied": "NONE (beyond the official left_context trim)",
        "shift_search_performed": "NO",
        "outcome_used_for_alignment": "NO",
        "conclusion": "GT[row_offset+i] and prediction[i] share the same physical "
                      "timestamp by construction and by exact array equality.",
    }
    with open(os.path.join(ART, "GATE3_ALIGNMENT_AUDIT.json"), "w",
              encoding="utf-8") as fh:
        json.dump(alignment, fh, indent=2, ensure_ascii=False)

    pose_error = {
        "artifact": "GATE3_POSE_ERROR.json",
        "plan_sha256": PLAN_SHA,
        "units": "degrees",
        "comparison": "predicted trusted-8 pose vs GT trusted-8 pose on the frozen "
                      "analysis population",
        "n": int(N),
        "overall_rmse_deg": overall_rmse,
        "overall_mae_deg": overall_mae,
        "per_frame_trusted8_rmse_deg": qstats(per_frame_err),
        "per_dof": per_dof,
        "trusted8_names": TRUSTED8_NAMES,
        "trusted8_emg2pose_indices": TRUSTED8_SRC_IDX,
    }
    with open(os.path.join(ART, "GATE3_POSE_ERROR.json"), "w", encoding="utf-8") as fh:
        json.dump(pose_error, fh, indent=2, ensure_ascii=False)

    summary = {
        "artifact": "GATE3_PRESERVATION_SUMMARY.json",
        "gate": "PHASE 1 / GATE 3 — FORMAL UPSTREAM SUBSTITUTION BASELINE",
        "plan_sha256": PLAN_SHA,
        "question": "When emg2pose ground-truth pose is replaced by pose predicted "
                    "from the same EMG by the official emg2pose estimator, how much "
                    "of the frozen downstream DB9-head behaviour is preserved?",
        "reference_behavior": "Y_GT (oracle-route output). NOT semantic ground truth.",
        "n_analysis_samples": int(N),
        "analysis_sampling_rate_hz": ANALYSIS_HZ,
        "hard_agreement": agreement,
        "n_disagreement": int(D.sum()),
        "balanced_preservation": bal_pres,
        "balanced_preservation_classes": sufficient,
        "insufficient_support_classes": insufficient,
        "min_class_support": MIN_CLASS_SUPPORT,
        "per_class_support": support,
        "per_class_preservation": {str(c): pres[c] for c in CLASSES},
        "cohen_kappa": float(kappa),
        "p_observed": p_o, "p_expected": p_e,
        "soft_preservation": {
            "tv_distance": qstats(tv), "js_divergence": qstats(js),
            "reference_class_probability_P_PRED_at_Y_GT": qstats(ref_p),
            "predicted_class_probability_P_PRED_at_Y_PRED": qstats(own_pred_p),
            "calibration_fitted": "NO",
            "proba_source": "native sklearn LinearDiscriminantAnalysis.predict_proba "
                            "on the same frozen head object",
        },
        "temporal_preservation": {
            "gt": t_gt, "pred": t_pr,
            "transition_event_tolerance_frames": TRANSITION_TOL_FRAMES,
            "transition_event_tolerance_ms": TRANSITION_TOL_FRAMES * 1000.0 / ANALYSIS_HZ,
            "n_gt_transition_events": n_events,
            "same_destination_within_tolerance": n_dest_matched,
            "same_destination_within_tolerance_fraction":
                (n_dest_matched / n_events) if n_events else None,
            "same_destination_exact_frame": n_matched,
            "same_destination_exact_frame_fraction":
                (n_matched / n_events) if n_events else None,
        },
        "side_stratification": by_side,
        "stage_stratification": by_stage,
        "class_conditional": by_class,
        "error_to_functional_failure": {
            "definition": "D_t = 1 if Y_PRED,t != Y_GT,t else 0",
            "binning": f"{N_DECILES} deciles of per-frame trusted-8 pose RMSE, "
                       "defined from the eligible sample distribution before "
                       "downstream outcome inspection",
            "decile_curve": curve,
            "spearman_frame_pose_error_vs_disagreement_descriptive": rho_frame,
            "per_dof_descriptive_association": dof_assoc,
            "inferential_caveat": "one participant, temporally correlated frames; "
                                  "no frame-level p-values are presented and no "
                                  "population-level significance is claimed",
        },
        "firewall": {
            "GATE_CREATED": "NO", "UNKNOWN_CLASS": "NO", "ABSTENTION": "NO",
            "REJECTION": "NO", "HUMAN_LABELS_USED": "NO",
            "CALIBRATION_FITTED": "NO", "TASK_SPECIFIC_RETRAINING": "NO",
            "UPSTREAM_RETRAINING": "NO", "SMOOTHING_APPLIED": "NO",
            "CHECKPOINT_SELECTED_ON_DOWNSTREAM_PERFORMANCE": "NO",
            "ALIGNMENT_OPTIMIZED_ON_OUTCOME": "NO",
            "SAMPLE_SELECTION_ON_DOWNSTREAM_OUTPUT": "NO",
            "SEMANTIC_ACCURACY_CLAIMED": "NO",
            "HISTORICAL_0_7646_USED_FOR_DESIGN": "NO",
            "FULL_CORPUS_DOWNLOADED": "NO",
        },
        "not_claimed": [
            "gesture accuracy on emg2pose", "posture accuracy on emg2pose",
            "transfer accuracy", "cross-dataset classification accuracy",
            "semantic correctness of any class assignment",
            "cross-user generalization", "universal Common Pose validity",
            "numerical cross-source coordinate equivalence",
        ],
        "wording_note": "This experiment measures FUNCTIONAL PRESERVATION of a "
                        "frozen downstream function under upstream substitution. "
                        "It does not measure semantic correctness.",
    }
    with open(os.path.join(ART, "GATE3_PRESERVATION_SUMMARY.json"), "w",
              encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)

    import csv as _csv
    # Exact integer counts (no float rounding) — the authoritative matrix.
    with open(os.path.join(ART, "GATE3_PRESERVATION_MATRIX_COUNTS.json"), "w",
              encoding="utf-8") as fh:
        json.dump({
            "artifact": "GATE3_PRESERVATION_MATRIX_COUNTS.json",
            "plan_sha256": PLAN_SHA,
            "orientation": "rows = Y_GT, columns = Y_PRED",
            "row_labels": [f"Y_GT_{c}" for c in CLASSES],
            "column_labels": [f"Y_PRED_{c}" for c in CLASSES],
            "counts": cm.tolist(),
            "row_sums": cm.sum(1).tolist(),
            "column_sums": cm.sum(0).tolist(),
            "total": int(cm.sum()),
            "note": "raw integer counts; the CSV variants are lossy to 8 decimals",
        }, fh, indent=2, ensure_ascii=False)
    np.savetxt(os.path.join(ART, "GATE3_PRESERVATION_MATRIX_COUNTS.csv"), cm,
               fmt="%d", delimiter=",",
               header=",".join(f"Y_PRED_{c}" for c in CLASSES), comments="")
    np.savetxt(os.path.join(ART, "GATE3_PRESERVATION_MATRIX.csv"),
               cm / cm.sum(1, keepdims=True), fmt="%.12f", delimiter=",",
               header=",".join(f"Y_PRED_{c}" for c in CLASSES), comments="")

    with open(os.path.join(ART, "GATE3_PRESERVATION_BY_CLASS.csv"), "w",
              encoding="utf-8", newline="") as fh:
        cols = ["class", "support", "support_fraction", "preservation", "n_correct",
                "n_errors", "main_error_destination", "main_error_destination_count",
                "main_error_destination_fraction_of_errors", "median_pose_error_deg",
                "median_tv", "median_js", "median_ref_prob"]
        w = _csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in by_class:
            w.writerow(r)

    with open(os.path.join(ART, "GATE3_PRESERVATION_BY_SIDE.csv"), "w",
              encoding="utf-8", newline="") as fh:
        cols = ["side", "n", "n_files", "agreement", "balanced_preservation",
                "cohen_kappa", "median_tv", "median_js", "pose_mae_deg",
                "pose_rmse_deg", "switch_rate_gt", "switch_rate_pred"]
        w = _csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for s_, v in by_side.items():
            w.writerow({"side": s_, **{k: v[k] for k in cols if k != "side"}})

    with open(os.path.join(ART, "GATE3_PRESERVATION_BY_STAGE.csv"), "w",
              encoding="utf-8", newline="") as fh:
        cols = ["stage", "sides", "n", "agreement", "balanced_preservation",
                "pose_mae_deg", "dominant_gt_class", "dominant_gt_fraction",
                "dominant_pred_class", "dominant_pred_fraction", "median_tv"]
        w = _csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in by_stage:
            w.writerow(r)

    with open(os.path.join(ART, "GATE3_ERROR_PRESERVATION_CURVE.csv"), "w",
              encoding="utf-8", newline="") as fh:
        w = _csv.DictWriter(fh, fieldnames=list(curve[0].keys()))
        w.writeheader()
        for r in curve:
            w.writerow(r)

    decision = {
        "artifact": "GATE3_DECISION.json",
        "gate": "PHASE 1 / GATE 3",
        "plan_sha256": PLAN_SHA,
        "categorical_labels_emitted": "NO",
        "reason": "The plan declares no pass/fail threshold and no descriptive "
                  "categorical criterion for this gate, because no threshold "
                  "existed before the experiment. Per the plan, the result is the "
                  "observed quantitative preservation profile and the numbers are "
                  "reported without a verdict.",
        "observed_profile": {
            "n_analysis_samples": int(N),
            "hard_agreement": agreement,
            "balanced_preservation": bal_pres,
            "cohen_kappa": float(kappa),
            "median_tv": float(np.median(tv)),
            "median_js": float(np.median(js)),
            "overall_pose_rmse_deg": overall_rmse,
            "overall_pose_mae_deg": overall_mae,
            "gt_switch_rate": t_gt["switch_rate_per_sample"],
            "pred_switch_rate": t_pr["switch_rate_per_sample"],
        },
        "historical_reference": {
            "value": 0.7646,
            "status": "NOT USED FOR DESIGN — not for thresholds, alignment, "
                      "checkpoint selection, smoothing, sample selection or "
                      "pass/fail. Recorded here only as a non-comparable "
                      "prior-stage reference from a different pipeline "
                      "(4-DOF decoder, central-60% windows, different head).",
        },
        "next_allowed_step": "Design a frozen reliability/abstention gate and "
                             "evaluate preservation-versus-coverage; do not execute "
                             "until the Gate3 result is reviewed.",
    }
    with open(os.path.join(ART, "GATE3_DECISION.json"), "w", encoding="utf-8") as fh:
        json.dump(decision, fh, indent=2, ensure_ascii=False)

    with open(os.path.join(LOGS, "gate3_stdout.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(log_lines) + "\n")

    log(f"elapsed {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
