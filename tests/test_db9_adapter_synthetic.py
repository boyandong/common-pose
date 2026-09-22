"""End-to-end DB9 adapter test on a synthetic `.mat`.

Skipped automatically when scipy is unavailable. This exercises the whole loading path —
channel-order resolution, the segmentation trap refusal, verdict-driven validity, and the
utility-protocol segmentation — against a file this test constructs, so no third-party
dataset is needed and none is redistributed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

scipy_io = pytest.importorskip("scipy.io", reason="scipy is required for .mat I/O")

from common_pose import Validity  # noqa: E402
from common_pose.adapters.base import AdapterError  # noqa: E402
from common_pose.adapters.db9 import DB9Adapter, DB9_CHANNEL_ORDER  # noqa: E402

SEGMENT = 100
MOVEMENTS = (1, 3, 6, 11, 9)   # 6 is the fist, 11 is the reference posture, 9 is wrist
REPETITIONS = (1, 2)


def _write_synth(path: Path, *, truncate_labels_by: int = 0) -> Path:
    """Build a minimal but structurally faithful Exercise-B recording."""
    rng = np.random.default_rng(0)
    n = SEGMENT * len(MOVEMENTS) * len(REPETITIONS)
    angles = rng.normal(20.0, 10.0, size=(n, 22))
    # Vendor-excluded index-middle abduction sensor: all-NaN in the release.
    angles[:, 5] = np.nan

    restim = np.zeros(n, dtype=np.int32)
    rerep = np.zeros(n, dtype=np.int32)
    cursor = 0
    for mov in MOVEMENTS:
        for rep in REPETITIONS:
            sl = slice(cursor, cursor + SEGMENT)
            restim[sl] = mov
            rerep[sl] = rep
            # MCP2_f flexes on an unambiguous fist (movement 6)...
            angles[sl, 4] += 30.0 * (mov == 6)
            # ...while DIP3 moves the opposite way. That inversion is the audited defect.
            angles[sl, 17] -= 15.0 * (mov == 6)
            cursor += SEGMENT

    order = np.array(
        [f"{i + 1}:{c}" for i, c in enumerate(DB9_CHANNEL_ORDER)], dtype=object
    )
    payload = {
        "angles": angles,
        "restimulus": restim[: n - truncate_labels_by],
        "rerepetition": rerep[: n - truncate_labels_by],
        "order_of_angles": order,
    }
    scipy_io.savemat(str(path), payload)
    return path


@pytest.fixture()
def synth_mat(tmp_path: Path) -> Path:
    return _write_synth(tmp_path / "S1_E2_A1.mat")


def test_trusted_arm_loads_and_every_kept_dimension_is_usable(synth_mat: Path):
    adapter = DB9Adapter(mat_path=synth_mat, subset="trusted")
    stream = adapter.load()
    assert adapter.validate(stream) == []
    assert len(stream.registry) == 8
    assert len(stream) == SEGMENT * len(MOVEMENTS) * len(REPETITIONS)
    assert all(v == 1.0 for v in stream.valid_fraction().values())
    assert stream.native_rate_hz == 25.0


def test_handshape_selection_and_central_window(synth_mat: Path):
    adapter = DB9Adapter(mat_path=synth_mat)
    all_frames = adapter.load()
    handshape = adapter.load(handshape_only=True)

    # MOVEMENTS = (1, 3, 6, 11, 9): three are hand shapes (1, 3, 6) and two are not
    # (11 is the reference posture, 9 is a wrist movement). Movement 11 is correctly
    # excluded from the hand-shape task even though it defines the zero.
    n_handshape = len(set(MOVEMENTS) & {1, 2, 3, 4, 5, 6, 7, 8, 17})
    assert n_handshape == 3
    assert len(all_frames) == SEGMENT * len(MOVEMENTS) * len(REPETITIONS)
    assert len(handshape) == SEGMENT * n_handshape * len(REPETITIONS)

    central = adapter.load(handshape_only=True, central_fraction=0.6)
    per_segment = int(round(SEGMENT * 0.6))
    assert len(central) == per_segment * n_handshape * len(REPETITIONS)


def test_movement_selection_and_handshape_only_are_mutually_exclusive(synth_mat: Path):
    adapter = DB9Adapter(mat_path=synth_mat)
    with pytest.raises(ValueError, match="not both"):
        adapter.load(movements=[1], handshape_only=True)


def test_reference_movement_is_included_in_the_full_selection(synth_mat: Path):
    """Movement 11 defines the zero, so it must survive a full-selection load."""
    stream = DB9Adapter(mat_path=synth_mat).load()
    assert len(stream) > 0
    assert 11 in stream.provenance.extras["movements_included"]


def test_historial_arm_marks_dropped_channels_invalid_without_zeroing(synth_mat: Path):
    adapter = DB9Adapter(mat_path=synth_mat, subset="canonical16")
    stream = adapter.load()

    dip3 = stream.validity_column("middle_dip_flexion")
    assert all(v is Validity.INVALID for v in dip3)
    # The released value is emitted verbatim, not repaired and not zeroed: a re-reader
    # must still be able to reproduce the historical number.
    raw = stream.column("middle_dip_flexion")
    assert np.isfinite(raw).all()

    # MCP2_f (canonical index_mcp_flexion) is a real channel on this file, so its column
    # must be finite. Its sibling MCP2_a is the all-NaN vendor-excluded sensor, and that
    # one is absent from canonical16 entirely rather than emitted as NaN.
    assert np.isfinite(stream.column("index_mcp_flexion")).all()

    # The kept dimensions on this arm are VALID.
    assert all(
        v is Validity.VALID for v in stream.validity_column("index_pip_flexion")
    )


def test_dropped_dimensions_are_reported_by_the_contract(synth_mat: Path):
    adapter = DB9Adapter(mat_path=synth_mat, subset="canonical16")
    problems = adapter.validate(adapter.load())
    assert any("middle_dip_flexion" in p and "DROPped" in p for p in problems)
    assert any("pinky_dip_flexion" in p and "DROPped" in p for p in problems)


def test_segmentation_trap_is_refused_not_silently_handled(tmp_path: Path):
    """`repetition` is 7 samples longer than the kinematics in 24 of 99 released files.
    A loader that indexes kinematics with a misaligned vector shifts every boundary."""
    bad = _write_synth(tmp_path / "S13_E2_A1.mat", truncate_labels_by=7)
    with pytest.raises(AdapterError, match="length mismatch"):
        DB9Adapter(mat_path=bad).load()


def _resave(path: Path, mutate) -> Path:
    """Load, mutate one field, and re-save without scipy's metadata keys."""
    payload = {
        k: v
        for k, v in scipy_io.loadmat(str(path)).items()
        if not k.startswith("__")
    }
    mutate(payload)
    scipy_io.savemat(str(path), payload)
    return path


def test_missing_order_of_angles_is_refused(tmp_path: Path):
    """Channel order must come from the file, never from an index convention."""
    p = _write_synth(tmp_path / "S1_E2_A1.mat")
    _resave(p, lambda d: d.pop("order_of_angles", None))
    with pytest.raises(AdapterError, match="order_of_angles"):
        DB9Adapter(mat_path=p).load()


def test_wrong_channel_order_is_refused(tmp_path: Path):
    """A file whose declared order disagrees with the audited order must not load."""
    p = _write_synth(tmp_path / "S1_E2_A1.mat")

    def swap_first_two(d: dict) -> None:
        order = [str(x) for x in np.atleast_1d(d["order_of_angles"]).ravel()]
        order[0], order[1] = order[1], order[0]
        d["order_of_angles"] = np.array(order, dtype=object)

    _resave(p, swap_first_two)
    with pytest.raises(AdapterError, match="order_of_angles"):
        DB9Adapter(mat_path=p).load()
