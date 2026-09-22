"""Contract tests for the Common Pose API.

These are not smoke tests. Each one pins a property whose violation has already produced
a wrong scientific result somewhere in this project's history, or would produce one
silently. Run with::

    python -m pytest tests/ -q

Pure numpy/scipy/sklearn; no GPU, no dataset download, no training.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from common_pose import (  # noqa: E402
    DofRegistry,
    DofSpec,
    PoseFrame,
    PoseStream,
    Provenance,
    Validity,
    get_registry,
    load_trusted_db9_subset,
)
from common_pose.api.dof import trusted_db9_exclusions  # noqa: E402
from common_pose.api.verdicts import VALIDITY_CODES, NOT_ESTABLISHED_CODE  # noqa: E402
from common_pose.evaluation.metrics import (  # noqa: E402
    classification_report,
    per_subject_report,
)
from common_pose.tasks.posture import PostureTask, posture_representation_names  # noqa: E402

VALID = VALIDITY_CODES[Validity.VALID]
INVALID = VALIDITY_CODES[Validity.INVALID]


def _codes(n: int, d: int, fill: int = VALID) -> np.ndarray:
    """Validity code array. Codes, not enum members — see the Validity docstring."""
    return np.full((n, d), fill, dtype=np.int8)


# --------------------------------------------------------------------------- #
# Vocabulary
# --------------------------------------------------------------------------- #


def test_canonical16_has_sixteen_dimensions():
    reg = get_registry("canonical16")
    assert len(reg) == 16
    assert len(reg.names) == len(set(reg.names))


def test_canonical16_source_indices_are_unique():
    """Two DOF claiming one column is exactly how a subset gets mislabelled."""
    reg = get_registry("canonical16")
    db9 = reg.by_source_index("db9")
    emg = reg.by_source_index("emg2pose")
    assert len(db9) == 16
    assert len(emg) == 16


def test_db9_channel_order_matches_the_released_declaration():
    """The order is read from the .mat's own order_of_angles; pin it."""
    from common_pose.adapters.db9 import DB9_CHANNEL_ORDER

    assert DB9_CHANNEL_ORDER[5] == "MCP2_a"
    assert DB9_CHANNEL_ORDER[16] == "DIP2"
    assert DB9_CHANNEL_ORDER[20] == "WRIST_F"
    assert len(DB9_CHANNEL_ORDER) == 22


def test_vendor_excluded_channel_is_all_nan_in_the_release_and_named():
    from common_pose.adapters.db9 import DB9_VENDOR_EXCLUDED

    assert "MCP2_a" in DB9_VENDOR_EXCLUDED
    reg = get_registry("canonical16")
    assert all(s.db9_channel != "MCP2_a" for s in reg.specs)


# --------------------------------------------------------------------------- #
# The frozen trusted subset
# --------------------------------------------------------------------------- #


def test_trusted_subset_is_the_frozen_eight_channels():
    reg = load_trusted_db9_subset()
    assert reg.names == (
        "thumb_mcp_flexion",
        "thumb_ip_flexion",
        "index_mcp_flexion",
        "index_pip_flexion",
        "middle_mcp_flexion",
        "ring_mcp_flexion",
        "pinky_mcp_flexion",
        "pinky_pip_flexion",
    )


def test_trusted_subset_records_that_it_preceded_any_classifier():
    """The ordering guarantee is the reason the subset is evidence rather than a result
    chosen for its accuracy. It must be visible from the object, not just the paper."""
    reg = load_trusted_db9_subset()
    assert "frozen_before_any_classifier=True" in reg.provenance
    assert "FROZEN EVIDENCE" in reg.status
    assert "Revalidated across all 77 DB9 participants" in reg.status


def test_trusted_subset_carries_no_wrist_dimension():
    """The subset has no wrist channel by construction, which is why the wrist-inclusive
    task is not a fair evaluation of it."""
    reg = load_trusted_db9_subset()
    assert not any("wrist" in n for n in reg.names)


