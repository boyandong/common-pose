"""Read-only successor runtime/seal/hash and exact-range transport diagnosis.

Credentials are read from the explicitly authorized original user record into
RAM only. No source, partial, scientific method, or original seal is mutated.
"""
import concurrent.futures as cf
import datetime
import json
from pathlib import Path
import re
import subprocess
import time
import sys

from runtime_common import LANE, ROOT, frozen, read, save, sha
from pipeline_supervisor import Supervisor, REMOTE_LANE
from acquire_sources import response

LOCAL = Path('D:/CommonPose_confirmation_N80_20261010')
ORIGINAL_RECORD = Path('C:/Users/董伯言/.codex/sessions/2026/10/09/rollout-2026-10-09T17-14-50-01a11ff1-9aef-7eb2-b6a3-e1f589db0718.jsonl')


def credential():
    found = set()
    with ORIGINAL_RECORD.open(encoding='utf-8') as stream:
        for line in stream:
            if '47514' not in line:
                continue
            item = json.loads(line)
            payload = item.get('payload', {})
            if item.get('type') != 'response_item' or payload.get('role') != 'user':
                continue
            text = '\n'.join(c.get('text', '') for c in payload.get('content', []))
            for user_line in text.splitlines():
                if '47514' in user_line and 'root@connect.westc.seetacloud.com' in user_line:
                    match = re.search(r'密码\s*[:：=]?\s*([^\s]+)\s*$', user_line)
                    if match:
                        found.add(match.group(1))
    assert len(found) == 1, 'trusted credential absent or ambiguous; no guessing'
    return found.pop()


def handles():
    script = "Get-Process -Name python -ErrorAction SilentlyContinue | Select-Object Id,@{N='start_time';E={$_.StartTime.ToString('o')}} | ConvertTo-Json -Compress"
    result = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', script], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0
    return json.loads(result.stdout or '[]')


def check_file(row):
    path = LOCAL/'source'/row['user']/Path(row['source_member']).name
    partial = path.with_name(path.name+'.partial')
    if path.exists():
        meta = read(path.with_name(path.name+'.receipt.json'))
        assert path.stat().st_size == row['size'] == meta['size']
        assert meta['source_member'] == row['source_member']
        assert meta['cohort_sha256'] == sha(LANE/'ENROLLMENT_MANIFEST.json')
        assert sha(path) == meta['sha256']
        return {'member':row['source_member'], 'state':'COMPLETE_REHASH_PASS', 'bytes':row['size']}
    if partial.exists():
        return {'member':row['source_member'], 'state':'PARTIAL_RETAINED', 'bytes':partial.stat().st_size, 'sha256':sha(partial)}
    return {'member':row['source_member'], 'state':'NOT_PRESENT', 'bytes':0}


def probe(cohort, row):
    path = LOCAL/'source'/row['user']/Path(row['source_member']).name
    partial = path.with_name(path.name+'.partial')
    have = partial.stat().st_size
    result = {'member':row['source_member'], 'partial_bytes':have, 'source_data_offset':row['archive_data_offset'], 'writes_performed':False}
    if not have:
        result['tail']='EMPTY_NO_TAIL'
    else:
        n = min(have, 4096)
        with partial.open('rb') as f:
            f.seek(have-n); tail = f.read(n)
        start = time.monotonic()
        with response(cohort, row['archive_data_offset']+have-n, row['archive_data_offset']+have-1) as r:
            assert r.read(n+1) == tail, 'retained partial tail integrity mismatch'
        result.update(tail='EXACT_RANGE_ETAG_TAIL_PASS', tail_seconds=time.monotonic()-start)
    begin = row['archive_data_offset']+have
    count = min(256<<10, row['size']-have)
    if count:
        start = time.monotonic()
        with response(cohort, begin, begin+count-1) as r:
            result['headers_seconds'] = time.monotonic()-start
            got = 0; reads = []
            while got < count:
                before = time.monotonic()
                data = r.read1(min(64<<10, count-got))
                assert data, 'diagnostic range truncated'
                got += len(data)
                reads.append({'bytes':len(data),'seconds':time.monotonic()-before})
            assert r.read(1) == b'', 'diagnostic range oversized'
        result.update(probe_bytes=got, total_seconds=time.monotonic()-start, read1_observations=reads)
    return result


