import gc
import json
import time
import warnings

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits

from server_common import *


def train():
    cs=conditions();cfgs={lane:json.loads((PRE/lane/'RESULTS.json').read_text())['config'] for lane in {c['lane'] for c in cs}}
    cfg0=next(iter(cfgs.values()));dev={u:load_old(Path(cfg0['runtime_dev']),u) for u in cfg0['train_users']+cfg0['threshold_users']+cfg0['validation_users']}
    modeldir=HERE/'models';modeldir.mkdir(exist_ok=False);certdir=HERE/'training';certdir.mkdir(exist_ok=False)
    receipts=[];failed=[]
    with threadpool_limits(limits=2),warnings.catch_warnings():
        warnings.simplefilter('error',ConvergenceWarning)
        for ci,c in enumerate(cs):
            cfg=cfgs[c['lane']];tag=c['lane']+'__'+c['name'];data={}
            fisher=np.concatenate([c['lda'].transform((dev[u]['p']-c['consumer'].base.mean)/c['consumer'].base.scale) for u in cfg['train_users']])
            assert np.allclose(fisher.std(0),c['sigma'],atol=1e-12,rtol=0);del fisher
            for u,d in dev.items():
                dd,x=ec.features(d,c);data[u]={**dd,'x':x}
            x,y,wB,ledger=sampled_training(data,cfg['train_users'],5000,None)
            assert ledger==c['contract']['training'] and len(y)==c['contract']['sampled_rows']==65000
            width=2*len(c['consumer'].classes)+3;wU=np.zeros(len(y));offset=0
            for cell in ledger:
                n=cell['sampled_rows'];yy=y[offset:offset+n];ww=wU[offset:offset+n]
                for state in np.unique(yy):ww[yy==state]=1/(len(np.unique(yy))*np.sum(yy==state))
                offset+=n
            wU*=len(wU)/wU.sum()
            sampled_indices={u:np.flatnonzero(data[u]['valid'])[np.linspace(0,np.sum(data[u]['valid'])-1,5000,dtype=np.int64)] for u in cfg['train_users']}
            np.savez_compressed(certdir/(tag+'.npz'),X=x,y=y,wU=wU,wB=wB,
                ref=np.concatenate([data[u]['ref'][sampled_indices[u]] for u in cfg['train_users']]),
                users=np.concatenate([np.full(r['sampled_rows'],r['user']) for r in ledger]))
            for u in cfg['threshold_users']:
                dd=data[u];tp=HERE/'threshold_data'/tag/(u+'.npz');tp.parent.mkdir(parents=True,exist_ok=True)
                np.savez_compressed(tp,X=dd['x'],ref=dd['ref'],pred=dd['pred'],valid=dd['valid'])
            all_models={};selections={};model_receipts={};costs={}
            for goal in ['U','B']:
                for bit in range(8):
                    key=goal+'_'+str(bit);ix=columns(width,x.shape[1],bit)
                    if bit in [0,3,7]:
                        oldkey=goal+'_'+{0:'score_only',3:'full_no_tta',7:'full'}[bit]
                        model=c['gates'][oldkey];r=c['contract']['models'][oldkey]
                        assert sha(r['path'])==r['sha256']
                        model_receipts[key]={'reused':True,'path':r['path'],'sha256':r['sha256'],'columns':ix}
                        selections[key]=c['contract']['selections'][oldkey];costs[key]=0.
                    else:
                        start=time.monotonic()
                        try:
                            if goal=='U':
                                model=HistGradientBoostingClassifier(max_iter=100,max_depth=3,learning_rate=.1,l2_regularization=1.,random_state=0)
                                model.fit(x[:,ix],y,sample_weight=wU)
                            else:model=fit_b(x[:,ix],y,wB)
                        except (ConvergenceWarning,RuntimeError) as exc:
                            failed.append({'consumer':tag,'goal':goal,'feature_bits':bit,'status':'FIT_FAILED_PRESERVED','reason':str(exc)})
                            print('FIT_FAILED_PRESERVED',tag,key,flush=True);continue
                        p=modeldir/(tag+'__'+key+'.joblib');joblib.dump(model,p);costs[key]=time.monotonic()-start
                        model_receipts[key]={'reused':False,'path':str(p),'sha256':sha(p),'columns':ix}
                        risks={u:model.predict_proba(d['x'][:,ix])[:,1] for u,d in data.items()}
                        selections[key]=select(data,risks,goal,c['consumer'].classes,cfg)
                    all_models[key]=model
                    assert model.n_features_in_==len(ix)
                    print('FACTORIAL_MODEL_READY',ci+1,6,tag,key,flush=True)
                    dump(HERE/'PROGRESS.json',{'stage':'factorial_fit','consumers_completed':ci,'current':tag,'last_model':key,'failed_models':len(failed),'pid':os.getpid()})
            receipt={'consumer':tag,'lane':c['lane'],'condition':c['name'],'models':model_receipts,'selections':selections,
                'fit_seconds':costs,'training':ledger,'training_rows':len(y),'sigma':c['sigma'].tolist(),
                'train_users':cfg['train_users'],'threshold_users':cfg['threshold_users'],'validation_users':cfg['validation_users'],
                'training_npz_sha256':sha(certdir/(tag+'.npz')),'consumer_sha256':c['consumer_sha256']}
            dump(HERE/'instances'/(tag+'.json'),receipt);receipts.append(receipt)
            del data,x,y,wU,wB,all_models;gc.collect()
    dump(HERE/'FACTORIAL_FIT_RECEIPT.json',{'status':'COMPLETE_ALL_REQUESTED_FITS_ATTEMPTED','conditions':receipts,'failed':failed,
        'new_models':sum(not m['reused'] for r in receipts for m in r['models'].values()),'originals_reused':sum(m['reused'] for r in receipts for m in r['models'].values())})
    print('FACTORIAL_FIT_COMPLETE',len(receipts),len(failed),flush=True)


