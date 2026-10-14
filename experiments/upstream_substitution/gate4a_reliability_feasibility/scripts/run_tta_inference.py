#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GATE 4A — TTA inference over the FROZEN transform set.

Implements GATE4A_PLAN.md §4.2 / §7 for the prediction side only.

  EMG -> official regression_vemg2pose -> Pred_pose^(k) -> trusted-8 -> frozen DB9
  Fisher transform -> z_t^(k),  for k in {0, +1, -1}

Frozen weights, no training, no fine-tuning, no test-time adaptation, no
smoothing, no calibration, no GT used, no target compared to anything.

Identity view (k=0) must reproduce the frozen Gate3 predicted stream
BIT-EXACTLY, otherwise this script fails loudly.

Run:
  /root/miniconda3/envs/emg2pose-gate3/bin/python -X utf8 scripts/run_tta_inference.py
"""
from __future__ import annotations

import os
import sys
import time

import h5py
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import io_common as C  # noqa: E402

sys.path.insert(0, C.EMG_REPO)
sys.path.insert(0, "/root/work/emg2pose_inference")

from predict_pose import PredictPose  # noqa: E402


def main() -> int:
    C.ensure_dirs()
    t = C.Tee(os.path.join(C.LOGS, "tta_inference_stdout.txt"))
    C.banner(t, "GATE 4A — TTA INFERENCE (frozen weights, EMG only)")

    ck_sha = C.sha256_file(C.CKPT)
    assert ck_sha == "748b1d1ef0ce1985f6fc07225d97eebfb370243429af803b4997d28ecce2424e", \
        "checkpoint identity changed -> STOP"
    t.log(f"checkpoint sha256 : {ck_sha}")
    t.log(f"TTA shifts        : {list(C.TTA_SHIFTS)}")
    t.log(f"GT read           : NO")
    t.log(f"target compared   : NO")
    t.log()

    model = PredictPose(experiment="regression_vemg2pose", checkpoint=C.CKPT,
                        repo_root=C.EMG_REPO, device="cuda")
    desc = model.describe()
    t.log(f"estimator         : {desc['experiment']}  left_context={desc['left_context']}"
          f"  right_context={desc['right_context']}"
          f"  provide_initial_pos={desc['provide_initial_pos']}")
    t.log()

    files = C.record_files()
    assert len(files) == C.EXPECTED_RECORDS, len(files)

    # Frozen eligibility (verbatim Gate3/Gate3B rule) via the shared rebuild.
    pop = C.build_population(require_expected=True)
    assert len(pop["files"]) == len(files)
    # ELIGIBLE-ONLY index-space contract, established once and used everywhere below:
    #   pop["block_idx"] is the LOCAL 0-based block position inside its own record.
    #   block_parts[r]  are record r's local eligible block positions.
    #   z_views[*]      hold ONLY those eligible rows, concatenated in pop["files"] order.
    rec_start, rec_len = C.record_offsets(pop)
    assert int(rec_len.sum()) == pop["n"] == C.EXPECTED_N, \
        (int(rec_len.sum()), pop["n"], C.EXPECTED_N)
    assert (rec_len > 0).all(), "a record contributed zero eligible samples"
    block_parts = np.split(pop["block_idx"], np.cumsum(rec_len)[:-1])
    assert len(block_parts) == len(pop["files"]) == len(files)
    assert int(np.concatenate(block_parts).shape[0]) == C.EXPECTED_N
    assert np.array_equal(
        np.concatenate(block_parts), pop["block_idx"]), "block partition mismatch"
    t.log(f"    eligible-only contract: {int(rec_len.sum())} rows across "
          f"{len(rec_len)} records; block partition verified")
    bounds = {}
    cursor = 0
    for f, stem in zip(files, [os.path.basename(x)[: -len(".hdf5")] for x in files]):
        k = int((pop["record"] == stem).sum())
        if k:
            bounds[stem] = (cursor, cursor + k)
            cursor += k
    assert cursor == pop["n"]

    z_views: dict[str, list[np.ndarray]] = {name: [] for name in C.TTA_VIEW_NAMES}
    per_record = []
    total_t = 0.0

    # ---------------- timing instrumentation (documentation only) --------------
    # time.perf_counter brackets around the existing work. Nothing about the
    # computation is changed: no batching, no parallelism, no caching, no h5py
    # behaviour change, no CUDA/cuDNN/AMP settings.
    T_WALL0 = time.perf_counter()
    tm = {"h5_read": 0.0, "feat_load": 0.0, "transform": 0.0, "forward": 0.0,
          "reduce": 0.0, "check": 0.0, "write_view": 0.0, "write_pack": 0.0}

    for i, f in enumerate(files, 1):
        stem = os.path.basename(f)[: -len(".hdf5")]
        t_a = time.perf_counter()
        with h5py.File(f, "r") as h:
            g = h["emg2pose"]
            attrs = dict(g.attrs)
            emg = np.asarray(g["timeseries"]["emg"][:])
        tm["h5_read"] += time.perf_counter() - t_a

        t_a = time.perf_counter()
        with np.load(os.path.join(C.PRED_DIR, f"{stem}_pred.npz")) as z:
            ang_frozen = np.asarray(z["angles"])
            t_frozen = np.asarray(z["time"])
            off = int(z["row_offset"])
        tm["feat_load"] += time.perf_counter() - t_a

        nb = (ang_frozen.shape[0] // C.POSE_STRIDE) * C.POSE_STRIDE
        rec = {"record": stem, "side": str(attrs["side"]),
               "stage": str(attrs["stage"]), "T_2khz": int(emg.shape[0]),
               "blocks": int(nb // C.POSE_STRIDE),
               "eligible_blocks": int(bounds[stem][1] - bounds[stem][0]),
               "timing_seconds": {}}

        preds_this = {}
        for name, k in zip(C.TTA_VIEW_NAMES, C.TTA_SHIFTS):
            t_a = time.perf_counter()
            emg_in = emg if k == 0 else np.roll(emg, int(k), axis=1)
            tm["transform"] += time.perf_counter() - t_a

            t0 = time.perf_counter()
            pred = np.asarray(model.predict(emg_in), dtype=np.float32)
            dt = time.perf_counter() - t0
            tm["forward"] += dt
            total_t += dt

            t_a = time.perf_counter()
            if name == "k0":
                if not np.array_equal(pred, ang_frozen):
                    raise AssertionError(
                        f"IDENTITY VIEW MISMATCH on {stem}: identity TTA must reproduce "
                        f"the frozen Gate3 predicted stream bit-exactly "
                        f"(max|diff|={np.abs(pred - ang_frozen).max()})")
                rec["identity_bit_exact"] = True
            rec[f"seconds_{name}"] = float(dt)
            rec[f"finite_{name}"] = bool(np.isfinite(pred).all())
            tm["check"] += time.perf_counter() - t_a

            t_a = time.perf_counter()
            # trusted-8 40-row block means on the FULL prediction grid, reduced in
            # float64 exactly as the frozen Gate3/Gate3B population did it (a float32
            # reduction would perturb the target by ~1e-6).
            #
            # SINGLE EXPLICIT INDEX-SPACE CONTRACT (eligible-only):
            #   every persisted view holds EXACTLY the 86,833 frozen eligible samples,
            #   record r contributing rec_len[r] rows in pop["files"] order, selected
            #   by that record's frozen LOCAL eligible block positions.
            all_blocks = (pred.astype(np.float64)[:nb]
                          .reshape(-1, C.POSE_STRIDE, 20).mean(1)[:, C.TRUSTED8_SRC_IDX])
            eligible_local = block_parts[i - 1]
            assert eligible_local.size == int(rec_len[i - 1]), \
                (stem, int(eligible_local.size), int(rec_len[i - 1]))
            assert eligible_local.size > 0, stem
            assert int(eligible_local.min()) >= 0, (stem, int(eligible_local.min()))
            assert int(eligible_local.max()) < all_blocks.shape[0], \
                (stem, int(eligible_local.max()), int(all_blocks.shape[0]))
            z_views[name].append(all_blocks[eligible_local])
            preds_this[name] = pred
            tm["reduce"] += time.perf_counter() - t_a
            rec["timing_seconds"][name] = {
                "forward": float(dt),
                "reduce": float(time.perf_counter() - t_a),
            }

        # per-record TTA view deviation (frozen V2/V5 bound check)
        t_a = time.perf_counter()
        dev = {}
        base = preds_this["k0"][:, C.TRUSTED8_SRC_IDX]
        for name in ("k+1", "k-1"):
            other = preds_this[name][:, C.TRUSTED8_SRC_IDX]
            d = (other - base) * 180.0 / np.pi
            frame = np.sqrt((d ** 2).mean(1))
            dev[name] = {
                "median_frame_rmse_deg": float(np.median(frame)),
                "p90_frame_rmse_deg": float(np.percentile(frame, 90)),
                "max_abs_delta_deg": float(np.abs(d).max()),
            }
        tm["check"] += time.perf_counter() - t_a
        rec["view_deviation_vs_identity"] = dev
        per_record.append(rec)

        t.log(f"  [{i:>2}/{len(files)}] {stem[-38:]:<38} T={emg.shape[0]:>7} "
              f"blocks={rec['blocks']:>5} eligible={rec['eligible_blocks']:>5} "
              f"k0_exact={rec['identity_bit_exact']} "
              f"dev(k+1) med {dev['k+1']['median_frame_rmse_deg']:.2f} "
              f"dev(k-1) med {dev['k-1']['median_frame_rmse_deg']:.2f}")

    # Addressing for the persisted views: they are ELIGIBLE-ONLY, so record r occupies
    # rows [rec_start[r], rec_start[r]+rec_len[r]) and record r contributed exactly the
    # rows selected by block_parts[r] from its own full-grid block array.
    idx = pop["block_idx"].astype(np.int64)          # local, for provenance only
    tta_idx_provenance = pop["tta_idx"].astype(np.int64)

    # ------------------------------------------------------------------ packs
    t.log()
    t.log("[pack] stacking TTA views (eligible-only)")
    head, mu, sd = C.load_frozen_head()
    sigma = C.load_db9_sigma()

    z_pack = {}
    pose_pack = {}
    for name in C.TTA_VIEW_NAMES:
        pose_blocks = np.vstack(z_views[name]).astype(np.float64)
        assert pose_blocks.shape[0] == C.EXPECTED_N, \
            (name, pose_blocks.shape, C.EXPECTED_N)
        pose_pack[name] = pose_blocks
        z_pack[name] = C.pose_fisher(head, mu, sd, pose_blocks).astype(np.float64)
        t.log(f"    {name:<4} pose_blocks {pose_blocks.shape} "
              f"-> fisher {z_pack[name].shape}")

    n_eligible_rows = idx.size
    t.log(f"    eligible samples : {n_eligible_rows}  (expected {C.EXPECTED_N})")
    assert n_eligible_rows == C.EXPECTED_N, \
        f"population changed: {n_eligible_rows} -> STOP"

    # ------------------------------------------------------------------ agreement
    # Non-vacuous identity-view agreement. The k0 view's full prediction stream was
    # already asserted BIT-EXACT against the frozen Gate3 stream frame by frame in the
    # per-record loop. Here the persisted, eligible-only, block-reduced k0 rows are
    # compared against the frozen Gate3 stream under the SAME reduction, per record,
    # with the compared sample count itself asserted.
    k0_list = z_views["k0"]
    assert len(k0_list) == len(files) == len(pop["files"])
    per_record_agreement = []
    total_compared = 0
    pose_diffs, fisher_diffs = [], []
    for r, stem_path in enumerate(pop["files"]):
        stem = C.record_stem(stem_path)
        assert stem == C.record_stem(files[r]), \
            f"record order mismatch at {r}: {stem} vs {C.record_stem(files[r])}"
        n_r = int(rec_len[r])
        a = int(rec_start[r])
        persisted = k0_list[r]
        # (1) persisted row count for this record
        assert persisted.shape[0] == n_r, (stem, persisted.shape[0], n_r)
        # (2) never an empty comparison
        assert n_r > 0, f"record {stem} contributed zero rows -> STOP"
        # (3) the frozen stream, reduced with identical semantics
        with np.load(os.path.join(C.PRED_DIR, f"{stem}_pred.npz")) as zz:
            ang = np.asarray(zz["angles"], dtype=np.float32)
        nb_r = (ang.shape[0] // C.POSE_STRIDE) * C.POSE_STRIDE
        frozen_all = (ang[:nb_r].astype(np.float64).reshape(-1, C.POSE_STRIDE, 20)
                      .mean(1)[:, C.TRUSTED8_SRC_IDX])
        local = block_parts[r]
        ref = frozen_all[local]
        # (4) compared counts agree and are non-empty
        assert ref.shape[0] == persisted.shape[0] == n_r, \
            (stem, ref.shape[0], persisted.shape[0], n_r)
        assert ref.shape[0] > 0
        d_pose = float(np.abs(persisted - ref).max())
        z_ref = C.pose_fisher(head, mu, sd, ref)
        z_pers = z_pack["k0"][a:a + n_r]
        d_fisher = float(np.abs(z_pers - z_ref).max())
        # (5) record slices concatenate in Gate3/Gate3B population order
        assert np.abs(pop["P"][a:a + n_r] - ref).max() <= C.TTA_BLOCK_MEAN_TOL, stem
        pose_diffs.append(d_pose)
        fisher_diffs.append(d_fisher)
        total_compared += n_r
        per_record_agreement.append({
            "r": r, "record": stem, "n_compared": int(n_r),
            "max_abs_pose_diff": d_pose,
            "max_abs_fisher_diff": d_fisher,
            "within_pose_tolerance": bool(d_pose <= C.TTA_BLOCK_MEAN_TOL),
        })
        if d_pose > C.TTA_BLOCK_MEAN_TOL:
            raise AssertionError(
                f"IDENTITY AGREEMENT FAILURE on {stem}: n={n_r} "
                f"max|pose diff|={d_pose:.6e} > {C.TTA_BLOCK_MEAN_TOL:g} -> STOP")
    # (6) global accounting
    assert total_compared == C.EXPECTED_N, (total_compared, C.EXPECTED_N)
    assert len(per_record_agreement) == len(files) == 30
    assert all(x["n_compared"] > 0 for x in per_record_agreement)
    agree = float(max(pose_diffs))
    agree_fisher = float(max(fisher_diffs))
    t.log(f"    identity agreement: {len(per_record_agreement)}/30 records compared, "
          f"total compared {total_compared} (expected {C.EXPECTED_N}), "
          f"no empty comparison")
    t.log(f"    identity max |pose diff|   = {agree:.3e} rad "
          f"(tolerance {C.TTA_BLOCK_MEAN_TOL:g})")
    t.log(f"    identity max |Fisher diff| = {agree_fisher:.3e}")
    k0_matches_frozen = agree <= C.TTA_BLOCK_MEAN_TOL
    assert k0_matches_frozen, "identity agreement failed -> STOP"
    t.log(f"    k0 eligible rows == frozen Gate3 block means within "
          f"{C.TTA_BLOCK_MEAN_TOL:g} rad: {k0_matches_frozen}")

    # per-view Fisher deviation versus identity, on eligible samples
    view_dev = {}
    z0 = z_pack["k0"]
    for name in ("k+1", "k-1"):
        d = (z_pack[name] - z0) / sigma
        dn = np.sqrt((d ** 2).sum(1))
        view_dev[name] = C.qstats(dn)
        t.log(f"    DB9-normalised Fisher deviation {name} vs k0: "
              f"median {view_dev[name]['median']:.4f} "
              f"p95 {view_dev[name]['p95']:.4f}")

    # ------------------------------------------------------------------ V4/V5
    t.log()
    t.log("[validity] plan §4.3 conditions")
    v4 = all(r["identity_bit_exact"] for r in per_record)
    t.log(f"    V4 identity bit-exact on all 30 records           : {v4}")
    ok_v5 = 0
    for r in per_record:
        good = all(v["median_frame_rmse_deg"] < C.TTA_MAX_MEDIAN_VIEW_DEV_DEG
                   and v["max_abs_delta_deg"] < C.TTA_MAX_ABS_VIEW_DEV_DEG
                   for v in r["view_deviation_vs_identity"].values())
        ok_v5 += int(good)
    t.log(f"    V5 bounded response on {ok_v5}/30 records "
          f"(need >= {C.TTA_MIN_OK_RECORDS})          : "
          f"{ok_v5 >= C.TTA_MIN_OK_RECORDS}")
    v1 = all(r[f"finite_{n}"] for r in per_record for n in C.TTA_VIEW_NAMES)
    t.log(f"    V1 all views finite on all records                : {v1}")

    status = ("EVALUABLE" if (v1 and v4 and ok_v5 >= C.TTA_MIN_OK_RECORDS)
              else "NOT_EVALUABLE")
    t.log(f"    TTA_STATUS = {status}")

    os.makedirs(C.WORK, exist_ok=True)
    t_a = time.perf_counter()
    np.savez_compressed(
        os.path.join(C.WORK, "tta_fisher_views.npz"),
        **{f"z_{name.replace('+', 'p')}": z_pack[name] for name in C.TTA_VIEW_NAMES},
        sigma_db9=sigma,
    )
    tm["write_pack"] += time.perf_counter() - t_a
    for name in C.TTA_VIEW_NAMES:
        assert z_pack[name].shape == (C.EXPECTED_N, 7), (name, z_pack[name].shape)
    t.log(f"wrote work/tta_fisher_views.npz ({C.EXPECTED_N} x 7 x "
          f"{len(C.TTA_VIEW_NAMES)} float64, eligible-only)")
    # trusted-8 pose block means that feed the Fisher transform, kept in float64 so
    # the score can be re-derived independently in the verifier
    t_a = time.perf_counter()
    np.savez_compressed(
        os.path.join(C.WORK, "tta_pose_blocks.npz"),
        **{f"pose_{name.replace('+', 'p')}": pose_pack[name]
           for name in C.TTA_VIEW_NAMES},
        block_idx=idx,
        tta_idx=tta_idx_provenance,
    )
    tm["write_pack"] += time.perf_counter() - t_a
    for name in C.TTA_VIEW_NAMES:
        assert pose_pack[name].shape == (C.EXPECTED_N, 8), (name, pose_pack[name].shape)
    t.log(f"wrote work/tta_pose_blocks.npz (trusted-8 eligible block means, "
          f"{C.EXPECTED_N} x 8 per view); block_idx/tta_idx are provenance only")

    # ------------------------------------------------------------ runtime report
    wall = time.perf_counter() - T_WALL0
    fwd = tm["forward"]
    non_fwd = wall - fwd
    view_secs = np.array([r[f"seconds_{n}"] for r in per_record
                          for n in C.TTA_VIEW_NAMES], dtype=np.float64)
    timing = {
        "instrumentation": "time.perf_counter brackets around existing work; "
                           "no batching, parallelism, caching, h5py, CUDA/cuDNN or AMP "
                           "changes. Documentation only.",
        "performance_optimization_performed": "NO",
        "total_wall_seconds": float(wall),
        "hdf5_read_seconds": float(tm["h5_read"]),
        "frozen_prediction_load_seconds": float(tm["feat_load"]),
        "tta_transform_preprocess_seconds": float(tm["transform"]),
        "model_forward_seconds": float(fwd),
        "block_reduction_seconds": float(tm["reduce"]),
        "identity_and_validity_check_seconds": float(tm["check"]),
        "persistence_write_seconds": float(tm["write_pack"]),
        "non_forward_seconds": float(non_fwd),
        "forward_fraction_of_wall": float(fwd / wall) if wall > 0 else None,
        "n_views": int(view_secs.size),
        "seconds_per_view_mean": float(view_secs.mean()),
        "seconds_per_view_median": float(np.median(view_secs)),
        "seconds_per_view_min": float(view_secs.min()),
        "seconds_per_view_max": float(view_secs.max()),
        "forward_seconds_sum_check": float(view_secs.sum()),
        "accounted_seconds": float(tm["h5_read"] + tm["feat_load"] + tm["transform"]
                                   + fwd + tm["reduce"] + tm["check"]
                                   + tm["write_pack"]),
        "model_loaded_once": True,
        "batch_size": 1,
        "dataloader": "NONE (direct h5py reads)",
    }
    t.log()
    t.log("[timing] runtime breakdown (documentation only)")
    for k in ("total_wall_seconds", "hdf5_read_seconds",
              "frozen_prediction_load_seconds", "tta_transform_preprocess_seconds",
              "model_forward_seconds", "block_reduction_seconds",
              "identity_and_validity_check_seconds", "persistence_write_seconds",
              "non_forward_seconds", "forward_fraction_of_wall",
              "seconds_per_view_mean", "seconds_per_view_median",
              "seconds_per_view_min", "seconds_per_view_max"):
        t.log(f"    {k:<40} {timing[k]}")

    C.write_json(os.path.join(C.WORK, "tta_inference_records.json"), {
        "TTA_STATUS": status,
        "checkpoint_sha256": ck_sha,
        "tta_shifts": list(C.TTA_SHIFTS),
        "view_names": list(C.TTA_VIEW_NAMES),
        "index_space": "ELIGIBLE-ONLY (86,833 rows per view, Gate3/Gate3B population "
                       "order); no all-block rows are persisted",
        "n_eligible": int(n_eligible_rows),
        "n_rows_per_view": int(n_eligible_rows),
        "seconds_total_model_forward": float(total_t),
        "per_record": per_record,
        "view_fisher_deviation_vs_identity": view_dev,
        "V1_all_finite": bool(v1),
        "V4_identity_bit_exact": bool(v4),
        "V5_ok_records": int(ok_v5),
        "identity_agreement": {
            "records_compared": len(per_record_agreement),
            "total_rows_compared": int(total_compared),
            "no_empty_comparison": bool(
                all(x["n_compared"] > 0 for x in per_record_agreement)),
            "max_abs_pose_diff_rad": float(agree),
            "max_abs_fisher_diff": float(agree_fisher),
            "tolerance_rad": float(C.TTA_BLOCK_MEAN_TOL),
            "within_tolerance": bool(k0_matches_frozen),
            "per_record": per_record_agreement,
        },
        "timing": timing,
    })
    t.log()
    t.log("wrote work/tta_fisher_views.npz, work/tta_pose_blocks.npz, "
          "work/tta_inference_records.json  (timing carried in the records)")
    t.log(f"total model-forward seconds: {total_t:.1f}  (wall {wall:.1f}s, "
          f"forward {100.0 * fwd / wall:.1f}%)")
    t.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
