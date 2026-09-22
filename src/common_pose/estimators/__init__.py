"""Upstream pose estimators: biosignal in, hand joint state out.

These are the replaceable front end of the chain. Nothing downstream of the Common Pose
API may depend on which estimator produced a stream — that substitution is the research
question, not an implementation detail.

``emg2pose``
    A wrapper (not the model) around the official pretrained baseline. The baseline is
    not redistributed: it is licensed CC-BY-NC-SA-4.0 and its bundled UmeTrack is
    CC-BY-NC-4.0. See ``docs/licensing.md``.
"""

from __future__ import annotations

__all__: list[str] = []