def test_exclusions_separate_established_broken_from_not_established():
    ex = trusted_db9_exclusions()
    assert {e["name"] for e in ex["DROP"]} == {
        "MCP2_a", "CMC5", "MCP5_a", "DIP3", "DIP5", "WRIST_A",
    }
    assert len(ex["INCONCLUSIVE"]) == 8


def test_trusted_subset_reports_agreement_and_subject_count():
    reg = load_trusted_db9_subset()
    for spec in reg.specs:
        assert "n=37 subjects" in spec.calibration_provenance
        assert "agreement with the official sign criterion" in spec.calibration_provenance


# --------------------------------------------------------------------------- #
# Registry mechanics
# --------------------------------------------------------------------------- #


def test_registry_refuses_duplicate_names():
    reg = get_registry("canonical16")
    with pytest.raises(ValueError, match="duplicate DOF name"):
        DofRegistry(name="dup", specs=(reg.specs[0], reg.specs[0]))


def test_registry_lookup_error_lists_available_names():
    reg = get_registry("canonical16")
    with pytest.raises(KeyError, match="available:"):
        _ = reg["no_such_dof"]


def test_unknown_registry_name_raises():
    with pytest.raises(KeyError):
        get_registry("canonical17")


def test_incomplete_semantics_are_reported_not_defaulted():
    """A DOF with an unanswerable field must say so, never invent a default."""
    spec = DofSpec("made_up_dof", "index", "MCP", "FE")
    assert not spec.fully_specified
    assert "INCOMPLETE SEMANTICS" in spec.describe()


# --------------------------------------------------------------------------- #
# PoseStream container
# --------------------------------------------------------------------------- #


def _tiny_provenance() -> Provenance:
    return Provenance(
        source_dataset="unit-test",
        source_identity="synthetic",
        calibration_established=None,
        code_version="COMMIT PENDING",
    )


def _tiny_stream(
    n: int = 5, registry: DofRegistry | None = None, dt: float = 0.04
) -> PoseStream:
    reg = registry or load_trusted_db9_subset()
    t = np.arange(n, dtype=np.float64) * dt
    v = np.zeros((n, len(reg)), dtype=np.float64)
    return PoseStream(
        timestamps_s=t, values=v, validity=_codes(n, len(reg)), registry=reg,
        provenance=_tiny_provenance(), native_rate_hz=25.0,
    )


def test_stream_rejects_shape_vocabulary_mismatch():
    reg = load_trusted_db9_subset()
    with pytest.raises(ValueError, match="registry"):
        PoseStream(
            timestamps_s=np.arange(3.0),
            values=np.zeros((3, len(reg) + 1)),
            registry=reg,
            provenance=_tiny_provenance(),
        )


def test_stream_rejects_non_increasing_timestamps():
    reg = load_trusted_db9_subset()
    with pytest.raises(ValueError, match="strictly increasing"):
        PoseStream(
            timestamps_s=np.array([0.0, 0.1, 0.1]),
            values=np.zeros((3, len(reg))),
            registry=reg,
            provenance=_tiny_provenance(),
        )


def test_validity_must_be_supplied_as_members_or_codes_not_strings():
    """Coercing a string validity is how 'not established' becomes 'valid'."""
    reg = load_trusted_db9_subset()
    bad = np.full((3, len(reg)), "VALID", dtype=object)
    with pytest.raises(TypeError, match="Refusing to coerce"):
        PoseStream(
            timestamps_s=np.arange(3.0), values=np.zeros((3, len(reg))),
            validity=bad, registry=reg, provenance=_tiny_provenance(),
        )


