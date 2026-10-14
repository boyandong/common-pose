"""Bounded process/receipt evidence without reading scientific effect values."""
import argparse
import datetime
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from runtime_common import read,save
from pipeline_supervisor import Supervisor,REMOTE_LANE
from successor_preflight_transport_20261010 import credential,handles

HERE=Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser();ap.add_argument('label');args=ap.parse_args()
    assert args.label.replace('_','').isalnum()
    client=Supervisor(credential())
    try:
        result=client.rpc(f'''import json
from pathlib import Path
p=Path({REMOTE_LANE!r});s=p/'score_only_supplement_20261011';stages={{}}
for prefix,names in [('', ['qualification','reconstruction','support','analysis','verification']),('score_only_supplement_20261011/', ['support','analysis','verification','backup_export'])]:
 for n in names:
  q=p/prefix;d=q/'jobs'/n;dispatch=q/('dispatch_'+n+'.json');r={{}}
  for name in ['LAUNCH.json','TERMINAL.json']:
   if (d/name).exists():r[name]=json.loads((d/name).read_text())
  if dispatch.exists():r['dispatch']=json.loads(dispatch.read_text())
  r['state']='TERMINAL' if 'TERMINAL.json' in r else 'DISPATCHED' if r else 'NOT_DISPATCHED'
  live=[]
  for role,pid in ((k,v) for k,v in r.get('LAUNCH.json',{{}}).items() if k in ['parent_pid','child_pid']):
   proc=Path('/proc')/str(pid)
   if proc.exists():
    cmd=(proc/'cmdline').read_bytes().split(b'\\0')
    live.append({{'role':role,'pid':pid,'scripts':[Path(x.decode(errors='replace')).name for x in cmd if x.endswith(b'.py')],'start_ticks':(proc/'stat').read_text().split()[21]}})
  r['actual_handles']=live;stages[prefix+n]=r
qualification=None
if (p/'SOURCE_QUALIFICATION.json').exists():
 q=json.loads((p/'SOURCE_QUALIFICATION.json').read_text())
 qualification={{'status':q['status'],'files':len(q['files']),'users':len(q['valid_block_totals']),'bad_users':q['bad_users'],'valid_block_total':sum(q['valid_block_totals'].values()),'minimum_user_valid_blocks':min(q['valid_block_totals'].values()),'effects_read':q['effects_read']}}
print(json.dumps({{'stages':stages,'source_qualification':qualification,'supplement_partial_files':[{{'name':str(q.relative_to(s)),'bytes':q.stat().st_size}} for q in s.rglob('*.partial')],'effect_values_read':False}}))
''')
    finally:client.close_connection();client.password=None
    result['local_python_handles']=handles()
    result['observed_local_time']=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
    result['local_terminal_receipt_present']=(HERE/'CONTROLLER_TERMINAL.json').exists()
    save(HERE/('EXECUTION_OBSERVATION_'+args.label+'.json'),result)
    print(json.dumps(result))

if __name__=='__main__':main()
