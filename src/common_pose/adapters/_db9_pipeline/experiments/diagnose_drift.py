#!/usr/bin/env python
"""Follow-up diagnostics: does session drift explain the result?

D3 in `diagnose_posture16.py` found that the glove's REST posture drifts over a
session by a median of ~45% of the between-movement spread.  Because the DB9
protocol was NOT randomised -- movements were performed in a fixed order -- that
drift is confounded with movement identity, and in principle a classifier could
score well partly by reading "how far into the session is this" instead of "what
does the hand look like".

This script settles it two ways.

D6. **Drift-corrected LOSO.**  Estimate each subject's drift trajectory from the
    REST blocks alone (no labels, no movement data), linearly interpolate it over
    the session, subtract it from every movement posture, and re-run
    leave-one-subject-out.  If accuracy survives, drift is not the driver.  This
    is a *diagnostic*, not a change to the frozen primary pipeline -- the primary
    result is reported uncorrected.

D7. **Drift-only predictor.**  Train a classifier that sees ONLY the label-free
    drift estimate at each movement's time.  That is the strongest possible
    version of the "session-time shortcut".  Its accuracy bounds how much of the
    real result drift could possibly explain.

D8. **Negative control without DIP.**  The B5/B8 pair turned out to be separated
    mostly by DIP extension (|Cohen's d| ~3.3), and DB9 warns DIP readings
    degrade for small hands.  Re-run the pair on canonical12_noDIP to see whether
    the separation survives without the least reliable sensors.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_ROOT, "posture_decoder"))
sys.path.insert(0, os.path.join(_ROOT, "representation"))

from sklearn.discriminant_analysis import LinearDiscriminantAnalysis  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

import db9_to_canonical16 as d2c  # noqa: E402
from db9.loader import (  # noqa: E402
    db9_exercise_index,
    discover_unpacked,
    load_recording,
    resolve_subject,
)

PRIMARY = (1, 2, 3, 4, 6, 7)


def loso_accuracy(X, y, subj) -> tuple[float, float, list]:
    accs, rows = [], []
    for s in sorted(set(subj.tolist())):
        te = subj == s
        tr = ~te
        if len(set(y[tr].tolist())) < 2:
            continue
        sc = StandardScaler().fit(X[tr])
        m = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
        m.fit(sc.transform(X[tr]), y[tr])
        p = m.predict(sc.transform(X[te]))
        a = float((p == y[te]).mean())
        accs.append(a)
        rows.append({"subject": int(s), "accuracy": a})
    return float(np.mean(accs)), float(np.std(accs)), rows


def build_drift_trajectories(extracted: str):
    """Per-subject, label-free drift estimate as a function of time.

    Returns ``{subject: (times, offsets)}`` where ``offsets`` is the median rest
    posture of each rest block minus the subject's first rest block.
    """
    traj: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    for slot, path in discover_unpacked(extracted):
        rec = load_recording(path)
        subject_id, _ = resolve_subject(slot, rec.subject, path)
        if db9_exercise_index(rec, subject_id) != 1:
            continue
        c16 = d2c.to_canonical16(rec.angles)
        rs = rec.restimulus
        rest_idx = np.flatnonzero(rs == 0)
        if rest_idx.size < 400:
            continue
        splits = np.flatnonzero(np.diff(rest_idx) != 1) + 1
        blocks = [b for b in np.split(rest_idx, splits) if b.size >= 40]
        if len(blocks) < 4:
            continue
        t = np.array([b.mean() / rec.n_samples for b in blocks])       # 0..1
        meds = np.stack([np.median(c16[b], axis=0) for b in blocks])
        traj[subject_id] = (t, meds - meds[0])
    return traj


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--extracted", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    z = np.load(os.path.join(args.data_dir, "representative_postures.npz"))
    X16, X12 = z["X_canonical16"], z["X_canonical12_noDIP"]
    y, subj = z["movement"], z["subject"]
    names = list(d2c.canonical16_names())
    out: dict = {}

    pm = np.isin(y, PRIMARY)
    base_mean, base_std, base_rows = loso_accuracy(X16[pm], y[pm], subj[pm])
    print("=" * 78)
    print("D6  DRIFT-CORRECTED LEAVE-ONE-SUBJECT-OUT")
    print("=" * 78)
    print(f"  baseline (uncorrected) LOSO = {base_mean:.4f} +- {base_std:.4f}")

    traj = build_drift_trajectories(args.extracted)
    print(f"  drift trajectories built for {len(traj)} subjects")

    # Rebuild the representative postures together with their session position,
    # so the drift estimate can be sampled at the right time.
    times: dict[tuple[int, int, int], float] = {}
    for slot, path in discover_unpacked(args.extracted):
        rec = load_recording(path)
        subject_id, _ = resolve_subject(slot, rec.subject, path)
        if db9_exercise_index(rec, subject_id) != 1:
            continue
        rs, rr = rec.restimulus, rec.rerepetition
        for lab in sorted(set(int(v) for v in np.unique(rs)) - {0}):
            for rep in sorted(set(int(v) for v in np.unique(rr[rs == lab])) - {0}):
                m = (rs == lab) & (rr == rep)
                idx = np.flatnonzero(m)
                if idx.size < 30:
                    continue
                n = idx.size
                third = n // 3
                central = idx[third: n - third]
                times[(subject_id, int(lab), int(rep))] = float(central.mean() / rec.n_samples)

    corrected = X16.copy()
    n_corrected = 0
    for i in range(len(y)):
        key = (int(subj[i]), int(y[i]), int(z["repetition"][i]))
        s = int(subj[i])
        if s not in traj or key not in times:
            continue
        t_grid, offsets = traj[s]
        t = times[key]
        off = np.stack([np.interp(t, t_grid, offsets[:, c]) for c in range(offsets.shape[1])])
        corrected[i] = X16[i] - off
        n_corrected += 1
    print(f"  drift removed from {n_corrected}/{len(y)} postures using REST blocks only")

    corr_mean, corr_std, corr_rows = loso_accuracy(corrected[pm], y[pm], subj[pm])
    print(f"  drift-corrected LOSO       = {corr_mean:.4f} +- {corr_std:.4f}  "
          f"(delta {corr_mean - base_mean:+.4f})")
    verdict = ("drift is NOT the driver: the score survives removing it entirely"
               if corr_mean > 0.90 else
               "CAUTION: the score drops materially once drift is removed, so part "
               "of the original result was a session-time shortcut")
    print(f"  => {verdict}")
    out["D6_drift_corrected_loso"] = {
        "baseline_mean": base_mean, "baseline_std": base_std,
        "corrected_mean": corr_mean, "corrected_std": corr_std,
        "delta": corr_mean - base_mean,
        "n_corrected": n_corrected,
        "method": ("per-subject drift trajectory estimated from REST blocks only, "
                   "linearly interpolated over normalised session time, subtracted "
                   "from every posture; diagnostic only"),
        "per_subject_baseline": base_rows, "per_subject_corrected": corr_rows,
        "verdict": verdict,
    }

    # ------------------------------------------------------------------ D7
    print()
    print("=" * 78)
    print("D7  DRIFT-ONLY PREDICTOR -- upper bound on the session-time shortcut")
    print("=" * 78)
    D = np.zeros_like(X16)
    ok = np.zeros(len(y), dtype=bool)
    for i in range(len(y)):
        s, key = int(subj[i]), (int(subj[i]), int(y[i]), int(z["repetition"][i]))
        if s in traj and key in times:
            t_grid, offsets = traj[s]
            t = times[key]
            D[i] = np.array([np.interp(t, t_grid, offsets[:, c])
                             for c in range(offsets.shape[1])])
            ok[i] = True
    mask = pm & ok
    d_mean, d_std, _ = loso_accuracy(D[mask], y[mask], subj[mask])
    print(f"  drift-estimate-only LOSO = {d_mean:.4f} +- {d_std:.4f} "
          f"(chance {1/len(PRIMARY):.4f}, n={int(mask.sum())})")
    print(f"  => drift alone carries {'substantial' if d_mean > 0.4 else 'little'} "
          f"movement information")
    out["D7_drift_only_loso"] = {"mean": d_mean, "std": d_std,
                                 "chance": 1 / len(PRIMARY), "n": int(mask.sum())}

    # ------------------------------------------------------------------ D8
    print()
    print("=" * 78)
    print("D8  NEGATIVE-CONTROL PAIR B5 vs B8 WITHOUT THE DIP CHANNELS")
    print("=" * 78)
    nc = np.isin(y, (5, 8))
    m16, s16, _ = loso_accuracy(X16[nc], y[nc], subj[nc])
    m12, s12, _ = loso_accuracy(X12[nc], y[nc], subj[nc])
    print(f"  canonical16      LOSO = {m16:.4f} +- {s16:.4f}")
    print(f"  canonical12_noDIP LOSO = {m12:.4f} +- {s12:.4f}")
    print(f"  => the B5/B8 separation {'survives' if m12 > 0.85 else 'largely rests on'} "
          f"the DIP channels")
    out["D8_negative_control_noDIP"] = {
        "canonical16_mean": m16, "canonical16_std": s16,
        "canonical12_noDIP_mean": m12, "canonical12_noDIP_std": s12,
        "interpretation": ("B5/B8 are separated mostly by DIP extension; if the "
                           "noDIP score collapses, the separation rests on the "
                           "channels DB9 flags as least reliable"),
    }

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"\n[follow-up] wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
