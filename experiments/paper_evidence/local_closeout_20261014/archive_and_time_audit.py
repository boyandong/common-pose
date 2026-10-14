"""Recover existing costs/feasibility and execute synthetic index diagnostics."""
import json
import tarfile
from pathlib import Path

import numpy as np

from analyze_local import dump, sha, table, CONSUMERS

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];BASE=ROOT/'experiments/multi_consumer'


def main():
    out=HERE/'results';costs=[];archives=[]
    for stage,rel in [('four_candidates','v3_ub_four_candidates_20261012/verified_ub_results.tar.gz'),
                      ('five_candidates','v3_full_tta_ablation_20261012/verified_ub_results.tar.gz')]:
        p=BASE/rel;assert p.exists();count=0
        with tarfile.open(p,'r|gz') as t:
            for member in t:
                if not member.isfile() or not member.name.endswith('_instance.json'):continue
                assert member.size<10_000_000
                item=json.loads(t.extractfile(member).read());count+=1
                lane=member.name.split('/')[0]
                for key, seconds in item.get('fit_seconds',{}).items():
                    model=item['models'].get(key,{})
                    costs.append({'stage':stage,'lane':lane,'condition':item['name'],'model':key,
                        'fit_seconds_recorded':seconds,'reused':model.get('reused',False),'model_sha256':model.get('sha256',''),
                        'training_rows':item['sampled_rows'],'scope':item['scope'],
                        'interpretation':'reuse_accounting_not_zero_original_cost' if model.get('reused') else 'recorded_fit_wall_time'})
        archives.append({'stage':stage,'path':str(p.relative_to(ROOT)),'sha256':sha(p),'instances':count})
        assert count==59
    table(out/'RECORDED_TRAINING_COSTS.csv',costs);dump(out/'COST_ARCHIVE_RECEIPT.json',archives)
    cache=json.loads((BASE/'n80_serialization_repair_20261012/CACHE_EXECUTION.json').read_text())
    dump(out/'UPSTREAM_COST_LIMITS.json',{'shared_four_view_files':cache['files'],
        'shared_stage_wall_seconds':cache['GPU_elapsed_seconds'],'includes':['input_reading','hashing','storage','inference'],
        'pure_GPU_time':'UNKNOWN','online_per_input_latency':'UNKNOWN','historic_data_collection_cost':'UNKNOWN',
        'new_local_source_fold_costs':'See SOURCE_LOSO_REPRODUCTION.csv; reproduction CPU timing, not original development cost'})
    registry=json.loads((BASE/'n80_serialization_repair_20261012/verified_local_results/evaluation/FROZEN_REGISTRY.json').read_text())
    feasibility=[]
    for r in registry:
        if r['scope']!='primary':continue
        name=CONSUMERS[(r['lane'],r['name'])]
        for goal in ['U','B']:
            for method in ['boundary','score_only','full_no_tta','full']:
                s=r['selections'][goal+'_'+method];candidate=s['chosen']
                feasibility.append({'consumer':name,'goal':goal,'method':method,'status':s['status'],
                    'feasible':bool(candidate['feasible']),'threshold':candidate['threshold'],
                    'DEV_median_coverage':candidate['median_coverage'],
                    'DEV_quantile':candidate['retention'],'model_sha256':r['models'].get(goal+'_'+method,{}).get('sha256',''),
                    'scope':'frozen_DEV_selection_not_new_search'})
    table(out/'FULL_SCORE_FIXED_THRESHOLD_FEASIBILITY.csv',feasibility)
    # Explicit grids matching torch 1-D interpolate. A shared prefix is extended.
    def resample(values,n,align_corners):
        positions=np.linspace(0,len(values)-1,n) if align_corners else (np.arange(n)+.5)*len(values)/n-.5
        return np.interp(positions,np.arange(len(values)),values)
    feature=np.arange(66,dtype=float)
    a=resample(feature[:53],105,True);b=resample(feature,130,True)
    pose=np.arange(130,dtype=float)
    qa=resample(pose[:105],4210,False);qb=resample(pose,5210,False)
    feature_diff=float(np.max(np.abs(a-b[:105])));pose_diff=float(np.max(np.abs(qa-qb[:4210])))
    assert feature_diff>1e-6 and pose_diff>1e-6
    upstream=ROOT.parent/'emg2pose_handstate/baseline/emg2pose/emg2pose/pose_modules.py'
    expected=json.loads((ROOT/'docs/reviews/20261011_identity_runtime_causality_audit/UPSTREAM_CODE_VERIFICATION.json').read_text())['critical_hashes']['emg2pose/pose_modules.py']
    assert sha(upstream)==expected
    code=upstream.read_text(encoding='utf-8');assert 'align_corners=True' in code and 'interpolate' in code
    dump(out/'SYNTHETIC_TIME_GRID_DIAGNOSTIC.json',{'status':'PASS_LENGTH_DEPENDENCE_REPRODUCED',
        'upstream_pose_modules_sha256':sha(upstream),'raw_lengths':[6000,7000],'native_feature_lengths':[53,66],
        'rollout_lengths':[105,130],'aligned_pose_lengths':[4210,5210],
        'feature_shared_prefix_max_difference':feature_diff,'pose_shared_prefix_max_difference':pose_diff,
        'method':'NumPy explicit align-corners and half-pixel linear index algebra; synthetic ramps',
        'trained_checkpoint_used':False,'real_sensor_synchronization_verified':False,'physical_alignment_verified':False,
        'streaming_pipeline_verified':False})
    print('ARCHIVE_AND_TIME_AUDIT_COMPLETE',len(costs),len(feasibility),flush=True)


if __name__=='__main__':main()
