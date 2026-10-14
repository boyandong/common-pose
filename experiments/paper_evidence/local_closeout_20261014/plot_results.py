"""Evidence charts in this lane only; no manuscript assets are replaced."""
import csv
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'runtime_plot'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def rows(name):
    with (HERE/'results'/name).open(encoding='utf-8') as f:return list(csv.DictReader(f))


def main():
    out=HERE/'results/figures';out.mkdir(exist_ok=True)
    names=['DB9 posture','DB9 grasp','CeTI posture','CeTI grasp','SHOW instruction','KIN phase']
    estimates=[r for r in rows('PRIMARY_PAIRED_INTERVALS.csv') if r['cohort']=='N80' and r['A']=='boundary']
    joint=[r for r in rows('JOINT_SUPPORT_SENSITIVITY.csv') if r['cohort']=='N80' and r['retention']=='0.3']
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    for grayscale in [False,True]:
        colors=['#0072B2','#D55E00'] if not grayscale else ['#202020','#777777']
        fig,axes=plt.subplots(1,2,figsize=(13,5.2),sharey=True)
        for j,metric in enumerate(['U','B']):
            vals=[next(r for r in estimates if r['consumer']==name and r['metric']==metric) for name in names]
            mids=np.array([float(r['median_reduction_pp']) for r in vals]);lo=np.array([float(r['CI95_low_pp']) for r in vals]);hi=np.array([float(r['CI95_high_pp']) for r in vals])
            axes[0].errorbar(mids,np.arange(6)+(j-.5)*.17,xerr=[mids-lo,hi-mids],fmt='o' if j==0 else 's',
                color=colors[j],capsize=3,label='Overall U (n=80)' if j==0 else 'Balanced B (joint support)')
            mj=np.array([float(next(r for r in joint if r['consumer']==name)['joint_'+metric+'_pp']) for name in names])
            lj=np.array([float(next(r for r in joint if r['consumer']==name)['joint_'+metric+'_low_pp']) for name in names]);hj=np.array([float(next(r for r in joint if r['consumer']==name)['joint_'+metric+'_high_pp']) for name in names])
            axes[1].errorbar(mj,np.arange(6)+(j-.5)*.17,xerr=[mj-lj,hj-mj],fmt='o' if j==0 else 's',color=colors[j],capsize=3,label='Same-subset '+metric)
        axes[0].set_yticks(np.arange(6),[name+'  (B n='+next(r for r in joint if r['consumer']==name)['joint_users']+')' for name in names])
        axes[0].invert_yaxis()
        for ax,title in zip(axes,['Main participant sets','Same joint-support participants']):
            ax.axvline(0,color='#555555',ls='--',lw=.8);ax.grid(axis='x',alpha=.2);ax.set_xlabel('Boundary minus Full/U (percentage points)');ax.set_title(title);ax.legend(loc='lower left',fontsize=9)
        fig.suptitle('N80, 30% offline retention: paired medians and pointwise 95% intervals',fontsize=12)
        fig.text(.5,.015,'DB9 posture balanced analysis has only 3 participants. These are exploratory conditional intervals.',ha='center',fontsize=9)
        fig.tight_layout(rect=[0,.05,1,.92])
        suffix='grayscale' if grayscale else 'color'
        fig.savefig(out/('N80_primary_and_joint_CI_'+suffix+'.svg'));fig.savefig(out/('N80_primary_and_joint_CI_'+suffix+'.png'),dpi=180);plt.close(fig)
    print('COLOR_AND_GRAYSCALE_EVIDENCE_CHARTS_COMPLETE')


if __name__=='__main__':main()
