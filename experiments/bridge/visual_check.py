"""
bridge_audit/visual_check.py -- PHASE 9, OPTIONAL visual inspection.

DEBUGGING / INTERPRETATION ONLY.

Renders a SMALL, PRE-DECLARED number of representative paired frames so a human
can see what "VEMG2Pose error" and "decoder boundary crossing" actually look like
in hand geometry. The selection rule is stated before the frames are looked at
and never uses emg2pose ``stage`` names as a proxy for gesture truth.

Selection (deterministic, quantile-based, no cherry-picking):
  A. low pose error AND decoder agreement            (best case)
  B. moderate pose error AND decoder agreement       (typical case)
  C. decoder boundary crossing (GT-pose vs predicted-pose top-1 differ)
  D. largest domain distance on which the two sides still AGREE
     -- i.e. a confident decoder output that the domain audit says is extrapolation

Geometry is rendered with the frozen Session-4 forward-kinematics implementation
(``hand_visualizer/tools/hand_kinematics_np.py``), which is used read-only.

Run:
    <EMG2POSE_VENV>\\Scripts\\python.exe visual_check.py --results <results dir>
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import decoder as D  # noqa: E402
from _common import CANON16, ROOT  # noqa: E402

VIZ_TOOLS = os.path.join(ROOT, "hand_visualizer", "tools")
if VIZ_TOOLS not in sys.path:
    sys.path.insert(0, VIZ_TOOLS)

# Finger chains as INDEX PATHS INTO THE OFFICIAL 21-LANDMARK ARRAY, derived from
# hand_model.json itself (rest positions + LANDMARK_NAMES), not guessed:
#   landmark 5 = WRIST_JOINT (the frame root, the origin of every chain)
#   landmark 0 = THUMB_FINGERTIP, 6/7 = THUMB_INTERMEDIATE/DISTAL_FRAME
#   landmark 1..4 = INDEX..PINKY fingertips, 8..19 = their proximal/intermediate/
#   distal frames in finger order.
# Verified by matching every landmark rest position against the corresponding
# joint rest position in config/hand_model.json.
CHAINS: dict[str, list[int]] = {
    "thumb": [5, 6, 7, 0],
    "index": [5, 8, 9, 10, 1],
    "middle": [5, 11, 12, 13, 2],
    "ring": [5, 14, 15, 16, 3],
    "pinky": [5, 17, 18, 19, 4],
}

#: canonical16 index -> official 20D index (frozen Session-2 contract).
#: The four MCP-AA slots are ABSENT from canonical16 by design; they are set to
#: zero for rendering only, which is stated on the figure.
CANON16_TO_OFFICIAL20 = [0, 1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15, 17, 18, 19]


def embed_canonical16_in_official20(x16: np.ndarray) -> np.ndarray:
    """Place a canonical16 vector back into the official 20D layout, MCP-AA = 0.

    RENDERING ONLY. This is not an inverse of the adapter and is never used for
    any statistic: it exists so the Session-4 forward-kinematics renderer, which
    expects 20 numbers in the official order, can draw a hand.
    """
    x16 = np.asarray(x16, dtype=np.float64)
    out = np.zeros((x16.shape[0], 20), dtype=np.float64)
    out[:, CANON16_TO_OFFICIAL20] = x16
    return out


def load_model():
    import hand_kinematics_np as H

    return H, H.load_default_model()


def select_frames(sess_dir: str, sessions: list[dict], dec: D.FrozenDecoder,
                  geom: D.DomainGeometry, *, n_per_case: int = 2, seed: int = 20260101):
    """Deterministic representative-frame selection. No stage names involved."""
    rng = np.random.default_rng(seed)
    G, P, S, T = [], [], [], []
    for s in sessions:
        z = np.load(os.path.join(sess_dir, f"{s['session']}.paired50hz.npz"))
        keep = z["gt_valid"]
        G.append(z["gt16"][keep].astype(np.float64))
        P.append(z["pred16"][keep].astype(np.float64))
        T.append(z["time"][keep])
        S.append(np.full(int(keep.sum()), s["session"], dtype=object))
    G = np.concatenate(G)
    P = np.concatenate(P)
    T = np.concatenate(T)
    S = np.concatenate(S)

    err = np.abs(np.degrees(P - G))
    mae = err.mean(axis=1)
    agree = dec.predict(G) == dec.predict(P)
    dist_g = geom.min_mahalanobis(dec.z(G), geom.centroids, geom.precision)

    q = np.percentile(mae, [5, 25, 50, 75, 95])
    cases = {}

    m = agree & (mae <= q[0])
    cases["A_low_error_agreement"] = m
    m = agree & (mae >= q[1]) & (mae <= q[2])
    cases["B_moderate_error_agreement"] = m
    cases["C_boundary_crossing"] = ~agree
    m = agree & (dist_g >= np.percentile(dist_g, 99))
    cases["D_confident_output_far_outside_db9"] = m

    picked = []
    for name, mask in cases.items():
        idx = np.flatnonzero(mask)
        if idx.size == 0:
            continue
        # spread over sessions: pick the top-n_per_case by the case's own criterion
        if name.startswith("A") or name.startswith("B"):
            score = -mae[idx] if name.startswith("A") else -np.abs(mae[idx] - q[1])
        elif name.startswith("C"):
            score = -np.abs(mae[idx] - np.median(mae[idx]))   # typical crossing
        else:
            score = dist_g[idx]
        order = idx[np.argsort(-score)]
        chosen, seen = [], set()
        for j in order:
            sid = str(S[j])
            if sid in seen:
                continue
            seen.add(sid)
            chosen.append(int(j))
            if len(chosen) >= n_per_case:
                break
        for j in chosen:
            picked.append({
                "case": name, "index": int(j), "session": str(S[j]), "time_s": float(T[j]),
                "canonical16_mae_deg": float(mae[j]),
                "decoder_gt": int(dec.predict(G[j:j + 1])[0]),
                "decoder_pred": int(dec.predict(P[j:j + 1])[0]),
                "agree": bool(agree[j]),
                "db9_min_mahalanobis_gt": float(dist_g[j]),
                "gt16": G[j].tolist(), "pred16": P[j].tolist(),
                "per_dof_abs_err_deg": err[j].tolist(),
            })
    return picked, {"mae_percentiles_deg": q.tolist(),
                    "selection_rule": {
                        "A": "agreement AND MAE <= p05",
                        "B": "agreement AND p25 <= MAE <= p50",
                        "C": "GT-pose and predicted-pose top-1 decoder labels differ, "
                             "closest to the median disagreement error",
                        "D": "agreement AND GT domain distance >= p99",
                        "spread": "at most one frame per session, in selection order",
                        "no_stage_names_used": True,
                    }}


def render(rec: dict, model, H, out_png: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    gt20 = embed_canonical16_in_official20(np.asarray(rec["gt16"])[None, :])[0]
    pr20 = embed_canonical16_in_official20(np.asarray(rec["pred16"])[None, :])[0]
    lm_gt = model.skin_landmarks(gt20)
    lm_pr = model.skin_landmarks(pr20)

    fig = plt.figure(figsize=(13.5, 5.4))
    for col, (title, lm, colour) in enumerate((
            ("GT emg2pose kinematics", lm_gt, "#1f77b4"),
            ("VEMG2Pose predicted kinematics", lm_pr, "#d62728"))):
        for row, (elev, azim) in enumerate(((80, -90), (20, -55))):
            ax = fig.add_subplot(2, 2, row * 2 + col + 1, projection="3d")
            for fname, chain in CHAINS.items():
                pts = lm[chain]
                ax.plot(pts[:, 0], pts[:, 1], pts[:, 2], "-o", ms=3.2, lw=1.7,
                        color=colour, alpha=0.9)
                ax.text(pts[-1, 0], pts[-1, 1], pts[-1, 2], f" {fname}", fontsize=6,
                        color=colour)
            c = lm.mean(axis=0)
            r = float(np.abs(lm - c).max()) * 1.05
            ax.set_xlim(c[0] - r, c[0] + r)
            ax.set_ylim(c[1] - r, c[1] + r)
            ax.set_zlim(c[2] - r, c[2] + r)
            ax.set_box_aspect((1, 1, 1))
            ax.view_init(elev=elev, azim=azim)
            ax.set_axis_off()
            if row == 0:
                ax.set_title(title, fontsize=10)
    fig.suptitle(
        f"case {rec['case']}  |  {rec['session'][-34:]}  t={rec['time_s']:.2f}s  |  "
        f"canonical16 MAE {rec['canonical16_mae_deg']:.1f} deg  |  "
        f"decoder GT-pose={rec['decoder_gt']} vs predicted-pose={rec['decoder_pred']}  "
        f"({'AGREE' if rec['agree'] else 'BOUNDARY CROSSING'})  |  "
        f"DB9 min-Mahalanobis(GT) {rec['db9_min_mahalanobis_gt']:.2f}\n"
        f"canonical16 is a LOSSY projection: the four non-thumb MCP ab/adduction DOF "
        f"are absent and drawn as 0 (identical on both sides). Debugging aid only.",
        fontsize=8.5,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(out_png, dpi=115)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", required=True)
    ap.add_argument("--n-per-case", type=int, default=2)
    args = ap.parse_args()

    results_path = os.path.join(args.results, "bridge_audit_results.json")
    r = json.load(open(results_path, encoding="utf-8"))
    sess_dir = r["artifacts"]["sessions_dir"]
    fig_dir = os.path.join(args.results, "figures")
    os.makedirs(fig_dir, exist_ok=True)

    dec = D.reconstruct(verbose=False)
    H, model = load_model()

    # Sanity: the chain indices must reference real landmarks of the loaded model.
    n_lm = int(model.landmark_rest_positions.shape[0])
    if n_lm != 21 or max(max(c) for c in CHAINS.values()) >= n_lm:
        print(f"[visual] unexpected landmark table ({n_lm} landmarks); aborting")
        return 2

    picked, meta = select_frames(sess_dir, r["phase2_3_corpus"]["sessions"], dec,
                                 dec.geometry, n_per_case=args.n_per_case)
    made = []
    for i, rec in enumerate(picked):
        png = os.path.join(fig_dir, f"paired_example_{i:02d}_{rec['case']}.png")
        render(rec, model, H, png)
        rec["figure"] = os.path.relpath(png, args.results).replace("\\", "/")
        made.append(png)
        print(f"  [{rec['case']}] mae={rec['canonical16_mae_deg']:.1f} deg "
              f"agree={rec['agree']} -> {os.path.basename(png)}")

    out = {
        "phase": "9 -- OPTIONAL visual inspection (debugging/interpretation only)",
        "policy": (
            "a small pre-declared number of representative paired frames; selection "
            "is deterministic and quantile-based; emg2pose stage names are never "
            "used as gesture truth and are not part of the selection rule"
        ),
        "renderer": {
            "module": "hand_visualizer/tools/hand_kinematics_np.py (Session 4, read-only)",
            "landmarks": "official 21-landmark skin model",
            "views": "two 3D viewpoints per pose (palm-on and oblique)",
            "canonical16_handling": (
                "canonical16 is embedded back into the official 20D layout with the "
                "four non-thumb MCP ab/adduction DOF set to ZERO, identically on the "
                "GT and the predicted side. This is a rendering convenience, not an "
                "inverse of the adapter, and it is stated on every figure. The four "
                "absent DOF are exactly the ones canonical16 drops by design, so they "
                "cannot create a visual difference between the two sides."
            ),
        },
        "selection_meta": meta,
        "examples": picked,
        "figures": [os.path.relpath(p, args.results).replace("\\", "/") for p in made],
    }
    with open(os.path.join(args.results, "phase9_visual_examples.json"), "w",
              encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=lambda o: float(o) if isinstance(o, np.floating)
                  else int(o) if isinstance(o, np.integer) else str(o))
    print(f"[written] {os.path.join(args.results, 'phase9_visual_examples.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
