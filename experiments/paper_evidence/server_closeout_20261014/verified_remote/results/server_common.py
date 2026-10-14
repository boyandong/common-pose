import csv
import gc
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import joblib
import numpy as np

HERE=Path(__file__).resolve().parent
REPO=Path('/root/work/common-pose-db9-no-calibration-20261011')
PRE=Path('/root/autodl-tmp/common_pose_v3_full_tta_ablation_20261012')
OLD_FULL=Path('/root/autodl-tmp/common_pose_v3_full_legacy_20261012')
N80=Path('/root/autodl-tmp/common_pose_n80_all_dataset_supplement_20261012')
REPAIR=Path('/root/autodl-tmp/common_pose_n80_serialization_repair_20261012')
sys.path[:0]=[str(REPO/'src'),str(REPO/'experiments/multi_consumer/db9_scoreonly_v3_20261011'),
    str(REPO/'experiments/multi_consumer/v3_full_tta_ablation_20261012'),
    str(REPO/'experiments/multi_consumer/n80_all_dataset_supplement_20261012')]
import evaluation_common as ec
import run_experiments as original
from run_five import select
from common_pose.workflows.score_only import sampled_training,fit_b,evaluation


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def dump(path,x):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.partial')
    tmp.write_text(json.dumps(x,indent=2,allow_nan=False,default=lambda v:v.item() if isinstance(v,np.generic) else v.tolist())+'\n')
    os.replace(tmp,p)


def table(path,data):
    assert data
    with Path(path).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)


def conditions():
    expected=json.loads((HERE/'EXPECTED_CODE_HASHES.json').read_text())
    assert all(sha(REPO/f)==h for f,h in expected.items())
    cs=[c for c in ec.conditions() if c['scope']=='primary'];assert len(cs)==6
    return cs


def load_old(root,user):
    parts={k:[] for k in ['p','g','valid','group','file','block','views']};starts={}
    for p in sorted((root/user).glob('*.npz')):
        m=json.loads(p.with_suffix('.json').read_text());assert sha(p)==m['output_sha256']
        tp=OLD_FULL/'tta'/user/p.name;tm=json.loads(tp.with_suffix('.json').read_text());assert sha(tp)==tm['output_sha256']
        z=np.load(p,allow_pickle=False);v=np.load(tp,allow_pickle=False);assert np.array_equal(z['block_index'],v['block_index'])
        group=ec.recording_group(m['file']);n=len(z['block_index']);starts[group]=min(starts.get(group,float('inf')),m['time_first'])
        for k,a in [('p',z['pred_pose8']),('g',z['gt_pose8']),('valid',z['gt_valid']),('group',np.full(n,group)),
                    ('file',np.full(n,p.stem)),('block',z['block_index']),('views',v['pose_views'])]:parts[k].append(a)
    d={k:np.concatenate(v) for k,v in parts.items()};d['ordered_groups']=sorted(starts,key=lambda k:(starts[k],ec.recording_key(k)))
    assert np.max(np.abs(d['views'][:,0]-d['p']))<=1e-5
    return d


def columns(width,dimension,bit):
    ix=list(range(width))
    if bit&1:ix+=list(range(width,width+8))
    if bit&2:ix+=list(range(width+8,dimension-2))
    if bit&4:ix+=[dimension-2,dimension-1]
    return ix


def metrics(d,mask,classes):
    valid=d['valid'].astype(bool);kept=mask&valid;p=int(kept.sum());a=int(mask.sum())
    f=int(((d['ref']!=d['pred'])&kept).sum());m=a-p
    support=[int(np.sum(valid&(d['ref']==k))) for k in classes]
    served=[int(np.sum(kept&(d['ref']==k))) for k in classes]
    b=float(np.mean([np.mean(d['ref'][kept&(d['ref']==k)]!=d['pred'][kept&(d['ref']==k)]) for k in classes])) if all(x>=30 for x in support+served) else None
    return {'runtime_n':len(mask),'accepted_n':a,'paired_n':int(valid.sum()),'accepted_paired_n':p,'observed_flips':f,
        'U':f/p if p else None,'B':b,'coverage':a/len(mask) if len(mask) else None,
        'accepted_missing_reference':m,'risk_lower_all_inputs':f/a if a else None,'risk_upper_all_inputs':(f+m)/a if a else None,
        'complete_reference_support':all(x>=30 for x in support),'complete_served_support':all(x>=30 for x in served)}


def accepted(risk,retention,order=None):
    if order is None:order=np.argsort(risk,kind='stable')
    mask=np.zeros(len(risk),bool);mask[order[:int(np.ceil(float(retention)*len(risk)))]]=True
    return mask


def verify_old_scores(cohort,user,c,d,x):
    if cohort=='N80':p=REPAIR/'evaluation'/user/(c['lane']+'__'+c['name']+'.npz')
    else:p=PRE/c['lane']/'decisions'/(c['name']+'_'+user+'.npz')
    receipt=json.loads(p.with_suffix('.json').read_text()) if cohort=='N80' else None
    if receipt:assert sha(p)==receipt['sha256']
    old=np.load(p,allow_pickle=False)
    assert np.array_equal(old['ref'],d['ref']) and np.array_equal(old['pred'],d['pred']) and np.array_equal(old['valid'],d['valid'])
    width=2*len(c['consumer'].classes)+3;result={};deltas={};costs={}
    for bit,key in [(0,'score_only'),(3,'full_no_tta'),(7,'full')]:
        for goal in ['U','B']:
            mk=goal+'_'+key;start=time.monotonic();now=c['gates'][mk].predict_proba(x[:,columns(width,x.shape[1],bit)])[:,1]
            costs[(goal,bit)]=time.monotonic()-start
            delta=float(np.max(np.abs(now-old[mk])));assert delta<1e-8,(c['lane'],c['name'],mk,delta)
            result[(goal,bit)]=old[mk];deltas[mk]=delta
    return result,deltas,costs
