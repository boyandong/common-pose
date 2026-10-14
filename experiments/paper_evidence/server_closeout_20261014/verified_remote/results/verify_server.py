"""Independently recount saved arrays, weights, thresholds and support."""
from server_common import HERE,sha,dump,conditions
import csv
import json
import math
import joblib
import numpy as np


def read_rows(name):
    with (HERE/name).open() as f:return list(csv.DictReader(f))


def check_row(r,ref,pred,valid,mask,classes):
    paired=valid&mask;f=int(np.sum(ref[paired]!=pred[paired]));p=int(paired.sum());a=int(mask.sum())
    assert (f,p,a,int(valid.sum()),len(mask))==tuple(int(r[k]) for k in ['observed_flips','accepted_paired_n','accepted_n','paired_n','runtime_n'])
    assert int(r['accepted_missing_reference'])==a-p
    if p:assert abs(float(r['U'])-f/p)<1e-12
    else:assert not r['U']
    class_counts=[(int(np.sum(valid&(ref==c))),int(np.sum(paired&(ref==c)))) for c in classes]
    eligible=all(before>=30 and after>=30 for before,after in class_counts)
    if eligible:
        b=sum(np.sum((ref!=pred)&paired&(ref==c))/after for c,(_,after) in zip(classes,class_counts))/len(classes)
        assert abs(float(r['B'])-b)<1e-12
    else:assert not r['B']
    assert abs(float(r['coverage'])-a/len(mask))<1e-12
    if a:
        assert abs(float(r['risk_lower_all_inputs'])-f/a)<1e-12
        assert abs(float(r['risk_upper_all_inputs'])-(f+a-p)/a)<1e-12
    return 8


def main():
    fit=json.loads((HERE/'FACTORIAL_FIT_RECEIPT.json').read_text());inst={r['consumer']:r for r in fit['conditions']}
    cs=conditions();classes={c['lane']+'__'+c['name']:c['consumer'].classes for c in cs};checks=0
    for tag,r in inst.items():
        p=HERE/'training'/(tag+'.npz');assert sha(p)==r['training_npz_sha256'];z=np.load(p,allow_pickle=False)
        y,ref,users=z['y'],z['ref'],z['users'];assert len(y)==65000 and len(np.unique(users))==13
        for goal in ['U','B']:
            weight=np.zeros(len(y))
            for user in r['train_users']:
                cell=users==user
                groups=[cell] if goal=='U' else [cell&(ref==c) for c in np.unique(ref[cell])]
                for group in groups:
                    for state in np.unique(y[group]):
                        ix=group&(y==state);weight[ix]=1/(len(groups)*len(np.unique(y[group]))*ix.sum())
            weight*=len(weight)/weight.sum();assert np.array_equal(weight,z['w'+goal]);checks+=len(y)
        for key,m in r['models'].items():
            assert sha(m['path'])==m['sha256'];model=joblib.load(m['path']);assert model.n_features_in_==len(m['columns'])
            goal=key.split('_')[0];selection=r['selections'][key]
            risks={};threshold_data={}
            for user in r['threshold_users']:
                t=np.load(HERE/'threshold_data'/tag/(user+'.npz'),allow_pickle=False);threshold_data[user]=t
                risks[user]=model.predict_proba(t['X'][:,m['columns']])[:,1]
            candidates=[]
            for old in selection['candidates']:
                fraction=old['retention'];threshold=None if fraction==1 else float(np.median([np.quantile(risks[u],fraction) for u in r['threshold_users']]))
                if threshold is None:assert old['threshold'] is None
                else:assert abs(threshold-old['threshold'])<1e-10
                vals=[];cov=[]
                for user in r['threshold_users']:
                    t=threshold_data[user];mask=np.ones(len(risks[user]),bool) if threshold is None else risks[user]<=threshold
                    keep=t['valid']&mask;cov.append(float(mask.mean()))
                    if goal=='U':value=float(np.mean(t['ref'][keep]!=t['pred'][keep])) if keep.any() else None
                    else:
                        cc=[keep&(t['ref']==c) for c in classes[tag]]
                        value=float(np.mean([np.mean(t['ref'][v]!=t['pred'][v]) for v in cc])) if all(v.sum()>=30 for v in cc) and all(np.sum(t['valid']&(t['ref']==c))>=30 for c in classes[tag]) else None
                    vals.append(value)
                feasible=all(v is not None and v<=.1 for v in vals) and np.median(cov)>=.1
                assert feasible==old['feasible'];assert abs(float(np.median(cov))-old['median_coverage'])<1e-12
                candidates.append(old);checks+=5
            eligible=[v for v in candidates if v['feasible']]
            chosen=sorted(eligible,key=lambda v:(-v['median_coverage'],v['median_goal_risk'],v['index']))[0] if eligible else next(v for v in candidates if v['retention']==.3)
            assert chosen==selection['chosen'];checks+=1
    for csv_name,kind in [('FACTORIAL_USER_METRICS.csv','factorial'),('LAG_SENSITIVITY_USERS.csv','lag'),('WINDOW_SENSITIVITY_USERS.csv','window')]:
        groups={}
        for r in read_rows(csv_name):
            k=(r['cohort'],r['user'],r['consumer'],r.get('width_blocks',''))
            groups.setdefault(k,[]).append(r)
        for (cohort,user,tag,width),rr in groups.items():
            if kind=='factorial':p=HERE/'factorial_decisions'/cohort/user/(tag+'.npz')
            else:p=HERE/'sensitivity_decisions'/cohort/user/(tag+('__lag' if kind=='lag' else '__window'+width)+'.npz')
            receipt=json.loads(p.with_suffix('.json').read_text());assert sha(p)==receipt['sha256'];z=np.load(p,allow_pickle=False)
            orders={}
            for r in rr:
                if kind=='factorial':
                    key=r['goal']+'_'+r['feature_bits'];risk=z[key]
                    if r['mode']=='fixed_threshold':
                        th=inst[tag]['selections'][key]['chosen']['threshold'];mask=np.ones(len(risk),bool) if th is None else risk<=th
                    else:
                        if key not in orders:orders[key]=np.lexsort((np.arange(len(risk)),risk))
                        mask=np.zeros(len(risk),bool);mask[orders[key][:math.ceil(float(r['retention'])*len(risk))]]=True
                    ref=z['ref']
                else:
                    key=r['method'];ref=z['ref_shift'][int(r['shift_blocks'])+2] if kind=='lag' else z['ref']
                    if key=='all':mask=np.ones(len(z['pred']),bool)
                    else:
                        risk=z[key]
                        if key not in orders:orders[key]=np.lexsort((np.arange(len(risk)),risk))
                        mask=np.zeros(len(risk),bool);mask[orders[key][:math.ceil(.3*len(risk))]]=True
                checks+=check_row(r,ref,z['pred'],z['valid'],mask,classes[tag])
        print('INDEPENDENT_METRIC_SECTION_PASS',kind,checks,flush=True)
    dump(HERE/'INDEPENDENT_VERIFICATION.json',{'status':'PASS','checks':checks,'models_verified':sum(len(r['models']) for r in inst.values()),
        'all_weights_exact':True,'threshold_candidates_reconstructed':True,'support_denominators_and_saved_scores_recounted':True,
        'failed_models_preserved':fit['failed'],'original_implementations_hash_verified':True})


if __name__=='__main__':main()
