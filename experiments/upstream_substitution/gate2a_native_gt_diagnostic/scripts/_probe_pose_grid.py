#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Reconnaissance: determine the native emg2pose GT pose time grid.

Read-only probe. Used to fix the sampling policy in GATE2A_PLAN.md BEFORE any
head output is inspected. Writes nothing.

Run: <EMG2POSE_VENV>\\Scripts\\python.exe -X utf8 scripts/_probe_pose_grid.py
"""
from __future__ import annotations

import glob
import json

import h5py
import numpy as np

CORPUS = r"C:\emg2pose\data\official\emg2pose_dataset_mini"

out = {}
files = sorted(glob.glob(CORPUS + r"\*.hdf5"))
print(f"files: {len(files)}")

# Probe a few files of differing length.
probe = [f for f in files if any(k in f for k in
         ("recording-1_left", "recording-10_left", "recording-13_left", "recording-15_left"))]
if not probe:
    probe = files[:3]

for f in probe:
    with h5py.File(f, "r") as h:
        ds = h["emg2pose/timeseries"]
        n = ds.shape[0]
        t = ds["time"][:]
        ja = ds["joint_angles"][:]
    dt = np.diff(t)
    # exact repeat detection on the raw float32 joint vector
    same = np.all(ja[1:] == ja[:-1], axis=1)
    # run lengths of identical consecutive rows
    runs = []
    cur = 1
    for v in same:
        if v:
            cur += 1
        else:
            runs.append(cur)
            cur = 1
    runs.append(cur)
    runs = np.array(runs)
    # transition rate: positions where the pose actually changes
    n_change = int((~same).sum())
    span = float(t[-1] - t[0])
    rec = f.split("recording-")[1].split(".hdf5")[0]
    out[rec] = {
        "rows": int(n),
        "span_s": round(span, 3),
        "nominal_hz_rows_over_span": round(n / span, 3),
        "dt_median_us": float(np.median(dt) * 1e6),
        "dt_unique_count": int(len(np.unique(np.round(dt, 9)))),
        "dt_min_us": float(dt.min() * 1e6),
        "dt_max_us": float(dt.max() * 1e6),
        "pose_changes": n_change,
        "pose_change_hz": round(n_change / span, 3),
        "identical_run_median_rows": int(np.median(runs)),
        "identical_run_max_rows": int(runs.max()),
        "identical_run_p95_rows": int(np.percentile(runs, 95)),
        "unique_pose_rows": int(n - int(same.sum())),
        "unique_pose_rows_per_span_s": round((n - int(same.sum())) / span, 3),
    }

print()
print(json.dumps(out, indent=2))

# Aggregate over ALL files: the pose-change rate is the defensible native rate.
allrows = 0
allspan = 0.0
allchange = 0
run_med = []
for f in files:
    with h5py.File(f, "r") as h:
        ds = h["emg2pose/timeseries"]
        n = ds.shape[0]
        t = ds["time"][:]
        ja = ds["joint_angles"][:]
    same = np.all(ja[1:] == ja[:-1], axis=1)
    n_change = int((~same).sum())
    span = float(t[-1] - t[0])
    allrows += n
    allspan += span
    allchange += n_change
    run_med.append(n / max(n_change, 1))

print()
print("=== ALL 30 FILES ===")
print(f"total stored rows          : {allrows}")
print(f"total span (s)             : {allspan:.1f}")
print(f"total pose CHANGES          : {allchange}")
print(f"rows per pose change (median over files): {np.median(run_med):.2f}")
print(f"global pose-change rate    : {allchange / allspan:.3f} Hz")
print(f"global row rate over span  : {allrows / allspan:.3f} Hz")
