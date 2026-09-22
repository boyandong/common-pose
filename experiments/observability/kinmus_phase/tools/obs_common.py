"""Shared helpers for the KIN-MUS task-observability lane.

Read-only with respect to every OTHER lane.  Nothing here fits, selects or tunes
anything; the frozen choices live in ``obs_plan.py``.  Only one external asset is
ever opened, READ-ONLY: the KIN-MUS .mat audited by the admission lane.  No
cross-dataset pose corpus and no EMG array is read anywhere in this branch.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import numpy as np

ROOT = r"<PROJECT_ROOT>"
LANE = os.path.join(ROOT, "kinmus_task_observability")
TOOLS = os.path.join(LANE, "tools")
FIGDIR = os.path.join(LANE, "figures")
RESULTS = os.path.join(LANE, "results")
LOGS = os.path.join(LANE, "logs")

#: The upstream lane that owns the audited KIN-MUS source.  Read only.
ADMISSION_LANE = os.path.join(ROOT, "pose_api_dataset_admission")
KIN_MUS_MAT = os.path.join(ADMISSION_LANE, "raw", "kin_mus", "KIN_MUS_UJI.mat")

sys.path.insert(0, TOOLS)

SEED = 20260101

#: The 18 released UJI columns, in release order (frozen by the admission audit).
UJI18 = ("CMC1_F", "CMC1_A", "MCP1_F", "IP1_F", "MCP2_F", "MCP2-3_A", "PIP2_F",
         "MCP3_F", "PIP3_F", "MCP4_F", "MCP3-4_A", "PIP4_F", "PalmArch",
         "MCP5_F", "MCP4-5_A", "PIP5_F", "WR_F", "WR_A")

#: shared10_poc_v1 -> released column index, frozen by the admission decision.
SHARED10_COLUMNS = (0, 2, 4, 6, 7, 8, 9, 11, 13, 15)
SHARED10_NAMES = ("thumb_cmc_flexion", "thumb_mcp_flexion", "index_mcp_flexion",
                  "index_pip_flexion", "middle_mcp_flexion",
                  "middle_pip_flexion", "ring_mcp_flexion", "ring_pip_flexion",
                  "pinky_mcp_flexion", "pinky_pip_flexion")

PHASE_NAME = {1: "REACHING", 2: "MANIPULATION", 3: "RELEASING"}
PHASES = (1, 2, 3)


# --------------------------------------------------------------------- hashing
def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: str, obj) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return sha256_file(path)


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_text(path: str, text: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return sha256_file(path)


def log_to(path: str):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fh = open(path, "a", encoding="utf-8", newline="\n")

    def _log(msg: str = ""):
        print(msg, flush=True)
        fh.write(msg + "\n")
        fh.flush()

    return _log, fh


# ------------------------------------------------------------------ statistics
def wilson(k: int, n: int, z: float = 1.959963984540054):
    import math
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1.0 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def rate(k: int, n: int, *, label: str | None = None) -> dict:
    lo, hi = wilson(int(k), int(n))
    out = {"numerator": int(k), "denominator": int(n),
           "value": (k / n) if n else None,
           "wilson95": [None, None] if not n else [lo, hi]}
    if label:
        out["label"] = label
    return out


def balanced_accuracy(y_true: np.ndarray, y_pred: np.ndarray,
                      classes=PHASES) -> float:
    rec = []
    for c in classes:
        sel = y_true == c
        if sel.sum() == 0:
            continue
        rec.append(float((y_pred[sel] == c).mean()))
    return float(np.mean(rec)) if rec else float("nan")


def macro_f1(y_true: np.ndarray, y_pred: np.ndarray, classes=PHASES) -> float:
    fs = []
    for c in classes:
        tp = int(((y_pred == c) & (y_true == c)).sum())
        fp = int(((y_pred == c) & (y_true != c)).sum())
        fn = int(((y_pred != c) & (y_true == c)).sum())
        if tp + fp + fn == 0:
            continue
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        fs.append(0.0 if (prec + rec) == 0 else 2 * prec * rec / (prec + rec))
    return float(np.mean(fs)) if fs else float("nan")


def confusion(y_true: np.ndarray, y_pred: np.ndarray, classes=PHASES) -> dict:
    idx = {c: i for i, c in enumerate(classes)}
    m = np.zeros((len(classes), len(classes)), dtype=np.int64)
    for t, p in zip(y_true, y_pred):
        if t in idx and p in idx:
            m[idx[t], idx[p]] += 1
    return {
        "classes": [PHASE_NAME[c] for c in classes],
        "matrix_true_x_pred": m.tolist(),
        "per_class_recall": {
            PHASE_NAME[c]: (rate(int(m[i, i]), int(m[i].sum()))
                            if m[i].sum() else
                            {"numerator": 0, "denominator": 0, "value": None,
                             "wilson95": [None, None]})
            for i, c in enumerate(classes)},
        "per_class_precision": {
            PHASE_NAME[c]: (rate(int(m[i, i]), int(m[:, i].sum()))
                            if m[:, i].sum() else
                            {"numerator": 0, "denominator": 0, "value": None,
                             "wilson95": [None, None]})
            for i, c in enumerate(classes)},
    }


def subject_bootstrap(values: np.ndarray, subjects: np.ndarray, *,
                      n_boot: int = 2000, seed: int = SEED) -> dict:
    """Bootstrap over SUBJECTS, never over frames."""
    values = np.asarray(values, dtype=np.float64)
    subjects = np.asarray(subjects)
    uniq = np.unique(subjects)
    if uniq.size < 2 or values.size == 0:
        return {"value": float(values.mean()) if values.size else None,
                "subject_bootstrap_95": [None, None], "n_boot": 0,
                "resample_unit": "subject"}
    idx = {s: np.flatnonzero(subjects == s) for s in uniq}
    rng = np.random.default_rng(seed)
    draws = np.empty(n_boot, dtype=np.float64)
    for b in range(n_boot):
        pick = rng.integers(0, uniq.size, size=uniq.size)
        vals = np.concatenate([values[idx[uniq[p]]] for p in pick])
        draws[b] = vals.mean() if vals.size else np.nan
    lo, hi = np.nanpercentile(draws, [2.5, 97.5])
    return {"value": float(values.mean()),
            "subject_bootstrap_95": [float(lo), float(hi)],
            "n_boot": int(n_boot), "resample_unit": "subject",
            "n_subjects": int(uniq.size)}


# ------------------------------------------------------------------ data load
def load_kinmus() -> dict:
    """The released kinematic block, parsed exactly as the admission audit did.

    A trial is usable iff ``Kinematic_data`` is 2-D with 18 columns and its row
    count matches ``time``.  Three containers in the release are empty and are
    reported, never repaired.
    """
    import scipy.io as sio
    m = sio.loadmat(KIN_MUS_MAT, squeeze_me=True, struct_as_record=False)
    top = m["EMG_KIN_v4"].ravel()
    trials, malformed = [], []
    for i, e in enumerate(top):
        k = np.asarray(e.Kinematic_data, dtype=np.float64)
        t = np.asarray(e.time, dtype=np.float64).ravel()
        if k.ndim != 2 or k.shape[1] != 18 or k.shape[0] != t.size:
            malformed.append({"trial_index": int(i), "subject": int(e.Subject),
                              "ADL": int(e.ADL), "phase": int(e.Phase),
                              "kin_shape": list(k.shape),
                              "time_len": int(t.size)})
            continue
        trials.append({"trial_index": int(i), "subject": int(e.Subject),
                       "adl": int(e.ADL), "phase": int(e.Phase),
                       "n_frames": int(k.shape[0]), "K": k, "time": t})
    return {"trials": trials, "malformed": malformed,
            "n_containers": int(top.size)}


def stack(trials: list[dict], columns) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Concatenate trials -> (X, phase, subject) using the given column subset."""
    X = np.vstack([t["K"][:, list(columns)] for t in trials])
    y = np.concatenate([np.full(t["n_frames"], t["phase"], dtype=np.int64)
                        for t in trials])
    s = np.concatenate([np.full(t["n_frames"], t["subject"], dtype=np.int64)
                        for t in trials])
    return X, y, s


def boundary_mask(trials: list[dict], margin: int) -> np.ndarray:
    """True where a frame is at least ``margin`` frames from any phase boundary.

    Boundaries are the trial's own first and last frame (a phase segment is one
    trial), so interior = frames in ``[margin, n_frames - margin)``.
    """
    out = []
    for t in trials:
        n = t["n_frames"]
        idx = np.arange(n)
        out.append((idx >= margin) & (idx < n - margin))
    return np.concatenate(out)


if __name__ == "__main__":  # pragma: no cover
    d = load_kinmus()
    print("containers", d["n_containers"], "usable", len(d["trials"]),
          "malformed", len(d["malformed"]))
    X, y, s = stack(d["trials"], SHARED10_COLUMNS)
    print("shared10", X.shape, "subjects", np.unique(s).size)
