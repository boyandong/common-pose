#!/usr/bin/env python
"""Freeze the confirmatory design and identify the untouched cohort.

Why this exists
---------------
The 22-subject run and the two 34-subject smoke runs were *result-producing*.
Every subject that appeared in them is now **development-exposed**: its
performance has been seen, so it can no longer serve as pristine confirmation.
The remaining subjects must be enumerated from evidence, not assumed from a
count, and their performance must not be inspected before the final frozen run.

This script does exactly three things, none of which evaluate a classifier:

1. recovers the **development-exposed** cohort by parsing the run logs (the
   authoritative record of which subjects entered a result-producing run);
2. intersects that with the **currently available** corpus to determine the
   **untouched confirmation cohort**;
3. writes the frozen design specification, including a primary
   model/normalisation choice made on **methodological reasoning only**.

It deliberately does not load a model, compute an accuracy, or rank anything.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_ROOT, "posture_decoder"))
sys.path.insert(0, os.path.join(_ROOT, "posture_decoder", "experiments"))
sys.path.insert(0, os.path.join(_ROOT, "representation"))

import db9_to_canonical16 as d2c  # noqa: E402
from db9.loader import load_recording  # noqa: E402
import confirmatory_policy as cp  # noqa: E402

EXERCISE_B_MAX_LABEL = 17


def source_db(n: int) -> str:
    return "DB1" if n <= 27 else ("DB2" if n <= 67 else "DB5")


def available_subjects(extracted: str) -> dict[int, str]:
    """Subjects with a complete, loadable Exercise-B file (integrity check only)."""
    ok: dict[int, str] = {}
    for d in glob.glob(os.path.join(extracted, "s_*_angles")):
        slot = int(os.path.basename(d).split("_")[1])
        for p in glob.glob(os.path.join(d, "*.mat")):
            if os.path.basename(p).startswith("._"):
                continue
            try:
                r = load_recording(p)
            except Exception:  # noqa: BLE001
                continue
            if int(r.restimulus.max()) == EXERCISE_B_MAX_LABEL:
                ok[slot] = os.path.basename(p)
    return dict(sorted(ok.items()))


def read_text(path: str) -> str:
    """Decode a run log regardless of how PowerShell wrote it.

    PowerShell 5.1's `*>` redirection emits **UTF-16LE**, not UTF-8.  Reading such
    a file as UTF-8 silently yields NUL-interleaved text in which no ASCII pattern
    matches -- which would make this script report "zero exposed subjects" and
    therefore claim the entire corpus was untouched.  That is the single most
    dangerous failure mode here, so the encoding is sniffed from the BOM and the
    result is sanity-checked rather than assumed.
    """
    raw = open(path, "rb").read()
    for bom, enc in ((b"\xff\xfe", "utf-16"), (b"\xfe\xff", "utf-16"),
                     (b"\xef\xbb\xbf", "utf-8-sig")):
        if raw.startswith(bom):
            return raw.decode(enc, errors="replace")
    if raw[:1] == b"\x00" or raw[1:2] == b"\x00":
        return raw.decode("utf-16-le", errors="replace")
    return raw.decode("utf-8", errors="replace")


def exposed_subjects(log_dir: str) -> tuple[set[int], dict[str, list[int]]]:
    """Subjects that entered a result-producing run, from the run logs."""
    exposed: set[int] = set()
    per_log: dict[str, list[int]] = {}
    for path in sorted(glob.glob(os.path.join(log_dir, "*.log"))):
        text = read_text(path)
        subs = sorted({int(m) for m in re.findall(r"\[ok\] s(\d+)", text)})
        if not subs:
            continue
        # A log only counts as result-producing if it actually reported metrics.
        produced = bool(re.search(r"(frame=|LOSO\s*=|acc(uracy)?\s*=)", text))
        per_log[os.path.basename(path)] = subs
        if produced:
            exposed |= set(subs)
    return exposed, per_log


METHOD_NOTE_MODEL = (
    "Chosen on methodological grounds only; NO accuracy figure entered this "
    "decision. Linear discriminant analysis with Ledoit-Wolf shrinkage "
    "(solver='lsqr', shrinkage='auto') is closed-form and deterministic -- no "
    "iteration, no random seed, and no hyperparameter to search. The analytic "
    "shrinkage estimator is the standard remedy for the small-n / "
    "many-features-per-class regime that 6 postures x 6 repetitions x N subjects "
    "creates, and it yields a probabilistic decision rule, which matches the "
    "question being asked ('is the posture identifiable from these kinematics') "
    "rather than 'how well can a flexible model fit'. The other four models "
    "(two nearest-centroid variants, logistic regression, random forest) are "
    "reported as secondary so that the conclusion does not rest on one "
    "inductive bias."
)

METHOD_NOTE_NORM = (
    "Chosen on methodological grounds only; NO accuracy figure entered this "
    "decision. Train-only z-scoring is used because the 16 canonical channels "
    "are heterogeneous in scale (thumb CMC and DIP flexion ranges differ "
    "several-fold) and DB9's calibration applies per-subject sensor gains, so a "
    "shared-covariance model is scale-sensitive. Statistics are fitted on TRAIN "
    "subjects only. Per-subject normalisation of test subjects is EXCLUDED by "
    "policy: it would require subject-specific calibration that a deployed "
    "decoder would not have. The unnormalised ('raw') variant is retained as a "
    "reported control."
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--extracted", required=True)
    ap.add_argument("--logs", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    avail = available_subjects(args.extracted)
    exposed, per_log = exposed_subjects(args.logs)
    available_set = set(avail)
    untouched = sorted(available_set - exposed)
    exposed_available = sorted(available_set & exposed)

    print("=" * 78)
    print("COHORT SEPARATION (acquisition / integrity state only -- no accuracy computed)")
    print("=" * 78)
    print(f"  logs parsed for result-producing runs:")
    for name, subs in per_log.items():
        print(f"    {name:<24} {len(subs)} subjects")
    print()
    print(f"  development-EXPOSED (seen in a result-producing run): {len(exposed)}")
    print(f"    {sorted(exposed)}")
    print(f"  currently AVAILABLE and verified as Exercise B: {len(avail)}")
    print(f"    by source: "
          f"{ {db: len([s for s in avail if source_db(s) == db]) for db in ('DB1','DB2','DB5')} }")
    print(f"  UNTOUCHED confirmation cohort (available minus exposed): {len(untouched)}")
    print(f"    {untouched}")
    print(f"    by source: "
          f"{ {db: len([s for s in untouched if source_db(s) == db]) for db in ('DB1','DB2','DB5')} }")
    print()
    expected_untouched = [n for n in range(28, 78)]
    print(f"  research lead's expectation: all 40 DB2 + the 3 unseen DB5 = 43")
    print(f"  DB2 subjects in the untouched set: {len([s for s in untouched if 28 <= s <= 67])}/40")
    print(f"  DB5 subjects in the untouched set: "
          f"{sorted(s for s in untouched if s >= 68)} "
          f"(expected 75, 76, 77 once acquired)")
    still_missing = [n for n in range(1, 78) if n not in available_set]
    print(f"  not yet acquired: {len(still_missing)} -> DB2="
          f"{len([n for n in still_missing if 28 <= n <= 67])}, DB5="
          f"{len([n for n in still_missing if n >= 68])}, DB1="
          f"{len([n for n in still_missing if n <= 27])}")

    spec = {
        "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "FROZEN -- design decisions locked before the confirmatory run",
        "gate": (
            "DO NOT start the 77-subject replication until the independent Work "
            "code audit has returned. No further partial-data, smoke, accuracy, "
            "LOSO, model-comparison, normalisation-comparison or ablation run may "
            "be executed while acquisition is incomplete."
        ),

        "cohorts": {
            "derivation": (
                "MACHINE-DERIVED, never hand-edited. Re-run "
                "tools/freeze_confirmatory_spec.py at the end of acquisition to "
                "refresh the cohort lists; the design block below does not change. "
                "The exposed set is parsed from the result-producing run logs and "
                "the untouched set is (available Exercise-B subjects) minus "
                "(exposed). Reading the logs requires BOM-aware decoding: PowerShell "
                "5.1's '*>' redirection writes UTF-16LE, and a UTF-8 read silently "
                "matches nothing, which would report every subject as untouched."
            ),
            "development_exposed": {
                "n": len(exposed),
                "subjects": sorted(exposed),
                "evidence": {k: v for k, v in per_log.items()},
                "note": ("these subjects entered a result-producing run "
                         "(the 22-subject exploratory run and/or the 34-subject "
                         "smoke runs); their performance has been observed and "
                         "they can no longer serve as pristine confirmation"),
            },
            "untouched_confirmation": {
                "n": len(untouched),
                "subjects": untouched,
                "by_source_dataset": {
                    db: [s for s in untouched if source_db(s) == db]
                    for db in ("DB1", "DB2", "DB5")
                },
                "expected_final_n": 43,
                "note": ("never entered any result-producing run and must not be "
                         "inspected for classification performance before the "
                         "final frozen run; this cohort is the strongest "
                         "confirmatory evidence"),
            },
            "currently_available": {
                "n": len(avail),
                "subjects": sorted(avail),
                "not_yet_acquired": still_missing,
            },
        },

        "frozen_design": {
            "class_vocabulary": {
                "primary": [1, 2, 3, 4, 6, 7],
                "primary_names": ["Thumb up",
                                  "Extension of index and middle, flexion of the others",
                                  "Flexion of ring and little finger, extension of the others",
                                  "Thumb opposing base of little finger",
                                  "Fingers flexed together in fist",
                                  "Pointing index"],
                "negative_control": [5, 8],
                "excluded": "exercise-C object grasps and exercise-B wrist/forearm movements",
            },
            "representations": {
                "canonical16": {"ndim": 16, "names": list(d2c.canonical16_names()),
                                "role": "PRIMARY"},
                "canonical15_noThumbAA": {
                    "ndim": 15, "names": list(d2c.canonical15_noThumbAA_names()),
                    "dropped": list(d2c.CANONICAL15_NOTHUMBAA_DROPPED),
                    "role": "pre-registered robustness control (thumb-axis uncertainty)"},
                "canonical12_noDIP": {
                    "ndim": 12, "names": list(d2c.canonical12_noDIP_names()),
                    "dropped": list(d2c.CANONICAL12_NODIP_DROPPED),
                    "role": "pre-registered robustness control (DIP reliability)"},
                "policy": ("all three reported side by side; canonical16 is primary; "
                           "none is used to select or tune the primary model"),
                "frozen_sign_transformation": dict(d2c.FROZEN_DB9_SIGN),
            },
            "representative_posture_extraction": {
                "rule": ("split each labelled repetition into thirds; take the "
                         "MEDIAN of the central third"),
                "central_fraction": 1.0 / 3.0,
                "min_samples_per_repetition": 30,
                "unit_of_analysis": "subject x movement x repetition",
                "tuning": "segmentation boundaries are never tuned per class or per accuracy",
            },
            "classifiers": {
                "primary": "lda",
                "primary_config": "LinearDiscriminantAnalysis(solver='lsqr', shrinkage='auto')",
                "secondary_reported": ["nearest_centroid_euclidean",
                                       "nearest_centroid_mahalanobis",
                                       "logreg", "random_forest"],
                "random_forest_config": "n_estimators=500, random_state=20260101",
                "logreg_config": "max_iter=5000, C=1.0, random_state=20260101",
                "tuning": "no hyperparameter search of any kind",
            },
            "normalization": {
                "primary": "train_only_zscore",
                "reported_control": "raw",
                "excluded_by_policy": ("per-subject normalisation of test subjects "
                                       "(requires subject-specific calibration a "
                                       "deployed decoder would not have)"),
            },
            "drift_correction": {
                "method": ("per-subject drift trajectory estimated from REST blocks "
                           "only (labelled-free), median rest posture per block, "
                           "offsets relative to the first block, linearly "
                           "interpolated over normalised session time, subtracted"),
                "uses_test_labels": False,
                "role": "falsification control; the primary result is reported uncorrected",
            },
            "metrics": {
                "primary_confirmatory": "accuracy on the untouched cohort",
                "companion": "balanced accuracy (classes are balanced by design)",
                "also_reported": ["macro F1", "per-class recall", "confusion matrix",
                                  "drift-only LOSO", "drift-corrected LOSO",
                                  "label-permutation control"],
                "chance": 1.0 / 6,
                "majority_class_baseline": "reported alongside every accuracy",
            },
        },

        "pre_registration": {
            "primary_model": "lda",
            "primary_normalization": "train_only_zscore",
            "justification_model": METHOD_NOTE_MODEL,
            "justification_normalization": METHOD_NOTE_NORM,
            "decision_rule_used": (
                "option A of the research lead's instruction: one primary choice "
                "pre-registered on methodological reasoning, because no primary "
                "model or normalisation had been formally frozen before the smoke "
                "runs. All other combinations are reported without choosing a "
                "post-hoc winner, and no accuracy figure from the smoke runs "
                "entered this choice."
            ),
        },

        "final_evaluation_plan": {
            "1_full_77_loso": "descriptive / full-corpus replication",
            "2_untouched_confirmation": {
                "a_train_exposed_test_untouched": (
                    "PRIMARY CONFIRMATORY: train on the development-exposed cohort, "
                    "evaluate on the untouched cohort. The untouched subjects are "
                    "never in training and never inspected beforehand."),
                "b_loso_within_untouched": (
                    "secondary confirmatory: leave-one-subject-out restricted to the "
                    "untouched cohort"),
                "status": "strongest confirmatory evidence",
            },
            "3_source_breakdowns": "DB1 / DB2 / DB5 separately",
            "4_source_held_out": "train on two source databases, test on the third",
            "5_representation_controls": "canonical16 / canonical15_noThumbAA / canonical12_noDIP",
        },
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2)
    print(f"\n[frozen] specification written to {args.out}")

    # ---- item 8: the three cohort sets, machine-derived -------------------
    # `integrity_only_touched` is every subject whose file was opened for a
    # file/schema/integrity check. That is NOT outcome exposure and is recorded
    # separately so the distinction cannot be blurred later.
    cohort_path = os.path.join(_ROOT, cp.COHORT_RECORD_PATH.replace("/", os.sep))
    rec = cp.write_cohort_record(
        cohort_path,
        development_exposed=sorted(exposed),
        outcome_unseen=untouched,
        integrity_only_touched=sorted(available_set),
        evidence={
            "result_producing_logs": {k: v for k, v in per_log.items()},
            "n_available": len(available_set),
            "n_exposed": len(exposed),
            "n_outcome_unseen": len(untouched),
            "derivation_tool": "posture_decoder/tools/freeze_confirmatory_spec.py",
        },
    )
    print(f"[cohorts] record written to {cohort_path}")
    print(f"  development_exposed    : {len(rec['development_exposed'])}")
    print(f"  outcome_unseen         : {len(rec['outcome_unseen'])}")
    print(f"  integrity_only_touched : {len(rec['integrity_only_touched'])} "
          f"(NOT outcome exposure)")

    print(f"[gate]   do NOT run the replication until the independent Work code audit returns")
    return 0


if __name__ == "__main__":
    sys.exit(main())
