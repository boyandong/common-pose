"""
bridge_audit/domain_depth.py -- supplementary readings of the PHASE-5 domain audit.

These are ADDITIONAL views of the same frozen geometry and the same paired arrays
produced by ``run_bridge_audit.py``. Nothing here refits the decoder, retunes the
threshold, or re-runs the model; it only asks sharper questions of existing
numbers:

  1. Where do emg2pose poses sit *relative to the DB9 held-out distance
     distribution* (percentile positions, not just a single 95th-percentile flag)?
  2. What do the ORACLE-POSE decoder labels look like -- is there any class the
     decoder emits at all on emg2pose poses, or is the output degenerate?
  3. Does the predicted pose look *more* like DB9 than the GT pose does, or less?
  4. Is the error direction inside the discriminative subspace actually
     class-relevant?  The subspace contains 5 directions; not all of them separate
     the six classes usefully.  A per-pair reading is more informative.
  5. Is a boundary crossing explained by the error's projection onto the relevant
     pairwise decision boundary normal?

Run:
    <EMG2POSE_VENV>\\Scripts\\python.exe domain_depth.py --results <results dir>
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import decoder as D  # noqa: E402
from _common import CANON16, describe  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    results_path = os.path.join(args.results, "bridge_audit_results.json")
    r = json.load(open(results_path, encoding="utf-8"))
    sess_dir = r["artifacts"]["sessions_dir"]

    dec = D.reconstruct(verbose=False)
    geom = dec.geometry
    classes = [int(c) for c in dec.classes]

    # ---- reassemble the paired arrays exactly as the driver stored them ----
    G, P, S = [], [], []
    for s in r["phase2_3_corpus"]["sessions"]:
        z = np.load(os.path.join(sess_dir, f"{s['session']}.paired50hz.npz"))
        k = z["gt_valid"]
        G.append(z["gt16"][k].astype(np.float64))
        P.append(z["pred16"][k].astype(np.float64))
        S.append(np.full(int(k.sum()), s["session"], dtype=object))
    G, P, S = np.concatenate(G), np.concatenate(P), np.concatenate(S)
    n = G.shape[0]

    # ---- DB9 held-out reference distribution of the SAME statistic ---------
    train = D.load_training_representation()
    cls_list = classes
    te_mask = np.isin(train["subject"], dec.test_subjects) & np.isin(
        train["movement"], cls_list)
    tr_mask = np.isin(train["subject"], dec.train_subjects) & np.isin(
        train["movement"], cls_list)
    Zte = dec.z(train["X16"][te_mask])
    d_te = geom.min_mahalanobis(Zte, geom.centroids, geom.precision)
    d_tr = geom.reference_distance
    thr = geom.thresholds["p95"]

    d_g = geom.min_mahalanobis(dec.z(G), geom.centroids, geom.precision)
    d_p = geom.min_mahalanobis(dec.z(P), geom.centroids, geom.precision)

    def pct_in(values, ref):
        ref = np.sort(ref)
        return np.searchsorted(ref, values, side="left") / ref.size

    out: dict = {
        "phase": "5 (supplementary) -- domain-depth readings",
        "policy": (
            "the p95 threshold and the class geometry are the frozen DB9-only ones; "
            "no threshold was recomputed on emg2pose data in this block"
        ),
        "db9_held_out_reference": {
            "n": int(te_mask.sum()),
            "distance": describe(d_te, prefix=""),
            "fraction_beyond_train_p95": float((d_te > thr).mean()),
            "role": (
                "the honest false-alarm rate of the threshold on DB9 data the decoder "
                "never saw. It is ~13%, not 5%. CORRECTED 2026-09-18 after the "
                "independent S5 audit: the PRIMARY cause is source-database / cohort "
                "distribution shift, not a family-wise property of the statistic. The "
                "43 held-out subjects are DB2 (40) + DB5 (3) while the 34 "
                "development-exposed subjects are DB1 (27) + DB5 (7) -- not one DB2 "
                "subject is in the training cohort, so this number measures "
                "between-database domain shift as much as subject sampling. Audit "
                "diagnostics: within-subject split-half held-out exceedance 4.74% "
                "against a nominal 5% (the support statistic itself is approximately "
                "unbiased), per-subject median distance 4.04 (held-out) vs 3.68 "
                "(train), subject-level permutation p = 0.0158, subject-bootstrap "
                "95% CI for the 13.2% = [8.5%, 18.6%]. The family-wise effect is real "
                "but SECONDARY: a single 16-dof chi-square at this threshold would "
                "give 1.59%, so the min-over-six structure does widen the tail. This "
                "is a descriptive calibration number, NOT a new confirmatory claim."
            ),
        },
        "emg2pose_gt": {
            "distance": describe(d_g, prefix=""),
            "fraction_beyond_db9_train_p95": float((d_g > thr).mean()),
            "fraction_beyond_db9_heldout_p95": float((d_g > np.percentile(d_te, 95)).mean()),
            "median_percentile_in_db9_heldout_distribution": float(
                np.median(pct_in(d_g, d_te))),
            "fraction_inside_db9_heldout_median_distance": float(
                (d_g <= np.median(d_te)).mean()),
            "closest_1pct_of_frames_within_db9_train_p95": float(
                (np.percentile(d_g, 1) <= thr)),
        },
        "emg2pose_predicted": {
            "distance": describe(d_p, prefix=""),
            "fraction_beyond_db9_train_p95": float((d_p > thr).mean()),
            "median_percentile_in_db9_heldout_distribution": float(
                np.median(pct_in(d_p, d_te))),
        },
        "does_the_prediction_look_more_like_db9_than_the_gt": {
            "median_distance_gt": float(np.median(d_g)),
            "median_distance_pred": float(np.median(d_p)),
            "median_change": float(np.median(d_p) - np.median(d_g)),
            "fraction_pred_farther": float((d_p > d_g).mean()),
            "mean_change": float(d_p.mean() - d_g.mean()),
            "note": (
                "VEMG2Pose is fitted to reproduce the joint-angle trajectory, not to "
                "stay inside the DB9 class regions, so a systematic outward drift is "
                "not a defect of the audit."
            ),
        },
    }

    # ---- oracle-pose decoder output: is it degenerate? ---------------------
    probs_g = dec.predict_proba(G)
    probs_p = dec.predict_proba(P)
    top_g = np.asarray(dec.classes)[probs_g.argmax(1)]
    top_p = np.asarray(dec.classes)[probs_p.argmax(1)]
    out["oracle_pose_label_distribution"] = {
        "note": (
            "These are ORACLE-POSE REFERENCE labels, NOT gesture ground truth. They "
            "show whether the frozen decoder emits a meaningful spread of postures on "
            "emg2pose kinematics, or collapses."
        ),
        "gt_pose_counts": {str(c): int((top_g == c).sum()) for c in classes},
        "gt_pose_fractions": {str(c): float((top_g == c).mean()) for c in classes},
        "predicted_pose_counts": {str(c): int((top_p == c).sum()) for c in classes},
        "predicted_pose_fractions": {str(c): float((top_p == c).mean()) for c in classes},
        "balanced_chance": 1.0 / len(classes),
        "gt_top1_probability": describe(probs_g.max(axis=1), prefix=""),
        "pred_top1_probability": describe(probs_p.max(axis=1), prefix=""),
        "gt_strictly_more_confident_than_pred_fraction": float(
            (probs_g.max(axis=1) > probs_p.max(axis=1)).mean()),
    }

    # ---- per-pair boundary-normal reading ----------------------------------
    # Two readings, because they answer different questions:
    #
    #  (a) PAIR-SET FLIPS.  57-66% of frames change WHICH two classes the frozen
    #      decoder is comparing, because the top-2 order is nearly degenerate for
    #      a 6-class LDA on poses this far out of domain. This inflates any
    #      "boundary pair changed" counter and must not be read as a decision
    #      change on its own.
    #
    #  (b) A WITNESS BOUNDARY.  For frames where both sides agree on the top-2
    #      set, there is a single well-defined boundary and we can ask the
    #      arithmetic question directly: does the error's projection onto the
    #      boundary normal exceed the margin the frozen decoder had?
    normals = np.asarray(dec.lda.coef_, dtype=np.float64)
    Vg = dec.decision(G)
    Vp = dec.decision(P)
    ord_g = np.argsort(-Vg, axis=1)
    ord_p = np.argsort(-Vp, axis=1)
    same_pair = (ord_g[:, :2] == ord_p[:, :2]).all(axis=1)
    dz = dec.z(P) - dec.z(G)

    margin = np.zeros(n)
    proj = np.zeros(n)
    for row in np.unique(np.stack([ord_g[:, 0], ord_g[:, 1]], axis=1), axis=0):
        a, b = int(row[0]), int(row[1])
        m = (ord_g[:, 0] == a) & (ord_g[:, 1] == b)
        nrm = normals[a] - normals[b]
        margin[m] = Vg[m, a] - Vg[m, b]
        proj[m] = dz[m] @ nrm

    comparable = same_pair
    edges = [-np.inf, 0.0, 0.5, 1.0, 2.0, np.inf]
    ratio = np.where(comparable, proj / np.maximum(margin, 1e-12), np.nan)
    label_g = np.asarray(dec.classes)[ord_g[:, 0]]
    label_p = np.asarray(dec.classes)[ord_p[:, 0]]
    agree = label_g == label_p

    # ------------------------------------------------------------------
    # EXACT reading of the frozen decoder's own top-1/top-2 boundary.
    #
    # The LDA score is  v_c(z) = z . coef_c + intercept_c.  For the GT-pose top-2
    # pair A (top-1) and B (top-2) the intercept cancels in the difference, so
    # with dz = z_pred - z_gt:
    #
    #   margin  mg  = Vg[:,A] - Vg[:,B]  =  z_gt . (coef_A - coef_B)  +  (I_A - I_B)
    #   shift   sh  = (Vp - Vg)[:,A] - (Vp - Vg)[:,B]  =  dz . (coef_A - coef_B)
    #
    # and therefore, exactly,
    #
    #   mg + sh  =  Vp[:,A] - Vp[:,B]        (the predicted score difference)
    #
    # so the predicted label overtakes B precisely when
    #
    #   mg + sh < 0   <=>   sh < -mg   <=>   Vp[:,B] > Vp[:,A].
    #
    # A tempting but WRONG "identity" is mg == -(dz . nrm): that would say the
    # predicted score difference is zero for every frame, which is false. It was
    # written here twice and caught twice by the check below -- which is exactly
    # why the check is kept rather than reasoned away.
    A = ord_g[:, 0]
    B = ord_g[:, 1]
    rows = np.arange(n)
    mg = Vg[rows, A] - Vg[rows, B]
    shift = np.einsum("ij,ij->i", dz, normals[A] - normals[B])
    vp_diff = Vp[rows, A] - Vp[rows, B]
    crossing = Vp[rows, B] > Vp[rows, A]
    identity_residual = np.abs((mg + shift) - vp_diff)
    predicate_agreement = float((crossing == ((mg + shift) < 0)).mean())

    consistency = {
        "n_frames_checked": int(n),
        "max_abs_identity_residual": float(identity_residual.max()),
        "identity_holds": bool(identity_residual.max() < 1e-9),
        "identity": ("Vg[:,A] - Vg[:,B] + (z_pred - z_gt).(coef_A - coef_B) "
                     "== Vp[:,A] - Vp[:,B]"),
        "exact_crossing_predicate": "Vp[:,B] > Vp[:,A]  <=>  mg + shift < 0",
        "exact_crossing_predicate_agreement": predicate_agreement,
        "identity_predicate_both_verified": bool(
            identity_residual.max() < 1e-9 and predicate_agreement == 1.0),
        "rejected_false_identity": (
            "mg == -(dz . (coef_A - coef_B)) is FALSE (it would force every predicted "
            "score difference to zero). Two earlier drafts of this block asserted it "
            "and both were caught by this same numeric check."
        ),
        "phase8_uses_the_same_algebra": (
            "run_bridge_audit.py attributes Delta margin = (z_pred - z_gt) . "
            "(coef_a - coef_b), exact by the same intercept cancellation"
        ),
    }

    bands = {}
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = comparable & (ratio > lo) & (ratio <= hi)
        if m.sum() == 0:
            continue
        bands[f"proj_over_margin in ({lo:g}, {hi:g}]"] = {
            "n": int(m.sum()),
            "top1_agreement": float(agree[m].mean()),
            "mean_abs_prob_diff": float(
                np.abs(dec.predict_proba(G[m]) - dec.predict_proba(P[m])).mean()),
        }

    out["pairwise_boundary_reading"] = {
        "definition": (
            "(a) pair-set flip = the set/order of the frozen decoder's top-2 classes "
            "differs between the GT-pose and predicted-pose decisions. "
            "(b) for frames where both sides agree on the top-2 pair, margin = "
            "decision(top1) - decision(top2) at the GT pose and projection = "
            "(z_pred - z_gt) . (coef_top1 - coef_top2); the predicted label can change "
            "exactly when projection > margin."
        ),
        "pair_set_flip_rate": float((~same_pair).mean()),
        "pair_set_flip_rate_is_not_a_decision_change": (
            "the top-2 order is nearly degenerate far out of domain, so this counter "
            "runs high even where the top-1 label is identical; it is reported for "
            "transparency, not as a stability metric"
        ),
        "linear_attribution_consistency_check": consistency,
        "crossed_boundary_on_disagreements": {
            "definition": (
                "The frozen decoder's own top-1/top-2 boundary, evaluated exactly. "
                "mg = Vg[:,A] - Vg[:,B] with A, B the GT-pose top-2 classes is the "
                "margin the decoder had; shift = (z_pred - z_gt) . (coef_A - coef_B) is "
                "the signed change of that same score difference caused by the pose "
                "error. The predicted label overtakes B exactly when -shift > mg."
            ),
            "identity_residual_max": consistency["max_abs_identity_residual"],
            "identity_holds": consistency["identity_holds"],
            "predicate_agreement": consistency["exact_crossing_predicate_agreement"],
            "crossing_rate_all_frames": float(crossing.mean()),
            "top1_disagreement_rate_all_frames": float((~agree).mean()),
            "crossing_given_disagreement": float(crossing[~agree].mean()),
            "disagreement_given_no_crossing": float((~agree)[~crossing].mean()),
            "median_margin_mg_all": float(np.median(mg)),
            "median_shift_all": float(np.median(shift)),
            "median_abs_shift_all": float(np.median(np.abs(shift))),
            "median_abs_shift_over_margin_all": float(
                np.median(np.abs(shift) / np.maximum(mg, 1e-9))),
            "median_margin_mg_on_disagreements": float(np.median(mg[~agree])),
            "median_margin_mg_on_agreements": float(np.median(mg[agree])),
            "median_abs_shift_on_disagreements": float(np.median(np.abs(shift[~agree]))),
            "median_abs_shift_on_agreements": float(np.median(np.abs(shift[agree]))),
            "median_predicted_score_difference_on_disagreements": float(
                np.median((mg + shift)[~agree])),
            "interpretation": (
                "the predicted label overtakes the runner-up in ~18% of frames while the "
                "top-1 label differs in ~24%. The gap is the remaining disagreement mode: "
                "frames where a THIRD class, not the runner-up, takes the top slot -- "
                "which is what a near-degenerate 6-class posterior far outside the "
                "training support looks like. Margins on disagreeing frames are 3.74x "
                "smaller than on agreeing frames (17.18 / 4.60), i.e. the decoder's "
                "margin and the pose error are of comparable size on the frames where "
                "the label moves. NOTE (corrected after the independent S5 audit): this "
                "is a marginal association, not a dose-response. Conditionally on GT "
                "distance or GT margin the effect of prediction drift changes sign, and "
                "a direction-shuffled error null reproduces the agreement to within 1.4 "
                "percentage points (0.7507 vs 0.7646), so error MAGNITUDE against a "
                "narrow margin -- not a harmful error DIRECTION -- is what the evidence "
                "supports."
            ),
        },
        "comparable_frames": int(comparable.sum()),
        "comparable_fraction": float(comparable.mean()),
        "signed_projection_on_boundary_normal": describe(proj[comparable], prefix=""),
        "margin_at_gt_pose": describe(margin[comparable], prefix=""),
        "projection_exceeds_margin_fraction": float(
            (proj[comparable] > margin[comparable]).mean()),
        "projection_exceeds_half_margin_fraction": float(
            (proj[comparable] > 0.5 * margin[comparable]).mean()),
        "top1_agreement_by_projection_over_margin": bands,
        "top1_agreement_comparable_frames": float(agree[comparable].mean()),
        "interpretation": (
            "the disagreement should climb monotonically with the error-to-margin "
            "ratio. If it does, the instability is arithmetic -- VEMG2Pose error is "
            "large compared with the margin the frozen decoder had -- rather than a "
            "change in the decision geometry."
        ),
    }

    # ---- session-level domain depth ---------------------------------------
    rows = []
    for s in r["phase2_3_corpus"]["sessions"]:
        m = S == s["session"]
        if m.sum() == 0:
            continue
        rows.append({
            "session": s["session"], "stage": s["stage"], "side": s["side"],
            "n": int(m.sum()),
            "gt_median_db9_dist": float(np.median(d_g[m])),
            "pred_median_db9_dist": float(np.median(d_p[m])),
            "gt_fraction_beyond_p95": float((d_g[m] > thr).mean()),
            "pred_fraction_beyond_p95": float((d_p[m] > thr).mean()),
            "gt_median_percentile_in_db9_heldout": float(np.median(pct_in(d_g[m], d_te))),
        })
    out["per_session_domain_depth"] = {
        "table": rows,
        "gt_fraction_beyond_p95": describe(
            np.array([x["gt_fraction_beyond_p95"] for x in rows]), prefix="sess_"),
        "sessions_with_zero_gt_frames_inside_db9_p95": int(
            sum(1 for x in rows if x["gt_fraction_beyond_p95"] >= 0.999999)),
        "sessions_with_over_90pct_gt_frames_outside": int(
            sum(1 for x in rows if x["gt_fraction_beyond_p95"] > 0.90)),
    }

    out_path = args.out or os.path.join(args.results, "domain_depth_supplement.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=lambda o: float(o) if isinstance(o, np.floating)
                  else int(o) if isinstance(o, np.integer) else str(o))
    print(json.dumps(out, indent=2, default=lambda o: float(o) if isinstance(o, np.floating)
                     else int(o) if isinstance(o, np.integer) else str(o))[:6000])
    print(f"\n[written] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
