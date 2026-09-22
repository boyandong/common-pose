"""The emg2pose estimator wrapper.

This package carries a *wrapper* around the official emg2pose pretrained baseline, not the
baseline itself. Two reasons, and the licensing one is not incidental:

* **Licensing.** The baseline is released under CC-BY-NC-SA-4.0, and its bundled UmeTrack
  under CC-BY-NC-4.0. Neither is redistributed here. Locate your own checkout with
  ``COMMON_POSE_EMG2POSE_BASELINE``.
* **Packaging.** The wrapper is a few hundred lines with no deep-learning dependency at
  import time. Vendoring a PyTorch project into a research repository that does not need
  PyTorch to run its audits would be a large dependency for no benefit.

``predict_pose`` windows the official model into an EMG-only interface. The model needs
``TDS_LEFT_CONTEXT`` (1790) samples of history before its first output row, so the output
is ``(T - 1790, 20)``, not ``(T, 20)`` — a detail that silently misaligns predictions
against ground truth if it is assumed away.

See ``common_pose.adapters.emg2pose`` for the Common Pose adapter that consumes this.
"""

from __future__ import annotations

__all__: list[str] = []
