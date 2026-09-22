"""The Common Pose API namespace.

Frozen vs provisional, stated plainly
-------------------------------------
This package mixes two very different kinds of thing, and the distinction matters more
than the code:

FROZEN EVIDENCE (do not re-derive, do not re-word)
    ``audits/db9/trusted_pose/TRUSTED_DB9_POSE_v1.json`` — the DB9 channel subset,
    frozen before any classifier ran. Loaded by :func:`~common_pose.load_trusted_db9_subset`.

PROVISIONAL INTERFACE (expect it to change)
    Everything in this module: the container, the registry, the adapter ABC. The
    container is deliberately not frozen, because the project is still establishing what
    the interface must carry.

The one rule the interface enforces
-----------------------------------
A value never travels without its interpretability. There is no accessor anywhere in
this package that returns a bare joint angle without either a paired
:class:`~common_pose.api.verdicts.Validity` or an explicit statement that validity was
not established. That is a deliberate ergonomic cost.
"""

from .dof import (
    DofRegistry,
    DofSpec,
    get_registry,
    load_trusted_db9_subset,
    trusted_db9_exclusions,
)
from .pose_frame import PoseFrame, PoseStream, frames_to_stream, iter_frames
from .provenance import Provenance
from .verdicts import AuditVerdict, Validity

__all__ = [
    "AuditVerdict",
    "DofRegistry",
    "DofSpec",
    "PoseFrame",
    "PoseStream",
    "Provenance",
    "Validity",
    "frames_to_stream",
    "get_registry",
    "iter_frames",
    "load_trusted_db9_subset",
    "trusted_db9_exclusions",
]
