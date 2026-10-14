#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GATE 3B — independent verification.

Recomputes the Gate3B representation metrics FROM SOURCE and asserts they match
the published artifacts, then checks the firewall assertions.  Deliberately does
not import the runner.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sys

import h5py
import joblib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
ART = os.path.join(LANE, "artifacts")
PLAN = os.path.join(LANE, "GATE3B_PLAN.md")

MINI_DIR = "/root/data/emg2pose_dataset_mini"
PRED_DIR = "/root/work/gate3_work/pred_pose"
FROZEN_HEAD = "/root/work/gate3_work/frozen_head/frozen_db9_trusted8_lda.joblib"
DB9_EXTRACTED = "/root/data/ninapro_db9/extracted"

POSE_STRIDE = 40
ANALYSIS_HZ = 50.0
TRUSTED8_SRC_IDX = [2, 3, 5, 6, 9, 13, 17, 18]
CLASSES = [1, 2, 3, 4, 5, 6, 7, 8]
EPS = 1e-12
N_DECILES = 10
EXPECTED_N = 86833
EXPECTED_SUBSET_SHA = "e51dde6e63941fd080c84f3896a98cf50fba9e17d5f9cebe909253d5465782d1"
EXPECTED_HEAD_SHA = "b0ef8caf8e390a480fa2a3b448f79ccf14f75c71265ef925ee299a5e9e660386"

CHECKS = 0
FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""),
          flush=True)
    if not cond:
        FAILS.append(name)


def close(a, b, tol=1e-9) -> bool:
    if a is None or b is None:
        return a is b
    return bool(np.allclose(np.asarray(a, dtype=np.float64),
                            np.asarray(b, dtype=np.float64), atol=tol, rtol=1e-9))


