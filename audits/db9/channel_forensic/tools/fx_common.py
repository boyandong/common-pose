# =============================================================================
# Fx common  ---  ported from db9_channel_forensic_v2/scripts/fx_common.py
#
# Common Pose public repository. Frozen plan SHA-256:
#   4c618b562903d0d364d03bb8a997ef6b4140bd9e09d0f2475f1b008ad80c8793
#
# Driver order: segmentation -> forensic_core -> verdicts -> utility -> decision
#               -> final_validation.
# `verdicts` freezes TRUSTED_DB9_POSE_v1 and `utility` asserts against that frozen
# subset, so it must run after it.
#
# The Ninapro DB9 release is not redistributed with this repository. Paths are supplied
# through the environment; `fx_common` is the single place that reads them.
#
# Edits relative to the archived original: I/O plumbing only --- local absolute paths
# moved to environment variables, and the numeric filename prefixes dropped. No numeric
# logic, threshold, seed, verdict vocabulary or assertion count was changed.
# =============================================================================

"""Shared helpers for the S8 DB9 channel-forensic lane.

Read-only with respect to every other lane.  Nothing here trains or fits a classifier; the
only fitting is the analytical recovery of the published calibration transform, which is
deterministic least squares on two parameters at most.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sys

import numpy as np
import scipy.io as sio

# --------------------------------------------------------------------------- #
# Paths. Every one is supplied through the environment so this audit can run outside the
# machine it was authored on. The archived original held absolute local paths; they are
# replaced here and NOWHERE ELSE in this tool set.
#
#   COMMON_POSE_DB9_ROOT       root of the Ninapro DB9 release
#                              (default ./data/ninapro_db9)
#   COMMON_POSE_DB9_EXTRACTED  directory holding the `s_<n>_angles/` folders
#                              (default <ROOT>/extracted)
#   COMMON_POSE_DB9_RAW        directory holding the raw `s_<n>_angles.zip` archives
#                              (default <ROOT>/raw)
#   COMMON_POSE_DB9_OUT        where this audit writes artifacts/figures/logs
#                              (default the directory holding these scripts)
#
# POINT `COMMON_POSE_DB9_OUT` AT A SCRATCH DIRECTORY when re-running: the drivers
# overwrite the frozen artifacts published in this repository, including
# TRUSTED_DB9_POSE_v1.json.
# --------------------------------------------------------------------------- #

ROOT = os.environ.get("COMMON_POSE_DB9_ROOT", os.path.join(".", "data", "ninapro_db9"))
EXTRACTED = os.environ.get("COMMON_POSE_DB9_EXTRACTED", os.path.join(ROOT, "extracted"))
RAWZIP = os.environ.get("COMMON_POSE_DB9_RAW", os.path.join(ROOT, "raw"))

#: Where this driver set lives. The frozen plan is read from here, so it must sit beside
#: the scripts -- which is the case in this repository. This is a read-only location.
LANE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = LANE

#: Writable outputs. Defaults to the script directory; set COMMON_POSE_DB9_OUT to keep a
#: re-run away from the published artifacts.
_OUT = os.environ.get("COMMON_POSE_DB9_OUT", ".")
ART = os.path.join(_OUT, "artifacts")
FIGS = os.path.join(_OUT, "figures")
LOGS = os.path.join(_OUT, "logs")
DOCS = os.path.join(_OUT, "docs")

PLAN = os.path.join(LANE, "FORENSIC_PLAN.md")
PLAN_SHA = os.path.join(LANE, "PLAN_SHA256.txt")

OFFICIAL = "OFFICIAL"
OFFICIAL_CODE = "OFFICIAL-CODE"
LITERATURE = "LITERATURE"
EMPIRICAL = "EMPIRICAL"
INFERENCE = "INFERENCE"
UNRESOLVED = "UNRESOLVED"

#: released channel order, taken from the `order_of_angles` field of every .mat
ORDER22 = ("CMC1_f", "CMC1_a", "MCP1", "IP1", "MCP2_f", "MCP2_a", "PIP2", "MCP3_f", "PIP3",
           "MCP4_f", "MCP4_a", "PIP4", "CMC5", "MCP5_f", "MCP5_a", "PIP5", "DIP2", "DIP3",
           "DIP4", "DIP5", "WRIST_F", "WRIST_A")
IDX = {n: i for i, n in enumerate(ORDER22)}

#: official DB9 sign criteria (paper Table 6)
SIGN = {n: "flexion + / extension -" for n in
        ("DIP2", "DIP3", "DIP4", "DIP5", "PIP2", "PIP3", "PIP4", "PIP5", "IP1",
         "MCP1", "MCP2_f", "MCP3_f", "MCP4_f", "MCP5_f", "WRIST_F", "CMC5", "CMC1_f")}
SIGN.update({"MCP2_a": "fingers separated + / together -",
             "MCP4_a": "fingers separated + / together -",
             "MCP5_a": "fingers separated + / together -",
             "CMC1_a": "abduction + / adduction -",
             "WRIST_A": "radial deviation + / cubital deviation -"})

#: independent 2024 study (Robotics 13(6):82) flags
LITERATURE_FLAGGED = {"DIP3", "DIP4", "DIP5", "CMC5"}

#: Exercise B movement list, official (Ninapro movements figure)
EX_B = {1: "Thumb up",
        2: "Extension of index and middle, flexion of the others",
        3: "Flexion of ring and little finger, extension of the others",
        4: "Thumb opposing base of little finger",
        5: "Abduction of all fingers",
        6: "Fingers flexed together in fist",
        7: "Pointing index",
        8: "Adduction of extended fingers",
        9: "Wrist supination (axis: middle finger)",
        10: "Wrist pronation (axis: middle finger)",
        11: "Wrist supination (axis: little finger)  [holds the reference posture in its "
            "central part per the DB9 paper]",
        12: "Wrist pronation (axis: little finger)",
        13: "Wrist flexion", 14: "Wrist extension",
        15: "Wrist radial deviation", 16: "Wrist ulnar deviation",
        17: "Wrist extension with closed hand"}

#: published calibration constants, transcribed from the DB9 paper (Tables 2-5)
PUB = {
    "MCP1": 0.562, "MCP2_f": 0.91, "MCP3_f": 0.95, "MCP4_f": 0.97, "MCP5_f": 1.06,
    "IP1": 1.19, "PIP2": 0.91, "PIP3": 1.07, "PIP4": 1.57, "PIP5": 0.89,
    "DIP2": 1.08, "DIP3": 1.82, "DIP4": 2.08, "DIP5": 1.26,
    "CMC5": 0.285,
    "WRIST_F": ("quadratic", 0.008, -190.451),
    "WRIST_A": ("composite", -1.020, 0.467, 75.336),
    "CMC1_f": ("composite", 0.713, 0.623),
    "CMC1_a": ("composite", -0.321, 0.050),
    "MCP2_a": ("poly2", -0.503, -0.071, -0.004, 0.091, -0.010, 0.014),
    "MCP4_a": ("poly2", 0.229, -0.169, 0.006, 0.167, 0.007, -0.013),
    "MCP5_a": ("poly2", 0.214, -0.091, 0.004, 0.250, 0.005, -0.011),
}


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def plan_sha() -> str:
    return open(PLAN_SHA, encoding="utf-8").read().split()[0]


def write_json(p, o):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(o, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return sha256_file(p)


def write_text(p, t):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(t)
    return sha256_file(p)


def write_csv(p, header, rows):
    import csv
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        for r in rows:
            w.writerow(["" if v is None else v for v in r])
    return sha256_file(p)


def tee(name):
    os.makedirs(LOGS, exist_ok=True)
    p = os.path.join(LOGS, name + ".log")
    fh = open(p, "w", encoding="utf-8", newline="\n")

    class T:
        def write(self, s):
            fh.write(s)
            sys.__stdout__.write(s)

        def flush(self):
            fh.flush()
            sys.__stdout__.flush()

    sys.stdout = T()
    return p


def banner(t):
    print("=" * 78)
    print(t)
    print("=" * 78)


def wilson(k, n, z=1.959963984540054):
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


# --------------------------------------------------------------------- data
def all_files():
    return sorted(glob.glob(os.path.join(EXTRACTED, "s_*_angles", "*.mat")))


def ex_files(ex):
    return [f for f in all_files() if f"_{ex}_" in os.path.basename(f)]


def load(path):
    m = sio.loadmat(path, squeeze_me=True, struct_as_record=False)
    base = os.path.basename(path)
    # FINDING: the in-file `subject` field is SOURCE-DATABASE-LOCAL.  S68_E2_A1.mat (DB5
    # subject 68) reports subject == 1, colliding with S1_E2_A1.mat.  The filename prefix is
    # the only DB9-global subject identifier, so it is the primary key here.
    fname_subject = int(base.split("_")[0][1:])
    try:
        field_subject = int(np.asarray(m["subject"]).ravel()[0])
    except Exception:
        field_subject = None
    try:
        field_exercise = int(np.asarray(m["exercise"]).ravel()[0])
    except Exception:
        field_exercise = None
    d = {"path": path, "name": base,
         "glove": np.asarray(m["glove"], dtype=np.float64),
         "angles": np.asarray(m["angles"], dtype=np.float64),
         "restimulus": np.ravel(np.asarray(m["restimulus"])),
         "rerepetition": np.ravel(np.asarray(m["rerepetition"])),
         "stimulus": np.ravel(np.asarray(m["stimulus"])),
         "repetition": np.ravel(np.asarray(m["repetition"])),
         "order": [str(x) for x in np.ravel(m["order_of_angles"])],
         "subject": fname_subject, "subject_field": field_subject,
         "exercise": int(base.split("_")[1][1:]), "exercise_field": field_exercise}
    return d


def segments(d, key="restimulus", rep="rerepetition", exclude_rest=True):
    """Contiguous runs of (restimulus, rerepetition).  Returns list of dicts."""
    ks, rs = d[key], d[rep]
    n = len(ks)
    assert n == len(rs)
    out, start = [], 0
    for i in range(1, n + 1):
        if i == n or ks[i] != ks[start] or rs[i] != rs[start]:
            st, rp = int(ks[start]), int(rs[start])
            if not (exclude_rest and (st == 0 or rp == 0)):
                out.append({"stim": st, "rep": rp, "start": start, "end": i - 1,
                            "n": i - start})
            start = i
    return out


def core(seg, frac=0.6):
    """Central `frac` of a segment - the plan's rule for a stable window."""
    n = seg["n"]
    k = max(1, int(round(n * frac)))
    a = seg["start"] + (n - k) // 2
    return a, a + k
