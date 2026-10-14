"""Frozen supplementary DEV cross-fitting and FINAL descriptive comparisons."""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import warnings
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
import joblib
import numpy as np
from scipy.stats import binomtest
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

LANE=Path(__file__).resolve().parent
BASE=LANE.parent
ART=LANE/'comparative_analysis'
METHODS=['class_empirical','margin','entropy','boundary_distance','full','no_tta','class_model']
COVERAGES=np.arange(1,101)/100

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()
def load(name,p):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
def save(p,o):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():raise RuntimeError('refuse overwrite '+str(p))
    t=p.with_suffix(p.suffix+'.partial');t.write_text(json.dumps(o,indent=2,sort_keys=True,allow_nan=False)+'\n')
    os.replace(t,p);p.with_suffix('.sha256').write_text(sha(p)+'  '+p.name+'\n')
def csvsave(p,rows):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():raise RuntimeError('refuse overwrite '+str(p))
    with p.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def stat(values,infer=False):
    a=np.array([v for v in values if v is not None],float);missing=len(values)-len(a)
    o={'n':len(a),'n_missing':missing,'median':float(np.median(a)) if len(a) else None}
    if not len(a):return o
    o.update(q25=float(np.quantile(a,.25)),q75=float(np.quantile(a,.75)),min=float(a.min()),max=float(a.max()))
    rng=np.random.default_rng(20261009);b=np.median(a[rng.integers(0,len(a),(20000,len(a)))],axis=1)
    o['ci95']=np.quantile(b,[.025,.975]).tolist()
    if infer:
        n=int(np.sum(a!=0));pos=int(np.sum(a>0));o['positive_users']=pos;o['zero_users']=int(np.sum(a==0))
        o['sign_p_two_sided']=float(binomtest(pos,n,.5).pvalue) if n and missing==0 else None
    return o
def tiekeys(split,u,n,seed=20261009):
    return np.array([int.from_bytes(hashlib.sha256(f'{seed}|{split}|{u}|{i}'.encode()).digest()[:8],'big') for i in range(n)],dtype=np.uint64)
def order(sc,ties):return np.lexsort((ties,sc))
def weights(names,data,contract):
    xx=[];yy=[];ww=[]
    for u in names:
        v=data[u];idx=np.linspace(0,len(v['flip'])-1,min(5000,len(v['flip'])),dtype=np.int64)
        y=v['flip'][idx];ref=v['ygt'][idx];w=np.zeros(len(idx),float)
        if contract=='U':
            for state in np.unique(y):w[y==state]=1/(len(np.unique(y))*np.sum(y==state))
        else:
            for c in np.unique(ref):
                mask=ref==c
                for state in np.unique(y[mask]):
                    cell=mask&(y==state);w[cell]=1/(len(np.unique(ref))*len(np.unique(y[mask]))*np.sum(cell))
        xx.append(v['x'][idx]);yy.append(y);ww.append(w)
    x=np.concatenate(xx);y=np.concatenate(yy);w=np.concatenate(ww);w*=len(w)/w.sum();return x,y,w
def fit(x,y,w,contract):
    if contract=='U':
        model=HistGradientBoostingClassifier(max_iter=100,max_depth=3,learning_rate=.1,l2_regularization=1.,random_state=0)
        model.fit(x,y,sample_weight=w)
    else:
        model=make_pipeline(StandardScaler(),LogisticRegression(C=1.,solver='lbfgs',max_iter=300,random_state=0))
        model.fit(x,y,logisticregression__sample_weight=w)
    return model
def empirical(names,data):
    rates=[]
    for k in range(1,9):
        vals=[]
        for u in names:
            v=data[u];mask=v['ypred']==k;n=int(mask.sum())
            if n:vals.append((float(v['flip'][mask].sum())+.5)/(n+1))
        rates.append(float(np.mean(vals)) if vals else .5)
    return np.array(rates)
