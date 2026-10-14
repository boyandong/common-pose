"""Exact frozen member acquisition, bounded same-member transport retries only."""
import concurrent.futures as cf
import hashlib
import os
from pathlib import Path
import threading
import time
import urllib.error
import urllib.request
from runtime_common import LANE,DATA as REMOTE_DATA,frozen,sha,read,save,progress
DATA=Path('D:/CommonPose_confirmation_N80_20261010')

STOP=threading.Event()
LOCK=threading.Lock()
class IntegrityError(Exception):pass

def event(kind,**fields):
    with LOCK:
        with (LANE/'acquisition_events.jsonl').open('a',encoding='utf-8') as f:
            import json
            f.write(json.dumps({'event':kind,'epoch':time.time(),**fields})+'\n')

def response(cohort,begin,end):
    request=urllib.request.Request(cohort['source_url'],headers={'Range':f'bytes={begin}-{end}','If-Match':cohort['etag']})
    r=urllib.request.urlopen(request,timeout=30)
    if r.status!=206 or r.headers.get('Content-Range')!=f'bytes {begin}-{end}/{cohort["archive_bytes"]}' or r.headers.get('ETag')!=cohort['etag']:
        r.close();raise IntegrityError('source version or range mismatch')
    return r

def acquire(cohort,row):
    p=DATA/'source'/row['user']/Path(row['source_member']).name
    p.parent.mkdir(parents=True,exist_ok=True)
    receipt=p.with_name(p.name+'.receipt.json');partial=p.with_name(p.name+'.partial')
    if p.exists():
        if not receipt.exists():raise IntegrityError('complete source without receipt; preserve for audit')
        meta=read(receipt)
        assert meta['cohort_sha256']==sha(LANE/'ENROLLMENT_MANIFEST.json') and meta['source_member']==row['source_member']
        assert p.stat().st_size==row['size']==meta['size'] and sha(p)==meta['sha256']
        return row['size']
    started=time.monotonic()
    for attempt in range(8):
        if STOP.is_set():raise RuntimeError('cancelled after another file failure')
        have=partial.stat().st_size if partial.exists() else 0
        if have>row['size']:raise IntegrityError('oversized partial')
        if have==row['size']:break
        if time.monotonic()-started>900:raise TimeoutError('same-member deadline exceeded')
        try:
            if have:
                n=min(4096,have)
                with partial.open('rb') as f:f.seek(have-n);tail=f.read(n)
                with response(cohort,row['archive_data_offset']+have-n,row['archive_data_offset']+have-1) as r:
                    if r.read(n+1)!=tail:raise IntegrityError('resumed tail mismatch')
            begin=row['archive_data_offset']+have;end=row['archive_data_offset']+row['size']-1
            with response(cohort,begin,end) as r,partial.open('ab',buffering=0) as f:
                while not STOP.is_set():
                    if time.monotonic()-started>900:raise TimeoutError('same-member deadline exceeded')
                    data=r.read(64<<10)
                    if not data:break
                    f.write(data)
            if partial.stat().st_size!=row['size']:raise OSError('truncated response')
            break
        except IntegrityError:raise
        except urllib.error.HTTPError as ex:
            if ex.code not in [408,429,500,502,503,504]:raise
            event('TRANSPORT_RETRY',member=row['source_member'],attempt=attempt+1,error=repr(ex))
        except (TimeoutError,OSError) as ex:
            event('TRANSPORT_RETRY',member=row['source_member'],attempt=attempt+1,error=repr(ex))
        STOP.wait(min(2**attempt,8))
    if STOP.is_set():raise RuntimeError('cancelled')
    if not partial.exists() or partial.stat().st_size!=row['size']:raise TimeoutError('retry budget exhausted')
    digest=sha(partial)
    meta={'source_member':row['source_member'],'size':row['size'],'sha256':digest,
          'cohort_sha256':sha(LANE/'ENROLLMENT_MANIFEST.json'),'source_url':cohort['source_url'],
          'etag':cohort['etag'],'archive_data_offset':row['archive_data_offset'],
          'official_per_member_hash_available':False,'runner_sha256':sha(Path(__file__))}
    if receipt.exists():assert read(receipt)==meta,'preserved receipt mismatch'
    else:save(receipt,meta)
    os.replace(partial,p)
    event('FILE_COMPLETE',member=row['source_member'],bytes=row['size'],sha256=digest)
    return row['size']

def main():
    cohort=frozen(dependencies=False)
    assert DATA.drive.upper()=='D:' and DATA.name=='CommonPose_confirmation_N80_20261010'
    DATA.mkdir(exist_ok=True)
    import shutil
    assert shutil.disk_usage(DATA).free>=cohort['total_bytes']+15_000_000_000,'capacity preflight failed'
    start=time.monotonic();done=0;completed_bytes=0
    progress('ACQUISITION_RUNNING',required_files=cohort['total_files'],completed_files=0)
    with cf.ThreadPoolExecutor(max_workers=8) as pool:
        futures={pool.submit(acquire,cohort,r):r for r in cohort['files']}
        for future in cf.as_completed(futures):
            try:completed_bytes+=future.result()
            except Exception:
                STOP.set()
                for pending in futures:pending.cancel()
                progress('ACQUISITION_FAILED',completed_files=done,failed_member=futures[future]['source_member'])
                raise
            done+=1
            if done%10==0 or done==cohort['total_files']:
                progress('ACQUISITION_RUNNING',required_files=cohort['total_files'],completed_files=done,
                         completed_bytes=completed_bytes,elapsed_seconds=time.monotonic()-start)
                print('ACQUIRED',done,cohort['total_files'],completed_bytes,flush=True)
    assert completed_bytes==cohort['total_bytes']
    save(LANE/'ACQUISITION_COMPLETE.json',{'status':'COMPLETE','files':done,'bytes':completed_bytes,
          'cohort_sha256':sha(LANE/'ENROLLMENT_MANIFEST.json'),'runner_sha256':sha(Path(__file__)),
          'elapsed_seconds':time.monotonic()-start})
    progress('ACQUISITION_COMPLETE',files=done,bytes=completed_bytes)

if __name__=='__main__':main()
