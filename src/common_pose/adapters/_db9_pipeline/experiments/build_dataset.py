#!/usr/bin/env python
"""Build a compact, auditable frame table from the extracted official DB9 files.

Output is a single ``.npz`` plus a JSON sidecar so that every experiment can be
re-run from one immutable artifact instead of re-parsing thousands of MATLAB
files.

What goes in
------------
For every (subject, exercise, sample) we store

* ``X_can16`` - (N, 16) the FROZEN first-experiment representation
  (``canonical.canonical16``): shared thumb chains plus MCP/PIP/DIP flexion for
  index..pinky, and **no inter-finger spread features**, in radians.
* ``X_can18`` - (N, 18) the same columns with the two reliable spread features
  (ring and pinky MCP abduction) appended.  Pre-wired so switching them on
  later is a one-argument change.
* ``X_db9``   - (N, 21) all usable DB9 channels, including glove-only wrist and
  pinky CMC.  Kept as an upper-bound reference; not shared with emg2pose.
* ``y``         - global movement id = ``exercise_offset + restimulus``, so that
  exercise B label 1 ("Thumb up") and exercise C label 1 ("Large diameter
  grasp") can never collide.
* ``subject``, ``exercise``, ``repetition``, ``frame_index``
* ``quality_flags`` - per-row bitfield from :mod:`db9.quality` (FLAG, not delete).

Rest samples (``restimulus == 0``) are kept in the artifact with ``y = -1`` so
that downstream code can see them, but every experiment excludes them by
default: the rest position is not one of the 40 movements.

Temporal decimation
-------------------
DB9 super-sampled the ~25 Hz CyberGlove stream to 100/200/2000 Hz depending on
the source database.  Keeping every sample would (a) waste compute and (b)
massively over-count temporally correlated frames.  The builder therefore keeps
every sample whose index is a multiple of ``--stride``, where the default stride
is chosen per recording so the retained rate is ~25 Hz -- i.e. the true sensor
rate, not the interpolated one.  Trials are never discarded; only redundant
interpolated frames are.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db9 import canonical, labels, quality  # noqa: E402
from db9.loader import (  # noqa: E402
    CYBERGLOVE_LINK_RATE_HZ,
    NOMINAL_RATE_HZ,
    db9_exercise_index,
    discover_unpacked,
    load_recording,
    resolve_subject,
    source_db_for_subject,
)

#: Global label ids: exercise B occupies 1..17, exercise C occupies 101..123.
#: The gap makes an accidental collision impossible and keeps ids readable.
EXERCISE_LABEL_OFFSET = {1: 0, 2: 100}


def global_label(exercise_index: int, restimulus: int) -> int:
    if restimulus == 0:
        return -1
    return EXERCISE_LABEL_OFFSET[exercise_index] + int(restimulus)


def label_name(global_id: int) -> str:
    if global_id == -1:
        return labels.REST_NAME
    for ex, off in EXERCISE_LABEL_OFFSET.items():
        if off < global_id <= off + 30:
            return f"E{ex}:{labels.movement_name(ex, global_id - off)}"
    return f"UNKNOWN_{global_id}"


def label_family(global_id: int):
    if global_id == -1:
        return labels.Family.REST
    for ex, off in EXERCISE_LABEL_OFFSET.items():
        if off < global_id <= off + 30:
            return labels.family_of(ex, global_id - off)
    return labels.Family.REST


def build(extracted_dir: str, stride_mode: str, max_subjects: int | None) -> dict:
    found = discover_unpacked(extracted_dir)
    if not found:
        raise SystemExit(f"no extracted .mat files under {extracted_dir}")
    subjects = sorted({s for s, _ in found})
    if max_subjects:
        subjects = subjects[:max_subjects]
        found = [(s, p) for s, p in found if s in set(subjects)]
    print(f"[build] {len(found)} files across {len(subjects)} subjects: {subjects}")

    can16_names = list(canonical.representation_names("canonical16"))
    can18_names = list(canonical.representation_names("canonical18"))
    db9_names = [d.name for d in canonical.CANONICAL_DOFS if d.in_db9]

    X_can16, X_can18, X_db9, y, subject_col, exercise_col, rep_col, frame_col, qflag = (
        [] for _ in range(9)
    )
    reports: list[quality.QualityReport] = []
    per_file: list[dict] = []
    problems: list[str] = []
    seen_pairs: set[tuple[int, str]] = set()
    # slot -> set of internally recorded subject values, used to prove that the
    # archive slots really are distinct participants.
    recorded_by_slot: dict[int, set[int]] = {}

    for subj, path in found:
        rec = load_recording(path)
        fname = os.path.basename(path)

        # --- channel-name verification against the official table -----------
        order_problems = canonical.verify_db9_order(rec.order)
        if order_problems:
            problems.append(f"{fname}: order_of_angles mismatch: {order_problems}")
            print(f"  !! {fname}: channel-name mismatch, skipping")
            continue

        # --- subject identity -----------------------------------------------
        # The DB9 archive slot is authoritative. Each source database numbered
        # its own subjects from 1, so a DB5-derived file for archive slot 68
        # records `subject = 1` internally; using that verbatim would silently
        # attribute six DB5 subjects' data to DB1 subjects.
        subject_id, identity_note = resolve_subject(subj, rec.subject, path)
        if identity_note:
            problems.append(identity_note)
            print(f"  ~~ {fname}: {identity_note.split(': ', 1)[-1]}")
        recorded_by_slot.setdefault(subject_id, set()).add(rec.subject)

        # --- which Ninapro exercise is this? (verified, not assumed) --------
        try:
            ex_idx = db9_exercise_index(rec, subject_id)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{fname}: {exc}")
            print(f"  !! {fname}: {exc}")
            continue

        key = (subject_id, fname)
        if key in seen_pairs:
            problems.append(f"{fname}: duplicate file for subject {subject_id}")
            continue
        seen_pairs.add(key)

        # --- quality flags (never delete) -----------------------------------
        rep = quality.check_angles(
            rec.angles, restimulus=rec.restimulus, rerepetition=rec.rerepetition,
            channel_names=rec.order, label=f"s{subject_id}_{fname}",
        )
        reports.append(rep)
        flags = np.zeros(rec.n_samples, dtype=np.uint8)
        flags |= (rep.outlier_rows.astype(np.uint8) << 0)
        flags |= (rep.jump_rows.astype(np.uint8) << 1)
        flags |= ((rec.restimulus == 0).astype(np.uint8) << 2)

        # --- temporal decimation to the true sensor rate --------------------
        nominal = NOMINAL_RATE_HZ[source_db_for_subject(subject_id)]
        if stride_mode == "none":
            stride = 1
        elif stride_mode == "sensor":
            stride = max(1, int(round(nominal / CYBERGLOVE_LINK_RATE_HZ)))
        else:  # explicit integer
            stride = max(1, int(stride_mode))
        sel = np.arange(0, rec.n_samples, stride)
        if sel.size == 0 or sel[-1] != rec.n_samples - 1:
            sel = np.append(sel, rec.n_samples - 1)

        # --- canonical projection ------------------------------------------
        a_rad = np.radians(rec.angles)          # DB9 publishes DEGREES
        c16 = canonical.db9_degrees_to_representation(
            rec.angles, "canonical16", radians=True)
        c18 = canonical.db9_degrees_to_representation(
            rec.angles, "canonical18", radians=True)
        full = a_rad[:, [d.db9_index for d in canonical.CANONICAL_DOFS if d.in_db9]]

        glob = np.array([global_label(ex_idx, v) for v in rec.restimulus[sel]],
                        dtype=np.int64)

        X_can16.append(c16[sel].astype(np.float32))
        X_can18.append(c18[sel].astype(np.float32))
        X_db9.append(full[sel].astype(np.float32))
        y.append(glob)
        subject_col.append(np.full(sel.size, subject_id, dtype=np.int32))
        exercise_col.append(np.full(sel.size, ex_idx, dtype=np.int8))
        rep_col.append(rec.rerepetition[sel].astype(np.int16))
        frame_col.append(sel.astype(np.int64))
        qflag.append(flags[sel])

        present = sorted(set(int(v) for v in np.unique(rec.restimulus)))
        expected = {0} | {m.label for m in labels.movements_for(ex_idx)}
        unexpected = sorted(set(present) - expected)
        missing = sorted(expected - set(present))
        if unexpected:
            problems.append(f"{fname}: unexpected restimulus values {unexpected}")
        per_file.append({
            "file": fname,
            "subject": subject_id,
            "recorded_subject_field": rec.subject,
            "source_db": source_db_for_subject(subject_id),
            "recorded_exercise_field": rec.exercise,
            "ninapro_exercise": {1: "B", 2: "C"}[ex_idx],
            "db9_exercise_index": ex_idx,
            "n_samples_raw": rec.n_samples,
            "stride": stride,
            "n_samples_kept": int(sel.size),
            "nominal_rate_hz": nominal,
            "effective_rate_hz": nominal / stride,
            "inclinometer": rec.inclin is not None,
            "labels_present": present,
            "labels_missing": missing,
            "quality": rep.summary(),
        })
        print(
            f"  [ok] s{subject_id:<3d} {fname:<16} B/C={ {1:'B',2:'C'}[ex_idx] } "
            f"N={rec.n_samples}->{sel.size} (stride {stride}) "
            f"labels={len(present) - 1} "
            f"flags(outlier={rep.outlier_row_fraction:.3%}, jump={rep.jump_row_fraction:.3%})"
        )

    # --- subject-identity integrity ----------------------------------------
    # A subject-independent split is only valid if each archive slot really is
    # a different participant. That is verified here from the corpus rather
    # than assumed from the release's metadata.
    multi_valued = {s: sorted(v) for s, v in recorded_by_slot.items() if len(v) > 1}
    if multi_valued:
        problems.append(
            f"archive slots with inconsistent internal subject values: {multi_valued}"
        )
    by_recorded: dict[int, list[int]] = {}
    for slot, vals in recorded_by_slot.items():
        for v in vals:
            by_recorded.setdefault(v, []).append(slot)
    collisions = {v: slots for v, slots in by_recorded.items() if len(slots) > 1}
    if collisions:
        # Two archive slots claiming the same participant would silently turn a
        # "cross-subject" evaluation into a partly within-subject one.
        problems.append(f"recorded subject values shared by multiple slots: {collisions}")
    identity_check = {
        "archive_slots_used": sorted(recorded_by_slot),
        "recorded_subject_by_slot": {str(k): sorted(v) for k, v in sorted(recorded_by_slot.items())},
        "slots_with_multiple_recorded_values": multi_valued,
        "recorded_value_collisions": collisions,
        "slot_to_participant_is_injective": not collisions,
        "authority": ("the DB9 archive slot is the identity; the in-file `subject` "
                      "field uses each source database's own numbering and is "
                      "recorded for audit only"),
    }
    print()
    print(f"[build] subject identity: {len(recorded_by_slot)} archive slots, "
          f"injective={identity_check['slot_to_participant_is_injective']}")
    if multi_valued or collisions:
        print(f"        !! identity anomalies recorded: {multi_valued or collisions}")

    if not X_can16:
        raise SystemExit("no usable recordings were built")

    out = {
        "X_can16": np.concatenate(X_can16),
        "X_can18": np.concatenate(X_can18),
        "X_db9": np.concatenate(X_db9),
        "y": np.concatenate(y),
        "subject": np.concatenate(subject_col),
        "exercise": np.concatenate(exercise_col),
        "repetition": np.concatenate(rep_col),
        "frame_index": np.concatenate(frame_col),
        "quality_flags": np.concatenate(qflag),
    }
    meta = {
        "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "extracted_dir": os.path.abspath(extracted_dir),
        "stride_mode": stride_mode,
        "representations": {
            "canonical16": can16_names,
            "canonical18": can18_names,
            "canonical18_adds": list(canonical.OPTIONAL_SPREAD_NAMES),
            "db9full21": db9_names,
        },
        "frozen_first_experiment_representation": "canonical16",
        "label_offsets": EXERCISE_LABEL_OFFSET,
        "units": "radians (converted from DB9 degrees)",
        "n_frames": int(out["y"].size),
        "subjects": subjects,
        "subject_identity": identity_check,
        "files": per_file,
        "problems": problems,
        "quality_pooled": quality.aggregate_summary(reports),
        "provenance": {
            "figure": canonical.__dict__.get("FIGURE_URL", ""),
            "db9_page": labels.DB9_PAGE,
            "paper_db9": labels.PAPER_DB9,
        },
    }
    return {"arrays": out, "meta": meta}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--extracted", required=True)
    ap.add_argument("--out", required=True, help="output .npz path")
    ap.add_argument(
        "--stride", default="sensor",
        help="'sensor' (~25 Hz), 'none' (every sample), or an integer",
    )
    ap.add_argument("--max-subjects", type=int, default=0)
    args = ap.parse_args()

    built = build(args.extracted, args.stride,
                  args.max_subjects or None)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    np.savez_compressed(args.out, **built["arrays"])
    meta_path = os.path.splitext(args.out)[0] + ".meta.json"
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(built["meta"], fh, indent=2)

    meta = built["meta"]
    y = built["arrays"]["y"]
    moved = y > 0
    print()
    print(f"[build] {meta['n_frames']:,} frames -> {args.out}")
    print(f"        {int(moved.sum()):,} movement frames, "
          f"{int((~moved).sum()):,} rest frames")
    print(f"        canonical16 (FROZEN): {len(meta['representations']['canonical16'])}D  "
          f"canonical18: {len(meta['representations']['canonical18'])}D "
          f"(+{meta['representations']['canonical18_adds']})  "
          f"db9full21: {len(meta['representations']['db9full21'])}D")
    cls = Counter(zip(built["arrays"]["exercise"][moved].tolist(), y[moved].tolist()))
    print(f"        {len(cls)} distinct (exercise, movement) classes")
    if meta["problems"]:
        print(f"        {len(meta['problems'])} problem(s) recorded -> {meta_path}")
    qp = meta["quality_pooled"]
    print(f"        pooled: nan_live_rows={qp['nan_row_fraction_live_channels']:.4%} "
          f"outlier_rows={qp['outlier_row_fraction']:.4%} "
          f"jump_rows={qp['jump_row_fraction']:.4%} "
          f"rest={qp['rest_fraction']:.4%}")
    print(f"        meta -> {meta_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
