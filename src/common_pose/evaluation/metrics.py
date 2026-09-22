"""Classification metrics, with the protocol attached to each number.

Why not ``sklearn.metrics`` directly
------------------------------------
``sklearn.metrics.accuracy_score`` will happily accept predictions for a subset of a
subject-held-out evaluation and return a number with no indication of what it was
computed over. Two failure modes the historical audits actually hit:

* **Pooled accuracy carried by easy subjects.** On the DB9 posture task the pooled
  balanced accuracy is 0.7254 for the trusted subset, but the worst subject is 0.4794.
  Both are true; the second one is the one that predicts what happens on a new person.
* **Per-class collapse hidden by a macro average.** A class with recall below 0.5 is
  dropped from no report that only prints the macro F1. ``classes_with_recall_below_half``
  makes it explicit.

Nothing here silently handles a class that is present in the labels but absent from the
predictions; that is reported as ``missing_classes``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

import numpy as np


@dataclass(frozen=True)
class ClassificationReport:
    """A classification outcome with its protocol attached."""

    n: int
    n_classes: int
    accuracy: float
    balanced_accuracy: float
    macro_f1: float
    chance_balanced_accuracy: float
    per_class_recall: Mapping[int, float] = field(default_factory=dict)
    confusion: np.ndarray | None = None
    labels: Sequence[int] = ()
    missing_classes: Sequence[int] = ()
    """Labels present in the ground truth with zero predictions. A silent form of
    class collapse and always a defect worth surfacing."""
    classes_with_recall_below_half: Sequence[int] = ()
    class_collapse: bool = False

    @property
    def balanced_accuracy_over_chance(self) -> float:
        return self.balanced_accuracy / self.chance_balanced_accuracy

    def summary(self) -> str:
        lines = [
            f"n={self.n}  classes={self.n_classes}  chance BA="
            f"{self.chance_balanced_accuracy:.4f}",
            f"  accuracy          {self.accuracy:.6f}",
            f"  balanced accuracy {self.balanced_accuracy:.6f}  "
            f"({self.balanced_accuracy_over_chance:.2f}x chance)",
            f"  macro F1          {self.macro_f1:.6f}",
        ]
        if self.classes_with_recall_below_half:
            lines.append(
                f"  classes with recall < 0.5: "
                f"{list(self.classes_with_recall_below_half)}"
            )
        if self.missing_classes:
            lines.append(
                f"  MISSING CLASSES (never predicted): {list(self.missing_classes)}"
            )
        if self.class_collapse:
            lines.append("  CLASS COLLAPSE: True")
        return "\n".join(lines)


def _per_class_recall(
    y_true: np.ndarray, y_pred: np.ndarray, labels: Sequence[int]
) -> dict[int, float]:
    out: dict[int, float] = {}
    for lab in labels:
        mask = y_true == lab
        n = int(mask.sum())
        out[int(lab)] = float((y_pred[mask] == lab).sum() / n) if n else float("nan")
    return out


def classification_report(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    labels: Sequence[int] | None = None,
    *,
    recall_threshold: float = 0.5,
) -> ClassificationReport:
    """Balanced accuracy / macro F1 / per-class recall for discrete labels.

    Implemented directly rather than delegated, so that the definitions used here are
    the ones this project's frozen results were computed with: balanced accuracy is the
    unweighted mean of per-class recall, macro F1 is the unweighted mean of per-class
    F1, and both are NaN-safe only in the sense that an absent class is reported rather
    than dropped.
    """
    yt = np.asarray(y_true).ravel()
    yp = np.asarray(y_pred).ravel()
    if yt.shape != yp.shape:
        raise ValueError(f"shape mismatch: y_true {yt.shape}, y_pred {yp.shape}")
    if yt.size == 0:
        raise ValueError("empty evaluation set")

    labs = (
        np.asarray(sorted(set(int(v) for v in np.unique(yt))), dtype=np.int64)
        if labels is None
        else np.asarray(sorted(int(v) for v in labels), dtype=np.int64)
    )
    n_classes = int(labs.size)
    if n_classes == 0:
        raise ValueError("no labels present in y_true")

    accuracy = float((yt == yp).mean())
    recall = _per_class_recall(yt, yp, labs)
    present = [k for k, v in recall.items() if not np.isnan(v)]
    balanced = float(np.mean([recall[k] for k in present])) if present else float("nan")

    f1s: list[float] = []
    for lab in present:
        tp = float(((yt == lab) & (yp == lab)).sum())
        fp = float(((yt != lab) & (yp == lab)).sum())
        fn = float(((yt == lab) & (yp != lab)).sum())
        denom = 2 * tp + fp + fn
        f1s.append(0.0 if denom == 0 else (2 * tp) / denom)
    macro_f1 = float(np.mean(f1s)) if f1s else float("nan")

    predicted = set(int(v) for v in np.unique(yp))
    missing = [int(lab) for lab in labs if int(lab) not in predicted]

    labels_present = np.array(present, dtype=np.int64)
    confusion = np.zeros((labels_present.size, labels_present.size), dtype=np.int64)
    index = {int(lab): i for i, lab in enumerate(labels_present)}
    for t, p in zip(yt.tolist(), yp.tolist()):
        if int(t) in index and int(p) in index:
            confusion[index[int(t)], index[int(p)]] += 1

    below = [
        int(k) for k, v in recall.items() if not np.isnan(v) and v < recall_threshold
    ]

    return ClassificationReport(
        n=int(yt.size),
        n_classes=n_classes,
        accuracy=accuracy,
        balanced_accuracy=balanced,
        macro_f1=macro_f1,
        chance_balanced_accuracy=1.0 / n_classes,
        per_class_recall=recall,
        confusion=confusion,
        labels=tuple(int(v) for v in labels_present),
        missing_classes=tuple(missing),
        classes_with_recall_below_half=tuple(sorted(below)),
        class_collapse=bool(below),
    )


def cohen_kappa(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Cohen's kappa, computed from the confusion matrix.

    Reported because a balanced accuracy well above chance can still coexist with a
    degenerate prediction distribution; kappa penalises that.
    """
    yt = np.asarray(y_true).ravel()
    yp = np.asarray(y_pred).ravel()
    labs = np.union1d(np.unique(yt), np.unique(yp))
    n = yt.size
    if n == 0:
        return float("nan")
    idx = {int(lab): i for i, lab in enumerate(labs)}
    m = np.zeros((labs.size, labs.size), dtype=np.float64)
    for t, p in zip(yt.tolist(), yp.tolist()):
        m[idx[int(t)], idx[int(p)]] += 1
    po = float(np.trace(m) / n)
    pe = float((m.sum(axis=0) * m.sum(axis=1)).sum() / (n * n))
    return float("nan") if pe == 1.0 else (po - pe) / (1.0 - pe)


