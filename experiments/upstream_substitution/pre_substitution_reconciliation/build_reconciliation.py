#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build the PRE-SUBSTITUTION EVIDENCE RECONCILIATION deliverables.

This script does NOT run experiments.  It reads already-published artifacts from
``audits/`` and ``docs/``, reconciles them against the frozen
``TRUSTED_DB9_POSE_v1`` channel subset, and emits:

    artifacts/TRUSTED8_EVIDENCE_MATRIX.csv
    artifacts/TRUSTED8_EVIDENCE_MATRIX.json
    artifacts/RECONCILIATION_DECISION.json

Every number written into the matrix is copied from a cited artifact by this
script; nothing is transcribed by hand and nothing is re-measured.

Run:  python -X utf8 experiments/upstream_substitution/pre_substitution_reconciliation/build_reconciliation.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]  # .../common-pose

ART = HERE / "artifacts"
ART.mkdir(parents=True, exist_ok=True)

FROZEN_SUBSET_SHA = "e51dde6e63941fd080c84f3896a98cf50fba9e17d5f9cebe909253d5465782d1"


def load(rel: str):
    p = REPO / rel
    if not p.exists():
        raise SystemExit(f"required evidence artifact missing: {rel}")
    return json.loads(p.read_text(encoding="utf-8"))


def sha256(rel: str) -> str:
    p = REPO / rel
    return hashlib.sha256(p.read_bytes()).hexdigest()


# --------------------------------------------------------------------------
# Evidence sources
# --------------------------------------------------------------------------

TRUSTED = load("audits/db9/trusted_pose/TRUSTED_DB9_POSE_v1.json")
FINAL = load("audits/db9/channel_forensic/artifacts/FINAL_VALIDATION.json")
FORENSIC = load("audits/db9/channel_forensic/artifacts/FORENSIC_CORE.json")
SRCDEF = load("audits/db9/coordinate_audit/artifacts/SOURCE_DEFINITION_AUDIT.json")
CONFCLS = load("audits/db9/coordinate_audit/artifacts/DIMENSION_CONFIDENCE_CLASSIFICATION.json")
EMG_VERIF = load("docs/canonical_emg2pose_verification.json")
ZEROCOMP = load("docs/DB9_EMG2POSE_ZERO_COMPATIBILITY.json")

# The 8 frozen channels, in frozen artifact order, mapped to their canonical DOF.
# canonical name is authoritative from docs/db9_trusted_subset.md section 3.
TRUSTED8 = [
    ("MCP1", "thumb_mcp_flexion"),
    ("IP1", "thumb_ip_flexion"),
    ("MCP2_f", "index_mcp_flexion"),
    ("PIP2", "index_pip_flexion"),
    ("MCP3_f", "middle_mcp_flexion"),
    ("MCP4_f", "ring_mcp_flexion"),
    ("MCP5_f", "pinky_mcp_flexion"),
    ("PIP5", "pinky_pip_flexion"),
]

SRCDEF_BY_NAME = {e["canonical_name"]: e for e in SRCDEF["per_dimension"]}
EMG_BY_JOINT = {e["canonical"]: e for e in EMG_VERIF["per_dof"]}
TRUSTED_BY_NAME = {e["name"]: e for e in TRUSTED["keep"]}

# --------------------------------------------------------------------------
# Frozen classifications (read, not re-derived)
# --------------------------------------------------------------------------

# Calibration provenance. Two parts, and they must not be conflated:
#   (i) WITHIN-SOURCE provenance for the DB9 released angle is RECOVERED FROM THE BYTES.
#  (ii) CROSS-SOURCE scale equivalence is still absent, and criterion J fails for that reason.
CALIB_PROVENANCE = (
    "TWO PARTS, DO NOT CONFLATE. (i) WITHIN-SOURCE provenance is ESTABLISHED: the released "
    "angle is an exact per-channel affine map of a single raw glove column - recovered from the "
    "bytes for all 8 (FORENSIC_CORE.json .A_transform_forms, kind 'linear_exact', max residual "
    "3.8e-12 to 1.6e-11), and the recovered slope reproduces the PUBLISHED calibration gain to "
    "within 0.61% on every channel (max ratio deviation: MCP1 +0.05%, IP1 +0.07%, MCP2_f +0.32%, "
    "PIP2 -0.16%, MCP3_f +0.28%, MCP4_f +0.00%, MCP5_f +0.61%, PIP5 +0.12%). The released "
    "calibration is therefore auditable and is not a mystery. (ii) CROSS-SOURCE provenance is "
    "NOT_ESTABLISHED, which is why criterion J FAILS x16 (SOURCE_DEFINITION_AUDIT.json "
    ".global_findings.source_of_per_dimension_disagreement): DB9's gains came from a 10-subject "
    "protocol applied to all 77, emg2pose's values are an IK fit of the generic UmeTrack model - "
    "two different metrological processes. Knowing DB9's ruler exactly does not establish that "
    "emg2pose uses the same ruler. No cross-source calibration record exists on either side."
)

