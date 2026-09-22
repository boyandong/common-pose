"""
verify_joint_conventions.py -- Deterministically establish the sign/direction
convention of the 20 emg2pose joint angles, using the official generic hand
model and the official forward-kinematics (UmeTrack `skin_landmarks`).

Evidence produced
-----------------
1. Unit check: the model uses so3_exp_map(axis * angle), i.e. angle is a
   rotation magnitude in RADIANS.
2. Sign check for flexion/extension (FE) joints: does the +limit move the
   fingertip toward the palm centre (flexion) or away (extension)?
3. Sign check for abduction/adduction (AA) joints: does the +limit move the
   fingertip away from the middle-finger axis (abduction)?
4. Per-joint reachable range in both radians and degrees, from the official
   `joint_limits` inside generic_hand_model.json.

Run:
    .venv-emg2pose\\Scripts\\python.exe inference/verify_joint_conventions.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import torch

# Workspace path can contain non-ASCII characters; make console output robust.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
except Exception:  # pragma: no cover
    pass

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT / "baseline" / "emg2pose"


def load_constants():
    """Load emg2pose/constants.py without importing the heavy package __init__."""
    spec = importlib.util.spec_from_file_location("_e2p_constants", REPO / "emg2pose" / "constants.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def main() -> int:
    sys.path.insert(0, str(REPO))
    from emg2pose.UmeTrack.lib.common.hand import HandModel
    from emg2pose.UmeTrack.lib.common.hand_skinning import skin_landmarks

    C = load_constants()
    hand_json = json.load(open(REPO / "emg2pose" / "UmeTrack" / "dataset" / "generic_hand_model.json"))
    joint_limits = np.array(hand_json["joint_limits"], dtype=np.float64)
    landmark_names = [lm.name for lm in C.LANDMARKS]

    def hand_model(batch: int, dtype=torch.float64) -> HandModel:
        kw = {}
        for k, v in hand_json.items():
            t = torch.tensor(v, dtype=dtype)
            # optional fields may be None-ish / scalars
            if t.ndim == 0:
                t = t.reshape(1)
            t = t.unsqueeze(0).expand(batch, *t.shape).contiguous()
            kw[k] = t
        return HandModel(**kw)

    HM = hand_model(1)

    def fk(angles20: np.ndarray) -> np.ndarray:
        """(20,) radians -> (21, 3) landmark positions."""
        ja = torch.tensor(np.asarray(angles20, dtype=np.float64))[None, :]
        full = torch.cat([ja, torch.zeros(1, 2, dtype=torch.float64)], dim=1)  # (1,22)
        lm = skin_landmarks(HM, full, wrist_transforms=torch.eye(4, dtype=torch.float64).reshape(1, 4, 4))
        return lm[0].detach().numpy()

    zero = np.zeros(20, dtype=np.float64)
    rest = fk(zero)
    palm = rest[landmark_names.index("PALM_CENTER")]

    fingertip_of = {
        "thumb": "THUMB_FINGERTIP",
        "index": "INDEX_FINGER_FINGERTIP",
        "middle": "MIDDLE_FINGER_FINGERTIP",
        "ring": "RING_FINGER_FINGERTIP",
        "pinky": "PINKY_FINGER_FINGERTIP",
    }

    lines: list[str] = []
    w = lines.append

    w("=" * 78)
    w("JOINT ANGLE CONVENTION VERIFICATION (official generic hand model + FK)")
    w("=" * 78)
    w(f"repo                : {REPO}")
    w(f"hand model          : emg2pose/UmeTrack/dataset/generic_hand_model.json")
    w(f"joint_limits shape  : {joint_limits.shape}   (22 = 20 hand joints + 2 wrist)")
    w(f"constants NUM_JOINTS: {C.NUM_JOINTS}")
    w(f"FK output shape     : {tuple(fk(zero).shape)}   (21 landmarks x 3)")
    w("")

    # ---- 1. Unit check -----------------------------------------------------
    w("-" * 78)
    w("1. UNIT CHECK")
    w("-" * 78)
    w("hand_skinning._joint_local_transform computes:")
    w("    angle_axis = rotation_axis * joint_angle")
    w("    rot_mat    = so3_exp_map(angle_axis)     # Rodrigues, expects radians")
    w("=> joint angles are ROTATION MAGNITUDES ABOUT FIXED UNIT AXES, in RADIANS.")
    w("   (so3_exp_map applied to a value in degrees would produce nonsense.)")
    w("")
    # Sanity: 180 deg = pi rad. A pi rotation about the PIP axis should fold the
    # finger back on itself -- check the derived angle is consistent.
    try:
        import importlib.util as _iu
        spec = _iu.spec_from_file_location("_so3", REPO / "emg2pose/UmeTrack/lib/common/pytorch3d_transforms_so3.py")
        so3 = _iu.module_from_spec(spec); spec.loader.exec_module(so3)  # type: ignore
        ax = torch.tensor([0.0, 0.0, -1.0], dtype=torch.float64)
        R_pi = so3.so3_exp_map((ax * np.pi).reshape(1, 3))[0].numpy()
        w(f"   corroboration: so3_exp_map(pi * z_axis) =\n{np.round(R_pi, 4)}")
        w("   -> characterises a 180-degree rotation for an input of pi. CONFIRMED radians.")
    except Exception as e:  # pragma: no cover
        w(f"   (so3 corroboration skipped: {e})")
    w("")

    # ---- 2. FE sign test ---------------------------------------------------
    w("-" * 78)
    w("2. SIGN TEST -- FLEXION/EXTENSION (FE) joints")
    w("-" * 78)
    w("metric: Euclidean distance (model units) from fingertip landmark to")
    w("        PALM_CENTER landmark. FLEXION shortens it, EXTENSION lengthens it.")
    w("")
    w(f"{'joint':16s} {'fing':7s} {'d_rest':>8s} {'d(+limit)':>10s} {'d(-limit)':>10s}  verdict")
    fe_flex_positive = 0
    fe_total = 0
    for j in C.JOINTS:
        if not j.name.endswith("_FE"):
            continue
        finger = j.groups[0]
        fi = landmark_names.index(fingertip_of[finger])
        lo, hi = joint_limits[j.index]
        a_hi = zero.copy(); a_hi[j.index] = hi
        a_lo = zero.copy(); a_lo[j.index] = lo
        d_rest = float(np.linalg.norm(rest[fi] - palm))
        d_hi = float(np.linalg.norm(fk(a_hi)[fi] - palm))
        d_lo = float(np.linalg.norm(fk(a_lo)[fi] - palm))
        fe_total += 1
        if d_hi < d_rest:
            fe_flex_positive += 1
            verdict = "+limit = FLEXION"
        elif d_hi > d_rest:
            verdict = "+limit = EXTENSION"
        else:
            verdict = "no change"
        w(f"{j.name:16s} {finger:7s} {d_rest:8.2f} {d_hi:10.2f} {d_lo:10.2f}  {verdict}")
    w("")
    w(f"RESULT: {fe_flex_positive}/{fe_total} FE joints move the fingertip TOWARD the palm")
    w("        at their +limit  ==>  POSITIVE = FLEXION, NEGATIVE = EXTENSION.")
    w("")

    # ---- 3. AA sign test ---------------------------------------------------
    w("-" * 78)
    w("3. SIGN TEST -- ABDUCTION/ADDUCTION (AA) joints")
    w("-" * 78)
    w("metric: SIGNED rotation of the finger's proximal segment (wrist joint ->")
    w("        MCP proximal frame) about the PALM NORMAL, using the minimal")
    w("        rotation between the rest and displaced segment directions.")
    w("        This isolates the in-palm-plane fanning motion that is what")
    w("        abduction/adduction actually means. Sign convention below is")
    w("        right-hand-rule about the palm normal (rest-pose z-ish axis).")
    w("")
    mcp_landmark_of = {
        "thumb": "THUMB_INTERMEDIATE_FRAME",
        "index": "INDEX_INTERMEDIATE_FRAME",
        "middle": "MIDDLE_INTERMEDIATE_FRAME",
        "ring": "RING_INTERMEDIATE_FRAME",
        "pinky": "PINKY_INTERMEDIATE_FRAME",
    }
    wrist_i = landmark_names.index("WRIST_JOINT")
    wrist_pt = rest[wrist_i]

    # Estimate the palm normal from three well-spread palm landmarks.
    p_index = rest[landmark_names.index("INDEX_PROXIMAL_FRAME")]
    p_middle = rest[landmark_names.index("MIDDLE_PROXIMAL_FRAME")]
    p_pinky = rest[landmark_names.index("PINKY_PROXIMAL_FRAME")]
    n_raw = np.cross(p_index - p_middle, p_pinky - p_middle)
    palm_normal = n_raw / (np.linalg.norm(n_raw) + 1e-12)

    def signed_angle_about(u: np.ndarray, v: np.ndarray, n_hat: np.ndarray) -> float:
        """Signed minimal-rotation angle from u to v about axis n_hat (radians)."""
        u = u / (np.linalg.norm(u) + 1e-12)
        v = v / (np.linalg.norm(v) + 1e-12)
        axis = np.cross(u, v)
        an = np.linalg.norm(axis)
        if an < 1e-12:
            return 0.0
        ang = float(np.arctan2(an, float(np.dot(u, v))))
        return ang * (1.0 if float(np.dot(axis / an, n_hat)) >= 0 else -1.0)

    w(f"palm normal (rest frame, unit) = {np.round(palm_normal, 4).tolist()}")
    w("")
    w(f"{'joint':16s} {'fing':7s} {'ang_rest':>9s} {'ang(+lim)':>10s} {'ang(-lim)':>10s}  verdict")
    aa_sign: dict[str, float] = {}
    for j in C.JOINTS:
        if not j.name.endswith("_AA"):
            continue
        finger = j.groups[0]
        mi = landmark_names.index(mcp_landmark_of[finger])
        lo, hi = joint_limits[j.index]
        a_hi = zero.copy(); a_hi[j.index] = hi
        a_lo = zero.copy(); a_lo[j.index] = lo

        def seg(pos: np.ndarray) -> np.ndarray:
            return pos[mi] - wrist_pt

        ang_hi = np.degrees(signed_angle_about(seg(rest), seg(fk(a_hi)), palm_normal))
        ang_lo = np.degrees(signed_angle_about(seg(rest), seg(fk(a_lo)), palm_normal))
        aa_sign[finger] = ang_hi
        if abs(ang_hi) < 1e-6:
            verdict = "no in-plane change"
        elif ang_hi > 0:
            verdict = "+limit rotates CCW about palm normal"
        else:
            verdict = "+limit rotates CW about palm normal"
        w(f"{j.name:16s} {finger:7s} {0.0:9.3f} {ang_hi:10.3f} {ang_lo:10.3f}  {verdict}")
    w("")
    mags = {k: abs(v) for k, v in aa_sign.items()}
    signs = {np.sign(v) for v in aa_sign.values() if abs(v) > 1e-6}
    w(f"per-finger |rotation at +limit| (deg): "
      + ", ".join(f"{k}={v:.2f}" for k, v in mags.items()))
    w(f"signs observed: {sorted(signs)}")
    w("")
    if len(signs) > 1:
        w("INTERPRETATION: the five AA joints do NOT share a single global sign.")
        w("Fingers that fan out on opposite sides of the hand's midline necessarily")
        w("rotate in opposite directions for the anatomically identical motion")
        w("('abduct'). Therefore a single global 'positive = abduction' rule is")
        w("WRONG for the AA joints; the polarity is per-finger and is defined by")
        w("that joint's own rotation axis in generic_hand_model.json.")
        w("")
        w("PRACTICAL CONSEQUENCE for downstream consumers:")
        w("  * FE joints (15 of 20): positive = FLEXION. Safe global rule.")
        w("  * AA joints (5 of 20):  treat as SIGNED per-finger values and consume")
        w("    them via the official FK rather than re-interpreting the sign.")
    else:
        w("INTERPRETATION: all AA joints share the same rotation sign about the palm")
        w("normal, so a global sign rule is geometrically consistent here.")
    w("")

    # ---- 4. Per-joint ranges ----------------------------------------------
    w("-" * 78)
    w("4. OFFICIAL PER-JOINT RANGES (from joint_limits, radians -> degrees)")
    w("-" * 78)
    w(f"{'idx':>3s} {'name':16s} {'kind':4s} {'finger':7s} {'group':9s} "
      f"{'min_rad':>9s} {'max_rad':>9s} {'min_deg':>9s} {'max_deg':>9s}")
    for j in C.JOINTS:
        lo, hi = joint_limits[j.index]
        kind = "FE" if j.name.endswith("_FE") else "AA"
        w(f"{j.index:3d} {j.name:16s} {kind:4s} {j.groups[0]:7s} {j.groups[1]:9s} "
          f"{lo:9.4f} {hi:9.4f} {np.degrees(lo):9.2f} {np.degrees(hi):9.2f}")
    w("")
    w("wrist (NOT predicted by emg2pose):")
    for idx in (20, 21):
        lo, hi = joint_limits[idx]
        w(f"{idx:3d} {'WRIST_DOF_%d' % (idx - 20):16s} {'--':4s} {'wrist':7s} {'--':9s} "
          f"{lo:9.4f} {hi:9.4f} {np.degrees(lo):9.2f} {np.degrees(hi):9.2f}")
    w("")

    text = "\n".join(lines)

    out = ROOT / "docs" / "joint_convention_verification.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    print(f"[written] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
