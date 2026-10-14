"""Back up all transferred reporting inputs and retained seed refit models.

This supplements (never replaces) the original 104-member feature/model backup.
Archives remain private and ignored by Git. Every member is checked before
packaging; the new archive has its own identity, not the old transfer tar hash.
"""
import hashlib
import json
from pathlib import Path
import tarfile

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
SRC=BASE/'paper_supplement_v1_20261009'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    manifest=json.loads((SRC/'RESULT_TRANSFER_MANIFEST.json').read_text())['files']
    files={}
    for name,value in manifest.items():
        p=SRC/name;assert sha(p)==value;files[p]=value
    seed=HERE/'reproduction_attempt3_8threads/seed_results'
    seed_manifest=json.loads((seed/'RUN_MANIFEST.json').read_text())['files']
    for name,value in seed_manifest.items():
        if name.endswith('.joblib'):
            p=seed/name;assert sha(p)==value;files[p]=value
    p=HERE/'reproduction_attempt3_8threads/score_order_control/PRIVATE_SCORE_VECTORS.npz'
    receipt=json.loads((p.parent/'SCORE_ORDER_DIAGNOSIS.json').read_text());assert sha(p)==receipt['private_score_sha256']
    files[p]=receipt['private_score_sha256']
    archive=HERE/'private_reporting_and_seed_backup_20261010.tar.gz'
    assert not archive.exists()
    with tarfile.open(archive,'w:gz') as t:
        for p in sorted(files):t.add(p,arcname=str(p.relative_to(BASE)),recursive=False)
    output={'status':'PASS','archive':archive.name,'bytes':archive.stat().st_size,
            'sha256':sha(archive),'members':len(files),'private_not_for_git':True,
            'files':{str(p.relative_to(BASE)):value for p,value in files.items()},
            'identity':'new private byte-preserving archive; not the original result-transfer archive'}
    (HERE/'REPORTING_SEED_BACKUP_MANIFEST.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({k:v for k,v in output.items() if k!='files'}))

if __name__=='__main__':main()
