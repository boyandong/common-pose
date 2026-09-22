"""Downstream task heads trained on Common Pose state, not on task-specific biosignals.

The design intent is that a task head consumes ``pose + label``. If a task head needed
the raw biosignal, the interface would not be doing any work, and the research question
("does a standardized physical pose interface decouple biosignal decoding from task
definition?") would be untestable by construction.

Current members
---------------
``posture``
    DB9 postural-shape identification from joint angles alone: the decoupled half of the
    chain, and the first downstream task. No EMG, no deep networks.

``phase``
    Reaching-vs-manipulation phase observability from KIN-MUS pose, with a permutation
    null, a boundary stratification and a velocity-negation control. Its physical
    *interpretation* is downgraded for four of ten columns by the dataset-admission
    audit; see ``docs/research_status.md``.
"""

from __future__ import annotations

from .posture import PostureTask, posture_representation_names

__all__ = ["PostureTask", "posture_representation_names"]
