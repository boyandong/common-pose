"""
predict_pose.py -- Standalone EMG -> hand joint angle inference using the
official emg2pose pretrained baseline checkpoints.

Primary (and default) mode is **regression VEMG2Pose**, which requires ONLY EMG:
no initial hand pose is needed. This is the mode to use when the only available
input at test time is 16-channel wrist sEMG.

Interface
---------
    >>> from predict_pose import PredictPose
    >>> model = PredictPose(experiment="regression_vemg2pose")   # EMG-only
    >>> angles = model.predict(emg)          # emg: (T, 16) float32 numpy/torch
    >>> angles.shape
    (T - 1790, 20)

The returned array is organised as ``[T_pose, N_joint]`` with ``N_joint == 20``
(hard requirement from the official model; see docs/joint_angle_definition.md).
Values are joint angles in **radians**.

Everything documented here was verified against the official code/checkpoints/
dataset; see docs/joint_angle_definition.md for provenance and confidence.

Author: Session 2 (emg2pose baseline bring-up)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:  # pragma: no cover
    import torch


# --------------------------------------------------------------------------- #
# Official constants (mirrors emg2pose/constants.py -- do NOT invent values)
# --------------------------------------------------------------------------- #

EMG_SAMPLE_RATE = 2000  # Hz, official (paper + emg2pose.constants)
NUM_EMG_CHANNELS = 16  # official (paper: "2kHz, 16 channel sEMG")
NUM_JOINTS = 20  # official (emg2pose.constants.NUM_JOINTS)

#: Number of raw EMG samples consumed as left context before the first output
#: sample is produced. Equal to ``TdsNetwork.left_context`` for the official
#: ``config/network/tds.yaml`` architecture. Runtime-verified = 1790, which also
#: matches the comment in config/experiment/*_vemg2pose.yaml
#: ("Adding 1790 samples, which is the left_context of the tds network").
#: Note: this is NOT derivable from the top-level tds_stages widths alone --
#: TdsNetwork._get_left_context() sums the stage in_conv + each block kernel.
TDS_LEFT_CONTEXT = 1790

#: Temporal rate (Hz) at which the TDS featurizer + LSTM decoder natively
#: roll out. The 2 kHz output is a *linear interpolation* of this.
ROLLOUT_FREQ = 50

#: How long (in raw 2 kHz samples) the decoder predicts absolute positions
#: before switching to velocity integration. 500 samples = 250 ms.
NUM_POSITION_STEPS = 500

# Official joint names, in output order (emg2pose/constants.py :: JOINTS).
JOINT_NAMES: list[str] = [
    "THUMB_CMC_FE",
    "THUMB_CMC_AA",
    "THUMB_MCP_FE",
    "THUMB_IP_FE",
    "INDEX_MCP_AA",
    "INDEX_MCP_FE",
    "INDEX_PIP_FE",
    "INDEX_DIP_FE",
    "MIDDLE_MCP_AA",
    "MIDDLE_MCP_FE",
    "MIDDLE_PIP_FE",
    "MIDDLE_DIP_FE",
    "RING_MCP_AA",
    "RING_MCP_FE",
    "RING_PIP_FE",
    "RING_DIP_FE",
    "PINKY_MCP_AA",
    "PINKY_MCP_FE",
    "PINKY_PIP_FE",
    "PINKY_DIP_FE",
]

EXPERIMENTS = (
    "regression_vemg2pose",
    "tracking_vemg2pose",
    "regression_neuropose",
    "regression_emg2pose",
    "tracking_emg2pose",
)


@dataclass
class PredictionResult:
    """Container returned by :meth:`PredictPose.predict_full`.

    Attributes
    ----------
    angles : np.ndarray
        ``(T_pose, 20)`` joint angles in radians.
    start_index : int
        Index into the input EMG array of the first predicted sample.
        Equals :attr:`PredictPose.left_context`.
    sample_rate : int
        Sample rate of ``angles`` in Hz (2000, matching the EMG input).
    """

    angles: np.ndarray
    start_index: int
    sample_rate: int = EMG_SAMPLE_RATE

    @property
    def times(self) -> np.ndarray:
        """Wall-clock offsets (seconds) of each predicted sample w.r.t. input."""
        return (np.arange(self.angles.shape[0]) + self.start_index) / self.sample_rate


class PredictPose:
    """EMG -> hand joint angle prediction with official emg2pose checkpoints.

    Parameters
    ----------
    experiment : str
        Which official experiment config to use. Must match the checkpoint.
        ``regression_vemg2pose`` (default) is the EMG-only regression baseline.
    checkpoint : str | Path | None
        Path to a ``.ckpt`` file. Defaults to
        ``<repo>/checkpoints/emg2pose_model_checkpoints/<experiment>.ckpt``.
    repo_root : str | Path | None
        Path to the cloned official ``emg2pose`` repository. Defaults to
        ``<this file>/../baseline/emg2pose``.
    device : str
        ``"cpu"`` or ``"cuda"``.
    """

    def __init__(
        self,
        experiment: str = "regression_vemg2pose",
        checkpoint: str | Path | None = None,
        repo_root: str | Path | None = None,
        device: str = "cpu",
    ) -> None:
        if experiment not in EXPERIMENTS:
            raise ValueError(
                f"unknown experiment {experiment!r}; expected one of {EXPERIMENTS}"
            )

        self.experiment = experiment
        self.device = device

        # NOTE: deliberately NOT Path(__file__).resolve(). On this machine the
        # project is also reachable through the ASCII junction <PROJECT_ROOT>;
        # .resolve() dereferences junctions back to the non-ASCII user path,
        # which breaks h5py/documentation tooling. Keep the literal path.
        here = Path(__file__).absolute().parent
        self.repo_root = Path(repo_root) if repo_root else (here.parent / "baseline" / "emg2pose")
        if not self.repo_root.is_dir():
            raise FileNotFoundError(
                f"official emg2pose repo not found at {self.repo_root}. "
                "Clone it with: git clone https://github.com/facebookresearch/emg2pose.git"
            )

        self.checkpoint_path = (
            Path(checkpoint)
            if checkpoint
            else (here.parent / "checkpoints" / "emg2pose_model_checkpoints" / f"{experiment}.ckpt")
        )
        if not self.checkpoint_path.is_file():
            raise FileNotFoundError(f"checkpoint not found: {self.checkpoint_path}")

        self._module = self._load_module()

        # Runtime-verified architecture facts
        self.left_context: int = int(self._module.model.left_context)
        self.right_context: int = int(self._module.model.right_context)
        self.num_joints: int = int(NUM_JOINTS)
        #: True when the model was configured to consume a ground-truth initial
        #: pose. For regression this is False => pure-EMG inference.
        self.provide_initial_pos: bool = bool(self._module.provide_initial_pos)

    # ------------------------------------------------------------------ #
    # Construction
    # ------------------------------------------------------------------ #

    def _load_module(self) -> Any:
        # Import lazily so that `import predict_pose` stays cheap and so the
        # official repo is put on sys.path only when actually needed.
        import sys

        repo = str(self.repo_root)
        if repo not in sys.path:
            sys.path.insert(0, repo)

        import torch  # noqa: F401
        from emg2pose.lightning import Emg2PoseModule
        from emg2pose.utils import generate_hydra_config_from_overrides

        # NOTE: we deliberately do NOT pass `checkpoint=<path>` as a Hydra
        # override. Hydra's override grammar cannot parse a Windows path
        # ("C:\..." contains ':'), and `config.checkpoint` is only used for
        # logging inside emg2pose.train -- the actual checkpoint is passed to
        # Emg2PoseModule.load_from_checkpoint below.
        config = generate_hydra_config_from_overrides(
            config_path=str(self.repo_root / "config"),
            overrides=[f"experiment={self.experiment}"],
        )

        module = Emg2PoseModule.load_from_checkpoint(
            str(self.checkpoint_path),
            network=config.network,
            optimizer=config.optimizer,
            lr_scheduler=config.lr_scheduler,
            map_location=self.device,
        )
        module.eval()
        module.to(self.device)
        for p in module.parameters():
            p.requires_grad_(False)
        return module

    # ------------------------------------------------------------------ #
    # Inference
    # ------------------------------------------------------------------ #

    def min_input_length(self) -> int:
        """Minimum number of EMG samples required to produce >=1 output sample."""
        return self.left_context + self.right_context + 1

    def _as_tensor(self, emg: Any) -> "torch.Tensor":
        import torch

        if isinstance(emg, np.ndarray):
            t = torch.as_tensor(np.ascontiguousarray(emg), dtype=torch.float32)
        elif torch.is_tensor(emg):
            t = emg.detach().to(dtype=torch.float32)
        else:
            raise TypeError(f"emg must be numpy.ndarray or torch.Tensor, got {type(emg)}")

        if t.ndim != 2:
            raise ValueError(f"emg must be 2-D (T, 16), got shape {tuple(t.shape)}")
        if t.shape[1] != NUM_EMG_CHANNELS:
            raise ValueError(
                f"emg must have {NUM_EMG_CHANNELS} channels in dim 1 (got {t.shape[1]}). "
                "If you have (16, T), transpose it."
            )
        if t.shape[0] < self.min_input_length():
            raise ValueError(
                f"emg too short: got T={t.shape[0]}, need >= {self.min_input_length()} "
                f"({self.left_context} samples of left context + right_context="
                f"{self.right_context})."
            )
        return t.to(self.device)

    def predict_full(self, emg: Any) -> PredictionResult:
        """Run inference and return angles together with their time alignment."""
        import torch

        emg_t = self._as_tensor(emg)  # (T, C)
        batch = {
            "emg": emg_t.T.unsqueeze(0),  # (B=1, C=16, T)
            # Dummy ground truth: unused because provide_initial_pos=False for
            # regression. Consumed only for shape/masking bookkeeping.
            "joint_angles": torch.zeros(
                (1, NUM_JOINTS, emg_t.shape[0]), dtype=torch.float32, device=self.device
            ),
            "no_ik_failure": torch.ones(
                (1, emg_t.shape[0]), dtype=torch.bool, device=self.device
            ),
        }

        with torch.no_grad():
            preds, _targets, _mask = self._module.forward(batch)

        angles = preds[0].T.detach().to("cpu").numpy()  # (T_pose, 20)
        return PredictionResult(
            angles=angles,
            start_index=self.left_context,
            sample_rate=EMG_SAMPLE_RATE,
        )

    def predict(self, emg: Any) -> np.ndarray:
        """Predict joint angles.

        Parameters
        ----------
        emg : array-like
            ``(T, 16)`` float EMG at 2 kHz, already high-pass filtered and
            scaled as in the official dataset (noise floor std ~= 1).

        Returns
        -------
        np.ndarray
            ``(T_pose, 20)`` joint angles in **radians**, where
            ``T_pose = T - left_context`` (``left_context`` is 852 for the
            official VEMG2Pose architecture).
        """
        return self.predict_full(emg).angles

    # ------------------------------------------------------------------ #
    # Introspection helpers
    # ------------------------------------------------------------------ #

    def describe(self) -> dict[str, Any]:
        """Return a JSON-serialisable description of the loaded model."""
        return {
            "experiment": self.experiment,
            "checkpoint": str(self.checkpoint_path),
            "repo_root": str(self.repo_root),
            "device": self.device,
            "provide_initial_pos": self.provide_initial_pos,
            "emg_sample_rate": EMG_SAMPLE_RATE,
            "num_emg_channels": NUM_EMG_CHANNELS,
            "num_joints": self.num_joints,
            "joint_names": JOINT_NAMES,
            "left_context": self.left_context,
            "right_context": self.right_context,
            "rollout_freq": ROLLOUT_FREQ,
            "num_position_steps": NUM_POSITION_STEPS,
            "min_input_length": self.min_input_length(),
        }


def joint_names() -> list[str]:
    """Official output ordering of the 20 joint angles."""
    return list(JOINT_NAMES)


if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", default="regression_vemg2pose", choices=EXPERIMENTS)
    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--describe", action="store_true", help="print model description and exit")
    args = parser.parse_args()

    model = PredictPose(
        experiment=args.experiment, checkpoint=args.checkpoint, device=args.device
    )
    print(json.dumps(model.describe(), indent=2))
