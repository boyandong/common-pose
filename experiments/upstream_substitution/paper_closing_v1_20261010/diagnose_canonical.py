"""Read-only FINAL score admission and within-class precision diagnostics.

No fitting, rounding, score substitution, sorting changes or new seed outcomes.
Run in the restored original numerical environment. Outputs live in an explicit
new attempt directory, leaving historical failures untouched.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import sys
import joblib
import numpy as np
import sklearn
from threadpoolctl import threadpool_info

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
SRC = BASE / 'paper_supplement_v1_20261009'

def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(4 << 20), b''): h.update(b)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True, type=Path)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    sp = importlib.util.spec_from_file_location('supplement', SRC/'analyze_comparisons.py')
    old = importlib.util.module_from_spec(sp); sp.loader.exec_module(old)
    assert sha(SRC/'analyze_comparisons.py') == (SRC/'analyze_comparisons.sha256').read_text().split()[0]
    receipt = json.loads((HERE/'REMOTE_CACHE_VERIFICATION.json').read_text())
    transfer=json.loads((HERE/'SOURCE_TRANSFER_MANIFEST.json').read_text())['files']
    for name,value in transfer.items():assert sha(SRC/name)==value,name
    for r in receipt['features']:
        p=SRC/'features'/r['split']/(r['user']+'.npz')
        assert sha(p)==r['sha256']==p.with_suffix('.sha256').read_text().split()[0]
        with np.load(p) as z:
            assert set(z.files)=={'x','flip','ygt','ypred'}
            assert z['x'].shape==(len(z['flip']),36) and np.isfinite(z['x']).all()
            assert set(np.unique(z['flip'])).issubset({0,1})
            for k in ['ygt','ypred']:assert z[k].shape==z['flip'].shape and np.all((z[k]>=1)&(z[k]<=8))
    print('CACHE_AND_TRANSFER_VERIFIED',len(receipt['features']),len(transfer),flush=True)
    summary = json.loads((SRC/'comparative_analysis/SUMMARY.json').read_text())['summary']
    with (SRC/'comparative_analysis/RISK_COVERAGE_ROWS.csv').open(encoding='utf-8-sig', newline='') as f:
        ref = {(r['contract'],r['user'],r['method']):r for r in csv.DictReader(f)
               if r['split']=='FINAL' and float(r['nominal_coverage'])==.3}
    rows=[]; precision=[]; hashes={}
    for c,folder in [('U','gate4e_customer_flip_gate_v1'),('B','gate4f_class_balanced_flip_gate_v1')]:
        fp=BASE/folder/'artifacts/FINAL_GATE_MODEL.joblib'
        inst=json.loads((fp.parent/'FINAL_GATE_INSTANCE.json').read_text())
        assert sha(fp)==inst['model_sha256']
        fm=joblib.load(fp); fm=fm if c=='U' else fm['model']
        cp=SRC/'comparative_analysis'/f'{c}_class_model_DEV_ONLY.joblib'
        assert sha(cp)==cp.with_suffix('.sha256').read_text().split()[0]
        cm=joblib.load(cp)
        rates=np.array(json.loads((SRC/'comparative_analysis'/f'{c}_SUPPLEMENT_INSTANCE.json').read_text())['class_empirical_rates'])
        hashes[c]={'full':sha(fp),'class_model':sha(cp)}
        for r in receipt['features']:
            if r['split']!='FINAL':continue
            u=r['user'];p=SRC/'features/FINAL'/f'{u}.npz';assert sha(p)==r['sha256']
            with np.load(p) as z:v={k:z[k] for k in z.files}
            n=len(v['flip']);take=math.ceil(.3*n);ties=old.tiekeys('FINAL',u,n)
            sc={'full':fm.predict_proba(v['x'])[:,1],
                'class_model':cm.predict_proba(v['x'][:,:8])[:,1],
                'class_empirical':rates[v['ypred']-1]}
            common=summary[c+'_FINAL']['common_reference_class_sets'][u]
            for m,s in sc.items():
                mask=np.zeros(n,bool);rank=old.order(s,ties);mask[rank[:take]]=True
                got=old.maskmetric(v,mask,common)
                for metric in ['ordinary_risk','fixed_common_risk','dynamic_balanced_risk']:
                    expected=float(ref[c,u,m][metric]) if ref[c,u,m][metric] else None
                    value=got[metric];delta=None if value is None or expected is None else value-expected
                    rows.append({'contract':c,'user':u,'method':m,'metric':metric,
                                 'original_accepted':int(ref[c,u,m]['accepted']), 'accepted':take,
                                 'reference':expected,'recovered':value,'difference':delta,
                                 'pass':(value is None)==(expected is None) and (delta is None or abs(delta)<1e-12)})
                if m!='class_model':continue
                for k in range(1,9):
                    values=s[v['ypred']==k];unique=np.unique(values)
                    precision.append({'contract':c,'user':u,'predicted_class':k,
                                      'blocks':len(values),'unique_score_count':len(unique),
                                      'score_min':float(unique[0]) if len(unique) else None,
                                      'score_max':float(unique[-1]) if len(unique) else None,
                                      'score_hex_values':'|'.join(float(a).hex() for a in unique),
                                      'x_dtype':str(v['x'].dtype),'x_c_contiguous':bool(v['x'].flags.c_contiguous),
                                      'class_x_c_contiguous':bool(v['x'][:,:8].flags.c_contiguous)})
            print('DIAGNOSED',c,u,flush=True)
    for name,rr in [('CANONICAL_FINAL_ADMISSION.csv',rows),('CLASS_SCORE_PRECISION.csv',precision)]:
        with (args.out/name).open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
    result={'status':'PASS' if all(r['pass'] and r['original_accepted']==r['accepted'] for r in rows) else 'FAIL',
            'cache_files_verified':len(receipt['features']),'transfer_hashes_verified':len(transfer),
            'n_checks':len(rows),'failed_checks':[r for r in rows if not r['pass'] or r['original_accepted']!=r['accepted']],
            'max_abs_difference':max(abs(r['difference']) for r in rows if r['difference'] is not None),
            'code_sha256':sha(Path(__file__)),'models':hashes,'python':platform.python_version(),
            'numpy':np.__version__,'sklearn':sklearn.__version__,'threadpools':threadpool_info(),
            'thread_environment':{k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']},
            'interpretation':'risk admission only; original per-block score vectors unavailable; no fitting or new seed outcomes'}
    (args.out/'DIAGNOSIS.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':result['status'],'n_checks':len(rows),'failed_checks':result['failed_checks']}),flush=True)
    return 0 if result['status']=='PASS' else 2

if __name__=='__main__':sys.exit(main())
