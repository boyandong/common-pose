"""One human-authorized successor launch; credentials only in RAM/stdin."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from runtime_common import ROOT,read,save,sha
from successor_preflight_transport_20261010 import credential,handles

HERE=Path(__file__).resolve().parent

def main():
    preflight=HERE/'SUCCESSOR_EXECUTION_PREFLIGHT_20261011.json'
    assert read(preflight)['status']=='PASS_READY_FOR_SINGLE_INTEGRATED_LAUNCH'
    receipt=HERE/'INTEGRATED_CONTROLLER_LAUNCH_20261011.json'
    assert not receipt.exists() and not (HERE/'CONTROLLER_TERMINAL.json').exists()
    live=handles()
    if isinstance(live,dict):live=[live]
    assert all(p['Id']==os.getpid() for p in live),'unexpected Python handles; no launch'
    script=HERE/'run_integrated_pipeline.py'
    assert sha(script)==read(HERE/'CODE_SEAL.json')['files'][script.name]
    password=credential()
    with (HERE/'successor_dispatch.stdout.log').open('xb') as out, (HERE/'successor_dispatch.stderr.log').open('xb') as err:
        child=subprocess.Popen([sys.executable,'-u',str(script)],cwd=ROOT,stdin=subprocess.PIPE,stdout=out,stderr=err,
            creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP)
        command=f"$p=Get-Process -Id {child.pid} -ErrorAction Stop; $p.StartTime.ToString('o')"
        observed=subprocess.check_output(['powershell','-NoProfile','-NonInteractive','-Command',command],text=True,creationflags=subprocess.CREATE_NO_WINDOW).strip()
        save(receipt,{'status':'SINGLE_HUMAN_AUTHORIZED_INTEGRATED_LAUNCH','pid':child.pid,'start_time':observed,'observed_local_time':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'runner_sha256':sha(script),'launcher_sha256':sha(Path(__file__)),'preflight_sha256':sha(preflight),'credential_channel':'RAM_TO_STDIN_ONLY','original_frozen_files_changed':False})
        child.stdin.write((password+'\n').encode());child.stdin.close();password=None
    print(json.dumps({'status':'LAUNCHED_ONCE','pid':child.pid,'start_time':observed,'receipt':str(receipt)}))

if __name__=='__main__':main()