def test_object_array_of_members_is_rejected_rather_than_silently_degraded():
    """NumPy turns a str-mixin enum into a bare Python string inside an object array.

    That degradation is silent and would make every cell look non-valid, or (if the
    check were lenient) make everything valid. The container must refuse it, which is
    why it stores int8 codes instead.
    """
    reg = load_trusted_db9_subset()
    d = len(reg)
    degraded = np.full((3, d), Validity.VALID, dtype=object)
    assert not isinstance(degraded[0, 0], Validity), (
        "precondition: this NumPy version is expected to degrade the enum here"
    )
    with pytest.raises(TypeError, match="Refusing to coerce"):
        PoseStream(
            timestamps_s=np.arange(3.0), values=np.zeros((3, d)),
            validity=degraded, registry=reg, provenance=_tiny_provenance(),
        )


def test_int_code_validity_array_is_accepted_and_round_trips():
    reg = load_trusted_db9_subset()
    s = PoseStream(
        timestamps_s=np.arange(2.0), values=np.zeros((2, len(reg))),
        validity=_codes(2, len(reg)), registry=reg, provenance=_tiny_provenance(),
    )
    codes = s.validity_column("index_pip_flexion")
    assert all(c is Validity.VALID for c in codes)


def test_out_of_range_validity_code_is_rejected_at_construction():
    reg = load_trusted_db9_subset()
    bad = _codes(2, len(reg))
    bad[0, 0] = 99
    with pytest.raises(ValueError, match="not a validity code"):
        PoseStream(
            timestamps_s=np.arange(2.0), values=np.zeros((2, len(reg))),
            validity=bad, registry=reg, provenance=_tiny_provenance(),
        )


def test_missing_validity_defaults_to_not_established_never_valid():
    """An adapter that forgets validity must not get a free pass."""
    reg = load_trusted_db9_subset()
    s = PoseStream(
        timestamps_s=np.arange(3.0), values=np.zeros((3, len(reg))),
        registry=reg, provenance=_tiny_provenance(),
    )
    assert np.all(s.validity == NOT_ESTABLISHED_CODE)
    assert all(c is Validity.NOT_ESTABLISHED for c in s.validity_column("index_pip_flexion"))
    assert s.valid_fraction()["index_pip_flexion"] == 0.0


def test_zero_valued_invalid_sample_is_not_treated_as_a_pose():
    """The emg2pose IK-failure encoding: all-zero rows that are NOT poses."""
    reg = load_trusted_db9_subset()
    d = len(reg)
    val = np.array([np.full(d, INVALID, dtype=np.int8), np.full(d, VALID, dtype=np.int8)])
    s = PoseStream(
        timestamps_s=np.array([0.0, 0.04]), values=np.zeros((2, d)), validity=val,
        registry=reg, provenance=_tiny_provenance(),
    )
    mask = s.mask()
    assert not mask[0].any(), "all-zero frame marked INVALID must not count as usable"
    assert mask[1].all(), "all-zero frame marked VALID is the extended hand and counts"


def test_window_and_history_are_half_open():
    # dt = 0.1 keeps the boundary arithmetic exact, so this checks the half-open
    # convention rather than floating-point luck.
    s = _tiny_stream(n=10, dt=0.1)
    w = s.window(0.0, 0.2)
    assert len(w) == 2
    assert w.timestamps_s[0] == 0.0
    assert w.timestamps_s[-1] < 0.2
    h = s.history(end_s=0.3, lookback_s=0.2)
    assert len(h) == 2
    assert h.timestamps_s[-1] == pytest.approx(0.2)


def test_window_rejects_empty_range():
    s = _tiny_stream()
    with pytest.raises(ValueError, match="empty/inverted"):
        s.window(0.2, 0.2)


def test_select_keeps_requested_order_and_subset():
    s = _tiny_stream()
    sel = s.select(["pinky_pip_flexion", "index_mcp_flexion"])
    assert sel.registry.names == ("pinky_pip_flexion", "index_mcp_flexion")
    assert len(sel.registry) == 2


def test_provenance_warnings_flag_unverifiable_calibration():
    s = _tiny_stream()
    warnings = s.provenance_warnings()
    assert any("numeric coordinate equivalence" in w for w in warnings)


def test_sample_rate_is_derived_when_not_given():
    s = _tiny_stream(n=25)
    assert s.sample_rate_hz == pytest.approx(25.0)


