#!/usr/bin/env python3
"""Frozen Gate4D DEV-only TTA and grouped selective-risk benchmark."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

import joblib
import numpy as np
from scipy.stats import spearmanr
from sklearn.ensemble import GradientBoostingRegressor

LANE = Path(__file__).resolve().parents[1]
ROOT = Path("/root/work/common-pose")
C = ROOT / "experiments/upstream_substitution/gate4c_upstream_substitution_reliability_v1"
RESULTS = C / "results"
ART = LANE / "artifacts"
TTA = LANE / "tta"
HEAD = Path("/root/work/gate3_work/frozen_head/frozen_db9_trusted8_lda.joblib")
SCALE = ROOT / "experiments/upstream_substitution/gate3b_continuous_representation/artifacts/FISHER_DB9_REFERENCE_SCALE.json"
CKPT = Path("/root/models/emg2pose/regression_vemg2pose.ckpt")
ADAPTER = ROOT / "src/common_pose/representation/canonical_hand.py"
PREDICTOR = Path("/root/work/emg2pose_inference/predict_pose.py")
PARENT_PLAN_SHA = "f346608139d1386947f7200c3fd80b93abcdec4e1fe385c2b647bf756eaa2332"
PARENT_COHORT_SHA = "db61d9c75510d78e17b3858943bc3dd052dab61aa041dc260c84e064e619bead"
PARENT_RUNNER_SHA = "e3ca8e3b2a7d4a6059ac5fba9d01df264d329f52dc3497fdcc9cfdc0b4e98091"
HEAD_SHA = "b0ef8caf8e390a480fa2a3b448f79ccf14f75c71265ef925ee299a5e9e660386"
CKPT_SHA = "748b1d1ef0ce1985f6fc07225d97eebfb370243429af803b4997d28ecce2424e"
ADAPTER_SHA = "24694cfda80604148490485d47bf5eddc8e20479d1b55d522ca5d0199b649193"
PREDICTOR_SHA = "6cdd060ab639975eb5e2f96bfe43d01371f9f91ec6ecb812c2af2c314bbef818"
COVERAGES = [1.0, .9, .8, .7, .6, .5, .3]
MODEL_KWARGS = dict(loss="quantile", alpha=.90, n_estimators=100,
                    learning_rate=.1, max_depth=3, subsample=1.0,
                    criterion="friedman_mse", min_samples_split=2,
                    min_samples_leaf=1, max_features=None, random_state=0)
TRUSTED_CANONICAL = [2, 3, 4, 5, 7, 10, 13, 14]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def checked(path: Path) -> str:
    expected = path.with_suffix(".sha256").read_text().split()[0]
    actual = sha(path)
    if actual != expected:
        raise RuntimeError(f"frozen hash differs: {path}")
    return actual


def save_json(name: str, obj: dict) -> None:
    ART.mkdir(exist_ok=True)
    path = ART / name
    if path.exists():
        raise RuntimeError(f"refuse overwrite: {path}")
    blob = (json.dumps(obj, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    temp = path.with_suffix(path.suffix + f".{os.getpid()}.partial")
    temp.write_bytes(blob)
    os.replace(temp, path)
    path.with_suffix(".sha256").write_text(f"{sha(path)}  {path.name}\n")


def frozen():
    for name in ("GATE4D_PLAN.md", "LAYER_SELECTION.md", "COHORT_MANIFEST.json",
                 "ANALYSIS_IMPLEMENTATION.md", "IMPLEMENTATION_REPAIR_001.md"):
        checked(LANE / name)
    checked(Path(__file__))
    if sha(C / "GATE4C_PLAN.md") != PARENT_PLAN_SHA or sha(C / "COHORT_MANIFEST.json") != PARENT_COHORT_SHA:
        raise RuntimeError("Gate4C identity changed")
    if sha(HEAD) != HEAD_SHA:
        raise RuntimeError("frozen head changed")
    cohort = json.loads((LANE / "COHORT_MANIFEST.json").read_text())
    rows = cohort["selected_files"]
    users = cohort["users"]
    if len(rows) != 654 or len(users) != 19 or any(r["split"] != "DEV" for r in rows):
        raise RuntimeError("DEV cohort differs")
    source = json.loads((C / "COHORT_MANIFEST.json").read_text())
    if rows != [r for r in source["selected_files"] if r["split"] == "DEV"]:
        raise RuntimeError("not exact Gate4C DEV subset")
    bundle = joblib.load(HEAD)
    head, mu, sd = bundle["head"], bundle["mu"], bundle["sd"]
    if head.scalings_.shape != (8, 7) or list(head.classes_) != list(range(1, 9)):
        raise RuntimeError("Fisher geometry changed")
    sigma = np.array(json.loads(SCALE.read_text())["fisher_component_sigma_db9"], dtype=np.float64)
    if sigma.shape != (7,) or not np.all(sigma > 0):
        raise RuntimeError("DB9 Fisher scale differs")
    return rows, users, head, mu, sd, sigma


def paths(r):
    stem = Path(r["source_member"]).stem
    return RESULTS / "DEV" / r["participant_id"] / (stem + ".npz"), TTA / r["participant_id"] / (stem + ".npz")


def load_base(r):
    p, _ = paths(r)
    receipt = json.loads(p.with_suffix(".json").read_text())
    if (receipt["input_sha256"] != r["sha256"] or receipt["output_sha256"] != sha(p) or
        receipt["plan_sha256"] != PARENT_PLAN_SHA or receipt["cohort_sha256"] != PARENT_COHORT_SHA or
        receipt["runner_sha256"] != PARENT_RUNNER_SHA):
        raise RuntimeError(f"Gate4C receipt differs: {p}")
    with np.load(p) as z:
        return {k: z[k] for k in z.files}


def tta_one(r, model, head, mu, sd, sigma):
    import h5py
    from src.common_pose.representation.canonical_hand import to_canonical16

    base, out = paths(r)
    receipt = out.with_suffix(".json")
    if out.exists() and receipt.exists():
        m = json.loads(receipt.read_text())
        if m.get("input_sha256") == r["sha256"] and m.get("output_sha256") == sha(out):
            return "SKIP"
    z = load_base(r)
    idx = z["block_index"].astype(np.int64)
    out.parent.mkdir(parents=True, exist_ok=True)
    if len(idx) == 0:
        views = np.empty((0, 4, 7), np.float32)
    else:
        source = Path(r["path"])
        if source.stat().st_size != r["size"] or sha(source) != r["sha256"]:
            raise RuntimeError("TTA source identity changed")
        with h5py.File(source) as h:
            emg = np.asarray(h["emg2pose"]["timeseries"]["emg"], dtype=np.float32)
        if emg.ndim != 2 or emg.shape[1] != 16:
            raise RuntimeError("TTA EMG shape changed")
        key = ("GATE4D_TTA_NOISE_V1|" + r["source_member"]).encode()
        seed = int.from_bytes(hashlib.sha256(key).digest()[:8], "little")
        rng = np.random.default_rng(seed)
        rms = float(np.sqrt(np.mean(emg.astype(np.float64) ** 2)))
        noise = rng.standard_normal(emg.shape, dtype=np.float32)
        inputs = (emg, emg * np.float32(.97), emg * np.float32(1.03),
                  emg + np.float32(.005 * rms) * noise)
        all_views = []
        for v in inputs:
            pred = model.predict(model._as_tensor(v))
            if pred.shape != (len(emg) - 1790, 20):
                raise RuntimeError("TTA model alignment changed")
            blocks = len(pred) // 40
            p20 = pred[:blocks * 40].reshape(blocks, 40, 20).mean(axis=1)
            pose8 = to_canonical16(p20, repo_root="/root/work/emg2pose")[:, TRUSTED_CANONICAL][idx]
            api8 = (pose8 - mu) / sd
            all_views.append(head.transform(api8).astype(np.float32))
        views = np.stack(all_views, axis=1)
        identity = head.transform(z["pred_api8"]).astype(np.float32)
        if not np.allclose(views[:, 0], identity, rtol=0, atol=1e-5):
            raise RuntimeError(f"TTA identity differs from Gate4C: {base}")
    tmp = out.with_name(out.name + f".{os.getpid()}.partial")
    with tmp.open("wb") as f:
        np.savez_compressed(f, fisher_views=views)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, out)
    receipt_tmp = receipt.with_name(receipt.name + f".{os.getpid()}.partial")
    receipt_tmp.write_text(json.dumps({"source_member": r["source_member"],
        "input_sha256": r["sha256"], "output_sha256": sha(out),
        "blocks": len(idx), "view_shape": list(views.shape)}, sort_keys=True) + "\n")
    os.replace(receipt_tmp, receipt)
    return "DONE"


def run_tta():
    rows, _, head, mu, sd, sigma = frozen()
    if sha(CKPT) != CKPT_SHA or sha(ADAPTER) != ADAPTER_SHA or sha(PREDICTOR) != PREDICTOR_SHA:
        raise RuntimeError("TTA frozen model/adapter changed")
    sys.path.insert(0, "/root/work/emg2pose_inference")
    sys.path.insert(0, "/root/work/emg2pose")
    sys.path.insert(0, str(ROOT))
    from predict_pose import PredictPose
    model = PredictPose(experiment="regression_vemg2pose", checkpoint=str(CKPT),
                        repo_root="/root/work/emg2pose", device="cuda")
    if model.left_context != 1790 or model.right_context != 0:
        raise RuntimeError("TTA model context changed")
    for i, r in enumerate(rows, 1):
        state = tta_one(r, model, head, mu, sd, sigma)
        print(f"TTA {i}/{len(rows)} {state} {r['source_member']}", flush=True)
    print(f"GATE4D_TTA_COMPLETE {len(rows)}/{len(rows)}", flush=True)


def margins(head, api):
    s = np.asarray(head.decision_function(api), dtype=np.float64)
    return np.partition(s, -2, axis=1)[:, -1] - np.partition(s, -2, axis=1)[:, -2]


def features(pose, fisher, side_right):
    n = len(pose)
    d1p = np.zeros_like(pose); d1f = np.zeros_like(fisher)
    d2p = np.zeros_like(pose); d2f = np.zeros_like(fisher)
    if n > 1:
        d1p[1:] = pose[1:] - pose[:-1]
        d1f[1:] = fisher[1:] - fisher[:-1]
    if n > 2:
        d2p[2:] = d1p[2:] - d1p[1:-1]
        d2f[2:] = d1f[2:] - d1f[1:-1]
    return np.column_stack((pose, fisher, d1p, d1f, d2p, d2f,
        np.full(n, float(side_right)), np.arange(n) > 0, np.arange(n) > 1)).astype(np.float32)


def corr(a, b):
    if len(a) < 2 or np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def q(a, p):
    return float(np.quantile(a, p)) if len(a) else None


def summary(vals):
    vals = [float(x) for x in vals if x is not None and np.isfinite(x)]
    return {"n": len(vals), "median": q(vals, .5), "q25": q(vals, .25),
            "q75": q(vals, .75), "minimum": min(vals) if vals else None,
            "maximum": max(vals) if vals else None}


def load_user(rows, head, sigma):
    parts = defaultdict(list)
    physical = []
    for file_i, r in enumerate(rows):
        z = load_base(r)
        n = len(z["block_index"])
        if n == 0:
            continue
        zg = head.transform(z["gt_api8"]).astype(np.float32)
        zp = head.transform(z["pred_api8"]).astype(np.float32)
        ef = np.linalg.norm((zp - zg) / sigma, axis=1)
        raw = np.linalg.norm(zp - zg, axis=1)
        mg, mp = margins(head, z["gt_api8"]), margins(head, z["pred_api8"])
        pg, pp = z["gt_pose8"].astype(np.float64), z["pred_pose8"].astype(np.float64)
        physical.append((pg, pp))
        parts["X"].append(features(pp, zp, r["hand"] == "right"))
        for key, value in (('ef',ef),('raw',raw),('zg',zg),('zp',zp),
                           ('margin',np.abs(mp-mg)),('margin_pred',mp),
                           ('tv',np.abs(z["proba_gt"]-z["proba_pred"]).sum(axis=1)/2),
                           ('entropy',-(z["proba_pred"]*np.log(np.maximum(z["proba_pred"],1e-12))).sum(axis=1)),
                           ('ygt',z["y_gt"]),('ypred',z["y_pred"]),
                           ('record',np.full(n,file_i,dtype=np.int32))):
            parts[key].append(value)
        tpath = paths(r)[1]
        receipt = json.loads(tpath.with_suffix(".json").read_text())
        if receipt["input_sha256"] != r["sha256"] or receipt["output_sha256"] != sha(tpath):
            raise RuntimeError("TTA receipt differs")
        with np.load(tpath) as t:
            views = t["fisher_views"].astype(np.float64)
        if views.shape != (n,4,7):
            raise RuntimeError("TTA shape differs")
        scaled = views / sigma
        centroid = scaled.mean(axis=1, keepdims=True)
        parts["tta"].append(((scaled-centroid)**2).sum(axis=2).mean(axis=1))
    u = {k: np.concatenate(v) for k,v in parts.items()}
    if not u or u["X"].shape[1] != 48:
        raise RuntimeError("empty or incorrect DEV features")
    gt, pred = map(lambda i: np.concatenate([x[i] for x in physical]), (0,1))
    dofs = []
    for j in range(8):
        a,b = gt[:,j],pred[:,j]
        ac,bc = a-a.mean(),b-b.mean()
        den = float(ac@ac)
        dofs.append({"dof":j,"bias":float((b-a).mean()),
                     "centered_slope_pred_on_gt":float((ac@bc)/den) if den>0 else None,
                     "centered_rmse":float(np.sqrt(np.mean((bc-ac)**2))),
                     "centered_correlation":corr(ac,bc)})
    return u, dofs


def fisher_corr(u, sel):
    zg,zp,rec = u["zg"][sel].astype(np.float64),u["zp"][sel].astype(np.float64),u["record"][sel]
    a,b = [],[]
    for k in np.unique(rec):
        m = rec == k
        if m.sum() < 2: continue
        a.append((zg[m]-zg[m].mean(axis=0)).ravel())
        b.append((zp[m]-zp[m].mean(axis=0)).ravel())
    return corr(np.concatenate(a),np.concatenate(b)) if a else None


def one_coverage(u, sel):
    yg,yp = u["ygt"][sel],u["ypred"][sel]
    balanced = [float(np.mean(yp[yg==k]==k)) for k in range(1,9) if np.sum(yg==k)>=30]
    return {"accepted_blocks":int(len(sel)),
            "fisher_error_median":q(u["ef"][sel],.5),
            "fisher_error_p90":q(u["ef"][sel],.9),
            "fisher_raw_l2_median":q(u["raw"][sel],.5),
            "fisher_trajectory_correlation":fisher_corr(u,sel),
            "margin_change_median":q(u["margin"][sel],.5),
            "probability_tv_median":q(u["tv"][sel],.5),
            "hard_preservation":float(np.mean(yg==yp)),
            "balanced_preservation":float(np.mean(balanced)) if balanced else None,
            "balanced_classes":len(balanced)}


def train_fold(users, data, fold):
    test=[u for i,u in enumerate(users) if i%5==fold]
    rest=sorted(set(users)-set(test))
    cal=[rest[(fold+4*i)%len(rest)] for i in range(3)]
    train=[u for u in rest if u not in cal]
    assert not (set(test)&set(cal) or set(test)&set(train) or set(cal)&set(train))
    xx,yy=[],[]
    for u in train:
        n=len(data[u]["ef"])
        idx=np.linspace(0,n-1,min(n,5000),dtype=np.int64)
        xx.append(data[u]["X"][idx]); yy.append(data[u]["ef"][idx])
    model=GradientBoostingRegressor(**MODEL_KWARGS)
    model.fit(np.concatenate(xx),np.concatenate(yy))
    cal_q=[]
    for u in cal:
        n=len(data[u]["ef"])
        idx=np.linspace(0,n-1,min(n,5000),dtype=np.int64)
        pred=model.predict(data[u]["X"][idx])
        cal_q.append(q(data[u]["ef"][idx]-pred,.9))
    offset=q(cal_q,.9)
    scores={u:model.predict(data[u]["X"])+offset for u in test}
    return test,{"fold":fold,"train_users":train,"calibration_users":cal,
                 "held_out_users":test,"training_blocks":int(sum(len(y) for y in yy)),
                 "grouped_empirical_calibration_offset":offset},scores


def run_analysis():
    rows, users, head, mu, sd, sigma=frozen()
    grouped=defaultdict(list)
    for r in rows: grouped[r["participant_id"]].append(r)
    data={}; physical={}
    for i,u in enumerate(users,1):
        data[u],physical[u]=load_user(grouped[u],head,sigma)
        print(f"LOAD_DEV_USER {i}/{len(users)} {u} {len(data[u]['ef'])}",flush=True)
    scores={"gate_a":{},"tta":{},"margin":{},"entropy":{}}
    folds=[]
    for f in range(5):
        test,info,s=train_fold(users,data,f)
        folds.append(info); scores["gate_a"].update(s)
        print(f"FIT_FOLD {f+1}/5 held_out={','.join(test)}",flush=True)
    for u in users:
        scores["tta"][u]=data[u]["tta"]
        scores["margin"][u]=-data[u]["margin_pred"]
        scores["entropy"][u]=data[u]["entropy"]
    risk=[]; ranks=[]; representations=[]
    for u in users:
        v=data[u]; n=len(v["ef"])
        full=one_coverage(v,np.arange(n))
        representations.append({"participant_id":u,**full})
        for gate in scores:
            s=np.asarray(scores[gate][u])
            if len(s)!=n or not np.isfinite(s).all():raise RuntimeError("gate score invalid")
            order=np.argsort(s,kind="stable")
            rho=float(spearmanr(s,v["ef"]).statistic) if np.std(s)>0 and np.std(v["ef"])>0 else None
            rows_gate=[]
            for cov in COVERAGES:
                k=max(1,math.ceil(cov*n))
                row={"participant_id":u,"gate":gate,"coverage":cov,**one_coverage(v,order[:k])}
                risk.append(row);rows_gate.append(row)
            med30=rows_gate[-1]["fisher_error_median"]
            ranks.append({"participant_id":u,"gate":gate,"spearman_score_vs_error":rho,
                          "full_median_eF":full["fisher_error_median"],
                          "accepted_30pct_median_eF":med30,
                          "accepted_30pct_p90_eF":rows_gate[-1]["fisher_error_p90"],
                          "median_improves_at_30pct":bool(med30<full["fisher_error_median"]),
                          "ranking_reversal":bool(rho is not None and rho<0)})
    aggs=[]
    for gate in scores:
        curve=[]
        for cov in COVERAGES:
            subset=[r for r in risk if r["gate"]==gate and r["coverage"]==cov]
            curve.append({"coverage":cov,"users":len(subset),
                          **{k:summary([r[k] for r in subset]) for k in
                             ("fisher_error_median","fisher_error_p90","probability_tv_median",
                              "hard_preservation","balanced_preservation","fisher_trajectory_correlation")}})
        auc=float(np.trapz([r["fisher_error_median"]["median"] for r in curve[::-1]],
                               [r["coverage"] for r in curve[::-1]]))
        aggs.append({"gate":gate,"curve":curve,"auc_median_fisher_risk":auc,
                     "spearman_user_summary":summary([r["spearman_score_vs_error"] for r in ranks if r["gate"]==gate]),
                     "users_improving_at_30pct":sum(r["median_improves_at_30pct"] for r in ranks if r["gate"]==gate)})
    save_json("DEV_USER_METRICS.json",{"schema":"gate4d-dev-users-v1","folds":folds,
                                      "users":representations})
    save_json("GATE_RISK_COVERAGE.json",{"schema":"gate4d-risk-coverage-v1","rows":risk,"aggregates":aggs})
    save_json("GATE_RANKING_METRICS.json",{"schema":"gate4d-rank-v1","rows":ranks})
    save_json("REPRESENTATION_PRESERVATION.json",{"schema":"gate4d-representation-v1","users":representations})
    save_json("PHYSICAL_ERROR_DIAGNOSTICS.json",{"schema":"gate4d-physical-v1","users":physical})
    best=min(aggs,key=lambda x:x["auc_median_fisher_risk"])
    save_json("ANALYSIS_SUMMARY.json",{"status":"DEV_BENCHMARK_COMPLETE","dev_users":19,
        "files":len(rows),"gates":list(scores),"best_auc_gate":best["gate"],
        "auc_by_gate":{a["gate"]:a["auc_median_fisher_risk"] for a in aggs},
        "plan_sha256":sha(LANE/"GATE4D_PLAN.md"),"validation_users_opened":0,
        "semantic_gesture_accuracy":"NOT_IDENTIFIABLE"})
    try:
        import matplotlib;matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plots=[("fisher_error_median","Fisher error (user median)","FISHER_RISK_COVERAGE.png"),
               ("probability_tv_median","Probability TV (user median)","TV_RISK_COVERAGE.png"),
               ("hard_preservation","Hard preservation (user median)","HARD_PRESERVATION_COVERAGE.png"),
               ("balanced_preservation","Balanced preservation (user median)","BALANCED_PRESERVATION_COVERAGE.png")]
        for field,ylabel,name in plots:
            fig,ax=plt.subplots(figsize=(5.4,3.7))
            for a in aggs:
                cc=a["curve"][::-1]
                ax.plot([x["coverage"] for x in cc],[x[field]["median"] for x in cc],marker="o",label=a["gate"])
            ax.set(xlabel="Accepted coverage",ylabel=ylabel);ax.legend();fig.tight_layout()
            fig.savefig(ART/name,dpi=150);plt.close(fig)
        fig,ax=plt.subplots(figsize=(7,4.4))
        matrix=np.array([[next(r["spearman_score_vs_error"] for r in ranks
                          if r["gate"]==g and r["participant_id"]==u)
                          for g in scores] for u in users],dtype=float)
        im=ax.imshow(matrix,aspect="auto",vmin=-1,vmax=1,cmap="coolwarm")
        ax.set_xticks(range(len(scores)),list(scores))
        ax.set_yticks(range(len(users)),users,fontsize=6)
        ax.set_title("Per-user gate risk ranking (Spearman)")
        fig.colorbar(im,ax=ax,label="rho")
        fig.tight_layout();fig.savefig(ART/"USER_GATE_RANKING.png",dpi=150);plt.close(fig)
    except ImportError:
        pass
    print("GATE4D_DEV_BENCHMARK_COMPLETE",flush=True)


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--tta",action="store_true")
    mode.add_argument("--analyze",action="store_true")
    args=parser.parse_args()
    run_tta() if args.tta else run_analysis()
