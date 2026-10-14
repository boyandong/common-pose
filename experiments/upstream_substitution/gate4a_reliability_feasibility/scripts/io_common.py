#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GATE 4A — shared I/O, population reconstruction and metric primitives.

Implements GATE4A_PLAN.md §3, §5, §9. No gate logic lives here.

The population rebuild below is the VERBATIM Gate3 / Gate3B eligibility rule; it
is deliberately duplicated (not imported from the Gate3B lane) so that the
reconstruction is an independent re-derivation rather than a shared code path.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sys
from typing import Any

import h5py
import joblib
import numpy as np

# --------------------------------------------------------------------------- #
# Paths (frozen)
# --------------------------------------------------------------------------- #
LANE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(LANE, "artifacts")
LOGS = os.path.join(LANE, "logs")
WORK = os.path.join(LANE, "work")

MINI_DIR = "/root/data/emg2pose_dataset_mini"
PRED_DIR = "/root/work/gate3_work/pred_pose"
FROZEN_HEAD = "/root/work/gate3_work/frozen_head/frozen_db9_trusted8_lda.joblib"
DB9_REF = ("/root/work/common-pose/experiments/upstream_substitution/"
           "gate3b_continuous_representation/artifacts/FISHER_DB9_REFERENCE_SCALE.json")
GATE3B_DECISION = ("/root/work/common-pose/experiments/upstream_substitution/"
                   "gate3b_continuous_representation/artifacts/GATE3B_DECISION.json")
GATE3B_DATA_LINK = ("/root/work/common-pose/experiments/upstream_substitution/"
                    "gate3b_continuous_representation/artifacts/GATE3B_DATA_LINK.json")
CKPT = "/root/models/emg2pose/regression_vemg2pose.ckpt"

EMG_REPO = "/root/work/emg2pose"
PREDICT_WRAPPER = "/root/work/emg2pose_inference/predict_pose.py"

# --------------------------------------------------------------------------- #
# Constants (frozen; identical to Gate3 / Gate3B)
# --------------------------------------------------------------------------- #
POSE_STRIDE = 40
ANALYSIS_HZ = 50.0
TRUSTED8_SRC_IDX = [2, 3, 5, 6, 9, 13, 17, 18]
EXPECTED_N = 86833
EXPECTED_RECORDS = 30
EXPECTED_STAGES = 15
EPS = 1e-12

BACKBONE_FEATURES = frozenset((
    "pose_j", "fisher_j", "dpose_j", "dfisher_j",
    "d2pose_j", "d2fisher_j", "side_right", "d1_valid", "d2_valid",
))
N_BACKBONE_FEATURES = 48

# Gate3B recorded target statistics (independent reproduction check, plan §5).
# NOTE ON TOLERANCE: these literals are published in GATE3B_PLAN.md / the Gate3B log
# rounded to 6 decimal places and are compared against the full-precision value, so
# the achievable agreement floor is 5e-7, not 1e-9. Measured across four equivalent
# block-mean constructions (plain mean, sum/count, per-slice loop, float32-source
# variants) the deviation from these literals is 2.6e-7 .. 6.3e-7, i.e. exactly the
# rounding floor. TARGET_REPRO_TOL is therefore set to 1e-6, which still rules out any
# real population or alignment change (those shift the statistics by >= 1e-3).
GATE3B_TARGET_RECORD = {
    "n": 86833,
    "median": 2.896259,
    "iqr": 1.651728,
    "p05": 1.283626,
    "p95": 5.201622,
}
TARGET_REPRO_TOL = 1e-6
TARGET_REPRO_TOL_NOTE = (
    "Gate3B literals are recorded to 6 decimals; 1e-9 is unreachable by construction. "
    "Four equivalent reduction orders deviate from the literals by 2.6e-7..6.3e-7, so "
    "1e-6 is the rounding floor. A real population/alignment change would shift these "
    "statistics by >= 1e-3.")

# Frozen TTA transform set (plan §4.2)
TTA_SHIFTS = (0, 1, -1)
TTA_VIEW_NAMES = ("k0", "k+1", "k-1")

