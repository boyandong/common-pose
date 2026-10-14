"""Exactly-once isolated stages with recorded terminal exit states."""
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

HERE=Path(__file__).resolve().parent


def write(p,d):
    q=p.with_suffix('.json.partial');q.write_text(json.dumps(d,indent=2)+'\n');os.replace(q,p)


def main():
    with (HERE/'EXECUTION.lock').open('x') as f:f.write(str(os.getpid())+'\n')
    stages=[('gpu_cost',['gpu_cost_profile.py']),('factorial_fit',['factorial_experiment.py','fit']),
        ('factorial_evaluation',['factorial_experiment.py','evaluate']),('lag_window_sensitivity',['time_window_sensitivity.py']),
        ('independent_verification',['verify_server.py']),('report_package',['summarize_server.py'])]
    completed=[];start=time.monotonic()
    try:
        for name,args in stages:
            write(HERE/'PIPELINE_STATE.json',{'status':'RUNNING','stage':name,'controller_pid':os.getpid(),'completed':completed,'elapsed_seconds':time.monotonic()-start})
            with (HERE/(name+'.log')).open('wb') as log:
                child=subprocess.Popen([sys.executable,str(HERE/args[0]),*args[1:]],cwd=HERE,stdout=log,stderr=subprocess.STDOUT,
                    env={**os.environ,'OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2','MKL_NUM_THREADS':'2'})
                ticks=Path('/proc/'+str(child.pid)+'/stat').read_text().split()[21]
                write(HERE/(name+'.launch.json'),{'pid':child.pid,'start_ticks':ticks,'argv':args,'controller_pid':os.getpid()})
                code=child.wait()
            write(HERE/(name+'.terminal.json'),{'exit_code':code,'stage':name,'pid':child.pid,'outcome':'KNOWN'})
            if code:raise RuntimeError(name+' exited '+str(code))
            completed.append(name)
        write(HERE/'PIPELINE_STATE.json',{'status':'COMPLETE_PENDING_LOCAL_DELIVERY','completed':completed,'controller_pid':os.getpid(),'elapsed_seconds':time.monotonic()-start})
    except Exception as exc:
        write(HERE/'PIPELINE_STATE.json',{'status':'FAILED_PRESERVED','completed':completed,'controller_pid':os.getpid(),'reason':str(exc),'traceback':traceback.format_exc()})
        raise


if __name__=='__main__':main()
