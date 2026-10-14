#!/usr/bin/env python3
"""Evaluate two frozen customer contracts on twenty final users, without fitting."""
from __future__ import annotations
import hashlib,importlib.util,json,math,os
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
import joblib,numpy as np
from scipy.stats import binomtest

LANE=Path(__file__).resolve().parent
ROOT=Path('/root/work/common-pose');BASE=ROOT/'experiments/upstream_substitution'
E=BASE/'gate4e_customer_flip_gate_v1';F=BASE/'gate4f_class_balanced_flip_gate_v1'
HEAD=Path('/root/work/gate3_work/frozen_head/frozen_db9_trusted8_lda.joblib')
SCALE=BASE/'gate3b_continuous_representation/artifacts/FISHER_DB9_REFERENCE_SCALE.json'
USER_ART=LANE/'artifacts/users';COVERAGES=[1.,.9,.8,.7,.6,.5,.3]

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()

def check(p):
 if sha(p)!=p.with_suffix('.sha256').read_text().split()[0]:raise RuntimeError('frozen hash differs '+str(p))

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
 spec.loader.exec_module(m);return m

def save(p,obj):
 if p.exists():raise RuntimeError('refuse overwrite '+str(p))
 p.parent.mkdir(parents=True,exist_ok=True)
 tmp=p.with_name(p.name+f'.{os.getpid()}.partial')
 tmp.write_text(json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n')
 os.replace(tmp,p);p.with_suffix('.sha256').write_text(f'{sha(p)}  {p.name}\n')

def summarize(values):
 v=np.array([x for x in values if x is not None and np.isfinite(x)],dtype=float)
 return {'n':int(len(v)),'median':float(np.median(v)) if len(v) else None,
         'q25':float(np.quantile(v,.25)) if len(v) else None,
         'q75':float(np.quantile(v,.75)) if len(v) else None,
         'min':float(np.min(v)) if len(v) else None,
         'max':float(np.max(v)) if len(v) else None}

def main():
 for name in ('FINAL_RUN_PLAN.md','FINAL_COHORT_MANIFEST.json','STRUCTURAL_QUALIFICATION.json'):
  check(LANE/name)
 check(Path(__file__))
 cohort=json.loads((LANE/'FINAL_COHORT_MANIFEST.json').read_text())
 structural=json.loads((LANE/'STRUCTURAL_QUALIFICATION.json').read_text())
 if not structural['session_minimum_10000_met'] or cohort['n_users']!=20:raise RuntimeError('final input gate differs')
 for lane in (E,F):
  for name in ('FEATURE_MANIFEST.json','METHOD_MANIFEST.json','COHORT_MANIFEST.json'):
   check(lane/name)
  check(lane/'artifacts/FINAL_GATE_INSTANCE.json')
  instance=json.loads((lane/'artifacts/FINAL_GATE_INSTANCE.json').read_text())
  if sha(lane/'artifacts/FINAL_GATE_MODEL.joblib')!=instance['model_sha256']:
   raise RuntimeError('frozen gate model differs')
 e_instance=json.loads((E/'artifacts/FINAL_GATE_INSTANCE.json').read_text())
 f_instance=json.loads((F/'artifacts/FINAL_GATE_INSTANCE.json').read_text())
 if e_instance['method']!='hist_gbdt' or f_instance['method']!='logistic':raise RuntimeError('selected family differs')
 e_model=joblib.load(E/'artifacts/FINAL_GATE_MODEL.joblib')
 f_bundle=joblib.load(F/'artifacts/FINAL_GATE_MODEL.joblib')
 f_model=f_bundle['model']
 if f_bundle['method']!='logistic' or f_model is None:raise RuntimeError('Gate4F model package differs')
 e=load('gate4e_frozen',E/'analysis/gate4e_flip_gate.py')
 if sha(E/'analysis/gate4e_flip_gate.py')!=e_instance['analysis_code_sha256']:
  raise RuntimeError('Gate4E code differs')
 if sha(F/'analysis/gate4f_balanced_gate.py')!=f_instance['analysis_code_sha256']:
  raise RuntimeError('Gate4F code differs')
 head_bundle=joblib.load(HEAD);head=head_bundle['head']
 if sha(HEAD)!='b0ef8caf8e390a480fa2a3b448f79ccf14f75c71265ef925ee299a5e9e660386':
  raise RuntimeError('DB9 head differs')
 sigma=np.array(json.loads(SCALE.read_text())['fisher_component_sigma_db9'],dtype=np.float64)
 if sha(SCALE)!='d15997aa56e5264bdede56c10727a910f94b2c7e32ab8137a6e8e9e45c39c667':
  raise RuntimeError('Fisher scale differs')
 S=head.scalings_;W=np.linalg.lstsq(S,head.coef_.T,rcond=None)[0]
 if float(np.max(np.abs(S@W-head.coef_.T)))>=1e-10:raise RuntimeError('Fisher geometry differs')
 units=[];norms=np.empty((8,8))
 for i,j in e.PAIRS:
  delta=W[:,i]-W[:,j];norm=float(np.linalg.norm(delta));units.append(delta/norm);norms[i,j]=norms[j,i]=norm
 np.fill_diagonal(norms,np.inf);units=np.array(units).T
 infer=load('final_inference_receipts',LANE/'run_final_inference.py')
 check(LANE/'run_final_inference.py')
 cohort_sha=sha(LANE/'FINAL_COHORT_MANIFEST.json');plan_sha=sha(LANE/'FINAL_RUN_PLAN.md')
 m=SimpleNamespace(paths=infer.paths,load_base=infer.make_base_loader(plan_sha,cohort_sha,sha(LANE/'run_final_inference.py')))
 grouped=defaultdict(list)
 for row in infer.rows_from_manifest(cohort,cohort_sha):grouped[row['participant_id']].append(row)
 ordered=[r['user_id'] for r in cohort['users']]
 if set(ordered)!=set(grouped) or len(ordered)!=20:raise RuntimeError('cohort grouping differs')
 for i,user in enumerate(ordered,1):
  p=USER_ART/(user+'.json')
  if p.exists():
   check(p);prior=json.loads(p.read_text())
   if prior['cohort_sha256']!=cohort_sha or prior['e_model_sha256']!=e_instance['model_sha256'] or prior['f_model_sha256']!=f_instance['model_sha256']:
    raise RuntimeError('existing user result identity differs')
   continue
  v=e.load_user(grouped[user],m,head,sigma,units,norms)
  if len(v['flip'])==0 or v['x'].shape[1]!=36:raise RuntimeError('empty/invalid final user')
  scores={'Gate4E_Requirement_U':e_model.predict_proba(v['x'])[:,1],
          'Gate4F_Requirement_B':f_model.predict_proba(v['x'])[:,1]}
  gates={}
  for name,sc in scores.items():
   if not np.isfinite(sc).all():raise RuntimeError('nonfinite frozen gate score')
   instance=e_instance if name.startswith('Gate4E') else f_instance
   auc,ap=e.auc_metrics(v['flip'],sc)
   curve=[];thresholds=[]
   for cov in COVERAGES:
    curve.append(e.coverage_row(user,v,sc,name,cov))
    threshold=instance['thresholds_by_nominal_coverage'][str(cov)]
    accepted=sc<=threshold
    thresholds.append({'nominal_coverage':cov,'achieved_coverage':float(np.mean(accepted)),
                       'threshold':threshold,'accepted':int(accepted.sum())})
   # The frozen Gate4E module has no threshold_metrics helper; evaluate identically here.
   for t,cov in zip(thresholds,COVERAGES):
    accepted=sc<=t['threshold'];n=int(accepted.sum())
    cls=v['ygt'][accepted];flip=v['flip'][accepted]
    support=[int(np.sum(cls==k)) for k in range(1,9)]
    risk=[float(np.mean(flip[cls==k])) if support[k-1] else None for k in range(1,9)]
    valid=[risk[k-1] for k in range(1,9) if support[k-1]>=30]
    t.update({'accepted_flip_risk':float(np.mean(flip)) if n else None,
              'accepted_balanced_flip_risk':float(np.mean(valid)) if valid else None,
              'class_support':support,'class_flip_risk':risk,'supported_classes':[k for k in range(1,9) if support[k-1]>=30]})
   baseline=curve[0];low=curve[-1]
   b0=1-baseline['balanced_preservation'] if baseline['balanced_preservation'] is not None else None
   b30=1-low['balanced_preservation'] if low['balanced_preservation'] is not None else None
   gates[name]={'auroc':auc,'auprc':ap,'fixed_coverage_curve':curve,'deployment_threshold_rows':thresholds,
                'ordinary_risk_reduction_100_to_30':baseline['flip_risk']-low['flip_risk'],
                'balanced_risk_reduction_100_to_30':b0-b30 if b0 is not None and b30 is not None else None}
  save(p,{'schema':'common-pose-final-user-v1','user_id':user,'paired_blocks':len(v['flip']),
          'cohort_sha256':cohort_sha,'e_model_sha256':e_instance['model_sha256'],
          'f_model_sha256':f_instance['model_sha256'],'gates':gates})
  if i%5==0:print(f'FINAL_EVAL_PROGRESS {i}/20',flush=True)
 users=[json.loads((USER_ART/(u+'.json')).read_text()) for u in ordered]
 primary={}
 for gate,field in [('Gate4E_Requirement_U','ordinary_risk_reduction_100_to_30'),
                    ('Gate4F_Requirement_B','balanced_risk_reduction_100_to_30')]:
  values=[u['gates'][gate][field] for u in users]
  defined=all(v is not None for v in values)
  positive=sum(v is not None and v>0 for v in values)
  p=float(binomtest(positive,20,.5,alternative='greater').pvalue) if defined else None
  primary[gate]={'effect':summarize(values),'positive_users':positive,'defined_users':sum(v is not None for v in values),
                 'raw_one_sided_sign_p':p,'per_user_effect':dict(zip(ordered,values))}
 valid=[(k,v['raw_one_sided_sign_p']) for k,v in primary.items() if v['raw_one_sided_sign_p'] is not None]
 if len(valid)==2:
  sorted_p=sorted(valid,key=lambda x:x[1]);adjusted={};running=0
  for rank,(k,p) in enumerate(sorted_p):
   running=max(running,min(1.,p*(2-rank)));adjusted[k]=running
  for k in primary:
   primary[k]['holm_adjusted_p']=adjusted[k]
   primary[k]['passes_prespecified_test']=bool(adjusted[k]<.05 and primary[k]['effect']['median']>0)
 else:
  for k in primary:primary[k]['holm_adjusted_p']=None;primary[k]['passes_prespecified_test']=False
 curves={}
 for gate in ('Gate4E_Requirement_U','Gate4F_Requirement_B'):
  curves[gate]=[]
  for cov in COVERAGES:
   rows=[next(r for r in u['gates'][gate]['fixed_coverage_curve'] if r['coverage']==cov) for u in users]
   curves[gate].append({'coverage':cov,'ordinary_flip_risk':summarize([r['flip_risk'] for r in rows]),
                        'balanced_flip_risk':summarize([1-r['balanced_preservation'] if r['balanced_preservation'] is not None else None for r in rows]),
                        'supported_class_count':summarize([sum(n>=30 for n in r['class_support']) for r in rows])})
 out={'schema':'common-pose-final-joint-confirmation-v1','status':'FINAL_UNTOUCHED_USER_SYSTEM_CONFIRMATION_COMPLETE',
      'claim_boundary':cohort['claim_boundary'],'cohort_sha256':cohort_sha,
      'plan_sha256':plan_sha,'n_users':20,'n_files':cohort['total_files'],'user_ids':ordered,
      'Gate4E_model_sha256':e_instance['model_sha256'],'Gate4F_model_sha256':f_instance['model_sha256'],
      'primary_endpoints':primary,'fixed_coverage_curves':curves,
      'candidate_users_outside_cohort_opened':False,'upstream_retrained':False,
      'gate_retrained_or_retuned':False,'all_user_receipts':[sha(USER_ART/(u+'.json')) for u in ordered]}
 save(LANE/'FINAL_CONFIRMATION_RESULTS.json',out)
 print('FINAL_JOINT_CONFIRMATION_COMPLETE',flush=True)

if __name__=='__main__':main()
