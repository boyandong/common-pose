#!/usr/bin/env python
"""Inspect freshly-unpacked official DB9 files and check the assumptions that
`db9.canonical` and `db9.labels` are built on.

This is deliberately a *reporting* tool: it never edits or filters data.  It
answers the questions that must be settled from the data itself rather than
from a paper:

  1. What variables are actually present, with what shapes and dtypes?
  2. What are the 22 CyberGlove channel names in this file's own ``order``,
     and can they be resolved to the canonical vocabulary?
  3. Which ``restimulus`` values occur?  Do they run 1..17 / 1..23 per exercise,
     or 1..40 globally?  (Emg2pose-style index assumptions are exactly the kind
     of thing that silently corrupts labels, so this is checked, not assumed.)
  4. Are there NaN / Inf / constant channels?
  5. What are the observed angle ranges per channel -- and do they look like
     degrees or radians?
  6. How many samples per restimulus, and how many distinct repetitions?

Usage
-----
    python tools/inspect_db9.py --extracted ../data/ninapro_db9/extracted --limit 4
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db9 import canonical, labels  # noqa: E402
from db9.loader import (  # noqa: E402
    CYBERGLOVE_LINK_RATE_HZ,
    NOMINAL_RATE_HZ,
    discover_unpacked,
    load_recording,
)


def _fmt_counts(counter: Counter, limit: int = 30) -> str:
    items = sorted(counter.items())
    shown = ", ".join(f"{k}:{v}" for k, v in items[:limit])
    if len(items) > limit:
        shown += f", ... (+{len(items) - limit} more)"
    return shown


def inspect_file(subject: int, path: str) -> dict:
    rec = load_recording(path, expect_subject=subject)
    out: dict = {
        "subject": rec.subject,
        "exercise": rec.exercise,
        "path": os.path.abspath(path),
        "source_format": rec.source_format,
        "n_samples": rec.n_samples,
        "angles_shape": list(rec.angles.shape),
        "glove_shape": list(rec.glove.shape),
        "inclin_shape": None if rec.inclin is None else list(rec.inclin.shape),
        "order_len": len(rec.order),
        "order": list(rec.order),
    }

    print("=" * 78)
    print(f"{os.path.basename(path)}")
    print(f"  format={rec.source_format}  subject={rec.subject}  exercise={rec.exercise}")
    print(f"  angles {rec.angles.shape}   glove {rec.glove.shape}   "
          f"inclin {None if rec.inclin is None else rec.inclin.shape}")
    nominal = NOMINAL_RATE_HZ.get("DB1" if rec.subject <= 27 else
                                  "DB2" if rec.subject <= 67 else "DB5")
    print(f"  nominal (super-sampled) rate = {nominal} Hz -> "
          f"{rec.n_samples / nominal:.1f} s   "
          f"[true glove link rate ~{CYBERGLOVE_LINK_RATE_HZ} Hz]")

    # ---- variable presence -------------------------------------------------
    print("\n  -- variables seen --")
    for name in ("glove", "angles", "inclin", "restimulus", "rerepetition", "order"):
        present = {
            "glove": rec.glove is not None and np.isfinite(rec.glove).any(),
            "angles": True,
            "inclin": rec.inclin is not None,
            "restimulus": True,
            "rerepetition": True,
            "order": len(rec.order) > 0,
        }[name]
        print(f"     {name:<12} {'present' if present else 'ABSENT'}")

    # ---- channel names -----------------------------------------------------
    print("\n  -- CyberGlove channel names (from this file's `order`) --")
    for i, name in enumerate(rec.order):
        print(f"     [{i:2d}] {name}")
    mapping = canonical.resolve_db9_channels(rec.order)
    unresolved = [k for k, v in mapping.items() if v is None]
    out["order_unresolved"] = unresolved
    if unresolved:
        print(f"\n  !! {len(unresolved)} channel(s) could NOT be resolved to the "
              f"canonical vocabulary: {unresolved}")
        print("     These must be reported, not silently dropped.")
    else:
        print(f"\n  all {len(mapping)} channels resolved to canonical DOF names")

    # ---- labels ------------------------------------------------------------
    print("\n  -- restimulus --")
    labs = rec.restimulus
    counts = Counter(int(v) for v in labs)
    print(f"     distinct values: {_fmt_counts(counts, 50)}")
    expected = {0} | {m.label for m in labels.movements_for(rec.exercise)} \
        if rec.exercise in (1, 2) else None
    out["restimulus_values"] = sorted(counts)
    if expected is not None:
        unexpected = sorted(set(counts) - expected)
        missing = sorted(expected - set(counts))
        print(f"     official label set for exercise {rec.exercise}: "
              f"0..{max(expected)} ({len(expected)} incl. rest)")
        if unexpected:
            print(f"     !! UNEXPECTED labels present: {unexpected}")
        if missing:
            print(f"     .. labels in the official table not present: {missing}")
        out["unexpected_labels"] = unexpected
        out["missing_labels"] = missing

    print("\n  -- rerepetition --")
    rc = Counter(int(v) for v in rec.rerepetition)
    print(f"     distinct values: {_fmt_counts(rc)}")
    out["rerepetition_values"] = sorted(rc)

    # samples per (label, repetition)
    pairs = Counter(zip(labs.tolist(), rec.rerepetition.tolist()))
    n_pairs = len(pairs)
    print(f"     {n_pairs} distinct (restimulus, rerepetition) pairs")

    # ---- numeric sanity ----------------------------------------------------
    print("\n  -- angles: numeric sanity --")
    a = rec.angles
    nan_cols = [i for i in range(a.shape[1]) if not np.isfinite(a[:, i]).all()]
    const_cols = [i for i in range(a.shape[1]) if np.nanstd(a[:, i]) == 0]
    print(f"     NaN/Inf columns : {nan_cols if nan_cols else 'none'}")
    print(f"     constant columns: {const_cols if const_cols else 'none'}")
    out["angles_nan_columns"] = nan_cols
    out["angles_constant_columns"] = const_cols

    mn, mx = np.nanmin(a, axis=0), np.nanmax(a, axis=0)
    span = mx - mn
    print(f"     global min={np.nanmin(a):+.3f}  max={np.nanmax(a):+.3f}  "
          f"max span={np.nanmax(span):.3f}")
    looks_degrees = bool(np.nanmax(np.abs(a)) > 4.0)
    unit_guess = "DEGREES" if looks_degrees else "radians or normalised"
    cmp_op = ">" if looks_degrees else "<="
    print(f"     range suggests units: {unit_guess} (|max| {cmp_op} 4)")
    out["angles_global_min"] = float(np.nanmin(a))
    out["angles_global_max"] = float(np.nanmax(a))
    out["angles_look_like_degrees"] = looks_degrees

    print("\n     per-channel min / max / std:")
    for i in range(a.shape[1]):
        nm = rec.order[i] if i < len(rec.order) else f"col{i}"
        print(f"       [{i:2d}] {nm:<24s} min={mn[i]:+9.3f} max={mx[i]:+9.3f} "
              f"std={np.nanstd(a[:, i]):8.3f}")
    out["angles_per_channel_min"] = [float(v) for v in mn]
    out["angles_per_channel_max"] = [float(v) for v in mx]
    out["angles_per_channel_std"] = [float(np.nanstd(a[:, i])) for i in range(a.shape[1])]

    if rec.inclin is not None:
        print("\n  -- inclin (roll, pitch) --")
        for i in range(rec.inclin.shape[1]):
            print(f"       [{i}] min={np.nanmin(rec.inclin[:, i]):+9.3f} "
                  f"max={np.nanmax(rec.inclin[:, i]):+9.3f} "
                  f"std={np.nanstd(rec.inclin[:, i]):8.3f}")
        out["inclin_min"] = [float(v) for v in np.nanmin(rec.inclin, axis=0)]
        out["inclin_max"] = [float(v) for v in np.nanmax(rec.inclin, axis=0)]

    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--extracted", required=True)
    ap.add_argument("--limit", type=int, default=4)
    ap.add_argument("--subjects", default="")
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()

    found = discover_unpacked(args.extracted)
    if args.subjects.strip():
        want = set()
        for chunk in args.subjects.replace(";", ",").split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            if "-" in chunk:
                a, b = chunk.split("-")
                want.update(range(int(a), int(b) + 1))
            else:
                want.add(int(chunk))
        found = [(s, p) for s, p in found if s in want]

    print(f"[inspect] {len(found)} .mat file(s) found under {args.extracted}")
    if not found:
        print("[inspect] nothing to do -- has unpack_db9.py run yet?")
        return 1

    records = [inspect_file(s, p) for s, p in found[: args.limit]]
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(records, fh, indent=2)
        print(f"\n[inspect] wrote {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