# Pre-declared TTA validity bounds (plan §4.3)
TTA_MAX_MEDIAN_VIEW_DEV_DEG = 15.0
TTA_MAX_ABS_VIEW_DEV_DEG = 90.0
TTA_MIN_OK_RECORDS = 29
# Declared tolerance for the block-mean agreement between a live forward pass and
# the frozen Gate3 prediction stream (both float32 sources, float64 reduction).
# 1e-6 rad is ~6e-8 deg, i.e. ~1e-7 of the natural per-block pose spread.
TTA_BLOCK_MEAN_TOL = 1e-6

# Risk-coverage grid (plan §9)
COVERAGE_POINTS = (1.00, 0.90, 0.75, 0.50, 0.25)
AURC_COVERAGES = tuple(round(0.10 + 0.01 * i, 2) for i in range(91))
N_DECILES = 10
DECILE = 10

# Pre-declared feasibility bands (plan §9.2)
FEASIBILITY_BANDS = (
    # (label, rho_min, medrec_min, posfrac_min, aurc_must_beat_nogate)
    ("MOST_PROMISING_FOR_MULTIUSER", 0.50, 0.40, 0.90, True),
    ("PROMISING", 0.30, 0.20, 0.80, True),
    ("WEAK", 0.10, None, 0.60, False),
)


def ensure_dirs() -> None:
    for d in (ART, LOGS, WORK):
        os.makedirs(d, exist_ok=True)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Tee:
    """Write stdout to console and to one or more log files."""

    def __init__(self, *paths: str) -> None:
        self.paths = list(paths)
        self.lines: list[str] = []
        self.handles = [open(p, "w", encoding="utf-8") for p in paths]

    def log(self, msg: str = "") -> None:
        print(msg, flush=True)
        for h in self.handles:
            h.write(msg + "\n")
            h.flush()
        self.lines.append(msg)

    def close(self) -> None:
        for h in self.handles:
            h.close()


def qstats(a: Any) -> dict | None:
    arr = np.asarray(a, dtype=np.float64)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return None
    q = np.percentile(arr, [5, 25, 75, 95])
    return {
        "n": int(arr.size),
        "mean": float(arr.mean()),
        "median": float(np.median(arr)),
        "iqr": float(q[2] - q[1]),
        "p05": float(q[0]),
        "p25": float(q[1]),
        "p75": float(q[2]),
        "p95": float(q[3]),
        "min": float(arr.min()),
        "max": float(arr.max()),
    }


def frac_positive_strict(values: Any) -> float | None:
    v = np.asarray(values, dtype=np.float64)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return None
    return float((v > 0).mean())


def load_frozen_head():
    bundle = joblib.load(FROZEN_HEAD)
    return bundle["head"], bundle["mu"], bundle["sd"]


def load_db9_sigma() -> np.ndarray:
    with open(DB9_REF, encoding="utf-8") as fh:
        ref = json.load(fh)
    sigma = np.asarray(ref["fisher_component_sigma_db9"], dtype=np.float64)
    assert sigma.shape == (7,), sigma.shape
    assert ref["provenance"]["emg2pose_data_used"] == "NO"
    return sigma


# --------------------------------------------------------------------------- #
# Population reconstruction (verbatim Gate3 / Gate3B rule)
# --------------------------------------------------------------------------- #
def record_files() -> list[str]:
    return sorted(glob.glob(os.path.join(MINI_DIR, "*.hdf5")))


