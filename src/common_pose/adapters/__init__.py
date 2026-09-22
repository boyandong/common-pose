"""Adapters: released dataset -> Common Pose stream.

An adapter's job is not to reshape an array. It is to answer, for every dimension it
emits, the questions in ``docs/common_pose_api.md`` — and to answer ``NOT_ESTABLISHED``
where the project has not established the answer.

Members
-------
``base``
    The ABC and the shared checks. :meth:`PoseAdapter.validate` is the contract.
``db9``
    Ninapro DB9 (Exercise B). Carries the frozen trusted-subset verdicts in-band.
``emg2pose``
    The emg2pose model output. Applies the IK-failure validity rule, without which
    15.6 percent of the official mini corpus is silently treated as poses.

The ``db9/`` sub-package below this one holds the DB9 task pipeline (loader, canonical
mapping, labels, quality checks) carried over from the research workspace. That is source
material for the adapter, not part of the interface itself.

Not yet written
---------------
MyoKi, KIN-MUS UJI and KINE-ADL BE-UJI were audited for admission but their corpora are
not redistributable and were not all obtained, so no adapter ships for them. Their column
orders, DOF coverage and unresolved blockers are recorded under
``audits/dataset_admission/``.
"""

from __future__ import annotations

from .base import AdapterCapability, AdapterError, PoseAdapter

__all__ = ["AdapterCapability", "AdapterError", "PoseAdapter"]
