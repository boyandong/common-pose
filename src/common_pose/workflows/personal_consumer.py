"""Personal score adaptation of a frozen consumer; never adapts pose or upstream.

The fitting API accepts predicted scores, independently confirmed y and trial
groups only. Reference pose and evaluation labels are not inputs to adaptation
or gate fitting. Fitting uses equal weight per independent recording group.
"""
from dataclasses import dataclass
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp
from .no_calibration import FrozenConsumer, gate_threshold


@dataclass(frozen=True)
class ScoreAdjustment:
    classes: tuple
    offsets: tuple
    regularization: float
    calibration_rows: int
    calibration_groups: int
    calibration_class_counts: tuple
    fit_objective: float

    @classmethod
    def fit(cls, predicted_scores, confirmed_labels, groups, classes,
            regularization=1.0):
        scores=np.asarray(predicted_scores,dtype=float)
        labels=np.asarray(confirmed_labels)
        groups=np.asarray(groups)
        classes=np.asarray(classes)
        if (scores.ndim!=2 or scores.shape!=(len(labels),len(classes)) or
                labels.ndim!=1 or groups.shape!=labels.shape or len(labels)==0 or
                not np.isfinite(scores).all() or regularization<=0 or
                not np.isfinite(regularization) or len(classes)<2 or
                len(np.unique(classes))!=len(classes)):
            raise ValueError('invalid score-adaptation contract')
        if not np.isin(labels,classes).all():
            raise ValueError('confirmed labels outside fixed task ontology')
        if len(np.unique(labels))<2:
            raise ValueError('personal adaptation requires two observed classes')
        target=np.array([int(np.flatnonzero(classes==y)[0]) for y in labels])
        _,inv,counts=np.unique(groups,return_inverse=True,return_counts=True)
        sample_weight=1.0/(len(counts)*counts[inv])
        # C-1 free parameters; the last offset imposes sum(offsets)=0.
        def unpack(theta):return np.r_[theta,-theta.sum()]
        def objective(theta):
            offsets=unpack(theta);adjusted=scores+offsets
            lse=logsumexp(adjusted,axis=1)
            loss=float(sample_weight@(lse-adjusted[np.arange(len(target)),target]))
            loss+=regularization*.5*float(offsets@offsets)
            probs=np.exp(adjusted-lse[:,None]);probs[np.arange(len(target)),target]-=1
            grad=(sample_weight[:,None]*probs).sum(axis=0)+regularization*offsets
            return loss,grad[:-1]-grad[-1]
        result=minimize(objective,np.zeros(len(classes)-1),jac=True,
                        method='L-BFGS-B',options={'maxiter':200,'ftol':1e-12,'gtol':1e-8})
        if not result.success or not np.isfinite(result.x).all():
            raise RuntimeError('personal score fit failed: '+str(result.message))
        return cls(tuple(int(c) for c in classes),tuple(float(v) for v in unpack(result.x)),
                   float(regularization),len(labels),len(counts),
                   tuple(int((labels==c).sum()) for c in classes),float(result.fun))


@dataclass(frozen=True)
class PersonalConsumer:
    base: FrozenConsumer
    adjustment: ScoreAdjustment

    def predict(self, pose):
        if tuple(int(c) for c in self.base.classes)!=self.adjustment.classes:
            raise ValueError('adjustment belongs to a different task')
        _,_,scores=self.base.predict(pose)
        scores=scores+np.asarray(self.adjustment.offsets)
        winner=scores.argmax(1)
        # W and source scaler are unchanged; intercept-only adjustment moves
        # class planes without redefining the source-normalized metric.
        norms=np.linalg.norm(self.base.weights[:,None,:]-self.base.weights[None,:,:],axis=2)[winner]
        norms[np.arange(len(scores)),winner]=1
        distance=(scores[np.arange(len(scores)),winner,None]-scores)/norms
        distance[np.arange(len(scores)),winner]=np.inf
        return self.base.classes[winner],distance.min(1),scores


def development_threshold(prediction_distances_by_user,keep_fraction=.3):
    """Equal-user median calibration quantile, with no q/y/test-score input."""
    if not prediction_distances_by_user:
        raise ValueError('global threshold needs separate development users')
    return float(np.median([gate_threshold(d,keep_fraction)
                            for d in prediction_distances_by_user.values()]))


def task_metrics(confirmed_y,predictions,mask,classes,min_support=30):
    """Task quality on labelled observations; absent fixed classes stay undefined."""
    y=np.asarray(confirmed_y);pred=np.asarray(predictions);mask=np.asarray(mask,dtype=bool)
    classes=np.asarray(classes)
    if y.shape!=pred.shape or y.shape!=mask.shape or y.ndim!=1:
        raise ValueError('task metric alignment differs')
    if not np.isin(y,classes).all() or not np.isin(pred,classes).all():
        raise ValueError('task metrics require fixed-ontology labels')
    cm=np.array([[int(np.sum((y==a)&(pred==b)&mask)) for b in classes] for a in classes])
    support=cm.sum(1);den=cm.sum(1)+cm.sum(0)
    recall=[float(cm[i,i]/n) if n else None for i,n in enumerate(support)]
    f1=[float(2*cm[i,i]/n) if n else None for i,n in enumerate(den)]
    all_supported=bool(np.all(support>=min_support))
    return dict(labelled_n=len(y),accepted_labelled_n=int(mask.sum()),
                labelled_coverage=float(mask.mean()) if len(y) else None,
                accuracy=float(np.mean(y[mask]==pred[mask])) if mask.any() else None,
                fixed_class_balanced_accuracy=float(np.mean(recall)) if all_supported else None,
                fixed_class_macro_f1=float(np.mean(f1)) if all_supported else None,
                all_label_classes_served=all_supported,classes=classes.tolist(),
                accepted_class_support=support.tolist(),recall=recall,confusion=cm.tolist())
