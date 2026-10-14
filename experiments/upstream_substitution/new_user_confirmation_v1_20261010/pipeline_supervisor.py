"""Durable gate-checked continuation of the already frozen N80 experiment.

Never replaces users, changes methods, restarts ambiguous jobs or selects effects.
Uses process/terminal evidence and preserves negative/incomplete scientific results.
"""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
import paramiko
from runtime_common import LANE,ROOT,frozen,read,save,sha
from relay_sources import HOST,PORT,PinnedKey
from relay_completed_sources_v2 import BoundedClient

REMOTE_LANE='/root/work/common-pose/experiments/upstream_substitution/new_user_confirmation_v1_20261010'
PYTHON='/root/miniconda3/envs/commonpose-supplement/bin/python'
STAGES=['qualification','reconstruction','support','analysis','verification']

class Supervisor:
    def __init__(self,password):self.password=password;self.client=None
    def connection(self):
        if self.client is not None and self.client.get_transport() is not None and self.client.get_transport().is_active():return self.client
        self.client=BoundedClient();self.client.set_missing_host_key_policy(PinnedKey())
        self.client.connect(HOST,port=PORT,username='root',password=self.password,allow_agent=False,look_for_keys=False,
                            timeout=20,auth_timeout=20,banner_timeout=20)
        self.client.get_transport().set_keepalive(30);return self.client
    def rpc(self,code):
        command=PYTHON+' -c '+shlex.quote(code)
        last=None
        for attempt in range(4):
            try:
                _,out,err=self.connection().exec_command(command,timeout=45)
                text=out.read().decode();error=err.read().decode();exit_code=out.channel.recv_exit_status()
                if exit_code:raise RuntimeError('remote read/check failed: '+error[-3000:])
                return json.loads(text)
            except (EOFError,OSError,paramiko.SSHException) as exc:
                if isinstance(exc,(paramiko.AuthenticationException,paramiko.BadHostKeyException)) or 'host key mismatch' in str(exc).lower():raise
                last=exc;self.close_connection();time.sleep(min(2**attempt,8))
        raise last
    def close_connection(self):
        if self.client is not None:self.client.close()
        self.client=None
    def copy_immutable(self,name):
        local=LANE/name;remote=REMOTE_LANE+'/'+name
        with self.connection().open_sftp() as sftp:
            try:
                with sftp.open(remote) as f:existing=f.read()
            except FileNotFoundError:existing=None
            if existing is not None:
                import hashlib
                assert hashlib.sha256(existing).hexdigest()==sha(local),'existing remote input differs '+name
            else:
                sftp.put(str(local),remote+'.supervisor.partial',confirm=True)
                sftp.rename(remote+'.supervisor.partial',remote)
    def fetch(self,name):
        target=LANE/name
        with self.connection().open_sftp() as sftp:
            partial=target.with_name(target.name+'.fetch.partial');sftp.get(REMOTE_LANE+'/'+name,str(partial))
        if target.exists():assert sha(target)==sha(partial),'existing local result differs '+name
        else:partial.replace(target)
        return read(target)
    def inspect_stage(self,stage):
        code=f'''import json,os
from pathlib import Path
p=Path({REMOTE_LANE!r});d=p/'jobs'/{stage!r}
if (d/'TERMINAL.json').exists():
 print(json.dumps({{"state":"TERMINAL","receipt":json.loads((d/'TERMINAL.json').read_text())}}))
elif (d/'LAUNCH.json').exists():
 r=json.loads((d/'LAUNCH.json').read_text());live=[]
 for role in ['parent_pid','child_pid']:
  path=Path('/proc')/str(r[role])/'cmdline'
  cmd=path.read_bytes().replace(b'\\0',b' ').decode(errors='replace') if path.exists() else ''
  expected='run_stage_job.py' if role=='parent_pid' else Path(r['command'][2]).name
  if expected in cmd:live.append({{"role":role,"pid":r[role],"command":cmd}})
 print(json.dumps({{"state":"LIVE" if live else "MISSING_HANDLES","launch":r,"live":live}}))
elif (p/('dispatch_'+{stage!r}+'.json')).exists():
 r=json.loads((p/('dispatch_'+{stage!r}+'.json')).read_text());path=Path('/proc')/str(r['pid'])/'cmdline'
 cmd=path.read_bytes().replace(b'\\0',b' ').decode(errors='replace') if path.exists() else ''
 print(json.dumps({{"state":"STARTING" if 'run_stage_job.py' in cmd else "MISSING_HANDLES","dispatch":r}}))
else:print(json.dumps({{"state":"NOT_DISPATCHED","directory_exists":d.exists()}}))
'''
        return self.rpc(code)
    def dispatch_once(self,stage):
        # Mutating dispatch is deliberately NOT inside the retried read-only RPC.
        code=f'''import json,os,subprocess,time
from pathlib import Path
p=Path({REMOTE_LANE!r});stage={stage!r};receipt=p/('dispatch_'+stage+'.json')
assert not receipt.exists() and not (p/'jobs'/stage).exists(),'existing stage; preserve and inspect'
env=dict(os.environ);env.update(OMP_NUM_THREADS='8',OPENBLAS_NUM_THREADS='8',MKL_NUM_THREADS='8')
with (p/('dispatcher_'+stage+'.log')).open('ab') as log:
 child=subprocess.Popen([{PYTHON!r},'-u',str(p/'run_stage_job.py'),stage],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
r={{'pid':child.pid,'stage':stage,'dispatched_epoch':time.time()}};receipt.write_text(json.dumps(r)+'\\n');print(json.dumps(r))
'''
        try:
            _,out,err=self.connection().exec_command(PYTHON+' -c '+shlex.quote(code),timeout=45)
            result=out.read().decode();error=err.read().decode();status=out.channel.recv_exit_status()
            if status:raise RuntimeError('dispatch failed: '+error)
            return json.loads(result)
        except (EOFError,OSError,paramiko.SSHException):
            self.close_connection()
            # Resolve the same attempted dispatch; never create a second launch.
            time.sleep(3);observed=self.inspect_stage(stage)
            if observed['state'] in ['LIVE','STARTING','TERMINAL']:return observed
            raise RuntimeError('dispatch outcome unresolved; preserve state, no automatic relaunch')
    def run_stage(self,stage):
        observed=self.inspect_stage(stage)
        if observed['state']=='NOT_DISPATCHED':
            assert not observed['directory_exists'];self.dispatch_once(stage)
        while True:
            observed=self.inspect_stage(stage)
            if observed['state']=='TERMINAL':
                if observed['receipt']['exit_code']!=0:raise RuntimeError('frozen stage failed: '+stage)
                return observed['receipt']
            if observed['state'] not in ['LIVE','STARTING']:raise RuntimeError('stage handles missing; inspect, do not relaunch: '+stage)
            state('REMOTE_STAGE_LIVE',stage_name=stage,actual_handle_observation=observed)
            time.sleep(30)
    def export_backup_once(self):
        # Export is a mutation: one detached launch, then only read-only polling.
        inspect=f'''import json
from pathlib import Path
p=Path({REMOTE_LANE!r});dest=p/'OFFHOST_BACKUP_MANIFEST.json';launch=p/'BACKUP_EXPORT_LAUNCH.json'
if dest.exists():print(json.dumps({{"state":"COMPLETE"}}))
elif launch.exists():
 r=json.loads(launch.read_text());proc=Path('/proc')/str(r['pid'])/'cmdline'
 cmd=proc.read_bytes().replace(b'\\0',b' ').decode(errors='replace') if proc.exists() else ''
 print(json.dumps({{"state":"LIVE" if 'export_backup_manifest.py' in cmd else "MISSING_HANDLE","pid":r['pid']}}))
else:print(json.dumps({{"state":"NOT_DISPATCHED"}}))
'''
        observed=self.rpc(inspect)
        if observed['state']=='NOT_DISPATCHED':
            code=f'''import json,subprocess,os,time
from pathlib import Path
p=Path({REMOTE_LANE!r});launch=p/'BACKUP_EXPORT_LAUNCH.json'
assert not launch.exists() and not (p/'OFFHOST_BACKUP_MANIFEST.json').exists()
env=dict(os.environ);env.update(OMP_NUM_THREADS='8',OPENBLAS_NUM_THREADS='8',MKL_NUM_THREADS='8')
with (p/'backup_export.log').open('ab') as log:
 child=subprocess.Popen([{PYTHON!r},str(p/'export_backup_manifest.py')],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
r={{'pid':child.pid,'started_epoch':time.time()}};launch.write_text(json.dumps(r)+'\\n');print(json.dumps(r))
'''
            try:
                _,out,err=self.connection().exec_command(PYTHON+' -c '+shlex.quote(code),timeout=45)
                result=out.read().decode();error=err.read().decode()
                if out.channel.recv_exit_status():raise RuntimeError('backup export launch failed: '+error)
                json.loads(result)
            except (EOFError,OSError,paramiko.SSHException):self.close_connection()
        while True:
            observed=self.rpc(inspect)
            if observed['state']=='COMPLETE':return
            if observed['state']!='LIVE':raise RuntimeError('backup export handle absent/unresolved; no automatic relaunch')
            state('BACKUP_EXPORT_LIVE',actual_handle_observation=observed);time.sleep(30)

