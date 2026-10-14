"""Task-specific frozen score gates, with no target-user calibration."""
import numpy as np
from dataclasses import dataclass
from scipy.special import softmax
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from .no_calibration import fidelity_metrics

@dataclass(frozen=True)
class ScoreGeometryConsumer:
    base: object
    plane_weights: np.ndarray
    @property
    def classes(self):return self.base.classes
    def predict(self,pose):
        predicted,_,scores=self.base.predict(pose);winner=scores.argmax(1)
        norms=np.linalg.norm(self.plane_weights[:,None,:]-self.plane_weights[None,:,:],axis=2)[winner]
        norms[np.arange(len(scores)),winner]=1
        distance=(scores[np.arange(len(scores)),winner,None]-scores)/norms
        distance[np.arange(len(scores)),winner]=np.inf
        return predicted,distance.min(1),scores

def score_geometry(base,lda):
    # Frozen LDA plane normals; no coordinate vector enters the gate.
    basis=lda.scalings_;w=np.linalg.lstsq(basis,lda.coef_.T,rcond=None)[0]
    if np.max(np.abs(basis@w-lda.coef_.T))>=1e-10:
        raise ValueError('frozen LDA decision geometry ambiguous')
    return ScoreGeometryConsumer(base,w.T)

def score_features(consumer,pose):
    predicted,distance,scores=consumer.predict(pose)
    ids=np.array([int(np.flatnonzero(consumer.classes==v)[0]) for v in predicted])
    top=np.sort(scores,axis=1)[:,-2:];prob=softmax(scores,axis=1)
    entropy=-(prob*np.log(np.maximum(prob,1e-12))).sum(axis=1)
    x=np.column_stack([np.eye(len(consumer.classes))[ids],scores,top[:,1]-top[:,0],entropy,distance])
    if x.shape[1]!=2*len(consumer.classes)+3 or not np.isfinite(x).all():
        raise ValueError('invalid score-only feature contract')
    return x,predicted,distance

def sampled_training(data,users,cap=5000,group_budget=None):
    xx=[];yy=[];ww=[];ledger=[]
    for u in users:
        d=data[u];valid=d['valid'].copy()
        if group_budget is not None:valid &= np.isin(d['group'],d['ordered_groups'][:group_budget])
        available=np.flatnonzero(valid)
        if not len(available):raise ValueError('no supervised rows for '+u)
        ix=available[np.linspace(0,len(available)-1,min(cap,len(available)),dtype=np.int64)]
        y=(d['ref'][ix]!=d['pred'][ix]).astype(int);ref=d['ref'][ix];w=np.zeros(len(ix))
        for c in np.unique(ref):
            for z in np.unique(y[ref==c]):
                mask=(ref==c)&(y==z)
                w[mask]=1/(len(np.unique(ref))*len(np.unique(y[ref==c]))*mask.sum())
        xx.append(d['x'][ix]);yy.append(y);ww.append(w)
        ledger.append({'user':u,'available_paired_rows':len(available),'sampled_rows':len(ix),'classes':np.unique(ref).tolist(),'flip_states':np.unique(y).tolist(),'recording_groups':len(np.unique(d['group'][available]))})
    x=np.concatenate(xx);y=np.concatenate(yy);w=np.concatenate(ww);w*=len(w)/w.sum()
    if len(np.unique(y))<2:raise ValueError('only one training Flip state')
    return x,y,w,ledger

def fit_b(x,y,w):
    model=make_pipeline(StandardScaler(),LogisticRegression(C=1,solver='lbfgs',max_iter=300,random_state=0))
    model.fit(x,y,logisticregression__sample_weight=w)
    if int(model[1].n_iter_.max())>=300:raise RuntimeError('logistic gate not converged')
    return model

def evaluation(d,risk,threshold,classes,min_support=30):
    mask=np.ones(len(risk),bool) if threshold is None else risk<=threshold
    valid=d['valid'];metrics,per=fidelity_metrics(d['ref'][valid],d['pred'][valid],mask[valid],classes,min_support)
    accepted=int(mask.sum());unknown=int((mask&~valid).sum());err=int(((d['ref']!=d['pred'])&mask&valid).sum())
    metrics.update(B_full_flip=metrics['fixed_support_macro_flip'] if metrics['all_classes_reference_supported'] and metrics['all_classes_served'] else None,
                   runtime_n=len(mask),runtime_accepted_n=accepted,runtime_coverage=float(mask.mean()),gt_missing_n=int((~valid).sum()),accepted_gt_missing_n=unknown,
                   unknown_risk_lower=err/accepted if accepted else None,unknown_risk_upper=(err+unknown)/accepted if accepted else None)
    return metrics,per,mask

def threshold_candidates(data,risks,users,classes,config):
    rows=[]
    for i,retention in enumerate(config['threshold_grid']):
        th=None if retention==1 else float(np.median([np.quantile(risks[u],retention) for u in users]))
        metrics=[evaluation(data[u],risks[u],th,classes,config['min_class_support'])[0] for u in users]
        macro=[m['fixed_support_macro_flip'] if m['all_classes_reference_supported'] and m['all_classes_served'] else None for m in metrics]
        ordinary=[m['accepted_flip'] for m in metrics]
        coverage=float(np.median([m['runtime_coverage'] for m in metrics]))
        feasible=all(x is not None and x<=config['max_risk'] for x in macro+ordinary) and coverage>=config['min_coverage']
        rows.append(dict(index=i,nominal_retention=retention,threshold=th,feasible=feasible,median_runtime_coverage=coverage,
                         median_macro_flip=float(np.median(macro)) if all(v is not None for v in macro) else None,users=metrics))
    possible=[r for r in rows if r['feasible']]
    chosen=sorted(possible,key=lambda r:(-r['median_runtime_coverage'],r['median_macro_flip'],r['index']))[0] if possible else next(r for r in rows if r['nominal_retention']==.3)
    return dict(status='FEASIBLE' if possible else 'NO_FEASIBLE_THRESHOLD_DIAGNOSTIC_ONLY',chosen=chosen,candidates=rows)
