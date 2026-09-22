"""The Common Pose container: a time-stamped stream of physical hand joint states.

Design intent
-------------
A consumer of hand pose should be able to ask, of the numbers it receives:

* what physical quantity is this, in what unit, with what sign, relative to what zero?
* was this value valid, and if not, in which of the three ways is it not valid?
* where did the scale come from, and can I compare it with another dataset's numbers?
* what were the recent values, if I need temporal state?

and get an answer from the object itself rather than from a sidebar document or an index
convention. That is what this module provides.

What this is NOT
----------------
This is not a streaming SDK, and the shape below is not a frozen wire format. The one
frozen thing in this project is the *DB9 trusted channel subset*
(``audits/db9/trusted_pose/TRUSTED_DB9_POSE_v1.json``); the container is deliberately
provisional so that it can still change as the adapters are built out.

Two traps this container is specifically shaped to prevent
----------------------------------------------------------
1. **Invalid poses encoded as zeros.** The emg2pose release encodes IK failures as
   all-zero ``joint_angles`` rows, not NaN — 15.6 percent of the official mini corpus.
   Zero is a legitimate angle (the extended hand), so a loader that treats zero as a
   pose silently trains on garbage. ``values`` here is therefore paired with a
   ``validity`` array that is never inferred from the values themselves.
2. **Native-rate inflation.** emg2pose's 2 kHz output holds only ``T/40`` independent
   values; the rest is linear interpolation. The true rate is carried in
   ``native_rate_hz`` alongside the sampling rate so a downstream window length can be
   chosen honestly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Mapping, Sequence

import numpy as np

from .dof import DofRegistry
from .provenance import Provenance
from .verdicts import (
    NOT_ESTABLISHED_CODE,
    VALIDITY_CODES,
    Validity,
    validity_from_code,
)


@dataclass
class PoseStream:
    """A time-stamped sequence of hand joint states in one anatomical vocabulary.

    Attributes
    ----------
    timestamps_s:
        ``(T,)`` seconds. Required and strictly increasing — a pose stream without a
        time base cannot be aligned with anything, which is the whole point.
    values:
        ``(T, len(registry))`` float64. Units are the registry's units, and are uniform
        across the frame; a mixed-unit frame is a bug, not a convenience.
    validity:
        ``(T, len(registry))`` int8 codes from
        :data:`~common_pose.api.verdicts.VALIDITY_CODES`. Never inferred from
        ``values``; supplied by the adapter that knows the source's own failure
        encoding. Stored as codes rather than as an ``object`` array because NumPy
        silently degrades ``str``-mixin enum members inside object arrays (see
        :class:`~common_pose.api.verdicts.Validity`). :meth:`validity_column` decodes
        back to members.
    registry:
        The vocabulary ``values`` columns are in.
    provenance:
        Where the numbers came from.
    native_rate_hz:
        The rate at which the upstream estimator actually updates, when it is lower than
        the sampling rate. ``None`` when the stream is not oversampled.
    """

    timestamps_s: np.ndarray
    values: np.ndarray
    registry: DofRegistry
    provenance: Provenance
    validity: np.ndarray | None = None
    sample_rate_hz: float | None = None
    native_rate_hz: float | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        t = np.asarray(self.timestamps_s, dtype=np.float64)
        v = np.asarray(self.values, dtype=np.float64)
        if t.ndim != 1:
            raise ValueError(f"timestamps_s must be 1-D, got shape {t.shape}")
        if v.ndim != 2:
            raise ValueError(f"values must be 2-D (T, D), got shape {v.shape}")
        if v.shape[0] != t.shape[0]:
            raise ValueError(
                f"values has {v.shape[0]} rows but timestamps_s has {t.shape[0]}"
            )
        if v.shape[1] != len(self.registry):
            raise ValueError(
                f"values has {v.shape[1]} columns but registry "
                f"{self.registry.name!r} has {len(self.registry)} dimensions; "
                f"a shape mismatch here means the vocabulary and the array disagree"
            )
        if t.size > 1 and not np.all(np.diff(t) > 0):
            raise ValueError("timestamps_s must be strictly increasing")

        if self.validity is None:
            validity = np.full(v.shape, NOT_ESTABLISHED_CODE, dtype=np.int8)
        else:
            validity = self._encode_validity(self.validity, v.shape)

        self.timestamps_s = t
        self.values = v
        self.validity = validity
        if self.sample_rate_hz is None and t.size > 1:
            self.sample_rate_hz = float(1.0 / np.median(np.diff(t)))

    @staticmethod
    def _encode_validity(raw: object, shape: tuple[int, int]) -> np.ndarray:
        """Coerce accepted validity inputs to int8 codes, refusing anything else.

        Accepts an int-code array, or an array of :class:`Validity` members. Strings
        are rejected outright: accepting ``"VALID"`` would let a caller who wrote the
        wrong string get a silently valid dimension, and accepting a NumPy-degraded
        object array would do the same. Both directions have to fail loudly.
        """
        arr = np.asarray(raw)
        if arr.shape != shape:
            raise ValueError(f"validity shape {arr.shape} != values shape {shape}")

        if arr.dtype == np.int8 or np.issubdtype(arr.dtype, np.integer):
            codes = arr.astype(np.int8, copy=True)
            # Validate every distinct code now, so an out-of-range code cannot sit in
            # the array until something happens to decode it.
            for code in np.unique(codes):
                validity_from_code(int(code))
            return codes

        obj = np.asarray(raw, dtype=object)
        codes = np.empty(shape, dtype=np.int8)
        for i in range(shape[0]):
            for j in range(shape[1]):
                cell = obj[i, j]
                if isinstance(cell, Validity):
                    codes[i, j] = cell.code
                else:
                    raise TypeError(
                        f"validity[{i}, {j}] must be a Validity member or an int code, "
                        f"got {type(cell).__name__}: {cell!r}. Refusing to coerce: a "
                        f"silently mis-parsed validity is a silent scientific error."
                    )
        return codes

    # -- shape helpers ------------------------------------------------------- #

    def __len__(self) -> int:
        return int(self.values.shape[0])

    @property
    def names(self) -> tuple[str, ...]:
        return self.registry.names

    def column(self, dof_name: str) -> np.ndarray:
        return self.values[:, self._col(dof_name)]

    def validity_column(self, dof_name: str) -> np.ndarray:
        """Return the dimension's validity as an array of :class:`Validity` members.

        Decoding happens here rather than being stored, because NumPy cannot hold
        ``str``-mixin enum members in an object array without degrading them.
        """
        codes = self.validity[:, self._col(dof_name)]
        return np.array([validity_from_code(int(c)) for c in codes], dtype=object)

    def _col(self, dof_name: str) -> int:
        try:
            return self.registry.names.index(dof_name)
        except ValueError as exc:
            raise KeyError(
                f"{dof_name!r} is not a dimension of this frame; frame carries "
                f"{', '.join(self.registry.names)}"
            ) from exc

    # -- selection ----------------------------------------------------------- #

    def select(self, dof_names: Sequence[str]) -> "PoseStream":
        """Return a frame carrying only ``dof_names``, preserving order."""
        cols = [self._col(n) for n in dof_names]
        specs = tuple(self.registry.specs[c] for c in cols)
        sub_registry = DofRegistry(
            name=f"{self.registry.name}::select[{len(cols)}]",
            specs=specs,
            status=self.registry.status,
            provenance=self.registry.provenance,
        )
        return PoseStream(
            timestamps_s=self.timestamps_s.copy(),
            values=self.values[:, cols].copy(),
            validity=self.validity[:, cols].copy(),
            registry=sub_registry,
            provenance=self.provenance,
            sample_rate_hz=self.sample_rate_hz,
            native_rate_hz=self.native_rate_hz,
            metadata=self.metadata,
        )

    def window(self, start_s: float, end_s: float) -> "PoseStream":
        """Half-open time window ``[start_s, end_s)``."""
        if end_s <= start_s:
            raise ValueError(f"empty/inverted window [{start_s}, {end_s})")
        mask = (self.timestamps_s >= start_s) & (self.timestamps_s < end_s)
        return PoseStream(
            timestamps_s=self.timestamps_s[mask].copy(),
            values=self.values[mask].copy(),
            validity=self.validity[mask].copy(),
            registry=self.registry,
            provenance=self.provenance,
            sample_rate_hz=self.sample_rate_hz,
            native_rate_hz=self.native_rate_hz,
            metadata=self.metadata,
        )

    def history(self, end_s: float, lookback_s: float) -> "PoseStream":
        """Recent history ending at ``end_s`` — the 'optional recent history' access
        pattern the interface is meant to support for temporal task heads."""
        return self.window(end_s - lookback_s, end_s)

    # -- honesty helpers ----------------------------------------------------- #

    def valid_fraction(self) -> Mapping[str, float]:
        """Per-dimension usable fraction. The first thing to look at before any
        statistic: a dimension that is 40 percent invalid will silently dominate an
        unmasked mean."""
        valid_code = VALIDITY_CODES[Validity.VALID]
        return {
            name: float(np.mean(self.validity[:, i] == valid_code))
            for i, name in enumerate(self.registry.names)
        }

    def mask(self) -> np.ndarray:
        """``(T, D)`` boolean usable-mask, AND-ed across dimensions.

        Use this for whole-frame statistics. For per-dimension statistics use
        :meth:`validity_column` instead — dropping a whole frame because one channel
        failed is a different (and usually worse) choice."""
        return self.validity == VALIDITY_CODES[Validity.VALID]

    def provenance_warnings(self) -> list[str]:
        return self.provenance.warnings()

    def describe(self) -> str:
        rate = f"{self.sample_rate_hz:.3f} Hz" if self.sample_rate_hz else "unknown"
        native = (
            f" (native update {self.native_rate_hz:.3f} Hz; intermediate samples are "
            f"interpolated)"
            if self.native_rate_hz
            else ""
        )
        lines = [
            f"PoseStream | {len(self)} frames x {len(self.registry)} dims | rate {rate}{native}",
            f"vocabulary : {self.registry.name}",
            f"source     : {self.provenance.source_dataset}",
            f"identity   : {self.provenance.source_identity}",
        ]
        frac = self.valid_fraction()
        weak = {k: v for k, v in frac.items() if v < 1.0}
        if weak:
            lines.append("dimensions below 100 percent valid:")
            for k, v in sorted(weak.items(), key=lambda kv: kv[1]):
                lines.append(f"  {k:<26} {v:.4f} usable")
        for w in self.provenance_warnings():
            lines.append(f"WARNING: {w}")
        return "\n".join(lines)


@dataclass
class PoseFrame:
    """One hand joint state at one instant.

    A single frame carries the same validity and provenance semantics as a stream, so a
    downstream task head can accept either without losing the ability to say no to a
    value.
    """

    t_s: float
    values: Mapping[str, float]
    registry: DofRegistry
    provenance: Provenance
    validity: Mapping[str, Validity] = field(default_factory=dict)

    def __post_init__(self) -> None:
        unknown = set(self.values) - set(self.registry.names)
        if unknown:
            raise KeyError(
                f"frame carries dimensions not in registry {self.registry.name!r}: "
                f"{sorted(unknown)}"
            )
        for name, cell in self.validity.items():
            if not isinstance(cell, Validity):
                raise TypeError(
                    f"validity[{name!r}] must be a Validity member, got "
                    f"{type(cell).__name__}"
                )

    def get(self, dof_name: str) -> tuple[float, Validity]:
        """Return ``(value, validity)``. There is no accessor that returns a bare number:
        the value and its interpretability are one object."""
        if dof_name not in self.values:
            return float("nan"), Validity.NOT_ESTABLISHED
        return (
            float(self.values[dof_name]),
            self.validity.get(dof_name, Validity.NOT_ESTABLISHED),
        )

    def as_array(self, dof_names: Sequence[str] | None = None) -> np.ndarray:
        names = tuple(dof_names) if dof_names is not None else self.registry.names
        return np.array(
            [self.values.get(n, np.nan) for n in names], dtype=np.float64
        )

    def describe(self) -> str:
        rows = []
        for name in self.registry.names:
            if name not in self.values:
                continue
            val, state = self.get(name)
            rows.append(f"  {name:<26} {val:>10.4f}  {state.value}")
        return "\n".join([f"PoseFrame t={self.t_s:.6f}s", *rows])


def frames_to_stream(
    frames: Sequence[PoseFrame],
    registry: DofRegistry | None = None,
    provenance: Provenance | None = None,
) -> PoseStream:
    """Collect frames into a stream. Frames must share one vocabulary."""
    if not frames:
        raise ValueError("no frames to collect")
    reg = registry or frames[0].registry
    prov = provenance or frames[0].provenance
    t = np.array([f.t_s for f in frames], dtype=np.float64)
    values = np.array(
        [[f.values.get(n, np.nan) for n in reg.names] for f in frames], dtype=np.float64
    )
    validity = np.array(
        [
            [
                (
                    f.validity[n].code
                    if isinstance(f.validity.get(n), Validity)
                    else NOT_ESTABLISHED_CODE
                )
                for n in reg.names
            ]
            for f in frames
        ],
        dtype=np.int8,
    )
    return PoseStream(
        timestamps_s=t, values=values, validity=validity,
        registry=reg, provenance=prov,
    )


def iter_frames(stream: PoseStream) -> Iterator[PoseFrame]:
    """Iterate a stream as single frames, preserving validity."""
    names = stream.registry.names
    for i in range(len(stream)):
        yield PoseFrame(
            t_s=float(stream.timestamps_s[i]),
            values={n: float(stream.values[i, j]) for j, n in enumerate(names)},
            validity={
                n: validity_from_code(int(stream.validity[i, j]))
                for j, n in enumerate(names)
            },
            registry=stream.registry,
            provenance=stream.provenance,
        )


__all__ = ["PoseFrame", "PoseStream", "frames_to_stream", "iter_frames"]