def state(stage,**fields):
    save(LANE/'PIPELINE_SUPERVISOR_PROGRESS.json',{'stage':stage,'pid':os.getpid(),'observed_epoch':time.time(),**fields},overwrite=True)
    print('PIPELINE_STATE',stage,flush=True)

def local_transfer_gate(cohort):
    for name in ['ACQUISITION_COMPLETE.json','LOCAL_RELAY_COMPLETE.json']:
        if not (LANE/name).exists():return False
        r=read(LANE/name)
        assert r['files']==cohort['total_files'] and r['bytes']==cohort['total_bytes']
        assert r['cohort_sha256']==sha(LANE/'ENROLLMENT_MANIFEST.json')
    assert read(LANE/'LOCAL_RELAY_COMPLETE.json')['status']=='ALL_FROZEN_SOURCES_TRANSFERRED_AND_REMOTE_SHA256_VERIFIED'
    return True

def local_process_evidence(launch_name,terminal_name):
    if (LANE/terminal_name).exists():return {'state':'TERMINAL_RECEIPT_PRESENT','receipt':terminal_name}
    launch=read(LANE/launch_name)
    pid=int(launch.get('new_pid',launch.get('pid')))
    expected=launch.get('new_start_time',launch.get('start_time'))
    command=f"$p=Get-Process -Id {pid} -ErrorAction SilentlyContinue; if($p){{ $p.StartTime.ToString('o') }}"
    observed=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',command],
                            capture_output=True,text=True,stdin=subprocess.DEVNULL,
                            creationflags=subprocess.CREATE_NO_WINDOW,timeout=20).stdout.strip()
    if observed!=expected:raise RuntimeError('required source/relay process missing or PID reused: '+launch_name)
    return {'state':'LIVE','pid':pid,'creation_time':observed}

