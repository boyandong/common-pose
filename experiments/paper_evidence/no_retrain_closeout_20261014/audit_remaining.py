"""Rehash provenance, recompute geometry/index algebra, consolidate existing costs."""
import csv,json,hashlib,math,ast
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
AUDIT=ROOT/'docs/reviews/20261014_embc_no_supplement_audit'
LOCAL=ROOT/'experiments/paper_evidence/local_closeout_20261014';SERVER=ROOT/'experiments/paper_evidence/server_closeout_20261014'
MULTI=ROOT/'experiments/multi_consumer'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def read(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def dump(n,r):(HERE/n).write_text(json.dumps(r,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
def table(n,rows):
    with (HERE/n).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def provenance():
    checkpoint=ROOT.parent/'emg2pose_handstate/checkpoints/emg2pose_model_checkpoints/regression_vemg2pose.ckpt'
    meta=ROOT.parent/'emg2pose_handstate/data/priority_pose_subset/raw/emg2pose_metadata.csv'
    provenance=MULTI/'consumer2_target_A_v1_20261011/checkpoint_provenance'
    release=load(provenance/'OFFICIAL_RELEASE_BINARY_IDENTITY.json');data=load(provenance/'OFFICIAL_DATA_VERSION_OBSERVATION.json')
    inspection=load(ROOT/'docs/reviews/20261011_identity_runtime_causality_audit/CHECKPOINT_INSPECTION.json')
    assert sha(checkpoint)==release['actual_checkpoint_sha256']==inspection['checkpoint_sha256']
    assert sha(meta)==data['local_metadata_sha256']==data['current_official_metadata_sha256']
    assert not inspection['participant_session_or_dataset_manifest_keys_present']
    dump('PROVENANCE_REHASH.json',{'status':'PASS','checkpoint_sha256':sha(checkpoint),'checkpoint_bytes':checkpoint.stat().st_size,'metadata_sha256':sha(meta),'release_member_identity':release['matching_members'],'released_checkpoint_specific_membership':'UNKNOWN','inspection_binding_sha256':sha(ROOT/'docs/reviews/20261011_identity_runtime_causality_audit/CHECKPOINT_INSPECTION.json'),'scope':'current local bytes bind to archived official receipt, not a new full release download'})
    scopes=[]
    for base in [provenance,ROOT.parent/'emg2pose_handstate/baseline/emg2pose/config',ROOT.parent/'emg2pose_handstate/checkpoints',ROOT.parent/'_recon_emg2pose']:
        files=[p for p in base.rglob('*') if p.is_file() and p.suffix.lower() in ['.json','.yaml','.yml','.csv','.ckpt','.md','.txt']]
        candidates=[p for p in files if any(k in p.name.lower() for k in ['manifest','hparams','run_config','training_users','train_records','hydra'])]
        scopes.append({'root':str(base.resolve()),'exists':base.exists(),'files_in_scope':len(files),'candidate_paths':[str(p.resolve()) for p in candidates],'interpretation':'candidate filenames are not checkpoint-run proof'})
    dump('TRAINING_RUN_SEARCH_SCOPE.json',{'local_scope':scopes,'release_archive_receipt_sha256':sha(provenance/'OFFICIAL_RELEASE_BINARY_IDENTITY.json'),'no_sha_bound_run_manifest_established_in_examined_evidence':True,'not_an_exhaustive_search_of_every_device_or_publisher_internal_system':True,'no_contacts_sent':True})

def physical():
    names=['thumb_MCP','thumb_IP','index_MCP','index_PIP','middle_MCP','ring_MCP','pinky_MCP','pinky_PIP']
    ids=[2,3,5,6,9,13,17,18];show=MULTI/'show3d_scoreonly_v3_20261012'
    admission=load(show/'NATIVE_ADMISSION.json');generic=load(show/'UPSTREAM_GENERIC_HAND_MODEL.json')
    assert sha(show/'UPSTREAM_GENERIC_HAND_MODEL.json')==admission['generic_reference_sha256']
    axes=np.asarray(generic['joint_rotation_axes']);geometry=[]
    def bend(positions,k):
        a=np.array(positions[k])-positions[k-1];b=np.array(positions[k+1])-positions[k]
        return math.degrees(math.atan2(float(np.linalg.norm(np.cross(a,b))),float(a@b)))
    gr=[bend(generic['joint_rest_positions'],k) for k in [6,18]]
    assert np.allclose(gr,admission['generic_PIP2_PIP5_model_rest_bend_degrees'],atol=1e-9,rtol=0)
    for old in admission['profiles']:
        path=ROOT.parent/'common-pose-data/show3d_native_20261012/hand_pose/hand_profiles'/old['subject']/'profile_umetrack.json'
        assert sha(path)==old['sha256'];m=load(path)['hand_model'];aa=np.asarray(m['joint_rotation_axes'])
        assert m['joint_parent'][:20]==generic['joint_parent'][:20] and m['joint_frame_index'][:20]==generic['joint_frame_index'][:20]
        cos=np.array([float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b))) for a,b in zip(aa,axes)])[ids]
        rest=[bend(m['joint_rest_positions'],k) for k in [6,18]]
        assert np.allclose(cos,old['trusted8_axis_cosines'],atol=1e-12,rtol=0) and np.allclose(rest,old['PIP2_PIP5_model_rest_bend_degrees'],atol=1e-9,rtol=0)
        geometry.append({'subject':old['subject'],'profile_sha256':sha(path),'min_trusted8_axis_cosine':float(cos.min()),'PIP2_rest_bend_deg':rest[0],'PIP5_rest_bend_deg':rest[1],'generic_PIP2_rest_deg':gr[0],'generic_PIP5_rest_deg':gr[1],'PIP2_difference_deg':rest[0]-gr[0],'PIP5_difference_deg':rest[1]-gr[1],'topology_equal':True,'physical_neutral_measured':False})
    assert len(geometry)==16;table('SHOW_PROFILE_GEOMETRY_RECOUNT.csv',geometry)
    ceti=load(MULTI/'ceti_age_scoreonly_v3_20261012/SOURCE_ADMISSION.json');kin=load(MULTI/'kinmus_uji_scoreonly_v3_20261012/SOURCE_ADMISSION.json')
    assert ceti['interface']['source_columns_zero_based']==[1,2,4,5,7,11,15,16] and kin['trusted8_columns']==[2,3,5,6,7,10,14,15]
    db9=read(ROOT/'experiments/upstream_substitution/pre_substitution_reconciliation/artifacts/TRUSTED8_EVIDENCE_MATRIX.csv')
    assert [int(r['db9_source_index']) for r in db9]==[2,3,4,6,7,9,13,15]
    matrix=[]
    for source,columns,unit,calibration,evidence in [
        ('DB9 posture',[2,3,4,6,7,9,13,15],'degree','published post-calibration; raw-column affine map audited','TRUSTED8_EVIDENCE_MATRIX.csv'),
        ('DB9 grasp',[2,3,4,6,7,9,13,15],'degree','published post-calibration; raw-column affine map audited','TRUSTED8_EVIDENCE_MATRIX.csv'),
        ('CeTI posture',ceti['interface']['source_columns_zero_based'],'degree','published offset/gain/cross-coupling; source exclusion S50 preserved','CeTI SOURCE_ADMISSION.json'),
        ('CeTI grasp',ceti['interface']['source_columns_zero_based'],'degree','published offset/gain/cross-coupling; source exclusion S50 preserved','CeTI SOURCE_ADMISSION.json'),
        ('SHOW instruction',ids,'radian','per-user UmeTrack profile; model rest differs from target generic model','NATIVE_ADMISSION.json and recomputed profile geometry'),
        ('KIN phase',kin['trusted8_columns'],'degree','published validated anatomical glove angles; no new calibration','KIN SOURCE_ADMISSION.json')]:
        for j,name in enumerate(names):matrix.append({'consumer':source,'joint':name,'source_column':columns[j],'target_native_column':ids[j],'source_units':unit,'target_units':'radian','conversion':'identity' if unit=='radian' else 'pi/180','calibration_provenance':calibration,'definition_evidence':evidence,'positive_flexion_evidence':'documented/previously audited convention; no new participant physical sign measurement','left_right_scope':'source conventions preserved; not a new bilateral equivalence measurement','absolute_zero_equivalence':'NOT_ESTABLISHED','common_independent_physical_anchor':'UNAVAILABLE','pose_transform_fitted':False})
    table('PHYSICAL_INTERFACE_EVIDENCE_48.csv',matrix)
    anchor=load(ROOT/'experiments/upstream_substitution/gate1_5_reference_zero/artifacts/REFERENCE_ANCHOR_DECISION.json')
    zero=load(ROOT/'experiments/upstream_substitution/gate1_5_reference_zero/artifacts/TRUSTED8_ZERO_COMPATIBILITY.json')
    assert zero['ANCHOR_STATUS']=='NO_INDEPENDENT_ANCHOR'
    dump('PHYSICAL_RECOUNT_RECEIPT.json',{'status':'PASS_DOCUMENTARY_AND_GEOMETRY_RECOUNT','interface_rows':48,'profiles_recomputed':16,'generic_rest_bend_degrees':gr,'trusted8_axis_cosine_min':min(r['min_trusted8_axis_cosine'] for r in geometry),'rest_difference_does_not_measure_physical_calibration_error':True,'anchor_decision_sha256':sha(ROOT/'experiments/upstream_substitution/gate1_5_reference_zero/artifacts/REFERENCE_ANCHOR_DECISION.json'),'anchor_status':zero['ANCHOR_STATUS'],'no_new_physical_observation':True})