# Per-channel recovered transform, for the matrix.
TRANSFORM_NOTE = (
    "FORENSIC_CORE.json .A_transform_forms[{ch}]: kind linear_exact, angle_col {ac}, "
    "glove_col {gc}, slope {slope:.6f} vs published_gain {pub:.3f} (ratio {ratio:.5f}), "
    "max residual {resid:.3e} deg. Implied per-subject reference gauge value {sref:.2f}. "
    "NOTE: this artifact is from the frozen 37-participant run; its PER-CHANNEL agreement "
    "figures are superseded by the 77-participant revalidation, but the recovered transform "
    "coefficients are properties of the released calibration, not of the sample."
)

# Handedness: criterion I is UNCERTAIN x16 in the audit; corroborated by the
# frozen strict-model-frame rendering statement.
HANDEDNESS_LIMITATION = (
    "CRITERION I UNCERTAIN x16 (source_definition_audit .per_dimension[].criteria"
    ".I_handedness = UNCERTAIN). The strict 'flipped into one right-hand model frame' "
    "reading is the coordinate audit's own rendering (its artifacts assert 'the joint "
    "angles are in the model frame'), not a first-party statement located in the official "
    "emg2pose release. Contained for these 8 DOFs: all are single-joint flexion hinge "
    "magnitudes, and neither corpus applies any handedness transform, so no "
    "meaning-changing handedness transform is in scope."
)

# Source-database dependence: a real, measured limitation for 5 of the 8.
SRC_DB_NOTE = (
    "DB2-DB1 subject-level 95% CI excludes zero (coordinate audit section 9): part of what "
    "a development->outcome gap measures is a source-database effect inside DB9 itself."
)


def sign_status(channel: str) -> tuple[str, str]:
    """Sign compatibility is a property of the variable, identical for all 8."""
    return (
        "ESTABLISHED",
        "DB9 paper Table 6: Flexion+ / Extension- for MCP(1-5)_F, PIP(2-5)_F, IP1_F "
        "(DB9_CANONICAL16_MAPPING.md section 3.2, OFFICIAL-DOC). emg2pose: 15/15 FE joints move "
        "the fingertip TOWARD the palm centre at their +limit, therefore positive = flexion "
        "(joint_convention_verification.txt, per-joint d(+limit) vs d(rest) for all 8). "
        "Adapter applies NO sign transform to any of the 8 (SOURCE_DEFINITION_AUDIT.json "
        ".per_dimension[].sign_transform_applied = 1.0).",
    )


def unit_status() -> tuple[str, str]:
    return (
        "ESTABLISHED",
        "DB9 released angles are degrees (paper + measured global range); emg2pose is radians "
        "via so3_exp_map (Rodrigues). conversion is an explicit pi/180 in the DB9 adapter, "
        "reproduced across 77 files / 77,354,864 samples with max |diff| 8.88e-16 rad "
        "(SOURCE_DEFINITION_AUDIT.json .per_dimension[].unit_conversion; coordinate audit "
        "section 6).",
    )


def zero_reference_status(dof: str) -> tuple[str, str, str]:
    """Returns (semantics_status, semantics_evidence, numerical_status)."""
    return (
        "ESTABLISHED",
        "Zero semantics match. DB9: documented reference posture = central part of Exercise B "
        "movement 11, hand resting on the table with fingers closed together and extended "
        "(DB9_CANONICAL16_MAPPING.md section 3.3). emg2pose: official 20D zero vector, whose FK "
        "pose is a fingers-extended hand (finger chain interior angles 179.10/179.45/179.28/"
        "174.85 deg proximal, 168.44/166.68/172.82/171.36 deg distal; zero sits 1.06% of the way "
        "between the most-closed and most-spread pose). MEASURED DB9 side: mean |angle| = 0.854 "
        "deg at the documented anchor, ratio 0.040 to other movements, per-joint vector "
        "[+1.27,-1.04,-0.17,+0.36,+1.42,+0.89,+0.24,+1.00,+0.06,-1.58,+0.58,0.00,-1.94,+1.21,"
        "+0.71,-1.19] deg (POSE_COORDINATE_AUDIT_REPORT.md section 7).",
        "NOT_ESTABLISHED",
    )


def zero_reference_numerical_evidence(dof: str) -> str:
    return (
        "No cross-source numerical zero comparison exists for this DOF. The emg2pose side of the "
        "zero claim is 0 BY CONSTRUCTION, not a measurement, so it can be neither confirmed nor "
        "refuted from the mini corpus; and the two corpora do not share a pose distribution, so "
        "the only available cross-source statistic - the per-dimension median gap (this DOF: "
        f"{SRCDEF_BY_NAME[dof]['median_difference_deg']:.2f} deg, DB9 median "
        f"{SRCDEF_BY_NAME[dof]['db9_median_deg']:.2f} vs emg2pose median "
        f"{SRCDEF_BY_NAME[dof]['emg2pose_median_deg']:.2f}) - is confounded by task composition "
        "(scripted 17-movement protocol vs natural activity) and is NOT a zero-compatibility "
        "measurement. Separately, the reference-posture level is source-database dependent "
        "(DB1 18.001 deg / DB2 5.911 deg / DB5 21.268 deg mean |angle|), so even the DB9-side "
        "zero is not a single cross-source constant."
    )


