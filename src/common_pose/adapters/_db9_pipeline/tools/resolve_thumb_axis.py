#!/usr/bin/env python
"""Attack the thumb ab/adduction blocker with geometry instead of convention.

The problem (report section 13, risk 1)
---------------------------------------
DB9 documents `CMC1_A` as *abduction-positive*. Driving emg2pose's
`THUMB_CMC_AA` positively moves the thumb tip dorsally and *closes* the
thumb-index web. Concluding "the polarities are opposite" required importing an
anatomical convention (ISB: abduction opens the web), which is exactly the kind
of assumption the protocol forbids.

There is a sharper question that needs no convention at all:

    Is emg2pose's `THUMB_CMC_AA` even the SAME physical degree of freedom as
    DB9's `CMC1_A`?

DB9's `CMC1_A` is computed from glove sensors 4 and 1 and is an **in-plane**
separation angle between thumb and index (its calibration formula is
`G1*S4 + G2*S1`, the same two sensors that make `CMC1_F`, with the roles
swapped). If emg2pose's thumb AA is instead dominated by an **out-of-plane lift**
of the thumb off the palm, then the two channels are different DOF and a sign
flip would be the wrong repair entirely -- a different emg2pose channel might be
the correct counterpart.

What this script measures
-------------------------
In an anatomical palm frame built from the official model's own landmarks:

* **in-plane web angle** -- the angle between the thumb ray and the index ray,
  projected into the palm plane. This is the quantity DB9's `CMC1_A` senses.
* **out-of-plane elevation** -- the angle of the thumb ray above the palm plane.

Then, for every one of the 20 emg2pose DOF, it computes the sensitivity of both
quantities to that DOF, by central differences over the DOF's official limit
range. No anatomical convention is used anywhere: the arbitrating question is
purely "which channel moves which geometric quantity".

It also confirms DB9's documented sign **from DB9's own labelled movements**,
which is a data-side check independent of Table 6.
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
sys.path.insert(0, os.path.join(_ROOT, "posture_decoder"))
sys.path.insert(0, os.path.join(_ROOT, "representation"))

WRIST, PALM = 5, 20
THUMB_INTER, INDEX_PROX, PINKY_PROX = 6, 8, 17
THUMB_TIP, INDEX_TIP = 0, 1

DOF_NAMES = [
    "THUMB_CMC_FE", "THUMB_CMC_AA", "THUMB_MCP_FE", "THUMB_IP_FE",
    "INDEX_MCP_AA", "INDEX_MCP_FE", "INDEX_PIP_FE", "INDEX_DIP_FE",
    "MIDDLE_MCP_AA", "MIDDLE_MCP_FE", "MIDDLE_PIP_FE", "MIDDLE_DIP_FE",
    "RING_MCP_AA", "RING_MCP_FE", "RING_PIP_FE", "RING_DIP_FE",
    "PINKY_MCP_AA", "PINKY_MCP_FE", "PINKY_PIP_FE", "PINKY_DIP_FE",
]


def palm_frame(lm: np.ndarray):
    """Orthonormal anatomical frame from the model's own landmarks."""
    origin = lm[PALM]
    distal = lm[PALM] - lm[WRIST]
    distal = distal / np.linalg.norm(distal)
    across = lm[INDEX_PROX] - lm[PINKY_PROX]
    across = across / np.linalg.norm(across)
    normal = np.cross(distal, across)
    normal = normal / np.linalg.norm(normal)
    # re-orthogonalise across against distal
    across = np.cross(normal, distal)
    across = across / np.linalg.norm(across)
    return origin, distal, across, normal


