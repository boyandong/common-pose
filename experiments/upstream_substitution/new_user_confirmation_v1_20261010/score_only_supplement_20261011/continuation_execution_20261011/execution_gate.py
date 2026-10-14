"""Bind finalization to the genuine new OS exit; preserve original exit UNKNOWN."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from runtime_common import read,sha

def verify_execution_gate(here,cont):
    assert not (here/'CONTROLLER_TERMINAL.json').exists(),'Lost original exit must remain UNKNOWN'
    launch=read(cont/'LAUNCH.json')
    terminal=read(cont/'CONTROLLER_TERMINAL.json')
    observed=read(cont/'PROCESS_EXIT_OBSERVATION.json')
    complete=read(here/'EXECUTION_COMPLETE.json')
    assert launch['original_controller_exit']==terminal['original_controller_exit']==observed['original_controller_exit']==complete['original_controller_exit']=='UNKNOWN'
    assert terminal['exit_code']==observed['exit_code']==0
    assert terminal['pid']==observed['pid']==launch['pid']
    assert observed['status']=='ACTUAL_CHILD_PROCESS_WAIT_RETURNED'
    assert observed['launch_sha256']==terminal['continuation_launch_sha256']==complete['continuation_launch_sha256']==sha(cont/'LAUNCH.json')
    assert observed['observer_pid']==launch['launcher_pid']
    assert observed['observer_identity_sha256']==launch['launcher_identity_sha256']==sha(cont/'LAUNCHER_IDENTITY.json')
    assert terminal['finished_epoch']<=observed['observed_epoch']
    assert launch['preflight_sha256']==sha(cont/'PREFLIGHT.json')
    assert launch['original_launch_sha256']==terminal['original_launch_sha256']==sha(here/'INTEGRATED_CONTROLLER_LAUNCH_20261011.json')
    assert launch['original_incident_sha256']==sha(here/'INCIDENT_CONTROLLER_LOST_20261011.json')
    assert launch['execution_code_seal_sha256']==sha(cont/'EXECUTION_CODE_SEAL.json')
    for n,h in read(cont/'EXECUTION_CODE_SEAL.json')['files'].items(): assert sha(cont/n)==h,n
    assert complete['execution_identity']=='continuation_execution_20261011'
    assert complete['status']=='PRIMARY_AND_SCORE_ONLY_VERIFIED_AND_FULLY_BACKED_UP'
    return {'status':'PASS_REAL_CONTINUATION_EXIT_ZERO_ORIGINAL_EXIT_UNKNOWN','launch_sha256':sha(cont/'LAUNCH.json'),'terminal_sha256':sha(cont/'CONTROLLER_TERMINAL.json'),'actual_process_exit_sha256':sha(cont/'PROCESS_EXIT_OBSERVATION.json'),'original_controller_exit':'UNKNOWN'}
