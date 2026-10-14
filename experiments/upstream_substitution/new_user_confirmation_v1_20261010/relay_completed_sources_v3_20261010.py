"""Same frozen transfer/hash logic with finite Windows progress-replace recovery."""
import argparse
import concurrent.futures as cf
import json
import os
from pathlib import Path
import sys
import time

from runtime_common import LANE,read,save,sha,frozen
from relay_sources import KEY
import relay_completed_sources_v2 as transport

MAX_REPLACE_ATTEMPTS=20
REPLACE_DELAY_SECONDS=.05
PROGRESS=LANE/'STREAM_RELAY_V2_PROGRESS.json'  # preserved supervisor interface


def replace_progress(path,item):
    """Retry only Windows sharing/access denial on a mutable progress snapshot.

    Immutable scientific/source receipts still use the original sealed save().
    An exhausted attempt preserves its temporary file and raises; no infinite wait.
    """
    path=Path(path)
    tmp=path.with_name(path.name+f'.v3.{os.getpid()}.{time.time_ns()}.partial')
    tmp.write_text(json.dumps(item,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    for attempt in range(MAX_REPLACE_ATTEMPTS):
        try:
            os.replace(tmp,path)
            return
        except OSError as error:
            if getattr(error,'winerror',None) not in [5,32,33] or attempt+1==MAX_REPLACE_ATTEMPTS:
                raise
            time.sleep(REPLACE_DELAY_SECONDS)


def state(stage,**fields):
    replace_progress(PROGRESS,{'stage':stage,'pid':os.getpid(),'observed_epoch':time.time(),**fields})


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--attempt-id',required=True);args=ap.parse_args()
    assert args.attempt_id.replace('_','').isalnum()
    sys.stdout=(LANE/f'stream_relay_v3_{args.attempt_id}.stdout.log').open('x',encoding='utf-8',buffering=1)
    sys.stderr=(LANE/f'stream_relay_v3_{args.attempt_id}.stderr.log').open('x',encoding='utf-8',buffering=1)
    import msvcrt
    lock=(LANE/'STREAM_RELAY_V3.lock').open('a+b');lock.seek(0)
    if not lock.read(1):lock.write(b'1');lock.flush()
    lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    done=set();total=0;started=time.monotonic();terminal=None
    try:
        cohort=frozen(dependencies=False);seal=read(LANE/'STREAM_RELAY_V3_CODE_SEAL_20261010.json')
        for n,h in seal['files'].items():assert sha(LANE/n)==h,n
        assert seal['cohort_sha256']==sha(LANE/'ENROLLMENT_MANIFEST.json')
        assert seal['protocol_sha256']==sha(LANE/'SCIENTIFIC_SPEC.md')
        assert seal['preserved_copy_and_hash_implementation_sha256']==sha(LANE/'relay_completed_sources.py')
        assert seal['preserved_network_implementation_sha256']==sha(LANE/'relay_completed_sources_v2.py')
        transport.SECRET['password']=sys.stdin.readline().rstrip('\r\n');sys.stdin.close()
        pending={r['source_member']:r for r in cohort['files']};active={}
        state('STREAM_RELAY_V3_RUNNING',completed_files=0,required_files=cohort['total_files'])
        with cf.ThreadPoolExecutor(max_workers=4) as pool:
            while pending or active:
                for name,row in list(pending.items()):
                    if len(active)>=4:break
                    path=transport.LOCAL/'source'/row['user']/Path(row['source_member']).name
                    if path.exists() and path.with_name(path.name+'.receipt.json').exists():
                        active[pool.submit(transport.transfer,row)]=row;del pending[name]
                if not active:
                    state('WAITING_FOR_LOCAL_SOURCE',completed_files=len(done),required_files=cohort['total_files'],remotely_verified_bytes=total)
                    time.sleep(5);continue
                finished,_=cf.wait(active,timeout=5,return_when=cf.FIRST_COMPLETED)
                for future in finished:
                    row=active.pop(future);total+=future.result();done.add(row['source_member'])
                    print('REMOTE_SHA_VERIFIED',len(done),cohort['total_files'],row['source_member'],flush=True)
                state('STREAM_RELAY_V3_RUNNING',completed_files=len(done),required_files=cohort['total_files'],
                      remotely_verified_bytes=total,active_files=len(active),remaining_files=len(pending),elapsed_seconds=time.monotonic()-started)
        assert len(done)==cohort['total_files'] and total==cohort['total_bytes']
        while not (LANE/'ACQUISITION_COMPLETE.json').exists():time.sleep(2)
        assert read(LANE/'ACQUISITION_COMPLETE.json')['bytes']==total
        save(LANE/'LOCAL_RELAY_COMPLETE.json',{'status':'ALL_FROZEN_SOURCES_TRANSFERRED_AND_REMOTE_SHA256_VERIFIED',
             'files':len(done),'bytes':total,'cohort_sha256':sha(LANE/'ENROLLMENT_MANIFEST.json'),'runner_sha256':sha(Path(__file__)),
             'copy_and_hash_implementation_sha256':sha(LANE/'relay_completed_sources.py'),'host_key_sha256':KEY,
             'transport_status_seal_sha256':sha(LANE/'STREAM_RELAY_V3_CODE_SEAL_20261010.json'),
             'elapsed_seconds':time.monotonic()-started,'scientific_members_or_rules_changed':False})
        state('STREAM_RELAY_V3_COMPLETE',completed_files=len(done),remotely_verified_bytes=total)
        terminal={'status':'COMPLETE','exit_code':0,'files':len(done),'bytes':total}
    except BaseException as error:
        terminal={'status':'FAILED_PRESERVE_AND_INSPECT','exit_code':1,'files':len(done),'bytes':total,'error_type':type(error).__name__,'reason':str(error)}
        try:state('STREAM_RELAY_V3_FAILED',completed_files=len(done),remotely_verified_bytes=total,error_type=type(error).__name__)
        except OSError as snapshot_error:print('PROGRESS_WRITE_FAILURE',type(snapshot_error).__name__,getattr(snapshot_error,'winerror',None),flush=True)
        raise
    finally:
        for client in transport.CLIENTS:client.close()
        transport.SECRET['password']=None
        if terminal is not None:
            save(LANE/f'STREAM_RELAY_V3_TERMINAL_{args.attempt_id}.json',{**terminal,'pid':os.getpid(),'finished_epoch':time.time(),'elapsed_seconds':time.monotonic()-started})
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1);lock.close()


if __name__=='__main__':main()
