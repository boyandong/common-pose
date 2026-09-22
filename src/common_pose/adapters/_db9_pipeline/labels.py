"""Official Ninapro movement vocabulary for the exercises that make up DB9.

PROVENANCE / EVIDENCE LEVEL
---------------------------
Everything in this module is transcribed from **official Ninapro material**.
Nothing here is guessed, and nothing is inferred from a third-party mirror.

Primary source (movement names, 1:1):
  Ninapro official figure "Hand movements. Performed exercises: A, B, C, D."
    https://ninapro.hevs.ch/figures/SData_Movements.png
    sha256 f240dfcf247516a632308fc19b62ff0bc08fc87f50bf0cb4d7055b2a74cbc45b
    Content-Length 2,270,669 B, Last-Modified Fri, 28 Jul 2023 15:21:52 GMT
  Downloaded and read directly (see docs/ninapro_figure_reading.md).

Supporting source (exercise composition and counts):
  Ninapro DB9 instruction page, https://ninapro.hevs.ch/instructions/DB9.html
    "Exercise 1: Basic movements of the fingers.
     Exercise 2: Grasping and functional movements."
  Jarque-Bou, Atzori & Muller, "A large calibrated database of hand movements
  and grasps kinematics", Scientific Data 7:12 (2020),
  doi:10.1038/s41597-019-0349-2 (PMC6952409):
    "The exercises included in the kinematic dataset consist of 40 hand
     movements plus rest and correspond to exercise B and C described by
     Atzori et al. Exercise B consists of 8 isometric and isotonic hand
     configurations and 9 basic movements of the wrist; Exercise C consists of
     23 grasping and functional movements."
  Atzori et al., Scientific Data 1:140053 (2014), doi:10.1038/sdata.2014.53
  (PMC4421935), Table 1 -- fixes the exercise lettering used above:
    DB1: Exercise 1 = A (12), Exercise 2 = B (17), Exercise 3 = C (23)
    DB2: Exercise 1 = B (17), Exercise 2 = C (23), Exercise 3 = D (9)
    DB5: Exercise 1 = B (17), Exercise 2 = C (23)

Therefore **DB9 = Ninapro Exercise B (17 movements) + Exercise C (23
movements) = 40 movements**, plus the rest position. 8 + 9 = 17 and 23 are
exactly the counts stated in the 2020 paper, so the composition is
self-consistent rather than merely asserted.

WHAT THIS MEANS FOR THE SCIENCE (read before using these labels)
----------------------------------------------------------------
The 40 movements are NOT 40 independent hand postures, and they are not all
recoverable from finger kinematics.  They split into three qualitatively
different families, which is precisely the distinction the research question
asks us to make explicit:

* ``ISOMETRIC_ISOTONIC_CONFIGS`` (Exercise B 1-8) - genuine static hand
  configurations. These are *shapes*, so they are in principle identifiable
  from joint configuration alone.
* ``WRIST`` (Exercise B 13-17) - wrist flexion/extension/deviation. The
  CyberGlove-II carries its own ``WRIST_F`` and ``WRIST_A`` channels, so this is
  observable in DB9 -- but emg2pose never records the wrist, so it is invisible
  to the emg2pose model.
* ``FOREARM_ROT`` (Exercise B 9-12) - wrist supination/pronation is rotation
  about the *forearm* axis, not a hand-joint degree of freedom. No CyberGlove
  channel measures it; only the separate inclinometer could hint at it, and
  DB1-derived DB9 files ship no inclinometer at all. A model given only the 22
  angles should be *expected* to fail here, and that failure is a finding.
* ``GRASP`` (Exercise C 1-23) - grasps of physical objects. Some are distinct
  hand configurations (lateral grasp, tip pinch, tripod), but several differ
  mainly in the *object* being held (e.g. "large diameter grasp" vs "small
  diameter grasp", "power sphere" vs "precision sphere"). Those pairs can
  converge to near-identical joint configurations and may be inseparable from
  kinematics alone -- again a finding to measure, not to engineer away.

Consequently ``identifiability_family`` is attached to every movement so that
per-class results can be aggregated by family instead of only reported as a
flat 40-way accuracy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# --------------------------------------------------------------------------
# Provenance constants
# --------------------------------------------------------------------------
FIGURE_URL = "https://ninapro.hevs.ch/figures/SData_Movements.png"
FIGURE_SHA256 = "f240dfcf247516a632308fc19b62ff0bc08fc87f50bf0cb4d7055b2a74cbc45b"
DB9_PAGE = "https://ninapro.hevs.ch/instructions/DB9.html"
PAPER_DB9 = "doi:10.1038/s41597-019-0349-2"
PAPER_NINAPRO = "doi:10.1038/sdata.2014.53"

REST_LABEL = 0
REST_NAME = "Rest"

#: DB9 exercises are 1-indexed exactly as the archives name them.
DB9_EXERCISE_TO_NINAPRO = {
    1: "B",  # 17 movements, 8 isometric/isotonic configs + 9 wrist movements
    2: "C",  # 23 grasping and functional movements
}


class Family(str, Enum):
    """Which kind of quantity the movement actually is.

    The families are ordered by how much of the movement a *hand-kinematic*
    observation can in principle carry, which is exactly the axis the research
    question asks about.
    """

    REST = "rest"
    #: Static hand shape -> in principle recoverable from finger joint angles.
    POSTURE = "posture"
    #: Wrist motion. The CyberGlove-II's own ``WRIST_F`` / ``WRIST_A`` channels
    #: carry it, so it is observable in DB9 -- but emg2pose never records the
    #: wrist, so it is NOT observable on the emg2pose side.
    WRIST = "wrist"
    #: Forearm pronation/supination. This is rotation about the forearm axis,
    #: not a hand-joint degree of freedom: no CyberGlove channel measures it
    #: (only the separate inclinometer could hint at it, and DB1-derived files
    #: ship no inclinometer at all). Unobservable from the 22 angles.
    FOREARM_ROT = "forearm_rot"
    #: Grasp of a physical object -> partly object/contact/force dependent.
    GRASP = "grasp"

    @property
    def visible_in_finger_angles(self) -> bool:
        """Whether the 22 hand-kinematic channels can carry this movement."""
        return self in (Family.POSTURE, Family.WRIST, Family.GRASP)


@dataclass(frozen=True)
class Movement:
    exercise: int          # DB9's own exercise numbering: 1 = Ninapro B, 2 = C
    label: int             # value expected in `restimulus` for this exercise
    name: str              # official name from the Ninapro movement figure
    family: Family
    #: True when the movement is chiefly distinguished by the object held
    #: rather than by the hand configuration itself.
    object_dependent: bool = False
    notes: str = ""


# --------------------------------------------------------------------------
# Ninapro Exercise B (DB9 exercise 1) -- 17 movements
#   labels 1-8  : 8 isometric and isotonic hand configurations
#   labels 9-17 : 9 basic movements of the wrist
# --------------------------------------------------------------------------
EXERCISE_B: tuple[Movement, ...] = (
    Movement(1, 1, "Thumb up", Family.POSTURE),
    Movement(1, 2, "Extension of index and middle, flexion of the others", Family.POSTURE),
    Movement(1, 3, "Flexion of ring and little finger, extension of the others", Family.POSTURE),
    Movement(1, 4, "Thumb opposing base of little finger", Family.POSTURE),
    Movement(1, 5, "Abduction of all fingers", Family.POSTURE),
    Movement(1, 6, "Fingers flexed together in fist", Family.POSTURE),
    Movement(1, 7, "Pointing index", Family.POSTURE),
    Movement(1, 8, "Adduction of extended fingers", Family.POSTURE),
    Movement(1, 9, "Wrist supination (axis: middle finger)", Family.FOREARM_ROT,
             notes="Forearm rotation: no CyberGlove channel measures it."),
    Movement(1, 10, "Wrist pronation (axis: middle finger)", Family.FOREARM_ROT,
             notes="Forearm rotation: no CyberGlove channel measures it."),
    Movement(1, 11, "Wrist supination (axis: little finger)", Family.FOREARM_ROT,
             notes="Forearm rotation: no CyberGlove channel measures it."),
    Movement(1, 12, "Wrist pronation (axis: little finger)", Family.FOREARM_ROT,
             notes="Forearm rotation: no CyberGlove channel measures it."),
    Movement(1, 13, "Wrist flexion", Family.WRIST,
             notes="Carried by the glove's own WRIST_F channel."),
    Movement(1, 14, "Wrist extension", Family.WRIST,
             notes="Carried by the glove's own WRIST_F channel."),
    Movement(1, 15, "Wrist radial deviation", Family.WRIST,
             notes="Carried by the glove's own WRIST_A channel."),
    Movement(1, 16, "Wrist ulnar deviation", Family.WRIST,
             notes="Carried by the glove's own WRIST_A channel."),
    Movement(1, 17, "Wrist extension with closed hand", Family.WRIST,
             notes="Mixed: finger posture AND wrist extension."),
)

# --------------------------------------------------------------------------
# Ninapro Exercise C (DB9 exercise 2) -- 23 grasping / functional movements
# --------------------------------------------------------------------------
EXERCISE_C: tuple[Movement, ...] = (
    Movement(2, 1, "Large diameter grasp", Family.GRASP, object_dependent=True,
             notes="Differs from 'Small diameter grasp' mainly by object size."),
    Movement(2, 2, "Small diameter grasp (power grip)", Family.GRASP, object_dependent=True,
             notes="Differs from 'Large diameter grasp' mainly by object size."),
    Movement(2, 3, "Fixed hook grasp", Family.GRASP),
    Movement(2, 4, "Index finger extension", Family.GRASP),
    Movement(2, 5, "Medium wrap", Family.GRASP, object_dependent=True),
    Movement(2, 6, "Ring grasp", Family.GRASP),
    Movement(2, 7, "Prismatic four fingers grasp", Family.GRASP),
    Movement(2, 8, "Stick grasp", Family.GRASP),
    Movement(2, 9, "Writing tripod grasp", Family.GRASP),
    Movement(2, 10, "Power sphere grasp", Family.GRASP, object_dependent=True,
             notes="Sphere grasps differ largely by object size / contact area."),
    Movement(2, 11, "Three finger sphere grasp", Family.GRASP, object_dependent=True),
    Movement(2, 12, "Precision sphere grasp", Family.GRASP, object_dependent=True),
    Movement(2, 13, "Tripod grasp", Family.GRASP),
    Movement(2, 14, "Prismatic pinch grasp", Family.GRASP),
    Movement(2, 15, "Tip pinch grasp", Family.GRASP),
    Movement(2, 16, "Quadpod grasp", Family.GRASP),
    Movement(2, 17, "Lateral grasp", Family.GRASP),
    Movement(2, 18, "Parallel extension grasp", Family.GRASP),
    Movement(2, 19, "Extension type grasp", Family.GRASP),
    Movement(2, 20, "Power disk grasp", Family.GRASP, object_dependent=True),
    Movement(2, 21, "Open a bottle with a tripod grasp", Family.GRASP, object_dependent=True),
    Movement(2, 22, "Turn a screw (grasp the screwdriver with a stick grasp)",
             Family.GRASP, object_dependent=True),
    Movement(2, 23, "Cut something (grasp the knife with an index finger extension grasp)",
             Family.GRASP, object_dependent=True),
)

# --------------------------------------------------------------------------
# Exercises present in DB1/DB2/DB5 but NOT included in DB9. Recorded so that
# nobody accidentally reads a DB1/DB2/DB5 file through a DB9 label table.
# --------------------------------------------------------------------------
EXERCISE_A_DB1_ONLY: tuple[str, ...] = (
    "Index flexion", "Index extension", "Middle flexion", "Middle extension",
    "Ring flexion", "Ring extension", "Little finger flexion",
    "Little finger extension", "Thumb adduction", "Thumb abduction",
    "Thumb flexion", "Thumb extension",
)
EXERCISE_D_DB2_ONLY: tuple[str, ...] = (
    "Flexion of the little finger", "Flexion of the ring finger",
    "Flexion of the middle finger", "Flexion of the index finger",
    "Abduction of the thumb", "Flexion of the thumb",
    "Flexion of index and little finger", "Flexion of ring and middle finger",
    "Flexion of index finger and thumb",
)

MOVEMENTS: dict[int, tuple[Movement, ...]] = {1: EXERCISE_B, 2: EXERCISE_C}


def movements_for(exercise: int) -> tuple[Movement, ...]:
    if exercise not in MOVEMENTS:
        raise KeyError(
            f"DB9 exercise {exercise} is not part of this dataset "
            f"(expected one of {sorted(MOVEMENTS)} = Ninapro B and C)"
        )
    return MOVEMENTS[exercise]


def movement_name(exercise: int, label: int) -> str:
    """Official name for a ``restimulus`` value, or a clearly-marked unknown."""
    if label == REST_LABEL:
        return REST_NAME
    for m in movements_for(exercise):
        if m.label == label:
            return m.name
    # Never silently invent a name: an unexpected label is a data-integrity
    # signal that must surface, not be smoothed over.
    return f"UNKNOWN_LABEL_{label}"


def family_of(exercise: int, label: int) -> Family:
    if label == REST_LABEL:
        return Family.REST
    for m in movements_for(exercise):
        if m.label == label:
            return m.family
    return Family.REST if label == REST_LABEL else Family.GRASP


def is_object_dependent(exercise: int, label: int) -> bool:
    for m in movements_for(exercise):
        if m.label == label:
            return m.object_dependent
    return False


def table(exercise: int) -> list[dict[str, object]]:
    """Flat records, convenient for pandas / csv emission."""
    return [
        {
            "exercise": m.exercise,
            "label": m.label,
            "name": m.name,
            "family": m.family.value,
            "object_dependent": m.object_dependent,
            "notes": m.notes,
        }
        for m in movements_for(exercise)
    ]


if __name__ == "__main__":  # pragma: no cover - tiny self-check / CLI dump
    for ex, movs in sorted(MOVEMENTS.items()):
        letters = DB9_EXERCISE_TO_NINAPRO[ex]
        print(f"DB9 exercise {ex} (Ninapro exercise {letters}): {len(movs)} movements")
        for m in movs:
            flag = " [object-dependent]" if m.object_dependent else ""
            print(f"  {m.label:2d}  {m.family.value:8s} {m.name}{flag}")
        print()
    n_post = sum(1 for e in MOVEMENTS for m in MOVEMENTS[e] if m.family is Family.POSTURE)
    n_wrist = sum(1 for e in MOVEMENTS for m in MOVEMENTS[e] if m.family is Family.WRIST)
    n_rot = sum(1 for e in MOVEMENTS for m in MOVEMENTS[e] if m.family is Family.FOREARM_ROT)
    n_grasp = sum(1 for e in MOVEMENTS for m in MOVEMENTS[e] if m.family is Family.GRASP)
    n_obj = sum(1 for e in MOVEMENTS for m in MOVEMENTS[e] if m.object_dependent)
    total = sum(len(v) for v in MOVEMENTS.values())
    print(
        f"total={total} (posture={n_post}, wrist={n_wrist}, "
        f"forearm_rot={n_rot}, grasp={n_grasp}; object-dependent={n_obj})"
    )
    assert total == 40, "DB9 must contain exactly 40 movements"
    assert (n_post, n_wrist, n_rot, n_grasp) == (8, 5, 4, 23)