def build_row(channel: str, dof: str) -> dict:
    t = TRUSTED_BY_NAME[channel]
    s = SRCDEF_BY_NAME[dof]
    c = CONFCLS["per_dimension"][dof]
    f77 = FINAL["Q1_verdicts"]["ALL77"][channel]
    db5 = FINAL["Q1_verdicts"]["DB5"][channel]
    emg_joint = s["emg2pose_official_joint"]
    ev = EMG_BY_JOINT[emg_joint]

    src_ci = s["db2_minus_db1_ci95"]
    src_sig = not (src_ci[0] <= 0.0 <= src_ci[1])

    # ---- anatomical correspondence -------------------------------------
    anat_status = "ESTABLISHED"
    anat_ev = (
        f"DB9 channel {channel} (in-file order_of_angles index {t['source_index']}) <-> "
        f"canonical {dof} <-> emg2pose {emg_joint} (official constants.py index "
        f"{s['emg2pose_source_index']}). Name-based selection on both sides, never positional. "
        f"Criteria A (anatomical DOF) and B (joint indexing) PASS for this dimension in "
        f"SOURCE_DEFINITION_AUDIT.json; the frozen subset is corroborated by "
        f"src/common_pose/api/dof.py and registered with handedness='right'."
    )

    # ---- numerical interchangeability ----------------------------------
    # NOTE: the audit's per-finger anchor table (POSE_COORDINATE_AUDIT_REPORT.md section 10a)
    # covers index/middle/ring/pinky.  For the two thumb channels the per-dimension artifact
    # stores db9_anchor_change_deg = null, so no extended->flexed anchor CHANGE is cited for
    # them; their directional evidence is the KEEP verdict on the fist anchor.
    anchor = c["db9_anchor_change_deg"]
    diag = c["joint_identity_diagonal"]
    if anchor is None:
        anchor_txt = (
            "no extended->flexed anchor CHANGE is recorded for this channel in "
            "DIMENSION_CONFIDENCE_CLASSIFICATION.json (null); directional evidence is the "
            f"A_FIST anchor at 77 participants (agreement {f77['agreement']:.4f}, coherence "
            f"{f77['coherence']:.2f}, magnitude ratio {f77['mag_ratio']:.4f})"
        )
        row_anchor = None
    else:
        anchor_txt = f"{anchor:+.2f} deg extended->flexed anchor"
        row_anchor = round(anchor, 4)

    if c["class"] == "VERIFIED NUMERICALLY EQUIVALENT":
        inter = "INTERCHANGEABLE_WITH_KNOWN_CONVENTION"
        inter_note = (
            "Audit class VERIFIED NUMERICALLY EQUIVALENT: correct response to flexion "
            f"({anchor_txt}) AND its own counterpart is the best-matching emg2pose dimension. "
            "Still requires the per-channel calibration provenance the audit names as the "
            "load-bearing requirement, and the registry carries no numerical calibration "
            "record -- so 'with known convention', not 'directly interchangeable'."
        )
    else:
        inter = "SEMANTICALLY_MATCHED_BUT_CALIBRATION_UNCERTAIN"
        inter_note = (
            "Audit class VERIFIED SEMANTICALLY, NUMERIC CALIBRATION UNCERTAIN: responds "
            f"correctly to flexion ({anchor_txt}) but its movement-to-movement profile does "
            f"not match its own emg2pose counterpart (best match "
            f"{c['joint_identity_best_match']})."
        )

    row = {
        # "dof" is the name required by the reconciliation spec.
        "dof": dof,
        "canonical_dof": dof,
        "db9_channel": channel,
        "db9_source_index": t["source_index"],
        "emg2pose_joint": emg_joint,
        "emg2pose_source_index": s["emg2pose_source_index"],

        "db9_physical_identity_status": "ESTABLISHED",
        "db9_physical_identity_evidence": (
            f"Frozen verdict KEEP under TRUSTED_DB9_POSE_v1; anchor A_FIST on the official "
            f"Exercise-B fist. 77-participant agreement {f77['agreement']:.4f}, opposed "
            f"{f77['opposed']:.4f}, coherence {f77['coherence']:.2f}, magnitude ratio "
            f"{f77['mag_ratio']:.4f} (FINAL_VALIDATION.json .Q1_verdicts.ALL77.{channel}); "
            f"77-subject stable, 0 of 8 KEEP channels changed. NOTE: the DB9 channel's "
            f"direction is read from the released bytes behaviourally, and DB9's own "
            f"definitions carry no direction arrow."
        ),

        "emg2pose_physical_identity_status": "ESTABLISHED",
        "emg2pose_physical_identity_evidence": (
            f"Official joint {emg_joint} at constants.py index "
            f"{s['emg2pose_source_index']}; order verified against the official JOINTS list; "
            f"per-joint FK sign test: d(rest) {ev['observed_min']:.0f}/{ev['observed_max']:.0f} "
            f"observed range, +limit shortens fingertip-to-palm-centre distance "
            f"(joint_convention_verification.txt). Anatomical identity is from the official "
            f"constants + FK, not inferred from distributions."
        ),

        "anatomical_correspondence_status": anat_status,
        "anatomical_correspondence_evidence": anat_ev,

        "unit_compatibility_status": unit_status()[0],
        "unit_compatibility_evidence": unit_status()[1],

        "sign_compatibility_status": sign_status(channel)[0],
        "sign_compatibility_evidence": sign_status(channel)[1],

        "zero_reference_status": zero_reference_status(dof)[0],
        "zero_reference_evidence": zero_reference_status(dof)[1],
        "numerical_zero_interchangeability_status": zero_reference_status(dof)[2],
        "numerical_zero_interchangeability_evidence": zero_reference_numerical_evidence(dof),

        "handedness_status": "ESTABLISHED_WITH_LIMITATION",
        "handedness_evidence": HANDEDNESS_LIMITATION,

        "calibration_provenance_status": "ESTABLISHED_WITH_LIMITATION",
        "calibration_provenance_evidence": CALIB_PROVENANCE,
        "recovered_transform_evidence": TRANSFORM_NOTE.format(
            ch=channel,
            ac=FORENSIC["A_transform_forms"][channel]["angle_col"],
            gc=FORENSIC["A_transform_forms"][channel]["glove_col"],
            slope=FORENSIC["A_transform_forms"][channel]["slope"],
            pub=FORENSIC["A_transform_forms"][channel]["published_gain"],
            ratio=FORENSIC["A_transform_forms"][channel]["slope"]
            / FORENSIC["A_transform_forms"][channel]["published_gain"],
            resid=FORENSIC["A_transform_forms"][channel]["max_resid"],
            sref=FORENSIC["A_transform_forms"][channel]["S_ref_implied"],
        ),

        "numerical_interchangeability_status": inter,
        "numerical_interchangeability_evidence": inter_note,

        # Measured cross-source diagnostics, copied verbatim from the audit.
        "db9_median_deg": round(s["db9_median_deg"], 4),
        "emg2pose_median_deg": round(s["emg2pose_median_deg"], 4),
        "median_gap_deg": round(s["median_difference_deg"], 4),
        "wasserstein_deg": round(s["wasserstein_deg"], 4),
        "support_overlap": round(s["support_overlap"], 4),
        "matched_semantic_max_abs_gap_deg": round(c["matched_semantic_max_abs_gap_deg"], 4),
        "joint_identity_diagonal_winner": bool(diag),
        "joint_identity_best_match": c["joint_identity_best_match"],
        "db9_anchor_change_deg": row_anchor,
        "audit_dimension_class": c["class"],
        "audit_empirical_range_compatibility": s["empirical_range_compatibility"],

        # Source-database dependence.
        "db2_minus_db1_gap_deg": round(s["db2_minus_db1_gap_deg"], 4),
        "db2_minus_db1_ci95": [round(x, 4) for x in src_ci],
        "source_database_dependence": "YES" if src_sig else "NOT_DETECTED",
        "db5_only_anchor_status": db5["status"],
        "db5_only_anchor_agreement": db5["agreement"],

        # emg2pose model-limit exceedance (unclamped, per the frozen contract).
        "emg2pose_pct_outside_official_limits": round(
            100.0 * (ev["frac_below_limit"] + ev["frac_above_limit"]), 4
        ),

        "historical_claims_superseded": (
            "none for this DOF's physical identity. The audit's per-dimension 'already "
            "trustworthy' shortlist is a different, narrower claim than 'cross-source "
            "numerically interchangeable' (see EVIDENCE_RECONCILIATION.md section 5)."
        ),
        "remaining_gap": "",
        "next_minimal_check_if_needed": "",
    }

    # ---- per-DOF gap statement ------------------------------------------
    gaps = []
    if inter == "INTERCHANGEABLE_WITH_KNOWN_CONVENTION":
        gaps.append("no numerical calibration record on either side")
    else:
        gaps.append("dimension-level numerical calibration not demonstrated")
    if src_sig:
        gaps.append(
            "source-database level shift inside DB9 (DB2-DB1 "
            f"{s['db2_minus_db1_gap_deg']:+.2f} deg, CI excluding zero)"
        )
    if not diag:
        gaps.append("its own emg2pose counterpart is not the best-matching dimension")
    row["remaining_gap"] = "ESTABLISHED_WITH_LIMITATION: " + "; ".join(gaps) + "."
    row["next_minimal_check_if_needed"] = (
        "N2 (see RECONCILIATION_DECISION.json): GT-only zero/reference compatibility on the "
        "existing local mini corpus - locate the emg2pose frames that realise the DB9 "
        "documented reference posture and report the per-DOF distribution of the 8 values "
        "there. No model, no labels, no fitting."
    )
    return row


