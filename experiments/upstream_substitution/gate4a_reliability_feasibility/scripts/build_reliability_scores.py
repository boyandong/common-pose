#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GATE 4A — population, true Fisher-error target, and the three candidate scores.

Implements GATE4A_PLAN.md §3 (population), §5 (target), §6 (CANDIDATE 0),
§7 (CANDIDATE 1). No score-vs-target relationship is computed here — that is
evaluate_gate_scores.py's job.

Run:
  /root/miniconda3/envs/emg2pose-gate3/bin/python -X utf8 scripts/build_reliability_scores.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import io_common as C  # noqa: E402


def main() -> int:
    C.ensure_dirs()
    t = C.Tee(os.path.join(C.LOGS, "gate4a_stdout.txt"))
    C.banner(t, "GATE 4A — RELIABILITY SCORE CONSTRUCTION")

    # ------------------------------------------------------------ population
    t.log("[1] population rebuild (verbatim Gate3 / Gate3B rule)")
    pop = C.build_population(require_expected=True)
    n = pop["n"]
    t.log(f"    records          : {len(pop['files'])}")
    t.log(f"    samples          : {n}")
    t.log(f"    expected         : {C.EXPECTED_N}")
    t.log(f"    rate             : {C.ANALYSIS_HZ} Hz (pose_stride {C.POSE_STRIDE})")
    t.log(f"    sides            : {dict((s, int((pop['side'] == s).sum())) for s in sorted(set(pop['side'].tolist())))}")
    t.log(f"    stages           : {len(set(pop['stage'].tolist()))}")
    t.log(f"    participant dirs : {sorted({os.path.basename(f).split('-')[0] for f in pop['files']})}")
    t.log(f"    user             : {sorted(set(pop['user'].tolist()))}")
    t.log(f"    session          : {sorted(set(pop['session'].tolist()))}")

    # ------------------------------------------------------------ frozen head
    t.log()
    t.log("[2] frozen head + DB9 reference scales")
    head_sha = C.sha256_file(C.FROZEN_HEAD)
    t.log(f"    head sha256      : {head_sha}")
    assert head_sha == ("b0ef8caf8e390a480fa2a3b448f79ccf14f75c71265ef925ee299a5e9e660386"), \
        "frozen head identity changed -> STOP"
    head, mu, sd = C.load_frozen_head()
    sigma = C.load_db9_sigma()
    t.log(f"    sigma_DB9        : {np.round(sigma, 8).tolist()}")
    t.log(f"    scaling source   : DB9 training corpus only")

    # ------------------------------------------------------------ target
    t.log()
    t.log("[3] TRUE FISHER ERROR TARGET (plan §5)")
    z_gt = C.pose_fisher(head, mu, sd, pop["G"])
    z_pr = C.pose_fisher(head, mu, sd, pop["P"])
    assert z_gt.shape == (n, 7) and z_pr.shape == (n, 7)
    r = C.fisher_error(z_pr, z_gt, sigma)
    rs = C.qstats(r)
    t.log(f"    r median {rs['median']:.6f}  IQR {rs['iqr']:.6f}  "
          f"p05 {rs['p05']:.6f}  p95 {rs['p95']:.6f}  mean {rs['mean']:.6f}")
    rec = C.GATE3B_TARGET_RECORD
    repro = {
        "n": n == rec["n"],
        "median": abs(rs["median"] - rec["median"]) < C.TARGET_REPRO_TOL,
        "iqr": abs(rs["iqr"] - rec["iqr"]) < C.TARGET_REPRO_TOL,
        "p05": abs(rs["p05"] - rec["p05"]) < C.TARGET_REPRO_TOL,
        "p95": abs(rs["p95"] - rec["p95"]) < C.TARGET_REPRO_TOL,
    }
    devs = {
        k: abs(rs[k] - rec[k]) for k in ("median", "iqr", "p05", "p95")
    }
    t.log(f"    Gate3B record    : median {rec['median']} IQR {rec['iqr']} "
          f"p05 {rec['p05']} p95 {rec['p95']}  (published to 6 decimals)")
    t.log(f"    deviations       : " + "  ".join(f"{k} {v:.3e}" for k, v in devs.items()))
    t.log(f"    tolerance        : {C.TARGET_REPRO_TOL:g}  (rounding floor; "
          f"{C.TARGET_REPRO_TOL_NOTE})")
    t.log(f"    reproduction     : {repro}")
    assert all(repro.values()), f"target reproduction failed -> STOP: {repro}"

    # ------------------------------------------------------------ CANDIDATE 0
    t.log()
    t.log("[4] CANDIDATE 0 — temporal Fisher volatility baseline (plan §6)")
    dz = np.zeros_like(z_pr)
    temp_valid = np.zeros(n, dtype=bool)
    bounds = {}
    cursor = 0
    for stem in pop["files"]:
        k = int((pop["record"] == C.record_stem(stem)).sum())
        if k:
            bounds[stem] = (cursor, cursor + k)
            cursor += k
    assert cursor == n, (cursor, n)
    for stem, (a, b) in bounds.items():
        if b - a >= 2:
            dz[a + 1:b] = z_pr[a + 1:b] - z_pr[a:b - 1]
            temp_valid[a + 1:b] = True
    u_temp = np.full(n, np.nan, dtype=np.float64)
    u_temp[temp_valid] = np.sqrt(((dz[temp_valid] / sigma) ** 2).sum(1))
    ts = C.qstats(u_temp[temp_valid])
    t.log(f"    defined          : {int(temp_valid.sum())} / {n} "
          f"(NA at first valid frame of each record: {int((~temp_valid).sum())})")
    t.log(f"    u_TEMP median {ts['median']:.6f}  IQR {ts['iqr']:.6f}  "
          f"p95 {ts['p95']:.6f}")

    # ------------------------------------------------------------ CANDIDATE 1
    t.log()
    t.log("[5] CANDIDATE 1 — TTA Fisher consistency (plan §7)")
    tta_records_path = os.path.join(C.WORK, "tta_inference_records.json")
    tta_views_path = os.path.join(C.WORK, "tta_fisher_views.npz")
    tta_status = "NOT_EVALUABLE"
    tta_reason = "run_tta_inference.py has not produced work/tta_fisher_views.npz"
    u_tta = np.full(n, np.nan, dtype=np.float64)
    u_tta_sec = np.full(n, np.nan, dtype=np.float64)
    tta_info = {}
    if os.path.isfile(tta_views_path) and os.path.isfile(tta_records_path):
        with open(tta_records_path, encoding="utf-8") as fh:
            tta_info = json.load(fh)
        tta_status = tta_info.get("TTA_STATUS", "NOT_EVALUABLE")
        with np.load(tta_views_path) as zz:
            views = {}
            for name in C.TTA_VIEW_NAMES:
                key = f"z_{name.replace('+', 'p')}"
                assert key in zz.files, f"missing TTA view {key}"
                views[name] = zz[key]
            sigma_npz = zz["sigma_db9"]
        assert np.allclose(sigma_npz, sigma, rtol=0, atol=0)
        for name in C.TTA_VIEW_NAMES:
            assert views[name].shape == (n, 7), (name, views[name].shape)
        stack = np.stack([views[name] for name in C.TTA_VIEW_NAMES], axis=0)  # (K, n, 7)
        zbar = stack.mean(axis=0)
        dev = (stack - zbar[None, :, :]) / sigma[None, None, :]
        u_tta = np.sqrt((dev ** 2).sum(axis=2).mean(axis=0))
        # secondary: max normalised pairwise Fisher distance across views
        k = len(C.TTA_VIEW_NAMES)
        pair = np.zeros(n, dtype=np.float64)
        for i in range(k):
            for j in range(i + 1, k):
                d = np.sqrt((((stack[i] - stack[j]) / sigma) ** 2).sum(1))
                pair = np.maximum(pair, d)
        u_tta_sec = pair
        t.log(f"    TTA_STATUS       : {tta_status}")
        t.log(f"    views            : {list(C.TTA_VIEW_NAMES)}  K={k}")
        t.log(f"    identity exact   : {tta_info.get('V4_identity_bit_exact')}")
        t.log(f"    u_TTA median {C.qstats(u_tta)['median']:.6f}  "
              f"IQR {C.qstats(u_tta)['iqr']:.6f}  p95 {C.qstats(u_tta)['p95']:.6f}")
        t.log(f"    u_TTA_secondary (max pairwise) median "
              f"{C.qstats(u_tta_sec)['median']:.6f}")
        tta_reason = "all declared validity conditions satisfied" if tta_status == "EVALUABLE" \
            else "one or more declared validity conditions failed"
    else:
        t.log(f"    TTA_STATUS       : NOT_EVALUABLE")
        t.log(f"    reason           : {tta_reason}")

    # ------------------------------------------------------------ CANDIDATE 2
    t.log()
    t.log("[6] CANDIDATE 2 — OOF task-error predictor scores")
    oof_path = os.path.join(C.WORK, "task_error_oof.npz")
    u_err = np.full(n, np.nan, dtype=np.float64)
    err_info = {}
    if os.path.isfile(oof_path):
        with np.load(oof_path) as zz:
            u_err = zz["oof"].astype(np.float64)
            fold_of = zz["fold_of"].astype(np.int64)
        assert u_err.shape == (n,), u_err.shape
        assert np.isfinite(u_err).all(), "OOF score incomplete"
        with open(os.path.join(C.ART, "TASK_ERROR_PREDICTOR_SUMMARY.json"),
                  encoding="utf-8") as fh:
            err_info = json.load(fh)
        es = C.qstats(u_err)
        t.log(f"    OOF coverage     : {int(np.isfinite(u_err).sum())} / {n}")
        t.log(f"    u_ERR median {es['median']:.6f}  IQR {es['iqr']:.6f}  "
              f"p95 {es['p95']:.6f}")
        t.log(f"    models converged : {err_info.get('n_models_converged')} / 5")
    else:
        t.log("    NOT RUN — work/task_error_oof.npz missing")

    # ------------------------------------------------------------ artifacts
    t.log()
    t.log("[7] writing artifacts")
    plan_sha = C.sha256_file(os.path.join(C.LANE, "GATE4A_PLAN.md"))

    C.write_json(os.path.join(C.ART, "GATE4A_DATA_LINK.json"), {
        "artifact": "GATE4A_DATA_LINK.json",
        "gate": "PHASE 1 / GATE 4A — single-user reliability-score feasibility screen",
        "plan_sha256": plan_sha,
        "evidence_status": "SINGLE-USER FEASIBILITY SCREEN ONLY",
        "reuses_gate3_population": "YES",
        "gate3_artifacts_modified": "NO",
        "gate3b_artifacts_modified": "NO",
        "new_upstream_inference": "YES — only the frozen TTA transform set of plan §4.2 "
                                  "(identity + one electrode-band shift each way); the "
                                  "identity view reproduces the frozen Gate3 stream "
                                  "bit-exactly and is asserted",
        "predicted_stream": {"dir": C.PRED_DIR, "files": len(pop["files"])},
        "gt_stream": {"dir": C.MINI_DIR, "field": "emg2pose/timeseries/joint_angles"},
        "frozen_head": {"path": C.FROZEN_HEAD, "sha256": head_sha},
        "checkpoint": {"path": C.CKPT,
                       "sha256": "748b1d1ef0ce1985f6fc07225d97eebfb370243429af803b4997d28ecce2424e"},
        "population": {
            "n": n, "expected_n": C.EXPECTED_N, "identity_match": n == C.EXPECTED_N,
            "rate_hz": C.ANALYSIS_HZ, "pose_stride": C.POSE_STRIDE,
            "participant_dirs": sorted({os.path.basename(f).split("-")[0]
                                        for f in pop["files"]}),
            "users": sorted(set(pop["user"].tolist())),
            "sessions": sorted(set(pop["session"].tolist())),
            "sides": {s: int((pop["side"] == s).sum())
                      for s in sorted(set(pop["side"].tolist()))},
            "n_stages": len(set(pop["stage"].tolist())),
            "n_records": len(pop["files"]),
        },
        "alignment_rule": {
            "rule": "prediction[i] <-> GT[1790+i]",
            "verified": "np.array_equal(GT.time[1790:], pred.time) asserted per record",
            "lag_search_performed": "NO",
        },
        "target": {
            "definition": "r_t = sqrt(sum_j ((z_PRED_tj - z_GT_tj)/sigma_DB9_j)^2)",
            "sigma_source": "DB9 training corpus only (DB9-only reference scales)",
            "used_only_for": ["training the exploratory task-error predictor",
                              "candidate score evaluation", "risk-coverage analysis"],
            "used_in_tta_inference": "NO",
            "used_in_deployment_features": "NO",
            "used_in_perturbation_selection": "NO",
            "used_in_temporal_baseline": "NO",
        },
        "scaling_source": "DB9 training corpus only; no emg2pose-derived scaling",
        "filtering_applied": "NONE beyond the frozen Gate3 eligibility rule",
    })

    C.write_json(os.path.join(C.ART, "TRUE_FISHER_ERROR_TARGET.json"), {
        "artifact": "TRUE_FISHER_ERROR_TARGET.json",
        "plan_sha256": plan_sha,
        "definition": "r_t = sqrt( sum_j ( ( z_PRED,t,j - z_GT,t,j ) / sigma_DB9,j )^2 )",
        "representation": "frozen 7-D DB9 LDA Fisher embedding of DB9-standardised "
                          "trusted-8 pose",
        "trusted8_source_indices": C.TRUSTED8_SRC_IDX,
        "db9_component_sigma": sigma.tolist(),
        "stats": rs,
        "gate3b_recorded": rec,
        "reproduction_checks": repro,
        "reproduction_deviations": devs,
        "exact_gate3b_reproduction": bool(all(repro.values())),
        "reproduction_tolerance": C.TARGET_REPRO_TOL,
        "reproduction_tolerance_note": C.TARGET_REPRO_TOL_NOTE,
        "role": "supervision label / evaluation target ONLY",
        "deployment_available": "NO — never a feature, never used at inference",
    })

    C.write_json(os.path.join(C.ART, "TEMPORAL_BASELINE_SUMMARY.json"), {
        "artifact": "TEMPORAL_BASELINE_SUMMARY.json",
        "plan_sha256": plan_sha,
        "candidate": "CANDIDATE 0 — temporal Fisher volatility baseline",
        "definition": "u_TEMP,t = sqrt( sum_j ( ( z_PRED,t,j - z_PRED,t-1,j ) / sigma_DB9,j )^2 )",
        "deployment_visible_inputs": ["z_PRED (official upstream prediction only)"],
        "uses_gt": "NO",
        "uses_target": "NO",
        "record_connection": "records are never connected; the first valid frame of "
                             "each record has u_TEMP = NA",
        "n_defined": int(temp_valid.sum()),
        "n_na": int((~temp_valid).sum()),
        "stats": ts,
        "is_true_uncertainty": "NO — this is a task-relevant motion proxy; it is a "
                               "sanity baseline, not a gate",
    })

    C.write_json(os.path.join(C.ART, "TTA_SCORE_SUMMARY.json"), {
        "artifact": "TTA_SCORE_SUMMARY.json",
        "plan_sha256": plan_sha,
        "candidate": "CANDIDATE 1 — TTA Fisher consistency",
        "STATUS": tta_status,
        "status_reason": tta_reason,
        "primary_score": "u_TTA,t = sqrt( (1/K) * sum_k sum_j "
                         "( ( z_t^(k,j) - zbar_t,j ) / sigma_DB9,j )^2 )",
        "secondary_score": "max normalised pairwise Fisher distance across TTA views "
                           "(reported only; never substituted for the primary)",
        "secondary_is_primary": "NO",
        "K": len(C.TTA_VIEW_NAMES),
        "views": list(C.TTA_VIEW_NAMES),
        "shifts": list(C.TTA_SHIFTS),
        "inference_records": tta_info,
        "primary_stats": C.qstats(u_tta) if np.isfinite(u_tta).any() else None,
        "secondary_stats": C.qstats(u_tta_sec) if np.isfinite(u_tta_sec).any() else None,
        "runtime_documentation": tta_info.get("timing"),
        "identity_agreement": tta_info.get("identity_agreement"),
        "index_space": tta_info.get("index_space"),
        "n_rows_per_view": tta_info.get("n_rows_per_view"),
        "uses_gt": "NO",
        "uses_target": "NO",
        "model_retrained": "NO",
        "test_time_adaptation": "NO",
        "perturbation_tuned_on_target": "NO",
    })

    np.savez_compressed(
        os.path.join(C.WORK, "candidate_scores.npz"),
        u_TEMP=u_temp, u_TTA=u_tta, u_TTA_secondary=u_tta_sec,
        u_ERR=u_err, r=r, idx=np.arange(n),
        z_PRED=z_pr, z_GT=z_gt, temp_valid=temp_valid,
    )
    C.write_csv(
        os.path.join(C.WORK, "population_index.csv"),
        [{"idx": i, "record": str(pop["record"][i]), "side": str(pop["side"][i]),
          "stage": str(pop["stage"][i]), "block_idx": int(pop["block_idx"][i]),
          "tta_idx": int(pop["tta_idx"][i])}
         for i in range(n)],
        ["idx", "record", "side", "stage", "block_idx", "tta_idx"],
    )

    t.log("    work/candidate_scores.npz")
    t.log("    work/population_index.csv")
    t.log("    artifacts/GATE4A_DATA_LINK.json")
    t.log("    artifacts/TRUE_FISHER_ERROR_TARGET.json")
    t.log("    artifacts/TEMPORAL_BASELINE_SUMMARY.json")
    t.log("    artifacts/TTA_SCORE_SUMMARY.json")
    t.log()
    t.log("    NOTE: no score-vs-target comparison was computed in this script.")
    t.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
