"""The anatomical degree-of-freedom registry.

Why a registry instead of a constant vector
-------------------------------------------
A pose vector is only meaningful relative to a naming convention, and *two datasets
having a joint with the same name does not make the two numbers the same number*. The
cross-dataset audit found per-dimension disagreement of 2-40 deg in the medians and up to
450 deg in the ranges between two datasets whose DOF identities, units and sign
conventions all checked out
(``audits/db9/coordinate_audit/artifacts/COMMON_POSE_API_VERDICT.json``).

So a dimension here is not an index. It is a bundle of physical semantics that any
adapter must be able to fill in, and that a consumer can inspect before trusting a
number:

    anatomical DOF | unit | positive direction | zero / reference definition
    handedness convention | calibration provenance | validity / confidence

The registry holds three *distinct* things, and they must not be merged:

``canonical16``
    16 named DOF observable in emg2pose's 20 outputs and in DB9's 22 CyberGlove channels.
    This is a **vocabulary**, and it is the vocabulary the historical results were
    computed in. It is NOT a statement that every member is a valid physical measurement.

``TRUSTED_DB9_POSE_v1``
    The 8 DB9 channels that survived the frozen physical audit, chosen with no reference
    to classification performance. This is an **evidence result**, frozen before any
    classifier ran.

``CommonPoseSubset_v2_candidate``
    An 11-DOF *proposal* from the dataset-admission lane, selected for availability across
    additional third-party datasets. It is a PROPOSAL — it has not been run, has not been
    frozen, and is not the trusted subset. It is carried here so the two are not confused.

See ``docs/common_pose_api.md`` for the interface philosophy and
``docs/db9_trusted_subset.md`` for the audit that produced the trusted subset.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Literal, Mapping

from .verdicts import AuditVerdict

Axis = Literal["FE", "AA"]
Finger = Literal["thumb", "index", "middle", "ring", "pinky", "wrist", "palm"]

#: Repository root, derived from this file's location (``src/common_pose/api/dof.py``).
REPO_ROOT = Path(__file__).resolve().parents[3]

#: Default location of the frozen trusted-subset artifact.
TRUSTED_DB9_SUBSET_PATH = (
    REPO_ROOT / "audits" / "db9" / "trusted_pose" / "TRUSTED_DB9_POSE_v1.json"
)


@dataclass(frozen=True)
class DofSpec:
    """One anatomically-named degree of freedom.

    Every field is required to be *answerable*; fields that are genuinely unknown for a
    given dataset are ``None`` with a ``gap`` note explaining why, never a plausible
    default. An unanswerable field silently defaulted is exactly how a numeric
    coordinate equivalence gets asserted without evidence.
    """

    name: str
    """Canonical name, e.g. ``index_pip_flexion``."""

    finger: Finger
    joint: str
    axis: Axis

    unit: str = "deg"
    """Unit of the values in a frame's ``values`` array for this dimension."""

    positive_direction: str | None = None
    """What a positive value means physically, e.g. ``flexion``."""

    zero_definition: str | None = None
    """What a value of 0 means. ``None`` means the dataset does not define it."""

    handedness: str | None = None
    """Handedness convention, or ``None`` when unspecified by the source."""

    emg2pose_index: int | None = None
    """Column index in the emg2pose 20-DOF output, when published."""

    db9_channel: str | None = None
    """Official Ninapro DB9 CyberGlove channel name, when present."""

    db9_index: int | None = None
    """Column index in DB9's released 22-channel ``angles`` array."""

    db9_verdict: AuditVerdict | None = None
    """Frozen audit verdict for the DB9 channel, when the audit covers it."""

    calibration_provenance: str | None = None
    """Where the numbers' scale came from. This is the load-bearing field:
    the cross-dataset audit concluded that a shared API must carry per-channel
    calibration provenance, not just the anatomical name."""

    note: str = ""
    gap: str = ""

    @property
    def fully_specified(self) -> bool:
        """True only when every physical-semantics field is answered."""
        return all(
            v is not None
            for v in (
                self.positive_direction,
                self.zero_definition,
                self.handedness,
                self.calibration_provenance,
            )
        )

    def describe(self) -> str:
        state = "FULLY SPECIFIED" if self.fully_specified else "INCOMPLETE SEMANTICS"
        missing = [
            k
            for k, v in (
                ("positive_direction", self.positive_direction),
                ("zero_definition", self.zero_definition),
                ("handedness", self.handedness),
                ("calibration_provenance", self.calibration_provenance),
            )
            if v is None
        ]
        tail = f" | missing: {', '.join(missing)}" if missing else ""
        return f"{self.name}: {state}{tail}"


