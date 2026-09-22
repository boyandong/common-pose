"""build_cv.py - the subject-grouped cross-validated experiment.

Everything evaluated here uses the FROZEN protocol from the plan:
  * grouped 5-fold over the 22 subjects, deterministic round-robin assignment
  * TRAIN-FOLD-ONLY z-scoring
  * one frozen configuration per model, no hyperparameter search
  * the same model family across representations so the comparison is fair
  * INTERIOR frames as the primary stratum

Produces:
  KINMUS_SINGLE_FRAME_RESULTS.json   (R1, plus baselines and the full model set)
  KINMUS_VELOCITY_RESULTS.json       (R2 + temporal-shuffle control)
  KINMUS_TRAJECTORY_RESULTS.json     (R3, sensitivity windows, shuffle control)
  KINMUS_OBSERVABILITY_NULL_CONTROL.json
  results/predictions.npz            (per-frame held-out output, reused later)
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import obs_common as C  # noqa: E402
import obs_plan as P  # noqa: E402

CACHE = os.path.join(C.RESULTS, "features.npz")
PRED = os.path.join(C.RESULTS, "predictions.npz")
#: Cache of the expensive real-data fits so a later-stage crash cannot force a
#: 40-minute recomputation.  Keyed on the frozen plan hash.
REAL_CACHE = os.path.join(C.RESULTS, "real_results_cache.json")
PRED_CACHE = os.path.join(C.RESULTS, "real_preds_cache.npz")

SEED = P.VALIDATION and 20260101
#: SVM row caps.  LDA/LR see every row; the SVM control models are subsampled
#: because kernel fitting is superlinear in rows.  The cap is a COMPUTE choice,
#: identical across representations, so it cannot bias the comparison.  It was
#: lowered from the first attempt's 60000/30000 to 30000/15000 after the first
#: attempt spent over an hour inside SVC on R2 alone; the cap is recorded in
#: every SVM result so the reader sees the subsample actually used.
SVM_TRAIN_CAP = 30000
SVM_TEST_CAP = 15000


def folds_of(subject_ids: np.ndarray) -> dict[int, np.ndarray]:
    """Deterministic round-robin fold assignment over sorted subject ids."""
    uniq = np.sort(np.unique(subject_ids))
    return {int(s): int(i % 5) + 1 for i, s in enumerate(uniq)}


def fit_predict(model: str, Xtr, ytr, Xte, seed: int = 0):
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import SVC
    if model == "LDA":
        clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
    elif model == "LR":
        clf = LogisticRegression(multi_class="multinomial", solver="lbfgs",
                                 max_iter=2000, C=1.0)
    elif model == "LSVM":
        clf = SVC(kernel="linear", C=1.0)
    elif model == "RSVM":
        clf = SVC(kernel="rbf", C=1.0, gamma="scale")
    else:
        raise ValueError(model)
    clf.fit(Xtr, ytr)
    return np.asarray(clf.predict(Xte), dtype=np.int64)


def zscore_fit(Xtr):
    mu = Xtr.mean(axis=0)
    sd = Xtr.std(axis=0, ddof=0)
    sd = np.where(sd < 1e-12, 1.0, sd)
    return mu, sd


def metrics(y, yhat, subjects) -> dict:
    ba = C.balanced_accuracy(y, yhat)
    m = {
        "n": int(y.size),
        "balanced_accuracy": ba,
        "macro_f1": C.macro_f1(y, yhat),
        "accuracy": float((y == yhat).mean()) if y.size else None,
        "confusion": C.confusion(y, yhat),
        "directional_error": {
            "reaching_as_releasing": rate_of(y, yhat, 1, 3),
            "releasing_as_reaching": rate_of(y, yhat, 3, 1),
            "def": ("P(pred=RELEASING | true=REACHING) and "
                    "P(pred=REACHING | true=RELEASING)"),
        },
    }
    if subjects is not None:
        per = {}
        for s in np.unique(subjects):
            sel = subjects == s
            if sel.sum() == 0:
                continue
            with np.errstate(invalid="ignore"):
                per[str(int(s))] = {
                    "n": int(sel.sum()),
                    "balanced_accuracy": C.balanced_accuracy(y[sel], yhat[sel]),
                    "accuracy": float((y[sel] == yhat[sel]).mean()),
                }
        vals = np.array([v["balanced_accuracy"] for v in per.values()],
                        dtype=np.float64)
        vals = vals[np.isfinite(vals)]
        m["per_subject_balanced_accuracy"] = per
        # every summary is GUARDED: a stratum can be empty for a subject (e.g. a
        # subject with no boundary frames in a fold), and an empty reduction must
        # not crash the run
        m["across_subject_mean_ba"] = float(vals.mean()) if vals.size else None
        m["across_subject_sd_ba"] = (float(vals.std(ddof=1))
                                     if vals.size > 1 else None)
        m["worst_subject_ba"] = float(vals.min()) if vals.size else None
        m["n_subjects_scored"] = int(vals.size)
        m["n_subjects_ba_ge_0.50"] = int((vals >= 0.50).sum()) if vals.size else 0
        m["n_subjects_ba_lt_0.45"] = int((vals < 0.45).sum()) if vals.size else 0
    return m


def rate_of(y, yhat, true_c, pred_c) -> dict:
    sel = y == true_c
    if sel.sum() == 0:
        return {"numerator": 0, "denominator": 0, "value": None,
                "wilson95": [None, None]}
    return C.rate(int((yhat[sel] == pred_c).sum()), int(sel.sum()))


def run_cv(X, ok, y, subj, mask, models, fold_of, *, seed=0, verbose=True,
           caps=False):
    """Grouped 5-fold CV.  Returns per-model pooled predictions and metrics."""
    out = {}
    for model in models:
        yhat = np.full(y.size, -1, dtype=np.int64)
        per_fold = []
        for f in sorted(set(fold_of.values())):
            te_s = {s for s, k in fold_of.items() if k == f}
            tr = np.array([s not in te_s for s in subj])
            te = np.array([s in te_s for s in subj])
            sel_tr = tr & mask & ok
            sel_te = te & mask & ok
            if sel_tr.sum() == 0 or sel_te.sum() == 0:
                continue
            Xtr, ytr = X[sel_tr], y[sel_tr]
            if caps:
                rng = np.random.default_rng(SEED + f)
                if Xtr.shape[0] > SVM_TRAIN_CAP:
                    idx = rng.choice(Xtr.shape[0], SVM_TRAIN_CAP, replace=False)
                    Xtr, ytr = Xtr[idx], ytr[idx]
            mu, sd = zscore_fit(Xtr)
            Xtr_z = (Xtr - mu) / sd
            te_idx = np.flatnonzero(sel_te)
            Xte = X[te_idx]
            if caps and Xte.shape[0] > SVM_TEST_CAP:
                rng = np.random.default_rng(SEED + 100 + f)
                keep = rng.choice(Xte.shape[0], SVM_TEST_CAP, replace=False)
                keep.sort()
                te_idx = te_idx[keep]
                Xte = X[te_idx]
            Xte_z = (Xte - mu) / sd
            p = fit_predict(model, Xtr_z, ytr, Xte_z, seed=seed)
            yhat[te_idx] = p
            per_fold.append({
                "fold": int(f), "n_test": int(te_idx.size),
                "test_subjects": sorted(int(s) for s in te_s),
                "balanced_accuracy": C.balanced_accuracy(y[te_idx], p),
            })
        keep = yhat >= 0
        m = metrics(y[keep], yhat[keep], subj[keep])
        m["per_fold"] = per_fold
        m["mean_fold_ba"] = float(np.mean([f["balanced_accuracy"]
                                           for f in per_fold])) if per_fold else None
        m["sd_fold_ba"] = float(np.std([f["balanced_accuracy"] for f in per_fold],
                                       ddof=1)) if len(per_fold) > 1 else None
        m["row_caps_applied"] = bool(caps)
        m["svm_train_cap"] = SVM_TRAIN_CAP if caps else None
        m["svm_test_cap"] = SVM_TEST_CAP if caps else None
        out[model] = {"metrics": m, "yhat": yhat, "keep": keep}
        if verbose:
            print(f"      {model:<5} BA={m['balanced_accuracy']:.4f} "
                  f"acc={m['accuracy']:.4f} F1={m['macro_f1']:.4f} "
                  f"n={m['n']}")
    return out


def _per_subject_trial_labels(y, trial_index, subj, sid):
    """Return (unique_trial_codes, inverse_map, label_per_code) for one subject."""
    key = np.asarray(trial_index)[np.asarray(subj) == sid]
    codes, inv = np.unique(key, return_inverse=True)
    lab = np.empty(codes.size, dtype=np.int64)
    for i, c in enumerate(codes):
        lab[i] = int(np.asarray(y)[np.asarray(trial_index) == c][0])
    return codes, inv, lab


def permute_trial_labels(y, trial_index, subj, rng):
    """N1: permute the phase label across each subject's own trials.

    Destroys only the phase-to-pose correspondence; preserves the subject's
    movement repertoire, the segment lengths and the class structure.  Frames are
    NEVER permuted individually, because that would destroy temporal
    autocorrelation and give an unrealistically easy null.

    Implemented entirely in terms of ALLOCATED output positions (np.flatnonzero),
    never in terms of a boolean mask against ``y``, so it cannot be broken by an
    enclosing scope that has rebound the name ``y`` to a filtered array.
    """
    y = np.asarray(y)
    trial_index = np.asarray(trial_index)
    subj = np.asarray(subj)
    yp = y.copy()
    for s in np.unique(subj):
        pos = np.flatnonzero(subj == s)
        codes, inv, lab = _per_subject_trial_labels(y, trial_index, subj, s)
        newlab = lab[rng.permutation(lab.size)]
        yp[pos] = newlab[inv]
    return yp


def circular_shift_labels(y, trial_index, subj):
    """N2: circularly rotate each subject's phase-label sequence across trials."""
    y = np.asarray(y)
    trial_index = np.asarray(trial_index)
    subj = np.asarray(subj)
    yp = y.copy()
    for s in np.unique(subj):
        pos = np.flatnonzero(subj == s)
        codes, inv, lab = _per_subject_trial_labels(y, trial_index, subj, s)
        yp[pos] = np.roll(lab, 1)[inv]
    return yp


