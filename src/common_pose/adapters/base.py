"""Adapter contract.

The contract exists to make one class of silent error impossible: an adapter that produces
a plausible-looking pose array whose columns are not the physical quantities they are
labelled as. That failure has occurred in this project's history — a ten-column subset
whose index vector was taken from the wrong document, mislabelling four of ten channels —
and it is invisible to every downstream metric.

So :meth:`PoseAdapter.validate` is not optional and not a smoke test. It asserts that:

1. every emitted column has a registry entry with complete physical semantics;
2. every dimension's dataset-level audit verdict is known, not assumed;
3. the validity array is supplied by the adapter rather than inferred from values;
4. a ``DROP``ped channel is not emitted silently **from the source that verdict is about**.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Sequence

from ..api.dof import DofRegistry
from ..api.verdicts import AuditVerdict

if TYPE_CHECKING:  # pragma: no cover
    from ..api.pose_frame import PoseStream


@dataclass(frozen=True)
class AdapterCapability:
    """What a source is actually able to carry — as opposed to what it is named.

    Filled in from the audits, not from hope. A downstream task head can read this and
    know whether a dimension it needs is genuinely available before it is fed a column of
    NaN.
    """

    source: str
    dimensions_present: Sequence[str]
    dimensions_absent: Sequence[str] = ()
    dimensions_restricted: Sequence[str] = ()
    """Present as a column but not admitted as the named physical quantity."""

    native_rate_hz: float | None = None
    declared_rate_hz: float | None = None
    """When this exceeds ``native_rate_hz``, the difference is interpolation, not
    information. Recorded because one audited dataset inflated its kinematic stream by
    56x and published it on a 2 kHz grid."""

    has_emg: bool = False

    db9_verdicts_are_authoritative: bool = False
    """Whether the DB9 audit verdicts on the emitted dimensions describe *this*
    adapter's columns.

    ``True`` only for adapters that emit the released DB9 array. For any other source the
    verdict is about a different physical measurement of the same anatomical DOF, and
    applying it here would be a category error — an emg2pose column is not the DB9
    CyberGlove column, and its own calibration provenance is unresolved rather than
    DROPped."""

    notes: Sequence[str] = field(default_factory=tuple)

    @property
    def inflation_factor(self) -> float | None:
        if not self.declared_rate_hz or not self.native_rate_hz:
            return None
        return self.declared_rate_hz / self.native_rate_hz


class AdapterError(RuntimeError):
    """Raised when a source cannot be mapped without inventing information."""


class PoseAdapter(abc.ABC):
    """Base class for dataset -> Common Pose adapters."""

    #: Registry the adapter's output frame is expressed in.
    registry: DofRegistry

    @property
    @abc.abstractmethod
    def capability(self) -> AdapterCapability:
        """Which dimensions this source can actually carry."""

    @abc.abstractmethod
    def load(self, *args, **kwargs) -> "PoseStream":
        """Produce a :class:`~common_pose.api.pose_frame.PoseStream`."""

    # -- contract ------------------------------------------------------------ #

    def validate(self, stream: "PoseStream") -> list[str]:
        """Check the emitted stream against the adapter contract.

        Returns a list of problems. An empty list means the contract holds. Callers that
        treat a non-empty list as non-fatal are making a scientific choice, and should
        say so explicitly at the call site.
        """
        problems: list[str] = []

        if stream.registry.name != self.registry.name:
            problems.append(
                f"stream vocabulary {stream.registry.name!r} does not match adapter "
                f"vocabulary {self.registry.name!r}"
            )

        absent = set(self.capability.dimensions_absent)
        for spec in stream.registry.specs:
            if not spec.fully_specified and spec.name not in absent:
                problems.append(
                    f"{spec.name}: physical semantics incomplete "
                    f"({', '.join(_missing_semantics(spec))}). Every emitted dimension "
                    f"must answer unit / sign / zero / handedness / calibration"
                )
            if (
                spec.db9_verdict is AuditVerdict.DROP
                and self.capability.db9_verdicts_are_authoritative
            ):
                problems.append(
                    f"{spec.name}: emitted from the DB9 release although the frozen "
                    f"audit DROPped that channel. A dropped channel must not be "
                    f"emitted silently; mark it INVALID or select it out explicitly."
                )

        if stream.validity is None:
            problems.append(
                "no validity array: validity must be supplied by the adapter, never "
                "inferred from the values. Zero-invalid and zero-valued are different "
                "things and this project has already been bitten by the difference."
            )

        unexpected = set(stream.registry.names) - set(self.capability.dimensions_present)
        if unexpected:
            problems.append(
                f"emitted dimensions not declared in capability: {sorted(unexpected)}"
            )

        return problems

    def assert_valid(self, stream: "PoseStream") -> None:
        problems = self.validate(stream)
        if problems:
            raise AdapterError(
                f"{type(self).__name__} produced a stream that violates the adapter "
                f"contract:\n  - " + "\n  - ".join(problems)
            )


def _missing_semantics(spec) -> list[str]:
    return [
        k
        for k, v in (
            ("positive_direction", spec.positive_direction),
            ("zero_definition", spec.zero_definition),
            ("handedness", spec.handedness),
            ("calibration_provenance", spec.calibration_provenance),
        )
        if v is None
    ]


__all__ = ["AdapterCapability", "AdapterError", "PoseAdapter"]
