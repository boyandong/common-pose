"""Resolve provenance-only contact flags; never reads scientific outcome values."""
import csv
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
FINGERS=HERE.parents[3]
BASE=HERE.parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    search=json.loads((HERE/'HISTORICAL_ACCESS_METADATA_AUDIT_V2.json').read_text())
    prior=json.loads((BASE/'paper_closing_v1_20261010/prospective_inventory/AUDIT.json').read_text())
    teacher=FINGERS/'HumanEngine-EMG/humanengine/experiments/real_teacher_v01'
    provenance=json.loads((teacher/'PREREGISTRATION_PROVENANCE_V01.json').read_text())
    plan=json.loads((teacher/'ACQUISITION_PLAN.json').read_text())
    assert sha(teacher/'ACQUISITION_PLAN.json')==provenance['acquisition']['plan_sha256']
    assert len(plan['files'])==provenance['acquisition']['files']==48
    assert plan['total_bytes']==provenance['acquisition']['total_bytes']==871782416
    assert provenance['acquisition']['data_manifest_status']=='frozen_independently_reverified'
    contacts={r['user'] for r in plan['files']};assert len(contacts)==12
    extra=contacts&set(prior['candidate_users'])
    assert len(extra)==7
    reviewed=[];unresolved=[]
    for r in search['candidate_hits']:
        if r['classification']=='KNOWN_METADATA_ONLY':continue
        p=Path(r['source']).as_posix().lower()
        if '/real_teacher_v01/' in p and Path(r['source']).name in ['PREREGISTRATION_PROVENANCE_V01.json','ACQUISITION_PLAN.json']:
            assert r['user'] in contacts
            reviewed.append({**r,'decision':'EXCLUDE_PREVIOUS_CROSS_PROJECT_SCIENTIFIC_WORKFLOW_CONTACT'})
        else:unresolved.append(r)
    assert not unresolved,unresolved
    ids=[]
    with (BASE/'paper_closing_v1_20261010/prospective_inventory/IDENTITY_REGISTRY.csv').open(encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f):
            if r['user_id'] in extra:
                r['status']='CROSS_PROJECT_PRIOR_CONTACT_EXCLUDED'
                r['exposure_evidence']='HumanEngine real_teacher_v01: hash-verified 48-file acquisition plan and provenance of prior scientific workflow'
            ids.append(r)
    with (HERE/'IDENTITY_REGISTRY_PRECHECK.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(ids[0]));w.writeheader();w.writerows(ids)
    candidates=sorted(set(prior['candidate_users'])-extra)
    result={'status':'SCOPED_HISTORY_PRECHECK_PASS_WITH_SEVEN_EXTRA_EXCLUSIONS',
            'original_commonpose_known_exposed':49,'cross_project_extra_excluded':sorted(extra),
            'known_contact_excluded_total':56,'remaining_protected_excluded':10,
            'remaining_metadata_candidates':len(candidates),'candidate_users':candidates,
            'teacher_users':sorted(contacts),'teacher_plan_sha256':sha(teacher/'ACQUISITION_PLAN.json'),
            'teacher_provenance_sha256':sha(teacher/'PREREGISTRATION_PROVENANCE_V01.json'),
            'adjudicated_hits':reviewed,'search_receipt_sha256':sha(HERE/'HISTORICAL_ACCESS_METADATA_AUDIT_V2.json'),
            'code_sha256':sha(Path(__file__)),
            'claim_boundary':'documented gate/cross-project workflow unexposed under audited local provenance; checkpoint-specific upstream membership unresolved; unaudited remote/outside-root/unsaved history remains unknown',
            'no_new_outcome_values_read':True,'no_enrollment_or_selection':True}
    (HERE/'HISTORICAL_ACCESS_ADJUDICATION.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k in ['status','known_contact_excluded_total','remaining_protected_excluded','remaining_metadata_candidates','cross_project_extra_excluded']}))

if __name__=='__main__':main()
