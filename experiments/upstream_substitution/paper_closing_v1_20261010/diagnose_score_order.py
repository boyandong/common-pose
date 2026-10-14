"""Frozen failing-user numerical control: score precision and exact rank changes.

No fitting, tolerance relaxation or sorting change. Both thread settings are
controls on the same frozen model/cache, not candidate scientific methods.
"""
import csv
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import shutil
import joblib
import numpy as np
from threadpoolctl import threadpool_limits

HERE=Path(__file__).resolve().parent
SRC=HERE.parent/'paper_supplement_v1_20261009'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--saved-score-vectors',type=Path,
                    help='Summarize preserved score vectors; performs no numerical scoring')
    args=ap.parse_args()
    out=HERE/'reproduction_attempt3_8threads/score_order_control';out.mkdir(exist_ok=False)
    user='299b130307';p=SRC/'features/FINAL'/f'{user}.npz'
    seal=json.loads((HERE/'REMOTE_CACHE_VERIFICATION.json').read_text())
    assert sha(p)==next(r['sha256'] for r in seal['features'] if r['user']==user)
    with np.load(p) as z:v={k:z[k] for k in z.files}
    pmodel=SRC/'comparative_analysis/B_class_model_DEV_ONLY.joblib'
    assert sha(pmodel)==pmodel.with_suffix('.sha256').read_text().split()[0]
    model=joblib.load(pmodel);n=len(v['flip']);take=math.ceil(.3*n)
    ties=np.array([int.from_bytes(hashlib.sha256(f'20261009|FINAL|{user}|{i}'.encode()).digest()[:8],'big') for i in range(n)],dtype=np.uint64)
    score={};rank={};risk={}
    if args.saved_score_vectors:
        with np.load(args.saved_score_vectors) as z:
            score={8:z['score_threads8'],1:z['score_threads1']}
        assert all(s.shape==(n,) and np.isfinite(s).all() for s in score.values())
    for threads in [8,1]:
        if not args.saved_score_vectors:
            with threadpool_limits(limits=threads):score[threads]=model.predict_proba(v['x'][:,:8])[:,1]
        rank[threads]=np.lexsort((ties,score[threads]));risk[threads]=float(np.mean(v['flip'][rank[threads][:take]]))
    old=json.loads((HERE/'reproduction_attempt3_8threads/canonical/DIAGNOSIS.json').read_text())
    control=json.loads((HERE/'reproduction_attempt3_8threads/thread1_control/DIAGNOSIS.json').read_text())
    assert old['status']=='PASS'
    target=next(r for r in control['failed_checks'] if r['metric']=='ordinary_risk')
    matched=abs(risk[8]-target['reference'])<1e-12 and abs(risk[1]-target['recovered'])<1e-12
    a=set(rank[8][:take]);b=set(rank[1][:take]);removed=list(map(int,sorted(a-b)));added=list(map(int,sorted(b-a)))
    changed=score[8]!=score[1]
    records=[]
    for k in range(1,9):
        mask=v['ypred']==k
        for threads in [8,1]:
            unique,count=np.unique(score[threads][mask],return_counts=True)
            for s,num in zip(unique,count):records.append({'predicted_class':k,'threads':threads,
                                                          'score_hex':float(s).hex(),'score':float(s),'blocks':int(num)})
    with (out/'CLASS_FLOAT_SCORE_COUNTS.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    if args.saved_score_vectors:shutil.copyfile(args.saved_score_vectors,out/'PRIVATE_SCORE_VECTORS.npz')
    else:np.savez_compressed(out/'PRIVATE_SCORE_VECTORS.npz',score_threads8=score[8],score_threads1=score[1])
    result={'status':'CONTROL_REPRODUCED' if matched else 'CONTROL_DID_NOT_MATCH_SEPARATE_PROCESSES',
            'user':user,'contract':'B','method':'class_model','blocks':n,'accepted':take,
            'risk_threads8':risk[8],'risk_threads1':risk[1],'risk_difference':risk[1]-risk[8],
            'score_changed_blocks':int(changed.sum()),'max_abs_score_difference':float(np.max(np.abs(score[8]-score[1]))),
            'rank_position_changes':int((rank[8]!=rank[1]).sum()),
            'accepted_only_threads8':removed,'accepted_only_threads1':added,
            'removed_flip_sum':int(v['flip'][removed].sum()),'added_flip_sum':int(v['flip'][added].sum()),
            'cache_sha256':sha(p),'model_sha256':sha(pmodel),'code_sha256':sha(Path(__file__)),
            'private_score_sha256':sha(out/'PRIVATE_SCORE_VECTORS.npz'),
            'scoring_origin':'preserved remote score vectors; local serialization repair without rescoring' if args.saved_score_vectors else 'live numerical thread control',
            'original_partial_producer_sha256':'3a72ffd831124666a97f52cdcea7ed586bb3be735cbcd6441a999d9cb661a997' if args.saved_score_vectors else None,
            'interpretation':'same-instance same-cache numerical thread control; floating score strata precede SHA256 ties; no score rounding or new tie definition'}
    (out/'SCORE_ORDER_DIAGNOSIS.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
    return 0 if matched else 2

if __name__=='__main__':sys.exit(main())
