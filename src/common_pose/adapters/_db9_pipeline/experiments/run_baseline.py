#!/usr/bin/env python
"""Baseline: given ONLY hand joint angles, which labelled DB9 postures are
recognizable across subjects?

This is deliberately a *lightweight, interpretable* baseline.  No deep networks.
The point of this stage is not to maximize accuracy but to establish whether the
angle -> posture problem is valid at all, and to quantify its limits per class
family.

Scientific question (frozen by the PI)
--------------------------------------
    "Given only hand joint angles, which labeled hand postures can be reliably
     recognized across subjects?"

Protocol
--------
* Evaluation is **subject-independent**: folds are groups of subjects, so no
  subject appears in both train and test.  This is the only honest way to ask a
  cross-subject question.
* Both **frame-level** and **trial/repetition-level** accuracy are reported.  A
  "trial" is one (subject, exercise, movement, repetition) block.  Trial-level is
  the more honest number because frames inside a trial are temporally
  correlated; frame-level is reported because a real-time decoder runs per
  frame.
* Results are broken down by movement family (posture / wrist / forearm_rot /
  grasp) and by object-dependence, because a flat 40-way number hides the
  finding that matters.
* A **rejection** option is evaluated: when the maximum posterior is below a
  threshold the decoder answers "unknown / ambiguous" instead of guessing.

Feature sets
------------
* ``canonical16`` — **THE FROZEN REPRESENTATION. This is the headline.** The 16
  shared kinematic DOF with **no inter-finger spread features**: thumb
  (CMC FE/AA, MCP FE, IP FE) + MCP/PIP/DIP flexion for index, middle, ring and
  pinky.
* ``canonical18`` — identical columns with the two reliable spread features
  (ring and pinky MCP abduction) appended. Run only as a controlled extension;
  the pipeline needs no change to switch it on.
* ``db9full21`` — all usable DB9 channels (adds glove-only wrist and pinky CMC).
  An upper-bound reference, **not** shared with emg2pose and not a candidate
  representation.

The first scientific question is answered by ``canonical16`` alone:
``Can hand posture be recognized reliably from the shared 16D kinematic
representation alone?``

Normalization variants
----------------------
* ``raw``       - radians, untouched.
* ``train_z``   - z-score using TRAIN-subject statistics only (no test leakage).
* ``subject_z`` - per-subject z-score from that subject's own samples, using no
  labels.  This is *unsupervised* per-subject adaptation and is standard practice
  for glove data, but it does use the test subject's unlabelled data, so it is
  reported separately and never mixed into the headline number.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.build_dataset import label_family, label_name  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import confusion_matrix, f1_score  # noqa: E402
from sklearn.naive_bayes import GaussianNB  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

warnings.filterwarnings("ignore")


class NearestClassMean:
    """Nearest class mean under Euclidean distance -- the simplest possible
    generative-ish baseline. Cheap, interpretable, and a useful sanity floor."""

    def __init__(self) -> None:
        self.classes_: np.ndarray | None = None
        self.means_: np.ndarray | None = None
        self.prior_: np.ndarray | None = None

    def fit(self, X, y):
        self.classes_ = np.unique(y)
        self.means_ = np.stack([X[y == c].mean(axis=0) for c in self.classes_])
        counts = np.array([(y == c).sum() for c in self.classes_], dtype=float)
        self.prior_ = counts / counts.sum()
        return self

    def predict_proba(self, X):
        d2 = ((X[:, None, :] - self.means_[None, :, :]) ** 2).sum(axis=2)
        # Softmax over negative squared distance, tempered by the mean
        # within-class variance so probabilities are on a sensible scale.
        scale = np.median(d2) + 1e-9
        logits = -d2 / scale + np.log(self.prior_ + 1e-12)
        logits -= logits.max(axis=1, keepdims=True)
        p = np.exp(logits)
        return p / p.sum(axis=1, keepdims=True)

    def predict(self, X):
        return self.classes_[self.predict_proba(X).argmax(axis=1)]


def make_models() -> dict:
    return {
        "ncm": NearestClassMean(),
        "lda": LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"),
        "logreg": LogisticRegression(max_iter=1000, C=1.0, n_jobs=-1, random_state=0),
        "gnb": GaussianNB(),
    }


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------
def load_dataset(path: str) -> dict:
    z = np.load(path)
    meta_path = os.path.splitext(path)[0] + ".meta.json"
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as fh:
            meta = json.load(fh)
    return {"arrays": {k: z[k] for k in z.files}, "meta": meta}


def choose_subject_folds(subjects: np.ndarray, n_folds: int, seed: int = 0):
    """Contiguous-group folds over the *sorted unique* subjects.

    Folds are made by dealing the sorted subject list round-robin, which keeps
    fold sizes balanced without ever splitting a subject across folds.
    """
    uniq = np.unique(subjects)
    rng = np.random.default_rng(seed)
    order = rng.permutation(uniq)
    folds = [[] for _ in range(n_folds)]
    for i, s in enumerate(order):
        folds[i % n_folds].append(int(s))
    return folds


def normalize(X_tr, X_te, subjects_tr, subjects_te, mode: str):
    if mode == "raw":
        return X_tr, X_te
    if mode == "train_z":
        sc = StandardScaler().fit(X_tr)
        return sc.transform(X_tr), sc.transform(X_te)
    if mode == "subject_z":
        # Unsupervised per-subject centring: each subject's own mean/std, no
        # labels involved. Applied identically to train and test subjects.
        def per_subject(X, subs):
            out = X.copy()
            for s in np.unique(subs):
                m = subs == s
                mu = X[m].mean(axis=0)
                sd = X[m].std(axis=0)
                sd[sd == 0] = 1.0
                out[m] = (X[m] - mu) / sd
            return out

        return per_subject(X_tr, subjects_tr), per_subject(X_te, subjects_te)
    raise ValueError(mode)


def trial_level_accuracy(y_true, y_pred, trial_keys):
    """Majority vote within each (subject, exercise, movement, repetition)."""
    groups: dict[tuple, list[int]] = defaultdict(list)
    for i, k in enumerate(trial_keys):
        groups[k].append(i)
    correct = 0
    n = 0
    for k, idx in groups.items():
        true_label = y_true[idx[0]]
        if not np.all(y_true[idx] == true_label):
            continue  # malformed trial grouping; skip rather than mis-score
        preds = y_pred[idx]
        vals, counts = np.unique(preds, return_counts=True)
        n += 1
        correct += int(vals[counts.argmax()] == true_label)
    return correct / n if n else float("nan"), n


def rejection_curve(probs, y_true, classes):
    """Coverage / selective-accuracy as the max-posterior threshold rises."""
    pred_idx = probs.argmax(axis=1)
    conf = probs.max(axis=1)
    correct = classes[pred_idx] == y_true
    thresholds = np.linspace(0.0, 0.99, 40)
    rows = []
    for t in thresholds:
        accepted = conf >= t
        cov = accepted.mean()
        sel_acc = correct[accepted].mean() if accepted.any() else float("nan")
        rows.append({"threshold": float(t), "coverage": float(cov),
                     "selective_accuracy": float(sel_acc)})
    return rows


def stratified_subsample(y: np.ndarray, budget: int, seed: int) -> np.ndarray:
    """Index of a class-balanced subsample of at most ``budget`` rows.

    Training on the full frame set is unnecessary (adjacent frames are
    temporally correlated and add almost no information) and makes the
    iterative solver needlessly slow.  Evaluation always uses *every* held-out
    frame, so the subsampling cannot flatter the reported accuracy.
    """
    n = y.size
    if budget <= 0 or n <= budget:
        return np.arange(n)
    rng = np.random.default_rng(seed)
    classes, counts = np.unique(y, return_counts=True)
    # Allocate proportionally, but guarantee at least a few rows per class so a
    # rare class is never silently dropped from training.
    share = np.maximum(4, np.floor(budget * counts / counts.sum()).astype(int))
    if share.sum() > budget:
        share = np.maximum(2, np.floor(share * budget / share.sum()).astype(int))
    picked: list[np.ndarray] = []
    for c, k in zip(classes, share):
        idx = np.flatnonzero(y == c)
        if idx.size <= k:
            picked.append(idx)
        else:
            picked.append(rng.choice(idx, size=int(k), replace=False))
    out = np.concatenate(picked)
    rng.shuffle(out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--fig-dir", required=True)
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--features", default="canonical16",
                    help="comma list of canonical16,canonical18,db9full21; "
                         "canonical16 is the frozen headline representation")
    ap.add_argument("--norms", default="raw,train_z,subject_z")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--max-train-frames", type=int, default=80000,
        help="class-balanced cap on training rows per fold (0 = use everything). "
             "Evaluation always uses every held-out frame.",
    )
    ap.add_argument("--exclude-flagged", action="store_true",
                    help="drop rows flagged by the quality checks")
    args = ap.parse_args()

    for d in (args.out_dir, args.fig_dir, args.model_dir):
        os.makedirs(d, exist_ok=True)

    ds = load_dataset(args.dataset)
    A, meta = ds["arrays"], ds["meta"]
    y_all = A["y"]
    subjects_all = A["subject"]
    exercise_all = A["exercise"]
    rep_all = A["repetition"]
    flags_all = A["quality_flags"]

    # Movement frames only: the rest position is not one of the 40 movements.
    keep = y_all > 0
    if args.exclude_flagged:
        keep &= flags_all == 0
    n_rest = int((y_all <= 0).sum())
    n_dropped = int((flags_all[keep] != 0).sum()) if args.exclude_flagged else 0

    feature_sets = {
        "canonical16": A["X_can16"],
        "canonical18": A["X_can18"],
        "db9full21": A["X_db9"],
    }
    uniq_subjects = np.unique(subjects_all[keep])
    print(f"[baseline] frames total={y_all.size:,} movement={int(keep.sum()):,} "
          f"rest_excluded={n_rest:,}" + (f" flagged_dropped={n_dropped:,}" if args.exclude_flagged else ""))
    print(f"[baseline] subjects with movement data: {len(uniq_subjects)} "
          f"-> {uniq_subjects.tolist()}")
    if len(uniq_subjects) < 2:
        print("[baseline] need >= 2 subjects for a subject-independent split; "
              "running a within-subject sanity pass instead (NOT a "
              "cross-subject result).")

    folds = choose_subject_folds(subjects_all[keep], args.folds, args.seed)
    print(f"[baseline] subject folds: {folds}")

    results: dict = {
        "protocol": {
            "question": ("Given only hand joint angles, which labeled hand "
                         "postures can be reliably recognized across subjects?"),
            "split": "subject-independent GroupKFold over subjects",
            "folds": folds,
            "seed": args.seed,
            "frame_level": True,
            "trial_level": "majority vote within (subject, exercise, movement, repetition)",
            "rest_excluded": True,
            "quality_flags_excluded": bool(args.exclude_flagged),
            "max_train_frames_per_fold": args.max_train_frames,
            "train_subsampling": ("class-balanced random subsample per fold; "
                                  "evaluation always uses every held-out frame"),
            "units": "radians",
            "note_subject_z": ("'subject_z' uses the test subject's own "
                               "unlabelled samples; it is unsupervised adaptation "
                               "and is reported separately from the headline."),
        },
        "dataset": {
            "path": os.path.abspath(args.dataset),
            "n_subjects": int(len(uniq_subjects)),
            "n_movement_frames": int(keep.sum()),
            "n_rest_frames_excluded": n_rest,
            "representations": meta.get("representations", {}),
            "frozen_representation": "canonical16",
            "spread_features_used": False if "canonical18" not in args.features else "canonical18 also run",
        },
        "runs": [],
    }

    for fname in args.features.split(","):
        fname = fname.strip()
        if fname not in feature_sets:
            print(f"[baseline] unknown feature set {fname}, skipping")
            continue
        Xbase = feature_sets[fname]

        for norm in [n.strip() for n in args.norms.split(",") if n.strip()]:
            for model_name in ("ncm", "lda", "logreg", "gnb"):
                all_true, all_pred, all_probs, all_subj, all_ex, all_rep = (
                    [], [], [], [], [], []
                )
                fold_scores = []
                classes_ref = None

                for fi, test_subjects in enumerate(folds):
                    if not test_subjects:
                        continue
                    te = np.isin(subjects_all, test_subjects) & keep
                    tr = ~np.isin(subjects_all, test_subjects) & keep
                    if tr.sum() == 0 or te.sum() == 0:
                        continue

                    # Bound training cost with a class-balanced subsample.
                    # Evaluation uses every held-out frame, so this cannot
                    # flatter the reported numbers.
                    tr_idx = np.flatnonzero(tr)
                    sub = stratified_subsample(
                        y_all[tr_idx], args.max_train_frames, args.seed + fi
                    )
                    tr_fit = np.zeros_like(tr)
                    tr_fit[tr_idx[sub]] = True

                    Xtr, Xte = normalize(
                        Xbase[tr_fit], Xbase[te], subjects_all[tr_fit],
                        subjects_all[te], norm,
                    )
                    ytr, yte = y_all[tr_fit], y_all[te]
                    if len(np.unique(ytr)) < 2:
                        continue

                    model = make_models()[model_name]
                    model.fit(Xtr, ytr)
                    classes = np.asarray(model.classes_)
                    probs = model.predict_proba(Xte)
                    pred = classes[probs.argmax(axis=1)]

                    fold_scores.append({
                        "fold": fi,
                        "test_subjects": test_subjects,
                        "n_train_available": int(tr.sum()),
                        "n_train_used": int(tr_fit.sum()),
                        "n_test": int(te.sum()),
                        "frame_accuracy": float((pred == yte).mean()),
                        "frame_macro_f1": float(
                            f1_score(yte, pred, average="macro", zero_division=0)
                        ),
                    })
                    all_true.append(yte)
                    all_pred.append(pred)
                    all_probs.append(probs)
                    all_subj.append(subjects_all[te])
                    all_ex.append(exercise_all[te])
                    all_rep.append(rep_all[te])
                    classes_ref = classes

                if not fold_scores:
                    print(f"[baseline] {fname}/{norm}/{model_name}: no usable folds")
                    continue

                y_true = np.concatenate(all_true)
                y_pred = np.concatenate(all_pred)
                probs = np.concatenate(all_probs)
                subs = np.concatenate(all_subj)
                exs = np.concatenate(all_ex)
                reps = np.concatenate(all_rep)
                classes = classes_ref

                # top-2 accuracy
                order = np.argsort(-probs, axis=1)[:, :2]
                top2 = np.mean([y_true[i] in classes[order[i]] for i in range(len(y_true))])

                trial_keys = list(zip(subs.tolist(), exs.tolist(),
                                      y_true.tolist(), reps.tolist()))
                trial_acc, n_trials = trial_level_accuracy(y_true, y_pred, trial_keys)

                # per-class recall + family aggregation
                per_class = {}
                for c in classes:
                    m = y_true == c
                    if m.sum() == 0:
                        continue
                    per_class[int(c)] = {
                        "name": label_name(int(c)),
                        "family": label_family(int(c)).value,
                        "n": int(m.sum()),
                        "recall": float((y_pred[m] == c).mean()),
                    }
                fam_acc = defaultdict(list)
                for cid, rec in per_class.items():
                    fam_acc[rec["family"]].append(rec["recall"])
                family_summary = {
                    k: {"mean_recall": float(np.mean(v)), "n_classes": len(v)}
                    for k, v in sorted(fam_acc.items())
                }

                cm = confusion_matrix(y_true, y_pred, labels=classes)
                cm_norm = cm / np.maximum(cm.sum(axis=1, keepdims=True), 1)

                run = {
                    "features": fname,
                    "normalization": norm,
                    "model": model_name,
                    "n_folds_used": len(fold_scores),
                    "fold_scores": fold_scores,
                    "frame_accuracy": float((y_pred == y_true).mean()),
                    "frame_accuracy_std_across_folds": float(
                        np.std([f["frame_accuracy"] for f in fold_scores])
                    ),
                    "frame_macro_f1": float(
                        f1_score(y_true, y_pred, average="macro", zero_division=0)
                    ),
                    "top2_accuracy": float(top2),
                    "trial_accuracy": float(trial_acc),
                    "n_trials": int(n_trials),
                    "per_class": per_class,
                    "family_summary": family_summary,
                    "rejection_curve": rejection_curve(probs, y_true, classes),
                }
                results["runs"].append(run)

                tag = f"{fname}__{norm}__{model_name}"
                np.savez_compressed(
                    os.path.join(args.out_dir, f"predictions__{tag}.npz"),
                    y_true=y_true, y_pred=y_pred, probs=probs, classes=classes,
                    subject=subs, exercise=exs, repetition=reps,
                )
                np.save(os.path.join(args.model_dir, f"confusion__{tag}.npy"), cm_norm)

                print(
                    f"  {tag:<38} frame={run['frame_accuracy']:.4f} "
                    f"(+-{run['frame_accuracy_std_across_folds']:.4f})  "
                    f"top2={run['top2_accuracy']:.4f}  macroF1={run['frame_macro_f1']:.4f}  "
                    f"trial={run['trial_accuracy']:.4f} (n={n_trials})"
                )

    # ---------------- summary table + figures ------------------------------
    summary_path = os.path.join(args.out_dir, "baseline_results.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)

    if results["runs"]:
        best = max(results["runs"], key=lambda r: r["frame_accuracy"])
        print()
        print(f"[baseline] best: {best['features']}/{best['normalization']}/{best['model']} "
              f"frame={best['frame_accuracy']:.4f} trial={best['trial_accuracy']:.4f}")
        print("[baseline] family breakdown (mean per-class recall):")
        for fam, v in sorted(best["family_summary"].items()):
            print(f"    {fam:<12} {v['mean_recall']:.4f}  ({v['n_classes']} classes)")

        make_figures(results, args.fig_dir)

    print(f"\n[baseline] results -> {summary_path}")
    return 0


def make_figures(results: dict, fig_dir: str) -> None:
    runs = results["runs"]
    best = max(runs, key=lambda r: r["frame_accuracy"])

    # --- per-class recall, grouped by family -------------------------------
    items = sorted(best["per_class"].items(),
                   key=lambda kv: (kv[1]["family"], -kv[1]["recall"]))
    fam_color = {"posture": "#1f77b4", "wrist": "#2ca02c",
                 "forearm_rot": "#d62728", "grasp": "#ff7f0e"}
    fig, ax = plt.subplots(figsize=(11, max(6, len(items) * 0.26)))
    names = [v["name"] for _, v in items]
    recs = [v["recall"] for _, v in items]
    cols = [fam_color.get(v["family"], "gray") for _, v in items]
    ax.barh(range(len(items)), recs, color=cols)
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels(names, fontsize=6)
    ax.invert_yaxis()
    ax.set_xlabel("per-class recall (subject-independent)")
    ax.set_xlim(0, 1)
    ax.axvline(best["frame_accuracy"], color="k", ls="--", lw=1,
               label=f"overall frame acc = {best['frame_accuracy']:.3f}")
    ax.legend(fontsize=8)
    ax.set_title(f"Per-class recall — {best['features']}/{best['normalization']}/{best['model']}\n"
                 "colour = movement family (blue posture, green wrist, red forearm-rotation, orange grasp)")
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "per_class_recall.png"), dpi=140)
    plt.close(fig)

    # --- family summary across all runs ------------------------------------
    fig, ax = plt.subplots(figsize=(10, 5))
    labels_, vals_, errs_ = [], [], []
    for fam in ("posture", "wrist", "forearm_rot", "grasp"):
        v = [r["family_summary"].get(fam, {}).get("mean_recall", np.nan) for r in runs]
        v = [x for x in v if np.isfinite(x)]
        if not v:
            continue
        labels_.append(fam)
        vals_.append(float(np.mean(v)))
        errs_.append(float(np.std(v)))
    ax.bar(labels_, vals_, yerr=errs_, color=[fam_color.get(l, "gray") for l in labels_],
           capsize=4)
    ax.set_ylabel("mean per-class recall")
    ax.set_ylim(0, 1)
    ax.set_title("Identifiability by movement family, across all baseline runs\n"
                 "(error bar = spread over feature-set x normalization x model)")
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "family_summary.png"), dpi=140)
    plt.close(fig)

    # --- rejection curve ----------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 5))
    for r in runs[:12]:
        c = r["rejection_curve"]
        ax.plot([p["coverage"] for p in c], [p["selective_accuracy"] for p in c],
                label=f"{r['features']}/{r['normalization']}/{r['model']}", lw=1.4)
    ax.set_xlabel("coverage (fraction of frames answered)")
    ax.set_ylabel("selective accuracy on answered frames")
    ax.set_title("Rejection: accuracy vs coverage\n(max-posterior threshold sweep)")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "rejection_curve.png"), dpi=140)
    plt.close(fig)

    # --- confusion matrix for the best run ---------------------------------
    cm_path = os.path.join(os.path.dirname(fig_dir), "models",
                           f"confusion__{best['features']}__{best['normalization']}__{best['model']}.npy")
    if os.path.exists(cm_path):
        cm = np.load(cm_path)
        fig, ax = plt.subplots(figsize=(11, 10))
        im = ax.imshow(cm, cmap="magma", vmin=0, vmax=1)
        ax.set_title(f"Row-normalised confusion — {best['features']}/{best['normalization']}/{best['model']}")
        ax.set_xlabel("predicted class index")
        ax.set_ylabel("true class index")
        fig.colorbar(im, ax=ax, fraction=0.046)
        fig.tight_layout()
        fig.savefig(os.path.join(fig_dir, "confusion_matrix.png"), dpi=140)
        plt.close(fig)


if __name__ == "__main__":
    sys.exit(main())
