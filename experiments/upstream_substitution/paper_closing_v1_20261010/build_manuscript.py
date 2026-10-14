"""Build manuscript-facing tables and narrative from sealed reporting results.

This generates a Markdown reporting artifact, not a new experiment or hypothesis.
Seed admission/completion is explicit and cannot be inferred from existing tables.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
SRC=HERE.parent/'paper_supplement_v1_20261009'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    inputs={}
    def read(p):
        inputs[str(p.relative_to(HERE.parent))]=sha(p)
        return json.loads(p.read_text(encoding='utf-8-sig'))
    def table(p):
        inputs[str(p.relative_to(HERE.parent))]=sha(p)
        return pd.read_csv(p)
    frozen=read(HERE/'results/RUN_MANIFEST.json')
    for name,value in frozen['files'].items():assert sha(HERE/'results'/name)==value,name
    summary=read(SRC/'comparative_analysis/SUMMARY.json')['summary']
    area=read(HERE/'results/TARGET_AREA_SUMMARY.json')['summary']
    lineage=read(HERE/'results/REPRODUCTION_LINEAGE.json')
    tta=read(SRC/'comparative_analysis/TTA_COST.json')
    effects=table(HERE/'results/USER_EFFECTS_30.csv')
    service=table(HERE/'results/CLASSWISE_30_REFERENCE_DETAIL.csv')
    original=table(HERE/'results/ORIGINAL_DEPLOYMENT_USER_ROWS.csv')
    reconstructed=table(HERE/'results/RECONSTRUCTED_DEPLOYMENT_30.csv')
    target_effects=table(HERE/'results/TARGET_AREA_PAIRED_EFFECTS.csv')
    attempt=HERE/'reproduction_attempt3_8threads'
    seed_verified=(attempt/'INDEPENDENT_VERIFICATION.json').exists()
    if seed_verified:
        verification=read(attempt/'INDEPENDENT_VERIFICATION.json')
        assert verification['status']=='PASS' and verification['canonical_max_abs_difference']==0
        assert verification['result_manifest_sha256']==sha(attempt/'seed_results/RUN_MANIFEST.json')
        seed_summary=read(attempt/'seed_results/SUMMARY.json')['summary']
        seed_risks=table(attempt/'seed_results/SEED_USER_RISKS.csv')
        diagnosis=read(attempt/'canonical/DIAGNOSIS.json')
        control=read(attempt/'thread1_control/DIAGNOSIS.json')
        order_diagnosis=read(attempt/'score_order_control/SCORE_ORDER_DIAGNOSIS.json')
    out=HERE/'manuscript_closing';out.mkdir(exist_ok=True)
    lines=[]
    def add(s=''):lines.append(s)
    def tab(headers,rows):
        add('| '+' | '.join(headers)+' |');add('| '+' | '.join(['---']*len(headers))+' |')
        for r in rows:add('| '+' | '.join(map(str,r))+' |')
        add()
    def pct(v):return f'{100*v:.2f}'
    def estimate(s):return f"{pct(s['median'])} [{pct(s['ci95'][0])}, {pct(s['ci95'][1])}]"
    add('# CommonPose manuscript closing: selective preservation of a frozen consumer')
    add()
    add('## Study identity and claim boundary')
    add()
    add('We evaluated selective preservation of the decisions of one frozen consumer when its input pose was replaced by an upstream estimate. Flip denotes disagreement with the same consumer on measured pose; it is not independently labelled gesture error. The original frozen confirmation and the later supplement are distinct evidence sources. Baseline and ablation comparisons were specified after V1 results were known, and the 20 FINAL users had already been examined. These comparisons therefore provide supplementary empirical evidence, not a new independent confirmation.')
    add()
    add('DEV comparisons use 19 users in disjoint outer folds. Original per-block DEV scores and fold instances were not retained; later fold refitting must be described separately. FINAL scoring uses the sealed full instances and DEV-only supplementary class models. No feature, method or threshold is selected from these results.')
    add()
    add('## Thirty-percent rank selection: absolute target risks')
    add()
    add('Each method accepts the same ceiling of 30% of each user’s blocks. U uses ordinary Flip risk. B uses each user’s original common reference-class set with at least 30 accepted blocks under every one of the seven methods at 30%; this set is fixed for the supplementary comparisons. It conditions on supported classes and does not establish service for omitted classes. All intervals resample users (20,000 draws, seed 20261009). Risks and differences below are in percentage points.')
    add()
    riskrows=[]
    for m in ['class_empirical','class_model','margin','entropy','boundary_distance','full','no_tta']:
        u=summary['U_FINAL']['method_risks_at_30'][m]['ordinary_risk']
        b=summary['B_FINAL']['method_risks_at_30'][m]['fixed_common_risk']
        riskrows.append({'method':m,'U_median':u['median'],'U_ci_low':u['ci95'][0],'U_ci_high':u['ci95'][1],
                         'B_median':b['median'],'B_ci_low':b['ci95'][0],'B_ci_high':b['ci95'][1]})
    tab(['Method','FINAL U risk [95% CI], pp','FINAL B fixed-common risk [95% CI], pp'],
        [[m,estimate(summary['U_FINAL']['method_risks_at_30'][m]['ordinary_risk']),estimate(summary['B_FINAL']['method_risks_at_30'][m]['fixed_common_risk'])] for m in [r['method'] for r in riskrows]])
    pd.DataFrame(riskrows).to_csv(out/'ABSOLUTE_RISKS_FINAL_30.csv',index=False)
    add('## Paired incremental benefits and TTA')
    add()
    add('Positive effects mean comparator risk minus full-gate risk. The empirical class baseline and no-TTA comparison were the designated supplementary tests; other comparator results are descriptive. The later proposed new-cohort primary contrasts are U versus boundary distance and B versus the matched class model. They are not retroactively promoted to primary tests in the old cohort.')
    add()
    erows=[]
    for m in ['class_empirical','class_model','margin','entropy','boundary_distance','no_tta']:
        u=summary['U_FINAL']['comparisons'][f'full_vs_{m}__ordinary_risk']
        b=summary['B_FINAL']['comparisons'][f'full_vs_{m}__fixed_common_risk']
        erows.append([m,estimate(u),f"{u['positive_users']}/{u['n']}",estimate(b),f"{b['positive_users']}/{b['n']}"])
    tab(['Comparator','U extra reduction [95% CI], pp','U positive/defined','B extra reduction [95% CI], pp','B positive/defined'],erows)
    add(f"Full versus no-TTA does not provide clear evidence of an extra benefit: U {estimate(summary['U_FINAL']['comparisons']['full_vs_no_tta__ordinary_risk'])} pp and B {estimate(summary['B_FINAL']['comparisons']['full_vs_no_tta__fixed_common_risk'])} pp. This is not an equivalence result and does not authorize replacing the frozen gate. On one prespecified DEV recording, warmed CUDA-synchronized inference medians were {tta['median_base_seconds']:.3f} s for the base view and {tta['median_four_view_seconds']:.3f} s for four views ({tta['median_four_view_seconds']/tta['median_base_seconds']:.2f} times). This measurement does not represent all recordings or deployment latency.")
    add()
    add('## Sample selection within predicted classes')
    add()
    add('Accepting 30% separately inside each predicted class controls class composition. Relative to the empirical class gate, FINAL ordinary-risk reductions were:')
    add()
    tab(['Gate','Median reduction [95% CI], pp','Positive/defined users'],[[c,estimate(summary[c+'_FINAL']['comparisons']['full_vs_class_empirical__within_predicted_class_ordinary_risk']),f"{summary[c+'_FINAL']['comparisons']['full_vs_class_empirical__within_predicted_class_ordinary_risk']['positive_users']}/20"] for c in ['U','B']])
    add('These descriptive comparisons support sample-level selection beyond choosing easy predicted classes; they do not establish semantic recognition accuracy.')
    add()
    add('## Every FINAL user: the proposed strong-baseline contrasts')
    add()
    users=sorted(effects.loc[effects['split']=='FINAL','user'].unique())
    def user_effect(u,c,m):
        rr=effects[(effects['split']=='FINAL')&(effects['user']==u)&(effects['contract']==c)&(effects['comparison']=='full_vs_'+m)&(effects['metric']==('ordinary_risk' if c=='U' else 'fixed_common_risk'))]
        assert len(rr)==1
        return rr.iloc[0]['effect']
    tab(['User','U vs boundary distance, pp','B vs matched class model, pp'],[[u,pct(user_effect(u,'U','boundary_distance')),pct(user_effect(u,'B','class_model'))] for u in users])
    add('## Reference-class service at 30%')
    add()
    add('The following table separates baseline support from accepted support. “No service” counts only users who had at least 30 baseline reference blocks but zero accepted blocks; absent baseline classes are not added to that count. Sparse means 1–29 accepted blocks among baseline-supported users. Each cell is baseline-supported / accepted-supported / no-service / sparse users; the cohort contains 20 users.')
    add()
    sr=[]
    for k in range(1,9):
        cells=[]
        for c in ['U','B']:
            q=service[(service['split']=='FINAL')&(service['contract']==c)&(service['method']=='full')&(service['class']==k)]
            assert len(q)==20
            q=q[q['baseline_support']>=30]
            cells.append(f"{len(q)}/{int((q['accepted_support']>=30).sum())}/{int((q['accepted_support']==0).sum())}/{int(((q['accepted_support']>0)&(q['accepted_support']<30)).sum())}")
        sr.append([k,*cells])
    tab(['Reference class','U full','B full'],sr)
    add('Complete user/class counts, risks, coverage and omissions are in results/CLASSWISE_30_REFERENCE_DETAIL.csv and CLASS_SUPPORT_30_SUMMARY.csv. Classes omitted from the B common set cannot be interpreted as having zero risk.')
    add()
    add('## Frozen-threshold deployment, original confirmation records')
    add()
    add('Fixed thresholds need not deliver the nominal coverage for each user. The table below uses the original frozen confirmation records, not reconstructed supplementary scores. U ordinary and B dynamic supported-class risks are reported with their distinct identities; the B column is not a fixed-common metric.')
    add()
    dr=[]
    for c,gate in [('U','Gate4E_Requirement_U'),('B','Gate4F_Requirement_B')]:
        for cov in sorted(original.loc[original['gate']==gate,'nominal_coverage'].unique()):
            q=original[(original['gate']==gate)&np.isclose(original['nominal_coverage'],cov)]
            assert len(q)==20
            metric='ordinary_risk' if c=='U' else 'dynamic_balanced_risk'
            dr.append([c,pct(cov),pct(q['achieved_coverage'].median()),f"{pct(q['achieved_coverage'].min())}–{pct(q['achieved_coverage'].max())}",pct(q[metric].median()),pct(q[metric].max())])
    tab(['Gate','Nominal coverage %','Median actual coverage %','Actual coverage range %','Median target risk %','Worst-user target risk %'],dr)
    add('Reconstructed thresholds are kept separately in results/RECONSTRUCTED_DEPLOYMENT_30.csv. For B full at the 30% threshold, reconstructed fixed-common risk has median '+pct(reconstructed[(reconstructed['split']=='FINAL')&(reconstructed['contract']=='B')&(reconstructed['method']=='full')]['fixed_common_risk'].median())+'% and worst user '+pct(reconstructed[(reconstructed['split']=='FINAL')&(reconstructed['contract']=='B')&(reconstructed['method']=='full')]['fixed_common_risk'].max())+'%; its class set was established in the rank comparison, not in the original confirmation. Do not merge original and reconstructed endpoints.')
    add()
    add('## Late-delivered target-risk area, 30%–100%')
    add()
    add('For each user and method we integrated the target risk by trapezoids on the saved 1% grid from 0.30 to 1.00, then formed comparator-minus-full paired areas. This late-delivered secondary analysis does not change the original confirmation or introduce a new primary hypothesis. It is neither full-rank ordinary AURC nor the area under a median-user curve. The main curves retain all 19 DEV or 20 FINAL users across all methods and grid points. Dense low-coverage diagnostics use pointwise common users and show the changing denominator; FINAL B at 1% has zero common users and no risk value.')
    add()
    ar=[]
    for c in ['U','B']:
        for m in ['class_empirical','class_model','margin','entropy','boundary_distance','no_tta']:
            s=area[f'FINAL_{c}__full_vs_{m}']
            ar.append([c,m,f"{s['median']:.5f} [{s['ci95'][0]:.5f}, {s['ci95'][1]:.5f}]",f"{100*s['median']/.70:.3f} [{100*s['ci95'][0]/.70:.3f}, {100*s['ci95'][1]/.70:.3f}]",f"{s['positive_users']}/{s['n']}"])
    tab(['Gate','Comparator','Paired raw area [95% CI]','Area/0.70 reduction, pp [95% CI]','Positive/defined users'],ar)
    add('Detailed per-user areas, paired effects and all DEV/FINAL summaries remain in results/TARGET_AREA_*.')
    add()
    add('TTA findings depend on endpoint and coverage: the designated 30% comparison does not establish an extra benefit, while the late B area comparison has a small positive paired interval. The latter is secondary and does not justify changing the frozen gate or promoting a new primary hypothesis.')
    add()
    add('## Reproduction identity and numerical environment')
    add()
    add(f"Against original V1 FINAL receipts, the reconstructed frozen-model analysis has maximum aggregate risk drift {100*lineage['FINAL_frozen_model']['max_aggregate_risk_drift']:.4f} pp across {lineage['FINAL_frozen_model']['n_endpoints']} endpoints. This is an aggregate admission result, not evidence of identical per-block predictions or cache bytes. DEV refitting differences are recorded separately in results/REPRODUCTION_LINEAGE.json; their causes cannot be separated from the existing records, and the FINAL drift bound does not apply to them.")
    add()
    if seed_verified:
        add('The original supplement exports OMP, OPENBLAS and MKL thread counts as 8. Restoring that environment reproduced all 702 canonical risk endpoints exactly, including separately identified DEV refits; this does not prove equality of unavailable historical score vectors. All 39 cache files, 34 source-artifact hashes and frozen FINAL instances were verified. The preserved 1-thread control reproduced the prior failure on FINAL B class_model user 299b130307, whereas 8 threads matched every FINAL endpoint. Eight scores changed by at most 1.11e-16; sorting floating score strata before SHA256 ties changed three accepted blocks in each direction and increased accepted Flip count by two, producing the 0.0109445 pp ordinary-risk difference. Scores were not rounded and ordering/tolerance were not changed. The class-only comparator is therefore sensitive to numerical score strata; reproducibility requires the recorded runtime as well as model hashes.')
        add()
        add('The focused control first saved its score vectors and then failed to serialize NumPy integer block indices to JSON. Its failed log is preserved; the receipt was recovered by summarizing the saved vectors locally, without rescoring or fitting. The separate-process 1-thread and 8-thread diagnoses and the seed experiment were unaffected.')
        add()
        add('## All twenty prespecified tie seeds')
        add()
        add('Seeds 20261009–20261028 were all reported using unchanged scoring instances and the original SHA256 tie rule. FINAL uses frozen scores; DEV uses explicitly identified same-spec fold refits followed by fixed-score sensitivity. Seeds are perturbations, not additional independent users. Across-seed ranges and counts of conditional user-bootstrap intervals are descriptive. B retains the original seven-method common reference-class sets for all seeds, even when current support becomes sparse; a zero-support class leaves the fixed-set risk undefined, never zero.')
        add()
        rr=[]
        for split in ['DEV','FINAL']:
            for c in ['U','B']:
                for m in ['class_empirical','class_model']:
                    s=seed_summary[f'{split}_{c}__full_vs_{m}']
                    med=s['median_effect_range'];pos=s['positive_user_count_range']
                    rr.append([split,c,m,f'{100*med[0]:.3f}–{100*med[1]:.3f}',f'{pos[0]}–{pos[1]}',s['complete_cohort_seeds'],s['ci_lower_above_zero_seeds']])
        tab(['Cohort','Gate','Comparator','Median improvement range, pp','Positive-user count range','Complete-cohort seeds /20','Conditional CI lower >0 seeds /20'],rr)
        add('Every seed retains 19 DEV or 20 FINAL defined effects in all four contrasts. The independent verifier recomputed 4,680 user-risk rows, 37,440 class-support rows, 3,120 paired effects, 1,560 diagnostic support intersections and 160 conditional bootstrap summaries directly from cached features and already persisted models, without importing the producer’s metric/tie/statistic functions or fitting any model. Its 702 canonical checks had maximum difference zero.')
        add()
        sr=[]
        for split in ['DEV','FINAL']:
            for c in ['U','B']:
                for m in ['full','class_empirical','class_model']:
                    q=seed_risks[(seed_risks['split']==split)&(seed_risks['contract']==c)&(seed_risks['method']==m)]
                    sr.append([split,c,m,len(q),int(q['sparse_frozen_classes'].fillna('').ne('').sum()),int(q['missing_frozen_classes'].fillna('').ne('').sum())])
        tab(['Cohort','Gate','Method','User-seed rows','Rows with sparse frozen class','Rows with missing frozen class'],sr)
        add('All eight reference-class support counts and risks are preserved in SEED_CLASS_SUPPORT.csv. Sparse flags mean fewer than 30 accepted blocks; the frozen class set is not redefined from seed-dependent support. SEED_SUPPORT_INTERSECTIONS_DIAGNOSTIC.csv reports current three-method support intersections for inspection, never as a replacement endpoint. No best seed is selected.')
    else:
        add('The 20-seed extension is pending independent verification; no completed robustness conclusion is claimed.')
    add()
    add('## Prospective confirmation and reproducibility status')
    add()
    add('Score-only learning is deferred under the limited empirical positioning. New-user confirmation requires an independent exposure/protected-cohort audit, checkpoint-specific exposure caveat, strong-baseline sample-size planning, and a separate protocol with fixed instance hashes before new outcomes. The old FINAL users cannot provide a new independent confirmation. New-cohort planning is not completed experimentation.')
    add()
    add('Reproduction entry points: local_closing.py and verify_local.py for sealed reporting tables/figures; run_seed_attempt.py and verify_seed_independent.py for the restored 8-thread seed extension; build_manuscript.py for this document. Frozen manifests identify external cache and model dependencies, which remain private and are not redistributed. The source-release receipt identifies the fixed Git version separately. New-user confirmation is still pending and cannot be replaced by this reporting package.')
    add()
    add('Source ledger: manuscript_closing/BUILD_MANIFEST.json, closing INPUT_MANIFEST.json, results/RUN_MANIFEST.json, original final_joint_confirmation_v1, and reconstructed paper_supplement_v1_20261009. Corrected figure names are results/DEV_FIXED_USERS_30_100 and results/FINAL_FIXED_USERS_30_100; low-coverage diagnostics are *_COMPARABLE_DENSE.')
    p=out/'MANUSCRIPT_CLOSING.md';p.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    status='REPORTING_AND_SEEDS_VERIFIED' if seed_verified else 'REPORTING_GENERATED_SEEDS_PENDING'
    (out/'BUILD_MANIFEST.json').write_text(json.dumps({'status':status,'code_sha256':sha(Path(__file__)),'inputs':inputs,'outputs':{x.name:sha(x) for x in out.iterdir() if x.is_file() and x.name!='BUILD_MANIFEST.json'}},indent=2)+'\n')
    print(json.dumps({'status':status,'document':str(p),'users':len(users),'input_files':len(inputs)}))

if __name__=='__main__':main()
