"""Conditional strong-baseline planning; no enrollment or new-user outcomes.

Sign-test power is conditional on a specified number of nonzero, defined paired
user effects. Empirical magnitude precision uses already examined FINAL only as
an illustrative pilot distribution, not as an independent confirmation.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import binom,binomtest

HERE=Path(__file__).resolve().parent

def main():
    data=HERE/'results/USER_EFFECTS_30.csv'
    e=pd.read_csv(data)
    rows=[];precision=[]
    for n in [20,30,50,70,80,90,100,120,134]:
        critical=min(k for k in range(n//2+1,n+1) if binomtest(k,n,.5).pvalue<=.025)
        for p in [.6,.65,.7,.75,.8]:
            power=float(binom.sf(critical-1,n,p))
            rows.append({'nonzero_defined_users':n,'positive_required':critical,
                         'true_positive_probability':p,'endpoint_positive_direction_power':power,
                         'both_endpoint_success_union_bound_if_both_have_this_power':max(0.,2*power-1),
                         'both_endpoint_success_if_independent':power**2})
        for c,m,metric in [('U','boundary_distance','ordinary_risk'),('B','class_model','fixed_common_risk')]:
            a=e[(e['split']=='FINAL')&(e['contract']==c)&(e['comparison']=='full_vs_'+m)&(e['metric']==metric)]['effect'].dropna().to_numpy()
            assert len(a)==20
            rng=np.random.default_rng(20261010)
            medians=np.median(a[rng.integers(0,len(a),size=(20000,n))],axis=1)
            lo,hi=np.quantile(medians,[.025,.975])
            precision.append({'users':n,'contract':c,'comparator':m,'pilot_users':len(a),
                              'pilot_median':float(np.median(a)),'illustrative_median_sampling_q025':float(lo),
                              'illustrative_median_sampling_q975':float(hi),'illustrative_width_pp':float(100*(hi-lo)),
                              'pilot_positive_users':int((a>0).sum()),
                              'pilot_positive_probability_exact95':list(binomtest(int((a>0).sum()),len(a)).proportion_ci())})
    p=HERE/'prospective_inventory'
    pd.DataFrame(rows).to_csv(p/'CONDITIONAL_SIGN_POWER.csv',index=False)
    pd.DataFrame(precision).to_csv(p/'ILLUSTRATIVE_MAGNITUDE_PRECISION.csv',index=False)
    inv=pd.read_csv(p/'IDENTITY_REGISTRY.csv')
    sizes=inv[inv['status']=='METADATA_ELIGIBLE_PENDING_FULL_ACCESS_AUDIT']['preflight_bytes'].sort_values()
    result={'status':'PLANNING_ONLY_NO_ENROLLMENT_DECISION','alpha_per_endpoint_two_sided':.025,
            'family':'U vs boundary distance; B vs matched class model',
            'nominal_N80_p70_endpoint_power':next(r['endpoint_positive_direction_power'] for r in rows if r['nonzero_defined_users']==80 and r['true_positive_probability']==.7),
            'N80_p70_both_endpoint_union_bound':next(r['both_endpoint_success_union_bound_if_both_have_this_power'] for r in rows if r['nonzero_defined_users']==80 and r['true_positive_probability']==.7),
            'N80_source_bytes_subset_range':[int(sizes.head(80).sum()),int(sizes.tail(80).sum())],
            'unresolved':'power assumes 80 defined nonzero pairs; losses/ties reduce effective N; true probability unknown; magnitude precision pilot may be optimistic; exposure and structure audit pending',
            'source_effect_sha256':hashlib.sha256(data.read_bytes()).hexdigest(),
            'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'method_sources':['https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binomtest.html',
                              'https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binom.html']}
    (p/'SAMPLE_SIZE_PLANNING.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Strong-baseline new-user planning — not enrollment', '',
           'The primary proposed comparisons are U versus boundary distance and B versus the matched class model. Each endpoint uses a two-sided sign test at alpha .025; positive direction is required. The two endpoint family uses a conservative Bonferroni allocation. The old full-versus-full-coverage effect is not used.', '',
           '| Defined nonzero users | Positive probability | Endpoint positive-direction power | Both-endpoint lower bound |',
           '| --- | --- | --- | --- |']
    for r in rows:
        if r['nonzero_defined_users'] in [30,70,80,100] and r['true_positive_probability'] in [.65,.7,.8]:
            lines.append(f"| {r['nonzero_defined_users']} | {r['true_positive_probability']:.2f} | {r['endpoint_positive_direction_power']:.3f} | {r['both_endpoint_success_union_bound_if_both_have_this_power']:.3f} |")
    lines+=['','These are conditional binomial scenarios, not evidence that N=80 is sufficient. At probability .70, 80 nonzero defined users give endpoint power 0.908 and a both-endpoint success lower bound 0.817 regardless of endpoint dependence. If either effect is weaker, or pairs are missing/zero, power is lower. An enrolled N of 80 does not guarantee 80 nonzero defined pairs.', '',
            'Magnitude precision is separately illustrated by 20,000 draws from each already examined FINAL strong-baseline effect distribution. ILLUSTRATIVE_MAGNITUDE_PRECISION.csv records its medians and sampling quantiles; this assumes the old distribution represents future users and can be optimistic. It is not a guarantee of confidence-interval width, an independent confirmation or an effect-selection rule.', '',
            '134 users remain metadata candidates before the full historical-access and structural audits. The source-file total for any 80-user subset lies between 43.57 and 55.41 GB according to the existing metadata. This excludes derived outputs, backup space and inference time. No user subset has been selected for this estimate.', '',
            'The enrollment size/budget must be resolved before candidate enrollment, protocol sealing or outcome access. N=30 is a feasible budget scenario but has only 0.432 endpoint power at probability .70, and cannot silently inherit the stronger precision/power claim of an 80-user design. Both positive and negative results must be reported.', '',
            'Methods: [SciPy binomtest](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binomtest.html), [SciPy binomial survival function](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binom.html).']
    (p/'SAMPLE_SIZE_PLANNING.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(result))

if __name__=='__main__':main()
