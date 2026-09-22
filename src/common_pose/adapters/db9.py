"""Ninapro DB9 -> Common Pose adapter (Exercise B).

Three things here are the result of an audit and are not negotiable
------------------------------------------------------------------
1. **Segmentation uses ``restimulus`` x ``rerepetition``.** The field named
   ``repetition`` is the *pre-relabelling* acquisition vector and is length-mismatched
   with ``glove``/``angles`` in 24 of 99 released files. Indexing kinematics with it shifts
   every movement boundary. The field named ``stimulus`` has the same defect.
2. **Channel order comes from the file's own ``order_of_angles``**, not from a secondary
   document. An audit found a ten-column subset whose index vector had been taken from a
   later guide describing a different dataset, mislabelling four of ten channels — a
   defect invisible to every classification metric.
3. **The trusted subset verdicts are carried per dimension.** A ``DROP``ped channel is
   never quietly replaced by zero.

Released arrays are never modified. No sign flip, offset, affine alignment or rescaling is
applied here; where the released representation is established-defective, the verdict says
so and the value is emitted as ``INVALID`` rather than repaired.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

from ..api.dof import DofRegistry, get_registry, load_trusted_db9_subset
from ..api.pose_frame import PoseStream
from ..api.provenance import Provenance
from ..api.verdicts import (
    NOT_ESTABLISHED_CODE,
    VALIDITY_CODES,
    AuditVerdict,
    Validity,
)
from .base import AdapterCapability, AdapterError, PoseAdapter

#: Official DB9 CyberGlove channel names in released column order, as stored in each
#: recording's ``order_of_angles`` variable. The leading ``N:`` is stripped.
DB9_CHANNEL_ORDER: tuple[str, ...] = (
    "CMC1_f", "CMC1_a", "MCP1", "IP1",
    "MCP2_f", "MCP2_a", "PIP2",
    "MCP3_f", "PIP3",
    "MCP4_f", "MCP4_a", "PIP4",
    "CMC5", "MCP5_f", "MCP5_a", "PIP5",
    "DIP2", "DIP3", "DIP4", "DIP5",
    "WRIST_F", "WRIST_A",
)

#: Channel excluded by the vendor's own documentation. All-NaN in every recording.
DB9_VENDOR_EXCLUDED: Mapping[str, str] = {
    "MCP2_a": (
        "Ninapro usage notes: 'Sensor 11 (which corresponds to MCP2-3_A) was not "
        "included into the calibrated data due to noise problems.' The released "
        "angles[:, 5] column is all-NaN."
    ),
}

#: Exercise-B movement ids that are wrist movements rather than hand shapes. The trusted
#: subset contains no wrist channel by construction, so a 17-class Exercise-B task mixes
#: two targets and penalises the subset for a quantity it does not carry.
DB9_EXERCISE_B_WRIST_MOVEMENTS: tuple[int, ...] = (9, 10, 11, 12, 13, 14, 15, 16)

#: Exercise-B hand-shape movement ids.
DB9_EXERCISE_B_HANDSHAPE_MOVEMENTS: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8, 17)


def load_order_of_angles(mat_path: Path | str) -> list[str]:
    """Read the channel-order declaration stored inside a DB9 ``.mat``.

    There is no fallback to a hardcoded order. If the file does not declare its order, the
    adapter refuses: guessing the order from an index convention is the exact failure this
    project already made once.
    """
    try:
        from scipy.io import loadmat  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise AdapterError(
            "scipy is required to read DB9 .mat files. Install with "
            "`pip install scipy` (see requirements.txt)."
        ) from exc

    mat = loadmat(str(mat_path), squeeze_me=True, struct_as_record=False)
    if "order_of_angles" not in mat:
        raise AdapterError(
            f"{Path(mat_path).name} does not contain 'order_of_angles'. This adapter "
            f"refuses to guess the channel order from an index convention; that failure "
            f"mode is documented in audits/db9/coordinate_audit."
        )
    raw = mat["order_of_angles"]
    names: list[str] = []
    for item in np.atleast_1d(raw).ravel():
        s = str(item).strip()
        if ":" in s and s.split(":", 1)[0].strip().isdigit():
            s = s.split(":", 1)[1].strip()
        names.append(s)
    return names


@dataclass
class DB9Adapter(PoseAdapter):
    """Map released DB9 Exercise-B arrays onto the Common Pose vocabulary.

    Parameters
    ----------
    mat_path:
        A released ``S<N>_E2_A1.mat`` (Exercise B). Not redistributed with this
        repository; obtain it from the official Ninapro source.
    subset:
        ``"trusted"`` (default) emits only ``TRUSTED_DB9_POSE_v1``.
        ``"canonical16"`` emits the historical 16-DOF vocabulary, with each dimension's
        audit verdict attached and ``DROP``ped dimensions marked ``INVALID`` — this is
        what the historical results were computed in, and it is what a re-reader needs in
        order to see which historical conclusions lean on defective channels.
    """

    mat_path: Path | str | None = None
    subset: str = "trusted"

    def __post_init__(self) -> None:
        if self.subset not in ("trusted", "canonical16"):
            raise ValueError(
                f"subset must be 'trusted' or 'canonical16', got {self.subset!r}"
            )

    @property
    def registry(self) -> DofRegistry:  # type: ignore[override]
        return (
            load_trusted_db9_subset()
            if self.subset == "trusted"
            else get_registry("canonical16")
        )

    @property
    def capability(self) -> AdapterCapability:
        if self.subset == "trusted":
            present = load_trusted_db9_subset().names
            restricted: Sequence[str] = ()
        else:
            present = get_registry("canonical16").names
            restricted = tuple(self._drop_verdicts())
        return AdapterCapability(
            source="Ninapro DB9 (Exercise B, calibrated CyberGlove-II)",
            dimensions_present=tuple(present),
            dimensions_absent=(
                "index_mcp_ab_adduction",
                "middle_mcp_ab_adduction",
                "pinky_ab_adduction",
                "wrist_flexion",
                "wrist_deviation",
            ),
            dimensions_restricted=restricted,
            native_rate_hz=25.0,
            declared_rate_hz=None,
            has_emg=True,
            db9_verdicts_are_authoritative=True,
            notes=(
                "rates: DB1 100 Hz, DB5 200 Hz, DB2 2 kHz; the CyberGlove link is "
                "~25 Hz, so everything above that is interpolation",
                "MCP2_a is all-NaN and vendor-excluded",
                "there is no middle-finger abduction channel in the 22-channel set",
                "the in-file `subject` field is source-database-local and collides "
                "across source databases; never group by it",
            ),
        )

    def _drop_verdicts(self) -> list[str]:
        from ..api.dof import trusted_db9_exclusions

        keep = set(load_trusted_db9_subset().names)
        db9_to_canonical = {
            s.db9_channel: s.name
            for s in get_registry("canonical16").specs
            if s.db9_channel
        }
        return [
            db9_to_canonical[d]
            for d in (e["name"] for e in trusted_db9_exclusions()["DROP"])
            if d in db9_to_canonical and db9_to_canonical[d] not in keep
        ]

    # -- loading ------------------------------------------------------------- #

    def load(
        self,
        mat_path: Path | str | None = None,
        *,
        movements: Sequence[int] | None = None,
        handshape_only: bool = False,
        central_fraction: float | None = None,
    ) -> PoseStream:
        """Build a stream from one released Exercise-B recording.

        Parameters
        ----------
        movements:
            Restrict to these ``restimulus`` ids. ``None`` keeps all.
        handshape_only:
            Keep only :data:`DB9_EXERCISE_B_HANDSHAPE_MOVEMENTS`. This is the task the
            trusted subset was actually validated on; the mixed 17-class task is not a
            fair evaluation of a subset that contains no wrist channel.
        central_fraction:
            Keep only the central fraction of every ``(restimulus, rerepetition)``
            segment, as the frozen utility protocol does (0.6 there; the frozen posture
            corpus used the central-third median). ``None`` keeps whole segments.
        """
        path = Path(mat_path or self.mat_path)  # type: ignore[arg-type]
        if mat_path is None and self.mat_path is None:
            raise AdapterError("no mat_path supplied")
        if not path.exists():
            raise FileNotFoundError(
                f"{path} not found. DB9 is not redistributed with this repository; "
                f"download it from the official Ninapro source (see "
                f"docs/reproducibility.md)."
            )

        try:
            from scipy.io import loadmat  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise AdapterError("scipy is required to read DB9 .mat files") from exc

        mat = loadmat(str(path), squeeze_me=True, struct_as_record=False)
        for key in ("angles", "restimulus", "rerepetition"):
            if key not in mat:
                raise AdapterError(
                    f"{path.name} is missing required variable {key!r}. Refusing to "
                    f"substitute a differently-named field: see "
                    f"audits/db9/channel_forensic/SEGMENTATION_VALIDATION.md."
                )

        angles = np.asarray(mat["angles"], dtype=np.float64)
        restimulus = np.asarray(mat["restimulus"]).ravel()
        rerepetition = np.asarray(mat["rerepetition"]).ravel()

        if angles.ndim != 2 or angles.shape[1] != 22:
            raise AdapterError(
                f"expected (T, 22) released angles, got {angles.shape}. The 22-channel "
                f"CyberGlove layout is asserted by the audit; a different width means "
                f"this is not the release this adapter was written against."
            )
        if not (len(restimulus) == len(rerepetition) == angles.shape[0]):
            raise AdapterError(
                f"label/kinematics length mismatch: angles {angles.shape[0]}, "
                f"restimulus {len(restimulus)}, rerepetition {len(rerepetition)}. "
                f"Segmenting on a misaligned vector is the documented defect class."
            )

        channel_order = load_order_of_angles(path)
        if tuple(channel_order) != DB9_CHANNEL_ORDER:
            raise AdapterError(
                f"in-file order_of_angles disagrees with the audited order.\n"
                f"  file : {channel_order}\n  audit: {list(DB9_CHANNEL_ORDER)}"
            )

        keep_movements = self._resolve_movements(movements, handshape_only)
        mask = np.isin(restimulus, np.asarray(keep_movements))
        if central_fraction is not None:
            mask &= self._central_mask(restimulus, rerepetition, central_fraction)

        idx = np.flatnonzero(mask)
        if idx.size == 0:
            raise AdapterError("movement selection produced zero samples")

        values, validity = self._project(angles[idx])

        # A time base is synthesized at the glove's link rate. DB9's released angle bundle
        # carries no timestamps, so this is a reconstruction and is labelled as one in the
        # provenance rather than passed off as measured.
        native_rate = 25.0
        timestamps = np.arange(idx.size, dtype=np.float64) / native_rate

        return PoseStream(
            timestamps_s=timestamps,
            values=values,
            validity=validity,
            registry=self.registry,
            provenance=Provenance(
                source_dataset="Ninapro DB9 (Exercise B, calibrated CyberGlove-II)",
                source_version=str(path.name),
                source_identity=path.stem,
                transform=(
                    "released `angles` consumed as published; no alignment applied. The "
                    "release is f(glove) - f(glove_reference) with f a per-channel affine "
                    "or affine-quadratic calibration."
                ),
                calibration_established=None,
                calibration_note=(
                    "gains derived by the DB9 authors from 10 subjects and applied to all "
                    "77; raw gauges unpublished, so raw->released parity cannot be "
                    "independently closed. 16 of 22 released columns were recovered "
                    "exactly as affine/affine-quadratic functions of a single raw "
                    "column, which validates the transform form but not its scale "
                    "generalisation to the other 67 subjects."
                ),
                unit_conversion="released degrees consumed as degrees; no conversion",
                plan_sha256=(
                    "4c618b562903d0d364d03bb8a997ef6b4140bd9e09d0f2475f1b008ad80c8793"
                ),
                code_version="COMMIT PENDING",
                extras={
                    "segmentation": "restimulus x rerepetition",
                    "movements_included": sorted(set(keep_movements)),
                    "central_fraction": central_fraction,
                    "n_released_channels": 22,
                },
            ),
            native_rate_hz=native_rate,
            metadata={"mat_path_name": path.name, "n_selected": int(idx.size)},
        )

    def _resolve_movements(
        self, movements: Sequence[int] | None, handshape_only: bool
    ) -> Sequence[int]:
        if movements is not None and handshape_only:
            raise ValueError("pass either `movements` or `handshape_only`, not both")
        if movements is not None:
            return tuple(int(m) for m in movements)
        if handshape_only:
            return DB9_EXERCISE_B_HANDSHAPE_MOVEMENTS
        return tuple(
            sorted(
                set(DB9_EXERCISE_B_HANDSHAPE_MOVEMENTS)
                | set(DB9_EXERCISE_B_WRIST_MOVEMENTS)
            )
        )

    @staticmethod
    def _central_mask(
        restimulus: np.ndarray, rerepetition: np.ndarray, fraction: float
    ) -> np.ndarray:
        if not 0.0 < fraction <= 1.0:
            raise ValueError(f"central_fraction must be in (0, 1], got {fraction}")
        keep = np.zeros(restimulus.shape, dtype=bool)
        keys = np.stack([restimulus, rerepetition], axis=1)
        for segment in np.unique(keys, axis=0):
            sel = np.flatnonzero((keys == segment).all(axis=1))
            if sel.size == 0:
                continue
            n = sel.size
            width = max(1, int(round(n * fraction)))
            start = (n - width) // 2
            keep[sel[start : start + width]] = True
        return keep

    # -- projection ---------------------------------------------------------- #

    def _project(self, released_deg: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Select and order columns, attaching per-dimension validity.

        Validity is accumulated as int8 codes, never as an object array of enum members:
        NumPy applies its own string conversion to ``str``-mixin enum members inside
        object arrays, silently degrading ``Validity.VALID`` to the Python string
        ``'Valid'``, which then reads as neither valid nor invalid.
        """
        col_of = {name: i for i, name in enumerate(DB9_CHANNEL_ORDER)}
        specs = self.registry.specs

        values = np.full((released_deg.shape[0], len(specs)), np.nan, dtype=np.float64)
        validity = np.full(
            (released_deg.shape[0], len(specs)), NOT_ESTABLISHED_CODE, dtype=np.int8
        )
        val_code = VALIDITY_CODES[Validity.VALID]
        inv_code = VALIDITY_CODES[Validity.INVALID]
        unk_code = VALIDITY_CODES[Validity.NOT_ESTABLISHED]

        for j, spec in enumerate(specs):
            ch = spec.db9_channel
            if ch is None or ch not in col_of:
                continue
            raw = released_deg[:, col_of[ch]]
            verdict = spec.db9_verdict

            # The released column is copied verbatim. A DROPped channel is NOT repaired
            # and NOT zeroed: it is emitted as-is with validity INVALID, so a consumer
            # that wants to reproduce a historical number still can, and a consumer that
            # wants the trusted subset is told which columns to ignore.
            values[:, j] = raw
            if np.all(np.isnan(raw)):
                validity[:, j] = inv_code
                continue
            if verdict is AuditVerdict.DROP:
                validity[:, j] = inv_code
            elif verdict is AuditVerdict.INCONCLUSIVE:
                validity[:, j] = unk_code
            elif verdict is AuditVerdict.KEEP:
                # KEEP means the channel behaves as its published definition requires. It
                # does not mean every sample is in anatomical range; range is a separate,
                # dataset-specific question this project has not settled, so range is not
                # asserted here.
                validity[:, j] = val_code
            else:
                validity[:, j] = unk_code

        return values, validity


__all__ = [
    "DB9_CHANNEL_ORDER",
    "DB9_EXERCISE_B_HANDSHAPE_MOVEMENTS",
    "DB9_EXERCISE_B_WRIST_MOVEMENTS",
    "DB9_VENDOR_EXCLUDED",
    "DB9Adapter",
    "load_order_of_angles",
]
