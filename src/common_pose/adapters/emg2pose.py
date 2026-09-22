"""emg2pose model output -> Common Pose adapter.

The one thing this adapter exists to get right
----------------------------------------------
The official emg2pose release encodes inverse-kinematics failures as **all-zero
``joint_angles`` rows, not NaN**. In the official mini corpus that is 15.6 percent of
samples. Zero is a legitimate hand angle — the extended hand — so a consumer that treats
those rows as poses trains on garbage without any error being raised. Measured effect on
one held-out session: unmasked MAE 16.09 deg versus masked 12.48 deg.

Accordingly this adapter never infers validity from the values. It applies the official
failure rule explicitly and marks those samples ``INVALID``.

Rate honesty
------------
The model consumes 16-channel sEMG at 2 kHz and emits a ``(T, 20)`` array at what looks
like 2 kHz, but only ``T/40`` of those rows are independent: the internal rollout runs at
50 Hz and the rest is linear interpolation. ``native_rate_hz`` records 50 Hz so a
downstream window length cannot be chosen on a rate that does not exist.

Dependencies and licensing
--------------------------
The emg2pose baseline is **not vendored here**. This adapter imports it from a user-run
checkout. That is a licensing decision as much as a packaging one: the baseline is
released under CC-BY-NC-SA-4.0 and its bundled UmeTrack under CC-BY-NC-4.0, so it is not
redistributed. See ``docs/licensing.md``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import numpy as np

from ..api.dof import DofRegistry, get_registry
from ..api.pose_frame import PoseStream
from ..api.provenance import Provenance
from ..api.verdicts import NOT_ESTABLISHED_CODE, VALIDITY_CODES, Validity
from .base import AdapterCapability, AdapterError, PoseAdapter

#: Official constants, mirrored from the baseline. Do not invent values.
EMG_SAMPLE_RATE_HZ = 2000
NUM_EMG_CHANNELS = 16
NUM_JOINTS = 20
#: Independent rollout rate. The 2 kHz output is a linear interpolation of this.
ROLLOUT_FREQ_HZ = 50
#: Raw 2 kHz samples consumed as left context before the first output row.
TDS_LEFT_CONTEXT = 1790

#: Fraction of the official mini corpus that is IK-failure rows. Measured, not estimated.
MEASURED_IK_FAILURE_FRACTION_MINI = 0.15625


def ik_failures_mask(joint_angles: np.ndarray) -> np.ndarray:
    """``True`` where a row is a valid pose, reproducing the official rule.

    Reimplemented from the published definition rather than imported, so that this module
    carries no third-party code. The rule is: a row is an IK failure iff every component
    is close to zero. Deliberately *not* NaN-based, because the release does not use NaN
    for this.
    """
    arr = np.asarray(joint_angles)
    if arr.ndim < 1:
        raise ValueError("joint_angles must have at least one dimension")
    return ~np.all(np.isclose(arr, 0.0), axis=-1)


def resolve_baseline_root(explicit: Path | str | None = None) -> Path:
    """Locate a user-provided emg2pose checkout.

    Resolution order: explicit argument, ``COMMON_POSE_EMG2POSE_BASELINE``, then
    ``$COMMON_POSE_WORKSPACE/baseline/emg2pose``. Raises with instructions rather than
    guessing, because a wrong path here yields a silently different joint ordering.
    """
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(Path(explicit))
    env = os.environ.get("COMMON_POSE_EMG2POSE_BASELINE")
    if env:
        candidates.append(Path(env))
    ws = os.environ.get("COMMON_POSE_WORKSPACE")
    if ws:
        candidates.append(Path(ws) / "baseline" / "emg2pose")

    for c in candidates:
        if (c / "emg2pose" / "constants.py").exists():
            return c
    raise AdapterError(
        "emg2pose baseline not found. This repository does not redistribute it.\n"
        "  1. clone the official baseline from "
        "https://github.com/facebookresearch/emg2pose\n"
        "  2. set COMMON_POSE_EMG2POSE_BASELINE=/path/to/emg2pose\n"
        "  (or pass baseline_root=... explicitly)\n"
        f"  checked: {[str(c) for c in candidates] or 'no candidates supplied'}"
    )


@dataclass
class Emg2PoseAdapter(PoseAdapter):
    """Map emg2pose ``(T, 20)`` joint-angle arrays onto the Common Pose vocabulary.

    Parameters
    ----------
    baseline_root:
        Path to a user-provided emg2pose checkout, needed only for
        :meth:`load_from_recording`.
    vocab:
        ``"canonical16"`` (default). emg2pose publishes 16 of those dimensions plus two
        it does not regress; the two wrist dimensions are emitted as ``INVALID`` so a
        consumer sees the gap in-band.
    """

    baseline_root: Path | str | None = None
    vocab: str = "canonical16"
    extra_unspecified: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.vocab != "canonical16":
            raise ValueError(
                "only the canonical16 vocabulary is currently defined for this adapter"
            )
        self._absent = tuple(
            s.name
            for s in get_registry("canonical16").specs
            if s.emg2pose_index is None
        )

    @property
    def registry(self) -> DofRegistry:  # type: ignore[override]
        return get_registry("canonical16")

    @property
    def capability(self) -> AdapterCapability:
        present = [
            s.name
            for s in get_registry("canonical16").specs
            if s.emg2pose_index is not None
        ]
        return AdapterCapability(
            source="emg2pose pose model (learned sEMG -> UmeTrack hand joints)",
            dimensions_present=tuple(present),
            dimensions_absent=self._absent,
            dimensions_restricted=(),
            native_rate_hz=float(ROLLOUT_FREQ_HZ),
            declared_rate_hz=float(EMG_SAMPLE_RATE_HZ),
            has_emg=True,
            # The frozen DB9 verdicts are about the released DB9 columns, not about this
            # source's columns of the same anatomical DOF. Applying them here would be a
            # category error in both directions.
            db9_verdicts_are_authoritative=False,
            notes=(
                "emg2pose deliberately does not regress the wrist",
                "IK failures are all-zero rows, not NaN; masked by ik_failures_mask()",
                "the released `split` column alone cannot support a cross-subject "
                "claim: held-out structure lives in the `generalization` axis",
                "the official mini corpus covers ONE held-out user; every number "
                "computed on it is within-subject",
            ),
        )

    # -- loading ------------------------------------------------------------- #

    def load(
        self,
        joint_angles_rad: np.ndarray,
        *,
        sample_rate_hz: float = EMG_SAMPLE_RATE_HZ,
        start_s: float = 0.0,
        source_identity: str | None = None,
        stage: str | None = None,
    ) -> PoseStream:
        """Wrap an emg2pose output array.

        ``joint_angles_rad`` is ``(T, 20)`` in radians, in the official
        ``emg2pose.constants.JOINTS`` order, with ``+`` = flexion for the 15 flexion
        joints. The array is consumed as published; nothing is flipped or rescaled.
        """
        arr = np.asarray(joint_angles_rad, dtype=np.float64)
        if arr.ndim != 2 or arr.shape[1] != NUM_JOINTS:
            raise AdapterError(
                f"expected (T, {NUM_JOINTS}) joint angles, got {arr.shape}. The 20-DOF "
                f"layout is a hard requirement of the official model; a different width "
                f"means the joint ordering cannot be assumed."
            )

        specs = get_registry("canonical16").specs
        n = arr.shape[0]
        values = np.full((n, len(specs)), np.nan, dtype=np.float64)
        validity = np.full((n, len(specs)), NOT_ESTABLISHED_CODE, dtype=np.int8)
        val_code = VALIDITY_CODES[Validity.VALID]
        inv_code = VALIDITY_CODES[Validity.INVALID]

        frame_ok = ik_failures_mask(arr)  # (T,) True where NOT an IK failure
        n_failed = int((~frame_ok).sum())

        for j, spec in enumerate(specs):
            if spec.emg2pose_index is None:
                # emg2pose does not publish this dimension. Marked INVALID, not zero.
                validity[:, j] = inv_code
                continue
            values[:, j] = arr[:, spec.emg2pose_index]
            validity[:, j] = np.where(frame_ok, val_code, inv_code)

        dt = 1.0 / float(sample_rate_hz)
        timestamps = start_s + np.arange(n, dtype=np.float64) * dt

        return PoseStream(
            timestamps_s=timestamps,
            values=values,
            validity=validity,
            registry=self.registry,
            provenance=Provenance(
                source_dataset="emg2pose pose model output",
                source_version="official pretrained baseline checkpoints",
                source_identity=source_identity,
                transform=(
                    "consumed as published, in radians, in the official "
                    "emg2pose.constants.JOINTS order; + = flexion for the 15 flexion "
                    "joints"
                ),
                calibration_established=None,
                calibration_note=(
                    "learned regression trained against UmeTrack optical tracking. The "
                    "zero is a model-construction artefact, not a recorded physical "
                    "reference posture, so it is NOT numerically interchangeable with "
                    "DB9's recorded reference posture even though both are named "
                    "'extended hand'."
                ),
                unit_conversion="none; the model publishes radians and radians are used",
                code_version="COMMIT PENDING",
                extras={
                    "left_context_samples": TDS_LEFT_CONTEXT,
                    "native_rate_hz": ROLLOUT_FREQ_HZ,
                    "stage": stage,
                    "ik_failures_in_this_array": n_failed,
                    "ik_failure_fraction_in_this_array": (
                        round(n_failed / n, 6) if n else None
                    ),
                },
            ),
            native_rate_hz=float(ROLLOUT_FREQ_HZ),
            metadata={
                "declared_rate_hz": float(sample_rate_hz),
                "inflation_factor": float(sample_rate_hz) / ROLLOUT_FREQ_HZ,
            },
        )

    def load_from_recording(
        self,
        hdf5_path: Path | str,
        *,
        session: str = "regression_vemg2pose",
    ) -> tuple[PoseStream, np.ndarray]:
        """Run the official model on a released recording and wrap the result.

        Returns ``(stream, emg)``. Requires the official ``emg2pose`` package importable
        from a user-provided checkout; see :func:`resolve_baseline_root`.
        """
        root = resolve_baseline_root(self.baseline_root)
        import sys

        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        try:
            from emg2pose.utils import get_ik_failures_mask as official_mask
        except ImportError as exc:  # pragma: no cover
            raise AdapterError(
                f"could not import the official emg2pose package from {root}. Install "
                f"its environment (Python 3.10 is pinned by the official "
                f"environment.yml; the kinematics module fails at import on 3.11)."
            ) from exc

        from ..estimators.emg2pose.predict_pose import PredictPose

        path = Path(hdf5_path)
        if not path.exists():
            raise FileNotFoundError(
                f"{path} not found. emg2pose is not redistributed with this repository; "
                f"download it from the official source (see docs/reproducibility.md)."
            )

        import h5py

        with h5py.File(str(path), "r") as f:
            emg = np.asarray(f["emg"], dtype=np.float32)
            gt = np.asarray(f["joint_angles"], dtype=np.float32)

        model = PredictPose(experiment=session)
        pred = np.asarray(model.predict(emg), dtype=np.float64)

        # Cross-check this module's reimplementation against the official helper on the
        # ground-truth array, where both are defined. A silent divergence here would
        # reclassify 15 percent of the corpus.
        agree = bool(np.array_equal(ik_failures_mask(gt), official_mask(gt)))
        if not agree:
            raise AdapterError(
                "this module's ik_failures_mask disagrees with the official "
                "emg2pose.utils.get_ik_failures_mask on the recording's ground truth. "
                "Refusing to emit validity that would silently reclassify samples."
            )

        stream = self.load(
            pred,
            source_identity=path.stem,
            stage=None,
            sample_rate_hz=EMG_SAMPLE_RATE_HZ,
            start_s=TDS_LEFT_CONTEXT / EMG_SAMPLE_RATE_HZ,
        )
        stream.metadata = {**stream.metadata, "official_mask_agreement": agree}
        return stream, emg


__all__ = [
    "EMG_SAMPLE_RATE_HZ",
    "MEASURED_IK_FAILURE_FRACTION_MINI",
    "NUM_EMG_CHANNELS",
    "NUM_JOINTS",
    "ROLLOUT_FREQ_HZ",
    "TDS_LEFT_CONTEXT",
    "Emg2PoseAdapter",
    "ik_failures_mask",
    "resolve_baseline_root",
]