def scores(v,models,rates):
    return {'class_empirical':rates[v['ypred']-1],'margin':-v['x'][:,16],
        'entropy':v['x'][:,17],'boundary_distance':-v['x'][:,18],
        'full':models['full'].predict_proba(v['x'])[:,1],
        'no_tta':models['no_tta'].predict_proba(v['x'][:,:34])[:,1],
        'class_model':models['class_model'].predict_proba(v['x'][:,:8])[:,1]}
def calibrate(names,data,sc,contract):
    vals=[]
    for u in names:
        if contract=='U':vals.append(float(np.quantile(sc[u],.3)))
        else:
            vals.append(float(np.median([np.quantile(sc[u][data[u]['ygt']==k],.3)
                for k in range(1,9) if np.sum(data[u]['ygt']==k)>=30])))
    return float(np.median(vals))
def maskmetric(v,accepted,common):
    y=v['flip'];gt=v['ygt'];n=int(np.sum(accepted))
    support=[int(np.sum(accepted&(gt==k))) for k in range(1,9)]
    risk=[float(np.mean(y[accepted&(gt==k)])) if support[k-1] else None for k in range(1,9)]
    valid=[risk[k-1] for k in range(1,9) if support[k-1]>=30]
    fixed=[risk[k-1] for k in common]
    baseline=[k for k in range(1,9) if np.sum(gt==k)>=30]
    observed=[risk[k-1] for k in baseline if risk[k-1] is not None]
    missing=sum(risk[k-1] is None for k in baseline)
    return {'accepted':n,'coverage':n/len(y),'ordinary_risk':float(np.mean(y[accepted])) if n else None,
        'dynamic_balanced_risk':float(np.mean(valid)) if valid else None,
        'fixed_common_risk':float(np.mean(fixed)) if fixed and all(r is not None for r in fixed) else None,
        'baseline_set_risk_lower':float(sum(observed)/len(baseline)) if baseline else None,
        'baseline_set_risk_upper':float((sum(observed)+missing)/len(baseline)) if baseline else None,
        'missing_baseline_classes':missing,'class_support':support,'class_risk':risk}
def curve(v,idx,common):
    n=len(idx);y=v['flip'][idx];gt=v['ygt'][idx]
    cs=np.cumsum(y,dtype=np.int64);counts=[];flips=[];pred_counts=[];pred_flips=[]
    for k in range(1,9):
        mask=gt==k;counts.append(np.cumsum(mask,dtype=np.int64));flips.append(np.cumsum(y*mask,dtype=np.int64))
        mask=v['ypred'][idx]==k;pred_counts.append(np.cumsum(mask,dtype=np.int64));pred_flips.append(np.cumsum(y*mask,dtype=np.int64))
    out=[]
    for cov in COVERAGES:
        a=max(1,math.ceil(float(cov)*n));sup=[int(c[a-1]) for c in counts]
        risk=[float(flips[k][a-1]/sup[k]) if sup[k] else None for k in range(8)]
        dyn=[risk[k] for k in range(8) if sup[k]>=30]
        fix=[risk[k-1] for k in common]
        base=[k for k in range(8) if counts[k][-1]>=30];obs=[risk[k] for k in base if risk[k] is not None]
        out.append({'nominal_coverage':float(cov),'accepted':a,'achieved_coverage':a/n,
            'ordinary_risk':float(cs[a-1]/a),'dynamic_balanced_risk':float(np.mean(dyn)) if dyn else None,
            'fixed_common_risk':float(np.mean(fix)) if fix and all(x is not None for x in fix) else None,
            'baseline_set_risk_lower':float(sum(obs)/len(base)) if base else None,
            'baseline_set_risk_upper':float((sum(obs)+sum(risk[k] is None for k in base))/len(base)) if base else None,
            'class_support':sup,'class_risk':risk,
            'predicted_class_support':[int(a0[a-1]) for a0 in pred_counts],
            'predicted_class_risk':[float(pred_flips[k][a-1]/pred_counts[k][a-1]) if pred_counts[k][a-1] else None for k in range(8)]})
    return out,float(np.mean(cs/np.arange(1,n+1)))

