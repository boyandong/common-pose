"""Independent cached/model scoring, support, risk and statistics verification.

Reuse arithmetic from the sealed independent primary verifier, never the
supplement producer's ranking, statistics, scoring or measurement functions.
"""
import csv
import hashlib
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import joblib
import numpy as np
from runtime_common import LANE,BASE,DATA,read,save,sha,frozen,load_module

HERE=Path(__file__).resolve().parent
COVERAGES=[.3,.5,.6,.7,.8,.9,1.]
SEEDS=list(range(20261009,20261029))

def rows(name):
    with (HERE/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def number(v):return None if v in ['',None] else float(v)

def same(a,b):
    assert (a is None)==(b is None),(a,b)
    if a is not None:assert abs(a-b)<1e-12,(a,b)

def describe(values):
    valid=np.asarray([x for x in values if x is not None],float);pos=int(sum(valid>0));neg=int(sum(valid<0));zero=int(sum(valid==0));n=pos+neg
    p=min(1.,2*sum(math.comb(n,k) for k in range(min(pos,neg)+1))/(2**n)) if n else 1.
    if len(valid):
        rng=np.random.default_rng(20261009);distribution=np.median(valid[rng.integers(0,len(valid),(20000,len(valid)))],axis=1)
        center=float(np.median(valid));interval=np.quantile(distribution,[.025,.975]).tolist()
    else:center=None;interval=None
    return {'enrolled':len(values),'complete_pairs':len(valid),'missing_pairs':len(values)-len(valid),'positive':pos,'negative':neg,'zero':zero,'n_nonzero':n,
            'median':center,'descriptive_ci95':interval,'descriptive_sign_p':p if len(valid)==len(values) else None,'conditional_subset_sign_p':p if len(valid)!=len(values) else None}

def verify_summary(actual,expected):
    for k in ['enrolled','complete_pairs','missing_pairs','positive','zero','negative','n_nonzero']:assert actual[k]==expected[k],k
    for k in ['median','descriptive_sign_p','conditional_subset_sign_p']:same(actual[k],expected[k])
    assert (actual['descriptive_ci95'] is None)==(expected['descriptive_ci95'] is None)
    if expected['descriptive_ci95'] is not None:
        for a,b in zip(actual['descriptive_ci95'],expected['descriptive_ci95']):same(a,b)
    assert actual['inferential_status']=='SECONDARY_DESCRIPTIVE_NO_NEW_CONFIRMATORY_DECISION'

def main():
    cohort=frozen(numeric=True);seal=read(HERE/'CODE_SEAL.json')
    for n,h in seal['files'].items():assert sha(HERE/n)==h,n
    original_code=read(LANE/'ANALYSIS_CODE_SEAL.json')
    assert sha(LANE/'verify_new_results.py')==original_code['files']['verify_new_results.py']
    independent=load_module('sealed_independent_primary_arithmetic',LANE/'verify_new_results.py')
    primary=read(LANE/'INDEPENDENT_RESULT_VERIFICATION.json');assert primary['status']=='PASS' and primary['result_sha256']==sha(LANE/'PRIMARY_RESULT.json')
    manifest=read(HERE/'RESULT_MANIFEST.json')
    assert manifest['secondary_result_sha256']==sha(HERE/'SECONDARY_RESULT.json')
    for n,h in manifest['files'].items():assert sha(HERE/n)==h,n
    support=read(HERE/'SUPPORT_SEAL.json');assert support['status']=='FROZEN_WITHOUT_FLIP' and not support['flip_read']
    assert support['original_common_sets_sha256']==sha(LANE/'COMMON_CLASS_SETS.json') and not support['original_sets_changed']
    assert support['score_manifest_sha256']==sha(HERE/'SCORE_CACHE_MANIFEST.json') and support['support_rows_sha256']==sha(HERE/'CANONICAL_SUPPORT_ROWS.csv')
    result=read(HERE/'SECONDARY_RESULT.json');assert not result['new_confirmatory_primary'] and not result['original_primary_changed'] and not result['common_sets_changed']
    registration=read(HERE/'MODEL_REGISTRATION.json');sets=read(LANE/'COMMON_CLASS_SETS.json')['contract_user_sets'];scores_meta=read(HERE/'SCORE_CACHE_MANIFEST.json')['files']
    risk=rows('RISK_COVERAGE_ROWS.csv');classes=rows('CLASSWISE_ROWS.csv');seeds=rows('SEED_RISK_ROWS.csv');effects=rows('SEED_EFFECTS.csv');canonical=rows('SCORE_ONLY_USER_EFFECTS.csv')
    deployment=rows('DEPLOYMENT_ROWS.csv');within=rows('WITHIN_PREDICTED_CLASS_ROWS.csv');supportrows=rows('CANONICAL_SUPPORT_ROWS.csv')
    ri={(r['contract'],r['user'],r['method'],float(r['nominal_coverage'])):r for r in risk};ci={(r['contract'],r['user'],r['method'],float(r['nominal_coverage']),int(r['class'])):r for r in classes}
    si={(r['contract'],r['user'],r['method'],int(r['seed'])):r for r in seeds};ei={(r['contract'],r['user'],int(r['seed'])):r for r in effects}
    cai={(r['contract'],r['user']):r for r in canonical};di={(r['contract'],r['user'],r['method']):r for r in deployment};wi={(r['contract'],r['user'],r['method']):r for r in within}
    sui={(r['contract'],r['user'],r['method'],int(r['class'])):r for r in supportrows}
    assert len(ri)==len(risk)==2240 and len(ci)==len(classes)==17920
    assert len(si)==len(seeds)==6400 and len(ei)==len(effects)==3200 and len(cai)==len(canonical)==160
    assert len(di)==len(deployment)==320 and len(wi)==len(within)==320 and len(sui)==len(supportrows)==2560
    values={};vector_checks=0
    for contract,entry in registration['models'].items():
        mp=HERE/entry['model'];ip=HERE/entry['instance'];assert sha(mp)==entry['model_sha256'] and sha(ip)==entry['instance_sha256']
        instance=read(ip);assert instance['columns']==list(range(19)) and not set(cohort['enrolled_users']).intersection(instance['train']+instance['calibration'])
        model=joblib.load(mp);assert model.n_features_in_==19
        fullpath=BASE/('gate4e_customer_flip_gate_v1' if contract=='U' else 'gate4f_class_balanced_flip_gate_v1')/'artifacts/FINAL_GATE_MODEL.joblib'
        fullmodel=joblib.load(fullpath);fullmodel=fullmodel if contract=='U' else fullmodel['model']
        fullthreshold=read(BASE/'paper_supplement_v1_20261009/comparative_analysis'/f'{contract}_SUPPLEMENT_INSTANCE.json')['thresholds_at_nominal_30']['full']
        metric='ordinary_risk' if contract=='U' else 'fixed_common_risk'
        for user in sorted(cohort['enrolled_users']):
            fp=DATA/'features/FINAL'/(user+'.npz');assert sha(fp)==read(fp.with_suffix('.json'))['sha256'];meta=scores_meta[contract+'|'+user]
            assert meta['feature_sha256']==sha(fp) and sha(Path(meta['path']))==meta['sha256']
            with np.load(fp) as z:v={k:z[k] for k in ['x','ygt','ypred','flip']}
            assert np.array_equal((v['ygt']!=v['ypred']).astype(v['flip'].dtype),v['flip'])
            with np.load(meta['path']) as z:scores={m:z[m] for m in ['score_only','full']}
            for method,calculated in [('score_only',model.predict_proba(v['x'][:,:19])[:,1]),('full',fullmodel.predict_proba(v['x'])[:,1])]:
                assert np.array_equal(calculated,scores[method]),(contract,user,method);vector_checks+=1
            n=len(v['flip']);common=sets[contract][user];commontext='|'.join(map(str,common));basecounts=np.bincount(v['ygt'],minlength=9)[1:9];base=[k for k in range(1,9) if basecounts[k-1]>=30]
            for seed in SEEDS:
                keys=np.asarray([int.from_bytes(hashlib.sha256(f'{seed}|FINAL|{user}|{i}'.encode()).digest()[:8],'big') for i in range(n)],dtype=np.uint64)
                estimates={};canonical_counts={}
                for method,score in scores.items():
                    order=np.lexsort((keys,score));selection=order[:math.ceil(.3*n)];measure,counts,risks=independent.measure(v['flip'],v['ygt'],selection,common);estimates[method]=measure
                    sr=si[contract,user,method,seed];assert int(sr['accepted'])==len(selection) and sr['common_classes']==commontext
                    for name,val in measure.items():same(number(sr[name]),val)
                    assert sr['sparse_common_classes']=='|'.join(str(k) for k in common if counts[k-1]<30)
                    assert sr['missing_common_classes']=='|'.join(str(k) for k in common if counts[k-1]==0)
                    if seed!=20261009:continue
                    canonical_counts[method]=counts
                    for k in range(1,9):assert int(sui[contract,user,method,k]['class_support'])==counts[k-1]
                    for coverage in COVERAGES:
                        idx=order[:math.ceil(coverage*n)];measured,sup,cr=independent.measure(v['flip'],v['ygt'],idx,common);row=ri[contract,user,method,coverage]
                        assert int(row['paired_blocks'])==n and int(row['accepted'])==len(idx) and row['common_classes']==commontext
                        same(number(row['coverage']),len(idx)/n)
                        for name,val in measured.items():same(number(row[name]),val)
                        lower=sum(cr[k-1] for k in base if cr[k-1] is not None)/len(base) if base else None
                        upper=(sum(cr[k-1] for k in base if cr[k-1] is not None)+sum(cr[k-1] is None for k in base))/len(base) if base else None
                        same(number(row['baseline_set_risk_lower']),lower);same(number(row['baseline_set_risk_upper']),upper)
                        for k in range(1,9):
                            row=ci[contract,user,method,coverage,k];assert int(row['accepted_class'])==sup[k-1]
                            same(number(row['risk']),cr[k-1]);assert (row['in_original_common_set']=='True')==(k in common)
                    threshold=entry['threshold_at_nominal_30'] if method=='score_only' else fullthreshold;idx=np.flatnonzero(score<=threshold);measured,_,_=independent.measure(v['flip'],v['ygt'],idx,common)
                    row=di[contract,user,method];same(number(row['threshold']),threshold);assert int(row['accepted'])==len(idx);same(number(row['coverage']),len(idx)/n)
                    for name,val in measured.items():same(number(row[name]),val)
                    accepted=[]
                    for k in range(1,9):
                        idx=np.flatnonzero(v['ypred']==k)
                        if len(idx):accepted.extend(idx[np.lexsort((keys[idx],score[idx]))[:math.ceil(.3*len(idx))]].tolist())
                    measured,_,_=independent.measure(v['flip'],v['ygt'],np.asarray(accepted,dtype=np.int64),common);row=wi[contract,user,method]
                    assert int(row['accepted'])==len(accepted);same(number(row['coverage']),len(accepted)/n)
                    for name,val in measured.items():same(number(row[name]),val)
                a=estimates['score_only'][metric];b=estimates['full'][metric];effect=None if a is None or b is None else a-b
                row=ei[contract,user,seed];same(number(row['score_only_risk']),a);same(number(row['full_risk']),b);same(number(row['effect']),effect);assert row['metric']==metric
                if seed==20261009:
                    assert cai[contract,user]==row
                    diagnostic=support['diagnostics'][contract][user];assert diagnostic['original_common_classes']==common
                    assert diagnostic['score_only_sparse_common_classes']==[k for k in common if canonical_counts['score_only'][k-1]<30]
                    assert diagnostic['score_only_missing_common_classes']==[k for k in common if canonical_counts['score_only'][k-1]==0]
                    assert diagnostic['two_method_supported_intersection_diagnostic_only']==[k for k in range(1,9) if all(a[k-1]>=30 for a in canonical_counts.values())]
                values.setdefault((contract,seed),[]).append(effect)
            print('INDEPENDENT_SUPPLEMENT_USER_PASS',contract,user,flush=True)
    for contract in ['U','B']:
        verify_summary(result['canonical'][contract],describe(values[contract,20261009]))
        for seed in SEEDS:verify_summary(result['conditional_seeds'][f'{contract}|{seed}'],describe(values[contract,seed]))
    save(HERE/'INDEPENDENT_VERIFICATION.json',{'status':'PASS','users':80,'contracts':2,'model_prediction_vectors_checked':vector_checks,'risk_rows':len(risk),'class_rows':len(classes),
        'seed_risk_rows':len(seeds),'paired_seed_effects':len(effects),'canonical_user_effects':len(canonical),'support_rows':len(supportrows),'deployment_rows':len(deployment),'within_class_rows':len(within),
        'original_primary_verification_sha256':sha(LANE/'INDEPENDENT_RESULT_VERIFICATION.json'),'secondary_result_sha256':sha(HERE/'SECONDARY_RESULT.json'),
        'original_common_sets_sha256':sha(LANE/'COMMON_CLASS_SETS.json'),'original_sets_changed':False,'new_confirmatory_primary':False,'verifier_sha256':sha(Path(__file__))})
    print('INDEPENDENT_SCORE_ONLY_N80_PASS',flush=True)

if __name__=='__main__':main()
