#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GATE 2A — native-coordinate GT-only frozen-head diagnostic.

Implements GATE2A_PLAN.md (SHA-256 9fc91ea7b34fdfdc08791d9ebcba8922aa253b826edf89fa54222b6d1eb46ce7)
exactly and nothing else.  EXPLORATORY DIAGNOSTIC: no training beyond the authorised
identical reconstruction of the frozen head, no calibration fitting, no predicted pose,
no UNKNOWN gate, no semantic accuracy claim.

Run: <EMG2POSE_VENV>\\Scripts\\python.exe -X utf8 scripts/run_gate2a_native_gt.py
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import sys
import time
from collections import Counter, defaultdict

import h5py
import numpy as np
import scipy.io as sio
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.metrics import (accuracy_score, balanced_accuracy_score,
                             confusion_matrix, f1_score, recall_score)

# --------------------------------------------------------------------------
# Constants — all from GATE2A_PLAN.md
# --------------------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
ART = os.path.join(LANE, "artifacts")
LOGS = os.path.join(LANE, "logs")
os.makedirs(ART, exist_ok=True)
os.makedirs(LOGS, exist_ok=True)

PLAN = os.path.join(LANE, "GATE2A_PLAN.md")
PLAN_SHA = hashlib.sha256(open(PLAN, "rb").read()).hexdigest()

DB9_EXTRACTED = r"C:\emg2pose\data\ninapro_db9\extracted"
EMG2POSE_MINI = r"C:\emg2pose\data\official\emg2pose_dataset_mini"

FROZEN_SUBSET = r"<PROJECT_ROOT>\audits\db9\trusted_pose\TRUSTED_DB9_POSE_v1.json"

SEG_CAP = 200          # frozen per-segment frame cap
CORE_FRAC = 0.6        # frozen central fraction
AGREE_IDS = (1, 2, 3, 4, 5, 6, 7, 8)   # official handedness task ids

# DB9 released 22-channel order, read verbatim from order_of_angles.
DB9_ORDER = ["CMC1_f", "CMC1_a", "MCP1", "IP1", "MCP2_f", "MCP2_a", "PIP2",
             "MCP3_f", "PIP3", "MCP4_f", "MCP4_a", "PIP4", "CMC5", "MCP5_f",
             "MCP5_a", "PIP5", "DIP2", "DIP3", "DIP4", "DIP5", "WRIST_F", "WRIST_A"]

# canonical16 -> emg2pose index (from canonical_hand.py / CANONICAL16_CONTRACT.md)
CANON16_SRC = [0, 1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15, 17, 18, 19]
CANON16_NAMES = ["thumb_cmc_flexion", "thumb_cmc_ab_adduction", "thumb_mcp_flexion",
                 "thumb_ip_flexion", "index_mcp_flexion", "index_pip_flexion",
                 "index_dip_flexion", "middle_mcp_flexion", "middle_pip_flexion",
                 "middle_dip_flexion", "ring_mcp_flexion", "ring_pip_flexion",
                 "ring_dip_flexion", "pinky_mcp_flexion", "pinky_pip_flexion",
                 "pinky_dip_flexion"]
TRUSTED8_NAMES = ["thumb_mcp_flexion", "thumb_ip_flexion", "index_mcp_flexion",
                  "index_pip_flexion", "middle_mcp_flexion", "ring_mcp_flexion",
                  "pinky_mcp_flexion", "pinky_pip_flexion"]
TRUSTED8_CANON_IDX = [CANON16_NAMES.index(n) for n in TRUSTED8_NAMES]
TRUSTED8_SRC_IDX = [CANON16_SRC[i] for i in TRUSTED8_CANON_IDX]
TRUSTED8_DB9_COLS = [DB9_ORDER.index(n) for n in
                     ["MCP1", "IP1", "MCP2_f", "PIP2", "MCP3_f", "MCP4_f", "MCP5_f", "PIP5"]]

POSE_STRIDE = 40       # 2000 / 50 -> native 50 Hz pose cadence (bridge_audit/run_bridge_audit.py)
EMG_RATE = 2000

# Decision thresholds — declared in the plan BEFORE any output.
DEGEN_COLLAPSE_FRAC = 0.90
DEGEN_COLLAPSE_MAXCLASSES = 2
DEGEN_SWITCH_RATE = 0.5
DEGEN_BAD_MARGIN_FRAC = 0.10
DEGEN_C45_FRAC = 0.50
AMBIG_ENTROPY_BITS = 1.0

log_lines: list[str] = []


def log(m: str = "") -> None:
    print(m)
    log_lines.append(m)


# --------------------------------------------------------------------------
# DB9 side — frozen protocol, mirrored
# --------------------------------------------------------------------------

def segments(stim, rerep, exclude_rest=True):
    """restimulus x rerepetition segmentation (frozen rule)."""
    ks, rs = np.asarray(stim).ravel(), np.asarray(rerep).ravel()
    n = min(ks.size, rs.size)
    out, start = [], 0
    for i in range(1, n + 1):
        if i == n or ks[i] != ks[start] or rs[i] != rs[start]:
            st, rp = int(ks[start]), int(rs[start])
            if not (exclude_rest and (st == 0 or rp == 0)):
                out.append({"stim": st, "rep": rp, "start": start, "end": i - 1,
                            "n": i - start})
            start = i
    return out


