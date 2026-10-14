"""Prespecified nominal lag and aggregation tests; never optimize alignment."""
from threadpoolctl import threadpool_limits
from server_common import *

SHIFTS=[-2,-1,0,1,2]


def shifted_references(raw,consumer):
    n=len(raw['p']);maps=np.zeros((5,n),dtype=np.int64);exists=np.zeros((5,n),bool)
    for file in np.unique(raw['file']):
        ix=np.flatnonzero(raw['file']==file);blocks=raw['block'][ix];assert np.all(np.diff(blocks)>0)
        for j,shift in enumerate(SHIFTS):
            target=blocks+shift;pos=np.searchsorted(blocks,target);safe=np.minimum(pos,len(blocks)-1)
            ok=(pos<len(blocks))&(blocks[safe]==target);maps[j,ix]=ix[safe];exists[j,ix]=ok
    common=np.all(exists&raw['valid'][maps],axis=0)
    ref=np.zeros((5,n),np.int16)
    for j in range(5):ref[j,common]=consumer.predict(raw['g'][maps[j,common]])[0]
    return ref,common


def aggregate(raw,width):
    parts={k:[] for k in ['p','g','valid','views','file','block']};discarded=0;rejected=0
    for file in np.unique(raw['file']):
        ix=np.flatnonzero(raw['file']==file);n=len(ix)//width;discarded+=len(ix)-n*width
        if not n:continue
        chunks=ix[:n*width].reshape(n,width)
        consecutive=np.all(np.diff(raw['block'][chunks],axis=1)==1,axis=1)
        rejected+=int((~consecutive).sum());chunks=chunks[consecutive]
        if not len(chunks):continue
        for k in ['p','g','views']:parts[k].append(raw[k][chunks].mean(axis=1))
        parts['valid'].append(raw['valid'][chunks].all(axis=1));parts['file'].append(np.full(len(chunks),file));parts['block'].append(raw['block'][chunks[:,-1]])
    d={k:np.concatenate(v) for k,v in parts.items()};d['group']=d['file'];d['ordered_groups']=[]
    return d,discarded,rejected


def main():
    cs=conditions();cfg=json.loads((PRE/cs[0]['lane']/'RESULTS.json').read_text())['config']
    groups=[('A20',cfg['evaluation_users']),('N80',json.loads((N80/'CACHE_ADMISSION.json').read_text())['users'])]
    lag_rows=[];window_rows=[]
    with threadpool_limits(limits=2):
        for cohort,users in groups:
            for ui,user in enumerate(sorted(users)):
                raw,_=ec.load_user(user) if cohort=='N80' else (load_old(Path(cfg['runtime_eval']),user),None)
                aggregates={1:(raw,0,0),10:aggregate(raw,10),40:aggregate(raw,40)}
                for c in cs:
                    tag=c['lane']+'__'+c['name'];d,x=ec.features(raw,c)
                    original_risks,_,_=verify_old_scores(cohort,user,c,d,x)
                    risks={'boundary':-d['distance'],'score_only':original_risks[('U',0)],
                        'full_no_tta':original_risks[('U',3)],'full':original_risks[('U',7)]}
                    masks={m:accepted(r,.3) for m,r in risks.items()};masks['all']=np.ones(len(x),bool)
                    refs,common=shifted_references(raw,c['consumer'])
                    assert np.array_equal(refs[2,common],d['ref'][common])
                    for j,shift in enumerate(SHIFTS):
                        shifted={**d,'ref':refs[j],'valid':common}
                        for method,mask in masks.items():
                            lag_rows.append({'cohort':cohort,'user':user,'consumer':tag,'shift_blocks':shift,'nominal_ms':shift*20,
                                'method':method,'common_paired_n':int(common.sum()),'original_paired_n':int(d['valid'].sum()),
                                'risk_and_acceptance_unchanged_across_lags':True,**metrics(shifted,mask,c['consumer'].classes)})
                    dest=HERE/'sensitivity_decisions'/cohort/user;dest.mkdir(parents=True,exist_ok=True)
                    p=dest/(tag+'__lag.npz');np.savez_compressed(p,ref_shift=refs,pred=d['pred'],valid=common,**risks)
                    dump(p.with_suffix('.json'),{'sha256':sha(p),'classes':c['consumer'].classes.tolist(),'shifts':SHIFTS})
                    for width,(ag,tail,rejected) in aggregates.items():
                        ad,ax=(d,x) if width==1 else ec.features(ag,c)
                        rr=risks if width==1 else {'boundary':-ad['distance'],**{key:c['gates']['U_'+key].predict_proba(ec.width_view(ax,'U_'+key,2*len(c['consumer'].classes)+3))[:,1] for key in ['score_only','full_no_tta','full']}}
                        for method,risk in {**rr,'all':np.zeros(len(ax))}.items():
                            mask=np.ones(len(ax),bool) if method=='all' else accepted(risk,.3)
                            window_rows.append({'cohort':cohort,'user':user,'consumer':tag,'width_blocks':width,'nominal_ms':width*20,
                                'method':method,'discarded_tail_base_blocks':tail,'nonconsecutive_groups_rejected':rejected,
                                'support_unit':'aggregated_window',**metrics(ad,mask,c['consumer'].classes)})
                        wp=dest/(tag+'__window'+str(width)+'.npz');np.savez_compressed(wp,ref=ad['ref'],pred=ad['pred'],valid=ad['valid'],**rr)
                        dump(wp.with_suffix('.json'),{'sha256':sha(wp),'classes':c['consumer'].classes.tolist(),'width_blocks':width})
                    del d,x,refs,original_risks;gc.collect()
                dump(HERE/'PROGRESS.json',{'stage':'lag_and_window_sensitivity','cohort':cohort,'completed_users':ui+1,'users':len(users),'pid':os.getpid()})
                print('SENSITIVITY_USER_COMPLETE',cohort,ui+1,len(users),flush=True)
    table(HERE/'LAG_SENSITIVITY_USERS.csv',lag_rows);table(HERE/'WINDOW_SENSITIVITY_USERS.csv',window_rows)
    dump(HERE/'SENSITIVITY_RECEIPT.json',{'status':'COMPLETE_PRESPECIFIED_EXPLORATORY_SENSITIVITY','lag_rows':len(lag_rows),
        'window_rows':len(window_rows),'lag_selected':False,'physical_delay_estimated':False,'original_main_results_replaced':False})


if __name__=='__main__':main()