# --------------------------------------------------------------------------- #
# canonical16 — the shared VOCABULARY (not a validity claim)
# --------------------------------------------------------------------------- #
#
# DB9's released 22-channel order, read verbatim from the ``order_of_angles`` field
# stored inside every released .mat:
#
#   0 CMC1_f   1 CMC1_a   2 MCP1    3 IP1     4 MCP2_f  5 MCP2_a  6 PIP2
#   7 MCP3_f   8 PIP3     9 MCP4_f 10 MCP4_a 11 PIP4   12 CMC5   13 MCP5_f
#  14 MCP5_a  15 PIP5    16 DIP2   17 DIP3   18 DIP4   19 DIP5   20 WRIST_F
#  21 WRIST_A
#
# ``MCP2_a`` (index 5) is all-NaN in every examined recording and is excluded by the
# vendor: "Sensor 11 (which corresponds to MCP2-3_A) was not included into the
# calibrated data due to noise problems." It is therefore absent from canonical16.

_DB9_ZERO = (
    "the subject's own reference posture, taken over the central part of Exercise B "
    "movement 11 (hand resting on the table, fingers together and extended); the "
    "released angles are f(glove) - f(glove_reference)"
)
_DB9_SIGN = "flexion + / extension -"
_DB9_CALIB = (
    "Ninapro DB9 released per-channel calibration: a per-channel affine or "
    "affine-quadratic function of one raw CyberGlove gauge. The gains were derived by "
    "the DB9 authors from 10 subjects and applied to all 77; the raw gauges are not "
    "published, so parity cannot be independently closed."
)
_EMG2POSE_CALIB = (
    "emg2pose model output: a learned regression from 16-channel sEMG, trained against "
    "UmeTrack optical tracking. Its zero is a model-construction artefact, not a "
    "recorded physical reference posture."
)

