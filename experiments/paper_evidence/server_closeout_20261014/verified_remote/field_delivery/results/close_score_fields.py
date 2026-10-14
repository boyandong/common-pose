"""Independent verification, paired reporting and sealed delivery for field removals."""
import math
import csv
import json
import tarfile
from collections import defaultdict
import joblib
import numpy as np
from threadpoolctl import threadpool_limits
from server_common import HERE,sha,dump,table,conditions
from verify_server import check_row
from summarize_server import interval


def read(p):
    with p.open() as f:return list(csv.DictReader(f))


def main():
    out=HERE/'score_field_ablation'
    fit=json.loads((out/'FIT_RECEIPT.json').read_text())
    main_fit=json.loads((HERE/'FACTORIAL_FIT_RECEIPT.json').read_text())
    inst={r['consumer']:r for r in main_fit['conditions']}
    classes={c['lane']+'__'+c['name']:c['consumer'].classes for c in conditions()}
    models={(m['consumer'],m['removed_group']):m for m in fit['models']}
    checks=0
    with threadpool_limits(limits=2):
        for (tag,name),r in models.items():
            z=np.load(HERE/'training'/(tag+'.npz'),allow_pickle=False)
            assert sha(HERE/'training'/(tag+'.npz'))==r['training_npz_sha256']
            k=len(classes[tag]);dim=z['X'].shape[1]
            groups={'predicted_class':range(k),'discriminant_scores':range(k,2*k),
                'score_gap':[2*k],'entropy':[2*k+1],'boundary_distance':[2*k+2],
                'TTA_dispersion':[dim-2],'TTA_plane_sd':[dim-1]}
            assert r['columns']==[i for i in range(dim) if i not in groups[name]]
            weight=np.zeros(len(z['y']))
            for u in inst[tag]['train_users']:
                cell=z['users']==u;states=np.unique(z['y'][cell])
                for state in states:
                    ix=cell&(z['y']==state);weight[ix]=1/(len(states)*ix.sum())
            weight*=len(weight)/weight.sum()
            assert np.array_equal(weight,z['wU']);assert len(weight)==65000
            assert sha(r['model_path'])==r['model_sha256']
            model=joblib.load(r['model_path']);assert model.n_features_in_==len(r['columns'])
            params=model.get_params();assert all(params[a]==b for a,b in {'max_iter':100,'max_depth':3,'learning_rate':.1,'l2_regularization':1.,'random_state':0}.items())
            td={u:np.load(HERE/'threshold_data'/tag/(u+'.npz'),allow_pickle=False) for u in inst[tag]['threshold_users']}
            risks={u:model.predict_proba(t['X'][:,r['columns']])[:,1] for u,t in td.items()}
            candidates=[]
            for old in r['selection']['candidates']:
                q=old['retention'];th=None if q==1 else float(np.median([np.quantile(v,q) for v in risks.values()]))
                assert old['threshold'] is None if th is None else abs(th-old['threshold'])<1e-10
                cov=[];values=[]
                for u,t in td.items():
                    mask=np.ones(len(risks[u]),bool) if th is None else risks[u]<=th
                    paired=mask&t['valid'];cov.append(mask.mean());values.append(np.mean(t['ref'][paired]!=t['pred'][paired]) if paired.any() else None)
                feasible=all(v is not None and v<=.1 for v in values) and np.median(cov)>=.1
                assert feasible==old['feasible'];assert abs(np.median(cov)-old['median_coverage'])<1e-12
                assert abs(np.median(values)-old['median_goal_risk'])<1e-12
                candidates.append(old);checks+=5
            eligible=[v for v in candidates if v['feasible']]
            chosen=sorted(eligible,key=lambda v:(-v['median_coverage'],v['median_goal_risk'],v['index']))[0] if eligible else next(v for v in candidates if v['retention']==.3)
            assert chosen==r['selection']['chosen'];checks+=len(weight)+4
    rows=read(out/'USER_METRICS.csv');assert len(rows)==24720 and len(models)==42
    baseline={(r['cohort'],r['consumer'],r['user'],r['mode'],r['retention']):r for r in read(HERE/'FACTORIAL_USER_METRICS.csv') if r['goal']=='U' and r['feature_bits']=='7'}
    groups=defaultdict(list)
    for r in rows:groups[(r['cohort'],r['user'],r['consumer'])].append(r)
    for (cohort,user,tag),rr in groups.items():
        p=out/'decisions'/cohort/user/(tag+'.npz');receipt=json.loads(p.with_suffix('.json').read_text())
        assert sha(p)==receipt['sha256'];z=np.load(p,allow_pickle=False);orders={}
        main=np.load(HERE/'factorial_decisions'/cohort/user/(tag+'.npz'),allow_pickle=False)
        for key in ['ref','pred','valid']:assert np.array_equal(z[key],main[key])
        assert np.array_equal(z['original_full'],main['U_7'])
        for r in rr:
            name=r['removed_group'];risk=z[name]
            if r['mode']=='fixed_threshold':
                s=inst[tag]['selections']['U_7'] if name=='original_full' else models[(tag,name)]['selection']
                th=s['chosen']['threshold'];mask=np.ones(len(risk),bool) if th is None else risk<=th
            else:
                if name not in orders:orders[name]=np.lexsort((np.arange(len(risk)),risk))
                mask=np.zeros(len(risk),bool);mask[orders[name][:math.ceil(float(r['retention'])*len(risk))]]=True
            checks+=check_row(r,z['ref'],z['pred'],z['valid'],mask,classes[tag])
            if name=='original_full':
                old=baseline[(cohort,tag,user,r['mode'],r['retention'])]
                for key in ['U','B','runtime_n','accepted_n','paired_n','accepted_paired_n','observed_flips','coverage']:
                    assert r[key]==old[key];checks+=1
    dump(out/'INDEPENDENT_VERIFICATION.json',{'status':'PASS','checks':checks,'models_verified':42,'rows_verified':len(rows),'original_baseline_exact':True})
    lookup={(r['cohort'],r['consumer'],r['user'],r['removed_group'],r['mode'],r['retention']):r for r in rows};contrasts=[]
    for cohort in ['A20','N80']:
        for tag in sorted(classes):
            users=sorted({r['user'] for r in rows if r['cohort']==cohort and r['consumer']==tag})
            for name in sorted({name for t,name in models if t==tag}):
                for q in ['0.1','0.3','0.5','0.7']:
                    for metric in ['U','B']:
                        paired=[]
                        for user in users:
                            a=lookup[(cohort,tag,user,name,'offline_equal_coverage',q)];b=lookup[(cohort,tag,user,'original_full','offline_equal_coverage',q)]
                            if a[metric] and b[metric]:paired.append({'user':user,'difference':100*(float(a[metric])-float(b[metric]))})
                        md,lo,hi=interval(cohort,paired,'difference')
                        contrasts.append({'cohort':cohort,'consumer':tag,'removed_group':name,'retention':q,'metric':metric,'paired_users':len(paired),'median_reduction_pp':md,'CI95_low_pp':lo,'CI95_high_pp':hi,'status':'UNDEFINED' if not paired else 'LOW_SUPPORT' if len(paired)<10 else 'EXPLORATORY_POINTWISE'})
    table(out/'FIELD_REMOVAL_CONTRASTS.csv',contrasts)
    lines=['# Full/U field-family ablation','',f'42 frozen new fits; {checks} independent checks; 24,720 participant metric rows; original Full/U baseline exactly preserved. All variants are exploratory on previously examined users. Positive differences favor original Full/U; negative differences favor the removal. Pointwise intervals are not simultaneous intervals or independent repetitions. No variant is adopted.','', '|Consumer|Removed group|n|Reduction pp|95% interval|','|---|---|---:|---:|---|']
    for r in contrasts:
        if r['cohort']=='N80' and r['retention']=='0.3' and r['metric']=='U':lines.append(f"|{r['consumer']}|{r['removed_group']}|{r['paired_users']}|{r['median_reduction_pp']:.4f}|[{r['CI95_low_pp']:.4f}, {r['CI95_high_pp']:.4f}]|")
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
    small=[p for p in out.iterdir() if p.is_file() and p.name!='PROGRESS.json']+list((out/'models').glob('*.joblib'))
    small+=[HERE/n for n in ['SCORE_FIELD_SPEC.md','SCORE_FIELD_SEAL.json','score_field_ablation.py','close_score_fields.py','run_score_fields.py']]
    manifest={str(p.relative_to(HERE)):sha(p) for p in sorted(small)};dump(out/'DELIVERY_MANIFEST.json',manifest)
    package=out/'verified_score_fields.tar.gz'
    with tarfile.open(package,'w:gz') as t:
        for p in small+[out/'DELIVERY_MANIFEST.json']:t.add(p,arcname=str(p.relative_to(HERE)),recursive=False)
    dump(out/'FINAL_DELIVERY.json',{'status':'VERIFIED_REMOTE','package':str(package),'package_sha256':sha(package),'bytes':package.stat().st_size,'files':len(manifest),'checks':checks,'models':42})


if __name__=='__main__':main()
