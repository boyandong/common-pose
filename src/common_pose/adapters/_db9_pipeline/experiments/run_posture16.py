#!/usr/bin/env python
"""PHASES 2-7 -- the first angle-only posture experiment on canonical16.

Question (frozen)
-----------------
    Can hand posture be recognized across unseen subjects using only the shared
    16-dimensional hand kinematic representation?

Protocol, all of it fixed BEFORE any test evaluation
----------------------------------------------------
* **Independent unit** = subject x movement x repetition.  Published frames are
  not independent (the CyberGlove ran at <25 Hz and DB9 super-sampled it), so
  frame counts are never reported as sample counts.
* **Representative posture** = the MEDIAN of the **central third** of each
  labelled repetition.  The DB9 paper reports that this is the part
  "statistically expected to correspond the most to the target posture"; the
  first and last thirds contain the reach-in and return.  The segmentation is
  fixed at exactly one third and is never tuned per class or per accuracy.
* **No movement-order features.**  The protocol was not randomised and movement
  order leaks; repetitions are isolated so nothing from a neighbouring movement
  can be used, and absolute experiment time is not a feature.
* **Primary vocabulary** = exercise-B movements 1, 2, 3, 4, 6, 7 -- the hand
  configurations whose defining information canonical16 actually contains.
* **Negative control (pre-registered)** = movements 5 ("Abduction of all
  fingers") and 8 ("Adduction of extended fingers").  Both are DEFINED by
  inter-finger ab/adduction, which canonical16 deliberately removes.  They are
  therefore not in the primary vocabulary and are evaluated as a separate
  binary pair with a pre-registered expectation of near-chance accuracy.  This
  is option B from the protocol: an explicit negative control, not a silent
  exclusion and not a post-hoc removal.
* **Control representation** = ``canonical12_noDIP`` (canonical16 minus the four
  DIP variables), because DB9 warns that DIP readings degrade for subjects whose
  hands fit the glove poorly.
* **Split**: subject-independent, ~70/15/15, written to disk before the test set
  is ever touched.  No subject appears in two splits.  No random frame split.
* **Normalisation**: fitted on TRAIN subjects only.  Per-subject normalisation
  of the test subjects is explicitly NOT used -- it would require subject-
  specific calibration that a deployed decoder would not have.

Outputs
-------
``data/db9_posture16/representative_postures.npz``  one row per repetition
``data/db9_posture16/repetition_trajectories.npz``  full trajectories, kept for
    future work and NOT used by the classifier
``data/db9_posture16/subject_split.json``           the frozen split
``data/db9_posture16/results.json``                 all metrics
``figures/``                                        confusion matrices etc.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
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
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
)
from sklearn.preprocessing import StandardScaler  # noqa: E402

import db9_to_canonical16 as d2c  # noqa: E402
from db9 import labels  # noqa: E402
from db9.loader import (  # noqa: E402
    db9_exercise_index,
    discover_unpacked,
    load_recording,
    resolve_subject,
    source_db_for_subject,
)

# --------------------------------------------------------------------------
# PRE-REGISTERED PROTOCOL CONSTANTS -- frozen before test evaluation
# --------------------------------------------------------------------------
PRIMARY_MOVEMENTS = (1, 2, 3, 4, 6, 7)
NEGATIVE_CONTROL_MOVEMENTS = (5, 8)
CENTRAL_FRACTION = 1.0 / 3.0           # split each repetition into thirds
SPLIT_FRACTIONS = (0.70, 0.15, 0.15)   # train / val / test
MIN_SAMPLES_PER_REPETITION = 30        # a shorter labelled run is not a repetition
#: A repetition is UNUSABLE when fewer than this many valid frames lie inside the
#: original central third. It is reported, never silently replaced by another
#: interval.
MIN_VALID_CENTRAL_FRAMES = 5
RANDOM_SEED = 20260101

MOVEMENT_EXTRA_NOTES = {
    5: ("DEFINED by inter-finger abduction. canonical16 removes all four "
        "non-thumb MCP ab/adduction DOF by design, so the defining information "
        "is absent. Pre-registered negative control."),
    8: ("DEFINED by inter-finger adduction ('fingers closed together'). Same "
        "reason as movement 5. Pre-registered negative control."),
}


# --------------------------------------------------------------------------
# PHASE 2 -- representative posture extraction
# --------------------------------------------------------------------------
def central_third_bounds(n_original: int, fraction: float | None = None) -> tuple[int, int]:
    """Half-open ``[lo, hi)`` bounds of the central fraction of an interval.

    Defined purely on the ORIGINAL interval length.  Data-quality filtering must
    happen *after* these bounds are fixed, never before, or dropouts would shift
    the temporal window and silently redefine the target posture.
    """
    f = CENTRAL_FRACTION if fraction is None else fraction
    third = int(np.floor(n_original * f))
    return third, n_original - third


def select_central_valid(idx, valid, fraction: float | None = None,
                         min_valid: int | None = None):
    """Frames inside the ORIGINAL central third that are also valid.

    Returns ``(selected_indices, problem_or_None)``.  The order of operations is
    the whole point:

      1. take the labelled interval ``idx`` in original sample coordinates;
      2. compute its central-third boundaries from ``len(idx)``;
      3. select the frames inside those boundaries;
      4. only then drop frames flagged invalid;
      5. require a minimum number of valid frames, else report unusable.

    If too few valid frames remain, the repetition is reported as unusable.  The
    interval is never silently replaced with a different one.
    """
    mn = MIN_VALID_CENTRAL_FRAMES if min_valid is None else min_valid
    lo, hi = central_third_bounds(len(idx), fraction)
    central = idx[lo:hi]
    valid_central = central[np.asarray(valid)[central]]
    if valid_central.size < mn:
        return valid_central, {
            "reason": ("too few valid frames inside the original central third "
                       f"(< {mn})"),
            "n_original": int(len(idx)),
            "n_central": int(central.size),
            "n_valid_central": int(valid_central.size),
        }
    return valid_central, None
def extract_representatives(extracted: str, reps_out: str, traj_out: str,
                            meta_out: str) -> dict:
    files = discover_unpacked(extracted)
    if not files:
        raise SystemExit(f"no .mat files under {extracted}")

    X16, X12, y, subject, exercise, repetition, n_used, n_total = ([] for _ in range(8))
    traj: dict[str, np.ndarray] = {}
    per_file: list[dict] = []
    channel_notes: list[str] = []
    # repetitions reported as unusable, with the reason; never silently dropped
    unusable: list[dict] = []

    for slot, path in files:
        rec = load_recording(path)
        fname = os.path.basename(path)

        problems = d2c.verify_db9_channel_order(rec.order)
        if problems:
            channel_notes.append(f"{fname}: {problems}")
            continue

        subject_id, identity_note = resolve_subject(slot, rec.subject, path)
        ex_idx = db9_exercise_index(rec, subject_id)
        if ex_idx != 1:
            continue  # exercise B only for this experiment

        c16 = d2c.to_canonical16(rec.angles)                 # (T,16) radians
        c12 = d2c.to_canonical12_noDIP(rec.angles)           # (T,12) radians
        valid = d2c.db9_validity_mask(rec.angles)            # (T,) bool
        rs, rr = rec.restimulus, rec.rerepetition

        kept = 0
        for lab in sorted(set(int(v) for v in np.unique(rs)) - {0}):
            for rep in sorted(set(int(v) for v in np.unique(rr[rs == lab])) - {0}):
                m = (rs == lab) & (rr == rep)
                idx = np.flatnonzero(m)
                # The labelled interval is defined in ORIGINAL sample coordinates
                # and is never redefined by data-quality filtering.
                n_original = idx.size
                if n_original < MIN_SAMPLES_PER_REPETITION:
                    unusable.append({
                        "subject": subject_id, "movement": lab, "repetition": rep,
                        "reason": "labelled interval shorter than "
                                  f"{MIN_SAMPLES_PER_REPETITION} samples",
                        "n_original": int(n_original),
                    })
                    continue

                # (1) central-third boundaries from the ORIGINAL interval,
                # (2) frames inside that interval selected, (3) ONLY THEN invalid
                # frames removed. Doing (3) before (1) would let dropouts shift
                # the temporal window, silently redefining the target posture.
                valid_central, problem = select_central_valid(idx, valid)
                if problem is not None:
                    unusable.append({
                        "subject": subject_id, "movement": lab, "repetition": rep,
                        **problem,
                    })
                    continue

                X16.append(np.median(c16[valid_central], axis=0))
                X12.append(np.median(c12[valid_central], axis=0))
                y.append(lab)
                subject.append(subject_id)
                exercise.append(ex_idx)
                repetition.append(rep)
                n_used.append(int(valid_central.size))
                n_total.append(int(n_original))
                traj[f"s{subject_id}_m{lab}_r{rep}"] = c16[idx].astype(np.float32)
                kept += 1

        per_file.append({
            "file": fname, "subject": subject_id,
            "source_db": source_db_for_subject(subject_id),
            "recorded_subject_field": rec.subject,
            "subject_identity_note": identity_note,
            "ninapro_exercise": "B", "n_samples": int(rec.n_samples),
            "repetitions_extracted": kept,
        })
        print(f"  [ok] s{subject_id:<3d} {fname:<16} {kept} repetitions")

    if not X16:
        raise SystemExit("no repetitions extracted")

    reps_arrays = {
        "X_canonical16": np.asarray(X16, dtype=np.float64),
        "X_canonical12_noDIP": np.asarray(X12, dtype=np.float64),
        "movement": np.asarray(y, dtype=np.int32),
        "subject": np.asarray(subject, dtype=np.int32),
        "exercise": np.asarray(exercise, dtype=np.int8),
        "repetition": np.asarray(repetition, dtype=np.int32),
        "central_third_samples": np.asarray(n_used, dtype=np.int32),
        "labelled_interval_samples": np.asarray(n_total, dtype=np.int32),
    }
    meta = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "protocol": {
            "central_fraction": CENTRAL_FRACTION,
            "statistic": "median over the central third of each labelled repetition",
            "primary_movements": list(PRIMARY_MOVEMENTS),
            "negative_control_movements": list(NEGATIVE_CONTROL_MOVEMENTS),
            "min_samples_per_repetition": MIN_SAMPLES_PER_REPETITION,
            "unit_of_analysis": "subject x movement x repetition",
            "no_movement_order_features": True,
            "exercise_B_only": True,
            "dip_caveat": labels.DB9_PAGE,
        },
        "representations": {
            "canonical16": list(d2c.canonical16_names()),
            "canonical12_noDIP": list(d2c.canonical12_noDIP_names()),
            "unit": "radians",
            "db9_source_channels": list(d2c.canonical16_db9_channels()),
            "db9_column_indices": list(d2c.resolve_db9_columns()),
        },
        "n_repetitions": int(len(y)),
        "subjects": sorted({int(s) for s in subject}),
        "source_db_by_subject": {
            str(s): source_db_for_subject(s) for s in sorted({int(v) for v in subject})
        },
        "movement_counts": {str(k): int(v) for k, v in
                            sorted(Counter(int(v) for v in y).items())},
        "movement_names": {str(m): labels.movement_name(1, m)
                           for m in sorted(set(int(v) for v in y))},
        "files": per_file,
        "channel_order_problems": channel_notes,
        "unusable_repetitions": unusable,
        "n_unusable_repetitions": len(unusable),
    }

    for d in (os.path.dirname(os.path.abspath(reps_out)),):
        os.makedirs(d, exist_ok=True)
    np.savez_compressed(reps_out, **reps_arrays)
    np.savez_compressed(traj_out, **traj)
    with open(meta_out, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    if unusable:
        from collections import Counter as _C
        reasons = _C(u["reason"].split("(")[0].strip() for u in unusable)
        print(f"[phase2] {len(unusable)} repetition(s) marked UNUSABLE: {dict(reasons)}")
    print(f"\n[phase2] {len(y)} representative postures from "
          f"{len(meta['subjects'])} subjects -> {reps_out}")
    print(f"[phase2] full trajectories preserved -> {traj_out}")
    return {"arrays": reps_arrays, "meta": meta}


# --------------------------------------------------------------------------
# PHASE 5 -- frozen subject split
# --------------------------------------------------------------------------
def freeze_split(subjects: list[int], path: str) -> dict:
    """Subject-independent ~70/15/15, stratified by source database.

    Deterministic given RANDOM_SEED, and written to disk so it cannot drift.
    """
    rng = np.random.default_rng(RANDOM_SEED)
    by_db: dict[str, list[int]] = defaultdict(list)
    for s in subjects:
        by_db[source_db_for_subject(s)].append(s)

    train: list[int] = []
    val: list[int] = []
    test: list[int] = []
    for db, subj in sorted(by_db.items()):
        subj = sorted(subj)
        rng.shuffle(subj)
        n = len(subj)
        n_test = max(1, int(round(n * SPLIT_FRACTIONS[2])))
        n_val = max(1, int(round(n * SPLIT_FRACTIONS[1])))
        if n_test + n_val >= n:
            n_test = max(1, n // 5)
            n_val = max(1, n // 5)
        test += subj[:n_test]
        val += subj[n_test:n_test + n_val]
        train += subj[n_test + n_val:]

    split = {
        "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seed": RANDOM_SEED,
        "policy": ("subject-independent; every repetition of a subject falls in "
                   "exactly one split; stratified by source database (DB1/DB5)"),
        "fractions_requested": {"train": SPLIT_FRACTIONS[0],
                                "val": SPLIT_FRACTIONS[1],
                                "test": SPLIT_FRACTIONS[2]},
        "train": sorted(train), "val": sorted(val), "test": sorted(test),
        "source_db": {str(s): source_db_for_subject(s) for s in sorted(subjects)},
        "n_subjects": {"train": len(train), "val": len(val), "test": len(test)},
    }
    assert not (set(train) & set(val)), "subject in both train and val"
    assert not (set(train) & set(test)), "subject in both train and test"
    assert not (set(val) & set(test)), "subject in both val and test"
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(split, fh, indent=2)
    print(f"[phase5] split frozen -> {path}")
    print(f"         train={split['train']}")
    print(f"         val  ={split['val']}")
    print(f"         test ={split['test']}")
    return split


# --------------------------------------------------------------------------
# PHASE 6 -- baselines
# --------------------------------------------------------------------------
class NearestCentroid:
    def __init__(self, metric: str = "euclidean"):
        self.metric = metric

    def fit(self, X, y):
        self.classes_ = np.unique(y)
        self.means_ = np.stack([X[y == c].mean(axis=0) for c in self.classes_])
        if self.metric == "mahalanobis":
            d = X - self.means_[np.searchsorted(self.classes_, y)]
            self.cov_inv_ = np.linalg.pinv(np.cov(d, rowvar=False) + 1e-6 * np.eye(X.shape[1]))
        return self

    def _scores(self, X):
        if self.metric == "mahalanobis":
            out = np.empty((X.shape[0], len(self.classes_)))
            for i, m in enumerate(self.means_):
                d = X - m
                out[:, i] = -np.einsum("ij,jk,ik->i", d, self.cov_inv_, d)
            return out
        d2 = ((X[:, None, :] - self.means_[None, :, :]) ** 2).sum(axis=2)
        return -d2

    def predict_proba(self, X):
        s = self._scores(X)
        s = s - s.max(axis=1, keepdims=True)
        p = np.exp(s / max(np.median(np.abs(s)) + 1e-9, 1e-9))
        return p / p.sum(axis=1, keepdims=True)

    def predict(self, X):
        return self.classes_[self._scores(X).argmax(axis=1)]


def make_models() -> dict:
    return {
        "nearest_centroid_euclidean": NearestCentroid("euclidean"),
        "nearest_centroid_mahalanobis": NearestCentroid("mahalanobis"),
        "lda": LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"),
        "logreg": LogisticRegression(max_iter=5000, C=1.0, random_state=RANDOM_SEED),
        "random_forest": RandomForestClassifier(
            n_estimators=500, random_state=RANDOM_SEED, min_samples_leaf=1
        ),
    }


def evaluate(X, y, subj, tr, te, model_name, normalize=True):
    scaler = StandardScaler().fit(X[tr]) if normalize else None
    Xtr = scaler.transform(X[tr]) if scaler else X[tr]
    Xte = scaler.transform(X[te]) if scaler else X[te]
    model = make_models()[model_name]
    model.fit(Xtr, y[tr])
    classes = np.asarray(getattr(model, "classes_", np.unique(y[tr])))
    probs = model.predict_proba(Xte)
    pred = classes[probs.argmax(axis=1)]

    per_class = {}
    for c in np.unique(y[te]):
        m = y[te] == c
        per_class[int(c)] = {
            "name": labels.movement_name(1, int(c)),
            "n": int(m.sum()),
            "accuracy": float((pred[m] == c).mean()),
        }
    per_subject = {}
    for s in np.unique(subj[te]):
        m = subj[te] == s
        per_subject[int(s)] = {
            "n": int(m.sum()),
            "accuracy": float((pred[m] == y[te][m]).mean()),
        }
    return {
        "model": model_name,
        "normalization": "train_zscore" if normalize else "none",
        "accuracy": float((pred == y[te]).mean()),
        "balanced_accuracy": float(balanced_accuracy_score(y[te], pred)),
        "macro_f1": float(f1_score(y[te], pred, average="macro", zero_division=0)),
        "per_class": per_class,
        "per_subject": per_subject,
        "classes": classes.tolist(),
        "y_true": y[te].tolist(),
        "y_pred": pred.tolist(),
        "probs": probs.tolist(),
        "n_test": int(te.sum()),
    }


def run_grid(X, y, subj, tr, te, tag, results: dict, fig_dir: str):
    print(f"\n  --- {tag} ({X.shape[1]}D, n_train={int(tr.sum())}, n_test={int(te.sum())}) ---")
    majority = Counter(y[tr]).most_common(1)[0]
    maj_acc = float((y[te] == majority[0]).mean())
    chance = 1.0 / len(np.unique(y))
    print(f"      majority-class baseline = {maj_acc:.4f} "
          f"(class {majority[0]} {labels.movement_name(1, majority[0])})")
    print(f"      uniform chance          = {chance:.4f}")
    results[tag] = {"majority_class_accuracy": maj_acc,
                    "uniform_chance": chance,
                    "majority_class": int(majority[0]), "runs": {}}

    for model_name in make_models():
        for normalize in (True, False):
            r = evaluate(X, y, subj, tr, te, model_name, normalize)
            key = f"{model_name}__{'z' if normalize else 'raw'}"
            results[tag]["runs"][key] = {k: v for k, v in r.items()
                                         if k not in ("y_true", "y_pred", "probs")}
            results[tag]["runs"][key]["_pred"] = {
                "y_true": r["y_true"], "y_pred": r["y_pred"], "probs": r["probs"],
            }
            print(f"      {key:<38} acc={r['accuracy']:.4f}  "
                  f"bal={r['balanced_accuracy']:.4f}  macroF1={r['macro_f1']:.4f}")
    return results[tag]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--extracted", required=True)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--fig-dir", required=True)
    ap.add_argument("--results-dir", required=True)
    args = ap.parse_args()

    os.makedirs(args.data_dir, exist_ok=True)
    os.makedirs(args.fig_dir, exist_ok=True)
    os.makedirs(args.results_dir, exist_ok=True)

    reps_path = os.path.join(args.data_dir, "representative_postures.npz")
    traj_path = os.path.join(args.data_dir, "repetition_trajectories.npz")
    meta_path = os.path.join(args.data_dir, "representative_postures.meta.json")
    split_path = os.path.join(args.data_dir, "subject_split.json")

    print("[phase2] extracting representative postures (central-third median)")
    if os.path.exists(reps_path) and os.path.exists(meta_path):
        print("         (cached)")
        z = np.load(reps_path)
        A = {k: z[k] for k in z.files}
        with open(meta_path, encoding="utf-8") as fh:
            meta = json.load(fh)
    else:
        built = extract_representatives(args.extracted, reps_path, traj_path, meta_path)
        A, meta = built["arrays"], built["meta"]

    y = A["movement"]
    subj = A["subject"]
    X16 = A["X_canonical16"]
    X12 = A["X_canonical12_noDIP"]

    print(f"\n[phase2] {len(y)} repetitions, {len(set(subj.tolist()))} subjects")
    counts = Counter(int(v) for v in y)
    for m in sorted(counts):
        fam = "PRIMARY" if m in PRIMARY_MOVEMENTS else "negative control"
        print(f"    movement {m:>2}  n={counts[m]:>3}  [{fam}]  "
              f"{labels.movement_name(1, m)}")

    # ---------------- PHASE 5: freeze the split ---------------------------
    all_subjects = sorted({int(s) for s in subj})
    split = freeze_split(all_subjects, split_path)
    tr = np.isin(subj, split["train"])
    va = np.isin(subj, split["val"])
    te = np.isin(subj, split["test"])

    results: dict = {
        "protocol": meta["protocol"],
        "representations": meta["representations"],
        "split": split,
        "n_repetitions": int(len(y)),
        "n_subjects": len(all_subjects),
        "movement_counts": {str(k): int(v) for k, v in sorted(counts.items())},
        "pre_registration": {
            "primary_movements": list(PRIMARY_MOVEMENTS),
            "negative_control_movements": list(NEGATIVE_CONTROL_MOVEMENTS),
            "decision": "B -- movements 5 and 8 kept as an explicit negative control",
            "rationale": MOVEMENT_EXTRA_NOTES,
            "why": ("canonical16 removes the four non-thumb MCP ab/adduction DOF "
                    "by design; movements 5 and 8 are defined by those DOF, so "
                    "their defining information is absent from the "
                    "representation. Freezing this before test evaluation."),
            "frozen_before_test_evaluation": True,
        },
    }

    # ---------------- PHASE 6: primary 6-class problem --------------------
    print("\n[phase6] PRIMARY vocabulary (movements 1,2,3,4,6,7)")
    pm = np.isin(y, PRIMARY_MOVEMENTS)
    for rep_name, X in (("canonical16", X16), ("canonical12_noDIP", X12)):
        run_grid(X[pm], y[pm], subj[pm], tr[pm], te[pm],
                 f"primary6__{rep_name}__test", results, args.fig_dir)

    # ---------------- negative control ------------------------------------
    print("\n[phase6] NEGATIVE CONTROL: movement 5 vs movement 8")
    nc = np.isin(y, NEGATIVE_CONTROL_MOVEMENTS)
    if nc.sum() > 0:
        run_grid(X16[nc], y[nc], subj[nc], tr[nc], te[nc],
                 "negative_control__B5_vs_B8__canonical16", results, args.fig_dir)
        run_grid(X16[nc], y[nc], subj[nc], tr[nc], te[nc],
                 "negative_control__B5_vs_B8__canonical16_rawnorm", results, args.fig_dir)

    # ---------------- secondary: all 8 ------------------------------------
    print("\n[phase6] SECONDARY (not primary): all 8 exercise-B configurations")
    eight = np.isin(y, PRIMARY_MOVEMENTS + NEGATIVE_CONTROL_MOVEMENTS)
    run_grid(X16[eight], y[eight], subj[eight], tr[eight], te[eight],
             "secondary8__canonical16__test", results, args.fig_dir)

    # ---------------- validation split, for reference ---------------------
    print("\n[phase6] VALIDATION split (reference only; test untouched)")
    run_grid(X16[pm], y[pm], subj[pm], tr[pm], va[pm],
             "primary6__canonical16__val", results, args.fig_dir)

    # ---------------- PHASE 4/7: DIP contribution ------------------------
    print("\n[phase4] canonical16 vs canonical12_noDIP (per-class / per-subject)")
    a = results["primary6__canonical16__test"]["runs"]
    b = results["primary6__canonical12_noDIP__test"]["runs"]
    dip = {}
    for k in a:
        if k not in b:
            continue
        dip[k] = {
            "accuracy_canonical16": a[k]["accuracy"],
            "accuracy_canonical12_noDIP": b[k]["accuracy"],
            "delta": a[k]["accuracy"] - b[k]["accuracy"],
            "balanced_accuracy_canonical16": a[k]["balanced_accuracy"],
            "balanced_accuracy_canonical12_noDIP": b[k]["balanced_accuracy"],
            "per_class_delta": {
                str(c): a[k]["per_class"][c]["accuracy"] - b[k]["per_class"][c]["accuracy"]
                for c in a[k]["per_class"] if c in b[k]["per_class"]
            },
            "per_subject_delta": {
                str(s): a[k]["per_subject"][s]["accuracy"] - b[k]["per_subject"][s]["accuracy"]
                for s in a[k]["per_subject"] if s in b[k]["per_subject"]
            },
        }
    results["phase4_dip_control"] = dip
    for k, v in dip.items():
        print(f"    {k:<40} canonical16={v['accuracy_canonical16']:.4f}  "
              f"noDIP={v['accuracy_canonical12_noDIP']:.4f}  delta={v['delta']:+.4f}")

    # ---------------- figures + PHASE 7 -----------------------------------
    make_figures(results, args.fig_dir, PRIMARY_MOVEMENTS)
    results["phase7_failure_analysis"] = failure_analysis(results, PRIMARY_MOVEMENTS)

    out = os.path.join(args.results_dir, "results.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print(f"\n[done] results -> {out}")
    return 0


def make_figures(results: dict, fig_dir: str, primary: tuple) -> None:
    for tag in ("primary6__canonical16__test", "primary6__canonical12_noDIP__test"):
        if tag not in results:
            continue
        runs = results[tag]["runs"]
        best = max(runs.items(), key=lambda kv: kv[1]["accuracy"])[1]
        classes = best["classes"]
        yt, yp = best["_pred"]["y_true"], best["_pred"]["y_pred"]
        cm = confusion_matrix(yt, yp, labels=classes)
        cmn = cm / np.maximum(cm.sum(axis=1, keepdims=True), 1)

        fig, ax = plt.subplots(figsize=(7, 6))
        im = ax.imshow(cmn, cmap="Blues", vmin=0, vmax=1)
        names = [labels.movement_name(1, int(c))[:26] for c in classes]
        ax.set_xticks(range(len(classes)))
        ax.set_yticks(range(len(classes)))
        ax.set_xticklabels(names, rotation=45, ha="right", fontsize=7)
        ax.set_yticklabels(names, fontsize=7)
        for i in range(len(classes)):
            for j in range(len(classes)):
                if cm[i, j]:
                    ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                            fontsize=8, color="white" if cmn[i, j] > 0.5 else "black")
        ax.set_title(f"{tag}\nrow-normalised confusion (counts annotated)\n"
                     f"acc={best['accuracy']:.3f} balanced={best['balanced_accuracy']:.3f}")
        ax.set_xlabel("predicted")
        ax.set_ylabel("true")
        fig.colorbar(im, ax=ax, fraction=0.046)
        fig.tight_layout()
        fig.savefig(os.path.join(fig_dir, f"confusion__{tag}.png"), dpi=150)
        plt.close(fig)

        # per-class accuracy bar
        fig, ax = plt.subplots(figsize=(8, 4))
        cs = sorted(best["per_class"], key=lambda c: int(c))
        ax.bar([labels.movement_name(1, int(c))[:22] for c in cs],
               [best["per_class"][c]["accuracy"] for c in cs], color="#1f77b4")
        ax.axhline(best["accuracy"], color="k", ls="--", lw=1,
                   label=f"overall {best['accuracy']:.3f}")
        ax.axhline(1 / len(cs), color="r", ls=":", lw=1, label=f"chance {1/len(cs):.3f}")
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("per-class accuracy")
        ax.tick_params(axis="x", rotation=30, labelsize=7)
        ax.legend(fontsize=8)
        ax.set_title(f"Per-class accuracy -- {tag}")
        fig.tight_layout()
        fig.savefig(os.path.join(fig_dir, f"per_class__{tag}.png"), dpi=150)
        plt.close(fig)


def failure_analysis(results: dict, primary: tuple) -> dict:
    """PHASE 7 -- attribute the strongest confusion pairs.

    The four attributions are the ones the protocol names.  Assignment is made
    from representation content and DB9 metadata only; no architecture is
    changed to rescue a result.
    """
    tag = "primary6__canonical16__test"
    if tag not in results:
        return {}
    best = max(results[tag]["runs"].items(), key=lambda kv: kv[1]["accuracy"])[1]
    classes = [int(c) for c in best["classes"]]
    yt = np.asarray(best["_pred"]["y_true"])
    yp = np.asarray(best["_pred"]["y_pred"])
    cm = confusion_matrix(yt, yp, labels=classes)

    pairs = []
    for i, t in enumerate(classes):
        for j, p in enumerate(classes):
            if i == j or cm[i, j] == 0:
                continue
            pairs.append({
                "true": t, "true_name": labels.movement_name(1, t),
                "predicted": p, "predicted_name": labels.movement_name(1, p),
                "count": int(cm[i, j]),
                "row_fraction": float(cm[i, j] / max(cm[i].sum(), 1)),
            })
    pairs.sort(key=lambda d: (-d["row_fraction"], -d["count"]))

    notes = {
        (1, 4): "both are thumb-dominant hand shapes; canonical16 has no finger-spread "
                "channel to separate them",
        (1, 2): "thumb opposition vs index/middle extension differ mainly in which "
                "fingers move, and both keep the thumb extended",
        (4, 6): "'Thumb opposing base of little finger' approaches a fist for the "
                "long fingers, which canonical16 encodes directly",
    }
    for p in pairs[:8]:
        p["canonical16_note"] = notes.get((p["true"], p["predicted"]), "")
        p["candidate_causes"] = {
            "1_missing_DOF": (
                "canonical16 drops the four non-thumb MCP ab/adduction DOF; if the "
                "pair differs mainly in finger spread, this is the cause"
            ),
            "2_sensor_or_calibration": (
                "DB9 warns DIP readings degrade for small hands; canonical16 "
                "contains 4 DIP channels"
            ),
            "3_genuinely_similar_kinematics": (
                "the two postures may simply have near-identical joint angles"
            ),
            "4_classifier_limitation": (
                "small n (one posture per repetition); a stronger model might help"
            ),
        }
    return {
        "note": ("assignment is from representation content and DB9 metadata; the "
                 "architecture is not redesigned to rescue a result"),
        "top_confusions": pairs[:8],
    }


if __name__ == "__main__":
    sys.exit(main())