_CANONICAL16: tuple[DofSpec, ...] = (
    DofSpec(
        "thumb_cmc_flexion", "thumb", "CMC", "FE",
        positive_direction="flexion", zero_definition=_DB9_ZERO,
        handedness="right", emg2pose_index=0, db9_channel="CMC1_f", db9_index=0,
        calibration_provenance=_DB9_CALIB,
        note="emg2pose publishes it as THUMB_CMC_FE.",
    ),
    DofSpec(
        "thumb_cmc_ab_adduction", "thumb", "CMC", "AA",
        positive_direction="abduction", zero_definition=_DB9_ZERO,
        handedness="right", emg2pose_index=1, db9_channel="CMC1_a", db9_index=1,
        calibration_provenance=_DB9_CALIB,
        note="the dataset-admission lane found no globally meaningful sign convention "
             "for thumb CMC abduction, which is why it is absent from every proposed "
             "shared subset.",
    ),
    DofSpec(
        "thumb_mcp_flexion", "thumb", "MCP", "FE",
        positive_direction="flexion", zero_definition=_DB9_ZERO,
        handedness="right", emg2pose_index=2, db9_channel="MCP1", db9_index=2,
        calibration_provenance=_DB9_CALIB,
    ),
    DofSpec(
        "thumb_ip_flexion", "thumb", "IP", "FE",
        positive_direction="flexion", zero_definition=_DB9_ZERO,
        handedness="right", emg2pose_index=3, db9_channel="IP1", db9_index=3,
        calibration_provenance=_DB9_CALIB,
    ),
    DofSpec(
        "index_mcp_flexion", "index", "MCP", "FE",
        positive_direction="flexion", zero_definition=_DB9_ZERO,
        handedness="right", emg2pose_index=5, db9_channel="MCP2_f", db9_index=4,
        calibration_provenance=_DB9_CALIB,
    ),
    DofSpec(
        "index_pip_flexion", "index", "PIP", "FE",
        positive_direction="flexion", zero_definition=_DB9_ZERO,
        handedness="right", emg2pose_index=6, db9_channel="PIP2", db9_index=6,
        calibration_provenance=_DB9_CALIB,
    ),
    DofSpec(
        "index_dip_flexion", "index", "DIP", "FE",
        positive_direction="flexion", zero_definition=_DB9_ZERO,
        handedness="right", emg2pose_index=7, db9_channel="DIP2", db9_index=16,
        calibration_provenance=_DB9_CALIB,
        note="absent from all three external third-party datasets audited; DB9's DIP "
             "gauges are hand-size dependent per the vendor's own note.",
    ),
    DofSpec(
        "middle_mcp_flexion", "middle", "MCP", "FE",
        positive_direction="flexion", zero_definition=_DB9_ZERO,
        handedness="right", emg2pose_index=9, db9_channel="MCP3_f", db9_index=7,
        calibration_provenance=_DB9_CALIB,
        gap="there is no middle-finger abduction channel in the 22-channel CyberGlove "
            "set, so MIDDLE_MCP_AA has no DB9 counterpart by construction.",
    ),
    DofSpec(
        "middle_pip_flexion", "middle", "PIP", "FE",
        positive_direction="flexion", zero_definition=_DB9_ZERO,
        handedness="right", emg2pose_index=10, db9_channel="PIP3", db9_index=8,
        calibration_provenance=_DB9_CALIB,
        note="Moved INCONCLUSIVE -> DROP at the final 77-participant sample under the "
             "already-frozen rules: agreement 0.45 with magnitude ratio 0.03, below the "
             "frozen responsiveness floor. The earlier 37-participant sample did not "
             "settle it. The larger sample made the rule strictly more conservative, "
             "never more permissive.",
    ),
    DofSpec(
        "middle_dip_flexion", "middle", "DIP", "FE",
        positive_direction="flexion", zero_definition=_DB9_ZERO,
        handedness="right", emg2pose_index=11, db9_channel="DIP3", db9_index=17,
        calibration_provenance=_DB9_CALIB,
        note="DB9 DIP3 is DROPped: on an unambiguous fist the raw gauge and the released "
             "angle both decrease while every MCP and PIP channel in the same segments "
             "increases. Directional inversion (77-participant ratio 0.06 / 0.92 "
             "opposed), not noise.",
    ),
    DofSpec(
        "ring_mcp_flexion", "ring", "MCP", "FE",
        positive_direction="flexion", zero_definition=_DB9_ZERO,
        handedness="right", emg2pose_index=13, db9_channel="MCP4_f", db9_index=9,
        calibration_provenance=_DB9_CALIB,
    ),
    DofSpec(
        "ring_pip_flexion", "ring", "PIP", "FE",
        positive_direction="flexion", zero_definition=_DB9_ZERO,
        handedness="right", emg2pose_index=14, db9_channel="PIP4", db9_index=11,
        calibration_provenance=_DB9_CALIB,
        note="Held INCONCLUSIVE at the final 77-participant sample: agreement 0.77, above "
             "the drop floor but not established.",
    ),
    DofSpec(
        "ring_dip_flexion", "ring", "DIP", "FE",
        positive_direction="flexion", zero_definition=_DB9_ZERO,
        handedness="right", emg2pose_index=15, db9_channel="DIP4", db9_index=18,
        calibration_provenance=_DB9_CALIB,
        note="Moved INCONCLUSIVE -> DROP at the final 77-participant sample under the "
             "already-frozen rules: agreement 0.29 with magnitude ratio 0.05, below the "
             "frozen responsiveness floor. Inversion direction was already observed in "
             "the earlier 37-participant sample but did not settle the verdict there.",
    ),
    DofSpec(
        "pinky_mcp_flexion", "pinky", "MCP", "FE",
        positive_direction="flexion", zero_definition=_DB9_ZERO,
        handedness="right", emg2pose_index=17, db9_channel="MCP5_f", db9_index=13,
        calibration_provenance=_DB9_CALIB,
    ),
    DofSpec(
        "pinky_pip_flexion", "pinky", "PIP", "FE",
        positive_direction="flexion", zero_definition=_DB9_ZERO,
        handedness="right", emg2pose_index=18, db9_channel="PIP5", db9_index=15,
        calibration_provenance=_DB9_CALIB,
    ),
    DofSpec(
        "pinky_dip_flexion", "pinky", "DIP", "FE",
        positive_direction="flexion", zero_definition=_DB9_ZERO,
        handedness="right", emg2pose_index=19, db9_channel="DIP5", db9_index=19,
        calibration_provenance=_DB9_CALIB,
        note="DB9 DIP5 is DROPped: the same directional inversion as DIP3 "
             "(77-participant ratio 0.19 / 0.81 opposed).",
    ),
)

