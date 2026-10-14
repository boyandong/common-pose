#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GATE 4A — candidate score evaluation against the true Fisher error.

Implements GATE4A_PLAN.md §9, §9.1, §9.2 and §11 outputs.
No threshold is selected. No class accuracy is reported. No p-values.

Run:
  /root/miniconda3/envs/emg2pose-gate3/bin/python -X utf8 scripts/evaluate_gate_scores.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import io_common as C  # noqa: E402

CANDIDATES = [
    ("TEMP", "u_TEMP", "CANDIDATE 0 — temporal Fisher volatility baseline"),
    ("TTA", "u_TTA", "CANDIDATE 1 — TTA Fisher consistency (primary score)"),
    ("ERR", "u_ERR", "CANDIDATE 2 — stage-grouped OOF task-error predictor"),
]
SECONDARY = ("TTA_secondary", "u_TTA_secondary",
             "CANDIDATE 1 secondary — max pairwise TTA Fisher distance")


def main() -> int:
    C.ensure_dirs()
    t = C.Tee(os.path.join(C.LOGS, "gate4a_evaluate_stdout.txt"))
    C.banner(t, "GATE 4A — CANDIDATE SCORE EVALUATION (single-user feasibility)")

    with np.load(os.path.join(C.WORK, "candidate_scores.npz")) as zz:
        r = zz["r"].astype(np.float64)
        scores = {key: zz[key].astype(np.float64) for _, key, _ in CANDIDATES}
        scores[SECONDARY[1]] = zz[SECONDARY[1]].astype(np.float64)
        temp_valid = zz["temp_valid"]
    with np.load(os.path.join(C.WORK, "task_error_oof.npz")) as zz:
        fold_of = zz["fold_of"].astype(np.int64)
    pop = C.build_population(require_expected=True)
    n = pop["n"]
    assert r.shape == (n,)

    t.log("[1] inputs")
    t.log(f"    n samples        : {n}")
    t.log(f"    target r         : median {np.median(r):.6f}  mean {r.mean():.6f}  "
          f"p90 {np.percentile(r, 90):.6f}")
    no_gate_mean = float(r.mean())
    no_gate_aurc = float(np.mean([no_gate_mean] * len(C.AURC_COVERAGES)))
    t.log(f"    NO-GATE mean risk (100% coverage): {no_gate_mean:.6f}")
    t.log(f"    NO-GATE reference AURC (constant risk curve): {no_gate_aurc:.6f}")
    t.log(f"    coverage points (frozen): {list(C.COVERAGE_POINTS)}")
    t.log(f"    AURC grid (frozen)      : {C.AURC_COVERAGES[0]} -> "
          f"{C.AURC_COVERAGES[-1]} step 0.01 ({len(C.AURC_COVERAGES)} points)")

    # -------------------------------------------------------------- oracle
    order_oracle = C.rank_order(r)
    oracle_cov = [C.risk_at_coverage(order_oracle, r, c) for c in C.COVERAGE_POINTS]
    oracle_aurc = C.aurc(order_oracle, r)
    t.log()
    t.log("[2] ORACLE ordering (impossible at deployment; ceiling reference only)")
    t.log(f"    AURC {oracle_aurc:.6f}")
    for row in oracle_cov:
        t.log(f"      coverage {row['coverage']:.2f}: accepted {row['n_accepted']:>6}  "
              f"mean r {row['mean_r']:.6f}  median {row['median_r']:.6f}  "
              f"p90 {row['p90_r']:.6f}")

    # -------------------------------------------------------------- candidates
    corr_rows, record_rows, cov_rows, aurc_rows, decile_rows = [], [], [], [], []
    per_candidate = {}

    for label, key, desc in list(CANDIDATES) + [SECONDARY]:
        u = scores[key]
        finite = np.isfinite(u)
        n_excl = int((~finite).sum())
        t.log()
        t.log(f"[3] {desc}")
        t.log(f"    score defined on {int(finite.sum())} / {n} samples "
              f"(excluded {n_excl} with undefined score, never imputed)")
        if int(finite.sum()) < 100:
            t.log("    NOT EVALUABLE — too few defined scores")
            per_candidate[label] = {"status": "NOT_EVALUABLE",
                                    "n_defined": int(finite.sum())}
            continue

        rho = C.spearman(u[finite], r[finite])
        tau = C.kendall(u[finite], r[finite])
        t.log(f"    pooled Spearman rho(u, r) = {rho:+.6f}")
        t.log(f"    pooled Kendall  tau(u, r) = {tau:+.6f}")

        # per-record consistency
        recs = sorted(set(pop["record"].tolist()))
        rec_stats = []
        for stem in recs:
            m = (pop["record"] == stem) & finite
            if int(m.sum()) < 50:
                rec_stats.append({"record": stem, "n": int(m.sum()), "rho": None})
                continue
            rr = C.spearman(u[m], r[m])
            rec_stats.append({
                "record": stem, "n": int(m.sum()), "rho": rr,
                "side": str(pop["side"][m][0]),
                "median_r": float(np.median(r[m])),
                "median_u": float(np.median(u[m])),
            })
        rhos = np.array([x["rho"] for x in rec_stats if x["rho"] is not None],
                        dtype=np.float64)
        med_rec = float(np.median(rhos)) if rhos.size else float("nan")
        iqr_rec = float(np.percentile(rhos, 75) - np.percentile(rhos, 25)) \
            if rhos.size else float("nan")
        pos_frac = float((rhos > 0).mean()) if rhos.size else float("nan")
        t.log(f"    per-record rho: median {med_rec:+.6f}  IQR {iqr_rec:.6f}  "
              f"min {rhos.min():+.6f}  max {rhos.max():+.6f}  "
              f"fraction > 0 = {pos_frac:.4f} ({int((rhos > 0).sum())}/{rhos.size})")
        for side in ("left", "right"):
            ss = [x["rho"] for x in rec_stats
                  if x["rho"] is not None and x.get("side") == side]
            if ss:
                t.log(f"    by hand {side:<5}: n_records {len(ss)}  "
                      f"median rho {np.median(ss):+.6f}  "
                      f"frac>0 {np.mean(np.array(ss) > 0):.4f}")

        # risk-coverage + AURC
        order = C.rank_order(u)
        cov = [C.risk_at_coverage(order, r, c) for c in C.COVERAGE_POINTS]
        au = C.aurc(order, r)
        t.log(f"    AURC {au:.6f}   (no-gate {no_gate_aurc:.6f}, oracle "
              f"{oracle_aurc:.6f})")
        for row in cov:
            t.log(f"      coverage {row['coverage']:.2f}: accepted "
                  f"{row['n_accepted']:>6}  mean r {row['mean_r']:.6f}  "
                  f"median {row['median_r']:.6f}  p90 {row['p90_r']:.6f}")

        dec = C.decile_summary(u, r)
        t.log("    deciles (ascending predicted risk):")
        t.log(f"      {'dec':>4}{'n':>7}{'med_score':>13}{'med_r':>10}"
              f"{'mean_r':>10}{'p90_r':>10}")
        for row in dec:
            t.log(f"      {row['decile']:>4}{row['n']:>7}{row['median_score']:>13.4f}"
                  f"{row['median_r']:>10.4f}{row['mean_r']:>10.4f}"
                  f"{row['p90_r']:>10.4f}")
        mono = all(dec[i]["median_r"] <= dec[i + 1]["median_r"]
                   for i in range(len(dec) - 1))
        first_last = dec[-1]["median_r"] - dec[0]["median_r"]
        t.log(f"    monotone non-decreasing median_r across all 10 deciles: {mono}")
        t.log(f"    median_r decile10 - decile1 = {first_last:+.6f}")

        band = C.feasibility_band(rho, med_rec, pos_frac, au, no_gate_aurc)
        t.log(f"    PRE-DECLARED FEASIBILITY BAND: {band}")

        corr_rows.append({
            "candidate": label, "description": desc,
            "n_defined": int(finite.sum()), "n_excluded": n_excl,
            "spearman_overall": rho, "kendall_overall": tau,
            "median_record_spearman": med_rec, "iqr_record_spearman": iqr_rec,
            "min_record_spearman": float(rhos.min()) if rhos.size else None,
            "max_record_spearman": float(rhos.max()) if rhos.size else None,
            "positive_record_fraction": pos_frac,
            "n_records": int(rhos.size),
            "aurc": au, "no_gate_aurc": no_gate_aurc, "oracle_aurc": oracle_aurc,
            "decile_median_r_monotone": bool(mono),
            "decile10_minus_decile1_median_r": float(first_last),
            "feasibility_band": band,
        })
        for x in rec_stats:
            record_rows.append({"candidate": label, **x})
        for row in cov:
            cov_rows.append({"candidate": label, **row})
        aurc_rows.append({"candidate": label, "aurc": au,
                          "no_gate_aurc": no_gate_aurc, "oracle_aurc": oracle_aurc,
                          "aurc_minus_no_gate": au - no_gate_aurc,
                          "n_defined": int(finite.sum())})
        for row in dec:
            decile_rows.append({"candidate": label, **row})
        per_candidate[label] = {
            "status": "EVALUATED", "spearman_overall": rho, "kendall_overall": tau,
            "median_record_spearman": med_rec, "positive_record_fraction": pos_frac,
            "aurc": au, "feasibility_band": band,
        }

    # oracle rows into the shared tables
    for row in oracle_cov:
        cov_rows.append({"candidate": "ORACLE", **row})
    aurc_rows.append({"candidate": "ORACLE", "aurc": oracle_aurc,
                      "no_gate_aurc": no_gate_aurc, "oracle_aurc": oracle_aurc,
                      "aurc_minus_no_gate": oracle_aurc - no_gate_aurc,
                      "n_defined": n})
    aurc_rows.append({"candidate": "NO_GATE", "aurc": no_gate_aurc,
                      "no_gate_aurc": no_gate_aurc, "oracle_aurc": oracle_aurc,
                      "aurc_minus_no_gate": 0.0, "n_defined": n})
    for row in C.decile_summary(np.arange(n, dtype=np.float64), r):
        decile_rows.append({"candidate": "ORACLE", **row})

    C.write_csv(os.path.join(C.ART, "CANDIDATE_CORRELATIONS.csv"), corr_rows)
    C.write_csv(os.path.join(C.ART, "CANDIDATE_BY_RECORD.csv"), record_rows)
    C.write_csv(os.path.join(C.ART, "CANDIDATE_RISK_COVERAGE.csv"), cov_rows)
    C.write_csv(os.path.join(C.ART, "CANDIDATE_AURC.csv"), aurc_rows)
    C.write_csv(os.path.join(C.ART, "CANDIDATE_DECILES.csv"), decile_rows)

    # -------------------------------------------------------------- summary
    t.log()
    t.log("[4] EXPLORATORY FEASIBILITY RANKING (SINGLE-USER FEASIBILITY ONLY —")
    t.log("    NOT A FINAL GATE SELECTION)")
    order_labels = ["MOST_PROMISING_FOR_MULTIUSER", "PROMISING", "WEAK",
                    "NO_VISIBLE_SIGNAL"]
    ranking = []
    for label in order_labels:
        for cand_label, _, _ in CANDIDATES:
            pc = per_candidate.get(cand_label, {})
            if pc.get("feasibility_band") == label:
                ranking.append({"band": label, "candidate": cand_label})
    for row in ranking:
        t.log(f"    {row['band']:<30} {row['candidate']}")
    for cand_label, _, _ in CANDIDATES:
        pc = per_candidate.get(cand_label, {})
        if pc.get("status") != "EVALUATED":
            t.log(f"    NOT_EVALUABLE                   {cand_label}")

    C.write_json(os.path.join(C.WORK, "evaluation.json"), {
        "plan_sha256": C.sha256_file(os.path.join(C.LANE, "GATE4A_PLAN.md")),
        "n": n,
        "no_gate_mean_risk": no_gate_mean,
        "no_gate_aurc": no_gate_aurc,
        "oracle_aurc": oracle_aurc,
        "oracle_coverage": oracle_cov,
        "candidates": per_candidate,
        "ranking": ranking,
        "coverage_points": list(C.COVERAGE_POINTS),
        "aurc_coverages": list(C.AURC_COVERAGES),
        "threshold_selected": "NO",
        "class_accuracy_reported": "NO",
        "p_values_reported": "NO",
    })
    t.log()
    t.log("wrote artifacts/CANDIDATE_CORRELATIONS.csv, CANDIDATE_BY_RECORD.csv, "
          "CANDIDATE_RISK_COVERAGE.csv, CANDIDATE_AURC.csv, CANDIDATE_DECILES.csv, "
          "work/evaluation.json")
    t.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
