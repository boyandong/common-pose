"""Separate prospective secondary control; parent seven-method outputs unchanged."""
import argparse
import csv
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import joblib
import numpy as np
from runtime_common import LANE,BASE,DATA,frozen,read,save,sha,load_module

HERE=Path(__file__).resolve().parent
COVERAGES=[.3,.5,.6,.7,.8,.9,1.]
SEEDS=list(range(20261009,20261029))

def checks():
    cohort=frozen(numeric=True);seal=read(HERE/'CODE_SEAL.json')
    assert seal['cohort_sha256']==sha(LANE/'ENROLLMENT_MANIFEST.json')
    assert seal['parent_protocol_sha256']==sha(LANE/'SCIENTIFIC_SPEC.md')
    for n,h in seal['files'].items():assert sha(HERE/n)==h,n
    registration=read(HERE/'MODEL_REGISTRATION.json')
    assert read(HERE/'RUNTIME_ADMISSION.json')['status']=='PASS'
    for entry in registration['models'].values():
        assert sha(HERE/entry['model'])==entry['model_sha256']
        assert sha(HERE/entry['instance'])==entry['instance_sha256']
        assert not set(cohort['enrolled_users']).intersection(entry['train']+entry['calibration'])
    return cohort,registration

def feature(user,effects=False):
    if effects:
        support=read(HERE/'SUPPORT_SEAL.json')
        assert support['status']=='FROZEN_WITHOUT_FLIP' and support['original_common_sets_sha256']==sha(LANE/'COMMON_CLASS_SETS.json')
    path=DATA/'features/FINAL'/(user+'.npz');assert sha(path)==read(path.with_suffix('.json'))['sha256']
    with np.load(path) as z:v={k:z[k] for k in (['x','ygt','ypred','flip'] if effects else ['x','ygt','ypred'])}
    assert v['x'].shape==(len(v['ygt']),36) and np.isfinite(v['x']).all()
    return v,path

