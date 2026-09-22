#!/usr/bin/env python
"""Adversarial diagnostics for the canonical16 posture result.

A near-perfect cross-subject score on the first attempt is a claim that has to
survive attempts to break it, not a result to report.  This script tries to
falsify the primary result in five independent ways.

D1. **Leave-one-subject-out.** The frozen split uses 3 test subjects. If the
    score depends on which three, it is not a cross-subject property. LOSO
    repeats the evaluation 22 times, holding out each subject in turn.

D2. **Single-feature separability.** If one canonical16 channel alone reaches
    near-perfect accuracy, the task is not really 16-dimensional and the result
    says much less than it appears to.

D3. **Movement-order / drift leak.** The DB9 protocol was NOT randomised:
    movements were performed in a fixed order, so movement identity is
    confounded with time-within-session. If the glove drifts, the rest periods
    between movements will drift too, and a classifier could key on "where in
    the session" rather than "what the hand looks like". The rest blocks give a
    label-free probe of exactly that drift.

D4. **Label-permutation control.** Shuffling the labels must destroy the score;
    if it does not, something is leaking.

D5. **What actually separates the negative-control pair?** The B5/B8 pair was
    pre-registered as expected-hard because canonical16 removes the finger-spread
    DOF. It scored 100%, which contradicts the pre-registration. Either the
    expectation was wrong or the separation comes from somewhere unexpected.
    The per-channel profile says which.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_ROOT, "posture_decoder"))
sys.path.insert(0, os.path.join(_ROOT, "representation"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

import db9_to_canonical16 as d2c  # noqa: E402
from db9 import labels  # noqa: E402
from db9.loader import (  # noqa: E402
    db9_exercise_index,
    discover_unpacked,
    load_recording,
    resolve_subject,
)

PRIMARY = (1, 2, 3, 4, 6, 7)
NEG_CONTROL = (5, 8)
SEED = 20260101


def loso(X, y, subj, model_name="lda"):
    """Leave-one-subject-out accuracy; every subject is test exactly once."""
    accs, rows = [], []
    for s in sorted(set(subj.tolist())):
        te = subj == s
        tr = ~te
        if len(set(y[tr].tolist())) < 2:
            continue
        sc = StandardScaler().fit(X[tr])
        if model_name == "lda":
            m = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
        else:
            m = LogisticRegression(max_iter=5000, random_state=SEED)
        m.fit(sc.transform(X[tr]), y[tr])
        p = m.predict(sc.transform(X[te]))
        a = float((p == y[te]).mean())
        accs.append(a)
        rows.append({"subject": int(s), "n": int(te.sum()), "accuracy": a})
    return float(np.mean(accs)), float(np.std(accs)), rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--extracted", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fig-dir", default="")
    args = ap.parse_args()

    z = np.load(os.path.join(args.data_dir, "representative_postures.npz"))
    X16 = z["X_canonical16"]
    y = z["movement"]
    subj = z["subject"]
    names = list(d2c.canonical16_names())

    out: dict = {"n_repetitions": int(len(y)), "canonical16_names": names}

    # ---------------------------------------------------------------- D1
    print("=" * 78)
    print("D1  LEAVE-ONE-SUBJECT-OUT (primary 6-class)")
    print("=" * 78)
    pm = np.isin(y, PRIMARY)
    for model_name in ("lda", "logreg"):
        m, s, rows = loso(X16[pm], y[pm], subj[pm], model_name)
        print(f"  {model_name:<8} mean accuracy over {len(rows)} held-out subjects "
              f"= {m:.4f} +- {s:.4f}")
        worst = sorted(rows, key=lambda r: r["accuracy"])[:4]
        print(f"           worst subjects: "
              + ", ".join(f"s{r['subject']}={r['accuracy']:.2f}" for r in worst))
        out[f"loso_primary6_{model_name}"] = {
            "mean_accuracy": m, "std": s, "per_subject": rows
        }

    # ---------------------------------------------------------------- D2
    print()
    print("=" * 78)
    print("D2  SINGLE-CHANNEL SEPARABILITY (primary 6-class)")
    print("=" * 78)
    single = []
    for i, n in enumerate(names):
        m, s, _ = loso(X16[pm][:, [i]], y[pm], subj[pm], "lda")
        single.append({"channel": n, "index": i, "loso_accuracy": m})
    single.sort(key=lambda d: -d["loso_accuracy"])
    for r in single[:6]:
        print(f"  {r['channel']:<24} LOSO acc = {r['loso_accuracy']:.4f}")
    print(f"  ... worst channel: {single[-1]['channel']} "
          f"{single[-1]['loso_accuracy']:.4f}")
    out["single_channel_loso"] = single

    # ---------------------------------------------------------------- D3
    print()
    print("=" * 78)
    print("D3  MOVEMENT-ORDER / DRIFT LEAK PROBE (rest periods)")
    print("=" * 78)
    drift = rest_drift_probe(args.extracted, X16, y, subj)
    print(f"  within-subject drift of the rest posture over the session,")
    print(f"  measured per channel and compared with the between-movement spread:")
    print(f"    median |drift| across rest blocks / between-movement spread "
          f"= {drift['median_ratio']:.4f}")
    print(f"    worst channel: {drift['worst_channel']} ratio="
          f"{drift['worst_ratio']:.4f}")
    verdict = ("SMALL: posture is far more stable than the movement signal, so a "
               "time-within-session shortcut cannot explain the result"
               if drift["median_ratio"] < 0.35 else
               "LARGE: movement identity is confounded with session time; the "
               "result may be partly a drift shortcut")
    print(f"    => {verdict}")
    out["drift_probe"] = drift

    # ---------------------------------------------------------------- D4
    print()
    print("=" * 78)
    print("D4  LABEL-PERMUTATION CONTROL (primary 6-class, LOSO)")
    print("=" * 78)
    rng = np.random.default_rng(SEED)
    perm_accs = []
    for _ in range(20):
        yp = y[pm].copy()
        # permute WITHIN subject so the permutation does not break the
        # subject structure that the split relies on
        for s in np.unique(subj[pm]):
            m = subj[pm] == s
            yp[m] = rng.permutation(yp[m])
        m, _, _ = loso(X16[pm], yp, subj[pm], "lda")
        perm_accs.append(m)
    print(f"  permuted-label LOSO accuracy = {np.mean(perm_accs):.4f} "
          f"+- {np.std(perm_accs):.4f}  (chance = {1/len(PRIMARY):.4f})")
    print(f"  real-label LOSO accuracy      = "
          f"{out['loso_primary6_lda']['mean_accuracy']:.4f}")
    out["label_permutation"] = {
        "permuted_mean": float(np.mean(perm_accs)),
        "permuted_std": float(np.std(perm_accs)),
        "chance": 1.0 / len(PRIMARY),
    }

    # ---------------------------------------------------------------- D5
    print()
    print("=" * 78)
    print("D5  WHAT SEPARATES THE PRE-REGISTERED NEGATIVE-CONTROL PAIR B5 vs B8?")
    print("=" * 78)
    nc = np.isin(y, NEG_CONTROL)
    m5, m8 = y[nc] == 5, y[nc] == 8
    prof = []
    for i, n in enumerate(names):
        a, b = X16[nc][m5, i], X16[nc][m8, i]
        pooled = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2) + 1e-12
        prof.append({
            "channel": n, "mean_m5": float(a.mean()), "mean_m8": float(b.mean()),
            "abs_diff_rad": float(abs(a.mean() - b.mean())),
            "cohens_d": float(abs(a.mean() - b.mean()) / pooled),
        })
    prof.sort(key=lambda d: -d["cohens_d"])
    print("  largest standardised differences between B5 and B8:")
    for r in prof[:8]:
        print(f"    {r['channel']:<24} B5={np.degrees(r['mean_m5']):+7.1f} deg  "
              f"B8={np.degrees(r['mean_m8']):+7.1f} deg  |d|={r['cohens_d']:.2f}")
    print(f"  all 16 channels mean |d| = {np.mean([r['cohens_d'] for r in prof]):.2f}")
    out["negative_control_profile"] = prof

    # ---------------------------------------------------------------- figures
    if args.fig_dir:
        os.makedirs(args.fig_dir, exist_ok=True)
        fig, ax = plt.subplots(figsize=(9, 4.5))
        order = sorted(range(len(names)), key=lambda i: -abs(prof[i]["cohens_d"]))
        vals = [prof[i]["cohens_d"] for i in order]
        ax.bar([names[i].replace("_", "\n") for i in order], vals, color="#d62728")
        ax.set_ylabel("|Cohen's d| between B5 and B8")
        ax.set_title("What actually separates 'Abduction of all fingers' (B5)\n"
                     "from 'Adduction of extended fingers' (B8)")
        ax.tick_params(axis="x", labelsize=7)
        fig.tight_layout()
        fig.savefig(os.path.join(args.fig_dir, "negative_control_profile.png"), dpi=150)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar([r["channel"].replace("_", "\n") for r in single[:16]],
               [r["loso_accuracy"] for r in single[:16]], color="#1f77b4")
        ax.axhline(1 / 6, color="r", ls=":", label="chance")
        ax.axhline(out["loso_primary6_lda"]["mean_accuracy"], color="k", ls="--",
                   label="all 16 channels")
        ax.set_ylabel("LOSO accuracy")
        ax.set_title("Single-channel separability of the primary 6 classes")
        ax.tick_params(axis="x", labelsize=7)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(os.path.join(args.fig_dir, "single_channel_loso.png"), dpi=150)
        plt.close(fig)

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"\n[diagnostics] wrote {args.out}")
    return 0


def rest_drift_probe(extracted: str, X16, y, subj) -> dict:
    """How much does the REST posture drift across a session?

    Rest blocks are the only label-free probe of session-long drift.  For each
    subject we take the median rest posture inside every inter-movement gap,
    then measure how far those medians move from the subject's first one.  That
    drift is compared with the between-movement spread of the real postures: if
    drift were comparable, "which movement" could be recovered from "when in the
    session", and the classification result would be partly a shortcut.
    """
    per_channel_drift = [[] for _ in range(16)]
    per_channel_spread = [[] for _ in range(16)]

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
        # split the rest samples into contiguous blocks
        splits = np.flatnonzero(np.diff(rest_idx) != 1) + 1
        blocks = np.split(rest_idx, splits)
        blocks = [b for b in blocks if b.size >= 40]
        if len(blocks) < 4:
            continue
        meds = np.stack([np.median(c16[b], axis=0) for b in blocks])
        ref = meds[0]
        drift = np.abs(meds - ref).max(axis=0)          # per channel
        for i in range(16):
            per_channel_drift[i].append(float(drift[i]))

    # between-movement spread, from the representative postures
    pm = np.isin(y, PRIMARY)
    for i in range(16):
        means = [X16[pm & (y == c), i].mean() for c in PRIMARY]
        per_channel_spread[i].append(float(np.ptp(means)))

    ratios = []
    for i in range(16):
        d = np.median(per_channel_drift[i]) if per_channel_drift[i] else 0.0
        s = per_channel_spread[i][0] if per_channel_spread[i] else 1.0
        ratios.append(d / s if s > 1e-12 else 0.0)
    worst = int(np.argmax(ratios))
    names = list(d2c.canonical16_names())
    return {
        "definition": ("median |rest-posture drift from the first rest block| per "
                       "channel, divided by the between-movement spread of that "
                       "channel"),
        "per_channel_drift_rad": [float(np.median(v)) if v else 0.0
                                  for v in per_channel_drift],
        "per_channel_between_movement_spread_rad": [v[0] if v else 0.0
                                                    for v in per_channel_spread],
        "per_channel_ratio": ratios,
        "channel_names": names,
        "median_ratio": float(np.median(ratios)),
        "worst_channel": names[worst],
        "worst_ratio": float(ratios[worst]),
    }


if __name__ == "__main__":
    sys.exit(main())
