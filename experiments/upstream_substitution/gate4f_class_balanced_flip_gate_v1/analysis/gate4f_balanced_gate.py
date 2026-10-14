#!/usr/bin/env python3
"""Frozen DEV-only class-balanced customer Flip gate benchmark and instance fit."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
from collections import defaultdict
from pathlib import Path

import joblib
import numpy as np
from scipy.optimize import nnls
from scipy.stats import norm, skew, spearmanr
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

LANE=Path(__file__).resolve().parents[1]
ROOT=Path('/root/work/common-pose')
D=ROOT/'experiments/upstream_substitution/gate4d_task_aware_gate_benchmark_v1'
E=ROOT/'experiments/upstream_substitution/gate4e_customer_flip_gate_v1'
ART=LANE/'artifacts'
COVERAGES=[1.,.9,.8,.7,.6,.5,.3]
PAIRS=[(i,j) for i in range(8) for j in range(i+1,8)]
METHODS=['margin','entropy','boundary_distance','tta_dispersion',
         'logistic','hist_gbdt','boundary_safety','gaussian_crossing']
SIMPLICITY=['margin','entropy','boundary_distance','tta_dispersion',
            'boundary_safety','gaussian_crossing','logistic','hist_gbdt']


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def checked(path):
    if sha(path)!=path.with_suffix('.sha256').read_text().split()[0]:
        raise RuntimeError(f'frozen hash differs: {path}')


def save(name,obj):
    ART.mkdir(exist_ok=True)
    p=ART/name
    if p.exists():raise RuntimeError(f'refuse overwrite {p}')
    temp=p.with_name(p.name+f'.{os.getpid()}.partial')
    temp.write_text(json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n')
    os.replace(temp,p)
    p.with_suffix('.sha256').write_text(f'{sha(p)}  {p.name}\n')


def q(x,p):
    x=np.asarray(x)
    return float(np.quantile(x,p)) if x.size else None


def summ(x):
    x=[float(v) for v in x if v is not None and np.isfinite(v)]
    return {'n':len(x),'median':q(x,.5),'q25':q(x,.25),'q75':q(x,.75),
            'minimum':min(x) if x else None,'maximum':max(x) if x else None}


def load_parent():
    for name in ('GATE4F_PLAN.md','BALANCED_CUSTOMER_REQUIREMENT.md','FEATURE_MANIFEST.json',
                 'METHOD_MANIFEST.json','COHORT_MANIFEST.json','ANALYSIS_IMPLEMENTATION.md'):
        checked(LANE/name)
    checked(Path(__file__))
    for name in ('FEATURE_MANIFEST.json','COHORT_MANIFEST.json'):
        if sha(LANE/name)!=sha(E/name):raise RuntimeError(f'Gate4E derivative differs: {name}')
    spec=importlib.util.spec_from_file_location('gate4d_frozen',D/'analysis/gate4d_analysis.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    drows,users,head,mu,sd,sigma=m.frozen()
    cohort=json.loads((LANE/'COHORT_MANIFEST.json').read_text())
    if len(cohort['selected_files'])!=654 or cohort['selected_files']!=drows or cohort['users']!=users:
        raise RuntimeError('not exact Gate4D DEV cohort')
    S=head.scalings_;W=np.linalg.lstsq(S,head.coef_.T,rcond=None)[0]
    residual=float(np.max(np.abs(S@W-head.coef_.T)))
    if residual>=1e-10 or W.shape!=(7,8):raise RuntimeError('LDA Fisher score geometry ambiguous')
    units=[]; norms=np.empty((8,8))
    for i,j in PAIRS:
        delta=W[:,i]-W[:,j];n=float(np.linalg.norm(delta))
        if n<=0:raise RuntimeError('zero LDA boundary normal')
        units.append(delta/n);norms[i,j]=norms[j,i]=n
    np.fill_diagonal(norms,np.inf)
    return m,drows,users,head,sigma,np.array(units).T,norms,residual


def load_user(rows,m,head,sigma,units,norms):
    parts=defaultdict(list)
    for r in rows:
        z=m.load_base(r);n=len(z['block_index'])
        if n==0:continue
        tp=m.paths(r)[1];meta=json.loads(tp.with_suffix('.json').read_text())
        if meta['input_sha256']!=r['sha256'] or meta['output_sha256']!=sha(tp):
            raise RuntimeError('TTA receipt differs')
        with np.load(tp) as t:views=t['fisher_views'].astype(np.float64)
        if views.shape!=(n,4,7):raise RuntimeError('TTA shape differs')
        zg=head.transform(z['gt_api8']).astype(np.float64)
        zp=head.transform(z['pred_api8']).astype(np.float64)
        score=np.asarray(head.decision_function(z['pred_api8']),dtype=np.float64)
        if score.shape!=(n,8):raise RuntimeError('customer score shape differs')
        cls=np.argmax(score,axis=1)
        if not np.array_equal(cls+1,z['y_pred']):raise RuntimeError('customer class differs')
        margins=score[np.arange(n),cls,None]-score
        distances=margins/norms[cls]
        distances[np.arange(n),cls]=np.inf
        nearest=np.argmin(distances,axis=1)
        pairproj=np.einsum('nvd,dk->nvk',views,units,optimize=True)
        pairvar=np.var(pairproj,axis=1)
        ownvar=np.empty((n,8),dtype=np.float64)
        for j in range(8):
            pidx=np.array([PAIRS.index((min(int(i),j),max(int(i),j))) if i!=j else 0 for i in cls])
            ownvar[:,j]=pairvar[np.arange(n),pidx]
        ownvar[np.arange(n),cls]=0
        nearest_sd=np.sqrt(ownvar[np.arange(n),nearest])
        dispersion=np.sum(((views/sigma)-(views/sigma).mean(axis=1,keepdims=True))**2,axis=2).mean(axis=1)
        pp=np.maximum(z['proba_pred'].astype(np.float64),1e-12)
        entropy=-np.sum(pp*np.log(pp),axis=1)
        top=np.partition(score,-2,axis=1)
        margin=top[:,-1]-top[:,-2]
        onehot=np.eye(8,dtype=np.float32)[cls]
        x=np.column_stack((onehot,score,margin,entropy,np.min(distances,axis=1),
                           z['pred_pose8'],zp,dispersion,nearest_sd)).astype(np.float32)
        if x.shape!=(n,36) or not np.isfinite(x).all():raise RuntimeError('feature contract differs')
        safety=-np.min(distances/(np.sqrt(ownvar)+1e-6),axis=1)
        for key,val in (('x',x),('flip',(z['y_gt']!=z['y_pred']).astype(np.int8)),
                        ('ygt',z['y_gt']),('ypred',z['y_pred']),('zg',zg),('zp',zp),
                        ('ef',np.linalg.norm((zp-zg)/sigma,axis=1)),
                        ('raw',np.linalg.norm(zp-zg,axis=1)),
                        ('tv',np.abs(z['proba_gt']-z['proba_pred']).sum(axis=1)/2),
                        ('pose_error',np.linalg.norm(z['pred_pose8']-z['gt_pose8'],axis=1)),
                        ('pairvar',pairvar.astype(np.float32)),('delta',(zg-zp).astype(np.float32)),
                        ('margin',-margin),('entropy',entropy),
                        ('boundary_distance',-np.min(distances,axis=1)),
                        ('tta_dispersion',dispersion),('boundary_safety',safety),
                        ('score',score),('ownvar',ownvar)):
            parts[key].append(val)
    out={k:np.concatenate(v) for k,v in parts.items()}
    if not out:raise RuntimeError('empty user')
    return out


def sample_user(v):
    n=len(v['flip'])
    return np.linspace(0,n-1,min(n,5000),dtype=np.int64)


def training_pack(names,data):
    xx=[];yy=[];ww=[];wg=[];delta=[];variance=[]
    for u in names:
        v=data[u];idx=sample_user(v);y=v['flip'][idx];ref=v['ygt'][idx]
        w=np.zeros(len(idx),dtype=float)
        for c in np.unique(ref):
            mask=ref==c;states=np.unique(y[mask])
            for state in states:
                cell=mask&(y==state)
                w[cell]=1/(len(np.unique(ref))*len(states)*int(cell.sum()))
        g=np.zeros(len(idx),dtype=float);states=np.unique(y)
        for state in states:g[y==state]=1/(len(states)*int(np.sum(y==state)))
        xx.append(v['x'][idx]);yy.append(y);ww.append(w);wg.append(g)
        delta.append(v['delta'][idx]);variance.append(v['pairvar'][idx])
    x=np.concatenate(xx);y=np.concatenate(yy);w=np.concatenate(ww);g=np.concatenate(wg)
    w*=len(w)/w.sum();g*=len(g)/g.sum()
    return x,y,w,g,np.concatenate(delta),np.concatenate(variance)


def fit_direct(x,y,w):
    if len(np.unique(y))<2:raise RuntimeError('training Flip class degenerate')
    logistic=make_pipeline(StandardScaler(),LogisticRegression(C=1.,solver='lbfgs',
                                          max_iter=300,random_state=0))
    logistic.fit(x,y,logisticregression__sample_weight=w)
    gbdt=HistGradientBoostingClassifier(max_iter=100,max_depth=3,learning_rate=.1,
                                        l2_regularization=1.,random_state=0)
    gbdt.fit(x,y,sample_weight=w)
    return logistic,gbdt


def fit_gaussian(delta,var,units,w):
    coeff=[];scaled=[]
    for p in range(len(PAIRS)):
        e=delta@units[:,p]
        target=e*e
        A=np.column_stack((np.ones(len(var)),var[:,p]))
        ab,_=nnls(A*np.sqrt(w[:,None]),target*np.sqrt(w))
        ab[0]=max(ab[0],1e-8)
        coeff.append(ab)
        scaled.append(e/np.sqrt(ab[0]+ab[1]*var[:,p]))
    s=np.concatenate(scaled)
    signed_skew=float(skew(s))
    diag={'absolute_q95':q(np.abs(s),.95),'signed_mean':float(np.mean(s)),
          'signed_skew':signed_skew if np.isfinite(signed_skew) else None}
    supported=bool(1<=diag['absolute_q95']<=3 and abs(diag['signed_mean'])<=.5
                   and diag['signed_skew'] is not None and abs(diag['signed_skew'])<=1)
    return np.array(coeff),diag,supported


def gaussian_score(v,coeff,units,norms):
    n=len(v['flip']);score=v['score'];cls=np.argmax(score,axis=1)
    margins=score[np.arange(n),cls,None]-score
    survival=np.ones(n,dtype=float)
    for j in range(8):
        mask=cls!=j
        if not np.any(mask):continue
        pidx=np.array([PAIRS.index((min(int(i),j),max(int(i),j))) for i in cls[mask]])
        ab=coeff[pidx]
        sd=np.sqrt(ab[:,0]+ab[:,1]*v['pairvar'][mask,pidx])
        distance=margins[mask,j]/norms[cls[mask],j]
        crossing=norm.cdf(-distance/sd)
        survival[mask]*=(1-crossing)
    return 1-survival


def auc_metrics(y,s):
    if len(np.unique(y))<2 or np.std(s)==0:return None,None
    return float(roc_auc_score(y,s)),float(average_precision_score(y,s))


def coverage_row(u,v,s,method,cov):
    idx=np.argsort(s,kind='stable')[:max(1,math.ceil(cov*len(s)))]
    y=v['flip'][idx];cls=v['ygt'][idx]
    supports=[int(np.sum(cls==k)) for k in range(1,9)]
    byclass=[float(1-np.mean(y[cls==k])) if supports[k-1]>0 else None for k in range(1,9)]
    valid=[byclass[k-1] for k in range(1,9) if supports[k-1]>=30]
    return {'user':u,'method':method,'coverage':cov,'accepted':len(idx),
             'flip_risk':float(np.mean(y)),'preservation':float(1-np.mean(y)),
             'balanced_preservation':float(np.mean(valid)) if valid else None,
            'balanced_flip_risk':float(1-np.mean(valid)) if valid else None,
            'supported_classes':[k for k in range(1,9) if supports[k-1]>=30],
            'class_support':supports,'class_preservation':byclass,
            'fisher_error_median':q(v['ef'][idx],.5),'fisher_raw_l2_median':q(v['raw'][idx],.5),
            'probability_tv_median':q(v['tv'][idx],.5),
             'physical_pose_error_median':q(v['pose_error'][idx],.5)}


def class_balanced_quantile(v,s,cov):
    values=[q(s[v['ygt']==k],cov) for k in range(1,9)
            if int(np.sum(v['ygt']==k))>=30]
    if not values:raise RuntimeError('calibration user has no supported reference class')
    return q(values,.5)


def threshold_metrics(v,sel):
    if not sel.any():return {'accepted_flip_risk':None,'accepted_balanced_flip_risk':None,
                            'class_support':[0]*8,'class_flip_risk':[None]*8,'supported_classes':[]}
    y=v['flip'][sel];cls=v['ygt'][sel]
    support=[int(np.sum(cls==k)) for k in range(1,9)]
    risk=[float(np.mean(y[cls==k])) if support[k-1] else None for k in range(1,9)]
    valid=[risk[k-1] for k in range(1,9) if support[k-1]>=30]
    return {'accepted_flip_risk':float(np.mean(y)),
            'accepted_balanced_flip_risk':float(np.mean(valid)) if valid else None,
            'class_support':support,'class_flip_risk':risk,
            'supported_classes':[k for k in range(1,9) if support[k-1]>=30]}


def fixed_scores(v):
    return {k:v[k] for k in ('margin','entropy','boundary_distance',
                              'tta_dispersion','boundary_safety')}


def fold_groups(users,f):
    test=[u for i,u in enumerate(users) if i%5==f]
    rest=sorted(set(users)-set(test))
    cal=[rest[(f+4*i)%len(rest)] for i in range(3)]
    train=[u for u in rest if u not in cal]
    assert len(set(cal))==3 and not(set(test)&set(cal) or set(test)&set(train))
    return train,cal,test


def fit_final(selected,users,data,units,norms):
    cal=[u for i,u in enumerate(users) if i%5==0]
    train=[u for u in users if u not in cal]
    x,y,w,w_gaussian,delta,var=training_pack(train,data)
    model=None;coef=None;diag=None
    if selected=='logistic':model=fit_direct(x,y,w)[0]
    elif selected=='hist_gbdt':model=fit_direct(x,y,w)[1]
    elif selected=='gaussian_crossing':
        coef,diag,supported=fit_gaussian(delta,var,units,w_gaussian)
        if not supported:raise RuntimeError('selected Gaussian fails final DEV adequacy; no rescue')
    model_path=ART/'FINAL_GATE_MODEL.joblib'
    if model_path.exists():raise RuntimeError('refuse overwrite final model')
    joblib.dump({'method':selected,'model':model,'gaussian_coefficients':coef},model_path)
    model_file=model_path.name;model_hash=sha(model_path)
    threshold={}
    for cov in COVERAGES:
        vals=[]
        for u in cal:
            v=data[u]
            score=(model.predict_proba(v['x'])[:,1] if model is not None else
                   gaussian_score(v,coef,units,norms) if coef is not None else v[selected])
            vals.append(class_balanced_quantile(v,score,cov))
        threshold[str(cov)]=q(vals,.5)
    instance={'schema':'gate4f-db9-balanced-customer-instance-v1','method':selected,
              'trained_users':train,'calibration_users':cal,'user_count':19,
              'feature_manifest_sha256':sha(LANE/'FEATURE_MANIFEST.json'),
              'method_manifest_sha256':sha(LANE/'METHOD_MANIFEST.json'),
               'failure_definition_sha256':sha(LANE/'BALANCED_CUSTOMER_REQUIREMENT.md'),
               'training_weighting':'equal users; equal observed reference classes per user; equal observed Flip states per user-class',
               'calibration':'median supported-class score quantile per user, then median calibration users',
              'analysis_code_sha256':sha(Path(__file__)),
              'score_orientation':'lower risk means higher confidence',
              'thresholds_by_nominal_coverage':threshold,
              'model_file':model_file,'model_sha256':model_hash,
              'gaussian_coefficients':coef.tolist() if coef is not None else None,
              'gaussian_training_diagnostic':diag,
              'no_confirmation_users_opened':True}
    return instance


def main():
    m,rows,users,head,sigma,units,norms,residual=load_parent()
    grouped=defaultdict(list)
    for r in rows:grouped[r['participant_id']].append(r)
    data={}
    for i,u in enumerate(users,1):
        data[u]=load_user(grouped[u],m,head,sigma,units,norms)
        print(f'LOAD_DEV {i}/19 {u} {len(data[u]["flip"])}',flush=True)
    # Targets are only read after all plan/code hashes pass.
    by_user=[];counts=np.zeros(8,dtype=np.int64);flips=np.zeros(8,dtype=np.int64)
    for u in users:
        v=data[u];support=np.bincount(v['ygt'].astype(int),minlength=9)[1:9]
        fp=np.array([np.sum(v['flip'][v['ygt']==k]) for k in range(1,9)])
        counts+=support;flips+=fp
        by_user.append({'user':u,'paired_blocks':len(v['flip']),
                        'flip_prevalence':float(np.mean(v['flip'])),
                        'balanced_flip_prevalence':float(np.mean([fp[i]/support[i] for i in range(8) if support[i]>=30])) if np.any(support>=30) else None,
                        'reference_class_support':support.tolist(),
                        'reference_class_flip_prevalence':[(float(fp[i]/support[i]) if support[i] else None) for i in range(8)]})
    pooled_n=int(counts.sum());pooled_flip=int(flips.sum())
    target={'schema':'gate4f-balanced-flip-target-v1','users':by_user,'pooled_blocks_descriptive_only':pooled_n,
            'pooled_flip_prevalence_descriptive_only':pooled_flip/pooled_n,
            'reference_class_support':counts.tolist(),
            'reference_class_flip_prevalence':[(float(flips[i]/counts[i]) if counts[i] else None) for i in range(8)]}
    save('BALANCED_FLIP_TARGET_SUMMARY.json',target)
    print('BALANCED_FLIP_TARGET_SUMMARY_SEALED',flush=True)
    scoremap={k:{} for k in METHODS};folds=[];threshold_rows=[];gdiag=[]
    for f in range(5):
        train,cal,test=fold_groups(users,f)
        x,y,w,w_gaussian,delta,var=training_pack(train,data)
        logistic,gbdt=fit_direct(x,y,w)
        coef,diag,supported=fit_gaussian(delta,var,units,w_gaussian)
        gdiag.append({'fold':f,'supported':supported,**diag})
        fold_scores={}
        for u in cal+test:
            v=data[u];s=fixed_scores(v)
            s['logistic']=logistic.predict_proba(v['x'])[:,1]
            s['hist_gbdt']=gbdt.predict_proba(v['x'])[:,1]
            if supported:s['gaussian_crossing']=gaussian_score(v,coef,units,norms)
            fold_scores[u]=s
        for u in test:
            for method,s in fold_scores[u].items():scoremap[method][u]=s
        for method in METHODS:
            if method=='gaussian_crossing' and not supported:continue
            for cov in COVERAGES:
                threshold=q([class_balanced_quantile(data[u],fold_scores[u][method],cov) for u in cal],.5)
                for u in test:
                    v=data[u];sel=fold_scores[u][method]<=threshold
                    threshold_rows.append({'fold':f,'method':method,'user':u,'nominal_coverage':cov,
                        'threshold':threshold,'achieved_coverage':float(np.mean(sel)),
                        'accepted':int(sel.sum()),**threshold_metrics(v,sel)})
        folds.append({'fold':f,'train_users':train,'calibration_users':cal,'held_out_users':test,
                      'training_blocks':len(y)})
        print(f'FIT_FOLD {f+1}/5 Gaussian_supported={supported}',flush=True)
    d_supported=all(x['supported'] for x in gdiag)
    if not d_supported:
        scoremap.pop('gaussian_crossing')
        threshold_rows=[r for r in threshold_rows if r['method']!='gaussian_crossing']
    rows_out=[];ranks=[];classwise=[];mechanistic=[]
    for u in users:
        v=data[u]
        med=q(v['ef'],.5)
        quad={}
        for small in (True,False):
            for flipped in (False,True):
                mask=((v['ef']<=med)==small)&(v['flip']==int(flipped))
                quad[f'{"small" if small else "large"}_fisher_{"flip" if flipped else "no_flip"}']=int(mask.sum())
        rho=float(spearmanr(v['ef'],v['flip']).statistic) if np.std(v['ef'])>0 and np.std(v['flip'])>0 else None
        mechanistic.append({'user':u,'fisher_median_split':med,'quadrants':quad,
                            'spearman_fisher_error_vs_flip':rho})
        for method,sc in scoremap.items():
            s=sc[u]
            if len(s)!=len(v['flip']) or not np.isfinite(s).all():raise RuntimeError('invalid score')
            auc,ap=auc_metrics(v['flip'],s)
            rho=float(spearmanr(s,v['flip']).statistic) if np.std(s)>0 and np.std(v['flip'])>0 else None
            ranks.append({'user':u,'method':method,'auroc':auc,'auprc':ap,
                          'spearman_score_vs_flip':rho})
            for cov in COVERAGES:
                row=coverage_row(u,v,s,method,cov)
                rows_out.append(row)
                classwise.append({k:row[k] for k in ('user','method','coverage','class_support','class_preservation','balanced_preservation','balanced_flip_risk','supported_classes')})
    aggregate=[]
    for method in scoremap:
        per_user_auc=[];per_user_ordinary_auc=[]
        for u in users:
            rr=[r for r in rows_out if r['method']==method and r['user']==u]
            per_user_auc.append(float(np.trapz([r['balanced_flip_risk'] for r in rr[::-1]],
                                              [r['coverage'] for r in rr[::-1]])) if all(r['balanced_flip_risk'] is not None for r in rr) else None)
            per_user_ordinary_auc.append(float(np.trapz([r['flip_risk'] for r in rr[::-1]],
                                                       [r['coverage'] for r in rr[::-1]])))
        curve=[]
        for cov in COVERAGES:
            rr=[r for r in rows_out if r['method']==method and r['coverage']==cov]
            curve.append({'coverage':cov,**{k:summ([r[k] for r in rr]) for k in
                         ('balanced_flip_risk','flip_risk','preservation','balanced_preservation','fisher_error_median',
                           'probability_tv_median','physical_pose_error_median')}})
        c30=[r for r in rows_out if r['method']==method and r['coverage']==.3]
        c100={r['user']:r for r in rows_out if r['method']==method and r['coverage']==1.}
        worst30=[min(r['class_preservation'][k-1] for k in r['supported_classes']) if r['supported_classes'] else None for r in c30]
        eligible=all(x is not None for x in per_user_auc) and all(x is not None for x in worst30)
        aggregate.append({'method':method,'eligible':eligible,
                          'user_balanced_auc':dict(zip(users,per_user_auc)),
                          'user_ordinary_auc':dict(zip(users,per_user_ordinary_auc)),
                          'median_user_balanced_auc':q(per_user_auc,.5) if eligible else None,
                          'median_user_ordinary_auc':q(per_user_ordinary_auc,.5),'curve':curve,
                          'median_worst_supported_class_preservation_30pct':q(worst30,.5),
                          'users_improved_balanced_at_30pct':sum(r['balanced_flip_risk'] is not None and c100[r['user']]['balanced_flip_risk'] is not None and r['balanced_flip_risk']<c100[r['user']]['balanced_flip_risk'] for r in c30),
                          'median_user_auprc':summ([r['auprc'] for r in ranks if r['method']==method])['median']})
    def key(a):
        curve=a['curve']
        return (a['median_user_balanced_auc'],curve[5]['balanced_flip_risk']['median'],
                curve[6]['balanced_flip_risk']['median'],
                -a['median_worst_supported_class_preservation_30pct'],
                SIMPLICITY.index(a['method']))
    candidates=[a for a in aggregate if a['eligible']]
    if not candidates:raise RuntimeError('no class-supported method eligible; no rescue')
    selected=min(candidates,key=key)['method']
    save('DEV_USER_BALANCED_METRICS.json',{'schema':'gate4f-dev-users-v1','folds':folds,'users':by_user,'ranking_rows':ranks})
    save('BALANCED_RISK_COVERAGE.json',{'schema':'gate4f-balanced-risk-coverage-v1','rows':rows_out,'aggregates':aggregate})
    save('DEPLOYMENT_THRESHOLD_METRICS.json',{'schema':'gate4f-threshold-v1','rows':threshold_rows})
    save('METHOD_COMPARISON.json',{'schema':'gate4f-method-comparison-v1','selected_method':selected,
         'selection_rule':'median user balanced Flip-risk AUC 30%-100%, then 50%, 30%, worst-class preservation, simplicity',
         'gaussian_diagnostics':gdiag,'gaussian_status':'SUPPORTED' if d_supported else 'UNSUPPORTED_GAUSSIAN',
         'methods':[{'method':a['method'],'eligible':a['eligible'],'median_user_balanced_auc':a['median_user_balanced_auc'],
                     'median_user_ordinary_auc':a['median_user_ordinary_auc'],
                     'users_improved_balanced_at_30pct':a['users_improved_balanced_at_30pct']} for a in aggregate]})
    save('FISHER_MECHANISTIC_ANALYSIS.json',{'schema':'gate4f-fisher-mechanistic-v1','users':mechanistic})
    save('CLASSWISE_PRESERVATION.json',{'schema':'gate4f-classwise-v1','rows':classwise})
    instance=fit_final(selected,users,data,units,norms)
    save('FINAL_GATE_INSTANCE.json',instance)
    save('ANALYSIS_SUMMARY.json',{'status':'DEV_METHOD_DEVELOPMENT_COMPLETE',
         'plan_sha256':sha(LANE/'GATE4F_PLAN.md'),'customer_head_sha256':m.HEAD_SHA,
         'dev_users':19,'dev_files':654,'selected_method':selected,
         'final_gate_instance_sha256':sha(ART/'FINAL_GATE_INSTANCE.json'),
         'validation_users_opened':0,'forbidden_gt_predictor_features':False,
         'canonical12_robustness':'DEFERRED_NO_FROZEN_CONSUMER'})
    try:
        import matplotlib;matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        plots=[('balanced_flip_risk','BALANCED_FLIP_RISK_COVERAGE.png'),
               ('flip_risk','ORDINARY_FLIP_RISK_COVERAGE.png'),
               ('balanced_preservation','BALANCED_PRESERVATION_COVERAGE.png')]
        for field,name in plots:
            fig,ax=plt.subplots(figsize=(5.3,3.6))
            for a in aggregate:
                c=a['curve'][::-1]
                ax.plot([r['coverage'] for r in c],[r[field]['median'] for r in c],marker='o',label=a['method'])
            ax.set(xlabel='Accepted coverage',ylabel='User median '+field);ax.legend(fontsize=6)
            fig.tight_layout();fig.savefig(ART/name,dpi=140);plt.close(fig)
        fig,ax=plt.subplots(figsize=(5.3,3.6))
        for u in users:
            rr=[r for r in rows_out if r['method']==selected and r['user']==u][::-1]
            ax.plot([r['coverage'] for r in rr],[r['balanced_flip_risk'] for r in rr],alpha=.45)
        ax.set(xlabel='Accepted coverage',ylabel='Balanced Flip risk',title='Selected gate: held-out users')
        fig.tight_layout();fig.savefig(ART/'PER_USER_BALANCED_RISK_COVERAGE.png',dpi=140);plt.close(fig)
        fig,ax=plt.subplots(figsize=(5.3,3.6))
        for k in range(1,9):
            rr=[r for r in classwise if r['method']==selected and r['coverage']==.5]
            ax.scatter([k]*len(rr),[r['class_preservation'][k-1] for r in rr],alpha=.5,s=14)
        ax.set(xlabel='Reference class',ylabel='Held-out user preservation',title='Selected gate at 50% coverage')
        fig.tight_layout();fig.savefig(ART/'CLASSWISE_PRESERVATION_50PCT.png',dpi=140);plt.close(fig)
        score=np.concatenate([scoremap[selected][u] for u in users]);flip=np.concatenate([data[u]['flip'] for u in users])
        idx=np.argsort(score,kind='stable');bins=np.array_split(idx,10)
        fig,ax=plt.subplots(figsize=(5.3,3.6))
        ax.plot([float(np.median(score[b])) for b in bins],[float(np.mean(flip[b])) for b in bins],marker='o')
        ax.set(xlabel='Gate risk score decile median',ylabel='Observed Flip rate',title='DEV score calibration diagnostic')
        fig.tight_layout();fig.savefig(ART/'PREDICTED_RISK_VS_OBSERVED_FLIP.png',dpi=140);plt.close(fig)
        ef=np.concatenate([data[u]['ef'] for u in users]);flip=np.concatenate([data[u]['flip'] for u in users])
        idx=np.argsort(ef,kind='stable');bins=np.array_split(idx,10)
        fig,ax=plt.subplots(figsize=(5.3,3.6))
        ax.plot([float(np.median(ef[b])) for b in bins],[float(np.mean(flip[b])) for b in bins],marker='o')
        ax.set(xlabel='Fisher task error decile median',ylabel='Observed Flip rate')
        fig.tight_layout();fig.savefig(ART/'FISHER_ERROR_VS_FLIP.png',dpi=140);plt.close(fig)
    except ImportError:pass
    print('GATE4F_DEV_METHOD_DEVELOPMENT_COMPLETE',selected,flush=True)


if __name__=='__main__':main()
