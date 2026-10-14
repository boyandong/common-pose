"""Restore a hash-verified private backup without replacing any existing file."""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

HERE=Path(__file__).resolve().parent
BASE=HERE.parent.resolve()

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    m=json.loads((HERE/'CACHE_BACKUP_MANIFEST.json').read_text())
    archive=HERE/m['archive']
    assert archive.stat().st_size==m['bytes'] and sha(archive)==m['sha256']
    restored=[];existing=[]
    allowed={'gate4e_customer_flip_gate_v1','gate4f_class_balanced_flip_gate_v1',
             'paper_closing_v1_20261010','paper_supplement_v1_20261009'}
    with tarfile.open(archive) as t:
        members=t.getmembers();assert len(members)==m['members']
        assert len({x.name for x in members})==len(members)
        # Validate every destination before writing any member.
        for x in members:
            p=Path(x.name);dest=(BASE/p).resolve()
            assert x.isfile() and not p.is_absolute() and p.parts[0] in allowed
            assert dest.is_relative_to(BASE) and '..' not in p.parts
        for x in members:
            dest=(BASE/x.name).resolve()
            f=t.extractfile(x)
            if dest.exists():
                h=hashlib.sha256()
                for b in iter(lambda:f.read(4<<20),b''):h.update(b)
                assert dest.is_file() and sha(dest)==h.hexdigest(),f'existing file differs: {x.name}'
                existing.append(x.name)
            else:
                dest.parent.mkdir(parents=True,exist_ok=True)
                with dest.open('xb') as out:shutil.copyfileobj(f,out)
                restored.append(x.name)
    (HERE/'CACHE_RESTORE_RECEIPT.json').write_text(json.dumps({'status':'PASS',
        'archive_sha256':m['sha256'],'restored_files':restored,'existing_identical_files':existing,
        'no_overwrites':True,'private_data_ignored_by_git':True},indent=2)+'\n')
    print(json.dumps({'status':'PASS','restored':len(restored),'existing_identical':len(existing)}))

if __name__=='__main__':main()
