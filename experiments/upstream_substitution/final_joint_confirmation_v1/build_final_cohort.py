#!/usr/bin/env python3
"""Freeze N=20 final identities and tar member metadata without HDF5 access."""
from __future__ import annotations
import csv, hashlib, json
from pathlib import Path, PurePosixPath

LANE=Path(__file__).resolve().parent
ROOT=LANE.parents[2]
BASE=ROOT/'experiments/upstream_substitution'
META=Path(r'C:\Users\董伯言\Desktop\fingers\emg2pose_handstate\data\official\emg2pose_dataset_mini\metadata.csv')
INDEX=Path(r'C:\Users\董伯言\Desktop\fingers\emg2pose_handstate\data\priority_pose_subset\raw\tar_index.jsonl')
AUDIT=BASE/'final_untouched_cohort_audit_v1'
B=BASE/'gate4b_multiuser_reliability'
SEED='COMMON_POSE_FINAL_UNTOUCHED_V1|2026-09-24|'

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def read(p):return json.loads(p.read_text(encoding='utf-8'))

def main():
 plan=LANE/'FINAL_RUN_PLAN.md';code=Path(__file__)
 for p in (plan,code):
  if sha(p)!=p.with_suffix('.sha256').read_text().split()[0]:raise RuntimeError(f'unsealed {p}')
 b=read(B/'COHORT_MANIFEST.json');eligible=read(AUDIT/'ELIGIBLE_USER_REGISTRY.json')
 touched=read(AUDIT/'TOUCHED_USER_REGISTRY.json')
 if sha(META)!=b['source']['metadata_csv_sha256'] or sha(INDEX)!=b['source']['tar_index_jsonl_sha256']:
  raise RuntimeError('official metadata/index identity changed')
 reserved={r['participant_id']:r for r in b['selected']}
 final_reserved=[r for r in b['selected'] if r['split']=='FINAL_TEST_LOCKED']
 if len(final_reserved)!=10 or any(r['participant_id'] in {x['user_id'] for x in touched['users']} for r in final_reserved):
  raise RuntimeError('frozen FINAL_TEST reservation differs')
 eligible_ids={r['user_id'] for r in eligible['users']}
 available=sorted(eligible_ids-set(reserved),key=lambda u:(hashlib.sha256((SEED+u).encode()).hexdigest(),u))
 added=available[:10]
 if len(added)!=10:raise RuntimeError('insufficient additional candidates')
 candidate={r['participant_id']:r for r in b['candidate_order']}
 users=[]
 for r in final_reserved:
  users.append({'user_id':r['participant_id'],'role':'PRE_RESERVED_FINAL_TEST','session_id':r['session_id'],
                'official_preflight_files':r['record_count'],'official_preflight_bytes':r['archive_bytes']})
 for u in added:
  r=candidate[u]
  users.append({'user_id':u,'role':'DETERMINISTIC_ADDITIONAL','session_id':r['session_id'],
                'official_preflight_files':r['record_count'],'official_preflight_bytes':r['archive_bytes'],
                'user_order_sha256':hashlib.sha256((SEED+u).encode()).hexdigest()})
 ids={r['user_id'] for r in users}
 if len(ids)!=20 or ids & {x['user_id'] for x in touched['users']}:raise RuntimeError('identity overlap')
 wanted={(r['user_id'],r['session_id']):r for r in users}
 source=[]
 with META.open(newline='',encoding='utf-8-sig') as f:
  for r in csv.DictReader(f):
   if (r['user'],r['session']) in wanted:
    source.append({'user_id':r['user'],'session_id':r['session'],'filename':r['filename']+'.hdf5',
                   'side':r['side'],'official_split':r['split']})
 names={r['filename'] for r in source}
 if len(names)!=len(source):raise RuntimeError('duplicate selected recording')
 members={}
 with INDEX.open(encoding='utf-8') as f:
  for line in f:
   m=json.loads(line);name=PurePosixPath(m['name']).name
   if name in names:
    if name in members:raise RuntimeError('duplicate tar member')
    members[name]=m
 if set(members)!=names:raise RuntimeError('missing selected tar member')
 for r in source:
  m=members[r['filename']]
  if m['typeflag'] not in ('0','\x00') or int(m['size'])<=0:raise RuntimeError('bad tar member')
  r.update({'source_member':m['name'],'archive_header_offset':int(m['offset']),
            'archive_data_offset':int(m['offset'])+512,'size':int(m['size'])})
 source.sort(key=lambda r:(r['user_id'],r['session_id'],r['filename']))
 for u in users:
  own=[r for r in source if r['user_id']==u['user_id']]
  if len(own)!=u['official_preflight_files'] or sum(r['size'] for r in own)!=u['official_preflight_bytes']:
   raise RuntimeError(f'candidate preflight mismatch: {u["user_id"]}')
 out={'schema':'common-pose-final-joint-cohort-v1','status':'IDENTITIES_AND_FILES_FROZEN_BEFORE_NEW_DATA',
      'claim_boundary':'CommonPose-development-untouched users; upstream training exposure unresolved',
      'n_users':20,'n_pre_reserved':10,'n_added':10,'user_hash_seed':SEED,
      'plan_sha256':sha(plan),'builder_sha256':sha(code),
      'touched_registry_sha256':sha(AUDIT/'TOUCHED_USER_REGISTRY.json'),
      'eligible_registry_sha256':sha(AUDIT/'ELIGIBLE_USER_REGISTRY.json'),
      'source':b['source'],'users':users,'files':source,
      'total_files':len(source),'total_bytes':sum(r['size'] for r in source),
      'candidate_scientific_outcomes_opened':False,'upstream_training_membership':'UNKNOWN'}
 p=LANE/'FINAL_COHORT_MANIFEST.json'
 if p.exists():raise RuntimeError('refuse overwrite final manifest')
 p.write_text(json.dumps(out,sort_keys=True,indent=2)+'\n',encoding='utf-8')
 p.with_suffix('.sha256').write_text(f'{sha(p)}  {p.name}\n',encoding='ascii')
 print('FINAL_COHORT_FROZEN',len(users),len(source),out['total_bytes'],sha(p))
 print('ADDITIONAL_USER_IDS',','.join(added))

if __name__=='__main__':main()
