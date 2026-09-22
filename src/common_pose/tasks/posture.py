"""The DB9 postural-shape task, expressed against the Common Pose vocabulary.

What this task is
-----------------
Given **only hand joint angles**, identify which of the nine Exercise-B hand-shape
movements (official ids 1-8 and 17) a representative posture belongs to, subject held
out. It is deliberately classical: one shared LDA per fold, train-fold-only
standardisation, no deep network, no EMG. The unit of analysis is
``subject x movement x repetition``, not a frame.

Why the task definition is written down here rather than left implicit
--------------------------------------------------------------------
Two protocol choices change the number and neither is obvious from a results table:

1. **Hand-shape movements only, not all 17 Exercise-B movements.** Exercise B mixes nine
   hand shapes with eight wrist movements. ``TRUSTED_DB9_POSE_v1`` contains no wrist
   channel by construction, because the audit DROPped ``WRIST_A`` and held ``WRIST_F``
   inconclusive. Scoring a wristless representation on a wrist-inclusive target
   penalises it for a quantity it was never designed to carry. On the mixed task the
   trusted subset reaches BA 0.4853; on the hand-shape task, 0.7254. Both numbers are
   real; they answer different questions.
2. **The reference arm is the historical ``canonical16``, not a strawman.** The trusted
   subset loses 0.128 balanced accuracy against it (0.8538 -> 0.7254). Reporting only
   the trusted-subset number would hide the cost of the physical audit, and reporting
   only the loss would hide that the surviving subset is 6.5x chance with no class
   collapse.

Both arms are therefore always reported together. See
``docs/db9_trusted_subset.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from ..api.dof import get_registry, load_trusted_db9_subset

#: Exercise-B hand-shape movement ids (the task the trusted subset was validated on).
HANDSHAPE_MOVEMENTS: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8, 17)

#: Exercise-B wrist movement ids, excluded from the hand-shape task.
WRIST_MOVEMENTS: tuple[int, ...] = (9, 10, 11, 12, 13, 14, 15, 16)

#: Movement id the DB9 zero/reference posture was taken from, confirmed from the data.
REFERENCE_MOVEMENT = 11


def posture_representation_names(arm: str = "trusted") -> tuple[str, ...]:
    """Dimension names for one evaluation arm.

    ``"trusted"``       the 8 channels of ``TRUSTED_DB9_POSE_v1``
    ``"canonical16"``   the historical 16-DOF vocabulary (reference arm)
    """
    if arm == "trusted":
        return load_trusted_db9_subset().names
    if arm == "canonical16":
        return get_registry("canonical16").names
    raise KeyError(f"unknown arm {arm!r}; expected 'trusted' or 'canonical16'")


@dataclass(frozen=True)
class ArmResult:
    """One evaluation arm's outcome, with the caveats that belong to it."""

    arm: str
    n_dimensions: int
    n_frames: int
    n_subjects: int
    n_classes: int
    accuracy: float
    balanced_accuracy: float
    macro_f1: float
    chance_balanced_accuracy: float
    worst_subject_balanced_accuracy: float | None = None
    median_subject_balanced_accuracy: float | None = None
    classes_with_recall_below_half: Sequence[int] = ()
    class_collapse: bool | None = None

    @property
    def balanced_accuracy_over_chance(self) -> float:
        return self.balanced_accuracy / self.chance_balanced_accuracy

    def describe(self) -> str:
        lines = [
            f"arm {self.arm}: {self.n_dimensions} dims, {self.n_classes} classes, "
            f"{self.n_frames} frames, {self.n_subjects} subjects",
            f"  accuracy          {self.accuracy:.4f}",
            f"  balanced accuracy {self.balanced_accuracy:.4f} "
            f"({self.balanced_accuracy_over_chance:.2f}x chance "
            f"{self.chance_balanced_accuracy:.4f})",
            f"  macro F1          {self.macro_f1:.4f}",
        ]
        if self.worst_subject_balanced_accuracy is not None:
            lines.append(
                f"  worst subject BA  {self.worst_subject_balanced_accuracy:.4f}"
            )
        if self.median_subject_balanced_accuracy is not None:
            lines.append(
                f"  median subject BA {self.median_subject_balanced_accuracy:.4f}"
            )
        if self.classes_with_recall_below_half:
            lines.append(
                f"  classes with recall < 0.5: {list(self.classes_with_recall_below_half)}"
            )
        lines.append(f"  class collapse    {self.class_collapse}")
        return "\n".join(lines)


