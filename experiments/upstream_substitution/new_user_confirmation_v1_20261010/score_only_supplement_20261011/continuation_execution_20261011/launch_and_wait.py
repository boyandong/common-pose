"""Single hidden launch with retained child handle and actual OS exit observation."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from runtime_common import ROOT,read,save,sha
from successor_preflight_transport_20261010 import credential,handles

CONT=Path(__file__).resolve().parent
HERE=CONT.parent

def creation(pid):
    return subprocess.check_output(['powershell','-NoProfile','-NonInteractive','-Command',f"$p=Get-Process -Id {pid} -ErrorAction Stop; $p.StartTime.ToString('o')"],text=True,creationflags=subprocess.CREATE_NO_WINDOW).strip()

def main():
    sys.stdout=(CONT/'launcher.stdout.log').open('x',encoding='utf-8',buffering=1)
    sys.stderr=(CONT/'launcher.stderr.log').open('x',encoding='utf-8',buffering=1)
    import msvcrt
    lock=(CONT/'LAUNCHER.lock').open('a+b');lock.seek(0)
    if not lock.read(1):lock.write(b'1');lock.flush()
    lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    assert not (CONT/'LAUNCH.json').exists() and not (CONT/'PROCESS_EXIT_OBSERVATION.json').exists()
    assert not (HERE/'CONTROLLER_TERMINAL.json').exists()
    assert read(CONT/'PREFLIGHT.json')['status']=='PASS_READY_FOR_EXECUTION_ONLY_CONTINUATION'
    assert read(CONT/'ORIGINAL_REQUIREMENTS_RECHECK.json')['release_file_and_git_blob_hashes_checked']==125
    code_seal=read(CONT/'EXECUTION_CODE_SEAL.json')
    for n,h in code_seal['files'].items():assert sha(CONT/n)==h,n
    live=handles()
    if isinstance(live,dict):live=[live]
    assert all(p['Id']==os.getpid() for p in live),'Unattributed local Python handles'
    password=credential()
    save(CONT/'LAUNCHER_IDENTITY.json',{'pid':os.getpid(),'start_time':creation(os.getpid()),'launcher_sha256':sha(Path(__file__)),'execution_code_seal_sha256':sha(CONT/'EXECUTION_CODE_SEAL.json')})
    script=CONT/'run_continuation.py'
    with (CONT/'dispatch.stdout.log').open('xb') as out,(CONT/'dispatch.stderr.log').open('xb') as err:
        child=subprocess.Popen([sys.executable,'-u',str(script)],cwd=ROOT,stdin=subprocess.PIPE,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP)
        save(CONT/'LAUNCH.json',{'status':'SINGLE_HUMAN_AUTHORIZED_EXECUTION_ONLY_CONTINUATION','pid':child.pid,'start_time':creation(child.pid),'launcher_pid':os.getpid(),'launcher_identity_sha256':sha(CONT/'LAUNCHER_IDENTITY.json'),'runner_sha256':sha(script),'preflight_sha256':sha(CONT/'PREFLIGHT.json'),'execution_code_seal_sha256':sha(CONT/'EXECUTION_CODE_SEAL.json'),'original_launch_sha256':sha(HERE/'INTEGRATED_CONTROLLER_LAUNCH_20261011.json'),'original_incident_sha256':sha(HERE/'INCIDENT_CONTROLLER_LOST_20261011.json'),'original_controller_exit':'UNKNOWN','credential_channel':'RAM_TO_STDIN_ONLY','observed_local_time':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()})
        child.stdin.write((password+'\n').encode());child.stdin.close();password=None
        code=child.wait()
    save(CONT/'PROCESS_EXIT_OBSERVATION.json',{'status':'ACTUAL_CHILD_PROCESS_WAIT_RETURNED','exit_code':code,'pid':child.pid,'launch_sha256':sha(CONT/'LAUNCH.json'),'observer_pid':os.getpid(),'observer_identity_sha256':sha(CONT/'LAUNCHER_IDENTITY.json'),'observed_epoch':time.time(),'original_controller_exit':'UNKNOWN'})
    print(json.dumps({'child_exit_code':code,'original_controller_exit':'UNKNOWN'}),flush=True)
    lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1);lock.close()
    raise SystemExit(code)

if __name__=='__main__':main()
