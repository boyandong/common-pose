#!/usr/bin/env python
"""Generate the confirmatory-run provenance manifest, and finalise it afterwards.

The project is not a Git repository, so file-level cryptographic provenance is
the reproducibility record.  Two modes:

``--mode prepare``  (run BEFORE the experiment)
    Records the exact command, interpreter and package versions, the frozen
    spec / schema / code-file hashes, the 77 input files with their sizes and
    SHA-256, the subject -> source mapping, and the frozen design constants.
    Refuses to emit a manifest unless the corpus passes the hard identity
    assertions, so a manifest can never describe an incomplete corpus.

``--mode finalize``  (run AFTER the experiment)
    Appends SHA-256 for every result artifact, so the numbers in the report can
    be tied to specific bytes.

Nothing here evaluates a model.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_ROOT, "posture_decoder"))
sys.path.insert(0, os.path.join(_ROOT, "posture_decoder", "experiments"))
sys.path.insert(0, os.path.join(_ROOT, "representation"))

import confirmatory_policy as cp  # noqa: E402
import db9_to_canonical16 as d2c  # noqa: E402
from db9.loader import (  # noqa: E402
    db9_exercise_index, discover_unpacked, load_recording, resolve_subject,
    source_db_for_subject,
)

#: Every code file the confirmatory pipeline depends on.
CODE_FILES = (
    "representation/db9_to_canonical16.py",
    "representation/canonical_hand.py",
    "posture_decoder/db9/loader.py",
    "posture_decoder/db9/labels.py",
    "posture_decoder/db9/canonical.py",
    "posture_decoder/db9/quality.py",
    "posture_decoder/experiments/confirmatory_policy.py",
    "posture_decoder/experiments/run_posture16.py",
    "posture_decoder/experiments/run_full_db9.py",
    "posture_decoder/experiments/build_dataset.py",
    "posture_decoder/tools/fetch_db9_member.py",
    "posture_decoder/tools/freeze_confirmatory_spec.py",
)

FROZEN_SPEC = "docs/FROZEN_CONFIRMATORY_SPEC.json"
SCHEMA = "representation/db9_canonical16_schema.json"
COHORTS = cp.COHORT_RECORD_PATH


def sha256(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def package_versions() -> dict[str, str]:
    import importlib

    out = {}
    for name in ("numpy", "scipy", "sklearn", "matplotlib", "h5py"):
        try:
            mod = importlib.import_module(name)
            out[name] = getattr(mod, "__version__", "unknown")
        except Exception:  # noqa: BLE001
            out[name] = "NOT INSTALLED"
    return out


def corpus_rows(extracted: str) -> list[dict]:
    rows = []
    for slot, path in discover_unpacked(extracted):
        rec = load_recording(path)
        subject, note = resolve_subject(slot, rec.subject, path)
        try:
            ex = db9_exercise_index(rec, subject)
        except Exception:  # noqa: BLE001
            continue
        if ex != 1:
            continue
        rows.append({
            "global_subject_id": subject,
            "source_dataset": source_db_for_subject(subject),
            "recorded_subject_field": int(rec.subject),
            "file": os.path.abspath(path),
            "file_bytes": os.path.getsize(path),
            "file_sha256": sha256(path),
            "samples": int(rec.n_samples),
            "identity_note": note,
        })
    return sorted(rows, key=lambda r: r["global_subject_id"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=("prepare", "finalize"), required=True)
    ap.add_argument("--extracted", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--data-dir", default="")
    ap.add_argument("--fig-dir", default="")
    ap.add_argument("--command", default="", help="exact command that will be/was run")
    args = ap.parse_args()

    p = lambda rel: os.path.join(_ROOT, rel)  # noqa: E731

    if args.mode == "prepare":
        rows = corpus_rows(args.extracted)
        identity = cp.assert_corpus_identity(rows, require_full=True)

        spec = json.load(open(p(FROZEN_SPEC), encoding="utf-8"))
        cohorts = {}
        if os.path.exists(p(COHORTS)):
            cohorts = json.load(open(p(COHORTS), encoding="utf-8"))

        # The primary confirmatory arm is defined by the cohort record, so the
        # manifest proves the partition actually covers this corpus BEFORE the
        # run rather than describing it afterwards.
        arms: dict = {
            "rule": ("A is the primary number. B and C are reported alongside it "
                     "and may never be substituted for it."),
        }
        if cohorts:
            part = cp.assert_cohort_partition(
                cohorts["development_exposed"], cohorts["outcome_unseen"],
                [r["global_subject_id"] for r in rows],
            )
            arms["A_primary_confirmatory"] = {
                "design_item": "2_untouched_confirmation.a_train_exposed_test_untouched",
                "train_on": "development_exposed",
                "test_on": "outcome_unseen",
                "n_train_subjects": part["n_exposed"],
                "n_test_subjects": part["n_unseen"],
                "test_evaluations": 1,
                "cohort_record": COHORTS,
                "partition_source": ("loaded from the cohort record at run time by "
                                     "confirmatory_policy.load_cohort_record; never "
                                     "hard-coded in the driver"),
                "strongest_evidence": True,
            }
            arms["B_full_77_loso_descriptive"] = {
                "design_item": "1_full_77_loso",
                "tier": ("descriptive only -- the development-exposed subjects are "
                         "inside this evaluation"),
            }
            arms["C_secondary_confirmatory"] = {
                "design_item": "2_untouched_confirmation.b_loso_within_untouched",
                "tier": ("LOSO within the outcome-unseen cohort; cohort peers are in "
                         "every training fold, so this is not an untouched external "
                         "holdout"),
            }
        else:
            raise SystemExit(
                f"cohort record {COHORTS} is missing; the primary confirmatory arm "
                "is undefined and this manifest must not be prepared without it"
            )

        manifest = {
            "manifest_version": 1,
            "mode": "prepare",
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "exact_command": args.command or "(not supplied)",
            "interpreter": {
                "python": sys.version,
                "executable": sys.executable,
                "platform": platform.platform(),
            },
            "package_versions": package_versions(),
            "hashes": {
                "frozen_spec_sha256": sha256(p(FROZEN_SPEC)),
                "db9_canonical16_schema_sha256": sha256(p(SCHEMA)),
                "cohort_record_sha256": sha256(p(COHORTS)),
                "code_files": {
                    rel: sha256(p(rel)) for rel in CODE_FILES
                },
            },
            "primary_model": {
                "model": cp.PRIMARY_MODEL,
                "config": cp.PRIMARY_MODEL_CONFIG,
                "normalization": cp.PRIMARY_NORMALIZATION,
                "representation": cp.PRIMARY_REPRESENTATION,
                "selection_rule": ("fixed by pre-registration; a secondary "
                                   "configuration scoring higher may not displace it"),
            },
            "confirmatory_arms": arms,
            "class_vocabulary": spec["frozen_design"]["class_vocabulary"],
            "representations": spec["frozen_design"]["representations"],
            "extraction_rule": spec["frozen_design"]["representative_posture_extraction"],
            "drift_correction": spec["frozen_design"]["drift_correction"],
            "normalization": spec["frozen_design"]["normalization"],
            "metrics": spec["frozen_design"]["metrics"],
            "frozen_sign_transformation": dict(d2c.FROZEN_DB9_SIGN),
            "cohort_definitions": cohorts,
            "corpus": {
                "n_subjects": len(rows),
                "identity_assertions": identity,
                "subject_source_mapping": {
                    str(r["global_subject_id"]): r["source_dataset"] for r in rows
                },
                "inputs": rows,
            },
            "result_artifacts": None,
        }
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)
        print(f"[manifest] PREPARE -> {args.out}")
        print(f"  subjects            : {manifest['corpus']['n_subjects']} "
              f"{identity['by_source_dataset']}")
        print(f"  identity assertions : PASSED (complete={identity['complete']})")
        print(f"  frozen spec sha256  : {manifest['hashes']['frozen_spec_sha256']}")
        print(f"  schema sha256       : {manifest['hashes']['db9_canonical16_schema_sha256']}")
        print(f"  code files hashed   : {sum(1 for v in manifest['hashes']['code_files'].values() if v)}"
              f"/{len(CODE_FILES)}")
        a = manifest["confirmatory_arms"]["A_primary_confirmatory"]
        print(f"  PRIMARY arm (A)     : train {a['n_train_subjects']} "
              f"development-exposed -> test {a['n_test_subjects']} outcome-unseen "
              f"(one shot)")
        return 0

    # ---- finalize ---------------------------------------------------------
    manifest = json.load(open(args.out, encoding="utf-8"))
    artifacts: dict[str, dict] = {}
    for d, label in ((args.data_dir, "data"), (args.fig_dir, "figures")):
        if not d or not os.path.isdir(d):
            continue
        for path in sorted(glob.glob(os.path.join(d, "**", "*"), recursive=True)):
            if os.path.isfile(path):
                artifacts[f"{label}/{os.path.relpath(path, d)}"] = {
                    "bytes": os.path.getsize(path),
                    "sha256": sha256(path),
                }
    manifest["result_artifacts"] = artifacts
    manifest["finalized_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    manifest["mode"] = "prepare+finalize"
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"[manifest] FINALIZE -> {args.out}: {len(artifacts)} artifact(s) hashed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
