"""Full-file identity and original source structural/validity rules, no inference."""
from collections import defaultdict
from pathlib import Path
import h5py
import numpy as np
from runtime_common import LANE,frozen,rows,save,sha,progress

def main():
    cohort=frozen(numeric=True);rr=rows(cohort);totals=defaultdict(int);results=[];bad=[]
    for i,r in enumerate(rr,1):
        p=Path(r['path'])
        with h5py.File(p,'r') as h:
            ts=h['emg2pose/timeseries'];emg=ts['emg'];gt=ts['joint_angles'];t=ts['time']
            n=len(gt)
            if emg.shape!=(n,16) or gt.shape!=(n,20) or t.shape!=(n,) or n<=1870:raise RuntimeError('shape qualification failed '+str(p))
            if not np.isfinite(emg).all():raise RuntimeError('nonfinite EMG '+str(p))
            if not np.isfinite(t).all() or not np.all(np.diff(t)>0):raise RuntimeError('time qualification failed '+str(p))
            g=gt[1790:];valid=np.isfinite(g).all(axis=1)&(~np.all(np.isclose(g,0),axis=1))
            blocks=len(g)//40;vb=valid[:blocks*40].reshape(blocks,40).all(axis=1);vb[0]=False
            count=int(vb.sum())
        totals[r['participant_id']]+=count
        results.append({'user':r['participant_id'],'member':r['source_member'],'sha256':r['sha256'],
                        'rows':n,'gt_valid_50hz_blocks':count,'emg_finite':True,'time_finite_increasing':True})
        if i%25==0 or i==len(rr):
            progress('QUALIFICATION_RUNNING',completed_files=i,required_files=len(rr))
            print('QUALIFIED',i,len(rr),flush=True)
    assert set(totals)==set(cohort['enrolled_users'])
    bad=[u for u in cohort['enrolled_users'] if totals[u]<10000]
    receipt={'status':'PASS' if not bad else 'STRUCTURAL_FAILURE_NO_REPLACEMENT',
             'cohort_sha256':sha(LANE/'ENROLLMENT_MANIFEST.json'),'runner_sha256':sha(Path(__file__)),
             'files':results,'valid_block_totals':dict(totals),'bad_users':bad,
             'predictions_run':False,'effects_read':False}
    save(LANE/'SOURCE_QUALIFICATION.json',receipt)
    progress('QUALIFICATION_PASS' if not bad else 'QUALIFICATION_FAILED',users=80,bad_users=bad)
    if bad:raise RuntimeError('frozen validity floor failed; no replacement')
    print('SOURCE_QUALIFICATION_PASS',80,len(rr),flush=True)

if __name__=='__main__':main()
