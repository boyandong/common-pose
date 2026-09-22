"""A reusable task head: representative postures -> movement label, from pose alone.

This is the smallest thing that can answer the project's decoupling question. It reads a
``PoseStream`` and a label array. It never sees a biosignal, a subject id, or a dataset
identity, and it never sees test-fold statistics during fitting.

Leakage rules this head enforces mechanically
---------------------------------------------
* **Train-fold-only normalisation.** Standardisation statistics come from the training
  fold. Computing them over the whole corpus leaks test information into the model, and
  it is invisible in the accuracy number.
* **Subject-disjoint folds are the caller's obligation, and are not checked here.** The
  head cannot know whether two rows come from the same person, because the in-file
  ``subject`` field of DB9 is source-database-local and collides across source databases.
  Pass a split that was built from a verified identity map. See
  ``audits/db9/channel_forensic/DB9_FORENSIC_DECISION.md``, "subject-identity collision".
* **Invalid samples are dropped, not zero-filled.** Rows whose validity is not
  ``VALID`` for every dimension used are excluded, and the count is reported.

Dependencies: numpy + scikit-learn. No torch, no GPU.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

import numpy as np

from ..api.pose_frame import PoseStream
from ..api.verdicts import Validity


@dataclass
class PostureTaskHead:
    """Linear discriminant posture classifier over a fixed set of pose dimensions.

    Parameters
    ----------
    dimensions:
        Pose dimensions to use, in order. Names, not indices — an index-based selection
        is how a subset gets silently mislabelled.
    """

    dimensions: Sequence[str]
    shrinkage: str | float | None = "auto"
    solver: str = "lsqr"

    _model: object | None = field(default=None, init=False, repr=False)
    _center: np.ndarray | None = field(default=None, init=False, repr=False)
    _scale: np.ndarray | None = field(default=None, init=False, repr=False)
    classes_: np.ndarray | None = field(default=None, init=False, repr=False)
    n_dropped_train_: int = field(default=0, init=False)
    n_dropped_test_: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if not self.dimensions:
            raise ValueError("dimensions must be non-empty")
        if len(set(self.dimensions)) != len(self.dimensions):
            raise ValueError("duplicate dimension names in `dimensions`")

    # -- helpers ------------------------------------------------------------- #

    def _matrix(self, stream: PoseStream) -> tuple[np.ndarray, np.ndarray]:
        """Extract ``(X, usable)`` for the configured dimensions.

        ``usable`` is the per-row AND over exactly the configured dimensions. A row is
        dropped when any of the dimensions the model actually reads is not VALID.
        """
        cols = []
        usable = np.ones(len(stream), dtype=bool)
        for name in self.dimensions:
            if name not in stream.registry.names:
                raise KeyError(
                    f"dimension {name!r} is not present in the stream vocabulary "
                    f"{stream.registry.name!r}; available: "
                    f"{', '.join(stream.registry.names)}"
                )
            cols.append(stream.column(name))
            usable &= np.array([c.usable for c in stream.validity_column(name)])
        X = np.column_stack(cols).astype(np.float64)
        return X, usable

    # -- fit / predict ------------------------------------------------------- #

    def fit(self, stream: PoseStream, labels: np.ndarray) -> "PostureTaskHead":
        from sklearn.discriminant_analysis import LinearDiscriminantAnalysis

        y = np.asarray(labels).ravel()
        if y.shape[0] != len(stream):
            raise ValueError(
                f"{y.shape[0]} labels for {len(stream)} frames"
            )
        X, usable = self._matrix(stream)
        if not usable.all():
            self.n_dropped_train_ = int((~usable).sum())
            X, y = X[usable], y[usable]
        if X.shape[0] == 0:
            raise ValueError("no usable training samples after the validity mask")

        # Train-fold-only statistics. Fitted here, applied in predict().
        self._center = X.mean(axis=0)
        scale = X.std(axis=0, ddof=1)
        scale[scale == 0.0] = 1.0
        self._scale = scale

        model = LinearDiscriminantAnalysis(solver=self.solver, shrinkage=self.shrinkage)
        model.fit((X - self._center) / self._scale, y)
        self._model = model
        self.classes_ = np.asarray(model.classes_)
        return self

    def predict(self, stream: PoseStream) -> tuple[np.ndarray, np.ndarray]:
        """Return ``(predictions, usable)``.

        Predictions for unusable rows are ``-1``; ``usable`` tells the caller which rows
        those are, so a caller that averages over ``predictions`` without checking gets
        an obviously wrong answer rather than a plausible one.
        """
        if self._model is None or self._center is None or self._scale is None:
            raise RuntimeError("PostureTaskHead.predict called before fit")
        X, usable = self._matrix(stream)
        preds = np.full(X.shape[0], -1, dtype=np.int64)
        if usable.any():
            Xz = (X[usable] - self._center) / self._scale
            preds[usable] = self._model.predict(Xz).astype(np.int64)
        self.n_dropped_test_ = int((~usable).sum())
        return preds, usable

    # -- description --------------------------------------------------------- #

    def describe(self) -> str:
        state = "fitted" if self._model is not None else "unfitted"
        return "\n".join(
            [
                f"PostureTaskHead [{state}]",
                f"  dimensions   {len(self.dimensions)}: {', '.join(self.dimensions)}",
                f"  model        LinearDiscriminantAnalysis(solver={self.solver!r}, "
                f"shrinkage={self.shrinkage!r})",
                f"  normalisation train-fold-only z-score "
                f"(center/scale fitted on the training fold)",
                f"  dropped (train) {self.n_dropped_train_}   dropped (test) "
                f"{self.n_dropped_test_}",
            ]
        )


def validity_summary(stream: PoseStream, dimensions: Sequence[str]) -> Mapping[str, float]:
    """Usable fraction per dimension, for the dimensions a head actually reads.

    Reported next to every score, because a dimension that is mostly invalid will
    silently dominate an unmasked statistic.
    """
    out: dict[str, float] = {}
    for name in dimensions:
        col = stream.validity_column(name)
        out[name] = float(np.mean([c is Validity.VALID for c in col]))
    return out


__all__ = ["PostureTaskHead", "validity_summary"]
