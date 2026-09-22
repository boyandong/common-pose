"""Frozen confirmatory policy: primary lock, cohort records, cache validity, and
hard subject-identity assertions.

This module exists so that the rules the confirmatory result depends on live in
exactly one place and are testable without running any experiment.  Nothing in
here inspects a score.

The four rules it encodes
-------------------------
1. **Primary lock.**  The primary confirmatory result is fixed to
   ``lda(lsqr, shrinkage='auto')`` + train-only z-score + canonical16.  It is
   returned by identity, and :func:`select_primary` never consults accuracy, so a
   better-scoring secondary configuration cannot displace it.  Secondary
   configurations are reported for information only.
2. **Cache validity.**  A cached representative-posture artifact may only be
   reused when its validity key matches, and the key covers the exact input file
   list, every input file's size and content hash, the schema hash, the
   extraction-code hash, the frozen-spec hash and the representation name.  The
   confirmatory driver rebuilds unconditionally; caching is opt-in and verified.
3. **Cohorts.**  Development-exposed, outcome-unseen and integrity-only sets are
   machine-derived records, never hand-edited.
4. **Identity.**  The DB9 archive slot defines a participant.  The in-file
   ``subject`` field is provenance metadata only: each source database restarted
   its own numbering, so equal local ids from different source databases are
   *expected* and are not a defect.  The real requirement is that the
   ``(source_database, recorded_subject)`` tuple is injective and that every
   global slot occurs exactly once.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# 1. PRIMARY LOCK
# ---------------------------------------------------------------------------
# These three constants ARE the confirmatory configuration.  They are not
# defaults, not preferences, and not selectable at runtime.
PRIMARY_MODEL = "lda"
PRIMARY_MODEL_CONFIG = {"solver": "lsqr", "shrinkage": "auto"}
PRIMARY_NORMALIZATION = "train_only_zscore"
PRIMARY_REPRESENTATION = "canonical16"

#: How the normalisation choice is spelled in result keys.
_NORM_TOKEN = {"train_only_zscore": "z", "raw": "raw"}

#: Secondary configurations, reported for information only.  This tuple is used
#: to label output; it is never used to pick anything.
SECONDARY_MODELS = (
    "nearest_centroid_euclidean",
    "nearest_centroid_mahalanobis",
    "lda",
    "logreg",
    "random_forest",
)
SECONDARY_NORMALIZATIONS = ("train_only_zscore", "raw")


def run_key(model: str, normalization: str) -> str:
    token = _NORM_TOKEN.get(normalization)
    if token is None:
        raise KeyError(f"unknown normalization {normalization!r}")
    return f"{model}__{token}"


def primary_run_key() -> str:
    """The frozen primary run key. A pure function -- it cannot depend on results."""
    return run_key(PRIMARY_MODEL, PRIMARY_NORMALIZATION)


def select_primary(results_by_key: dict[str, Any]) -> tuple[str, Any]:
    """Return ``(primary_key, primary_result)`` **by identity**.

    Deliberately ignores every score in ``results_by_key``.  There is no
    ``max``/``argmax``/ranking here and there must never be one: the primary
    configuration is fixed before evaluation, and a secondary configuration that
    happens to score higher may not displace it.

    Returns ``(key, None)`` when the primary configuration is absent -- the
    caller must treat that as a hard error rather than falling back to something
    that did run.
    """
    key = primary_run_key()
    return key, results_by_key.get(key)


def assert_no_score_based_primary_selection(source_text: str) -> list[str]:
    """Static guard: report score-based selection idioms in driver source.

    Returns a list of offending lines.  Used by a test so that a future edit
    reintroducing ``max(..., key=...accuracy...)`` fails loudly.
    """
    import re

    bad: list[str] = []
    patterns = (
        r"\bbest_key\b", r"\bbest_model\b", r"\bwinner\b",
        r"max\([^)]*key\s*=\s*lambda[^)]*accuracy",
        r"max\([^)]*key\s*=\s*lambda[^)]*\[.?accuracy",
    )
    for i, line in enumerate(source_text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for p in patterns:
            if re.search(p, line):
                bad.append(f"{i}: {stripped}")
                break
    return bad


# ---------------------------------------------------------------------------
# 2. CACHE VALIDITY
# ---------------------------------------------------------------------------
CACHE_SCHEMA_VERSION = 2


def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def cache_validity_key(
    *,
    input_files: Iterable[str],
    schema_path: str,
    extraction_code_path: str,
    frozen_spec_path: str,
    representation: str,
) -> dict[str, Any]:
    """Everything a representative-posture cache must match to be reusable."""
    files = sorted(os.path.abspath(f) for f in input_files)
    return {
        "cache_schema_version": CACHE_SCHEMA_VERSION,
        "representation": representation,
        "n_input_files": len(files),
        "input_files": [
            {"path": f, "bytes": os.path.getsize(f), "sha256": sha256_file(f)}
            for f in files
        ],
        "schema_sha256": sha256_file(schema_path) if os.path.exists(schema_path) else None,
        "extraction_code_sha256": (
            sha256_file(extraction_code_path)
            if os.path.exists(extraction_code_path) else None
        ),
        "frozen_spec_sha256": (
            sha256_file(frozen_spec_path) if os.path.exists(frozen_spec_path) else None
        ),
    }


def cache_is_usable(cache_meta_path: str, expected_key: dict[str, Any]) -> tuple[bool, str]:
    """Compare a cache's recorded validity key with the expected one.

    A missing or malformed metadata file is *not* usable.  Any mismatch forces a
    rebuild; there is no partial-trust path.
    """
    if not os.path.exists(cache_meta_path):
        return False, "cache metadata missing"
    try:
        with open(cache_meta_path, encoding="utf-8") as fh:
            recorded = json.load(fh)
    except Exception as exc:  # noqa: BLE001
        return False, f"cache metadata unreadable: {exc!r}"
    rec_key = recorded.get("validity_key")
    if rec_key is None:
        return False, "cache has no validity_key (pre-dates the hardened policy)"
    if rec_key != expected_key:
        differing = [
            k for k in set(rec_key) | set(expected_key)
            if rec_key.get(k) != expected_key.get(k)
        ]
        return False, f"validity key mismatch on {sorted(differing)}"
    return True, "validity key matches"


# ---------------------------------------------------------------------------
# 3. COHORTS
# ---------------------------------------------------------------------------
COHORT_RECORD_PATH = "docs/CONFIRMATORY_COHORTS.json"


def write_cohort_record(
    path: str,
    *,
    development_exposed: Iterable[int],
    outcome_unseen: Iterable[int],
    integrity_only_touched: Iterable[int],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """Persist the three machine-derived cohort sets in one record.

    * ``development_exposed`` -- entered a result-producing run.
    * ``outcome_unseen``      -- never entered a result-producing run.
    * ``integrity_only_touched`` -- loaded only for file/schema/integrity checks.
      Touch-for-integrity is explicitly **not** outcome exposure, and the two are
      recorded separately so the distinction cannot be blurred later.
    """
    rec = {
        "policy": ("machine-derived; never hand-edited. The final report must "
                   "distinguish A primary untouched/outcome-unseen holdout "
                   "evidence, B full-77 LOSO descriptive evidence, and C "
                   "secondary/exploratory comparisons -- these are not equally "
                   "confirmatory."),
        "development_exposed": sorted(int(s) for s in development_exposed),
        "outcome_unseen": sorted(int(s) for s in outcome_unseen),
        "integrity_only_touched": sorted(int(s) for s in integrity_only_touched),
        "integrity_touch_is_not_outcome_exposure": True,
        "evidence": evidence,
    }
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2)
    return rec


#: Expected cohort sizes, from the frozen design. Asserted, not assumed.
EXPECTED_EXPOSED_N = 34
EXPECTED_UNSEEN_N = 43


def load_cohort_record(path: str) -> dict:
    """Load the machine-derived cohort record.

    The driver must obtain its cohorts from this artifact rather than
    hard-coding subject ids, so cohort membership cannot drift into the code.
    """
    if not os.path.exists(path):
        raise IdentityAssertionError(
            f"cohort record {path} is missing; run "
            "tools/freeze_confirmatory_spec.py first"
        )
    with open(path, encoding="utf-8") as fh:
        rec = json.load(fh)
    for k in ("development_exposed", "outcome_unseen"):
        if k not in rec:
            raise IdentityAssertionError(f"cohort record lacks {k!r}")
    return rec


def assert_cohort_partition(exposed: Iterable[int], unseen: Iterable[int],
                            all_subjects: Iterable[int]) -> dict:
    """Hard assertions for the primary confirmatory partition.

    Requires: |exposed| = 34, |unseen| = 43, disjoint, union = all 77 subjects.
    Any violation raises; there is no fallback.
    """
    e = set(int(s) for s in exposed)
    u = set(int(s) for s in unseen)
    a = set(int(s) for s in all_subjects)

    if len(e) != EXPECTED_EXPOSED_N:
        raise IdentityAssertionError(
            f"development_exposed has {len(e)} subjects, expected {EXPECTED_EXPOSED_N}"
        )
    if len(u) != EXPECTED_UNSEEN_N:
        raise IdentityAssertionError(
            f"outcome_unseen has {len(u)} subjects, expected {EXPECTED_UNSEEN_N}"
        )
    if e & u:
        raise IdentityAssertionError(
            f"cohorts are not disjoint: {sorted(e & u)}"
        )
    if e | u != a:
        missing = sorted(a - (e | u))
        extra = sorted((e | u) - a)
        raise IdentityAssertionError(
            "cohort union != all subjects; "
            f"missing={missing[:10]} extra={extra[:10]}"
        )
    return {
        "n_exposed": len(e),
        "n_unseen": len(u),
        "disjoint": True,
        "union_equals_all_subjects": True,
        "n_all_subjects": len(a),
        "primary_train_source": "development_exposed",
        "primary_test_source": "outcome_unseen",
    }


# ---------------------------------------------------------------------------
# 4. HARD SUBJECT-IDENTITY ASSERTIONS
# ---------------------------------------------------------------------------
EXPECTED_CORPUS = {"DB1": (1, 27), "DB2": (28, 67), "DB5": (68, 77)}
EXPECTED_TOTAL = 77


class IdentityAssertionError(AssertionError):
    """Raised when the corpus is not exactly the official DB9 composition."""


def expected_slots() -> list[int]:
    out: list[int] = []
    for lo, hi in EXPECTED_CORPUS.values():
        out.extend(range(lo, hi + 1))
    return out


def source_db_of(slot: int) -> str:
    for db, (lo, hi) in EXPECTED_CORPUS.items():
        if lo <= slot <= hi:
            return db
    raise ValueError(f"global slot {slot} is outside 1-77")


def assert_corpus_identity(rows: Iterable[dict[str, Any]], *, require_full: bool = True) -> dict:
    """Assert the official 77 = 27 + 40 + 10 composition, by global slot.

    ``rows`` must supply ``global_subject_id``, ``source_dataset`` and
    ``recorded_subject_field``.

    Checks performed:
      * no duplicate global slot; every expected slot present when
        ``require_full``;
      * per-source counts and slot ranges exactly as official;
      * one recorded value per slot (a slot must not report two different
        internal ids);
      * **(source_database, recorded_subject) injective** -- this is the real
        identity requirement.  Equal recorded ids across *different* source
        databases are expected (DB1 slot 1, DB2 slot 28 and DB5 slot 68 all
        record `subject = 1`) and are deliberately NOT treated as a defect.
    """
    rows = list(rows)
    slots = [int(r["global_subject_id"]) for r in rows]
    dupes = sorted(s for s, c in Counter(slots).items() if c > 1)
    if dupes:
        raise IdentityAssertionError(f"duplicate global subject slots: {dupes}")

    present = set(slots)
    missing = sorted(set(expected_slots()) - present)
    if require_full and missing:
        raise IdentityAssertionError(
            f"corpus is incomplete: {len(missing)} expected global slots missing: "
            f"{missing[:10]}{'...' if len(missing) > 10 else ''}"
        )
    unexpected = sorted(present - set(expected_slots()))
    if unexpected:
        raise IdentityAssertionError(f"unexpected global slots: {unexpected}")

    by_source: dict[str, list[int]] = {}
    for r in rows:
        db = str(r["source_dataset"])
        slot = int(r["global_subject_id"])
        if db != source_db_of(slot):
            raise IdentityAssertionError(
                f"slot {slot} is labelled {db}, expected {source_db_of(slot)}"
            )
        by_source.setdefault(db, []).append(slot)

    for db, (lo, hi) in EXPECTED_CORPUS.items():
        got = sorted(by_source.get(db, []))
        if require_full and got != list(range(lo, hi + 1)):
            raise IdentityAssertionError(
                f"{db} must occupy global slots {lo}-{hi} exactly once; got "
                f"{len(got)} slots {got[:5]}{'...' if len(got) > 5 else ''}"
            )

    # one recorded value per slot
    multi = {}
    for r in rows:
        slot = int(r["global_subject_id"])
        val = int(r["recorded_subject_field"])
        multi.setdefault(slot, set()).add(val)
    multi = {s: sorted(v) for s, v in multi.items() if len(v) > 1}
    if multi:
        raise IdentityAssertionError(
            f"slots reporting more than one internal `subject` value: {multi}"
        )

    # the real injectivity requirement
    tuples = [(str(r["source_dataset"]), int(r["recorded_subject_field"])) for r in rows]
    tcounts = Counter(tuples)
    collisions = {t: c for t, c in tcounts.items() if c > 1}
    if collisions:
        raise IdentityAssertionError(
            "(source_database, recorded_subject) is not injective: "
            f"{collisions}"
        )

    return {
        "n_subjects": len(slots),
        "by_source_dataset": {k: len(v) for k, v in sorted(by_source.items())},
        "expected_total": EXPECTED_TOTAL,
        "identity_authority": ("DB9 archive slot; the in-file `subject` field is "
                               "provenance metadata only"),
        "source_recorded_tuples_injective": True,
        "equal_recorded_ids_across_sources_are_expected": True,
        "complete": not missing and len(slots) == EXPECTED_TOTAL,
    }
