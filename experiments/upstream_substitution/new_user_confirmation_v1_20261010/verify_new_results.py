"""Independent scoring/ordering/counting/statistics; no producer functions imported."""
import csv
import hashlib
import math
from pathlib import Path
import joblib
import numpy as np
from runtime_common import LANE,BASE,DATA,frozen,read,sha,save,progress,paths

METHODS=['class_empirical','margin','entropy','boundary_distance','full','no_tta','class_model']
METRICS=['ordinary_risk','fixed_common_risk','dynamic_balanced_risk']

def number(v):return None if v in ['',None] else float(v)
def same(a,b):
    assert (a is None)==(b is None),(a,b)
    if a is not None:assert abs(a-b)<1e-12,(a,b)
def csvrows(name):
    with (LANE/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def order(score,user,seed):
    keys=np.asarray([int(hashlib.sha256(f'{seed}|FINAL|{user}|{i}'.encode()).hexdigest()[:16],16) for i in range(len(score))],dtype=np.uint64)
    return np.lexsort((keys,score))
def measure(flip,gt,indices,common):
    yy=flip[indices];classes=gt[indices];counts=[int(np.count_nonzero(classes==k)) for k in range(1,9)]
    risks=[float(np.sum(yy[classes==k],dtype=np.int64)/counts[k-1]) if counts[k-1] else None for k in range(1,9)]
    ordinary=float(np.sum(yy,dtype=np.int64)/len(yy)) if len(yy) else None
    fixed=float(sum(risks[k-1] for k in common)/len(common)) if common and all(counts[k-1]>0 for k in common) else None
    valid=[risks[k-1] for k in range(1,9) if counts[k-1]>=30]
    dynamic=float(sum(valid)/len(valid)) if valid else None
    return dict(zip(METRICS,[ordinary,fixed,dynamic])),counts,risks

def sign_exact(pos,neg):
    n=pos+neg
    return min(1.,2*sum(math.comb(n,k) for k in range(min(pos,neg)+1))/(2**n)) if n else 1.

def verify_feature_lineage(cohort,user,v):
    fp=DATA/'features/FINAL'/(user+'.npz');receipt=read(fp.with_suffix('.json'))
    all_gt=[];all_pred=[]
    for row in [r for r in cohort['files'] if r['user']==user]:
        row={**row,'participant_id':user};bp,tp=paths(row);entry=receipt['inputs'][row['source_member']]
        assert sha(bp)==entry['base'] and sha(tp)==entry['tta']
        bm=read(bp.with_suffix('.json'));tm=read(tp.with_suffix('.json'))
        assert bm['input_sha256']==tm['input_sha256']==entry['source']
        assert bm['output_sha256']==entry['base'] and tm['output_sha256']==entry['tta']
        assert bm['cohort_sha256']==sha(LANE/'ENROLLMENT_MANIFEST.json')
        assert bm['plan_sha256']==sha(LANE/'SCIENTIFIC_SPEC.md')
        with np.load(bp) as z:b={k:z[k] for k in z.files}
        assert len(b['block_index'])==len(b['y_gt'])==len(b['y_pred'])==bm['paired_valid_blocks']
        assert np.all(b['block_index']>=1) and np.all(np.diff(b['block_index'])>0)
        all_gt.append(b['y_gt']);all_pred.append(b['y_pred'])
    gt=np.concatenate(all_gt);pred=np.concatenate(all_pred)
    assert np.array_equal(gt,v['ygt']) and np.array_equal(pred,v['ypred'])
    assert np.array_equal((gt!=pred).astype(np.int8),v['flip'])
    assert np.array_equal(np.eye(8,dtype=np.float32)[pred-1],v['x'][:,:8])

def main():
    cohort=frozen(numeric=True)
    code=read(LANE/'ANALYSIS_CODE_SEAL.json')
    for name,h in code['files'].items():assert sha(LANE/name)==h,name
    result_manifest=read(LANE/'RESULT_MANIFEST.json')
    for name,h in result_manifest['files'].items():assert sha(LANE/name)==h
    assert result_manifest['primary_result_sha256']==sha(LANE/'PRIMARY_RESULT.json')
    sets_receipt=read(LANE/'COMMON_CLASS_SETS.json')
    assert sets_receipt['score_manifest_sha256']==sha(LANE/'SCORE_CACHE_MANIFEST.json')
    assert sets_receipt['support_rows_sha256']==sha(LANE/'CANONICAL_SUPPORT_ROWS.csv')
    sets=sets_receipt['contract_user_sets'];scores_meta=read(LANE/'SCORE_CACHE_MANIFEST.json')['files']
    seedrows=csvrows('SEED_RISK_ROWS.csv');curve=csvrows('RISK_COVERAGE_ROWS.csv');classes=csvrows('CLASSWISE_ROWS.csv')
    effects=csvrows('SEED_EFFECTS.csv');primary=csvrows('PRIMARY_USER_EFFECTS.csv');deploy=csvrows('DEPLOYMENT_ROWS.csv');within=csvrows('WITHIN_PREDICTED_CLASS_ROWS.csv')
    si={(r['contract'],r['user'],int(r['seed']),r['method']):r for r in seedrows}
    ci={(r['contract'],r['user'],r['method'],float(r['nominal_coverage'])):r for r in curve}
    cli={(r['contract'],r['user'],r['method'],float(r['nominal_coverage']),int(r['class'])):r for r in classes}
    di={(r['contract'],r['user'],r['method']):r for r in deploy};wi={(r['contract'],r['user'],r['method']):r for r in within}
    assert len(si)==len(seedrows)==80*2*20*7
    assert len(ci)==len(curve)==80*2*7*7 and len(cli)==len(classes)==len(ci)*8
    assert len(effects)==80*2*20*6 and len(primary)==160 and len(di)==len(deploy)==80*2*7 and len(wi)==len(within)==len(di)
    values={};cache_count=0;score_vectors=0;lineage_users=set()
    for contract,folder in [('U','gate4e_customer_flip_gate_v1'),('B','gate4f_class_balanced_flip_gate_v1')]:
        fm=joblib.load(BASE/folder/'artifacts/FINAL_GATE_MODEL.joblib');fm=fm if contract=='U' else fm['model']
        src=BASE/'paper_supplement_v1_20261009/comparative_analysis';inst=read(src/f'{contract}_SUPPLEMENT_INSTANCE.json')
        cm=joblib.load(src/f'{contract}_class_model_DEV_ONLY.joblib');nm=joblib.load(src/f'{contract}_no_tta_DEV_ONLY.joblib')
        for user in sorted(cohort['enrolled_users']):
            fp=DATA/'features/FINAL'/(user+'.npz');assert sha(fp)==read(fp.with_suffix('.json'))['sha256']
            with np.load(fp) as z:v={k:z[k] for k in z.files}
            if user not in lineage_users:
                verify_feature_lineage(cohort,user,v);lineage_users.add(user)
            cache_count+=1;n=len(v['flip']);assert n>0
            calculated={'full':fm.predict_proba(v['x'])[:,1],'class_model':cm.predict_proba(v['x'][:,:8])[:,1],
                        'no_tta':nm.predict_proba(v['x'][:,:34])[:,1],
                        'class_empirical':np.asarray(inst['class_empirical_rates'])[v['ypred']-1],
                        'margin':-v['x'][:,16],'entropy':v['x'][:,17],'boundary_distance':-v['x'][:,18]}
            score_entry=scores_meta[contract+'|'+user];sp=Path(score_entry['path']);assert sha(sp)==score_entry['sha256']
            with np.load(sp) as z:
                for method in METHODS:assert np.array_equal(z[method],calculated[method]),(contract,user,method)
            score_vectors+=7
            canonical_supported=[]
            for seed in range(20261009,20261029):
                for method in METHODS:
                    rank=order(calculated[method],user,seed);idx=rank[:math.ceil(.3*n)]
                    metrics,counts,risks=measure(v['flip'],v['ygt'],idx,sets[contract][user])
                    recorded=si[contract,user,seed,method];assert len(idx)==int(recorded['accepted'])
                    for metric in METRICS:same(metrics[metric],number(recorded[metric]))
                    assert recorded['sparse_common_classes']=='|'.join(str(k) for k in sets[contract][user] if counts[k-1]<30)
                    assert recorded['missing_common_classes']=='|'.join(str(k) for k in sets[contract][user] if counts[k-1]==0)
                    values[contract,user,seed,method]=metrics
                    if seed!=20261009:continue
                    canonical_supported.append({k for k in range(1,9) if counts[k-1]>=30})
                    for coverage in [.3,.5,.6,.7,.8,.9,1.]:
                        chosen=rank[:math.ceil(coverage*n)];mm,cc,rr=measure(v['flip'],v['ygt'],chosen,sets[contract][user])
                        row=ci[contract,user,method,coverage];assert int(row['accepted'])==len(chosen) and int(row['paired_blocks'])==n
                        for metric in METRICS:same(mm[metric],number(row[metric]))
                        for k in range(1,9):
                            cr=cli[contract,user,method,coverage,k];assert int(cr['accepted_class'])==cc[k-1];same(rr[k-1],number(cr['risk']))
                    chosen=np.flatnonzero(calculated[method]<=inst['thresholds_at_nominal_30'][method]);mm,_,_=measure(v['flip'],v['ygt'],chosen,sets[contract][user])
                    row=di[contract,user,method];assert int(row['accepted'])==len(chosen);same(float(row['coverage']),len(chosen)/n)
                    for metric in METRICS:same(mm[metric],number(row[metric]))
                    chosen=[]
                    # Full ranks restricted to a class preserve the identical score/tie order.
                    for k in range(1,9):
                        restricted=rank[v['ypred'][rank]==k];chosen.extend(restricted[:math.ceil(.3*len(restricted))])
                    mm,_,_=measure(v['flip'],v['ygt'],np.asarray(chosen,dtype=np.int64),sets[contract][user]);row=wi[contract,user,method]
                    assert int(row['accepted'])==len(chosen)
                    for metric in ['ordinary_risk','fixed_common_risk']:same(mm[metric],number(row[metric]))
            assert sorted(set.intersection(*canonical_supported))==sets[contract][user]
            print('INDEPENDENTLY_VERIFIED',contract,user,flush=True)
    effect_map={}
    for row in effects:
        c,u,s,b=row['contract'],row['user'],int(row['seed']),row['baseline'];metric='ordinary_risk' if c=='U' else 'fixed_common_risk'
        a=values[c,u,s,b][metric];full=values[c,u,s,'full'][metric];effect=None if a is None or full is None else a-full
        same(effect,number(row['effect']));same(a,number(row['baseline_risk']));same(full,number(row['full_risk']))
        effect_map.setdefault(f'{c}|{s}|{b}',[]).append(effect)
    result=read(LANE/'PRIMARY_RESULT.json')
    for key,vals in effect_map.items():
        arr=np.asarray([x for x in vals if x is not None],float);summary=result['conditional_seed_descriptions'][key]
        assert summary['complete_pairs']==len(arr) and summary['missing_pairs']==80-len(arr)
        assert summary['positive']==int(np.count_nonzero(arr>0)) and summary['negative']==int(np.count_nonzero(arr<0)) and summary['zero']==int(np.count_nonzero(arr==0))
        same(summary['median'],float(np.median(arr)) if len(arr) else None)
        if len(arr):
            rng=np.random.default_rng(20261009);bootstrap=np.median(arr[rng.integers(0,len(arr),size=(20000,len(arr)))],axis=1)
            assert np.allclose(np.quantile(bootstrap,[.025,.975]),summary['descriptive_ci95'],rtol=0,atol=1e-12)
    decisions=[]
    for c,b in [('U','boundary_distance'),('B','class_model')]:
        vals=effect_map[f'{c}|20261009|{b}'];arr=np.asarray([x for x in vals if x is not None]);missing=80-len(arr)
        pos=int(np.sum(arr>0));neg=int(np.sum(arr<0));p=sign_exact(pos,neg)
        s=result['primary'][c];assert s['enrolled']==80 and s['complete_pairs']==len(arr) and s['n_nonzero']==pos+neg
        summary=result['conditional_seed_descriptions'][f'{c}|20261009|{b}']
        for name in ['positive','negative','zero','median','descriptive_ci95','missing_pairs']:
            assert s[name]==summary[name],(c,name)
        same(s['sign_p_two_sided'],None if missing else p)
        same(s['conditional_subset_sign_p'],p if missing else None)
        decision='EVIDENCE_INSUFFICIENT' if missing else ('POSITIVE' if pos>neg and p<=.025 else 'NOT_CONFIRMED')
        assert s['formal_decision']==decision;decisions.append(decision)
        assert len([r for r in primary if r['contract']==c])==80
        for r in primary:
            if r['contract']==c:
                assert r['baseline']==b and int(r['seed'])==20261009
                matching=next(e for e in effects if e['contract']==c and e['user']==r['user'] and e['baseline']==b and int(e['seed'])==20261009)
                assert r==matching
    joint='POSITIVE' if decisions==['POSITIVE','POSITIVE'] else ('EVIDENCE_INSUFFICIENT' if 'EVIDENCE_INSUFFICIENT' in decisions else 'NOT_CONFIRMED')
    assert result['joint_decision']==joint
    save(LANE/'INDEPENDENT_RESULT_VERIFICATION.json',{'status':'PASS','joint_decision':joint,'users':80,
         'cache_checks':cache_count,'exact_rescored_vectors':score_vectors,'seed_rows':len(seedrows),
         'curve_rows':len(curve),'class_rows':len(classes),'effect_rows':len(effects),'primary_rows':len(primary),
         'bootstrap_summaries':len(effect_map),'all_frozen_support_sets_rederived':True,
         'raw_base_tta_hash_and_label_lineage_users':len(lineage_users),
         'producer_score_tie_metric_stats_functions_imported':False,'result_sha256':sha(LANE/'PRIMARY_RESULT.json'),
         'verifier_sha256':sha(Path(__file__))})
    progress('INDEPENDENT_RESULT_VERIFICATION_PASS',joint_decision=joint)
    print('INDEPENDENT_RESULT_VERIFICATION_PASS',joint,flush=True)

if __name__=='__main__':main()
