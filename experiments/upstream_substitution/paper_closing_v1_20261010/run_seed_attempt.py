"""Run the original sealed seed implementation in a new, traced attempt directory.

The implementation, strict canonical gate, seeds and sorting remain unchanged.
This entry point restores the registered numerical environment before importing
numerical libraries and never overwrites a previous attempt or FINAL instance.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform

HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--attempt',required=True,type=Path)
    args=ap.parse_args()
    assert not (args.attempt/'seed_results').exists()
    diagnostic=json.loads((args.attempt/'canonical/DIAGNOSIS.json').read_text())
    assert diagnostic['status']=='PASS' and diagnostic['max_abs_difference']==0
    assert diagnostic['cache_files_verified']==39 and diagnostic['transfer_hashes_verified']==34
    for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:
        assert os.environ.get(k)=='8',(k,os.environ.get(k))
    code=HERE/'seed_robustness.py'
    assert sha(code)==code.with_suffix('.sha256').read_text(encoding='utf-8-sig').split()[0]
    assert sha(HERE/'CLOSING_SPEC.md')==(HERE/'CLOSING_SPEC.sha256').read_text().split()[0]
    env={'status':'STARTED','original_code_sha256':sha(code),'entry_sha256':sha(Path(__file__)),
         'diagnosis_sha256':sha(args.attempt/'canonical/DIAGNOSIS.json'),
         'python':platform.python_version(),'threads':{k:os.environ[k] for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']},
         'output':str(args.attempt/'seed_results'),
         'identity':'unmodified sealed seed implementation; FINAL no fit; DEV separate same-spec refit'}
    with (args.attempt/'SEED_EXECUTION.json').open('x') as f:json.dump(env,f,indent=2)
    sp=importlib.util.spec_from_file_location('sealed_seed',code)
    module=importlib.util.module_from_spec(sp);sp.loader.exec_module(module)
    module.OUT=args.attempt/'seed_results'
    # Existing failed attempts never reached a progress receipt. Keep current
    # progress inside this attempt without changing the sealed implementation.
    original_dump=module.dump
    def attempt_dump(p,v):
        if p==HERE/'SEED_PROGRESS.json':p=args.attempt/'SEED_PROGRESS.json'
        original_dump(p,v)
    module.dump=attempt_dump
    module.main()
    env.update(status='COMPLETE',results_manifest_sha256=sha(module.OUT/'RUN_MANIFEST.json'))
    (args.attempt/'SEED_EXECUTION_COMPLETE.json').write_text(json.dumps(env,indent=2)+'\n')

if __name__=='__main__':main()
