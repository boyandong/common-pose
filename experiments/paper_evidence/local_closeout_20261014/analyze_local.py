"""Standalone participant-level analysis of existing frozen primary tables."""
import argparse
import csv
import hashlib
import json
import platform
from pathlib import Path

import numpy as np

N_BOOT = 10000
SEED = 20261014
CONSUMERS = {
    ("db9_scoreonly_v3_20261011", "C1_primary"): "DB9 posture",
    ("db9_scoreonly_v3_20261011", "C2_primary"): "DB9 grasp",
    ("ceti_age_scoreonly_v3_20261012", "C1_primary"): "CeTI posture",
    ("ceti_age_scoreonly_v3_20261012", "C2_primary"): "CeTI grasp",
    ("show3d_scoreonly_v3_20261012", "C1_primary"): "SHOW instruction",
    ("kinmus_uji_scoreonly_v3_20261012", "C1_primary"): "KIN phase",
}
CONTRASTS = [("boundary", "full"), ("score_only", "full"),
             ("full_no_tta", "full"), ("score_only", "full_no_tta")]


def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""): h.update(b)
    return h.hexdigest()


def rows(p):
    with Path(p).open(encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f))


def table(p, data):
    assert data
    with Path(p).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0])); w.writeheader(); w.writerows(data)


def dump(p, value):
    Path(p).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+"\n", encoding="utf-8")


class Bootstrap:
    def __init__(self, out): self.cache = {}; self.out = out; self.manifest = []

    def interval(self, cohort, users, differences):
        if not users: return None, None, None, "UNDEFINED"
        key = f"{SEED}|{cohort}|" + "|".join(users)
        digest = hashlib.sha256(key.encode()).hexdigest()
        if digest not in self.cache:
            seed = int.from_bytes(bytes.fromhex(digest)[:8], "little")
            ix = np.random.default_rng(seed).integers(0, len(users), size=(N_BOOT, len(users)), dtype=np.int32)
            self.cache[digest] = ix
            np.save(self.out / "bootstrap_indices" / (digest+".npy"), ix, allow_pickle=False)
            self.manifest.append({"digest": digest, "cohort": cohort, "users": users, "seed": seed, "replicates": N_BOOT})
        x = np.asarray(differences, dtype=float)
        boot = np.median(x[self.cache[digest]], axis=1)
        lo, hi = np.quantile(boot, [.025, .975], method="linear")
        return float(np.median(x)), float(lo), float(hi), "LOW_SUPPORT" if len(users)<10 else "DESCRIPTIVE_POINTWISE"


