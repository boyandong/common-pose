"""A shared canonical anatomical hand representation for emg2pose and Ninapro DB9.

WHY THIS EXISTS
---------------
The intended chain is

    emg2pose wrist EMG -> emg2pose pose model -> canonical hand state
                                              -> posture decoder trained on DB9

For that to mean anything, the 20 emg2pose numbers and the 22 CyberGlove
numbers must live in **one anatomical vocabulary**.  They must never be paired
by index, because the two orderings are structurally different:

* emg2pose publishes **20** finger DOF ordered
  *thumb* [CMC_FE, CMC_AA, MCP_FE, IP_FE], then per finger
  [MCP_AA, MCP_FE, PIP_FE, DIP_FE] for index -> pinky.
  (Verified index-by-index against ``emg2pose/constants.py::JOINTS``; see
  the project's ``docs/joint_angle_definition.md``.)
* Ninapro DB9 publishes **22** CyberGlove-II channels in a *grouped* order that
  is NOT "5 fingers x 4 joints".  Read verbatim from the recording's own
  ``order_of_angles`` variable -- four thumb channels, then the flexion chain
  of fingers 2-5 interleaved with their abduction sensors, then all four DIP
  sensors together, then two wrist channels.  Consecutive index ≠ same joint.

HOW THE MAPPING WAS ESTABLISHED (evidence, not assumption)
----------------------------------------------------------
Every DB9 channel name below is copied from the ``order_of_angles`` variable
inside the official archives, e.g. ``s_1_angles/S1_E2_A1.mat``:

    1:CMC1_f  2:CMC1_a  3:MCP1   4:IP1    5:MCP2_f  6:MCP2_a  7:PIP2
    8:MCP3_f  9:PIP3   10:MCP4_f 11:MCP4_a 12:PIP4   13:CMC5   14:MCP5_f
    15:MCP5_a 16:PIP5  17:DIP2   18:DIP3   19:DIP4   20:DIP5   21:WRIST_F
    22:WRIST_A

Two facts were then checked against the data rather than taken on trust:

1. The official DB9 docs state that the index-middle abduction sensor
   (MCP2-3_A) "was not included into the calibrated data due to noise
   problems".  Consistent with that, column ``6:MCP2_a`` is **all-NaN in every
   recording examined**, and it is the only such column.  So the excluded
   sensor is confirmed to be the *index* abduction channel.
2. There is **no middle-finger abduction channel at all** in the 22-channel
   CyberGlove set, and no palm-arch channel.  Those canonical DOF therefore
   have no DB9 counterpart by construction, not by measurement failure.

The upshot is that exactly **18** canonical DOF are observable in both
datasets.  That number is a result, not a design choice, and
``coverage_report()`` prints the reason for every gap.

UNITS
-----
emg2pose joint angles are **radians**; DB9 calibrated ``angles`` are
**degrees** (measured: global range -322..+173 over subject 1, which is only
sensible in degrees).  ``db9_degrees_to_canonical`` performs the conversion
explicitly so a unit error cannot hide inside an index mapping.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Literal

Axis = Literal["FE", "AA"]
Finger = Literal["thumb", "index", "middle", "ring", "pinky", "wrist", "palm"]

#: The 22 official DB9 CyberGlove channel names, in column order, exactly as
#: they appear in every recording's ``order_of_angles`` variable.  The leading
#: "N:" is stripped here; `strip_index_prefix` handles both forms.
DB9_CHANNEL_ORDER: tuple[str, ...] = (
    "CMC1_f", "CMC1_a", "MCP1", "IP1",
    "MCP2_f", "MCP2_a", "PIP2",
    "MCP3_f", "PIP3",
    "MCP4_f", "MCP4_a", "PIP4",
    "CMC5", "MCP5_f", "MCP5_a", "PIP5",
    "DIP2", "DIP3", "DIP4", "DIP5",
    "WRIST_F", "WRIST_A",
)

#: Channel documented (and measured) to be unusable in the calibrated data.
DB9_EXCLUDED_CHANNELS: dict[str, str] = {
    "MCP2_a": (
        "All-NaN in every recording examined. Official DB9 docs: 'Sensor 11 "
        "(which corresponds to MCP2-3_A) was not included into the calibrated "
        "data due to noise problems.'"
    ),
}

#: Units of each dataset's published angles, established by measurement.
EMG2POSE_UNIT = "rad"
DB9_UNIT = "deg"


def strip_index_prefix(name: str) -> str:
    """'6:MCP2_a' -> 'MCP2_a'. Tolerates names without a numeric prefix."""
    s = str(name).strip()
    if ":" in s:
        head, _, tail = s.partition(":")
        if head.strip().isdigit():
            return tail.strip()
    return s


@dataclass(frozen=True)
class CanonicalDof:
    """One anatomically-named degree of freedom in the shared vocabulary."""

    name: str
    finger: Finger
    joint: str
    axis: str
    #: emg2pose column index, or None when emg2pose does not publish it.
    emg2pose_index: int | None = None
    #: Official DB9 CyberGlove channel name, or None when DB9 lacks it.
    db9_channel: str | None = None
    note: str = ""
    emg2pose_gap: str = ""
    db9_gap: str = ""

    @property
    def in_emg2pose(self) -> bool:
        return self.emg2pose_index is not None

    @property
    def in_db9(self) -> bool:
        return self.db9_channel is not None and self.db9_channel not in DB9_EXCLUDED_CHANNELS

    @property
    def db9_index(self) -> int | None:
        if self.db9_channel is None:
            return None
        return DB9_CHANNEL_ORDER.index(self.db9_channel)

    @property
    def shared(self) -> bool:
        return self.in_emg2pose and self.in_db9


CANONICAL_DOFS: tuple[CanonicalDof, ...] = (
    # ---- thumb: 4 DOF, all present on both sides ---------------------------
    CanonicalDof("THUMB_CMC_FE", "thumb", "CMC", "FE", 0, "CMC1_f",
                 note="Thumb carpometacarpal flexion/extension."),
    CanonicalDof("THUMB_CMC_AA", "thumb", "CMC", "AA", 1, "CMC1_a",
                 note="Thumb carpometacarpal abduction/adduction."),
    CanonicalDof("THUMB_MCP_FE", "thumb", "MCP", "FE", 2, "MCP1"),
    CanonicalDof("THUMB_IP_FE", "thumb", "IP", "FE", 3, "IP1"),
    # ---- index ------------------------------------------------------------
    CanonicalDof(
        "INDEX_MCP_AA", "index", "MCP", "AA", 4, "MCP2_a",
        db9_gap=DB9_EXCLUDED_CHANNELS["MCP2_a"],
    ),
    CanonicalDof("INDEX_MCP_FE", "index", "MCP", "FE", 5, "MCP2_f"),
    CanonicalDof("INDEX_PIP_FE", "index", "PIP", "FE", 6, "PIP2"),
    CanonicalDof("INDEX_DIP_FE", "index", "DIP", "FE", 7, "DIP2"),
    # ---- middle -----------------------------------------------------------
    CanonicalDof(
        "MIDDLE_MCP_AA", "middle", "MCP", "AA", 8, None,
        db9_gap=(
            "The 22-channel CyberGlove-II set contains abduction sensors for "
            "index, ring and pinky only (MCP2_a, MCP4_a, MCP5_a). There is no "
            "middle-finger abduction channel, so this DOF is unobservable in "
            "DB9 by construction."
        ),
    ),
    CanonicalDof("MIDDLE_MCP_FE", "middle", "MCP", "FE", 9, "MCP3_f"),
    CanonicalDof("MIDDLE_PIP_FE", "middle", "PIP", "FE", 10, "PIP3"),
    CanonicalDof("MIDDLE_DIP_FE", "middle", "DIP", "FE", 11, "DIP3"),
    # ---- ring -------------------------------------------------------------
    CanonicalDof("RING_MCP_AA", "ring", "MCP", "AA", 12, "MCP4_a"),
    CanonicalDof("RING_MCP_FE", "ring", "MCP", "FE", 13, "MCP4_f"),
    CanonicalDof("RING_PIP_FE", "ring", "PIP", "FE", 14, "PIP4"),
    CanonicalDof("RING_DIP_FE", "ring", "DIP", "FE", 15, "DIP4"),
    # ---- pinky ------------------------------------------------------------
    CanonicalDof("PINKY_MCP_AA", "pinky", "MCP", "AA", 16, "MCP5_a"),
    CanonicalDof("PINKY_MCP_FE", "pinky", "MCP", "FE", 17, "MCP5_f"),
    CanonicalDof("PINKY_PIP_FE", "pinky", "PIP", "FE", 18, "PIP5"),
    CanonicalDof("PINKY_DIP_FE", "pinky", "DIP", "FE", 19, "DIP5"),
    # ---- DB9-only ---------------------------------------------------------
    CanonicalDof(
        "PINKY_CMC_FE", "pinky", "CMC", "FE", None, "CMC5",
        note="Fifth carpometacarpal (hypothenar) sensor. Present only on the glove.",
        emg2pose_gap=(
            "emg2pose's 20 outputs contain no pinky CMC channel; its hand model "
            "treats the pinky chain as MCP/PIP/DIP only."
        ),
    ),
    CanonicalDof(
        "WRIST_FE", "wrist", "wrist", "FE", None, "WRIST_F",
        note="Wrist flexion/extension, carried on the glove itself.",
        emg2pose_gap=(
            "emg2pose does not regress wrist angles: 'We do not regress to wrist "
            "angles, which were not recorded for this dataset.' "
            "kinematics.forward_kinematics appends two zeros for the wrist."
        ),
    ),
    CanonicalDof(
        "WRIST_DEV", "wrist", "wrist", "DEV", None, "WRIST_A",
        note="Wrist abduction/adduction (radial/ulnar deviation).",
        emg2pose_gap="Same as WRIST_FE: not recorded by emg2pose.",
    ),
)

BY_NAME: dict[str, CanonicalDof] = {d.name: d for d in CANONICAL_DOFS}
BY_DB9_CHANNEL: dict[str, CanonicalDof] = {
    d.db9_channel: d for d in CANONICAL_DOFS if d.db9_channel
}

#: emg2pose's published ordering, duplicated here so this module stands alone.
#: `verify_emg2pose_order()` asserts the two agree.
EMG2POSE_ORDER: tuple[str, ...] = (
    "THUMB_CMC_FE", "THUMB_CMC_AA", "THUMB_MCP_FE", "THUMB_IP_FE",
    "INDEX_MCP_AA", "INDEX_MCP_FE", "INDEX_PIP_FE", "INDEX_DIP_FE",
    "MIDDLE_MCP_AA", "MIDDLE_MCP_FE", "MIDDLE_PIP_FE", "MIDDLE_DIP_FE",
    "RING_MCP_AA", "RING_MCP_FE", "RING_PIP_FE", "RING_DIP_FE",
    "PINKY_MCP_AA", "PINKY_MCP_FE", "PINKY_PIP_FE", "PINKY_DIP_FE",
)


def verify_emg2pose_order() -> None:
    got = tuple(
        d.name
        for d in sorted(
            (d for d in CANONICAL_DOFS if d.in_emg2pose),
            key=lambda d: d.emg2pose_index,  # type: ignore[arg-type,return-value]
        )
    )
    if got != EMG2POSE_ORDER:
        raise AssertionError(
            "canonical -> emg2pose mapping does not reproduce the official "
            f"ordering.\n  canonical: {list(got)}\n  official : {list(EMG2POSE_ORDER)}"
        )


def verify_db9_order(order_of_angles: Iterable[str]) -> list[str]:
    """Check a recording's own ``order_of_angles`` against the known table.

    Returns a list of human-readable problems (empty == clean).  Reported, never
    silently repaired: an unexpected channel name means either a naming variant
    we have not seen or a file that is not the DB9 we think it is.
    """
    problems: list[str] = []
    names = [strip_index_prefix(n) for n in order_of_angles if str(n).strip()]
    if len(names) != len(DB9_CHANNEL_ORDER):
        problems.append(
            f"expected {len(DB9_CHANNEL_ORDER)} channels, file declares {len(names)}"
        )
    for i, (got, want) in enumerate(zip(names, DB9_CHANNEL_ORDER)):
        if got != want:
            problems.append(f"column {i}: file says {got!r}, table says {want!r}")
    for extra in names[len(DB9_CHANNEL_ORDER):]:
        problems.append(f"unexpected extra channel {extra!r}")
    return problems


def shared_dofs() -> tuple[CanonicalDof, ...]:
    """Canonical DOF observable in BOTH datasets -- the only safe bridge."""
    return tuple(d for d in CANONICAL_DOFS if d.shared)


# ===========================================================================
# FROZEN REPRESENTATIONS FOR THE EXPERIMENTS
# ===========================================================================
# ``canonical16`` is the representation frozen for the first experiment: the
# shared kinematics *without* any inter-finger spread feature.  ``canonical18``
# is the same thing plus the two spread features that are genuinely reliable in
# both datasets.  canonical18 is a strict column-wise extension of canonical16
# (the first 16 columns are identical, the 2 spread columns are appended), so
# enabling them later is a one-argument change and never a rewrite.
#
# WHY EXACTLY THESE TWO SPREAD FEATURES
# -------------------------------------
# The candidate shared spread DOF are the four MCP abduction channels.  Only two
# survive as *reliable*:
#   * INDEX_MCP_AA  -- emg2pose publishes it, but DB9's channel `6:MCP2_a` is
#                      all-NaN: officially "not included into the calibrated
#                      data due to noise problems".  NOT reliable.
#   * MIDDLE_MCP_AA -- emg2pose publishes it, but the 22-channel CyberGlove has
#                      no middle-finger abduction sensor at all.  NOT available.
#   * RING_MCP_AA   -- present and calibrated in both.  RELIABLE.
#   * PINKY_MCP_AA  -- present and calibrated in both.  RELIABLE.
# Hence canonical18 = canonical16 + {RING_MCP_AA, PINKY_MCP_AA}.
CORE_16_NAMES: tuple[str, ...] = (
    # thumb: 4 DOF
    "THUMB_CMC_FE", "THUMB_CMC_AA", "THUMB_MCP_FE", "THUMB_IP_FE",
    # index: MCP / PIP / DIP flexion
    "INDEX_MCP_FE", "INDEX_PIP_FE", "INDEX_DIP_FE",
    # middle
    "MIDDLE_MCP_FE", "MIDDLE_PIP_FE", "MIDDLE_DIP_FE",
    # ring
    "RING_MCP_FE", "RING_PIP_FE", "RING_DIP_FE",
    # pinky
    "PINKY_MCP_FE", "PINKY_PIP_FE", "PINKY_DIP_FE",
)

#: The two spread features that can be switched on later without touching the
#: pipeline.  Chosen by elimination, documented above.
OPTIONAL_SPREAD_NAMES: tuple[str, ...] = ("RING_MCP_AA", "PINKY_MCP_AA")

REPRESENTATIONS: dict[str, tuple[str, ...]] = {
    "canonical16": CORE_16_NAMES,
    "canonical18": CORE_16_NAMES + OPTIONAL_SPREAD_NAMES,
    #: Everything DB9 can give (includes glove-only wrist + pinky CMC). Kept
    #: only as an upper-bound reference; it is NOT shared with emg2pose.
    "db9full21": tuple(d.name for d in CANONICAL_DOFS if d.in_db9),
}

assert len(CORE_16_NAMES) == 16
assert len(REPRESENTATIONS["canonical18"]) == 18
assert REPRESENTATIONS["canonical18"][:16] == CORE_16_NAMES, (
    "canonical18 must be a strict column-wise extension of canonical16"
)
for _n in REPRESENTATIONS["canonical16"] + REPRESENTATIONS["canonical18"]:
    if _n not in BY_NAME:
        raise AssertionError(f"representation references unknown canonical DOF {_n!r}")
for _n in OPTIONAL_SPREAD_NAMES:
    if not (BY_NAME[_n].in_emg2pose and BY_NAME[_n].in_db9):
        raise AssertionError(
            f"{_n} is listed as an optional spread feature but is not reliable "
            "in both datasets"
        )


def representation_names(representation: str) -> tuple[str, ...]:
    if representation not in REPRESENTATIONS:
        raise KeyError(
            f"unknown representation {representation!r}; "
            f"expected one of {sorted(REPRESENTATIONS)}"
        )
    return REPRESENTATIONS[representation]


def representation_emg2pose_indices(representation: str) -> list[int]:
    """emg2pose column indices for a representation, in canonical order."""
    out = []
    for n in representation_names(representation):
        d = BY_NAME[n]
        if not d.in_emg2pose:
            raise KeyError(f"{n} is not observable in emg2pose")
        out.append(d.emg2pose_index)  # type: ignore[arg-type]
    return out


def representation_db9_indices(representation: str) -> list[int]:
    """DB9 column indices for a representation, in canonical order."""
    out = []
    for n in representation_names(representation):
        d = BY_NAME[n]
        if not d.in_db9:
            raise KeyError(f"{n} is not observable in DB9")
        out.append(d.db9_index)  # type: ignore[arg-type]
    return out


def db9_degrees_to_representation(
    angles_22_deg, representation: str = "canonical16", *, radians: bool = True
):
    """(..., 22) DB9 degrees -> (..., D) in the requested representation.

    Column order follows :data:`REPRESENTATIONS` exactly, so ``canonical18``
    simply appends the two spread features to the ``canonical16`` columns.
    """
    import numpy as np

    a = np.asarray(angles_22_deg, dtype=float)
    if a.shape[-1] != len(DB9_CHANNEL_ORDER):
        raise ValueError(f"expected last axis 22 (DB9 channels), got {a.shape}")
    cols = representation_db9_indices(representation)
    out = a[..., cols]
    if radians:
        out = np.radians(out)
    return out


def emg2pose_to_representation(
    angles_20, representation: str = "canonical16", *, degrees: bool = False
):
    """(..., 20) emg2pose angles -> (..., D) in the requested representation."""
    import numpy as np

    a = np.asarray(angles_20, dtype=float)
    if a.shape[-1] != 20:
        raise ValueError(f"expected last axis 20 (emg2pose joints), got {a.shape}")
    cols = representation_emg2pose_indices(representation)
    out = a[..., cols]
    return np.degrees(out) if degrees else out


def db9_split_core_and_optional(angles_22_deg, *, radians: bool = True):
    """Return ``(core16, optional_spread2, names16, names2)``.

    Provided so that switching the optional spread features on later is a
    concatenation rather than a refactor: nothing upstream needs to change.
    """
    core = db9_degrees_to_representation(angles_22_deg, "canonical16", radians=radians)
    opt = db9_degrees_to_representation(angles_22_deg, "canonical18",
                                        radians=radians)[..., 16:]
    return core, opt, CORE_16_NAMES, OPTIONAL_SPREAD_NAMES


# --- back-compatible helpers (pre-freeze names) ----------------------------
def shared_emg2pose_indices() -> list[int]:
    return representation_emg2pose_indices("canonical16")


def db9_shared_matrix(angles_N22_deg, *, radians: bool = True):
    """Deprecated alias for the canonical16 projection."""
    names = representation_names("canonical16")
    m = db9_degrees_to_representation(angles_N22_deg, "canonical16", radians=radians)
    import numpy as np

    return m, list(names), np.isfinite(m)


def canonical_to_emg2pose_vector(state: dict[str, float], *, degrees: bool = False):
    """Render a canonical state as emg2pose's 20-D vector.

    DOF that emg2pose does not publish are ignored; DOF missing from ``state``
    raise, so a silently-zero-filled vector is impossible.
    """
    import numpy as np

    out = np.full(20, np.nan, dtype=float)
    for d in CANONICAL_DOFS:
        if d.emg2pose_index is None:
            continue
        if d.name not in state:
            raise KeyError(f"canonical state is missing {d.name}")
        out[d.emg2pose_index] = state[d.name]
    if degrees:
        out = np.degrees(out)
    return out


def emg2pose_vector_to_canonical(angles_20, *, degrees: bool = False) -> dict[str, float]:
    """Name the 20 emg2pose numbers. No rescaling beyond an optional unit change."""
    import numpy as np

    a = np.asarray(angles_20, dtype=float).reshape(-1)
    if a.size != 20:
        raise ValueError(f"emg2pose angles must be 20-D, got {a.size}")
    if degrees:
        a = np.degrees(a)
    return {
        d.name: float(a[d.emg2pose_index])
        for d in CANONICAL_DOFS
        if d.emg2pose_index is not None
    }


def db9_degrees_to_canonical(angles_22_deg, *, radians: bool = True) -> dict[str, float]:
    """Name the 22 DB9 numbers and convert degrees -> radians.

    The unit conversion is explicit and named, because the two datasets differ
    (emg2pose radians, DB9 degrees) and a missing conversion would look like a
    plausible-but-wrong model rather than an error.
    """
    import numpy as np

    a = np.asarray(angles_22_deg, dtype=float).reshape(-1)
    if a.size != len(DB9_CHANNEL_ORDER):
        raise ValueError(f"DB9 angles must be 22-D, got {a.size}")
    out: dict[str, float] = {}
    for d in CANONICAL_DOFS:
        if d.db9_channel is None:
            continue
        v = float(a[DB9_CHANNEL_ORDER.index(d.db9_channel)])
        if radians:
            v = math.radians(v) if math.isfinite(v) else float("nan")
        out[d.name] = v
    return out


def db9_shared_matrix(angles_N22_deg, *, radians: bool = True):
    """(N, 22) DB9 degrees -> (N, 18) canonical shared DOF, in canonical order.

    Returns ``(matrix, names, mask)`` where ``mask`` marks finite entries.  The
    excluded MCP2_a channel is dropped here and only here, via the canonical
    table -- never by ad-hoc column slicing at a call site.
    """
    import numpy as np

    a = np.asarray(angles_N22_deg, dtype=float)
    if a.ndim != 2 or a.shape[1] != len(DB9_CHANNEL_ORDER):
        raise ValueError(f"expected (N, 22) DB9 angles, got {a.shape}")
    cols = [d.db9_index for d in shared_dofs()]
    names = [d.name for d in shared_dofs()]
    m = a[:, cols].copy()
    if radians:
        m = np.radians(m)
    return m, names, np.isfinite(m)


def coverage_report() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for d in CANONICAL_DOFS:
        rows.append(
            {
                "canonical": d.name,
                "finger": d.finger,
                "joint": d.joint,
                "axis": d.axis,
                "emg2pose_index": d.emg2pose_index,
                "db9_channel": d.db9_channel,
                "db9_index": d.db9_index,
                "in_emg2pose": d.in_emg2pose,
                "in_db9": d.in_db9,
                "shared": d.shared,
                "emg2pose_gap": d.emg2pose_gap,
                "db9_gap": d.db9_gap,
                "note": d.note,
            }
        )
    return rows


if __name__ == "__main__":  # pragma: no cover
    verify_emg2pose_order()
    n_e = sum(1 for d in CANONICAL_DOFS if d.in_emg2pose)
    n_b = sum(1 for d in CANONICAL_DOFS if d.in_db9)
    print(f"official DB9 channels        : {len(DB9_CHANNEL_ORDER)}")
    print(f"canonical DOF slots          : {len(CANONICAL_DOFS)}")
    print(f"  observable in emg2pose     : {n_e}")
    print(f"  observable in DB9          : {n_b}")
    print(f"  SHARED (safe bridge)       : {len(shared_dofs())}")
    print()
    for r in coverage_report():
        e = f"e{r['emg2pose_index']:>2}" if r["in_emg2pose"] else "  -"
        b = f"b{r['db9_index']:>2}" if r["in_db9"] else "  -"
        mark = "SHARED" if r["shared"] else "      "
        print(f"  {mark} {r['canonical']:<16s} {e} {b}  {r['db9_channel'] or ''}")
    print()
    print("emg2pose-only:", [d.name for d in CANONICAL_DOFS if d.in_emg2pose and not d.in_db9])
    print("DB9-only     :", [d.name for d in CANONICAL_DOFS if d.in_db9 and not d.in_emg2pose])
    print()
    for rep in ("canonical16", "canonical18"):
        names = representation_names(rep)
        print(f"{rep} ({len(names)}D):")
        for i, n in enumerate(names):
            d = BY_NAME[n]
            print(f"   [{i:2d}] {n:<16s} emg2pose#{d.emg2pose_index:<2} "
                  f"db9#{d.db9_index} ({d.db9_channel})")
        print(f"   emg2pose indices: {representation_emg2pose_indices(rep)}")
        print(f"   db9      indices: {representation_db9_indices(rep)}")
        print()
    print("optional spread features (off in canonical16, on in canonical18):")
    for n in OPTIONAL_SPREAD_NAMES:
        print(f"   {n}: emg2pose#{BY_NAME[n].emg2pose_index}, DB9 {BY_NAME[n].db9_channel}")
