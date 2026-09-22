"""Evaluation: metrics that state what they were computed over.

Every metric here returns, alongside its value, the counts that make it interpretable —
how many frames, how many subjects, how many classes, what chance is, and which classes
collapsed. A bare accuracy number is not a result in this project; it is a number that
has been detached from its protocol.

The one metric worth reading first is
:func:`~common_pose.evaluation.metrics.per_subject_balanced_accuracy`. A pooled accuracy
can be carried entirely by a few easy subjects, and ``worst_subject_balanced_accuracy``
is what exposes that.
"""

from __future__ import annotations

from .metrics import (
    ClassificationReport,
    classification_report,
    cohen_kappa,
    per_subject_balanced_accuracy,
    per_subject_report,
)

__all__ = [
    "ClassificationReport",
    "classification_report",
    "cohen_kappa",
    "per_subject_balanced_accuracy",
    "per_subject_report",
]