#: The propositional subset from the dataset-admission lane. NOT frozen, NOT run.
COMMON_POSE_SUBSET_V2_CANDIDATE_TIER1: tuple[str, ...] = (
    "index_mcp_flexion", "index_pip_flexion",
    "middle_mcp_flexion", "middle_pip_flexion",
    "ring_mcp_flexion", "ring_pip_flexion",
    "pinky_mcp_flexion", "pinky_pip_flexion",
)
COMMON_POSE_SUBSET_V2_CANDIDATE_TIER2: tuple[str, ...] = (
    "thumb_cmc_flexion", "thumb_mcp_flexion", "thumb_ip_flexion",
)


@dataclass
class DofRegistry:
    """An ordered set of :class:`DofSpec` with lookup by name or by source index."""

    name: str
    specs: tuple[DofSpec, ...]
    status: str = ""
    provenance: str = ""
    _by_name: dict[str, DofSpec] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        seen: dict[str, DofSpec] = {}
        for s in self.specs:
            if s.name in seen:
                raise ValueError(f"duplicate DOF name {s.name!r} in registry {self.name!r}")
            seen[s.name] = s
        self._by_name = seen

    def __len__(self) -> int:
        return len(self.specs)

    def __iter__(self):
        return iter(self.specs)

    def __contains__(self, name: object) -> bool:
        return name in self._by_name

    def __getitem__(self, name: str) -> DofSpec:
        try:
            return self._by_name[name]
        except KeyError as exc:
            raise KeyError(
                f"{name!r} is not in registry {self.name!r}; available: "
                f"{', '.join(self._by_name)}"
            ) from exc

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(s.name for s in self.specs)

    def by_source_index(self, source: Literal["db9", "emg2pose"]) -> dict[int, DofSpec]:
        """Map *source column index* -> spec. Refuses to invent positions."""
        out: dict[int, DofSpec] = {}
        for s in self.specs:
            idx = s.db9_index if source == "db9" else s.emg2pose_index
            if idx is None:
                continue
            if idx in out:
                raise ValueError(
                    f"{source} index {idx} claimed by both {out[idx].name!r} and "
                    f"{s.name!r} in registry {self.name!r}"
                )
            out[idx] = s
        return out

    def incompletely_specified(self) -> list[DofSpec]:
        return [s for s in self.specs if not s.fully_specified]

    def report(self) -> str:
        complete = len(self.specs) - len(self.incompletely_specified())
        lines = [
            f"registry      : {self.name}",
            f"status        : {self.status}",
            f"dimensions    : {len(self.specs)}",
            f"fully specified semantics: {complete}/{len(self.specs)}",
        ]
        if self.provenance:
            lines.append(f"provenance    : {self.provenance}")
        for s in self.incompletely_specified():
            lines.append("  " + s.describe())
        return "\n".join(lines)


