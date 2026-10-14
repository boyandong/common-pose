"""Twenty fixed tie seeds on cached FINAL scores and separately identified DEV refits."""
from __future__ import annotations
import csv
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time
import joblib
import numpy as np

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
SRC=BASE/'paper_supplement_v1_20261009'
OUT=HERE/'seed_results'
SEEDS=range(20261009,20261029)
METHODS=['full','class_empirical','class_model']


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()


def dump(p,v):
    p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')


def csvsave(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def load_module(p):
    spec=importlib.util.spec_from_file_location('frozen_supplement',p)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod


def main():
    if OUT.exists() and any(OUT.iterdir()):raise ValueError('Refuse overwrite seed results')
    OUT.mkdir(exist_ok=True)
    old=load_module(SRC/'analyze_comparisons.py')
    assert sha(SRC/'analyze_comparisons.py')==(SRC/'analyze_comparisons.sha256').read_text().split()[0]
    assert sha(HERE/'CLOSING_SPEC.md')==(HERE/'CLOSING_SPEC.sha256').read_text().split()[0]
    assert sha(Path(__file__))==(HERE/'seed_robustness.sha256').read_text().split()[0]
    cache=json.loads((HERE/'REMOTE_CACHE_VERIFICATION.json').read_text())
    data={}
    for r in cache['features']:
        p=SRC/'features'/r['split']/(r['user']+'.npz')
        assert sha(p)==r['sha256']
        with np.load(p) as z:data[r['user']]={k:z[k] for k in z.files}
    with (SRC/'comparative_analysis/RISK_COVERAGE_ROWS.csv').open(encoding='utf-8-sig',newline='') as f:
        reference={(r['split'],r['contract'],r['user'],r['method']):r for r in csv.DictReader(f) if float(r['nominal_coverage'])==.3}
    summary=json.loads((SRC/'comparative_analysis/SUMMARY.json').read_text())['summary']
    splits=json.loads((SRC/'comparative_analysis/SPLITS.json').read_text())['outer_folds']
    scores={};lineage=[];canonical=[]
    for c,folder in [('U','gate4e_customer_flip_gate_v1'),('B','gate4f_class_balanced_flip_gate_v1')]:
        inst=json.loads((BASE/folder/'artifacts/FINAL_GATE_INSTANCE.json').read_text())
        full_path=BASE/folder/'artifacts/FINAL_GATE_MODEL.joblib'
        assert sha(full_path)==inst['model_sha256']
        loaded=joblib.load(full_path)
        full=loaded if c=='U' else loaded['model']
        model_path=SRC/'comparative_analysis'/(c+'_class_model_DEV_ONLY.joblib')
        assert sha(model_path)==model_path.with_suffix('.sha256').read_text().split()[0]
        models={'full':full,'class_model':joblib.load(model_path)}
        supp=json.loads((SRC/'comparative_analysis'/(c+'_SUPPLEMENT_INSTANCE.json')).read_text())
        rates=np.array(supp['class_empirical_rates'])
        final=[r['user'] for r in cache['features'] if r['split']=='FINAL']
        for u in final:
            v=data[u]
            scores['FINAL',c,u]={'full':full.predict_proba(v['x'])[:,1],
                'class_model':models['class_model'].predict_proba(v['x'][:,:8])[:,1],
                'class_empirical':rates[v['ypred']-1]}
        lineage.append({'split':'FINAL','contract':c,'identity':'original frozen full + sealed DEV-only class model; no fit',
            'full_sha256':sha(full_path),'class_model_sha256':sha(model_path)})
        # Fold scores were not saved; reconstruct once and disclose this distinction.
        for fold in [r for r in splits if r['contract']==c]:
            tr,cal,test=fold['train'],fold['calibration'],fold['test']
            assert not(set(tr)&set(cal) or set(tr)&set(test) or set(cal)&set(test))
            assert not(set(tr+cal+test)&set(final))
            x,y,w=old.weights(tr,data,c)
            models={'full':old.fit(x,y,w,c),'class_model':old.fit(x[:,:8],y,w,c)}
            rates=old.empirical(tr,data)
            for m,model in models.items():
                p=OUT/(c+'_fold'+str(fold['fold'])+'_'+m+'.joblib');joblib.dump(model,p)
                lineage.append({'split':'DEV','contract':c,'fold':fold['fold'],'method':m,'identity':'same-spec fold refit; original score vectors unavailable',
                    'model_sha256':sha(p),'train':tr,'calibration':cal,'test':test})
            for u in test:
                v=data[u]
                scores['DEV',c,u]={'full':models['full'].predict_proba(v['x'])[:,1],
                    'class_model':models['class_model'].predict_proba(v['x'][:,:8])[:,1],
                    'class_empirical':rates[v['ypred']-1]}
            print('DEV_REFIT',c,fold['fold'],flush=True)
    # Canonical admission against old 30% output; all differences retained.
    for (split,c,u),sc in sorted(scores.items()):
        v=data[u];n=len(v['flip']);num=math.ceil(.3*n)
        common=summary[c+'_'+split]['common_reference_class_sets'][u]
        ties=old.tiekeys(split,u,n,20261009)
        for m in METHODS:
            mask=np.zeros(n,bool);mask[old.order(sc[m],ties)[:num]]=True
            got=old.maskmetric(v,mask,common);ref=reference[split,c,u,m]
            for metric in ['ordinary_risk','fixed_common_risk','dynamic_balanced_risk']:
                expected=float(ref[metric]) if ref[metric] else None
                value=got[metric]
                delta=value-expected if value is not None and expected is not None else None
                canonical.append({'split':split,'contract':c,'user':u,'method':m,'metric':metric,
                    'reference_risk':expected,'recovered_risk':value,'difference':delta})
                assert (value is None)==(expected is None)
                if delta is not None:assert abs(delta)<1e-12, (split,c,u,m,metric,delta)
    csvsave(OUT/'CANONICAL_SEED_ADMISSION.csv',canonical)
    dump(OUT/'SCORE_LINEAGE.json',{'rows':lineage,'canonical_max_abs_risk_difference':max(abs(r['difference']) for r in canonical if r['difference'] is not None),
        'scope':'canonical risk endpoints match; does not prove original per-block score identity, especially DEV refits'})
    rows=[];classrows=[];effectrows=[];seed_summary={};supports={}
    # Tie keys reused for U/B within each user/seed. No perturbation of models.
    for split in ['DEV','FINAL']:
        users=sorted(r['user'] for r in cache['features'] if r['split']==split)
        for u in users:
            v=data[u];n=len(v['flip']);num=math.ceil(.3*n)
            for seed in SEEDS:
                ties=old.tiekeys(split,u,n,seed)
                for c in ['U','B']:
                    sc=scores[split,c,u];common=summary[c+'_'+split]['common_reference_class_sets'][u]
                    values={};seed_supported=[]
                    for m in METHODS:
                        mask=np.zeros(n,bool);mask[old.order(sc[m],ties)[:num]]=True
                        vals=old.maskmetric(v,mask,common);values[m]=vals
                        sparse=[k for k in common if vals['class_support'][k-1]<30]
                        missing=[k for k in common if vals['class_support'][k-1]==0]
                        served=[k for k in range(1,9) if vals['class_support'][k-1]>=30]
                        seed_supported.append(set(served))
                        rows.append({'split':split,'contract':c,'user':u,'seed':seed,'method':m,'accepted':num,
                            'ordinary_risk':vals['ordinary_risk'],'fixed_common_risk':vals['fixed_common_risk'],
                            'frozen_common_classes':'|'.join(map(str,common)),'sparse_frozen_classes':'|'.join(map(str,sparse)),
                            'missing_frozen_classes':'|'.join(map(str,missing)), 'supported_classes_at_seed':'|'.join(map(str,served)),
                            'baseline_set_risk_lower':vals['baseline_set_risk_lower'],'baseline_set_risk_upper':vals['baseline_set_risk_upper']})
                        for k in range(1,9):
                            classrows.append({'split':split,'contract':c,'user':u,'seed':seed,'method':m,'class':k,
                                'accepted_support':vals['class_support'][k-1],'accepted_risk':vals['class_risk'][k-1],
                                'in_frozen_common_set':k in common,'supported':vals['class_support'][k-1]>=30})
                    supports[split,c,u,seed]=sorted(set.intersection(*seed_supported))
                    metric='ordinary_risk' if c=='U' else 'fixed_common_risk'
                    for m in ['class_empirical','class_model']:
                        a,b=values[m][metric],values['full'][metric]
                        effectrows.append({'split':split,'contract':c,'user':u,'seed':seed,'comparison':'full_vs_'+m,'metric':metric,
                            'effect':a-b if a is not None and b is not None else None})
            dump(HERE/'SEED_PROGRESS.json',{'status':'RUNNING','completed_user':u,'split':split,'updated_at_epoch':time.time()})
            print('SEEDS_DONE',split,u,flush=True)
        for c in ['U','B']:
            for m in ['class_empirical','class_model']:
                per_seed=[]
                for seed in SEEDS:
                    vals=[r['effect'] for r in effectrows if r['split']==split and r['contract']==c and r['seed']==seed and r['comparison']=='full_vs_'+m]
                    st=old.stat(vals,True);per_seed.append({'seed':seed,**st})
                valid=[r for r in per_seed if r['median'] is not None]
                seed_summary[split+'_'+c+'__full_vs_'+m]={'per_seed':per_seed,
                    'median_effect_range':[min(r['median'] for r in valid),max(r['median'] for r in valid)] if valid else None,
                    'positive_user_count_range':[min(r['positive_users'] for r in valid),max(r['positive_users'] for r in valid)] if valid else None,
                    'complete_cohort_seeds':sum(r['n_missing']==0 for r in per_seed),
                    'ci_lower_above_zero_seeds':sum(r['ci95'] is not None and r['ci95'][0]>0 for r in valid)}
    csvsave(OUT/'SEED_USER_RISKS.csv',rows)
    csvsave(OUT/'SEED_CLASS_SUPPORT.csv',classrows)
    csvsave(OUT/'SEED_PAIRED_EFFECTS.csv',effectrows)
    csvsave(OUT/'SEED_SUPPORT_INTERSECTIONS_DIAGNOSTIC.csv',[{'split':s,'contract':c,'user':u,'seed':seed,'three_method_supported_intersection':'|'.join(map(str,v)),
        'note':'diagnostic only; does not replace original seven-method frozen common set'} for (s,c,u,seed),v in supports.items()])
    dump(OUT/'SUMMARY.json',{'status':'COMPLETE','seeds':list(SEEDS),'summary':seed_summary,
        'claim':'FINAL frozen-score robustness; DEV separately identified same-spec refit then fixed-score robustness; seeds are not independent users',
        'no_best_seed_selection':True,'frozen_class_sets_unchanged':True})
    dump(OUT/'RUN_MANIFEST.json',{'status':'COMPLETE','code_sha256':sha(Path(__file__)),'spec_sha256':sha(HERE/'CLOSING_SPEC.md'),
        'cache_receipt_sha256':sha(HERE/'REMOTE_CACHE_VERIFICATION.json'),'files':{p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file()}})
    dump(HERE/'SEED_PROGRESS.json',{'status':'COMPLETE','user_risks':len(rows),'class_support_rows':len(classrows),'effects':len(effectrows),'completed_at_epoch':time.time()})
    print('SEED_ROBUSTNESS_COMPLETE',len(rows),len(classrows),len(effectrows),flush=True)


if __name__=='__main__': main()
