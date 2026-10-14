#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GATE 3 — official emg2pose upstream inference (server-side, GPU).

Runs the OFFICIAL, already-established emg2pose pose estimator
(``regression_vemg2pose`` — EMG-only regression) over the exact mini corpus used
by Gate1.5 / Gate2A, and stores the predicted 20-D pose stream.

This script performs INFERENCE ONLY.  It never:
  * trains or fine-tunes anything;
  * touches the DB9 head;
  * reads or writes any downstream task output;
  * applies smoothing, calibration, filtering or resampling.

Output per recording: ``<stem>_pred.npz`` with
    angles      (T - left_context, 20) float32, radians
    time        (T - left_context,)    float64, seconds (input grid)
    row_offset  scalar int == left_context
    T_in        scalar int
plus ``INFERENCE_MANIFEST.json`` describing checkpoint, settings and counts.

Run:
  /root/miniconda3/envs/emg2pose-gate3/bin/python -X utf8 run_emg2pose_inference.py
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys
import time

import h5py
import numpy as np
import torch

sys.path.insert(0, "/root/work/emg2pose")
sys.path.insert(0, "/root/work/emg2pose_inference")

from predict_pose import PredictPose, JOINT_NAMES  # noqa: E402

CKPT = "/root/models/emg2pose/regression_vemg2pose.ckpt"
EXPECTED_CKPT_SHA256 = "748b1d1ef0ce1985f6fc07225d97eebfb370243429af803b4997d28ecce2424e"

log_lines: list[str] = []


def log(m: str = "") -> None:
    print(m, flush=True)
    log_lines.append(m)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mini-dir", default="/root/data/emg2pose_dataset_mini")
    ap.add_argument("--out-dir", default="/root/work/gate3_work/pred_pose")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--limit", type=int, default=0, help="debug: only first N files")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    t0 = time.time()

    log("=" * 78)
    log("GATE 3 — official emg2pose upstream inference (regression_vemg2pose)")
    log("=" * 78)

    ck_sha = sha256_file(CKPT)
    log(f"checkpoint        : {CKPT}")
    log(f"checkpoint sha256 : {ck_sha}")
    log(f"matches documented: {ck_sha == EXPECTED_CKPT_SHA256}")
    assert ck_sha == EXPECTED_CKPT_SHA256, "checkpoint identity changed -> STOP"

    dev = args.device
    if dev == "cuda" and not torch.cuda.is_available():
        log("!! CUDA unavailable, falling back to cpu")
        dev = "cpu"
    log(f"device            : {dev}")
    if dev == "cuda":
        log(f"gpu               : {torch.cuda.get_device_name(0)}")
        log(f"torch / cuda      : {torch.__version__} / {torch.version.cuda}")

    model = PredictPose(experiment="regression_vemg2pose", checkpoint=CKPT,
                        repo_root="/root/work/emg2pose", device=dev)
    desc = model.describe()
    log(f"experiment        : {desc['experiment']}")
    log(f"provide_initial_pos: {desc['provide_initial_pos']}")
    log(f"left_context      : {desc['left_context']}")
    log(f"right_context     : {desc['right_context']}")
    log(f"rollout_freq      : {desc['rollout_freq']}")
    log(f"emg_sample_rate   : {desc['emg_sample_rate']}")
    log(f"num_joints        : {desc['num_joints']}")
    log()

    files = sorted(glob.glob(os.path.join(args.mini_dir, "*.hdf5")))
    if args.limit:
        files = files[: args.limit]
    log(f"recordings        : {len(files)}")

    per_file = []
    total_in = 0
    total_out = 0
    total_nonfinite = 0

    for i, f in enumerate(files, 1):
        with h5py.File(f, "r") as h:
            g = h["emg2pose"]
            attrs = dict(g.attrs)
            ts = g["timeseries"]
            emg = ts["emg"][:]
            time_arr = ts["time"][:]
            T = int(emg.shape[0])

        angles = model.predict(emg)                     # (T - left_context, 20)
        expected = T - model.left_context
        assert angles.shape == (expected, 20), (angles.shape, expected, 20)

        out_time = time_arr[model.left_context:]
        assert out_time.shape[0] == angles.shape[0]

        nonfinite = int((~np.isfinite(angles)).sum())
        total_nonfinite += nonfinite

        stem = os.path.basename(f)[: -len(".hdf5")]
        np.savez_compressed(
            os.path.join(args.out_dir, f"{stem}_pred.npz"),
            angles=angles.astype(np.float32),
            time=out_time.astype(np.float64),
            row_offset=np.int64(model.left_context),
            T_in=np.int64(T),
        )
        total_in += T
        total_out += int(angles.shape[0])
        per_file.append({
            "file": os.path.basename(f),
            "side": str(attrs["side"]),
            "stage": str(attrs["stage"]),
            "user": str(attrs["user"]),
            "session": str(attrs["session"]),
            "T_in": T,
            "row_offset": int(model.left_context),
            "T_out": int(angles.shape[0]),
            "nonfinite": nonfinite,
            "t_start": float(out_time[0]),
            "t_end": float(out_time[-1]),
            "angles_min": float(angles.min()),
            "angles_max": float(angles.max()),
        })
        log(f"  [{i:>2}/{len(files)}] {os.path.basename(f)[-38:]:<38} "
            f"T={T:>7} -> {angles.shape[0]:>7}  nonfinite={nonfinite}")

    manifest = {
        "artifact": "INFERENCE_MANIFEST.json",
        "role": "official emg2pose upstream inference for GATE 3",
        "estimator": {
            "experiment": desc["experiment"],
            "checkpoint": CKPT,
            "checkpoint_sha256": ck_sha,
            "checkpoint_sha256_expected": EXPECTED_CKPT_SHA256,
            "checkpoint_match": ck_sha == EXPECTED_CKPT_SHA256,
            "repo_root": desc["repo_root"],
            "provide_initial_pos": desc["provide_initial_pos"],
            "left_context": desc["left_context"],
            "right_context": desc["right_context"],
            "rollout_freq": desc["rollout_freq"],
            "position_steps": desc["num_position_steps"],
            "emg_sample_rate": desc["emg_sample_rate"],
            "num_joints": desc["num_joints"],
            "joint_names": JOINT_NAMES,
            "device": dev,
        },
        "settings": {
            "smoothing": "NONE",
            "calibration": "NONE",
            "resampling": "NONE (predictions returned on the 2 kHz input grid)",
            "test_time_adaptation": "NONE",
            "chunking": f"single pass per recording; EMG tensor (T,16) -> "
                        f"predictions spanning EMG[{desc['left_context']}:T]",
            "output_cadence_hz": 2000.0,
            "db9_head_accessed": "NO",
            "downstream_output_read": "NO",
        },
        "totals": {
            "recordings": len(files),
            "input_rows": total_in,
            "output_rows": total_out,
            "nonfinite_values": total_nonfinite,
        },
        "per_file": per_file,
    }
    with open(os.path.join(args.out_dir, "INFERENCE_MANIFEST.json"), "w",
              encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)

    log()
    log(f"input rows        : {total_in}")
    log(f"output rows       : {total_out}")
    log(f"nonfinite values  : {total_nonfinite}")
    log(f"elapsed           : {time.time()-t0:.1f}s")
    log(f"out dir           : {args.out_dir}")

    with open("/root/work/gate3_work/inference_stdout.txt", "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(log_lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
