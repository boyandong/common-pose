"""Metadata-only prospective inventory; never reads candidate signal/outcome arrays.

Historical registry is updated with actually opened FINAL artifacts. Reservations
are excluded independently of exposure. This is an eligibility audit, not cohort
selection, enrollment, a protocol freeze or an assertion of upstream independence.
"""
import csv
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=HERE.parents[2]
OFFICIAL=Path.home()/'Desktop/fingers/emg2pose_handstate'
METADATA=OFFICIAL/'data/official/emg2pose_dataset_mini/metadata.csv'
INDEX=OFFICIAL/'data/priority_pose_subset/raw/tar_index.jsonl'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    out=HERE/'prospective_inventory'
    out.mkdir(exist_ok=False)
    sources={}
    def read(p):
        sources[str(p.relative_to(ROOT))]=sha(p)
        side=p.with_suffix('.sha256')
        if side.exists():assert sources[str(p.relative_to(ROOT))]==side.read_text(encoding='utf-8-sig').split()[0],p
        return json.loads(p.read_text(encoding='utf-8-sig'))
    history=BASE/'final_untouched_cohort_audit_v1'
    old=read(history/'TOUCHED_USER_REGISTRY.json')
    candidates=read(history/'ELIGIBLE_USER_REGISTRY.json')
    locks=read(history/'LOCKED_COHORT_STATUS.json')
    upstream=read(history/'UPSTREAM_EXPOSURE_AUDIT.json')
    final=read(BASE/'final_joint_confirmation_v1/FINAL_COHORT_MANIFEST.json')
    old_ids={r['user_id'] for r in old['users']}
    declared_final={r['user_id'] for r in final['users']}
    # Filenames alone establish opening; this audit does not read old/protected outcomes.
    opened_final={p.stem for p in (BASE/'final_joint_confirmation_v1/artifacts/users').glob('*.json')}
    assert len(opened_final)==20 and opened_final<=declared_final
    assert len(old_ids)==29 and not(old_ids&declared_final)
    touched=old_ids|declared_final|opened_final
    evidence={u:['historical development exposure registry'] for u in old_ids}
    for u in declared_final:evidence[u]=['historical FINAL cohort manifest','existing FINAL user artifact filename']
    # Check later gate manifests/models cannot introduce an unregistered trained user.
    for lane in ['gate4c_upstream_substitution_reliability_v1','gate4d_task_aware_gate_benchmark_v1',
                 'gate4e_customer_flip_gate_v1','gate4f_class_balanced_flip_gate_v1']:
        m=read(BASE/lane/'COHORT_MANIFEST.json')
        ids=set(m.get('users',[])) if isinstance(m.get('users',[]),list) and all(isinstance(x,str) for x in m.get('users',[])) else set()
        ids|={r['participant_id'] for r in m.get('selected_sessions',[]) if 'participant_id' in r}
        ids|={r['participant_id'] for r in m.get('selected_files',[]) if 'participant_id' in r}
        assert ids<=old_ids,(lane,ids-old_ids)
    for lane in ['gate4e_customer_flip_gate_v1','gate4f_class_balanced_flip_gate_v1']:
        m=read(BASE/lane/'artifacts/FINAL_GATE_INSTANCE.json')
        assert set(m['trained_users']+m['calibration_users'])<=old_ids
    for c in ['U','B']:
        m=read(BASE/'paper_supplement_v1_20261009/comparative_analysis'/f'{c}_SUPPLEMENT_INSTANCE.json')
        assert set(m['train']+m['calibration'])<=old_ids
    reserved=set().union(*(set(c['users']) for c in locks['cohorts']))
    unresolved_reservations=reserved-touched
    assert sha(METADATA)==old['metadata_sha256']==candidates['metadata_sha256']
    assert sha(INDEX)==candidates['tar_index_sha256']
    with METADATA.open(encoding='utf-8-sig',newline='') as f:
        official={r['user'] for r in csv.DictReader(f)}
    assert len(official)==193 and touched|reserved<=official
    known_candidates={r['user_id']:r for r in candidates['users']}
    eligible=official-touched-reserved
    assert eligible<=set(known_candidates)
    rows=[]
    for u in sorted(official):
        r=known_candidates.get(u,{})
        status='HISTORICALLY_EXPOSED' if u in touched else 'PROTECTED_RESERVED' if u in reserved else 'METADATA_ELIGIBLE_PENDING_FULL_ACCESS_AUDIT'
        rows.append({'user_id':u,'status':status,'exposure_evidence':'|'.join(evidence.get(u,[])),
                     'protected_reservation':u in reserved,'upstream_membership':'UNKNOWN',
                     'preflight_session_id':r.get('preflight_session_id'),
                     'preflight_files':r.get('preflight_session_recording_count'),
                     'preflight_bytes':r.get('preflight_session_archive_bytes'),
                     'paired_structure':'NOT_YET_CERTIFIED'})
    with (out/'IDENTITY_REGISTRY.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    receipt={'status':'METADATA_AUDIT_COMPLETE_FULL_ACCESS_AUDIT_PENDING','official_users':len(official),
             'historical_development_touched':len(old_ids),'opened_final_users':len(opened_final),
             'total_known_exposed':len(touched),'protected_reservations':len(reserved),
             'protected_already_opened_final':len(reserved&touched),
             'protected_remaining_excluded':len(unresolved_reservations),
             'remaining_metadata_candidates':len(eligible),'candidate_users':sorted(eligible),
             'candidate_preflight_bytes':sum(known_candidates[u]['preflight_session_archive_bytes'] for u in eligible),
             'upstream_training_membership':upstream['checkpoint_specific_training_membership'],
             'checkpoint_sha256':upstream['checkpoint_sha256'],'sources':sources,
             'metadata_sha256':sha(METADATA),'tar_index_sha256':sha(INDEX),'code_sha256':sha(Path(__file__)),
             'scope':'repository manifest and existing filename audit; does not certify all other projects, sessions or remote stores free of exposure; no selection or candidate outcomes'}
    (out/'AUDIT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k in ['status','official_users','total_known_exposed','protected_remaining_excluded','remaining_metadata_candidates','candidate_preflight_bytes']}))

if __name__=='__main__':main()
