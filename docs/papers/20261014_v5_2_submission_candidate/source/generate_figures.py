"""Approved V5 vector figures from sealed CSVs; no new experiment or bootstrap."""
import sys,csv,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]
ROOT=next((p for p in HERE.parents if (p/'experiments/paper_evidence/local_closeout_20261014').is_dir()),HERE)
sys.path.insert(0,str(ROOT/'experiments/paper_evidence/local_closeout_20261014/runtime_plot'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
from matplotlib.colors import Normalize
DATA=ROOT/'experiments/paper_evidence/local_closeout_20261014'
if not DATA.is_dir():DATA=HERE/'reproducibility/figure_data'
NAMES=['DB9 posture','DB9 grasp','CeTI posture','CeTI grasp','SHOW instruction','KIN phase']
MAP={('db9_scoreonly_v3_20261011','C1_primary'):NAMES[0],('db9_scoreonly_v3_20261011','C2_primary'):NAMES[1],('ceti_age_scoreonly_v3_20261012','C1_primary'):NAMES[2],('ceti_age_scoreonly_v3_20261012','C2_primary'):NAMES[3],('show3d_scoreonly_v3_20261012','C1_primary'):NAMES[4],('kinmus_uji_scoreonly_v3_20261012','C1_primary'):NAMES[5]}
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
SOURCES=[DATA/'results/PRIMARY_PAIRED_INTERVALS.csv',DATA/'results/PAIRED_INTERVALS_ALL_BUDGETS.csv',DATA/'results/JOINT_SUPPORT_SENSITIVITY.csv',DATA/'reproduction_bundle/input/N80_USER_COVERAGE_SERVICE.csv']
primary=read(SOURCES[0]);allrows=read(SOURCES[1]);joint=read(SOURCES[2]);service=read(SOURCES[3])
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8.5,'axes.titlesize':9,'axes.labelsize':8.5,'xtick.labelsize':8,'ytick.labelsize':8.5,'svg.fonttype':'none','pdf.fonttype':42,'savefig.facecolor':'white'})
def save(fig,name):
    for ext in ['pdf','svg','png']:fig.savefig(HERE/'figures'/(name+'.'+ext),dpi=230,bbox_inches='tight',pad_inches=.025)
    plt.close(fig)
def figure1(gray):
    blue='#2166ac' if not gray else '#333333';grey='#686868'
    pale='#eef5fb' if not gray else '#f1f1f1';neutral='#f5f5f5'
    fig,ax=plt.subplots(figsize=(3.5,1.70));ax.set(xlim=(0,100),ylim=(-9,103));ax.axis('off')
    # Broad lanes provide hierarchy; node borders remain light and spaced apart.
    for x,y,w,h,fill in [(2,20,44,65,neutral),(51,20,47,80,pale)]:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.5,rounding_size=3',linewidth=0,facecolor=fill))
    def box(x,y,w,label,color,fill='white',height=10,fs=7.2):
        ax.add_patch(FancyBboxPatch((x,y),w,height,boxstyle='round,pad=.35,rounding_size=1.8',linewidth=.7,edgecolor=color,facecolor=fill))
        ax.text(x+w/2,y+height/2,label,ha='center',va='center',fontsize=fs,color='#202020',linespacing=1.15)
    def arrow(a,b,color,style='solid'):
        ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=7,linewidth=.8,color=color,linestyle=style,shrinkA=1,shrinkB=1))
    ax.text(24,94,'Measured reference',ha='center',fontsize=7.6,fontweight='bold',color=grey)
    ax.text(74.5,94,'EMG',ha='center',fontsize=7.8,fontweight='bold',color=blue)
    box(55,74,39,'Frozen estimator',blue)
    box(4,58,40,'Measured pose',grey);box(55,58,39,'Estimated pose',blue)
    for x,w in [(4,40),(55,39)]:box(x,42,w,'Same frozen classifier',grey,fs=6.8)
    box(4,26,40,'Reference decision: A',grey,fs=6.8);box(55,26,39,'Estimated decision: B',blue,fs=6.8)
    arrow((74.5,91),(74.5,85),blue)
    for a,b in [(74,68),(58,52),(42,36)]:arrow((74.5,a),(74.5,b),blue)
    for a,b in [(58,52),(42,36)]:arrow((24,a),(24,b),grey,'dashed')
    box(4,5,40,'Example: A ≠ B → flip',grey,height=12,fs=7)
    box(55,5,39,'Rank: retain / reject',blue,fill=pale,height=12,fs=7)
    arrow((24,26),(24,17.5),grey,'dashed');arrow((74.5,26),(74.5,17.5),blue)
    # The reference comparison receives both decisions; ranking has no reference arrow.
    ax.plot([55,48,48,44],[31,31,12,12],color=grey,lw=.8,ls='--')
    arrow((47,12),(44,12),grey,'dashed')
    ax.text(24,-5,'Development / evaluation',ha='center',fontsize=7,color=grey)
    ax.text(74.5,-5,'Estimated features only',ha='center',fontsize=7,color=blue)
    save(fig,'fig1_compact'+('_grayscale' if gray else ''))

