"""Enumerate immutable caches, frozen dependencies and results for off-host backup."""
import subprocess
from pathlib import Path
from runtime_common import LANE,ROOT,DATA,frozen,read,sha,save

def main():
    frozen(numeric=True)
    assert read(LANE/'INDEPENDENT_RESULT_VERIFICATION.json')['status']=='PASS'
    for stage in ['qualification','reconstruction','support','analysis','verification']:
        assert read(LANE/'jobs'/stage/'TERMINAL.json')['exit_code']==0
    files=[]
    def add(p,relative):
        assert p.is_file()
        files.append({'remote_path':str(p),'local_relative':relative,'bytes':p.stat().st_size,'sha256':sha(p)})
    for p in sorted(DATA.rglob('*')):
        if p.is_file() and 'source' not in p.relative_to(DATA).parts:
            assert not p.name.endswith('.partial'),p
            add(p,str(p.relative_to(DATA)))
    inputs=read(LANE/'FROZEN_EXECUTION_MANIFEST.json')
    for relative,h in inputs['parent_dependencies'].items():
        p=ROOT/relative;assert sha(p)==h
        add(p,'frozen_dependencies/common-pose/'+relative)
    for name,h in inputs['external_dependencies'].items():
        p=Path(name);assert sha(p)==h
        add(p,'frozen_dependencies/external/'+str(p).removeprefix('/root/'))
    upstream=Path('/root/work/emg2pose')
    names=subprocess.check_output(['git','-C',str(upstream),'ls-files','-z']).decode().split('\0')
    for name in names:
        if name:add(upstream/name,'frozen_dependencies/emg2pose/'+name)
    for p in sorted(LANE.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.name not in ['PROGRESS.json'] and not p.name.endswith('.partial'):
            add(p,'results/'+str(p.relative_to(LANE)))
    assert len({r['local_relative'] for r in files})==len(files)
    save(LANE/'OFFHOST_BACKUP_MANIFEST.json',{'status':'IMMUTABLE_RUNTIME_FILES_READY_FOR_BACKUP',
         'files':files,'bytes':sum(r['bytes'] for r in files),'cohort_sha256':sha(LANE/'ENROLLMENT_MANIFEST.json'),
         'raw_sources':'already retained on local D with individual acquisition SHA256 receipts; excluded from this second transfer',
         'exporter_sha256':sha(Path(__file__))})
    print('OFFHOST_BACKUP_MANIFEST_READY',len(files),sum(r['bytes'] for r in files),flush=True)

if __name__=='__main__':main()
