"""Report all verified eight-method evidence, keeping original outputs intact."""
import csv
from pathlib import Path
import re
import shutil
import statistics
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from runtime_common import LANE,read,save,sha

HERE=Path(__file__).resolve().parent
ARCHIVE=Path('D:/CommonPose_confirmation_N80_20261010/results/score_only_supplement_20261011')

def num(v):return None if v in ['',None] else float(v)
def show(v):return 'missing' if v is None else f'{100*v:.3f}'
def median(v):
    a=[x for x in v if x is not None];return statistics.median(a) if a else None
def table(headers,rr):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rr])

def main():
    assert read(HERE/'EXECUTION_COMPLETE.json')['status']=='PRIMARY_AND_SCORE_ONLY_VERIFIED_AND_FULLY_BACKED_UP'
    assert read(HERE/'OFFHOST_BACKUP_VERIFICATION.json')['status']=='PASS'
    verification=read(ARCHIVE/'INDEPENDENT_VERIFICATION.json');assert verification['status']=='PASS'
    result=read(ARCHIVE/'SECONDARY_RESULT.json');assert sha(ARCHIVE/'SECONDARY_RESULT.json')==verification['secondary_result_sha256']
    manifest=read(ARCHIVE/'RESULT_MANIFEST.json')
    for n,h in manifest['files'].items():assert sha(ARCHIVE/n)==h,n
    def rows(n):
        with (ARCHIVE/n).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
    users=rows('SCORE_ONLY_USER_EFFECTS.csv');risk=rows('RISK_COVERAGE_ROWS.csv');deployment=rows('DEPLOYMENT_ROWS.csv');assert len(users)==160
    parts=['# N80 prospective score-only secondary control',
       'The human added this control before any N80 inference/effect reading. It reuses two exact old DEV-only matched consumer-score models, with no N80 fitting or calibration. Old FINAL control results informed this design and are not independent confirmation. The original seven-method support sets, two primary comparisons and familywise decision are preserved.',
       'Score-only uses19 consumer features including predicted class identity, scores, margin, entropy and boundary geometry; excludes pose/Fisher/TTA features. U uses matched hist-GBDT, B matched scaled logistic. Linux admission checked both models on all19 old DEV users and266 accepted sets. The secondary comparison is score_only minus full; positive favors full. All statistics below are descriptive, with no additional confirmatory primary or adjusted success claim.',
       'Flip is frozen-consumer output preservation, not independently labelled gesture accuracy. Checkpoint-specific upstream membership remains unresolved.',
       '## Canonical30% secondary results']
    summary=[]
    for c in ['U','B']:
        s=result['canonical'][c];rr=[r for r in users if r['contract']==c];ci=s['descriptive_ci95']
        summary.append([c,s['enrolled'],s['complete_pairs'],s['missing_pairs'],f"{s['positive']}/{s['zero']}/{s['negative']}",s['n_nonzero'],
           show(median([num(r['score_only_risk']) for r in rr])),show(median([num(r['full_risk']) for r in rr])),show(s['median']),
           'missing' if ci is None else f'[{show(ci[0])}, {show(ci[1])}]',s['descriptive_sign_p'],s['conditional_subset_sign_p']])
    parts.append(table(['Endpoint','Enrolled','Complete','Missing','+/0/-','Nonzero','Score-only median risk %','Full median risk %','Effect pp','Descriptive95%CI pp','Descriptive sign p','Conditional subset p'],summary))
    parts.extend(['Missing fixed-set risk is not zero. Score-only classes below30 or absent are reported against the original common sets; sets are never changed to rescue the added control.', '## Every enrolled user'])
    index={(r['contract'],r['user']):r for r in users};rr=[]
    for user in sorted({r['user'] for r in users}):
        row=[user]
        for c in ['U','B']:row.extend(show(num(index[c,user][k])) for k in ['score_only_risk','full_risk','effect'])
        rr.append(row)
    assert len(rr)==80;parts.append(table(['User','U score-only %','U full %','U effect pp','B score-only %','B full %','B effect pp'],rr))
    parts.append('## Seven coverages and frozen-threshold deployment');rr=[]
    for c in ['U','B']:
        metric='ordinary_risk' if c=='U' else 'fixed_common_risk'
        for method in ['score_only','full']:
            for coverage in [.3,.5,.6,.7,.8,.9,1.]:
                x=[r for r in risk if r['contract']==c and r['method']==method and float(r['nominal_coverage'])==coverage];assert len(x)==80
                vals=[num(r[metric]) for r in x];rr.append([c,method,coverage,sum(v is not None for v in vals),show(median(vals))])
    parts.append(table(['Endpoint','Method','Nominal coverage','Defined /80','Risk median %'],rr));rr=[]
    for c in ['U','B']:
        metric='ordinary_risk' if c=='U' else 'fixed_common_risk'
        for method in ['score_only','full']:
            x=[r for r in deployment if r['contract']==c and r['method']==method];assert len(x)==80
            rr.append([c,method,show(median([float(r['coverage']) for r in x])),show(median([num(r[metric]) for r in x])),sum(num(r[metric]) is None for r in x)])
    parts.append(table(['Endpoint','Method','Fixed threshold coverage median %','Risk median %','Missing'],rr))
    parts.append('## All20 conditional tie seeds');rr=[]
    for c in ['U','B']:
        for seed in range(20261009,20261029):
            s=result['conditional_seeds'][f'{c}|{seed}'];rr.append([c,seed,s['complete_pairs'],s['missing_pairs'],show(s['median']),f"{s['positive']}/{s['zero']}/{s['negative']}"])
    parts.append(table(['Endpoint','Seed','Complete','Missing','Effect median pp','+/0/-'],rr))
    support=read(ARCHIVE/'SUPPORT_SEAL.json');rr=[]
    for c in ['U','B']:
        for user,d in sorted(support['diagnostics'][c].items()):rr.append([c,user,'|'.join(map(str,d['original_common_classes'])),'|'.join(map(str,d['score_only_sparse_common_classes'])),'|'.join(map(str,d['score_only_missing_common_classes']))])
    parts.extend(['## Frozen-set support omissions',table(['Endpoint','User','Original common classes','Score-only <30','Score-only absent'],rr),
       'All class risks/supports, baseline-class missing-risk lower/upper bounds, within-predicted-class results and20-seed rows accompany this report. Two-method supported intersections are diagnostics only. No users, methods, thresholds or seeds were selected by effects; no independent semantic-accuracy, pose/TTA causal or upstream-unseen claim is made.'])
    dest=HERE/'manuscript_score_only';dest.mkdir(exist_ok=False);report=dest/'SCORE_ONLY_N80_REPORT.md';report.write_text('\n\n'.join(parts)+'\n',encoding='utf-8')
    primary=LANE/'manuscript_confirmation/MANUSCRIPT_CONFIRMATION.md';assert primary.exists()
    original=primary.read_text(encoding='utf-8')
    amended=re.sub(r'Score-only remains deferred[^.]*\.', 'The original seven-method protocol excluded score-only; the separately sealed prospective supplement below reports the subsequently authorized control.',original,count=1)
    integrated=dest/'MANUSCRIPT_CONFIRMATION_WITH_SCORE_ONLY.md';integrated.write_text(amended+'\n\n'+'\n\n'.join(parts)+'\n',encoding='utf-8')
    save(dest/'BUILD_MANIFEST.json',{'status':'VERIFIED_EIGHT_METHOD_REPORTS_BUILT','original_primary_report_sha256':sha(primary),'original_primary_unchanged':True,
         'secondary_result_sha256':sha(ARCHIVE/'SECONDARY_RESULT.json'),'secondary_verification_sha256':sha(ARCHIVE/'INDEPENDENT_VERIFICATION.json'),
         'reports':{p.name:sha(p) for p in [report,integrated]},'all80_user_rows_and20_seeds_reported':True,'original_primaries_and_common_sets_preserved':True,'source_code_sha256':sha(Path(__file__))})
    backup=ARCHIVE/'manuscript_score_only';backup.mkdir(exist_ok=False)
    for path in dest.iterdir():
        if path.is_file():shutil.copyfile(path,backup/path.name);assert sha(backup/path.name)==sha(path)
    save(HERE/'REPORT_BACKUP_VERIFICATION.json',{'status':'PASS','local_D_report_files':{p.name:sha(p) for p in backup.iterdir() if p.is_file()},'all_local_SHA256_recomputed':True})
    print('SCORE_ONLY_AND_INTEGRATED_REPORTS_BACKED_UP',flush=True)

if __name__=='__main__':main()