def per_subject_balanced_accuracy(
    y_true: np.ndarray, y_pred: np.ndarray, subject_ids: Sequence
) -> dict[str, float]:
    """Balanced accuracy computed **within each subject**.

    This is the number that predicts behaviour on a new person. It is also the number
    that a pooled average hides. ``subject_ids`` are opaque; do not pass DB9's in-file
    ``subject`` field, which is source-database-local and collides across source
    databases.
    """
    yt = np.asarray(y_true).ravel()
    yp = np.asarray(y_pred).ravel()
    subs = np.asarray(list(subject_ids)).ravel()
    if not (yt.shape == yp.shape == subs.shape):
        raise ValueError(
            f"shape mismatch: y_true {yt.shape}, y_pred {yp.shape}, subjects {subs.shape}"
        )
    out: dict[str, float] = {}
    for s in sorted(set(subs.tolist()), key=str):
        mask = subs == s
        labs = np.unique(yt[mask])
        if labs.size == 0:
            continue
        recalls = []
        for lab in labs:
            sel = mask & (yt == lab)
            recalls.append(float((yp[sel] == lab).mean()))
        out[str(s)] = float(np.mean(recalls))
    return out


@dataclass(frozen=True)
class SubjectSpread:
    """Distribution of a per-subject metric. The tail is the interesting part."""

    n_subjects: int
    median: float
    worst: float
    best: float
    p10: float
    p90: float
    n_below_chance: int

    def summary(self, label: str = "balanced accuracy") -> str:
        return (
            f"per-subject {label}: n={self.n_subjects} median={self.median:.4f} "
            f"worst={self.worst:.4f} best={self.best:.4f} "
            f"p10={self.p10:.4f} p90={self.p90:.4f} "
            f"subjects at/below chance={self.n_below_chance}"
        )


def per_subject_report(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    subject_ids: Sequence,
    *,
    chance: float | None = None,
) -> SubjectSpread:
    """Summarise the per-subject distribution, including the tail."""
    values = per_subject_balanced_accuracy(y_true, y_pred, subject_ids)
    if not values:
        raise ValueError("no subjects in the evaluation set")
    arr = np.array(list(values.values()), dtype=np.float64)
    n_below = int((arr <= (chance if chance is not None else 0.0)).sum())
    return SubjectSpread(
        n_subjects=int(arr.size),
        median=float(np.median(arr)),
        worst=float(arr.min()),
        best=float(arr.max()),
        p10=float(np.percentile(arr, 10)),
        p90=float(np.percentile(arr, 90)),
        n_below_chance=n_below,
    )


__all__ = [
    "ClassificationReport",
    "SubjectSpread",
    "classification_report",
    "cohen_kappa",
    "per_subject_balanced_accuracy",
    "per_subject_report",
]