def analyze(inp, out):
    out.mkdir(parents=True, exist_ok=False)
    (out / "bootstrap_indices").mkdir()
    bootstrap = Bootstrap(out)
    estimates = []; paired = []; sensitivities = []; plot_rows = []; bounds = []; fixed_rows = []; support_rows = []
    for cohort, n in [("N80", 80), ("A20", 20)]:
        data = rows(inp / (cohort+"_USER_COVERAGE_SERVICE.csv"))
        lookup = {(r["lane"], r["condition"], r["user"], r["goal"], r["method"], r["mode"], r["nominal_retention"]): r for r in data}
        assert len(lookup) == len(data)
        for r in data:
            p, m, a = (int(r[k]) for k in ["accepted_paired_n", "accepted_GT_missing_n", "accepted_runtime_n"])
            assert p+m == a and p <= int(r["paired_n"]) and a <= int(r["runtime_n"])
            if p:
                f = round(float(r["U"])*p)
                assert abs(float(r["U"])*p-f) < 1e-6
            else:
                assert not r["U"]; f = 0
            bounds.append({"cohort": cohort, "consumer": CONSUMERS[(r["lane"],r["condition"])],
                "user": r["user"], "goal":r["goal"], "method":r["method"], "mode":r["mode"],
                "retention":r["nominal_retention"], "accepted_n":a, "paired_n":p, "missing_n":m,
                "observed_flips":f, "paired_U": r["U"], "lower_all_inputs":f/a if a else None,
                "upper_all_inputs":(f+m)/a if a else None, "missing_fraction":m/a if a else None,
                "actual_missing_reference_risk":"UNKNOWN"})
        for (lane, condition), name in CONSUMERS.items():
            users = sorted({r["user"] for r in data if r["lane"]==lane and r["condition"]==condition})
            assert len(users)==n
            for goal in ["U", "B"]:
                for method in ["all", "boundary", "score_only", "full_no_tta", "full"]:
                    rr=[lookup[(lane,condition,u,goal,method,"deployment","")] for u in users]
                    fixed_rows.append({"cohort":cohort,"consumer":name,"goal":goal,"method":method,"users":n,
                        "U_median":float(np.median([float(r['U']) for r in rr if r['U']])),
                        "B_median":float(np.median([float(r['B']) for r in rr if r['B']])) if any(r['B'] for r in rr) else None,
                        "B_evaluable":sum(bool(r['B']) for r in rr),
                        "coverage_median":float(np.median([float(r['runtime_coverage']) for r in rr])),
                        "U_le_0_10_users":sum(bool(r['U']) and float(r['U'])<=.1 for r in rr),
                        "B_le_0_10_users":sum(bool(r['B']) and float(r['B'])<=.1 for r in rr),
                        "coverage_ge_0_10_users":sum(float(r['runtime_coverage'])>=.1 for r in rr),
                        "protocol":"existing_whole_record_fixed_threshold_not_causal_deployment"})
            for retention in ["0.1", "0.3", "0.5", "0.7"]:
                methods={m:[lookup[(lane,condition,u,"U",m,"offline_equal_coverage",retention)] for u in users]
                         for m in ["boundary","score_only","full_no_tta","full"]}
                for a,b in CONTRASTS:
                    for metric in ["U","B"]:
                        valid=[j for j,(ra,rb) in enumerate(zip(methods[a],methods[b])) if ra[metric] and rb[metric]]
                        ids=[users[j] for j in valid]
                        diff=[100*(float(methods[a][j][metric])-float(methods[b][j][metric])) for j in valid]
                        md,lo,hi,status=bootstrap.interval(cohort,ids,diff)
                        est={"cohort":cohort,"consumer":name,"retention":retention,"A":a,"B_method":b,"metric":metric,
                            "users":len(ids),"median_reduction_pp":md,"CI95_low_pp":lo,"CI95_high_pp":hi,"status":status,
                            "primary_budget":retention=="0.3","positive_favors":b}
                        estimates.append(est)
                        paired.extend({**{k:est[k] for k in ['cohort','consumer','retention','A','B_method','metric']},
                            "user":u,"difference_pp":v} for u,v in zip(ids,diff))
                        if retention=="0.3" and a=="boundary" and b=="full": plot_rows.append(est)
                aa,bb=methods["boundary"],methods["full"]
                joint=[j for j,(ra,rb) in enumerate(zip(aa,bb)) if ra['B'] and rb['B']]
                ids=[users[j] for j in joint]
                ud=[100*(float(aa[j]['U'])-float(bb[j]['U'])) for j in joint]
                bd=[100*(float(aa[j]['B'])-float(bb[j]['B'])) for j in joint]
                um,ul,uh,st=bootstrap.interval(cohort,ids,ud);bm,bl,bh,_=bootstrap.interval(cohort,ids,bd)
                full_u=float(np.median([100*(float(a['U'])-float(b['U'])) for a,b in zip(aa,bb)]))
                sensitivities.append({"cohort":cohort,"consumer":name,"retention":retention,"joint_users":len(ids),
                    "full_cohort_users":n,"full_cohort_U_pp":full_u,"joint_U_pp":um,"joint_U_low_pp":ul,"joint_U_high_pp":uh,
                    "joint_B_pp":bm,"joint_B_low_pp":bl,"joint_B_high_pp":bh,"status":st,
                    "opposite_U_B_median_direction":um is not None and bm is not None and um*bm<0})
                for m,rr in methods.items():
                    support_rows.append({"cohort":cohort,"consumer":name,"retention":retention,"method":m,
                        "B_evaluable":sum(bool(r['B']) for r in rr),"users":n})
            allrows=[lookup[(lane,condition,u,"U","all","deployment","")] for u in users]
            support_rows.append({"cohort":cohort,"consumer":name,"retention":"1.0","method":"all",
                "B_evaluable":sum(bool(r['B']) for r in allrows),"users":n})
        print("COHORT_ANALYSIS_COMPLETE",cohort,flush=True)
    table(out/'PAIRED_INTERVALS_ALL_BUDGETS.csv',estimates)
    table(out/'PRIMARY_PAIRED_INTERVALS.csv',[r for r in estimates if r['retention']=='0.3' and (r['A'],r['B_method']) in CONTRASTS[:2]])
    table(out/'EXISTING_MATCHED_FEATURE_CONTRASTS.csv',[r for r in estimates if (r['A'],r['B_method']) in CONTRASTS[2:]])
    table(out/'PARTICIPANT_PAIRED_DIFFERENCES.csv',paired)
    table(out/'JOINT_SUPPORT_SENSITIVITY.csv',sensitivities)
    table(out/'MISSING_REFERENCE_BOUNDS.csv',bounds)
    table(out/'FIXED_THRESHOLD_EVALUATION.csv',fixed_rows)
    table(out/'REFERENCE_SUPPORT.csv',support_rows)
    table(out/'MAIN_FIGURE_DATA.csv',plot_rows)
    grouped={}
    for r in bounds:
        key=tuple(r[k] for k in ['cohort','consumer','goal','method','mode','retention']);grouped.setdefault(key,[]).append(r)
    bs=[]
    for key, rr in grouped.items():
        bs.append({**dict(zip(['cohort','consumer','goal','method','mode','retention'],key)),"users":len(rr),
            "median_lower_all_inputs":float(np.median([r['lower_all_inputs'] for r in rr if r['accepted_n']])),
            "median_upper_all_inputs":float(np.median([r['upper_all_inputs'] for r in rr if r['accepted_n']])),
            "median_missing_fraction":float(np.median([r['missing_fraction'] for r in rr if r['accepted_n']]))})
    table(out/'MISSING_REFERENCE_BOUND_SUMMARY.csv',bs)
    dump(out/'BOOTSTRAP_MANIFEST.json',bootstrap.manifest)
    dump(out/'ANALYSIS_RECEIPT.json',{"status":"COMPLETE_EXPLORATORY_LOCAL_ANALYSIS","bootstrap_replicates":N_BOOT,"seed":SEED,
        "numpy":np.__version__,"python":platform.python_version(),"interval_rows":len(estimates),"paired_rows":len(paired),
        "missing_bound_rows":len(bounds),"fixed_threshold_rows":len(fixed_rows),"source_tables":{p.name:sha(p) for p in inp.glob('*_USER_COVERAGE_SERVICE.csv')},
        "no_refit_no_new_inference":True,"no_independent_confirmation_claim":True})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();analyze(a.input,a.output)