def get_registry(name: str = "canonical16") -> DofRegistry:
    """Return a named registry.

    ``canonical16``
        The 16-DOF shared vocabulary. Semantics are complete for the physical fields
        this project has established; validity is NOT uniform across members — consult
        ``db9_verdict`` on each spec.
    """
    if name == "canonical16":
        return DofRegistry(
            name="canonical16",
            specs=_canonical16_with_verdicts(),
            status="VOCABULARY — defines names, units and conventions. NOT a validity "
                   "claim about every member. Each spec's `db9_verdict` carries the "
                   "frozen audit outcome for its DB9 column.",
            provenance=(
                "DOF identities verified index-by-index against emg2pose/constants.py "
                "JOINTS and against DB9's in-file order_of_angles field. Per-channel "
                "physical validity is a separate result: see load_trusted_db9_subset()."
            ),
        )
    raise KeyError(f"unknown registry {name!r}; known: canonical16")


# --------------------------------------------------------------------------- #
# The frozen, physically audited DB9 subset
# --------------------------------------------------------------------------- #


def load_trusted_db9_subset(
    path: Path | str | None = None,
) -> DofRegistry:
    """Load ``TRUSTED_DB9_POSE_v1`` — the frozen DB9 physical-validity result.

    The artifact records that the subset was frozen *before any classifier ran*
    (``frozen_before_any_classifier: true``) and carries its own content hash. Both are
    surfaced on the returned registry so a consumer can see the ordering guarantee
    rather than being asked to trust it.

    Channels the audit DROPped or held INCONCLUSIVE are returned in
    ``registry.excluded`` style via :func:`trusted_db9_exclusions` rather than being
    dropped silently.
    """
    p = Path(path) if path is not None else TRUSTED_DB9_SUBSET_PATH
    if not p.exists():
        raise FileNotFoundError(
            f"frozen trusted subset not found at {p}. It is a required evidence "
            f"artifact, not a cache: re-run audits/db9/channel_forensic/tools/verdicts.py."
        )
    payload = json.loads(p.read_text(encoding="utf-8"))
    by_name = {s.name: s for s in _CANONICAL16}
    db9_to_canonical = {
        s.db9_channel: s.name for s in _CANONICAL16 if s.db9_channel is not None
    }

    specs: list[DofSpec] = []
    for entry in payload["keep"]:
        ch = str(entry["name"])
        canonical = db9_to_canonical.get(ch)
        if canonical is None:
            raise ValueError(
                f"trusted subset names DB9 channel {ch!r}, which canonical16 does not "
                f"map. Refusing to invent a DOF for it."
            )
        base = by_name[canonical]
        specs.append(
            DofSpec(
                name=base.name, finger=base.finger, joint=base.joint, axis=base.axis,
                unit=str(payload.get("unit", "deg")),
                positive_direction=base.positive_direction,
                zero_definition=str(payload.get("zero_definition", _DB9_ZERO)),
                handedness=base.handedness,
                emg2pose_index=base.emg2pose_index,
                db9_channel=ch,
                db9_index=int(entry["source_index"]),
                db9_verdict=AuditVerdict.KEEP,
                calibration_provenance=(
                    f"{_DB9_CALIB} Audit agreement with the official sign criterion: "
                    f"{float(entry.get('agreement_with_official_sign', float('nan'))):.4f} "
                    f"over n={entry.get('n_subjects')} subjects; "
                    f"confidence={entry.get('confidence')}; case={entry.get('case')}."
                ),
                note=str(entry.get("anchor", "")),
            )
        )

    reg = DofRegistry(
        name="TRUSTED_DB9_POSE_v1",
        specs=tuple(specs),
        status=(
            "FROZEN EVIDENCE — selected by physical validity rules only, with no "
            "reference to classification performance. Revalidated across all 77 DB9 "
            "participants under the frozen rules; the 8-channel subset was unchanged."
        ),
        provenance=(
            f"source {p.relative_to(REPO_ROOT).as_posix()} | plan_sha256 "
            f"{payload.get('plan_sha256')} | frozen_before_any_classifier="
            f"{payload.get('frozen_before_any_classifier')} | "
            f"commit={payload.get('commit')}"
        ),
    )
    return reg


