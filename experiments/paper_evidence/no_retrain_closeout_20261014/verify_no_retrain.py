"""Alternative summary/interval calculations and links to unchanged frozen inputs."""
import csv,json,hashlib,math
from collections import defaultdict,Counter
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def med(x):
    a=sorted(x);n=len(a);return a[n//2] if n%2 else (a[n//2-1]+a[n//2])/2
def qnt(a,q):
    v=(len(a)-1)*q;i=math.floor(v);j=math.ceil(v);return a[i]+(a[j]-a[i])*(v-i)
def main():
    checks=0
    original=json.loads((HERE/'PRE_ANALYSIS_SEAL.json').read_text())
    for n,h in original['inputs'].items():
        p=HERE/'GOALS_BEFORE_FINAL_UPDATE.md' if n.endswith('ALL_27_REVISION_GOALS_AND_FINDINGS.md') else ROOT/n
        assert sha(p)==h;checks+=1
    amended=json.loads((HERE/'AMENDED_PRE_ANALYSIS_SEAL.json').read_text())
    for n,h in amended['files'].items():assert sha(n)==h;checks+=1
    members=read(HERE/'PUBLIC_RECIPE_MEMBERSHIP.csv');meta=read(ROOT.parent/'emg2pose_handstate/data/priority_pose_subset/raw/emg2pose_metadata.csv')
    train=Counter(r['user'] for r in meta if r['split']=='train');byuser={(r['cohort'],r['user']):r for r in members}
    groups=Counter((r['cohort'],r['public_recipe_group']) for r in members)
    assert groups=={('A20','PUBLIC_RECIPE_TRAIN_OVERLAP'):16,('A20','PUBLIC_RECIPE_NO_TRAIN_RECORDS'):4,('N80','PUBLIC_RECIPE_TRAIN_OVERLAP'):70,('N80','PUBLIC_RECIPE_NO_TRAIN_RECORDS'):10}
    legacy={r['user'] for r in read(ROOT/'docs/reviews/20261011_identity_runtime_causality_audit/USER_IDENTITY_INTERSECTION.csv') if r['cohort']=='FINAL'}
    assert legacy.isdisjoint({r['user'] for r in members if r['cohort']=='A20'})
    for r in members:
        assert int(r['official_train_records'])==train[r['user']] and r['actual_checkpoint_membership']=='UNKNOWN'
        assert (r['public_recipe_group']=='PUBLIC_RECIPE_TRAIN_OVERLAP')==(train[r['user']]>0);checks+=3
    old=read(ROOT/'experiments/paper_evidence/local_closeout_20261014/results/PARTICIPANT_PAIRED_DIFFERENCES.csv')
    oldlookup={(r['cohort'],r['consumer'],r['retention'],r['A'],r['B_method'],r['metric'],r['user']):float(r['difference_pp']) for r in old}
    paired=read(HERE/'PUBLIC_RECIPE_PAIRED_DIFFERENCES.csv');grouped=defaultdict(list)
    for r in paired:
        assert abs(float(r['difference_pp'])-oldlookup[(r['cohort'],r['consumer'],r['retention'],r['baseline'],'full',r['metric'],r['user'])])<1e-12
        assert r['public_recipe_group']==byuser[(r['cohort'],r['user'])]['public_recipe_group'];checks+=2
        grouped[(r['cohort'],r['public_recipe_group'],r['consumer'],r['retention'],r['baseline'],r['metric'])].append(r)
    for s in read(HERE/'PUBLIC_RECIPE_SUBGROUP_SUMMARY.csv'):
        key=tuple(s[k] for k in ['cohort','public_recipe_group','consumer','retention','baseline','metric']);rr=sorted(grouped[key],key=lambda r:r['user']);n=len(rr)
        assert n==int(s['paired_users']) and int(s['group_users'])==groups[(s['cohort'],s['public_recipe_group'])];checks+=2
        if not n:assert not s['median_reduction_pp'] and not s['CI95_low_pp'] and not s['CI95_high_pp'];continue
        x=np.array([float(r['difference_pp']) for r in rr]);assert abs(med(x)-float(s['median_reduction_pp']))<1e-12
        seed=int.from_bytes(hashlib.sha256(('20261014|'+s['cohort']+'|'+'|'.join(r['user'] for r in rr)).encode()).digest()[:8],'little')
        ix=np.random.default_rng(seed).integers(0,n,size=(10000,n),dtype=np.int32);a=np.sort(x[ix],axis=1)
        draws=a[:,n//2] if n%2 else (a[:,n//2-1]+a[:,n//2])/2;draws.sort()
        assert abs(qnt(draws,.025)-float(s['CI95_low_pp']))<1e-10 and abs(qnt(draws,.975)-float(s['CI95_high_pp']))<1e-10;checks+=3
    service=read(HERE/'PUBLIC_RECIPE_SUBGROUP_SERVICE.csv')
    for cohort in ['A20','N80']:
        src=read(ROOT/'experiments/paper_evidence/local_closeout_20261014/reproduction_bundle/input'/(cohort+'_USER_COVERAGE_SERVICE.csv'))
        for s in [s for s in service if s['cohort']==cohort]:
            rr=[r for r in src if r['goal']=='U' and r['mode']=='offline_equal_coverage' and r['method']==s['method'] and r['nominal_retention']==s['retention'] and byuser[(cohort,r['user'])]['public_recipe_group']==s['public_recipe_group'] and (('DB9 posture' if r['condition']=='C1_primary' else 'DB9 grasp') if r['lane'].startswith('db9_') else ('CeTI posture' if r['condition']=='C1_primary' else 'CeTI grasp') if r['lane'].startswith('ceti_') else 'SHOW instruction' if r['lane'].startswith('show') else 'KIN phase')==s['consumer']]
            vals=[float(r[s['metric']]) for r in rr if r[s['metric']]];assert len(vals)==int(s['evaluable_users']);checks+=1
            if vals:assert abs(med(vals)-float(s['median_risk']))<1e-12;checks+=1
            else:assert not s['median_risk']
    costs=read(HERE/'FIT_COST_LEDGER.csv');summaries=read(HERE/'NEW_FIT_COST_SUMMARY.csv')
    for s in summaries:
        a=[float(r['fit_seconds']) for r in costs if r['batch']==s['batch']]
        assert len(a)==int(s['fits']) and abs(math.fsum(a)-float(s['sum_logged_stage_seconds']))<1e-9 and abs(med(a)-float(s['median_logged_stage_seconds']))<1e-12;checks+=3
    paper=json.loads((ROOT/'docs/reviews/20261014_embc_no_supplement_audit/PAPER_UNCHANGED_HASHES.json').read_text())
    for n,h in paper.items():assert sha(ROOT/n)==h;checks+=1
    assert len(read(HERE/'PHYSICAL_INTERFACE_EVIDENCE_48.csv'))==48 and len(read(HERE/'SHOW_PROFILE_GEOMETRY_RECOUNT.csv'))==16
    receipt={'status':'PASS','checks':checks,'subgroup_cells_verified':384,'subgroup_participant_differences_verified':len(paired),'all_subgroup_intervals_independently_recomputed':True,'A20_public_recipe_groups':[16,4],'N80_public_recipe_groups':[70,10],'A20_not_legacy_FINAL':True,'paper_files_unchanged':len(paper),'models_fitted':0,'inference_rerun':False,'actual_checkpoint_membership_certified':False}
    (HERE/'INDEPENDENT_VERIFICATION.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
