#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GATE 3 — independent verification.

Recomputes the Gate3 metrics FROM SOURCE (HDF5 + prediction .npz + serialized
frozen head) and asserts they match the published artifacts, then checks the
firewall assertions.  It deliberately does NOT import the runner, so a bug in the
runner cannot propagate into its own verification.

Run:
  <env>/bin/python -X utf8 verify_gate3.py
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

LANE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(LANE, "artifacts")
MODELS = os.path.join(LANE, "models")
PLAN = os.path.join(LANE, "GATE3_PLAN.md")

MINI_DIR = "/root/data/emg2pose_dataset_mini"
PRED_DIR = "/root/work/gate3_work/pred_pose"
HEAD_JOBLIB = "/root/work/gate3_work/frozen_head/frozen_db9_trusted8_lda.joblib"

POSE_STRIDE = 40
ANALYSIS_HZ = 50.0
TRUSTED8_SRC_IDX = [2, 3, 5, 6, 9, 13, 17, 18]
CLASSES = [1, 2, 3, 4, 5, 6, 7, 8]
MIN_CLASS_SUPPORT = 30
TRANSITION_TOL_FRAMES = 1

EXPECTED_SUBSET_SHA = "e51dde6e63941fd080c84f3896a98cf50fba9e17d5f9cebe909253d5465782d1"
EXPECTED_CKPT_SHA = "748b1d1ef0ce1985f6fc07225d97eebfb370243429af803b4997d28ecce2424e"

CHECKS = 0
FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f"  -- {detail}" if detail else ""), flush=True)
    if not cond:
        FAILS.append(name)


def close(a, b, tol=1e-9) -> bool:
    return bool(np.allclose(np.asarray(a, dtype=np.float64),
                            np.asarray(b, dtype=np.float64), atol=tol, rtol=1e-9))