def test_describe_reports_weak_dimensions_and_warnings():
    reg = load_trusted_db9_subset()
    n = 4
    val = _codes(n, len(reg))
    val[:, 0] = INVALID
    s = PoseStream(
        timestamps_s=np.arange(n, dtype=np.float64) / 25.0,
        values=np.zeros((n, len(reg))), validity=val, registry=reg,
        provenance=_tiny_provenance(),
    )
    text = s.describe()
    assert "below 100 percent valid" in text
    assert "WARNING" in text


# --------------------------------------------------------------------------- #
# PoseFrame
# --------------------------------------------------------------------------- #


def test_frame_get_returns_value_with_validity():
    reg = load_trusted_db9_subset()
    f = PoseFrame(
        t_s=0.0, values={"index_pip_flexion": 12.5}, registry=reg,
        provenance=_tiny_provenance(),
        validity={"index_pip_flexion": Validity.VALID},
    )
    value, state = f.get("index_pip_flexion")
    assert value == 12.5 and state is Validity.VALID


def test_frame_absent_dimension_is_nan_and_not_established():
    reg = load_trusted_db9_subset()
    f = PoseFrame(t_s=0.0, values={}, registry=reg, provenance=_tiny_provenance())
    value, state = f.get("index_pip_flexion")
    assert np.isnan(value) and state is Validity.NOT_ESTABLISHED


def test_frame_rejects_dimensions_outside_the_registry():
    reg = load_trusted_db9_subset()
    with pytest.raises(KeyError, match="not in registry"):
        PoseFrame(
            t_s=0.0, values={"elbow_flexion": 1.0}, registry=reg,
            provenance=_tiny_provenance(),
        )


def test_frame_rejects_string_validity():
    reg = load_trusted_db9_subset()
    with pytest.raises(TypeError, match="Validity member"):
        PoseFrame(
            t_s=0.0, values={"index_pip_flexion": 1.0}, registry=reg,
            provenance=_tiny_provenance(), validity={"index_pip_flexion": "VALID"},
        )


# --------------------------------------------------------------------------- #
# Adapter contract
# --------------------------------------------------------------------------- #


def test_emg2pose_ik_mask_reproduces_the_official_rule():
    from common_pose.adapters.emg2pose import ik_failures_mask

    arr = np.array(
        [
            [0.0] * 20,
            [0.1] * 20,
            np.zeros(20),
            [1e-9] * 20,
            [0.0] * 19 + [0.5],
        ]
    )
    mask = ik_failures_mask(arr)
    assert list(mask) == [False, True, False, False, True]


def test_emg2pose_adapter_marks_ik_failures_invalid_and_wrist_absent():
    from common_pose.adapters.emg2pose import Emg2PoseAdapter

    adapter = Emg2PoseAdapter()
    arr = np.full((4, 20), 0.2, dtype=np.float64)
    arr[2, :] = 0.0  # an IK failure row, encoded as zeros
    stream = adapter.load(arr, source_identity="synthetic")
    assert adapter.validate(stream) == []
    # Every canonical16 dimension that emg2pose publishes is VALID except row 2.
    valid = stream.validity_column("index_pip_flexion")
    assert [v is Validity.VALID for v in valid] == [True, True, False, True]
    # The wrist dimensions emg2pose does not regress are INVALID, never zero.
    for name in ("wrist_flexion", "wrist_deviation"):
        if name in stream.registry.names:
            col = stream.validity_column(name)
            assert all(v is Validity.INVALID for v in col)
    assert stream.metadata["inflation_factor"] == pytest.approx(40.0)
    assert stream.native_rate_hz == pytest.approx(50.0)


def test_emg2pose_adapter_rejects_wrong_joint_width():
    from common_pose.adapters.base import AdapterError
    from common_pose.adapters.emg2pose import Emg2PoseAdapter

    with pytest.raises(AdapterError, match="20"):
        Emg2PoseAdapter().load(np.zeros((5, 19)))


