"""Pre-publication audit scans for the common-pose public repository.

Runs, from the repository root:
  1. SECRET_SCAN              credential-shaped strings and private-key blocks
  2. ABSOLUTE_PATH_SCAN       machine-local paths that must not be published
  3. LARGE_FILE_SCAN          files over 1 / 10 / 50 / 100 MB
  4. THIRD_PARTY_DATA_SCAN    data-shaped and vendor-artifact extensions
  5. PERSONAL_DATA_SCAN       participant / annotator / personal information shapes

Each scan returns PASS / FAIL (or REVIEW where a human must judge) and writes a JSON
record so the result in PUBLICATION_AUDIT.md is backed by an artifact rather than a claim.

Usage:
    python scripts/publication_scan.py            # human-readable report
    python scripts/publication_scan.py --json OUT # also write machine-readable results
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Text files we scan. Binary formats are covered by size and extension rules instead.
TEXT_SUFFIXES = {
    ".py", ".md", ".txt", ".json", ".jsonl", ".csv", ".yaml", ".yml", ".toml",
    ".cfg", ".ini", ".ps1", ".sh", ".bat", ".cmd", ".js", ".mjs", ".ts", ".html",
    ".css", ".gitignore", ".gitattributes",
}

#: Directories that are not part of the published tree.
SKIP_DIRS = {
    ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", ".venv", "venv", "build", "dist", ".egg-info",
}

#: Files that legitimately contain path and credential *patterns* as data: the scanners
#: define what they look for, and the curation manifest documents the substitution table
#: by placeholder. Scanning them for the absence of their own patterns is circular.
PATTERN_DEFINITION_FILES = {
    "scripts/publication_scan.py",
    "scripts/verify_curated_tree.py",
    "scripts/build_curated_tree.py",
    "provenance/CURATION_MANIFEST.json",
}

#: Extensions that indicate redistributed data or model weights.
DATA_SUFFIXES = {
    ".mat", ".h5", ".hdf5", ".npz", ".npy", ".pkl", ".pickle", ".joblib",
    ".ckpt", ".pth", ".pt", ".safetensors", ".onnx", ".pb", ".zip", ".tar",
    ".gz", ".tgz", ".7z", ".bin", ".parquet", ".feather", ".xlsx", ".xls",
    ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".mp4", ".mov",
}

SECRET_PATTERNS: list[tuple[str, str]] = [
    ("openai_key", r"sk-[A-Za-z0-9_\-]{20,}"),
    ("anthropic_key", r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    ("github_pat", r"gh[pousr]_[A-Za-z0-9]{20,}"),
    ("aws_access_key", r"AKIA[0-9A-Z]{16}"),
    ("aws_secret", r"(?i)aws_secret_access_key\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{30,}"),
    ("google_api_key", r"AIza[0-9A-Za-z_\-]{35}"),
    ("slack_token", r"xox[abprs]-[A-Za-z0-9\-]{10,}"),
    ("huggingface_token", r"hf_[A-Za-z0-9]{30,}"),
    ("private_key_block", r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"),
    ("ssh_rsa_pubkey", r"ssh-rsa AAAA[0-9A-Za-z+/=]{50,}"),
    ("basic_auth_url", r"https?://[^/\s:@]{1,64}:[^/\s:@]{1,64}@[A-Za-z0-9.\-]+"),
    ("password_assignment", r"(?i)\b(?:password|passwd|pwd)\b\s*[:=]\s*['\"][^'\"]{6,}['\"]"),
    ("api_key_assignment", r"(?i)\bapi[_-]?key\b\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]"),
    ("secret_assignment", r"(?i)\b(?:client_secret|secret_key|access_token)\b\s*[:=]\s*['\"][^'\"]{12,}['\"]"),
]

#: Machine-local path shapes. The literal strings are assembled at runtime so that this
#: scanner does not itself become a hit.
_DRIVE = "C:" + "\\" + "Users"
_ALT_DRIVE = "[A-Za-z]:" + "\\\\"
ABSOLUTE_PATH_PATTERNS: list[tuple[str, str]] = [
    ("windows_user_profile", re.escape(_DRIVE) + r"\\"),
    ("windows_drive_path", r"(?<![A-Za-z0-9_])" + _ALT_DRIVE + r"[A-Za-z0-9_\-]+"),
    ("posix_root_home", r"/root/"),
    ("posix_home", r"/home/[A-Za-z0-9_\-]+/"),
    ("users_posix", r"/Users/[A-Za-z0-9_\-]+/"),
    ("windows_unc", r"\\\\[A-Za-z0-9_\-]+\\[A-Za-z0-9_\-$]+"),
]

#: Paths that are legitimate published test fixtures or documentation placeholders.
ABSOLUTE_PATH_ALLOWLIST = (
    "C:\\Users\\<",
    "C:/Users/<",
    "/path/to/",
)

PERSONAL_PATTERNS: list[tuple[str, str]] = [
    ("cn_mobile", r"(?<![\d.])1[3-9]\d{9}(?![\d.])"),
    # A bare email-shaped token matches version strings such as "3.11.13", so require a
    # plausible alphabetic TLD and at least one non-digit character before the "@".
    (
        "email",
        r"[A-Za-z0-9._%+\-]*[A-Za-z][A-Za-z0-9._%+\-]*@"
        r"(?:[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,24}\b",
    ),
    # A bare 18-digit run matches ordinary floats. Require the label context.
    ("cn_id_card_labeled", r"(?i)\b(?:id[_ ]?(?:card|number|no)|身份证)\b[^\n]{0,12}\b\d{17}[\dXx]\b"),
    ("student_id", r"(?i)\b(?:student[_ ]?id|学号)\b\s*[:=]?\s*\d{6,}"),
    ("annotator_identity", r"(?i)\b(?:annotator|participant|subject)[_ ]?(?:name|email|phone)\b"),
    ("phone_label", r"(?i)\b(?:phone|tel|mobile)\b\s*[:=]\s*\+?\d"),
]

#: Emails that are public-by-design or syntactically required, not personal data leakage.
EMAIL_ALLOWLIST_SUBSTRINGS = (
    "noreply", "example.com", "example.org", "user@", "you@", "@example",
)

LARGE_THRESHOLDS_MB = (1, 10, 50, 100)


@dataclass
class Finding:
    path: str
    line: int | None
    pattern: str
    excerpt: str


@dataclass
class ScanResult:
    name: str
    verdict: str = "PASS"
    findings: list[Finding] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    counted: dict = field(default_factory=dict)

    def fail(self, note: str) -> None:
        self.verdict = "FAIL"
        self.notes.append(note)

    def review(self, note: str) -> None:
        if self.verdict == "PASS":
            self.verdict = "REVIEW"
        self.notes.append(note)


def iter_files(root: Path):
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        yield p


def rel(p: Path) -> str:
    try:
        return p.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def is_text(p: Path) -> bool:
    if p.suffix.lower() in TEXT_SUFFIXES:
        return True
    if p.name in {".gitignore", ".gitattributes", "LICENSE", "NOTICE", "Makefile"}:
        return True
    return False


def scan_text(pattern_pairs, strip_allow=()):
    hits: list[Finding] = []
    for p in iter_files(REPO_ROOT):
        if not is_text(p):
            continue
        if rel(p) in PATTERN_DEFINITION_FILES:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if any(a in line for a in strip_allow):
                continue
            for name, pattern in pattern_pairs:
                if re.search(pattern, line):
                    hits.append(
                        Finding(rel(p), lineno, name, line.strip()[:160])
                    )
    return hits


def scan_secrets() -> ScanResult:
    r = ScanResult("SECRET_SCAN")
    hits = scan_text(SECRET_PATTERNS)
    # A checksum in a manifest is not a secret; filter obvious sha256-in-json lines.
    real: list[Finding] = []
    for h in hits:
        if re.fullmatch(r"[0-9a-f]{64}", h.excerpt.strip().strip('",')) or (
            "sha256" in h.excerpt.lower() and re.search(r"[0-9a-f]{64}", h.excerpt)
        ):
            r.notes.append(f"ignored checksum-shaped match at {h.path}:{h.line}")
            continue
        real.append(h)
    r.findings = real
    r.counted = {"files_scanned": sum(1 for p in iter_files(REPO_ROOT) if is_text(p))}
    if real:
        r.fail(f"{len(real)} credential-shaped match(es) found")
    return r


def scan_absolute_paths() -> ScanResult:
    r = ScanResult("ABSOLUTE_PATH_SCAN")
    hits = scan_text(ABSOLUTE_PATH_PATTERNS, strip_allow=ABSOLUTE_PATH_ALLOWLIST)
    # A pattern definition inside the scanner itself is not a leak.
    hits = [h for h in hits if h.path != "scripts/publication_scan.py"]
    # Placeholders and documented examples are acceptable.
    kept: list[Finding] = []
    for h in hits:
        ex = h.excerpt
        if re.search(r"[A-Za-z]:[\\/](path|to|your|example)", ex):
            r.notes.append(f"placeholder path accepted at {h.path}:{h.line}")
            continue
        if "<" in ex and ">" in ex:
            r.notes.append(f"angle-bracket placeholder accepted at {h.path}:{h.line}")
            continue
        kept.append(h)
    r.findings = kept
    if kept:
        r.fail(f"{len(kept)} machine-local absolute path(s) found")
    return r


def scan_large_files() -> ScanResult:
    r = ScanResult("LARGE_FILE_SCAN")
    sizes = [(p, p.stat().st_size) for p in iter_files(REPO_ROOT)]
    buckets: dict[str, list[dict]] = {f">{m}MB": [] for m in LARGE_THRESHOLDS_MB}
    for p, size in sizes:
        mb = size / (1024 * 1024)
        for m in LARGE_THRESHOLDS_MB:
            if mb > m:
                buckets[f">{m}MB"].append({"path": rel(p), "mb": round(mb, 3)})
    for k in buckets:
        buckets[k].sort(key=lambda d: -d["mb"])
    r.counted = {
        "files_total": len(sizes),
        "bytes_total": sum(s for _, s in sizes),
        "mb_total": round(sum(s for _, s in sizes) / (1024 * 1024), 3),
        "buckets": {k: v[:25] for k, v in buckets.items()},
        "bucket_counts": {k: len(v) for k, v in buckets.items()},
        "largest_10": [
            {"path": rel(p), "kb": round(s / 1024, 2)}
            for p, s in sorted(sizes, key=lambda t: -t[1])[:10]
        ],
    }
    for m in (10, 50, 100):
        if buckets[f">{m}MB"]:
            r.fail(f"{len(buckets[f'>{m}MB'])} file(s) larger than {m} MB")
    if buckets[">1MB"]:
        r.review(f"{len(buckets['>1MB'])} file(s) larger than 1 MB - confirm each is curated")
    return r


def scan_third_party_data() -> ScanResult:
    r = ScanResult("THIRD_PARTY_DATA_SCAN")
    hits = []
    for p in iter_files(REPO_ROOT):
        if p.suffix.lower() in DATA_SUFFIXES:
            hits.append({"path": rel(p), "kb": round(p.stat().st_size / 1024, 2)})
    r.counted = {"data_shaped_files": hits}
    if hits:
        r.fail(f"{len(hits)} data-shaped or vendor-artifact file(s) present")
    return r


def scan_personal_data() -> ScanResult:
    r = ScanResult("PERSONAL_DATA_SCAN")
    hits = scan_text(PERSONAL_PATTERNS)
    hits = [h for h in hits if h.path != "scripts/publication_scan.py"]
    kept: list[Finding] = []
    for h in hits:
        if h.pattern == "email" and any(
            a in h.excerpt.lower() for a in EMAIL_ALLOWLIST_SUBSTRINGS
        ):
            r.notes.append(f"non-personal email accepted at {h.path}:{h.line}")
            continue
        kept.append(h)
    r.findings = kept
    if kept:
        # Any hit here needs a human decision; it is never auto-passed.
        r.review(f"{len(kept)} possible personal-data match(es) - human review required")
    return r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    results = [
        scan_secrets(),
        scan_absolute_paths(),
        scan_large_files(),
        scan_third_party_data(),
        scan_personal_data(),
    ]

    width = 78
    print("=" * width)
    print("COMMON POSE - PRE-PUBLICATION SCANS")
    print(f"root: {REPO_ROOT}")
    print("=" * width)
    for r in results:
        print(f"\n[{r.verdict}] {r.name}")
        for k, v in r.counted.items():
            if k == "buckets":
                for b, items in v.items():
                    print(f"    {b}: {len(items)}")
                    for it in items[:10]:
                        print(f"        {it['mb']:>10.3f} MB  {it['path']}")
            elif k == "largest_10":
                print("    largest 10:")
                for it in v:
                    print(f"        {it['kb']:>10.2f} KB  {it['path']}")
            else:
                print(f"    {k}: {v}")
        for n in r.notes[:20]:
            print(f"    note: {n}")
        if r.findings:
            print(f"    FINDINGS ({len(r.findings)}):")
            for f in r.findings[:40]:
                print(f"        {f.path}:{f.line}  [{f.pattern}]  {f.excerpt}")

    overall = "PASS"
    if any(r.verdict == "FAIL" for r in results):
        overall = "FAIL"
    elif any(r.verdict == "REVIEW" for r in results):
        overall = "REVIEW"
    print("\n" + "=" * width)
    print(f"OVERALL: {overall}")
    print("=" * width)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(
                {
                    "root": str(REPO_ROOT),
                    "overall": overall,
                    "scans": [
                        {
                            "name": r.name,
                            "verdict": r.verdict,
                            "counted": r.counted,
                            "notes": r.notes,
                            "findings": [asdict(f) for f in r.findings],
                        }
                        for r in results
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"wrote {args.json}")

    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
