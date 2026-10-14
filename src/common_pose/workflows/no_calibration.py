"""Reusable frozen-pose consumer evaluation with no upstream adaptation.

Only task heads and gate thresholds may be trained by callers. There is no
pose fitting operation in this module. Runtime acceptance never reads GT.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib, json, re
import numpy as np

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(4<<20),b''):h.update(block)
    return h.hexdigest()

def assert_no_calibration(policy):
    for key in ['upstream_training','upstream_calibration','pose_calibration','bias_fit','scale_fit']:
        if policy.get(key,False):raise ValueError('forbidden upstream/pose adaptation: '+key)
    if policy.get('pose_transform','identity')!='identity':raise ValueError('qhat must remain unchanged')

@dataclass(frozen=True)
class FrozenConsumer:
    name:str
    classes:np.ndarray
    mean:np.ndarray
    scale:np.ndarray
    weights:np.ndarray
    intercept:np.ndarray
    @classmethod
    def from_instance(cls,name,instance):
        return cls(name,np.asarray(instance['classes']),np.asarray(instance['source_scaler_mean']),
                   np.asarray(instance['source_scaler_scale']),np.asarray(instance['standardized_coefficients']),
                   np.asarray(instance['standardized_intercepts']))
    def predict(self,q):
        q=np.asarray(q,dtype=np.float64)
        if q.ndim!=2 or q.shape[1]!=len(self.mean) or not np.isfinite(q).all():raise ValueError('invalid pose interface')
        scores=((q-self.mean)/self.scale)@self.weights.T+self.intercept
        winner=scores.argmax(1)
        norms=np.linalg.norm(self.weights[:,None,:]-self.weights[None,:,:],axis=2)[winner]
        norms[np.arange(len(q)),winner]=1
        distance=(scores[np.arange(len(q)),winner,None]-scores)/norms
        distance[np.arange(len(q)),winner]=np.inf
        return self.classes[winner],distance.min(1),scores

def recording_group(name):
    return re.sub(r'_(left|right)$','',Path(str(name)).stem)

def recording_key(name):
    # Native names begin with capture date + Unix capture timestamp; natural
    # sorting prevents recording-10 from preceding recording-2.
    return tuple((0,int(x)) if x.isdigit() else (1,x) for x in re.split(r'(\d+)',str(name)))

def split_groups(names,reserved=5):
    groups=sorted({recording_group(n) for n in names},key=recording_key)
    return groups[:reserved],groups[reserved:]

def gate_threshold(distance,keep_fraction=.3):
    distance=np.asarray(distance,float)
    if not len(distance) or not np.isfinite(distance).all():raise ValueError('no valid prediction-only calibration data')
    return float(np.quantile(distance,1-keep_fraction))

def fidelity_metrics(reference,predicted,mask,classes,min_support=30):
    reference=np.asarray(reference);predicted=np.asarray(predicted);mask=np.asarray(mask,bool)
    if reference.shape!=predicted.shape or mask.shape!=reference.shape:raise ValueError('shape mismatch')
    error=reference!=predicted;n=len(error);accepted=int(mask.sum());per=[]
    fixed=[int(c) for c in classes if int((reference==c).sum())>=min_support]
    for c in classes:
        ix=reference==c;total=int(ix.sum());kept=int((ix&mask).sum())
        per.append(dict(label=int(c),reference_n=total,accepted_n=kept,coverage=kept/total if total else None,
                        flip=float(error[ix&mask].mean()) if kept else None,
                        supported=total>=min_support,service=kept>=min_support))
    served={r['label']:r for r in per}
    evaluable_fixed=bool(fixed) and all(served[c]['accepted_n']>=min_support for c in fixed)
    macro=float(np.mean([served[c]['flip'] for c in fixed])) if evaluable_fixed else None
    expectation=0.
    for c in np.unique(predicted):
        ix=predicted==c;expectation+=int((ix&mask).sum())*float(error[ix].mean())
    random=expectation/accepted if accepted else None
    risk=float(error[mask].mean()) if accepted else None
    return dict(paired_n=n,accepted_n=accepted,paired_coverage=accepted/n if n else None,
                all_accept_flip=float(error.mean()) if n else None,accepted_flip=risk,
                fixed_reference_support_classes=fixed,fixed_support_macro_flip=macro,
                all_classes_reference_supported=len(fixed)==len(classes),
                all_classes_served=all(r['service'] for r in per),
                predicted_class_matched_random_flip=random,
                within_class_benefit=random-risk if random is not None else None),per

def user_interval(values,seed=20261011):
    values=np.asarray([v for v in values if v is not None],float)
    if not len(values):return dict(users=0,median=None,ci95=None)
    rng=np.random.default_rng(seed)
    boots=np.median(values[rng.integers(0,len(values),size=(5000,len(values)))],axis=1)
    return dict(users=len(values),median=float(np.median(values)),ci95=np.quantile(boots,[.025,.975]).tolist(),
                positive=int((values>0).sum()),negative=int((values<0).sum()))
