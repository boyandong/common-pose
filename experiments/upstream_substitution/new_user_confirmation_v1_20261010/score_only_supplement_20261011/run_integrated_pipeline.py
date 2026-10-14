"""Original frozen stages plus separately sealed eighth-method supplement.

All dispatches are one-shot with live/terminal resolution, never blind retries.
The controller reads effects only after both independent verifiers have passed.
"""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
import paramiko
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from runtime_common import LANE,ROOT,read,save,sha,frozen
from pipeline_supervisor import Supervisor,REMOTE_LANE,PYTHON,local_transfer_gate
import pipeline_supervisor as original_controller
from relay_completed_sources_v3_20261010 import replace_progress

HERE=Path(__file__).resolve().parent
REMOTE=REMOTE_LANE+'/score_only_supplement_20261011'

def parent_state(stage,**fields):
    replace_progress(LANE/'PIPELINE_SUPERVISOR_PROGRESS.json',{'stage':stage,'pid':os.getpid(),'observed_epoch':time.time(),**fields})
    print('PIPELINE_STATE',stage,flush=True)

original_controller.state=parent_state

class Integrated(Supervisor):
    def inspect_supplement(self,stage):
        return self.rpc(f'''import json
from pathlib import Path
p=Path({REMOTE!r});d=p/'jobs'/{stage!r};dispatch=p/('dispatch_'+{stage!r}+'.json')
if (d/'TERMINAL.json').exists():print(json.dumps({{'state':'TERMINAL','receipt':json.loads((d/'TERMINAL.json').read_text())}}))
elif (d/'LAUNCH.json').exists():
 r=json.loads((d/'LAUNCH.json').read_text());live=[]
 for role in ['parent_pid','child_pid']:
  path=Path('/proc')/str(r[role])/'cmdline';cmd=path.read_bytes().replace(b'\\0',b' ').decode(errors='replace') if path.exists() else ''
  expected='run_supplement_job.py' if role=='parent_pid' else Path(r['command'][2]).name
  if expected in cmd:live.append({{'role':role,'pid':r[role]}})
 print(json.dumps({{'state':'LIVE' if live else 'MISSING_HANDLES','launch':r,'live':live}}))
elif dispatch.exists():
 r=json.loads(dispatch.read_text());path=Path('/proc')/str(r['pid'])/'cmdline';cmd=path.read_bytes().replace(b'\\0',b' ').decode(errors='replace') if path.exists() else ''
 print(json.dumps({{'state':'STARTING' if 'run_supplement_job.py' in cmd else 'MISSING_HANDLES','dispatch':r}}))
else:print(json.dumps({{'state':'NOT_DISPATCHED','directory_exists':d.exists()}}))
''')
    def dispatch_supplement_once(self,stage):
        code=f'''import json,os,subprocess,time
from pathlib import Path
p=Path({REMOTE!r});stage={stage!r};receipt=p/('dispatch_'+stage+'.json')
assert not receipt.exists() and not (p/'jobs'/stage).exists()
env=dict(os.environ);env.update(OMP_NUM_THREADS='8',OPENBLAS_NUM_THREADS='8',MKL_NUM_THREADS='8')
with (p/('dispatcher_'+stage+'.log')).open('ab') as log:
 child=subprocess.Popen([{PYTHON!r},'-u',str(p/'run_supplement_job.py'),stage],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
r={{'pid':child.pid,'stage':stage,'dispatched_epoch':time.time()}};receipt.write_text(json.dumps(r)+'\\n');print(json.dumps(r))
'''
        try:
            _,out,err=self.connection().exec_command(PYTHON+' -c '+shlex.quote(code),timeout=45)
            result=out.read().decode();error=err.read().decode();status=out.channel.recv_exit_status()
            if status:raise RuntimeError('supplement dispatch rejected: '+error)
            return json.loads(result)
        except (EOFError,OSError,paramiko.SSHException):
            self.close_connection();time.sleep(3);observed=self.inspect_supplement(stage)
            if observed['state'] in ['LIVE','STARTING','TERMINAL']:return observed
            raise RuntimeError('supplement dispatch outcome unresolved; no automatic relaunch')
    def run_supplement(self,stage):
        observed=self.inspect_supplement(stage)
        if observed['state']=='NOT_DISPATCHED':
            assert not observed['directory_exists'];self.dispatch_supplement_once(stage)
        while True:
            observed=self.inspect_supplement(stage)
            if observed['state']=='TERMINAL':
                assert observed['receipt']['exit_code']==0,'supplement failed: '+stage
                return observed['receipt']
            assert observed['state'] in ['LIVE','STARTING'],'supplement handles missing; preserve, do not relaunch'
            replace_progress(HERE/'CONTROLLER_PROGRESS.json',{'stage':'SUPPLEMENT_'+stage.upper(),'observed_epoch':time.time(),'pid':os.getpid(),'actual_handle_evidence':observed})
            time.sleep(60)
    def export_integrated_backup(self):
        stage='backup_export';observed=self.inspect_supplement(stage)
        if observed['state']=='NOT_DISPATCHED':
            assert not observed['directory_exists'];self.dispatch_supplement_once(stage)
        while True:
            observed=self.inspect_supplement(stage)
            if observed['state']=='TERMINAL':
                assert observed['receipt']['exit_code']==0,'backup export failed'
                return
            assert observed['state'] in ['LIVE','STARTING'],'backup export handle absent; preserve, no relaunch'
            time.sleep(60)

