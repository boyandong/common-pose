"""Report every signed prespecified comparison and seal delivery artifacts."""
import csv
import hashlib
import json
import tarfile
from collections import defaultdict

import numpy as np

from server_common import HERE,sha,dump,table


def read(name):
    with (HERE/name).open() as f:return list(csv.DictReader(f))


def interval(cohort,rr,key):
    rr=sorted(rr,key=lambda r:r['user']);x=np.array([float(r[key]) for r in rr]);n=len(x)
    if not n:return None,None,None
    seed=int.from_bytes(hashlib.sha256(('20261014|'+cohort+'|'+'|'.join(r['user'] for r in rr)).encode()).digest()[:8],'little')
    ix=np.random.default_rng(seed).integers(n,size=(10000,n));b=np.median(x[ix],axis=1)
    lo,hi=np.quantile(b,[.025,.975]);return float(np.median(x)),float(lo),float(hi)


def main():
    verification=json.loads((HERE/'INDEPENDENT_VERIFICATION.json').read_text());assert verification['status']=='PASS'
    rows=read('FACTORIAL_USER_METRICS.csv')
    lookup={(r['cohort'],r['consumer'],r['user'],r['goal'],int(r['feature_bits']),r['mode'],r['retention']):r for r in rows}
    tags=sorted({r['consumer'] for r in rows});contrasts=[]
    for cohort in ['A20','N80']:
        for tag in tags:
            users=sorted({r['user'] for r in rows if r['cohort']==cohort and r['consumer']==tag})
            for goal in ['U','B']:
                for block,flag in [('pose',1),('Fisher',2),('TTA',4)]:
                    for context in [b for b in range(8) if not b&flag]:
                        with_block=context|flag
                        for retention in ['0.1','0.3','0.5','0.7']:
                            for metric in ['U','B']:
                                paired=[]
                                for user in users:
                                    a=lookup.get((cohort,tag,user,goal,context,'offline_equal_coverage',retention))
                                    b=lookup.get((cohort,tag,user,goal,with_block,'offline_equal_coverage',retention))
                                    if a and b and a[metric] and b[metric]:paired.append({'user':user,'difference':100*(float(a[metric])-float(b[metric]))})
                                md,lo,hi=interval(cohort,paired,'difference')
                                contrasts.append({'cohort':cohort,'consumer':tag,'goal':goal,'added_block':block,'context_bits':context,
                                    'with_block_bits':with_block,'retention':retention,'metric':metric,'paired_users':len(paired),
                                    'median_reduction_pp':md,'CI95_low_pp':lo,'CI95_high_pp':hi,
                                    'status':'UNDEFINED_OR_FIT_UNAVAILABLE' if not paired else 'LOW_SUPPORT' if len(paired)<10 else 'EXPLORATORY_POINTWISE'})
    table(HERE/'FEATURE_CONDITIONAL_CONTRASTS.csv',contrasts)
    for name,group_keys in [('LAG_SENSITIVITY_USERS.csv',['cohort','consumer','method','shift_blocks','nominal_ms']),
                            ('WINDOW_SENSITIVITY_USERS.csv',['cohort','consumer','method','width_blocks','nominal_ms'])]:
        groups=defaultdict(list)
        for r in read(name):groups[tuple(r[k] for k in group_keys)].append(r)
        result=[]
        for key,rr in groups.items():
            row={**dict(zip(group_keys,key)),'users':len(rr),'U_evaluable':sum(bool(r['U']) for r in rr),'B_evaluable':sum(bool(r['B']) for r in rr)}
            for metric in ['U','B','coverage']:
                values=[float(r[metric]) for r in rr if r[metric]];row[metric+'_median']=float(np.median(values)) if values else None
            row['paired_n_median']=float(np.median([int(r['paired_n']) for r in rr]));result.append(row)
        table(HERE/(name.replace('_USERS','_SUMMARY')),result)
    fit=json.loads((HERE/'FACTORIAL_FIT_RECEIPT.json').read_text());gpu=json.loads((HERE/'GPU_COST_RECEIPT.json').read_text())
    lines=['# Clone-server paper evidence results','',
        'All new feature variants and sensitivity analyses are exploratory on previously examined cohorts. Original heads, scorers, thresholds and cached inputs remain unchanged. No target task accuracy, physical equivalence, strict upstream-unseen generalization or causal online service is established.','',
        f"New model fits: {fit['new_models']}; exact original model instances reused: {fit['originals_reused']}; failed fits preserved: {len(fit['failed'])}.",
        f"Independent verification: {verification['checks']} checks; {verification['models_verified']} models; weights, thresholds, saved scores, denominators and full-class support verified.",
        '','## N80 U-training group additions at 30% offline retention','',
        '|Consumer|Added block|Other blocks (bits)|Paired n|Median reduction pp|Pointwise 95% interval|',
        '|---|---|---:|---:|---:|---|']
    for r in contrasts:
        if r['cohort']=='N80' and r['goal']=='U' and r['retention']=='0.3' and r['metric']=='U':
            md=r['median_reduction_pp'];ci='undefined' if md is None else f"[{r['CI95_low_pp']:.3f}, {r['CI95_high_pp']:.3f}]"
            lines.append(f"|{r['consumer']}|{r['added_block']}|{r['context_bits']}|{r['paired_users']}|{md:.3f}"+f"|{ci}|" if md is not None else f"|{r['consumer']}|{r['added_block']}|{r['context_bits']}|0|undefined|undefined|")
    lines+=['','The same predictions and row sets were used within each training goal; the two goals use different fixed learners and weights. Pose and Fisher fields carry related information. The table does not isolate physical causal effects, does not select a best variant, and does not count comparisons as independent confirmations.',
        '',f"GPU cost status: {gpu['status']}. See GPU_OFFLINE_COST.csv for read/view/inference/aggregation timing, peak memory and new-GPU numerical differences; these are offline whole-record times.",
        '', 'Lag and window tables preserve every prespecified setting. There is no selected lag or window. Lag results use a common paired-reference set with original acceptance; aggregation changes units and support. Physical synchronization and absolute-zero calibration remain unverified.',
        '', 'Actual checkpoint training membership needs weight-bound provenance; target semantic accuracy needs independent labels; independent human readers and physical anchors are external requirements. More server compute alone cannot complete these items.']
    (HERE/'REPORT.md').write_text('\n'.join(lines)+'\n')
    small=[]
    for p in HERE.iterdir():
        if p.is_file() and p.suffix in ['.csv','.json','.md','.py'] and p.name not in ['PIPELINE_STATE.json','PROGRESS.json']:small.append(p)
    small+=list((HERE/'models').glob('*.joblib'))
    manifest={str(p.relative_to(HERE)):sha(p) for p in sorted(small)};dump(HERE/'DELIVERY_MANIFEST.json',manifest)
    package=HERE/'verified_paper_closeout_results.tar.gz'
    with tarfile.open(package,'w:gz') as t:
        for p in small:t.add(p,arcname=str(p.relative_to(HERE)),recursive=False)
        t.add(HERE/'DELIVERY_MANIFEST.json',arcname='DELIVERY_MANIFEST.json',recursive=False)
    dump(HERE/'FINAL_DELIVERY.json',{'status':'REMOTE_VERIFIED_LOCAL_DELIVERY_PENDING','package':str(package),
        'package_sha256':sha(package),'bytes':package.stat().st_size,'files':len(manifest),'new_models':fit['new_models'],
        'independent_checks':verification['checks'],'large_training_and_decision_arrays_retained_remote':True})
    print('SEALED_SERVER_DELIVERY_READY',package.stat().st_size,flush=True)


if __name__=='__main__':main()
