"""Linux scoring admission on all old DEV; no fitting, Flip or N80 input."""
import hashlib
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import joblib
import numpy as np
from runtime_common import LANE,BASE,read,save,sha,frozen

HERE=Path(__file__).resolve().parent
COVERAGES=[.3,.5,.6,.7,.8,.9,1.]

def main():
    frozen(numeric=True);registration=read(HERE/'MODEL_REGISTRATION.json');manifest=read(HERE/'OLD_DEV_REFERENCE_MANIFEST.json')
    assert manifest['model_registration_sha256']==sha(HERE/'MODEL_REGISTRATION.json')
    path=HERE/manifest['reference_path'];assert sha(path)==manifest['reference_sha256']
    assert len(manifest['features'])==19;maximum=0.;checks=0;threshold_differences={}
    with np.load(path) as reference:
        for c,entry in registration['models'].items():
            modelpath=HERE/entry['model'];assert sha(modelpath)==entry['model_sha256'];model=joblib.load(modelpath)
            for user,feature in sorted(manifest['features'].items()):
                fp=BASE/feature['path'];assert sha(fp)==feature['sha256']
                with np.load(fp) as z:x=z['x'][:,:19]
                scores=model.predict_proba(x)[:,1];expected=reference[c+'|'+user]
                assert len(scores)==feature['rows']==len(expected) and np.isfinite(scores).all()
                delta=float(np.max(np.abs(scores-expected)));maximum=max(maximum,delta);assert delta<=1e-12,(c,user,delta)
                keys=np.asarray([int.from_bytes(hashlib.sha256(f'20261009|FINAL|{user}|{i}'.encode()).digest()[:8],'big') for i in range(len(scores))],dtype=np.uint64)
                left=np.lexsort((keys,scores));right=np.lexsort((keys,expected))
                for coverage in COVERAGES:
                    n=math.ceil(coverage*len(scores));assert np.array_equal(np.sort(left[:n]),np.sort(right[:n])),(c,user,coverage)
                    checks+=1
                threshold=entry['threshold_at_nominal_30'];threshold_differences[c+'|'+user]=int(np.sum((scores<=threshold)!=(expected<=threshold)))
    save(HERE/'RUNTIME_ADMISSION.json',{'status':'PASS','old_DEV_users':19,'prediction_vectors_checked':38,
         'accepted_set_checks':checks,'maximum_probability_difference':maximum,'fixed_threshold_mask_difference_counts':threshold_differences,
         'reference_manifest_sha256':sha(HERE/'OLD_DEV_REFERENCE_MANIFEST.json'),'model_registration_sha256':sha(HERE/'MODEL_REGISTRATION.json'),
         'scoring_runtime':'Original frozen Linux numerical versions and8threads','N80_features_or_effects_read':False,'old_DEV_Flip_read':False,'refit_performed':False,'runner_sha256':sha(Path(__file__))})
    print('SCORE_ONLY_LINUX_ADMISSION_PASS',checks,maximum,flush=True)

if __name__=='__main__':main()