def main() -> int:
    t0 = time.time()
    log, fh = C.log_to(os.path.join(C.LANE, "KINMUS_TASK_OBSERVABILITY_FULL_LOG.txt"))
    log("")
    log("=" * 78)
    log("STAGE 8 - SUBJECT-GROUPED CROSS-VALIDATED EXPERIMENT")
    log("=" * 78)
    plan_sha = C.sha256_file(os.path.join(C.LANE, P.PLAN_ARTIFACT))
    log(f"frozen plan sha256 = {plan_sha}")

    z = np.load(CACHE, allow_pickle=False)
    y = z["phase"]
    subj = z["subject"]
    trial_index = z["trial_index"]
    interior = z["boundary_interior"]
    fold_of = folds_of(subj)
    log(f"rows {y.size}, subjects {np.unique(subj).size}, "
        f"interior rows {int(interior.sum())}")
    log(f"folds: { {k: int(v) for k, v in sorted(fold_of.items())} }")

    REPS = {"R1_POSE": ("pose", []),
            "R2_POSE_VELOCITY": ("velocity", []),
            "R3_TRAJECTORY": ("trajectory", []),
            "R4_POSE_PAST_ONLY": ("causal", []),
            "R5_FULL18": ("full18", []),
            "R6_FULL18_VELOCITY": ("full18", [])}

    results = {}
    preds = {}
    base = None          # bound before flush() can reference it
    cached = None
    if os.path.exists(REAL_CACHE) and os.path.exists(PRED_CACHE):
        try:
            blob = C.load_json(REAL_CACHE)
            if blob.get("plan_sha256") == plan_sha:
                results = blob["results"]
                base = blob["base"]
                zp = np.load(PRED_CACHE, allow_pickle=False)
                preds = {k: zp[k] for k in zp.files}
                cached = True
                log("  [cache] real-fit results reused (plan hash matches)")
        except Exception as exc:  # noqa: BLE001
            log(f"  [cache] unreadable ({exc!r}); recomputing")

    def flush():
        """Persist partial real-fit results so a crash cannot force a recompute."""
        C.write_json(REAL_CACHE, {"plan_sha256": plan_sha, "results": results,
                                  "base": base, "partial": True})
        if preds:
            np.savez_compressed(PRED_CACHE, **preds)

    if not cached:
        for rep in REPS:
            X = z[rep]
            ok = z[rep + "_ok"]
            results[rep] = {}
            results[rep]["_shape"] = list(X.shape)
            # ---- primary model on every representation (fair comparison) ---
            log("")
            log(f"  [{rep}] {X.shape[1]} features, {int((ok & interior).sum())} "
                f"interior rows")
            res = run_cv(X, ok, y, subj, interior, ["LDA"], fold_of)
            results[rep]["LDA"] = res["LDA"]["metrics"]
            preds[rep + "|LDA"] = res["LDA"]["yhat"]
            flush()

        # ---- the full controlled model set on the three primary representations
        for rep in ("R1_POSE", "R2_POSE_VELOCITY", "R3_TRAJECTORY"):
            log("")
            log(f"  [{rep}] control models (subsampled: train<={SVM_TRAIN_CAP}, "
                f"test<={SVM_TEST_CAP})")
            res = run_cv(z[rep], z[rep + "_ok"], y, subj, interior,
                         ["LR", "LSVM", "RSVM"], fold_of, caps=True)
            for k, v in res.items():
                results[rep][k] = v["metrics"]
                preds[rep + "|" + k] = v["yhat"]
            flush()

    # ------------------------------------------------------------- baselines
    log("")
    log("  [baselines] majority / prior / balanced-random (train-fold priors)")
    if not cached:
        base = {}
    if base is None:
        base = {}
    for name in ("majority", "prior", "balanced_random"):
        yhat = np.full(y.size, -1, dtype=np.int64)
        rng = np.random.default_rng(SEED)
        for f in sorted(set(fold_of.values())):
            te_s = {s for s, k in fold_of.items() if k == f}
            tr = np.array([s not in te_s for s in subj])
            te = np.array([s in te_s for s in subj])
            sel_tr, sel_te = tr & interior, te & interior
            counts = {c: int((y[sel_tr] == c).sum()) for c in C.PHASES}
            if name == "majority":
                pred = max(counts, key=lambda c: counts[c])
                yhat[sel_te] = pred
            elif name == "prior":
                tot = sum(counts.values())
                probs = np.array([counts[c] / tot if tot else 1 / 3
                                  for c in C.PHASES])
                yhat[sel_te] = rng.choice(np.array(C.PHASES), size=int(sel_te.sum()),
                                          p=probs)
            else:
                yhat[sel_te] = rng.choice(np.array(C.PHASES),
                                          size=int(sel_te.sum()))
        keep = yhat >= 0
        base[name] = metrics(y[keep], yhat[keep], subj[keep])
        log(f"    {name:<16} BA={base[name]['balanced_accuracy']:.4f} "
            f"acc={base[name]['accuracy']:.4f}")
    # the analytic prior-only BA is 1/3; report both
    base["prior_only_analytic_balanced_accuracy"] = 1.0 / 3.0

    # persist the expensive real fits so a later crash cannot force a recompute
    if not cached:
        C.write_json(REAL_CACHE, {"plan_sha256": plan_sha, "results": results,
                                  "base": base})
        np.savez_compressed(PRED_CACHE, **preds)
        log("  [cache] real-fit results persisted")

    # ------------------------------------------------------------- nulls
    log("")
    log("  [null] N1 trial permutation and N2 circular shift, "
        f"{P.NULL_CONTROL['replicates']} replicates each")
    rng = np.random.default_rng(SEED)
    null = {}
    for rep in ("R1_POSE", "R2_POSE_VELOCITY", "R3_TRAJECTORY"):
        X, ok = z[rep], z[rep + "_ok"]
        for scheme, fn in (("N1_TRIAL_PERMUTATION", permute_trial_labels),
                           ("N2_CIRCULAR_SHIFT", None)):
            bas = []
            for r in range(P.NULL_CONTROL["replicates"]):
                if fn is None:
                    yp = circular_shift_labels(y, trial_index, subj)
                else:
                    yp = fn(y, trial_index, subj, rng)
                res = run_cv(X, ok, yp, subj, interior, ["LDA"], fold_of,
                             verbose=False)
                m = res["LDA"]["metrics"]
                bas.append({"balanced_accuracy": m["balanced_accuracy"],
                            "accuracy": m["accuracy"], "macro_f1": m["macro_f1"],
                            "n": m["n"]})
            arr = np.array([b["balanced_accuracy"] for b in bas])
            null[f"{rep}|{scheme}"] = {
                "representation": rep, "scheme": scheme,
                "n_replicates": len(bas),
                "balanced_accuracy": {
                    "mean": float(arr.mean()), "sd": float(arr.std(ddof=1)),
                    "min": float(arr.min()), "max": float(arr.max()),
                    "p2_5": float(np.percentile(arr, 2.5)),
                    "p97_5": float(np.percentile(arr, 97.5)),
                    "replicates": [float(v) for v in arr]},
                "accuracy": {
                    "mean": float(np.mean([b["accuracy"] for b in bas]))},
                "real_balanced_accuracy": results[rep]["LDA"]["balanced_accuracy"],
                "real_minus_null_mean": float(
                    results[rep]["LDA"]["balanced_accuracy"] - arr.mean()),
                "real_above_null_p97_5": bool(
                    results[rep]["LDA"]["balanced_accuracy"]
                    > np.percentile(arr, 97.5)),
            }
            log(f"    {rep:<20} {scheme:<22} null BA "
                f"{arr.mean():.4f} +/- {arr.std(ddof=1):.4f}  "
                f"real {results[rep]['LDA']['balanced_accuracy']:.4f}  "
                f"above p97.5="
                f"{null[f'{rep}|{scheme}']['real_above_null_p97_5']}")

    # ------------------------------------------------- temporal shuffle control
    log("")
    log("  [control] TEMPORAL SHUFFLE: reverse local temporal order")
    shuffle = {}
    # R2: negate velocity.  R3: reverse the window before summarising.
    X2 = z["R2_POSE_VELOCITY"].copy()
    X2[:, 10:] *= -1.0
    r2 = run_cv(X2, z["R2_POSE_VELOCITY_ok"], y, subj, interior, ["LDA"], fold_of,
                verbose=False)
    shuffle["R2_POSE_VELOCITY_VELOCITY_NEGATED"] = {
        "scheme": "negate every velocity channel; pose untouched",
        "metrics": r2["LDA"]["metrics"],
        "real_balanced_accuracy": results["R2_POSE_VELOCITY"]["LDA"][
            "balanced_accuracy"],
        "real_minus_shuffled": float(
            results["R2_POSE_VELOCITY"]["LDA"]["balanced_accuracy"]
            - r2["LDA"]["metrics"]["balanced_accuracy"]),
    }
    log(f"    R2 velocity negated    BA="
        f"{r2['LDA']['metrics']['balanced_accuracy']:.4f} vs real "
        f"{results['R2_POSE_VELOCITY']['LDA']['balanced_accuracy']:.4f}")

    d = C.load_kinmus()
    h = C.load_json(os.path.join(C.LANE, P.PLAN_ARTIFACT))[
        "representations"]["R3_TRAJECTORY"]["primary_window_frames"]
    s10 = list(P.SHARED10["released_column_indices"])
    rev = np.full_like(z["R3_TRAJECTORY"], np.nan)
    ok_rev = np.zeros(y.size, dtype=bool)
    row = 0
    for t in d["trials"]:
        n = t["n_frames"]
        K = t["K"][:, s10]
        V = np.zeros_like(K)
        Kr = K[::-1]                     # reversed temporal order
        if n > 2:
            num = Kr[2:] - Kr[:-2]
            den = (t["time"][::-1][2:] - t["time"][::-1][:-2])[:, None]
            V[1:-1] = num / np.where(den == 0, np.nan, den)
        if n > 1:
            V[0] = Kr[1] - Kr[0]
            V[-1] = Kr[-1] - Kr[-2]
        V[~np.isfinite(V)] = 0.0
        cs = np.vstack([np.zeros(K.shape[1]), np.cumsum(Kr, axis=0)])
        for i in range(h, n - h):
            lo, hi = i - h, i + h
            seg = Kr[lo:hi + 1]
            span = t["time"][::-1][hi] - t["time"][::-1][lo]
            mean_v = ((cs[hi + 1] - cs[lo]) / span if span > 0
                      else np.zeros(K.shape[1]))
            rev[row + i] = np.concatenate([Kr[i], mean_v, Kr[hi] - Kr[lo],
                                           seg.std(axis=0)])
            ok_rev[row + i] = True
        row += n
    r3 = run_cv(rev, ok_rev, y, subj, interior, ["LDA"], fold_of, verbose=False)
    shuffle["R3_TRAJECTORY_WINDOW_REVERSED"] = {
        "scheme": ("reverse the frame order inside each window before computing "
                   "the summary; the feature set and its marginal distribution are "
                   "unchanged, only local temporal direction is destroyed"),
        "metrics": r3["LDA"]["metrics"],
        "real_balanced_accuracy": results["R3_TRAJECTORY"]["LDA"][
            "balanced_accuracy"],
        "real_minus_shuffled": float(
            results["R3_TRAJECTORY"]["LDA"]["balanced_accuracy"]
            - r3["LDA"]["metrics"]["balanced_accuracy"]),
    }
    log(f"    R3 window reversed     BA="
        f"{r3['LDA']['metrics']['balanced_accuracy']:.4f} vs real "
        f"{results['R3_TRAJECTORY']['LDA']['balanced_accuracy']:.4f}")

    # --------------------------------------------------- R3 window sensitivity
    log("")
    log("  [sensitivity] R3 at 200 ms and 1000 ms (reported only; the headline "
        "window may NOT be re-selected)")
    sens = {}
    for ms, hh in ((200, 10), (1000, 100)):
        Xw = np.full((y.size, 40), np.nan)
        okw = np.zeros(y.size, dtype=bool)
        row = 0
        for t in d["trials"]:
            n = t["n_frames"]
            w, o = window_from_trial(t, s10, hh)
            Xw[row:row + n] = w
            okw[row:row + n] = o
            row += n
        rr = run_cv(Xw, okw, y, subj, interior, ["LDA"], fold_of, verbose=False)
        sens[f"{ms}ms"] = {"window_frames": hh,
                           "n_valid_rows": int(okw.sum()),
                           "balanced_accuracy": rr["LDA"]["metrics"][
                               "balanced_accuracy"],
                           "accuracy": rr["LDA"]["metrics"]["accuracy"]}
        log(f"    {ms:>4d} ms ({hh:>3d} frames): BA="
            f"{sens[f'{ms}ms']['balanced_accuracy']:.4f} "
            f"({int(okw.sum())} rows)")

    np.savez_compressed(PRED, **{k: v for k, v in preds.items()})
    np.savez_compressed(os.path.join(C.RESULTS, "shuffle_preds.npz"),
                        R2_neg=r2["LDA"]["yhat"], R3_rev=r3["LDA"]["yhat"])

    log("")
    log("  PRIMARY TABLE (LDA, interior frames, subject-held-out)")
    log(f"    {'representation':<24} {'BA':>7} {'acc':>7} {'F1':>7}  "
        f"{'reachRec':>8} {'manipRec':>8} {'relRec':>8}")
    for rep in ("R1_POSE", "R2_POSE_VELOCITY", "R3_TRAJECTORY",
                "R4_POSE_PAST_ONLY", "R5_FULL18", "R6_FULL18_VELOCITY"):
        m = results[rep]["LDA"]
        pr = m["confusion"]["per_class_recall"]
        log(f"    {rep:<24} {m['balanced_accuracy']:>7.4f} {m['accuracy']:>7.4f} "
            f"{m['macro_f1']:>7.4f}  "
            f"{pr['REACHING']['value']:>8.4f} {pr['MANIPULATION']['value']:>8.4f} "
            f"{pr['RELEASING']['value']:>8.4f}")

    # ------------------------------------------------------------- artifacts
    common = {
        "branch_id": P.BRANCH_ID, "plan_sha256": plan_sha,
        "protocol": P.VALIDATION,
        "evaluation_stratum": "INTERIOR",
        "boundary_margin_frames": P.BOUNDARY["margin_frames"],
        "model_configurations": P.MODELS,
        "no_hyperparameter_search": P.MODELS["no_hyperparameter_search"],
        "notes": [
            "balanced accuracy is the primary metric",
            "all numbers are subject-held-out",
            "normalisation statistics come from the training folds only",
        ],
    }
    sf = dict(common)
    sf.update({
        "artifact": "KINMUS_SINGLE_FRAME_RESULTS.json",
        "representation": "R1_POSE",
        "features": P.SHARED10["api_order"],
        "n_features": 10,
        "baselines": base,
        "by_model": {k: results["R1_POSE"][k] for k in
                     ("LDA", "LR", "LSVM", "RSVM")},
        "primary": results["R1_POSE"]["LDA"],
    })
    sha1 = C.write_json(os.path.join(C.LANE, "KINMUS_SINGLE_FRAME_RESULTS.json"), sf)

    vf = dict(common)
    vf.update({
        "artifact": "KINMUS_VELOCITY_RESULTS.json",
        "representation": "R2_POSE_VELOCITY",
        "features": P.SHARED10["api_order"] + ["velocity of each of the ten"],
        "n_features": 20,
        "velocity_rule": P.REPRESENTATIONS["R2_POSE_VELOCITY"]["velocity_rule"],
        "by_model": {k: results["R2_POSE_VELOCITY"][k] for k in
                     ("LDA", "LR", "LSVM", "RSVM")},
        "primary": results["R2_POSE_VELOCITY"]["LDA"],
        "vs_R1": {
            "delta_balanced_accuracy": float(
                results["R2_POSE_VELOCITY"]["LDA"]["balanced_accuracy"]
                - results["R1_POSE"]["LDA"]["balanced_accuracy"]),
        },
        "temporal_shuffle_control": shuffle["R2_POSE_VELOCITY_VELOCITY_NEGATED"],
    })
    sha2 = C.write_json(os.path.join(C.LANE, "KINMUS_VELOCITY_RESULTS.json"), vf)

    tf = dict(common)
    tf.update({
        "artifact": "KINMUS_TRAJECTORY_RESULTS.json",
        "representation": "R3_TRAJECTORY",
        "primary_window_ms": P.REPRESENTATIONS["R3_TRAJECTORY"][
            "primary_window_ms"],
        "primary_window_frames": P.REPRESENTATIONS["R3_TRAJECTORY"][
            "primary_window_frames"],
        "feature_definition": P.REPRESENTATIONS["R3_TRAJECTORY"]["definition"],
        "n_features": 40,
        "by_model": {k: results["R3_TRAJECTORY"][k] for k in
                     ("LDA", "LR", "LSVM", "RSVM")},
        "primary": results["R3_TRAJECTORY"]["LDA"],
        "vs_R1": {
            "delta_balanced_accuracy": float(
                results["R3_TRAJECTORY"]["LDA"]["balanced_accuracy"]
                - results["R1_POSE"]["LDA"]["balanced_accuracy"]),
        },
        "temporal_shuffle_control": shuffle["R3_TRAJECTORY_WINDOW_REVERSED"],
        "window_sensitivity": sens,
        "sensitivity_role": P.REPRESENTATIONS["R3_TRAJECTORY"]["sensitivity_role"],
    })
    sha3 = C.write_json(os.path.join(C.LANE, "KINMUS_TRAJECTORY_RESULTS.json"), tf)

    cf = dict(common)
    cf.update({
        "artifact": "KINMUS_OBSERVABILITY_NULL_CONTROL.json",
        "why_mandatory": P.NULL_CONTROL["why_not_frame_permutation"],
        "schemes": P.NULL_CONTROL["schemes"],
        "replicates": P.NULL_CONTROL["replicates"],
        "seed": SEED,
        "nulls": null,
        "shuffle_control": shuffle,
        "summary": {
            f"{k}": {
                "real_ba": v["real_balanced_accuracy"],
                "null_mean_ba": v["balanced_accuracy"]["mean"],
                "real_minus_null": v["real_minus_null_mean"],
                "real_above_null_p97_5": v["real_above_null_p97_5"],
            } for k, v in null.items()
        },
    })
    sha4 = C.write_json(os.path.join(C.LANE,
                                     "KINMUS_OBSERVABILITY_NULL_CONTROL.json"), cf)

    # causal R4 result goes in its own small record, referenced from the decision
    causal = dict(common)
    causal.update({
        "artifact": "KINMUS_VELOCITY_RESULTS.json::R4",
        "representation": "R4_POSE_PAST_ONLY",
        "role": "SECONDARY (causal)",
        "n_features": 30,
        "primary": results["R4_POSE_PAST_ONLY"]["LDA"],
        "vs_R1": {"delta_balanced_accuracy": float(
            results["R4_POSE_PAST_ONLY"]["LDA"]["balanced_accuracy"]
            - results["R1_POSE"]["LDA"]["balanced_accuracy"])},
        "vs_R3": {"delta_balanced_accuracy": float(
            results["R4_POSE_PAST_ONLY"]["LDA"]["balanced_accuracy"]
            - results["R3_TRAJECTORY"]["LDA"]["balanced_accuracy"])},
        "why": P.REPRESENTATIONS["R4_POSE_PAST_ONLY"]["why"],
    })
    vf["R4_causal"] = causal
    C.write_json(os.path.join(C.LANE, "KINMUS_VELOCITY_RESULTS.json"), vf)

    # full18 + full18 velocity, secondary
    f18 = dict(common)
    f18.update({
        "artifact": "KINMUS_FULL18_DIAGNOSTIC.json",
        "role": "SECONDARY DIAGNOSTIC ONLY - may never redefine shared10",
        "policy": P.FULL18_POLICY,
        "question": P.REPRESENTATIONS["R5_FULL18"]["question"],
        "R5_FULL18": {"n_features": 18, "primary": results["R5_FULL18"]["LDA"]},
        "R6_FULL18_VELOCITY": {"n_features": 36,
                               "primary": results["R6_FULL18_VELOCITY"]["LDA"]},
        "vs_shared10": {
            "R5_minus_R1_balanced_accuracy": float(
                results["R5_FULL18"]["LDA"]["balanced_accuracy"]
                - results["R1_POSE"]["LDA"]["balanced_accuracy"]),
            "R6_minus_R2_balanced_accuracy": float(
                results["R6_FULL18_VELOCITY"]["LDA"]["balanced_accuracy"]
                - results["R2_POSE_VELOCITY"]["LDA"]["balanced_accuracy"]),
        },
        "extra_columns_available_to_full18_only": [
            n for n in C.UJI18 if n not in P.SHARED10["released_columns"]],
    })
    sha6 = C.write_json(os.path.join(C.LANE, "KINMUS_FULL18_DIAGNOSTIC.json"), f18)

    log("")
    log(f"  wrote KINMUS_SINGLE_FRAME_RESULTS.json      sha256={sha1[:16]}")
    log(f"  wrote KINMUS_VELOCITY_RESULTS.json          sha256={sha2[:16]}")
    log(f"  wrote KINMUS_TRAJECTORY_RESULTS.json        sha256={sha3[:16]}")
    log(f"  wrote KINMUS_OBSERVABILITY_NULL_CONTROL.json sha256={sha4[:16]}")
    log(f"  wrote KINMUS_FULL18_DIAGNOSTIC.json         sha256={sha6[:16]}")
    log(f"  elapsed {time.time() - t0:.1f} s")
    fh.close()
    return 0


def window_from_trial(t, cols, h):
    """Window summary at an arbitrary h (used only for the frozen sensitivity)."""
    K = t["K"][:, cols]
    tt = t["time"]
    n = K.shape[0]
    p = len(cols)
    out = np.full((n, 4 * p), np.nan)
    ok = np.zeros(n, dtype=bool)
    if n <= 2 * h:
        return out, ok
    cs = np.vstack([np.zeros(p), np.cumsum(K, axis=0)])
    for i in range(h, n - h):
        lo, hi = i - h, i + h
        seg = K[lo:hi + 1]
        span = tt[hi] - tt[lo]
        mean_v = (cs[hi + 1] - cs[lo]) / span if span > 0 else np.zeros(p)
        out[i] = np.concatenate([K[i], mean_v, K[hi] - K[lo],
                                 seg.std(axis=0, ddof=0)])
        ok[i] = True
    return out, ok


if __name__ == "__main__":
    raise SystemExit(main())