def evaluate_all():
    cs=conditions();fit=json.loads((HERE/'FACTORIAL_FIT_RECEIPT.json').read_text());receipts={r['consumer']:r for r in fit['conditions']}
    for c in cs:
        tag=c['lane']+'__'+c['name'];c['new_receipt']=receipts[tag]
        c['factorial_models']={k:joblib.load(r['path']) for k,r in receipts[tag]['models'].items()}
        assert all(sha(r['path'])==r['sha256'] for r in receipts[tag]['models'].values())
    cfg=json.loads((PRE/cs[0]['lane']/'RESULTS.json').read_text())['config']
    groups=[('validation',cfg['validation_users']),('A20',cfg['evaluation_users']),('N80',json.loads((N80/'CACHE_ADMISSION.json').read_text())['users'])]
    costs=[];baseline_deltas=[];rows=[]
    with threadpool_limits(limits=2):
        for cohort,users in groups:
            for ui,user in enumerate(sorted(users)):
                raw,_=ec.load_user(user) if cohort=='N80' else (load_old(Path(cfg['runtime_dev'] if cohort=='validation' else cfg['runtime_eval']),user),None)
                for c in cs:
                    tag=c['lane']+'__'+c['name'];start=time.monotonic();d,x=ec.features(raw,c);feature_seconds=time.monotonic()-start
                    original_risks,deltas,old_costs=verify_old_scores(cohort,user,c,d,x) if cohort!='validation' else ({},{},{})
                    baseline_deltas.append({'cohort':cohort,'user':user,'consumer':tag,'max_risk_difference':max(deltas.values()) if deltas else None})
                    risk_arrays={};masks={}
                    for key,model in c['factorial_models'].items():
                        goal,bit=key.split('_');bit=int(bit);r=c['new_receipt'];ix=r['models'][key]['columns'];start=time.monotonic()
                        risk=original_risks[(goal,bit)] if (goal,bit) in original_risks else model.predict_proba(x[:,ix])[:,1]
                        seconds=old_costs[(goal,bit)] if (goal,bit) in old_costs else time.monotonic()-start;risk_arrays[key]=risk.astype(np.float64)
                        costs.append({'cohort':cohort,'user':user,'consumer':tag,'goal':goal,'feature_bits':bit,
                            'rows':len(x),'features':len(ix),'feature_seconds':feature_seconds,'scorer_seconds':seconds,
                            'cached_original_risk':(goal,bit) in original_risks,'numeric_threads':2})
                        selected=r['selections'][key];th=selected['chosen']['threshold'];mask=np.ones(len(risk),bool) if th is None else risk<=th
                        order=np.argsort(risk,kind='stable')
                        for mode,retention,mask in [('fixed_threshold','',mask)]+[('offline_equal_coverage',q,accepted(risk,q,order)) for q in [.1,.3,.5,.7]]:
                            rows.append({'cohort':cohort,'user':user,'consumer':tag,'goal':goal,'feature_bits':bit,'mode':mode,'retention':retention,
                                'threshold_status':selected['status'],**metrics(d,mask,c['consumer'].classes)})
                    dest=HERE/'factorial_decisions'/cohort/user;dest.mkdir(parents=True,exist_ok=True)
                    p=dest/(tag+'.npz');np.savez_compressed(p,ref=d['ref'],pred=d['pred'],valid=d['valid'],**risk_arrays)
                    dump(p.with_suffix('.json'),{'sha256':sha(p),'rows':len(d['pred']),'classes':c['consumer'].classes.tolist(),'consumer_sha256':c['consumer_sha256']})
                    del d,x,risk_arrays;gc.collect()
                dump(HERE/'PROGRESS.json',{'stage':'factorial_evaluation','cohort':cohort,'completed_users':ui+1,'users':len(users),'pid':os.getpid()})
                print('FACTORIAL_USER_COMPLETE',cohort,ui+1,len(users),flush=True)
    table(HERE/'FACTORIAL_USER_METRICS.csv',rows);table(HERE/'SCORING_COSTS.csv',costs);table(HERE/'BASELINE_NUMERICAL_CHECKS.csv',baseline_deltas)
    dump(HERE/'FACTORIAL_EVALUATION_RECEIPT.json',{'status':'COMPLETE','rows':len(rows),'failed_fits_preserved':fit['failed'],'cohorts':[g[0] for g in groups]})


if __name__=='__main__':
    if sys.argv[1]=='fit':train()
    elif sys.argv[1]=='evaluate':evaluate_all()
    else:raise ValueError('Unknown phase')