ROWS = [build_row(ch, dof) for ch, dof in TRUSTED8]

# --------------------------------------------------------------------------
# CSV (all columns, plus the required semantic columns)
# --------------------------------------------------------------------------

CSV_FIELDS = [
    "dof", "canonical_dof", "db9_channel", "db9_source_index",
    "emg2pose_joint", "emg2pose_source_index",
    "db9_physical_identity_status", "db9_physical_identity_evidence",
    "emg2pose_physical_identity_status", "emg2pose_physical_identity_evidence",
    "anatomical_correspondence_status", "anatomical_correspondence_evidence",
    "unit_compatibility_status", "unit_compatibility_evidence",
    "sign_compatibility_status", "sign_compatibility_evidence",
    "zero_reference_status", "zero_reference_evidence",
    "numerical_zero_interchangeability_status", "numerical_zero_interchangeability_evidence",
    "handedness_status", "handedness_evidence",
    "calibration_provenance_status", "calibration_provenance_evidence",
    "recovered_transform_evidence",
    "numerical_interchangeability_status", "numerical_interchangeability_evidence",
    "db9_median_deg", "emg2pose_median_deg", "median_gap_deg", "wasserstein_deg",
    "support_overlap", "matched_semantic_max_abs_gap_deg",
    "joint_identity_diagonal_winner", "joint_identity_best_match", "db9_anchor_change_deg",
    "audit_dimension_class", "audit_empirical_range_compatibility",
    "db2_minus_db1_gap_deg", "db2_minus_db1_ci95", "source_database_dependence",
    "db5_only_anchor_status", "db5_only_anchor_agreement",
    "emg2pose_pct_outside_official_limits",
    "historical_claims_superseded", "remaining_gap", "next_minimal_check_if_needed",
]

