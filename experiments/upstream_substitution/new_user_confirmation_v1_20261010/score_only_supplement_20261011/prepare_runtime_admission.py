"""Reference vectors only on old DEV, using the source score-control runtime."""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import joblib
import numpy as np
from runtime_common import LANE,BASE,read,save,sha

HERE=Path(__file__).resolve().parent

def main():
    import sklearn
    from threadpoolctl import threadpool_info
    assert np.__version__=='1.26.4' and sklearn.__version__=='1.5.2' and joblib.__version__=='1.5.2'
    assert all(os.environ.get(k)=='8' for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'])
    assert all(p['num_threads']==8 for p in threadpool_info())
    registration=read(HERE/'MODEL_REGISTRATION.json');source=BASE/'paper_supplement_v1_20261009/features/DEV'
    expected=read(BASE/'paper_closing_v1_20261010/REMOTE_CACHE_VERIFICATION.json')['features']
    expected={r['user']:r['sha256'] for r in expected if r['split']=='DEV'};assert len(expected)==19
    models={}
    for c,entry in registration['models'].items():
        path=HERE/entry['model'];assert sha(path)==entry['model_sha256'];models[c]=joblib.load(path)
        assert models[c].n_features_in_==19
    vectors={};features={}
    for user,digest in sorted(expected.items()):
        path=source/(user+'.npz');assert sha(path)==digest
        with np.load(path) as z:x=z['x'][:,:19]
        assert x.shape[1]==19 and np.isfinite(x).all()
        for c,model in models.items():vectors[c+'|'+user]=model.predict_proba(x)[:,1]
        features[user]={'path':str(path.relative_to(BASE)).replace('\\','/'),'sha256':digest,'rows':len(x)}
    dest=HERE/'private_admission';dest.mkdir(exist_ok=False)
    with (dest/'OLD_DEV_REFERENCE_SCORES.npz').open('xb') as f:np.savez_compressed(f,**vectors)
    save(HERE/'OLD_DEV_REFERENCE_MANIFEST.json',{'status':'ALL19_OLD_DEV_REFERENCE_VECTORS','features':features,
        'reference_path':'private_admission/OLD_DEV_REFERENCE_SCORES.npz','reference_sha256':sha(dest/'OLD_DEV_REFERENCE_SCORES.npz'),
        'model_registration_sha256':sha(HERE/'MODEL_REGISTRATION.json'),'runtime':{'python':sys.version,'numpy':np.__version__,'sklearn':sklearn.__version__,'joblib':joblib.__version__,'threadpools':threadpool_info()},
        'N80_features_or_effects_read':False,'old_DEV_Flip_read':False})
    print('OLD_DEV_REFERENCE_READY',len(vectors),sum(r['rows'] for r in features.values()),flush=True)

if __name__=='__main__':main()
