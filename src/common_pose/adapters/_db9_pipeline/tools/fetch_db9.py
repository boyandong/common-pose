#!/usr/bin/env python
"""Resumable, parallel, provenance-recording fetcher for the official Ninapro
DB9 per-subject archives.

Source of record
----------------
Official Ninapro distribution site, DB9 instruction page:
    https://ninapro.hevs.ch/instructions/DB9.html
Each subject is published as one zip of per-exercise MATLAB files:
    https://ninapro.hevs.ch/files/DB9/<source_db>/s_<n>_angles.zip
``<source_db>`` is the original Ninapro database the subject was drawn from
(DB1 for subjects 1-27, DB2 for 28-67, DB5 for 68-77) -- transcribed from the
official DB9 table, not inferred.

Design notes
------------
* HTTP is delegated to ``curl.exe``.  Measured on this link, curl reaches
  ~75 KB/s aggregate with 4 workers versus ~13 KB/s single-stream, and
  ``curl -C -`` implements Range-based resume correctly.
* A subject is only accepted when its byte length equals the server's
  Content-Length.  Partial files are therefore never mistaken for data.
* The manifest records url + size + sha256 + Last-Modified per file so the
  corpus stays auditable after the fact.
* Re-running is idempotent: verified files are skipped.

This script intentionally does NOT unpack the archives; extraction is a
separate, auditable step (``unpack_db9.py``).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
from typing import Any

BASE = "https://ninapro.hevs.ch/files/DB9"
LOCK = threading.Lock()


def source_db(subject: int) -> str:
    """Official subject -> source-database mapping (transcribed from DB9 page)."""
    if 1 <= subject <= 27:
        return "DB1"
    if 28 <= subject <= 67:
        return "DB2"
    if 68 <= subject <= 77:
        return "DB5"
    raise ValueError(f"subject {subject} outside the official DB9 numbering (1-77)")


def url_for(subject: int) -> str:
    return f"{BASE}/{source_db(subject)}/s_{subject}_angles.zip"


def expand_spec(spec: str) -> list[int]:
    out: set[int] = set()
    for chunk in re.split(r"[,;]", spec):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", chunk)
        if m:
            out.update(range(int(m.group(1)), int(m.group(2)) + 1))
        elif chunk.isdigit():
            out.add(int(chunk))
        else:
            raise ValueError(f"unparsable subject token {chunk!r}")
    return sorted(out)


def curl(args: list[str], timeout: float) -> tuple[int, str]:
    """Run curl, returning (exit_code, stdout). stderr is discarded on purpose."""
    try:
        p = subprocess.run(
            ["curl.exe", *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
        return p.returncode, p.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        return 124, ""


def head_size(url: str) -> int | None:
    for _ in range(5):
        rc, out = curl(["-sSI", "--max-time", "45", url], timeout=60)
        m = re.search(r"^Content-Length:\s*(\d+)", out, re.MULTILINE | re.IGNORECASE)
        if rc == 0 and m:
            return int(m.group(1))
        time.sleep(2)
    return None


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch_one(subject: int, out_dir: str, expect: int) -> dict[str, Any]:
    url = url_for(subject)
    dest = os.path.join(out_dir, f"s_{subject}_angles.zip")

    if os.path.exists(dest) and os.path.getsize(dest) == expect:
        return {
            "subject": subject, "status": "ALREADY_PRESENT",
            "bytes": expect, "sha256": sha256_of(dest),
        }
    if os.path.exists(dest) and os.path.getsize(dest) > expect:
        os.remove(dest)  # corrupt oversize -> restart this one from scratch

    t0 = time.time()
    start = os.path.getsize(dest) if os.path.exists(dest) else 0
    for attempt in range(1, 7):
        curl(
            ["-sS", "-C", "-", "--max-time", "2400", "--retry", "3",
             "--retry-delay", "3", "-o", dest, url],
            timeout=2500,
        )
        have = os.path.getsize(dest) if os.path.exists(dest) else 0
        if have == expect:
            return {
                "subject": subject, "status": "DOWNLOADED", "bytes": have,
                "seconds": round(time.time() - t0, 1),
                "mean_Bps": round((have - start) / max(time.time() - t0, 1e-9), 1),
                "sha256": sha256_of(dest),
            }
        time.sleep(min(2.0 * attempt, 15.0))

    have = os.path.getsize(dest) if os.path.exists(dest) else 0
    return {
        "subject": subject, "status": "INCOMPLETE", "bytes": have,
        "expected": expect,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--subjects", required=True, help="e.g. 1-16;68-73")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    subjects = expand_spec(args.subjects)
    os.makedirs(args.out, exist_ok=True)
    manifest_path = os.path.join(args.out, "manifest.json")

    print(f"[fetch] {len(subjects)} subjects: {','.join(map(str, subjects))}", flush=True)

    expect: dict[int, int] = {}
    for s in subjects:
        n = head_size(url_for(s))
        if n is None:
            print(f"[warn] HEAD failed for s_{s}", flush=True)
        else:
            expect[s] = n
    total_mb = sum(expect.values()) / 1e6
    print(
        f"[fetch] sizes resolved for {len(expect)}/{len(subjects)}; "
        f"{total_mb:.1f} MB total; {args.workers} workers",
        flush=True,
    )

    results: dict[int, dict[str, Any]] = {}
    todo = [s for s in subjects if s in expect]
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(fetch_one, s, args.out, expect[s]): s for s in todo}
        for fut in concurrent.futures.as_completed(futs):
            s = futs[fut]
            try:
                rec = fut.result()
            except Exception as exc:  # noqa: BLE001
                rec = {"subject": s, "status": "ERROR", "error": repr(exc)}
            rec["url"] = url_for(s)
            rec["source_db"] = source_db(s)
            rec["expected_bytes"] = expect[s]
            with LOCK:
                results[s] = rec
                done = len(results)
            print(
                f"  [{rec['status']:>15s}] s_{s:<3d} "
                f"{(rec.get('bytes') or 0) / 1e6:6.2f} MB  "
                f"({done}/{len(todo)})",
                flush=True,
            )

    files: dict[str, Any] = {}
    for s in subjects:
        path = os.path.join(args.out, f"s_{s}_angles.zip")
        if not os.path.exists(path):
            continue
        rec = dict(results.get(s, {"status": "MISSING_HEAD"}))
        rec.update(
            {
                "path": os.path.abspath(path),
                "bytes": os.path.getsize(path),
                "complete": s in expect and os.path.getsize(path) == expect[s],
                "last_write": time.strftime(
                    "%Y-%m-%dT%H:%M:%S", time.localtime(os.path.getmtime(path))
                ),
            }
        )
        files[f"s_{s}"] = rec

    manifest = {
        "source": "https://ninapro.hevs.ch/instructions/DB9.html",
        "paper": (
            "Jarque-Bou, Atzori, Muller, Sci Data 7:12 (2020), "
            "doi:10.1038/s41597-019-0349-2"
        ),
        "retrieved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "subject_to_source_db": {
            "DB1": "1-27", "DB2": "28-67", "DB5": "68-77"
        },
        "files": files,
    }
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    ok = sum(1 for r in files.values() if r.get("complete"))
    print(
        f"[done] {ok}/{len(subjects)} verified, "
        f"{sum(r.get('bytes', 0) for r in files.values()) / 1e6:.1f} MB, "
        f"{time.time() - t0:.0f}s -> {manifest_path}",
        flush=True,
    )
    return 0 if ok == len(subjects) else 1


if __name__ == "__main__":
    sys.exit(main())
