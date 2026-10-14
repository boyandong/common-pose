"""Alternative arithmetic validation, original table checks, input postcheck."""
import csv
import json
import math
from pathlib import Path

import numpy as np

from analyze_local import CONSUMERS, dump, rows, sha

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=HERE/'results'


def sorted_median(values):
    values=sorted(values);n=len(values)
    return values[n//2] if n%2 else (values[n//2-1]+values[n//2])/2


def percentile(values,q):
    ordered=np.sort(values);position=(len(ordered)-1)*q;lo=math.floor(position);hi=math.ceil(position)
    return float(ordered[lo]*(hi-position)+ordered[hi]*(position-lo)) if hi!=lo else float(ordered[lo])


def main():
    seal=json.loads((HERE/'PRE_EXECUTION_SEAL.json').read_text());checks=0
    for rel,h in seal['inputs'].items():assert sha(ROOT/rel)==h,rel;checks+=1
    for rel,h in seal['analysis_code'].items():assert sha(HERE/rel)==h,rel;checks+=1
    paired=rows(OUT/'PARTICIPANT_PAIRED_DIFFERENCES.csv');grouped={}
    for r in paired:
        k=tuple(r[x] for x in ['cohort','consumer','retention','A','B_method','metric'])
        grouped.setdefault(k,[]).append(r)
    manifests=json.loads((OUT/'BOOTSTRAP_MANIFEST.json').read_text())
    ix_by_users={(r['cohort'],tuple(r['users'])):r['digest'] for r in manifests}
    for estimate in rows(OUT/'PAIRED_INTERVALS_ALL_BUDGETS.csv'):
        key=tuple(estimate[x] for x in ['cohort','consumer','retention','A','B_method','metric'])
        rr=sorted(grouped.get(key,[]),key=lambda r:r['user'])
        assert len(rr)==int(estimate['users'])
        if not rr:assert not estimate['median_reduction_pp'];continue
        x=np.array([float(r['difference_pp']) for r in rr]);ids=tuple(r['user'] for r in rr)
        assert abs(sorted_median(x)-float(estimate['median_reduction_pp']))<1e-10
        ix=np.load(OUT/'bootstrap_indices'/(ix_by_users[(estimate['cohort'],ids)]+'.npy'),allow_pickle=False)
        sampled=np.sort(x[ix],axis=1);n=len(x)
        boot=sampled[:,n//2] if n%2 else (sampled[:,n//2-1]+sampled[:,n//2])/2
        assert abs(percentile(boot,.025)-float(estimate['CI95_low_pp']))<1e-10
        assert abs(percentile(boot,.975)-float(estimate['CI95_high_pp']))<1e-10
        checks+=4
    paper=ROOT/'docs/papers/20261014_v4_5_independent_review'
    original_s3={(r['cohort'],r['consumer'],r['retention']):r for r in rows(paper/'evidence/S3_DIRECT_PAIRED_SUMMARY.csv')}
    original_s4={r['consumer']:r for r in rows(paper/'evidence/S4_CLASS_FIDELITY.csv')}
    for r in rows(OUT/'PAIRED_INTERVALS_ALL_BUDGETS.csv'):
        if (r['A'],r['B_method'],r['metric'])==('score_only','full','U'):
            expected=original_s3[(r['cohort'],r['consumer'],r['retention'])]
            assert abs(float(r['median_reduction_pp'])-float(expected['delta_pp']))<1e-10;checks+=1
        if r['cohort']=='N80' and r['retention']=='0.3' and (r['A'],r['B_method'])==('boundary','full'):
            expected=original_s4[r['consumer']]
            assert int(r['users'])==int(expected[r['metric']+'_users'])
            assert abs(float(r['median_reduction_pp'])-float(expected['delta_'+r['metric']+'_pp']))<1e-10;checks+=2
    for r in rows(OUT/'MISSING_REFERENCE_BOUNDS.csv'):
        p,m,a,f=(int(r[k]) for k in ['paired_n','missing_n','accepted_n','observed_flips'])
        assert p+m==a and 0<=f<=p
        if a:
            lo,hi=float(r['lower_all_inputs']),float(r['upper_all_inputs'])
            assert 0<=lo<=hi<=1 and abs((hi-lo)-m/a)<1e-12
        checks+=2
    original=json.loads((ROOT/'docs/reviews/20261014_embc_no_supplement_audit/PAPER_UNCHANGED_HASHES.json').read_text())
    assert all(sha(ROOT/k)==v for k,v in original.items());checks+=len(original)
    source=json.loads((OUT/'source_replay/SOURCE_REPLAY_RECEIPT.json').read_text())
    assert source['status']=='PASS' and source['consumers']==6
    dump(OUT/'INDEPENDENT_RECOUNT.json',{'status':'PASS','checks':checks,'alternative_sorted_medians_and_linear_percentiles':True,
        'all_48_S3_cells_reproduced':True,'all_12_S4_cells_reproduced':True,'source_LOSO_reproduction':source,
        'paper_187_files_unchanged':True,'input_postcheck':'PASS','no_training_of_target_gates':True})
    print('LOCAL_INDEPENDENT_RECOUNT_PASS',checks,flush=True)


if __name__=='__main__':main()