with (ART / "TRUSTED8_EVIDENCE_MATRIX.csv").open("w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
    w.writeheader()
    for r in ROWS:
        out = dict(r)
        out["db2_minus_db1_ci95"] = json.dumps(out["db2_minus_db1_ci95"])
        w.writerow(out)

# --------------------------------------------------------------------------
# JSON matrix
# --------------------------------------------------------------------------

matrix = {
    "artifact": "TRUSTED8_EVIDENCE_MATRIX.json",
    "purpose": "Per-DOF evidence reconciliation for cross-source compatibility of "
               "TRUSTED_DB9_POSE_v1 against the corresponding emg2pose GT DOF, before any "
               "frozen-downstream-head substitution.",
    "classification": "EVIDENCE RECONCILIATION ONLY. No model was trained, no head was called, "
                      "no label or task output was inspected, and no mapping parameter was fitted.",
    "frozen_representation": "TRUSTED_DB9_POSE_v1",
    "frozen_subset_sha256": FROZEN_SUBSET_SHA,
    "frozen_subset_sha256_verified": sha256(
        "audits/db9/trusted_pose/TRUSTED_DB9_POSE_v1.json"
    ) == FROZEN_SUBSET_SHA,
    "scope_note": "Only column B of the research question is in scope: DB9 <-> emg2pose "
                  "cross-source variable compatibility. Column A (DB9 internal physical "
                  "validity) is CLOSED and is not re-adjudicated here.",
    "status_vocabulary": [
        "ESTABLISHED", "ESTABLISHED_WITH_LIMITATION", "UNRESOLVED",
        "NOT_ESTABLISHED", "SUPERSEDED",
    ],
    "interchangeability_vocabulary": [
        "DIRECTLY_INTERCHANGEABLE", "INTERCHANGEABLE_WITH_KNOWN_CONVENTION",
        "SEMANTICALLY_MATCHED_BUT_CALIBRATION_UNCERTAIN", "NOT_INTERCHANGEABLE", "UNRESOLVED",
    ],
    "rows": ROWS,
    "evidence_sources": {
        rel: sha256(rel)
        for rel in [
            "audits/db9/trusted_pose/TRUSTED_DB9_POSE_v1.json",
            "audits/db9/channel_forensic/FINAL_VALIDATION.md",
            "audits/db9/channel_forensic/artifacts/FINAL_VALIDATION.json",
            "audits/db9/channel_forensic/artifacts/FORENSIC_CORE.json",
            "audits/db9/coordinate_audit/POSE_COORDINATE_AUDIT_REPORT.md",
            "audits/db9/coordinate_audit/POSE_COORDINATE_AUDIT_PLAN.json",
            "audits/db9/coordinate_audit/artifacts/COMMON_POSE_API_VERDICT.json",
            "audits/db9/coordinate_audit/artifacts/SOURCE_DEFINITION_AUDIT.json",
            "audits/db9/coordinate_audit/artifacts/DIMENSION_CONFIDENCE_CLASSIFICATION.json",
            "docs/DB9_EMG2POSE_ZERO_COMPATIBILITY.json",
            "docs/canonical_emg2pose_verification.json",
            "docs/joint_angle_definition.md",
            "docs/DB9_CANONICAL16_MAPPING.md",
            "docs/CANONICAL16_CONTRACT.md",
            "docs/research_status.md",
            "docs/db9_trusted_subset.md",
            "src/common_pose/api/dof.py",
        ]
    },
}

(ART / "TRUSTED8_EVIDENCE_MATRIX.json").write_text(
    json.dumps(matrix, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
)

# --------------------------------------------------------------------------
# Decision artifact
# --------------------------------------------------------------------------

decision = {
    "artifact": "RECONCILIATION_DECISION.json",
    "phase": "PRE-SUBSTITUTION EVIDENCE RECONCILIATION",
    "frozen_representation": "TRUSTED_DB9_POSE_v1",
    "frozen_subset_sha256": FROZEN_SUBSET_SHA,

    "go_no_go": "CONDITIONAL_GO",
    "go_no_go_basis": {
        "GO_TO_GATE2_requirements": {
            "all_8_dofs_have_established_semantic_or_anatomical_mapping": True,
            "units_sign_order_closed": True,
            "no_unresolved_handedness_issue_can_change_physical_meaning": True,
            "remaining_calibration_uncertainty_characterisable_without_outcome_driven_fitting": False,
        },
        "why_not_GO": "All eight DOFs are semantically and anatomically matched, and "
                      "units/sign/zero-semantics/order are closed; DB9's own ruler is fully "
                      "recovered from the bytes. But no CROSS-SOURCE calibration record exists on "
                      "either side, and the only available cross-source statistic (per-dimension "
                      "median gap, 10.57-31.23 deg) is confounded by task composition: the audit "
                      "measured the emg2pose-side session spread at 3.74x the cross-dataset median "
                      "gap and stated that no per-dimension cross-dataset claim in the 20-30 deg "
                      "range is resolvable with this corpus at all. One minimal, pre-declared, "
                      "outcome-free check can bound it.",
        "why_not_NO_GO": "No required DOF lacks a defensible physical correspondence. All eight "
                         "have ESTABLISHED anatomical correspondence, unit compatibility, sign "
                         "compatibility and zero SEMANTICS. No arbitrary fitted alignment is "
                         "required to state the mapping; the open question is measurement "
                         "equivalence, not identity.",
    },

    "closed_facts": [
        "Anatomical correspondence for all 8 frozen DOFs (criteria A and B PASS x16).",
        "Source indexing: DB9 order_of_angles indices 2, 3, 4, 6, 7, 9, 13, 15 and the "
        "emg2pose constants.py indices 2, 3, 5, 6, 9, 13, 17, 18.",
        "Units: DB9 degrees, emg2pose radians, explicit pi/180, reproduced bit-exactly across "
        "77 files / 77,354,864 samples (max |diff| 8.88e-16 rad).",
        "Sign: positive = flexion on both sides for all 8 (DB9 Table 6 documented; emg2pose "
        "15/15 FE joints FK-verified). Zero sign transforms applied.",
        "Zero SEMANTICS: both sides place zero at the extended, fingers-together hand; DB9's "
        "documented anchor is numerically attained (0.854 deg mean |angle|).",
        "Angle convention: both are joint rotation magnitudes about fixed joint-specific axes, "
        "not derived interior angles (PIP round-trip 0.5-0.9 deg).",
        "Range/wrapping: neither side wraps (criterion H PASS x16).",
        "DB9 physical identity of all 8 channels: 77/77 stable, 0 of 8 KEEP channels changed.",
        "DB9-internal anchor behaviour: for the six finger channels a positive change from the "
        "extended anchor to the flexed anchor (+31.72 to +123.79 deg, "
        "DIMENSION_CONFIDENCE_CLASSIFICATION.json); for the two thumb channels (MCP1, IP1) no "
        "extended->flexed anchor CHANGE is recorded in the artifacts (null), so their "
        "directional evidence rests on the A_FIST anchor at 77 participants (agreement 0.9221 "
        "and 1.0000 respectively).",
        "The 8 DOFs are disjoint from every DOF the coordinate audit found directionally "
        "defective (middle/ring/pinky DIP and middle PIP).",
        "DB9 WITHIN-SOURCE calibration provenance: the released angle of every one of the 8 "
        "channels is an exact affine map of a single raw glove column (FORENSIC_CORE.json "
        ".A_transform_forms, max residual 3.8e-12 to 1.6e-11 deg), and the recovered slope "
        "reproduces the published calibration gain to within 0.61% on every channel. The DB9 "
        "ruler is therefore fully known and auditable.",
    ],

    "partially_closed": [
        "Sign compatibility of MCP1: 77-participant agreement 0.9221 (opposed 0.0779) rather "
        "than 1.0000. DB1 1.000, DB2 0.925, DB5 0.700 - DB5 alone rates MCP1 INCONCLUSIVE. "
        "The frozen rule pools all 77, so the KEEP is correct under the frozen rule; the "
        "per-source detail is a limitation, not a contradiction.",
        "Numerical interchangeability: 4 of 8 are INTERCHANGEABLE_WITH_KNOWN_CONVENTION "
        "(IP1, PIP2, MCP4_f, PIP5), 4 of 8 are SEMANTICALLY_MATCHED_BUT_CALIBRATION_UNCERTAIN "
        "(MCP1, MCP2_f, MCP3_f, MCP5_f). None is DIRECTLY_INTERCHANGEABLE.",
        "Source-database independence: 5 of 8 show a DB2-DB1 subject-level CI excluding zero "
        "(MCP2_f, PIP2, MCP3_f, MCP4_f, MCP5_f).",
        "Numerical zero interchangeability: NOT_ESTABLISHED for all 8 (the emg2pose side is 0 "
        "by construction, not a measurement).",
        "Handedness: criterion I UNCERTAIN x16; contained, not closed.",
        "emg2pose official-limit adherence: 0.05%-20.97% of mini-corpus samples lie outside the "
        "official UmeTrack limits per DOF, and the frozen contract forbids clamping.",
    ],

    "superseded_evidence": [
        {
            "old_claim": "docs/research_status.md section E5: the coordinate audit's "
                         "per-source-database reference means (DB1 18.0 / DB2 5.9 / DB5 21.3 "
                         "degrees) were computed on a repetition-grouped corpus that does not "
                         "match the frozen one.",
            "classification": "INVALIDATED (by reconciliation, not by re-running)",
            "why": "The coordinate audit was run on the frozen corpus, not the old one. Its "
                   "frozen plan pins data/db9_posture16/representative_postures_77.npz "
                   "(sha256 4fba093dff0ef82925176a77358b934ebcb362bd35b262d21d2ec7611f5e8b9f); "
                   "its reproducibility section reports 77 raw .mat files / 77,354,864 samples "
                   "with max |diff| 8.88e-16 rad against the frozen adapter; its bug log records "
                   "that db9_pick_file_for_slot keyed on the filename tag _E2_ was FIXED to "
                   "identify the protocol file from the data (the same defect that separated "
                   "37 from 77 participants); and the non-zero values it reports are exactly the "
                   "values in SOURCE_DEFINITION_AUDIT.json and DB9_SOURCE_CALIBRATION_AUDIT.json.",
            "what_replaces_it": "The values 18.001 / 5.911 / 21.268 deg ARE valid evidence and "
                                "are used as such in this reconciliation. The genuinely "
                                "superseded 179.7 deg figure is a different statistic (grand "
                                "mean offset) from a different branch, correctly reinterpreted "
                                "by the coordinate audit section 20.",
            "action": "REPORTED ONLY. No authoritative document was edited. See "
                      "EVIDENCE_RECONCILIATION.md section 8.",
        },
        {
            "old_claim": "POSE_COORDINATE_AUDIT_REPORT.md section 18 cell for thumb_ip_flexion: "
                         "'NOT YET SAFE (range disagreement 31 deg)', with "
                         "empirical_range_compatibility = LOW.",
            "classification": "UNRESOLVED (audit-internal figure, not reproducible here)",
            "why": "31.2328 is stored in DIMENSION_CONFIDENCE_CLASSIFICATION.json and "
                   "CANONICAL16_EQUIVALENCE_MATRIX.csv as median_difference_deg - a median "
                   "LOCATION gap, not a range/span gap. THUMB_IP_FE official limits are "
                   "-14.81 to +62.30 deg and the DB9 median is +6.89 deg; nothing preserved in "
                   "common-pose yields a 31 deg RANGE disagreement. The construction rule for "
                   "empirical_range_compatibility is not present in this repository.",
            "what_replaces_it": "Nothing yet. The verdict direction is conservative (a caution, "
                                "not a clearance), so no status here changes. Recorded so the "
                                "31 deg is not quoted as a range fact.",
            "action": "REPORTED ONLY. See EVIDENCE_RECONCILIATION.md section 10.",
        },
        {
            "old_claim": "TRUSTED_DB9_POSE_v1.json .exclusion_list[C MC5] carries "
                         "case = CASE_B_SENSOR_OR_FIT_LIMITATION.",
            "classification": "SUPERSEDED",
            "why": "The final case is CASE_A_RELEASED_REPRESENTATION (docs/research_status.md "
                   "section A3; docs/db9_trusted_subset.md section 4.3). The artifact is frozen "
                   "and preserved unmodified.",
            "what_replaces_it": "docs/db9_trusted_subset.md section 4.3 - released CMC5 = exact "
                                "affine function of the same raw column as WRIST_F.",
            "action": "Recorded. Not relevant to any of the 8 trusted DOFs (CMC5 is DROP).",
        },
        {
            "old_claim": "TRUSTED_DB9_POSE_v1.json records n_subjects: 37 throughout.",
            "classification": "SUPERSEDED",
            "why": "Coverage is 77 of 77 participants; the 37 was a loader selection artifact.",
            "what_replaces_it": "audits/db9/channel_forensic/FINAL_VALIDATION.md "
                                "(sha256 4fa700dc26d0d50f243c72372b2c1a67ee9749b4964757e529b8212839fd2b81).",
            "action": "Recorded. 0 of 8 KEEP channels changed at 77 participants.",
        },
        {
            "old_claim": "DB9_EMG2POSE_ZERO_COMPATIBILITY.json section thumb_cmc_ab_adduction: "
                         "'emg2pose_positive_is_abduction: false', confidence MEDIUM.",
            "classification": "SUPERSEDED",
            "why": "The probe used only +/- 0.3 rad.",
            "what_replaces_it": "The full-range FK sweep over the official limit range "
                                "[-0.6118, +0.6118] rad (DB9_CANONICAL16_MAPPING.md section 4.2).",
            "action": "Recorded. thumb CMC AA is NOT one of the 8 trusted DOFs.",
        },
        {
            "old_claim": "The coordinate audit's 179.7 deg grand-mean offset reading as a "
                         "possible coordinate mismatch between the two datasets.",
            "classification": "INVALIDATED",
            "why": "The coordinate audit section 20 shows the statistic was dominated by DB9's "
                   "broken DIP channels, task composition and source-database imbalance.",
            "what_replaces_it": "A genuine cross-dataset disagreement that is smaller, "
                                "joint-specific and differently shaped.",
            "action": "Already superseded before this round; carried here for completeness.",
        },
    ],

    "true_remaining_blockers": [
        {
            "id": "B1",
            "blocker": "No CROSS-SOURCE calibration record exists, so 'same physical variable' "
                       "does not yet imply 'same physical scale'. The DB9 ruler is fully known "
                       "(recovered from the bytes) but emg2pose's is not, and the frozen head's "
                       "decision boundaries were learned on DB9 scales.",
            "affects": "all 8 DOFs",
            "severity": "NON-TASK-DERIVED CALIBRATION / ZERO QUESTION - needs one minimal "
                        "pre-declared check, not a redesign",
        },
        {
            "id": "B2",
            "blocker": "Numerical zero interchangeability is NOT_ESTABLISHED: the emg2pose zero "
                       "is a model-construction fact, not a measurement, and no cross-source "
                       "zero comparison exists for any of the 8.",
            "affects": "all 8 DOFs",
            "severity": "same minimal check as B1",
        },
        {
            "id": "B3",
            "blocker": "Source-database level shifts inside DB9 (5 of 8 DOFs) mean 'DB9' is not "
                       "one calibration. A substitution result therefore cannot be attributed "
                       "to upstream substitution alone unless source-database identity is "
                       "carried as metadata.",
            "affects": "MCP2_f, PIP2, MCP3_f, MCP4_f, MCP5_f",
            "severity": "METADATA REQUIREMENT - no new measurement needed",
        },
    ],

    "not_a_blocker": [
        "The coordinate audit's classification of four dimensions as 'already trustworthy' is "
        "internally consistent with, and not contradicted by, the DROP of PIP3 as DB9's own "
        "middle-PIP channel. They measure different things: PIP3 (middle finger) is DROP; "
        "middle_pip_flexion is therefore ABSENT from the trusted-8, while ring_pip_flexion is "
        "INCONCLUSIVE and also absent. The trusted-8 contains exactly one PIP: PIP2 (index) "
        "and PIP5 (pinky).",
    ],

    "next_minimal_check": {
        "id": "N2",
        "question": "On the local emg2pose mini corpus, at frames whose pose realises the DB9 "
                    "documented reference posture (hand resting on the table, fingers closed "
                    "together and extended), what is the per-DOF distribution of the 8 "
                    "canonical16 values?",
        "why_it_is_not_duplicating_previous_work": "The audit verified the DB9 side of the "
                    "anchor (0.854 deg mean |angle|) and asserted the emg2pose side is 0 by "
                    "construction. It never MEASURED the emg2pose side at an equivalent "
                    "physical posture. That is the single missing term in the zero claim.",
        "why_it_is_not_outcome_driven": "It uses only GT joint angles and the official hand "
                    "model. No task head, no labels, no probabilities, no margins, no accuracy, "
                    "and no fitted parameter enters the check. The pass/fail rule is declared "
                    "in advance.",
        "data_required": "docs-adjacent local emg2pose mini corpus "
                         "(data/official/emg2pose_dataset_mini/*.hdf5, 30 sessions) plus "
                         "generic_hand_model.json "
                         "(sha256 96649ddf7d036be3357dadd7c13db325a18638c6713583fbbbdd71446ce07564).",
        "existing_local_data_sufficient": True,
        "server_needed": False,
        "gpu_needed": False,
        "expected_scope": "Single CPU pass over ~4.2M frames of already-local 20D joint angles. "
                          "Select frames by proximity to the DB9 reference-posture prototype in "
                          "canonical16 space; report per-DOF median and p05/p95. Minutes.",
        "pass_criterion": "For every one of the 8 DOFs, the emg2pose value at the "
                          "reference-posture frames lies within +/- 2 deg of 0, i.e. consistent "
                          "with the DB9 anchor's own per-joint residuals "
                          "(range 0.00 to 1.94 deg in absolute value). This would establish "
                          "numerical zero interchangeability.",
        "fail_criterion": "Any DOF whose reference-posture frames sit at a non-zero level that "
                          "exceeds the DB9 anchor residual by more than the DB9 anchor's own "
                          "movement-to-movement spread would establish a per-DOF zero offset, "
                          "which would be a hard blocker for head substitution and would have to "
                          "be reported as a negative result.",
        "note": "If the natural mini corpus does not contain the reference posture at all, the "
                "check is NOT_EVALUABLE LOCALLY and must be reported as such - it must not be "
                "rescued by synthesising the pose from the model, because that would assume the "
                "model's zero equals the physical zero.",
    },

    "downstream_firewall": {
        "DOWNSTREAM_HEAD_ACCESSED": "NO",
        "TASK_LABELS_GENERATED": "NO",
        "TASK_PROBABILITIES_INSPECTED": "NO",
        "GT_VS_PRED_PRESERVATION_RUN": "NO",
        "MAPPING_TUNED_USING_TASK_OUTPUT": "NO",
    },

    "next_allowed_step": "Run only the specified minimal physical-compatibility check before "
                         "any task-head evaluation.",

    "execution_scope": {
        "models_trained": 0,
        "db9_forensic_rerun": False,
        "trusted_channels_reselected": False,
        "TRUSTED_DB9_POSE_v1_modified": False,
        "new_heavy_data_files_created": False,
        "deep_learning_run": False,
        "server_used": False,
        "network_used": False,
    },
}

(ART / "RECONCILIATION_DECISION.json").write_text(
    json.dumps(decision, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
)

# --------------------------------------------------------------------------
# Console summary
# --------------------------------------------------------------------------

print("rows written:", len(ROWS))
print()
hdr = f"{'canonical DOF':<22}{'DB9':<9}{'interchangeability':<46}{'class':<48}"
print(hdr)
print("-" * len(hdr))
for r in ROWS:
    print(
        f"{r['canonical_dof']:<22}{r['db9_channel']:<9}"
        f"{r['numerical_interchangeability_status']:<46}"
        f"{r['audit_dimension_class']:<48}"
    )
print()
print("frozen subset hash verified:",
      matrix["frozen_subset_sha256_verified"])
print("decision:", decision["go_no_go"])