def prepare():
    rec=load('rec',LANE/'tools/reconstruct_outputs.py')
    e=load('original_e',BASE/'gate4e_customer_flip_gate_v1/analysis/gate4e_flip_gate.py')
    head=joblib.load('/root/work/gate3_work/frozen_head/frozen_db9_trusted8_lda.joblib')['head']
    sigma=np.array(json.loads((BASE/'gate3b_continuous_representation/artifacts/FISHER_DB9_REFERENCE_SCALE.json').read_text())['fisher_component_sigma_db9'])
    W=np.linalg.lstsq(head.scalings_,head.coef_.T,rcond=None)[0];units=[];norms=np.empty((8,8))
    for i,j in e.PAIRS:
        delta=W[:,i]-W[:,j];n=float(np.linalg.norm(delta));units.append(delta/n);norms[i,j]=norms[j,i]=n
    np.fill_diagonal(norms,np.inf);units=np.array(units).T
    def paths(r):
        stem=Path(r['source_member']).stem
        return LANE/'reconstructed/base'/r['split']/r['participant_id']/(stem+'.npz'),LANE/'reconstructed/tta'/r['split']/r['participant_id']/(stem+'.npz')
    def base_loader(r):
        p,_=paths(r);receipt=json.loads(p.with_suffix('.json').read_text())
        if receipt['input_sha256']!=r['sha256'] or receipt['output_sha256']!=sha(p):raise RuntimeError('base receipt differs')
        with np.load(p) as z:return {k:z[k] for k in z.files}
    groups=defaultdict(list)
    for r in rec.rows():groups[r['split'],r['participant_id']].append(r)
    for (split,u),rr in sorted(groups.items()):
        p=LANE/'features'/split/(u+'.npz')
        if p.exists():
            if sha(p)!=p.with_suffix('.sha256').read_text().split()[0]:raise RuntimeError('feature hash differs')
            continue
        v=e.load_user(rr,SimpleNamespace(paths=paths,load_base=base_loader),head,sigma,units,norms)
        p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('wb') as f:np.savez_compressed(f,**{k:v[k] for k in ('x','flip','ygt','ypred')})
        p.with_suffix('.sha256').write_text(sha(p)+'  '+p.name+'\n')
        print('FEATURES_READY',split,u,len(v['flip']),flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prepare',action='store_true');ap.add_argument('--run',action='store_true')
    args=ap.parse_args()
    if args.prepare:prepare()
    if not args.run:return
    for p in [LANE/'SUPPLEMENT_SPEC.md',Path(__file__)]:
        if sha(p)!=p.with_suffix('.sha256').read_text().split()[0]:raise RuntimeError('supplement seal differs')
    ART.mkdir(exist_ok=True)
    data={};splitnames={}
    for split in ['DEV','FINAL']:
        names=[]
        for p in sorted((LANE/'features'/split).glob('*.npz')):
            if sha(p)!=p.with_suffix('.sha256').read_text().split()[0]:raise RuntimeError('feature seal differs')
            with np.load(p) as z:data[p.stem]={k:z[k] for k in z.files}
            names.append(p.stem)
        splitnames[split]=names
    dev=splitnames['DEV'];final=splitnames['FINAL']
    if len(dev)!=19 or len(final)!=20 or set(dev)&set(final):raise RuntimeError('cohort feature inventory differs')
    original=load('old_e',BASE/'gate4e_customer_flip_gate_v1/analysis/gate4e_flip_gate.py')
    fullE=joblib.load(BASE/'gate4e_customer_flip_gate_v1/artifacts/FINAL_GATE_MODEL.joblib')
    fullF=joblib.load(BASE/'gate4f_class_balanced_flip_gate_v1/artifacts/FINAL_GATE_MODEL.joblib')['model']
    instances={c:json.loads((BASE/f'gate4{l}_{name}/artifacts/FINAL_GATE_INSTANCE.json').read_text())
        for c,l,name in [('U','e','customer_flip_gate_v1'),('B','f','class_balanced_flip_gate_v1')]}
    for c,l,name in [('U','e','customer_flip_gate_v1'),('B','f','class_balanced_flip_gate_v1')]:
        if sha(BASE/f'gate4{l}_{name}/artifacts/FINAL_GATE_MODEL.joblib')!=instances[c]['model_sha256']:
            raise RuntimeError('frozen full model hash differs')
    admission=[]
    for u in final:
        v=data[u];old=json.loads((BASE/'final_joint_confirmation_v1/artifacts/users'/(u+'.json')).read_text())
        if len(v['flip'])!=old['paired_blocks']:raise RuntimeError('paired count reconstruction differs '+u)
        for c,model in [('U',fullE),('B',fullF)]:
            gate='Gate4E_Requirement_U' if c=='U' else 'Gate4F_Requirement_B'
            sc=model.predict_proba(v['x'])[:,1];idx=np.argsort(sc,kind='stable')
            for r in old['gates'][gate]['fixed_coverage_curve']:
                mask=np.zeros(len(idx),bool);mask[idx[:math.ceil(r['coverage']*len(idx))]]=True
                got=maskmetric(v,mask,[])
                if r['coverage']==1 and got['class_support']!=r['class_support']:raise RuntimeError('baseline class support differs '+u)
                od=got['ordinary_risk']-r['flip_risk'];bd=got['dynamic_balanced_risk']-(1-r['balanced_preservation'])
                admission.append({'user':u,'contract':c,'coverage':r['coverage'],'ordinary_drift':od,'dynamic_balanced_drift':bd,
                    'class_support_equal':got['class_support']==r['class_support']})
    save(ART/'REPRODUCTION_ADMISSION.json',{'rows':admission,'max_risk_drift':max(abs(r[k]) for r in admission for k in ['ordinary_drift','dynamic_balanced_drift']),
        'interpretation':'aggregate comparison only; individual original predictions and byte identity unavailable'})
    if max(abs(r[k]) for r in admission for k in ['ordinary_drift','dynamic_balanced_drift'])>.005:raise RuntimeError('reconstruction admission risk drift exceeds 0.005')
    allrows=[];effectrows=[];classrows=[];denseclassrows=[];deprows=[];summary={};tiesensitivity=[];splits=[]
    for c in ['U','B']:
        cohort_scores={};thresholds={};folds={}
        for fold in range(5):
            tr,cal,test=original.fold_groups(dev,fold);x,y,w=weights(tr,data,c)
            models={'full':fit(x,y,w,c),'no_tta':fit(x[:,:34],y,w,c),'class_model':fit(x[:,:8],y,w,c)}
            rates=empirical(tr,data)
            cal_sc={u:scores(data[u],models,rates) for u in cal}
            th={m:calibrate(cal,data,{u:cal_sc[u][m] for u in cal},c) for m in METHODS}
            splits.append({'contract':c,'fold':fold,'train':tr,'calibration':cal,'test':test})
            for u in test:cohort_scores[u]=scores(data[u],models,rates);thresholds[u]=th;folds[u]=fold
            print('CV_FOLD_DONE',c,fold,flush=True)
        inst=instances[c];tr=inst['trained_users'];cal=inst['calibration_users'];x,y,w=weights(tr,data,c)
        models={'full':fullE if c=='U' else fullF,'no_tta':fit(x[:,:34],y,w,c),'class_model':fit(x[:,:8],y,w,c)}
        rates=empirical(tr,data);cal_sc={u:scores(data[u],models,rates) for u in cal}
        th={m:calibrate(cal,data,{u:cal_sc[u][m] for u in cal},c) for m in METHODS}
        th['full']=inst['thresholds_by_nominal_coverage']['0.3']
        model_hashes={}
        for key in ['no_tta','class_model']:
            p=ART/f'{c}_{key}_DEV_ONLY.joblib'
            if p.exists():raise RuntimeError('refuse overwrite supplementary model')
            joblib.dump(models[key],p);model_hashes[key]=sha(p)
            p.with_suffix('.sha256').write_text(sha(p)+'  '+p.name+'\n')
        save(ART/f'{c}_SUPPLEMENT_INSTANCE.json',{'contract':c,'train':tr,'calibration':cal,'thresholds_at_nominal_30':th,
            'class_empirical_rates':rates.tolist(),'hyperparameters':'unchanged original selected family','columns':{'no_tta':'0:34','class_model':'0:8'},
            'model_sha256':model_hashes})
        for u in final:cohort_scores[u]=scores(data[u],models,rates);thresholds[u]=th;folds[u]='FINAL_DEV_ONLY_FIT'
        for split,names in [('DEV',dev),('FINAL',final)]:
            rows30={};within30={};commonsets={}
            for u in names:
                v=data[u];n=len(v['flip']);sc=cohort_scores[u];ties=tiekeys(split,u,n)
                ranks={m:order(sc[m],ties) for m in METHODS};num=math.ceil(.3*n)
                support=[]
                for m in METHODS:support.append(np.bincount(v['ygt'][ranks[m][:num]],minlength=9)[1:])
                base=np.bincount(v['ygt'],minlength=9)[1:]
                common=[k+1 for k in range(8) if base[k]>=30 and all(s[k]>=30 for s in support)]
                commonsets[u]=common
                save(ART/'scores'/split/(c+'_'+u+'.json'),{'user':u,'contract':c,'fold':folds[u],'common_reference_classes':common,
                    'class_empirical_rates_observed':np.unique(sc['class_empirical']).tolist()})
                for m in METHODS:
                    cc,aurc=curve(v,ranks[m],common)
                    for r in cc:
                        allrows.append({'split':split,'user':u,'contract':c,'method':m,**{k:val for k,val in r.items() if k not in ['class_support','class_risk','predicted_class_support','predicted_class_risk']},'common_classes':'|'.join(map(str,common))})
                        for grouping,basecls,supkey,riskkey in [('reference_class',v['ygt'],'class_support','class_risk'),('predicted_class',v['ypred'],'predicted_class_support','predicted_class_risk')]:
                            bcounts=np.bincount(basecls,minlength=9)[1:]
                            for k in range(1,9):
                                denseclassrows.append({'split':split,'user':u,'contract':c,'method':m,'coverage':r['nominal_coverage'],
                                    'grouping':grouping,'class':k,'baseline_support':int(bcounts[k-1]),'accepted_support':r[supkey][k-1],
                                    'class_coverage':r[supkey][k-1]/int(bcounts[k-1]) if bcounts[k-1] else None,
                                    'accepted_risk':r[riskkey][k-1],'supported':r[supkey][k-1]>=30})
                    r=cc[29];rows30[u,m]=r
                    for k in range(1,9):
                        classrows.append({'split':split,'user':u,'contract':c,'method':m,'grouping':'reference_class','class':k,
                            'baseline_support':int(base[k-1]),'accepted_support':r['class_support'][k-1],
                            'class_coverage':r['class_support'][k-1]/int(base[k-1]) if base[k-1] else None,
                            'accepted_risk':r['class_risk'][k-1],'baseline_risk':float(np.mean(v['flip'][v['ygt']==k])) if base[k-1] else None})
                    accepted=np.zeros(n,bool)
                    for k in range(1,9):
                        sub=np.flatnonzero(v['ypred']==k)
                        if not len(sub):continue
                        subord=sub[order(sc[m][sub],ties[sub])];take=subord[:math.ceil(.3*len(sub))];accepted[take]=True
                        classrows.append({'split':split,'user':u,'contract':c,'method':m,'grouping':'within_predicted_class','class':k,
                            'baseline_support':len(sub),'accepted_support':len(take),'class_coverage':len(take)/len(sub),
                            'accepted_risk':float(np.mean(v['flip'][take])),'baseline_risk':float(np.mean(v['flip'][sub]))})
                    within30[u,m]=maskmetric(v,accepted,common)
                    dep=maskmetric(v,sc[m]<=thresholds[u][m],common)
                    deprows.append({'split':split,'user':u,'contract':c,'method':m,'threshold':thresholds[u][m],
                        **{k:val for k,val in dep.items() if k not in ['class_support','class_risk']}})
                    if m=='class_empirical':
                        variants=[]
                        for seed in range(20261009,20261029):
                            ix=order(sc[m],tiekeys(split,u,n,seed))[:num];mask=np.zeros(n,bool);mask[ix]=True
                            vals=maskmetric(v,mask,common);variants.append(vals['ordinary_risk'])
                        tiesensitivity.append({'split':split,'user':u,'contract':c,'seed_min_risk':min(variants),'seed_max_risk':max(variants),
                            'seed_mean_risk':float(np.mean(variants)),'seeds':20,
                            'stable_original_order_risk':float(np.mean(v['flip'][np.argsort(sc[m],kind='stable')[:num]]))})
                    # Save scalar AURC and all-method effects below, without pooled-sample inference.
                    rows30[u,m]['exact_ordinary_aurc']=aurc
                print('SCORED_USER',c,split,u,'COMMON',common,flush=True)
            metrics=['ordinary_risk','dynamic_balanced_risk','fixed_common_risk','exact_ordinary_aurc']
            comps={}
            for baseline in [m for m in METHODS if m!='full']:
                for metric in metrics:
                    vals=[]
                    for u in names:
                        a=rows30[u,baseline].get(metric);b=rows30[u,'full'].get(metric);effect=a-b if a is not None and b is not None else None
                        vals.append(effect);effectrows.append({'split':split,'user':u,'contract':c,'comparison':'full_vs_'+baseline,'metric':metric,'effect':effect})
                    comps['full_vs_'+baseline+'__'+metric]=stat(vals,True)
                vals=[]
                for u in names:
                    effect=within30[u,baseline]['ordinary_risk']-within30[u,'full']['ordinary_risk'];vals.append(effect)
                    effectrows.append({'split':split,'user':u,'contract':c,'comparison':'full_vs_'+baseline,'metric':'within_predicted_class_ordinary_risk','effect':effect})
                comps['full_vs_'+baseline+'__within_predicted_class_ordinary_risk']=stat(vals,True)
            summary[c+'_'+split]={'comparisons':comps,'common_reference_class_sets':commonsets,
                'empty_common_set_users':[u for u in names if not commonsets[u]],
                'method_risks_at_30':{m:{metric:stat([rows30[u,m].get(metric) for u in names]) for metric in metrics} for m in METHODS}}
    # Four designated tests, separately within DEV and previously examined FINAL cohorts.
    for split in ['DEV','FINAL']:
        tests=[]
        for c,metric in [('U','ordinary_risk'),('B','fixed_common_risk')]:
            for baseline in ['class_empirical','no_tta']:
                key='full_vs_'+baseline+'__'+metric;st=summary[c+'_'+split]['comparisons'][key]
                tests.append((st,st.get('sign_p_two_sided')))
        valid=[(s,p) for s,p in tests if p is not None]
        if len(valid)==4:
            running=0
            for i,(st,p) in enumerate(sorted(valid,key=lambda a:a[1])):
                running=max(running,min(1.,p*(4-i)));st['holm_p_four_designated']=running
    csvsave(ART/'RISK_COVERAGE_ROWS.csv',allrows);csvsave(ART/'PAIRED_EFFECTS.csv',effectrows)
    csvsave(ART/'CLASSWISE_30_ROWS.csv',classrows);csvsave(ART/'DEPLOYMENT_30_ROWS.csv',deprows);csvsave(ART/'CLASS_ONLY_TIE_SENSITIVITY.csv',tiesensitivity)
    csvsave(ART/'CLASSWISE_DENSE_ROWS.csv',denseclassrows)
    save(ART/'SPLITS.json',{'outer_folds':splits,'no_final_fit_or_selection':True})
    save(ART/'SUMMARY.json',{'status':'SUPPLEMENT_COMPARATIVE_ANALYSIS_COMPLETE','spec_sha256':sha(LANE/'SUPPLEMENT_SPEC.md'),
        'analysis_sha256':sha(Path(__file__)),'claim_boundary':'post-V1 supplemental; reconstructed outputs; no new independent confirmation',
        'summary':summary,'user_bootstrap_draws':20000,'seed':20261009})
    print('SUPPLEMENT_COMPARATIVE_ANALYSIS_COMPLETE',flush=True)

if __name__=='__main__':main()
