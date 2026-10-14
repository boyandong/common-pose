"""Offline frozen-estimator cost on three prespecified existing raw recordings."""
import json
import os
import sys
import time
from pathlib import Path

import h5py
import numpy as np
import torch

from server_common import HERE,N80,REPO,sha,dump,table


def main():
    cfg=json.loads((REPO/'experiments/multi_consumer/db9_scoreonly_v3_20261011/CONFIG.json').read_text())
    admission=json.loads((N80/'CACHE_ADMISSION.json').read_text())
    selected=sorted(admission['files'],key=lambda r:(r['user'],r['source_member']))[:3]
    for key in ['checkpoint','predict_helper']:assert sha(cfg[key])==cfg['frozen_inputs'][cfg[key]]
    missing=[r['path'] for r in selected if not Path(r['path']).is_file()]
    if missing:
        dump(HERE/'GPU_COST_RECEIPT.json',{'status':'NOT_AUDITED_RAW_INPUT_UNAVAILABLE','missing':missing});return
    sys.path[:0]=[cfg['upstream_repo'],str(Path(cfg['predict_helper']).parent)]
    os.environ['TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD']='1'
    from predict_pose import PredictPose
    start=time.monotonic();model=PredictPose(experiment='regression_vemg2pose',checkpoint=cfg['checkpoint'],repo_root=cfg['upstream_repo'],device='cuda')
    load_seconds=time.monotonic()-start;assert model.left_context==1790 and model.right_context==0
    rows=[]
    for i,r in enumerate(selected):
        assert sha(r['path'])==r['sha256'];start=time.monotonic()
        with h5py.File(r['path']) as f:emg=np.asarray(f['emg2pose']['timeseries']['emg'],dtype=np.float32)
        read_s=time.monotonic()-start;start=time.monotonic()
        rng=np.random.default_rng(int.from_bytes(__import__('hashlib').sha256(('GATE4D_TTA_NOISE_V1|'+r['source_member']).encode()).digest()[:8],'little'))
        rms=np.sqrt(np.mean(emg.astype(float)**2));noise=rng.standard_normal(emg.shape,dtype=np.float32)
        views=[emg,emg*np.float32(.97),emg*np.float32(1.03),emg+np.float32(.005*rms)*noise];view_s=time.monotonic()-start
        if i==0:
            model.predict(model._as_tensor(emg));torch.cuda.synchronize()
        for repeat in range(2):
            torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize();start=time.monotonic();outputs=[];per=[]
            for view in views:
                torch.cuda.synchronize();ts=time.monotonic();p=model.predict(model._as_tensor(view));torch.cuda.synchronize();per.append(time.monotonic()-ts)
                outputs.append(p.detach().cpu().numpy() if isinstance(p,torch.Tensor) else np.asarray(p))
            torch.cuda.synchronize();infer_s=time.monotonic()-start
            start=time.monotonic();n=len(outputs[0])//40
            pose=np.stack([p[:n*40,cfg['native_pose_indices']].reshape(n,40,8).mean(1) for p in outputs],axis=1)
            aggregate_s=time.monotonic()-start
            old=np.load(N80/'runtime_N80'/r['user']/(Path(r['path']).stem+'.npz'),allow_pickle=False)
            max_delta=float(np.max(np.abs(pose[old['block_index'],0]-old['pred_pose8'])))
            rows.append({'file':Path(r['path']).name,'user':r['user'],'repeat':repeat,'samples':len(emg),
                'nominal_record_seconds':len(emg)/2000,'views':4,'read_seconds':read_s,'view_construction_seconds':view_s,
                'four_view_inference_and_transfer_seconds':infer_s,'single_view_seconds':json.dumps(per),
                'block_aggregation_seconds':aggregate_s,'peak_allocated_bytes':torch.cuda.max_memory_allocated(),
                'peak_reserved_bytes':torch.cuda.max_memory_reserved(),'original_cache_max_abs_difference':max_delta,
                'source_sha256':r['sha256'],'scope':'whole_record_offline_cost_not_causal_latency'})
            print('GPU_COST_PASS',i+1,3,repeat,round(infer_s,3),flush=True)
            dump(HERE/'PROGRESS.json',{'stage':'gpu_offline_cost','completed_files':i,'current_repeat':repeat,'pid':os.getpid()})
        assert sha(r['path'])==r['sha256']
    table(HERE/'GPU_OFFLINE_COST.csv',rows)
    dump(HERE/'GPU_COST_RECEIPT.json',{'status':'COMPLETE_OFFLINE_COST_PROFILE','model_load_seconds':load_seconds,
        'selected_files':[r['source_member'] for r in selected],'timed_passes':len(rows),'warmups':1,
        'cuda_device':torch.cuda.get_device_name(),'torch':torch.__version__,'online_latency_verified':False,'cached_predictions_replaced':False})


if __name__=='__main__':main()