def figure2(gray):
    vals=np.zeros((6,8))
    for i,name in enumerate(NAMES):
        for m,method in enumerate(['score_only','full']):
            for j,q in enumerate(['0.1','0.3','0.5','0.7']):
                rr=[r for r in service if MAP[(r['lane'],r['condition'])]==name and r['goal']=='U' and r['mode']=='offline_equal_coverage' and r['nominal_retention']==q and r['method'] in ['boundary',method]]
                byuser={}
                for r in rr:byuser.setdefault(r['user'],{})[r['method']]=float(r['U'])
                assert len(byuser)==80 and all(set(d)=={'boundary',method} for d in byuser.values())
                vals[i,m*4+j]=float(np.median([100*(d['boundary']-d[method]) for d in byuser.values()]))
                if method=='full':
                    archived=[r for r in allrows if r['cohort']=='N80' and r['consumer']==name and r['A']=='boundary' and r['B_method']==method and r['metric']=='U' and r['retention']==q]
                    assert len(archived)==1 and abs(vals[i,m*4+j]-float(archived[0]['median_reduction_pp']))<1e-12
    fig,ax=plt.subplots(figsize=(7.05,1.45));im=ax.pcolormesh(np.arange(9)-.5,np.arange(7)-.5,vals,cmap='Greys' if gray else 'Blues',norm=Normalize(min(0,float(vals.min())),float(vals.max())),shading='flat',rasterized=False)
    ax.set_xlim(-.5,7.5);ax.set_ylim(5.5,-.5)
    ax.set_yticks(range(6),NAMES);ax.set_xticks(range(8),['10%','30%','50%','70%']*2);ax.tick_params(length=0)
    ax.text(1.5,-.92,'Score-only/U',ha='center',fontweight='bold');ax.text(5.5,-.92,'Full/U',ha='center',fontweight='bold')
    for i in range(6):
        for j in range(8):ax.text(j,i,f'{vals[i,j]:+.2f}',ha='center',va='center',color='white' if vals[i,j]>.57*vals.max() else '#111111',fontsize=8)
    ax.axvline(3.5,color='white',lw=2);ax.set_xlabel('Offline retention budget (prediction-valid blocks)',labelpad=3)
    cbar=fig.colorbar(im,ax=ax,fraction=.026,pad=.02);cbar.set_label('Paired reduction (pp)',fontsize=8);cbar.ax.tick_params(labelsize=7);cbar.solids.set_rasterized(False)
    fig.tight_layout(pad=.3);save(fig,'fig2_N80_ranking'+('_grayscale' if gray else ''))
    if not gray:
        (HERE/'review/FIGURE2_VALUES.json').write_text(json.dumps({'consumers':NAMES,'columns':['Score-only/U '+q for q in ['10%','30%','50%','70%']]+['Full/U '+q for q in ['10%','30%','50%','70%']],'values':vals.tolist()},indent=2)+'\n')
