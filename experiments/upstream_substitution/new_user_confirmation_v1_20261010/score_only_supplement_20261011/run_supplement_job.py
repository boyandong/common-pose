"""One immutable supplemental stage launch/terminal receipt, no auto relaunch."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from runtime_common import read,save,sha

HERE=Path(__file__).resolve().parent
STAGES={'support':['analyze_score_only.py','support'],'analysis':['analyze_score_only.py','analysis'],'verification':['verify_score_only.py'],'backup_export':['export_integrated_backup_manifest.py']}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=STAGES);args=parser.parse_args()
    seal=read(HERE/'CODE_SEAL.json')
    for n,h in seal['files'].items():assert sha(HERE/n)==h,n
    path=HERE/'jobs'/args.stage;path.mkdir(parents=True,exist_ok=False);started=time.time()
    with (path/'output.log').open('xb') as log:
        command=[sys.executable,'-u',str(HERE/STAGES[args.stage][0]),*STAGES[args.stage][1:]]
        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
        save(path/'LAUNCH.json',{'stage':args.stage,'parent_pid':os.getpid(),'child_pid':child.pid,'started_epoch':started,'command':command,'code_seal_sha256':sha(HERE/'CODE_SEAL.json')})
        code=child.wait()
    save(path/'TERMINAL.json',{'stage':args.stage,'exit_code':code,'started_epoch':started,'finished_epoch':time.time(),'output_log_sha256':sha(path/'output.log')})
    sys.exit(code)

if __name__=='__main__':main()
