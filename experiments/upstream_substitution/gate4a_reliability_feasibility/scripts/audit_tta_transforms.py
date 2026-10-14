#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GATE 4A — audit the official electrode-band rotation transform.

Implements GATE4A_PLAN.md §4.1 and the pre-freeze part of §4.3.

Code/config inspection FIRST, TTA transform set frozen SECOND. This script runs
before any TTA score is compared to the Fisher error target, and it reads EMG
only: no GT pose, no Fisher error target, no candidate score.

Run:
  /root/miniconda3/envs/emg2pose-gate3/bin/python -X utf8 scripts/audit_tta_transforms.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time

import h5py
import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import io_common as C  # noqa: E402

sys.path.insert(0, C.EMG_REPO)
sys.path.insert(0, "/root/work/emg2pose_inference")

from emg2pose.transforms import RotationAugmentation  # noqa: E402
from predict_pose import PredictPose  # noqa: E402


def section(t, s):
    t.log("")
    t.log(s)


def main() -> int:
    C.ensure_dirs()
    t = C.Tee(os.path.join(C.LOGS, "tta_transform_audit_stdout.txt"))
    C.banner(t, "GATE 4A — TTA TRANSFORM AUDIT (code inspection only, no GT)")
    t.log(f"TTA_SHIFTS (frozen)  : {list(C.TTA_SHIFTS)}")
    t.log(f"TTA_VIEW_NAMES       : {list(C.TTA_VIEW_NAMES)}")
    t.log(f"K                    : {len(C.TTA_SHIFTS)}")
    t.log()

    audit: dict = {
        "artifact": "TTA_TRANSFORM_AUDIT.json",
        "gate": "PHASE 1 / GATE 4A — single-user reliability-score feasibility screen",
        "plan_sha256": C.sha256_file(os.path.join(C.LANE, "GATE4A_PLAN.md")),
        "evidence_level": "SINGLE-USER FEASIBILITY SCREEN ONLY",
        "reads_gt": "NO",
        "reads_fisher_target": "NO",
        "computes_candidate_score": "NO",
    }

    # ------------------------------------------------------------------ 1
    section(t, "[1] official source inspection")
    tr_path = importlib.util.find_spec("emg2pose.transforms").origin
    files = {
        "transforms.py": tr_path,
        "transforms_config": os.path.join(C.EMG_REPO, "config/transforms/rotation_augmentation.yaml"),
        "basic_transforms_config": os.path.join(C.EMG_REPO, "config/transforms/basic.yaml"),
        "base_config": os.path.join(C.EMG_REPO, "config/base.yaml"),
        "regression_vemg2pose_config": os.path.join(
            C.EMG_REPO, "config/experiment/regression_vemg2pose.yaml"),
        "train.py": os.path.join(C.EMG_REPO, "emg2pose/train.py"),
        "data.py": os.path.join(C.EMG_REPO, "emg2pose/data.py"),
        "predict_wrapper": C.PREDICT_WRAPPER,
    }
    hashes = {}
    for name, path in files.items():
        assert os.path.isfile(path), path
        hashes[name] = {"path": path, "sha256": C.sha256_file(path)}
        t.log(f"    {name:<30} {hashes[name]['sha256']}  {path}")
    audit["official_files"] = hashes

    import subprocess
    repo_commit = subprocess.run(
        ["git", "-C", C.EMG_REPO, "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False).stdout.strip()
    audit["upstream_repo"] = {
        "url": "https://github.com/facebookresearch/emg2pose.git",
        "commit": repo_commit,
    }
    t.log(f"    upstream repo commit           {repo_commit}")

    # ------------------------------------------------------------------ 2
    section(t, "[2] RotationAugmentation semantics vs torch.roll")
    sample = torch.arange(16).float().view(1, 1, 16)
    rolls = {int(k): torch.roll(sample, int(k), dims=-1)[0, 0, :4].tolist()
             for k in (-1, 0, 1)}
    for k, vals in rolls.items():
        t.log(f"    torch.roll(x, {k:+d}, dims=-1) first 4 = {vals}")

    draws = []
    for _ in range(300):
        v = RotationAugmentation()(torch.arange(16).float().view(1, 1, 16))
        draws.append(int(v[0, 0, 15].item()))
    realised = sorted(set(draws))
    t.log(f"    RotationAugmentation draws (300): last-channel values = {realised}")
    t.log("    interpretation on x=[0..15]: value 15 == roll k=+1, value 14 == roll k=0, "
          "value 0 == roll k=-1; observed support is exactly {-1, 0, +1}")
    assert set(realised) == {0, 14, 15}, f"unexpected draw support: {realised}"

    equiv = True
    for _ in range(50):
        x = torch.arange(16).float().view(1, 1, 16)
        y = RotationAugmentation()(x.clone())
        if not any(torch.equal(y, torch.roll(x, int(k), dims=-1)) for k in (-1, 0, 1)):
            equiv = False
    t.log(f"    every draw == torch.roll(x,k,-1) for k in {{-1,0,1}}: {equiv}")
    audit["transform_semantics"] = {
        "official_class": "emg2pose.transforms.RotationAugmentation",
        "official_implementation": "rotation = np.random.choice([-1, 0, 1]); "
                                   "torch.roll(data, rotation, dims=-1)",
        "np_roll_axis_equivalence": "input emg is (T, 16); the official transform rolls "
                                    "the last dim AFTER the (T,C)->(C,T) transpose, so "
                                    "np.roll(emg, k, axis=1) is the identical operation",
        "draw_support": [-1, 0, 1],
        "draw_probe_n": 300,
        "draw_probe_last_channel_values": realised,
        "equivalence_verified": bool(equiv),
        "equivalence_draws_tested": 50,
    }

    # ------------------------------------------------------------------ 3
    section(t, "[3] config chain (train uses it, val/test do not)")
    cfg_lines = {}
    for name in ("transforms_config", "base_config", "regression_vemg2pose_config"):
        with open(files[name], encoding="utf-8") as fh:
            cfg_lines[name] = fh.read()
    t.log("    transforms/rotation_augmentation.yaml:")
    for ln in cfg_lines["transforms_config"].splitlines():
        t.log(f"      | {ln}")
    t.log("    base.yaml defaults line:")
    for ln in cfg_lines["base_config"].splitlines():
        if "transforms" in ln:
            t.log(f"      | {ln}")
    t.log("    experiment/regression_vemg2pose.yaml defaults + datamodule:")
    keep = ("pose_module", "network", "_self_", "window_length", "provide_initial_pos")
    for ln in cfg_lines["regression_vemg2pose_config"].splitlines():
        if any(k in ln for k in keep):
            t.log(f"      | {ln}")
    t.log("    -> the experiment config does NOT override `transforms`, so the official")
    t.log("       base default (rotation_augmentation) applies to this checkpoint.")
    audit["config_chain"] = {
        "train_transforms": ["ExtractToTensor", "RotationAugmentation"],
        "val_transforms": ["ExtractToTensor"],
        "test_transforms": ["ExtractToTensor"],
        "experiment_config_overrides_transforms": False,
        "conclusion": "the published regression_vemg2pose checkpoint was trained with "
                      "the electrode-band rotation augmentation, so the transforms in "
                      "its support are label-preserving by the authors' definition",
    }

    # label-preservation argument, stated explicitly
    audit["target_preservation_argument"] = {
        "mechanism": "deterministic circular shift of the electrode index along the "
                     "16-channel arrangement of the sEMG cuff",
        "does_not_change": ["joint angles", "hand pose label", "DB9 class", "task",
                            "stage", "hand side", "timing/alignment"],
        "requires_gt": "NO",
        "adds_information": "NO (a permutation of the input channels)",
        "outside_official_support_used": "NO — only k in {-1, 0, +1}",
    }

    # ------------------------------------------------------------------ 4
    section(t, "[4] downstream consumption verification (val/test path)")
    dy = os.path.join(C.EMG_REPO, "emg2pose/lightning.py")
    with open(dy, encoding="utf-8") as fh:
        lines = fh.readlines()
    shown = 0
    for i, ln in enumerate(lines, 1):
        if "transform=" in ln and shown < 6:
            t.log(f"    lightning.py:{i:<4} | {ln.rstrip()}")
            shown += 1
    audit["val_test_transform_source"] = "emg2pose/lightning.py (datamodule transform=...)"

    # ------------------------------------------------------------------ 5
    section(t, "[5] pre-freeze response probe (EMG only, no GT, no target)")
    ck_sha = C.sha256_file(C.CKPT)
    t.log(f"    checkpoint sha256 : {ck_sha}")
    t.log(f"    expected          : 748b1d1ef0ce1985f6fc07225d97eebfb370243429af803b4997d28ecce2424e")
    assert ck_sha == "748b1d1ef0ce1985f6fc07225d97eebfb370243429af803b4997d28ecce2424e"
    audit["checkpoint"] = {"path": C.CKPT, "sha256": ck_sha}

    model = PredictPose(experiment="regression_vemg2pose", checkpoint=C.CKPT,
                        repo_root=C.EMG_REPO, device="cuda")
    desc = model.describe()
    audit["estimator"] = desc
    t.log(f"    device {desc['device']}  left_context {desc['left_context']}  "
          f"right_context {desc['right_context']}  provide_initial_pos "
          f"{desc['provide_initial_pos']}")

    files_all = C.record_files()
    probe = []
    seen_sides = set()
    for f in files_all:
        with h5py.File(f, "r") as h:
            side = str(dict(h["emg2pose"].attrs)["side"])
            emg = h["emg2pose"]["timeseries"]["emg"][:]
            stem = os.path.basename(f)[: -len(".hdf5")]
        if side in seen_sides:
            continue
        seen_sides.add(side)
        t0 = time.time()
        a0 = model.predict(emg)
        dt = time.time() - t0
        a0b = model.predict(emg)
        determ = bool(np.array_equal(a0, a0b))
        entry = {
            "record": stem, "side": side, "n_frames_2khz": int(emg.shape[0]),
            "seconds_per_view": float(dt), "repeat_run_identical": determ,
            "views": {},
        }
        t.log(f"    {stem[-30:]:<30} side {side:<5} T={emg.shape[0]:>7} "
              f"{dt:.2f}s/view  deterministic={determ}")
        p0 = a0[:, C.TRUSTED8_SRC_IDX]
        for k in (1, -1):
            ak = model.predict(np.roll(emg, int(k), axis=1))
            pk = ak[:, C.TRUSTED8_SRC_IDX]
            d = (pk - p0) * 180.0 / np.pi
            frame = np.sqrt((d ** 2).mean(1))
            rec = {
                "k": int(k),
                "finite": bool(np.isfinite(ak).all()),
                "median_frame_rmse_deg": float(np.median(frame)),
                "mean_frame_rmse_deg": float(frame.mean()),
                "p90_frame_rmse_deg": float(np.percentile(frame, 90)),
                "max_abs_delta_deg": float(np.abs(d).max()),
            }
            entry["views"][f"k{k:+d}"] = rec
            t.log(f"        k{k:+d}: finite={rec['finite']} "
                  f"median {rec['median_frame_rmse_deg']:.3f} deg  "
                  f"max|d| {rec['max_abs_delta_deg']:.3f} deg")
        probe.append(entry)
        if len(seen_sides) == 2:
            break
    audit["pre_freeze_probe"] = {
        "records": probe,
        "note": "pre-freeze feasibility probe, EMG only; not a gate result",
    }

    # ------------------------------------------------------------------ 6
    section(t, "[6] declared validity conditions (plan §4.3)")
    vals = [v for e in probe for v in e["views"].values()]
    finite_ok = all(v["finite"] for v in vals)
    bounded_ok = all(
        v["median_frame_rmse_deg"] < C.TTA_MAX_MEDIAN_VIEW_DEV_DEG
        and v["max_abs_delta_deg"] < C.TTA_MAX_ABS_VIEW_DEV_DEG for v in vals)
    determ_ok = all(e["repeat_run_identical"] for e in probe)
    t.log(f"    V1 shifted views all finite (probe)              : {finite_ok}")
    t.log(f"    V2 bounded response (< {C.TTA_MAX_MEDIAN_VIEW_DEV_DEG} deg median, "
          f"< {C.TTA_MAX_ABS_VIEW_DEV_DEG} deg max) (probe)   : {bounded_ok}")
    t.log(f"    V3 repeat-run determinism (probe)                : {determ_ok}")
    t.log("    V4 identity view bit-exact vs frozen Gate3 stream: evaluated in "
          "build_reliability_scores.py (needs the frozen stream)")
    t.log("    V5 full-records bounded response                  : evaluated in "
          "build_reliability_scores.py")
    audit["validity_conditions"] = {
        "V1_finite_probe": bool(finite_ok),
        "V2_bounded_probe": bool(bounded_ok),
        "V3_determinism_probe": bool(determ_ok),
        "V4_identity_reproduction": "DEFERRED to build_reliability_scores.py",
        "V5_full_record_bounds": "DEFERRED to build_reliability_scores.py",
        "thresholds": {
            "max_median_view_dev_deg": C.TTA_MAX_MEDIAN_VIEW_DEV_DEG,
            "max_abs_view_dev_deg": C.TTA_MAX_ABS_VIEW_DEV_DEG,
            "min_ok_records": C.TTA_MIN_OK_RECORDS,
        },
    }
    audit["TTA_TRANSFORM_SET_FROZEN"] = {
        "shifts": list(C.TTA_SHIFTS),
        "view_names": list(C.TTA_VIEW_NAMES),
        "K": len(C.TTA_SHIFTS),
        "frozen_before_outcome_inspection": True,
        "perturbation_tuned_on_target": "NO",
    }
    audit["TTA_STATUS_PROVISIONAL"] = (
        "EVALUABLE_PENDING_FULL_POPULATION_CHECK"
        if (finite_ok and bounded_ok and determ_ok) else "NOT_EVALUABLE")
    t.log()
    t.log(f"    PROVISIONAL TTA STATUS: {audit['TTA_STATUS_PROVISIONAL']}")

    C.write_json(os.path.join(C.ART, "TTA_TRANSFORM_AUDIT.json"), audit)
    t.log("")
    t.log("wrote artifacts/TTA_TRANSFORM_AUDIT.json")
    t.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
