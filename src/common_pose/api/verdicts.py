"""Validity and audit-verdict vocabularies.

Two distinct vocabularies live here, and conflating them is the single easiest way to
overstate what this project knows:

``Validity``
    A property of **one number in one pose frame**. It answers: may this dimension of
    this sample be interpreted as the physical quantity it is named after?

``AuditVerdict``
    A property of **a channel in a released dataset**, established by an offline
    physical audit. It answers: has this channel been shown to behave as its published
    anatomical definition requires?

A dimension whose dataset-level verdict is ``KEEP`` can still carry ``INVALID`` samples
(missing sensor, saturated gauge, out-of-range). A dimension whose verdict is
``INCONCLUSIVE`` is not thereby wrong — it is *not established*, and downstream code must
say so rather than defaulting it to zero.
"""

from __future__ import annotations

from enum import Enum


class Validity(str, Enum):
    """Per-sample, per-dimension interpretability.

    This is a three-state vocabulary on purpose. A boolean ``is_valid`` flag forces
    "not yet established" to collapse into either "valid" or "invalid", and both
    collapse directions have silently corrupted results in this project's history
    (see ``audits/db9/channel_forensic/BUGFIX_LOG.md``).

    .. warning::
       This enum mixes in ``str`` for ergonomic comparison in ordinary Python code.
       That makes it **unsafe to store in an ``object``-dtype NumPy array**: NumPy
       applies its own string conversion and the member silently degrades to the
       Python string ``'Valid'``, which is neither a member nor a valid code. The
       container therefore stores validity as :data:`VALIDITY_CODES` (int8) and
       converts through :func:`validity_from_code` — see
       ``common_pose.api.pose_frame``. Do not "simplify" that back to an object array.
    """

    VALID = "VALID"
    """The value may be interpreted as the named physical quantity."""

    INVALID = "INVALID"
    """The value is KNOWN not to be interpretable: missing sensor, all-NaN column,
    out-of-anatomical-range, or an explicitly excluded channel. Do not substitute 0 —
    0 is a legitimate angle (the extended hand)."""

    NOT_ESTABLISHED = "NOT_ESTABLISHED"
    """No physical validity evidence exists for this dimension in this dataset/session.
    Neither usable nor known-bad. Downstream code must handle this explicitly."""

    @property
    def usable(self) -> bool:
        """Only ``VALID`` is usable. ``NOT_ESTABLISHED`` is not usable by default."""
        return self is Validity.VALID

    @property
    def code(self) -> int:
        return VALIDITY_CODES[self]


#: Int8 wire codes. Order matters only in that it must stay stable.
VALIDITY_CODES: Mapping[Validity, int] = {
    Validity.INVALID: 0,
    Validity.NOT_ESTABLISHED: 1,
    Validity.VALID: 2,
}

#: Reverse lookup: int8 code -> member.
VALIDITY_BY_CODE: Mapping[int, Validity] = {v: k for k, v in VALIDITY_CODES.items()}

#: Default code for a dimension whose validity was never established.
NOT_ESTABLISHED_CODE: int = VALIDITY_CODES[Validity.NOT_ESTABLISHED]


def validity_from_code(code: int) -> Validity:
    """Decode one validity cell. Refuses to guess.

    A lenient decoder here would turn "not established" into "valid", which is the
    single most damaging silent default in an interface of this kind.
    """
    try:
        return VALIDITY_BY_CODE[int(code)]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            f"{code!r} is not a validity code; known codes: "
            f"{ {k: v.name for k, v in VALIDITY_BY_CODE.items()} }"
        ) from exc


class AuditVerdict(str, Enum):
    """Dataset-channel-level outcome of a frozen physical validity audit.

    The vocabulary is fixed by the audit plan
    (``audits/db9/channel_forensic/FORENSIC_PLAN.md``, SHA-256
    ``4c618b562903d0d364d03bb8a997ef6b4140bd9e09d0f2475f1b008ad80c8793``) and must not be
    re-worded here. Verdict strings in the frozen artifacts are mapped onto this enum
    verbatim; see ``audits/db9/trusted_pose/TRUSTED_DB9_POSE_v1.json``.
    """

    KEEP = "KEEP"
    """Passes the frozen physical criteria; included in the trusted subset."""

    DROP = "DROP"
    """Evidence establishes that the released channel is not the named physical
    quantity. Excluded."""

    INCONCLUSIVE = "INCONCLUSIVE"
    """The available evidence does not settle the question. Excluded from the trusted
    subset, but NOT asserted to be broken."""

    OFFICIAL_EXCLUSION = "OFFICIAL_EXCLUSION"
    """The dataset's own documentation excludes the channel. Sub-case of DROP carried
    separately because the evidence source is the vendor, not this audit."""

    @classmethod
    def parse(cls, raw: str) -> "AuditVerdict":
        key = str(raw).strip().upper().replace("-", "_").replace(" ", "_")
        if key in cls.__members__:
            return cls[key]
        raise ValueError(f"unknown audit verdict {raw!r}; refusing to guess a mapping")


__all__ = ["AuditVerdict", "Validity"]
