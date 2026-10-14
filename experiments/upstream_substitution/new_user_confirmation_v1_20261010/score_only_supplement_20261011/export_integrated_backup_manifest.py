"""Full frozen primary/supplement backup inventory, excluding exporter live files.

The original exporter is preserved. Its own currently written output log cannot
be included as an immutable result hash; preserve it separately after termination.
"""
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from runtime_common import LANE,ROOT,DATA,frozen,read,save,sha

HERE=Path(__file__).resolve().parent

def main():
    frozen(numeric=True);assert read(LANE/'INDEPENDENT_RESULT_VERIFICATION.json')['status']=='PASS'
    assert read(HERE/'INDEPENDENT_VERIFICATION.json')['status']=='PASS'
    for stage in ['qualification','reconstruction','support','analysis','verification']:
        assert read(LANE/'jobs'/stage/'TERMINAL.json')['exit_code']==0
    for stage in ['support','analysis','verification']:
        assert read(HERE/'jobs'/stage/'TERMINAL.json')['exit_code']==0
    files=[]
    def add(path,relative):
        assert path.is_file();files.append({'remote_path':str(path),'local_relative':relative,'bytes':path.stat().st_size,'sha256':sha(path)})
    for path in sorted(DATA.rglob('*')):
        if path.is_file() and 'source' not in path.relative_to(DATA).parts:
            assert not path.name.endswith('.partial'),path
            add(path,str(path.relative_to(DATA)))
    inputs=read(LANE/'FROZEN_EXECUTION_MANIFEST.json')
    for relative,digest in inputs['parent_dependencies'].items():
        path=ROOT/relative;assert sha(path)==digest;add(path,'frozen_dependencies/common-pose/'+relative)
    for name,digest in inputs['external_dependencies'].items():
        path=Path(name);assert sha(path)==digest;add(path,'frozen_dependencies/external/'+str(path).removeprefix('/root/'))
    upstream=Path('/root/work/emg2pose')
    names=subprocess.check_output(['git','-C',str(upstream),'ls-files','-z']).decode().split('\0')
    for name in names:
        if name:add(upstream/name,'frozen_dependencies/emg2pose/'+name)
    excluded={HERE/'jobs/backup_export/output.log',HERE/'dispatcher_backup_export.log'}
    for path in sorted(LANE.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path not in excluded and path.name!='PROGRESS.json' and not path.name.endswith('.partial'):
            add(path,'results/'+str(path.relative_to(LANE)))
    assert len({r['local_relative'] for r in files})==len(files)
    save(LANE/'OFFHOST_BACKUP_MANIFEST.json',{'status':'IMMUTABLE_RUNTIME_FILES_READY_FOR_BACKUP','files':files,'bytes':sum(r['bytes'] for r in files),
         'cohort_sha256':sha(LANE/'ENROLLMENT_MANIFEST.json'),'raw_sources':'already retained on local D with individual SHA256 receipts; independently rehashed by backup verifier',
         'exporter_sha256':sha(Path(__file__)),'supplement_included':True,'primary_verification_sha256':sha(LANE/'INDEPENDENT_RESULT_VERIFICATION.json'),
         'supplement_verification_sha256':sha(HERE/'INDEPENDENT_VERIFICATION.json'),'excluded_live_export_logs':[str(p.relative_to(LANE)) for p in sorted(excluded)],
         'export_terminal_and_logs':'preserved separately after export stage closes, no self-referential live-log hash'})
    print('INTEGRATED_OFFHOST_MANIFEST_READY',len(files),sum(r['bytes'] for r in files),flush=True)

if __name__=='__main__':main()
