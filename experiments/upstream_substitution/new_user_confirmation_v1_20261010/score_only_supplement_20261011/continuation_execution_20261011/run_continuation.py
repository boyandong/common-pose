"""Original frozen stages plus separately sealed eighth-method supplement.

All dispatches are one-shot with live/terminal resolution, never blind retries.
The controller reads effects only after both independent verifiers have passed.
"""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time
import paramiko
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from runtime_common import LANE,ROOT,read,save,sha,frozen
from pipeline_supervisor import Supervisor,REMOTE_LANE,PYTHON,local_transfer_gate
import pipeline_supervisor as original_controller
from relay_completed_sources_v3_20261010 import replace_progress

HERE=Path(__file__).resolve().parent
REMOTE=REMOTE_LANE+'/score_only_supplement_20261011'

from run_integrated_pipeline import Integrated
CONT=Path(__file__).resolve().parent
HERE=CONT.parent
from successor_preflight_transport_20261010 import handles

def parent_state(stage,**fields):
    replace_progress(CONT/"PROGRESS.json", {"stage":stage,"pid":os.getpid(),"observed_epoch":time.time(),**fields})
    print("PIPELINE_STATE",stage,flush=True)
original_controller.state=parent_state

def main():
    sys.stdout=(CONT/'controller.stdout.log').open('a',encoding='utf-8',buffering=1)
    sys.stderr=(CONT/'controller.stderr.log').open('a',encoding='utf-8',buffering=1)
    import msvcrt
    lock=(CONT/'CONTROLLER.lock').open('a+b');lock.seek(0)
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
        preflight=read(CONT/'PREFLIGHT.json')
        assert preflight['status']=='PASS_READY_FOR_EXECUTION_ONLY_CONTINUATION'
        assert sha(CONT/'PREFLIGHT.json')==read(CONT/'LAUNCH.json')['preflight_sha256']
        assert not (HERE/'CONTROLLER_TERMINAL.json').exists(), 'Original exit remains UNKNOWN'
        for stage in ['qualification','reconstruction']:
            observed=controller.inspect_stage(stage)
            assert observed['state']=='TERMINAL' and observed['receipt']['exit_code']==0
            assert observed['receipt']==preflight['remote']['stages'][stage]['terminal']
        # Already terminal stages are never redispatched. Both support stages precede effects.
        controller.run_stage('support')
        controller.run_supplement('support')
        for stage in ['analysis','verification']:controller.run_stage(stage)
        for stage in ['analysis','verification']:controller.run_supplement(stage)
        for name in ['SOURCE_QUALIFICATION.json','RECONSTRUCTION_RUNTIME.json','FEATURE_CACHE_MANIFEST.json','COMMON_CLASS_SETS.json','PRIMARY_RESULT.json','INDEPENDENT_RESULT_VERIFICATION.json','RESULT_MANIFEST.json']:
            controller.fetch(name)
        for name in ['SUPPORT_SEAL.json','SECONDARY_RESULT.json','INDEPENDENT_VERIFICATION.json','RESULT_MANIFEST.json']:
            controller.fetch('score_only_supplement_20261011/'+name)
        assert read(LANE/'INDEPENDENT_RESULT_VERIFICATION.json')['status']=='PASS' and read(HERE/'INDEPENDENT_VERIFICATION.json')['status']=='PASS'
        controller.export_integrated_backup();controller.fetch('OFFHOST_BACKUP_MANIFEST.json')
        inventory=read(LANE/'OFFHOST_BACKUP_MANIFEST.json')
        dest=Path('D:/CommonPose_confirmation_N80_20261010')
        required_bytes=sum(r['bytes'] for r in inventory['files'] if not (dest/r['local_relative']).exists())
        assert shutil.disk_usage(dest).free>required_bytes+1_000_000_000,'Insufficient D capacity for the exact export inventory'
        save(CONT/'BACKUP_CAPACITY_GATE.json',{'status':'PASS','required_new_bytes':required_bytes,'available_bytes':shutil.disk_usage(dest).free,'manifest_sha256':sha(LANE/'OFFHOST_BACKUP_MANIFEST.json')})
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
        save(HERE/'EXECUTION_COMPLETE.json',{'status':'PRIMARY_AND_SCORE_ONLY_VERIFIED_AND_FULLY_BACKED_UP','primary_pipeline_complete_sha256':sha(LANE/'PIPELINE_EXECUTION_COMPLETE.json'),'supplement_verification_sha256':sha(HERE/'INDEPENDENT_VERIFICATION.json'),'supplement_backup_verification_sha256':sha(HERE/'OFFHOST_BACKUP_VERIFICATION.json'),'reports_and_full_goal_audit':'STILL_REQUIRED','execution_identity':'continuation_execution_20261011','original_controller_exit':'UNKNOWN','continuation_launch_sha256':sha(CONT/'LAUNCH.json')})
        terminal={'status':'COMPLETE_REPORTING_PENDING','exit_code':0}
    except BaseException as error:
        terminal={'status':'FAILED_PRESERVE_AND_INSPECT','exit_code':1,'error_type':type(error).__name__,'reason':str(error)}
        raise
    finally:
        if terminal is not None:save(CONT/'CONTROLLER_TERMINAL.json',{**terminal,'original_controller_exit':'UNKNOWN','original_launch_sha256':sha(HERE/'INTEGRATED_CONTROLLER_LAUNCH_20261011.json'),'continuation_launch_sha256':sha(CONT/'LAUNCH.json'),'pid':os.getpid(),'started_epoch':started,'finished_epoch':time.time()})
        controller.close_connection();controller.password=None;lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1);lock.close()

if __name__=='__main__':main()