def build_population(require_expected: bool = True) -> dict:
    """Rebuild the frozen Gate3 eligible population from raw sources.

    Returns dict with G, P (trusted-8 pose block means), side, stage, record,
    block_idx (index of the accepted block inside its record's block list),
    tta_view_idx (index into that record's 2 kHz prediction grid) and n.
    """
    files = record_files()
    Gp, Pp = [], []
    side_l, stage_l, rec_l, blk_l, tta_l = [], [], [], [], []
    user_l, session_l = [], []

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
        assert np.array_equal(tgt[off:], tpred), f"alignment broken: {stem}"
        gt_w, pr_w = ja[off:], ang
        n = gt_w.shape[0]
        gv = (~np.all(np.isclose(gt_w, 0.0), axis=1)) & np.isfinite(gt_w).all(axis=1)
        pv = (~np.all(np.isclose(pr_w, 0.0), axis=1)) & np.isfinite(pr_w).all(axis=1)
        nb = ang.shape[0] // POSE_STRIDE
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
        blk = np.flatnonzero(m)
        k = int(m.sum())
        Gp.append(gb[m])
        Pp.append(pb[m])
        side_l.extend([str(attrs["side"])] * k)
        stage_l.extend([str(attrs["stage"])] * k)
        rec_l.extend([stem] * k)
        user_l.extend([str(attrs["user"])] * k)
        session_l.extend([str(attrs["session"])] * k)
        blk_l.append(blk)
        tta_l.append(off + blk * POSE_STRIDE)

    out = {
        "G": np.vstack(Gp).astype(np.float64),
        "P": np.vstack(Pp).astype(np.float64),
        "side": np.asarray(side_l),
        "stage": np.asarray(stage_l),
        "record": np.asarray(rec_l),
        "user": np.asarray(user_l),
        "session": np.asarray(session_l),
        "files": files,
        "block_idx": np.concatenate(blk_l),
        "tta_idx": np.concatenate(tta_l),
    }
    out["n"] = int(out["G"].shape[0])
    if require_expected:
        assert out["n"] == EXPECTED_N, (
            f"population changed: {out['n']} != {EXPECTED_N} -> STOP")
    return out


def record_stem(path_or_stem: str) -> str:
    """Record stem from either a full .hdf5 path, a *_pred.npz path, or a bare stem."""
    base = os.path.basename(path_or_stem)
    for suf in (".hdf5", "_pred.npz", ".npz"):
        if base.endswith(suf):
            base = base[: -len(suf)]
            break
    return base


def record_offsets(pop: dict) -> tuple[np.ndarray, np.ndarray]:
    """Per-record (start, length) of the CONCATENATED population arrays.

    `pop["G"]`, `pop["P"]`, `pop["record"]`, ... are one flat concatenation over
    the records in `pop["files"]` order, so record r's samples occupy the slice
    `[rec_start[r], rec_start[r] + rec_len[r])` of those arrays.

    Index contract (verified empirically, see GATE4A_DECISION.json
    `index_contract`):
      * `pop["tta_idx"]` is GLOBAL within its own record: the row index into that
        record's 2 kHz prediction grid, equal to `row_offset + 40 * block_pos`.
      * `pop["block_idx"]` is LOCAL and 0-based: the position of the accepted block
        inside its own record's block list, i.e. `np.flatnonzero(valid_mask)`.
        It is NOT a global population position, so it indexes a per-record block
        array directly and must never be offset by `rec_start`.

    `pop["files"]` holds full .hdf5 paths while `pop["record"]` holds record
    STEMS, so the per-record counts are computed against the stem.
    """
    stems = [record_stem(f) for f in pop["files"]]
    rec_len = np.array([int((pop["record"] == s).sum()) for s in stems],
                       dtype=np.int64)
    rec_start = np.concatenate([[0], np.cumsum(rec_len)[:-1]]).astype(np.int64)
    assert int(rec_len.sum()) == int(pop["n"]), \
        f"record lengths do not sum to the population size: {int(rec_len.sum())} " \
        f"!= {int(pop['n'])}"
    return rec_start, rec_len


def pose_fisher(head, mu, sd, pose: np.ndarray) -> np.ndarray:
    """Frozen L1 Fisher embedding of a trusted-8 pose matrix."""
    return head.transform((pose - mu) / sd)


def fisher_error(z_pred: np.ndarray, z_gt: np.ndarray,
                 sigma: np.ndarray) -> np.ndarray:
    """DB9-normalised Fisher displacement r_t (plan §5)."""
    return np.sqrt((((z_pred - z_gt) / sigma) ** 2).sum(1))


