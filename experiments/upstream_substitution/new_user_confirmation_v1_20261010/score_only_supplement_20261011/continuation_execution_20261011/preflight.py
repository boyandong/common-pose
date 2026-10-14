"""Fresh read-only admission after controller loss; no efficacy values read."""
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from runtime_common import LANE, ROOT, read, save, sha, frozen
from pipeline_supervisor import Supervisor, REMOTE_LANE, local_transfer_gate
from successor_preflight_transport_20261010 import credential, handles, check_file

CONT = Path(__file__).resolve().parent
HERE = CONT.parent

def main():
    cohort = frozen(dependencies=False)
    manifest = read(LANE/'FROZEN_EXECUTION_MANIFEST.json')
    for n,h in manifest['parent_dependencies'].items(): assert sha(ROOT/n)==h,n
    seal = read(HERE/'CODE_SEAL.json')
    assert sha(HERE/'CODE_SEAL.json')=='aebe0573e0e332c923e9c27fb0ee4611b5e10a32ef89bd796d208b51c1f7eec3'
    assert sha(LANE/'ENROLLMENT_MANIFEST.json')=='349efb4b38e6351427cb061d022ead447ca6a4fe9db0d1c9a285c70f8c3b3597'
    assert sha(LANE/'SCIENTIFIC_SPEC.md')==seal['parent_protocol_sha256']
    for n,h in seal['files'].items(): assert sha(HERE/n)==h,n
    for n,h in read(LANE/'ANALYSIS_CODE_SEAL.json')['files'].items(): assert sha(LANE/n)==h,n
    for n,key in [('pipeline_supervisor.py','parent_controller_sha256'),('relay_completed_sources_v3_20261010.py','parent_status_writer_sha256'),('ANALYSIS_CODE_SEAL.json','parent_analysis_code_seal_sha256')]: assert sha(LANE/n)==seal[key]
    assert local_transfer_gate(cohort)
    assert not (HERE/'CONTROLLER_TERMINAL.json').exists()
    assert not (HERE/'EXECUTION_COMPLETE.json').exists()
    local_handles=handles()
    if isinstance(local_handles,dict): local_handles=[local_handles]
    assert all(p['Id']==os.getpid() for p in local_handles), 'Unattributed local Python handle'
    incident=read(HERE/'INCIDENT_FORENSIC_D_BACKUP_VERIFICATION_20261011.json')
    for n,r in incident['files'].items():
        assert sha(Path(incident['local_D_root'])/n)==r['sha256'],n
        if n=='LAST_PARENT_PROGRESS_SNAPSHOT_AT_INCIDENT.json':
            assert not (HERE/n).exists(), 'Snapshot is the preserved D-only forensic copy'
        else: assert sha(HERE/n)==r['sha256'],n
    client=Supervisor(credential())
    try:
        remote=client.rpc(f'''import sys,os,json,shutil,platform
from pathlib import Path
os.environ.update(OMP_NUM_THREADS='8',OPENBLAS_NUM_THREADS='8',MKL_NUM_THREADS='8')
sys.path.insert(0,{REMOTE_LANE!r})
import numpy,torch
from runtime_common import frozen,read,sha,LANE,BASE,DATA,load_module
from threadpoolctl import threadpool_info
from importlib.metadata import version
frozen(numeric=True)
a=read(LANE/'ANALYSIS_CODE_SEAL.json');assert all(sha(LANE/n)==h for n,h in a['files'].items())
p=LANE/'score_only_supplement_20261011';s=read(p/'CODE_SEAL.json');assert sha(p/'CODE_SEAL.json')=={sha(HERE/'CODE_SEAL.json')!r}
assert all(sha(p/n)==h for n,h in s['files'].items())
assert read(p/'RUNTIME_ADMISSION.json')['status']=='PASS'
m=load_module('continuation_upstream',BASE/'gate4c_upstream_substitution_reliability_v1/scripts/run_gate4c.py')
assert m.upstream_tree_sha()==read(LANE/'FROZEN_EXECUTION_MANIFEST.json')['upstream_tree_sha256']
assert torch.__version__=='2.8.0+cu128' and torch.version.cuda=='12.8' and torch.cuda.is_available() and 'RTX 5090 D' in torch.cuda.get_device_name()
stages={{}}
for root,names,prefix in [(LANE,['qualification','reconstruction','support','analysis','verification'],''),(p,['support','analysis','verification','backup_export'],'score_only_supplement_20261011/')]:
 for n in names:
  d=root/'jobs'/n;dispatch=root/('dispatch_'+n+'.json')
  if n in ['qualification','reconstruction'] and root==LANE:
   l=read(d/'LAUNCH.json');t=read(d/'TERMINAL.json')
   assert t['exit_code']==0 and t['output_log_sha256']==sha(d/'output.log') and t['started_epoch']==l['started_epoch']
   assert l['code_seal_sha256']==sha(LANE/'ANALYSIS_CODE_SEAL.json')
   stages[prefix+n]={{'state':'TERMINAL','launch':l,'terminal':t}}
  else:
   assert not d.exists() and not dispatch.exists(),'Unexpected existing stage '+prefix+n
   stages[prefix+n]={{'state':'NOT_DISPATCHED'}}
processes=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:cmd=(proc/'cmdline').read_bytes().split(b'\\0')
 except (FileNotFoundError,PermissionError,ProcessLookupError):continue
 scripts=[Path(x.decode(errors='replace')).name for x in cmd if x.endswith(b'.py')]
 if any(n in scripts for n in ['run_stage_job.py','run_supplement_job.py','reconstruct_users.py','qualify_sources.py','run_integrated_pipeline.py']):processes.append({{'pid':int(proc.name),'scripts':scripts,'start_ticks':(proc/'stat').read_text().split()[21]}})
assert not processes,'Unattributed remote scientific handles'
cache_bytes=sum(q.stat().st_size for folder in ['base','tta','features','scores','score_only_scores'] for q in (DATA/folder).rglob('*') if q.is_file())
print(json.dumps({{'status':'PASS','stages':stages,'scientific_processes':processes,'python':platform.python_version(),'versions':{{k:version(k) for k in read(LANE/'FROZEN_EXECUTION_MANIFEST.json')['numerical_versions']}},'threadpools':threadpool_info(),'torch':torch.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(),'remote_free_bytes':shutil.disk_usage(DATA).free,'existing_cache_bytes_lower_bound':cache_bytes,'source_files':len(list((DATA/'source').rglob('*.hdf5'))),'supplement_files_checked':len(s['files'])}}))
''')
    finally:client.close_connection();client.password=None
    assert remote['source_files']==2768 and remote['remote_free_bytes']>=15_000_000_000
    files=[check_file(r) for r in cohort['files']]
    assert all(r['state']=='COMPLETE_REHASH_PASS' for r in files)
    free=shutil.disk_usage('D:/').free
    assert free>remote['existing_cache_bytes_lower_bound']+5_000_000_000,'Insufficient D backup capacity'
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    result={'status':'PASS_READY_FOR_EXECUTION_ONLY_CONTINUATION','observed_local_time':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'git_head':head,'remote':remote,'local_source_files_rehashed':len(files),'local_source_bytes':sum(r['bytes'] for r in files),'local_D_free_bytes':free,'local_handles':local_handles,'incident_D_files_rehashed':len(incident['files']),'original_controller_exit':'UNKNOWN','original_launch_sha256':sha(HERE/'INTEGRATED_CONTROLLER_LAUNCH_20261011.json'),'incident_sha256':sha(HERE/'INCIDENT_CONTROLLER_LOST_20261011.json'),'effect_values_read':False,'supplement_seal_sha256':sha(HERE/'CODE_SEAL.json')}
    save(CONT/'PREFLIGHT.json',result)
    print(json.dumps(result))

if __name__=='__main__':main()