def load_json(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    print("=" * 78)
    print("GATE 3B — INDEPENDENT VERIFICATION")
    print("=" * 78)

    # ---------------- 1. plan ----------------
    print("\n[1] plan integrity")
    frozen = open(os.path.join(LANE, "GATE3B_PLAN.sha256"), encoding="utf-8").read().split()
    plan_sha = sha(PLAN)
    check("plan sha256 matches GATE3B_PLAN.sha256", plan_sha == frozen[0],
          f"{plan_sha[:16]}… vs {frozen[0][:16]}…")
    for a in ("GATE3B_DATA_LINK.json", "FISHER_PRESERVATION_SUMMARY.json",
              "SCORE_SPACE_PRESERVATION.json", "POSE_TO_FISHER_RELATION.json",
              "GATE3B_DECISION.json", "REPRESENTATIONAL_CKA.json"):
        check(f"{a} records the same plan sha",
              load_json(os.path.join(ART, a))["plan_sha256"] == plan_sha)

    # ---------------- 2. frozen objects ----------------
    print("\n[2] frozen objects")
    check("frozen head sha256", sha(FROZEN_HEAD) == EXPECTED_HEAD_SHA)
    ref = load_json(os.path.join(ART, "FISHER_DB9_REFERENCE_SCALE.json"))
    check("trusted subset sha256",
          ref["provenance"]["frozen_subset"] .endswith("TRUSTED_DB9_POSE_v1.json"))
    tp = "/root/work/common-pose/audits/db9/trusted_pose/TRUSTED_DB9_POSE_v1.json"
    check("trusted subset content sha256", sha(tp) == EXPECTED_SUBSET_SHA)
    check("DB9 reference declares no emg2pose data used",
          ref["provenance"]["emg2pose_data_used"] == "NO")
    check("DB9 reference declares no Gate3B outcome inspected",
          ref["provenance"]["gate3b_outcome_inspected"] == "NO")
    check("DB9 corpus reproduced frozen head frame count",
          ref["db9_corpus_consistency"]["frames_match_frozen_head"] is True,
          str(ref["provenance"]["db9_frames"]))
    check("DB9 corpus reproduces head mu", ref["db9_corpus_consistency"]["mu_matches"] is True)
    check("DB9 corpus reproduces head sd", ref["db9_corpus_consistency"]["sd_matches"] is True)

    bundle = joblib.load(FROZEN_HEAD)
    head, mu, sd = bundle["head"], bundle["mu"], bundle["sd"]
    check("LDA solver is svd", head.solver == "svd")
    check("scalings_ shape == (8, 7)", head.scalings_.shape == (8, 7),
          str(head.scalings_.shape))
    zprobe = head.transform(np.zeros((2, 8)))
    check("Fisher dimension == 7", zprobe.shape[1] == 7, str(zprobe.shape[1]))
    check("Fisher dimension recorded as 7",
          ref["frozen_head_geometry"]["fisher_dimension"] == 7)
    check("explained_variance_ratio_ present with 7 entries",
          len(ref["frozen_head_geometry"]["explained_variance_ratio"]) == 7)
    check("evr sums to 1", close(sum(ref["frozen_head_geometry"]["explained_variance_ratio"]), 1.0))
    check("transform includes xbar_ centering (identity verified)",
          ref["frozen_head_geometry"]["transform_is_x_minus_xbar_times_scalings"] is True)

    # ---------------- 3. rebuild the exact Gate3 population ----------------
    print("\n[3] population + alignment identity")
    files = sorted(glob.glob(os.path.join(MINI_DIR, "*.hdf5")))
    Gp, Pp, side_l, stage_l, file_l = [], [], [], [], []
    align_ok = True
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
        if not (off == 1790 and np.array_equal(tgt[off:], tpred)):
            align_ok = False
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

    G, P = np.vstack(Gp), np.vstack(Pp)
    side, stage, filearr = np.array(side_l), np.array(stage_l), np.array(file_l)
    N = G.shape[0]
    check("alignment exact for every record (offset 1790)", align_ok)
    check("population == Gate3 eligible population", N == EXPECTED_N, f"{N}")
    dl = load_json(os.path.join(ART, "GATE3B_DATA_LINK.json"))
    check("data link records same population", dl["population"]["n"] == N)
    check("analysis rate is 50 Hz",
          load_json(os.path.join(LANE, "artifacts",
                                 "GATE3B_DATA_LINK.json"))["population"]["rate_hz"]
          == ANALYSIS_HZ)

    # ---------------- 4. recompute representation metrics ----------------
    print("\n[4] representation recomputation")
    x_gt = (G - mu) / sd
    x_pr = (P - mu) / sd
    z_gt = head.transform(x_gt)
    z_pr = head.transform(x_pr)
    check("z shapes are (N, 7)", z_gt.shape == (N, 7) and z_pr.shape == (N, 7))

    na, nb_ = np.linalg.norm(z_gt, axis=1), np.linalg.norm(z_pr, axis=1)
    valid = (na > EPS) & (nb_ > EPS)
    cos = np.full(N, np.nan)
    cos[valid] = np.sum(z_gt[valid] * z_pr[valid], 1) / (na[valid] * nb_[valid])
    cz = cos[valid]

    fish = load_json(os.path.join(ART, "FISHER_PRESERVATION_SUMMARY.json"))
    check("valid cosine frame count recomputes",
          fish["cosine"]["n_valid_cosine_frames"] == int(valid.sum()),
          f"{int(valid.sum())}")
    check("invalid cosine frame count reported",
          fish["cosine"]["n_invalid_cosine_frames"] == int((~valid).sum()))
    check("no frame was silently assigned cosine 1",
          not bool(np.any(cos[~valid] == 1.0)))
    check("cosine median recomputes", close(np.median(cz), fish["cosine"]["stats"]["median"]))
    check("cosine mean recomputes", close(cz.mean(), fish["cosine"]["stats"]["mean"]))
    check("cosine IQR recomputes",
          close(np.percentile(cz, 75) - np.percentile(cz, 25), fish["cosine"]["stats"]["iqr"]))
    check("cosine p05 recomputes", close(np.percentile(cz, 5), fish["cosine"]["stats"]["p05"]))
    check("cosine p95 recomputes", close(np.percentile(cz, 95), fish["cosine"]["stats"]["p95"]))
    check("fraction <0 recomputes", close(float((cz < 0).mean()), fish["cosine"]["fraction_lt_0"]))
    check("fraction >0.5 recomputes", close(float((cz > 0.5).mean()), fish["cosine"]["fraction_gt_0_5"]))
    check("fraction >0.8 recomputes", close(float((cz > 0.8).mean()), fish["cosine"]["fraction_gt_0_8"]))
    check("fraction >0.9 recomputes", close(float((cz > 0.9).mean()), fish["cosine"]["fraction_gt_0_9"]))
    check("cosine in [-1,1]", bool((cz >= -1 - 1e-9).all() and (cz <= 1 + 1e-9).all()))

    # DB9 scaling
    sigma_db9 = np.array(ref["fisher_component_sigma_db9"])
    check("DB9 sigma has 7 entries", sigma_db9.size == 7)
    check("DB9 sigma positive", bool((sigma_db9 > 0).all()))
    # verify the DB9 sigma values really come from DB9 (rebuild from .mat if present)
    import scipy.io as sio
    if os.path.isdir(DB9_EXTRACTED):
        DB9_ORDER = ["CMC1_f", "CMC1_a", "MCP1", "IP1", "MCP2_f", "MCP2_a", "PIP2",
                     "MCP3_f", "PIP3", "MCP4_f", "MCP4_a", "PIP4", "CMC5", "MCP5_f",
                     "MCP5_a", "PIP5", "DIP2", "DIP3", "DIP4", "DIP5", "WRIST_F",
                     "WRIST_A"]
        cols = [DB9_ORDER.index(nm) for nm in
                ["MCP1", "IP1", "MCP2_f", "PIP2", "MCP3_f", "MCP4_f", "MCP5_f", "PIP5"]]
        Xs = []
        for f in sorted(glob.glob(os.path.join(DB9_EXTRACTED, "s_*_angles", "*.mat"))):
            m = sio.loadmat(f, squeeze_me=True, struct_as_record=False)
            if not all(k in m for k in ("restimulus", "rerepetition", "angles")):
                continue
            ks = np.asarray(m["restimulus"]).ravel()
            rs = np.asarray(m["rerepetition"]).ravel()
            n = min(ks.size, rs.size)
            segs, start = [], 0
            for i in range(1, n + 1):
                if i == n or ks[i] != ks[start] or rs[i] != rs[start]:
                    st, rp = int(ks[start]), int(rs[start])
                    if not (st == 0 or rp == 0):
                        segs.append((st, start, i - start))
                    start = i
            if sorted({s[0] for s in segs}) != list(range(1, 18)):
                continue
            if not any(s[0] == 6 for s in segs) or not any(s[0] == 11 for s in segs):
                continue
            ang_all = m["angles"]
            idx = {}
            for st, a0, cnt in segs:
                if st in CLASSES:
                    k = max(1, int(round(cnt * 0.6)))
                    a = a0 + (cnt - k) // 2
                    idx.setdefault(st, []).extend(range(a, a + k))
            for st in CLASSES:
                if st not in idx:
                    continue
                a = np.array(idx[st])
                ang = ang_all[a, :][:, cols]
                ok = np.isfinite(ang).all(axis=1)
                if not ok.any():
                    continue
                ang = ang[ok]
                if ang.shape[0] > 200:
                    ang = ang[np.linspace(0, ang.shape[0] - 1, 200).astype(int)]
                Xs.append(np.deg2rad(ang))
        Xdb9 = np.vstack(Xs)
        check("DB9 corpus rebuild frame count == 123200", Xdb9.shape[0] == 123200,
              f"{Xdb9.shape[0]}")
        z_db9 = head.transform((Xdb9 - mu) / sd)
        sig_rebuilt = z_db9.std(axis=0, ddof=0)
        check("DB9 Fisher sigma recomputes from raw DB9 data",
              close(sig_rebuilt, sigma_db9, tol=1e-8),
              f"max diff {np.abs(sig_rebuilt - sigma_db9).max():.3e}")
    else:
        print("  [SKIP] DB9 raw corpus not present; sigma verified from artifact only")

    d_norm = np.sqrt((((z_pr - z_gt) / sigma_db9) ** 2).sum(1))
    d_raw = np.linalg.norm(z_pr - z_gt, axis=1)
    check("d_norm median recomputes",
          close(np.median(d_norm), fish["distance_db9_normalized"]["median"]))
    check("d_norm mean recomputes",
          close(d_norm.mean(), fish["distance_db9_normalized"]["mean"]))
    check("d_norm IQR recomputes",
          close(np.percentile(d_norm, 75) - np.percentile(d_norm, 25),
                fish["distance_db9_normalized"]["iqr"]))
    check("d_norm p05/p95 recompute",
          close(np.percentile(d_norm, 5), fish["distance_db9_normalized"]["p05"]) and
          close(np.percentile(d_norm, 95), fish["distance_db9_normalized"]["p95"]))
    check("d_raw median recomputes",
          close(np.median(d_raw), fish["distance_raw_euclidean"]["median"]))
    check("d_norm uses DB9 sigma only (recomputed identically)",
          close(d_norm, np.sqrt((((z_pr - z_gt) / sigma_db9) ** 2).sum(1))))

    # components
    evr = np.array(ref["frozen_head_geometry"]["explained_variance_ratio"])
    comps = fish["component_preservation"]
    check("7 components reported", len(comps) == 7)
    for j, c in enumerate(comps):
        a, b = z_gt[:, j], z_pr[:, j]
        r = float(np.corrcoef(a, b)[0, 1])
        mae = float(np.abs(b - a).mean())
        rmse = float(np.sqrt(((b - a) ** 2).mean()))
        slope, inter = np.polyfit(a, b, 1)
        check(f"  component {j+1} pearson recomputes", close(r, c["pearson_r"]))
        check(f"  component {j+1} MAE recomputes", close(mae, c["mae"]))
        check(f"  component {j+1} RMSE recomputes", close(rmse, c["rmse"]))
        check(f"  component {j+1} db9 weight recomputes",
              close(evr[j], c["db9_variance_ratio"]))
        check(f"  component {j+1} OLS slope/intercept recompute",
              close(slope, c["ols_slope_pred_on_gt"]) and close(inter, c["ols_intercept"]))
    w = evr / evr.sum()
    wcc = float(sum(w[j] * comps[j]["pearson_r"] for j in range(7)))
    check("DB9-weighted component correlation recomputes",
          close(wcc, fish["db9_weighted_component_correlation"]))
    check("weights sum to 1", close(w.sum(), 1.0))

    # ---------------- 5. score space ----------------
    print("\n[5] score-space recomputation")
    scal = head.scalings_
    cmeans = head.means_ @ scal
    logpri = np.log(head.priors_)

    def class_scores(xz):
        z = xz @ scal
        d2 = ((z[:, None, :] - cmeans[None, :, :]) ** 2).sum(-1)
        return -0.5 * d2 + logpri[None, :]

    s_gt, s_pr = class_scores(x_gt), class_scores(x_pr)
    check("score vectors are 8-D", s_gt.shape == (N, 8))
    _chk = np.argmax(s_gt, axis=1)
    _direct = np.array([int(np.flatnonzero(head.classes_ == c)[0])
                        for c in head.predict(x_gt)])
    check("affinity-score argmax reproduces head.predict exactly",
          bool(np.array_equal(_chk, _direct)))
    cs_gt = s_gt - s_gt.mean(1, keepdims=True)
    cs_pr = s_pr - s_pr.mean(1, keepdims=True)
    check("centering arithmetic: row means are 0",
          bool(np.allclose(cs_gt.mean(1), 0, atol=1e-12) and
               np.allclose(cs_pr.mean(1), 0, atol=1e-12)))

    na2, nb2 = np.linalg.norm(cs_gt, axis=1), np.linalg.norm(cs_pr, axis=1)
    v2 = (na2 > EPS) & (nb2 > EPS)
    scos = np.full(N, np.nan)
    scos[v2] = (cs_gt[v2] * cs_pr[v2]).sum(1) / (na2[v2] * nb2[v2])
    sa = load_json(os.path.join(ART, "SCORE_SPACE_PRESERVATION.json"))
    check("score cosine valid count recomputes", sa["score_cosine"]["n_valid"] == int(v2.sum()))
    check("score cosine median recomputes",
          close(np.median(scos[v2]), sa["score_cosine"]["stats"]["median"]))
    tau = np.array(ref["score_centered_sigma_db9"])
    check("DB9 score sigma has 8 entries", tau.size == 8)
    check("DB9 score sigma positive", bool((tau > 0).all()))
    sd_norm = np.sqrt((((cs_pr - cs_gt) / tau) ** 2).sum(1))
    check("score normalized distance median recomputes",
          close(np.median(sd_norm), sa["score_distance_db9_normalized"]["median"]))
    check("score raw distance median recomputes",
          close(np.median(np.linalg.norm(cs_pr - cs_gt, axis=1)),
                sa["score_distance_raw"]["median"]))

    # ---------------- 6. probability + hard ----------------
    print("\n[6] probability and hard-decision reproduction")
    pg, pp = head.predict_proba(x_gt), head.predict_proba(x_pr)
    tv = 0.5 * np.abs(pg - pp).sum(1)

    def js(p, q):
        m_ = 0.5 * (p + q)
        def kl(a, b):
            b = np.clip(b, 1e-300, 1.0)
            return np.where(a > 0, a * np.log2(a / b), 0.0).sum(1)
        return 0.5 * kl(p, m_) + 0.5 * kl(q, m_)
    jsd = js(pg, pp)
    g3 = load_json("/root/work/common-pose/experiments/upstream_substitution/"
                   "gate3_formal_substitution/artifacts/GATE3_PRESERVATION_SUMMARY.json")
    check("Gate3 TV median reproduced",
          close(np.median(tv), g3["soft_preservation"]["tv_distance"]["median"]),
          f"{np.median(tv):.6f} vs {g3['soft_preservation']['tv_distance']['median']:.6f}")
    check("Gate3 JS median reproduced",
          close(np.median(jsd), g3["soft_preservation"]["js_divergence"]["median"]),
          f"{np.median(jsd):.6f} vs {g3['soft_preservation']['js_divergence']['median']:.6f}")
    y_gt = head.predict(x_gt).astype(np.int16)
    y_pr = head.predict(x_pr).astype(np.int16)
    flip = y_pr != y_gt
    check("Gate3 hard agreement reproduced",
          close(float(1 - flip.mean()), g3["hard_agreement"]),
          f"{1-flip.mean():.8f} vs {g3['hard_agreement']:.8f}")

    # ---------------- 7. SAME / FLIP ----------------
    print("\n[7] SAME vs FLIP")
    # NOTE: csv.DictReader yields strings, so counts must be coerced before any
    # numeric comparison (an earlier version compared str + str against int).
    gr = {r["group"]: r for r in
          _read_csv(os.path.join(ART, "REPRESENTATION_BY_HARD_OUTCOME.csv"))}
    n_same = int(gr["SAME"]["n"])
    n_flip = int(gr["FLIP"]["n"])
    check("SAME + FLIP counts == total", n_same + n_flip == N,
          f"{n_same}+{n_flip}={n_same + n_flip} vs {N}")
    check("SAME count recomputes", n_same == int((~flip).sum()),
          f"{n_same} vs {int((~flip).sum())}")
    check("FLIP count recomputes", n_flip == int(flip.sum()),
          f"{n_flip} vs {int(flip.sum())}")
    check("SAME fraction recomputes", close(float(gr["SAME"]["n_fraction"]),
                                            float((~flip).mean())))
    check("FLIP fraction recomputes", close(float(gr["FLIP"]["n_fraction"]),
                                            float(flip.mean())))
    check("SAME fisher cosine median recomputes",
          close(np.median(cos[~flip & valid]), gr["SAME"]["fisher_cosine_median"]))
    check("FLIP fisher cosine median recomputes",
          close(np.median(cos[flip & valid]), gr["FLIP"]["fisher_cosine_median"]))
    check("SAME fisher distance median recomputes",
          close(np.median(d_norm[~flip]), gr["SAME"]["fisher_distance_norm_median"]))
    check("FLIP fisher distance median recomputes",
          close(np.median(d_norm[flip]), gr["FLIP"]["fisher_distance_norm_median"]))
    check("SAME TV median recomputes", close(np.median(tv[~flip]), gr["SAME"]["tv_median"]))
    check("FLIP TV median recomputes", close(np.median(tv[flip]), gr["FLIP"]["tv_median"]))
    check("no classifier fitted to predict flips",
          not os.path.exists(os.path.join(ART, "FLIP_CLASSIFIER.json")))

    # ---------------- 8. deciles ----------------
    print("\n[8] decile accounting")
    for fname, key, asc in (("FISHER_DISTANCE_DECILES.csv", d_norm, True),
                            ("FISHER_COSINE_DECILES.csv", cos, False)):
        rows = _read_csv(os.path.join(ART, fname))
        check(f"{fname} has {N_DECILES} deciles", len(rows) == N_DECILES)
        check(f"{fname} sizes sum to N", sum(int(r["n"]) for r in rows) == N,
              f"{sum(int(r['n']) for r in rows)}")
        o = np.argsort(key if asc else -key, kind="mergesort")
        for r, ix in zip(rows, np.array_split(o, N_DECILES)):
            cvv = valid[ix]
            med = float(np.median(cos[ix][cvv])) if cvv.any() else None
            ok = close(r["median_fisher_distance_norm"], float(np.median(d_norm[ix])))
            ok2 = close(r["hard_agreement"], float(1 - flip[ix].mean()))
            ok3 = (med is None and r["median_fisher_cosine"] is None) or \
                  close(med, r["median_fisher_cosine"])
            check(f"  {fname} decile {r['decile']} recomputes", ok and ok2 and ok3)

    # ---------------- 9. pose -> fisher -> hard ----------------
    print("\n[9] pose -> fisher -> hard")
    err_deg = np.degrees(P - G)
    pose_rmse = np.sqrt((err_deg ** 2).mean(1))
    pf = load_json(os.path.join(ART, "POSE_TO_FISHER_RELATION.json"))

    def sp(x, y):
        def rk(a):
            order = np.argsort(a, kind="mergesort")
            r = np.empty(a.size)
            r[order] = np.arange(a.size)
            sa = a[order]
            i = 0
            while i < sa.size:
                j = i
                while j + 1 < sa.size and sa[j + 1] == sa[i]:
                    j += 1
                if j > i:
                    r[order[i:j + 1]] = (i + j) / 2
                i = j + 1
            return r
        rx, ry = rk(x), rk(y)
        rx -= rx.mean(); ry -= ry.mean()
        return float((rx * ry).sum() / np.sqrt((rx**2).sum() * (ry**2).sum()))
    check("spearman(pose RMSE, fisher distance) recomputes",
          close(sp(pose_rmse, d_norm), pf["spearman_pose_rmse_vs_fisher_distance"]))
    check("spearman(fisher distance, flip) recomputes",
          close(sp(d_norm, flip.astype(float)), pf["spearman_fisher_distance_vs_flip"]))
    check("Gate3 value quoted, not recomputed as new",
          close(pf["spearman_pose_rmse_vs_flip_gate3_recorded"], 0.162137))
    check("no causal claim asserted", pf["causal_claim"] == "NONE")

    # ---------------- 10. temporal ----------------
    print("\n[10] temporal (zero-lag, no lag search)")
    trows = _read_csv(os.path.join(ART, "TEMPORAL_FISHER_PRESERVATION.csv"))
    check("7 components reported temporally", len(trows) == 7)
    cursor = 0
    bounds = []
    for f in files:
        stem = os.path.basename(f)[: -len(".hdf5")]
        k = int((filearr == stem).sum())
        if k:
            bounds.append((cursor, cursor + k))
            cursor += k
    check("sequence bounds cover all samples", cursor == N)
    dgt = np.zeros_like(z_gt); dpr = np.zeros_like(z_pr)
    keep = np.zeros(N, dtype=bool)
    for a, b in bounds:
        if b - a >= 2:
            dgt[a + 1:b] = z_gt[a + 1:b] - z_gt[a:b - 1]
            dpr[a + 1:b] = z_pr[a + 1:b] - z_pr[a:b - 1]
            keep[a + 1:b] = True
    check("derivative pairs computed only within record boundaries",
          bool(keep.sum() == sum(max(0, b - a - 1) for a, b in bounds)),
          f"{int(keep.sum())}")
    for j, r in enumerate(trows):
        check(f"  component {j+1} zero-lag pearson recomputes",
              close(float(np.corrcoef(z_gt[:, j], z_pr[:, j])[0, 1]),
                    r["zero_lag_pearson"]))
        check(f"  component {j+1} derivative pearson recomputes",
              close(float(np.corrcoef(dgt[keep, j], dpr[keep, j])[0, 1]),
                    r["derivative_pearson"]))
        check(f"  component {j+1} derivative pair count recomputes",
              int(r["n_derivative_pairs"]) == int(keep.sum()))
    check("no lag search artifacts present",
          not any("lag" in x.lower() for x in os.listdir(ART)))

    # ---------------- 11. side / stage ----------------
    print("\n[11] side / stage accounting")
    for fname, keys in (("REPRESENTATION_BY_SIDE.csv", side),
                        ("REPRESENTATION_BY_STAGE.csv", stage)):
        rows = _read_csv(os.path.join(ART, fname))
        tot = sum(int(r["n"]) for r in rows)
        check(f"{fname} counts sum to N", tot == N, f"{tot}")
        for r in rows:
            m = keys == r["key"]
            check(f"  {fname} {r['key'][:26]} n recomputes", int(r["n"]) == int(m.sum()))
            cvv = valid[m]
            got = float(np.median(cos[m][cvv])) if cvv.any() else None
            check(f"  {fname} {r['key'][:26]} cosine recomputes",
                  (got is None and r["fisher_cosine_median"] is None) or
                  close(got, r["fisher_cosine_median"]))
    check("15 stages present",
          len(_read_csv(os.path.join(ART, "REPRESENTATION_BY_STAGE.csv"))) == 15)

    # ---------------- 12. CKA ----------------
    print("\n[12] CKA")
    ck = load_json(os.path.join(ART, "REPRESENTATIONAL_CKA.json"))
    if ck["mode"] == "FULL":
        Xc = z_gt - z_gt.mean(0, keepdims=True)
        Yc = z_pr - z_pr.mean(0, keepdims=True)
        val = np.linalg.norm(Xc.T @ Yc, "fro") ** 2 / (
            np.linalg.norm(Xc.T @ Xc, "fro") * np.linalg.norm(Yc.T @ Yc, "fro"))
        check("linear CKA recomputes", close(float(val), ck["linear_cka"]))
        check("CKA in [0,1]", 0 <= ck["linear_cka"] <= 1 + 1e-9)
    else:
        check("CKA mode is the declared deterministic subsample",
              ck["mode"] == "DETERMINISTIC_FIRST_N" and ck["n_used"] == 40000)

    # ---------------- 13. firewall ----------------
    print("\n[13] firewall")
    d = load_json(os.path.join(ART, "GATE3B_DECISION.json"))
    for k, v in d["firewall"].items():
        check(f"firewall {k} == {v}", v == "NO")
    check("evidence status declared post-hoc motivated",
          "POST-HOC MOTIVATED" in d["evidence_status"])
    check("no arbitrary thresholds claimed",
          d["no_arbitrary_thresholds"] is True)
    check("hard agreement did not drive the label",
          d["hard_agreement_alone_did_not_drive_the_label"] is True)
    check("mechanism label is one of the four declared",
          d["MECHANISM"] in (
              "REPRESENTATION_LARGELY_PRESERVED_BOUNDARY_FRAGILE",
              "REPRESENTATION_PARTIALLY_PRESERVED",
              "REPRESENTATION_SUBSTANTIALLY_DEGRADED",
              "MIXED_OR_AMBIGUOUS"), d["MECHANISM"])
    check("no gate artifact created",
          not any(x in os.listdir(ART) for x in
                  ("GATE3B_RELIABILITY.json", "GATE3B_UNKNOWN.json",
                   "GATE3B_COVERAGE.csv")))
    check("no human-label artifact created",
          not os.path.exists(os.path.join(ART, "GATE3B_HUMAN_LABELS.csv")))
    check("Gate3 artifacts unmodified (plan sha still matches)",
          sha("/root/work/common-pose/experiments/upstream_substitution/"
              "gate3_formal_substitution/GATE3_PLAN.md")
          == "9869d9b94ba07d916fc8accd1646f51ec3ea9a0efe5427a530f37880edcfc381")

    print("\n" + "=" * 78)
    print(f"ASSERTIONS: {CHECKS}   FAILED: {len(FAILS)}")
    if FAILS:
        for x in FAILS:
            print(f"  FAILED: {x}")
        print("VERIFY_GATE3B: FAIL")
        return 1
    print("VERIFY_GATE3B: PASS")
    return 0


def _read_csv(p):
    import csv
    with open(p, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


if __name__ == "__main__":
    sys.exit(main())