def main():
    sys.stdout=(HERE/'integrated_controller.stdout.log').open('a',encoding='utf-8',buffering=1)
    sys.stderr=(HERE/'integrated_controller.stderr.log').open('a',encoding='utf-8',buffering=1)
    import msvcrt
    lock=(HERE/'INTEGRATED_CONTROLLER.lock').open('a+b');lock.seek(0)
    if not lock.read(1):lock.write(b'1');lock.flush()
    lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    cohort=frozen(dependencies=False);assert local_transfer_gate(cohort)
    seal=read(HERE/'CODE_SEAL.json')
    for n,h in seal['files'].items():assert sha(HERE/n)==h,n
    assert sha(LANE/'relay_completed_sources_v3_20261010.py')==seal['parent_status_writer_sha256']
    assert sha(LANE/'pipeline_supervisor.py')==seal['parent_controller_sha256']
    assert read(HERE/'RUNTIME_ADMISSION.json')['status']=='PASS'
    password=sys.stdin.readline().rstrip('\r\n');sys.stdin.close();controller=Integrated(password);password=None
    started=time.time();terminal=None
    try:
        # Synchronize only immutable parent/supplement inputs; no frozen overwrite.
        inputs=read(LANE/'FROZEN_EXECUTION_MANIFEST.json');analysis=read(LANE/'ANALYSIS_CODE_SEAL.json')
        names=set(inputs['lane_files'])|set(analysis['files'])|{'FROZEN_EXECUTION_MANIFEST.json','FROZEN_EXECUTION_MANIFEST.json.sha256','ANALYSIS_CODE_SEAL.json','ANALYSIS_CODE_SEAL.json.sha256','ACQUISITION_COMPLETE.json','LOCAL_RELAY_COMPLETE.json','export_backup_manifest.py','backup_runtime_to_D.py'}
        names|={'score_only_supplement_20261011/'+n for n in seal['files']}
        names|={'score_only_supplement_20261011/'+n for n in ['CODE_SEAL.json','CODE_SEAL.json.sha256','RUNTIME_ADMISSION.json']}
        for name in sorted(names):controller.copy_immutable(name)
        check=controller.rpc(f'''import os,sys,json,shutil
sys.path.insert(0,{REMOTE_LANE!r});os.environ.update(OMP_NUM_THREADS='8',OPENBLAS_NUM_THREADS='8',MKL_NUM_THREADS='8')
import numpy,torch
from runtime_common import frozen,read,sha,LANE,BASE,load_module
frozen(numeric=True);a=read(LANE/'ANALYSIS_CODE_SEAL.json');assert all(sha(LANE/n)==h for n,h in a['files'].items())
p=LANE/'score_only_supplement_20261011';s=read(p/'CODE_SEAL.json');assert all(sha(p/n)==h for n,h in s['files'].items())
assert read(p/'RUNTIME_ADMISSION.json')['status']=='PASS'
m=load_module('integrated_upstream',BASE/'gate4c_upstream_substitution_reliability_v1/scripts/run_gate4c.py');assert m.upstream_tree_sha()==read(LANE/'FROZEN_EXECUTION_MANIFEST.json')['upstream_tree_sha256']
assert torch.__version__=='2.8.0+cu128' and torch.version.cuda=='12.8' and torch.cuda.is_available() and 'RTX 5090 D' in torch.cuda.get_device_name()
assert shutil.disk_usage('/root/autodl-tmp').free>=15_000_000_000
print(json.dumps({{'status':'PASS','gpu':torch.cuda.get_device_name(),'remaining_bytes':shutil.disk_usage('/root/autodl-tmp').free}}))
''')
        save(HERE/'REMOTE_PREFLIGHT_BEFORE_N80.json',check)
        for stage in ['qualification','reconstruction','support']:controller.run_stage(stage)
        controller.run_supplement('support')
        for stage in ['analysis','verification']:controller.run_stage(stage)
        for stage in ['analysis','verification']:controller.run_supplement(stage)
        for name in ['SOURCE_QUALIFICATION.json','RECONSTRUCTION_RUNTIME.json','FEATURE_CACHE_MANIFEST.json','COMMON_CLASS_SETS.json','PRIMARY_RESULT.json','INDEPENDENT_RESULT_VERIFICATION.json','RESULT_MANIFEST.json']:
            controller.fetch(name)
        for name in ['SUPPORT_SEAL.json','SECONDARY_RESULT.json','INDEPENDENT_VERIFICATION.json','RESULT_MANIFEST.json']:
            controller.fetch('score_only_supplement_20261011/'+name)
        assert read(LANE/'INDEPENDENT_RESULT_VERIFICATION.json')['status']=='PASS' and read(HERE/'INDEPENDENT_VERIFICATION.json')['status']=='PASS'
        controller.export_integrated_backup();controller.fetch('OFFHOST_BACKUP_MANIFEST.json')
        with (HERE/'backup.log').open('ab') as log:
            child=subprocess.Popen([sys.executable,'-u',str(LANE/'backup_runtime_to_D.py')],stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
            save(HERE/'BACKUP_LAUNCH.json',{'pid':child.pid,'started_epoch':time.time()})
            child.stdin.write((controller.password+'\n').encode());child.stdin.close();code=child.wait()
        assert code==0 and read(LANE/'OFFHOST_BACKUP_VERIFICATION.json')['status']=='PASS'
        # Explicitly prove the original exporter included all supplemental files.
        manifest=read(LANE/'OFFHOST_BACKUP_MANIFEST.json');records={r['local_relative']:r for r in manifest['files']};dest=Path('D:/CommonPose_confirmation_N80_20261010')
        required=['SECONDARY_RESULT.json','INDEPENDENT_VERIFICATION.json','SUPPORT_SEAL.json','CODE_SEAL.json','MODEL_REGISTRATION.json']+list(seal['files'])
        for n in sorted(set(required)):
            relative='results/score_only_supplement_20261011/'+n;entry=records[relative];assert sha(dest/relative)==entry['sha256']
        score_manifest=read(dest/'results/score_only_supplement_20261011/SCORE_CACHE_MANIFEST.json')
        for entry in score_manifest['files'].values():
            relative=str(Path(entry['path']).relative_to('/root/autodl-tmp/common_pose_confirmation_N80_20261010')).replace('\\','/')
            assert sha(dest/relative)==entry['sha256']
        # The exporter cannot hash its own live stdout/terminal before it ends.
        # Back up those explicitly after the durable export parent is terminal.
        evidence=controller.rpc(f'''import json,hashlib
from pathlib import Path
p=Path({REMOTE!r});names=['jobs/backup_export/output.log','jobs/backup_export/TERMINAL.json','jobs/backup_export/TERMINAL.json.sha256','dispatcher_backup_export.log']
print(json.dumps([{{'relative':n,'bytes':(p/n).stat().st_size,'sha256':hashlib.sha256((p/n).read_bytes()).hexdigest()}} for n in names]))
''')
        with controller.connection().open_sftp() as ftp:
            for entry in evidence:
                target=dest/'results/score_only_supplement_20261011'/entry['relative'];target.parent.mkdir(parents=True,exist_ok=True)
                if not target.exists():
                    part=target.with_name(target.name+'.export-evidence.partial');ftp.get(REMOTE+'/'+entry['relative'],str(part))
                    assert part.stat().st_size==entry['bytes'] and sha(part)==entry['sha256'];part.replace(target)
                assert sha(target)==entry['sha256']
        save(HERE/'OFFHOST_BACKUP_VERIFICATION.json',{'status':'PASS','original_backup_verification_sha256':sha(LANE/'OFFHOST_BACKUP_VERIFICATION.json'),'supplement_dependency_result_files_checked':len(set(required)),'supplement_score_caches_checked':len(score_manifest['files']),'model_instances_included':True,'all_checked_local_sha256_recomputed':True})
        save(HERE/'EXPORT_EXECUTION_BACKUP_VERIFICATION.json',{'status':'PASS','closed_export_logs_and_terminal':evidence,'all_local_sha256_recomputed':True})
        save(LANE/'PIPELINE_EXECUTION_COMPLETE.json',{'status':'FROZEN_EXPERIMENT_INDEPENDENTLY_VERIFIED_AND_BACKED_UP','joint_decision':read(LANE/'PRIMARY_RESULT.json')['joint_decision'],
             'cohort_sha256':sha(LANE/'ENROLLMENT_MANIFEST.json'),'independent_verification_sha256':sha(LANE/'INDEPENDENT_RESULT_VERIFICATION.json'),'backup_verification_sha256':sha(LANE/'OFFHOST_BACKUP_VERIFICATION.json'),
             'supplement_verification_sha256':sha(HERE/'INDEPENDENT_VERIFICATION.json'),'supplement_backup_verification_sha256':sha(HERE/'OFFHOST_BACKUP_VERIFICATION.json'),'manuscript_update_and_completion_audit':'STILL_REQUIRED'})
        save(HERE/'EXECUTION_COMPLETE.json',{'status':'PRIMARY_AND_SCORE_ONLY_VERIFIED_AND_FULLY_BACKED_UP','primary_pipeline_complete_sha256':sha(LANE/'PIPELINE_EXECUTION_COMPLETE.json'),'supplement_verification_sha256':sha(HERE/'INDEPENDENT_VERIFICATION.json'),'supplement_backup_verification_sha256':sha(HERE/'OFFHOST_BACKUP_VERIFICATION.json'),'reports_and_full_goal_audit':'STILL_REQUIRED'})
        terminal={'status':'COMPLETE_REPORTING_PENDING','exit_code':0}
    except BaseException as error:
        terminal={'status':'FAILED_PRESERVE_AND_INSPECT','exit_code':1,'error_type':type(error).__name__,'reason':str(error)}
        raise
    finally:
        if terminal is not None:save(HERE/'CONTROLLER_TERMINAL.json',{**terminal,'pid':os.getpid(),'started_epoch':started,'finished_epoch':time.time()})
        controller.close_connection();controller.password=None;lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1);lock.close()

if __name__=='__main__':main()
