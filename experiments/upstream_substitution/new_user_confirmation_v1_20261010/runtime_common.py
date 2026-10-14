"""Frozen execution seals and append-only receipts for the approved N80 lane."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time

LANE=Path(__file__).resolve().parent
ROOT=LANE.parents[2]
BASE=LANE.parent
DATA=Path('/root/autodl-tmp/common_pose_confirmation_N80_20261010')

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def save(path,obj,overwrite=False):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and not overwrite:raise RuntimeError('refuse overwrite '+str(path))
    tmp=path.with_name(path.name+f'.{os.getpid()}.partial')
    tmp.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    os.replace(tmp,path)
    if not overwrite:path.with_suffix(path.suffix+'.sha256').write_text(sha(path)+'  '+path.name+'\n')

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def frozen(dependencies=True,numeric=False):
    seal=read(LANE/'FROZEN_EXECUTION_MANIFEST.json')
    assert sha(LANE/'FROZEN_EXECUTION_MANIFEST.json')==(LANE/'FROZEN_EXECUTION_MANIFEST.json.sha256').read_text().split()[0]
    for name,h in seal['lane_files'].items():assert sha(LANE/name)==h, name
    if dependencies:
        for name,h in seal['parent_dependencies'].items():assert sha(ROOT/name)==h,name
        for name,h in seal['external_dependencies'].items():assert sha(name)==h,name
    if numeric:
        from importlib.metadata import version
        import platform
        assert platform.python_version()=='3.10.13'
        for pkg,v in seal['numerical_versions'].items():assert version(pkg)==v,(pkg,version(pkg),v)
        for var in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:
            assert os.environ.get(var)=='8',var
        from threadpoolctl import threadpool_info
        assert all(p['num_threads']==8 for p in threadpool_info()),threadpool_info()
    cohort=read(LANE/'ENROLLMENT_MANIFEST.json')
    assert cohort['enrollment_count']==len(set(cohort['enrolled_users']))==80
    assert cohort['no_replacement'] and not cohort['valid_nonzero_pairs_assumed']
    return cohort

def rows(cohort):
    out=[]
    for r in cohort['files']:
        p=DATA/'source'/r['user']/Path(r['source_member']).name
        receipt=read(p.with_name(p.name+'.receipt.json'))
        assert receipt['cohort_sha256']==sha(LANE/'ENROLLMENT_MANIFEST.json')
        assert receipt['source_member']==r['source_member'] and receipt['size']==r['size']
        assert p.stat().st_size==r['size'] and sha(p)==receipt['sha256']
        out.append({**r,'participant_id':r['user'],'session_id':r['session'],
                    'split':'FINAL','path':str(p),'sha256':receipt['sha256']})
    return out

def paths(r):
    stem=Path(r['source_member']).stem
    return (DATA/'base/FINAL'/r['participant_id']/(stem+'.npz'),
            DATA/'tta/FINAL'/r['participant_id']/(stem+'.npz'))

def progress(stage,**fields):
    save(LANE/'PROGRESS.json',{'stage':stage,'observed_epoch':time.time(),'pid':os.getpid(),**fields},overwrite=True)

