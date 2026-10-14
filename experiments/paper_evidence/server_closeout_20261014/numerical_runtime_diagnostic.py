import os
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
os.environ['TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD']='1'
import sys
import json
import time
from pathlib import Path
import numpy as np
import h5py
import torch
from server_common import HERE,REPO,N80,conditions,sha,dump,table


def main():
    cfg=json.loads((REPO/'experiments/multi_consumer/db9_scoreonly_v3_20261011/CONFIG.json').read_text())
    sys.path[:0]=[cfg['upstream_repo'],str(Path(cfg['predict_helper']).parent)]
    from predict_pose import PredictPose
    model=PredictPose(experiment='regression_vemg2pose',checkpoint=cfg['checkpoint'],repo_root=cfg['upstream_repo'],device='cuda')
    cs=conditions();files=sorted(json.loads((N80/'CACHE_ADMISSION.json').read_text())['files'],key=lambda r:(r['user'],r['source_member']))[:3]
    initial={'matmul_tf32':torch.backends.cuda.matmul.allow_tf32,'cudnn_tf32':torch.backends.cudnn.allow_tf32,
        'precision':torch.get_float32_matmul_precision(),'cudnn_deterministic':torch.backends.cudnn.deterministic,
        'cudnn_benchmark':torch.backends.cudnn.benchmark}
    rows=[];decisions=[];failures=[]
    for policy in ['default','IEEE_FP32','deterministic_IEEE_FP32']:
        torch.use_deterministic_algorithms(False)
        torch.set_float32_matmul_precision(initial['precision'] if policy=='default' else 'highest')
        torch.backends.cuda.matmul.allow_tf32=initial['matmul_tf32'] if policy=='default' else False
        torch.backends.cudnn.allow_tf32=initial['cudnn_tf32'] if policy=='default' else False
        torch.backends.cudnn.deterministic=initial['cudnn_deterministic'] if policy=='default' else policy.startswith('deterministic')
        torch.backends.cudnn.benchmark=initial['cudnn_benchmark'] if policy=='default' else False
        torch.use_deterministic_algorithms(policy.startswith('deterministic'))
        for f in files:
            assert sha(f['path'])==f['sha256']
            with h5py.File(f['path']) as h:emg=np.asarray(h['emg2pose']['timeseries']['emg'],dtype=np.float32)
            old=np.load(N80/'runtime_N80'/f['user']/(Path(f['path']).stem+'.npz'),allow_pickle=False);previous=None
            for repeat in range(2):
                try:
                    torch.cuda.synchronize();begin=time.monotonic();p=model.predict(model._as_tensor(emg));torch.cuda.synchronize();seconds=time.monotonic()-begin
                except RuntimeError as exc:
                    failures.append({'policy':policy,'file':Path(f['path']).name,'reason':str(exc)});break
                p=p.detach().cpu().numpy().astype(float) if isinstance(p,torch.Tensor) else np.asarray(p,dtype=float)
                n=len(p)//40;q=p[:n*40,cfg['native_pose_indices']].reshape(n,40,8).mean(1).astype(np.float32)[old['block_index']]
                diff=q.astype(float)-old['pred_pose8'].astype(float)
                rows.append({'policy':policy,'file':Path(f['path']).name,'repeat':repeat,'rows':len(q),'max_abs_rad':float(np.max(np.abs(diff))),
                    'RMS_rad':float(np.sqrt(np.mean(diff**2))),'p99_abs_rad':float(np.quantile(np.abs(diff),.99)),
                    'repeat_max_abs_rad':float(np.max(np.abs(q-previous))) if previous is not None else None,
                    'inference_seconds':seconds,'matmul_tf32':torch.backends.cuda.matmul.allow_tf32,
                    'cudnn_tf32':torch.backends.cudnn.allow_tf32,'matmul_precision':torch.get_float32_matmul_precision()})
                for c in cs:
                    a=c['consumer'].predict(old['pred_pose8'])[0];b=c['consumer'].predict(q)[0];valid=old['gt_valid'];ref=c['consumer'].predict(old['gt_pose8'][valid])[0]
                    decisions.append({'policy':policy,'file':Path(f['path']).name,'repeat':repeat,'consumer':c['lane']+'__'+c['name'],
                        'changed_decisions_fraction':float(np.mean(a!=b)),'paired_old_U':float(np.mean(a[valid]!=ref)),
                        'paired_new_U':float(np.mean(b[valid]!=ref)),'scope':'three_record_runtime_diagnostic_not_new_validation'})
                previous=q.copy()
            print('NUMERICAL_POLICY_FILE_COMPLETE',policy,Path(f['path']).name,flush=True)
    table(HERE/'NUMERICAL_REPRODUCIBILITY.csv',rows);table(HERE/'NUMERICAL_CONSUMER_EFFECTS.csv',decisions)
    dump(HERE/'NUMERICAL_DIAGNOSTIC_RECEIPT.json',{'status':'COMPLETE_DIAGNOSTIC','initial_backend_flags':initial,'failures':failures,
        'records':3,'policies':3,'original_caches_replaced':False,'main_experiment_inputs_changed':False,'scope':'bounded_audit_not_exhaustive_hardware_equivalence'})


if __name__=='__main__':main()
