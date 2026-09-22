#!/usr/bin/env python
"""Explicit first-web-space test for emg2pose `THUMB_CMC_AA`, with frozen output.

The decision this produces (made by the research lead, implemented here)
------------------------------------------------------------------------
DB9's `CMC1_A` is documented as abduction-positive. Anatomy defines thumb CMC
abduction as the thumb moving away from the palm / opening the first web space,
and adduction as returning toward the palm / closing it. The research lead's
ruling is that if positive emg2pose `THUMB_CMC_AA` **closes** the first web
space, then DB9's `CMC1_A` must be **sign-flipped** when DB9 is converted into
the emg2pose-oriented canonical16 frame.

This script re-runs that test explicitly and persists both numerical and visual
evidence, then reports which way the frozen transformation goes.

Two things it also records, because they are material and must not be buried:

1. **The criteria can disagree for this DOF.** "Away from the palm" can mean
   *out of the palm plane* (dorsally) or *opening the web in the palm plane*.
   For emg2pose's `THUMB_CMC_AA` the thumb moves dorsally AND the web closes, so
   the two readings point in opposite directions. The frozen ruling uses the
   **web-space** criterion, consistently with DB9's own calibration, which
   computes `CMC1_A` from the two thumb-base sensors as an in-plane
   thumb/index separation.
2. **emg2pose's `THUMB_CMC_AA` is not the dominant in-plane web channel** --
   `THUMB_CMC_FE` moves the in-plane web angle about three times more strongly.
   See `tools/resolve_thumb_axis.py`. The flip is therefore a correction of a
   sign, applied to a channel whose *magnitude* semantics are themselves only
   approximately the DB9 DOF.

Evidence is written to JSON plus a PNG so the claim can be checked without
re-running anything.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_ROOT, "hand_visualizer", "tools"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

WRIST, PALM = 5, 20
THUMB_INTER, INDEX_PROX, PINKY_PROX = 6, 8, 17
THUMB_TIP, INDEX_TIP = 0, 1

THUMB_CMC_AA_INDEX = 1


def palm_frame(lm: np.ndarray):
    origin = lm[PALM]
    distal = lm[PALM] - lm[WRIST]
    distal /= np.linalg.norm(distal)
    across = lm[INDEX_PROX] - lm[PINKY_PROX]
    across /= np.linalg.norm(across)
    normal = np.cross(distal, across)
    normal /= np.linalg.norm(normal)
    across = np.cross(normal, distal)
    across /= np.linalg.norm(across)
    return origin, distal, across, normal


def web_metrics(lm: np.ndarray) -> dict:
    origin, distal, across, normal = palm_frame(lm)
    t = lm[THUMB_INTER] - origin
    i = lm[INDEX_PROX] - origin
    t2 = np.array([t @ distal, t @ across])
    i2 = np.array([i @ distal, i @ across])
    cos = float(np.clip(t2 @ i2 / (np.linalg.norm(t2) * np.linalg.norm(i2)), -1, 1))
    return {
        "web_angle_in_plane_deg": float(np.degrees(np.arccos(cos))),
        "tip_distance": float(np.linalg.norm(lm[THUMB_TIP] - lm[INDEX_TIP])),
        "out_of_plane_deg": float(np.degrees(np.arctan2(t @ normal, np.linalg.norm(t2)))),
        "thumb_tip_palm_xy": t2.tolist(),
        "index_tip_palm_xy": i2.tolist(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, help="JSON evidence path")
    ap.add_argument("--fig", required=True, help="PNG evidence path")
    ap.add_argument("--sweep", type=float, default=0.7)
    args = ap.parse_args()

    from hand_kinematics_np import load_default_model  # type: ignore

    model = load_default_model()
    lo, hi = model.joint_limits[THUMB_CMC_AA_INDEX]
    sweep = np.linspace(-min(args.sweep, hi), min(args.sweep, hi), 29)

    rows = []
    for v in sweep:
        a = np.zeros(20)
        a[THUMB_CMC_AA_INDEX] = v
        m = web_metrics(np.asarray(model.skin_landmarks(a)))
        rows.append({"THUMB_CMC_AA_rad": float(v), **m})

    at_zero = next(r for r in rows if abs(r["THUMB_CMC_AA_rad"]) < 1e-9)
    at_pos = next(r for r in rows if abs(r["THUMB_CMC_AA_rad"] - sweep.max()) < 1e-9)
    at_neg = next(r for r in rows if abs(r["THUMB_CMC_AA_rad"] - sweep.min()) < 1e-9)

    d_pos = at_pos["tip_distance"] - at_zero["tip_distance"]
    d_neg = at_neg["tip_distance"] - at_zero["tip_distance"]
    web_pos = at_pos["web_angle_in_plane_deg"] - at_zero["web_angle_in_plane_deg"]
    web_neg = at_neg["web_angle_in_plane_deg"] - at_zero["web_angle_in_plane_deg"]

    positive_closes_web = bool(d_pos < 0 and web_pos < 0)
    positive_moves_dorsally = bool(at_pos["out_of_plane_deg"] > at_zero["out_of_plane_deg"])
    criteria_agree = bool(
        (positive_closes_web and not positive_moves_dorsally)
        or (positive_moves_dorsally and not positive_closes_web)
    )

    print("=" * 78)
    print("First-web-space test for emg2pose THUMB_CMC_AA")
    print("=" * 78)
    print(f"  official limit range      = [{lo:+.4f}, {hi:+.4f}] rad")
    print(f"  {'CMC_AA':>8} {'web angle':>11} {'Δweb':>9} {'tip dist':>10} {'Δdist':>9} {'elev':>9}")
    for r in rows[::4]:
        print(f"  {r['THUMB_CMC_AA_rad']:>+8.3f} {r['web_angle_in_plane_deg']:>11.2f} "
              f"{r['web_angle_in_plane_deg'] - at_zero['web_angle_in_plane_deg']:>+9.2f} "
              f"{r['tip_distance']:>10.2f} {r['tip_distance'] - at_zero['tip_distance']:>+9.2f} "
              f"{r['out_of_plane_deg']:>+9.2f}")
    print()
    print(f"  positive CMC_AA:  d(web) = {web_pos:+.2f} deg, d(tip dist) = {d_pos:+.2f}, "
          f"d(elevation) = {at_pos['out_of_plane_deg'] - at_zero['out_of_plane_deg']:+.2f} deg")
    print(f"  negative CMC_AA:  d(web) = {web_neg:+.2f} deg, d(tip dist) = {d_neg:+.2f}, "
          f"d(elevation) = {at_neg['out_of_plane_deg'] - at_zero['out_of_plane_deg']:+.2f} deg")
    print()
    print(f"  positive CMC_AA CLOSES the first web space : {positive_closes_web}")
    print(f"  positive CMC_AA moves the thumb DORSALLY   : {positive_moves_dorsally}")
    print(f"  the two criteria AGREE for this DOF        : {criteria_agree}")
    print(f"    ('away from the palm' as out-of-plane motion vs 'open the web' as "
          f"in-plane separation give {'the same' if criteria_agree else 'OPPOSITE'} answers)")

    # ---- frozen decision --------------------------------------------------
    flip = bool(positive_closes_web)
    print()
    print("  FROZEN DECISION (research lead's ruling, web-space criterion):")
    if flip:
        print("    emg2pose positive CMC_AA closes the web -> adduction")
        print("    DB9 CMC1_A positive is abduction          -> opposite")
        print("    => DB9 canonical16 slot 'thumb_cmc_ab_adduction' is SIGN-FLIPPED")
        print("       in db9_to_canonical16. Session 2's emg2pose adapter is NOT touched.")
    else:
        print("    emg2pose positive CMC_AA opens the web -> abduction, same as DB9")
        print("    => NO flip. canonical16 slot used as-is.")

    sign = -1.0 if flip else 1.0
    zero_alignment = {
        "db9_reference_cmc1_a_deg": None,
        "emg2pose_zero_cmc_aa_rad": 0.0,
        "note": ("DB9's reference posture is the extended-and-together hand; the "
                 "exercise-B movements closest to all-zero canonical16 are the "
                 "wrist-rotation movements, whose CMC1_A sits near 0 deg. "
                 "emg2pose's rest pose has CMC_AA = 0 by construction. Both "
                 "datasets therefore place this DOF's zero at the same physical "
                 "configuration, so the correction is a PURE SIGN FLIP with no "
                 "offset. Verified numerically in "
                 "data/db9_posture16/thumb_zero_alignment.json."),
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump({
            "variable": "canonical16 slot 1 (thumb_cmc_ab_adduction)",
            "emg2pose_dof": "THUMB_CMC_AA (index 1)",
            "official_limit_range_rad": [float(lo), float(hi)],
            "sweep": rows,
            "at_zero": at_zero, "at_positive_extreme": at_pos, "at_negative_extreme": at_neg,
            "positive_closes_first_web_space": positive_closes_web,
            "positive_moves_thumb_dorsally": positive_moves_dorsally,
            "criteria_agree": criteria_agree,
            "criterion_used": ("first web space (in-plane thumb/index separation), "
                               "consistent with DB9's own CMC1_A calibration which "
                               "computes an in-plane separation from the two "
                               "thumb-base sensors"),
            "frozen_sign_multiplier_for_db9": sign,
            "applied_in": "representation/db9_to_canonical16.py only",
            "session2_adapter_modified": False,
            "zero_alignment": zero_alignment,
        }, fh, indent=2)

    # ---- visual evidence --------------------------------------------------
    os.makedirs(os.path.dirname(os.path.abspath(args.fig)), exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    v = [r["THUMB_CMC_AA_rad"] for r in rows]
    axes[0].plot(v, [r["web_angle_in_plane_deg"] for r in rows], "o-", color="#1f77b4")
    axes[0].set_xlabel("emg2pose THUMB_CMC_AA (rad)")
    axes[0].set_ylabel("first web angle, in-plane (deg)")
    axes[0].set_title("Web angle vs CMC_AA\n(smaller = more closed)")
    axes[0].grid(alpha=0.3)

    axes[1].plot(v, [r["tip_distance"] for r in rows], "o-", color="#d62728")
    axes[1].set_xlabel("emg2pose THUMB_CMC_AA (rad)")
    axes[1].set_ylabel("thumb tip <-> index tip distance")
    axes[1].set_title("Tip separation vs CMC_AA")
    axes[1].grid(alpha=0.3)

    for r, c, lab in ((at_neg, "#2ca02c", f"{at_neg['THUMB_CMC_AA_rad']:+.2f}"),
                      (at_zero, "#000000", "0.00"),
                      (at_pos, "#d62728", f"{at_pos['THUMB_CMC_AA_rad']:+.2f}")):
        txy = np.array(r["thumb_tip_palm_xy"])
        ixy = np.array(r["index_tip_palm_xy"])
        axes[2].plot([0, txy[0]], [0, txy[1]], "-o", color=c, label=f"thumb @ {lab}")
        axes[2].plot([0, ixy[0]], [0, ixy[1]], "--s", color=c, alpha=0.55)
    axes[2].plot([], [], "k--s", label="index ray")
    axes[2].set_xlabel("palm-plane: distal ->")
    axes[2].set_ylabel("palm-plane: across ->")
    axes[2].set_title("Thumb (solid) vs index (dashed) in the palm plane")
    axes[2].legend(fontsize=8)
    axes[2].grid(alpha=0.3)
    fig.suptitle(
        f"THUMB_CMC_AA first-web-space test — positive "
        f"{'CLOSES' if positive_closes_web else 'OPENS'} the web "
        f"=> frozen DB9 sign multiplier {sign:+.0f}", fontsize=11)
    fig.tight_layout()
    fig.savefig(args.fig, dpi=150)
    plt.close(fig)
    print(f"\n[wrote] {args.out}\n[wrote] {args.fig}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