# --------------------------------------------------------------------------- #
# Metrics (plan §9)
# --------------------------------------------------------------------------- #
def rankdata_average(a: np.ndarray) -> np.ndarray:
    """Average ranks, vectorised, stable for ties (matches scipy 'average')."""
    a = np.asarray(a, dtype=np.float64)
    order = np.argsort(a, kind="mergesort")
    sa = a[order]
    n = a.size
    if n == 0:
        return np.empty(0)
    idx = np.arange(n, dtype=np.float64)
    obs = np.ones(n, dtype=bool)
    obs[1:] = sa[1:] != sa[:-1]
    start = np.flatnonzero(obs)
    counts = np.diff(np.append(start, n)).astype(np.float64)
    avg = start.astype(np.float64) + (counts - 1.0) / 2.0
    r = np.empty(n, dtype=np.float64)
    r[order] = np.repeat(avg, counts.astype(np.int64))
    return r


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    ok = np.isfinite(x) & np.isfinite(y)
    if int(ok.sum()) < 3:
        return float("nan")
    rx, ry = rankdata_average(x[ok]), rankdata_average(y[ok])
    rx = rx - rx.mean()
    ry = ry - ry.mean()
    den = float(np.sqrt((rx ** 2).sum() * (ry ** 2).sum()))
    return float((rx * ry).sum() / den) if den > 0 else float("nan")


def kendall(x: np.ndarray, y: np.ndarray) -> float:
    """Kendall tau-b via scipy (tie-corrected, matches its documented default)."""
    from scipy.stats import kendalltau
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    ok = np.isfinite(x) & np.isfinite(y)
    if int(ok.sum()) < 3:
        return float("nan")
    res = kendalltau(x[ok], y[ok], variant="b")
    return float(res.statistic)


def rank_order(score: np.ndarray) -> np.ndarray:
    """Ascending risk order (lowest predicted risk first), deterministic."""
    return np.argsort(np.asarray(score, dtype=np.float64), kind="mergesort")


def risk_at_coverage(order: np.ndarray, r: np.ndarray,
                     coverage: float) -> dict:
    k = int(np.floor(coverage * order.size))
    k = max(1, min(k, order.size))
    sel = order[:k]
    rr = r[sel]
    return {
        "coverage": float(coverage),
        "n_accepted": int(k),
        "mean_r": float(rr.mean()),
        "median_r": float(np.median(rr)),
        "p90_r": float(np.percentile(rr, 90)),
    }


def risk_coverage_curve(order: np.ndarray, r: np.ndarray,
                        coverages=AURC_COVERAGES) -> list[dict]:
    return [risk_at_coverage(order, r, c) for c in coverages]


def aurc(order: np.ndarray, r: np.ndarray, coverages=AURC_COVERAGES) -> float:
    vals = [risk_at_coverage(order, r, c)["mean_r"] for c in coverages]
    return float(np.mean(vals))


def decile_summary(score: np.ndarray, r: np.ndarray,
                   n_deciles: int = N_DECILES) -> list[dict]:
    order = rank_order(score)
    rows = []
    for k, ix in enumerate(np.array_split(order, n_deciles), 1):
        sr, rr = score[ix], r[ix]
        rows.append({
            "decile": k,
            "n": int(ix.size),
            "median_score": float(np.median(sr)),
            "median_r": float(np.median(rr)),
            "mean_r": float(rr.mean()),
            "p90_r": float(np.percentile(rr, 90)),
            "min_score": float(sr.min()),
            "max_score": float(sr.max()),
        })
    return rows


def feasibility_band(rho: float, med_record_rho: float, pos_frac: float,
                     aurc_value: float, no_gate_aurc: float) -> str:
    beats = aurc_value < no_gate_aurc
    for label, rho_min, medrec_min, posfrac_min, need_beat in FEASIBILITY_BANDS:
        if not np.isfinite(rho) or rho < rho_min:
            continue
        if medrec_min is not None and (not np.isfinite(med_record_rho)
                                       or med_record_rho < medrec_min):
            continue
        if posfrac_min is not None and (not np.isfinite(pos_frac)
                                        or pos_frac < posfrac_min):
            continue
        if need_beat and not beats:
            continue
        return label
    return "NO_VISIBLE_SIGNAL"


def write_json(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False, default=str)


def write_csv(path: str, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    import csv
    if not rows:
        raise ValueError(f"refusing to write empty csv: {path}")
    names = fieldnames or list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=names, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def banner(t: Tee, title: str) -> None:
    t.log("=" * 78)
    t.log(title)
    t.log("=" * 78)
    t.log(f"python             : {sys.version.split()[0]}")
    t.log(f"plan sha256        : {sha256_file(os.path.join(LANE, 'GATE4A_PLAN.md'))}")
    t.log()
