#!/usr/bin/env python
"""PHASE 6 addendum -- confidence / probability reporting.

The protocol asks for "confidence/probability where supported".  Every model in
the grid exposes `predict_proba`, and the frozen test run already stores those
posteriors, so this script turns them into the three things that actually matter
for a decoder that is meant to be trusted:

1. **Separation** -- how much more confident the model is when it is right than
   when it is wrong.  If those two distributions overlap heavily, the confidence
   number is decorative.
2. **Selective prediction** -- accuracy as a function of how much of the input
   the decoder is willing to answer.  This is the practical "say unknown instead
   of guessing" curve.
3. **Calibration** -- expected calibration error, i.e. whether a stated 0.9
   posterior really corresponds to ~90 % correctness.

It also reports the same for the pooled leave-one-subject-out predictions, which
are the reliable basis (3 test subjects is thin).
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

from db9 import labels  # noqa: E402

PRIMARY = (1, 2, 3, 4, 6, 7)


def separation(probs: np.ndarray, correct: np.ndarray) -> dict:
    conf = probs.max(axis=1)
    return {
        "mean_confidence_all": float(conf.mean()),
        "mean_confidence_correct": float(conf[correct].mean()) if correct.any() else None,
        "mean_confidence_incorrect": float(conf[~correct].mean()) if (~correct).any() else None,
        "gap": (
            float(conf[correct].mean() - conf[~correct].mean())
            if correct.any() and (~correct).any() else None
        ),
        "min_confidence_on_a_correct_prediction": float(conf[correct].min())
        if correct.any() else None,
        "max_confidence_on_a_wrong_prediction": float(conf[~correct].max())
        if (~correct).any() else None,
    }


def selective_curve(probs: np.ndarray, correct: np.ndarray) -> list[dict]:
    conf = probs.max(axis=1)
    rows = []
    for t in np.linspace(0.0, 0.999, 25):
        acc = conf >= t
        rows.append({
            "threshold": float(t),
            "coverage": float(acc.mean()),
            "selective_accuracy": float(correct[acc].mean()) if acc.any() else None,
            "n_answered": int(acc.sum()),
        })
    return rows


def expected_calibration_error(probs: np.ndarray, correct: np.ndarray,
                               n_bins: int = 10) -> dict:
    conf = probs.max(axis=1)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    bins = []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        m = (conf > lo) & (conf <= hi) if i else (conf >= lo) & (conf <= hi)
        if not m.any():
            bins.append({"lo": float(lo), "hi": float(hi), "n": 0,
                         "mean_confidence": None, "accuracy": None})
            continue
        c, a, n = float(conf[m].mean()), float(correct[m].mean()), int(m.sum())
        ece += (n / len(conf)) * abs(c - a)
        bins.append({"lo": float(lo), "hi": float(hi), "n": n,
                     "mean_confidence": c, "accuracy": a})
    return {"n_bins": n_bins, "expected_calibration_error": float(ece), "bins": bins}


def loso_probabilities(data_dir: str) -> dict:
    """Pool honest out-of-subject posteriors over all 22 subjects."""
    z = np.load(os.path.join(data_dir, "representative_postures.npz"))
    X, y, subj = z["X_canonical16"], z["movement"], z["subject"]
    pm = np.isin(y, PRIMARY)
    X, y, subj = X[pm], y[pm], subj[pm]
    yt, pr, classes = [], [], None
    for s in sorted(set(subj.tolist())):
        te, tr = subj == s, subj != s
        sc = StandardScaler().fit(X[tr])
        m = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
        m.fit(sc.transform(X[tr]), y[tr])
        classes = np.asarray(m.classes_)
        yt.append(y[te])
        pr.append(m.predict_proba(sc.transform(X[te])))
    yt = np.concatenate(yt)
    pr = np.concatenate(pr)
    pred = classes[pr.argmax(axis=1)]
    return {"y_true": yt, "probs": pr, "pred": pred, "classes": classes}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.results, encoding="utf-8") as fh:
        results = json.load(fh)

    report: dict = {"primary_movements": list(PRIMARY),
                    "movement_names": {str(m): labels.movement_name(1, m)
                                       for m in PRIMARY}}

    print("=" * 78)
    print("FROZEN TEST SPLIT -- confidence behaviour (n = 108)")
    print("=" * 78)
    report["frozen_test"] = {}
    for key, run in sorted(results["primary6__canonical16__test"]["runs"].items()):
        probs = np.asarray(run["_pred"]["probs"])
        yt = np.asarray(run["_pred"]["y_true"])
        yp = np.asarray(run["_pred"]["y_pred"])
        correct = yt == yp
        sep = separation(probs, correct)
        ece = expected_calibration_error(probs, correct)
        sel = selective_curve(probs, correct)
        report["frozen_test"][key] = {
            "accuracy": float(correct.mean()),
            "separation": sep,
            "expected_calibration_error": ece["expected_calibration_error"],
            "calibration_bins": ece["bins"],
            "selective_curve": sel,
        }
        print(f"  {key:<40} acc={correct.mean():.4f}  "
              f"conf(correct)={sep['mean_confidence_correct']}  "
              f"conf(wrong)={sep['mean_confidence_incorrect']}  ECE={ece['expected_calibration_error']:.4f}")

    # ---------------------------------------------------------------- LOSO
    print()
    print("=" * 78)
    print("POOLED LEAVE-ONE-SUBJECT-OUT -- the reliable basis (n = 792)")
    print("=" * 78)
    lo = loso_probabilities(args.data_dir)
    correct = lo["y_true"] == lo["pred"]
    sep = separation(lo["probs"], correct)
    ece = expected_calibration_error(lo["probs"], correct)
    sel = selective_curve(lo["probs"], correct)
    report["loso_pooled"] = {
        "n": int(len(correct)),
        "accuracy": float(correct.mean()),
        "separation": sep,
        "expected_calibration_error": ece["expected_calibration_error"],
        "calibration_bins": ece["bins"],
        "selective_curve": sel,
    }
    print(f"  accuracy                       = {correct.mean():.4f} "
          f"({int(correct.sum())}/{len(correct)})")
    print(f"  mean confidence (all)          = {sep['mean_confidence_all']:.4f}")
    print(f"  mean confidence when correct   = {sep['mean_confidence_correct']:.4f}")
    print(f"  mean confidence when wrong     = {sep['mean_confidence_incorrect']:.4f}")
    print(f"  separation gap                 = {sep['gap']:.4f}")
    print(f"  expected calibration error     = {ece['expected_calibration_error']:.4f}")
    print()
    print("  selective prediction (answer only above a confidence threshold):")
    for row in sel:
        if row["threshold"] in (0.0,) or row["coverage"] < 1.0:
            if row["selective_accuracy"] is None:
                continue
            if row["coverage"] in (1.0,) or row["threshold"] in (0.5, 0.7, 0.9, 0.95, 0.99):
                print(f"    threshold {row['threshold']:.3f}  coverage={row['coverage']:.3f}  "
                      f"selective accuracy={row['selective_accuracy']:.4f}  "
                      f"(n={row['n_answered']})")
    # the operating point a decoder would actually use
    useful = [r for r in sel if r["selective_accuracy"] is not None
              and r["selective_accuracy"] >= 0.99 and r["coverage"] >= 0.5]
    if useful:
        best = max(useful, key=lambda r: r["coverage"])
        report["loso_pooled"]["reject_option"] = {
            "rule": "answer only when max posterior >= threshold, else 'unknown'",
            "threshold": best["threshold"],
            "coverage": best["coverage"],
            "accuracy_on_answered": best["selective_accuracy"],
            "unknown_rate": 1.0 - best["coverage"],
        }
        print()
        print(f"  reject option: answering {best['coverage']:.1%} of inputs at "
              f"max-posterior >= {best['threshold']:.3f} gives "
              f"{best['selective_accuracy']:.2%} accuracy on the answered set "
              f"({1.0 - best['coverage']:.1%} flagged unknown)")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print(f"\n[wrote] {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
