import os
import sys
import subprocess
import time
from server_common import HERE,dump,sha

def main():
    seal=__import__('json').loads((HERE/'SCORE_FIELD_SEAL.json').read_text())
    assert all(sha(HERE/n)==h for n,h in seal['files'].items())
    assert not (HERE/'score_field_ablation').exists()
    start=time.monotonic();state=HERE/'SCORE_FIELD_STATE.json'
    dump(HERE/'SCORE_FIELD_LAUNCH.json',{'pid':os.getpid(),'start_ticks':open('/proc/self/stat').read().split()[21],'python':sys.executable,'seal_sha256':sha(HERE/'SCORE_FIELD_SEAL.json')})
    for script in ['score_field_ablation.py','close_score_fields.py']:
        dump(state,{'stage':script,'status':'RUNNING','pid':os.getpid(),'elapsed_seconds':time.monotonic()-start})
        with (HERE/(script+'.log')).open('w') as log:
            r=subprocess.run([sys.executable,str(HERE/script)],stdout=log,stderr=subprocess.STDOUT)
        if r.returncode:
            dump(state,{'stage':script,'status':'FAILED_KNOWN_EXIT','exit_code':r.returncode,'pid':os.getpid()});return r.returncode
    dump(state,{'status':'COMPLETE','elapsed_seconds':time.monotonic()-start,'pid':os.getpid()})
    return 0

if __name__=='__main__':sys.exit(main())
