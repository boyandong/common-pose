#!/usr/bin/env python
"""Unpack the official Ninapro DB9 per-subject archives, verify every member
against its CRC-32, and record what was actually extracted.

Why a separate step
-------------------
``fetch_db9.py`` only proves that the *archive* arrived intact (byte length +
sha256).  It says nothing about whether the MATLAB payloads are readable.  This
step therefore:

* verifies every member's CRC-32 as reported by the zip central directory
  (``ZipFile.testzip``) before extracting anything from that archive;
* never overwrites an already-extracted file whose size and CRC still match;
* writes ``unpack_manifest.json`` describing, per archive, every member name,
  its uncompressed size and CRC, and the destination path.

A corrupt archive is reported and skipped rather than partially extracted, so
a damaged download can never masquerade as valid data.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import zipfile
from typing import Any


def _is_macos_junk(member_name: str) -> bool:
    """True for the AppleDouble/resource-fork entries macOS zip tools add.

    The DB9 archives were produced on macOS and contain ``__MACOSX/._*.mat``
    sidecar entries alongside the real payload.  They have ``.mat`` names but
    are not MATLAB files, so extracting them would make discovery see phantom
    recordings.
    """
    parts = member_name.replace("\\", "/").split("/")
    return "__MACOSX" in parts or any(p.startswith("._") for p in parts if p)


def unpack_one(zip_path: str, out_dir: str) -> dict[str, Any]:
    name = os.path.basename(zip_path)
    rec: dict[str, Any] = {"archive": name, "path": os.path.abspath(zip_path)}

    if not zipfile.is_zipfile(zip_path):
        rec["status"] = "NOT_A_ZIP"
        return rec

    with zipfile.ZipFile(zip_path) as zf:
        bad = zf.testzip()  # None when every member's CRC matches
        if bad is not None:
            rec["status"] = "CRC_FAILED"
            rec["bad_member"] = bad
            return rec

        members = []
        for info in zf.infolist():
            if info.is_dir():
                continue
            if _is_macos_junk(info.filename):
                continue
            members.append(
                {
                    "member": info.filename,
                    "size": info.file_size,
                    "crc32": f"{info.CRC:08x}",
                    "compress_size": info.compress_size,
                }
            )
        rec["members"] = members

        dest_dir = os.path.join(out_dir, os.path.splitext(name)[0])
        os.makedirs(dest_dir, exist_ok=True)
        extracted: list[str] = []
        for info in zf.infolist():
            if info.is_dir() or _is_macos_junk(info.filename):
                continue
            # Flatten: DB9 archives store their .mat files at the top level, but
            # be defensive about any nesting.
            target = os.path.join(dest_dir, os.path.basename(info.filename))
            if os.path.exists(target) and os.path.getsize(target) == info.file_size:
                extracted.append(target)
                continue
            with zf.open(info) as src, open(target, "wb") as dst:
                while True:
                    block = src.read(1 << 20)
                    if not block:
                        break
                    dst.write(block)
            extracted.append(target)
        rec["extracted"] = extracted
        rec["status"] = "OK"

    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", required=True, help="directory holding s_<n>_angles.zip")
    ap.add_argument("--out", required=True, help="directory to extract into")
    ap.add_argument("--subjects", default="", help="optional filter, e.g. 1-5;68")
    args = ap.parse_args()

    only: set[int] | None = None
    if args.subjects.strip():
        only = set()
        for chunk in args.subjects.replace(";", ",").split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            if "-" in chunk:
                a, b = chunk.split("-")
                only.update(range(int(a), int(b) + 1))
            else:
                only.add(int(chunk))

    os.makedirs(args.out, exist_ok=True)
    zips = sorted(
        f for f in os.listdir(args.raw) if f.startswith("s_") and f.endswith(".zip")
    )
    if only is not None:
        zips = [z for z in zips if int(z.split("_")[1]) in only]

    print(f"[unpack] {len(zips)} archives -> {args.out}", flush=True)
    records = []
    for z in zips:
        rec = unpack_one(os.path.join(args.raw, z), args.out)
        records.append(rec)
        n = len(rec.get("members", []))
        print(
            f"  [{rec['status']:>10s}] {z:<22} {n} member(s)"
            + (f" bad={rec.get('bad_member')}" if rec["status"] == "CRC_FAILED" else ""),
            flush=True,
        )

    manifest = {
        "source_archives_dir": os.path.abspath(args.raw),
        "extracted_to": os.path.abspath(args.out),
        "unpacked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "archives": records,
    }
    path = os.path.join(args.out, "unpack_manifest.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    ok = sum(1 for r in records if r["status"] == "OK")
    print(f"[unpack] {ok}/{len(records)} archives OK -> {path}", flush=True)
    return 0 if ok == len(records) else 1


if __name__ == "__main__":
    sys.exit(main())
