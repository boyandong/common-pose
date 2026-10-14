"""Freeze transport/qualification tools and prior scientific dependency hashes."""
import hashlib
import json
from pathlib import Path
from runtime_common import LANE,ROOT,BASE,sha,read,save

def main():
    cohort=read(LANE/'ENROLLMENT_MANIFEST.json')
    candidates=cohort['candidate_users']
    independent=sorted(candidates,key=lambda u:(hashlib.sha256(('COMMONPOSE_NEW_USER_CONFIRMATION_V1|20261010|'+u).encode('utf-8')).hexdigest(),u))[:80]
    assert independent==cohort['enrolled_users']
    assert len(cohort['files'])==cohort['total_files']==2768
    assert sum(r['size'] for r in cohort['files'])==cohort['total_bytes']==50213536592
    selected=set(cohort['enrolled_users'])
    original=read(BASE/'new_user_preflight_v1_20261010/CANDIDATE_SOURCE_PREFLIGHT_MANIFEST.json')
    assert cohort['files']==sorted([r for r in original['files'] if r['user'] in selected],key=lambda r:(r['user'],r['source_member']))
    parent_names=['gate4c_upstream_substitution_reliability_v1/scripts/run_gate4c.py',
                  'gate4d_task_aware_gate_benchmark_v1/analysis/gate4d_analysis.py',
                  'gate4e_customer_flip_gate_v1/analysis/gate4e_flip_gate.py',
                  'gate4f_class_balanced_flip_gate_v1/analysis/gate4f_balanced_gate.py',
                  'gate3b_continuous_representation/artifacts/FISHER_DB9_REFERENCE_SCALE.json',
                  'gate4e_customer_flip_gate_v1/artifacts/FINAL_GATE_MODEL.joblib',
                  'gate4f_class_balanced_flip_gate_v1/artifacts/FINAL_GATE_MODEL.joblib',
                  'paper_supplement_v1_20261009/analyze_comparisons.py']
    for c in ['U','B']:
        parent_names.extend('paper_supplement_v1_20261009/comparative_analysis/'+name for name in
                            [f'{c}_SUPPLEMENT_INSTANCE.json',f'{c}_class_model_DEV_ONLY.joblib',f'{c}_no_tta_DEV_ONLY.joblib'])
    dependencies={str((BASE/n).relative_to(ROOT)).replace('\\','/'):sha(BASE/n) for n in parent_names}
    dependencies['src/common_pose/representation/canonical_hand.py']=sha(ROOT/'src/common_pose/representation/canonical_hand.py')
    expected={'gate4c_upstream_substitution_reliability_v1/scripts/run_gate4c.py':'e3ca8e3b2a7d4a6059ac5fba9d01df264d329f52dc3497fdcc9cfdc0b4e98091',
              'gate4e_customer_flip_gate_v1/artifacts/FINAL_GATE_MODEL.joblib':'ca06d630e40fc44687bec5ac12c83d9b20aa7c48fe200d89e48d583f9d09f035',
              'gate4f_class_balanced_flip_gate_v1/artifacts/FINAL_GATE_MODEL.joblib':'535828304087d511402c8224ea0276d55e58e0a0c1cba0562bafe7d2d1147b66'}
    for n,h in expected.items():assert sha(BASE/n)==h,n
    names=[p.name for p in LANE.glob('*.py')]+['AUTHORIZATION.json','SCIENTIFIC_SPEC.md','ENROLLMENT_MANIFEST.json','TRANSPORT_ROUTE_AMENDMENT.md']
    save(LANE/'FROZEN_EXECUTION_MANIFEST.json',{
        'status':'FROZEN_BEFORE_SOURCE_DOWNLOAD','scope':'acquisition and source qualification; inference/analysis code separately sealed before first prediction',
        'lane_files':{n:sha(LANE/n) for n in sorted(names)},'parent_dependencies':dependencies,
        'external_dependencies':{'/root/models/emg2pose/regression_vemg2pose.ckpt':'748b1d1ef0ce1985f6fc07225d97eebfb370243429af803b4997d28ecce2424e',
           '/root/work/gate3_work/frozen_head/frozen_db9_trusted8_lda.joblib':'b0ef8caf8e390a480fa2a3b448f79ccf14f75c71265ef925ee299a5e9e660386',
           '/root/work/emg2pose_inference/predict_pose.py':'6cdd060ab639975eb5e2f96bfe43d01371f9f91ec6ecb812c2af2c314bbef818'},
        'numerical_versions':{'numpy':'1.26.4','scipy':'1.13.1','scikit-learn':'1.5.2','joblib':'1.4.2','threadpoolctl':'3.7.0'},
        'upstream_tree_sha256':'0fc2d40b69c46254c9cb4fdc72e7a3e2f37549803e60bb698b6ba09ffecb6b7b',
        'selection_independently_rechecked':True,'local_relay_source_root':'D:/CommonPose_confirmation_N80_20261010/source',
        'no_new_predictions_or_effects':True})
    print(json.dumps({'status':'EXECUTION_SEAL_CREATED','cohort_users':80,'files':2768,'bytes':50213536592,'dependencies':len(dependencies)}))

if __name__=='__main__':main()