def core(seg, frac=CORE_FRAC):
    n = seg["n"]
    k = max(1, int(round(n * frac)))
    a = seg["start"] + (n - k) // 2
    return a, a + k


def load_mat(path):
    m = sio.loadmat(path, squeeze_me=True, struct_as_record=False)
    base = os.path.basename(path)
    d = {k: m[k] for k in ("angles", "glove", "restimulus", "rerepetition", "stimulus",
                           "repetition", "subject", "exercise") if k in m}
    # identity = archive slot parsed from the filename (frozen rule)
    d["global_key"] = int(base.split("_")[0].lstrip("Ss"))
    d["name"] = base
    return d


def load_exercise_b():
    """Every file whose DATA is the 17-movement Exercise B protocol."""
    files = sorted(glob.glob(os.path.join(DB9_EXTRACTED, "s_*_angles", "*.mat")))
    keep = []
    for f in files:
        d = load_mat(f)
        segs = segments(d["restimulus"], d["rerepetition"])
        stims = sorted({s["stim"] for s in segs})
        if stims != list(range(1, 18)):
            continue
        idx = {}
        for sg in segs:
            idx.setdefault(sg["stim"], []).extend(range(*core(sg)))
        if 6 not in idx or 11 not in idx:
            continue
        keep.append({"name": d["name"], "subject": d["global_key"],
                     "angles": d["angles"], "idx": idx})
    return keep


def collect(fl, cols, keep_ids):
    Xs, ys, ss, fs = [], [], [], []
    seg = 0
    for r in fl:
        for st in keep_ids:
            if st not in r["idx"]:
                continue
            a = np.array(r["idx"][st])
            ang = r["angles"][a, :][:, cols]
            ok = np.isfinite(ang).all(axis=1)
            if not ok.any():
                continue
            ang = ang[ok]
            if SEG_CAP and ang.shape[0] > SEG_CAP:
                pick = np.linspace(0, ang.shape[0] - 1, SEG_CAP).astype(int)
                ang = ang[pick]
            Xs.append(np.deg2rad(ang))
            ys.append(np.full(ang.shape[0], st, dtype=np.int16))
            ss.append(np.full(ang.shape[0], r["subject"], dtype=np.int32))
            fs.append(np.full(ang.shape[0], seg, dtype=np.int32))
            seg += 1
    return (np.vstack(Xs), np.concatenate(ys), np.concatenate(ss), np.concatenate(fs))


def loso_scores(X, y, s):
    """Frozen LOSO: train-fold-only z-score + LinearDiscriminantAnalysis() defaults.

    Returns (pred, score_matrix) with score columns ordered by sorted classes.
    """
    pred = np.full(y.shape, -1, dtype=np.int16)
    classes = np.unique(y)
    scores = np.full((y.size, classes.size), np.nan, dtype=np.float64)
    for k in np.unique(s):
        te = s == k
        tr = ~te
        Xtr = X[tr].copy()
        mu = Xtr.mean(0)
        sd = Xtr.std(0)
        sd = np.where(sd > 0, sd, 1.0)
        Xtr -= mu
        Xtr /= sd
        m = LinearDiscriminantAnalysis()
        m.fit(Xtr, y[tr])
        Xte = X[te].copy()
        Xte -= mu
        Xte /= sd
        pred[te] = m.predict(Xte).astype(np.int16)
        sc = m.decision_function(Xte)
        scores[te] = sc[:, [int(np.flatnonzero(m.classes_ == c)[0]) for c in classes]]
    return pred, scores, classes


# --------------------------------------------------------------------------
# emg2pose side — GT only, frozen 50 Hz reduction
# --------------------------------------------------------------------------

def emg2pose_blocks():
    """All GT-valid 50 Hz analysis samples from the local mini corpus."""
    files = sorted(glob.glob(os.path.join(EMG2POSE_MINI, "*.hdf5")))
    xs, blocks, meta = [], [], []
    stored_rows = 0
    valid_rows = 0
    for f in files:
        with h5py.File(f, "r") as h:
            g = h["emg2pose"]
            attrs = dict(g.attrs)
            ds = g["timeseries"]
            n = ds.shape[0]
            ja = ds["joint_angles"][:]
        stored_rows += n
        # IK failure = all-zero row over all 20 dims (official semantics)
        row_valid = ~np.all(np.isclose(ja, 0.0), axis=1)
        valid_rows += int(row_valid.sum())

        nb = n // POSE_STRIDE
        usable = nb * POSE_STRIDE
        blk = ja[:usable].reshape(nb, POSE_STRIDE, ja.shape[1]).mean(axis=1)
        blk_valid = row_valid[:usable].reshape(nb, POSE_STRIDE).all(axis=1)

        sel = blk[:, TRUSTED8_SRC_IDX]
        xs.append(sel[blk_valid])
        blocks.append((f, attrs, int(blk_valid.sum()), np.flatnonzero(blk_valid)))
        meta.append({
            "file": os.path.basename(f),
            "recording": f.split("recording-")[1].split("_")[0],
            "side": attrs["side"],
            "stage": attrs["stage"],
            "stored_rows": int(n),
            "valid_rows": int(row_valid.sum()),
            "ik_failure_rows": int((~row_valid).sum()),
            "blocks": int(nb),
            "valid_blocks": int(blk_valid.sum()),
        })
    X = np.vstack(xs) if xs else np.zeros((0, 8))
    return X, blocks, meta, stored_rows, valid_rows, len(files)


