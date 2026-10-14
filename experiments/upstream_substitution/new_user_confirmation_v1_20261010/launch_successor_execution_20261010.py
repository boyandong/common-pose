"""One-shot known-terminal transport/controller launch; no unknown-job restart."""
import argparse
import datetime
import os
from pathlib import Path
import subprocess
import sys
import time

from runtime_common import LANE, ROOT, frozen, read, save, sha
from successor_preflight_transport_20261010 import credential, handles
from pipeline_supervisor import Supervisor


def creation(pid):
    command=f"$p=Get-Process -Id {int(pid)} -ErrorAction SilentlyContinue; if($p){{$p.StartTime.ToString('o')}}"
    result=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,timeout=20)
    assert result.returncode==0
    return result.stdout.strip()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('role',choices=['download','controller']);ap.add_argument('--attempt-id',required=True)
    args=ap.parse_args();assert args.attempt_id.replace('_','').isalnum()
    frozen(dependencies=False)
    seal=read(LANE/'SEGMENTED_TRANSPORT_CODE_SEAL_20261010.json')
    for name,value in seal['files'].items():assert sha(LANE/name)==value,name
    target=LANE/f'SUCCESSOR_{args.role.upper()}_LAUNCH_{args.attempt_id}.json'
    assert not target.exists(),'existing dispatch, inspect instead of relaunch'
    current_name='DURABLE_DOWNLOAD_LAUNCH_RECEIPT.json' if args.role=='download' else 'PIPELINE_SUPERVISOR_LAUNCH.json'
    old=read(LANE/current_name);old_pid=int(old.get('new_pid',old.get('pid')))
    assert not creation(old_pid),'previous handle still exists; inspect PID identity before proceeding'
    all_handles=handles();observed={r['Id']:r['start_time'] for r in (all_handles if isinstance(all_handles,list) else [all_handles])}
    uploader=read(LANE/'STREAM_RELAY_V2_LAUNCH.json')
    assert observed.get(uploader['pid'])==uploader['start_time'],'sole uploader identity missing'
    progress=read(LANE/'STREAM_RELAY_V2_PROGRESS.json')
    assert progress['pid']==uploader['pid'] and 'FAILED' not in progress['stage']
    if args.role=='download':
        assert read(LANE/'DOWNLOAD_SECOND_DEADLINE_FAILURE_20261010_1710.json')
        assert read(LANE/'SUCCESSOR_FULL_SEGMENT_SMOKE_20261010.json')['status']=='FULL_SEGMENT_EXACT_RANGE_PASS'
        assert old==read(LANE/'DOWNLOAD_SECOND_DURABLE_LAUNCH_20261010_1643.json')
        script=LANE/'acquire_sources_segmented_20261010.py'
        command=[sys.executable,'-u',str(script),'--attempt-id',args.attempt_id]
        password=None
    else:
        assert read(LANE/'PIPELINE_SECOND_TRANSFER_GATE_STOP_20261010_1710.json')
        assert old==read(LANE/'PIPELINE_SECOND_LAUNCH_20261010_1649.json')
        download=read(LANE/'DURABLE_DOWNLOAD_LAUNCH_RECEIPT.json')
        assert creation(download['new_pid'])==download['new_start_time'],'current downloader identity missing'
        status=read(LANE/'PROGRESS.json')
        assert status['pid']==download['new_pid'] and 'FAILED' not in status['stage']
        original_seal=read(LANE/'PIPELINE_SUPERVISOR_CODE_SEAL.json')
        assert original_seal['runner_sha256']==sha(LANE/'pipeline_supervisor.py')
        password=credential();supervisor=Supervisor(password)
        try:
            # Ensure recovery provenance is also preserved in the remote/off-host
            # runtime inventory; original frozen input files are never replaced.
            for name in sorted(set(seal['files'])|{'SEGMENTED_TRANSPORT_CODE_SEAL_20261010.json','SEGMENTED_TRANSPORT_CODE_SEAL_20261010.json.sha256',
                         'SUCCESSOR_PREFLIGHT_TRANSPORT_DIAGNOSIS_20261010.json','SUCCESSOR_RANGE_SIZE_COMPARISON_20261010.json','SUCCESSOR_FULL_SEGMENT_SMOKE_20261010.json'}):
                supervisor.copy_immutable(name)
        finally:
            supervisor.close_connection();supervisor.password=None
        command=[sys.executable,'-u',str(LANE/'pipeline_supervisor.py')]
    with (LANE/f'successor_{args.role}_{args.attempt_id}.launch.log').open('xb') as log:
        child=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.PIPE if password else subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                               creationflags=subprocess.CREATE_NO_WINDOW|subprocess.DETACHED_PROCESS)
        if password:
            child.stdin.write((password+'\n').encode());child.stdin.close();password=None
        start_time=creation(child.pid)
        item={'status':'HIDDEN_SUCCESSOR_LAUNCHED_AFTER_VERIFIED_TERMINAL','pid':child.pid,'start_time':start_time,
              'previous_pid_verified_absent':old_pid,'attempt_id':args.attempt_id,'role':args.role,
              'runner_sha256':sha(Path(command[2])),'transport_seal_sha256':sha(LANE/'SEGMENTED_TRANSPORT_CODE_SEAL_20261010.json'),
              'cohort_sha256':sha(LANE/'ENROLLMENT_MANIFEST.json'),'credential_transport':'stdin/RAM only' if args.role=='controller' else 'no credential',
              'scientific_protocol_and_members_changed':False,'observed_local_time':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()}
        save(target,item)
        if args.role=='download':item={**item,'new_pid':child.pid,'new_start_time':start_time}
        save(LANE/current_name,item,overwrite=True)
        print('SUCCESSOR_LAUNCHED',args.role,child.pid,start_time,flush=True)
        assert start_time,'launched handle not observed; preserve receipt and inspect'


if __name__=='__main__':main()
