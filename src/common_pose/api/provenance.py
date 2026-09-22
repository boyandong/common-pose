"""Calibration and extraction provenance for a pose stream.

The cross-dataset audit's load-bearing conclusion was that a shared pose API must carry
**per-channel calibration provenance**, not just the anatomical name: two datasets can
agree on DOF identity, unit and sign convention and still disagree by 2-40 deg in the
medians because the numbers were produced by different metrological processes.

Provenance here is therefore not decoration. A pose frame that cannot name where its
scale came from is a pose frame whose numbers cannot be compared with another dataset's,
and the interface says so rather than letting a consumer assume otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class Provenance:
    """Where a pose stream's numbers came from, and how far that is established.

    ``calibration_established`` is deliberately three-valued in effect:

    * ``True``  — the calibration chain was reproduced or documented independently.
    * ``False`` — a defect in the released calibration is established.
    * ``None``  — the chain is not independently closable (e.g. the raw gauges were
      never published). This is the majority case across the audited datasets and must
      not be rendered as either of the other two.
    """

    source_dataset: str
    """Human-readable dataset identity, e.g. ``Ninapro DB9`` (Exercise B)."""

    source_version: str | None = None
    """Release identifier, DOI, or archive hash as recorded by the audit."""

    source_identity: str | None = None
    """Subject / session / recording identity used to build this stream."""

    transform: str | None = None
    """The released transform, in words or as a formula, if recovered."""

    calibration_established: bool | None = None
    """``True`` reproduced, ``False`` established-defective, ``None`` not closable."""

    calibration_note: str = ""
    """Free-text reason, e.g. 'gains derived from 10 subjects and applied to 77;
    raw gauges unpublished, so parity cannot be independently closed'."""

    unit_conversion: str | None = None
    """Any unit conversion applied on the way into the frame, stated explicitly."""

    extracted_utc: str | None = None

    plan_sha256: str | None = None
    """Frozen audit-plan hash under which this source was assessed, when applicable."""

    code_version: str | None = None
    """Commit SHA or content-hash snapshot. ``COMMIT PENDING`` is an accepted value and
    means exactly what it says."""

    extras: Mapping[str, object] = field(default_factory=dict)

    def warnings(self) -> list[str]:
        """Human-readable caveats that must travel with the numbers."""
        out: list[str] = []
        if self.calibration_established is None:
            out.append(
                "calibration chain not independently closable for this source; "
                "numeric coordinate equivalence with any other source is UNVERIFIED"
            )
        elif self.calibration_established is False:
            out.append(
                "released calibration is established-defective for at least one "
                "dimension; per-dimension validity must be consulted"
            )
        if not self.transform:
            out.append("released transform not recovered/documented for this source")
        if not self.source_identity:
            out.append(
                "source identity not recorded; subject/session grouping cannot be "
                "audited from this frame alone"
            )
        return out


__all__ = ["Provenance"]
