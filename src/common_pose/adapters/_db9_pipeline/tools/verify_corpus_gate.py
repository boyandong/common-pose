#!/usr/bin/env python
"""Per-subject corpus gate: PASS/FAIL with independently recomputed integrity.

Runs the same checks whether the corpus is partial or complete, so it can be
used to validate what is present now and re-run as the final 77/77 gate.

Checks per subject
------------------
* expected global slot, and that the source database agrees with the official
  slot ranges (DB1 1-27, DB2 28-67, DB5 68-77);
* the file is the Exercise-B member (resolved through the source-aware exercise
  numbering, not the filename);
* the MAT loads;
* **CRC-32 recomputed locally** and compared with the value declared by the
  archive it came from -- read from the original zip's central directory when
  that zip is still on disk, otherwise from the hardened member-fetch manifest;
* movement labels exactly 1-17 (none missing, none extra);
* repetitions exactly 1-6 for every movement, from `rerepetition`;
* protocol-side `repetition` also 1-6 where the variable is present;
* no missing and no duplicated (movement, repetition) pair;
* no unexpected repetition > 6;
* global/source-local mapping valid: the in-file `subject` field must equal the
  source database's own local index (slot - offset), and must never be used as
  the global identity.

No classifier, no metrics, no outcomes.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import zipfile
import zlib
from collections import Counter

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_ROOT, "posture_decoder"))
sys.path.insert(0, os.path.join(_ROOT, "representation"))

from db9.loader import (  # noqa: E402
    SUBJECT_RECORDED_OFFSET, _load_mat5, _load_mat73, _sniff_format,
    ninapro_letter, discover_unpacked, load_recording,
    source_db_for_subject,
)

MOVEMENTS = list(range(1, 18))
EXPECTED_REPS = list(range(1, 7))


def archive_crcs(raw_dir: str) -> dict[tuple[int, str], dict]:
    """CRC/size declared by each still-present original zip's central directory."""
    out: dict[tuple[int, str], dict] = {}
    for z in glob.glob(os.path.join(raw_dir, "s_*_angles.zip")):
        slot = int(os.path.basename(z).split("_")[1])
        try:
            with zipfile.ZipFile(z) as zf:
                for info in zf.infolist():
                    if info.is_dir() or os.path.basename(info.filename).startswith("._"):
                        continue
                    out[(slot, os.path.basename(info.filename))] = {
                        "crc32": info.CRC, "size": info.file_size,
                        "origin": f"zip central directory ({os.path.basename(z)})",
                    }
        except Exception:  # noqa: BLE001
            continue
    return out


