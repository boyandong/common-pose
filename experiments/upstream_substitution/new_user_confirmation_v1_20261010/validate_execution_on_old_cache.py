"""Pre-inference numerical controls on old FINAL only, never the N80 data."""
import csv
import math
from pathlib import Path
import joblib
import numpy as np
from runtime_common import LANE,BASE,sha,read,save,load_module
from analyze_new_users import stats
from verify_new_results import measure,order,sign_exact,same

def main():
    source=BASE/'paper_supplement_v1_20261009'
    cohort=read(LANE/'ENROLLMENT_MANIFEST.json')
    old_users=[p.stem for p in sorted((source/'features/FINAL').glob('*.npz'))]
    assert len(old_users)==20 and not set(old_users).intersection(cohort['enrolled_users'])
    old=load_module('old_supplement',source/'analyze_comparisons.py')
    with (source/'comparative_analysis/RISK_COVERAGE_ROWS.csv').open(encoding='utf-8-sig',newline='') as f:
        reference={(r['contract'],r['user'],r['method']):r for r in csv.DictReader(f) if r['split']=='FINAL' and float(r['nominal_coverage'])==.3}
    sets=read(source/'comparative_analysis/SUMMARY.json')['summary'];checks=0
    for c,folder in [('U','gate4e_customer_flip_gate_v1'),('B','gate4f_class_balanced_flip_gate_v1')]:
        full=joblib.load(BASE/folder/'artifacts/FINAL_GATE_MODEL.joblib');full=full if c=='U' else full['model']
        models={'full':full,**{m:joblib.load(source/'comparative_analysis'/f'{c}_{m}_DEV_ONLY.joblib') for m in ['class_model','no_tta']}}
        rates=np.asarray(read(source/'comparative_analysis'/f'{c}_SUPPLEMENT_INSTANCE.json')['class_empirical_rates'])
        for user in old_users:
            with np.load(source/'features/FINAL'/(user+'.npz')) as z:v={k:z[k] for k in z.files}
            common=sets[c+'_FINAL']['common_reference_class_sets'][user]
            scores=old.scores(v,models,rates)
            for method,score in scores.items():
                actual=order(score,user,20261009)
                assert np.array_equal(actual,old.order(score,old.tiekeys('FINAL',user,len(score))))
                got,_,_=measure(v['flip'],v['ygt'],actual[:math.ceil(.3*len(score))],common)
                expected=reference[c,user,method]
                for metric,value in got.items():same(value,float(expected[metric]) if expected[metric] else None);checks+=1
    for n in range(1,13):
        for positive in range(n+1):
            values=[1.]*positive+[-1.]*(n-positive)
            s=stats(values,True);same(s['sign_p_two_sided'],sign_exact(positive,n-positive))
    assert stats([0.]*80,True)['formal_decision']=='NOT_CONFIRMED'
    assert stats([1.]*79+[None],True)['formal_decision']=='EVIDENCE_INSUFFICIENT'
    assert stats([-1.]*80,True)['formal_decision']=='NOT_CONFIRMED'
    assert stats([1.]*6,True)['formal_decision']=='NOT_CONFIRMED'
    assert stats([1.]*7,True)['formal_decision']=='POSITIVE'
    save(LANE/'OLD_CACHE_EXECUTION_VALIDATION.json',{'status':'PASS','old_FINAL_users_only':20,'new_user_features_read':False,
        'canonical_seven_method_risk_checks':checks,'exhaustive_small_n_sign_cases':sum(n+1 for n in range(1,13)),
        'zero_missing_negative_and_alpha_boundaries_checked':True,'verifier_sha256':sha(Path(__file__)),
        'analysis_code_sha256':sha(LANE/'analyze_new_users.py'),'independent_code_sha256':sha(LANE/'verify_new_results.py')})
    print('OLD_CACHE_EXECUTION_VALIDATION_PASS',checks,flush=True)

if __name__=='__main__':main()
