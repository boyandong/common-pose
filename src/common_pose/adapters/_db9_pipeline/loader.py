"""Loading official Ninapro DB9 MATLAB files into tidy, validated arrays.

Formats
-------
Ninapro distributes MATLAB ``.mat`` files that may be MATLAB v5 (readable with
``scipy.io.loadmat``) or v7.3 (HDF5, readable with ``h5py``).  This loader
sniffs the actual file magic rather than guessing from the file name, because
the two source databases involved (DB1, DB2/DB5) were not converted with the
same MATLAB version.

Variables documented in the official DB9 page
(https://ninapro.hevs.ch/instructions/DB9.html) for every exercise file:

    Subject       subject number
    Exercise      exercise number
    glove         (N, 22) uncalibrated CyberGlove-II sensor signal
    angles        (N, 22) calibrated joint angles
    inclin        (N, 2)  inclinometer (roll, pitch)
    restimulus    (N, 1)  a-posteriori refined movement label
    rerepetition  (N, 1)  repetition index of restimulus
    order         (22)    the name of each angle column

Official caveat carried in the docs: "Sensor 11 (which corresponds to
MCP2-3_A) was not included into the calibrated data due to noise problems."
This loader does **not** silently drop or repair that column -- it reports what
it actually finds so the claim can be checked against the data.

Nothing in this module filters, resamples or repairs the signal.  Quality
decisions belong to :mod:`db9.quality` and must be explicit.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import numpy as np

#: Official variable names.  The DB9 page lists "order of angles"; MATLAB
#: stores that as ``order_of_angles`` (verified present in every archive).  The
#: bare ``order`` spelling is accepted too in case a conversion renames it.
VARIABLES = (
    "subject",
    "exercise",
    "glove",
    "angles",
    "inclin",
    "restimulus",
    "rerepetition",
    "repetition",
    "stimulus",
    "order_of_angles",
    "order",
)

#: Exercises actually shipped inside the DB9 archives, keyed by the value of
#: each file's own ``exercise`` variable.  IMPORTANT: that variable keeps the
#: *source database's* original numbering, which differs between DB1 and
#: DB2/DB5, so it can never be used directly as a DB9 exercise index.
#:    Atzori et al. 2014, Table 1:
#:      DB1: exercise 1 = A(12), 2 = B(17), 3 = C(23)
#:      DB2: exercise 1 = B(17), 2 = C(23), 3 = D(9)
#:      DB5: exercise 1 = B(17), 2 = C(23), 3 = D(9)
#: DB9 ships only B and C, so the (source_db, exercise) -> Ninapro letter
#: mapping below is what identifies a file.  It is additionally cross-checked
#: against the observed ``restimulus`` maximum, which is 17 for B and 23 for C.
NINAPRO_LETTER_BY_SOURCE_EXERCISE: dict[tuple[str, int], str] = {
    ("DB1", 2): "B", ("DB1", 3): "C",
    ("DB2", 1): "B", ("DB2", 2): "C",
    ("DB5", 1): "B", ("DB5", 2): "C",
}

#: ``max(restimulus)`` expected for each Ninapro exercise letter.
EXPECTED_MAX_LABEL = {"B": 17, "C": 23}

#: Sampling rates the official DB9 page / paper state for each source database
#: ("the data streams were super-sampled to the highest sampling frequency in
#: the acquisition setup (100 Hz, 2 kHz and 200 Hz respectively for Ninapro
#: DB1, DB2 and DB5)").  NOTE these are *super-sampled* rates: the CyberGlove
#: itself transmitted at "slightly less than 25 Hz", so consecutive samples are
#: heavily interpolated.  See `effective_source_rate_hz`.
NOMINAL_RATE_HZ = {"DB1": 100.0, "DB2": 2000.0, "DB5": 200.0}

#: The physical CyberGlove-II link rate, per the DB9 paper. This -- not the
#: super-sampled rate -- bounds the true temporal resolution of the data.
CYBERGLOVE_LINK_RATE_HZ = 25.0


class MatLoadError(RuntimeError):
    """Raised when a DB9 MATLAB file cannot be read in either supported format."""


@dataclass
class Db9Recording:
    """One subject x exercise recording, straight from the official archive."""

    subject: int
    exercise: int
    path: str
    order: list[str]           # names of the 22 angle columns
    angles: np.ndarray         # (N, 22) float64, calibrated
    glove: np.ndarray          # (N, 22) float64, uncalibrated
    inclin: np.ndarray | None  # (N, 2) float64 or None if absent
    restimulus: np.ndarray     # (N,) int
    rerepetition: np.ndarray   # (N,) int
    n_samples: int
    source_format: str         # "mat5" | "mat73"

    @property
    def duration_s(self) -> float:
        return float(self.n_samples)

    def labels_present(self) -> np.ndarray:
        return np.unique(self.restimulus)


def _sniff_format(path: str) -> str:
    """Return 'mat73', 'mat5' or raise. Sniffs content, not the extension."""
    with open(path, "rb") as fh:
        head = fh.read(128)
    if head[:8] == b"\x89HDF\r\n\x1a\n":
        return "mat73"
    if head[:4] == b"MATL" or head[124:126] == b"IM":
        return "mat5"
    # Some writers emit a bare MAT5 header without the 'IM' marker at 124.
    if head[:2] == b"\x01\x00" or head[:2] == b"\x00\x01":
        return "mat5"
    raise MatLoadError(
        f"{path}: unrecognised container (first bytes {head[:8]!r}); "
        "refusing to guess a MATLAB version"
    )


def _load_mat5(path: str) -> dict[str, Any]:
    from scipy.io import loadmat

    raw = loadmat(path, squeeze_me=False, struct_as_record=False)
    return {k: v for k, v in raw.items() if not k.startswith("__")}


def _load_mat73(path: str) -> dict[str, Any]:
    import h5py

    out: dict[str, Any] = {}
    with h5py.File(path, "r") as f:
        for key in f.keys():
            node = f[key]
            if isinstance(node, h5py.Dataset):
                arr = np.array(node)
                # MATLAB stores column-major; h5py gives the transposed shape.
                if arr.ndim == 2 and key in ("angles", "glove", "inclin"):
                    arr = arr.T
                out[key] = arr
            else:  # nested struct, e.g. a table wrapper
                for sub in node.keys():
                    arr = np.array(node[sub])
                    if arr.ndim == 2 and sub in ("angles", "glove", "inclin"):
                        arr = arr.T
                    out[sub] = arr
    return out


def _as_2d(a: Any, name: str, path: str) -> np.ndarray:
    arr = np.asarray(a, dtype=np.float64)
    arr = np.squeeze(arr)
    if arr.ndim == 1:
        arr = arr[:, None]
    if arr.ndim != 2:
        raise MatLoadError(f"{path}: variable '{name}' has shape {arr.shape}")
    return arr


def _as_1d_int(a: Any, name: str, path: str, n: int) -> np.ndarray:
    arr = np.asarray(a).squeeze()
    if arr.ndim == 0:
        arr = arr.reshape(1)
    if arr.size != n:
        raise MatLoadError(
            f"{path}: variable '{name}' has {arr.size} values but the recording "
            f"has {n} samples"
        )
    return np.rint(arr.astype(np.float64)).astype(np.int64)


def _order_names(a: Any) -> list[str]:
    """Decode the MATLAB cell array of column names into plain strings."""
    out: list[str] = []
    flat = np.asarray(a).squeeze()
    for item in np.atleast_1d(flat):
        s = item
        while isinstance(s, np.ndarray):
            s = s.squeeze()
            if s.ndim == 0:
                s = s.item()
                break
            if s.size == 1:
                s = s.reshape(-1)[0]
            else:
                break
        if isinstance(s, bytes):
            s = s.decode("utf-8", "replace")
        out.append(str(s).strip())
    return out


def load_recording(path: str, expect_subject: int | None = None,
                   expect_exercise: int | None = None) -> Db9Recording:
    """Read one official DB9 exercise file and validate its internal metadata."""
    fmt = _sniff_format(path)
    data = _load_mat5(path) if fmt == "mat5" else _load_mat73(path)

    missing = [v for v in ("angles", "restimulus", "rerepetition") if v not in data]
    if missing:
        raise MatLoadError(
            f"{path}: missing required variable(s) {missing}; found {sorted(data)}"
        )

    angles = _as_2d(data["angles"], "angles", path)
    n = angles.shape[0]

    glove = (
        _as_2d(data["glove"], "glove", path)
        if "glove" in data
        else np.full_like(angles, np.nan)
    )
    if glove.shape[0] != n:
        raise MatLoadError(f"{path}: glove has {glove.shape[0]} rows, angles has {n}")

    inclin = None
    if "inclin" in data:
        inclin = _as_2d(data["inclin"], "inclin", path)
        if inclin.shape[0] != n:
            raise MatLoadError(f"{path}: inclin has {inclin.shape[0]} rows, angles has {n}")

    restimulus = _as_1d_int(data["restimulus"], "restimulus", path, n)
    rerepetition = _as_1d_int(data["rerepetition"], "rerepetition", path, n)

    subject = int(np.asarray(data["subject"]).squeeze()) if "subject" in data else -1
    exercise = int(np.asarray(data["exercise"]).squeeze()) if "exercise" in data else -1

    # The file's own metadata must agree with where the archive put it, or the
    # subject/exercise bookkeeping is wrong and every downstream label is suspect.
    if expect_subject is not None and subject not in (-1, expect_subject):
        raise MatLoadError(
            f"{path}: file says subject={subject} but archive slot says {expect_subject}"
        )
    if expect_exercise is not None and exercise not in (-1, expect_exercise):
        raise MatLoadError(
            f"{path}: file says exercise={exercise} but archive slot says {expect_exercise}"
        )

    order = []
    for key in ("order_of_angles", "order"):
        if key in data:
            order = _order_names(data[key])
            break

    return Db9Recording(
        subject=subject,
        exercise=exercise,
        path=path,
        order=order,
        angles=angles,
        glove=glove,
        inclin=inclin,
        restimulus=restimulus,
        rerepetition=rerepetition,
        n_samples=n,
        source_format=fmt,
    )


def discover_unpacked(extracted_dir: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for root, _dirs, files in os.walk(extracted_dir):
        if "__MACOSX" in root.replace("\\", "/").split("/"):
            continue
        for f in files:
            if not f.lower().endswith(".mat"):
                continue
            if f.startswith("._"):  # macOS AppleDouble sidecar, not a MAT file
                continue
            base = os.path.basename(root)
            digits = "".join(ch for ch in base.split("_")[1] if ch.isdigit()) if base.startswith("s_") else ""
            if not digits:
                digits = "".join(ch for ch in f.split("_")[1] if ch.isdigit()) if f.startswith("s_") else ""
            if not digits:
                continue
            found.append((int(digits), os.path.join(root, f)))
    return sorted(found)


# ---------------------------------------------------------------------------
# Which Ninapro exercise is this file?
# ---------------------------------------------------------------------------
# The DB9 archives keep each source database's *original* exercise numbering,
# so `rec.exercise` alone is ambiguous across subjects.  The official subject ->
# source database table (DB1 = 1-27, DB2 = 28-67, DB5 = 68-77) disambiguates it,
# and the observed label range is used as an independent cross-check.
def source_db_for_subject(subject: int) -> str:
    if 1 <= subject <= 27:
        return "DB1"
    if 28 <= subject <= 67:
        return "DB2"
    if 68 <= subject <= 77:
        return "DB5"
    raise ValueError(f"subject {subject} is outside the official DB9 numbering (1-77)")


#: Expected offset between the DB9 archive slot and the numeric value stored in
#: a file's own ``subject`` variable.  Each source database numbered its own
#: subjects from 1 while the DB9 archive keeps the global 1..77 numbering:
#:     DB1 subjects 1..27  -> recorded == archive slot
#:     DB2 subjects 28..67 -> recorded == archive slot - 27
#:     DB5 subjects 68..77 -> recorded == archive slot - 67
#: The offset is checked, but only as a *consistency warning*: the archive slot
#: is what the official DB9 table indexes, and it is what defines subject
#: identity for a subject-independent split.  Divergence is reported because it
#: signals a labelling defect in the release, not because it invalidates the
#: slot.  (Observed: slot 69 records subject=11 where the offset predicts 2.)
SUBJECT_RECORDED_OFFSET = {"DB1": 0, "DB2": 27, "DB5": 67}


def resolve_subject(
    archive_subject: int, recorded_subject: int, path: str = ""
) -> tuple[int, str | None]:
    """Return ``(authoritative_subject_id, anomaly_note_or_None)``.

    The authoritative id is the **DB9 archive slot**: the official DB9 table
    lists one row per slot, and one slot is one participant, so the slot is a
    well-defined person identifier even when the in-file ``subject`` field is
    defective.  The recorded field is never used as the identity, because each
    source database restarted its own numbering from 1 -- using it verbatim
    would silently merge DB5 participants with DB1 participants of the same
    number.

    A mismatch with the expected offset is returned as a note.  Callers are
    expected to surface it; ``build_dataset`` additionally checks that the
    slot -> recorded mapping is injective across the whole corpus, which is the
    property that actually protects a subject-independent split.
    """
    db = source_db_for_subject(archive_subject)
    expected = archive_subject - SUBJECT_RECORDED_OFFSET[db]
    if recorded_subject == expected:
        return archive_subject, None
    return archive_subject, (
        f"{path}: archive slot s_{archive_subject} (source {db}) records "
        f"subject={recorded_subject} internally, but the source database's own "
        f"numbering predicts {expected}. The archive slot is used as the "
        "authoritative identity; this is an inconsistency in the official "
        "release's metadata, not a reason to drop the recording."
    )


def ninapro_letter_for(
    subject: int, exercise_field: int, restimulus_max: int, path: str = ""
) -> str:
    """Return 'B' or 'C', verified against the observed label range.

    ``subject`` must be the **authoritative** DB9 subject id (archive slot), not
    the value recorded inside the file.
    """
    key = (source_db_for_subject(subject), exercise_field)
    letter = NINAPRO_LETTER_BY_SOURCE_EXERCISE.get(key)
    if letter is None:
        raise MatLoadError(
            f"{path}: subject {subject} is from {source_db_for_subject(subject)}, "
            f"whose exercise {exercise_field} is not one of the B/C exercises "
            "DB9 ships"
        )
    expected = EXPECTED_MAX_LABEL[letter]
    if restimulus_max != expected:
        raise MatLoadError(
            f"{path}: subject {subject} (source "
            f"{source_db_for_subject(subject)}) exercise {exercise_field} maps to "
            f"Ninapro exercise {letter}, whose highest label should be {expected}, "
            f"but the file's restimulus max is {restimulus_max}. The file's own "
            "metadata and its labels disagree."
        )
    return letter


def ninapro_letter(rec: Db9Recording, subject: int | None = None) -> str:
    """``ninapro_letter_for`` bound to a recording.

    ``subject`` defaults to the value recorded inside the file, which is only
    correct for DB1-derived archives; callers handling DB2/DB5 subjects must
    pass the archive slot explicitly.
    """
    return ninapro_letter_for(
        subject if subject is not None else rec.subject,
        rec.exercise,
        int(rec.restimulus.max()),
        rec.path,
    )


def db9_exercise_index(rec: Db9Recording, subject: int | None = None) -> int:
    """1 for Ninapro B, 2 for Ninapro C -- DB9's own exercise numbering."""
    return {"B": 1, "C": 2}[ninapro_letter(rec, subject)]