def load_json(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    print("=" * 78)
    print("GATE 3 — INDEPENDENT VERIFICATION")
    print("=" * 78)

    # ---------------- 1. plan hash ----------------
    print("\n[1] plan integrity")
    frozen = open(os.path.join(LANE, "GATE3_PLAN.sha256"), encoding="utf-8").read().split()
    plan_sha = hashlib.sha256(open(PLAN, "rb").read()).hexdigest()
    check("plan sha256 matches GATE3_PLAN.sha256", plan_sha == frozen[0],
          f"{plan_sha[:16]}… vs {frozen[0][:16]}…")
    for a in ("GATE3_DATA_MANIFEST.json", "GATE3_ALIGNMENT_AUDIT.json",
              "GATE3_POSE_ERROR.json", "GATE3_PRESERVATION_SUMMARY.json",
              "GATE3_DECISION.json"):
        check(f"{a} records the same plan sha", load_json(os.path.join(ART, a))["plan_sha256"] == plan_sha)

    # ---------------- 2. frozen subsets / head ----------------
    print("\n[2] frozen objects")
    bundle = joblib.load(HEAD_JOBLIB)
    head, mu, sd, fh_meta = bundle["head"], bundle["mu"], bundle["sd"], bundle["meta"]
    check("frozen subset sha256",
          fh_meta["protocol"]["frozen_subset_sha256"] == EXPECTED_SUBSET_SHA)
    check("head DB9 columns == [2,3,4,6,7,9,13,15]",
          fh_meta["protocol"]["db9_columns"] == [2, 3, 4, 6, 7, 9, 13, 15])
    check("head class set == 1..8", list(head.classes_) == CLASSES)
    check("head has predict_proba", hasattr(head, "predict_proba"))
    check("head replication EXACT",
          fh_meta["replication_check"]["exact"] is True,
          f"{fh_meta['replication_check']['n_quantities_checked']} quantities")
    rc = fh_meta["replication_check"]
    for k, v in rc["scalar_quantities"].items():
        check(f"  replication {k} == frozen record", v["match"] is True,
              f"{v['reconstructed']} vs {v['frozen']}")
    for c, v in rc["per_class_recall"].items():
        check(f"  replication recall class {c}", v["match"] is True,
              f"{v['reconstructed']} vs {v['frozen']}")

    # ---------------- 3. mapping ----------------
    print("\n[3] trusted-8 mapping")
    pose_err = load_json(os.path.join(ART, "GATE3_POSE_ERROR.json"))
    check("trusted-8 emg2pose indices == [2,3,5,6,9,13,17,18]",
          pose_err["trusted8_emg2pose_indices"] == TRUSTED8_SRC_IDX)
    check("8 trusted DOF names present", len(pose_err["per_dof"]) == 8)

    # ---------------- 4. recompute from source ----------------
    print("\n[4] recomputation from source (independent of the runner)")
    files = sorted(glob.glob(os.path.join(MINI_DIR, "*.hdf5")))
    dm = load_json(os.path.join(ART, "GATE3_DATA_MANIFEST.json"))
    check("record count matches manifest", len(files) == dm["n_files"],
          f"{len(files)} vs {dm['n_files']}")

    G_parts, P_parts, n_gt_valid, n_pr_valid = [], [], 0, 0
    ts_equal_all = True
    shapes_ok = True
    stored = 0
    aligned = 0

    for f in files:
        stem = os.path.basename(f)[: -len(".hdf5")]
        with h5py.File(f, "r") as h:
            g = h["emg2pose"]
            ts = g["timeseries"]
            ja = ts["joint_angles"][:]
            tgt = ts["time"][:]
            side = str(g.attrs["side"])
            stage = str(g.attrs["stage"])
        with np.load(os.path.join(PRED_DIR, f"{stem}_pred.npz")) as z:
            ang = z["angles"]
            tpred = z["time"]
            off = int(z["row_offset"])
        T = ja.shape[0]
        stored += T
        if not np.array_equal(tgt[off:], tpred):
            ts_equal_all = False
        if ang.shape != (T - off, 20):
            shapes_ok = False
            continue
        gt_w, pr_w = ja[off:], ang
        n = gt_w.shape[0]
        aligned += n
        gv = (~np.all(np.isclose(gt_w, 0.0), axis=1)) & np.isfinite(gt_w).all(axis=1)
        pv = (~np.all(np.isclose(pr_w, 0.0), axis=1)) & np.isfinite(pr_w).all(axis=1)
        n_gt_valid += int(gv.sum())
        n_pr_valid += int(pv.sum())
        nb = n // POSE_STRIDE
        u = nb * POSE_STRIDE
        gb = gt_w[:u].reshape(nb, POSE_STRIDE, 20).mean(1)[:, TRUSTED8_SRC_IDX]
        pb = pr_w[:u].reshape(nb, POSE_STRIDE, 20).mean(1)[:, TRUSTED8_SRC_IDX]
        gok = gv[:u].reshape(nb, POSE_STRIDE).all(1)
        pok = pv[:u].reshape(nb, POSE_STRIDE).all(1)
        # runner's lead-block rule
        if nb:
            gok[0] = False
            pok[0] = False
        m = gok & pok
        if m.any():
            G_parts.append(gb[m])
            P_parts.append(pb[m])

    check("GT/pred timestamp grids exactly equal for every record", ts_equal_all)
    check("GT/pred shapes consistent for every record", shapes_ok)
    check("stored rows match manifest", stored == dm["counts"]["stored_rows"],
          f"{stored} vs {dm['counts']['stored_rows']}")
    check("GT-valid rows match manifest", n_gt_valid == dm["counts"]["gt_valid_rows"],
          f"{n_gt_valid} vs {dm['counts']['gt_valid_rows']}")
    check("prediction-valid rows match manifest",
          n_pr_valid == dm["counts"]["pred_valid_rows"],
          f"{n_pr_valid} vs {dm['counts']['pred_valid_rows']}")
    check("aligned rows match manifest", aligned == dm["counts"]["aligned_rows"])

    G = np.vstack(G_parts)
    P = np.vstack(P_parts)
    N = G.shape[0]
    check("analysis rows == sum of per-file eligible blocks",
          N == sum(m["both_valid_blocks"] for m in dm["files"]),
          f"{N}")
    check("analysis sampling rate is 50 Hz",
          load_json(os.path.join(ART, "GATE3_PRESERVATION_SUMMARY.json"))
          ["analysis_sampling_rate_hz"] == ANALYSIS_HZ)

    y_gt = head.predict((G - mu) / sd).astype(np.int16)
    y_pr = head.predict((P - mu) / sd).astype(np.int16)
    proba_gt = head.predict_proba((G - mu) / sd)
    proba_pr = head.predict_proba((P - mu) / sd)
    cls_list = [int(c) for c in head.classes_]

    summary = load_json(os.path.join(ART, "GATE3_PRESERVATION_SUMMARY.json"))
    check("n_analysis_samples matches", summary["n_analysis_samples"] == N,
          f"{N} vs {summary['n_analysis_samples']}")

    agreement = float((y_pr == y_gt).mean())
    check("hard agreement recomputes",
          close(agreement, summary["hard_agreement"]),
          f"{agreement:.8f} vs {summary['hard_agreement']:.8f}")
    check("disagreement count recomputes",
          int((y_pr != y_gt).sum()) == summary["n_disagreement"])

    # occupancy / class support sums
    support = {c: int((y_gt == c).sum()) for c in CLASSES}
    check("class supports sum to N", sum(support.values()) == N)
    check("class supports recompute", support == {int(k): v for k, v in
                                                  summary["per_class_support"].items()})
    occ = np.array([support[c] for c in CLASSES]) / N
    check("Y_GT occupancy sums to 1", abs(occ.sum() - 1.0) < 1e-12, f"{occ.sum()}")

    pres = {}
    for c in CLASSES:
        m = y_gt == c
        pres[c] = float((y_pr[m] == c).mean()) if m.any() else None
    suf = [c for c in CLASSES if support[c] >= MIN_CLASS_SUPPORT]
    bal = float(np.mean([pres[c] for c in suf])) if suf else None
    check("balanced preservation recomputes",
          close(bal, summary["balanced_preservation"]),
          f"{bal:.8f} vs {summary['balanced_preservation']:.8f}")
    check("sufficient class list recomputes", suf == summary["balanced_preservation_classes"])
    for c in CLASSES:
        check(f"  per-class preservation class {c} recomputes",
              close(pres[c], summary["per_class_preservation"][str(c)]))

    # preservation matrix
    cm = np.zeros((8, 8), dtype=np.int64)
    for i, a in enumerate(CLASSES):
        for j, b_ in enumerate(CLASSES):
            cm[i, j] = int(((y_gt == a) & (y_pr == b_)).sum())
    check("preservation matrix total == N", int(cm.sum()) == N, f"{cm.sum()}")
    check("preservation matrix rows sum to class supports",
          bool(np.array_equal(cm.sum(1), np.array([support[c] for c in CLASSES]))))
    mat = np.loadtxt(os.path.join(ART, "GATE3_PRESERVATION_MATRIX.csv"),
                     delimiter=",", skiprows=1)
    cnt = np.loadtxt(os.path.join(ART, "GATE3_PRESERVATION_MATRIX_COUNTS.csv"),
                     delimiter=",", skiprows=1)
    exact = json.load(open(os.path.join(ART, "GATE3_PRESERVATION_MATRIX_COUNTS.json"),
                           encoding="utf-8"))
    check("row-normalised matrix matches recomputation (12-dp file)", close(mat, cm / cm.sum(1, keepdims=True)))
    check("count matrix matches recomputation", np.array_equal(cnt.astype(np.int64), cm))
    check("exact integer count matrix (JSON) matches recomputation",
          np.array_equal(np.array(exact["counts"], dtype=np.int64), cm))
    check("exact count matrix total == N", exact["total"] == N)
    check("exact count matrix row sums == class supports",
          exact["row_sums"] == [support[c] for c in CLASSES])
    check("matrix orientation is rows=Y_GT, columns=Y_PRED",
          exact["orientation"] == "rows = Y_GT, columns = Y_PRED")
    check("row-normalised matrix rows sum to 1",
          bool(np.allclose(mat.sum(1), 1.0, atol=1e-9)))

    # kappa
    po = float(np.trace(cm) / N)
    pe = float(((cm.sum(1) / N) * (cm.sum(0) / N)).sum())
    kappa = (po - pe) / (1 - pe)
    check("Cohen kappa recomputes", close(kappa, summary["cohen_kappa"]),
          f"{kappa:.8f} vs {summary['cohen_kappa']:.8f}")

    # soft metrics
    def tv(p, q):
        return 0.5 * np.abs(p - q).sum(1)

    def js(p, q):
        m_ = 0.5 * (p + q)
        def kl(a, b):
            b = np.clip(b, 1e-300, 1.0)
            return np.where(a > 0, a * np.log2(a / b), 0.0).sum(1)
        return 0.5 * kl(p, m_) + 0.5 * kl(q, m_)

    tvr = tv(proba_gt, proba_pr)
    jsr = js(proba_gt, proba_pr)
    sp = summary["soft_preservation"]
    check("TV median recomputes", close(np.median(tvr), sp["tv_distance"]["median"]))
    check("TV IQR recomputes", close(np.percentile(tvr, 75) - np.percentile(tvr, 25),
                                     sp["tv_distance"]["iqr"]))
    check("JS median recomputes", close(np.median(jsr), sp["js_divergence"]["median"]))
    ref_p = proba_pr[np.arange(N), [cls_list.index(int(c)) for c in y_gt]]
    check("P_PRED[Y_GT] median recomputes",
          close(np.median(ref_p),
                sp["reference_class_probability_P_PRED_at_Y_GT"]["median"]))
    check("TV in [0,1]", bool((tvr >= -1e-12).all() and (tvr <= 1 + 1e-12).all()))
    check("JS >= 0", bool((jsr >= -1e-12).all()))

    # pose error
    err = np.degrees(P - G)
    check("overall pose RMSE recomputes",
          close(float(np.sqrt((err ** 2).mean())), pose_err["overall_rmse_deg"]))
    check("overall pose MAE recomputes",
          close(float(np.abs(err).mean()), pose_err["overall_mae_deg"]))
    for j, nm in enumerate(pose_err["trusted8_names"]):
        check(f"  DOF {nm} MAE recomputes",
              close(float(np.abs(err[:, j]).mean()), pose_err["per_dof"][nm]["mae"]))

    # temporal
    cur = 0
    gseq, pseq = [], []
    for m_ in dm["files"]:
        k = m_["both_valid_blocks"]
        if k == 0:
            continue
        gseq.append(y_gt[cur:cur + k])
        pseq.append(y_pr[cur:cur + k])
        cur += k
    check("contiguous sequence assembly consumes all samples", cur == N)

    def swrate(seqs):
        s = t = 0
        for s_ in seqs:
            if s_.size > 1:
                s += int((s_[1:] != s_[:-1]).sum())
                t += int(s_.size - 1)
        return s / t

    tp = summary["temporal_preservation"]
    check("GT switch rate recomputes", close(swrate(gseq), tp["gt"]["switch_rate_per_sample"]))
    check("prediction switch rate recomputes", close(swrate(pseq), tp["pred"]["switch_rate_per_sample"]))

    n_ev = n_hit = 0
    for a, b_ in zip(gseq, pseq):
        chg = np.flatnonzero(a[1:] != a[:-1]) + 1
        chp = np.flatnonzero(b_[1:] != b_[:-1]) + 1
        pr_map = {}
        for i in chp:
            pr_map.setdefault(int(i), []).append(int(b_[i]))
        for i in chg:
            n_ev += 1
            dest = int(a[i])
            ok = False
            for d in range(-TRANSITION_TOL_FRAMES, TRANSITION_TOL_FRAMES + 1):
                hits = pr_map.get(int(i) + d)
                if hits and dest in hits:
                    ok = True
                    break
            n_hit += int(ok)
    check("GT transition event count recomputes", n_ev == tp["n_gt_transition_events"],
          f"{n_ev} vs {tp['n_gt_transition_events']}")
    check("transition-event match fraction recomputes",
          close(n_hit / n_ev, tp["same_destination_within_tolerance_fraction"]),
          f"{n_hit/n_ev:.6f}")

    # ---------------- 5. stratification accounting ----------------
    print("\n[5] stratification accounting")
    sides = {}
    for m_ in dm["files"]:
        sides[m_["side"]] = sides.get(m_["side"], 0) + m_["both_valid_blocks"]
    check("side counts sum to N", sum(sides.values()) == N, f"{sides}")
    ss = summary["side_stratification"]
    for s_, v in ss.items():
        check(f"  side {s_} n matches", v["n"] == sides[s_], f"{v['n']} vs {sides[s_]}")
        check(f"  side {s_} agreement recomputes",
              close(1.0 - (y_pr != y_gt)[
                  np.concatenate([np.full(m_["both_valid_blocks"], m_["side"] == s_)
                                  for m_ in dm["files"] if m_["both_valid_blocks"]]).astype(bool)
              ].mean() if sides[s_] else np.nan, v["agreement"]))
    stages = {}
    for m_ in dm["files"]:
        stages[m_["stage"]] = stages.get(m_["stage"], 0) + m_["both_valid_blocks"]
    check("stage counts sum to N", sum(stages.values()) == N, f"{len(stages)} stages")
    for r in summary["stage_stratification"]:
        check(f"  stage {r['stage'][:28]} n matches",
              r["n"] == stages[r["stage"]], f"{r['n']} vs {stages[r['stage']]}")

    # ---------------- 6. firewall ----------------
    print("\n[6] firewall assertions")
    fw = summary["firewall"]
    for k, v in fw.items():
        check(f"firewall {k} == {v}", v == "NO")
    dec = load_json(os.path.join(ART, "GATE3_DECISION.json"))
    check("no categorical verdict emitted",
          dec["categorical_labels_emitted"] == "NO")
    check("historical 0.7646 flagged not-used-for-design",
          "NOT USED FOR DESIGN" in dec["historical_reference"]["status"])
    check("no gate artifact present (no GMM/OCSVM/conformal files)",
          not any(x in os.listdir(ART) for x in
                  ("GATE3_RELIABILITY.json", "GATE3_UNKNOWN.json", "GATE3_COVERAGE.csv")))
    check("no human-label artifact present",
          not os.path.exists(os.path.join(ART, "GATE3_HUMAN_LABELS.csv")))

    # ---------------- 7. error -> failure curve ----------------
    print("\n[7] error -> functional failure curve")
    pf = np.sqrt((err ** 2).mean(1))
    order = np.argsort(pf, kind="mergesort")
    parts = np.array_split(order, 10)
    curve = load_json(os.path.join(ART, "GATE3_PRESERVATION_SUMMARY.json"))[
        "error_to_functional_failure"]["decile_curve"]
    check("curve has 10 deciles", len(curve) == 10)
    check("decile sizes sum to N", sum(c["n"] for c in curve) == N)
    for c, ix in zip(curve, parts):
        check(f"  decile {c['decile']} n/median recompute",
              c["n"] == ix.size and close(c["median_pose_error_deg"], float(np.median(pf[ix]))))
        check(f"  decile {c['decile']} disagreement rate recomputes",
              close(c["disagreement_rate"], float((y_pr[ix] != y_gt[ix]).mean())))

    # ---------------- 8. alignment audit ----------------
    print("\n[8] alignment audit")
    al = load_json(os.path.join(ART, "GATE3_ALIGNMENT_AUDIT.json"))
    check("shift_search_performed == NO", al["shift_search_performed"] == "NO")
    check("outcome_used_for_alignment == NO", al["outcome_used_for_alignment"] == "NO")
    check("only official left_context trim applied", al["shift_applied"].startswith("NONE"))
    check("row offsets are exactly [1790]", al["row_offsets"] == [1790],
          f"{al['row_offsets']}")

    print("\n" + "=" * 78)
    print(f"ASSERTIONS: {CHECKS}   FAILED: {len(FAILS)}")
    if FAILS:
        for x in FAILS:
            print(f"  FAILED: {x}")
        print("VERIFY_GATE3: FAIL")
        return 1
    print("VERIFY_GATE3: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
