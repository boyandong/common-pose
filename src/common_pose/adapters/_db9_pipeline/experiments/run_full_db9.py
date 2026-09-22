#!/usr/bin/env python
"""Full-DB9 (77-subject) replication of the canonical16 posture experiment.

This is a REPLICATION, not an improvement.  Everything that defines the
experiment is imported from `run_posture16` rather than re-declared here, so it
is impossible for the two to drift apart:

  canonical16 / canonical12_noDIP   -> db9_to_canonical16 (frozen schema)
  stable-posture extraction         -> run_posture16.extract_representatives
  central-third rule, representative median, class vocabulary,
  classifiers and their hyperparameters, normalisation policy
                                    -> run_posture16 constants / make_models

The previous 22-subject run is development evidence and its frozen test split
has already been inspected, so it is no longer confirmatory.  This run freezes
every design decision first and only then evaluates the subjects that were absent
from the development corpus.

Evidence tiers (frozen final_evaluation_plan)
---------------------------------------------
The run reports three arms and labels each one, because they are not equally
confirmatory and must never be interchanged:

  A  PRIMARY CONFIRMATORY   design item 2_untouched_confirmation.a
                            train on the development-exposed cohort, predict the
                            outcome-unseen cohort exactly once.  The cohort
                            partition is LOADED from docs/CONFIRMATORY_COHORTS.json,
                            never hard-coded here.  Strongest evidence.
  B  descriptive            design item 1_full_77_loso -- full-corpus replication.
                            Descriptive only: development-exposed subjects are
                            inside this evaluation.
  C  secondary              design item 2_untouched_confirmation.b (LOSO within
                            the outcome-unseen cohort) plus the source-held-out
                            and representation-control comparisons.

What it adds beyond the 22-subject run
--------------------------------------
* the pre-registered primary confirmatory arm on the outcome-unseen cohort (A)
* a subject manifest (report item 2)
* DB1 / DB2 / DB5 breakdowns (item 3, 7)
* source-held-out tests: train on two source databases, test on the third (item 8)
* leave-one-subject-out across all subjects (item 6, descriptive)
* drift-only, drift-corrected and label-permutation controls (item 10)
* canonical16 vs canonical12_noDIP, overall and per source database (item 9)
* confusion matrices and errors by class and source database (items 11, 13),
  computed per evidence tier and tagged with that tier

No deep model, no architecture search, no hyperparameter tuning, and no
cross-dataset connection.
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
from sklearn.metrics import confusion_matrix  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

import db9_to_canonical16 as d2c  # noqa: E402
from db9 import labels  # noqa: E402
from db9.loader import (  # noqa: E402
    db9_exercise_index, discover_unpacked, load_recording, resolve_subject,
    source_db_for_subject,
)

# ---- FROZEN protocol, imported so it cannot drift from the 22-subject run ----
import run_posture16 as rp  # noqa: E402
import confirmatory_policy as cp  # noqa: E402

PRIMARY = rp.PRIMARY_MOVEMENTS
NEG_CONTROL = rp.NEGATIVE_CONTROL_MOVEMENTS
SEED = rp.RANDOM_SEED
MODEL_NAMES = tuple(rp.make_models().keys())


def subject_of(path_slot: int, path: str) -> tuple[int, str]:
    rec = load_recording(path)
    subject, note = resolve_subject(path_slot, rec.subject, path)
    return subject, note or ""


# ---------------------------------------------------------------------------
# report item 2 -- subject manifest
# ---------------------------------------------------------------------------
def build_manifest(reps_npz: str, extracted: str) -> dict:
    """One row per archive slot: identity, exercises, repetitions, provenance."""
    z = np.load(reps_npz)
    subj_arr, mov_arr, rep_arr = z["subject"], z["movement"], z["repetition"]

    per_subject_reps: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for s, m, r in zip(subj_arr.tolist(), mov_arr.tolist(), rep_arr.tolist()):
        per_subject_reps[s][int(m)] += 1

    rows = []
    for slot, path in discover_unpacked(extracted):
        rec = load_recording(path)
        subject, note = resolve_subject(slot, rec.subject, path)
        try:
            ex = db9_exercise_index(rec, subject)
        except Exception:  # noqa: BLE001
            continue
        if ex != 1:
            continue
        rows.append({
            "global_subject_id": subject,
            "source_dataset": source_db_for_subject(subject),
            "recorded_subject_field": rec.subject,
            "subject_identity_note": note,
            "available_exercises_in_this_file": {"B": 1, "C": 2}[
                {1: "B", 2: "C"}[ex]],
            "file": os.path.basename(path),
            "file_bytes": os.path.getsize(path),
            "samples": int(rec.n_samples),
            "movements_present": sorted(set(int(v) for v in np.unique(rec.restimulus)) - {0}),
            "repetitions_per_movement": dict(sorted(per_subject_reps[subject].items())),
            "total_repetitions": int(sum(per_subject_reps[subject].values())),
            "status": "OK",
        })
    rows.sort(key=lambda r: r["global_subject_id"])
    counts = Counter(r["source_dataset"] for r in rows)
    return {
        "n_subjects": len(rows),
        "by_source_dataset": dict(sorted(counts.items())),
        "expected": {"DB1": 27, "DB2": 40, "DB5": 10, "total": 77},
        "authority": ("the DB9 archive slot is the participant identity; the "
                      "in-file `subject` field uses each source database's own "
                      "numbering and is recorded for audit only"),
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# evaluation helpers (identical policy to the 22-subject run)
# ---------------------------------------------------------------------------
def fit_predict(Xtr, ytr, Xte, model_name, normalize):
    scaler = StandardScaler().fit(Xtr) if normalize else None
    A = scaler.transform(Xtr) if scaler else Xtr
    B = scaler.transform(Xte) if scaler else Xte
    model = rp.make_models()[model_name]
    model.fit(A, ytr)
    classes = np.asarray(getattr(model, "classes_", np.unique(ytr)))
    probs = model.predict_proba(B)
    return classes[probs.argmax(axis=1)], classes


def score(y_true, y_pred) -> dict:
    from sklearn.metrics import balanced_accuracy_score, f1_score

    return {
        "accuracy": float((y_true == y_pred).mean()),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "n": int(len(y_true)),
    }


def loso(X, y, subj, model_name="lda", normalize=True, sources=None):
    """Leave-one-subject-out; returns pooled predictions and per-subject rows."""
    yt, yp, ss = [], [], []
    rows = []
    for s in sorted(set(subj.tolist())):
        te, tr = subj == s, subj != s
        if len(set(y[tr].tolist())) < 2 or te.sum() == 0:
            continue
        pred, _ = fit_predict(X[tr], y[tr], X[te], model_name, normalize)
        yt.append(y[te]); yp.append(pred); ss.append(subj[te])
        rows.append({"subject": int(s), "n": int(te.sum()),
                     "accuracy": float((pred == y[te]).mean())})
    if not yt:
        return None
    yt = np.concatenate(yt); yp = np.concatenate(yp); ss = np.concatenate(ss)
    out = {"pooled": score(yt, yp), "per_subject": rows,
           "y_true": yt.tolist(), "y_pred": yp.tolist(), "subject": ss.tolist()}
    if sources is not None:
        src = np.array([source_db_for_subject(int(s)) for s in ss])
        out["by_source_dataset"] = {
            db: score(yt[src == db], yp[src == db]) for db in sorted(set(src.tolist()))
        }
    return out


def evaluate_explicit_partition(X, y, subjects, train_subjects, test_subjects,
                               representation="canonical16",
                               model_name=cp.PRIMARY_MODEL,
                               normalization=cp.PRIMARY_NORMALIZATION):
    """PRIMARY confirmatory evaluation on an EXPLICIT subject partition.

    The partition is passed in; it is never inferred from leave-one-out logic.

    Procedure, in order, with no exception:
      1. fit the scaler on TRAIN subjects' samples only;
      2. transform train with that scaler, fit the classifier on train only;
      3. transform the TEST subjects with the SAME train-fitted scaler;
      4. predict the test subjects, once;
      5. score with the frozen metrics.

    No test-subject statistic enters scaler fitting, classifier fitting, model or
    hyperparameter selection, threshold selection, calibration, or adaptation.
    There is no refitting and no per-subject calibration.

    Returns a record carrying the partition and the fitted scaler's statistics,
    so that train-only fitting is auditable rather than asserted.
    """
    normalize = normalization == "train_only_zscore"
    train_subjects = sorted(int(s) for s in train_subjects)
    test_subjects = sorted(int(s) for s in test_subjects)

    overlap = sorted(set(train_subjects) & set(test_subjects))
    if overlap:
        raise cp.IdentityAssertionError(
            f"train and test subject sets overlap: {overlap}"
        )

    tr = np.isin(subjects, train_subjects)
    te = np.isin(subjects, test_subjects)
    if tr.sum() == 0 or te.sum() == 0:
        raise cp.IdentityAssertionError(
            f"empty partition: {int(tr.sum())} train samples, {int(te.sum())} test samples"
        )

    # Every sample must belong to exactly the side its subject was assigned to.
    unseen_subjects_present = sorted(set(subjects[~tr & ~te].tolist()))
    if unseen_subjects_present:
        raise cp.IdentityAssertionError(
            "samples from subjects in neither cohort are present: "
            f"{unseen_subjects_present[:10]}"
        )
    train_subs_present = sorted(set(subjects[tr].tolist()))
    test_subs_present = sorted(set(subjects[te].tolist()))
    if not set(train_subs_present) <= set(train_subjects):
        raise cp.IdentityAssertionError("train samples outside train_subjects")
    if not set(test_subs_present) <= set(test_subjects):
        raise cp.IdentityAssertionError("test samples outside test_subjects")

    scaler = StandardScaler().fit(X[tr]) if normalize else None
    A = scaler.transform(X[tr]) if scaler else X[tr]
    B = scaler.transform(X[te]) if scaler else X[te]
    model = rp.make_models()[model_name]
    if model_name == cp.PRIMARY_MODEL:
        # Assert the frozen configuration rather than trusting the factory.
        got = {k: getattr(model, k, None) for k in ("solver", "shrinkage")}
        for k, v in cp.PRIMARY_MODEL_CONFIG.items():
            if got.get(k) != v:
                raise SystemExit(
                    f"PRIMARY model config drift: {k}={got.get(k)!r}, expected {v!r}"
                )
    model.fit(A, y[tr])
    classes = np.asarray(getattr(model, "classes_", np.unique(y[tr])))
    probs = model.predict_proba(B)
    pred = classes[probs.argmax(axis=1)]

    y_te = y[te]
    per_subject = {}
    for s in sorted(set(subjects[te].tolist())):
        m = subjects[te] == s
        per_subject[int(s)] = {"n": int(m.sum()),
                               "accuracy": float((pred[m] == y_te[m]).mean())}
    src = np.array([source_db_for_subject(int(s)) for s in subjects[te]])
    by_source = {db: score(y_te[src == db], pred[src == db])
                 for db in sorted(set(src.tolist()))}

    return {
        "tier": "A: PRIMARY CONFIRMATORY -- one-shot external holdout",
        "representation": representation,
        "model": model_name,
        "normalization": normalization,
        "train_subjects": train_subjects,
        "test_subjects": test_subjects,
        "n_train_subjects": len(train_subjects),
        "n_test_subjects": len(test_subjects),
        "n_train_samples": int(tr.sum()),
        "n_test_samples": int(te.sum()),
        "pooled": score(y_te, pred),
        "per_subject": per_subject,
        "by_source_dataset": by_source,
        "classes": classes.tolist(),
        "scaler_fitted_on": "train subjects only",
        "scaler_mean": (scaler.mean_.tolist() if scaler else None),
        "scaler_scale": (scaler.scale_.tolist() if scaler else None),
        "refit_using_test_subjects": False,
        "per_subject_calibration": False,
        "test_evaluations": 1,
        "y_true": y_te.tolist(),
        "y_pred": pred.tolist(),
        "subject": subjects[te].tolist(),
        "probs": probs.tolist(),
    }


def loso_within(X, y, subjects, cohort_subjects, **kw):
    """LOSO restricted to a named cohort (used for the SECONDARY arm).

    Each fold trains on the other cohort members and tests the held-out one, so
    the cohort's subjects DO participate in training in other folds. This is NOT
    an untouched external holdout and must never be described as one.
    """
    cohort = sorted(int(s) for s in cohort_subjects)
    m = np.isin(subjects, cohort)
    r = loso(X[m], y[m], subjects[m], **kw)
    if r is not None:
        r["restricted_to_subjects"] = cohort
        r["n_cohort_subjects"] = len(cohort)
    return r


def confusion_report(y_true, y_pred, subjects, classes, *, tier_key, tier_label,
                     model_key):
    """Confusion matrix plus per-class error decomposition for ONE evidence tier.

    The tier is a required argument and is embedded in the returned record, so a
    descriptive full-corpus matrix cannot be silently read as the primary
    confirmatory one.
    """
    yt = np.asarray(y_true)
    yp = np.asarray(y_pred)
    sst = np.asarray(subjects)
    if not (len(yt) == len(yp) == len(sst)):
        raise ValueError("y_true / y_pred / subject length mismatch")
    srcs = np.array([source_db_for_subject(int(s)) for s in sst])
    cm = confusion_matrix(yt, yp, labels=classes)

    per_src = {}
    for db in sorted(set(srcs.tolist())):
        m = srcs == db
        per_src[db] = {
            "n": int(m.sum()),
            "accuracy": float((yt[m] == yp[m]).mean()),
            "confusion": confusion_matrix(yt[m], yp[m], labels=classes).tolist(),
        }

    errs = []
    for i, t in enumerate(classes):
        for j, p in enumerate(classes):
            if i != j and cm[i, j]:
                m = (yt == t) & (yp == p)
                errs.append({
                    "true": int(t), "pred": int(p),
                    "true_name": labels.movement_name(1, t),
                    "pred_name": labels.movement_name(1, p),
                    "count": int(cm[i, j]),
                    "row_fraction": float(cm[i, j] / max(cm[i].sum(), 1)),
                    "by_source_dataset": dict(Counter(srcs[m].tolist())),
                })
    errs.sort(key=lambda d: (-d["row_fraction"], -d["count"]))

    return {
        "tier_key": tier_key,
        "tier": tier_label,
        "model": model_key,
        "classes": [int(c) for c in classes],
        "classes_named": {str(int(c)): labels.movement_name(1, int(c))
                          for c in classes},
        "n": int(len(yt)),
        "overall": cm.tolist(),
        "by_source_dataset": per_src,
        "total_errors": int((yt != yp).sum()),
        "top_confusions": errs,
        "per_class_recall": {
            str(int(c)): (float((yp[yt == c] == c).mean())
                          if int((yt == c).sum()) else None)
            for c in classes
        },
        "per_class_recall_by_source": {
            db: {str(int(c)): float((yp[(yt == c) & (srcs == db)] == c).mean())
                 for c in classes if ((yt == c) & (srcs == db)).sum()}
            for db in sorted(set(srcs.tolist()))
        },
    }


def source_held_out(X, y, subj, model_name="lda", normalize=True):
    """Train on two source databases, test on the third."""
    src = np.array([source_db_for_subject(int(s)) for s in subj])
    out = {}
    for db in sorted(set(src.tolist())):
        te, tr = src == db, src != db
        if te.sum() == 0 or tr.sum() == 0 or len(set(y[tr].tolist())) < 2:
            continue
        pred, _ = fit_predict(X[tr], y[tr], X[te], model_name, normalize)
        res = score(y[te], pred)
        res["train_sources"] = sorted(set(src[tr].tolist()))
        res["test_subjects"] = sorted(set(subj[te].tolist()))
        out[f"hold_out_{db}"] = res
    return out


def permutation_control(X, y, subj, model_name="lda", n_perm=20):
    rng = np.random.default_rng(SEED)
    accs = []
    for _ in range(n_perm):
        yp_ = y.copy()
        for s in np.unique(subj):
            m = subj == s
            yp_[m] = rng.permutation(yp_[m])
        r = loso(X, yp_, subj, model_name)
        if r:
            accs.append(r["pooled"]["accuracy"])
    return {"permuted_mean": float(np.mean(accs)), "permuted_std": float(np.std(accs)),
            "n_perm": len(accs), "chance": 1.0 / len(PRIMARY)}


# ---------------------------------------------------------------------------
# drift control -- SAME method as the 22-subject run, extended to all subjects
# ---------------------------------------------------------------------------
def build_drift(extracted: str) -> dict:
    """Per-subject drift trajectory from REST blocks only (no labels)."""
    traj = {}
    for slot, path in discover_unpacked(extracted):
        rec = load_recording(path)
        subject, _ = resolve_subject(slot, rec.subject, path)
        if db9_exercise_index(rec, subject) != 1:
            continue
        c16 = d2c.to_canonical16(rec.angles)
        rest_idx = np.flatnonzero(rec.restimulus == 0)
        if rest_idx.size < 400:
            continue
        blocks = [b for b in np.split(rest_idx, np.flatnonzero(np.diff(rest_idx) != 1) + 1)
                  if b.size >= 40]
        if len(blocks) < 4:
            continue
        t = np.array([b.mean() / rec.n_samples for b in blocks])
        meds = np.stack([np.median(c16[b], axis=0) for b in blocks])
        traj[subject] = (t, meds - meds[0])
    return traj


def posture_times(extracted: str) -> dict:
    out = {}
    for slot, path in discover_unpacked(extracted):
        rec = load_recording(path)
        subject, _ = resolve_subject(slot, rec.subject, path)
        if db9_exercise_index(rec, subject) != 1:
            continue
        rs, rr = rec.restimulus, rec.rerepetition
        for lab in sorted(set(int(v) for v in np.unique(rs)) - {0}):
            for rep in sorted(set(int(v) for v in np.unique(rr[rs == lab])) - {0}):
                idx = np.flatnonzero((rs == lab) & (rr == rep))
                if idx.size < 30:
                    continue
                k = idx.size // 3
                out[(subject, lab, rep)] = float(idx[k: idx.size - k].mean() / rec.n_samples)
    return out


def drift_estimate(X, y, subj, rep, traj, times):
    D = np.zeros_like(X)
    ok = np.zeros(len(y), dtype=bool)
    for i in range(len(y)):
        key = (int(subj[i]), int(y[i]), int(rep[i]))
        s = int(subj[i])
        if s in traj and key in times:
            t_grid, offsets = traj[s]
            t = times[key]
            D[i] = [np.interp(t, t_grid, offsets[:, c]) for c in range(offsets.shape[1])]
            ok[i] = True
    return D, ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--extracted", required=True)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--fig-dir", required=True)
    ap.add_argument(
        "--cohorts",
        default=os.path.join(_ROOT, cp.COHORT_RECORD_PATH.replace("/", os.sep)),
        help=("machine-derived cohort record; the primary confirmatory partition "
              "is read from here and is never hard-coded in this driver"),
    )
    args = ap.parse_args()
    for d in (args.data_dir, args.out_dir, args.fig_dir):
        os.makedirs(d, exist_ok=True)

    frozen = {
        "canonical16_names": list(d2c.canonical16_names()),
        "canonical12_noDIP_names": list(d2c.canonical12_noDIP_names()),
        "canonical15_noThumbAA_names": list(d2c.canonical15_noThumbAA_names()),
        "frozen_sign_transformation": dict(d2c.FROZEN_DB9_SIGN),
        "primary_movements": list(PRIMARY),
        "negative_control_movements": list(NEG_CONTROL),
        "control_representations": {
            "canonical12_noDIP": {
                "dropped": list(d2c.CANONICAL12_NODIP_DROPPED),
                "purpose": "DIP-sensor reliability control",
            },
            "canonical15_noThumbAA": {
                "dropped": list(d2c.CANONICAL15_NOTHUMBAA_DROPPED),
                "purpose": ("tests whether the residual cross-dataset uncertainty "
                            "in the thumb CMC ab/adduction axis materially drives "
                            "posture identifiability"),
            },
            "policy": ("all three representations are reported side by side; none "
                       "is used to select or tune the primary model, and the "
                       "primary model choice is fixed at canonical16"),
        },
        "central_fraction": rp.CENTRAL_FRACTION,
        "min_samples_per_repetition": rp.MIN_SAMPLES_PER_REPETITION,
        "models": list(MODEL_NAMES),
        "seed": SEED,
        "normalization": "train-only z-score, or none; never per-subject test centring",
        "drift_method": ("per-subject rest-block median trajectory, offsets relative "
                         "to the first rest block, linearly interpolated over "
                         "normalised session time, subtracted; label-free"),
        "claim": ("Stable target postures are identifiable from canonical hand "
                  "kinematics across unseen subjects. NOT a claim about continuous "
                  "or streaming recognition."),
        "evidence_tiers": {
            "A_primary_confirmatory": (
                "design item 2_untouched_confirmation.a_train_exposed_test_untouched "
                "-- train on the development-exposed cohort, test once on the "
                "outcome-unseen cohort. Strongest confirmatory evidence."),
            "B_full_77_loso_descriptive": (
                "design item 1_full_77_loso -- full-corpus replication figure. "
                "Descriptive only: the development-exposed subjects are inside "
                "this evaluation."),
            "C_secondary_confirmatory": (
                "design item 2_untouched_confirmation.b_loso_within_untouched -- "
                "LOSO inside the outcome-unseen cohort. Cohort peers are in every "
                "training fold, so this is not an untouched external holdout."),
            "rule": ("A is the primary number; B and C are reported alongside it "
                     "and may never be substituted for it. All three are computed "
                     "with the same frozen model, representation and metrics."),
        },
    }
    print("[frozen] design decisions (none of these are tuned in this run):")
    for k, v in frozen.items():
        print(f"    {k}: {v}")
    results: dict = {"frozen_protocol": frozen}

    # ---- extraction (ALWAYS rebuilt; no cache is trusted) -----------------
    # The confirmatory run must not reuse any previously produced artifact: the
    # 22-subject caches predate the frozen thumb-AA sign mapping, and a cached
    # central-third extract computed before the ordering fix would silently
    # contaminate the result. Caching is opt-in and validity-key checked; the
    # confirmatory path rebuilds unconditionally.
    reps_path = os.path.join(args.data_dir, "representative_postures_77.npz")
    traj_path = os.path.join(args.data_dir, "repetition_trajectories_77.npz")
    meta_path = os.path.join(args.data_dir, "representative_postures_77.meta.json")
    cache_meta_path = os.path.join(args.data_dir, "representative_postures_77.cache.json")
    if os.path.exists(reps_path):
        # Quarantine rather than delete: reversible, and it makes the invalidation
        # visible instead of leaving a stale artifact in place.
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        stale_dir = os.path.join(args.data_dir, "_invalidated")
        os.makedirs(stale_dir, exist_ok=True)
        for p in (reps_path, traj_path, meta_path, cache_meta_path):
            if os.path.exists(p):
                os.replace(p, os.path.join(stale_dir, f"{os.path.basename(p)}.{stamp}"))
        print(f"[phase2] quarantined pre-existing representative caches -> {stale_dir}")
    print("\n[phase2] REBUILDING representative postures from validated raw DB9 "
          "Exercise-B files (cache ignored by policy)")
    built = rp.extract_representatives(args.extracted, reps_path, traj_path, meta_path)
    A, meta = built["arrays"], built["meta"]
    if built["meta"].get("n_unusable_repetitions"):
        print(f"[phase2] {built['meta']['n_unusable_repetitions']} repetition(s) unusable "
              "and reported, not substituted")
    X16, X12 = A["X_canonical16"], A["X_canonical12_noDIP"]
    y, subj, rep = A["movement"], A["subject"], A["repetition"]
    results["extraction"] = {k: v for k, v in meta.items() if k != "files"}
    results["extraction_files"] = meta.get("files", [])

    # ---- item 2: manifest --------------------------------------------------
    print("\n[manifest] building subject manifest")
    manifest = build_manifest(reps_path, args.extracted)
    results["subject_manifest"] = manifest
    print(f"    {manifest['n_subjects']} subjects; {manifest['by_source_dataset']}")
    print(f"    expected: {manifest['expected']}")

    # ---- item 4: HARD subject-identity assertions -------------------------
    # Database of record is the archive slot. Equal in-file `subject` values
    # across different source databases are EXPECTED (DB1 slot 1, DB2 slot 28 and
    # DB5 slot 68 all record subject=1) and are not a defect; the real
    # requirement is that (source_database, recorded_subject) is injective and
    # that every global slot occurs exactly once.
    identity = cp.assert_corpus_identity(manifest["rows"], require_full=True)
    results["subject_identity_assertions"] = identity
    print(f"    identity assertions PASSED: {identity['by_source_dataset']} "
          f"total={identity['n_subjects']} (expected {identity['expected_total']})")
    print(f"      (source_database, recorded_subject) injective: "
          f"{identity['source_recorded_tuples_injective']}")
    with open(os.path.join(args.out_dir, "subject_manifest.json"), "w",
              encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    pm = np.isin(y, PRIMARY)
    X, yy, ss, rr = X16[pm], y[pm], subj[pm], rep[pm]
    src = np.array([source_db_for_subject(int(s)) for s in ss])

    # ---- item 3: composition ----------------------------------------------
    results["composition"] = {
        "n_repetitions": int(len(y)),
        "n_primary": int(pm.sum()),
        "subjects": sorted(set(int(s) for s in subj)),
        "subjects_by_source": {
            db: sorted(set(int(s) for s in ss[src == db])) for db in sorted(set(src.tolist()))
        },
        "primary_movements_by_source": {
            db: {str(m): int(((yy == m) & (src == db)).sum()) for m in PRIMARY}
            for db in sorted(set(src.tolist()))
        },
    }
    print(f"\n[phase6] primary set: {int(pm.sum())} postures from "
          f"{len(results['composition']['subjects'])} subjects")

    # =====================================================================
    # TIER A -- PRIMARY CONFIRMATORY ARM
    # =====================================================================
    # Frozen design item `2_untouched_confirmation.a_train_exposed_test_untouched`.
    #
    # The subjects that were used to develop, debug and inspect this experiment
    # are separated from the subjects whose outcomes have never been looked at.
    # The primary number is produced by fitting once on the development-exposed
    # cohort and predicting the outcome-unseen cohort exactly once.
    #
    # The partition is LOADED from the machine-derived cohort record, never
    # hard-coded here and never derived from leave-one-out logic, so cohort
    # membership cannot silently drift into this file.
    if not os.path.exists(args.cohorts):
        raise SystemExit(
            f"cohort record {args.cohorts} is missing; without it the primary "
            "confirmatory arm is undefined and this run must not proceed"
        )
    cohort_rec = cp.load_cohort_record(args.cohorts)
    exposed = [int(s) for s in cohort_rec["development_exposed"]]
    unseen = [int(s) for s in cohort_rec["outcome_unseen"]]
    partition = cp.assert_cohort_partition(exposed, unseen,
                                          sorted(set(int(s) for s in ss)))
    results["cohort_partition"] = {
        "source_artifact": os.path.abspath(args.cohorts),
        "loaded_not_hard_coded": True,
        "development_exposed": sorted(exposed),
        "outcome_unseen": sorted(unseen),
        **partition,
    }
    print(f"\n[TIER A / cohorts] loaded from {os.path.basename(args.cohorts)}: "
          f"development_exposed={partition['n_exposed']}  "
          f"outcome_unseen={partition['n_unseen']}  "
          f"partition of {partition['n_all_subjects']} subjects")

    print("[TIER A] PRIMARY confirmatory arm: train on development-exposed, "
          "test on outcome-unseen (one shot)")
    primary_key = cp.primary_run_key()
    prim = evaluate_explicit_partition(
        X, yy, ss, train_subjects=exposed, test_subjects=unseen,
    )
    prim["run_key"] = primary_key
    prim["design_item"] = "2_untouched_confirmation.a_train_exposed_test_untouched"
    prim["selection_rule"] = ("configuration fixed by pre-registration; never "
                              "selected from evaluation scores")
    prim["cohort_source_artifact"] = os.path.abspath(args.cohorts)
    results["primary_confirmatory"] = prim
    print(f"    {primary_key}  pooled accuracy = {prim['pooled']['accuracy']:.4f} "
          f"balanced_accuracy = {prim['pooled']['balanced_accuracy']:.4f} "
          f"macro_f1 = {prim['pooled']['macro_f1']:.4f}")
    print(f"    train n={prim['n_train_samples']} over {prim['n_train_subjects']} "
          f"subjects; test n={prim['n_test_samples']} over "
          f"{prim['n_test_subjects']} subjects; test evaluations=1")
    for db, d in prim["by_source_dataset"].items():
        print(f"      {db}: n={d['n']} accuracy={d['accuracy']:.4f}")

    # ---- TIER B: full-77 LOSO, DESCRIPTIVE only --------------------------
    # This is the full-corpus replication figure. It is NOT the primary
    # confirmatory evidence: it pools the development-exposed subjects into the
    # evaluation, so it cannot be the strongest confirmatory evidence and is
    # labelled accordingly.
    print("\n[TIER B / descriptive] full-77 leave-one-subject-out")
    loso_out = {}
    for model_name in MODEL_NAMES:
        for norm in (True, False):
            key = f"{model_name}__{'z' if norm else 'raw'}"
            r = loso(X, yy, ss, model_name, norm, sources=True)
            if r is None:
                continue
            loso_out[key] = r
            per = " ".join(f"{k}={v['accuracy']:.4f}" for k, v in
                           r["by_source_dataset"].items())
            print(f"    {key:<38} overall={r['pooled']['accuracy']:.4f}  {per}")
    # The frozen configuration is returned BY IDENTITY: no score is consulted and
    # a higher-scoring secondary run may not displace it. `select_primary`
    # contains no max/argmax/ranking.
    desc_key, desc_run = cp.select_primary(loso_out)
    if desc_run is None:
        raise SystemExit(
            f"frozen configuration {desc_key} did not run in the full-77 LOSO "
            "pass; refusing to fall back to another configuration"
        )
    results["full_77_loso_descriptive"] = {
        "tier": ("B: full-corpus descriptive evidence (NOT the primary "
                 "confirmatory arm -- the development-exposed subjects are "
                 "included in this evaluation)"),
        "design_item": "1_full_77_loso",
        "run_key": desc_key,
        "model": cp.PRIMARY_MODEL,
        "model_config": cp.PRIMARY_MODEL_CONFIG,
        "normalization": cp.PRIMARY_NORMALIZATION,
        "representation": cp.PRIMARY_REPRESENTATION,
        "n_subjects": len(set(int(s) for s in ss)),
        "overall": desc_run["pooled"],
        "by_source_dataset": desc_run["by_source_dataset"],
        "per_subject": desc_run["per_subject"],
        "all_configurations": {
            k: {kk: vv for kk, vv in v.items()
                if kk not in ("y_true", "y_pred", "subject")}
            for k, v in loso_out.items()
        },
        "selection_rule": ("frozen configuration returned by identity; never "
                           "selected from evaluation scores"),
    }
    results["secondary_exploratory_runs"] = sorted(k for k in loso_out if k != desc_key)
    print(f"    frozen configuration (by identity): {desc_key}  "
          f"accuracy={desc_run['pooled']['accuracy']:.4f}")
    print(f"    {len(results['secondary_exploratory_runs'])} other configuration(s) "
          f"reported for information only")

    # ---- TIER C: secondary confirmatory, LOSO within the unseen cohort ----
    # Frozen design item `2_untouched_confirmation.b_loso_within_untouched`.
    # Every subject here was outcome-unseen, but in each fold the held-out
    # subject's cohort peers ARE in the training set, so this is a within-cohort
    # generalisation estimate and NOT an untouched external holdout.
    print("\n[TIER C] secondary confirmatory: LOSO within the outcome-unseen cohort")
    sec = loso_within(
        X, yy, ss, unseen, model_name=cp.PRIMARY_MODEL,
        normalize=(cp.PRIMARY_NORMALIZATION == "train_only_zscore"), sources=True,
    )
    if sec is None:
        raise SystemExit(
            "secondary confirmatory arm produced no folds; refusing to continue"
        )
    sec_cohort = sec.pop("restricted_to_subjects")
    sec_n = sec.pop("n_cohort_subjects")
    results["secondary_confirmatory"] = {
        "tier": ("C: secondary confirmatory -- LOSO within the outcome-unseen "
                 "cohort; cohort peers participate in training in every fold, so "
                 "this is NOT an untouched external holdout"),
        "design_item": "2_untouched_confirmation.b_loso_within_untouched",
        "run_key": primary_key,
        "model": cp.PRIMARY_MODEL,
        "model_config": cp.PRIMARY_MODEL_CONFIG,
        "normalization": cp.PRIMARY_NORMALIZATION,
        "representation": cp.PRIMARY_REPRESENTATION,
        "restricted_to_subjects": sec_cohort,
        "n_cohort_subjects": sec_n,
        "overall": sec["pooled"],
        "by_source_dataset": sec["by_source_dataset"],
        "per_subject": sec["per_subject"],
        "y_true": sec["y_true"],
        "y_pred": sec["y_pred"],
        "subject": sec["subject"],
    }
    print(f"    {primary_key}  pooled LOSO accuracy = "
          f"{sec['pooled']['accuracy']:.4f} "
          f"balanced_accuracy = {sec['pooled']['balanced_accuracy']:.4f}")

    # ---- evidence-tier summary -------------------------------------------
    # One machine-readable statement of which number is allowed to carry which
    # claim, so no downstream reader has to infer it.
    a_acc = results["primary_confirmatory"]["pooled"]["accuracy"]
    b_acc = results["full_77_loso_descriptive"]["overall"]["accuracy"]
    c_acc = results["secondary_confirmatory"]["overall"]["accuracy"]
    results["evidence_tiers"] = {
        "A_primary_confirmatory": {
            "design_item": "2_untouched_confirmation.a_train_exposed_test_untouched",
            "n_test_subjects": results["primary_confirmatory"]["n_test_subjects"],
            "accuracy": a_acc,
            "may_be_cited_as": ("the primary confirmatory evidence for posture "
                                "identifiability across unseen subjects"),
            "may_not_be_cited_as": ("a full-corpus figure; its test subjects are "
                                    "only the outcome-unseen cohort"),
        },
        "B_full_77_loso_descriptive": {
            "design_item": "1_full_77_loso",
            "n_subjects": results["full_77_loso_descriptive"]["n_subjects"],
            "accuracy": b_acc,
            "may_be_cited_as": "full-corpus descriptive replication evidence",
            "may_not_be_cited_as": ("the primary confirmatory result; the "
                                    "development-exposed subjects are inside this "
                                    "evaluation"),
        },
        "C_secondary_confirmatory": {
            "design_item": "2_untouched_confirmation.b_loso_within_untouched",
            "n_cohort_subjects": results["secondary_confirmatory"]["n_cohort_subjects"],
            "accuracy": c_acc,
            "may_be_cited_as": ("a within-outcome-unseen-cohort generalisation "
                                "estimate"),
            "may_not_be_cited_as": "an untouched external holdout result",
        },
        "ordering_rule": ("A is the strongest evidence; B and C are supportive "
                          "and are never substituted for A"),
        "strongest_confirmatory_evidence": "A_primary_confirmatory",
    }
    print("\n[tiers] A(primary)={:.4f}  B(full-77 descriptive)={:.4f}  "
          "C(secondary)={:.4f}".format(a_acc, b_acc, c_acc))

    # ---- item 8: source-held-out ------------------------------------------
    print("\n[source-held-out] train on two source databases, test on the third")
    so = {}
    for model_name in MODEL_NAMES:
        for norm in (True, False):
            key = f"{model_name}__{'z' if norm else 'raw'}"
            res = source_held_out(X, yy, ss, model_name, norm)
            if res:
                so[key] = res
                txt = " ".join(f"{k.replace('hold_out_','')}={v['accuracy']:.4f}"
                               for k, v in res.items())
                print(f"    {key:<38} {txt}")
    so["_meta"] = {
        "tier": ("C: secondary/exploratory comparison -- source-database transfer. "
                 "NOT the primary confirmatory arm."),
        "design_item": "4_source_held_out",
        "note": ("held-out source database subjects are not the primary "
                 "confirmatory test set; this is reported alongside arm A and is "
                 "never substituted for it"),
    }
    results["source_held_out"] = so

    # ---- item 9: representation controls, overall and per source ----------
    # Three representations, reported side by side.  canonical16 is the primary
    # and its model choice is already fixed; the two controls exist to be
    # reported, NOT to select or tune anything.
    print("\n[representation controls] canonical16 vs canonical12_noDIP vs "
          "canonical15_noThumbAA")
    X15p = d2c.canonical15_from_canonical16(X16)[pm]
    reps = {"canonical16": X, "canonical12_noDIP": X12[pm], "canonical15_noThumbAA": X15p}
    dip = {}
    for model_name in MODEL_NAMES:
        for norm in (True, False):
            key = f"{model_name}__{'z' if norm else 'raw'}"
            per_rep = {name: loso(M, yy, ss, model_name, norm, sources=True)
                       for name, M in reps.items()}
            if any(v is None for v in per_rep.values()):
                continue
            dip[key] = {
                name: {
                    "overall": v["pooled"],
                    "by_source_dataset": v["by_source_dataset"],
                }
                for name, v in per_rep.items()
            }
            base = per_rep["canonical16"]["pooled"]["accuracy"]
            dip[key]["delta_vs_canonical16"] = {
                name: per_rep[name]["pooled"]["accuracy"] - base for name in reps
            }
            dip[key]["delta_by_source_vs_canonical16"] = {
                name: {
                    db: per_rep[name]["by_source_dataset"][db]["accuracy"]
                        - per_rep["canonical16"]["by_source_dataset"][db]["accuracy"]
                    for db in per_rep["canonical16"]["by_source_dataset"]
                    if db in per_rep[name]["by_source_dataset"]
                }
                for name in reps if name != "canonical16"
            }
            d = dip[key]["delta_vs_canonical16"]
            print(f"    {key:<38} c16={base:.4f}  "
                  f"noDIP={per_rep['canonical12_noDIP']['pooled']['accuracy']:.4f} "
                  f"({d['canonical12_noDIP']:+.4f})  "
                  f"noThumbAA={per_rep['canonical15_noThumbAA']['pooled']['accuracy']:.4f} "
                  f"({d['canonical15_noThumbAA']:+.4f})")
    dip["_meta"] = {
        "tier": ("C: secondary/exploratory comparison -- pre-registered "
                 "representation controls on the full-77 LOSO corpus. NOT the "
                 "primary confirmatory arm."),
        "design_item": "5_representation_controls",
        "note": ("the primary confirmatory number is produced by arm A with "
                 "canonical16 only; these controls are reported alongside it and "
                 "never substituted for it"),
    }
    results["representation_controls"] = dip
    results["representation_controls_policy"] = (
        "canonical16 is the primary representation and its model is fixed. The "
        "two control representations are REPORTED ONLY and were pre-registered; "
        "no model, hyperparameter or representation was selected using them."
    )
    # Backwards-compatible key so downstream readers of the 22-subject artefact
    # do not silently lose the DIP comparison.
    results["dip_control"] = {
        k: {
            "canonical16": v["canonical16"]["overall"],
            "canonical12_noDIP": v["canonical12_noDIP"]["overall"],
            "delta": v["delta_vs_canonical16"]["canonical12_noDIP"],
            "canonical16_by_source": v["canonical16"]["by_source_dataset"],
            "canonical12_noDIP_by_source": v["canonical12_noDIP"]["by_source_dataset"],
            "delta_by_source": v["delta_by_source_vs_canonical16"]["canonical12_noDIP"],
            "canonical15_noThumbAA": v["canonical15_noThumbAA"]["overall"],
            "delta_noThumbAA": v["delta_vs_canonical16"]["canonical15_noThumbAA"],
            "delta_noThumbAA_by_source":
                v["delta_by_source_vs_canonical16"]["canonical15_noThumbAA"],
        }
        for k, v in dip.items() if not k.startswith("_")
    }
    results["dip_control"]["_tier"] = dip["_meta"]["tier"]

    # ---- item 10: drift + permutation controls, correctly labelled --------
    # These are ORACLE / TEST-SUBJECT-CALIBRATED UPPER-BOUND analyses, NOT clean
    # leakage-free falsification controls:
    #   * drift-corrected subtracts a trajectory estimated from the HELD-OUT
    #     subject's own rest samples -- a test-subject-derived statistic;
    #   * drift-only locates the measurement time using the TRUE movement label.
    # They bound how much a session-time shortcut could explain. They are not
    # deployment-valid, and the primary posture-identifiability result does not
    # depend on any drift correction.
    print("\n[drift control] ORACLE / TEST-SUBJECT-CALIBRATED UPPER BOUND "
          "(explicitly NOT a leakage-free control)")
    traj = build_drift(args.extracted)
    times = posture_times(args.extracted)
    D, ok = drift_estimate(X, yy, ss, rr, traj, times)
    print(f"    drift estimated for {int(ok.sum())}/{len(yy)} postures "
          f"({len(traj)} subjects)")
    ctrl = {"n_with_drift": int(ok.sum()), "n_total": int(len(yy))}
    if ok.sum() > 0:
        ctrl["drift_only"] = loso(D[ok], yy[ok], ss[ok], "lda", True)["pooled"]
        ctrl["canonical16"] = loso(X[ok], yy[ok], ss[ok], "lda", True)["pooled"]
        ctrl["drift_corrected"] = loso(X[ok] - D[ok], yy[ok], ss[ok], "lda", True)["pooled"]
        ctrl["delta_corrected_vs_plain"] = (
            ctrl["drift_corrected"]["accuracy"] - ctrl["canonical16"]["accuracy"])
        for k in ("drift_only", "canonical16", "drift_corrected"):
            print(f"    {k:<18} LOSO = {ctrl[k]['accuracy']:.4f}")
        print(f"    drift-corrected minus plain = {ctrl['delta_corrected_vs_plain']:+.4f}")
    print("\n[permutation control] labels shuffled within subject "
          "(this one IS leakage-free)")
    ctrl["permutation"] = permutation_control(X, yy, ss)
    print(f"    permuted LOSO = {ctrl['permutation']['permuted_mean']:.4f} "
          f"+- {ctrl['permutation']['permuted_std']:.4f} "
          f"(chance {ctrl['permutation']['chance']:.4f})")
    ctrl["validity"] = {
        "tier": "ORACLE / TEST-SUBJECT-CALIBRATED UPPER BOUND",
        "evidence_tier": ("supporting control only; NOT the primary confirmatory "
                          "arm, and never substituted for it"),
        "leakage_free": False,
        "why_not_leakage_free": [
            "drift-corrected uses a trajectory estimated from the held-out "
            "subject's own rest samples (a test-subject-derived statistic)",
            "drift-only locates measurement time using the true movement label",
        ],
        "may_be_cited_as": ("an upper bound on how much a session-time shortcut "
                            "could explain"),
        "may_not_be_cited_as": ("a deployment-valid or leakage-free control, or as "
                                "support for the primary result"),
        "leakage_free_subcomponent": "permutation",
        "primary_result_depends_on_drift_correction": False,
    }
    results["controls"] = ctrl

    # ---- item 11/13: confusion + errors by class and source, PER TIER -----
    # Every confusion matrix is computed from the FROZEN PRIMARY configuration
    # (never from whichever configuration scored highest) and carries an explicit
    # evidence tier, so the full-corpus descriptive matrix can never be read as
    # the primary confirmatory one.
    classes = sorted(set(int(v) for v in yy))
    print("\n[TIER A confusion] primary confirmatory arm "
          "(train development-exposed -> test outcome-unseen), by source database")
    confusion = {
        "primary_confirmatory": confusion_report(
            prim["y_true"], prim["y_pred"], prim["subject"], classes,
            tier_key="A_primary_confirmatory",
            model_key=primary_key,
            tier_label=("A: PRIMARY CONFIRMATORY -- one-shot external holdout "
                        "(train on development-exposed, test on outcome-unseen)"),
        ),
        "full_77_loso_descriptive": confusion_report(
            desc_run["y_true"], desc_run["y_pred"], desc_run["subject"], classes,
            tier_key="B_full_77_loso_descriptive",
            model_key=desc_key,
            tier_label=("B: full-corpus descriptive evidence (NOT the primary "
                        "confirmatory arm; development-exposed subjects are "
                        "inside this evaluation)"),
        ),
        "secondary_confirmatory": confusion_report(
            results["secondary_confirmatory"]["y_true"],
            results["secondary_confirmatory"]["y_pred"],
            results["secondary_confirmatory"]["subject"], classes,
            tier_key="C_secondary_confirmatory",
            model_key=primary_key,
            tier_label=("C: secondary confirmatory -- LOSO within the "
                        "outcome-unseen cohort (NOT an untouched external holdout)"),
        ),
        "classes": classes,
        "classes_named": {str(c): labels.movement_name(1, c) for c in classes},
        "tier_rule": ("`primary_confirmatory` is the primary confusion matrix; "
                      "the other two are reported alongside it and are never "
                      "substituted for it"),
    }
    results["confusion"] = confusion
    cm = np.array(confusion["primary_confirmatory"]["overall"], dtype=int)
    print(f"    rows=true, cols=predicted, classes={classes}")
    for i, c in enumerate(classes):
        print(f"      {c:>2} " + " ".join(f"{v:>4}" for v in cm[i]))

    # Errors are reported at the PRIMARY tier. The descriptive and secondary
    # decompositions stay inside `results["confusion"]` above.
    a_report = confusion["primary_confirmatory"]
    results["errors_by_class_and_source"] = {
        "tier_key": a_report["tier_key"],
        "tier": a_report["tier"],
        "model": a_report["model"],
        "n": a_report["n"],
        "total_errors": a_report["total_errors"],
        "top_confusions": a_report["top_confusions"],
        "per_class_recall": a_report["per_class_recall"],
        "per_class_recall_by_source": a_report["per_class_recall_by_source"],
        "note": ("this decomposition is the PRIMARY confirmatory arm; the "
                 "descriptive and secondary decompositions are in "
                 "results['confusion']"),
    }
    print(f"\n    {a_report['total_errors']} errors of {a_report['n']} "
          f"(primary confirmatory arm)")
    for e in a_report["top_confusions"][:6]:
        print(f"      {e['true_name'][:38]:<38} -> {e['pred_name'][:38]:<38} "
              f"n={e['count']} {e['by_source_dataset']}")

    # ---- figures -----------------------------------------------------------
    # Tier-tagged filenames: a figure can never be mistaken for the wrong arm.
    for tag, block, key in (
        ("primary_confirmatory", confusion["primary_confirmatory"], "A"),
        ("full77_loso", confusion["full_77_loso_descriptive"], "B"),
    ):
        for db, d in block["by_source_dataset"].items():
            c = np.array(d["confusion"], dtype=float)
            cn = c / np.maximum(c.sum(axis=1, keepdims=True), 1)
            fig, ax = plt.subplots(figsize=(7, 6))
            im = ax.imshow(cn, cmap="Blues", vmin=0, vmax=1)
            names = [labels.movement_name(1, int(k))[:24] for k in classes]
            ax.set_xticks(range(len(classes))); ax.set_yticks(range(len(classes)))
            ax.set_xticklabels(names, rotation=45, ha="right", fontsize=7)
            ax.set_yticklabels(names, fontsize=7)
            for i in range(len(classes)):
                for j in range(len(classes)):
                    if c[i, j]:
                        ax.text(j, i, str(int(c[i, j])), ha="center", va="center",
                                fontsize=8, color="white" if cn[i, j] > 0.5 else "black")
            ax.set_title(f"[TIER {key}] {tag} -- {db} only (n={d['n']}, "
                         f"acc={d['accuracy']:.3f})")
            ax.set_xlabel("predicted"); ax.set_ylabel("true")
            fig.colorbar(im, ax=ax, fraction=0.046)
            fig.tight_layout()
            fig.savefig(os.path.join(args.fig_dir, f"confusion_{tag}_{db}.png"), dpi=150)
            plt.close(fig)

    with open(os.path.join(args.out_dir, "full_db9_results.json"), "w",
              encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print(f"\n[done] {os.path.join(args.out_dir, 'full_db9_results.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
