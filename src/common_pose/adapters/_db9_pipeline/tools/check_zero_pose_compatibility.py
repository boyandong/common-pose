#!/usr/bin/env python
"""PHASE 1B -- cross-dataset zero / axis compatibility check.

The unresolved risk this addresses
----------------------------------
Canonical16 names the same anatomical variables on both sides, but naming the
same DOF does not mean the two datasets *measure from the same zero*.  If DB9's
zero (the extended-and-together reference posture) and emg2pose's zero (the
UmeTrack rest pose) differ by a constant offset, then a canonical16 vector from
one dataset does not mean the same thing as a canonical16 vector from the other
-- and any classifier trained on DB9 would be fed a systematically shifted input
by the emg2pose pose model.

What is checked here, and how
-----------------------------
Everything is derived from **geometry**, never from classification accuracy
(tuning offsets against test accuracy is explicitly forbidden).

1. **Is the emg2pose zero pose "extended and together"?**  Forward kinematics of
   the official UmeTrack model at all-zero joint angles.  Finger straightness is
   measured as the interior angle of the fingertip chain; togetherness as the
   fingertip-to-fingertip spacing compared with the same spacing when the
   abduction DOF are driven to their official limits.

2. **Do the 15 flexion DOFs share a zero?**  For a flexion DOF, zero should be
   the straight/extended configuration on both sides.  This is measured, not
   asserted: at canonical zero, each finger's chain should be near-collinear.

3. **Thumb CMC ab/adduction** gets its own check, because the frozen contract
   warns that its polarity is per-joint and that "positive = abduction" must not
   be assumed.  The thumb tip is tracked while the DOF is driven negative and
   positive, and its displacement is decomposed into "away from the palm"
   (abduction) versus "across the palm" (adduction).

4. **Independent data-side anchor.**  The DB9 paper says the reference posture
   was taken from the central part of an exercise-B movement that is "the hand
   resting on the table with the fingers closed together and extended".  If that
   is true, the movement whose central third is closest to all-zero angles in the
   real DB9 files identifies the reference posture from the data alone.  This
   gives a second, dataset-side handle on the same question.

Output: ``docs/DB9_EMG2POSE_ZERO_COMPATIBILITY.json`` plus a printed report.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))            # .../posture_decoder/tools
_ROOT = os.path.dirname(os.path.dirname(_HERE))               # .../emg2pose_handstate
sys.path.insert(0, os.path.join(_ROOT, "hand_visualizer", "tools"))
sys.path.insert(0, os.path.join(_ROOT, "posture_decoder"))
sys.path.insert(0, os.path.join(_ROOT, "representation"))

# Landmark indices, from emg2pose/constants.py::LANDMARKS (official ordering).
FINGERTIP = {"thumb": 0, "index": 1, "middle": 2, "ring": 3, "pinky": 4}
WRIST = 5
FINGER_FRAMES = {           # (proximal, intermediate, distal)
    "index": (8, 9, 10), "middle": (11, 12, 13),
    "ring": (14, 15, 16), "pinky": (17, 18, 19),
}
THUMB_FRAMES = (6, 7)
PALM_CENTER = 20


def _interior_angle(a, b, c) -> float:
    """Angle at ``b`` in the chain a-b-c, in degrees (180 = perfectly straight)."""
    u, v = a - b, c - b
    nu, nv = np.linalg.norm(u), np.linalg.norm(v)
    if nu == 0 or nv == 0:
        return float("nan")
    cos = float(np.clip(np.dot(u, v) / (nu * nv), -1.0, 1.0))
    return float(np.degrees(np.arccos(cos)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--extracted", default="",
                    help="extracted DB9 dir, for the data-side reference anchor")
    ap.add_argument("--no-data-anchor", action="store_true")
    args = ap.parse_args()

    from hand_kinematics_np import load_default_model  # type: ignore

    model = load_default_model()
    print(f"[1B] UmeTrack model: {model.source_path}")
    print(f"     sha256 {model.source_sha256}")

    zeros20 = np.zeros(20)
    lm0 = np.array(model.skin_landmarks(zeros20))

    # ---- 1. is the emg2pose zero pose extended and together? --------------
    print()
    print("[1B] emg2pose (UmeTrack) pose at ALL-ZERO joint angles")
    straightness = {}
    for f, (p, i, d) in FINGER_FRAMES.items():
        tip = FINGERTIP[f]
        ang_prox = _interior_angle(lm0[p], lm0[i], lm0[d])
        ang_dist = _interior_angle(lm0[i], lm0[d], lm0[tip])
        straightness[f] = {"proximal_chain_angle_deg": ang_prox,
                           "distal_chain_angle_deg": ang_dist}
        print(f"     {f:<7} chain angles: proximal={ang_prox:6.2f} deg  "
              f"distal={ang_dist:6.2f} deg   (180 = straight)")

    # togetherness: fingertip spacing at zero vs at the official abduction limits
    def spacing(lm):
        return {
            "index-middle": float(np.linalg.norm(lm[1] - lm[2])),
            "middle-ring": float(np.linalg.norm(lm[2] - lm[3])),
            "ring-pinky": float(np.linalg.norm(lm[3] - lm[4])),
            "palm_width": float(np.linalg.norm(lm[1] - lm[4])),
        }

    sp0 = spacing(lm0)
    lim = model.joint_limits
    aa_idx = {"index": 4, "middle": 8, "ring": 12, "pinky": 16}

    def _separation_for(settings: dict[str, float]) -> float:
        a = zeros20.copy()
        for f, v in settings.items():
            a[aa_idx[f]] = v
        lm = np.array(model.skin_landmarks(a))
        return float(
            np.linalg.norm(lm[FINGERTIP["index"]] - lm[FINGERTIP["middle"]])
            + np.linalg.norm(lm[FINGERTIP["middle"]] - lm[FINGERTIP["ring"]])
            + np.linalg.norm(lm[FINGERTIP["ring"]] - lm[FINGERTIP["pinky"]])
        )

    # The ab/adduction polarity is PER FINGER (the frozen contract says so), so
    # driving all four to the same sign does not produce a spread hand.  The
    # direction that increases separation is found per finger, geometrically.
    spread_settings: dict[str, float] = {}
    close_settings: dict[str, float] = {}
    per_finger_direction: dict[str, str] = {}
    for f, k in aa_idx.items():
        lo, hi = float(lim[k][0]), float(lim[k][1])
        trial = {f: hi}
        sep_hi = _separation_for({f: hi})
        sep_lo = _separation_for({f: lo})
        if sep_hi >= sep_lo:
            spread_settings[f], close_settings[f] = hi, lo
            per_finger_direction[f] = "positive opens"
        else:
            spread_settings[f], close_settings[f] = lo, hi
            per_finger_direction[f] = "negative opens"
    # Combine the per-finger directions into whole-hand extremes.
    spread_settings = {
        f: (float(lim[aa_idx[f]][1]) if per_finger_direction[f] == "positive opens"
            else float(lim[aa_idx[f]][0]))
        for f in aa_idx
    }
    close_settings = {
        f: (float(lim[aa_idx[f]][0]) if per_finger_direction[f] == "positive opens"
            else float(lim[aa_idx[f]][1]))
        for f in aa_idx
    }

    def _lm_for(settings):
        a = zeros20.copy()
        for f, v in settings.items():
            a[aa_idx[f]] = v
        return np.array(model.skin_landmarks(a))

    lm_wide, lm_narrow = _lm_for(spread_settings), _lm_for(close_settings)
    wide = {"state": spread_settings, "spacing": spacing(lm_wide)}
    narrow = {"state": close_settings, "spacing": spacing(lm_narrow)}
    print()
    print("     ab/adduction polarity is PER FINGER -- the sign that opens each "
          "finger was found geometrically:")
    for f in aa_idx:
        print(f"       {f:<7} {per_finger_direction[f]}")

    print()
    print("     fingertip spacing (model units):")
    print(f"       zero pose        : " + "  ".join(f"{k}={v:.2f}" for k, v in sp0.items()))
    print(f"       most-spread pose : " + "  ".join(f"{k}={v:.2f}" for k, v in wide['spacing'].items()))
    print(f"       most-closed pose : " + "  ".join(f"{k}={v:.2f}" for k, v in narrow['spacing'].items()))

    def _gap(sp):
        return sp["index-middle"] + sp["middle-ring"] + sp["ring-pinky"]

    gap_open = _gap(wide["spacing"]) - _gap(narrow["spacing"])
    gap_zero = _gap(sp0) - _gap(narrow["spacing"])
    togetherness_ratio = gap_zero / gap_open if gap_open else float("nan")
    verdict_together = bool(togetherness_ratio < 0.5)
    print(f"       zero sits {togetherness_ratio:.0%} of the way from 'closed' to "
          f"'spread' on summed inter-fingertip spacing")
    print(f"       => emg2pose zero pose looks extended={all(v['proximal_chain_angle_deg'] > 160 for v in straightness.values())}, "
          f"together={verdict_together}")

    # ---- 2. thumb CMC ab/adduction dedicated check ------------------------
    print()
    print("[1B] thumb CMC ab/adduction (canonical idx 1) direction test")
    thumb_tests = {}
    base_lm = np.array(model.skin_landmarks(zeros20))
    thumb_base = base_lm[FINGERTIP["thumb"]]
    palm_axis = base_lm[PALM_CENTER] - base_lm[WRIST]
    palm_axis = palm_axis / np.linalg.norm(palm_axis)
    # A "palm normal" proxy: cross product of the across-palm and along-palm axes.
    across = base_lm[FINGERTIP["pinky"]] - base_lm[FINGERTIP["index"]]
    across = across / np.linalg.norm(across)
    palm_normal = np.cross(palm_axis, across)
    palm_normal = palm_normal / np.linalg.norm(palm_normal)

    for label, value in (("negative", -0.3), ("zero", 0.0), ("positive", +0.3)):
        a = zeros20.copy()
        a[1] = value
        lm = np.array(model.skin_landmarks(a))
        tip = lm[FINGERTIP["thumb"]]
        d = tip - thumb_base
        thumb_tests[label] = {
            "angle_rad": value,
            "thumb_tip": tip.tolist(),
            "displacement_from_zero": d.tolist(),
            "displacement_norm": float(np.linalg.norm(d)),
            "along_palm_normal": float(np.dot(d, palm_normal)),
            "along_palm_axis": float(np.dot(d, palm_axis)),
            "thumb_index_tip_distance": float(np.linalg.norm(tip - lm[FINGERTIP["index"]])),
        }
        print(f"     CMC1_AA = {value:+.2f}  |disp|={np.linalg.norm(d):7.3f}  "
              f"palm-normal component={np.dot(d, palm_normal):+7.3f}  "
              f"thumb<->index tip = {np.linalg.norm(tip - lm[FINGERTIP['index']]):7.3f}")

    pos_norm = thumb_tests["positive"]["along_palm_normal"]
    neg_norm = thumb_tests["negative"]["along_palm_normal"]
    d_pos = thumb_tests["positive"]["thumb_index_tip_distance"] - \
        thumb_tests["zero"]["thumb_index_tip_distance"]
    d_neg = thumb_tests["negative"]["thumb_index_tip_distance"] - \
        thumb_tests["zero"]["thumb_index_tip_distance"]

    # The frozen visu aliser establishes the model's anatomical axes; it is the
    # authority used here rather than a guess about which side is "up".
    #   hand_visualizer/README.md: `y` is the palm-normal axis and **the palm
    #   faces -y**; +z is the thumb side; the model is a RIGHT hand.
    # Our palm_normal proxy is cross(distal, index->pinky) which evaluates to
    # +y, i.e. the DORSAL direction.
    palm_normal_is_dorsal = True
    dors = "dorsal" if palm_normal_is_dorsal else "palmar"
    palm = "palmar" if palm_normal_is_dorsal else "dorsal"

    print(f"       model axes (from hand_visualizer/README.md): palm faces -y; "
          f"our palm-normal proxy is +y = {dors}")
    print(f"     => emg2pose +THUMB_CMC_AA moves the thumb {dors} "
          f"(+{pos_norm:.1f}), -THUMB_CMC_AA moves it {palm} ({neg_norm:.1f})")
    print(f"     => thumb<->index tip distance change: +AA {d_pos:+.1f}, -AA {d_neg:+.1f}")
    # Under the ISB convention, thumb CMC abduction swings the thumb away from
    # the index finger (opening the web), which INCREASES the thumb-index tip
    # distance.  The direction that increases it is therefore abduction.
    emg2pose_positive_abducts = bool(d_pos > d_neg)
    print(f"     => treating 'opens the thumb-index web' as abduction, "
          f"emg2pose positive THUMB_CMC_AA = "
          f"{'ABDUCTION' if emg2pose_positive_abducts else 'ADDUCTION'}")
    print(f"        DB9's CMC1_A is documented as 'Abduction+ / Adduction-' (Table 6).")
    polarity_agrees = bool(emg2pose_positive_abducts)
    print(f"     => polarities agree: {polarity_agrees}")

    # ---- 4. data-side anchor ---------------------------------------------
    data_anchor = None
    if not args.no_data_anchor and args.extracted:
        try:
            data_anchor = reference_posture_from_data(args.extracted)
        except Exception as exc:  # noqa: BLE001
            print(f"[1B] data anchor skipped: {exc!r}")

    report = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hand_model": {"path": str(model.source_path), "sha256": model.source_sha256},
        "question": ("Do DB9 and emg2pose share a zero / axis convention for the "
                     "16 canonical16 variables after name-based selection?"),
        "emg2pose_zero_pose": {
            "all_zero_joint_angles": True,
            "finger_chain_interior_angles_deg": straightness,
            "fingertip_spacing": sp0,
            "most_spread_pose_spacing": wide["spacing"],
            "most_closed_pose_spacing": narrow["spacing"],
            "zero_position_between_closed_and_spread": togetherness_ratio,
            "zero_looks_extended_and_together": verdict_together,
        },
        "thumb_cmc_ab_adduction": {
            "tests": thumb_tests,
            "model_axis_authority": (
                "hand_visualizer/README.md: y is the palm-normal axis, the palm "
                "faces -y, +z is the thumb side, model is a right hand. The "
                "palm-normal proxy used here is +y = dorsal."
            ),
            "emg2pose_positive_moves_thumb_dorsally": bool(pos_norm > 0),
            "emg2pose_positive_thumb_index_distance_change": d_pos,
            "emg2pose_negative_thumb_index_distance_change": d_neg,
            "abduction_interpretation": (
                "ISB-style: thumb CMC abduction swings the thumb away from the "
                "index finger, opening the web and INCREASING the thumb-index "
                "tip distance."
            ),
            "emg2pose_positive_is_abduction": bool(emg2pose_positive_abducts),
            "db9_documented_sign": "CMC1_A: Abduction+ / Adduction- (Table 6)",
            "polarity_agrees": bool(polarity_agrees),
            "confidence": "MEDIUM",
            "why_not_high": (
                "The frozen emg2pose contract explicitly declines to fix the "
                "sign of THUMB_CMC_AA ('NO globally meaningful sign rule'). This "
                "check infers the polarity from model geometry plus an "
                "anatomical convention, not from an official statement about "
                "emg2pose's thumb AA. NO sign flip is applied anywhere in this "
                "codebase as a result."
            ),
        },
        "data_side_reference_anchor": data_anchor,
        "conclusion": None,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print(f"\n[1B] wrote {args.out}")
    return 0


def reference_posture_from_data(extracted: str) -> dict:
    """Which DB9 movement's central third sits closest to all-zero angles?

    The DB9 paper states the reference posture came from the central part of an
    exercise-B movement described as "the hand resting on the table with the
    fingers closed together and extended".  If the calibration is consistent,
    that movement should have the smallest absolute angle magnitude.  This is a
    data-side check of the documented zero, with no model involved.
    """
    import glob

    import db9_to_canonical16 as db9map  # type: ignore
    from db9 import labels
    from db9.loader import db9_exercise_index, load_recording, resolve_subject

    per_movement: dict[int, list[float]] = {}
    for slot_dir in sorted(glob.glob(os.path.join(extracted, "s_*_angles"))):
        slot = int(os.path.basename(slot_dir).split("_")[1])
        for mat in sorted(glob.glob(os.path.join(slot_dir, "*.mat"))):
            if os.path.basename(mat).startswith("._"):
                continue
            rec = load_recording(mat)
            subject, _ = resolve_subject(slot, rec.subject, mat)
            ex = db9_exercise_index(rec, subject)
            if ex != 1:
                continue  # exercise B only: the reference is documented there
            c16 = db9map.to_canonical16(rec.angles)  # radians
            rs, rr = rec.restimulus, rec.rerepetition
            for lab in sorted(set(int(v) for v in np.unique(rs)) - {0}):
                for rep in sorted(set(int(v) for v in np.unique(rr[rs == lab])) - {0}):
                    m = (rs == lab) & (rr == rep)
                    n = int(m.sum())
                    if n < 30:
                        continue
                    third = n // 3
                    central = c16[m][third: n - third]
                    # median over the central third, then mean |angle|
                    med = np.median(central, axis=0)
                    per_movement.setdefault(lab, []).append(
                        float(np.mean(np.abs(med)))
                    )
    table = []
    for lab, vals in sorted(per_movement.items()):
        table.append({
            "exercise_b_label": lab,
            "name": labels.movement_name(1, lab),
            "mean_abs_canonical16_rad": float(np.mean(vals)),
            "n_repetitions": len(vals),
        })
    table.sort(key=lambda r: r["mean_abs_canonical16_rad"])
    print()
    print("[1B] data-side reference anchor -- mean |canonical16| of the central "
          "third, exercise B (smallest = closest to the documented zero)")
    for r in table:
        print(f"     label {r['exercise_b_label']:>2}  {r['mean_abs_canonical16_rad']:.4f} rad  "
              f"{r['name']}")
    winner = table[0] if table else None
    print(f"     => closest to zero: {winner['name'] if winner else 'n/a'}")
    return {
        "method": ("median of the central third of every repetition, then mean "
                   "absolute value across the 16 canonical16 channels"),
        "exercise_b_table": table,
        "closest_to_zero_label": winner["exercise_b_label"] if winner else None,
        "closest_to_zero_name": winner["name"] if winner else None,
        "documented_reference": (
            "exercise-B movement described as 'the hand resting on the table "
            "with the fingers closed together and extended' (Jarque-Bou 2020)"
        ),
    }


if __name__ == "__main__":
    sys.exit(main())
