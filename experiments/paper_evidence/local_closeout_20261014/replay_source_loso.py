"""Reproduce six unchanged source procedures without replacing frozen heads."""
import json
import time
from pathlib import Path

import numpy as np
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from analyze_local import dump, sha, table

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
BASE=ROOT/'experiments/multi_consumer'
SOURCES=[
    ('DB9 posture','db9_no_calibration_v2_20261011/source/C1_legacy.npz','users','sample',False,'db9_no_calibration_v2_20261011/remote_results/source_results/C1_legacy_6_oof.npz','db9_no_calibration_v2_20261011/remote_results/source_results/C1_legacy_6_summary.json'),
    ('DB9 grasp','consumer2_db9c_source_v1_20261011/source_arrays.npz','users','sample',False,'consumer2_db9c_source_v1_20261011/source_predictions.npz','consumer2_db9c_source_v1_20261011/RESULTS.json'),
    ('CeTI posture','ceti_age_scoreonly_v3_20261012/prepared_source/C1_source_blocks.npz','user','block',True,'ceti_age_scoreonly_v3_20261012/verified_source/source_results/C1_full_trial_6_OOF.npz','ceti_age_scoreonly_v3_20261012/verified_source/source_results/C1_budget6_receipt.json'),
    ('CeTI grasp','ceti_age_scoreonly_v3_20261012/prepared_source/C2_source_blocks.npz','user','block',True,'ceti_age_scoreonly_v3_20261012/verified_source/source_results/C2_full_trial_6_OOF.npz','ceti_age_scoreonly_v3_20261012/verified_source/source_results/C2_budget6_receipt.json'),
    ('SHOW instruction','show3d_scoreonly_v3_20261012/prepared_source/C1_source_blocks.npz','user','recording',True,'show3d_scoreonly_v3_20261012/verified_remote/source_results/C1_all_OOF.json','show3d_scoreonly_v3_20261012/verified_remote/source_results/C1_all_receipt.json'),
    ('KIN phase','kinmus_uji_scoreonly_v3_20261012/prepared_source/C1_source_blocks.npz','user','parent_phase',True,'kinmus_uji_scoreonly_v3_20261012/verified_remote/source_results/C1_all_OOF.json','kinmus_uji_scoreonly_v3_20261012/verified_remote/source_results/C1_all_receipt.json'),
]


def replay(out):
    out.mkdir(exist_ok=False);summaries=[];folds=[]
    with threadpool_limits(limits=2):
        for name,rel,ukey,unit,uniform,oldpred,oldreceipt in SOURCES:
            z=np.load(BASE/rel,allow_pickle=False);x,y,u=z['X'],z['y'],z[ukey];classes=np.unique(y)
            assert np.isfinite(x).all();pred=np.empty_like(y);scores=np.full((len(y),len(classes)),np.nan)
            start=time.monotonic();fit_total=0
            for held in np.unique(u):
                train=u!=held;test=~train;assert set(u[train]).isdisjoint(set(u[test]))
                model=make_pipeline(StandardScaler(),LinearDiscriminantAnalysis(solver='svd',priors=np.full(len(classes),1/len(classes)) if uniform else None))
                begin=time.monotonic();model.fit(x[train],y[train]);fit=time.monotonic()-begin;fit_total+=fit
                pred[test]=model.predict(x[test]);scores[test]=model.decision_function(x[test])
                folds.append({'consumer':name,'held_user':str(held),'train_users':len(np.unique(u[train])),
                    'train_rows':int(train.sum()),'test_rows':int(test.sum()),'fit_seconds':fit,'identity_intersection':0})
            if unit in ['recording','parent_phase']:
                units=[]
                for who in np.unique(u):
                    for trial in np.unique(z['trial'][u==who]):
                        mask=(u==who)&(z['trial']==trial);labels=np.unique(y[mask]);assert len(labels)==1
                        units.append({'user':str(who),'trial':str(trial),'y':int(labels[0]),'pred':int(classes[scores[mask].mean(0).argmax()])})
                labels=np.array([r['y'] for r in units]);guesses=np.array([r['pred'] for r in units])
                previous=json.loads((BASE/oldpred).read_text());arch={(str(r['user']),str(r['trial'])):(int(r['y']),int(r['pred'])) for r in previous}
                assert len(arch)==len(units)
                mismatches=sum(arch[(r['user'],r['trial'])]!=(r['y'],r['pred']) for r in units)
                dump(out/(name.replace(' ','_')+'_OOF.json'),units)
            else:
                labels,guesses=y,pred
                with np.load(BASE/oldpred,allow_pickle=False) as prev:
                    assert np.array_equal(prev['y'],y)
                    mismatches=int(np.sum(prev['pred']!=pred))
                np.savez_compressed(out/(name.replace(' ','_')+'_OOF.npz'),y=y,pred=pred,user=u)
            cm=np.array([[np.sum((labels==a)&(guesses==b)) for b in classes] for a in classes])
            ba=float(np.mean(np.diag(cm)/cm.sum(1)))
            receipt=json.loads((BASE/oldreceipt).read_text());expected=receipt['pooled']['ba'] if 'pooled' in receipt else receipt['pooled_balanced_accuracy']
            result={'consumer':name,'users':len(np.unique(u)),'classes':len(classes),'test_units':len(labels),'unit':unit,
                'pooled_BA':ba,'archived_BA':expected,'prediction_mismatches':mismatches,
                'fold_fit_seconds':fit_total,'wall_seconds':time.monotonic()-start,'source_input_sha256':sha(BASE/rel),
                'status':'PASS_EXACT_OOF_REPRODUCTION' if mismatches==0 and abs(ba-expected)<1e-12 else 'REPRODUCTION_MISMATCH'}
            summaries.append(result);dump(out/(name.replace(' ','_')+'_receipt.json'),result)
            print('SOURCE_REPLAY',name,result['status'],round(100*ba,5),flush=True)
            if result['status']!='PASS_EXACT_OOF_REPRODUCTION':break
    table(out/'SOURCE_LOSO_REPRODUCTION.csv',summaries);table(out/'SOURCE_LOSO_FOLDS.csv',folds)
    dump(out/'SOURCE_REPLAY_RECEIPT.json',{'status':'PASS' if len(summaries)==6 and all(r['status']=='PASS_EXACT_OOF_REPRODUCTION' for r in summaries) else 'INCOMPLETE_OR_MISMATCH',
        'consumers':len(summaries),'folds':len(folds),'original_heads_replaced':False,'new_independent_test_cohort':False})


if __name__=='__main__':replay(HERE/'results/source_replay')