# --------------------------------------------------------------------------
# Diagnostics
# --------------------------------------------------------------------------

def cat(arrs):
    """Concatenate, tolerating files that contributed a single analysis sample."""
    arrs = [np.atleast_1d(a) for a in arrs]
    return np.concatenate(arrs) if arrs else np.zeros(0)


def occupancy(pred, classes):
    n = pred.size
    fr = {int(c): float((pred == c).sum()) / n for c in classes}
    p = np.array([fr[int(c)] for c in classes])
    p_safe = np.where(p > 0, p, 1.0)
    ent = float(-(p * np.log2(p_safe)).sum())
    return fr, ent, float(p.max())


def margin_stats(marg):
    if marg.size == 0:
        return {k: None for k in ("median", "p25", "p75", "iqr", "p05", "p95",
                                  "min", "max", "frac_le_zero")}
    q = np.percentile(marg, [5, 25, 75, 95])
    return {"median": float(np.median(marg)), "p25": float(q[1]), "p75": float(q[2]),
            "iqr": float(q[2] - q[1]), "p05": float(q[0]), "p95": float(q[3]),
            "min": float(marg.min()), "max": float(marg.max()),
            "frac_le_zero": float((marg <= 0).mean())}


def temporal(pred_seqs):
    """pred_seqs: list of per-file contiguous predicted-label arrays."""
    sw = 0
    tot = 0
    durs = []
    for p in pred_seqs:
        if p.size < 2:
            if p.size == 1:
                durs.append(1)
            continue
        ch = np.flatnonzero(p[1:] != p[:-1]) + 1
        sw += int(ch.size)
        tot += int(p.size - 1)
        bounds = np.concatenate(([0], ch, [p.size]))
        durs.extend(np.diff(bounds).tolist())
    d = np.array(durs) if durs else np.zeros(0)
    return {
        "n_transitions": tot,
        "n_switches": sw,
        "switch_rate_per_sample": float(sw / tot) if tot else None,
        "n_runs": int(d.size),
        "median_dwell_blocks": float(np.median(d)) if d.size else None,
        "median_dwell_s": float(np.median(d) / 50.0) if d.size else None,
        "p25_dwell_blocks": float(np.percentile(d, 25)) if d.size else None,
        "p75_dwell_blocks": float(np.percentile(d, 75)) if d.size else None,
        "max_dwell_blocks": float(d.max()) if d.size else None,
    }