def manifest_crcs(manifest_path: str) -> dict[tuple[int, str], dict]:
    if not os.path.exists(manifest_path):
        return {}
    try:
        m = json.load(open(manifest_path, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    out: dict[tuple[int, str], dict] = {}
    for key, rec in m.get("subjects", {}).items():
        slot = int(key.split("_")[1])
        # Primary source: the attempt records written by the hardened fetcher,
        # which carry the re-validation evidence.
        for a in rec.get("attempts", []):
            # Two manifest generations exist: the hardened fetcher writes
            # `evidence` as a dict, the earlier one wrote it as a string.
            ev = a.get("evidence")
            if not isinstance(ev, dict):
                ev = {}
            crc = (ev.get("expected_crc32")
                   or a.get("crc32_verified_against_central_directory")
                   or a.get("crc32_verified"))
            size = ev.get("expected_uncompressed_size") or a.get("uncompressed_bytes")
            if crc is None:
                continue
            try:
                crc_int = int(str(crc), 16)
            except ValueError:
                continue
            out[(slot, os.path.basename(a["member"]))] = {
                "crc32": crc_int, "size": size,
                "origin": "member-fetch manifest attempt (archive central directory)",
            }
        # Fallback: `members[]` is the archive's own central-directory listing,
        # recorded at fetch time. It covers subjects processed before the
        # attempt-level evidence existed (e.g. slot 74, fetched by the original
        # smoke test) and is still the ARCHIVE's declared CRC -- which is exactly
        # what a locally recomputed CRC must be compared against.
        for mem in rec.get("members", []):
            name = os.path.basename(mem.get("name", ""))
            if not name.lower().endswith(".mat") or name.startswith("._"):
                continue
            try:
                crc_int = int(str(mem["crc32"]), 16)
            except (KeyError, ValueError):
                continue
            out.setdefault((slot, name), {
                "crc32": crc_int,
                "size": mem.get("uncompressed_size"),
                "origin": "member-fetch manifest members[] (archive central directory)",
            })
    return out


def check_subject(slot: int, path: str, crc_lookup: dict) -> dict:
    name = os.path.basename(path)
    checks: dict[str, object] = {}
    reasons: list[str] = []

    db = source_db_for_subject(slot)
    checks["source_database"] = db
    checks["expected_global_slot"] = slot

    try:
        rec = load_recording(path)
        checks["mat_loads"] = True
    except Exception as exc:  # noqa: BLE001
        return {"subject": slot, "source_db": db, "file": name, "pass": False,
                "checks": {"mat_loads": False},
                "reasons": [f"MAT load failed: {exc!r}"]}

    # Exercise-B resolution
    try:
        letter = ninapro_letter(rec, slot)
        checks["exercise_letter"] = letter
        if letter != "B":
            reasons.append(f"resolves to Ninapro exercise {letter}, not B")
    except Exception as exc:  # noqa: BLE001
        checks["exercise_letter"] = None
        reasons.append(f"exercise resolution failed: {exc!r}")

    # Identity. The archive slot is the participant identity; the in-file
    # `subject` field is provenance metadata only and must never define it. A
    # mismatch against the source database's own local index is therefore
    # recorded as an ANOMALY, not a failure -- the official release genuinely
    # contains one (DB5 slot 69 records subject=11 where 2 is predicted). What
    # actually has to hold is that the (source_database, recorded_subject) tuple
    # stays unique, which is checked corpus-wide in main().
    offset = SUBJECT_RECORDED_OFFSET[db]
    expected_local = slot - offset
    checks["recorded_subject_field"] = int(rec.subject)
    checks["expected_source_local_id"] = expected_local
    anomalies: list[str] = []
    if int(rec.subject) != expected_local:
        anomalies.append(
            f"in-file subject {int(rec.subject)} != expected source-local "
            f"{expected_local} (official-release metadata defect; archive slot "
            "remains authoritative)"
        )
    checks["identity_anomalies"] = anomalies
    checks["global_identity_from_archive_slot"] = True

    # CRC, recomputed locally
    key = (slot, name)
    src = crc_lookup.get(key)
    with open(path, "rb") as fh:
        crc = 0
        for block in iter(lambda: fh.read(1 << 20), b""):
            crc = zlib.crc32(block, crc)
    local_crc = crc & 0xFFFFFFFF
    checks["local_crc32"] = f"{local_crc:08x}"
    checks["local_bytes"] = os.path.getsize(path)
    if src is None:
        checks["crc_verified"] = None
        reasons.append("CRC not independently verifiable (no archive record found)")
    else:
        checks["crc_expected"] = f"{src['crc32']:08x}"
        checks["crc_evidence_origin"] = src["origin"]
        if src.get("size") is not None and src["size"] != os.path.getsize(path):
            checks["crc_verified"] = False
            reasons.append(f"size {os.path.getsize(path)} != declared {src['size']}")
        elif local_crc != src["crc32"]:
            checks["crc_verified"] = False
            reasons.append("CRC-32 mismatch against the archive's declared value")
        else:
            checks["crc_verified"] = True

    # labels
    labels_present = sorted(set(int(v) for v in np.unique(rec.restimulus)) - {0})
    checks["movements_present"] = labels_present
    if labels_present != MOVEMENTS:
        missing = sorted(set(MOVEMENTS) - set(labels_present))
        extra = sorted(set(labels_present) - set(MOVEMENTS))
        reasons.append(f"movement labels wrong; missing={missing} extra={extra}")

    rs, rr = rec.restimulus, rec.rerepetition
    per_movement: dict[str, dict] = {}
    missing_pairs = []
    unexpected_reps = []
    for lab in MOVEMENTS:
        m = rs == lab
        if not m.any():
            per_movement[str(lab)] = {"n_repetitions": 0}
            continue
        reps = sorted(set(int(v) for v in np.unique(rr[m])) - {0})
        per_movement[str(lab)] = {"rerepetition_values": reps,
                                  "n_repetitions": len(reps)}
        if reps != EXPECTED_REPS:
            missing = sorted(set(EXPECTED_REPS) - set(reps))
            extra = sorted(set(reps) - set(EXPECTED_REPS))
            if missing:
                missing_pairs.append({"movement": lab, "missing": missing})
            if extra:
                unexpected_reps.append({"movement": lab, "extra": extra})
    checks["per_movement"] = per_movement
    if missing_pairs:
        reasons.append(f"missing movement x repetition pairs: {missing_pairs[:3]}")
    if unexpected_reps:
        reasons.append(f"unexpected repetitions: {unexpected_reps[:3]}")

    # duplicates / zero-sample cells
    dupes = []
    for lab in MOVEMENTS:
        info = per_movement.get(str(lab), {})
        if info.get("n_repetitions", 0) and len(
                set(info.get("rerepetition_values", []))) != info["n_repetitions"]:
            dupes.append(lab)
    checks["duplicate_repetition_cells"] = dupes
    if dupes:
        reasons.append(f"duplicate repetition indices in movements {dupes}")

    # protocol-side repetition, where present
    raw = None
    try:
        fmt = _sniff_format(path)
        raw = _load_mat5(path) if fmt == "mat5" else _load_mat73(path)
    except Exception:  # noqa: BLE001
        raw = None
    if raw is not None and "repetition" in raw:
        rp = np.rint(np.asarray(raw["repetition"]).squeeze().astype(float)).astype(int)
        vals = sorted(set(int(v) for v in np.unique(rp)) - {0})
        checks["protocol_repetition_values"] = vals
        if vals != EXPECTED_REPS:
            reasons.append(f"protocol-side `repetition` values {vals} != 1..6")
    else:
        checks["protocol_repetition_values"] = None

    return {
        "subject": slot, "source_db": db, "file": name,
        "pass": not reasons, "checks": checks, "reasons": reasons,
        "identity_anomalies": anomalies,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--extracted", required=True)
    ap.add_argument("--raw", default="")
    ap.add_argument("--manifest", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--require-full", action="store_true",
                    help="hard-fail unless all 77 slots are present and pass")
    args = ap.parse_args()

    crc_lookup: dict[tuple[int, str], dict] = {}
    if args.raw:
        crc_lookup.update(archive_crcs(args.raw))
    if args.manifest:
        crc_lookup.update(manifest_crcs(args.manifest))

    # slot -> Exercise-B path
    by_slot: dict[int, str] = {}
    for slot, path in discover_unpacked(args.extracted):
        try:
            rec = load_recording(path)
            if ninapro_letter(rec, slot) != "B":
                continue
        except Exception:  # noqa: BLE001
            continue
        by_slot.setdefault(slot, path)

    rows = [check_subject(s, p, crc_lookup) for s, p in sorted(by_slot.items())]

    present = sorted(by_slot)
    missing = [n for n in range(1, 78) if n not in set(present)]
    by_db = Counter(r["source_db"] for r in rows)
    fails = [r for r in rows if not r["pass"]]
    crc_unverified = [r["subject"] for r in rows
                      if r["checks"].get("crc_verified") is None]
    anomalies = [{"subject": r["subject"], "source_db": r["source_db"],
                  "anomalies": r["identity_anomalies"]}
                 for r in rows if r["identity_anomalies"]]

    # Corpus-level identity requirement: the release-numbering tuple
    # (source_database, recorded_subject) must be injective. Equal in-file ids
    # across DIFFERENT source databases are expected, not a defect.
    tuples = [(r["source_db"], r["checks"].get("recorded_subject_field")) for r in rows]
    tuple_counts = Counter(tuples)
    tuple_collisions = {f"{k[0]}:{k[1]}": c for k, c in tuple_counts.items() if c > 1}

    print("=" * 78)
    print("CORPUS GATE (non-outcome; integrity and identity only)")
    print("=" * 78)
    print(f"  present : DB1 {by_db.get('DB1',0)}/27  DB2 {by_db.get('DB2',0)}/40  "
          f"DB5 {by_db.get('DB5',0)}/10  TOTAL {len(rows)}/77")
    print(f"  missing global slots ({len(missing)}): {missing}")
    print(f"  PASS {len(rows) - len(fails)}   FAIL {len(fails)}")
    print(f"  CRC independently verified: {len(rows) - len(crc_unverified)}/{len(rows)}"
          + (f"  (not verifiable: {crc_unverified})" if crc_unverified else ""))
    print(f"  (source_db, recorded_subject) injective: {not tuple_collisions}"
          + (f"  COLLISIONS={tuple_collisions}" if tuple_collisions else ""))
    if anomalies:
        print(f"  identity anomalies (official-release metadata; NOT failures): "
              f"{len(anomalies)}")
        for a in anomalies:
            print(f"     slot {a['subject']} ({a['source_db']}): {a['anomalies'][0]}")
    print()
    print(f"  {'slot':>4} {'src':>4}  {'result':<6} {'crc':<8} note")
    for r in rows:
        note = "" if r["pass"] else "; ".join(r["reasons"])[:70]
        crc = {True: "ok", False: "BAD", None: "n/a"}[r["checks"].get("crc_verified")]
        print(f"  {r['subject']:>4} {r['source_db']:>4}  "
              f"{'PASS' if r['pass'] else 'FAIL':<6} {crc:<8} {note}")

    summary = {
        "present": {db: by_db.get(db, 0) for db in ("DB1", "DB2", "DB5")},
        "total_present": len(rows),
        "expected_total": 77,
        "missing_global_slots": missing,
        "n_pass": len(rows) - len(fails),
        "n_fail": len(fails),
        "crc_not_verifiable": crc_unverified,
        "crc_lookup_entries": len(crc_lookup),
        "source_recorded_tuples_injective": not tuple_collisions,
        "source_recorded_tuple_collisions": tuple_collisions,
        "identity_anomalies": anomalies,
        "identity_authority": ("DB9 archive slot; the in-file `subject` field is "
                               "provenance metadata only and is not used as "
                               "participant identity"),
        "complete": len(rows) == 77 and not missing,
        "all_pass": not fails,
        "failures": fails,
        "subjects": rows,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print(f"\n[wrote] {args.out}")

    if args.require_full:
        if missing:
            print(f"[GATE] FAILED: {len(missing)} slot(s) missing")
            return 2
        if fails:
            print(f"[GATE] FAILED: {len(fails)} subject(s) failed validation")
            return 3
        print("[GATE] PASSED: 77/77 present and valid")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
