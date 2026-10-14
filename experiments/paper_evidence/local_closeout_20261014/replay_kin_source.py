"""Finish KIN using its original user/parent/phase grouping; keep first five passes."""
import json
import time

import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from threadpoolctl import threadpool_limits

from analyze_local import dump, table, sha
from replay_source_loso import HERE, BASE, SOURCES


def main():
    out=HERE/'results/source_replay';source=SOURCES[-1];name,rel,ukey,unit,uniform,oldpred,oldreceipt=source
    z=np.load(BASE/rel,allow_pickle=False);x,y,u=z['X'],z['y'],z[ukey];classes=np.unique(y);scores=np.full((len(y),3),np.nan)
    start=time.monotonic();fit_total=0;kin_folds=[]
    with threadpool_limits(limits=2):
        for held in np.unique(u):
            train=u!=held;test=~train
            model=make_pipeline(StandardScaler(),LinearDiscriminantAnalysis(solver='svd',priors=np.full(3,1/3)))
            begin=time.monotonic();model.fit(x[train],y[train]);fit=time.monotonic()-begin;fit_total+=fit
            scores[test]=model.decision_function(x[test])
            kin_folds.append({'consumer':name,'held_user':str(held),'train_users':len(np.unique(u))-1,
                'train_rows':int(train.sum()),'test_rows':int(test.sum()),'fit_seconds':fit,'identity_intersection':0})
    units=[]
    for who in np.unique(u):
        for trial in np.unique(z['trial'][u==who]):
            for phase in classes:
                mask=(u==who)&(z['trial']==trial)&(y==phase)
                if mask.any():units.append({'user':int(who),'trial':int(trial),'y':int(phase),
                    'pred':int(classes[scores[mask].mean(0).argmax()])})
    previous=json.loads((BASE/oldpred).read_text())
    archived={(int(r['user']),int(r['trial']),int(r['y'])):int(r['pred']) for r in previous}
    assert len(archived)==len(units)==1478
    mismatch=sum(archived[(r['user'],r['trial'],r['y'])]!=r['pred'] for r in units)
    labels=np.array([r['y'] for r in units]);pred=np.array([r['pred'] for r in units])
    cm=np.array([[np.sum((labels==a)&(pred==b)) for b in classes] for a in classes]);ba=float(np.mean(np.diag(cm)/cm.sum(1)))
    expected=json.loads((BASE/oldreceipt).read_text())['pooled']['ba']
    assert mismatch==0 and abs(ba-expected)<1e-12
    result={'consumer':name,'users':22,'classes':3,'test_units':1478,'unit':unit,'pooled_BA':ba,'archived_BA':expected,
        'prediction_mismatches':mismatch,'fold_fit_seconds':fit_total,'wall_seconds':time.monotonic()-start,
        'source_input_sha256':sha(BASE/rel),'status':'PASS_EXACT_OOF_REPRODUCTION'}
    dump(out/'KIN_phase_OOF.json',units);dump(out/'KIN_phase_receipt.json',result)
    summaries=[json.loads((out/(s[0].replace(' ','_')+'_receipt.json')).read_text()) for s in SOURCES]
    assert len(summaries)==6 and all(r['status']=='PASS_EXACT_OOF_REPRODUCTION' for r in summaries)
    folds=[]
    for s in SOURCES[:-1]:
        src=np.load(BASE/s[1],allow_pickle=False);usr=src[s[2]]
        for held in np.unique(usr):
            folds.append({'consumer':s[0],'held_user':str(held),'train_users':len(np.unique(usr))-1,
                'train_rows':int(np.sum(usr!=held)),'test_rows':int(np.sum(usr==held)),
                'fit_seconds':None,'identity_intersection':0})
    folds+=kin_folds;assert len(folds)==249
    table(out/'SOURCE_LOSO_REPRODUCTION.csv',summaries);table(out/'SOURCE_LOSO_FOLDS.csv',folds)
    dump(out/'SOURCE_REPLAY_RECEIPT.json',{'status':'PASS','consumers':6,'folds':249,'original_heads_replaced':False,
        'new_independent_test_cohort':False,'KIN_scored_unit':'user,parent_recording,phase',
        'implementation_correction':'Original probe grouped KIN by user/trial only and stopped; source contract requires phase too. Five successful source fits were retained, not rerun.'})
    print('KIN_CORRECT_GROUPING_EXACT_REPRODUCTION',100*ba,'ALL_SIX_PASS',flush=True)


if __name__=='__main__':main()
