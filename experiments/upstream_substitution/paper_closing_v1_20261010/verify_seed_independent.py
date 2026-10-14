"""Independent raw-cache verification of all seed risks/support/effects/summaries.

Does not import the producer's metric, ordering, tie or statistic functions.
Uses only frozen FINAL instances and already persisted DEV refit instances;
never fits any model. Numerical threads must match the frozen runtime.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import joblib
import numpy as np
from threadpoolctl import threadpool_info

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
SRC=BASE/'paper_supplement_v1_20261009'
SEEDS=list(range(20261009,20261029))
METHODS=['full','class_empirical','class_model']

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()

def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def number(s):return None if s=='' else float(s)

def same(a,b):
    assert (a is None)==(b is None),(a,b)
    if a is not None:assert abs(a-b)<1e-12,(a,b)

def empirical(names,data):
    rates=[]
    for k in range(1,9):
        vals=[]
        for u in names:
            take=data[u]['ypred']==k
            if take.sum():vals.append((float(data[u]['flip'][take].sum())+.5)/(int(take.sum())+1))
        rates.append(float(np.mean(vals)) if vals else .5)
    return np.asarray(rates)

def statistic(vals):
    a=np.asarray([x for x in vals if x is not None],float)
    out={'n':len(a),'n_missing':len(vals)-len(a),'median':float(np.median(a)) if len(a) else None}
    if not len(a):return out
    q=np.quantile(a,[.25,.75]);rng=np.random.default_rng(20261009)
    boot=np.median(a[rng.integers(0,len(a),size=(20000,len(a)))],axis=1)
    pos=int((a>0).sum());zero=int((a==0).sum());n=len(a)-zero
    k=min(pos,n-pos)
    # Independent exact two-sided binomial calculation at symmetric p=.5.
    p=min(1.,2*sum(math.comb(n,j) for j in range(k+1))/2**n) if n and out['n_missing']==0 else None
    out.update(q25=float(q[0]),q75=float(q[1]),min=float(a.min()),max=float(a.max()),
               ci95=np.quantile(boot,[.025,.975]).tolist(),positive_users=pos,zero_users=zero,sign_p_two_sided=p)
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--attempt',required=True,type=Path)
    args=ap.parse_args();out=args.attempt/'seed_results'
    assert not (args.attempt/'INDEPENDENT_VERIFICATION.json').exists()
    for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:assert os.environ.get(k)=='8'
    manifest=json.loads((out/'RUN_MANIFEST.json').read_text());assert manifest['status']=='COMPLETE'
    for name,value in manifest['files'].items():assert sha(out/name)==value,name
    sr=rows(out/'SEED_USER_RISKS.csv');cr=rows(out/'SEED_CLASS_SUPPORT.csv');er=rows(out/'SEED_PAIRED_EFFECTS.csv')
    ir=rows(out/'SEED_SUPPORT_INTERSECTIONS_DIAGNOSTIC.csv')
    assert (len(sr),len(cr),len(er),len(ir))==(4680,37440,3120,1560)
    def key(r):return r['split'],r['contract'],r['user'],int(r['seed']),r['method']
    sm={key(r):r for r in sr};cm={(*key(r),int(r['class'])):r for r in cr}
    em={(r['split'],r['contract'],r['user'],int(r['seed']),r['comparison']):r for r in er}
    im={(r['split'],r['contract'],r['user'],int(r['seed'])):r for r in ir}
    assert len(sm)==len(sr) and len(cm)==len(cr) and len(em)==len(er) and len(im)==len(ir)
    receipt=json.loads((HERE/'REMOTE_CACHE_VERIFICATION.json').read_text());data={};users={}
    for r in receipt['features']:
        p=SRC/'features'/r['split']/(r['user']+'.npz');assert sha(p)==r['sha256']
        with np.load(p) as z:data[r['user']]={k:z[k] for k in z.files}
        users.setdefault(r['split'],[]).append(r['user'])
    frozen=json.loads((SRC/'comparative_analysis/SUMMARY.json').read_text())['summary']
    lineage=json.loads((out/'SCORE_LINEAGE.json').read_text())
    assert lineage['canonical_max_abs_risk_difference']==0
    scores={}
    for c,lane in [('U','gate4e_customer_flip_gate_v1'),('B','gate4f_class_balanced_flip_gate_v1')]:
        p=BASE/lane/'artifacts/FINAL_GATE_MODEL.joblib'
        inst=json.loads((p.parent/'FINAL_GATE_INSTANCE.json').read_text());assert sha(p)==inst['model_sha256']
        full=joblib.load(p);full=full if c=='U' else full['model']
        p=SRC/'comparative_analysis'/f'{c}_class_model_DEV_ONLY.joblib'
        assert sha(p)==p.with_suffix('.sha256').read_text().split()[0];model=joblib.load(p)
        rates=np.asarray(json.loads((SRC/'comparative_analysis'/f'{c}_SUPPLEMENT_INSTANCE.json').read_text())['class_empirical_rates'])
        for u in users['FINAL']:
            v=data[u];scores['FINAL',c,u]={'full':full.predict_proba(v['x'])[:,1],
                'class_model':model.predict_proba(v['x'][:,:8])[:,1],'class_empirical':rates[v['ypred']-1]}
        lr=[r for r in lineage['rows'] if r['split']=='DEV' and r['contract']==c]
        for fold in range(5):
            rr={r['method']:r for r in lr if r['fold']==fold};assert set(rr)=={'full','class_model'}
            models={m:joblib.load(out/f'{c}_fold{fold}_{m}.joblib') for m in rr}
            for m,r in rr.items():assert sha(out/f'{c}_fold{fold}_{m}.joblib')==r['model_sha256']
            train=rr['full']['train'];test=rr['full']['test'];cal=rr['full']['calibration']
            assert not(set(train)&set(test) or set(train)&set(cal) or set(cal)&set(test))
            assert not(set(train+test+cal)&set(users['FINAL']))
            rates=empirical(train,data)
            for u in test:
                v=data[u];scores['DEV',c,u]={'full':models['full'].predict_proba(v['x'])[:,1],
                    'class_model':models['class_model'].predict_proba(v['x'][:,:8])[:,1],
                    'class_empirical':rates[v['ypred']-1]}
    original={(r['split'],r['contract'],r['user'],r['method']):r for r in rows(SRC/'comparative_analysis/RISK_COVERAGE_ROWS.csv') if float(r['nominal_coverage'])==.3}
    derived_effects={};maxdiff=0.;canonical_checks=0
    for split in ['DEV','FINAL']:
        for u in sorted(users[split]):
            v=data[u];n=len(v['flip']);take=math.ceil(.3*n)
            baseline=np.bincount(v['ygt'],minlength=9)[1:]>=30
            for seed in SEEDS:
                tie=np.array([int(hashlib.sha256(f'{seed}|{split}|{u}|{i}'.encode()).hexdigest()[:16],16) for i in range(n)],dtype=np.uint64)
                for c in ['U','B']:
                    common=frozen[c+'_'+split]['common_reference_class_sets'][u];values={};sets=[]
                    for m in METHODS:
                        s=scores[split,c,u][m];idx=np.lexsort((tie,s))[:take]
                        support=np.bincount(v['ygt'][idx],minlength=9)[1:]
                        flips=np.bincount(v['ygt'][idx],weights=v['flip'][idx],minlength=9)[1:]
                        risk=[float(flips[k]/support[k]) if support[k] else None for k in range(8)]
                        ordinary=float(v['flip'][idx].sum()/take)
                        fixed=float(np.mean([risk[k-1] for k in common])) if common and all(risk[k-1] is not None for k in common) else None
                        dynamic=float(np.mean([risk[k] for k in range(8) if support[k]>=30])) if np.any(support>=30) else None
                        values[m]=ordinary if c=='U' else fixed
                        r=sm[split,c,u,seed,m];assert int(r['accepted'])==take
                        same(ordinary,number(r['ordinary_risk']));same(fixed,number(r['fixed_common_risk']))
                        if seed==20261009:
                            ref=original[split,c,u,m];assert int(ref['accepted'])==take
                            for metric,val in [('ordinary_risk',ordinary),('fixed_common_risk',fixed),('dynamic_balanced_risk',dynamic)]:
                                expected=number(ref[metric]);same(val,expected);canonical_checks+=1
                                if val is not None:maxdiff=max(maxdiff,abs(val-expected))
                        def joined(ks):return '|'.join(map(str,ks))
                        assert r['frozen_common_classes']==joined(common)
                        assert r['sparse_frozen_classes']==joined(k for k in common if support[k-1]<30)
                        assert r['missing_frozen_classes']==joined(k for k in common if support[k-1]==0)
                        served={k+1 for k in range(8) if support[k]>=30};sets.append(served)
                        assert r['supported_classes_at_seed']==joined(sorted(served))
                        obs=[risk[k] for k in range(8) if baseline[k] and risk[k] is not None]
                        missing=sum(baseline[k] and risk[k] is None for k in range(8));den=int(baseline.sum())
                        same(float(sum(obs)/den) if den else None,number(r['baseline_set_risk_lower']))
                        same(float((sum(obs)+missing)/den) if den else None,number(r['baseline_set_risk_upper']))
                        for k in range(1,9):
                            q=cm[split,c,u,seed,m,k];assert int(q['accepted_support'])==support[k-1]
                            same(risk[k-1],number(q['accepted_risk']))
                            assert (q['in_frozen_common_set']=='True')==(k in common)
                            assert (q['supported']=='True')==(support[k-1]>=30)
                    assert im[split,c,u,seed]['three_method_supported_intersection']==joined(sorted(set.intersection(*sets)))
                    for m in METHODS[1:]:
                        val=None if values[m] is None or values['full'] is None else values[m]-values['full']
                        r=em[split,c,u,seed,'full_vs_'+m];same(val,number(r['effect']))
                        assert r['metric']==('ordinary_risk' if c=='U' else 'fixed_common_risk')
                        derived_effects[split,c,u,seed,m]=val
            print('INDEPENDENT_USER_VERIFIED',split,u,flush=True)
    summ=json.loads((out/'SUMMARY.json').read_text());assert summ['seeds']==SEEDS and summ['status']=='COMPLETE'
    groups=0
    for split in ['DEV','FINAL']:
        for c in ['U','B']:
            for m in METHODS[1:]:
                s=summ['summary'][f'{split}_{c}__full_vs_{m}'];stats=[]
                for rr in s['per_seed']:
                    seed=rr['seed'];st=statistic([derived_effects[split,c,u,seed,m] for u in sorted(users[split])]);stats.append(st)
                    for k,val in st.items():
                        if isinstance(val,list):
                            for a,b in zip(val,rr[k]):same(a,b)
                        else:same(val,rr[k])
                    groups+=1
                valid=[r for r in stats if r['median'] is not None]
                for key,field in [('median_effect_range','median'),('positive_user_count_range','positive_users')]:
                    expected=[min(r[field] for r in valid),max(r[field] for r in valid)] if valid else None
                    assert s[key]==expected
                assert s['complete_cohort_seeds']==sum(r['n_missing']==0 for r in stats)
                assert s['ci_lower_above_zero_seeds']==sum(r.get('ci95') is not None and r['ci95'][0]>0 for r in valid)
    result={'status':'PASS','user_risks':len(sr),'class_support_rows':len(cr),'paired_effects':len(er),
            'support_intersections':len(ir),'summary_groups':groups,'canonical_checks':canonical_checks,
            'canonical_max_abs_difference':maxdiff,'cache_files_verified':len(data),'result_manifest_sha256':sha(out/'RUN_MANIFEST.json'),
            'verifier_sha256':sha(Path(__file__)),'threadpools':threadpool_info(),
            'scope':'independent raw-cache rescore, SHA256 tie sorting, all support/risk/effect rows, frozen sets, original canonical admission, 160 conditional user bootstraps; no fitting'}
    (args.attempt/'INDEPENDENT_VERIFICATION.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)

if __name__=='__main__':main()
