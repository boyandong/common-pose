"""The DB9 postural-shape task, expressed against the Common Pose vocabulary.

What this task is
-----------------
Given **only hand joint angles**, identify which of the **eight official Exercise-B hand
configurations (movement IDs 1-8)** a representative posture belongs to, subject held
out. Movement IDs 9-17 are wrist movements and are not part of this task. It is deliberately classical: one shared LDA per fold, train-fold-only
standardisation, no deep network, no EMG. The unit of analysis is
``subject x movement x repetition``, not a frame.

Why the task definition is written down here rather than left implicit
--------------------------------------------------------------------
Two protocol choices change the number and neither is obvious from a results table:

1. **Official movement IDs 1-8 only.** Exercise B mixes eight hand configurations with
   nine wrist movements. ``TRUSTED_DB9_POSE_v1`` contains no wrist channel by
   construction, because the audit DROPped ``WRIST_A`` and held ``WRIST_F``
   inconclusive. Scoring a wristless representation on a wrist-inclusive target
   penalises it for a quantity it was never designed to carry.
2. **The reference arm is the historical ``canonical16``, not a strawman.** The trusted
   subset loses 0.108 balanced accuracy against it (0.8556 -> 0.7479 on 77 subjects).
   Reporting only the trusted-subset number would hide the cost of the physical audit,
   and reporting only the loss would hide that the surviving subset is 6.0x chance with
   no class collapse.
3. **A fixed per-segment frame cap of 200.** DB2 recordings are far longer than DB1/DB5
   recordings, so an uncapped frame-level evaluation would weight the DB2 source database
   merely because it holds more frames per segment. The cap keeps every participant,
   movement and segment while preventing recording duration from defining the weight.

Both arms are therefore always reported together. See
``docs/db9_trusted_subset.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from ..api.dof import get_registry, load_trusted_db9_subset

#: Exercise-B hand-configuration movement ids — the task the trusted subset was validated
#: on. IDs 1-8 only. **Movement 17 is NOT here**: the official protocol defines it as
#: "Wrist extension with closed hand", i.e. a wrist movement, and an earlier public
#: revision wrongly counted it as a ninth hand-shape class.
HANDSHAPE_MOVEMENTS: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8)

#: Exercise-B movement ids excluded from the hand-configuration task: 9-12 are
#: supination/pronation and 13-17 are wrist flexion/extension/deviation. Kept for
#: completeness; note that ``TRUSTED_DB9_POSE_v1`` has no wrist channel by construction,
#: which is why none of these can be scored fairly against it.
EXCLUDED_FROM_HANDSHAPE_TASK: tuple[int, ...] = (9, 10, 11, 12, 13, 14, 15, 16, 17)

#: Movement id the DB9 zero/reference posture was taken from, confirmed from the data.
REFERENCE_MOVEMENT = 11

#: The movement that is an unambiguous fist, used as the physical anchor.
FIST_MOVEMENT = 6


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
#: FINAL: the official 8-posture benchmark over all 77 DB9 participants (movement IDs
#: 1-8 only), with a fixed per-segment frame cap of 200. This is the downstream DB9
#: posture baseline. The earlier 37-subject, 9-class mixed-task run is retained as
#: HISTORICAL_MIXED_TASK_UTILITY below and is NOT the official benchmark.
#: Source of the numbers: ``audits/db9/channel_forensic/artifacts/FINAL_VALIDATION.json``.
FROZEN_HANDSHAPE_UTILITY: Mapping[str, ArmResult] = {
    "A_historical_canonical16": ArmResult(
        arm="A_historical_canonical16", n_dimensions=16, n_frames=123_200,
        n_subjects=77, n_classes=8,
        accuracy=0.8556, balanced_accuracy=0.8556,
        macro_f1=0.8559, chance_balanced_accuracy=0.125,
        worst_subject_balanced_accuracy=0.5850,
        median_subject_balanced_accuracy=0.8744,
        classes_with_recall_below_half=(), class_collapse=False,
    ),
    "B_TRUSTED_DB9_POSE_v1": ArmResult(
        arm="B_TRUSTED_DB9_POSE_v1", n_dimensions=8, n_frames=123_200,
        n_subjects=77, n_classes=8,
        accuracy=0.7479, balanced_accuracy=0.7479,
        macro_f1=0.7460, chance_balanced_accuracy=0.125,
        worst_subject_balanced_accuracy=0.5369,
        median_subject_balanced_accuracy=0.7556,
        classes_with_recall_below_half=(4,), class_collapse=False,
    ),
}

#: HISTORICAL, NOT THE BENCHMARK. The earlier 37-subject run on nine classes
#: (movement IDs 1-8 and 17). Movement 17 is a wrist movement and was wrongly counted as a
#: hand-shape class; the run also covered only the 37 DB1/DB5 Exercise-B participants
#: because the loader then selected Exercise B by filename exercise code. Kept only so the
#: earlier statement remains traceable. Source:
#: ``audits/db9/channel_forensic/artifacts/POSTURE_UTILITY_POSTURE_ONLY.json``.
HISTORICAL_MIXED_TASK_UTILITY: Mapping[str, ArmResult] = {
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
    """Task definition for DB9 hand-configuration identification.

    Holds the *definition*; the frozen pipeline that computes it lives at
    ``src/common_pose/adapters/db9/experiments/`` and
    ``audits/db9/channel_forensic/tools/utility_posture_only.py``. This object exists so
    that a consumer can ask what the number means without reading either.
    """

    include_wrist_movements: bool = False
    """Must stay ``False`` while the evaluated representation carries no wrist channel.
    Setting it ``True`` reproduces the mixed 17-class Exercise-B task, which is a
    legitimate but different question and understates a wristless subset. **It is not the
    official posture baseline**, which is the eight hand configurations only."""

    central_fraction: float = 0.60
    """Fraction of each segment retained, centred. The frozen utility protocol uses the
    central 60 percent of every segment."""

    frame_cap_per_segment: int | None = 200
    """Fixed per-segment frame cap used by the frozen 77-participant baseline.

    Declared because it is a real deviation from an uncapped evaluation. DB2 recordings
    are roughly 20x longer than DB1/DB5, so an uncapped pooled frame set would be
    dominated by DB2 purely by frame count. The cap keeps every participant, movement and
    segment while removing that duration weighting. ``None`` reproduces the uncapped set
    (11 843 312 frames over 77 participants)."""

    unit_of_analysis: str = "frame"
    """Frames within a ``(subject, movement, repetition)`` segment. Note that frames are
    temporally correlated, so this is not an independent-sample count."""

    split: str = "leave-one-subject-out"

    identity_key: str = "archive slot parsed from the filename (DB9-global 1..77)"
    """The in-file ``subject`` field MUST NOT be used: it is source-database-local and
    collides across source databases, merging distinct people."""

    normalization: str = "train-fold-only z-score"
    """Standardisation statistics are computed on the training fold only. Computing them
    over the whole corpus is subject leakage and was explicitly avoided."""

    model: str = "LinearDiscriminantAnalysis (one shared model per fold)"

    @property
    def movement_ids(self) -> tuple[int, ...]:
        if self.include_wrist_movements:
            return tuple(
                sorted(set(HANDSHAPE_MOVEMENTS) | set(EXCLUDED_FROM_HANDSHAPE_TASK))
            )
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
                "PostureTask — DB9 Exercise B hand-configuration identification",
                f"  movements        {list(self.movement_ids)}",
                f"  classes          {self.n_classes} "
                f"(chance BA {self.chance_balanced_accuracy:.4f})",
                f"  wrist included   {self.include_wrist_movements}",
                f"  central fraction {self.central_fraction}",
                f"  frame cap        {self.frame_cap_per_segment}",
                f"  split            {self.split}",
                f"  identity key     {self.identity_key}",
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
    "EXCLUDED_FROM_HANDSHAPE_TASK",
    "FIST_MOVEMENT",
    "FROZEN_HANDSHAPE_UTILITY",
    "HANDSHAPE_MOVEMENTS",
    "HISTORICAL_MIXED_TASK_UTILITY",
    "REFERENCE_MOVEMENT",
    "ArmResult",
    "PostureTask",
    "posture_representation_names",
]
