from threadpoolctl import threadpool_limits
from sklearn.ensemble import HistGradientBoostingClassifier
from server_common import *


def main():
    out=HERE/'score_field_ablation';out.mkdir(exist_ok=False);(out/'models').mkdir()
    cs=conditions();fit=json.loads((HERE/'FACTORIAL_FIT_RECEIPT.json').read_text());instances={r['consumer']:r for r in fit['conditions']}
    models={};selections={};definitions={};training=[];rows=[]
    with threadpool_limits(limits=2):
        for c in cs:
            tag=c['lane']+'__'+c['name'];r=instances[tag];cfg=json.loads((PRE/c['lane']/'RESULTS.json').read_text())['config']
            z=np.load(HERE/'training'/(tag+'.npz'),allow_pickle=False);x,y,w=z['X'],z['y'],z['wU'];k=len(c['consumer'].classes)
            groups={'predicted_class':list(range(k)),'discriminant_scores':list(range(k,2*k)),
                'score_gap':[2*k],'entropy':[2*k+1],'boundary_distance':[2*k+2],
                'TTA_dispersion':[x.shape[1]-2],'TTA_plane_sd':[x.shape[1]-1]}
            td={u:np.load(HERE/'threshold_data'/tag/(u+'.npz'),allow_pickle=False) for u in r['threshold_users']}
            data={u:{'ref':z0['ref'],'pred':z0['pred'],'valid':z0['valid']} for u,z0 in td.items()}
            models[tag]={};selections[tag]={};definitions[tag]={}
            for name,removed in groups.items():
                ix=[j for j in range(x.shape[1]) if j not in removed];start=time.monotonic()
                m=HistGradientBoostingClassifier(max_iter=100,max_depth=3,learning_rate=.1,l2_regularization=1.,random_state=0)
                m.fit(x[:,ix],y,sample_weight=w);p=out/'models'/(tag+'__'+name+'.joblib');joblib.dump(m,p)
                risks={u:m.predict_proba(t['X'][:,ix])[:,1] for u,t in td.items()}
                s=select(data,risks,'U',c['consumer'].classes,cfg);models[tag][name]=m;selections[tag][name]=s;definitions[tag][name]=ix
                training.append({'consumer':tag,'removed_group':name,'columns':ix,'model_path':str(p),'model_sha256':sha(p),
                    'training_npz_sha256':r['training_npz_sha256'],'rows':65000,'fit_seconds':time.monotonic()-start,'selection':s})
                print('SCORE_FIELD_FIT',tag,name,flush=True)
            dump(out/'PROGRESS.json',{'stage':'fit','consumer':tag,'fitted':len(training),'pid':os.getpid()})
        dump(out/'FIT_RECEIPT.json',{'status':'COMPLETE','new_models':len(training),'models':training,'definitions':definitions})
        cfg=json.loads((PRE/cs[0]['lane']/'RESULTS.json').read_text())['config']
        for cohort,users in [('validation',cfg['validation_users']),('A20',cfg['evaluation_users']),('N80',json.loads((N80/'CACHE_ADMISSION.json').read_text())['users'])]:
            for ui,user in enumerate(sorted(users)):
                raw,_=ec.load_user(user) if cohort=='N80' else (load_old(Path(cfg['runtime_dev'] if cohort=='validation' else cfg['runtime_eval']),user),None)
                for c in cs:
                    tag=c['lane']+'__'+c['name'];d,x=ec.features(raw,c)
                    p=HERE/'factorial_decisions'/cohort/user/(tag+'.npz');old=np.load(p,allow_pickle=False)
                    assert np.array_equal(old['ref'],d['ref']) and np.array_equal(old['pred'],d['pred'])
                    risks={'original_full':old['U_7']}
                    for name,m in models[tag].items():risks[name]=m.predict_proba(x[:,definitions[tag][name]])[:,1]
                    for name,risk in risks.items():
                        selection=instances[tag]['selections']['U_7'] if name=='original_full' else selections[tag][name]
                        th=selection['chosen']['threshold'];fixed=np.ones(len(risk),bool) if th is None else risk<=th;order=np.argsort(risk,kind='stable')
                        for mode,q,mask in [('fixed_threshold','',fixed)]+[('offline_equal_coverage',q,accepted(risk,q,order)) for q in [.1,.3,.5,.7]]:
                            rows.append({'cohort':cohort,'user':user,'consumer':tag,'removed_group':name,'mode':mode,'retention':q,
                                'threshold_status':selection['status'],**metrics(d,mask,c['consumer'].classes)})
                    dest=out/'decisions'/cohort/user;dest.mkdir(parents=True,exist_ok=True);p=dest/(tag+'.npz')
                    np.savez_compressed(p,ref=d['ref'],pred=d['pred'],valid=d['valid'],**risks)
                    dump(p.with_suffix('.json'),{'sha256':sha(p),'classes':c['consumer'].classes.tolist()})
                dump(out/'PROGRESS.json',{'stage':'evaluation','cohort':cohort,'users_complete':ui+1,'users':len(users),'pid':os.getpid()})
                print('SCORE_FIELD_USER_COMPLETE',cohort,ui+1,len(users),flush=True)
        table(out/'USER_METRICS.csv',rows);dump(out/'EVALUATION_RECEIPT.json',{'status':'COMPLETE','rows':len(rows),'new_models':42})


if __name__=='__main__':main()