def main():
    if '--check-only' in sys.argv:
        cohort=frozen(dependencies=False)
        print(json.dumps({'users':80,'files':cohort['total_files'],'transfer_gate_ready':local_transfer_gate(cohort),
                          'would_start_inference_now':False,'protocol_sha256':sha(LANE/'SCIENTIFIC_SPEC.md')}));return
    sys.stdout=(LANE/'pipeline_supervisor.stdout.log').open('a',encoding='utf-8',buffering=1)
    sys.stderr=(LANE/'pipeline_supervisor.stderr.log').open('a',encoding='utf-8',buffering=1)
    import msvcrt
    lock=(LANE/'PIPELINE_SUPERVISOR.lock').open('a+b');lock.seek(0)
    if lock.read(1)==b'':lock.write(b'1');lock.flush()
    lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    cohort=frozen(dependencies=False);seal=read(LANE/'PIPELINE_SUPERVISOR_CODE_SEAL.json')
    assert seal['runner_sha256']==sha(Path(__file__))
    password=sys.stdin.readline().rstrip('\r\n');sys.stdin.close();supervisor=Supervisor(password);password=None
    try:
        while not local_transfer_gate(cohort):
            for name in ['PROGRESS.json','STREAM_RELAY_V2_PROGRESS.json']:
                if (LANE/name).exists():
                    status=read(LANE/name)
                    if 'FAILED' in status['stage']:raise RuntimeError('transfer terminal failure; preserve and inspect '+name)
            handles=[local_process_evidence('DURABLE_DOWNLOAD_LAUNCH_RECEIPT.json','ACQUISITION_COMPLETE.json'),
                     local_process_evidence('STREAM_RELAY_V2_LAUNCH.json','LOCAL_RELAY_COMPLETE.json')]
            state('WAITING_FOR_COMPLETE_FIXED_TRANSFERS',actual_local_handle_evidence=handles);time.sleep(30)
        inputs=read(LANE/'FROZEN_EXECUTION_MANIFEST.json');analysis=read(LANE/'ANALYSIS_CODE_SEAL.json')
        payload=set(inputs['lane_files'])|set(analysis['files'])|{'FROZEN_EXECUTION_MANIFEST.json','FROZEN_EXECUTION_MANIFEST.json.sha256',
                'ANALYSIS_CODE_SEAL.json','ANALYSIS_CODE_SEAL.json.sha256','ACQUISITION_COMPLETE.json','LOCAL_RELAY_COMPLETE.json',
                'export_backup_manifest.py','backup_runtime_to_D.py'}
        for name in sorted(payload):supervisor.copy_immutable(name)
        check=supervisor.rpc(f'''import sys,json,os,shutil
sys.path.insert(0,{REMOTE_LANE!r});os.environ.update(OMP_NUM_THREADS='8',OPENBLAS_NUM_THREADS='8',MKL_NUM_THREADS='8')
import numpy,torch
from runtime_common import frozen,read,sha,LANE
c=frozen(numeric=True);s=read(LANE/'ANALYSIS_CODE_SEAL.json')
assert all(sha(LANE/n)==h for n,h in s['files'].items())
assert torch.__version__=='2.8.0+cu128' and torch.version.cuda=='12.8' and torch.cuda.is_available()
assert 'RTX 5090 D' in torch.cuda.get_device_name()
assert shutil.disk_usage('/root/autodl-tmp').free>=15_000_000_000
print(json.dumps({{'status':'PASS','torch':torch.__version__,'device':torch.cuda.get_device_name(),'remaining_bytes':shutil.disk_usage('/root/autodl-tmp').free}}))
''')
        save(LANE/'REMOTE_PREFLIGHT_BEFORE_FROZEN_INFERENCE.json',check)
        for stage in STAGES:supervisor.run_stage(stage)
        for name in ['SOURCE_QUALIFICATION.json','RECONSTRUCTION_RUNTIME.json','FEATURE_CACHE_MANIFEST.json','COMMON_CLASS_SETS.json',
                     'PRIMARY_RESULT.json','INDEPENDENT_RESULT_VERIFICATION.json','RESULT_MANIFEST.json']:
            supervisor.fetch(name)
        assert read(LANE/'INDEPENDENT_RESULT_VERIFICATION.json')['status']=='PASS'
        supervisor.export_backup_once();supervisor.fetch('OFFHOST_BACKUP_MANIFEST.json')
        state('OFFHOST_BACKUP_RUNNING')
        with (LANE/'supervised_backup.log').open('ab') as log:
            child=subprocess.Popen([sys.executable,'-u',str(LANE/'backup_runtime_to_D.py')],stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
            save(LANE/'SUPERVISED_BACKUP_LAUNCH.json',{'pid':child.pid,'started_epoch':time.time()})
            child.stdin.write((supervisor.password+'\n').encode());child.stdin.close();exit_code=child.wait()
        if exit_code:raise RuntimeError('off-host backup failed; preserve verified copies and inspect')
        assert read(LANE/'OFFHOST_BACKUP_VERIFICATION.json')['status']=='PASS'
        save(LANE/'PIPELINE_EXECUTION_COMPLETE.json',{'status':'FROZEN_EXPERIMENT_INDEPENDENTLY_VERIFIED_AND_BACKED_UP',
             'joint_decision':read(LANE/'PRIMARY_RESULT.json')['joint_decision'],'cohort_sha256':sha(LANE/'ENROLLMENT_MANIFEST.json'),
             'independent_verification_sha256':sha(LANE/'INDEPENDENT_RESULT_VERIFICATION.json'),
             'backup_verification_sha256':sha(LANE/'OFFHOST_BACKUP_VERIFICATION.json'),
             'manuscript_update_and_completion_audit':'STILL_REQUIRED'})
        state('EXPERIMENT_AND_BACKUP_COMPLETE_REPORTING_PENDING')
    except BaseException as error:
        state('PIPELINE_STOPPED_PRESERVE_AND_INSPECT',error_type=type(error).__name__,reason=str(error))
        raise
    finally:
        supervisor.close_connection();supervisor.password=None
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1);lock.close()

if __name__=='__main__':main()
