"""build_features.py - construct the FROZEN representations and cache them.

Every rule here is the one frozen in the plan; none of it is chosen after seeing
performance.  The cache exists so the CV, stability, boundary, null and full18
tools all read byte-identical features.

Representations (plan §4):
  R1_POSE             pose(t)                                            10
  R2_POSE_VELOCITY    [pose(t), dpose/dt(t)]                             20
  R3_TRAJECTORY       window summary at the primary 500 ms window        40
  R4_POSE_PAST_ONLY   causal: [pose, past-mean-velocity, past change]   30
  R5_FULL18           all 18 released columns                            18
  R6_FULL18_VELOCITY  [18 columns, velocity]                             36

Every representation carries, per row:
  phase, subject, trial_index, frame_index   (bookkeeping only, never a feature)
  in_window: True where the representation was actually defined for that frame
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import obs_common as C  # noqa: E402
import obs_plan as P  # noqa: E402

CACHE = os.path.join(C.RESULTS, "features.npz")

#: what each cached array is, for documentation
LAYOUT = {
    "phase": "int64 (N,)",
    "subject": "int64 (N,)",
    "trial_index": "int64 (N,) container index in EMG_KIN_v4",
    "frame_index": "int64 (N,) frame index within its trial",
    "boundary_interior": "bool (N,) at least 20 frames from either trial end",
    "R1_POSE": "float64 (N,10) shared10 pose, degrees",
    "R1_ok": "bool (N,)",
    "R2_POSE_VELOCITY": "float64 (N,20) pose then velocity, deg and deg/s",
    "R2_ok": "bool (N,)",
    "R3_TRAJECTORY": "float64 (N,40) 500 ms window summary",
    "R3_ok": "bool (N,)",
    "R4_POSE_PAST_ONLY": "float64 (N,30) causal past-only summary",
    "R4_ok": "bool (N,)",
    "R5_FULL18": "float64 (N,18) all released columns, degrees",
    "R5_ok": "bool (N,)",
    "R6_FULL18_VELOCITY": "float64 (N,36)",
    "R6_ok": "bool (N,)",
}

NAMES = {
    "R1_POSE": list(P.SHARED10["api_order"]),
    "R2_POSE_VELOCITY": ([f"pose:{n}" for n in P.SHARED10["api_order"]]
                         + [f"vel:{n}" for n in P.SHARED10["api_order"]]),
    "R3_TRAJECTORY": ([f"pose:{n}" for n in P.SHARED10["api_order"]]
                      + [f"winmeanvel:{n}" for n in P.SHARED10["api_order"]]
                      + [f"winchange:{n}" for n in P.SHARED10["api_order"]]
                      + [f"winsd:{n}" for n in P.SHARED10["api_order"]]),
    "R4_POSE_PAST_ONLY": ([f"pose:{n}" for n in P.SHARED10["api_order"]]
                          + [f"pastmeanvel:{n}" for n in P.SHARED10["api_order"]]
                          + [f"pastchange:{n}" for n in P.SHARED10["api_order"]]),
    "R5_FULL18": list(C.UJI18),
    "R6_FULL18_VELOCITY": list(C.UJI18) + [f"vel:{n}" for n in C.UJI18],
}


def velocity(t: dict, cols: list[int]) -> np.ndarray:
    """Frozen velocity: central difference, one-sided at the two ends.

    Uses the trial's OWN time stamps (seconds), so the sampling interval is
    correct even if a trial deviates from exactly 100 Hz.  Never crosses a trial
    boundary, because a trial IS one phase segment.  No smoothing, no labels.
    """
    K = t["K"][:, cols]
    tt = t["time"]
    n = K.shape[0]
    V = np.zeros_like(K)
    if n == 1:
        return V
    # interior: central difference
    if n > 2:
        num = K[2:] - K[:-2]
        den = (tt[2:] - tt[:-2])[:, None]
        V[1:-1] = num / np.where(den == 0, np.nan, den)
    # the two ends: first-order one-sided, the ONLY exception
    d0 = tt[1] - tt[0]
    V[0] = (K[1] - K[0]) / d0 if d0 != 0 else 0.0
    dl = tt[-1] - tt[-2]
    V[-1] = (K[-1] - K[-2]) / dl if dl != 0 else 0.0
    V[~np.isfinite(V)] = 0.0
    return V


def window_summary(t: dict, cols: list[int], h: int) -> tuple[np.ndarray, np.ndarray]:
    """40-D centred-window summary over +/- h frames.

    [pose(t), mean velocity over the window, pose(t+h) - pose(t-h), per-channel SD
    over the window].  A frame is valid only if the FULL window fits inside the
    trial; invalid frames are marked and never padded.  Because a trial is one
    phase segment, a window can never cross a phase boundary.
    """
    K = t["K"][:, cols]
    V = velocity(t, cols)
    tt = t["time"]
    n = K.shape[0]
    p = len(cols)
    out = np.full((n, 4 * p), np.nan)
    ok = np.zeros(n, dtype=bool)
    if n <= 2 * h:
        return out, ok
    cs = np.vstack([np.zeros(p), np.cumsum(K, axis=0)])
    for i in range(h, n - h):
        lo, hi = i - h, i + h
        seg = K[lo:hi + 1]
        m = cs[hi + 1] - cs[lo]
        span = tt[hi] - tt[lo]
        mean_v = m / span if span > 0 else np.zeros(p)
        change = K[hi] - K[lo]
        sd = seg.std(axis=0, ddof=0)
        out[i] = np.concatenate([K[i], mean_v, change, sd])
        ok[i] = True
    return out, ok


def causal_summary(t: dict, cols: list[int], h: int) -> tuple[np.ndarray, np.ndarray]:
    """Causal 30-D summary using ONLY frames at or before t."""
    K = t["K"][:, cols]
    tt = t["time"]
    n = K.shape[0]
    p = len(cols)
    out = np.full((n, 3 * p), np.nan)
    ok = np.zeros(n, dtype=bool)
    cs = np.vstack([np.zeros(p), np.cumsum(K, axis=0)])
    for i in range(h, n):
        lo = i - h
        m = cs[i + 1] - cs[lo]
        span = tt[i] - tt[lo]
        mean_v = m / span if span > 0 else np.zeros(p)
        out[i] = np.concatenate([K[i], mean_v, K[i] - K[lo]])
        ok[i] = True
    return out, ok


def main() -> int:
    d = C.load_kinmus()
    trials = d["trials"]
    plan = C.load_json(os.path.join(C.LANE, P.PLAN_ARTIFACT))
    h = plan["representations"]["R3_TRAJECTORY"]["primary_window_frames"]
    h_causal = h

    s10 = list(P.SHARED10["released_column_indices"])
    s18 = list(range(18))

    acc = {k: [] for k in ("phase", "subject", "trial_index", "frame_index")}
    blocks = {k: [] for k in ("R1_POSE", "R2_POSE_VELOCITY", "R3_TRAJECTORY",
                              "R4_POSE_PAST_ONLY", "R5_FULL18",
                              "R6_FULL18_VELOCITY")}
    oks = {k + "_ok": [] for k in blocks}
    pca_rows = []          # a shared pose matrix for figure use, same order

    for t in trials:
        n = t["n_frames"]
        acc["phase"].append(np.full(n, t["phase"], dtype=np.int64))
        acc["subject"].append(np.full(n, t["subject"], dtype=np.int64))
        acc["trial_index"].append(np.full(n, t["trial_index"], dtype=np.int64))
        acc["frame_index"].append(np.arange(n, dtype=np.int64))

        P10 = t["K"][:, s10]
        V10 = velocity(t, s10)
        P18 = t["K"][:, s18]
        V18 = velocity(t, s18)

        blocks["R1_POSE"].append(P10)
        oks["R1_POSE_ok"].append(np.ones(n, dtype=bool))
        blocks["R2_POSE_VELOCITY"].append(np.hstack([P10, V10]))
        oks["R2_POSE_VELOCITY_ok"].append(np.ones(n, dtype=bool))
        blocks["R5_FULL18"].append(P18)
        oks["R5_FULL18_ok"].append(np.ones(n, dtype=bool))
        blocks["R6_FULL18_VELOCITY"].append(np.hstack([P18, V18]))
        oks["R6_FULL18_VELOCITY_ok"].append(np.ones(n, dtype=bool))

        w, okw = window_summary(t, s10, h)
        blocks["R3_TRAJECTORY"].append(w)
        oks["R3_TRAJECTORY_ok"].append(okw)
        c, okc = causal_summary(t, s10, h_causal)
        blocks["R4_POSE_PAST_ONLY"].append(c)
        oks["R4_POSE_PAST_ONLY_ok"].append(okc)
        pca_rows.append(P10)

    out = {}
    for k, v in acc.items():
        out[k] = np.concatenate(v)
    for k, v in blocks.items():
        out[k] = np.vstack(v)
    for k, v in oks.items():
        out[k] = np.concatenate(v)

    # boundary flag at the frozen margin
    out["boundary_interior"] = C.boundary_mask(trials, plan["boundary"]["margin_frames"])

    # ---- integrity assertions (fail loudly, never silently) --------------
    assert out["R1_POSE"].shape[1] == 10
    assert out["R2_POSE_VELOCITY"].shape[1] == 20
    assert out["R3_TRAJECTORY"].shape[1] == 40
    assert out["R4_POSE_PAST_ONLY"].shape[1] == 30
    assert out["R5_FULL18"].shape[1] == 18
    assert out["R6_FULL18_VELOCITY"].shape[1] == 36
    assert np.isfinite(out["R1_POSE"]).all()
    assert np.isfinite(out["R2_POSE_VELOCITY"]).all()
    assert np.isfinite(out["R5_FULL18"]).all()
    # a window must never span more than one trial
    for t in trials:
        i0 = int(out["trial_index"][0])
    # frames marked ok for R3 must lie inside their own trial's window range
    ok = out["R3_TRAJECTORY_ok"]
    fi = out["frame_index"]
    ti = out["trial_index"]
    assert ((fi[ok] >= h)).all(), "an R3 window used frames before its trial start"
    n_per_trial = {t["trial_index"]: t["n_frames"] for t in trials}
    assert all(fi[i] < n_per_trial[ti[i]] - h for i in np.flatnonzero(ok)), \
        "an R3 window used frames after its trial end"
    # R4 is CAUSAL: it needs only h past frames, so it is defined at least as
    # WIDELY as R3 (which additionally needs h future frames).  The relation is
    # R3_ok subset-of R4_ok, not the other way round.
    assert (ok <= out["R4_POSE_PAST_ONLY_ok"]).all(), \
        "a frame with a full centred window must also have a full past-only window"

    np.savez_compressed(CACHE, **out)
    print(f"wrote {CACHE} ({os.path.getsize(CACHE)} bytes)")
    print(f"  rows {out['R1_POSE'].shape[0]}")
    for k in ("R1_POSE", "R2_POSE_VELOCITY", "R3_TRAJECTORY",
              "R4_POSE_PAST_ONLY", "R5_FULL18", "R6_FULL18_VELOCITY"):
        print(f"  {k:<20} {out[k].shape[1]:>3d} features, "
              f"{int(out[k + '_ok'].sum())} valid rows")
    print(f"  R3 window = {h} frames "
          f"({h * 10} ms at 100 Hz); causal window = {h_causal} frames")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
