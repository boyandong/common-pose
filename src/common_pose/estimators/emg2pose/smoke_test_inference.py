"""
smoke_test_inference.py -- Real end-to-end inference smoke test on the OFFICIAL
emg2pose mini dataset, using the official pretrained checkpoints.

This does NOT train anything. It loads a pretrained checkpoint, feeds real
recorded 16-channel sEMG through the model, and checks:

  * checkpoint loads
  * input shape contract
  * output shape contract
  * no NaN / Inf
  * numerical range plausibility vs. the official joint limits
  * angular error against ground-truth motion-capture labels (sanity, since
    this is an evaluation, not a training run)

Evidence is written to docs/smoke_test_evidence.json.

Run (from emg2pose_handstate/):
    ..\\.venv-emg2pose310\\Scripts\\python.exe inference\\smoke_test_inference.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT / "baseline" / "emg2pose"
DATA = ROOT / "data" / "official" / "emg2pose_dataset_mini"
DOCS = ROOT / "docs"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
except Exception:  # pragma: no cover
    pass

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))

from predict_pose import EMG_SAMPLE_RATE, NUM_JOINTS, PredictPose  # noqa: E402

# Official joint limits (radians), from generic_hand_model.json indices 0..19.
JOINT_LIMITS_RAD = np.array(
    [
        [-0.78726643, 1.28726649],
        [-0.61179936, 0.61179936],
        [0.0, 1.28726649],
        [-0.25853947, 1.08726645],
        [-0.33726647, 0.48726645],
        [-0.28726646, 1.33726645],
        [0.0, 1.88246226],
        [0.0, 1.43366337],
        [-0.48726645, 0.28726646],
        [-0.28726646, 1.43726647],
        [0.0, 1.88246226],
        [0.0, 1.43366337],
        [-0.28726646, 0.28726646],
        [-0.28726646, 1.53726649],
        [0.0, 1.88246226],
        [0.0, 1.43366337],
        [-0.68726647, 0.48726645],
        [-0.48726645, 1.63726652],
        [0.0, 1.88246226],
        [0.0, 1.43366337],
    ]
)

# Official 5-second evaluation trajectory length (paper: "we evaluate on 5 second
# trajectories"), in raw 2 kHz samples.
WINDOW = 10_000


def main() -> int:
    from emg2pose.data import Emg2PoseSessionData

    ev: dict = {"test": "smoke_test_inference", "env": {}}
    report: list[str] = []
    w = report.append

    w("=" * 78)
    w("REAL INFERENCE SMOKE TEST -- official emg2pose mini dataset")
    w("=" * 78)

    # ---------------- data ----------------
    files = sorted(DATA.glob("*.hdf5"))
    if not files:
        print(f"FATAL: no HDF5 files under {DATA}", file=sys.stderr)
        return 2
    session_path = files[0]
    sess = Emg2PoseSessionData(hdf5_path=session_path)
    n = len(sess)
    w(f"session        : {session_path.name}")
    w(f"samples (2 kHz): {n}  ({n / EMG_SAMPLE_RATE:.2f} s)")
    w(f"user / stage   : {sess.metadata.get('user')} / {sess.metadata.get('stage')}")
    w(f"side           : {sess.metadata.get('side')}")
    w("")

    emg_all = np.asarray(sess["emg"], dtype=np.float32)  # (T,16)
    ja_all = np.asarray(sess["joint_angles"], dtype=np.float32)  # (T,20)
    ev["env"].update(
        {
            "session": session_path.name,
            "n_samples": int(n),
            "emg_shape": list(emg_all.shape),
            "joint_angles_shape": list(ja_all.shape),
            "declared_num_channels": int(sess.metadata.get("num_channels", -1)),
            "declared_sample_rate": float(sess.metadata.get("sample_rate", -1)),
        }
    )

    # ---------------- model ----------------
    results: dict = {}
    for experiment in ("regression_vemg2pose", "tracking_vemg2pose", "regression_neuropose"):
        ckpt = ROOT / "checkpoints" / "emg2pose_model_checkpoints" / f"{experiment}.ckpt"
        if not ckpt.is_file():
            w(f"[skip] {experiment}: checkpoint missing")
            continue
        w("-" * 78)
        w(f"MODEL: {experiment}")
        w("-" * 78)
        t0 = time.time()
        model = PredictPose(experiment=experiment, device="cpu")
        load_s = time.time() - t0
        w(f"  checkpoint loaded            : {ckpt.name} ({ckpt.stat().st_size/1e6:.1f} MB)")
        w(f"  provide_initial_pos          : {model.provide_initial_pos}")
        w(f"  left_context / right_context : {model.left_context} / {model.right_context}")
        w(f"  load time                    : {load_s:.2f} s")

        lc = model.left_context
        start = 0
        T = min(WINDOW + lc, n - 1)
        emg_win = emg_all[start:T]  # (T,16)
        n_out_expected = emg_win.shape[0] - lc

        t0 = time.time()
        res = model.predict_full(emg_win)
        infer_s = time.time() - t0
        pred = res.angles

        w(f"  input emg shape              : {emg_win.shape}")
        w(f"  output shape                 : {pred.shape}")
        w(f"  expected T_pose              : {n_out_expected}")
        w(f"  time alignment start_index    : {res.start_index}")
        w(f"  inference time               : {infer_s:.2f} s "
          f"({emg_win.shape[0]/EMG_SAMPLE_RATE/infer_s:.1f}x realtime)")

        finite = bool(np.isfinite(pred).all())
        n_nan = int(np.isnan(pred).sum())
        n_inf = int(np.isinf(pred).sum())
        amin, amax = float(pred.min()), float(pred.max())
        w(f"  finite (no NaN/Inf)          : {finite}  (nan={n_nan}, inf={n_inf})")
        w(f"  value range (rad)            : [{amin:.4f}, {amax:.4f}]")
        w(f"  value range (deg)            : [{np.degrees(amin):.2f}, {np.degrees(amax):.2f}]")

        # within official limits?
        lo = JOINT_LIMITS_RAD[:, 0][None, :]
        hi = JOINT_LIMITS_RAD[:, 1][None, :]
        if pred.shape[1] == NUM_JOINTS:
            out_of_lim = (pred < lo - 1e-3) | (pred > hi + 1e-3)
            frac_oob = float(out_of_lim.mean())
            per_joint_oob = out_of_lim.mean(axis=0)
            w(f"  frac outside official limits : {frac_oob:.4f} "
              f"({frac_oob*100:.2f}% of joint-time samples)")
            worst = np.argsort(-per_joint_oob)[:5]
            w("  worst joints (frac out-of-bounds): "
              + ", ".join(f"j{int(i)}={per_joint_oob[i]:.3f}" for i in worst))

        # Accuracy vs ground truth (sanity only -- NOT a benchmark number).
        #
        # CRITICAL: IK failures are encoded as ALL-ZERO joint-angle rows, not
        # NaNs (official helper: emg2pose.utils.get_ik_failures_mask). Those
        # rows are INVALID poses and must be excluded from every pose
        # statistic. Including them produces a meaningless (inflated) error.
        mae_rad = float("nan")
        mae_rad_masked = float("nan")
        frac_ik_fail = float("nan")
        if pred.shape[1] == NUM_JOINTS:
            from emg2pose.utils import get_ik_failures_mask

            gt = ja_all[lc:T].astype(np.float32)
            if gt.shape == pred.shape:
                # (a) UNMASKED: reported only to quantify the contamination.
                mae_rad = float(np.abs(pred - gt).mean())

                # (b) MASKED: the correct number.
                ok = get_ik_failures_mask(gt)  # True where NOT an IK failure
                frac_ik_fail = float((~ok).mean())
                if ok.any():
                    diff = np.abs(pred[ok] - gt[ok])
                    mae_rad_masked = float(diff.mean())
                    per_joint = diff.mean(axis=0)
                else:
                    per_joint = np.full(NUM_JOINTS, np.nan)

                w(f"  IK-failure rows in window     : {frac_ik_fail*100:.2f}% "
                  f"(all-zero joint_angles rows -- EXCLUDED from masked metric)")
                w(f"  MAE vs ground truth (MASKED)  : {mae_rad_masked:.4f} rad "
                  f"({np.degrees(mae_rad_masked):.2f} deg)")
                w(f"  MAE vs ground truth (UNMASKED): {mae_rad:.4f} rad "
                  f"({np.degrees(mae_rad):.2f} deg)  <-- CONTAMINATED, do not cite")
                w("    (single held-out-user session; sanity check only, NOT the")
                w("     official benchmark number, which averages over test users)")
                w("  per-joint MAE (deg, masked): "
                  + " ".join(f"{np.degrees(v):.1f}" for v in per_joint))

        results[experiment] = {
            "checkpoint_loaded": True,
            "provide_initial_pos": model.provide_initial_pos,
            "left_context": int(model.left_context),
            "right_context": int(model.right_context),
            "input_shape": list(emg_win.shape),
            "output_shape": list(pred.shape),
            "start_index": int(res.start_index),
            "finite": finite,
            "n_nan": n_nan,
            "n_inf": n_inf,
            "min_rad": amin,
            "max_rad": amax,
            "min_deg": float(np.degrees(amin)),
            "max_deg": float(np.degrees(amax)),
            "inference_seconds": infer_s,
            "realtime_factor": float(emg_win.shape[0] / EMG_SAMPLE_RATE / infer_s),
            "mae_rad": mae_rad,
            "mae_deg": float(np.degrees(mae_rad)) if mae_rad == mae_rad else None,
            "mae_rad_masked": mae_rad_masked,
            "mae_deg_masked": float(np.degrees(mae_rad_masked)) if mae_rad_masked == mae_rad_masked else None,
            "frac_ik_failure_in_window": frac_ik_fail,
            "metric_note": (
                "mae_*_masked excludes all-zero IK-failure rows and is the only "
                "valid number. mae_rad/mae_deg are UNMASKED and contaminated; "
                "kept only to quantify contamination."
            ),
        }
        w("")

        # Extra: explicit tiny-input contract check
        if experiment == "regression_vemg2pose":
            try:
                model.predict(emg_all[: model.min_input_length() - 1])
                w("  [contract] too-short input correctly NOT rejected  <-- BUG")
                results[experiment]["short_input_rejected"] = False
            except ValueError as e:
                w(f"  [contract] too-short input rejected as expected: {str(e)[:70]}...")
                results[experiment]["short_input_rejected"] = True
            w("")

    ev["results"] = results
    (DOCS / "smoke_test_evidence.json").write_text(
        json.dumps(ev, indent=2, default=str), encoding="utf-8"
    )
    text = "\n".join(report)
    (DOCS / "smoke_test_report.txt").write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"\n[written] {DOCS / 'smoke_test_evidence.json'}")
    print(f"[written] {DOCS / 'smoke_test_report.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