def test_canonical16_arm_is_flagged_for_its_dropped_dimensions():
    """The historical vocabulary contains channels the audit DROPped. A re-reader must
    be able to see which ones, in-band."""
    from common_pose.adapters.db9 import DB9Adapter

    adapter = DB9Adapter(subset="canonical16")
    cap = adapter.capability
    assert {"middle_dip_flexion", "pinky_dip_flexion"}.issubset(
        set(cap.dimensions_restricted)
    )
    assert cap.db9_verdicts_are_authoritative is True


def test_canonical16_specs_carry_the_frozen_verdicts():
    """Every canonical16 dimension with a DB9 column must carry its audit verdict.
    Without this, a re-reader silently re-adopts a dropped channel."""
    from common_pose.api.verdicts import AuditVerdict

    reg = get_registry("canonical16")
    with_db9 = [s for s in reg.specs if s.db9_channel is not None]
    assert len(with_db9) == 16
    assert all(s.db9_verdict is not None for s in with_db9)
    verdicts = {s.name: s.db9_verdict for s in with_db9}
    assert verdicts["middle_dip_flexion"] is AuditVerdict.DROP
    assert verdicts["pinky_dip_flexion"] is AuditVerdict.DROP
    assert verdicts["ring_dip_flexion"] is AuditVerdict.INCONCLUSIVE
    assert verdicts["index_pip_flexion"] is AuditVerdict.KEEP
    # The trusted subset is exactly the KEEP set.
    assert {n for n, v in verdicts.items() if v is AuditVerdict.KEEP} == set(
        load_trusted_db9_subset().names
    )


def test_db9_verdicts_are_scoped_to_the_db9_source():
    """An emg2pose column is not the DB9 CyberGlove column, so a DB9 DROP verdict must
    not be applied to it. Getting this wrong in either direction is a defect."""
    from common_pose.adapters.emg2pose import Emg2PoseAdapter

    assert Emg2PoseAdapter().capability.db9_verdicts_are_authoritative is False


def test_db9_adapter_rejects_invalid_subset_name():
    from common_pose.adapters.db9 import DB9Adapter

    with pytest.raises(ValueError, match="trusted"):
        DB9Adapter(subset="everything")


def test_db9_adapter_refuses_missing_file_with_an_actionable_message():
    from common_pose.adapters.base import AdapterError
    from common_pose.adapters.db9 import DB9Adapter

    with pytest.raises(FileNotFoundError, match="Ninapro"):
        DB9Adapter().load("does_not_exist.mat")


# --------------------------------------------------------------------------- #
# Task definition
# --------------------------------------------------------------------------- #


def test_posture_task_defaults_to_handshape_only():
    task = PostureTask()
    assert task.movement_ids == (1, 2, 3, 4, 5, 6, 7, 8, 17)
    assert task.n_classes == 9
    assert task.chance_balanced_accuracy == pytest.approx(1 / 9)
    assert 11 not in task.movement_ids


def test_wrist_inclusive_task_is_available_but_not_the_default():
    task = PostureTask(include_wrist_movements=True)
    assert task.n_classes == 17
    assert task.chance_balanced_accuracy == pytest.approx(1 / 17)


def test_wristless_arm_is_flagged_as_unable_to_carry_a_wrist_task():
    """The reason the mixed task understates the trusted subset is a property of the
    protocol, so it must be checkable rather than remembered."""
    assert PostureTask().may_be_carrying("trusted")
    assert not PostureTask(include_wrist_movements=True).may_be_carrying("trusted")


def test_representation_names_are_indices_free():
    assert len(posture_representation_names("trusted")) == 8
    assert len(posture_representation_names("canonical16")) == 16


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #


def test_perfect_predictions_give_unit_scores():
    y = np.array([1, 1, 2, 2, 3, 3])
    rep = classification_report(y, y)
    assert rep.accuracy == 1.0
    assert rep.balanced_accuracy == 1.0
    assert rep.macro_f1 == 1.0
    assert not rep.class_collapse