#: Frozen record of the audited posture-utility result, transcribed from
#: ``audits/db9/channel_forensic/artifacts/POSTURE_UTILITY_POSTURE_ONLY.json``
#: (trusted_subset_sha256 e51dde6e63941fd080c84f3896a98cf50fba9e17d5f9cebe909253d5465782d1).
#:
#: PROVISIONAL: the utility arm covered the 37 Exercise-B subjects. It is not the final
#: full-77-subject validation.
FROZEN_HANDSHAPE_UTILITY: Mapping[str, ArmResult] = {
    "A_historical_canonical16": ArmResult(
        arm="A_historical_canonical16", n_dimensions=16, n_frames=544_556,
        n_subjects=37, n_classes=9,
        accuracy=0.8554785917334489, balanced_accuracy=0.8537944617929629,
        macro_f1=0.855988044051196, chance_balanced_accuracy=0.1111111111111111,
        worst_subject_balanced_accuracy=0.5647617572799044,
        median_subject_balanced_accuracy=0.870701145679425,
        classes_with_recall_below_half=(), class_collapse=False,
    ),
    "B_TRUSTED_DB9_POSE_v1": ArmResult(
        arm="B_TRUSTED_DB9_POSE_v1", n_dimensions=8, n_frames=544_556,
        n_subjects=37, n_classes=9,
        accuracy=0.7285843880151903, balanced_accuracy=0.7254456066785173,
        macro_f1=0.7256736065614833, chance_balanced_accuracy=0.1111111111111111,
        worst_subject_balanced_accuracy=0.47942322289171785,
        median_subject_balanced_accuracy=0.7346817034262487,
        classes_with_recall_below_half=(8,), class_collapse=False,
    ),
}


@dataclass
class PostureTask:
    """Task definition for DB9 hand-shape identification.

    Holds the *definition*; the frozen pipeline that computes it lives at
    ``src/common_pose/adapters/db9/experiments/`` and
    ``audits/db9/channel_forensic/tools/utility_posture_only.py``. This object exists so
    that a consumer can ask what the number means without reading either.
    """

    include_wrist_movements: bool = False
    """Must stay ``False`` while the evaluated representation carries no wrist channel.
    Setting it ``True`` reproduces the mixed 17-class task, which is a legitimate but
    different question and understates a wristless subset."""

    central_fraction: float = 0.60
    """Fraction of each segment retained, centred. The frozen utility protocol uses the
    central 60 percent of every segment."""

    unit_of_analysis: str = "frame"
    """Frames within a ``(subject, movement, repetition)`` segment. Note that frames are
    temporally correlated, so this is not an independent-sample count."""

    split: str = "subject-held-out"

    normalization: str = "train-fold-only z-score"
    """Standardisation statistics are computed on the training fold only. Computing them
    over the whole corpus is subject leakage and was explicitly avoided."""

    model: str = "LinearDiscriminantAnalysis (one shared model per fold)"

    @property
    def movement_ids(self) -> tuple[int, ...]:
        if self.include_wrist_movements:
            return tuple(sorted(set(HANDSHAPE_MOVEMENTS) | set(WRIST_MOVEMENTS)))
        return HANDSHAPE_MOVEMENTS

    @property
    def n_classes(self) -> int:
        return len(self.movement_ids)

    @property
    def chance_balanced_accuracy(self) -> float:
        return 1.0 / self.n_classes

    def describe(self) -> str:
        return "\n".join(
            [
                "PostureTask — DB9 Exercise B hand-shape identification",
                f"  movements        {list(self.movement_ids)}",
                f"  classes          {self.n_classes} "
                f"(chance BA {self.chance_balanced_accuracy:.4f})",
                f"  wrist included   {self.include_wrist_movements}",
                f"  central fraction {self.central_fraction}",
                f"  split            {self.split}",
                f"  normalization    {self.normalization}",
                f"  model            {self.model}",
                f"  unit of analysis {self.unit_of_analysis}",
            ]
        )

    def may_be_carrying(self, arm: str) -> bool:
        """Whether a representation arm is even able to express this task's target.

        A wristless representation scored on a wrist-inclusive task is being penalised
        for a target it does not carry. This predicate makes that explicit instead of
        leaving it to whoever reads the results table.
        """
        names = posture_representation_names(arm)
        has_wrist = any("wrist" in n for n in names)
        return (not self.include_wrist_movements) or has_wrist


__all__ = [
    "FROZEN_HANDSHAPE_UTILITY",
    "HANDSHAPE_MOVEMENTS",
    "REFERENCE_MOVEMENT",
    "WRIST_MOVEMENTS",
    "ArmResult",
    "PostureTask",
    "posture_representation_names",
]