def main() -> int:
    t0 = time.time()
    log("=" * 78)
    log("GATE 2A — NATIVE-COORDINATE GT-ONLY FROZEN-HEAD DIAGNOSTIC")
    log("=" * 78)
    log(f"plan            : GATE2A_PLAN.md")
    log(f"plan SHA-256    : {PLAN_SHA}")
    log()

    tr = json.load(open(FROZEN_SUBSET, encoding="utf-8"))
    log(f"frozen subset   : {tr['name']}  keep={tr['keep_names']}")
    log(f"frozen subset sha256: {hashlib.sha256(open(FROZEN_SUBSET,'rb').read()).hexdigest()}")
    assert tr["keep_names"] == ["MCP1", "IP1", "MCP2_f", "PIP2", "MCP3_f", "MCP4_f",
                                "MCP5_f", "PIP5"], "frozen channel set changed"
    log(f"DB9 columns     : {TRUSTED8_DB9_COLS}")
    log(f"emg2pose idx    : {TRUSTED8_SRC_IDX}")
    log()

    # ---------------- DB9: rebuild the frozen corpus ----------------
    log("[1] DB9 frozen-corpus rebuild")
    fl = load_exercise_b()
    log(f"    Exercise-B-format files : {len(fl)}")
    log(f"    global keys             : {min(r['subject'] for r in fl)}..{max(r['subject'] for r in fl)}"
        f"  (distinct {len(set(r['subject'] for r in fl))})")
    X, y, s, fseg = collect(fl, TRUSTED8_DB9_COLS, AGREE_IDS)
    log(f"    X={X.shape}  classes={sorted(set(y.tolist()))}  subjects={len(set(s.tolist()))}")
    log(f"    segments (subject x movement x repetition): {len(set(fseg.tolist()))}")
    log()

    # ---------------- replication check (must reproduce the frozen record) -----
    log("[2] REPLICATION CHECK vs FINAL_VALIDATION.json .Q4_posture8")
    pred, scores, classes = loso_scores(X, y, s)
    ok = pred >= 0
    y2, p2 = y[ok], pred[ok]
    rep = {
        "n_frames": int(y2.size),
        "n_subjects": int(len(set(s[ok].tolist()))),
        "accuracy": float(accuracy_score(y2, p2)),
        "balanced_accuracy": float(balanced_accuracy_score(y2, p2)),
        "macro_f1": float(f1_score(y2, p2, average="macro", zero_division=0)),
        "per_class_recall": {int(c): float(r) for c, r in zip(
            np.unique(y2), recall_score(y2, p2, labels=np.unique(y2), average=None,
                                        zero_division=0))},
        "median_subject_ba": float(np.median(
            [balanced_accuracy_score(y2[s[ok] == u], p2[s[ok] == u])
             for u in np.unique(s[ok])])),
    }
    frozen = json.load(open(os.path.join(
        r"<PROJECT_ROOT>\audits\db9\channel_forensic"
        r"\artifacts\FINAL_VALIDATION.json"), encoding="utf-8"))["Q4_posture8"]["results"]["B_TRUSTED_DB9_POSE_v1"]
    checks = {
        "n_frames": (rep["n_frames"], frozen["n_frames"]),
        "n_subjects": (rep["n_subjects"], frozen["n_subjects"]),
        "accuracy": (round(rep["accuracy"], 6), round(frozen["accuracy"], 6)),
        "balanced_accuracy": (round(rep["balanced_accuracy"], 6),
                              round(frozen["balanced_accuracy"], 6)),
        "macro_f1": (round(rep["macro_f1"], 6), round(frozen["macro_f1"], 6)),
    }
    log(f"    {'quantity':<20}{'reconstructed':>16}{'frozen record':>16}  match")
    for k, (a, b) in checks.items():
        log(f"    {k:<20}{a:>16}{b:>16}  {'YES' if a == b else 'NO'}")
    for c in sorted(rep["per_class_recall"]):
        a = round(rep["per_class_recall"][c], 6)
        b = round(frozen["per_class_recall"][str(c)], 6)
        log(f"    recall class {c:<7}{a:>16}{b:>16}  {'YES' if a == b else 'NO'}")
    replication_exact = all(a == b for a, b in checks.values()) and all(
        round(rep["per_class_recall"][c], 6) == round(frozen["per_class_recall"][str(c)], 6)
        for c in rep["per_class_recall"])
    log(f"    REPLICATION: {'EXACT' if replication_exact else 'MISMATCH'}")
    log()

    # ---------------- DB9 comparator statistics ----------------
    db9_occ, db9_ent, db9_max = occupancy(p2, classes)
    db9_pred_occ, db9_pred_ent, db9_pred_max = occupancy(p2, classes)
    db9_marg = np.sort(scores[ok], axis=1)
    db9_margin = db9_marg[:, -1] - db9_marg[:, -2]
    db9_mstats = margin_stats(db9_margin)
    # DB9 temporal: contiguous frames inside each frozen segment, ordered as built
    db9_seqs = [p2[fseg[ok] == sg] for sg in np.unique(fseg[ok])]
    db9_temporal = temporal(db9_seqs)
    log(f"[3] DB9 comparator: pred-occupancy entropy {db9_pred_ent:.4f} bits, "
        f"max-class frac {db9_pred_max:.4f}, median margin {db9_mstats['median']:.4f}, "
        f"switch rate {db9_temporal['switch_rate_per_sample']:.4f}, "
        f"median dwell {db9_temporal['median_dwell_blocks']:.0f} frames")
    log(f"    (DB9 true-label occupancy entropy for reference: {db9_ent:.4f} bits)")
    log()

    # ---------------- aggregate head trained on all 77 ----------------
    log("[4] Aggregate head (all 77 DB9 participants) — the object applied to emg2pose")
    mu = X.mean(0)
    sd = X.std(0)
    sd = np.where(sd > 0, sd, 1.0)
    Xz = (X - mu) / sd
    head = LinearDiscriminantAnalysis()
    head.fit(Xz, y)
    priors = {int(c): round(float(p), 6) for c, p in zip(head.classes_, head.priors_)}
    log(f"    train frames      : {X.shape[0]}")
    log(f"    class priors      : {priors}")
    log(f"    standardisation mu: {np.round(mu, 4).tolist()}")
    log(f"    standardisation sd: {np.round(sd, 4).tolist()}")
    log(f"    LDA defaults      : solver={head.solver} shrinkage={head.shrinkage}")
    log()

    # ---------------- emg2pose GT ----------------
    log("[5] emg2pose GT (native values, frozen 50 Hz block reduction)")
    E, blocks, meta, stored_rows, valid_rows, nfiles = emg2pose_blocks()
    log(f"    files             : {nfiles}")
    log(f"    stored rows       : {stored_rows}")
    log(f"    GT-valid rows     : {valid_rows}  (IK-failure {stored_rows-valid_rows})")
    log(f"    analysis samples  : {E.shape[0]}   at 50 Hz (block mean of 40 rows)")
    sides = Counter(m["side"] for m in meta)
    log(f"    sides             : {dict(sides)}")
    log(f"    stages            : {len(set(m['stage'] for m in meta))}")
    log()

    Ez = (E - mu) / sd
    epred = head.predict(Ez).astype(np.int16)
    esc = head.decision_function(Ez)
    esc = esc[:, [int(np.flatnonzero(head.classes_ == c)[0]) for c in classes]]
    esort = np.sort(esc, axis=1)
    emargin = esort[:, -1] - esort[:, -2]
    etop2 = np.argsort(-esc, axis=1)[:, :2]
    cls_list = [int(c) for c in classes]
    i4, i5 = cls_list.index(4), cls_list.index(5)
    c45 = {i4, i5}

    occ, ent, maxfrac = occupancy(epred, classes)
    mstats = margin_stats(emargin)
    log("[6] PRIMARY DIAGNOSTICS")
    log(f"    class occupancy   : " + " ".join(
        f"{int(c)}:{occ[int(c)]:.4f}" for c in classes))
    log(f"    occupancy entropy : {ent:.4f} bits (max {np.log2(len(classes)):.4f})")
    log(f"    max-class fraction: {maxfrac:.4f}  (class {int(classes[int(np.argmax([occ[int(c)] for c in classes]))])})")
    log(f"    margin median     : {mstats['median']:.4f}  IQR [{mstats['p25']:.4f}, {mstats['p75']:.4f}]"
        f"  p05 {mstats['p05']:.4f}  p95 {mstats['p95']:.4f}")
    log(f"    margin <= 0 frac  : {mstats['frac_le_zero']:.4f}")
    log()

    # per-file sequences for temporal stats (blocks were emitted in file order)
    epred_seqs = []
    per_file_rows = []
    cursor = 0
    for fpath, attrs, nvb, valid_idx in blocks:
        seg_pred = epred[cursor:cursor + nvb]
        seg_marg = emargin[cursor:cursor + nvb]
        seg_occ, seg_ent, seg_max = occupancy(seg_pred, classes)
        per_file_rows.append({
            "file": os.path.basename(fpath), "side": attrs["side"], "stage": attrs["stage"],
            "n_valid_blocks": int(nvb), "occupancy": seg_occ, "entropy_bits": seg_ent,
            "max_class_fraction": seg_max,
            "median_margin": float(np.median(seg_marg)) if seg_marg.size else None,
            "dominant_class": int(max(seg_occ, key=seg_occ.get)) if nvb else None,
            "class4_fraction": float((seg_pred == 4).mean()) if nvb else None,
        })
        epred_seqs.append(seg_pred)
        cursor += nvb
    assert cursor == E.shape[0], (cursor, E.shape[0])

    etemporal = temporal(epred_seqs)
    log("[7] TEMPORAL STRUCTURE (contiguous per-file sequences at 50 Hz)")
    log(f"    transitions       : {etemporal['n_transitions']}")
    log(f"    switches          : {etemporal['n_switches']}")
    log(f"    switch rate       : {etemporal['switch_rate_per_sample']:.4f} per sample")
    log(f"    median dwell      : {etemporal['median_dwell_blocks']:.0f} blocks "
        f"({etemporal['median_dwell_s']:.3f} s)")
    log(f"    DB9 comparator    : rate {db9_temporal['switch_rate_per_sample']:.4f}, "
        f"dwell {db9_temporal['median_dwell_blocks']:.0f} frames")
    log()

    # side stratification
    side_stats = {}
    for sd_ in ("left", "right"):
        idxs = [i for i, m in enumerate(meta) if m["side"] == sd_]
        if not idxs:
            continue
        sl = cat([epred_seqs[i] for i in idxs])
        sm = cat([emargin[i] for i in idxs])
        so, se, smx = occupancy(sl, classes)
        side_stats[sd_] = {
            "n_samples": int(sl.size), "n_files": len(idxs),
            "occupancy": so, "entropy_bits": se, "max_class_fraction": smx,
            "margin": margin_stats(sm),
            "dominant_class": int(max(so, key=so.get)),
            "class4_fraction": float((sl == 4).mean()),
            "temporal": temporal([epred_seqs[i] for i in idxs]),
        }
        log(f"[8] SIDE {sd_:<6}: n={sl.size}  entropy {se:.4f}  maxfrac {smx:.4f} "
            f"dom class {side_stats[sd_]['dominant_class']}  median margin {np.median(sm):.4f}  "
            f"switch {side_stats[sd_]['temporal']['switch_rate_per_sample']:.4f}")
    log()

    # stage stratification
    stage_rows = []
    for st in sorted(set(m["stage"] for m in meta)):
        idxs = [i for i, m in enumerate(meta) if m["stage"] == st]
        sl = cat([epred_seqs[i] for i in idxs])
        sm = cat([emargin[i] for i in idxs])
        so, se, smx = occupancy(sl, classes)
        dom = int(max(so, key=so.get))
        st_side = sorted(set(meta[i]["side"] for i in idxs))
        stage_rows.append({
            "stage": st, "sides": "|".join(st_side), "n_files": len(idxs),
            "n_samples": int(sl.size), "entropy_bits": se,
            "dominant_class": dom, "dominant_class_fraction": so[dom],
            "median_margin": float(np.median(sm)) if sm.size else None,
            "class4_fraction": float((sl == 4).mean()),
            **{f"class{c}_fraction": so[c] for c in classes},
        })
        log(f"[9] STAGE {st[:44]:<44} n={sl.size:>7} dom={dom} "
            f"frac={so[dom]:.3f} ent={se:.3f} c4={so[4]:.3f} c5={so[5]:.3f}")
    log()

    # class 4/5
    c4f = float((epred == 4).mean())
    c4m = emargin[epred == 4]
    pair45 = float(np.mean([set(etop2[i].tolist()) == c45 for i in range(etop2.shape[0])]))
    sep45 = esc[:, i4] - esc[:, i5]
    c45_stats = {
        "class4_fraction": c4f,
        "class4_margin": margin_stats(c4m),
        "class5_fraction": float((epred == 5).mean()),
        "top2_pair_is_4_5_fraction": pair45,
        "score4_minus_score5": {
            "median": float(np.median(sep45)),
            "mean": float(sep45.mean()),
            "frac_positive": float((sep45 > 0).mean()),
        },
        "stage_wise_class4": {r["stage"]: r["class4_fraction"] for r in stage_rows},
    }
    log(f"[10] CLASS 4/5: class4 frac {c4f:.4f}  class5 frac {c45_stats['class5_fraction']:.4f}")
    log(f"     class4 margin median {c45_stats['class4_margin']['median']:.4f}")
    log(f"     top2 pair == {{4,5}} fraction {pair45:.4f}")
    log(f"     score4-score5 median {c45_stats['score4_minus_score5']['median']:.4f} "
        f"(frac > 0: {c45_stats['score4_minus_score5']['frac_positive']:.4f})")
    log()

    # ---------------- decision ----------------
    log("[11] DECISION (rule fixed in the plan before any output)")
    reasons = []
    cls_sorted = sorted(occ, key=occ.get, reverse=True)
    top_fracs = [occ[c] for c in cls_sorted]
    collapse_global = (sum(top_fracs[:DEGEN_COLLAPSE_MAXCLASSES]) > DEGEN_COLLAPSE_FRAC)
    stage_doms = set(r["dominant_class"] for r in stage_rows)
    collapse_everywhere = collapse_global and len(stage_doms) <= DEGEN_COLLAPSE_MAXCLASSES and len(
        set(side_stats[s]["dominant_class"] for s in side_stats)) <= DEGEN_COLLAPSE_MAXCLASSES
    if collapse_everywhere:
        reasons.append(f"collapse: <= {DEGEN_COLLAPSE_MAXCLASSES} classes take "
                       f"{sum(top_fracs[:DEGEN_COLLAPSE_MAXCLASSES]):.4f} and this holds in every "
                       f"stage and both sides")
    if etemporal["switch_rate_per_sample"] is not None and \
            etemporal["switch_rate_per_sample"] > DEGEN_SWITCH_RATE:
        reasons.append(f"switch rate {etemporal['switch_rate_per_sample']:.4f} > {DEGEN_SWITCH_RATE}")
    if mstats["frac_le_zero"] > DEGEN_BAD_MARGIN_FRAC:
        reasons.append(f"margin <= 0 for {mstats['frac_le_zero']:.4f} > {DEGEN_BAD_MARGIN_FRAC}")
    if pair45 > DEGEN_C45_FRAC:
        reasons.append(f"top2 == {{4,5}} for {pair45:.4f} > {DEGEN_C45_FRAC}")

    ambig = []
    if ent < AMBIG_ENTROPY_BITS:
        ambig.append(f"occupancy entropy {ent:.4f} bits < {AMBIG_ENTROPY_BITS}")
    if len(set(side_stats[s]["dominant_class"] for s in side_stats)) > 1:
        ambig.append("dominant class differs between left and right")
    if len(stage_doms) == 1:
        ambig.append("identical dominant class for all stages")

    if reasons:
        decision = "DEGENERATE"
    elif ambig:
        decision = "AMBIGUOUS"
    else:
        decision = "STRUCTURED_NONDEGENERATE"
    log(f"     DEGENERATE triggers : {reasons if reasons else 'none'}")
    log(f"     AMBIGUOUS triggers  : {ambig if ambig else 'none'}")
    log(f"     GATE2A DECISION     : {decision}")
    log()

    # ---------------- artifacts ----------------
    behavior = {
        "artifact": "GT_HEAD_BEHAVIOR.json",
        "gate": "PHASE 1 / GATE 2A — native-coordinate GT-only frozen-head diagnostic",
        "plan_sha256": PLAN_SHA,
        "class": "EXPLORATORY DIAGNOSTIC",
        "question": "does the frozen DB9 posture head exhibit structured, non-degenerate, "
                    "further-studyable behaviour on native-coordinate emg2pose GT pose?",
        "head": {
            "instantiation": "RECONSTRUCTED (no serialized head artifact exists; searched "
                             "workspace-wide for .joblib/.pkl/.pickle/.onnx/.pt/.pth/.sav)",
            "applied_object": "one aggregate LDA trained on all 77 DB9 participants with the "
                              "frozen protocol; every emg2pose frame is out-of-sample",
            "protocol": "TRUSTED_DB9_POSE_v1 (8 channels by name, columns "
                        f"{TRUSTED8_DB9_COLS}), Exercise-B movement ids 1-8, central 60% of "
                        "each restimulus x rerepetition segment, per-segment cap 200 via "
                        "linspace, np.deg2rad, train-fold z-score (sd>0 guard), "
                        "sklearn LinearDiscriminantAnalysis() with all defaults, LOSO by "
                        "archive-slot global key",
            "standardisation_source": "DB9 only (never emg2pose)",
            "random_seed": None,
            "tuning_performed": False,
            "train_frames": int(X.shape[0]),
            "train_class_priors": {int(c): float(p) for c, p in zip(head.classes_, head.priors_)},
            "standardisation_mu": mu.tolist(),
            "standardisation_sd": sd.tolist(),
            "lda_solver": head.solver,
            "lda_shrinkage": head.shrinkage,
        },
        "replication_check": {
            "against": "FINAL_VALIDATION.json .Q4_posture8.results.B_TRUSTED_DB9_POSE_v1",
            "reconstructed": rep,
            "exact": bool(replication_exact),
            "detail": {k: {"reconstructed": a, "frozen": b, "match": a == b}
                       for k, (a, b) in checks.items()},
        },
        "frozen_subset_sha256": hashlib.sha256(open(FROZEN_SUBSET, "rb").read()).hexdigest(),
        "emg2pose_input": {
            "source": "GROUND TRUTH joint_angles only; predicted pose never read",
            "files": nfiles,
            "participants": 1,
            "sessions": 1,
            "sides": dict(sides),
            "stages": len(set(m["stage"] for m in meta)),
            "stored_rows": stored_rows,
            "gt_valid_rows": valid_rows,
            "ik_failure_rows": stored_rows - valid_rows,
            "analysis_samples": int(E.shape[0]),
            "analysis_sampling_rate_hz": 50.0,
            "reduction": f"non-overlapping {POSE_STRIDE}-row block mean; block valid only if all "
                         f"{POSE_STRIDE} rows are GT-valid; trailing remainder dropped",
            "reduction_provenance": "bridge_audit/run_bridge_audit.py POSE_STRIDE=40 with "
                                    "EMG_RATE=2000 ('the model's native 50 Hz update cadence')",
        },
        "class_occupancy": {"fractions": occ, "entropy_bits": ent,
                            "max_class_fraction": maxfrac,
                            "max_entropy_bits": float(np.log2(len(classes)))},
        "margin_structure": mstats,
        "temporal_structure": etemporal,
        "side_stratification": side_stats,
        "stage_stratification": stage_rows,
        "class4_class5": c45_stats,
        "db9_comparator": {
            "n_frames": int(y2.size), "n_subjects": int(len(set(s[ok].tolist()))),
            "predicted_occupancy": db9_pred_occ,
            "occupancy_entropy_bits": db9_pred_ent,
            "max_class_fraction": db9_pred_max,
            "margin_structure": db9_mstats,
            "temporal_structure": db9_temporal,
            "per_class_recall": rep["per_class_recall"],
            "frozen_balanced_accuracy": frozen["balanced_accuracy"],
            "frozen_macro_f1": frozen["macro_f1"],
        },
        "notation": {
            "primary_margin": "top1_decision_function - top2_decision_function, native "
                              "discriminant units; comparable between the emg2pose and DB9 "
                              "computations because both use the same head definition",
            "entropy_units": "bits; maximum log2(n_classes) = 3.0",
            "stage_labels": "activity labels, NOT posture ground truth",
        },
        "firewall": {
            "PREDICTED_POSE_USED": "NO", "GT_VS_PRED_AGREEMENT": "NOT RUN",
            "EMG_INFERENCE_RUN": "NO", "UNKNOWN_GATE_CREATED": "NO",
            "CALIBRATION_FITTED": "NO", "SEMANTIC_ACCURACY_CLAIMED": "NO",
            "OFFSET_OR_SCALE_FITTED": "NO", "SUBSET_SELECTED": "NO",
            "MODEL_TUNED": "NO", "SERVER_USED": "NO", "GPU_USED": "NO",
            "FULL_CORPUS_DOWNLOADED": "NO",
        },
        "per_file": per_file_rows,
    }
    with open(os.path.join(ART, "GT_HEAD_BEHAVIOR.json"), "w", encoding="utf-8") as fh:
        json.dump(behavior, fh, indent=2, ensure_ascii=False)

    import csv as _csv
    with open(os.path.join(ART, "GT_HEAD_BEHAVIOR_BY_STAGE.csv"), "w", encoding="utf-8",
              newline="") as fh:
        cols = ["stage", "sides", "n_files", "n_samples", "entropy_bits", "dominant_class",
                "dominant_class_fraction", "median_margin", "class4_fraction"] + \
               [f"class{c}_fraction" for c in classes]
        w = _csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in stage_rows:
            w.writerow(r)

    with open(os.path.join(ART, "GT_HEAD_BEHAVIOR_BY_SIDE.csv"), "w", encoding="utf-8",
              newline="") as fh:
        cols = ["side", "n_files", "n_samples", "entropy_bits", "max_class_fraction",
                "dominant_class", "class4_fraction", "margin_median", "margin_p25",
                "margin_p75", "margin_p05", "margin_p95", "switch_rate_per_sample",
                "median_dwell_blocks", "median_dwell_s"] + \
               [f"class{c}_fraction" for c in classes]
        w = _csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for sd_, v in side_stats.items():
            row = {"side": sd_, "n_files": v["n_files"], "n_samples": v["n_samples"],
                   "entropy_bits": v["entropy_bits"],
                   "max_class_fraction": v["max_class_fraction"],
                   "dominant_class": v["dominant_class"],
                   "class4_fraction": v["class4_fraction"],
                   "margin_median": v["margin"]["median"], "margin_p25": v["margin"]["p25"],
                   "margin_p75": v["margin"]["p75"], "margin_p05": v["margin"]["p05"],
                   "margin_p95": v["margin"]["p95"],
                   "switch_rate_per_sample": v["temporal"]["switch_rate_per_sample"],
                   "median_dwell_blocks": v["temporal"]["median_dwell_blocks"],
                   "median_dwell_s": v["temporal"]["median_dwell_s"]}
            for c in classes:
                row[f"class{c}_fraction"] = v["occupancy"][c]
            w.writerow(row)

    decision_art = {
        "artifact": "GATE2A_DECISION.json",
        "gate": "PHASE 1 / GATE 2A",
        "plan_sha256": PLAN_SHA,
        "GATE2A_DECISION": decision,
        "degenerate_triggers": reasons,
        "ambiguous_triggers": ambig,
        "declared_thresholds": {
            "collapse_frac": DEGEN_COLLAPSE_FRAC,
            "collapse_max_classes": DEGEN_COLLAPSE_MAXCLASSES,
            "switch_rate": DEGEN_SWITCH_RATE,
            "bad_margin_frac": DEGEN_BAD_MARGIN_FRAC,
            "class45_frac": DEGEN_C45_FRAC,
            "ambiguity_entropy_bits": AMBIG_ENTROPY_BITS,
        },
        "evidence": {
            "occupancy_entropy_bits": ent,
            "max_class_fraction": maxfrac,
            "margin_median": mstats["median"],
            "margin_iqr": mstats["iqr"],
            "margin_frac_le_zero": mstats["frac_le_zero"],
            "switch_rate_per_sample": etemporal["switch_rate_per_sample"],
            "median_dwell_blocks": etemporal["median_dwell_blocks"],
            "median_dwell_s": etemporal["median_dwell_s"],
            "class4_fraction": c4f,
            "top2_pair_4_5_fraction": pair45,
            "n_distinct_stage_dominant_classes": len(stage_doms),
            "n_stages": len(stage_rows),
            "n_side_dominant_classes": len(set(side_stats[s]["dominant_class"]
                                              for s in side_stats)),
        },
        "db9_comparator_summary": {
            "occupancy_entropy_bits": db9_pred_ent,
            "max_class_fraction": db9_pred_max,
            "margin_median": db9_mstats["median"],
            "switch_rate_per_sample": db9_temporal["switch_rate_per_sample"],
            "median_dwell_blocks": db9_temporal["median_dwell_blocks"],
        },
        "meaning": {
            "STRUCTURED_NONDEGENERATE": "the frozen head exhibits sufficiently varied and "
                                        "temporally coherent behaviour on native emg2pose GT to "
                                        "justify a separately designed semantic validation step. "
                                        "It does NOT mean the behaviour is correct.",
            "DEGENERATE": "native-coordinate use of the frozen head is not currently "
                          "scientifically useful; the failure may reflect unresolved "
                          "calibration/domain mismatch rather than the Common Pose concept. "
                          "Do not rescue with fitted calibration.",
            "AMBIGUOUS": "report the ambiguity and the smallest discriminating follow-up.",
        },
        "not_claimed": [
            "posture accuracy", "balanced accuracy", "semantic correctness",
            "sensitivity / specificity", "transfer accuracy",
            "any cross-source calibration equivalence",
            "that structured output implies correct output",
        ],
        "firewall": behavior["firewall"],
        "next_allowed_step": {
            "STRUCTURED_NONDEGENERATE": "Design a fresh prospective GT semantic-applicability "
                                        "validation before any GT-vs-PRED substitution claim.",
            "DEGENERATE": "Stop native-coordinate substitution; do not fit calibration from "
                          "task outputs.",
            "AMBIGUOUS": "Run only the specified minimal diagnostic needed to distinguish "
                         "degeneracy from usable structure.",
        }[decision],
    }
    with open(os.path.join(ART, "GATE2A_DECISION.json"), "w", encoding="utf-8") as fh:
        json.dump(decision_art, fh, indent=2, ensure_ascii=False)

    with open(os.path.join(LOGS, "gate2a_stdout.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(log_lines) + "\n")

    log(f"elapsed {time.time()-t0:.1f}s")
    log("artifacts written: GT_HEAD_BEHAVIOR.json, GT_HEAD_BEHAVIOR_BY_STAGE.csv, "
        "GT_HEAD_BEHAVIOR_BY_SIDE.csv, GATE2A_DECISION.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
