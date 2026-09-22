#!/usr/bin/env python
"""Verify the emg2pose half of the canonical mapping against official data.

Uses only the **already-local** official mini dataset (30 HDF5 sessions), so it
costs no bandwidth.  Four things are checked, each of which would otherwise be
an untested assumption in :mod:`db9.canonical`:

1. **Ordering.**  ``X_shared`` column names must reproduce, in order, the
   official ``emg2pose/constants.py::JOINTS`` list.  Asserted, not trusted.
2. **Units and sign.**  Observed ground-truth ranges are compared with the
   official ``generic_hand_model.json::joint_limits``.  Every flexion joint
   should sit inside its documented range, and the ranges should be asymmetric
   toward positive (positive = flexion).
3. **IK failures.**  Official convention: an inverse-kinematics failure is a row
   of **exact zeros**, not NaN.  Their fraction is measured and they are
   excluded, because an all-zero row is not a neutral hand.
4. **Emg2pose-side coverage.**  Which canonical DOF emg2pose can and cannot
   supply, with per-DOF observed statistics in canonical names.

Outputs ``docs/canonical_emg2pose_verification.json`` and prints a table.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db9 import canonical  # noqa: E402


def load_official_angles(mini_dir: str) -> tuple[np.ndarray, list[str]]:
    """Concatenate ground-truth joint angles from the official mini dataset."""
    import h5py

    files = sorted(glob.glob(os.path.join(mini_dir, "*.hdf5")))
    if not files:
        raise SystemExit(f"no official HDF5 files under {mini_dir}")
    chunks = []
    for f in files:
        with h5py.File(f, "r") as fh:
            ja = fh["emg2pose"]["timeseries"]["joint_angles"][:]  # (T, 20)
        if ja.shape[1] != 20:
            raise SystemExit(f"{f}: joint_angles has {ja.shape[1]} columns, expected 20")
        chunks.append(np.asarray(ja, dtype=np.float64))
    return np.concatenate(chunks), files


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mini-dir", required=True)
    ap.add_argument("--hand-model", required=True,
                    help="official generic_hand_model.json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    canonical.verify_emg2pose_order()
    print("[verify] canonical -> emg2pose ordering matches the official constants table")

    angles, files = load_official_angles(args.mini_dir)
    n_total = angles.shape[0]

    # ---- 3. IK failures: official convention is an exact all-zero row ------
    is_zero_row = np.all(np.isclose(angles, 0.0), axis=1)
    n_bad = int(is_zero_row.sum())
    print(f"[verify] {len(files)} official sessions, {n_total:,} samples")
    print(f"[verify] IK-failure (all-zero) rows: {n_bad:,} = {n_bad / n_total:.3%}")
    good = angles[~is_zero_row]
    print(f"[verify] usable samples: {good.shape[0]:,}")

    # ---- 2. ranges versus the official joint limits -----------------------
    with open(args.hand_model, "r", encoding="utf-8") as fh:
        hm = json.load(fh)
    limits = np.asarray(hm["joint_limits"], dtype=float)[:20]  # rows 0-19
    if limits.shape != (20, 2):
        raise SystemExit(f"unexpected joint_limits shape {limits.shape}")

    names = [d.name for d in sorted(
        (d for d in canonical.CANONICAL_DOFS if d.in_emg2pose),
        key=lambda d: d.emg2pose_index,  # type: ignore[arg-type,return-value]
    )]

    rows = []
    n_outside_total = 0
    for i, nm in enumerate(names):
        col = good[:, i]
        lo, hi = limits[i]
        below = int((col < lo - 1e-9).sum())
        above = int((col > hi + 1e-9).sum())
        n_outside_total += below + above
        rows.append({
            "index": i,
            "canonical": nm,
            "observed_min": float(col.min()),
            "observed_max": float(col.max()),
            "observed_p01": float(np.percentile(col, 1)),
            "observed_p99": float(np.percentile(col, 99)),
            "limit_min": float(lo),
            "limit_max": float(hi),
            "frac_below_limit": below / col.size,
            "frac_above_limit": above / col.size,
        })

    frac_out = n_outside_total / good.size
    print(f"[verify] ground-truth samples outside the official joint_limits: {frac_out:.4%}")
    print()
    print(f"  {'#':>2} {'canonical':<16} {'obs min':>9} {'obs max':>9} "
          f"{'lim min':>9} {'lim max':>9} {'outside':>8}")
    for r in rows:
        print(f"  {r['index']:>2} {r['canonical']:<16} {r['observed_min']:>9.4f} "
              f"{r['observed_max']:>9.4f} {r['limit_min']:>9.4f} {r['limit_max']:>9.4f} "
              f"{(r['frac_below_limit'] + r['frac_above_limit']):>8.3%}")

    # ---- 4. coverage ------------------------------------------------------
    report = {
        "source": {
            "mini_dir": os.path.abspath(args.mini_dir),
            "n_sessions": len(files),
            "n_samples_total": int(n_total),
            "hand_model": os.path.abspath(args.hand_model),
            "note": "official emg2pose mini dataset; no network access used",
        },
        "ordering_check": "PASS - canonical order reproduces constants.py::JOINTS",
        "ik_failures": {
            "convention": "all-zero row (official get_ik_failures_mask), not NaN",
            "n_all_zero_rows": n_bad,
            "fraction": n_bad / n_total,
            "usable_samples": int(good.shape[0]),
        },
        "joint_limits_check": {
            "n_samples_outside_limits": n_outside_total,
            "fraction_outside_limits": frac_out,
            "note": ("These are GROUND-TRUTH labels, so any out-of-limit value is "
                     "the official IK/mocap pipeline exceeding the generic hand "
                     "model's range, not a model error."),
        },
        "per_dof": rows,
        "canonical_coverage": canonical.coverage_report(),
        "shared_dof_names": [d.name for d in canonical.shared_dofs()],
        "emg2pose_only_dof": [d.name for d in canonical.CANONICAL_DOFS
                              if d.in_emg2pose and not d.in_db9],
        "db9_only_dof": [d.name for d in canonical.CANONICAL_DOFS
                         if d.in_db9 and not d.in_emg2pose],
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    print()
    print(f"[verify] shared DOF (observable in both datasets): {len(report['shared_dof_names'])}")
    print(f"[verify] emg2pose-only: {report['emg2pose_only_dof']}")
    print(f"[verify] DB9-only     : {report['db9_only_dof']}")
    print(f"[verify] wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
