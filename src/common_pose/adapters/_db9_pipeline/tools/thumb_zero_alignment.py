#!/usr/bin/env python
"""Zero/reference alignment check for the thumb ab/adduction dimension, on its own.

The research lead required this to be verified separately from the sign flip,
because a sign flip is only a complete correction if the two datasets also agree
on where zero is.  A sign flip cannot fix an offset, and an offset cannot fix a
sign; treating them as one question is how a frame conversion goes quietly wrong.

What is measured, and a probe that had to be corrected
------------------------------------------------------
The first probe tried here was `restimulus == 0`, on the assumption that the
protocol's post-repetition rest intervals are the reference posture.  **That
assumption is wrong, and the data says so**: at `restimulus == 0` the pure
flexion control channels sit at +52.6 deg (index PIP) and +44.4 deg (middle MCP),
which a "fingers extended" hand cannot be.  `restimulus` is the *a-posteriori
refined* label; it marks as 0 everything not confidently inside a movement,
which mixes true rest with the reach-in and return transitions.  That negative
result is kept in the output because anyone using DB9 rest as a baseline needs
to know it.

The probe actually used is the one the paper names: the reference posture "was
chosen as the central part of movement 11 in exercise B".  So the anchor is the
**central third of exercise-B movement 11**, per subject, which involves no
model and no rest-interval assumption.  Movement 8 ("Adduction of extended
fingers", i.e. fingers extended and together) is reported as a second, purely
descriptive anchor because its name describes the reference configuration.

* `thumb_cmc_ab_adduction` (canonical slot 1) at the documented anchor.
* Control channels that must also be near zero there, to show the anchor really
  is the extended reference and not an arbitrary pose.
* The emg2pose side is 0 at its rest pose **by construction**.

Verdict rule, fixed in advance: zero aligns if the anchor's value for slot 1 is
small relative to that channel's own between-movement spread.
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

import db9_to_canonical16 as d2c  # noqa: E402
from db9 import labels  # noqa: E402
from db9.loader import (  # noqa: E402
    db9_exercise_index, discover_unpacked, load_recording, resolve_subject,
)

#: Alignment is accepted when the anchor posture sits within this fraction of the
#: channel's between-movement spread of zero.  Fixed before measurement.
ALIGNMENT_TOLERANCE_FRACTION = 0.25

#: The paper names exercise-B movement 11 as the source of the reference posture.
DOCUMENTED_REFERENCE_LABEL = 11
#: Descriptive second anchor: "fingers extended and together".
EXTENDED_TOGETHER_LABEL = 8

CONTROL_CHANNELS = ("index_pip_flexion", "middle_mcp_flexion", "pinky_pip_flexion")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--extracted", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    names = list(d2c.canonical16_names())

    # Per subject: pre-sign values (degrees) at each anchor, plus the movement
    # spread used to normalise.
    anchor_med: dict[int, list[np.ndarray]] = {DOCUMENTED_REFERENCE_LABEL: [],
                                               EXTENDED_TOGETHER_LABEL: []}
    spread: list[np.ndarray] = []
    rest_med: list[np.ndarray] = []

    files = discover_unpacked(args.extracted)
    n_files = 0
    for path_slot, path in files:
        rec = load_recording(path)
        subject, _ = resolve_subject(path_slot, rec.subject, path)
        if db9_exercise_index(rec, subject) != 1:
            continue
        n_files += 1
        raw_deg = rec.angles[:, d2c.resolve_db9_columns()]   # no sign, no radians
        rs, rr = rec.restimulus, rec.rerepetition

        per_move = {}
        for lab in sorted(set(int(v) for v in np.unique(rs)) - {0}):
            reps = []
            for rep in sorted(set(int(v) for v in np.unique(rr[rs == lab])) - {0}):
                idx = np.flatnonzero((rs == lab) & (rr == rep))
                if idx.size < 30:
                    continue
                k = idx.size // 3
                reps.append(np.median(raw_deg[idx[k: idx.size - k]], axis=0))
            if reps:
                per_move[lab] = np.median(np.stack(reps), axis=0)
        if per_move:
            spread.append(np.ptp(np.stack(list(per_move.values())), axis=0))
        for lab in anchor_med:
            if lab in per_move:
                anchor_med[lab].append(per_move[lab])
        rest = rs == 0
        if rest.sum() >= 200:
            rest_med.append(np.median(raw_deg[rest], axis=0))

    def summarise(samples: list[np.ndarray]) -> dict:
        if not samples:
            return {}
        arr = np.stack(samples)
        med = np.median(arr, axis=0)
        sp = np.median(np.stack(spread), axis=0) if spread else np.full(len(names), np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            ratio = np.abs(med) / sp
        return {
            n: {
                "anchor_median_deg_presign": float(med[i]),
                "between_movement_spread_deg": float(sp[i]),
                "abs_anchor_over_spread": float(ratio[i]),
                "is_control": n in CONTROL_CHANNELS,
            }
            for i, n in enumerate(names)
        }

    doc = summarise(anchor_med[DOCUMENTED_REFERENCE_LABEL])
    ext = summarise(anchor_med[EXTENDED_TOGETHER_LABEL])
    rest = summarise(rest_med)

    print("=" * 78)
    print("Zero/reference alignment for DB9 canonical16 slot 1")
    print("=" * 78)
    print(f"  files examined: {n_files}")

    def show(title: str, table: dict, note: str = "") -> None:
        print()
        print(f"  {title}")
        if note:
            print(f"    {note}")
        if not table:
            print("    (no data)")
            return
        print(f"    {'channel':<26} {'anchor median':>14} {'spread':>10} {'ratio':>8}")
        for n in ("thumb_cmc_ab_adduction",) + CONTROL_CHANNELS:
            r = table.get(n)
            if r:
                print(f"    {n:<26} {r['anchor_median_deg_presign']:>+13.2f}d "
                      f"{r['between_movement_spread_deg']:>9.2f}d "
                      f"{r['abs_anchor_over_spread']:>8.3f}")

    show(
        f"A. DOCUMENTED anchor -- central third of exercise-B movement "
        f"{DOCUMENTED_REFERENCE_LABEL}",
        doc,
        f"({labels.movement_name(1, DOCUMENTED_REFERENCE_LABEL)}; the paper names this "
        f"as where the reference posture was taken from)",
    )
    show(
        f"B. DESCRIPTIVE anchor -- movement {EXTENDED_TOGETHER_LABEL}",
        ext,
        f"({labels.movement_name(1, EXTENDED_TOGETHER_LABEL)}; name describes the "
        f"reference configuration)",
    )
    show(
        "C. NEGATIVE RESULT -- restimulus == 0 (NOT the reference posture)",
        rest,
        "(flexion controls are far from zero here, so this probe is invalid and is "
        "reported only to document that fact)",
    )

    thumb = doc.get("thumb_cmc_ab_adduction", {})
    controls_ok = all(
        doc.get(c, {}).get("abs_anchor_over_spread", 9.9) < ALIGNMENT_TOLERANCE_FRACTION
        for c in CONTROL_CHANNELS
    )
    aligned = bool(thumb.get("abs_anchor_over_spread", 9.9) < ALIGNMENT_TOLERANCE_FRACTION)

    print()
    print(f"  tolerance = {ALIGNMENT_TOLERANCE_FRACTION} of the between-movement spread")
    print(f"  documented anchor: thumb_cmc_ab_adduction ratio = "
          f"{thumb.get('abs_anchor_over_spread', float('nan')):.3f}  -> aligned={aligned}")
    print(f"  control channels also near zero at that anchor: {controls_ok}")
    print()
    print("  emg2pose side: THUMB_CMC_AA = 0 at the UmeTrack rest pose by construction,")
    print("  and that rest pose was independently verified to be an extended,")
    print("  fingers-together hand (docs/DB9_EMG2POSE_ZERO_COMPATIBILITY.json).")

    report = {
        "question": ("does DB9's zero for thumb_cmc_ab_adduction coincide with "
                     "emg2pose's zero for THUMB_CMC_AA?"),
        "db9_reference_posture_documented": (
            "'the hand resting on the table with the fingers closed together and "
            "extended', taken from 'the central part of movement 11 in exercise B' "
            "(Jarque-Bou et al. 2020, calibration section)"
        ),
        "n_files": n_files,
        "tolerance_fraction_of_movement_spread": ALIGNMENT_TOLERANCE_FRACTION,
        "probe_A_documented_anchor_movement_11": doc,
        "probe_B_descriptive_anchor_movement_8": ext,
        "probe_C_negative_result_restimulus_zero": rest,
        "probe_C_interpretation": (
            "restimulus == 0 is NOT the reference posture. It is the a-posteriori "
            "refined label, which marks as 0 everything not confidently inside a "
            "movement and therefore mixes true rest with the reach-in and return "
            "transitions. Measured here: index PIP sits at "
            f"{rest.get('index_pip_flexion', {}).get('anchor_median_deg_presign', float('nan')):+.1f} deg, "
            "which a fingers-extended hand cannot be. Recorded so the invalid probe "
            "is not repeated."
        ),
        "emg2pose_side": {
            "THUMB_CMC_AA_at_rest_rad": 0.0,
            "by_construction": True,
            "rest_pose_verified_extended_and_together": True,
            "evidence": "docs/DB9_EMG2POSE_ZERO_COMPATIBILITY.json",
        },
        "verdict": {
            "db9_zero_aligned_with_emg2pose_zero": aligned,
            "control_channels_confirm_anchor_is_the_extended_reference": bool(controls_ok),
            "consequence": (
                "the correction for this variable is a PURE SIGN FLIP with no "
                "offset; the frozen multiplier in "
                "db9_to_canonical16.FROZEN_DB9_SIGN is therefore complete"
                if aligned else
                "an offset would also be required, which the sign flip alone does "
                "not provide -- escalate before using this variable across datasets"
            ),
        },
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print(f"\n[wrote] {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
