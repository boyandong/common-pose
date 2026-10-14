"""Fresh successor evidence; preserve frozen scripts and historical receipts."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from runtime_common import LANE, ROOT, read, save, sha, frozen
from pipeline_supervisor import Supervisor, REMOTE_LANE, local_transfer_gate
from successor_preflight_transport_20261010 import credential, handles, check_file

HERE = Path(__file__).resolve().parent

def main():
    cohort = frozen(dependencies=False)
    parent = read(LANE/'FROZEN_EXECUTION_MANIFEST.json')
    for name, digest in parent['parent_dependencies'].items():
        assert sha(ROOT/name) == digest, name
    seal = read(HERE/'CODE_SEAL.json')
    assert sha(HERE/'CODE_SEAL.json') == (HERE/'CODE_SEAL.json.sha256').read_text().split()[0]
    for name, digest in seal['files'].items():
        assert sha(HERE/name) == digest, name
    for name, key in [('ANALYSIS_CODE_SEAL.json','parent_analysis_code_seal_sha256'), ('pipeline_supervisor.py','parent_controller_sha256'), ('relay_completed_sources_v3_20261010.py','parent_status_writer_sha256'), ('SCIENTIFIC_SPEC.md','parent_protocol_sha256')]:
        assert sha(LANE/name) == seal[key], name
    for name, digest in read(LANE/'ANALYSIS_CODE_SEAL.json')['files'].items():
        assert sha(LANE/name) == digest, name
    assert local_transfer_gate(cohort)
    for name in ['ACQUISITION_COMPLETE.json','LOCAL_RELAY_COMPLETE.json']:
        assert sha(LANE/name) == (LANE/(name+'.sha256')).read_text().split()[0]
    local_handles = handles()
    if isinstance(local_handles, dict): local_handles=[local_handles]
    assert all(h['Id']==os.getpid() for h in local_handles), 'Local Python handles need attribution before launch'
    for name in ['INTEGRATED_CONTROLLER_LAUNCH_20261011.json','CONTROLLER_TERMINAL.json','EXECUTION_COMPLETE.json']:
        assert not (HERE/name).exists(), 'Existing integrated execution evidence: '+name
    controller = Supervisor(credential())
    try:
        remote = controller.rpc(f'''import sys,os,json,shutil,platform,subprocess
from pathlib import Path
os.environ.update(OMP_NUM_THREADS='8',OPENBLAS_NUM_THREADS='8',MKL_NUM_THREADS='8')
sys.path.insert(0,{REMOTE_LANE!r})
import numpy,torch
from runtime_common import frozen,read,sha,LANE,BASE,load_module
from importlib.metadata import version
from threadpoolctl import threadpool_info
c=frozen(numeric=True);a=read(LANE/'ANALYSIS_CODE_SEAL.json')
assert all(sha(LANE/n)==h for n,h in a['files'].items())
m=load_module('successor_upstream',BASE/'gate4c_upstream_substitution_reliability_v1/scripts/run_gate4c.py')
assert m.upstream_tree_sha()==read(LANE/'FROZEN_EXECUTION_MANIFEST.json')['upstream_tree_sha256']
assert torch.__version__=='2.8.0+cu128' and torch.version.cuda=='12.8' and torch.cuda.is_available()
assert 'RTX 5090 D' in torch.cuda.get_device_name()
p=LANE/'score_only_supplement_20261011'
expected={seal['files']!r};present=[];absent=[]
for n,h in expected.items():
 q=p/n
 if q.exists():assert sha(q)==h,n;present.append(n)
 else:absent.append(n)
if (p/'CODE_SEAL.json').exists():assert sha(p/'CODE_SEAL.json')=={sha(HERE/'CODE_SEAL.json')!r}
supplement_stages={{}}
for stage in ['support','analysis','verification','backup_export']:
 d=p/'jobs'/stage;dispatch=p/('dispatch_'+stage+'.json')
 supplement_stages[stage]={{'directory_exists':d.exists(),'dispatch_exists':dispatch.exists()}}
 assert not d.exists() and not dispatch.exists(),'existing supplement stage '+stage
processes=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:cmd=(proc/'cmdline').read_bytes().split(b'\\0')
 except (FileNotFoundError,PermissionError,ProcessLookupError):continue
 scripts=[Path(x.decode(errors='replace')).name for x in cmd if x.endswith(b'.py')]
 matched=[x for x in scripts if x in ['run_stage_job.py','run_supplement_job.py','qualify_sources.py','reconstruct_features.py','analyze_confirmation.py','verify_confirmation.py','analyze_score_only.py','verify_score_only.py','run_integrated_pipeline.py']]
 if matched:processes.append({{'pid':int(proc.name),'scripts':matched,'proc_stat':(proc/'stat').read_text().split()[21]}})
assert not processes,'unattributed scientific processes'
data=Path('/root/autodl-tmp/common_pose_confirmation_N80_20261010')
print(json.dumps({{'status':'PASS','python':platform.python_version(),'versions':{{k:version(k) for k in read(LANE/'FROZEN_EXECUTION_MANIFEST.json')['numerical_versions']}},'torch':torch.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(),'threadpools':threadpool_info(),'remaining_bytes':shutil.disk_usage(data).free,'source_files':len(list((data/'source').rglob('*.hdf5'))),'supplement_existing_files_verified':present,'supplement_files_pending_immutable_sync':absent,'supplement_stages':supplement_stages,'scientific_processes':processes,'gpu_state':subprocess.run(['nvidia-smi','--query-gpu=name,memory.used,memory.total,utilization.gpu','--format=csv,noheader'],capture_output=True,text=True).stdout}}))
''')
        stages = {s:controller.inspect_stage(s) for s in ['qualification','reconstruction','support','analysis','verification']}
        assert all(v['state']=='NOT_DISPATCHED' and not v['directory_exists'] for v in stages.values()), stages
        assert remote['source_files']==2768 and remote['remaining_bytes']>=15_000_000_000
    finally:
        controller.close_connection(); controller.password=None
    print('REMOTE_AND_FROZEN_SEALS_PASS', flush=True)
    # One fresh full local rehash. Remote qualification separately rehashes raw sources.
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=4) as pool:
        inventory=list(pool.map(check_file,cohort['files']))
    assert all(r['state']=='COMPLETE_REHASH_PASS' for r in inventory)
    assert sum(r['bytes'] for r in inventory)==cohort['total_bytes']
    result={'status':'PASS_READY_FOR_SINGLE_INTEGRATED_LAUNCH','observed_local_time':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'local_handles':local_handles,'remote_preflight':remote,'primary_stages':stages,'supplement_sealed_files_checked':len(seal['files']),'supplement_code_seal_sha256':sha(HERE/'CODE_SEAL.json'),'original_protocol_sha256':sha(LANE/'SCIENTIFIC_SPEC.md'),'cohort_sha256':sha(LANE/'ENROLLMENT_MANIFEST.json'),'local_source_files_rehashed':len(inventory),'local_source_bytes_rehashed':sum(r['bytes'] for r in inventory),'effect_values_read':False}
    save(HERE/'SUCCESSOR_EXECUTION_PREFLIGHT_20261011.json',result)
    print(json.dumps(result),flush=True)

if __name__=='__main__':main()
