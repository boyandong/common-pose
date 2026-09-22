#!/usr/bin/env python
"""Repetition audit over the acquired Exercise-B DB9 files.

No classifier, no metrics, no outcomes -- this reads schema-level fields only.

Two distinct quantities are audited, and confusing them is the likely source of
the documented 10-vs-6 discrepancy:

* ``stimulus`` / ``repetition``   -- the movement and repetition **as prompted by
  the acquisition protocol**, before any post-hoc correction.
* ``restimulus`` / ``rerepetition`` -- the **a-posteriori refined** labels after
  the offline relabelling described by Gijsberts et al. (2014).

The DB9 page documents both variables and states that `restimulus` has "the
duration of the movement label refined a-posteriori in order to better
correspond to the real movement".  So a file can legitimately carry 10 protocol
repetitions while the refined labels cover fewer.

The MAT files are treated as authoritative for what DB9 actually distributes;
the source protocols (DB1: 10 reps, DB2: 6, DB5: 6) are treated as a hypothesis
to be checked, not as a fact to be imposed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_ROOT, "posture_decoder"))
sys.path.insert(0, os.path.join(_ROOT, "representation"))

from db9.loader import (  # noqa: E402
    _load_mat5, _load_mat73, _sniff_format,
    db9_exercise_index, discover_unpacked, load_recording, resolve_subject,
    source_db_for_subject,
)

MOVEMENTS = list(range(1, 18))


def _read_raw_vars(path: str) -> dict:
    fmt = _sniff_format(path)
    return _load_mat5(path) if fmt == "mat5" else _load_mat73(path)


def _flat_int(a) -> np.ndarray:
    return np.rint(np.asarray(a).squeeze().astype(np.float64)).astype(np.int64)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--extracted", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = []
    for slot, path in discover_unpacked(args.extracted):
        fname = os.path.basename(path)
        try:
            rec = load_recording(path)
        except Exception as exc:  # noqa: BLE001
            rows.append({"archive_slot": slot, "file": fname,
                         "status": "UNREADABLE", "error": repr(exc)})
            continue
        subject, _ = resolve_subject(slot, rec.subject, path)
        db = source_db_for_subject(subject)
        try:
            if db9_exercise_index(rec, subject) != 1:
                continue
        except Exception:  # noqa: BLE001
            continue

        raw = _read_raw_vars(path)
        has_repetition = "repetition" in raw
        has_stimulus = "stimulus" in raw
        rep_protocol = _flat_int(raw["repetition"]) if has_repetition else None
        stim_protocol = _flat_int(raw["stimulus"]) if has_stimulus else None

        rs = rec.restimulus
        rr = rec.rerepetition

        per_movement = {}
        keys_seen = Counter()
        for lab in MOVEMENTS:
            m = rs == lab
            if not m.any():
                per_movement[str(lab)] = {"present": False}
                continue
            reps = sorted(set(int(v) for v in np.unique(rr[m])) - {0})
            per_movement[str(lab)] = {
                "present": True,
                "rerepetition_values": reps,
                "n_repetitions": len(reps),
                "n_samples": int(m.sum()),
                "samples_per_repetition": {
                    str(r): int(((rs == lab) & (rr == r)).sum()) for r in reps
                },
            }
            for r in reps:
                keys_seen[(lab, r)] += 1

        # protocol-side (pre-refinement) view, if the variables exist
        protocol_per_movement = {}
        if rep_protocol is not None and stim_protocol is not None:
            for lab in MOVEMENTS:
                m = stim_protocol == lab
                if not m.any():
                    continue
                reps = sorted(set(int(v) for v in np.unique(rep_protocol[m])) - {0})
                protocol_per_movement[str(lab)] = {
                    "repetition_values": reps, "n_repetitions": len(reps)
                }

        rows.append({
            "archive_slot": subject,
            "source_dataset": db,
            "file": fname,
            "status": "OK",
            "has_repetition_variable": has_repetition,
            "has_stimulus_variable": has_stimulus,
            "rerepetition_values_all": sorted(set(int(v) for v in np.unique(rr))),
            "repetition_values_all": (
                sorted(set(int(v) for v in np.unique(rep_protocol)))
                if rep_protocol is not None else None),
            "per_movement": per_movement,
            "per_movement_protocol_side": protocol_per_movement,
        })

    ok = [r for r in rows if r.get("status") == "OK"]
    by_db: dict[str, list[dict]] = defaultdict(list)
    for r in ok:
        by_db[r["source_dataset"]].append(r)

    summary: dict = {"n_files": len(rows), "n_ok": len(ok),
                     "by_source": {k: len(v) for k, v in sorted(by_db.items())},
                     "sources": {}}

    print("=" * 78)
    print("REPETITION AUDIT -- Exercise-B DB9 files (schema fields only)")
    print("=" * 78)
    print(f"  files inspected : {len(rows)}   readable: {len(ok)}")
    print(f"  by source       : {dict(sorted((k, len(v)) for k, v in by_db.items()))}")

    for db in sorted(by_db):
        files = by_db[db]
        print()
        print(f"  --- {db} ({len(files)} files) ---")

        rr_sets = Counter(tuple(r["rerepetition_values_all"]) for r in files)
        print(f"    `rerepetition` value sets (excluding 0), by frequency:")
        for s, c in sorted(rr_sets.items()):
            nz = tuple(v for v in s if v != 0)
            print(f"       {c:>3} file(s): 0..{max(s)}  -> {len(nz)} non-zero values "
                  f"{list(nz)}")

        rep_sets = Counter(tuple(r["repetition_values_all"]) for r in files
                           if r["repetition_values_all"] is not None)
        if rep_sets:
            print(f"    `repetition` (protocol-side) value sets, by frequency:")
            for s, c in sorted(rep_sets.items()):
                nz = tuple(v for v in s if v != 0)
                print(f"       {c:>3} file(s): 0..{max(s)}  -> {len(nz)} non-zero values "
                      f"{list(nz)}")
        else:
            print("    `repetition`/`stimulus` variables: ABSENT")

        counts = Counter()
        missing_keys = []
        for r in files:
            for lab in MOVEMENTS:
                info = r["per_movement"][str(lab)]
                if not info.get("present"):
                    missing_keys.append({"subject": r["archive_slot"],
                                         "movement": lab, "issue": "movement absent"})
                    continue
                counts[info["n_repetitions"]] += 1
        print(f"    repetitions per movement (from `rerepetition`), distribution:")
        for n, c in sorted(counts.items()):
            print(f"       {n} repetition(s): {c} (subject, movement) cells")

        # expected-vs-observed keys
        expected_n = max(counts) if counts else 0
        gap_keys = []
        for r in files:
            for lab in MOVEMENTS:
                info = r["per_movement"][str(lab)]
                if not info.get("present"):
                    continue
                got = set(info["rerepetition_values"])
                want = set(range(1, expected_n + 1))
                if got != want:
                    gap_keys.append({
                        "subject": r["archive_slot"], "movement": lab,
                        "missing": sorted(want - got), "extra": sorted(got - want),
                    })
        summary["sources"][db] = {
            "n_files": len(files),
            "subjects": sorted(r["archive_slot"] for r in files),
            "rerepetition_value_sets": {"|".join(map(str, s)): c
                                        for s, c in sorted(rr_sets.items())},
            "repetition_value_sets_protocol_side": {
                "|".join(map(str, s)): c for s, c in sorted(rep_sets.items())
            },
            "repetitions_per_movement_distribution": {str(k): v
                                                      for k, v in sorted(counts.items())},
            "dominant_repetitions_per_movement": expected_n,
            "movement_absent_cells": [m for m in missing_keys],
            "cells_not_matching_dominant_set": gap_keys,
        }
        print(f"    cells not matching the dominant 1..{expected_n} set: "
              f"{len(gap_keys)}")
        for g in gap_keys[:6]:
            print(f"       s{g['subject']} m{g['movement']}: "
                  f"missing={g['missing']} extra={g['extra']}")
        if missing_keys:
            print(f"    absent movement cells: {len(missing_keys)}")
        else:
            print("    absent movement cells: none (all 17 movements present)")

        # duplicate check
        dups = []
        for r in files:
            for lab in MOVEMENTS:
                info = r["per_movement"][str(lab)]
                if not info.get("present"):
                    continue
                sp = info["samples_per_repetition"]
                if any(v == 0 for v in sp.values()):
                    dups.append({"subject": r["archive_slot"], "movement": lab,
                                 "zero_sample_repetitions":
                                     [k for k, v in sp.items() if v == 0]})
        summary["sources"][db]["zero_sample_repetition_cells"] = dups
        print(f"    (movement, repetition) cells with zero samples: {len(dups)}")

    # per-movement counts table
    print()
    print("  per-movement repetition counts (dominant value across files):")
    print(f"    {'movement':>8}  " + "  ".join(f"{db:>6}" for db in sorted(by_db)))
    for lab in MOVEMENTS:
        cells = []
        for db in sorted(by_db):
            vals = [r["per_movement"][str(lab)].get("n_repetitions")
                    for r in by_db[db] if r["per_movement"][str(lab)].get("present")]
            cells.append(str(Counter(vals).most_common(1)[0][0]) if vals else "-")
        print(f"    {lab:>8}  " + "  ".join(f"{c:>6}" for c in cells))

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump({"summary": summary, "files": rows}, fh, indent=2)
    print(f"\n[wrote] {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