def test_missing_class_is_reported_not_hidden():
    y_true = np.array([1, 1, 2, 2, 3, 3])
    y_pred = np.array([1, 1, 2, 2, 2, 2])  # class 3 never predicted
    rep = classification_report(y_true, y_pred)
    assert 3 in rep.missing_classes
    assert 3 in rep.classes_with_recall_below_half
    assert rep.class_collapse


def test_balanced_accuracy_is_unweighted_mean_of_recall():
    y_true = np.array([1] * 10 + [2])
    y_pred = np.array([1] * 10 + [1])  # the rare class is always wrong
    rep = classification_report(y_true, y_pred)
    assert rep.accuracy == pytest.approx(10 / 11)
    assert rep.balanced_accuracy == pytest.approx(0.5)


def test_per_subject_tail_is_exposed():
    """Subject-held-out claims live or die on the worst subject, not the mean."""
    y_true = np.array([1, 2, 1, 2, 1, 2, 1, 2])
    y_pred = np.array([1, 2, 1, 2, 1, 1, 2, 2])  # the second subject is at chance
    subjects = ["a", "a", "a", "a", "b", "b", "b", "b"]
    spread = per_subject_report(y_true, y_pred, subjects, chance=0.5)
    assert spread.n_subjects == 2
    assert spread.worst == pytest.approx(0.5)
    assert spread.best == pytest.approx(1.0)
    assert spread.n_below_chance == 1


def test_report_rejects_empty_input():
    with pytest.raises(ValueError, match="empty"):
        classification_report(np.array([]), np.array([]))


def test_frozen_utility_record_is_self_consistent():
    """The published numbers must satisfy their own arithmetic. A transcription error in
    a README table is a scientific error, so it is checked rather than trusted."""
    from common_pose.tasks.posture import FROZEN_HANDSHAPE_UTILITY

    a = FROZEN_HANDSHAPE_UTILITY["A_historical_canonical16"]
    b = FROZEN_HANDSHAPE_UTILITY["B_TRUSTED_DB9_POSE_v1"]
    # The official task is the eight Exercise B hand configurations, movement IDs 1-8.
    # Movement IDs 9-17 are wrist movements and 17 is not a hand-shape class.
    assert a.n_classes == 8 and b.n_classes == 8
    assert a.chance_balanced_accuracy == pytest.approx(1 / 8)
    assert b.chance_balanced_accuracy == pytest.approx(1 / 8)
    assert a.n_subjects == 77 and b.n_subjects == 77
    assert b.balanced_accuracy < a.balanced_accuracy
    assert a.class_collapse is False and b.class_collapse is False
    # Class 4 is the weakest class and must stay visible in the official record.
    assert b.classes_with_recall_below_half == (4,)
    # ~6.0x chance, the claim made in the docs.
    assert 5.5 < b.balanced_accuracy_over_chance < 6.5
    # The loss is what the trusted subset costs; it must be reported, not buried.
    assert 0.09 < (a.balanced_accuracy - b.balanced_accuracy) < 0.12


def test_historical_mixed_task_record_is_kept_but_is_not_the_benchmark():
    """The 37-subject, 9-class run counted movement 17 as a hand-shape class. It is kept
    for traceability and must stay clearly separated from the official task."""
    from common_pose.tasks.posture import (FROZEN_HANDSHAPE_UTILITY,
                                           HISTORICAL_MIXED_TASK_UTILITY)

    h = HISTORICAL_MIXED_TASK_UTILITY["B_TRUSTED_DB9_POSE_v1"]
    assert h.n_classes == 9 and h.n_subjects == 37
    assert h.arm == FROZEN_HANDSHAPE_UTILITY["B_TRUSTED_DB9_POSE_v1"].arm
    assert h.balanced_accuracy != FROZEN_HANDSHAPE_UTILITY[
        "B_TRUSTED_DB9_POSE_v1"].balanced_accuracy
