"""Frozen, resumable Gate4C per-record upstream substitution acquisition."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import h5py
import joblib
import numpy as np
import torch

sys.path.insert(0, "/root/work/emg2pose")
sys.path.insert(0, "/root/work/emg2pose_inference")
sys.path.insert(0, "/root/work/common-pose")
from predict_pose import PredictPose  # noqa: E402
from src.common_pose.representation.canonical_hand import (  # noqa: E402
    resolve_source_indices, to_canonical16,
)


LANE = Path(__file__).resolve().parents[1]
CKPT = Path("/root/models/emg2pose/regression_vemg2pose.ckpt")
HEAD = Path("/root/work/gate3_work/frozen_head/frozen_db9_trusted8_lda.joblib")
HELPER = Path("/root/work/emg2pose_inference/predict_pose.py")
ADAPTER = Path("/root/work/common-pose/src/common_pose/representation/canonical_hand.py")
CKPT_SHA = "748b1d1ef0ce1985f6fc07225d97eebfb370243429af803b4997d28ecce2424e"
HEAD_SHA = "b0ef8caf8e390a480fa2a3b448f79ccf14f75c71265ef925ee299a5e9e660386"
HELPER_SHA = "6cdd060ab639975eb5e2f96bfe43d01371f9f91ec6ecb812c2af2c314bbef818"
ADAPTER_SHA = "24694cfda80604148490485d47bf5eddc8e20479d1b55d522ca5d0199b649193"
UPSTREAM_TREE_SHA = "0fc2d40b69c46254c9cb4fdc72e7a3e2f37549803e60bb698b6ba09ffecb6b7b"
TRUSTED8 = [2, 3, 5, 6, 9, 13, 17, 18]
CANONICAL_TRUSTED8 = [2, 3, 4, 5, 7, 10, 13, 14]
BLOCK = 40


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(4 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def frozen_hash(path: Path, seal: Path) -> str:
    expected = seal.read_text(encoding="ascii").split()[0]
    actual = sha(path)
    if actual != expected:
        raise RuntimeError(f"frozen hash differs: {path}")
    return actual


def upstream_tree_sha() -> str:
    root = Path("/root/work/emg2pose")
    raw = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"])
    paths = sorted(x.decode() for x in raw.split(b"\0") if x)
    if len(paths) != 97 or subprocess.check_output(
        ["git", "-C", str(root), "ls-files", "--others", "--exclude-standard"]
    ).strip():
        raise RuntimeError("upstream repository inventory differs")
    h = hashlib.sha256()
    for rel in paths:
        h.update(rel.encode() + b"\0" + sha(root / rel).encode() + b"\0")
    return h.hexdigest()


def receipt_ok(out: Path, receipt: Path, row: dict, plan_sha: str,
               cohort_sha: str, runner_sha: str) -> bool:
    if not out.is_file() or not receipt.is_file():
        return False
    try:
        meta = json.loads(receipt.read_text(encoding="utf-8"))
        return (meta["input_sha256"] == row["sha256"] and
                meta["output_sha256"] == sha(out) and
                meta["plan_sha256"] == plan_sha and
                meta["cohort_sha256"] == cohort_sha and
                meta["runner_sha256"] == runner_sha)
    except (KeyError, ValueError, OSError):
        return False


def one(row: dict, model: PredictPose, head, mu, sd, root: Path,
        plan_sha: str, cohort_sha: str, runner_sha: str) -> None:
    source = Path(row["path"])
    if source.stat().st_size != row["size"] or sha(source) != row["sha256"]:
        raise RuntimeError(f"source identity changed: {source}")
    with h5py.File(source, "r") as h:
        ts = h["emg2pose"]["timeseries"]
        emg, gt, times = ts["emg"], ts["joint_angles"], ts["time"]
    if emg.shape[1] != 16 or gt.shape[1] != 20 or len(emg) != len(gt):
        raise RuntimeError(f"source shape differs: {source}")
    input_tensor = model._as_tensor(emg)
    if not input_tensor.is_cuda:
        raise RuntimeError("EMG input tensor is not on CUDA")
    predicted = model.predict(input_tensor)
    offset = model.left_context
    if offset != 1790 or model.right_context != 0 or predicted.shape != (len(gt)-offset, 20):
        raise RuntimeError(f"frozen model alignment differs: {source}")
    gt_w = gt[offset:]
    time_w = times[offset:]
    if len(time_w) != len(predicted) or not np.isfinite(time_w).all() or not np.all(np.diff(time_w) > 0):
        raise RuntimeError(f"frozen timestamp rule failed: {source}")
    gt_valid = (~np.all(np.isclose(gt_w, 0.0), axis=1)) & np.isfinite(gt_w).all(axis=1)
    pred_valid = (~np.all(np.isclose(predicted, 0.0), axis=1)) & np.isfinite(predicted).all(axis=1)
    blocks = len(gt_w) // BLOCK
    usable = blocks * BLOCK
    g20 = gt_w[:usable].reshape(blocks, BLOCK, 20).mean(axis=1)
    p20 = predicted[:usable].reshape(blocks, BLOCK, 20).mean(axis=1)
    g = to_canonical16(g20, repo_root="/root/work/emg2pose")[:, CANONICAL_TRUSTED8]
    p = to_canonical16(p20, repo_root="/root/work/emg2pose")[:, CANONICAL_TRUSTED8]
    gok = gt_valid[:usable].reshape(blocks, BLOCK).all(axis=1)
    pok = pred_valid[:usable].reshape(blocks, BLOCK).all(axis=1)
    gok[0] = False
    pok[0] = False
    both = gok & pok
    indices = np.flatnonzero(both).astype(np.int32)
    gz = (g[both] - mu) / sd
    pz = (p[both] - mu) / sd
    ygt = head.predict(gz).astype(np.int16)
    ypred = head.predict(pz).astype(np.int16)
    proba_gt = head.predict_proba(gz).astype(np.float32)
    proba_pred = head.predict_proba(pz).astype(np.float32)
    out = root / row["split"] / row["participant_id"] / (source.stem + ".npz")
    out.parent.mkdir(parents=True, exist_ok=True)
    temp = out.with_name(out.name + f".{os.getpid()}.partial")
    with temp.open("wb") as f:
        np.savez_compressed(f, block_index=indices, gt_pose8=g[both].astype(np.float32),
                            pred_pose8=p[both].astype(np.float32),
                            gt_api8=gz.astype(np.float32), pred_api8=pz.astype(np.float32),
                            y_gt=ygt, y_pred=ypred, proba_gt=proba_gt,
                            proba_pred=proba_pred)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, out)
    meta = {"source_member": row["source_member"], "input_sha256": row["sha256"],
            "output_sha256": sha(out), "plan_sha256": plan_sha,
            "cohort_sha256": cohort_sha, "runner_sha256": runner_sha,
            "source_rows": len(gt), "aligned_rows": len(gt_w),
            "total_blocks": blocks, "gt_valid_blocks": int(gok.sum()),
            "pred_valid_blocks": int(pok.sum()), "paired_valid_blocks": len(indices),
            "cuda": True, "head_retrained": False}
    receipt = out.with_suffix(".json")
    temp_meta = receipt.with_name(receipt.name + f".{os.getpid()}.partial")
    temp_meta.write_text(json.dumps(meta, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temp_meta, receipt)


def main() -> None:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--status", action="store_true")
    args = ap.parse_args()
    cohort_sha = frozen_hash(LANE / "COHORT_MANIFEST.json", LANE / "COHORT_MANIFEST.sha256")
    plan_sha = frozen_hash(LANE / "GATE4C_PLAN.md", LANE / "GATE4C_PLAN.sha256")
    runner_sha = frozen_hash(Path(__file__), LANE / "scripts" / "run_gate4c.sha256")
    cohort = json.loads((LANE / "COHORT_MANIFEST.json").read_text(encoding="utf-8"))
    rows = cohort["selected_files"]
    if len(rows) != 926 or cohort["users"] != 27 or cohort["sessions"] != 27:
        raise RuntimeError("frozen cohort differs")
    if cohort["protected_splits_opened"] or cohort["discovery_user_opened"]:
        raise RuntimeError("protected split declaration differs")
    root = LANE / ("smoke" if args.smoke else "results")
    if args.status:
        complete = sum(receipt_ok(root / r["split"] / r["participant_id"] /
                                  (Path(r["path"]).stem + ".npz"),
                                  root / r["split"] / r["participant_id"] /
                                  (Path(r["path"]).stem + ".json"),
                                  r, plan_sha, cohort_sha, runner_sha) for r in rows)
        print(f"GATE4C_PROGRESS {complete}/{len(rows)}")
        return
    if not torch.cuda.is_available() or "RTX 4090" not in torch.cuda.get_device_name(0):
        raise RuntimeError("frozen CUDA GPU unavailable or unexpected")
    for path, expected in ((CKPT, CKPT_SHA), (HEAD, HEAD_SHA),
                           (HELPER, HELPER_SHA), (ADAPTER, ADAPTER_SHA)):
        if sha(path) != expected:
            raise RuntimeError(f"frozen implementation identity differs: {path}")
    source_indices = resolve_source_indices("/root/work/emg2pose")
    if [source_indices[i] for i in CANONICAL_TRUSTED8] != TRUSTED8:
        raise RuntimeError("frozen Common Pose shared DOF map differs")
    if upstream_tree_sha() != UPSTREAM_TREE_SHA:
        raise RuntimeError("frozen upstream worktree differs")
    bundle = joblib.load(HEAD)
    head, mu, sd = bundle["head"], bundle["mu"], bundle["sd"]
    if list(head.classes_) != list(range(1, 9)) or not bundle["meta"]["replication_check"]["exact"]:
        raise RuntimeError("frozen downstream head contract differs")
    model = PredictPose(experiment="regression_vemg2pose", checkpoint=str(CKPT),
                        repo_root="/root/work/emg2pose", device="cuda")
    if not next(model._module.parameters()).is_cuda:
        raise RuntimeError("model parameters are not on CUDA")
    selected = rows[:1] if args.smoke else rows
    for i, row in enumerate(selected, 1):
        out = root / row["split"] / row["participant_id"] / (Path(row["path"]).stem + ".npz")
        receipt = out.with_suffix(".json")
        if receipt_ok(out, receipt, row, plan_sha, cohort_sha, runner_sha):
            print(f"SKIP {i}/{len(selected)} {row['source_member']}", flush=True)
            continue
        one(row, model, head, mu, sd, root, plan_sha, cohort_sha, runner_sha)
        print(f"COMPLETE {i}/{len(selected)} {row['source_member']}", flush=True)
    print(f"GATE4C_{'SMOKE' if args.smoke else 'ACQUISITION'}_COMPLETE {len(selected)}/{len(selected)}", flush=True)


if __name__ == "__main__":
    main()
