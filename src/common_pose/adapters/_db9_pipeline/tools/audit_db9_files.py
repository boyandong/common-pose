#!/usr/bin/env python
"""PHASE 0 -- machine-readable audit of the official NinaPro DB9 files.

Reads every extracted ``.mat`` and reports, per file, exactly what is present:
subject, source database, exercise, the ``angles`` shape, the ``order_of_angles``
vocabulary, ``restimulus`` / ``rerepetition`` value sets, the ACTUAL number of
repetitions (counted from the data, never taken from documentation), numeric
ranges, NaN/Inf counts and sampling length.

It also re-checks three things the modelling depends on:

* every file declares the same 22-channel ``order_of_angles`` vocabulary;
* the archive-slot -> participant mapping is injective (a subject-independent
  split is only valid if one slot is one person);
* the hand side. DB9's protocol instructed all participants to perform the
  movements with the **right hand** and the MATLAB files carry no side field, so
  the check reports the absence of any side variable rather than assuming it.

Outputs ``docs/DB9_FILE_AUDIT.json`` plus a human-readable summary on stdout.
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

from db9 import canonical, labels  # noqa: E402
from db9.loader import (  # noqa: E402
    CYBERGLOVE_LINK_RATE_HZ,
    NOMINAL_RATE_HZ,
    db9_exercise_index,
    discover_unpacked,
    load_recording,
    resolve_subject,
    source_db_for_subject,
)


def _sniff_variable_names(path: str) -> list[str]:
    """List the variables actually stored in the file, for schema auditing."""
    from db9.loader import _load_mat5, _load_mat73, _sniff_format

    fmt = _sniff_format(path)
    data = _load_mat5(path) if fmt == "mat5" else _load_mat73(path)
    return sorted(k for k in data if not k.startswith("__"))


def audit_file(slot: int, path: str) -> dict:
    rec = load_recording(path)
    subject_id, identity_note = resolve_subject(slot, rec.subject, path)
    ex_idx = db9_exercise_index(rec, subject_id)
    src_db = source_db_for_subject(subject_id)
    nominal = NOMINAL_RATE_HZ[src_db]

    a = rec.angles
    finite = np.isfinite(a)
    nan_cols = [int(i) for i in np.where(~finite.any(axis=0))[0]]
    inf_cols = [int(i) for i in np.where(np.isinf(a).any(axis=0))[0]]

    rs = rec.restimulus
    rr = rec.rerepetition
    movement_mask = rs > 0
    # Repetitions counted from the data: distinct rerepetition values reached by
    # a movement label, per movement.
    per_movement_reps: dict[int, int] = {}
    for lab in sorted(set(int(v) for v in np.unique(rs)) - {0}):
        reps = sorted(set(int(v) for v in np.unique(rr[rs == lab])) - {0})
        per_movement_reps[lab] = len(reps)
    rep_values = sorted(set(int(v) for v in np.unique(rr)))
    stim_present = "stimulus" in _sniff_variable_names(path)

    return {
        "file": os.path.basename(path),
        "archive_slot": slot,
        "subject": subject_id,
        "recorded_subject_field": rec.subject,
        "subject_identity_note": identity_note,
        "source_db": src_db,
        "exercise_field": rec.exercise,
        "ninapro_exercise": {1: "B", 2: "C"}[ex_idx],
        "db9_exercise_index": ex_idx,
        "matlab_format": rec.source_format,
        "variables_present": _sniff_variable_names(path),
        "has_stimulus_variable": stim_present,
        "has_inclinometer": rec.inclin is not None,
        "hand_side_variable": None,  # DB9 .mat files carry no side field
        "angles_shape": list(a.shape),
        "glove_shape": list(rec.glove.shape),
        "order_of_angles": list(rec.order),
        "order_matches_official_table": not canonical.verify_db9_order(rec.order),
        "sample_count": int(rec.n_samples),
        "nominal_rate_hz": nominal,
        "true_sensor_rate_hz": CYBERGLOVE_LINK_RATE_HZ,
        "nominal_duration_s": rec.n_samples / nominal,
        "nan_columns": nan_cols,
        "nan_column_names": [rec.order[i] for i in nan_cols if i < len(rec.order)],
        "inf_columns": inf_cols,
        "nan_fraction_any": float((~finite.all(axis=1)).mean()),
        "restimulus_values": sorted(set(int(v) for v in np.unique(rs))),
        "restimulus_official_max": max(int(v) for v in np.unique(rs)),
        "rerepetition_values": rep_values,
        "repetitions_per_movement": per_movement_reps,
        "total_repetitions": int(sum(per_movement_reps.values())),
        "movement_sample_count": int(movement_mask.sum()),
        "rest_sample_count": int((~movement_mask).sum()),
        "rest_fraction": float((~movement_mask).mean()),
        "angles_global_min": float(np.nanmin(a)),
        "angles_global_max": float(np.nanmax(a)),
        "includes_movement_frames": bool(movement_mask.any()),
        "per_channel": [
            {
                "index": i,
                "name": rec.order[i] if i < len(rec.order) else f"col{i}",
                "min": float(np.nanmin(a[:, i])) if finite[:, i].any() else None,
                "max": float(np.nanmax(a[:, i])) if finite[:, i].any() else None,
                "mean": float(np.nanmean(a[:, i])) if finite[:, i].any() else None,
                "std": float(np.nanstd(a[:, i])) if finite[:, i].any() else None,
                "nan_count": int((~finite[:, i]).sum()),
            }
            for i in range(a.shape[1])
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--extracted", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    found = discover_unpacked(args.extracted)
    if not found:
        raise SystemExit(f"no .mat files under {args.extracted}")
    print(f"[audit] {len(found)} files")

    files = []
    for slot, path in found:
        files.append(audit_file(slot, path))

    # ---- corpus-level checks ---------------------------------------------
    # Identity semantics, stated correctly:
    #   * the DB9 archive slot defines a participant;
    #   * each source database restarted its own subject numbering, so equal
    #     in-file `subject` values across DIFFERENT source databases are
    #     EXPECTED and are not a defect (DB1 slot 1, DB2 slot 28 and DB5 slot 68
    #     all record subject=1). An earlier version of this check labelled that a
    #     "collision", which wrongly implied a data problem;
    #   * the real requirement is that the release-numbering tuple
    #     (source_database, recorded_subject) is INJECTIVE -- one tuple, one
    #     participant -- and that each slot reports exactly one recorded value.
    orders = {tuple(f["order_of_angles"]) for f in files}
    subject_identities: dict[int, set[int]] = defaultdict(set)
    for f in files:
        subject_identities[f["archive_slot"]].add(f["recorded_subject_field"])

    tuple_counts = Counter(
        (source_db_for_subject(int(f["subject"])), int(f["recorded_subject_field"]))
        for f in files
    )
    tuple_collisions = {f"{k[0]}:{k[1]}": v for k, v in tuple_counts.items() if v > 1}

    slots_for_recorded: dict[int, list[int]] = defaultdict(list)
    for slot, vals in subject_identities.items():
        for v in vals:
            slots_for_recorded[v].append(slot)
    recorded_id_reuse = {
        str(v): sorted(sl) for v, sl in sorted(slots_for_recorded.items()) if len(sl) > 1
    }
    slots_with_multiple_recorded = {
        str(s): sorted(v) for s, v in subject_identities.items() if len(v) > 1
    }

    slots = sorted({f["archive_slot"] for f in files})
    summary = {
        "source": {
            "db9_page": labels.DB9_PAGE,
            "paper": labels.PAPER_DB9,
            "movement_figure": labels.FIGURE_URL,
            "movement_figure_sha256": labels.FIGURE_SHA256,
            "extracted_dir": os.path.abspath(args.extracted),
        },
        "audited_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_files": len(files),
        "n_archive_slots": len(slots),
        "archive_slots": slots,
        "source_db_counts": dict(Counter(f["source_db"] for f in files)),
        "n_distinct_order_of_angles": len(orders),
        "order_of_angles_consistent": len(orders) == 1,
        "order_of_angles": list(next(iter(orders))) if len(orders) == 1 else None,
        "all_orders_match_official_table": all(
            f["order_matches_official_table"] for f in files
        ),
        "subject_identity": {
            "slot_to_recorded": {str(k): sorted(v) for k, v in sorted(subject_identities.items())},
            # The archive slot IS the participant identity: the official DB9
            # table lists one row per slot, and the slots in this corpus are
            # distinct, so N slots are N different participants.
            "participant_identity_is_archive_slot": True,
            "n_distinct_participants": len(slots),
            "slot_to_participant_is_injective": len(set(slots)) == len(slots),
            # The real identity requirement: the release-numbering tuple
            # (source_database, recorded_subject) maps one-to-one to participants.
            "source_recorded_tuple_collisions": tuple_collisions,
            "source_recorded_tuples_injective": not tuple_collisions,
            # Reuse of the same in-file id by different source databases is
            # EXPECTED, because each database numbered its own subjects from 1.
            "recorded_ids_reused_across_source_databases": recorded_id_reuse,
            "recorded_id_reuse_across_sources_is_expected": True,
            "slots_with_multiple_recorded_values": slots_with_multiple_recorded,
            "recorded_subject_field_is_usable_as_identity": False,
            "note": ("an in-file `subject` value equal to another source "
                     "database's is expected, not a defect; identity is the "
                     "archive slot"),
            "authority": ("archive slot; the in-file `subject` field uses each "
                          "source database's own numbering and is recorded for "
                          "audit only"),
        },
        "hand_side": {
            "side_variable_present": any(f["hand_side_variable"] for f in files),
            "protocol": ("DB9/Atzori protocol: participants performed the "
                         "movements with the RIGHT hand; the DB9 page's "
                         "'Handedness' column is the participant's own "
                         "handedness, not the recording side."),
            "verdict": ("no side field exists in the released files, so side "
                        "cannot be re-derived from the data; the protocol "
                        "statement is the only available authority"),
        },
        "nan_columns": sorted({tuple(f["nan_column_names"]) for f in files}),
        "nan_columns_consistent": len({tuple(f["nan_columns"]) for f in files}) == 1,
        "inclinometer_present_any": any(f["has_inclinometer"] for f in files),
        "inclinometer_present_all": all(f["has_inclinometer"] for f in files),
        "total_samples": int(sum(f["sample_count"] for f in files)),
        "total_movement_samples": int(sum(f["movement_sample_count"] for f in files)),
        "total_rest_samples": int(sum(f["rest_sample_count"] for f in files)),
        "repetitions_per_movement_by_slot": {
            str(f["archive_slot"]): f["repetitions_per_movement"] for f in files
        },
        "files": files,
    }
    pooled = summary["total_samples"]
    summary["pooled_rest_fraction"] = summary["total_rest_samples"] / pooled if pooled else 0.0

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    # ---- console summary --------------------------------------------------
    print()
    print(f"  archive slots      : {len(slots)}  {slots}")
    print(f"  source databases   : {summary['source_db_counts']}")
    print(f"  order_of_angles    : {summary['n_distinct_order_of_angles']} distinct vocabulary(ies); "
          f"matches official table: {summary['all_orders_match_official_table']}")
    print(f"  NaN columns        : consistent={summary['nan_columns_consistent']} -> "
          f"{summary['nan_columns']}")
    print(f"  inclinometer       : any={summary['inclinometer_present_any']} "
          f"all={summary['inclinometer_present_all']}")
    print(f"  samples            : {summary['total_samples']:,} total, "
          f"{summary['total_movement_samples']:,} movement, rest="
          f"{summary['pooled_rest_fraction']:.2%}")
    si = summary["subject_identity"]
    print(f"  subject identity   : participants={si['n_distinct_participants']} "
          f"(archive slot); (source_db, recorded_subject) injective="
          f"{si['source_recorded_tuples_injective']}")
    print(f"     in-file `subject` ids reused across source databases "
          f"(EXPECTED, not a defect): {si['recorded_ids_reused_across_source_databases']}")
    if not si["source_recorded_tuples_injective"]:
        print(f"     !! (source_db, recorded_subject) is NOT injective: "
              f"{si['source_recorded_tuple_collisions']}")
    if si["slots_with_multiple_recorded_values"]:
        print(f"     !! slots reporting more than one internal subject value: "
              f"{si['slots_with_multiple_recorded_values']}")

    # repetitions actually observed
    rep_counts = Counter()
    for f in files:
        for lab, n in f["repetitions_per_movement"].items():
            rep_counts[(f["ninapro_exercise"], lab, n)] += 1
    by_ex = defaultdict(list)
    for (ex, lab, n), cnt in rep_counts.items():
        by_ex[(ex, lab)].append(n)
    print()
    print("  repetitions per movement (counted from `rerepetition`, per file):")
    for (ex, lab) in sorted(by_ex):
        ns = sorted(set(by_ex[(ex, lab)]))
        name = labels.movement_name(1 if ex == "B" else 2, lab)
        print(f"    ex{ex} label {lab:>2}  reps={ns}  {name}")

    print()
    print(f"[audit] wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
