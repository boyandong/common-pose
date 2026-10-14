"""Frozen seven methods, support-first class sets, N80 exact-sign primaries."""
import argparse
import csv
import math
from pathlib import Path
import joblib
import numpy as np
from scipy.stats import binomtest
from runtime_common import LANE,BASE,DATA,frozen,sha,read,save,load_module,progress

METHODS=['class_empirical','margin','entropy','boundary_distance','full','no_tta','class_model']
COVERAGES=[.3,.5,.6,.7,.8,.9,1.]
SEEDS=list(range(20261009,20261029))

def checked_analysis():
    cohort=frozen(numeric=True)
    seal=read(LANE/'ANALYSIS_CODE_SEAL.json')
    for n,h in seal['files'].items():assert sha(LANE/n)==h,n
    return cohort

def cache(user,with_flip):
    p=DATA/'features/FINAL'/(user+'.npz');meta=read(p.with_suffix('.json'))
    assert meta['sha256']==sha(p)
    with np.load(p) as z:
        out={k:z[k] for k in (['x','ygt','ypred','flip'] if with_flip else ['x','ygt','ypred'])}
    assert out['x'].shape==(len(out['ygt']),36) and np.isfinite(out['x']).all()
    return out

def stats(values,formal=False):
    a=np.asarray([x for x in values if x is not None],float)
    assert np.isfinite(a).all()
    missing=len(values)-len(a);pos=int(np.sum(a>0));neg=int(np.sum(a<0));zero=int(np.sum(a==0));nonzero=pos+neg
    p=float(binomtest(pos,nonzero,.5).pvalue) if nonzero else 1.
    if len(a):
        rng=np.random.default_rng(20261009)
        boot=np.median(a[rng.integers(0,len(a),(20000,len(a)))],axis=1)
        median=float(np.median(a));ci=np.quantile(boot,[.025,.975]).tolist()
    else:median=None;ci=None
    decision='EVIDENCE_INSUFFICIENT' if missing else ('POSITIVE' if pos>neg and p<=.025 else 'NOT_CONFIRMED')
    return {'enrolled':len(values),'complete_pairs':len(a),'missing_pairs':missing,'positive':pos,'negative':neg,
            'zero':zero,'n_nonzero':nonzero,'median':median,'descriptive_ci95':ci,
            'sign_p_two_sided':p if formal and not missing else None,
            'conditional_subset_sign_p':p if formal and missing else None,
            'formal_decision':decision if formal else 'CONDITIONAL_DESCRIPTIVE_ONLY'}

def write_csv(name,items):
    p=LANE/name
    if p.exists():raise RuntimeError('refuse overwrite '+str(p))
    assert items
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(items[0]));w.writeheader();w.writerows(items)
    p.with_suffix(p.suffix+'.sha256').write_text(sha(p)+'  '+p.name+'\n')

def freeze_support(cohort,old):
    feature=read(LANE/'FEATURE_CACHE_MANIFEST.json');assert feature['users']==80 and feature['status']=='COMPLETE'
    supports=[];sets={};score_manifest={}
    for contract,folder in [('U','gate4e_customer_flip_gate_v1'),('B','gate4f_class_balanced_flip_gate_v1')]:
        full=joblib.load(BASE/folder/'artifacts/FINAL_GATE_MODEL.joblib');full=full if contract=='U' else full['model']
        src=BASE/'paper_supplement_v1_20261009/comparative_analysis'
        models={'full':full,**{m:joblib.load(src/f'{contract}_{m}_DEV_ONLY.joblib') for m in ['class_model','no_tta']}}
        instance=read(src/f'{contract}_SUPPLEMENT_INSTANCE.json')
        rates=np.asarray(instance['class_empirical_rates']);sets[contract]={}
        for user in sorted(cohort['enrolled_users']):
            v=cache(user,False);n=len(v['ygt']);assert n>0
            scores=old.scores(v,models,rates)
            assert set(scores)==set(METHODS) and all(np.isfinite(s).all() and len(s)==n for s in scores.values())
            sp=DATA/'scores'/contract/(user+'.npz');sp.parent.mkdir(parents=True,exist_ok=True)
            if sp.exists():raise RuntimeError('refuse overwrite score cache')
            with sp.open('wb') as f:np.savez_compressed(f,**scores)
            score_manifest[contract+'|'+user]={'path':str(sp),'sha256':sha(sp),'feature_sha256':sha(DATA/'features/FINAL'/(user+'.npz'))}
            ties=old.tiekeys('FINAL',user,n,20261009);supported=[]
            for method in METHODS:
                selected=old.order(scores[method],ties)[:math.ceil(.3*n)]
                counts=[int(np.sum(v['ygt'][selected]==k)) for k in range(1,9)]
                supported.append({k for k,count in enumerate(counts,1) if count>=30})
                for k,count in enumerate(counts,1):supports.append({'contract':contract,'user':user,'method':method,'class':k,'accepted':len(selected),'class_support':count})
            sets[contract][user]=sorted(set.intersection(*supported))
            print('SCORES_AND_SUPPORT_READY',contract,user,n,flush=True)
    write_csv('CANONICAL_SUPPORT_ROWS.csv',supports)
    save(LANE/'SCORE_CACHE_MANIFEST.json',{'status':'FROZEN_SCORES','files':score_manifest,
          'cohort_sha256':sha(LANE/'ENROLLMENT_MANIFEST.json'),'runner_sha256':sha(Path(__file__))})
    save(LANE/'COMMON_CLASS_SETS.json',{'status':'FROZEN_FROM_SUPPORT_ONLY_BEFORE_EFFECT_ANALYSIS',
          'contract_user_sets':sets,'support_rows_sha256':sha(LANE/'CANONICAL_SUPPORT_ROWS.csv'),
          'feature_manifest_sha256':sha(LANE/'FEATURE_CACHE_MANIFEST.json'),
          'score_manifest_sha256':sha(LANE/'SCORE_CACHE_MANIFEST.json'),'canonical_seed':20261009,
          'minimum_class_blocks_each_of_seven_methods':30,'flip_used_for_selection':False})
    progress('SUPPORT_SETS_FROZEN',users=80,sets_sha256=sha(LANE/'COMMON_CLASS_SETS.json'))

