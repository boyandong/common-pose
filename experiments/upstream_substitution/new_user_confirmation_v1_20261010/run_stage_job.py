"""One durable monitored stage, with parent/child handles and terminal exit receipt."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
from runtime_common import LANE,read,save,sha

STAGES={'qualification':['qualify_sources.py'],'reconstruction':['reconstruct_users.py'],
        'support':['analyze_new_users.py','--freeze-support'],'analysis':['analyze_new_users.py','--analyze'],
        'verification':['verify_new_results.py']}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=STAGES);args=ap.parse_args()
    stage=args.stage
    seal=read(LANE/'ANALYSIS_CODE_SEAL.json')
    for name,h in seal['files'].items():assert sha(LANE/name)==h,name
    dest=LANE/'jobs'/stage;dest.mkdir(parents=True,exist_ok=False)
    started=time.time()
    with (dest/'output.log').open('wb') as log:
        command=[sys.executable,'-u',str(LANE/STAGES[stage][0]),*STAGES[stage][1:]]
        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
        save(dest/'LAUNCH.json',{'stage':stage,'parent_pid':os.getpid(),'child_pid':child.pid,'started_epoch':started,
             'command':command,'code_seal_sha256':sha(LANE/'ANALYSIS_CODE_SEAL.json')})
        code=child.wait()
    save(dest/'TERMINAL.json',{'stage':stage,'exit_code':code,'started_epoch':started,'finished_epoch':time.time(),
         'output_log_sha256':sha(dest/'output.log')})
    sys.exit(code)

if __name__=='__main__':main()
