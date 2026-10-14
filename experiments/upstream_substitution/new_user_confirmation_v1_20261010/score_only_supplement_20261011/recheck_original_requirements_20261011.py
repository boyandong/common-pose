"""Rehash completed original requirements without rerunning or selecting science."""
import csv
import datetime
import hashlib
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from runtime_common import BASE,LANE,ROOT,read,save,sha

HERE=Path(__file__).resolve().parent

def main():
    old=BASE/'paper_closing_v1_20261010'
    release=read(old/'RELEASE_CONTENT_MANIFEST.json')
    anchor=read(old/'GIT_RELEASE_RECEIPT.json')['commit']
    for n,h in release['files'].items():
        assert sha(ROOT/n)==h,n
        blob=subprocess.check_output(['git','show',anchor+':'+n],cwd=ROOT)
        assert hashlib.sha256(blob).hexdigest()==h,n
    backups=[]
    for n in ['LOCAL_BACKUP_VERIFICATION.json','REPORTING_SEED_BACKUP_MANIFEST.json']:
        r=read(old/n);p=old/r['archive']
        assert r['status']=='PASS' and p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
        backups.append({'receipt':n,'archive':p.name,'bytes':p.stat().st_size,'sha256':sha(p),'scope':'fresh archive rehash against frozen prior member verification'})
    seed=old/'reproduction_attempt3_8threads/seed_results'
    manifest=read(seed/'RUN_MANIFEST.json')
    for n,h in manifest['files'].items():assert sha(seed/n)==h,n
    independent=read(seed.parent/'INDEPENDENT_VERIFICATION.json')
    assert independent['status']=='PASS' and independent['canonical_max_abs_difference']==0
    counts={}
    for n,count in [('SEED_USER_RISKS.csv',4680),('SEED_CLASS_SUPPORT.csv',37440),('SEED_PAIRED_EFFECTS.csv',3120),('CANONICAL_SEED_ADMISSION.csv',702)]:
        with (seed/n).open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
        assert len(rows)==count,n
        counts[n]=count
    pre=BASE/'new_user_preflight_v1_20261010'
    audit=read(pre/'PRECHECK_VERIFICATION.json')
    for n,h in audit['artifact_sha256'].items():assert sha(pre/n)==h,n
    history=read(pre/'HISTORICAL_ACCESS_ADJUDICATION.json')
    cohort=read(LANE/'ENROLLMENT_MANIFEST.json')
    ordered=sorted(history['candidate_users'],key=lambda u:(hashlib.sha256((cohort['selection_namespace']+u).encode()).hexdigest(),u))[:80]
    assert ordered==cohort['enrolled_users']
    source=read(pre/'CANDIDATE_SOURCE_PREFLIGHT_MANIFEST.json')
    selected=[r for r in source['files'] if r['user'] in set(ordered)]
    assert len(selected)==len(cohort['files'])
    assert {r['source_member']:r for r in selected}=={r['source_member']:r for r in cohort['files']}
    registration=read(HERE/'MODEL_REGISTRATION.json')
    for model in registration['models'].values():
        assert not (set(model['train'])|set(model['calibration'])) & set(ordered)
    result={'status':'COMPLETED_ORIGINAL_REQUIREMENTS_CURRENTLY_REVERIFIED_N80_PENDING','observed_local_time':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'old_git_anchor':anchor,'release_file_and_git_blob_hashes_checked':len(release['files']),'old_backups':backups,'old_20seed_files_rehashed':len(manifest['files']),'old_20seed_row_counts':counts,'old_independent_verification_sha256':sha(seed.parent/'INDEPENDENT_VERIFICATION.json'),'old_independent_status':independent['status'],'canonical_max_abs_difference':independent['canonical_max_abs_difference'],'history_artifact_hashes_checked':len(audit['artifact_sha256']),'history_scope':audit['history_scope'],'upstream_membership':audit['upstream_training_membership'],'N80_selection_and_members_rederived':True,'score_only_old_DEV_users_disjoint':True,'N80_effect_values_read':False,'historical_score_only_deferral':'historical only; GOAL_SCOPE_AMENDMENT supersedes for the separately frozen N80 supplement'}
    save(HERE/'ORIGINAL_REQUIREMENTS_RECHECK_20261011.json',result)
    print(result['status'],len(release['files']),len(manifest['files']))

if __name__=='__main__':main()
