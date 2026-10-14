"""Frozen C/D/E function reuse; new source/caches only, no fitting or tuning."""
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import joblib
import numpy as np
import torch
from runtime_common import LANE,ROOT,BASE,DATA,frozen,read,rows,paths,load_module,save,sha,progress

def main():
    cohort=frozen(numeric=True)
    seal=read(LANE/'ANALYSIS_CODE_SEAL.json')
    for n,h in seal['files'].items():assert sha(LANE/n)==h,n
    qualification=read(LANE/'SOURCE_QUALIFICATION.json')
    assert qualification['status']=='PASS' and qualification['cohort_sha256']==sha(LANE/'ENROLLMENT_MANIFEST.json')
    rr=rows(cohort)
    os.environ['TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD']='1'
    sys.path[:0]=['/root/work/emg2pose','/root/work/emg2pose_inference',str(ROOT)]
    c=load_module('frozen_c',BASE/'gate4c_upstream_substitution_reliability_v1/scripts/run_gate4c.py')
    d=load_module('frozen_d',BASE/'gate4d_task_aware_gate_benchmark_v1/analysis/gate4d_analysis.py')
    e=load_module('frozen_e',BASE/'gate4e_customer_flip_gate_v1/analysis/gate4e_flip_gate.py')
    assert c.upstream_tree_sha()==read(LANE/'FROZEN_EXECUTION_MANIFEST.json')['upstream_tree_sha256']
    assert torch.cuda.is_available()
    from predict_pose import PredictPose
    bundle=joblib.load(c.HEAD);head,mu,sd=bundle['head'],bundle['mu'],bundle['sd']
    assert list(head.classes_)==list(range(1,9)) and bundle['meta']['replication_check']['exact']
    sigma=np.asarray(read(d.SCALE)['fisher_component_sigma_db9'])
    model=PredictPose(experiment='regression_vemg2pose',checkpoint=str(c.CKPT),repo_root='/root/work/emg2pose',device='cuda')
    assert model.left_context==1790 and model.right_context==0
    assert next(model._module.parameters()).is_cuda
    plan_sha=sha(LANE/'SCIENTIFIC_SPEC.md');cohort_sha=sha(LANE/'ENROLLMENT_MANIFEST.json');runner_sha=sha(Path(__file__))
    def base_loader(r):
        bp,_=paths(r)
        assert c.receipt_ok(bp,bp.with_suffix('.json'),r,plan_sha,cohort_sha,runner_sha)
        with np.load(bp) as z:return {k:z[k] for k in z.files}
    d.paths=paths;d.load_base=base_loader
    runtime={'torch':torch.__version__,'cuda_version':torch.version.cuda,'device':torch.cuda.get_device_name(),
             'numpy':np.__version__,'python':sys.version,'cohort_sha256':cohort_sha,'runner_sha256':runner_sha,
             'analysis_seal_sha256':sha(LANE/'ANALYSIS_CODE_SEAL.json'),'no_fitting':True}
    if not (LANE/'RECONSTRUCTION_RUNTIME.json').exists():save(LANE/'RECONSTRUCTION_RUNTIME.json',runtime)
    else:assert read(LANE/'RECONSTRUCTION_RUNTIME.json')==runtime
    from collections import defaultdict
    groups=defaultdict(list)
    for r in rr:groups[r['participant_id']].append(r)
    W=np.linalg.lstsq(head.scalings_,head.coef_.T,rcond=None)[0]
    assert np.max(np.abs(head.scalings_@W-head.coef_.T))<1e-10
    units=[];norms=np.empty((8,8))
    for i,j in e.PAIRS:
        delta=W[:,i]-W[:,j];norm=float(np.linalg.norm(delta));assert norm>0
        units.append(delta/norm);norms[i,j]=norms[j,i]=norm
    np.fill_diagonal(norms,np.inf);units=np.asarray(units).T
    started=time.monotonic();done=0;feature_inventory=[]
    for u in sorted(groups):
        for r in groups[u]:
            bp,tp=paths(r)
            if bp.exists() and not c.receipt_ok(bp,bp.with_suffix('.json'),r,plan_sha,cohort_sha,runner_sha):
                raise RuntimeError('existing base differs; preserve '+str(bp))
            if not bp.exists():c.one(r,model,head,mu,sd,DATA/'base',plan_sha,cohort_sha,runner_sha)
            if tp.exists():
                meta=read(tp.with_suffix('.json'))
                assert meta['input_sha256']==r['sha256'] and meta['output_sha256']==sha(tp)
            d.tta_one(r,model,head,mu,sd,sigma)
            lineage=tp.with_suffix('.lineage.json')
            lineage_obj={'cohort_sha256':cohort_sha,'plan_sha256':plan_sha,'runner_sha256':runner_sha,
                         'input_sha256':r['sha256'],'base_sha256':sha(bp),'tta_sha256':sha(tp),
                         'original_tta_code_sha256':sha(BASE/'gate4d_task_aware_gate_benchmark_v1/analysis/gate4d_analysis.py')}
            if lineage.exists():assert read(lineage)==lineage_obj
            else:save(lineage,lineage_obj)
            done+=1
            if done%5==0:
                progress('RECONSTRUCTION_RUNNING',completed_files=done,required_files=len(rr),elapsed_seconds=time.monotonic()-started)
                print('RECONSTRUCTED',done,len(rr),flush=True)
        fp=DATA/'features/FINAL'/(u+'.npz');receipt=fp.with_suffix('.json')
        source_hashes={r['source_member']:{'source':r['sha256'],'base':sha(paths(r)[0]),'tta':sha(paths(r)[1])} for r in groups[u]}
        if fp.exists():
            meta=read(receipt);assert meta['sha256']==sha(fp) and meta['inputs']==source_hashes
        else:
            v=e.load_user(groups[u],SimpleNamespace(paths=paths,load_base=base_loader),head,sigma,units,norms)
            fp.parent.mkdir(parents=True,exist_ok=True)
            with fp.open('wb') as f:np.savez_compressed(f,**{k:v[k] for k in ['x','flip','ygt','ypred']})
            save(receipt,{'user':u,'sha256':sha(fp),'inputs':source_hashes,'paired_blocks':len(v['flip']),
                          'runner_sha256':runner_sha,'cohort_sha256':cohort_sha,'no_fitting':True})
        fp.with_suffix('.sha256').write_text(sha(fp)+'  '+fp.name+'\n')
        feature_inventory.append(read(receipt))
        print('FEATURES_READY',u,read(receipt)['paired_blocks'],flush=True)
    save(LANE/'FEATURE_CACHE_MANIFEST.json',{'status':'COMPLETE','users':80,'files':feature_inventory,
          'cohort_sha256':cohort_sha,'runner_sha256':runner_sha,'effects_analyzed':False})
    progress('FEATURES_COMPLETE',users=80,files=done,elapsed_seconds=time.monotonic()-started)

if __name__=='__main__':main()
