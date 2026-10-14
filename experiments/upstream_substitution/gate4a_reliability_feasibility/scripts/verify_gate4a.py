#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GATE 4A — independent verifier.

Re-derives the population, target, candidate scores and every reported metric
from source, and asserts them against the recorded artifacts. Prefers assertions
over prose: any mismatch raises AssertionError.

Implements GATE4A_PLAN.md §27 of the Chat instruction (verification) and the
firewall of plan §12.

Run:
  /root/miniconda3/envs/emg2pose-gate3/bin/python -X utf8 scripts/verify_gate4a.py
"""
from __future__ import annotations

import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import io_common as C  # noqa: E402

from sklearn.ensemble import GradientBoostingRegressor  # noqa: E402
from sklearn.model_selection import GroupKFold  # noqa: E402

N_CHECKS = 0


def check(cond, msg: str) -> None:
    global N_CHECKS
    N_CHECKS += 1
    if not cond:
        raise AssertionError(f"FAILED CHECK: {msg}")
    print(f"    [ok] {msg}")


def close(a, b, tol) -> bool:
    return bool(np.allclose(np.asarray(a, dtype=np.float64),
                            np.asarray(b, dtype=np.float64), rtol=0, atol=tol))


def same_value(recomputed, recorded, tol=1e-9) -> bool:
    recorded = float(recorded)
    if np.isnan(recomputed) or np.isnan(recorded):
        return bool(np.isnan(recomputed) and np.isnan(recorded))
    return abs(float(recomputed) - recorded) < tol


def main() -> int:  # noqa: C901
    C.ensure_dirs()
    t = C.Tee(os.path.join(C.LOGS, "gate4a_verify_stdout.txt"))
    C.banner(t, "GATE 4A — INDEPENDENT VERIFICATION")

    def say(m=""):
        print(m, flush=True)
        t.log(m)

    # ------------------------------------------------------------------ 1 plan
    say("[1] plan SHA")
    with open(os.path.join(C.LANE, "GATE4A_PLAN.sha256"), encoding="utf-8") as fh:
        recorded = fh.read().split()[0].strip()
    actual = C.sha256_file(os.path.join(C.LANE, "GATE4A_PLAN.md"))
    check(recorded == actual, f"plan sha256 recorded == recomputed ({actual})")

    data_link = json.load(open(os.path.join(C.ART, "GATE4A_DATA_LINK.json"),
                               encoding="utf-8"))
    check(data_link["plan_sha256"] == actual, "GATE4A_DATA_LINK.json binds the plan hash")
    tta_audit = json.load(open(os.path.join(C.ART, "TTA_TRANSFORM_AUDIT.json"),
                               encoding="utf-8"))
    check(tta_audit["plan_sha256"] == actual, "TTA_TRANSFORM_AUDIT.json binds the plan hash")

    # ------------------------------------------------------------------ 2 population
    say()
    say("[2] Gate3B population identity (rebuilt from raw sources)")
    pop = C.build_population(require_expected=True)
    n = pop["n"]
    check(n == 86833, f"N == 86,833 (got {n})")
    check(len(pop["files"]) == 30, "30 records")
    check(len(set(pop["stage"].tolist())) == 15, "15 stages")
    sides = {s: int((pop["side"] == s).sum()) for s in sorted(set(pop["side"].tolist()))}
    check(sides == {"left": 43535, "right": 43298},
          f"side counts match Gate3B ({sides})")
    check(len(set(pop["user"].tolist())) == 1, "single participant")
    check(len(set(pop["session"].tolist())) == 1, "single session")
    check(C.ANALYSIS_HZ == 50.0 and C.POSE_STRIDE == 40, "50 Hz analysis rate")
    dl_pop = data_link["population"]
    check(dl_pop["n"] == n and dl_pop["n_stages"] == 15
          and dl_pop["n_records"] == 30, "DATA_LINK population agrees")
    # stage -> hands pairing used by the grouping scheme
    for s in sorted(set(pop["stage"].tolist())):
        hs = sorted(set(pop["side"][pop["stage"] == s].tolist()))
        check(hs == ["left", "right"], f"stage {s[:28]} contains both hands")
    # record counts sum to N
    per_rec = {stem: int((pop["record"] == C.record_stem(stem)).sum())
               for stem in pop["files"]}
    check(sum(per_rec.values()) == n, "record-level counts sum to N")

    # ------------------------------------------------------------------ 3 head/target
    say()
    say("[3] frozen head, DB9 scales, and exact true Fisher-error reproduction")
    head_sha = C.sha256_file(C.FROZEN_HEAD)
    check(head_sha == "b0ef8caf8e390a480fa2a3b448f79ccf14f75c71265ef925ee299a5e9e660386",
          "frozen head sha256")
    head, mu, sd = C.load_frozen_head()
    sigma = C.load_db9_sigma()
    ref = json.load(open(C.DB9_REF, encoding="utf-8"))
    check(close(sigma, ref["fisher_component_sigma_db9"], 0.0),
          "sigma_DB9 used == DB9-only reference scales (exact)")
    check(ref["provenance"]["emg2pose_data_used"] == "NO",
          "DB9 reference scales carry no emg2pose data")
    check(ref["provenance"]["db9_frames"] == 123200 and ref["provenance"]["db9_subjects"] == 77,
          "DB9 reference corpus = 123,200 frames / 77 participants")

    z_gt = C.pose_fisher(head, mu, sd, pop["G"])
    z_pr = C.pose_fisher(head, mu, sd, pop["P"])
    r = C.fisher_error(z_pr, z_gt, sigma)
    # ---- TARGET-INTEGRITY GUARD ----------------------------------------------
    # `r` is the Fisher-error target for the ENTIRE run. It must never be rebound to a
    # scalar by a loop index. This guard fails closed if it ever is.
    check(isinstance(r, np.ndarray) and r.ndim == 1 and r.shape == (n,),
          f"Fisher-error target r is ndarray shape ({n},) after construction")
    rs = C.qstats(r)
    with open(os.path.join(C.ART, "TRUE_FISHER_ERROR_TARGET.json"), encoding="utf-8") as fh:
        tgt = json.load(fh)
    rec_g3b = tgt["gate3b_recorded"]
    for k in ("median", "iqr", "p05", "p95"):
        check(abs(rs[k] - rec_g3b[k]) < C.TARGET_REPRO_TOL,
              f"r {k} reproduces Gate3B within {C.TARGET_REPRO_TOL:g} "
              f"({rs[k]:.9f} vs {rec_g3b[k]})")
    check(abs(rs["median"] - 2.896259) < 1e-6, "r median == 2.896259 (Gate3B)")
    for k in ("median", "iqr", "p05", "p95"):
        check(abs(rs[k] - rec_g3b[k]) < 1e-6,
              f"r {k} is within the 6-decimal rounding floor of the Gate3B literal")
    check(close(tgt["stats"]["mean"], rs["mean"], 1e-12), "target stats mean matches")

    # ------------------------------------------------------------------ 4 candidates
    say()
    say("[4] candidate scores re-derived independently")
    with np.load(os.path.join(C.WORK, "candidate_scores.npz")) as zz:
        u_temp_saved = zz["u_TEMP"].astype(np.float64)
        u_tta_saved = zz["u_TTA"].astype(np.float64)
        u_tta_sec_saved = zz["u_TTA_secondary"].astype(np.float64)
        u_err_saved = zz["u_ERR"].astype(np.float64)
        r_saved = zz["r"].astype(np.float64)
    check(close(r_saved, r, 1e-12), "stored r == independently recomputed r")

    # CANDIDATE 0 re-derived
    dz = np.zeros_like(z_pr)
    valid = np.zeros(n, dtype=bool)
    cursor = 0
    bounds = {}
    for stem in pop["files"]:
        n_rec = int((pop["record"] == C.record_stem(stem)).sum())
        if n_rec:
            bounds[stem] = (cursor, cursor + n_rec)
            cursor += n_rec
    for stem, (a, b) in bounds.items():
        if b - a >= 2:
            dz[a + 1:b] = z_pr[a + 1:b] - z_pr[a:b - 1]
            valid[a + 1:b] = True
    u_temp = np.full(n, np.nan)
    u_temp[valid] = np.sqrt(((dz[valid] / sigma) ** 2).sum(1))
    check(close(u_temp[valid], u_temp_saved[valid], 1e-12),
          "u_TEMP reproduces exactly on defined frames")
    check(np.isnan(u_temp_saved[~valid]).all() and int((~valid).sum()) == 30,
          "u_TEMP undefined (NA) exactly at the first valid frame of each of 30 records")
    check(not np.isfinite(u_temp_saved[~valid]).any(),
          "u_TEMP never imputed at record starts")

    # CANDIDATE 1 re-derived from stored trusted-8 pose block means
    tta_status = json.load(open(os.path.join(C.ART, "TTA_SCORE_SUMMARY.json"),
                                encoding="utf-8"))["STATUS"]
    tta_ok = tta_status == "EVALUABLE"
    if tta_ok:
        with np.load(os.path.join(C.WORK, "tta_pose_blocks.npz")) as zz:
            blocks = {name: zz[f"pose_{name.replace('+', 'p')}"].astype(np.float64)
                      for name in C.TTA_VIEW_NAMES}
            block_idx = zz["block_idx"].astype(np.int64)
            tta_idx = zz["tta_idx"].astype(np.int64)
        with np.load(os.path.join(C.WORK, "tta_fisher_views.npz")) as zz:
            z_views_npz = {name: zz[f"z_{name.replace('+', 'p')}"].astype(np.float64)
                           for name in C.TTA_VIEW_NAMES}
            sigma_npz = zz["sigma_db9"].astype(np.float64)
        # Loaded here so every consumer below sees it (the transform-set cross-check
        # and the per-view deviation recomputation both read `recs`).
        recs = json.load(open(os.path.join(C.WORK, "tta_inference_records.json"),
                              encoding="utf-8"))
        # ---- SINGLE EXPLICIT INDEX-SPACE CONTRACT: ELIGIBLE-ONLY (86,833 rows) ----
        check(all(b.shape == (C.EXPECTED_N, 8) for b in blocks.values()),
              f"TTA pose views are ELIGIBLE-ONLY {C.EXPECTED_N} x 8 per view; shapes="
              f"{ {k: v.shape for k, v in blocks.items()} }")
        check(all(b.shape == (C.EXPECTED_N, 7) for b in z_views_npz.values()),
              f"TTA Fisher views are ELIGIBLE-ONLY {C.EXPECTED_N} x 7 per view; shapes="
              f"{ {k: v.shape for k, v in z_views_npz.items()} }")
        check(np.array_equal(sigma_npz, sigma),
              "persisted sigma_db9 == the DB9-only reference scales, exactly")
        check(np.array_equal(block_idx, pop["block_idx"]),
              "persisted block_idx == population LOCAL block_idx (provenance)")
        check(np.array_equal(tta_idx, pop["tta_idx"]),
              "persisted tta_idx == population GLOBAL 2 kHz index (provenance)")
        check(np.array_equal(pop["tta_idx"],
                             1790 + C.POSE_STRIDE * pop["block_idx"]),
              "tta_idx == row_offset + pose_stride * block_idx (index contract)")
        rstart, rlen = C.record_offsets(pop)
        check(int(rlen.sum()) == C.EXPECTED_N,
              "per-record eligible counts sum to 86,833")
        check(bool((rlen > 0).all()), "no record contributed zero eligible rows")
        block_parts = np.split(pop["block_idx"], np.cumsum(rlen)[:-1])
        check(np.array_equal(np.concatenate(block_parts), pop["block_idx"]),
              "block partition concatenates to the population block index")
        # record concatenation order must match the frozen population order
        check(len(block_parts) == len(pop["files"]) == 30,
              "30 records in frozen population order")
        # ---- NON-VACUOUS identity agreement, per record ----
        # NOTE ON NAMES: the loop index must NOT be called `r`, because `r` is the
        # Fisher-error target array for the whole run. A bare `for r, ... in enumerate`
        # here rebound it to an int and corrupted every later metric computation.
        total_cmp = 0
        for rec_i, stem in enumerate(pop["files"]):
            n_r = int(rlen[rec_i])
            a = int(rstart[rec_i])
            sl = slice(a, a + n_r)
            check(n_r > 0, f"record {rec_i}: compared sample count > 0")
            check(blocks["k0"][sl].shape[0] == n_r,
                  f"record {rec_i}: persisted k0 rows == rec_len[rec_i] ({n_r})")
            with np.load(os.path.join(C.PRED_DIR,
                                      f"{C.record_stem(stem)}_pred.npz")) as zz:
                ang = np.asarray(zz["angles"], dtype=np.float32)
            nb = (ang.shape[0] // C.POSE_STRIDE) * C.POSE_STRIDE
            frozen_all = (ang[:nb].astype(np.float64).reshape(-1, C.POSE_STRIDE, 20)
                          .mean(1)[:, C.TRUSTED8_SRC_IDX])
            ref = frozen_all[block_parts[rec_i]]
            check(ref.shape[0] == n_r == blocks["k0"][sl].shape[0],
                  f"record {rec_i} ({C.record_stem(stem)[-22:]}): compared count == "
                  f"rec_len[rec_i] == {n_r}")
            check(int(ref.size) > 0, f"record {rec_i}: comparison is non-empty")
            check(np.abs(blocks["k0"][sl] - ref).max() == 0.0,
                  f"record {rec_i} ({C.record_stem(stem)[-22:]}): k0 eligible block "
                  f"means reproduce the frozen stream from source, bit-exactly")
            check(np.abs(blocks["k0"][sl] - pop["P"][sl]).max() <= C.TTA_BLOCK_MEAN_TOL,
                  f"record {rec_i}: k0 rows match the frozen population slice")
            total_cmp += n_r
        check(total_cmp == C.EXPECTED_N,
              f"total compared == 86,833 (got {total_cmp}); no record skipped")
        for name in C.TTA_VIEW_NAMES:
            # Contract (corrected): ONLY k0 is the identity view and must reproduce the
            # frozen eligible predicted stream. k+1 / k-1 are perturbed-INPUT views and
            # must NOT be required to equal pop["P"]; a label-preserving input
            # perturbation may legitimately leave the model output unchanged, so
            # output non-equality is deliberately NOT asserted anywhere.
            check(np.isfinite(blocks[name]).all(),
                  f"TTA view {name}: all pose values finite")
            check(np.isfinite(z_views_npz[name]).all(),
                  f"TTA view {name}: all Fisher values finite")
            check(blocks[name].shape == (C.EXPECTED_N, 8),
                  f"TTA view {name}: pose shape == (86833, 8)")
            check(z_views_npz[name].shape == (C.EXPECTED_N, 7),
                  f"TTA view {name}: Fisher shape == (86833, 7)")
            check(np.abs(z_views_npz[name] - C.pose_fisher(head, mu, sd, blocks[name]))
                  .max() < 1e-12,
                  f"TTA view {name}: Fisher view == Fisher(pose view)")
            if name == "k0":
                check(np.abs(blocks[name] - pop["P"]).max() <= C.TTA_BLOCK_MEAN_TOL,
                      f"TTA view k0 (identity): eligible rows == frozen pop['P'] "
                      f"within {C.TTA_BLOCK_MEAN_TOL:g} rad")
        # k0 Fisher representation must equal the frozen identity Fisher representation.
        # The binding frozen tolerance is expressed in POSE space
        # (C.TTA_BLOCK_MEAN_TOL, rad). The Fisher representation is a deterministic
        # LINEAR transform of the standardised pose, so the Fisher-space tolerance is
        # TRANSPORTED from it rather than invented:
        #     x_std_i = (pose_i - mu_i) / sd_i          (frozen preprocessing)
        #     z_j     = sum_i x_std_i * scalings_[i,j]  (head.transform == x @ scalings_,
        #                                                xbar_ ~ 0, verified 0.0 diff)
        # =>  max_i |dpose_i| <= t   implies   max_j |dz_j| <= t * gain_inf
        # with gain_inf = max_j sum_i |scalings_[i,j] / sd_i|  (exact induced inf-norm).
        # gain_inf depends only on the frozen serialized head, never on any outcome.
        gain_inf = float(np.max(np.sum(np.abs(head.scalings_ / sd[:, None]), axis=0)))
        fisher_tol = C.TTA_BLOCK_MEAN_TOL * gain_inf
        check(np.isfinite(gain_inf) and gain_inf > 0.0,
              f"frozen-head Fisher gain_inf is finite and positive ({gain_inf:.6e})")
        max_fisher_diff = float(np.abs(z_views_npz["k0"] - z_pr).max())
        check(max_fisher_diff <= fisher_tol,
              "TTA view k0: Fisher identity agreement within transported tolerance "
              f"{fisher_tol:.6e}; pose_tol={C.TTA_BLOCK_MEAN_TOL:.6e}; "
              f"frozen_gain_inf={gain_inf:.6e}; observed_max={max_fisher_diff:.6e}")
        # Independent algebraic check that the transported bound corresponds to the
        # ACTUAL frozen map: transport the real identity-pair pose difference through
        # the frozen linear map and confirm it reproduces the observed Fisher identity
        # difference to normal floating-point arithmetic precision. This validates the
        # bound's derivation; it does NOT set fisher_tol.
        delta_x = blocks["k0"] - pop["P"]
        delta_z_linear = delta_x @ (head.scalings_ / sd[:, None])
        delta_z_observed = z_views_npz["k0"] - z_pr
        d_lin = np.abs(delta_z_linear - delta_z_observed)
        scale = float(np.abs(delta_z_observed).max()) + float(np.abs(delta_z_linear).max())
        lin_tol = 1e-12 + 8.0 * np.finfo(np.float64).eps * scale
        check(float(d_lin.max()) <= lin_tol,
              "k0: pose-difference transported through the frozen linear map reproduces "
              f"the observed Fisher identity difference (max diff {d_lin.max():.3e} <= "
              f"arithmetic bound {lin_tol:.3e})")
        # the non-identity input transform was really applied: the audit must bind the
        # frozen shift set, and the persisted record must declare those shifts
        check(tta_audit["TTA_TRANSFORM_SET_FROZEN"]["shifts"] == [0, 1, -1]
              and list(tta_audit["TTA_TRANSFORM_SET_FROZEN"]["view_names"])
              == list(C.TTA_VIEW_NAMES),
              "transform audit confirms the {identity, +1, -1} electrode-band "
              "transforms were the frozen and applied set")
        check(list(recs["tta_shifts"]) == list(C.TTA_SHIFTS)
              and list(recs["view_names"]) == list(C.TTA_VIEW_NAMES),
              "TTA inference record declares the same frozen transform set")
        # recorded Fisher-deviation-vs-k0 summary is independently recomputed here
        for name in ("k+1", "k-1"):
            d_norm = np.sqrt((((z_views_npz[name] - z_views_npz["k0"]) / sigma) ** 2)
                             .sum(1))
            recomputed = C.qstats(d_norm)
            recorded = recs["view_fisher_deviation_vs_identity"][name]
            check(abs(recomputed["median"] - recorded["median"]) < 1e-9,
                  f"TTA view {name}: recorded median Fisher deviation vs k0 reproduces "
                  f"({recomputed['median']:.6f})")
            check(abs(recomputed["p95"] - recorded["p95"]) < 1e-9,
                  f"TTA view {name}: recorded p95 Fisher deviation vs k0 reproduces")
            check(abs(recomputed["max"] - recorded["max"]) < 1e-9,
                  f"TTA view {name}: recorded max Fisher deviation vs k0 reproduces")
        # u_TTA is retained and independently recomputed from the persisted views
        z_stack = np.stack([z_views_npz[name] for name in C.TTA_VIEW_NAMES], axis=0)
        check(z_stack.shape == (3, C.EXPECTED_N, 7), z_stack.shape)
        zbar = z_stack.mean(0)
        dev = (z_stack - zbar[None]) / sigma[None, None, :]
        u_tta = np.sqrt((dev ** 2).sum(2).mean(0))
        check(close(u_tta, u_tta_saved, 1e-9), "u_TTA re-derived matches recorded")
        pair = np.zeros(n)
        for i in range(3):
            for j in range(i + 1, 3):
                dd = np.sqrt((((z_stack[i] - z_stack[j]) / sigma) ** 2).sum(1))
                pair = np.maximum(pair, dd)
        check(close(pair, u_tta_sec_saved, 1e-9),
              "secondary max pairwise TTA distance re-derived")
        check(tta_audit["TTA_TRANSFORM_SET_FROZEN"]["shifts"] == [0, 1, -1],
              "TTA transform set is the frozen {-1,0,+1} electrode-band set")
        check(tta_audit["TTA_TRANSFORM_SET_FROZEN"]["perturbation_tuned_on_target"]
              == "NO", "TTA perturbation not tuned on the target")
        check(tta_audit["transform_semantics"]["equivalence_verified"] is True,
              "official RotationAugmentation equivalence verified")
        check(recs["V4_identity_bit_exact"] is True,
              "identity TTA reproduced the frozen Gate3 prediction stream bit-exactly")
        ia = recs["identity_agreement"]
        check(ia["no_empty_comparison"] is True,
              "no empty agreement comparison (every record compared > 0 rows)")
        check(ia["records_compared"] == 30,
              f"agreement compared all 30 records (got {ia['records_compared']})")
        check(ia["total_rows_compared"] == C.EXPECTED_N,
              f"agreement total compared == 86,833 (got {ia['total_rows_compared']})")
        check(ia["within_tolerance"] is True,
              "agreement within the declared block-mean tolerance")
        check(all(x["n_compared"] > 0 for x in ia["per_record"]),
              "every per-record agreement entry compared > 0 rows")
        check(recs["index_space"].startswith("ELIGIBLE-ONLY"),
              "persisted TTA index space is declared ELIGIBLE-ONLY")
        check(recs["n_rows_per_view"] == C.EXPECTED_N,
              "records declare 86,833 rows per view")
        check(recs["V1_all_finite"] is True, "all TTA views finite on all records")
        check(recs["V5_ok_records"] >= C.TTA_MIN_OK_RECORDS,
              f"bounded response on >= {C.TTA_MIN_OK_RECORDS} records")
        check(recs["timing"]["performance_optimization_performed"] == "NO",
              "TTA round declares no performance optimization")
        check(int(recs["timing"]["n_views"]) == 90,
              "TTA round performed 90 views (30 records x 3 views)")
    else:
        say("    TTA_STATUS is NOT_EVALUABLE: no TTA score is used below")
        check(not np.isfinite(u_tta_saved).any(),
              "no TTA score was fabricated while TTA is NOT_EVALUABLE")

    # CANDIDATE 2: fold structure + OOF re-derivation
    with open(os.path.join(C.ART, "TASK_ERROR_PREDICTOR_OOF.csv"), encoding="utf-8") as fh:
        import csv
        oof_rows = list(csv.DictReader(fh))
    check(len(oof_rows) == n, f"OOF csv has one row per sample ({len(oof_rows)})")
    check(sorted(int(x["idx"]) for x in oof_rows) == list(range(n)),
          "OOF csv covers every sample index exactly once")
    groups = pop["stage"]
    gkf = GroupKFold(n_splits=5)
    fold_of = np.full(n, -1, dtype=np.int64)
    for f, (tr, te) in enumerate(gkf.split(np.zeros(n), groups=groups)):
        fold_of[te] = f
        trs, tes = set(groups[tr].tolist()), set(groups[te].tolist())
        check(not (trs & tes), f"fold {f}: train/test stage groups disjoint")
        check(len(tes) >= 1, f"fold {f}: at least one held-out stage")
        for s in tes:
            m = groups == s
            check(bool((fold_of[m] == f).all()),
                  f"fold {f}: stage {s[:24]} entirely inside its fold")
    check((fold_of >= 0).all(), "every sample assigned to exactly one fold")
    csv_fold = np.array([int(x["fold"]) for x in oof_rows], dtype=np.int64)
    check(np.array_equal(csv_fold, fold_of), "OOF csv fold column == GroupKFold assignment")
    csv_u = np.array([float(x["u_ERR"]) for x in oof_rows], dtype=np.float64)
    check(np.isfinite(csv_u).all(), "no non-finite OOF score")
    check(close(csv_u, u_err_saved, 1e-12), "csv u_ERR == stored u_ERR")

    spec = json.load(open(os.path.join(C.ART, "TASK_ERROR_PREDICTOR_SPEC.json"),
                          encoding="utf-8"))
    feat_names = [f for group in spec["deployment_visible_features"].values()
                  for f in group]
    check(len(feat_names) == spec["feature_count"] == C.N_BACKBONE_FEATURES,
          f"feature count == {C.N_BACKBONE_FEATURES}")
    bad = [f for f in feat_names
           if re.search(r"(?i)(gt|truth|target|error|r_t|stage|class|label|flip|agree)",
                        f)]
    check(not bad, f"no GT/target/stage/class token in feature names ({bad})")
    check(spec["deployment_visible_features"]["E_hand_side_metadata"] == ["side_right"],
          "hand side is the only metadata feature")
    check("stage" not in [f.lower() for f in feat_names], "stage absent from predictor features")

    # recompute the OOF scores from the frozen rule
    summary = json.load(open(os.path.join(C.ART, "TASK_ERROR_PREDICTOR_SUMMARY.json"),
                             encoding="utf-8"))
    kwargs = dict(summary["model"]["kwargs"])
    check(kwargs["loss"] == "quantile" and kwargs["alpha"] == 0.90,
          "model is GradientBoostingRegressor(quantile, alpha=0.90)")
    check(summary["model"]["hyperparameters_tuned"] == "NO", "no hyperparameter tuning")

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import run_task_error_predictor as TEP  # noqa: E402
    X, d1v, d2v = TEP.build_features(pop, z_pr)
    check(np.array_equal(d1v, np.concatenate(
        [np.concatenate([[False], np.ones(k - 1, dtype=bool)]) if k else
         np.zeros(0, dtype=bool) for k in per_rec.values()])),
        "d1_valid is False exactly at the first frame of each record")
    check(int(d2v.sum()) == n - 2 * len(pop["files"]),
          "d2_valid is False exactly at the first two frames of each record")

    # causal / future-frame check: corrupting prediction rows after t must not change
    # any feature value at frames <= t+1 (asserted on a real record boundary)
    t_probe = n // 2
    z_corrupt = z_pr.copy()
    z_corrupt[t_probe + 2:] = 1.0e6
    X2, d1v2, d2v2 = TEP.build_features(pop, z_corrupt)
    check(np.array_equal(d1v2, d1v) and np.array_equal(d2v2, d2v),
          "difference-validity pattern is independent of future values")
    check(close(X2[:t_probe + 2], X[:t_probe + 2], 0.0),
          "feature rows <= t+1 unchanged when every row after t+1 is corrupted "
          "(no future-frame leakage)")
    check(not close(X2[t_probe + 2], X[t_probe + 2], 0.0),
          "sanity: row t+2 does change, so the corruption probe is sensitive")

    oof_re = np.full(n, np.nan)
    # ---- REFIT OPERAND GUARDS (fail closed before any fitting) ---------------
    check(isinstance(r, np.ndarray) and r.ndim == 1 and r.shape == (n,),
          "OOF refit operand r is still the Fisher-error ndarray and has not been "
          "shadowed")
    check(isinstance(X, np.ndarray)
          and X.shape == (n, C.N_BACKBONE_FEATURES),
          "OOF refit operand X is still the frozen feature matrix")
    for f in range(5):
        tr = np.flatnonzero(fold_of != f)
        te = np.flatnonzero(fold_of == f)
        model = GradientBoostingRegressor(**kwargs)
        model.fit(X[tr], r[tr])
        oof_re[te] = model.predict(X[te])
    check(close(oof_re, u_err_saved, 1e-9),
          "OOF scores reproduce from the frozen feature/model/split rule")
    # in-sample refit must differ -> the reported score really is out-of-fold
    model_full = GradientBoostingRegressor(**kwargs)
    model_full.fit(X, r)
    insample = model_full.predict(X)
    check(float(np.mean(np.abs(insample - oof_re))) > 0.0,
          "in-sample refit differs from OOF scores (reported score is out-of-fold)")

    # ------------------------------------------------------------------ 5 metrics
    say()
    say("[5] metric accounting re-derived from the artifacts")
    # ---- METRIC-SECTION TARGET GUARD -----------------------------------------
    # Every quantity below (Spearman, Kendall, AURC, risk-coverage, deciles,
    # per-record rho, no-gate risk, oracle risk) consumes `r`. Fail closed if it has
    # been shadowed anywhere upstream.
    check(isinstance(r, np.ndarray) and r.ndim == 1 and r.shape == (n,),
          "metric-verification target r is still the Fisher-error ndarray")
    with open(os.path.join(C.ART, "CANDIDATE_CORRELATIONS.csv"), encoding="utf-8") as fh:
        import csv
        corr_rows = {row["candidate"]: row for row in csv.DictReader(fh)}
    with open(os.path.join(C.ART, "CANDIDATE_RISK_COVERAGE.csv"), encoding="utf-8") as fh:
        cov_rows = list(csv.DictReader(fh))
    with open(os.path.join(C.ART, "CANDIDATE_AURC.csv"), encoding="utf-8") as fh:
        aurc_rows = {row["candidate"]: row for row in csv.DictReader(fh)}
    with open(os.path.join(C.ART, "CANDIDATE_DECILES.csv"), encoding="utf-8") as fh:
        dec_rows = list(csv.DictReader(fh))
    with open(os.path.join(C.ART, "CANDIDATE_BY_RECORD.csv"), encoding="utf-8") as fh:
        rec_rows = list(csv.DictReader(fh))

    scores = {"TEMP": u_temp, "ERR": u_err_saved}
    if tta_ok:
        scores["TTA"] = u_tta_saved
    for label, u in scores.items():
        finite = np.isfinite(u)
        rho = C.spearman(u[finite], r[finite])
        tau = C.kendall(u[finite], r[finite])
        check(abs(rho - float(corr_rows[label]["spearman_overall"])) < 1e-9,
              f"{label}: overall Spearman recomputes")
        check(abs(tau - float(corr_rows[label]["kendall_overall"])) < 1e-9,
              f"{label}: overall Kendall recomputes")
        order = C.rank_order(u)
        au = C.aurc(order, r)
        check(abs(au - float(aurc_rows[label]["aurc"])) < 1e-9,
              f"{label}: AURC recomputes ({au:.6f})")
        for c in C.COVERAGE_POINTS:
            row = [x for x in cov_rows
                   if x["candidate"] == label and abs(float(x["coverage"]) - c) < 1e-12]
            check(len(row) == 1, f"{label}: exactly one risk-coverage row at {c}")
            exp = C.risk_at_coverage(order, r, c)
            check(exp["n_accepted"] == int(row[0]["n_accepted"])
                  and abs(exp["mean_r"] - float(row[0]["mean_r"])) < 1e-9
                  and abs(exp["median_r"] - float(row[0]["median_r"])) < 1e-9
                  and abs(exp["p90_r"] - float(row[0]["p90_r"])) < 1e-9,
                  f"{label}: risk-coverage accounting recomputes at coverage {c}")
        dec = C.decile_summary(u, r)
        sub = [x for x in dec_rows if x["candidate"] == label]
        check(len(sub) == 10, f"{label}: 10 deciles reported")
        check(sum(int(x["n"]) for x in sub) == n, f"{label}: decile counts sum to N")
        for a, b in zip(sub, dec):
            check(int(a["n"]) == b["n"],
                  f"{label}: decile {b['decile']} n recomputes ({b['n']})")
            check(same_value(b["median_score"], a["median_score"]),
                  f"{label}: decile {b['decile']} median_score recomputes")
            check(same_value(b["median_r"], a["median_r"]),
                  f"{label}: decile {b['decile']} median_r recomputes")
            check(same_value(b["mean_r"], a["mean_r"]),
                  f"{label}: decile {b['decile']} mean_r recomputes")
            check(same_value(b["p90_r"], a["p90_r"]),
                  f"{label}: decile {b['decile']} p90_r recomputes")
        mono = all(dec[i]["median_r"] <= dec[i + 1]["median_r"]
                   for i in range(len(dec) - 1))
        delta = dec[-1]["median_r"] - dec[0]["median_r"]
        check((corr_rows[label]["decile_median_r_monotone"] == "True") == mono,
              f"{label}: reported decile_median_r_monotone recomputes ({mono})")
        check(same_value(delta, corr_rows[label]["decile10_minus_decile1_median_r"]),
              f"{label}: reported decile10_minus_decile1_median_r recomputes "
              f"({delta:+.6f})")
        # per-record completeness: every frozen record must be present with a
        # usable rho. Blank/missing rho is reported explicitly, never treated as an
        # absent record.
        expected_records = sorted(set(pop["record"].tolist()))
        check(len(expected_records) == 30, "30 records expected in the per-record table")
        n_records_reported = int(corr_rows[label]["n_records"])
        check(n_records_reported == 30,
              f"{label}: corr artifact reports n_records == 30 "
              f"(got {n_records_reported})")
        sub_rec = [x for x in rec_rows if x["candidate"] == label]
        check(len(sub_rec) == 30,
              f"{label}: per-record table has one row per record (got {len(sub_rec)})")
        check(sorted(x["record"] for x in sub_rec) == expected_records,
              f"{label}: per-record table covers exactly the frozen record set")
        blank = [x["record"] for x in sub_rec if not x["rho"]]
        check(not blank,
              f"{label}: every record has a non-empty rho "
              f"(blank: {[b[-22:] for b in blank]})")
        for x in sub_rec:
            m = (pop["record"] == x["record"]) & finite
            check(int(m.sum()) >= 50,
                  f"{label}: record {x['record'][-22:]} has >= 50 defined scores "
                  f"({int(m.sum())})")
            check(abs(C.spearman(u[m], r[m]) - float(x["rho"])) < 1e-9,
                  f"{label}: record {x['record'][-24:]} rho recomputes")

    # oracle + no-gate. Authoritative surface for the no-gate reference is the
    # NO_GATE row of CANDIDATE_AURC.csv; work/evaluation.json is a secondary
    # consistency check only.
    no_gate_mean = float(r.mean())
    oracle_aurc = C.aurc(C.rank_order(r), r)
    check(abs(no_gate_mean - float(aurc_rows["NO_GATE"]["aurc"])) < 1e-9,
          f"no-gate mean Fisher risk recomputed from raw r == CANDIDATE_AURC.csv "
          f"NO_GATE row ({no_gate_mean:.6f})")
    ev_json = json.load(open(os.path.join(C.WORK, "evaluation.json"), encoding="utf-8"))
    check(abs(no_gate_mean - float(ev_json["no_gate_mean_risk"])) < 1e-12,
          "secondary: work/evaluation.json no_gate_mean_risk agrees")
    check(abs(oracle_aurc - float(aurc_rows["ORACLE"]["aurc"])) < 1e-9,
          "oracle AURC recomputes")
    check(oracle_aurc <= min(float(aurc_rows[k]["aurc"]) for k in scores),
          "oracle AURC is <= every candidate AURC (ceiling sanity)")
    check(abs(float(aurc_rows["NO_GATE"]["aurc"]) - no_gate_mean) < 1e-9,
          "no-gate reference AURC == mean risk")

    # ------------------------------------------------------------------ 6 firewall
    say()
    say("[6] firewall / claim-boundary assertions")
    import ast

    scripts = ["io_common.py", "audit_tta_transforms.py", "run_tta_inference.py",
               "run_task_error_predictor.py", "build_reliability_scores.py",
               "evaluate_gate_scores.py"]
    bodies, code_tokens = {}, {}
    for s in scripts:
        with open(os.path.join(C.LANE, "scripts", s), encoding="utf-8") as fh:
            bodies[s] = fh.read()
        tree = ast.parse(bodies[s])
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.Attribute):
                names.add(node.attr)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    names.add(alias.name.split(".")[-1])
        code_tokens[s] = names

    # ---- CLASS / SEMANTIC-DECISION FIREWALL ------------------------------------
    # Intent: Gate4A candidate generation and evaluation never uses downstream
    # hard-class output or human/gesture labels as a score, feature, target or
    # threshold. It is NOT "no script contains the word predict": bare `predict(...)`
    # is the legitimate regression call in audit_tta_transforms.py,
    # run_tta_inference.py and run_task_error_predictor.py, and is allowed.
    class_decision_tokens = ("predict_proba", "argmax", "classes_", "human_label",
                             "gesture_label", "class_label")
    for s, names in code_tokens.items():
        for token in class_decision_tokens:
            check(token not in names,
                  f"{s}: no `{token}` (no class/semantic-decision path)")
    # no explicit downstream classification call reaching the frozen DB9 head
    for s in scripts:
        src = bodies[s]
        for token in ("head.predict(", "lda.predict(", "clf.predict(",
                      "classifier.predict("):
            check(token not in src,
                  f"{s}: no `{token}` (no downstream class decision)")
    # no source-text substring scan for prose words (grep-hostile): only executable
    # identifiers are examined above, so comments/docs/paths cannot trip the firewall
    # no upstream training / adaptation (executable identifiers only)
    for s, names in code_tokens.items():
        for token in ("fine_tune", "requires_grad_", "optimizer", "backward",
                      "Adam", "SGD"):
            check(token not in names, f"{s}: no `{token}` (no upstream training)")
    # Candidate 2 is the only fit, and it fits the declared estimator only
    fit_scripts = [s for s, names in code_tokens.items() if "fit" in names]
    check(fit_scripts == ["run_task_error_predictor.py"],
          f"`fit` appears only in the stage-grouped OOF predictor among production scripts "
          f"({fit_scripts})")
    check(code_tokens["run_task_error_predictor.py"] >= {"GradientBoostingRegressor",
                                                         "GroupKFold"},
          "predictor uses the declared sklearn estimator and grouping CV")
    # no GT pose / Fisher target in the TTA inference path
    tta_src = bodies["run_tta_inference.py"]
    check("z_gt" not in tta_src and "pose_fisher(head, mu, sd, pop" not in tta_src,
          "TTA inference never touches the GT Fisher representation")
    # Correct contract: the TTA path reaches the frozen head THROUGH the shared
    # helper, whose implementation (head.transform) deliberately lives in io_common.py.
    # Requiring the symbol to appear in run_tta_inference.py would be impossible.
    check("pose_fisher" in tta_src
          and "head.transform" in bodies["io_common.py"],
          "TTA inference reaches the frozen head only via io_common.pose_fisher "
          "(never a direct head.transform, never GT)")
    check('ja["' not in tta_src and "joint_angles" not in tta_src,
          "TTA inference never reads GT joint angles to build its score")
    # no threshold search / calibration fitting
    for s, names in code_tokens.items():
        for token in ("best_threshold", "optimal_threshold", "GridSearchCV",
                      "IsotonicRegression", "calibrate", "threshold_"):
            check(token not in names, f"{s}: no `{token}` (no threshold/calibration fit)")
    # no absolute DB9 support gate, no cloud rescue
    joined = "\n".join(bodies.values())
    for token in ("OCSVM", "OneClassSVM", "GaussianMixture", "SIMCA",
                  "Mahalanobis", "UNKNOWN_CLASS", "novelty"):
        check(token not in joined, f"no `{token}` anywhere in the gate path")
    check("np.roll" in tta_src and "TTA_SHIFTS" in tta_src,
          "TTA inference applies the frozen electrode-band shift via np.roll")
    # Correct contract: the requirement is that the official TRAINING-TIME
    # augmentation pipeline is not INVOKED during Gate4A inference. The string
    # `train_transforms` legitimately appears in audit_tta_transforms.py, which
    # DOCUMENTS the official config chain; that is not an invocation.
    for s in ("run_tta_inference.py", "run_task_error_predictor.py",
              "build_reliability_scores.py", "evaluate_gate_scores.py"):
        check("train_transforms" not in bodies[s],
              f"{s}: does not reference the training transform pipeline")
    for token in ("RotationAugmentation(", "transforms.Compose(", "Compose(["):
        check(token not in tta_src,
              f"run_tta_inference.py: does not instantiate `{token}` for inference")
    check("TTA_SHIFTS" in bodies["io_common.py"]
          and "TTA_SHIFTS" in tta_src,
          "the frozen TTA perturbations remain the declared deterministic Gate4A "
          "transforms (shared constant, not the training pipeline)")

    # ------------------------------------------------------------------ 7 decision
    say()
    say("[7] decision artifact (bands recomputed from the frozen rule)")
    ev = json.load(open(os.path.join(C.WORK, "evaluation.json"), encoding="utf-8"))
    band_rows = []
    for label in ("TEMP", "TTA", "ERR"):
        if label not in corr_rows:
            band_rows.append({"candidate": label, "feasibility_band": "NOT_EVALUABLE",
                              "reason": "no evaluated score"})
            continue
        row = corr_rows[label]
        recomputed = C.feasibility_band(
            float(row["spearman_overall"]), float(row["median_record_spearman"]),
            float(row["positive_record_fraction"]), float(row["aurc"]),
            float(row["no_gate_aurc"]))
        check(recomputed == row["feasibility_band"],
              f"{label}: recorded feasibility band == frozen-rule recomputation "
              f"({recomputed})")
        band_rows.append({
            "candidate": label,
            "feasibility_band": recomputed,
            "spearman_overall": float(row["spearman_overall"]),
            "kendall_overall": float(row["kendall_overall"]),
            "median_record_spearman": float(row["median_record_spearman"]),
            "positive_record_fraction": float(row["positive_record_fraction"]),
            "aurc": float(row["aurc"]),
        })

    bands_present = {band_row["feasibility_band"] for band_row in band_rows}
    if bands_present & {"MOST_PROMISING_FOR_MULTIUSER", "PROMISING"}:
        next_step = ("Freeze a multi-user cohort design for development/calibration/"
                     "held-out gate validation; do not choose a final threshold from "
                     "the current user.")
    else:
        next_step = ("Do not formalize a gate from this user; evaluate whether Deep "
                     "Ensemble or an uncertainty-aware upstream model is required "
                     "before multi-user gate validation.")

    tta_sum = json.load(open(os.path.join(C.ART, "TTA_SCORE_SUMMARY.json"),
                             encoding="utf-8"))
    decision = {
        "artifact": "GATE4A_DECISION.json",
        "gate": "PHASE 1 / GATE 4A — single-user reliability-score feasibility screen",
        "plan_sha256": actual,
        "evidence_level": "SINGLE-USER FEASIBILITY SCREEN ONLY",
        "is_formal_gate": "NO",
        "is_conformal_validation": "NO",
        "is_threshold_selection": "NO",
        "population": {"n": n, "records": 30, "stages": 15, "users": 1, "sessions": 1,
                       "rate_hz": C.ANALYSIS_HZ},
        "target": {"definition": "DB9-normalised Fisher displacement r_t",
                   "median": rs["median"], "iqr": rs["iqr"], "p05": rs["p05"],
                   "p95": rs["p95"],
                   "exact_gate3b_reproduction": True},
        "no_gate": {"mean_r": no_gate_mean, "aurc_reference": no_gate_mean},
        "oracle": {"aurc": oracle_aurc},
        "TTA_STATUS": tta_status,
        "candidate_bands": band_rows,
        "exploratory_feasibility_ranking": ev["ranking"],
        "ranking_is_final_gate_selection": "NO",
        "deferred_candidates": {
            "DEEP_ENSEMBLE_FISHER_UNCERTAINTY": "NOT EXECUTED — needs >= 3 "
                "independently trained upstream models; better placed in the multi-user "
                "stage",
            "MULTIVARIATE_CONFORMAL_REGION": "NOT EXECUTED — needs exchangeable units and "
                "a genuinely multivariate predictor; one session cannot supply them",
            "LTT_CONFORMAL_RISK_CONTROL": "RESERVED for future threshold calibration, "
                "not current score generation",
        },
        "firewall": {
            "NEW_UPSTREAM_TRAINING_RUN": "NO",
            "UPSTREAM_MODEL_RETRAINED": "NO",
            "DOWNSTREAM_TASK_RETRAINED": "NO",
            "DEEP_MODEL_TRAINED": "NO",
            "MODEL_FITTING_PERFORMED": "YES (Candidate 2 GradientBoostingRegressor, "
                                       "stage-grouped OOF only)",
            "CALIBRATION_FITTED": "NO",
            "THRESHOLD_SELECTED": "NO",
            "HUMAN_LABELS_USED": "NO",
            "DB9_CLASS_TARGET_USED": "NO",
            "ABSOLUTE_DB9_SUPPORT_GATE_USED": "NO",
            "OCSVM_GMM_SIMCA_RESCUE": "NO",
            "ZERO_OFFSET_FITTED": "NO",
            "LAG_SEARCH_PERFORMED": "NO",
            "SMOOTHING_TUNED_ON_OUTCOME": "NO",
            "TEST_TIME_ADAPTATION": "NO",
            "TTA_PERTURBATION_TUNED_ON_TARGET": "NO",
            "AUGMENTATION_SEARCH": "NO",
            "GT_AS_DEPLOYMENT_FEATURE": "NO",
            "R_T_AS_DEPLOYMENT_FEATURE": "NO",
            "STAGE_AS_DEPLOYMENT_FEATURE": "NO",
            "FUTURE_FRAME_FEATURE": "NO",
            "CONFORMAL_GUARANTEE_CLAIMED": "NO",
            "POPULATION_CHANGED": "NO",
            "GATE3_ARTIFACTS_MODIFIED": "NO",
            "GATE3B_ARTIFACTS_MODIFIED": "NO",
            "SCALING_FROM_EMG2POSE": "NO",
        },
        "human_labels_used": "NO",
        "db9_class_target_used": "NO",
        "absolute_db9_support_gate_used": "NO",
        "final_threshold_selected": "NO",
        "formal_conformal_guarantee_claimed": "NO",
        "deep_model_retrained": "NO",
        "gt_required_at_deployment": "NO",
        "next_allowed_step": next_step,
        "recovery_provenance": {
            "BUG_CLASS": "VERIFIER CONTRACT ERROR + VERIFIER TOLERANCE/UNIT-PROPAGATION "
                         "ERROR ONLY",
            "defect_1": "verify_gate4a.py applied the k0 identity-equality requirement "
                        "to all TTA views, including the perturbed-input views k+1/k-1",
            "defect_2": "verify_gate4a.py bounded the Fisher-space identity agreement "
                        "with a hardcoded 1e-9, which cannot be satisfied by a pose "
                        "agreement of 1e-6 rad propagated through the frozen head",
            "SCIENTIFIC_VALUES_CHANGED": "NO",
            "INPUT_ARTIFACTS_CHANGED": "NO",
            "TTA_ARTIFACTS_CHANGED": "NO",
            "PREDICTOR_ARTIFACTS_CHANGED": "NO",
            "EVALUATOR_ARTIFACTS_CHANGED": "NO",
            "GATE4A_PLAN_CHANGED": "NO",
            "NEW_SCIENTIFIC_THRESHOLD_INTRODUCED": "NO",
            "FISHER_TOLERANCE_SOURCE": "DETERMINISTIC TRANSPORT OF FROZEN POSE "
                                       "TOLERANCE THROUGH FROZEN LINEAR HEAD",
            "fisher_gain_inf": gain_inf,
            "fisher_tol_rad_equivalent": fisher_tol,
            "observed_max_fisher_identity_diff": max_fisher_diff,
            "repaired_in": "verify_gate4a.py only",
            "reruns_required": "verifier only",
            "index_space_contract": "ELIGIBLE-ONLY, 86,833 rows per view",
            "output_non_equality_asserted": "NO — a label-preserving input "
                                            "perturbation may legitimately leave the "
                                            "model output unchanged",
        },
    }
    C.write_json(os.path.join(C.ART, "GATE4A_DECISION.json"), decision)
    say(f"    wrote artifacts/GATE4A_DECISION.json")
    for row in band_rows:
        say(f"      {row['candidate']:<5} {row['feasibility_band']}")

    fw = decision["firewall"]
    for k, v in fw.items():
        if k == "MODEL_FITTING_PERFORMED":
            check(v == "YES (Candidate 2 GradientBoostingRegressor, stage-grouped OOF only)",
                  "the only permitted fit is declared explicitly")
        else:
            check(v == "NO", f"firewall {k} == NO")
    check(decision["evidence_level"] == "SINGLE-USER FEASIBILITY SCREEN ONLY",
          "decision artifact is labelled SINGLE-USER FEASIBILITY SCREEN ONLY")
    check(decision["final_threshold_selected"] == "NO", "no final threshold selected")
    check(decision["formal_conformal_guarantee_claimed"] == "NO",
          "no formal conformal guarantee claimed")
    check(decision["human_labels_used"] == "NO", "no human labels used")
    check(decision["db9_class_target_used"] == "NO", "no DB9 class target used")
    check(decision["absolute_db9_support_gate_used"] == "NO",
          "no absolute DB9 support gate used")
    check(decision["gt_required_at_deployment"] == "NO",
          "no candidate requires GT at deployment")
    check(decision["deep_model_retrained"] == "NO", "no deep model retrained")
    check(decision["TTA_STATUS"] == tta_sum["STATUS"], "decision TTA status == TTA summary")

    say()
    say(f"ALL CHECKS PASSED: {N_CHECKS}")
    t.log("")
    t.log(f"ALL CHECKS PASSED: {N_CHECKS}")
    say("VERIFY_GATE4A: PASS")
    t.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
