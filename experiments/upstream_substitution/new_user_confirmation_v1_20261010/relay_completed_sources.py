"""Upload each verified completed D source while the fixed acquisition continues.

No scientific membership or method changes. Existing frozen batch relay is kept.
Credentials enter on stdin only; completed local sources remain retained.
"""
import concurrent.futures as cf
import json
import os
from pathlib import Path
import posixpath
import shlex
import sys
import time
import paramiko
from runtime_common import LANE,sha,read,save,frozen
from relay_sources import HOST,PORT,KEY,PinnedKey,mkdirs

LOCAL=Path('D:/CommonPose_confirmation_N80_20261010')
REMOTE='/root/autodl-tmp/common_pose_confirmation_N80_20261010/source'

def remote_hash(client,path):
    _,out,err=client.exec_command('sha256sum -- '+shlex.quote(path),timeout=45)
    value=out.read().decode().split();error=err.read().decode()
    if out.channel.recv_exit_status()!=0 or not value:raise RuntimeError('remote hash failed: '+error)
    return value[0]

def send(client,row):
    local=LOCAL/'source'/row['user']/Path(row['source_member']).name
    receipt=local.with_name(local.name+'.receipt.json');meta=read(receipt)
    assert local.stat().st_size==row['size']==meta['size'] and sha(local)==meta['sha256']
    assert meta['cohort_sha256']==sha(LANE/'ENROLLMENT_MANIFEST.json')
    remote=posixpath.join(REMOTE,row['user'],local.name)
    sftp=client.open_sftp();sftp.get_channel().settimeout(45)
    try:
        mkdirs(sftp,posixpath.dirname(remote))
        try:existing=sftp.stat(remote)
        except FileNotFoundError:existing=None
        if existing:
            with sftp.open(remote+'.receipt.json') as f:stored=json.loads(f.read())
            assert stored==meta and existing.st_size==row['size']
        else:
            partial=remote+'.relay.partial'
            sftp.put(str(local),partial,confirm=True)
            try:
                with sftp.open(remote+'.receipt.json') as f:stored=json.loads(f.read())
            except FileNotFoundError:stored=None
            if stored is not None:assert stored==meta
            else:
                sftp.put(str(receipt),remote+'.receipt.json.relay.partial',confirm=True)
                sftp.rename(remote+'.receipt.json.relay.partial',remote+'.receipt.json')
            sftp.rename(partial,remote)
    finally:sftp.close()
    digest=remote_hash(client,remote)
    assert digest==meta['sha256'],'local/remote source hash differs'
    transfer=LOCAL/'relay_receipts'/row['user']/(local.name+'.transfer.json')
    item={'member':row['source_member'],'bytes':row['size'],'local_sha256':meta['sha256'],
          'remote_sha256':digest,'remote_path':remote,'cohort_sha256':meta['cohort_sha256'],
          'host_key_sha256':KEY,'runner_sha256':sha(Path(__file__)),'verified_epoch':time.time()}
    if not transfer.exists():save(transfer,item)
    else:
        old=read(transfer)
        for key in ['member','bytes','local_sha256','remote_sha256','remote_path','cohort_sha256','host_key_sha256']:
            assert old[key]==item[key],key
    return row['size']

def progress(stage,**fields):
    save(LANE/'STREAM_RELAY_PROGRESS.json',{'stage':stage,'pid':os.getpid(),'observed_epoch':time.time(),**fields},overwrite=True)

def main():
    # Own redirected logs keep this process independent of the chat's terminal.
    sys.stdout=(LANE/'stream_relay.stdout.log').open('a',encoding='utf-8',buffering=1)
    sys.stderr=(LANE/'stream_relay.stderr.log').open('a',encoding='utf-8',buffering=1)
    cohort=frozen(dependencies=False)
    seal=read(LANE/'STREAM_RELAY_CODE_SEAL.json')
    assert seal['runner_sha256']==sha(Path(__file__))
    assert seal['cohort_sha256']==sha(LANE/'ENROLLMENT_MANIFEST.json')
    assert seal['existing_acquisition_seal_sha256']==sha(LANE/'FROZEN_EXECUTION_MANIFEST.json')
    assert seal['preserved_scientific_protocol_sha256']==sha(LANE/'SCIENTIFIC_SPEC.md')
    password=sys.stdin.readline().rstrip('\r\n');sys.stdin.close()
    client=paramiko.SSHClient();client.set_missing_host_key_policy(PinnedKey())
    client.connect(HOST,port=PORT,username='root',password=password,allow_agent=False,look_for_keys=False,
                   timeout=20,auth_timeout=20,banner_timeout=20);password=None
    save(LANE/'STREAM_RELAY_AUTHENTICATION.json',{'status':'PINNED_HOST_AUTHENTICATION_PASS','host':HOST,'port':PORT,
         'host_key_sha256':KEY,'observed_epoch':time.time(),'pid':os.getpid()})
    started=time.monotonic();pending={r['source_member']:r for r in cohort['files']};active={};done=set();total=0
    progress('STREAM_RELAY_RUNNING',completed_files=0,required_files=cohort['total_files'])
    try:
        with cf.ThreadPoolExecutor(max_workers=4) as pool:
            while pending or active:
                for name,row in list(pending.items()):
                    if len(active)>=4:break
                    local=LOCAL/'source'/row['user']/Path(row['source_member']).name
                    if local.exists() and local.with_name(local.name+'.receipt.json').exists():
                        active[pool.submit(send,client,row)]=row;del pending[name]
                if not active:
                    progress('WAITING_FOR_LOCAL_SOURCE',completed_files=len(done),required_files=cohort['total_files'],
                             remotely_verified_bytes=total,elapsed_seconds=time.monotonic()-started)
                    time.sleep(5);continue
                finished,_=cf.wait(active,timeout=5,return_when=cf.FIRST_COMPLETED)
                for future in finished:
                    row=active.pop(future);total+=future.result();done.add(row['source_member'])
                    print('REMOTE_SHA_VERIFIED',len(done),cohort['total_files'],row['source_member'],flush=True)
                progress('STREAM_RELAY_RUNNING',completed_files=len(done),required_files=cohort['total_files'],
                         remotely_verified_bytes=total,active_files=len(active),waiting_local_files=len(pending),
                         elapsed_seconds=time.monotonic()-started)
        assert len(done)==cohort['total_files'] and total==cohort['total_bytes']
        while not (LANE/'ACQUISITION_COMPLETE.json').exists():time.sleep(2)
        assert read(LANE/'ACQUISITION_COMPLETE.json')['bytes']==total
        save(LANE/'LOCAL_RELAY_COMPLETE.json',{'status':'ALL_FROZEN_SOURCES_TRANSFERRED_AND_REMOTE_SHA256_VERIFIED',
             'files':len(done),'bytes':total,'cohort_sha256':sha(LANE/'ENROLLMENT_MANIFEST.json'),
             'runner_sha256':sha(Path(__file__)),'host_key_sha256':KEY,'elapsed_seconds':time.monotonic()-started})
        progress('STREAM_RELAY_COMPLETE',completed_files=len(done),remotely_verified_bytes=total)
    except BaseException as ex:
        progress('STREAM_RELAY_FAILED',completed_files=len(done),remotely_verified_bytes=total,error_type=type(ex).__name__)
        raise
    finally:client.close()

if __name__=='__main__':main()
