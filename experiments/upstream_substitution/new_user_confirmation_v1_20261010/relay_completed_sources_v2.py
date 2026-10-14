"""Bounded per-worker SSH reconnection, unchanged frozen member/copy/hash logic."""
import concurrent.futures as cf
import os
from pathlib import Path
import sys
import threading
import time
import paramiko
from runtime_common import LANE,read,save,sha,frozen
from relay_sources import HOST,PORT,KEY,PinnedKey
import relay_completed_sources as original

LOCAL=Path('D:/CommonPose_confirmation_N80_20261010')
TLS=threading.local();CLIENTS=[];CLIENT_LOCK=threading.Lock();SECRET={'password':None}

class BoundedClient(paramiko.SSHClient):
    def open_sftp(self):
        channel=self.get_transport().open_session(timeout=30)
        channel.settimeout(45);channel.invoke_subsystem('sftp')
        return paramiko.SFTPClient(channel)

def state(stage,**fields):
    save(LANE/'STREAM_RELAY_V2_PROGRESS.json',{'stage':stage,'pid':os.getpid(),'observed_epoch':time.time(),**fields},overwrite=True)

def connection():
    client=getattr(TLS,'client',None)
    if client is not None and client.get_transport() is not None and client.get_transport().is_active():return client
    client=BoundedClient();client.set_missing_host_key_policy(PinnedKey())
    client.connect(HOST,port=PORT,username='root',password=SECRET['password'],allow_agent=False,look_for_keys=False,
                   timeout=20,auth_timeout=20,banner_timeout=20)
    client.get_transport().set_keepalive(30)
    TLS.client=client
    with CLIENT_LOCK:CLIENTS.append(client)
    print('PINNED_WORKER_CONNECTION_PASS',threading.get_ident(),flush=True)
    return client

def transfer(row):
    for attempt in range(8):
        try:return original.send(connection(),row)
        except (paramiko.AuthenticationException,paramiko.BadHostKeyException):raise
        except (EOFError,OSError,paramiko.SSHException) as error:
            if 'host key mismatch' in str(error).lower():raise
            client=getattr(TLS,'client',None)
            if client is not None:client.close()
            TLS.client=None
            print('SAME_MEMBER_TRANSPORT_RECONNECT',row['source_member'],attempt+1,type(error).__name__,flush=True)
            if attempt==7:raise
            time.sleep(min(2**attempt,15))

def main():
    sys.stdout=(LANE/'stream_relay_v2.stdout.log').open('a',encoding='utf-8',buffering=1)
    sys.stderr=(LANE/'stream_relay_v2.stderr.log').open('a',encoding='utf-8',buffering=1)
    cohort=frozen(dependencies=False);seal=read(LANE/'STREAM_RELAY_V2_CODE_SEAL.json')
    assert seal['runner_sha256']==sha(Path(__file__))
    assert seal['preserved_copy_and_hash_implementation_sha256']==sha(LANE/'relay_completed_sources.py')
    assert seal['cohort_sha256']==sha(LANE/'ENROLLMENT_MANIFEST.json')
    assert seal['preserved_scientific_protocol_sha256']==sha(LANE/'SCIENTIFIC_SPEC.md')
    SECRET['password']=sys.stdin.readline().rstrip('\r\n');sys.stdin.close()
    pending={r['source_member']:r for r in cohort['files']};active={};done=set();total=0;started=time.monotonic()
    state('STREAM_RELAY_V2_RUNNING',completed_files=0,required_files=cohort['total_files'])
    try:
        with cf.ThreadPoolExecutor(max_workers=4) as pool:
            while pending or active:
                for name,row in list(pending.items()):
                    if len(active)>=4:break
                    p=LOCAL/'source'/row['user']/Path(row['source_member']).name
                    if p.exists() and p.with_name(p.name+'.receipt.json').exists():
                        active[pool.submit(transfer,row)]=row;del pending[name]
                if not active:
                    state('WAITING_FOR_LOCAL_SOURCE',completed_files=len(done),required_files=cohort['total_files'],remotely_verified_bytes=total)
                    time.sleep(5);continue
                finished,_=cf.wait(active,timeout=5,return_when=cf.FIRST_COMPLETED)
                for future in finished:
                    row=active.pop(future);total+=future.result();done.add(row['source_member'])
                    print('REMOTE_SHA_VERIFIED',len(done),cohort['total_files'],row['source_member'],flush=True)
                state('STREAM_RELAY_V2_RUNNING',completed_files=len(done),required_files=cohort['total_files'],
                      remotely_verified_bytes=total,active_files=len(active),remaining_files=len(pending),elapsed_seconds=time.monotonic()-started)
        assert len(done)==cohort['total_files'] and total==cohort['total_bytes']
        while not (LANE/'ACQUISITION_COMPLETE.json').exists():time.sleep(2)
        assert read(LANE/'ACQUISITION_COMPLETE.json')['bytes']==total
        save(LANE/'LOCAL_RELAY_COMPLETE.json',{'status':'ALL_FROZEN_SOURCES_TRANSFERRED_AND_REMOTE_SHA256_VERIFIED',
            'files':len(done),'bytes':total,'cohort_sha256':sha(LANE/'ENROLLMENT_MANIFEST.json'),'runner_sha256':sha(Path(__file__)),
            'copy_and_hash_implementation_sha256':sha(LANE/'relay_completed_sources.py'),'host_key_sha256':KEY,
            'elapsed_seconds':time.monotonic()-started,'scientific_members_or_rules_changed':False})
        state('STREAM_RELAY_V2_COMPLETE',completed_files=len(done),remotely_verified_bytes=total)
    except BaseException as error:
        state('STREAM_RELAY_V2_FAILED',completed_files=len(done),remotely_verified_bytes=total,error_type=type(error).__name__)
        raise
    finally:
        for client in CLIENTS:client.close()
        SECRET['password']=None

if __name__=='__main__':main()
