"""Complete reporting and explicit whole-goal audit only after terminal execution."""
import argparse
import ast
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from runtime_common import BASE,LANE,ROOT,read,save,sha,frozen

HERE=Path(__file__).resolve().parent
DEST=Path('D:/CommonPose_confirmation_N80_20261010')
CONT=HERE/'continuation_execution_20261011'
sys.path.insert(0,str(CONT))
from execution_gate import verify_execution_gate

def copy_exact(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():assert sha(target)==sha(source),str(target)
    else:shutil.copyfile(source,target)
    assert sha(target)==sha(source)

def backup_local_execution_closure():
    # Scientific inputs are covered by the integrated remote exporter. Also
    # preserve the local controller and its transitive lane-module imports.
    roots=list(HERE.glob('*.py'))+list(CONT.glob('*.py'))+[LANE/'build_confirmation_report.py',LANE/'backup_runtime_to_D.py']
    pending=list(roots);seen=set();records={}
    while pending:
        source=pending.pop().resolve()
        if source in seen:continue
        seen.add(source)
        tree=ast.parse(source.read_text(encoding='utf-8'))
        relative=source.relative_to(ROOT).as_posix()
        target=DEST/'successor_execution_20261011/source'/relative
        copy_exact(source,target)
        records[relative]={'sha256':sha(source),'bytes':source.stat().st_size}
        for node in ast.walk(tree):
            names=[node.module] if isinstance(node,ast.ImportFrom) and node.module else [a.name for a in node.names] if isinstance(node,ast.Import) else []
            for name in names:
                for folder in [CONT,HERE,LANE]:
                    module=folder/(name.split('.')[0]+'.py')
                    if module.is_file():pending.append(module)
    for name,key in [('pipeline_supervisor.py','parent_controller_sha256'),('relay_completed_sources_v3_20261010.py','parent_status_writer_sha256')]:
        assert sha(LANE/name)==read(HERE/'CODE_SEAL.json')[key]
        assert (LANE/name).relative_to(ROOT).as_posix() in records
    evidence={}
    for pattern in ['EXECUTION_OBSERVATION_*.json','USER_RUNTIME_PROGRESS_*.json','SESSION_HANDOVER_*.md']:
        for source in HERE.glob(pattern):
            copy_exact(source,DEST/'successor_execution_20261011/evidence'/source.name)
            evidence[source.name]=sha(source)
            sidecar=source.with_name(source.name+'.sha256')
            if sidecar.exists():copy_exact(sidecar,DEST/'successor_execution_20261011/evidence'/sidecar.name)
    for name in ['integrated_controller.stdout.log','integrated_controller.stderr.log','successor_dispatch.stdout.log','successor_dispatch.stderr.log','backup.log']:
        source=HERE/name
        assert source.is_file(),name
        copy_exact(source,DEST/'successor_execution_20261011/closed_local_logs'/name)
        evidence[name]=sha(source)
    for source in CONT.iterdir():
        if not source.is_file() or source.suffix=='.lock' or source.name=='PROGRESS.json':continue
        target=DEST/'successor_execution_20261011/continuation'/source.name
        copy_exact(source,target)
        evidence['continuation/'+source.name]=sha(source)
    for name in ['INCIDENT_CONTROLLER_LOST_20261011.json','INCIDENT_FORENSIC_D_BACKUP_VERIFICATION_20261011.json','INCIDENT_GOAL_BLOCKED_AUDIT_20261011.json']:
        copy_exact(HERE/name,DEST/'successor_execution_20261011/evidence'/name)
        evidence[name]=sha(HERE/name)
    receipt=HERE/'LOCAL_EXECUTION_SOURCE_BACKUP_VERIFICATION_20261011.json'
    result={'status':'PASS','source_files':records,'closed_local_logs_and_observation_evidence':evidence,'scope':'local execution Python modules and their transitive lane-module imports plus closed local execution logs/observations; scientific dependencies/models/caches remain in the original integrated backup','credentials_or_original_user_records_copied':False,'all_local_sha256_recomputed':True}
    if receipt.exists():assert read(receipt)==result
    else:save(receipt,result)
    copy_exact(receipt,DEST/'successor_execution_20261011'/receipt.name)
    return receipt

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check-ready',action='store_true');parser.add_argument('--prepare-reports',action='store_true');args=parser.parse_args()
    prerequisites=[CONT/'CONTROLLER_TERMINAL.json',CONT/'PROCESS_EXIT_OBSERVATION.json',CONT/'LAUNCH.json',HERE/'INDEPENDENT_VERIFICATION.json',HERE/'EXECUTION_COMPLETE.json',HERE/'OFFHOST_BACKUP_VERIFICATION.json',HERE/'EXPORT_EXECUTION_BACKUP_VERIFICATION.json',LANE/'PIPELINE_EXECUTION_COMPLETE.json',LANE/'INDEPENDENT_RESULT_VERIFICATION.json',LANE/'OFFHOST_BACKUP_VERIFICATION.json']
    missing=[str(p.relative_to(LANE)) for p in prerequisites if not p.exists()]
    if args.check_ready:
        gate=verify_execution_gate(HERE,CONT) if not missing else None
        print(json.dumps({'ready_receipts_present':not missing,'execution_gate':gate,'missing':missing,'effect_values_read':False}));return
    assert not missing,missing
    execution_gate=verify_execution_gate(HERE,CONT)
    assert read(HERE/'EXECUTION_COMPLETE.json')['status']=='PRIMARY_AND_SCORE_ONLY_VERIFIED_AND_FULLY_BACKED_UP'
    for p in [HERE/'OFFHOST_BACKUP_VERIFICATION.json',HERE/'EXPORT_EXECUTION_BACKUP_VERIFICATION.json',HERE/'INDEPENDENT_VERIFICATION.json',LANE/'INDEPENDENT_RESULT_VERIFICATION.json',LANE/'OFFHOST_BACKUP_VERIFICATION.json']:
        assert read(p)['status']=='PASS',p
    primary_verification=read(LANE/'INDEPENDENT_RESULT_VERIFICATION.json')
    secondary_verification=read(HERE/'INDEPENDENT_VERIFICATION.json')
    for key,count in {'users':80,'exact_rescored_vectors':1120,'seed_rows':22400,'curve_rows':7840,'class_rows':62720,'effect_rows':19200,'primary_rows':160,'bootstrap_summaries':240,'raw_base_tta_hash_and_label_lineage_users':80}.items():
        assert primary_verification[key]==count,(key,primary_verification[key],count)
    assert primary_verification['all_frozen_support_sets_rederived']
    assert not primary_verification['producer_score_tie_metric_stats_functions_imported']
    assert primary_verification['verifier_sha256']==sha(LANE/'verify_new_results.py')
    for key,count in {'users':80,'contracts':2,'model_prediction_vectors_checked':320,'risk_rows':2240,'class_rows':17920,'seed_risk_rows':6400,'paired_seed_effects':3200,'canonical_user_effects':160,'support_rows':2560,'deployment_rows':320,'within_class_rows':320}.items():
        assert secondary_verification[key]==count,(key,secondary_verification[key],count)
    assert secondary_verification['verifier_sha256']==sha(HERE/'verify_score_only.py')
    assert secondary_verification['original_primary_verification_sha256']==sha(LANE/'INDEPENDENT_RESULT_VERIFICATION.json')
    assert secondary_verification['original_common_sets_sha256']==sha(LANE/'COMMON_CLASS_SETS.json')
    assert not secondary_verification['original_sets_changed'] and not secondary_verification['new_confirmatory_primary']
    frozen(dependencies=False)
    seal=read(HERE/'CODE_SEAL.json')
    for n,h in seal['files'].items():assert sha(HERE/n)==h,n
    original=read(CONT/'ORIGINAL_REQUIREMENTS_RECHECK.json')
    assert original['release_file_and_git_blob_hashes_checked']==125 and original['old_20seed_files_rehashed']==27
    assert original['canonical_max_abs_difference']==0 and original['N80_selection_and_members_rederived']
    backup=read(LANE/'OFFHOST_BACKUP_VERIFICATION.json')
    assert backup['source_files']==2768 and backup['source_bytes']==50213536592
    assert backup['manifest_sha256']==sha(LANE/'OFFHOST_BACKUP_MANIFEST.json')
    records={r['local_relative']:r for r in read(LANE/'OFFHOST_BACKUP_MANIFEST.json')['files']}
    # Rehash every reported result; large cache/source bytes were independently rehashed by the backup verifier.
    rehashed=0
    for relative,row in records.items():
        if not relative.startswith('results/'):continue
        path=DEST/relative
        assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256'],relative
        rehashed+=1
    stages={}
    for prefix,names in [('', ['qualification','reconstruction','support','analysis','verification']),('score_only_supplement_20261011/',['support','analysis','verification','backup_export'])]:
        for stage in names:
            p=DEST/'results'/prefix/'jobs'/stage
            launch=read(p/'LAUNCH.json');terminal=read(p/'TERMINAL.json')
            assert terminal['exit_code']==0 and terminal['output_log_sha256']==sha(p/'output.log')
            stages[prefix+stage]={'start':launch['started_epoch'],'end':terminal['finished_epoch']}
    assert stages['qualification']['end']<=stages['reconstruction']['start']
    assert stages['reconstruction']['end']<=stages['support']['start']
    assert stages['support']['end']<=stages['score_only_supplement_20261011/support']['start']
    support_end=stages['score_only_supplement_20261011/support']['end']
    assert support_end<=stages['analysis']['start'] and support_end<=stages['score_only_supplement_20261011/analysis']['start']
    assert stages['verification']['end']<=stages['score_only_supplement_20261011/backup_export']['start']
    assert stages['score_only_supplement_20261011/verification']['end']<=stages['score_only_supplement_20261011/backup_export']['start']
    for folder,script in [(LANE/'manuscript_confirmation',LANE/'build_confirmation_report.py'),(HERE/'manuscript_score_only',HERE/'build_score_only_report.py')]:
        if not folder.exists():subprocess.run([sys.executable,str(script)],cwd=ROOT,check=True)
        assert (folder/'BUILD_MANIFEST.json').exists(),str(folder)
    report=LANE/'manuscript_confirmation';r=read(report/'BUILD_MANIFEST.json')
    assert r['status']=='VERIFIED_PROSPECTIVE_REPORT_BUILT' and sha(report/'MANUSCRIPT_CONFIRMATION.md')==r['report_sha256']
    report_files={}
    for p in report.iterdir():
        if p.is_file():copy_exact(p,DEST/'results/manuscript_confirmation'/p.name);report_files[p.name]=sha(p)
    receipt=HERE/'PRIMARY_REPORT_BACKUP_VERIFICATION_20261011.json'
    if not receipt.exists():save(receipt,{'status':'PASS','files':report_files,'all_local_sha256_recomputed':True})
    sr=read(HERE/'manuscript_score_only/BUILD_MANIFEST.json')
    assert sr['status']=='VERIFIED_EIGHT_METHOD_REPORTS_BUILT' and sr['original_primary_report_sha256']==r['report_sha256']
    for n,h in sr['reports'].items():
        assert sha(HERE/'manuscript_score_only'/n)==h and sha(DEST/'results/score_only_supplement_20261011/manuscript_score_only'/n)==h
    assert read(HERE/'REPORT_BACKUP_VERIFICATION.json')['status']=='PASS'
    figures=HERE/'confirmation_figures_20261011'
    if not figures.exists():subprocess.run([sys.executable,str(HERE/'build_continuation_confirmation_figures_20261011.py')],cwd=ROOT,check=True)
    figure_manifest=read(figures/'BUILD_MANIFEST.json')
    assert figure_manifest['status']=='VERIFIED_FROZEN_PRESENTATION_FIGURES_BUILT' and figure_manifest['summary_rows']==112
    for n,h in figure_manifest['files'].items():
        assert sha(figures/n)==h and sha(DEST/'results/score_only_supplement_20261011/confirmation_figures_20261011'/n)==h,n
    if args.prepare_reports:
        print('VERIFIED_REPORTS_AND_FIGURES_BACKED_UP_VISUAL_REVIEW_PENDING');return
    visual=read(HERE/'FIGURE_VISUAL_REVIEW_20261011.json')
    assert visual['status']=='PASS' and visual['figure_build_manifest_sha256']==sha(figures/'BUILD_MANIFEST.json')
    assert visual['png_files_inspected']=={n:h for n,h in figure_manifest['files'].items() if n.endswith('.png')}
    backup_local_execution_closure()
    scope=read(HERE/'GOAL_SCOPE_AMENDMENT.json')
    required=scope['required_receipts']
    for n in required:
        if not (HERE/n).exists():
            archived=DEST/'results/score_only_supplement_20261011'/n
            entry=records['results/score_only_supplement_20261011/'+n]
            assert sha(archived)==entry['sha256'],n
            copy_exact(archived,HERE/n)
        assert (HERE/n).exists(),n
    requirements=[
        ('old manuscript and fixed reproducible Git','ORIGINAL_REQUIREMENTS_RECHECK_20261011.json'),
        ('restored cache and private local archive backups','ORIGINAL_REQUIREMENTS_RECHECK_20261011.json'),
        ('canonical diagnosis and prescribed20-seed independent verification','ORIGINAL_REQUIREMENTS_RECHECK_20261011.json'),
        ('scoped history, protected cohort and upstream exposure audit','ORIGINAL_REQUIREMENTS_RECHECK_20261011.json'),
        ('frozen N80 original seven-method experiment','../INDEPENDENT_RESULT_VERIFICATION.json'),
        ('prospective eighth-method score-only supplement','INDEPENDENT_VERIFICATION.json'),
        ('full off-host source/cache/dependency/result backup','../OFFHOST_BACKUP_VERIFICATION.json'),
        ('supplement models, scores and result backup','OFFHOST_BACKUP_VERIFICATION.json'),
        ('closed export logs and terminal backup','EXPORT_EXECUTION_BACKUP_VERIFICATION.json'),
        ('local controller/import closure and closed execution evidence backup','LOCAL_EXECUTION_SOURCE_BACKUP_VERIFICATION_20261011.json'),
        ('original prospective report and backup','PRIMARY_REPORT_BACKUP_VERIFICATION_20261011.json'),
        ('supplement and integrated report and backup','REPORT_BACKUP_VERIFICATION.json')]
    requirements.append(('eight-method/primary paired figures and visual review','FIGURE_VISUAL_REVIEW_20261011.json'))
    proof=[{'requirement':name,'status':'VERIFIED','evidence':n,'sha256':sha(HERE/n)} for name,n in requirements]
    preparation={}
    for n in ['successor_execution_preflight_20261011.py','launch_integrated_successor_20261011.py','recheck_original_requirements_20261011.py','finalize_continuation_verified_goal_20261011.py','SUCCESSOR_EXECUTION_PREFLIGHT_20261011.json','ORIGINAL_REQUIREMENTS_RECHECK_20261011.json','INTEGRATED_CONTROLLER_LAUNCH_20261011.json','EXECUTION_COMPLETE.json','OFFHOST_BACKUP_VERIFICATION.json','EXPORT_EXECUTION_BACKUP_VERIFICATION.json','REPORT_BACKUP_VERIFICATION.json','PRIMARY_REPORT_BACKUP_VERIFICATION_20261011.json','FIGURE_VISUAL_REVIEW_20261011.json']:
        p=HERE/n;copy_exact(p,DEST/'successor_execution_20261011'/n);preparation[n]=sha(p)
    result={'execution_gate':execution_gate,'fresh_original_requirements_recheck_sha256':sha(CONT/'ORIGINAL_REQUIREMENTS_RECHECK.json'),'original_controller_exit':'UNKNOWN','status':'FULL_ORIGINAL_GOAL_PLUS_SCORE_ONLY_COMPLETION_AUDIT_PASS','observed_local_time':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'requirements':proof,'scope_amendment_sha256':sha(HERE/'GOAL_SCOPE_AMENDMENT.json'),'required_supplement_receipts_checked':required,'original_protocol_sha256':sha(LANE/'SCIENTIFIC_SPEC.md'),'cohort_sha256':sha(LANE/'ENROLLMENT_MANIFEST.json'),'all_stages_exit_zero':stages,'qualification_and_both_support_stages_precede_effect_analysis':True,'independent_verifier_coverage_count_contracts_checked':True,'independent_verification_scope':'independent frozen model/cache rescoring, ties, support sets, all risk/effect/count/statistics rows; does not independently rerun neural inference','archived_result_files_freshly_rehashed':rehashed,'successor_execution_evidence_D_backup':preparation,'upstream_membership':'UNRESOLVED','history_scope':original['history_scope'],'flip_definition':'one frozen consumer output preservation, not independently labelled gesture accuracy','joint_decision':read(LANE/'PRIMARY_RESULT.json')['joint_decision'],'score_only_role':'prospective descriptive secondary; original primary/common sets unchanged','private_sources_models_and_caches_retained':True}
    save(HERE/'FULL_GOAL_COMPLETION_AUDIT_20261011.json',result)
    copy_exact(HERE/'FULL_GOAL_COMPLETION_AUDIT_20261011.json',DEST/'successor_execution_20261011/FULL_GOAL_COMPLETION_AUDIT_20261011.json')
    print(result['status'])

if __name__=='__main__':main()
