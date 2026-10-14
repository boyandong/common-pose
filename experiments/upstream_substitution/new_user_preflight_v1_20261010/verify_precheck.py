"""Independent receipt and metadata checks; no predictions/outcome arrays read."""
import collections
import csv
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
FINGERS = HERE.parents[3]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(name):
    return json.loads((HERE/name).read_text(encoding='utf-8'))

def main():
    history=load('HISTORICAL_ACCESS_ADJUDICATION.json')
    manifest=load('CANDIDATE_SOURCE_PREFLIGHT_MANIFEST.json')
    complete=load('SOURCE_METADATA_PREFLIGHT_COMPLETE.json')
    initial=load('SOURCE_METADATA_PREFLIGHT.json')
    retry=load('SOURCE_METADATA_TRANSPORT_RETRY.json')
    budget=load('RESOURCE_BUDGET.json')
    capacity=load('REMOTE_CAPACITY_RECHECK_AFTER_USER_UPDATE.json')
    with (HERE/'IDENTITY_REGISTRY_PRECHECK.csv').open(encoding='utf-8',newline='') as f:
        registry=list(csv.DictReader(f))
    by_user={r['user_id']:r for r in registry}
    assert len(by_user)==len(registry)==193
    counts=collections.Counter(r['status'] for r in registry)
    assert counts=={'HISTORICALLY_EXPOSED':49,'CROSS_PROJECT_PRIOR_CONTACT_EXCLUDED':7,
                    'PROTECTED_RESERVED':10,'METADATA_ELIGIBLE_PENDING_FULL_ACCESS_AUDIT':127}
    candidates=set(history['candidate_users'])
    assert len(candidates)==127 and candidates=={u for u,r in by_user.items() if r['status']=='METADATA_ELIGIBLE_PENDING_FULL_ACCESS_AUDIT'}
    assert not candidates.intersection(history['teacher_users'])
    assert manifest['exposure_adjudication_sha256']==sha(HERE/'HISTORICAL_ACCESS_ADJUDICATION.json')
    source=FINGERS/'emg2pose_handstate/data'
    metadata=source/'official/emg2pose_dataset_mini/metadata.csv'
    index=source/'priority_pose_subset/raw/tar_index.jsonl'
    assert sha(metadata)==manifest['metadata_sha256'] and sha(index)==manifest['tar_index_sha256']
    with metadata.open(encoding='utf-8',newline='') as f:
        official={r['filename']:r for r in csv.DictReader(f)}
    tar={r['name']:r for r in (json.loads(line) for line in index.read_text().splitlines())}
    files=manifest['files']; names={r['source_member'] for r in files}
    assert len(names)==len(files)==manifest['records']==4285
    assert {r['user'] for r in files}==candidates
    assert sum(r['size'] for r in files)==manifest['bytes']==77844377520
    expected_names=set()
    for r in official.values():
        if r['user'] in candidates and r['session']==by_user[r['user']]['preflight_session_id']:
            expected_names.add('emg2pose_data/'+r['filename']+'.hdf5')
    assert names==expected_names
    for r in files:
        item=tar[r['source_member']]
        raw=official[Path(r['source_member']).stem]
        assert (r['user'],r['session'],r['side'])==(raw['user'],raw['session'],raw['side'])
        assert r['size']==item['size'] and r['archive_header_offset']==item['offset']
        assert r['archive_data_offset']==item['offset']+512
        assert r['archive_data_offset']%512==0 and 0<r['size']
        assert r['archive_data_offset']+r['size']<=manifest['archive_bytes']
    def key(r):return r['user'],r['side'],r['source_member']
    expected_probe={key(min(group,key=lambda r:r['source_member'])) for _,group in
                    __import__('itertools').groupby(sorted(files,key=lambda r:(r['user'],r['side'],r['source_member'])),key=lambda r:(r['user'],r['side']))}
    assert len(expected_probe)==254
    failed={key(r) for r in initial['failed_probes']}
    assert len(failed)==3 and all('UNEXPECTED_EOF' in r['detail'] for r in initial['failed_probes'])
    assert {key(r) for r in retry['results']}==failed and not retry['failed_probes']
    merged={key(r):r for r in initial['results'] if r['status']=='METADATA_SCHEMA_PASS'}
    merged.update({key(r):r for r in retry['results']})
    assert merged=={key(r):r for r in complete['results']} and set(merged)==expected_probe
    assert not complete['failed_probes']
    assert complete['initial_receipt_sha256']==sha(HERE/'SOURCE_METADATA_PREFLIGHT.json')
    assert complete['retry_receipt_sha256']==sha(HERE/'SOURCE_METADATA_TRANSPORT_RETRY.json')
    for r in merged.values():
        assert r['status']=='METADATA_SCHEMA_PASS' and r['no_timeseries_array_reads'] is True
        assert r['rows']>1870 and r['emg_shape']==[r['rows'],16] and r['joint_angle_shape']==[r['rows'],20]
    per_user=collections.Counter(); per_files=collections.Counter()
    for r in files:per_user[r['user']]+=r['size'];per_files[r['user']]+=1
    bounds=[sum(sorted(per_user.values())[:80]),sum(sorted(per_user.values())[-80:])]
    assert bounds==budget['source_bytes_range']
    assert [sum(sorted(per_files.values())[:80]),sum(sorted(per_files.values())[-80:])]==budget['source_files_range']
    cache=load('REMOTE_RESOURCE_OBSERVATION.json')['cache_sizes']
    for i in [0,1]:
        projected=sum(bounds[i]*cache[k]['bytes']/25141054576 for k in ['reconstructed/base','reconstructed/tta','features'])
        assert math.isclose(projected,budget['projected_cache_total_bytes'][i],rel_tol=1e-12)
        needed=bounds[i]+projected+11_500_000_000
        assert math.isclose(needed,budget['remote_additional_working_bytes_range'][i],rel_tol=1e-12)
        assert needed==budget['local_D_backup_bytes_range'][i]
    assert budget['capacity_receipt_sha256']==sha(HERE/'REMOTE_CAPACITY_RECHECK_AFTER_USER_UPDATE.json')
    assert capacity['data_disk']['total']==214748364800
    assert capacity['data_disk']['free']>=max(budget['remote_additional_working_bytes_range'])
    assert budget['local_disk_observations']['D']['free']>=max(budget['local_D_backup_bytes_range'])
    assert budget['planned_enrolled_users']==80 and budget['valid_nonzero_pairs_assumed'] is False
    assert budget['user_waived_currency_budget'] and budget['monetary_budget_requested'] is False
    scale=load('FISHER_SCALE_RECHECK.json')
    assert scale['status']=='PASS' and scale['sha256']==scale['expected_sha256']
    receipt={'status':'SCOPED_METADATA_AND_RESOURCE_PRECHECK_VERIFIED',
             'official_users':193,'known_contact_excluded':56,'remaining_protected_excluded':10,
             'metadata_candidates':127,'source_manifest_records':4285,'sampled_hand_schema_pass':254,
             'same_member_TLS_only_retries':3,'remote_capacity_pass':True,'local_backup_capacity_pass':True,
             'enrollment_selected':False,'new_predictions_or_effect_values_read':False,
             'full_source_hash_and_sample_validity':'NOT_YET_AUDITED',
             'upstream_training_membership':'UNRESOLVED',
             'history_scope':'local fingers provenance, including hidden/ignored manifests and processed filenames; outside-root, unsaved and private remote history not certified absent',
             'artifact_sha256':{n:sha(HERE/n) for n in ['HISTORICAL_ACCESS_ADJUDICATION.json','IDENTITY_REGISTRY_PRECHECK.csv','CANDIDATE_SOURCE_PREFLIGHT_MANIFEST.json','SOURCE_METADATA_PREFLIGHT_COMPLETE.json','SOURCE_METADATA_PREFLIGHT.json','SOURCE_METADATA_TRANSPORT_RETRY.json','REMOTE_CAPACITY_RECHECK_AFTER_USER_UPDATE.json','RESOURCE_BUDGET.json']},
             'code_sha256':sha(Path(__file__))}
    (HERE/'PRECHECK_VERIFICATION.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in receipt.items() if k not in ['artifact_sha256','history_scope','code_sha256']}))

if __name__=='__main__':main()
