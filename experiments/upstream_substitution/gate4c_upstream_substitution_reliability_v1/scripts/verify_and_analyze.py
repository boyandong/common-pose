"""Independent Gate4C result audit and frozen user-level analysis.

Run --verify only after the detached 926-file job ends. Run --analyze only
after --verify has sealed a complete PASS report. Never inspect partial results.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

import joblib
import numpy as np
from scipy.stats import spearmanr


LANE = Path(__file__).resolve().parents[1]
RESULTS = LANE / "results"
ART = LANE / "artifacts"
HEAD = Path("/root/work/gate3_work/frozen_head/frozen_db9_trusted8_lda.joblib")
HEAD_SHA = "b0ef8caf8e390a480fa2a3b448f79ccf14f75c71265ef925ee299a5e9e660386"
FLOOR = 10_000
SEED = 20260924
BOOT = 10_000


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(4 << 20), b""):
            h.update(b)
    return h.hexdigest()


def checked(path: Path, seal: Path) -> str:
    wanted = seal.read_text(encoding="ascii").split()[0]
    found = sha(path)
    if found != wanted:
        raise RuntimeError(f"sealed identity differs: {path}")
    return found


def seal_json(path: Path, value: dict) -> str:
    if path.exists() or path.with_suffix(".sha256").exists():
        raise FileExistsError(f"refusing to overwrite sealed result: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    digest = sha(path)
    path.with_suffix(".sha256").write_bytes(
        f"{digest}  {path.name}\n".encode("ascii"))
    path.with_suffix(".sha256").chmod(0o444)
    return digest


def frozen() -> tuple[dict, str, str, str]:
    plan = checked(LANE / "GATE4C_PLAN.md", LANE / "GATE4C_PLAN.sha256")
    cohort = checked(LANE / "COHORT_MANIFEST.json", LANE / "COHORT_MANIFEST.sha256")
    runner = checked(LANE / "scripts/run_gate4c.py", LANE / "scripts/run_gate4c.sha256")
    checked(LANE / "IMPLEMENTATION_REPAIR_001.md", LANE / "IMPLEMENTATION_REPAIR_001.sha256")
    if sha(HEAD) != HEAD_SHA:
        raise RuntimeError("frozen head identity differs")
    obj = json.loads((LANE / "COHORT_MANIFEST.json").read_text(encoding="utf-8"))
    if len(obj["selected_files"]) != 926 or obj["users"] != 27 or obj["sessions"] != 27:
        raise RuntimeError("frozen cohort population differs")
    return obj, plan, cohort, runner


def paths(row: dict) -> tuple[Path, Path]:
    p = RESULTS / row["split"] / row["participant_id"] / (Path(row["path"]).stem + ".npz")
    return p, p.with_suffix(".json")


def verify() -> None:
    cohort, plan_sha, cohort_sha, runner_sha = frozen()
    marker = "GATE4C_ACQUISITION_COMPLETE 926/926"
    log = (LANE / "run_stdout.txt").read_text(encoding="utf-8", errors="replace")
    if marker not in log:
        raise RuntimeError("detached acquisition has not logged final completion")
    expected_npz = {paths(r)[0] for r in cohort["selected_files"]}
    expected_json = {paths(r)[1] for r in cohort["selected_files"]}
    if set(RESULTS.rglob("*.npz")) != expected_npz or set(RESULTS.rglob("*.json")) != expected_json:
        raise RuntimeError("result membership differs from exact frozen cohort")
    if list(RESULTS.rglob("*.partial")):
        raise RuntimeError("result directory contains partial outputs")
    users = defaultdict(lambda: {"files": 0, "gt_valid_blocks": 0,
                                 "pred_valid_blocks": 0, "paired_valid_blocks": 0})
    total = 0
    for i, row in enumerate(cohort["selected_files"], 1):
        p, receipt = paths(row)
        m = json.loads(receipt.read_text(encoding="utf-8"))
        if (m["source_member"] != row["source_member"] or
            m["input_sha256"] != row["sha256"] or
            m["output_sha256"] != sha(p) or m["plan_sha256"] != plan_sha or
            m["cohort_sha256"] != cohort_sha or m["runner_sha256"] != runner_sha or
            m["cuda"] is not True or m["head_retrained"] is not False):
            raise RuntimeError(f"receipt identity differs: {p}")
        n = m["paired_valid_blocks"]
        if (m["source_rows"] != row["hdf5_rows"] or
            m["aligned_rows"] != m["source_rows"] - 1790 or
            m["total_blocks"] != m["aligned_rows"] // 40 or
            not 0 <= n <= min(m["gt_valid_blocks"], m["pred_valid_blocks"]) <= m["total_blocks"]):
            raise RuntimeError(f"receipt counts differ: {p}")
        with np.load(p, allow_pickle=False) as z:
            required = {"block_index", "gt_pose8", "pred_pose8", "gt_api8",
                        "pred_api8", "y_gt", "y_pred", "proba_gt", "proba_pred"}
            if set(z.files) != required:
                raise RuntimeError(f"result schema differs: {p}")
            idx = z["block_index"]
            if idx.shape != (n,) or (n and (idx[0] <= 0 or idx[-1] >= m["total_blocks"] or
                                        not np.all(np.diff(idx) > 0))):
                raise RuntimeError(f"block index differs: {p}")
            for field in ("gt_pose8", "pred_pose8", "gt_api8", "pred_api8",
                          "proba_gt", "proba_pred"):
                a = z[field]
                if a.shape != (n, 8) or not np.isfinite(a).all():
                    raise RuntimeError(f"array shape or finite values differ: {p} {field}")
            for field in ("y_gt", "y_pred"):
                a = z[field]
                if a.shape != (n,) or not np.isin(a, range(1, 9)).all():
                    raise RuntimeError(f"class output differs: {p} {field}")
            for field in ("proba_gt", "proba_pred"):
                a = z[field]
                if (not ((a >= 0) & (a <= 1)).all() or
                    not np.allclose(a.sum(axis=1), 1.0, atol=1e-5)):
                    raise RuntimeError(f"probability output differs: {p} {field}")
        u = users[(row["split"], row["participant_id"], row["session_id"])]
        u["files"] += 1
        for name in ("gt_valid_blocks", "pred_valid_blocks", "paired_valid_blocks"):
            u[name] += m[name]
        total += n
        if i % 100 == 0:
            print(f"RESULT_VERIFIED {i}/926", flush=True)
    if len(users) != 27:
        raise RuntimeError("user/session inventory differs")
    report = {"status": "PASS", "schema": "gate4c-result-integrity-v1",
              "plan_sha256": plan_sha, "cohort_sha256": cohort_sha,
              "runner_sha256": runner_sha, "files": 926, "users": 27,
              "paired_valid_blocks": total,
              "by_user": [{"split": k[0], "participant_id": k[1],
                           "session_id": k[2], **v, "below_10000_paired_blocks":
                           v["paired_valid_blocks"] < FLOOR}
                          for k, v in sorted(users.items())]}
    digest = seal_json(ART / "RESULT_INTEGRITY.json", report)
    print(f"GATE4C_RESULT_INTEGRITY_PASS 926/926 sha256={digest}", flush=True)


def scalar_summary(values: list[float | None]) -> dict:
    if not values or any(v is None or not np.isfinite(v) for v in values):
        return {"median": None, "q25": None, "q75": None,
                "minimum": None, "maximum": None}
    a = np.asarray(values, dtype=np.float64)
    return {"median": float(np.median(a)), "q25": float(np.quantile(a, .25)),
            "q75": float(np.quantile(a, .75)), "minimum": float(a.min()),
            "maximum": float(a.max())}


def bootstrap_median(values: list[float | None]) -> list[float] | None:
    if not values or any(v is None or not np.isfinite(v) for v in values):
        return None
    a = np.asarray(values, dtype=np.float64)
    rng = np.random.default_rng(SEED)
    medians = np.median(a[rng.integers(0, len(a), size=(BOOT, len(a)))], axis=1)
    return [float(np.quantile(medians, .025)), float(np.quantile(medians, .975))]


def association(x: np.ndarray, flips: np.ndarray) -> float | None:
    if len(x) < 2 or np.unique(x).size < 2 or np.unique(flips).size < 2:
        return None
    value = float(spearmanr(x, flips).statistic)
    return value if np.isfinite(value) else None


def analyze() -> None:
    cohort, plan_sha, cohort_sha, runner_sha = frozen()
    integrity_path = ART / "RESULT_INTEGRITY.json"
    integrity_sha = checked(integrity_path, ART / "RESULT_INTEGRITY.sha256")
    integrity = json.loads(integrity_path.read_text(encoding="utf-8"))
    if (integrity["status"] != "PASS" or integrity["files"] != 926 or
        integrity["plan_sha256"] != plan_sha or
        integrity["cohort_sha256"] != cohort_sha or
        integrity["runner_sha256"] != runner_sha):
        raise RuntimeError("independent result integrity is not PASS")
    bundle = joblib.load(HEAD)
    head = bundle["head"]
    by_user_files = defaultdict(list)
    for r in cohort["selected_files"]:
        by_user_files[(r["split"], r["participant_id"], r["session_id"])].append(r)
    user_metrics = []
    deciles = []
    for (split, participant, session), rows in sorted(by_user_files.items()):
        arrays = defaultdict(list)
        gt_valid = pred_valid = paired = 0
        for row in rows:
            p, receipt = paths(row)
            m = json.loads(receipt.read_text(encoding="utf-8"))
            gt_valid += m["gt_valid_blocks"]
            pred_valid += m["pred_valid_blocks"]
            paired += m["paired_valid_blocks"]
            with np.load(p, allow_pickle=False) as z:
                for name in ("gt_pose8", "pred_pose8", "gt_api8", "pred_api8",
                             "y_gt", "y_pred", "proba_gt", "proba_pred"):
                    arrays[name].append(z[name])
        a = {k: np.concatenate(v, axis=0) for k, v in arrays.items()}
        if len(a["y_gt"]) != paired:
            raise RuntimeError(f"paired count differs for {participant}")
        coverage = float(paired / gt_valid) if gt_valid else None
        agreement = float(np.mean(a["y_gt"] == a["y_pred"])) if paired else None
        counts = np.zeros((8, 8), dtype=np.int64)
        if paired:
            np.add.at(counts, (a["y_gt"].astype(int)-1, a["y_pred"].astype(int)-1), 1)
        support = counts.sum(axis=1)
        preservation = [float(counts[i, i] / support[i]) if support[i] else None
                        for i in range(8)]
        balanced = (float(np.mean([preservation[i] for i in range(8)
                                   if support[i] >= 30])) if (support >= 30).any() else None)
        if paired:
            chance = float(np.dot(counts.sum(axis=1), counts.sum(axis=0)) / paired**2)
            kappa = float((agreement-chance)/(1-chance)) if chance < 1 else None
            tv = .5 * np.abs(a["proba_gt"] - a["proba_pred"]).sum(axis=1)
            tv_median = float(np.median(tv))
            pose = np.sqrt(np.mean((a["gt_pose8"].astype(float)-a["pred_pose8"].astype(float))**2, axis=1))
            api = np.linalg.norm(a["gt_api8"].astype(float)-a["pred_api8"].astype(float), axis=1)
            fisher = np.linalg.norm(head.transform(a["gt_api8"])-head.transform(a["pred_api8"]), axis=1)
            flips = (a["y_gt"] != a["y_pred"]).astype(np.int8)
            rank_groups = np.array_split(np.argsort(pose, kind="mergesort"), 10)
            for j, ix in enumerate(rank_groups, 1):
                deciles.append({"split": split, "participant_id": participant,
                                "session_id": session, "decile": j, "count": len(ix),
                                "pose_rmse_median_radians": float(np.median(pose[ix])) if len(ix) else None,
                                "api_error_median": float(np.median(api[ix])) if len(ix) else None,
                                "fisher_error_median": float(np.median(fisher[ix])) if len(ix) else None,
                                "flip_rate": float(np.mean(flips[ix])) if len(ix) else None})
            chain = {"pose_rmse_median_radians": float(np.median(pose)),
                     "api_error_median": float(np.median(api)),
                     "fisher_error_median": float(np.median(fisher)),
                     "spearman_pose_error_vs_flip": association(pose, flips),
                     "spearman_api_error_vs_flip": association(api, flips),
                     "spearman_fisher_error_vs_flip": association(fisher, flips)}
        else:
            kappa = tv_median = None
            chain = {k: None for k in ("pose_rmse_median_radians", "api_error_median",
                                     "fisher_error_median", "spearman_pose_error_vs_flip",
                                     "spearman_api_error_vs_flip", "spearman_fisher_error_vs_flip")}
            for j in range(1, 11):
                deciles.append({"split": split, "participant_id": participant,
                                "session_id": session, "decile": j, "count": 0,
                                "pose_rmse_median_radians": None, "api_error_median": None,
                                "fisher_error_median": None, "flip_rate": None})
        user_metrics.append({"split": split, "participant_id": participant,
                             "session_id": session, "files": len(rows),
                             "gt_valid_blocks": gt_valid, "pred_valid_blocks": pred_valid,
                             "paired_valid_blocks": paired, "below_10000_paired_blocks": paired < FLOOR,
                             "valid_coverage": coverage, "hard_output_preservation": agreement,
                             "class_support": support.tolist(), "class_preservation": preservation,
                             "balanced_preservation": balanced, "cohen_kappa": kappa,
                             "tv_median": tv_median, "preservation_matrix_counts": counts.tolist(),
                             "error_chain": chain})
        print(f"USER_ANALYZED {len(user_metrics)}/27 {participant}", flush=True)
    val = [u for u in user_metrics if u["split"] == "VALIDATION"]
    dev = [u for u in user_metrics if u["split"] == "DEV"]
    if len(val) != 8 or len(dev) != 19:
        raise RuntimeError("frozen user split differs")
    summary = {"schema": "gate4c-user-analysis-v1", "status":
               "FULL_COHORT_FEASIBILITY_FAIL" if any(u["below_10000_paired_blocks"] for u in val)
               else "DESCRIPTIVE_COMPLETE", "result_integrity_sha256": integrity_sha,
               "plan_sha256": plan_sha, "cohort_sha256": cohort_sha,
               "primary_unit": "VALIDATION_USER", "validation_users": 8,
               "dev_users_descriptive_only": 19,
               "validation_hard_output_preservation": scalar_summary(
                   [u["hard_output_preservation"] for u in val]),
               "validation_hard_output_preservation_bootstrap_ci95": bootstrap_median(
                   [u["hard_output_preservation"] for u in val]),
               "validation_valid_coverage": scalar_summary([u["valid_coverage"] for u in val]),
               "validation_valid_coverage_bootstrap_ci95": bootstrap_median(
                   [u["valid_coverage"] for u in val]),
               "validation_insufficient_user_fraction": sum(
                   u["below_10000_paired_blocks"] for u in val) / 8,
               "validation_balanced_preservation": scalar_summary(
                   [u["balanced_preservation"] for u in val]),
               "validation_cohen_kappa": scalar_summary([u["cohen_kappa"] for u in val]),
               "validation_tv_median": scalar_summary([u["tv_median"] for u in val]),
               "semantic_balanced_accuracy": "NOT_IDENTIFIABLE",
               "semantic_macro_f1": "NOT_IDENTIFIABLE",
               "task_performance_delta": "NOT_IDENTIFIABLE",
               "unknown_ambiguous_flips": "NOT_APPLICABLE"}
    if any((ART / name).exists() for name in ("USER_METRICS.json", "ERROR_CHAIN_DECILES.json",
                                               "ANALYSIS_SUMMARY.json")):
        raise FileExistsError("analysis output already exists")
    seal_json(ART / "USER_METRICS.json", {"users": user_metrics})
    seal_json(ART / "ERROR_CHAIN_DECILES.json", {"rows": deciles})
    digest = seal_json(ART / "ANALYSIS_SUMMARY.json", summary)
    print(f"GATE4C_ANALYSIS_{summary['status']} users=27 sha256={digest}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--analyze", action="store_true")
    args = parser.parse_args()
    verify() if args.verify else analyze()