def figure3(gray):
    blue='#1f77b4' if not gray else '#222222';orange='#d55e00' if not gray else '#777777'
    fig,axes=plt.subplots(1,2,figsize=(7.05,1.92),gridspec_kw={'width_ratios':[1,1.23]})
    expected_n=[3,74,52,80,79,60]
    for panel,metric in enumerate(['U','B']):
        ax=axes[panel];ax.axvline(0,color='#666666',ls='--',lw=.8)
        for i,name in enumerate(NAMES):
            rr=[r for r in primary if r['cohort']=='N80' and r['consumer']==name and r['A']=='boundary' and r['B_method']=='full' and r['metric']==metric];assert len(rr)==1;r=rr[0]
            md,lo,hi=[float(r[k]) for k in ['median_reduction_pp','CI95_low_pp','CI95_high_pp']];assert int(r['users'])==(80 if panel==0 else expected_n[i])
            low=panel==1 and i==0;color='#999999' if low else blue if panel==0 else orange
            ax.hlines(i,lo,hi,color=color,lw=1.3,linestyle='dotted' if low else 'solid');ax.plot(md,i,marker='D' if low else 'o' if panel==0 else 's',ms=4.7 if i!=4 else 5.7,mfc='white' if low else color,mec=color)
        ax.set_ylim(5.6,-.6);ax.set_yticks(range(6),NAMES if panel==0 else [f'n={n}'+(' (low support)' if n==3 else '') for n in expected_n]);ax.tick_params(axis='y',length=0);ax.spines[['top','right','left']].set_visible(False);ax.grid(axis='x',alpha=.15)
        ax.set_title('A  Overall disagreement (n=80)' if panel==0 else 'B  Class-balanced disagreement',loc='left',fontsize=8.7,fontweight='bold')
        ax.set_xlabel('Paired reduction (pp)',fontsize=8,labelpad=1)
    axes[0].set_xlim(-.5,7.5);axes[1].set_xlim(-30,22)
    fig.subplots_adjust(left=.135,right=.99,top=.85,bottom=.40,wspace=.56)
    # Two grouped annotations replace the former undifferentiated footnote lines.
    fig.add_artist(FancyBboxPatch((.132,.005),.275,.185,transform=fig.transFigure,boxstyle='round,pad=.004,rounding_size=.012',facecolor='#f4f4f4',edgecolor='none'))
    fig.add_artist(FancyBboxPatch((.433,.005),.559,.185,transform=fig.transFigure,boxstyle='round,pad=.004,rounding_size=.012',facecolor='#fff3eb' if not gray else '#f4f4f4',edgecolor='none'))
    fig.text(.143,.115,'DB9 posture · class support',fontsize=7.5,fontweight='bold')
    fig.text(.143,.035,'No Gate 22/80 → Full/U (30%) 3/80',fontsize=7.5)
    fig.text(.444,.030,'SHOW (n=79)\nSame participants',fontsize=7.3,fontweight='bold',linespacing=1.35)
    fig.text(.615,.030,'Overall +2.608 [1.708, 2.960]\nClass-balanced −20.880 [−27.156, −12.280]',fontsize=7.5,linespacing=1.35)

    save(fig,'fig3_class_fidelity'+('_grayscale' if gray else ''))
def table1():
    expected=[[38.91,21.95,17.29,16.00],[18.37,6.67,4.87,3.46],[43.05,24.73,21.87,20.77],[41.10,31.59,29.60,25.65],[16.43,6.93,6.29,4.10],[22.32,5.95,3.81,3.66]]
    body=[];sealed=[]
    for i,name in enumerate(NAMES):
        nums=[]
        for method in ['all','boundary','score_only','full']:
            rr=[r for r in service if MAP[(r['lane'],r['condition'])]==name and r['goal']=='U' and r['method']==method and ((method=='all' and r['mode']=='deployment') or (method!='all' and r['mode']=='offline_equal_coverage' and r['nominal_retention']=='0.3'))]
            assert len(rr)==80;value=float(np.median([float(r['U']) for r in rr]))*100;nums.append(value)
        assert [f'{x:.2f}' for x in nums]==[f'{x:.2f}' for x in expected[i]],(name,nums)
        r=next(r for r in primary if r['cohort']=='N80' and r['consumer']==name and r['A']=='boundary' and r['B_method']=='full' and r['metric']=='U')
        effect=[float(r[k]) for k in ['median_reduction_pp','CI95_low_pp','CI95_high_pp']]
        body.append(name+' & '+' & '.join(f'{x:.2f}' for x in nums)+f' & {effect[0]:.3f} [{effect[1]:.3f}, {effect[2]:.3f}]'+r'\\')
        sealed.append({'consumer':name,'method_medians_percent':nums,'paired_effect_pp_and_CI':effect,'n':80})
    content=r'''\begingroup
\small
\setlength{\tabcolsep}{3pt}
\renewcommand{\arraystretch}{1.05}
\begin{tabular}{lrrrrl}
\toprule
Consumer & No Gate $U$ & Boundary $U$ & Score-only/U $U$ & Full/U $U$ & Paired Boundary--Full/U (95\% CI)\\
\midrule
'''+ '\n'.join(body)+r'''
\bottomrule
\end{tabular}
\par\smallskip
\begin{minipage}{\linewidth}\footnotesize
No Gate retains all prediction-valid blocks; selective methods retain 30\%. $U$: participant medians (\%; lower is better). Paired effects: percentage points (higher is better). Intervals are pointwise descriptive participant-bootstrap summaries, not differences between method medians.
\end{minipage}
\endgroup
'''
    (HERE/'table1.tex').write_text(content);(HERE/'review/TABLE1_VALUES.json').write_text(json.dumps(sealed,indent=2)+'\n')
if __name__=='__main__':
    # V5.2 Table I is retained as approved LaTeX, with expanded statistical note.
    for gray in [False,True]:figure3(gray);figure2(gray);figure1(gray)
    (HERE/'review/FIGURE_SOURCE_HASHES.json').write_text(json.dumps({str(p):sha(p) for p in SOURCES},indent=2)+'\n')
    print('APPROVED_TABLE_AND_THREE_VECTOR_FIGURES_COMPLETE')
