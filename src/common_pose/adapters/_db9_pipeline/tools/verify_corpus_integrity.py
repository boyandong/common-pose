#!/usr/bin/env python
"""Corpus-wide integrity verification. No classifier, no accuracy, no metrics.

This is the only kind of analysis permitted while acquisition is incomplete.  It
answers data-integrity questions that must be settled *before* the frozen
confirmatory run, because each of them could otherwise silently distort it:

1. **Is every acquired file Exercise B?**  Confirmed from each file's own
   `max(restimulus) == 17`, not from its name -- filenames disagree with the
   internal exercise field for DB5 (`S74_E2_A1.mat` carries `exercise = 1`).
2. **Is the label set complete?**  Movements 1-17 all present, and how many
   repetitions each has, counted from `rerepetition`.
3. **Is the channel vocabulary and dead-channel pattern identical everywhere?**
4. **Does the cross-source sampling-rate difference survive decimation?**
   DB2 was super-sampled to 2 kHz and DB1 to 100 Hz, so a DB2 file is ~21x
   larger.  The stride rule (nominal / ~25 Hz) should equalise retained frames.
   If it does not, the source databases contribute unequal amounts of training
   data and the DB1/DB2/DB5 breakdowns would be confounded with sample size.
   This check reports the numbers; it does not decide anything about them.
5. **Are units consistent?**  DB9 publishes degrees; a file in radians would be
   visible immediately in the global range.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_ROOT, "posture_decoder"))
sys.path.insert(0, os.path.join(_ROOT, "representation"))

import db9_to_canonical16 as d2c  # noqa: E402
from db9.loader import (  # noqa: E402
    CYBERGLOVE_LINK_RATE_HZ, NOMINAL_RATE_HZ,
    db9_exercise_index, discover_unpacked, load_recording, resolve_subject,
    source_db_for_subject,
)

EXERCISE_B_MAX_LABEL = 17


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--extracted", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = []
    problems = []
    orders: set[tuple[str, ...]] = set()
    nan_patterns: set[tuple[int, ...]] = set()

    for slot, path in discover_unpacked(args.extracted):
        fname = os.path.basename(path)
        try:
            rec = load_recording(path)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{fname}: unreadable: {exc!r}")
            continue
        subject, note = resolve_subject(slot, rec.subject, path)
        db = source_db_for_subject(subject)
        try:
            ex = db9_exercise_index(rec, subject)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{fname}: exercise resolution failed: {exc!r}")
            continue
        if ex != 1:
            continue  # exercise C files are not used by this experiment

        orders.add(tuple(rec.order))
        finite = np.isfinite(rec.angles)
        nan_patterns.add(tuple(int(i) for i in np.where(~finite.any(axis=0))[0]))
        if (nan_patterns and len(nan_patterns) > 1):
            problems.append(f"{fname}: NaN column pattern differs from the rest")

        nominal = NOMINAL_RATE_HZ[db]
        stride = max(1, int(round(nominal / CYBERGLOVE_LINK_RATE_HZ)))
        retained = len(range(0, rec.n_samples, stride))

        labels = sorted(set(int(v) for v in np.unique(rec.restimulus)) - {0})
        rr = rec.rerepetition
        reps_per_movement = {
            lab: len(set(int(v) for v in np.unique(rr[rec.restimulus == lab])) - {0})
            for lab in labels
        }
        missing_labels = sorted(set(range(1, 18)) - set(labels))
        if missing_labels:
            problems.append(f"{fname}: movements missing: {missing_labels}")
        odd_reps = {k: v for k, v in reps_per_movement.items() if v != 6}
        if odd_reps:
            problems.append(f"{fname}: movements without 6 repetitions: {odd_reps}")

        gmin, gmax = float(np.nanmin(rec.angles)), float(np.nanmax(rec.angles))
        looks_like_degrees = bool(max(abs(gmin), abs(gmax)) > 4.0)
        if not looks_like_degrees:
            problems.append(f"{fname}: angle range {gmin:.3f}..{gmax:.3f} does not "
                            "look like degrees")

        rows.append({
            "archive_slot": subject,
            "source_dataset": db,
            "recorded_subject_field": rec.subject,
            "file": fname,
            "file_bytes": os.path.getsize(path),
            "samples_raw": int(rec.n_samples),
            "nominal_rate_hz": nominal,
            "stride": stride,
            "retained_frames": retained,
            "retained_seconds": retained / CYBERGLOVE_LINK_RATE_HZ,
            "movements_present": labels,
            "movements_missing": missing_labels,
            "repetitions_per_movement": reps_per_movement,
            "total_repetitions": int(sum(reps_per_movement.values())),
            "angle_global_min": gmin,
            "angle_global_max": gmax,
            "units_look_like_degrees": looks_like_degrees,
            "nan_columns": sorted(nan_patterns)[0] if len(nan_patterns) == 1 else None,
            "identity_note": note,
        })

    by_db: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_db[r["source_dataset"]].append(r)

    def stat(vals):
        if not vals:
            return None
        return {"min": int(min(vals)), "median": int(np.median(vals)),
                "max": int(max(vals)), "mean": float(np.mean(vals))}

    summary = {
        "n_subjects": len(rows),
        "by_source_dataset": {k: len(v) for k, v in sorted(by_db.items())},
        "n_distinct_order_of_angles": len(orders),
        "order_of_angles_matches_official_table": (
            len(orders) == 1 and d2c.verify_db9_channel_order(next(iter(orders))) == []
        ),
        "nan_column_patterns": [list(p) for p in sorted(nan_patterns)],
        "retained_frames_by_source": {
            k: stat([r["retained_frames"] for r in v]) for k, v in sorted(by_db.items())
        },
        "samples_raw_by_source": {
            k: stat([r["samples_raw"] for r in v]) for k, v in sorted(by_db.items())
        },
        "total_repetitions_by_source": {
            k: stat([r["total_repetitions"] for r in v]) for k, v in sorted(by_db.items())
        },
        "problems": problems,
        "rows": sorted(rows, key=lambda r: r["archive_slot"]),
    }

    print("=" * 78)
    print("CORPUS INTEGRITY (no classifier, no accuracy, no metrics)")
    print("=" * 78)
    print(f"  Exercise-B subjects verified : {summary['n_subjects']}")
    print(f"  by source database           : {summary['by_source_dataset']}")
    print(f"  order_of_angles vocabularies : {summary['n_distinct_order_of_angles']} "
          f"(matches official table: {summary['order_of_angles_matches_official_table']})")
    print(f"  NaN column patterns          : {summary['nan_column_patterns']}")
    print()
    print("  cross-source sampling check (the stride rule must equalise retained data):")
    print(f"    {'source':<7} {'raw samples':>28} {'retained frames':>28} {'reps':>12}")
    for db in sorted(summary["retained_frames_by_source"]):
        s = summary["samples_raw_by_source"][db]
        f = summary["retained_frames_by_source"][db]
        t = summary["total_repetitions_by_source"][db]
        print(f"    {db:<7} {s['min']:>9,}{s['median']:>10,}{s['max']:>9,} "
              f"{f['min']:>9,}{f['median']:>10,}{f['max']:>9,} {t['median']:>12,}")
    print("             (min / median / max within each source database)")
    print()
    if problems:
        print(f"  !! {len(problems)} integrity problem(s):")
        for p in problems[:12]:
            print(f"     - {p}")
    else:
        print("  no integrity problems found")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print(f"\n[wrote] {args.out}")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