def table(name,rows):
    path=HERE/name
    with path.open('x',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    path.with_suffix(path.suffix+'.sha256').write_text(sha(path)+'  '+path.name+'\n')

def describe(values):
    from scipy.stats import binomtest
    a=np.asarray([x for x in values if x is not None],float);assert np.isfinite(a).all()
    pos=int(np.sum(a>0));neg=int(np.sum(a<0));zero=int(np.sum(a==0));n=pos+neg
    p=float(binomtest(pos,n,.5).pvalue) if n else 1.
    if len(a):
        rng=np.random.default_rng(20261009);boot=np.median(a[rng.integers(0,len(a),(20000,len(a)))],axis=1)
        median=float(np.median(a));ci=np.quantile(boot,[.025,.975]).tolist()
    else:median=None;ci=None
    return {'enrolled':len(values),'complete_pairs':len(a),'missing_pairs':len(values)-len(a),'positive':pos,'zero':zero,'negative':neg,
            'n_nonzero':n,'median':median,'descriptive_ci95':ci,'descriptive_sign_p':p if len(a)==len(values) else None,
            'conditional_subset_sign_p':p if len(a)!=len(values) else None,'inferential_status':'SECONDARY_DESCRIPTIVE_NO_NEW_CONFIRMATORY_DECISION'}

def freeze(cohort,registration,old):
    parent=read(LANE/'COMMON_CLASS_SETS.json');assert parent['status']=='FROZEN_FROM_SUPPORT_ONLY_BEFORE_EFFECT_ANALYSIS'
    assert not parent['flip_used_for_selection'];assert parent['score_manifest_sha256']==sha(LANE/'SCORE_CACHE_MANIFEST.json')
    original=read(LANE/'SCORE_CACHE_MANIFEST.json')['files'];rows=[];scores_meta={};diagnostics={}
    for contract,entry in registration['models'].items():
        model=joblib.load(HERE/entry['model']);diagnostics[contract]={}
        for user in sorted(cohort['enrolled_users']):
            v,fp=feature(user,False);n=len(v['ygt']);score=model.predict_proba(v['x'][:,:19])[:,1]
            assert len(score)==n and np.isfinite(score).all()
            source=original[contract+'|'+user];sp=Path(source['path']);assert sha(sp)==source['sha256'] and source['feature_sha256']==sha(fp)
            with np.load(sp) as z:full=z['full']
            path=DATA/'score_only_supplement_20261011/scores'/contract/(user+'.npz');path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb') as f:np.savez_compressed(f,score_only=score,full=full)
            scores_meta[contract+'|'+user]={'path':str(path),'sha256':sha(path),'feature_sha256':sha(fp),'original_score_sha256':source['sha256']}
            ties=old.tiekeys('FINAL',user,n,20261009);supports={}
            for method,sc in [('score_only',score),('full',full)]:
                selected=old.order(sc,ties)[:math.ceil(.3*n)];count=np.bincount(v['ygt'][selected],minlength=9)[1:9]
                supports[method]=count.tolist()
                for k in range(1,9):rows.append({'contract':contract,'user':user,'method':method,'class':k,'accepted':len(selected),'class_support':int(count[k-1])})
            common=parent['contract_user_sets'][contract][user]
            diagnostics[contract][user]={'original_common_classes':common,'score_only_sparse_common_classes':[k for k in common if supports['score_only'][k-1]<30],
                'score_only_missing_common_classes':[k for k in common if supports['score_only'][k-1]==0],
                'two_method_supported_intersection_diagnostic_only':[k for k in range(1,9) if all(s[k-1]>=30 for s in supports.values())]}
            print('SUPPLEMENT_SUPPORT_READY',contract,user,flush=True)
    table('CANONICAL_SUPPORT_ROWS.csv',rows)
    save(HERE/'SCORE_CACHE_MANIFEST.json',{'status':'FROZEN_WITHOUT_FLIP','files':scores_meta,'model_registration_sha256':sha(HERE/'MODEL_REGISTRATION.json')})
    save(HERE/'SUPPORT_SEAL.json',{'status':'FROZEN_WITHOUT_FLIP','flip_read':False,'original_common_sets_sha256':sha(LANE/'COMMON_CLASS_SETS.json'),
         'score_manifest_sha256':sha(HERE/'SCORE_CACHE_MANIFEST.json'),'support_rows_sha256':sha(HERE/'CANONICAL_SUPPORT_ROWS.csv'),
         'diagnostics':diagnostics,'original_sets_changed':False,'runner_sha256':sha(Path(__file__))})

def analyze(cohort,registration,old):
    seal=read(HERE/'SUPPORT_SEAL.json');assert seal['score_manifest_sha256']==sha(HERE/'SCORE_CACHE_MANIFEST.json')
    parent=read(LANE/'COMMON_CLASS_SETS.json');assert sha(LANE/'COMMON_CLASS_SETS.json')==seal['original_common_sets_sha256']
    scores_meta=read(HERE/'SCORE_CACHE_MANIFEST.json')['files'];risks=[];classes=[];seedrows=[];effects=[];canonical=[];deploy=[];within=[]
    for contract,entry in registration['models'].items():
        fullthreshold=read(BASE/'paper_supplement_v1_20261009/comparative_analysis'/f'{contract}_SUPPLEMENT_INSTANCE.json')['thresholds_at_nominal_30']['full']
        thresholds={'score_only':entry['threshold_at_nominal_30'],'full':fullthreshold};metric='ordinary_risk' if contract=='U' else 'fixed_common_risk'
        for user in sorted(cohort['enrolled_users']):
            v,fp=feature(user,True);n=len(v['flip']);common=parent['contract_user_sets'][contract][user];meta=scores_meta[contract+'|'+user]
            assert sha(fp)==meta['feature_sha256'] and sha(Path(meta['path']))==meta['sha256']
            with np.load(meta['path']) as z:scores={m:z[m] for m in ['score_only','full']}
            for seed in SEEDS:
                ties=old.tiekeys('FINAL',user,n,seed);values={}
                for method,score in scores.items():
                    order=old.order(score,ties);mask=np.zeros(n,bool);mask[order[:math.ceil(.3*n)]]=True;result=old.maskmetric(v,mask,common);values[method]=result
                    seedrows.append({'contract':contract,'user':user,'seed':seed,'method':method,'accepted':result['accepted'],
                        **{k:result[k] for k in ['ordinary_risk','fixed_common_risk','dynamic_balanced_risk']},'common_classes':'|'.join(map(str,common)),
                        'sparse_common_classes':'|'.join(str(k) for k in common if result['class_support'][k-1]<30),
                        'missing_common_classes':'|'.join(str(k) for k in common if result['class_support'][k-1]==0)})
                    if seed!=20261009:continue
                    for coverage in COVERAGES:
                        mask=np.zeros(n,bool);mask[order[:math.ceil(coverage*n)]]=True;cr=old.maskmetric(v,mask,common)
                        risks.append({'contract':contract,'user':user,'method':method,'nominal_coverage':coverage,'paired_blocks':n,
                            **{k:cr[k] for k in ['accepted','coverage','ordinary_risk','fixed_common_risk','dynamic_balanced_risk','baseline_set_risk_lower','baseline_set_risk_upper']},'common_classes':'|'.join(map(str,common))})
                        for k in range(1,9):classes.append({'contract':contract,'user':user,'method':method,'nominal_coverage':coverage,'class':k,'accepted_class':cr['class_support'][k-1],'risk':cr['class_risk'][k-1],'in_original_common_set':k in common})
                    dr=old.maskmetric(v,score<=thresholds[method],common);deploy.append({'contract':contract,'user':user,'method':method,'threshold':thresholds[method],**{k:dr[k] for k in ['accepted','coverage','ordinary_risk','fixed_common_risk','dynamic_balanced_risk']}})
                    mask=np.zeros(n,bool)
                    for k in range(1,9):
                        idx=np.flatnonzero(v['ypred']==k)
                        if len(idx):mask[idx[old.order(score[idx],ties[idx])[:math.ceil(.3*len(idx))]]]=True
                    wr=old.maskmetric(v,mask,common);within.append({'contract':contract,'user':user,'method':method,**{k:wr[k] for k in ['accepted','coverage','ordinary_risk','fixed_common_risk','dynamic_balanced_risk']}})
                a=values['score_only'][metric];b=values['full'][metric];effect=None if a is None or b is None else a-b
                row={'contract':contract,'user':user,'seed':seed,'metric':metric,'score_only_risk':a,'full_risk':b,'effect':effect}
                effects.append(row)
                if seed==20261009:canonical.append(row)
            print('SUPPLEMENT_ANALYZED',contract,user,flush=True)
    for name,rr in [('RISK_COVERAGE_ROWS.csv',risks),('CLASSWISE_ROWS.csv',classes),('SEED_RISK_ROWS.csv',seedrows),('SEED_EFFECTS.csv',effects),
                    ('SCORE_ONLY_USER_EFFECTS.csv',canonical),('DEPLOYMENT_ROWS.csv',deploy),('WITHIN_PREDICTED_CLASS_ROWS.csv',within)]:table(name,rr)
    summary={c:describe([r['effect'] for r in canonical if r['contract']==c]) for c in ['U','B']}
    conditional={f'{c}|{seed}':describe([r['effect'] for r in effects if r['contract']==c and r['seed']==seed]) for c in ['U','B'] for seed in SEEDS}
    save(HERE/'SECONDARY_RESULT.json',{'status':'ANALYZED_PENDING_INDEPENDENT_VERIFICATION','enrolled_users':80,'canonical':summary,'conditional_seeds':conditional,
         'comparison':'score_only minus full; positive favors full','new_confirmatory_primary':False,'original_primary_changed':False,'common_sets_changed':False,
         'source_seals':{'cohort':sha(LANE/'ENROLLMENT_MANIFEST.json'),'supplement_spec':sha(HERE/'SCIENTIFIC_SPEC.md'),'support':sha(HERE/'SUPPORT_SEAL.json'),
                         'models':sha(HERE/'MODEL_REGISTRATION.json'),'original_common_sets':sha(LANE/'COMMON_CLASS_SETS.json'),'code':sha(Path(__file__))}})
    save(HERE/'RESULT_MANIFEST.json',{'files':{p.name:sha(p) for p in HERE.glob('*.csv')},'secondary_result_sha256':sha(HERE/'SECONDARY_RESULT.json')})

def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['support','analysis']);args=ap.parse_args()
    cohort,registration=checks();old=load_module('supplement_original_metrics',BASE/'paper_supplement_v1_20261009/analyze_comparisons.py')
    if args.stage=='support':freeze(cohort,registration,old)
    else:analyze(cohort,registration,old)

if __name__=='__main__':main()
