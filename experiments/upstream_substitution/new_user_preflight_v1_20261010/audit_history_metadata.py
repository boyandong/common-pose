"""Cross-project provenance/filename audit without reading candidate outcomes."""
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE=Path(__file__).resolve().parent
FINGERS=HERE.parents[3]
BASE=HERE.parent
META=FINGERS/'emg2pose_handstate/data/official/emg2pose_dataset_mini/metadata.csv'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    prior=json.loads((BASE/'paper_closing_v1_20261010/prospective_inventory/AUDIT.json').read_text())
    candidates=set(prior['candidate_users'])
    assert sha(META)==prior['metadata_sha256']
    with META.open(encoding='utf-8-sig',newline='') as f:
        records=list(csv.DictReader(f))
    session_user={r['session']:r['user'] for r in records}
    official={r['user'] for r in records}
    args=['rg','--files','--hidden','--no-ignore',str(FINGERS),'-g','!**/.git/**']
    for g in ['*manifest*.json','*provenance*.json','*cohort*.json','*registry*.json','*acquisition*plan*.json']:
        args+=['--iglob',g]
    result=subprocess.run(args,capture_output=True,text=True,encoding='utf-8')
    assert result.returncode==0,result.stderr
    paths=[Path(s) for s in result.stdout.splitlines()]
    hits=[];inventory=[]
    def metadata_only(p):
        s=p.as_posix().lower()
        if s.endswith('gate4b_multiuser_reliability/cohort_manifest.json'):
            selected={r['participant_id'] for r in json.loads(p.read_text())['selected']}
            assert not (selected&candidates)
            return True  # Remaining candidate identifiers occur only in candidate_order.
        return ('new_user_preflight_v1_20261010' in s or 'prospective_inventory' in s or
                'final_untouched_cohort_audit_v1/eligible_user_registry' in s or
                'paper_closing_v1_20261010/release_content_manifest' in s or
                'tar_index.provenance' in s)
    for p in paths:
        # Read provenance identifiers only; no summary/risk/result arrays are opened.
        raw=p.read_bytes();assert len(raw)<20_000_000,p
        text=raw.decode('utf-8-sig')
        ids=set(re.findall(r'(?<![0-9a-f])[0-9a-f]{10}(?![0-9a-f])',text))&official
        sessions=set(re.findall(r'\d{4}-\d{2}-\d{2}-\d{10}-[0-9a-f]+-cv-emg-pose-[^\s"/]+?@2',text))
        ids|={session_user[s] for s in sessions if s in session_user}
        classification='KNOWN_METADATA_ONLY' if metadata_only(p) else 'PROVENANCE_CONTACT_REVIEW'
        inventory.append({'path':str(p.relative_to(FINGERS)),'sha256':hashlib.sha256(raw).hexdigest(),
                          'bytes':len(raw),'official_identifiers':len(ids),'classification':classification})
        for u in sorted(ids&candidates):
            hits.append({'user':u,'source':str(p.relative_to(FINGERS)),
                         'classification':classification,'source_sha256':hashlib.sha256(raw).hexdigest()})
    # Scientific artifact filenames can establish prior processing without reading values.
    artifact=subprocess.run(['rg','--files','--hidden','--no-ignore',str(FINGERS),'-g','*.npz','-g','*.npy','-g','!**/.git/**'],
                            capture_output=True,text=True,encoding='utf-8')
    assert artifact.returncode in [0,1],artifact.stderr
    filenames=artifact.stdout.splitlines()
    for name in filenames:
        p=Path(name);ids=set(re.findall(r'(?<![0-9a-f])[0-9a-f]{10}(?![0-9a-f])',name))&candidates
        ids|={session_user[s] for s in session_user if s in name and session_user[s] in candidates}
        for u in sorted(ids):hits.append({'user':u,'source':str(p.relative_to(FINGERS)),
                                         'classification':'PROCESSED_ARTIFACT_FILENAME_REVIEW','source_sha256':None})
    # Every old FINAL result filename has already been excluded by the parent audit.
    old_final=BASE/'final_joint_confirmation_v1/artifacts/users'
    assert not ({p.stem for p in old_final.glob('*.json')}&candidates)
    ambiguous=sorted({r['user'] for r in hits if r['classification']!='KNOWN_METADATA_ONLY'})
    out={'status':'SCOPED_METADATA_HISTORY_AUDIT_COMPLETE' if not ambiguous else 'CANDIDATE_CONTACT_REVIEW_REQUIRED',
         'scope_root':str(FINGERS),'provenance_files':len(inventory),'processed_artifact_filenames':len(filenames),
         'metadata_candidates':len(candidates),'candidate_contact_review_users':ambiguous,
         'candidate_hits':hits,'inventory':inventory,'code_sha256':sha(Path(__file__)),
         'limitations':'includes locally ignored/hidden provenance and processed-file names; complete remote/private/outside-root and unsaved interactive history is not established by this inventory; no candidate outcome values read'}
    (HERE/'HISTORICAL_ACCESS_METADATA_AUDIT_V2.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k in ['status','provenance_files','processed_artifact_filenames','metadata_candidates','candidate_contact_review_users']}))

if __name__=='__main__':main()
