"""Deterministic, idempotent build of the curated public tree.

Why this exists
---------------
The curated tree is assembled by copying selected files out of a read-only historical
research workspace. Doing that with ad-hoc shell commands produced three defects during
this build, all of which this script is designed to prevent:

1. an incremental build left files in an unknown state after a partial fix;
2. rewriting files through a line-ending-normalising writer doubled their CR bytes;
3. decoding a non-UTF-8 artifact as UTF-8 silently inserted U+FFFD replacement
   characters.

So the build is one pass from pristine sources, with transformations applied in memory
and written once, preserving the original encoding. Running it twice produces
byte-identical output.

Guarantees
----------
* **The source workspace is never written to.** Only reads are performed on it, and its
  hashes are re-verified at the end of every build; a drift is a build failure.
* Every curated file's source SHA-256 and target SHA-256 are recorded in
  ``provenance/CURATION_MANIFEST.json``, so "this is the code that produced that
  artifact" is checkable rather than asserted.
* A file that cannot be decoded cleanly is reported and skipped, never mangled.

Usage:
    python scripts/build_curated_tree.py --verify   # report, write nothing
    python scripts/build_curated_tree.py --apply    # write the curated tree
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKSPACE = REPO.parent / "emg2pose_handstate"

# --------------------------------------------------------------------------- #
# Substitution table
#
# Paths are replaced by role-named placeholders. The point is not cosmetic: a local
# absolute path leaks a username and an environment layout, and it makes an artifact
# non-portable. Longest patterns are applied first so a directory prefix is rewritten
# before a rule that would only match part of it.
# --------------------------------------------------------------------------- #

RAW_RULES: list[tuple[str, str]] = [
    (r"C:\Users\董伯言\Desktop\fingers\emg2pose_handstate", "<WORKSPACE_ROOT>"),
    (r"C:\Users\董伯言\Desktop\fingers", "<FINGERS_ROOT>"),
    (r"C:\Users\董伯言\AppData\Local\Programs\Microsoft VS Code", "<VSCODE_DIR>"),
    (r"C:\Users\董伯言\.conda", "<CONDA_ROOT>"),
    (r"D:\Anaconda3", "<ANACONDA_ROOT>"),
    (r"C:\Anaconda3", "<ANACONDA_ROOT>"),
    (r"C:\emg2pose-venv", "<EMG2POSE_VENV>"),
    (r"C:\emg2pose\data\ninapro_db9", "<DB9_DATA_ROOT>"),
    (r"C:\emg2pose\data", "<DATA_ROOT>"),
    (r"C:\emg2pose\docs", "<DOCS_ROOT>"),
    (r"C:\emg2pose\representation", "<REPRESENTATION_ROOT>"),
    (r"C:\emg2pose\baseline", "<BASELINE_ROOT>"),
    (r"C:\emg2pose\checkpoints", "<CHECKPOINTS_ROOT>"),
    (r"C:\emg2pose\inference", "<INFERENCE_ROOT>"),
    (r"C:\emg2pose", "<PROJECT_ROOT>"),
    (r"C:\Users\董伯言", "<USER_PROFILE>"),
    ("/root/emg2pose", "<PROJECT_ROOT>"),
    ("/root/", "<HOME>/"),
    ("/home/董伯言", "<USER_PROFILE>"),
]

#: Human-readable role of each placeholder, so the manifest can describe what was
#: replaced WITHOUT republishing the paths it replaced. A provenance record that leaks
#: the author's username would defeat the sanitisation it is documenting.
PLACEHOLDER_ROLE: dict[str, str] = {
    "<WORKSPACE_ROOT>": "historical research workspace root for this project",
    "<FINGERS_ROOT>": "parent directory holding the sibling research workspaces",
    "<VSCODE_DIR>": "local editor installation directory",
    "<ANACONDA_ROOT>": "local Python distribution root",
    "<CONDA_ROOT>": "local conda directory",
    "<EMG2POSE_VENV>": "local virtual environment for the emg2pose baseline",
    "<DB9_DATA_ROOT>": "extracted Ninapro DB9 release root",
    "<DATA_ROOT>": "project data root",
    "<DOCS_ROOT>": "project documentation root",
    "<REPRESENTATION_ROOT>": "representation-pipeline source root",
    "<BASELINE_ROOT>": "upstream baseline checkout root",
    "<CHECKPOINTS_ROOT>": "model checkpoint root",
    "<INFERENCE_ROOT>": "inference wrapper root",
    "<PROJECT_ROOT>": "project root as seen by the historical tooling",
    "<USER_PROFILE>": "user home directory",
    "<HOME>/": "POSIX home directory",
}

FORBIDDEN_AFTER: list[tuple[str, str]] = [
    ("windows_user_profile", re.escape("C:" + "\\" + "Users")),
    # A drive letter is only a leak when a real path segment follows it. `C:\...` and
    # `C:\<name>` are Windows path *grammar* examples in prose and match the shape
    # without naming anything on a machine. A preceding `<` marks a placeholder.
    ("windows_drive_path", r"(?<![A-Za-z0-9_<])" + "[A-Za-z]:" + r"\\+(?![.\\])"),
    ("ascii_junction", re.escape("C:" + "\\" + "emg2pose")),
    ("posix_root_home", r"(?<!<)/root/"),
]


def variants(raw: str) -> list[str]:
    """Every escaping of a raw path that occurs in the curated files.

    A path containing non-ASCII characters can appear as literal UTF-8, as a JSON string
    with doubled backslashes, as a JSON string that *also* writes the non-ASCII
    characters as ``\\uXXXX`` escapes (which is what ``json.dumps`` does by default), or
    with forward slashes. All four occur in this project's artifacts, and missing any of
    them means the rule silently does nothing for the file that uses it.
    """
    forms: set[str] = set()
    for base in (raw, raw.replace("\\", "\\\\"), raw.replace("\\", "\\\\\\\\")):
        forms.add(base)
        if any(ord(c) > 127 for c in base):
            forms.add("".join(c if ord(c) < 128 else f"\\u{ord(c):04x}" for c in base))
    forms.add(raw.replace("\\", "/"))
    return sorted(forms, key=len, reverse=True)


RULES: list[tuple[str, str, str]] = []
_seen_rules: set[str] = set()
for _raw, _ph in RAW_RULES:
    for _v in variants(_raw):
        if _v not in _seen_rules:
            _seen_rules.add(_v)
            # The third element is a LABEL used in the manifest. It is the placeholder,
            # never the raw path: the manifest is a published artifact.
            RULES.append((_v, _ph, _ph))
RULES.sort(key=lambda t: -len(t[0]))


def sanitize(text: str) -> tuple[str, list[str], int]:
    rules_hit: list[str] = []
    total = 0
    for search, repl, label in RULES:
        n = text.count(search)
        if n:
            text = text.replace(search, repl)
            total += n
            if label not in rules_hit:
                rules_hit.append(label)
    return text, rules_hit, total


def decode(path: Path) -> tuple[str, str]:
    """Decode preserving the original encoding.

    An unknown encoding is an error, not something to paper over with
    ``errors="replace"``: replacement characters are silent corruption of a scientific
    artifact.
    """
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16"), "utf-16"
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    return raw.decode("utf-8"), "utf-8"


# --------------------------------------------------------------------------- #
# The curation plan: (source relative to WORKSPACE, target relative to REPO)
# --------------------------------------------------------------------------- #

DB9_FORENSIC = "db9_channel_forensic_v2"
DB9_COORD = "pose_coordinate_audit"
ADM_V1 = "dataset_admission_audit_v1"
ADM_V0 = "pose_api_dataset_admission"
POSTURE = "posture_decoder"
KINMUS = "kinmus_task_observability"
BRIDGE = "bridge_audit"

PLAN: list[tuple[str, str]] = []


def add(src_dir: str, dst_dir: str, names: list[str]) -> None:
    for n in names:
        PLAN.append((f"{src_dir}/{n}", f"{dst_dir}/{n}"))


# --- DB9 channel forensic: the frozen physical audit --------------------------
add(DB9_FORENSIC, "audits/db9/channel_forensic", [
    "README.md", "FORENSIC_PLAN.md", "PLAN_SHA256.txt", "SEGMENTATION_VALIDATION.md",
    "DB9_CHANNEL_LEDGER.csv", "FLAGGED_CHANNEL_FORENSICS.md", "SENSOR11_IMPACT.md",
    "DIP_HANDSIZE_ANALYSIS.md", "BUGFIX_LOG.md", "DB9_FORENSIC_DECISION.md",
])
add(f"{DB9_FORENSIC}/artifacts", "audits/db9/channel_forensic/artifacts", [
    "DECISION.json", "FORENSIC_CORE.json", "POSTURE_UTILITY.json",
    "POSTURE_UTILITY_POSTURE_ONLY.json", "SEGMENTATION_VALIDATION.json", "VERDICTS.json",
    "TRANSFORM_SOLVER_S1E2.json", "RESIDUAL_MATRIX_S1E2.json",
])
add(f"{DB9_FORENSIC}/docs", "audits/db9/channel_forensic/docs", ["DB9_instructions.txt"])
add(f"{DB9_FORENSIC}/logs", "audits/db9/channel_forensic/logs", [
    "03_verdicts.log", "04b_utility_posture_only.log", "05_decision.log",
    "99_fact_check.log",
])
add(f"{DB9_FORENSIC}", "audits/db9/trusted_pose", [
    "TRUSTED_DB9_POSE_v1.json", "TRUSTED_SUBSET_SHA256.txt",
])

# --- DB9 coordinate audit ----------------------------------------------------
add(DB9_COORD, "audits/db9/coordinate_audit", [
    "POSE_COORDINATE_AUDIT_REPORT.md", "POSE_COORDINATE_AUDIT_HANDOVER.md",
    "POSE_COORDINATE_AUDIT_PLAN.json", "POSE_COORDINATE_AUDIT_PLAN.sha256",
    "CANONICAL16_CODE_PROVENANCE.md", "OFFICIAL_SOURCE_REFERENCES.md",
    "LARGE_OFFSET_FORENSICS.md", "SOURCE_DEFINITION_AUDIT.md",
])
add(DB9_COORD, "audits/db9/coordinate_audit/artifacts", [
    "COMMON_POSE_API_VERDICT.json", "DIMENSION_CONFIDENCE_CLASSIFICATION.json",
    "SOURCE_DEFINITION_AUDIT.json", "PHYSICAL_ANCHOR_AUDIT.json",
    "MATCHED_SEMANTIC_COORDINATE_AUDIT.json", "DB9_SOURCE_CALIBRATION_AUDIT.json",
    "CANONICAL16_EQUIVALENCE_MATRIX.csv", "CANONICAL16_EQUIVALENCE_MATRIX.json",
    "BROKEN_CHANNEL_CONTRIBUTION.json", "SYNTHETIC_ROUNDTRIP_RESULTS.json",
    "EMG2POSE_SESSION_CALIBRATION_AUDIT.json",
    "GEOMETRY_SHAPE_LOCATION_DECOMPOSITION.json", "LARGE_OFFSET_FORENSICS.json",
])

# --- dataset admission -------------------------------------------------------
add(ADM_V1, "audits/dataset_admission", [
    "README.md", "ADMISSION_DECISION.md", "AUDIT_PLAN.md", "PLAN_SHA256.txt",
    "BUGFIX_LOG.md", "SOURCE_PROVENANCE.md", "SHARED10_PROVENANCE_AUDIT.md",
    "SCHEMA_AUDIT.md", "PHYSICAL_QC.md", "LABEL_AUDIT.md", "SYNC_AUDIT.md",
    "COMMON_API_MAPPING_MATRIX.csv", "COORDINATE_LEDGER.csv", "DATASET_MANIFEST.csv",
    "LABEL_ADMISSION_MATRIX.csv", "kine_global_subject_map.csv",
])
add(f"{ADM_V1}/artifacts", "audits/dataset_admission/artifacts", [
    "ADMISSION_DECISION.json", "ARTIFACT_MANIFEST.json", "COMMON_API.json",
    "COORDINATE_LEDGER.json", "SCHEMA_AUDIT.json", "SHARED10_PROVENANCE.json",
    "SOURCE_FREEZE.json", "LABEL_AUDIT.json", "KINMUS_SPECIAL.json",
    "KINEADL_SPECIAL.json", "MYOKI_SPECIAL.json",
])
add(f"{ADM_V1}/logs", "audits/dataset_admission/logs", ["_fc_stdout.txt"])
PLAN.append(
    (
        f"{ADM_V1}/logs/_fc_stdout.txt",
        "audits/dataset_admission/logs/fact_check_stdout.txt",
    )
)
PLAN = [p for p in PLAN if p[1] != "audits/dataset_admission/logs/_fc_stdout.txt"]
add(ADM_V0, "audits/dataset_admission/pose_api_admission", [
    "COMMON_POSE_API_ADMISSION_CONTRACT_V0.md", "COMMON_POSE_API_REQUIREMENTS.json",
    "DATASET_ACCESS_AND_LICENSE.json", "DATASET_INDEPENDENCE_MATRIX.json",
    "DATASET_TASK_STRUCTURE.json", "EXTERNAL_TEST_FEASIBILITY.json",
    "FIRST_POC_DATASET_DECISION.json", "HUST_SOURCE_AUDIT.json",
    "HUST_QUALITY_AUDIT.json", "HUST_PHYSICAL_ANCHOR_AUDIT.json",
    "KINE_ADL_SOURCE_AUDIT.json", "KINE_ADL_QUALITY_AUDIT.json",
    "KINE_ADL_PHYSICAL_ANCHOR_AUDIT.json", "KIN_MUS_SOURCE_AUDIT.json",
    "KIN_MUS_QUALITY_AUDIT.json", "KIN_MUS_PHYSICAL_ANCHOR_AUDIT.json",
    "NEXT_POC_EXPERIMENT_PLAN.md", "OFFICIAL_SOURCE_REFERENCES.md",
    "POSE_API_DOF_MAPPING_MATRIX.csv", "POSE_API_DOF_MAPPING_MATRIX.json",
    "ANGLE_ORIGIN_AND_CALIBRATION_AUDIT.json", "DATASET_ADMISSION_REPORT.md",
    "DATASET_ADMISSION_HANDOVER.md", "DATASET_ADMISSION_PLAN.json",
    "DATASET_ADMISSION_PLAN.sha256",
])

# --- KIN-MUS task-phase observability ---------------------------------------
add(KINMUS, "experiments/observability/kinmus_phase", [
    "ARTIFACT_MANIFEST.json", "KINMUS_TASK_OBSERVABILITY_DECISION.json",
    "KINMUS_TASK_OBSERVABILITY_PLAN.json", "KINMUS_TASK_OBSERVABILITY_REPORT.md",
    "KINMUS_TASK_OBSERVABILITY_HANDOVER.md", "KINMUS_PHASE_COUNTS.json",
    "KINMUS_SINGLE_FRAME_RESULTS.json", "KINMUS_TRAJECTORY_RESULTS.json",
    "KINMUS_VELOCITY_RESULTS.json", "KINMUS_BOUNDARY_ANALYSIS.json",
    "KINMUS_DIRECTIONAL_ANALYSIS.json", "KINMUS_OBSERVABILITY_NULL_CONTROL.json",
    "KINMUS_SUBJECT_STABILITY.json", "KINMUS_PHASE_POSE_GEOMETRY.json",
    "KINMUS_PHASE_VELOCITY_GEOMETRY.json", "KINMUS_FULL18_DIAGNOSTIC.json",
    "KINMUS_OBSERVABILITY_SOURCE_PROVENANCE.json",
])
add(f"{KINMUS}/results", "experiments/observability/kinmus_phase/results", [
    "matched_subset.json", "real_results_cache.json",
])
add(f"{KINMUS}/tools", "experiments/observability/kinmus_phase/tools", [
    "obs_common.py", "obs_plan.py", "freeze_plan.py", "build_features.py",
    "build_cv.py", "build_matched.py", "build_geometry.py", "build_directional.py",
    "build_phase_counts.py", "build_post.py", "build_provenance.py",
    "build_decision.py", "build_report.py", "build_manifest.py", "build_figures.py",
    "kinmus_task_observability_fact_check.py",
])

# --- bridge audit ------------------------------------------------------------
add(BRIDGE, "experiments/bridge", [
    "_common.py", "decoder.py", "domain_depth.py", "run_bridge_audit.py",
    "visual_check.py", "SESSION5_BRIDGE_AUDIT_REPORT.md", "SESSION5_HANDOVER.md",
])

# --- core docs ---------------------------------------------------------------
add("docs", "docs", [
    "CANONICAL16_CONTRACT.md", "joint_angle_definition.md", "DB9_CANONICAL16_MAPPING.md",
    "DB9_EMG2POSE_ZERO_COMPATIBILITY.json", "EMG2POSE_DATASET_REFERENCE.md",
    "FROZEN_CONFIRMATORY_SPEC.json", "CONFIRMATORY_RESULTS.md",
    "CONFIRMATORY_RUN_MANIFEST.json", "CONFIRMATORY_COHORTS.json",
    "CORPUS_INTEGRITY.json", "CORPUS_GATE.json", "DB9_FILE_AUDIT.json",
    "REPETITION_AUDIT.json", "REMEDIATION_REPORT.md", "joint_reference_table.md",
    "joint_reference_table.json", "canonical16_real_data_evidence.json",
    "canonical_emg2pose_verification.json", "smoke_test_evidence.json",
    "SERVER_ACQUISITION_RUNBOOK.md", "DATASET_ACCESS_DECISION.md",
])

# --- DB9 posture task: the frozen result ------------------------------------
PLAN += [
    ("data/db9_posture16/results.json",
     "experiments/db9_posture/results/posture16_results.json"),
    ("data/db9_posture16/full_db9_results.json",
     "experiments/db9_posture/results/full_db9_results.json"),
]

# --- DB9 posture task: the carried-over research pipeline --------------------
# Kept under `_db9_pipeline/` rather than `db9/`, because `adapters/db9.py` is the
# adapter module and a sibling `db9/` package would collide with it in the import
# namespace (`common_pose.adapters.db9` cannot be both).
add(f"{POSTURE}/db9", "src/common_pose/adapters/_db9_pipeline", [
    "canonical.py", "labels.py", "loader.py", "quality.py", "__init__.py",
])
add(f"{POSTURE}/experiments", "src/common_pose/adapters/_db9_pipeline/experiments", [
    "build_dataset.py", "run_baseline.py", "run_posture16.py", "run_full_db9.py",
    "confirmatory_policy.py", "confidence_report.py", "diagnose_drift.py",
    "diagnose_posture16.py", "__init__.py",
])
add(f"{POSTURE}/tools", "src/common_pose/adapters/_db9_pipeline/tools", [
    "fetch_db9.py", "fetch_db9.ps1", "unpack_db9.py", "inspect_db9.py",
    "verify_canonical_emg2pose.py", "verify_corpus_gate.py",
    "verify_corpus_integrity.py", "audit_db9_files.py", "audit_repetitions.py",
    "check_zero_pose_compatibility.py", "freeze_confirmatory_spec.py",
    "make_confirmatory_manifest.py", "resolve_thumb_axis.py",
    "thumb_web_sign_test.py", "thumb_zero_alignment.py",
])
add(POSTURE, "src/common_pose/adapters/_db9_pipeline", ["README.md", "report.md"])

# --- emg2pose estimator wrapper ---------------------------------------------
add("inference", "src/common_pose/estimators/emg2pose", [
    "predict_pose.py", "verify_joint_conventions.py", "smoke_test_inference.py",
])

# --- representation lane ----------------------------------------------------
PLAN += [
    ("representation/canonical_hand.py",
     "src/common_pose/representation/canonical_hand.py"),
]

# --- human semantic-validation lane: curated public-safe subset ---------------
# Six files only. The lane's hidden labels, per-annotator raw data, unblinding keys and
# the still-unblinded selective-head arm are deliberately NOT copied; the curation note
# written by this repository states what is withheld and why.
HUMAN_LANE = "human_semantic_validation"
add(HUMAN_LANE, "audits/human_semantic_validation", [
    "LABEL_DEFINITIONS.md",
    "ANNOTATION_PROTOCOL.md",
    "BLINDING_SPEC.md",
    "FUTURE_ANALYSIS_PLAN.md",
])
add(f"{HUMAN_LANE}/formal_s6", "audits/human_semantic_validation/formal_s6", [
    "FORMAL_ANALYSIS_PREREGISTRATION.md",
    "ONTOLOGY_FREEZE.json",
])


# --------------------------------------------------------------------------- #
# DB9 forensic driver port (rename + path parameterisation)
# --------------------------------------------------------------------------- #

#: archive filename -> published filename
DRIVER_RENAME: dict[str, str] = {
    "fx_common.py": "fx_common.py",
    "01_segmentation.py": "segmentation.py",
    "02_forensic_core.py": "forensic_core.py",
    "03_verdicts.py": "verdicts.py",
    "04_utility.py": "utility.py",
    "04b_utility_posture_only.py": "utility_posture_only.py",
    "05_decision.py": "decision.py",
    "06_final_validation.py": "final_validation.py",
    "99_fact_check.py": "fact_check.py",
}

#: Literal archived filenames that the rename makes stale, rewritten to the new name.
#: These are start-up lookups only; no numeric logic, threshold or assertion is touched.
DRIVER_TEXT_FIXES: list[tuple[str, str]] = [
    ('"04_utility.py"', '"utility.py"'),
    ('"02_forensic_core.py"', '"forensic_core.py"'),
    ('"03_verdicts.py"', '"verdicts.py"'),
    ('"99_fact_check.py"', '"fact_check.py"'),
]

#: Files that are written by this repository's own scripts rather than copied from the
#: historical workspace. They must never be deleted by a clean rebuild, and they must
#: never be listed in PLAN either -- PLAN is strictly "copied from the source workspace".
GENERATED_BY_REPO = {
    "provenance/CURATION_MANIFEST.json",
    "provenance/CURATION_MANIFEST.sha256",
}

#: The DB9 drivers are produced by the port step below, so they must NOT also appear in
#: PLAN as straight copies: the straight-copy pass runs first, and the port would then be
#: silently overwritten by an unparameterised copy. That exact collision happened during
#: this build. Guard it structurally rather than by remembering.
_PORT_SOURCES = {
    f"{DB9_FORENSIC}/scripts/{n}"
    for n in (
        "fx_common.py", "01_segmentation.py", "02_forensic_core.py", "03_verdicts.py",
        "04_utility.py", "04b_utility_posture_only.py", "05_decision.py",
        "06_final_validation.py", "99_fact_check.py",
    )
}
_COLLISIONS = [s for s, _ in PLAN if s in _PORT_SOURCES]
if _COLLISIONS:
    raise SystemExit(
        "build plan error: these files are produced by the driver port and must not "
        f"also be listed as straight copies: {_COLLISIONS}"
    )

#: Provenance header for a ported driver.
#:
#: This is emitted as COMMENTS, not as a docstring, and it goes above the original
#: module docstring. Two constraints force that: `from __future__ import annotations`
#: must be the first *statement* after the module docstring, so any second string
#: literal before it is a SyntaxError; and comments may precede the docstring freely.
DRIVER_HEADER = '''# =============================================================================
# {title}  ---  ported from {source}
#
# Common Pose public repository. Frozen plan SHA-256:
#   4c618b562903d0d364d03bb8a997ef6b4140bd9e09d0f2475f1b008ad80c8793
#
# Driver order: segmentation -> forensic_core -> verdicts -> utility -> decision.
# `verdicts` freezes TRUSTED_DB9_POSE_v1 and `utility` asserts against that frozen
# subset, so it must run after it.
#
# The Ninapro DB9 release is not redistributed with this repository. Paths are supplied
# through the environment; `fx_common` is the single place that reads them.
#
# Edits relative to the archived original: I/O plumbing only --- local absolute paths
# moved to environment variables, and the numeric filename prefixes dropped. No numeric
# logic, threshold, seed, verdict vocabulary or assertion count was changed.
# =============================================================================
'''

#: The archived `fx_common.py` path block, replaced wholesale by the environment-driven
#: block below. `fx_common` is the only file in this tool set that contains an absolute
#: path, so parameterising it here makes the whole tool set relocatable. Pinned so the
#: build fails loudly if the archived file changes shape, rather than silently
#: mis-patching a driver.
FX_COMMON_ORIGINAL_PATHS = (
    'ROOT = r"C:\\emg2pose"\n'
    'LANE = os.path.join(ROOT, "db9_channel_forensic_v2")\n'
    'SCRIPTS = os.path.join(LANE, "scripts")\n'
    'ART = os.path.join(LANE, "artifacts")\n'
    'FIGS = os.path.join(LANE, "figures")\n'
    'LOGS = os.path.join(LANE, "logs")\n'
    'DOCS = os.path.join(LANE, "docs")\n'
    'EXTRACTED = os.path.join(ROOT, "data", "ninapro_db9", "extracted")\n'
    'RAWZIP = os.path.join(ROOT, "data", "ninapro_db9", "raw")\n'
    '\n'
    'PLAN = os.path.join(LANE, "FORENSIC_PLAN.md")\n'
    'PLAN_SHA = os.path.join(LANE, "PLAN_SHA256.txt")\n'
)

FX_COMMON_PATHS = '''# --------------------------------------------------------------------------- #
# Paths. Every one is supplied through the environment so this audit can run outside the
# machine it was authored on. The archived original held absolute local paths; they are
# replaced here and NOWHERE ELSE in this tool set.
#
#   COMMON_POSE_DB9_ROOT       root of the Ninapro DB9 release
#                              (default ./data/ninapro_db9)
#   COMMON_POSE_DB9_EXTRACTED  directory holding the `s_<n>_angles/` folders
#                              (default <ROOT>/extracted)
#   COMMON_POSE_DB9_RAW        directory holding the raw `s_<n>_angles.zip` archives
#                              (default <ROOT>/raw)
#   COMMON_POSE_DB9_OUT        where this audit writes artifacts/figures/logs
#                              (default the directory holding these scripts)
#
# POINT `COMMON_POSE_DB9_OUT` AT A SCRATCH DIRECTORY when re-running: the drivers
# overwrite the frozen artifacts published in this repository, including
# TRUSTED_DB9_POSE_v1.json.
# --------------------------------------------------------------------------- #

ROOT = os.environ.get("COMMON_POSE_DB9_ROOT", os.path.join(".", "data", "ninapro_db9"))
EXTRACTED = os.environ.get("COMMON_POSE_DB9_EXTRACTED", os.path.join(ROOT, "extracted"))
RAWZIP = os.environ.get("COMMON_POSE_DB9_RAW", os.path.join(ROOT, "raw"))

#: Where this driver set lives. The frozen plan is read from here, so it must sit beside
#: the scripts -- which is the case in this repository. This is a read-only location.
LANE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = LANE

#: Writable outputs. Defaults to the script directory; set COMMON_POSE_DB9_OUT to keep a
#: re-run away from the published artifacts.
_OUT = os.environ.get("COMMON_POSE_DB9_OUT", ".")
ART = os.path.join(_OUT, "artifacts")
FIGS = os.path.join(_OUT, "figures")
LOGS = os.path.join(_OUT, "logs")
DOCS = os.path.join(_OUT, "docs")

PLAN = os.path.join(LANE, "FORENSIC_PLAN.md")
PLAN_SHA = os.path.join(LANE, "PLAN_SHA256.txt")
'''


@dataclass
class Record:
    source: str
    target: str
    source_sha256: str
    target_sha256: str
    rules: list[str] = field(default_factory=list)
    note: str = ""

    @property
    def changed(self) -> bool:
        """Whether curation altered the bytes. Derived from the hashes, never counted.

        Recording a substitution *count* would make the manifest depend on how many
        times the build had already run: the first pass rewrites, later passes find
        nothing to rewrite, and the recorded numbers differ. Deriving the fact keeps the
        manifest reproducible, which is the whole point of publishing it.
        """
        return self.source_sha256 != self.target_sha256


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def check_residuals(rel: str, text: str, problems: list[str]) -> None:
    hits = [name for name, pat in FORBIDDEN_AFTER if re.search(pat, text)]
    if hits:
        problems.append(f"RESIDUAL LOCAL PATH in {rel}: {hits}")


def build(apply: bool) -> int:
    records: list[Record] = []
    problems: list[str] = []
    source_hashes: dict[str, str] = {}
    total_subs = 0
    files_altered = 0

    # --- straight copies ------------------------------------------------------
    for s_rel, t_rel in PLAN:
        src, dst = WORKSPACE / s_rel, REPO / t_rel
        if not src.exists():
            problems.append(f"MISSING SOURCE: {s_rel}")
            continue

        src_bytes = src.read_bytes()
        source_hashes[s_rel] = sha(src_bytes)
        try:
            text, encoding = decode(src)
        except UnicodeDecodeError as exc:
            problems.append(f"UNDECODABLE: {s_rel} ({exc})")
            continue

        new_text, rules, n = sanitize(text)
        total_subs += n
        check_residuals(t_rel, new_text, problems)

        if dst.suffix.lower() == ".json":
            try:
                json.loads(new_text)
            except json.JSONDecodeError as exc:
                problems.append(f"WOULD BREAK JSON: {t_rel} ({exc})")
                continue

        out_bytes = new_text.encode(encoding)
        rec = Record(s_rel, t_rel, source_hashes[s_rel], sha(out_bytes), rules)
        files_altered += int(rec.changed)
        records.append(rec)
        if apply:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(out_bytes)

    # --- the DB9 forensic drivers: copied, then parameterised ------------------
    for src_name, dst_name in DRIVER_RENAME.items():
        src = WORKSPACE / DB9_FORENSIC / "scripts" / src_name
        dst = REPO / "audits" / "db9" / "channel_forensic" / "tools" / dst_name
        t_rel = f"audits/db9/channel_forensic/tools/{dst_name}"
        if not src.exists():
            problems.append(f"MISSING SOURCE: {src_name}")
            continue

        src_bytes = src.read_bytes()
        key = f"{DB9_FORENSIC}/scripts/{src_name}"
        source_hashes[key] = sha(src_bytes)
        text, _ = decode(src)
        rules: list[str] = []
        n = 0

        # The fx_common path block must be replaced BEFORE the generic sanitiser runs,
        # because the sanitiser would rewrite the very strings the block match depends
        # on, and the parameterisation would then silently not apply.
        if dst_name == "fx_common.py":
            if FX_COMMON_ORIGINAL_PATHS not in text:
                problems.append(
                    "fx_common.py path block not found verbatim -- the archived file "
                    "changed shape, so the parameterisation would be mis-applied"
                )
                continue
            text = text.replace(FX_COMMON_ORIGINAL_PATHS, FX_COMMON_PATHS, 1)
            n += 1
            rules.append("path block -> environment variables")

        text, more_rules, more = sanitize(text)
        n += more
        for r in more_rules:
            if r not in rules:
                rules.append(r)

        for old, new in DRIVER_TEXT_FIXES:
            if old in text:
                text = text.replace(old, new)
                n += 1
                rules.append(old.strip('"'))

        # The provenance header goes BEFORE the module docstring. Inserting it after the
        # docstring puts text above `from __future__ import annotations`, which is a
        # SyntaxError -- the module must keep the future import first.
        title = dst_name.replace(".py", "").replace("_", " ").capitalize()
        header = DRIVER_HEADER.format(
            title=title, source=f"{DB9_FORENSIC}/scripts/{src_name}"
        )
        text = header + "\n" + text

        total_subs += n
        check_residuals(t_rel, text, problems)
        out_bytes = text.encode("utf-8")
        rec = Record(
            key, t_rel, source_hashes[key], sha(out_bytes), rules,
            note=f"renamed from {src_name}; original docstring retained below the header",
        )
        files_altered += int(rec.changed)
        records.append(rec)
        if apply:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(out_bytes)

    # --- verify the source workspace was not written to -----------------------
    drift = [k for k, v in source_hashes.items() if sha((WORKSPACE / k).read_bytes()) != v]
    if drift:
        problems.append(f"SOURCE WORKSPACE DRIFT: {drift}")

    # --- report ---------------------------------------------------------------
    mode = "APPLY" if apply else "VERIFY"
    print(f"[{mode}] {len(records)} curated files")
    print(f"  source workspace : elided (<SOURCE_WORKSPACE>)")
    print(f"  target           : {REPO.name}/")
    print(f"  substitutions    : {total_subs} applied this pass")
    print(f"  files altered by curation: {files_altered}")
    print(f"  source workspace re-hashed: {len(source_hashes)} files, "
          f"{len(drift)} drifted")

    if problems:
        print("\nPROBLEMS:")
        for p in problems:
            print(f"  {p}")

    if apply:
        # The manifest records where the copies came from WITHOUT naming the local
        # filesystem: a provenance record that leaks the author's username would defeat
        # the sanitisation it is documenting.
        manifest = {
            "generated_by": "scripts/build_curated_tree.py",
            "policy": (
                "Curated copies only, taken from the read-only historical research "
                "workspace named by `source_workspace_id`. That workspace's file hashes "
                "are re-verified at the end of every build, and a drift fails the build. "
                "`source_sha256` is the archived original; `target_sha256` is the "
                "curated copy published here. A file whose two hashes differ was altered "
                "by curation, and `rules_hit` names the substitution classes "
                "responsible."
            ),
            "source_workspace_id": "<SOURCE_WORKSPACE>",
            "substitution_table": [
                {
                    "placeholder": ph,
                    "role": PLACEHOLDER_ROLE.get(ph, "machine-local path"),
                    "note": (
                        "the replaced path is intentionally not recorded here; it "
                        "contained a username and a machine layout"
                    ),
                }
                for ph in dict.fromkeys(ph for _, ph in RAW_RULES)
            ],
            "files": [
                {
                    "source_path": r.source,
                    "target_path": r.target,
                    "source_sha256": r.source_sha256,
                    "target_sha256": r.target_sha256,
                    "altered_by_curation": r.changed,
                    "rules_hit": r.rules,
                    "note": r.note,
                }
                for r in sorted(records, key=lambda x: x.target)
            ],
        }
        out = REPO / "provenance" / "CURATION_MANIFEST.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        (REPO / "provenance" / "CURATION_MANIFEST.sha256").write_text(
            f"{sha(out.read_bytes())}  CURATION_MANIFEST.json\n", encoding="utf-8"
        )
        print(f"\nwrote provenance/CURATION_MANIFEST.json (+ .sha256)")

    return 1 if problems else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--verify", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    sys.exit(build(args.apply))
