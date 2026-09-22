"""Explicit, non-destructive data-quality checks for Ninapro DB9.

Design rule: **flag, never silently delete.**  Every check returns a boolean
mask plus human-readable diagnostics; callers decide what to do with them, and
the report states the flagged proportion.  Nothing here mutates the arrays it
is given.

What is checked, and with what evidence
---------------------------------------
1. **Missing values.**  The official DB9 docs state that the index-middle
   abduction channel (MCP2-3_A, column ``6:MCP2_a``) "was not included into the
   calibrated data due to noise problems".  Measured: that column is all-NaN and
   it is the only such column.  Handled by the canonical table, not by guessing.

2. **Frozen channels.**  A channel that never varies carries no information.
   Reported, not dropped (a frozen channel in a *posture* experiment can be a
   genuine finding, e.g. a sensor that never moved).

3. **Range sanity.**  DB9 calibrated ``angles`` are in **degrees** (measured).
   Absolute anatomical limits are NOT asserted here: the DB9 calibration maps
   glove readings onto a subject-specific scale, so applying emg2pose/UmeTrack
   limits to them would be an unjustified comparison.  Instead this module
   reports robust empirical ranges and flags deviations from a *robust* centre
   using MAD, which needs no external constant.  Where a genuine anatomical
   limit would be required, a ``TODO`` is emitted rather than an invented number.

4. **Temporal glitches.**  Large single-sample jumps.  The CyberGlove link ran
   at "slightly less than 25 Hz" and DB9 super-sampled to 100/200/2000 Hz, so
   consecutive samples are interpolated and *should* be smooth.  A big jump is
   therefore a real glitch, not fast motion.

5. **Label/sample bookkeeping.**  `restimulus == 0` is the rest position and
   `rerepetition == 0` marks rest/transition, i.e. no movement is being
   performed.  These samples are legitimate but must never be scored as if they
   were one of the 40 movements.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np

#: Emitted wherever a check would require an anatomical constant that the
#: official DB9 material does not supply for the DB9 calibration scale.
ANATOMICAL_LIMIT_TODO = (
    "TODO(anatomical-range): DB9 publishes calibrated CyberGlove angles on a "
    "subject-specific scale, not in an anatomical joint convention. Absolute "
    "per-joint anatomical limits therefore cannot be applied to these numbers "
    "without an external calibration mapping that the official release does "
    "not provide. Only robust, data-internal outlier checks are performed."
)


@dataclass
class QualityReport:
    """Outcome of the checks for one recording (or one pooled dataset)."""

    n_samples: int
    n_channels: int
    label: str = ""

    nan_columns: list[int] = field(default_factory=list)
    nan_row_count: int = 0
    nan_row_fraction: float = 0.0
    #: Rows with a NaN in a channel that is not entirely dead.  This is the
    #: number that signals an actual problem; ``nan_row_fraction`` is dominated
    #: by the officially-excluded all-NaN sensor.
    nan_live_row_count: int = 0
    nan_live_row_fraction: float = 0.0

    frozen_columns: list[int] = field(default_factory=list)

    #: True when the robust centre was estimated per (restimulus, rerepetition).
    group_conditional_outliers: bool = False

    #: rows whose robust z-score exceeds `mad_z_threshold` on >=1 channel
    outlier_rows: np.ndarray | None = None
    outlier_row_count: int = 0
    outlier_row_fraction: float = 0.0
    outlier_counts_per_channel: list[int] = field(default_factory=list)

    #: rows following a single-sample jump larger than `jump_threshold_deg`
    jump_rows: np.ndarray | None = None
    jump_row_count: int = 0
    jump_row_fraction: float = 0.0
    jump_counts_per_channel: list[int] = field(default_factory=list)

    rest_samples: int = 0
    rest_fraction: float = 0.0

    per_channel_min: list[float] = field(default_factory=list)
    per_channel_max: list[float] = field(default_factory=list)
    per_channel_median: list[float] = field(default_factory=list)
    per_channel_mad: list[float] = field(default_factory=list)

    channel_names: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def usable_rows(self) -> np.ndarray:
        """Boolean mask of rows that pass every flag-based check.

        This is a *convenience* mask, not an automatic filter: `outlier_rows`
        and `jump_rows` are deliberately excluded only when the caller asks for
        it via :meth:`strict_mask`.
        """
        if self.outlier_rows is None:
            raise ValueError("report has not been computed")
        return ~self.outlier_rows

    def strict_mask(self) -> np.ndarray:
        """Rows passing BOTH the outlier and the jump checks."""
        if self.outlier_rows is None or self.jump_rows is None:
            raise ValueError("report has not been computed")
        return ~(self.outlier_rows | self.jump_rows)

    def summary(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "n_samples": self.n_samples,
            "n_channels": self.n_channels,
            "nan_columns": self.nan_columns,
            "nan_row_count": self.nan_row_count,
            "nan_row_fraction": round(self.nan_row_fraction, 6),
            "nan_live_row_count": self.nan_live_row_count,
            "nan_live_row_fraction": round(self.nan_live_row_fraction, 6),
            "frozen_columns": self.frozen_columns,
            "group_conditional_outliers": self.group_conditional_outliers,
            "outlier_row_count": self.outlier_row_count,
            "outlier_row_fraction": round(self.outlier_row_fraction, 6),
            "jump_row_count": self.jump_row_count,
            "jump_row_fraction": round(self.jump_row_fraction, 6),
            "rest_samples": self.rest_samples,
            "rest_fraction": round(self.rest_fraction, 6),
            "notes": self.notes,
        }


def check_angles(
    angles: np.ndarray,
    *,
    restimulus: np.ndarray | None = None,
    rerepetition: np.ndarray | None = None,
    channel_names: list[str] | None = None,
    mad_z_threshold: float = 8.0,
    jump_threshold_deg: float = 45.0,
    label: str = "",
) -> QualityReport:
    """Run all checks on one (N, C) angle array in DEGREES.

    Outlier detection is **label-conditional when labels are supplied**.  A
    whole-recording robust centre is useless here: the rest position dominates
    the sample count (measured on subject 1: 63% of frames are rest), so a
    recording-wide MAD is essentially the rest distribution's width and every
    genuine movement sample looks like an "outlier".  Conditioning the robust
    centre on ``(restimulus, rerepetition)`` asks the question that actually
    matters for data quality -- *is this sample odd for the movement it claims
    to be* -- instead of *is this sample different from rest*, which is the
    signal.

    Parameters
    ----------
    mad_z_threshold
        Robust z-score (``0.6745 * (x - median) / MAD``) above which a sample is
        flagged.  8.0 is deliberately loose: meant to catch gross artefacts,
        not to trim the natural spread of real hand motion.
    jump_threshold_deg
        Single-sample change above which a row is flagged.  Natural hand motion
        cannot exceed this between consecutive samples of a >=25 Hz signal.
    """
    a = np.asarray(angles, dtype=float)
    if a.ndim != 2:
        raise ValueError(f"expected (N, C) angles, got {a.shape}")
    n, c = a.shape
    names = list(channel_names) if channel_names else [f"col{i}" for i in range(c)]

    rep = QualityReport(n_samples=n, n_channels=c, label=label, channel_names=names)
    rep.notes.append(ANATOMICAL_LIMIT_TODO)

    # ---- 1. missing values -------------------------------------------------
    finite = np.isfinite(a)
    col_all_nan = ~finite.any(axis=0)
    rep.nan_columns = [int(i) for i in np.where(col_all_nan)[0]]
    live = ~col_all_nan
    # Two different numbers, because they mean different things:
    #  - "any NaN at all" is dominated by the officially-excluded dead channel
    #  - "NaN in a live channel" is the number that actually signals a problem
    rep.nan_row_count = int((~finite.all(axis=1)).sum())
    rep.nan_live_row_count = int((~finite[:, live].all(axis=1)).sum()) if live.any() else 0
    rep.nan_row_fraction = rep.nan_row_count / n if n else 0.0
    rep.nan_live_row_fraction = rep.nan_live_row_count / n if n else 0.0
    if rep.nan_columns:
        rep.notes.append(
            f"{len(rep.nan_columns)} all-NaN column(s) (officially excluded "
            "sensors): " + ", ".join(names[i] for i in rep.nan_columns)
        )

    # ---- 2. frozen channels ------------------------------------------------
    col_std = np.zeros(c)
    for i in range(c):
        if live[i]:
            col_std[i] = float(np.nanstd(a[:, i]))
        else:
            col_std[i] = float("nan")
    rep.frozen_columns = [
        int(i) for i in range(c) if np.isfinite(col_std[i]) and col_std[i] == 0.0
    ]

    # ---- 3. robust range + (label-conditional) outliers -------------------
    if restimulus is not None:
        rs = np.asarray(restimulus).reshape(-1)
        if rerepetition is not None:
            rr = np.asarray(rerepetition).reshape(-1)
        else:
            rr = np.zeros(n, dtype=np.int64)
        keys = np.stack([rs, rr], axis=1)
        uniq, inverse = np.unique(keys, axis=0, return_inverse=True)
        inverse = inverse.reshape(-1)
        centre = np.zeros((len(uniq), c))
        scale = np.zeros((len(uniq), c))
        # The officially-excluded sensor is all-NaN, so nanmedian legitimately
        # hits an all-NaN slice for that column; that is expected and handled
        # (its z-scores are forced to 0 below), so silence the notice here
        # rather than let it look like an unexplained failure.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            for g in range(len(uniq)):
                rows = a[inverse == g]
                m = np.nanmedian(rows, axis=0)
                centre[g] = m
                scale[g] = np.nanmedian(np.abs(rows - m), axis=0)
        per_row_centre = centre[inverse]
        per_row_scale = scale[inverse]
        rep.notes.append(
            f"outlier check is conditional on (restimulus, rerepetition): "
            f"{len(uniq)} groups; a recording-wide centre would flag genuine "
            "movement as anomalous because rest dominates the sample count"
        )
        rep.group_conditional_outliers = True
    else:
        per_row_centre = np.nanmedian(a, axis=0)[None, :]
        per_row_scale = np.nanmedian(np.abs(a - per_row_centre), axis=0)[None, :]
        rep.group_conditional_outliers = False

    with np.errstate(invalid="ignore", divide="ignore"):
        denom = np.where(per_row_scale > 0, per_row_scale, np.nan)
        robust_z = 0.6745 * np.abs(a - per_row_centre) / denom
    z = np.nan_to_num(robust_z, nan=0.0, posinf=0.0, neginf=0.0)
    z[:, col_all_nan] = 0.0
    row_out = (z > mad_z_threshold).any(axis=1)
    rep.outlier_rows = row_out
    rep.outlier_row_count = int(row_out.sum())
    rep.outlier_row_fraction = rep.outlier_row_count / n if n else 0.0
    rep.outlier_counts_per_channel = [
        int((z[:, i] > mad_z_threshold).sum()) for i in range(c)
    ]
    rep.per_channel_min = [float(np.nanmin(a[:, i])) if live[i] else float("nan")
                           for i in range(c)]
    rep.per_channel_max = [float(np.nanmax(a[:, i])) if live[i] else float("nan")
                           for i in range(c)]
    med = np.nanmedian(a, axis=0)
    mad = np.nanmedian(np.abs(a - med), axis=0)
    rep.per_channel_median = [float(v) for v in med]
    rep.per_channel_mad = [float(v) for v in mad]

    # ---- 4. temporal glitches ---------------------------------------------
    # NaN columns are dropped first so one dead sensor cannot flag every row.
    live = ~np.array(col_all_nan)
    if live.any() and n > 1:
        d = np.abs(np.diff(a[:, live], axis=0))
        jump = np.zeros(n, dtype=bool)
        jump[1:] = (np.nan_to_num(d, nan=0.0) > jump_threshold_deg).any(axis=1)
        jump_counts_live = [
            int((np.nan_to_num(d[:, i], nan=0.0) > jump_threshold_deg).sum())
            for i in range(d.shape[1])
        ]
        live_idx = [i for i in range(c) if live[i]]
        counts = [0] * c
        for pos, ci in enumerate(live_idx):
            counts[ci] = jump_counts_live[pos]
    else:
        jump = np.zeros(n, dtype=bool)
        counts = [0] * c
    rep.jump_rows = jump
    rep.jump_row_count = int(jump.sum())
    rep.jump_row_fraction = rep.jump_row_count / n if n else 0.0
    rep.jump_counts_per_channel = counts

    # ---- 5. rest / transition bookkeeping ---------------------------------
    if restimulus is not None:
        rs = np.asarray(restimulus).reshape(-1)
        rep.rest_samples = int((rs == 0).sum())
        rep.rest_fraction = rep.rest_samples / n if n else 0.0

    return rep


def aggregate_summary(reports: list[QualityReport]) -> dict[str, Any]:
    """Pool per-recording reports into one summary for the report table."""
    if not reports:
        return {}
    total = sum(r.n_samples for r in reports)
    return {
        "n_recordings": len(reports),
        "total_samples": total,
        "nan_columns_by_recording": {r.label: r.nan_columns for r in reports if r.nan_columns},
        "nan_column_consistency": len({tuple(r.nan_columns) for r in reports}),
        "nan_row_fraction_any": sum(r.nan_row_count for r in reports) / total if total else 0.0,
        "nan_row_fraction_live_channels": (
            sum(r.nan_live_row_count for r in reports) / total if total else 0.0
        ),
        "outlier_row_fraction": sum(r.outlier_row_count for r in reports) / total if total else 0.0,
        "outliers_group_conditional": all(r.group_conditional_outliers for r in reports),
        "jump_row_fraction": sum(r.jump_row_count for r in reports) / total if total else 0.0,
        "rest_fraction": sum(r.rest_samples for r in reports) / total if total else 0.0,
        "frozen_columns_union": sorted({c for r in reports for c in r.frozen_columns}),
        "jump_threshold_note": (
            "single-sample change > 45 deg; the glove link ran at <25 Hz and was "
            "super-sampled, so consecutive samples are interpolated and should be smooth"
        ),
        "anatomical_limits": ANATOMICAL_LIMIT_TODO,
    }
