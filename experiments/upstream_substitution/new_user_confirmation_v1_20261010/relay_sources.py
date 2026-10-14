"""Pinned SSH local D source relay; credentials stdin only, no secret in files."""
import concurrent.futures as cf
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import posixpath
import sys
import time
import paramiko
from runtime_common import LANE,DATA as REMOTE_DATA,frozen,sha,read,save,progress

LOCAL_DATA=Path('D:/CommonPose_confirmation_N80_20261010')
KEY='962677eaf342b0d70d757796b387fe83964884f33f66284ff37e2fc6cf1496a7'
HOST='connect.westc.seetacloud.com';PORT=47514

class PinnedKey(paramiko.MissingHostKeyPolicy):
    def missing_host_key(self,client,hostname,key):
        if hashlib.sha256(key.asbytes()).hexdigest()!=KEY:raise paramiko.SSHException('host key mismatch')

def mkdirs(sftp,path):
    for end in list(PurePosixPath(path).parents)[::-1]+[PurePosixPath(path)]:
        if str(end) in ['.','/']:continue
        try:sftp.stat(str(end))
        except FileNotFoundError:
            try:sftp.mkdir(str(end))
            except OSError:sftp.stat(str(end))

def send(client,row):
    local=LOCAL_DATA/'source'/row['user']/Path(row['source_member']).name
    receipt=local.with_name(local.name+'.receipt.json');meta=read(receipt)
    assert local.stat().st_size==row['size']==meta['size'] and sha(local)==meta['sha256']
    assert meta['cohort_sha256']==sha(LANE/'ENROLLMENT_MANIFEST.json')
    remote=posixpath.join('/root/autodl-tmp/common_pose_confirmation_N80_20261010','source',row['user'],local.name)
    sftp=client.open_sftp();sftp.get_channel().settimeout(45)
    try:
        mkdirs(sftp,posixpath.dirname(remote))
        try:exists=sftp.stat(remote)
        except FileNotFoundError:exists=None
        if exists:
            with sftp.open(remote+'.receipt.json') as f:stored=json.loads(f.read())
            assert stored==meta and exists.st_size==row['size']
            # Full remote bytes are independently hashed during qualification.
            return row['size']
        part=remote+'.relay.partial'
        sftp.put(str(local),part,confirm=True)
        rpart=remote+'.receipt.json.relay.partial'
        sftp.put(str(receipt),rpart,confirm=True)
        sftp.rename(rpart,remote+'.receipt.json')
        sftp.rename(part,remote)
        return row['size']
    finally:sftp.close()

def main():
    cohort=frozen(dependencies=False)
    assert read(LANE/'ACQUISITION_COMPLETE.json')['bytes']==cohort['total_bytes']
    print('AUTH_INPUT_REQUIRED',flush=True)
    password=sys.stdin.readline().rstrip('\r\n')
    client=paramiko.SSHClient();client.set_missing_host_key_policy(PinnedKey())
    client.connect(HOST,port=PORT,username='root',password=password,allow_agent=False,look_for_keys=False,
                   timeout=20,auth_timeout=20,banner_timeout=20);password=None
    start=time.monotonic();done=0;total=0
    try:
        with cf.ThreadPoolExecutor(max_workers=4) as pool:
            futures={pool.submit(send,client,r):r for r in cohort['files']}
            for future in cf.as_completed(futures):
                total+=future.result();done+=1
                if done%10==0 or done==cohort['total_files']:
                    progress('LOCAL_RELAY_RUNNING',completed_files=done,required_files=cohort['total_files'],bytes=total,
                             elapsed_seconds=time.monotonic()-start)
                    print('RELAYED',done,cohort['total_files'],total,flush=True)
        save(LANE/'LOCAL_RELAY_COMPLETE.json',{'status':'TRANSFER_COMPLETE_PENDING_FULL_REMOTE_HASH_QUALIFICATION',
             'files':done,'bytes':total,'cohort_sha256':sha(LANE/'ENROLLMENT_MANIFEST.json'),
             'runner_sha256':sha(Path(__file__)),'host_key_sha256':KEY,'elapsed_seconds':time.monotonic()-start})
        progress('LOCAL_RELAY_COMPLETE',files=done,bytes=total)
    finally:client.close()

if __name__=='__main__':main()
