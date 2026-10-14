#!/usr/bin/env python3
"""Frozen final-input integrity and paired-stream structural qualification."""
from __future__ import annotations
import hashlib,json
from collections import defaultdict
from pathlib import Path
import h5py,numpy as np

LANE=Path(__file__).resolve().parent
DATA=Path('/root/autodl-tmp/common_pose_final_data')

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()

def main():
 for name in ('FINAL_RUN_PLAN.md','FINAL_COHORT_MANIFEST.json'):
  p=LANE/name
  if sha(p)!=p.with_suffix('.sha256').read_text().split()[0]:raise RuntimeError('frozen input differs '+name)
 code=Path(__file__)
 if sha(code)!=code.with_suffix('.sha256').read_text().split()[0]:raise RuntimeError('verifier code differs')
 manifest=json.loads((LANE/'FINAL_COHORT_MANIFEST.json').read_text())
 cohort_sha=sha(LANE/'FINAL_COHORT_MANIFEST.json')
 totals=defaultdict(int);files=[]
 for i,row in enumerate(manifest['files'],1):
  p=DATA/row['user_id']/row['filename'];receipt=p.with_name(p.name+'.receipt.json')
  if not p.exists() or not receipt.exists():raise RuntimeError('missing frozen file '+str(p))
  meta=json.loads(receipt.read_text())
  if p.stat().st_size!=row['size'] or meta['size']!=row['size'] or meta['source_member']!=row['source_member'] or meta['cohort_sha256']!=cohort_sha:
   raise RuntimeError('transport receipt differs '+str(p))
  with h5py.File(p,'r') as h:
   ts=h['emg2pose']['timeseries'];emg=ts['emg'];gt=ts['joint_angles'];times=ts['time']
   n=len(gt)
   if emg.ndim!=2 or emg.shape!=(n,16) or gt.ndim!=2 or gt.shape[1]!=20 or len(times)!=n or n<=1790+80:
    raise RuntimeError('paired stream shape differs '+str(p))
   t=np.asarray(times)
   if not np.isfinite(t).all() or not np.all(np.diff(t)>0):raise RuntimeError('timestamp invalid '+str(p))
   g=np.asarray(gt[1790:]);valid=np.isfinite(g).all(axis=1)&(~np.all(np.isclose(g,0),axis=1))
   blocks=len(g)//40
   valid_blocks=valid[:blocks*40].reshape(blocks,40).all(axis=1)
   valid_blocks[0]=False
   count=int(valid_blocks.sum())
  totals[(row['user_id'],row['session_id'])]+=count
  files.append({'user_id':row['user_id'],'session_id':row['session_id'],'filename':row['filename'],
                'size':row['size'],'transport_sha256':meta['sha256'],
                'source_rows':n,'gt_valid_50hz_blocks':count})
  if i%50==0:print(f'STRUCTURAL_PROGRESS {i}/{manifest["total_files"]}',flush=True)
 if len(files)!=manifest['total_files'] or len(totals)!=20:raise RuntimeError('cohort size differs')
 sessions=[{'user_id':u,'session_id':s,'gt_valid_50hz_blocks':n} for (u,s),n in sorted(totals.items())]
 bad=[r for r in sessions if r['gt_valid_50hz_blocks']<10000]
 out={'schema':'common-pose-final-structural-v1','cohort_sha256':cohort_sha,
      'verifier_sha256':sha(code),'files':files,'sessions':sessions,'session_minimum_10000_met':not bool(bad),
      'bad_sessions':bad,'scientific_model_inference_run':False}
 dest=LANE/'STRUCTURAL_QUALIFICATION.json'
 if dest.exists():raise RuntimeError('refuse overwrite structural result')
 dest.write_text(json.dumps(out,sort_keys=True,indent=2,allow_nan=False)+'\n')
 dest.with_suffix('.sha256').write_text(f'{sha(dest)}  {dest.name}\n')
 if bad:raise RuntimeError('frozen final session below structural validity floor; no replacement')
 print('FINAL_STRUCTURAL_QUALIFICATION_PASS',len(files),len(sessions),flush=True)

if __name__=='__main__':main()