def time_audit():
    verified=load(ROOT/'docs/reviews/20261011_identity_runtime_causality_audit/UPSTREAM_CODE_VERIFICATION.json')
    upstream=ROOT.parent/'emg2pose_handstate/baseline/emg2pose'
    assert all(sha(upstream/n)==h for n,h in verified['critical_hashes'].items())
    source=MULTI/'n80_all_dataset_supplement_20261012/reconstruct_runtime_tta.py';code=source.read_text()
    required=["gt=np.asarray(ts['joint_angles'])[1790:]","times=np.asarray(ts['time'])[1790:]","assert pred.shape==gt.shape","pred[:end].reshape(n,40,20).mean(1)","q=gt[:end].reshape(n,40,20).mean(1)","times[:end].reshape(n,40)[:,-1][blocks]","pok[0]=False","gok[0]=False"]
    assert all(v in code for v in required)
    rows=[];checks=0
    for length in [1791,1830,1831,1869,1870,1871,6000,7000,11790,200001]:
        n=(length-1790)//40;grid=np.arange(length,dtype=np.int64);crop=grid[1790:];actual=crop[:n*40].reshape(n,40)
        expected=1790+40*np.arange(n)[:,None]+np.arange(40)[None,:]
        assert np.array_equal(actual,expected);assert np.array_equal(actual[:,-1],1790+40*np.arange(n)+39) if n else True
        assert np.allclose(actual.mean(axis=1),1790+40*np.arange(n)+19.5)
        runtime=np.arange(1,n);assert all(np.array_equal(actual[b],np.arange(1790+40*b,1790+40*(b+1))) for b in runtime)
        rows.append({'input_rows':length,'post_crop_rows':length-1790,'complete_blocks':n,'dropped_tail_rows':(length-1790)%40,'max_runtime_blocks_after_first_exclusion':max(n-1,0),'first_possible_raw_block_start':1830 if n>1 else None,'nominal_block_period_ms':20,'nominal_start_to_end_span_ms':19.5,'label_time':'raw block last timestamp','model_run':False});checks+=n*40+max(n-1,0)+3
    table('SYNTHETIC_BLOCK_TIME_MAPPING.csv',rows)
    dump('TIME_CORRESPONDENCE_RECOUNT.json',{'status':'PASS_INDEX_ALGEBRA_AND_FROZEN_CODE_BINDING','checks':checks,'source_sha256':sha(source),'critical_upstream_files':len(verified['critical_hashes']),'startup_history_ms':895,'startup_history_is_fixed_inference_latency':False,'author_reported_sensor_relative_latency_ms_upper_bound':10,'author_report_is_our_measurement':False,'raw_sensor_synchronization_independently_measured':False,'whole_record_prefix_causality_verified':False,'references':['https://arxiv.org/html/2412.02725v1#S3.SS2','https://arxiv.org/html/2412.02725v1#A2.SS2']})

