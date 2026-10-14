"""Verify the curated tree: compile every Python file, parse every JSON, check encodings.

Runs from the repository root. Exits non-zero on any failure so it can gate a build.
"""

from __future__ import annotations

import json
import py_compile
import re
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".git"}

#: Files that legitimately contain path *patterns* as data: the scanners and this
#: checker define what they look for, and the curation manifest records the
#: substitution table. Checking them for absence of the pattern would be circular.
PATTERN_DEFINITION_FILES = {
    "scripts/publication_scan.py",
    "scripts/verify_curated_tree.py",
    "scripts/build_curated_tree.py",
    "scripts/check_readme_claims.py",
    "provenance/CURATION_MANIFEST.json",
}

#: Real path content, not merely the shape: after the drive letter and separators there
#: must be an actual segment of at least two characters. That distinguishes
#: `C:\Users\...` or `C:\emg2pose\data` from the Windows path grammar examples
#: `C:\...` and `C:\<name>` that appear in prose.
WINDOWS_DRIVE = r"(?<![A-Za-z0-9_<])" + "[A-Za-z]:" + r"\\+(?![.\\])(?=[A-Za-z0-9_])[^\\/\s\"']{2,}"
FORBIDDEN = [
    ("windows_user_profile", re.escape("C:" + "\\" + "Users")),
    ("windows_drive_path", WINDOWS_DRIVE),
    ("posix_root_home", r"(?<!<)/root/[A-Za-z0-9_]"),
]

failures: list[str] = []
counts = {"py": 0, "json": 0, "checked_text": 0}


def files():
    for p in sorted(REPO.rglob("*")):
        if p.is_file() and not any(part in SKIP_DIRS for part in p.parts):
            yield p


def decode(p: Path) -> tuple[str, str]:
    raw = p.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16"), "utf-16"
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    return raw.decode("utf-8"), "utf-8"


print("=" * 74)
print("CURATED TREE VERIFICATION")
print("=" * 74)

# --- Python ---
print("\n[1] py_compile every .py")
with tempfile.TemporaryDirectory() as td:
    for p in files():
        if p.suffix != ".py":
            continue
        counts["py"] += 1
        try:
            py_compile.compile(
                str(p), cfile=str(Path(td) / (p.stem + ".pyc")), doraise=True
            )
        except py_compile.PyCompileError as exc:
            failures.append(f"py_compile FAILED {p.relative_to(REPO).as_posix()}: {exc}")
    print(f"    compiled {counts['py']} files")

# --- JSON ---
print("\n[2] parse every .json")
for p in files():
    if p.suffix != ".json":
        continue
    counts["json"] += 1
    try:
        json.loads(decode(p)[0])
    except Exception as exc:  # noqa: BLE001
        failures.append(f"JSON PARSE FAILED {p.relative_to(REPO).as_posix()}: {exc}")
print(f"    parsed {counts['json']} files")

# --- encoding and paths ---
print("\n[3] encoding and residual machine-local paths")
for p in files():
    if p.suffix.lower() not in {
        ".py", ".md", ".txt", ".json", ".csv", ".yaml", ".yml", ".ps1", ".log",
        ".gitignore", ".toml", ".cfg",
    }:
        continue
    counts["checked_text"] += 1
    rel = p.relative_to(REPO).as_posix()
    if rel in PATTERN_DEFINITION_FILES:
        continue
    try:
        text, _ = decode(p)
    except UnicodeDecodeError as exc:
        failures.append(f"UNDECODABLE {rel}: {exc}")
        continue
    if "\ufffd" in text:
        failures.append(f"REPLACEMENT CHARACTER in {rel}")
    for name, pattern in FORBIDDEN:
        m = re.search(pattern, text)
        if m:
            s = max(0, m.start() - 60)
            failures.append(
                f"LOCAL PATH [{name}] in {rel}: ...{text[s:m.end() + 40]!r}..."
            )
print(f"    checked {counts['checked_text']} text files")

# --- summary ---
print("\n" + "=" * 74)
if failures:
    print(f"FAIL - {len(failures)} problem(s)")
    for f in failures[:40]:
        print("  " + f)
    sys.exit(1)
print("PASS - all Python compiles, all JSON parses, no local paths, no replacement chars")
sys.exit(0)
