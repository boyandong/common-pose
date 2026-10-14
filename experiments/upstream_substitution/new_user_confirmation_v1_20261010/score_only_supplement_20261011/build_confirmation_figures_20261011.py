"""Complete frozen eight-method presentation; no new endpoints or tests."""
import argparse
import csv
import math
from pathlib import Path
import statistics
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from runtime_common import LANE,read,save,sha

HERE=Path(__file__).resolve().parent
ARCHIVE=Path('D:/CommonPose_confirmation_N80_20261010/results')
METHODS=['class_empirical','margin','entropy','boundary_distance','full','no_tta','class_model','score_only']
COVERAGES=[.3,.5,.6,.7,.8,.9,1.]

def rows(path):
    with path.open(encoding='utf-8-sig',newline='') as stream:return list(csv.DictReader(stream))

def number(value):return None if value in ['',None] else float(value)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--check-ready',action='store_true');args=ap.parse_args()
    prerequisites=[HERE/'CONTROLLER_TERMINAL.json',HERE/'EXECUTION_COMPLETE.json',HERE/'INDEPENDENT_VERIFICATION.json',HERE/'OFFHOST_BACKUP_VERIFICATION.json',LANE/'INDEPENDENT_RESULT_VERIFICATION.json',LANE/'OFFHOST_BACKUP_VERIFICATION.json']
    missing=[str(p.relative_to(LANE)) for p in prerequisites if not p.exists()]
    if args.check_ready:
        print({'ready':not missing,'missing':missing,'effect_values_read':False});return
    assert not missing,missing
    assert read(HERE/'CONTROLLER_TERMINAL.json')['exit_code']==0
    assert read(HERE/'EXECUTION_COMPLETE.json')['status']=='PRIMARY_AND_SCORE_ONLY_VERIFIED_AND_FULLY_BACKED_UP'
    for p in prerequisites[2:]:assert read(p)['status']=='PASS',p
    manifest=read(LANE/'OFFHOST_BACKUP_MANIFEST.json');inventory={r['local_relative']:r for r in manifest['files']}
    inputs={}
    def checked(name):
        path=ARCHIVE/name;record=inventory['results/'+name]
        assert sha(path)==record['sha256'] and path.stat().st_size==record['bytes'],name
        inputs[name]=sha(path);return path
    parent_risks=rows(checked('RISK_COVERAGE_ROWS.csv'))
    secondary_risks=rows(checked('score_only_supplement_20261011/RISK_COVERAGE_ROWS.csv'))
    primary=rows(checked('PRIMARY_USER_EFFECTS.csv'));result=read(checked('PRIMARY_RESULT.json'))
    assert sha(ARCHIVE/'PRIMARY_RESULT.json')==read(LANE/'INDEPENDENT_RESULT_VERIFICATION.json')['result_sha256']
    assert len(parent_risks)==7840 and len(secondary_risks)==2240 and len(primary)==160
    original_full={(r['contract'],r['user'],r['nominal_coverage']):r for r in parent_risks if r['method']=='full'}
    for r in secondary_risks:
        if r['method']!='full':continue
        old=original_full[r['contract'],r['user'],r['nominal_coverage']]
        for field in ['ordinary_risk','fixed_common_risk']:
            a,b=number(r[field]),number(old[field]);assert (a is None)==(b is None)
            if a is not None:assert abs(a-b)<1e-12
    curve=parent_risks+[r for r in secondary_risks if r['method']=='score_only']
    summaries=[]
    for contract in ['U','B']:
        metric='ordinary_risk' if contract=='U' else 'fixed_common_risk'
        for method in METHODS:
            for coverage in COVERAGES:
                selected=[r for r in curve if r['contract']==contract and r['method']==method and float(r['nominal_coverage'])==coverage]
                assert len(selected)==80 and len({r['user'] for r in selected})==80
                valid=[number(r[metric]) for r in selected if number(r[metric]) is not None]
                summaries.append({'contract':contract,'method':method,'nominal_coverage':coverage,'metric':metric,'enrolled':80,'defined_users':len(valid),'missing_users':80-len(valid),'median_risk':statistics.median(valid) if valid else None})
    dest=HERE/'confirmation_figures_20261011';dest.mkdir(exist_ok=False)
    with (dest/'CURVE_PRESENTATION_SUMMARY.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(summaries[0]));writer.writeheader();writer.writerows(summaries)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    colors=['#0072B2','#56B4E9','#009E73','#CC79A7','#111111','#999933','#332288','#D55E00']
    fig,axes=plt.subplots(1,2,figsize=(13,6.4))
    for ax,contract in zip(axes,['U','B']):
        for method,color in zip(METHODS,colors):
            selected=[r for r in summaries if r['contract']==contract and r['method']==method]
            y=[100*r['median_risk'] if r['median_risk'] is not None else math.nan for r in selected]
            label=method+' (secondary)' if method=='score_only' else method
            ax.plot([100*r['nominal_coverage'] for r in selected],y,color=color,marker='o',markersize=3.5,linewidth=2.6 if method=='full' else 1.5,linestyle='--' if method=='score_only' else '-',label=label)
        ax.set_title('U: ordinary Flip risk' if contract=='U' else 'B: original fixed-common-class Flip risk')
        ax.set_xlabel('Nominal acceptance budget (%)');ax.set_ylabel('Median per-user risk (%)')
        ax.set_xticks([100*x for x in COVERAGES]);ax.set_ylim(bottom=0);ax.grid(alpha=.2)
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='lower center',ncol=4,bbox_to_anchor=(.5,.11),frameon=False)
    fig.text(.5,.04,'Each point is the median of defined per-user risks; denominators are in the companion CSV.\nB sets remain frozen across coverages and methods. Missing risks are never filled with zero.',ha='center',fontsize=9)
    fig.subplots_adjust(bottom=.29,wspace=.28,top=.89)
    fig.suptitle('Frozen N80 confirmation: all eight methods, all seven coverages',fontsize=14)
    for suffix in ['png','svg']:fig.savefig(dest/('EIGHT_METHOD_RISK_COVERAGE.'+suffix),dpi=240)
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,6))
    for ax,contract in zip(axes,['U','B']):
        all_rows=[r for r in primary if r['contract']==contract];assert len(all_rows)==80
        selected=[r for r in all_rows if number(r['baseline_risk']) is not None and number(r['full_risk']) is not None]
        x=[100*number(r['baseline_risk']) for r in selected];y=[100*number(r['full_risk']) for r in selected]
        ax.scatter(x,y,s=23,alpha=.65,color='#0072B2',edgecolor='white',linewidth=.3)
        bound=max([1.]+x+y)*1.08
        ax.plot([0,bound],[0,bound],color='#777777',linestyle='--',linewidth=1)
        ax.set_xlim(0,bound);ax.set_ylim(0,bound);ax.set_aspect('equal',adjustable='box');ax.grid(alpha=.2)
        baseline='boundary_distance' if contract=='U' else 'class_model'
        ax.set_xlabel(baseline+' risk (%)');ax.set_ylabel('full risk (%)')
        endpoint=result['primary'][contract]
        assert endpoint['complete_pairs']==len(selected)
        ax.set_title(f"{contract}: {len(selected)}/80 complete pairs\n{endpoint['formal_decision']}")
    fig.text(.5,.045,'Canonical 30% budget; one point per computable user. Missing pairs remain in the full report.\nFlip is preservation of one frozen consumer output, not independently labelled gesture accuracy.',ha='center',fontsize=9)
    fig.subplots_adjust(bottom=.23,wspace=.28,top=.86)
    fig.suptitle('The two original confirmatory comparisons',fontsize=14)
    for suffix in ['png','svg']:fig.savefig(dest/('PRIMARY_USER_PAIRED_RISKS.'+suffix),dpi=240)
    plt.close(fig)
    caption=dest/'FIGURE_CAPTIONS.md'
    caption.write_text('# Verified N80 presentation figures\n\n'
        'The risk-coverage panels include all original seven methods plus the separately frozen score-only secondary at every prescribed coverage. Points summarize only defined per-user risks; the CSV retains the exact 80-user denominators and missing counts for all 112 points. The composition of defined users may vary between points. Connecting lines are presentation only, not a dense-coverage estimator.\n\n'
        'The paired panels show the two original canonical 30% comparisons. Every computable user contributes one point; missing users remain in the full flow and manuscript. The formal decisions are copied from independently verified original results. No additional test, endpoint, seed choice, method search or causal pose/TTA claim is introduced.\n\n'
        'Flip measures preservation of one frozen consumer output, not independently labelled gesture accuracy. Upstream checkpoint membership remains UNRESOLVED.\n',encoding='utf-8')
    files={p.name:sha(p) for p in dest.iterdir() if p.is_file()}
    save(dest/'BUILD_MANIFEST.json',{'status':'VERIFIED_FROZEN_PRESENTATION_FIGURES_BUILT','input_sha256':inputs,'files':files,'source_code_sha256':sha(Path(__file__)),'matplotlib':matplotlib.__version__,'summary_rows':len(summaries),'all_eight_methods_and_seven_coverages':True,'new_inferential_test_or_endpoint':False,'missing_user_denominators_retained':True,'visual_review':'REQUIRED_BEFORE_FINAL_GOAL_COMPLETION'})
    from shutil import copyfile
    backup=ARCHIVE/'score_only_supplement_20261011/confirmation_figures_20261011';backup.mkdir(exist_ok=False)
    for source in dest.iterdir():
        if source.is_file():copyfile(source,backup/source.name);assert sha(source)==sha(backup/source.name)
    print('VERIFIED_PRESENTATION_FIGURES_BUILT_AND_BACKED_UP')

if __name__=='__main__':main()