def costs():
    ledger=[]
    for r in read(LOCAL/'results/RECORDED_TRAINING_COSTS.csv'):
        ledger.append({'batch':r['stage'],'consumer':r['lane']+'__'+r['condition'],'model':r['model'],'fit_seconds':float(r['fit_seconds_recorded']),'reused':r['reused'],'model_sha256':r['model_sha256'],'scope':'old archived rows; may repeat across stages; not total historical cost'})
    fit=load(SERVER/'verified_remote/results/FACTORIAL_FIT_RECEIPT.json')
    for c in fit['conditions']:
        for key,m in c['models'].items():
            if not m['reused']:ledger.append({'batch':'new_factorial_60','consumer':c['consumer'],'model':key,'fit_seconds':c['fit_seconds'][key],'reused':'False','model_sha256':m['sha256'],'scope':'recorded timer includes model fitting and serialization; excludes threshold prediction/selection'})
    fields=load(SERVER/'verified_remote/field_delivery/results/score_field_ablation/FIT_RECEIPT.json')
    for m in fields['models']:ledger.append({'batch':'new_field_removals_42','consumer':m['consumer'],'model':m['removed_group'],'fit_seconds':m['fit_seconds'],'reused':'False','model_sha256':m['model_sha256'],'scope':'recorded timer includes fitting/serialization/hash/threshold prediction and selection; not isolated model fit'})
    table('FIT_COST_LEDGER.csv',ledger);batches=[]
    for batch in ['new_factorial_60','new_field_removals_42']:
        rr=[r for r in ledger if r['batch']==batch];seconds=[r['fit_seconds'] for r in rr]
        scope='fit plus serialization, before threshold selection' if batch=='new_factorial_60' else 'fit plus serialization/hash and DEV threshold evaluation/selection'
        batches.append({'batch':batch,'fits':len(rr),'sum_logged_stage_seconds':sum(seconds),'median_logged_stage_seconds':float(np.median(seconds)),'min_logged_stage_seconds':min(seconds),'max_logged_stage_seconds':max(seconds),'scope':scope+'; excludes shared input and test evaluation/package phases'})
    assert [r['fits'] for r in batches]==[60,42];table('NEW_FIT_COST_SUMMARY.csv',batches)
    gpu=read(SERVER/'verified_remote/results/GPU_OFFLINE_COST.csv');cpu=read(SERVER/'verified_remote/OFFLINE_POSTPROCESS_COST.csv');phase=[]
    for name,rr,col in [('four_view_inference_and_transfer',gpu,'four_view_inference_and_transfer_seconds'),('block_aggregation',gpu,'block_aggregation_seconds'),('CPU_feature_and_reference',cpu,'feature_and_reference_seconds'),('CPU_original_full_score',cpu,'score_seconds')]:
        x=[float(r[col]) for r in rr];phase.append({'phase':name,'samples':len(x),'records':3,'participants':1,'min_seconds':min(x),'median_seconds':float(np.median(x)),'max_seconds':max(x),'p95_seconds':float(np.quantile(x,.95)),'scope':'whole-record bounded profile; repeats not independent population samples'})
    table('OFFLINE_PHASE_COST_SUMMARY.csv',phase)
    old=load(LOCAL/'results/UPSTREAM_COST_LIMITS.json');main=load(SERVER/'verified_remote/PIPELINE_STATE.json');field=load(SERVER/'verified_remote/SCORE_FIELD_STATE.json')
    dump('COST_SCOPE_RECEIPT.json',{'status':'EXISTING_LOGS_CONSOLIDATED','ledger_rows':len(ledger),'old_log_rows':len(ledger)-102,'old_unique_model_hashes':len({r['model_sha256'] for r in ledger if not r['batch'].startswith('new_')}),'old_logged_rows_not_summed_as_total':True,'new_fit_batches':batches,'shared_cache_stage_wall_seconds':old['shared_stage_wall_seconds'],'cache_wall_is_pure_GPU_time':False,'main_controller_wall_seconds':main['elapsed_seconds'],'field_controller_wall_seconds':field['elapsed_seconds'],'controller_wall_is_independent_experiment_latency':False,'history_acquisition_and_development_total':'UNKNOWN_NO_COMPLETE_RECORDS','online_causal_latency':'UNMEASURED_SEPARATE_BRANCH','source_LOSO_replay_log':str(LOCAL/'results/source_replay/SOURCE_LOSO_FOLDS.csv'),'no_new_timing_run':True})

if __name__=='__main__':
    provenance();physical();time_audit();costs();print('NO_RETRAIN_AUDITS_COMPLETE')