def trusted_db9_exclusions(path: Path | str | None = None) -> dict[str, list[dict]]:
    """Return the ``DROP`` and ``INCONCLUSIVE`` channels, with the audit's own reasons.

    Exposed so that a consumer can distinguish "excluded because established broken"
    from "excluded because not established" — a distinction the project treats as
    load-bearing.
    """
    p = Path(path) if path is not None else TRUSTED_DB9_SUBSET_PATH
    payload = json.loads(p.read_text(encoding="utf-8"))
    out: dict[str, list[dict]] = {"DROP": [], "INCONCLUSIVE": []}
    for entry in payload.get("exclusion_list", []):
        status = str(entry.get("status", "")).strip().upper()
        bucket = "INCONCLUSIVE" if status == "INCONCLUSIVE" else "DROP"
        out[bucket].append(entry)
    for entry in payload.get("inconclusive_list", []):
        out["INCONCLUSIVE"].append({"status": "INCONCLUSIVE", **entry})
    return out


def db9_channel_verdicts(
    path: Path | str | None = None,
) -> dict[str, AuditVerdict]:
    """Frozen audit verdict for every released DB9 channel the audit ruled on.

    Returns ``{db9_channel_name: AuditVerdict}`` covering the 8 KEEP, 6 DROP and 8
    INCONCLUSIVE channels.

    This exists because the *historical* 16-DOF vocabulary contains channels the audit
    later DROPped. Re-reading a historical result without knowing which of its columns
    were dropped is how a defective channel gets silently re-adopted, so the vocabulary
    carries the verdicts rather than leaving them in a separate document.
    """
    p = Path(path) if path is not None else TRUSTED_DB9_SUBSET_PATH
    payload = json.loads(p.read_text(encoding="utf-8"))
    verdicts: dict[str, AuditVerdict] = {}
    for entry in payload.get("keep", []):
        verdicts[str(entry["name"])] = AuditVerdict.KEEP
    for entry in payload.get("exclusion_list", []):
        raw = str(entry.get("status", "")).strip().upper()
        verdicts[str(entry["name"])] = (
            AuditVerdict.INCONCLUSIVE
            if raw == "INCONCLUSIVE"
            else AuditVerdict.OFFICIAL_EXCLUSION
            if raw == "OFFICIAL_EXCLUSION" or entry.get("case") == "OFFICIAL_EXCLUSION"
            else AuditVerdict.DROP
        )
    for entry in payload.get("inconclusive_list", []):
        verdicts[str(entry["name"])] = AuditVerdict.INCONCLUSIVE
    return verdicts


def _canonical16_with_verdicts() -> tuple[DofSpec, ...]:
    """Attach the frozen per-channel audit verdicts to the canonical16 vocabulary.

    Note the semantic: ``AuditVerdict.DROP`` here means "the released DB9 column for
    this DOF is not the physical quantity it is named after". It says nothing about the
    emg2pose column of the same DOF, which is a different measurement from a different
    source with its own (unresolved) calibration provenance. Consumers that read a
    dimension from a non-DB9 source should consult the source's own audit rather than
    this verdict.
    """
    try:
        verdicts = db9_channel_verdicts()
    except FileNotFoundError:
        # A missing evidence artifact must not be silently treated as "all fine".
        return _CANONICAL16
    from dataclasses import replace

    out: list[DofSpec] = []
    for spec in _CANONICAL16:
        if spec.db9_channel is None or spec.db9_channel not in verdicts:
            out.append(spec)
            continue
        out.append(replace(spec, db9_verdict=verdicts[spec.db9_channel]))
    return tuple(out)


__all__ = [
    "Axis",
    "COMMON_POSE_SUBSET_V2_CANDIDATE_TIER1",
    "COMMON_POSE_SUBSET_V2_CANDIDATE_TIER2",
    "DofRegistry",
    "DofSpec",
    "Finger",
    "REPO_ROOT",
    "TRUSTED_DB9_SUBSET_PATH",
    "db9_channel_verdicts",
    "get_registry",
    "load_trusted_db9_subset",
    "trusted_db9_exclusions",
]
