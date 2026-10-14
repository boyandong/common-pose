"""Read-only scientific cache verification; emits a dated closing receipt."""
import hashlib
import json
import platform
import sys
from pathlib import Path
import joblib
import numpy as np
import sklearn

BASE = Path('/root/work/common-pose/experiments/upstream_substitution')
SRC = BASE/'paper_supplement_v1_20261009'
OUT = BASE/'paper_closing_v1_20261010'


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4<<20),b''): h.update(b)
    return h.hexdigest()


def main():
    transfer = json.loads((OUT/'SOURCE_TRANSFER_MANIFEST.json').read_text())['files']
    for name,value in transfer.items():
        assert sha(SRC/name)==value, name
    features = []
    for split,expected in [('DEV',19),('FINAL',20)]:
        files = sorted((SRC/'features'/split).glob('*.npz'))
        assert len(files)==expected
        for p in files:
            value = sha(p)
            assert value==p.with_suffix('.sha256').read_text().split()[0], str(p)
            with np.load(p) as z:
                assert set(z.files)=={'x','flip','ygt','ypred'}
                n=len(z['flip'])
                assert z['x'].shape==(n,36)
                assert np.isfinite(z['x']).all()
                assert set(np.unique(z['flip'])).issubset({0,1})
                for k in ['ygt','ypred']: assert z[k].shape==(n,) and np.all((z[k]>=1)&(z[k]<=8))
            features.append({'split':split,'user':p.stem,'bytes':p.stat().st_size,'sha256':value,'blocks':n})
    models = {}
    for c,folder in [('U','gate4e_customer_flip_gate_v1'),('B','gate4f_class_balanced_flip_gate_v1')]:
        inst=json.loads((BASE/folder/'artifacts/FINAL_GATE_INSTANCE.json').read_text())
        p=BASE/folder/'artifacts/FINAL_GATE_MODEL.joblib'
        assert sha(p)==inst['model_sha256']
        loaded=joblib.load(p)
        model=loaded if c=='U' else loaded['model']
        models[c]={'sha256':sha(p),'class':type(model).__name__,'train':inst['trained_users'],'calibration':inst['calibration_users']}
    OUT.mkdir(exist_ok=True)
    receipt={'status':'PASS','features':features,'full_models':models,'transfer_artifact_hashes':len(transfer),
        'feature_bytes':sum(r['bytes'] for r in features),'python':platform.python_version(),
        'numpy':np.__version__,'sklearn':sklearn.__version__,'runtime_note':'cloned host reverified; no upstream inference or new fitting'}
    p=OUT/'REMOTE_CACHE_VERIFICATION.json'
    if p.exists(): raise ValueError('Refuse overwrite remote receipt')
    p.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'status':'PASS','feature_files':len(features),'feature_bytes':receipt['feature_bytes'],
        'transfer_artifacts':len(transfer),'full_models':{c:v['sha256'] for c,v in models.items()},'receipt':str(p)}))


if __name__=='__main__':main()
