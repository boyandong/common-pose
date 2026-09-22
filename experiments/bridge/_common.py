"""
bridge_audit/_common.py -- shared primitives for the Session-5 cross-dataset bridge
audit (emg2pose -> canonical kinematics -> frozen DB9 posture decoder).

FROZEN-ASSET POLICY
-------------------
Nothing in this package re-implements a frozen Session-2 or Session-3 artifact:

  20D -> canonical16          imported from  representation/canonical_hand.py      (S2, FROZEN)
  EMG -> 20D pose             imported from  inference/predict_pose.py             (S2, official ckpt)
  DB9 representative postures consumed verbatim from                                     (S3, FROZEN)
      data/db9_posture16/representative_postures_77.npz
  cohort partition            loaded from    docs/CONFIRMATORY_COHORTS.json         (S3, FROZEN)
  frozen classifier/config    imported from  posture_decoder/experiments/confirmatory_policy.py

This module only *consumes* those artifacts; it never writes into their directories.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Paths (ASCII junction, per Session-1 constraint: h5py cannot open non-ASCII
# paths on this machine, and Path.resolve() would dereference the junction).
# ---------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # .../emg2pose_handstate
ASCII_ROOT = r"<PROJECT_ROOT>"                       # junction -> ROOT

REPRESENTATION_DIR = os.path.join(ROOT, "representation")
INFERENCE_DIR = os.path.join(ROOT, "inference")
POSTURE_DIR = os.path.join(ROOT, "posture_decoder")
EXPERIMENTS_DIR = os.path.join(POSTURE_DIR, "experiments")
BASELINE_DIR = os.path.join(ROOT, "baseline", "emg2pose")

DOCS_DIR = os.path.join(ROOT, "docs")
DB9_DATA_DIR = os.path.join(ROOT, "data", "db9_posture16")
MINI_DIR = os.path.join(ROOT, "data", "official", "emg2pose_dataset_mini")
CHECKPOINT_DIR = os.path.join(ROOT, "checkpoints", "emg2pose_model_checkpoints")

REPS_77 = os.path.join(DB9_DATA_DIR, "representative_postures_77.npz")
REPS_77_META = os.path.join(DB9_DATA_DIR, "representative_postures_77.meta.json")
COHORTS = os.path.join(DOCS_DIR, "CONFIRMATORY_COHORTS.json")
FROZEN_SPEC = os.path.join(DOCS_DIR, "FROZEN_CONFIRMATORY_SPEC.json")
FULL_DB9_RESULTS = os.path.join(DB9_DATA_DIR, "full_db9_results.json")
CANONICAL_SCHEMA = os.path.join(REPRESENTATION_DIR, "canonical16_schema.json")
DB9_SCHEMA = os.path.join(REPRESENTATION_DIR, "db9_canonical16_schema.json")

for _p in (REPRESENTATION_DIR, INFERENCE_DIR, EXPERIMENTS_DIR, POSTURE_DIR, BASELINE_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Frozen adapters / policy (imported, never re-derived)
import canonical_hand as ch              # noqa: E402  (S2, FROZEN)
import db9_to_canonical16 as d2c         # noqa: E402  (S3, FROZEN)
import confirmatory_policy as cp         # noqa: E402  (S3, FROZEN)

#: Frozen representation index subsets, taken from the frozen adapter itself so
#: they cannot drift from Session 3.
CANON16 = list(ch.canonical16_names())
CANON15_IDX = [CANON16.index(n) for n in d2c.canonical15_noThumbAA_names()]
CANON12_IDX = [CANON16.index(n) for n in d2c.canonical12_noDIP_names()]

#: Anatomical grouping used for Phase-8 attribution (canonical16 order).
DOF_GROUPS: dict[str, list[int]] = {
    "thumb_cmc_flexion": [0],
    "thumb_cmc_ab_adduction": [1],
    "thumb_mcp_ip": [2, 3],
    "finger_mcp": [4, 7, 10, 13],
    "finger_pip": [5, 8, 11, 14],
    "finger_dip": [6, 9, 12, 15],
}


def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def sha256_json(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def hash_artifacts(paths: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for p in paths:
        if os.path.exists(p):
            st = os.stat(p)
            out[os.path.relpath(p, ROOT).replace("\\", "/")] = {
                "bytes": int(st.st_size),
                "sha256": sha256_file(p),
            }
        else:
            out[os.path.relpath(p, ROOT).replace("\\", "/")] = None
    return out


def jstep(x: np.ndarray, t: float) -> float:
    """Jensen-Shannon divergence between two aligned probability matrices."""

    p = np.clip(np.asarray(x, dtype=np.float64), 1e-12, None)
    q = np.clip(np.asarray(t, dtype=np.float64), 1e-12, None)
    p = p / p.sum(axis=1, keepdims=True)
    q = q / q.sum(axis=1, keepdims=True)
    m = 0.5 * (p + q)

    def _kl(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return np.sum(a * (np.log(a) - np.log(b)), axis=1)

    return 0.5 * _kl(p, m) + 0.5 * _kl(q, m)


def describe(values: np.ndarray, prefix: str = "") -> dict[str, float]:
    v = np.asarray(values, dtype=np.float64)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {f"{prefix}n": 0}
    q = np.percentile(v, [5, 25, 50, 75, 95])
    return {
        f"{prefix}n": int(v.size),
        f"{prefix}mean": float(v.mean()),
        f"{prefix}sd": float(v.std(ddof=1)) if v.size > 1 else 0.0,
        f"{prefix}min": float(v.min()),
        f"{prefix}p05": float(q[0]),
        f"{prefix}p25": float(q[1]),
        f"{prefix}median": float(q[2]),
        f"{prefix}p75": float(q[3]),
        f"{prefix}p95": float(q[4]),
        f"{prefix}max": float(v.max()),
    }


# ---------------------------------------------------------------------------
# SINGLE SOURCE OF TRUTH for the paired arrays
# ---------------------------------------------------------------------------
# Every analysis that reads the bridge-audit result file MUST assemble the paired
# GT / predicted canonical16 matrix through this one function. It was duplicated
# once (in domain_depth.py) and the two copies silently disagreed, which produced
# an identity check that failed for no visible reason. There is now one loader.
def load_paired(results_json: str) -> dict:
    """Rebuild the paired arrays from the per-session artifacts.

    Returns ``G`` (n,16) GT canonical16, ``P`` (n,16) predicted canonical16,
    ``S`` (n,) session names, and ``T`` (n,) timestamps -- all in the GT-valid
    native-cadence rows only, in a deterministic session order.
    """
    with open(results_json, encoding="utf-8") as fh:
        rec = json.load(fh)
    sess_dir = rec["artifacts"]["sessions_dir"]
    G, P, S, T = [], [], [], []
    for s in rec["phase2_3_corpus"]["sessions"]:
        z = np.load(os.path.join(sess_dir, f"{s['session']}.paired50hz.npz"))
        k = np.asarray(z["gt_valid"], dtype=bool)
        G.append(np.asarray(z["gt16"], dtype=np.float64)[k])
        P.append(np.asarray(z["pred16"], dtype=np.float64)[k])
        S.append(np.full(int(k.sum()), s["session"], dtype=object))
        T.append(np.asarray(z["time"], dtype=np.float64)[k])
    return {
        "G": np.concatenate(G),
        "P": np.concatenate(P),
        "S": np.concatenate(S),
        "T": np.concatenate(T),
        "results": rec,
    }
