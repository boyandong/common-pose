"""Common Pose — a standardized physical hand-pose interface (research prototype).

The intended chain is::

    biosignal / EMG
          |
          v
    pose estimator            (upstream, replaceable)
          |
          v
    Common Pose API           <- this package: physical semantics + validity + provenance
          |
          v
    reusable downstream task head

Status
------
This package is a **research prototype**, not a deployment SDK. It exists so that the
physical semantics of a hand-pose stream — units, sign conventions, zero/reference
definitions, calibration provenance and validity — travel *with the numbers* instead of
being re-derived from an index convention at every consumption site.

What is deliberately not claimed here
-------------------------------------
* that a universal task-transfer interface has been demonstrated;
* that two datasets' identically-named joints are numerically interchangeable;
* that every dimension of any released dataset is a trustworthy anatomical measurement.

See ``docs/research_status.md`` for the evidence ledger.

Public surface
--------------
``DofSpec`` / ``DofRegistry``   anatomical degree-of-freedom registry
``PoseFrame`` / ``PoseStream``  the time-stamped joint-state container
``Validity``                    per-dimension validity vocabulary
``Provenance``                  calibration / extraction provenance record
``load_trusted_db9_subset``     the frozen, physically audited DB9 subset
"""

from __future__ import annotations

from .api.dof import DofRegistry, DofSpec, get_registry, load_trusted_db9_subset
from .api.pose_frame import PoseFrame, PoseStream
from .api.provenance import Provenance
from .api.verdicts import AuditVerdict, Validity

__all__ = [
    "AuditVerdict",
    "DofRegistry",
    "DofSpec",
    "PoseFrame",
    "PoseStream",
    "Provenance",
    "Validity",
    "get_registry",
    "load_trusted_db9_subset",
]

__version__ = "0.1.0.dev0"
__status__ = "research-prototype"
