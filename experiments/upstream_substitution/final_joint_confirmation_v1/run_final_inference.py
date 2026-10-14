#!/usr/bin/env python3
"""Run frozen Gate4C upstream and Gate4D TTA on the sealed final cohort."""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
import joblib,numpy as np,torch

LANE=Path(__file__).resolve().parent
ROOT=Path('/root/work/common-pose')
DATA=Path('/root/autodl-tmp/common_pose_final_data')
RESULTS=LANE/'results';TTA=LANE/'tta'
C=ROOT/'experiments/upstream_substitution/gate4c_upstream_substitution_reliability_v1/scripts/run_gate4c.py'
D=ROOT/'experiments/upstream_substitution/gate4d_task_aware_gate_benchmark_v1/analysis/gate4d_analysis.py'
CKPT=Path('/root/models/emg2pose/regression_vemg2pose.ckpt')
HEAD=Path('/root/work/gate3_work/frozen_head/frozen_db9_trusted8_lda.joblib')
HELPER=Path('/root/work/emg2pose_inference/predict_pose.py')
ADAPTER=ROOT/'src/common_pose/representation/canonical_hand.py'
SCALE=ROOT/'experiments/upstream_substitution/gate3b_continuous_representation/artifacts/FISHER_DB9_REFERENCE_SCALE.json'
EXPECTED={str(C):'e3ca8e3b2a7d4a6059ac5fba9d01df264d329f52dc3497fdcc9cfdc0b4e98091',
 str(D):'fea112d6d62bac6dd6e915004137089b18b12a96011f11914c802ab400879f8c',
 str(CKPT):'748b1d1ef0ce1985f6fc07225d97eebfb370243429af803b4997d28ecce2424e',
 str(HEAD):'b0ef8caf8e390a480fa2a3b448f79ccf14f75c71265ef925ee299a5e9e660386',
 str(HELPER):'6cdd060ab639975eb5e2f96bfe43d01371f9f91ec6ecb812c2af2c314bbef818',
 str(ADAPTER):'24694cfda80604148490485d47bf5eddc8e20479d1b55d522ca5d0199b649193',
 str(SCALE):'d15997aa56e5264bdede56c10727a910f94b2c7e32ab8137a6e8e9e45c39c667'}

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()

def import_file(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
 spec.loader.exec_module(m);return m

def paths(r):
 stem=Path(r['source_member']).stem
 return RESULTS/'FINAL'/r['participant_id']/(stem+'.npz'),TTA/r['participant_id']/(stem+'.npz')

def make_base_loader(plan_sha,cohort_sha,runner_sha):
 def load_base(r):
  p,_=paths(r);meta=json.loads(p.with_suffix('.json').read_text())
  if (meta['input_sha256']!=r['sha256'] or meta['output_sha256']!=sha(p) or
      meta['plan_sha256']!=plan_sha or meta['cohort_sha256']!=cohort_sha or
      meta['runner_sha256']!=runner_sha):raise RuntimeError('final base receipt differs '+str(p))
  with np.load(p) as z:return {k:z[k] for k in z.files}
 return load_base

def rows_from_manifest(manifest,cohort_sha):
 rows=[]
 for r in manifest['files']:
  path=DATA/r['user_id']/r['filename']
  receipt=json.loads(path.with_name(path.name+'.receipt.json').read_text())
  if receipt['cohort_sha256']!=cohort_sha or receipt['source_member']!=r['source_member'] or receipt['size']!=r['size']:
   raise RuntimeError('transport receipt differs')
  rows.append({'path':str(path),'size':r['size'],'sha256':receipt['sha256'],
               'source_member':r['source_member'],'participant_id':r['user_id'],'split':'FINAL',
               'session_id':r['session_id']})
 return rows

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run',action='store_true');ap.add_argument('--status',action='store_true')
 args=ap.parse_args()
 if args.run==args.status:raise RuntimeError('choose --run or --status')
 for name in ('FINAL_RUN_PLAN.md','FINAL_COHORT_MANIFEST.json','STRUCTURAL_QUALIFICATION.json'):
  p=LANE/name
  if sha(p)!=p.with_suffix('.sha256').read_text().split()[0]:raise RuntimeError('frozen input differs '+name)
 code=Path(__file__);runner_sha=sha(code)
 if runner_sha!=code.with_suffix('.sha256').read_text().split()[0]:raise RuntimeError('runner code differs')
 structural=json.loads((LANE/'STRUCTURAL_QUALIFICATION.json').read_text())
 if not structural['session_minimum_10000_met'] or len(structural['sessions'])!=20:raise RuntimeError('structural gate failed')
 manifest=json.loads((LANE/'FINAL_COHORT_MANIFEST.json').read_text())
 cohort_sha=sha(LANE/'FINAL_COHORT_MANIFEST.json');plan_sha=sha(LANE/'FINAL_RUN_PLAN.md')
 rows=rows_from_manifest(manifest,cohort_sha)
 if len(rows)!=manifest['total_files']:raise RuntimeError('final file count differs')
 if args.status:
  done=sum(paths(r)[0].exists() and paths(r)[1].exists() for r in rows)
  print('FINAL_INFERENCE_PROGRESS',done,len(rows));return
 for path,expected in EXPECTED.items():
  if sha(Path(path))!=expected:raise RuntimeError('frozen component changed '+path)
 if not torch.cuda.is_available():raise RuntimeError('CUDA unavailable')
 c=import_file('frozen_gate4c',C);d=import_file('frozen_gate4d',D)
 if c.upstream_tree_sha()!=c.UPSTREAM_TREE_SHA:raise RuntimeError('upstream worktree differs')
 sys.path.insert(0,'/root/work/emg2pose_inference');sys.path.insert(0,'/root/work/emg2pose');sys.path.insert(0,str(ROOT))
 from predict_pose import PredictPose
 bundle=joblib.load(HEAD);head,mu,sd=bundle['head'],bundle['mu'],bundle['sd']
 if list(head.classes_)!=list(range(1,9)):raise RuntimeError('customer classes differ')
 sigma=np.array(json.loads(SCALE.read_text())['fisher_component_sigma_db9'],dtype=np.float64)
 model=PredictPose(experiment='regression_vemg2pose',checkpoint=str(CKPT),repo_root='/root/work/emg2pose',device='cuda')
 if model.left_context!=1790 or model.right_context!=0:raise RuntimeError('upstream alignment differs')
 d.paths=paths;d.load_base=make_base_loader(plan_sha,cohort_sha,runner_sha)
 for i,r in enumerate(rows,1):
  base,tta=paths(r)
  if not c.receipt_ok(base,base.with_suffix('.json'),r,plan_sha,cohort_sha,runner_sha):
   c.one(r,model,head,mu,sd,RESULTS,plan_sha,cohort_sha,runner_sha)
  d.tta_one(r,model,head,mu,sd,sigma)
  if i%25==0 or i==len(rows):print(f'FINAL_INFERENCE_PROGRESS {i}/{len(rows)}',flush=True)
 print('FINAL_FROZEN_INFERENCE_COMPLETE',len(rows),flush=True)

if __name__=='__main__':main()
