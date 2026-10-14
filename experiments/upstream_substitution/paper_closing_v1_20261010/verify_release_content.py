"""Verify a narrow staged release preserves sealed bytes and excludes private inputs."""
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PREFIXES=('experiments/upstream_substitution/paper_closing_v1_20261010/',
          'experiments/upstream_substitution/paper_supplement_v1_20261009/')

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)

def main():
    names=git('diff','--cached','--name-only','-z').decode('utf-8').split('\0')
    names=[n for n in names if n and not n.endswith('/RELEASE_CONTENT_MANIFEST.json')]
    assert names
    hashes={};total=0
    for name in names:
        assert name=='AGENTS.md' or name.startswith(PREFIXES),name
        assert not name.endswith(('.npz','.npy','.joblib','.ckpt','.pth','.tar','.tar.gz','.zip','.png','.pdf','.log')),name
        assert '/features/' not in name and '/__pycache__/' not in name,name
        disk=(ROOT/name).read_bytes();blob=git('show',':'+name)
        assert disk==blob,f'staged bytes differ from sealed worktree: {name}'
        assert len(blob)<10_000_000,(name,len(blob))
        hashes[name]=hashlib.sha256(blob).hexdigest();total+=len(blob)
    check=subprocess.run(['git','-c','core.whitespace=trailing-space,space-before-tab,cr-at-eol',
                          'diff','--cached','--check'],cwd=ROOT,capture_output=True,text=True)
    assert check.returncode==0,check.stdout[:1000]
    result={'status':'PASS','base_commit':git('rev-parse','HEAD').decode().strip(),
            'files':hashes,'file_count':len(hashes),'bytes':total,'preserves_worktree_bytes':True,
            'excludes_private_arrays_models_archives_figures':True,
            'manifest_self_hash_excluded':True,
            'scope':'explicit closing/supplement source and small scientific reporting artifacts plus project AGENTS; unrelated worktree modifications excluded',
            'whitespace_check':'standard trailing-space/indent checks with existing CRLF accepted as line endings; no sealed-byte normalization'}
    (HERE/'RELEASE_CONTENT_MANIFEST.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='files'}))

if __name__=='__main__':main()