def web_geometry(lm: np.ndarray) -> dict:
    """In-plane web angle and out-of-plane elevation of the thumb ray."""
    origin, distal, across, normal = palm_frame(lm)
    thumb = lm[THUMB_INTER] - origin
    index = lm[INDEX_PROX] - origin
    # components in the palm frame
    t_d, t_a, t_n = thumb @ distal, thumb @ across, thumb @ normal
    i_d, i_a, _ = index @ distal, index @ across, index @ normal
    in_plane_thumb = np.array([t_d, t_a])
    in_plane_index = np.array([i_d, i_a])

    def ang(u, v):
        nu, nv = np.linalg.norm(u), np.linalg.norm(v)
        if nu == 0 or nv == 0:
            return float("nan")
        return float(np.degrees(np.arccos(np.clip(u @ v / (nu * nv), -1, 1))))

    return {
        "in_plane_web_angle_deg": ang(in_plane_thumb, in_plane_index),
        "out_of_plane_elevation_deg": float(
            np.degrees(np.arctan2(t_n, np.hypot(t_d, t_a)))
        ),
        "thumb_tip_to_index_tip": float(np.linalg.norm(lm[THUMB_TIP] - lm[INDEX_TIP])),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--extracted", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    from hand_kinematics_np import load_default_model  # type: ignore
    import db9_to_canonical16 as d2c  # type: ignore
    from db9 import labels  # type: ignore
    from db9.loader import (  # type: ignore
        db9_exercise_index, discover_unpacked, load_recording, resolve_subject,
    )

    model = load_default_model()
    lim = model.joint_limits
    zeros = np.zeros(20)
    base = web_geometry(np.asarray(model.skin_landmarks(zeros)))
    print("=" * 78)
    print("Reference geometry at all-zero emg2pose joint angles")
    print("=" * 78)
    print(f"  in-plane web angle      = {base['in_plane_web_angle_deg']:.2f} deg")
    print(f"  out-of-plane elevation  = {base['out_of_plane_elevation_deg']:+.2f} deg")
    print(f"  thumb tip <-> index tip = {base['thumb_tip_to_index_tip']:.2f}")

    # ---- sensitivity of each emg2pose DOF --------------------------------
    print()
    print("=" * 78)
    print("Sensitivity of the thumb web geometry to each emg2pose DOF")
    print("  (central difference across the DOF's official limit range,")
    print("   expressed per radian of that DOF)")
    print("=" * 78)
    rows = []
    for k in range(20):
        lo, hi = float(lim[k][0]), float(lim[k][1])
        if hi - lo < 1e-9:
            continue
        step = (hi - lo) / 2.0
        a_hi, a_lo = zeros.copy(), zeros.copy()
        a_hi[k], a_lo[k] = step, -step
        g_hi = web_geometry(np.asarray(model.skin_landmarks(a_hi)))
        g_lo = web_geometry(np.asarray(model.skin_landmarks(a_lo)))
        d_web = (g_hi["in_plane_web_angle_deg"] - g_lo["in_plane_web_angle_deg"]) / (2 * step)
        d_ele = (g_hi["out_of_plane_elevation_deg"] - g_lo["out_of_plane_elevation_deg"]) / (2 * step)
        rows.append({
            "index": k, "dof": DOF_NAMES[k],
            "official_range_rad": [lo, hi],
            "d_in_plane_web_angle_per_rad": float(d_web),
            "d_out_of_plane_elevation_per_rad": float(d_ele),
            "in_plane_fraction": float(abs(d_web) / (abs(d_web) + abs(d_ele) + 1e-12)),
        })
    rows.sort(key=lambda r: -abs(r["d_in_plane_web_angle_per_rad"]))
    print(f"  {'#':>2} {'DOF':<16} {'d(web)/drad':>12} {'d(elev)/drad':>13} {'in-plane frac':>14}")
    for r in rows[:8]:
        print(f"  {r['index']:>2} {r['dof']:<16} {r['d_in_plane_web_angle_per_rad']:>+12.1f} "
              f"{r['d_out_of_plane_elevation_per_rad']:>+13.1f} {r['in_plane_fraction']:>14.3f}")

    cmc_aa = next(r for r in rows if r["dof"] == "THUMB_CMC_AA")
    cmc_fe = next(r for r in rows if r["dof"] == "THUMB_CMC_FE")
    print()
    print(f"  THUMB_CMC_AA: d(web)/drad = {cmc_aa['d_in_plane_web_angle_per_rad']:+.1f}, "
          f"d(elev)/drad = {cmc_aa['d_out_of_plane_elevation_per_rad']:+.1f} "
          f"-> in-plane fraction {cmc_aa['in_plane_fraction']:.3f}")
    print(f"  THUMB_CMC_FE: d(web)/drad = {cmc_fe['d_in_plane_web_angle_per_rad']:+.1f}, "
          f"d(elev)/drad = {cmc_fe['d_out_of_plane_elevation_per_rad']:+.1f} "
          f"-> in-plane fraction {cmc_fe['in_plane_fraction']:.3f}")

    best_mover = max(rows, key=lambda r: abs(r["d_in_plane_web_angle_per_rad"]))
    verdict = (
        f"the channel that moves the in-plane web angle most is "
        f"{best_mover['dof']} (emg2pose #{best_mover['index']})"
    )
    print(f"  => {verdict}")
    print()
    print("  INTERPRETATION:")
    print("    DB9's CMC1_A is an in-plane thumb/index separation (its calibration")
    print("    uses the same two sensors as CMC1_F with the roles swapped).")
    if abs(cmc_aa["d_in_plane_web_angle_per_rad"]) < 0.35 * abs(
            best_mover["d_in_plane_web_angle_per_rad"]):
        print(f"    THUMB_CMC_AA is NOT the dominant in-plane channel --")
        print(f"    {best_mover['dof']} is {abs(best_mover['d_in_plane_web_angle_per_rad']) / max(abs(cmc_aa['d_in_plane_web_angle_per_rad']), 1e-9):.1f}x stronger.")
        print("    A sign flip would therefore be the WRONG repair: these are not")
        print("    the same physical DOF.")
    else:
        print("    THUMB_CMC_AA IS the dominant in-plane channel, so the two")
        print("    datasets do describe the same DOF and only the sign is at issue.")

    # ---- DB9-side empirical confirmation of Table 6 ----------------------
    print()
    print("=" * 78)
    print("DB9-side check: is CMC1_a really abduction-positive in the data?")
    print("=" * 78)
    per_move: dict[int, list[np.ndarray]] = {}
    for slot, path in discover_unpacked(args.extracted):
        rec = load_recording(path)
        subject_id, _ = resolve_subject(slot, rec.subject, path)
        if db9_exercise_index(rec, subject_id) != 1:
            continue
        c16 = d2c.to_canonical16(rec.angles)
        rs, rr = rec.restimulus, rec.rerepetition
        for lab in sorted(set(int(v) for v in np.unique(rs)) - {0}):
            for rep in sorted(set(int(v) for v in np.unique(rr[rs == lab])) - {0}):
                m = (rs == lab) & (rr == rep)
                idx = np.flatnonzero(m)
                if idx.size < 30:
                    continue
                n = idx.size
                third = n // 3
                per_move.setdefault(lab, []).append(np.median(c16[idx[third:n - third]], axis=0))
    thumb_aa = []
    for lab in sorted(per_move):
        vals = np.stack(per_move[lab])[:, 1]          # canonical slot 1
        thumb_aa.append({
            "label": lab, "name": labels.movement_name(1, lab),
            "mean_deg": float(np.degrees(vals.mean())),
            "sd_deg": float(np.degrees(vals.std())),
            "n": len(vals),
        })
    for r in thumb_aa:
        print(f"  B{r['label']:>2} {r['mean_deg']:>+8.2f} deg (sd {r['sd_deg']:>5.2f})  {r['name'][:44]}")
    b5 = next(r for r in thumb_aa if r["label"] == 5)
    b8 = next(r for r in thumb_aa if r["label"] == 8)
    b4 = next(r for r in thumb_aa if r["label"] == 4)
    diff = b5["mean_deg"] - b8["mean_deg"]
    print()
    print(f"  B5 'Abduction of all fingers' minus B8 'Adduction of extended fingers' "
          f"= {diff:+.2f} deg")
    print(f"  B4 'Thumb opposing base of little finger' (thumb crosses the palm) "
          f"= {b4['mean_deg']:+.2f} deg")
    confirmed = diff > 0 and b4["mean_deg"] < b5["mean_deg"]
    print(f"  => DB9's documented 'CMC1_A Abduction+/Adduction-' is "
          f"{'CONFIRMED by the data' if confirmed else 'NOT confirmed'}")

    report = {
        "reference_geometry_at_zero": base,
        "dof_sensitivity": rows,
        "thumb_cmc_aa": cmc_aa,
        "thumb_cmc_fe": cmc_fe,
        "dominant_in_plane_channel": best_mover,
        "verdict": verdict,
        "db9_side_confirmation": {
            "per_movement_thumb_cmc_ab_adduction_deg": thumb_aa,
            "B5_minus_B8_deg": diff,
            "B4_deg": b4["mean_deg"],
            "table6_abduction_positive_confirmed_by_data": bool(confirmed),
        },
        "note": ("no anatomical convention is used to reach the in-plane/out-of-plane "
                 "split; the arbitration is purely which channel moves which "
                 "geometric quantity"),
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print(f"\n[wrote] {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