def analyze(cohort,old):
    frozen_sets=read(LANE/'COMMON_CLASS_SETS.json')
    assert frozen_sets['status']=='FROZEN_FROM_SUPPORT_ONLY_BEFORE_EFFECT_ANALYSIS' and not frozen_sets['flip_used_for_selection']
    assert frozen_sets['score_manifest_sha256']==sha(LANE/'SCORE_CACHE_MANIFEST.json')
    assert frozen_sets['support_rows_sha256']==sha(LANE/'CANONICAL_SUPPORT_ROWS.csv')
    score_manifest=read(LANE/'SCORE_CACHE_MANIFEST.json')['files'];curves=[];classes=[];seedrows=[];effects=[];deploy=[];within=[]
    effect_map={};primary=[]
    for contract in ['U','B']:
        thresholds=read(BASE/'paper_supplement_v1_20261009/comparative_analysis'/f'{contract}_SUPPLEMENT_INSTANCE.json')['thresholds_at_nominal_30']
        comparator='boundary_distance' if contract=='U' else 'class_model';metric='ordinary_risk' if contract=='U' else 'fixed_common_risk'
        for user in sorted(cohort['enrolled_users']):
            v=cache(user,True);n=len(v['flip']);assert set(np.unique(v['flip'])).issubset({0,1})
            common=frozen_sets['contract_user_sets'][contract][user]
            entry=score_manifest[contract+'|'+user];sp=Path(entry['path']);assert sha(sp)==entry['sha256']
            assert entry['feature_sha256']==sha(DATA/'features/FINAL'/(user+'.npz'))
            with np.load(sp) as z:scores={m:z[m] for m in METHODS}
            for seed in SEEDS:
                ties=old.tiekeys('FINAL',user,n,seed);values={}
                for method in METHODS:
                    order=old.order(scores[method],ties);mask=np.zeros(n,bool);mask[order[:math.ceil(.3*n)]]=True
                    result=old.maskmetric(v,mask,common);values[method]=result
                    seedrows.append({'contract':contract,'user':user,'seed':seed,'method':method,'accepted':result['accepted'],
                        'ordinary_risk':result['ordinary_risk'],'fixed_common_risk':result['fixed_common_risk'],
                        'dynamic_balanced_risk':result['dynamic_balanced_risk'],'common_classes':'|'.join(map(str,common)),
                        'sparse_common_classes':'|'.join(str(k) for k in common if result['class_support'][k-1]<30),
                        'missing_common_classes':'|'.join(str(k) for k in common if result['class_support'][k-1]==0)})
                    if seed!=20261009:continue
                    for coverage in COVERAGES:
                        cmask=np.zeros(n,bool);cmask[order[:math.ceil(coverage*n)]]=True
                        cr=old.maskmetric(v,cmask,common)
                        curves.append({'contract':contract,'user':user,'method':method,'nominal_coverage':coverage,'accepted':cr['accepted'],
                            'paired_blocks':n,'achieved_coverage':cr['coverage'],'ordinary_risk':cr['ordinary_risk'],
                            'fixed_common_risk':cr['fixed_common_risk'],'dynamic_balanced_risk':cr['dynamic_balanced_risk'],
                            'baseline_set_risk_lower':cr['baseline_set_risk_lower'],'baseline_set_risk_upper':cr['baseline_set_risk_upper'],
                            'common_classes':'|'.join(map(str,common))})
                        for k in range(1,9):classes.append({'contract':contract,'user':user,'method':method,'nominal_coverage':coverage,
                            'class':k,'accepted_class':cr['class_support'][k-1],'risk':cr['class_risk'][k-1],
                            'in_frozen_common_set':k in common})
                    dr=old.maskmetric(v,scores[method]<=thresholds[method],common)
                    deploy.append({'contract':contract,'user':user,'method':method,'frozen_threshold':thresholds[method],
                                   **{k:dr[k] for k in ['accepted','coverage','ordinary_risk','fixed_common_risk','dynamic_balanced_risk']}})
                    wm=np.zeros(n,bool)
                    for k in range(1,9):
                        idx=np.flatnonzero(v['ypred']==k)
                        if len(idx):wm[idx[old.order(scores[method][idx],ties[idx])[:math.ceil(.3*len(idx))]]]=True
                    wr=old.maskmetric(v,wm,common)
                    within.append({'contract':contract,'user':user,'method':method,'accepted':wr['accepted'],
                                   'ordinary_risk':wr['ordinary_risk'],'fixed_common_risk':wr['fixed_common_risk']})
                for baseline in METHODS:
                    if baseline=='full':continue
                    a=values[baseline][metric];b=values['full'][metric];delta=None if a is None or b is None else a-b
                    effect_map.setdefault((contract,seed,baseline),[]).append(delta)
                    effects.append({'contract':contract,'user':user,'seed':seed,'baseline':baseline,'metric':metric,
                                    'baseline_risk':a,'full_risk':b,'effect':delta})
                    if seed==20261009 and baseline==comparator:primary.append(effects[-1])
            print('ANALYZED',contract,user,flush=True)
    for name,rr in [('RISK_COVERAGE_ROWS.csv',curves),('CLASSWISE_ROWS.csv',classes),('SEED_RISK_ROWS.csv',seedrows),
                    ('SEED_EFFECTS.csv',effects),('DEPLOYMENT_ROWS.csv',deploy),('WITHIN_PREDICTED_CLASS_ROWS.csv',within),('PRIMARY_USER_EFFECTS.csv',primary)]:write_csv(name,rr)
    primary_stats={c:stats([r['effect'] for r in primary if r['contract']==c],formal=True) for c in ['U','B']}
    joint='POSITIVE' if all(s['formal_decision']=='POSITIVE' for s in primary_stats.values()) else (
        'EVIDENCE_INSUFFICIENT' if any(s['formal_decision']=='EVIDENCE_INSUFFICIENT' for s in primary_stats.values()) else 'NOT_CONFIRMED')
    seed_summary={f'{c}|{seed}|{baseline}':stats(vals) for (c,seed,baseline),vals in effect_map.items()}
    save(LANE/'PRIMARY_RESULT.json',{'status':'ANALYZED_PENDING_INDEPENDENT_VERIFICATION','joint_decision':joint,
        'primary':primary_stats,'comparisons':{'U':'full vs boundary_distance ordinary risk','B':'full vs class_model fixed common-class risk'},
        'alpha_per_endpoint':.025,'enrolled_users':80,'no_replacement':True,'upstream_membership':'UNRESOLVED',
        'conditional_seed_descriptions':seed_summary,'source_seals':{'protocol':sha(LANE/'SCIENTIFIC_SPEC.md'),
        'cohort':sha(LANE/'ENROLLMENT_MANIFEST.json'),'common_sets':sha(LANE/'COMMON_CLASS_SETS.json'),
        'scores':sha(LANE/'SCORE_CACHE_MANIFEST.json'),'code':sha(Path(__file__))}})
    save(LANE/'RESULT_MANIFEST.json',{'files':{p.name:sha(p) for p in LANE.glob('*.csv')},'primary_result_sha256':sha(LANE/'PRIMARY_RESULT.json')})
    progress('ANALYSIS_COMPLETE_PENDING_INDEPENDENT_VERIFICATION',joint_decision=joint)
    print('FROZEN_PRIMARY_RESULT',joint,primary_stats,flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze-support',action='store_true');ap.add_argument('--analyze',action='store_true');a=ap.parse_args()
    assert a.freeze_support!=a.analyze
    cohort=checked_analysis();old=load_module('frozen_supplement',BASE/'paper_supplement_v1_20261009/analyze_comparisons.py')
    if a.freeze_support:freeze_support(cohort,old)
    else:analyze(cohort,old)

if __name__=='__main__':main()