def main():
    cohort = frozen(dependencies=False)
    if '--segmented-smoke' in sys.argv:
        import hashlib
        import acquire_sources_segmented_20261010 as segmented
        row=next(r for r in cohort['files'] if r['source_member'].endswith('076e4-cv-emg-pose-demonstration@2-recording-16_left.hdf5'))
        partial=LOCAL/'source'/row['user']/(Path(row['source_member']).name+'.partial')
        have=partial.stat().st_size;begin=row['archive_data_offset']+have
        count=min(segmented.SEGMENT,row['size']-have);start=time.monotonic();digest=hashlib.sha256();got=0
        with segmented.response(cohort,begin,begin+count-1) as stream:
            while got<count:
                assert time.monotonic()-start<segmented.REQUEST_DEADLINE
                data=stream.read1(min(64<<10,count-got));assert data,'truncated smoke response'
                digest.update(data);got+=len(data)
            assert stream.read(1)==b''
        result={'status':'FULL_SEGMENT_EXACT_RANGE_PASS','member':row['source_member'],'begin':begin,'bytes':got,'sha256':digest.hexdigest(),'elapsed_seconds':time.monotonic()-start,'writes_performed':False,'runner_sha256':sha(LANE/'acquire_sources_segmented_20261010.py')}
        save(LANE/'SUCCESSOR_FULL_SEGMENT_SMOKE_20261010.json',result)
        print(json.dumps(result),flush=True)
        return
    analysis = read(LANE/'ANALYSIS_CODE_SEAL.json')
    assert all(sha(LANE/n) == h for n,h in analysis['files'].items())
    result = {'observed_local_time':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
              'local_python_handles':handles(), 'protocol_sha256':sha(LANE/'SCIENTIFIC_SPEC.md'),
              'cohort_sha256':sha(LANE/'ENROLLMENT_MANIFEST.json'), 'new_effects_read':False}
    if '--remote-only' not in sys.argv:
        with cf.ThreadPoolExecutor(max_workers=4) as pool:
            inventory = list(pool.map(check_file, cohort['files']))
        result['local_inventory'] = inventory
        result['complete_files'] = sum(r['state']=='COMPLETE_REHASH_PASS' for r in inventory)
        result['complete_bytes'] = sum(r['bytes'] for r in inventory if r['state']=='COMPLETE_REHASH_PASS')
        print('LOCAL_FULL_REHASH_PASS', result['complete_files'],result['complete_bytes'], flush=True)
    supervisor = Supervisor(credential())
    try:
        code = f'''import sys,os,json,shutil,platform,subprocess
from pathlib import Path
os.environ.update(OMP_NUM_THREADS='8',OPENBLAS_NUM_THREADS='8',MKL_NUM_THREADS='8')
sys.path.insert(0,{REMOTE_LANE!r})
import numpy,torch
from runtime_common import frozen,read,sha,LANE,BASE,load_module
c=frozen(numeric=True);s=read(LANE/'ANALYSIS_CODE_SEAL.json')
assert all(sha(LANE/n)==h for n,h in s['files'].items())
module=load_module('gate4c_preflight',BASE/'gate4c_upstream_substitution_reliability_v1/scripts/run_gate4c.py')
assert module.upstream_tree_sha()==read(LANE/'FROZEN_EXECUTION_MANIFEST.json')['upstream_tree_sha256']
assert torch.__version__=='2.8.0+cu128' and torch.version.cuda=='12.8' and torch.cuda.is_available()
assert 'RTX 5090 D' in torch.cuda.get_device_name()
from importlib.metadata import version
from threadpoolctl import threadpool_info
print(json.dumps({{'status':'PASS','python':platform.python_version(),'versions':{{k:version(k) for k in read(LANE/'FROZEN_EXECUTION_MANIFEST.json')['numerical_versions']}},'torch':torch.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(),'threadpools':threadpool_info(),'remaining_bytes':shutil.disk_usage('/root/autodl-tmp').free,'gpu_state':subprocess.run(['nvidia-smi','--query-gpu=name,memory.used,memory.total,utilization.gpu','--format=csv,noheader'],capture_output=True,text=True).stdout,'remote_jobs':[p.name for p in (LANE/'jobs').iterdir()] if (LANE/'jobs').exists() else [],'source_files':len(list(Path('/root/autodl-tmp/common_pose_confirmation_N80_20261010/source').rglob('*.hdf5'))),'upstream_tree_sha256':module.upstream_tree_sha()}}))
'''
        result['remote_preflight'] = supervisor.rpc(code)
        result['remote_stages'] = {s:supervisor.inspect_stage(s) for s in ['qualification','reconstruction','support','analysis','verification']}
        print('REMOTE_FROZEN_PREFLIGHT_PASS', json.dumps(result['remote_preflight']),flush=True)
    finally:
        supervisor.close_connection();supervisor.password=None
    if '--remote-only' not in sys.argv:
        partials=[row for row in cohort['files'] if (LOCAL/'source'/row['user']/(Path(row['source_member']).name+'.partial')).exists()]
        result['transport_probes']=[]
        for row in partials:
            try:
                observed=probe(cohort,row)
            except Exception as error:
                observed={'member':row['source_member'],'state':'PROBE_FAILED','error_type':type(error).__name__,'error':str(error)}
            result['transport_probes'].append(observed)
            print('EXACT_RANGE_PROBE', row['source_member'], observed.get('tail'),observed.get('total_seconds'),observed.get('error_type'),flush=True)
    result['status']='READ_ONLY_SUCCESSOR_AUDIT_COMPLETE'
    name='SUCCESSOR_REMOTE_RECHECK_20261010.json' if '--remote-only' in sys.argv else 'SUCCESSOR_PREFLIGHT_TRANSPORT_DIAGNOSIS_20261010.json'
    save(LANE/name,result)


if __name__=='__main__':main()
