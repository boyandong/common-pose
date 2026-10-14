"""Exact-path cache/result backup, pinned SSH and local SHA256 verification."""
from pathlib import Path
import sys
import time
import paramiko
from runtime_common import LANE,sha,read,save
from relay_sources import HOST,PORT,PinnedKey

DEST=Path('D:/CommonPose_confirmation_N80_20261010')

def main():
    manifest=read(LANE/'OFFHOST_BACKUP_MANIFEST.json')
    assert manifest['cohort_sha256']==sha(LANE/'ENROLLMENT_MANIFEST.json')
    print('AUTH_INPUT_REQUIRED',flush=True);password=sys.stdin.readline().rstrip('\r\n')
    client=paramiko.SSHClient();client.set_missing_host_key_policy(PinnedKey())
    client.connect(HOST,port=PORT,username='root',password=password,allow_agent=False,look_for_keys=False,
                   timeout=20,auth_timeout=20,banner_timeout=20);password=None
    sftp=client.open_sftp();sftp.get_channel().settimeout(45);checked=[];start=time.monotonic()
    try:
        for i,r in enumerate(manifest['files'],1):
            dest=(DEST/r['local_relative']).resolve()
            assert dest.is_relative_to(DEST.resolve()),dest
            dest.parent.mkdir(parents=True,exist_ok=True)
            if dest.exists():assert dest.stat().st_size==r['bytes'] and sha(dest)==r['sha256']
            else:
                partial=dest.with_name(dest.name+'.backup.partial')
                sftp.get(r['remote_path'],str(partial))
                assert partial.stat().st_size==r['bytes'] and sha(partial)==r['sha256'],dest
                partial.replace(dest)
            checked.append(r['local_relative'])
            if i%25==0 or i==len(manifest['files']):print('BACKUP_VERIFIED',i,len(manifest['files']),flush=True)
    finally:sftp.close();client.close()
    # Independently rehash the retained source files, not just the transfer receipts.
    cohort=read(LANE/'ENROLLMENT_MANIFEST.json');source_bytes=0
    for r in cohort['files']:
        p=DEST/'source'/r['user']/Path(r['source_member']).name;meta=read(p.with_name(p.name+'.receipt.json'))
        assert p.stat().st_size==r['size'] and sha(p)==meta['sha256']
        assert meta['cohort_sha256']==sha(LANE/'ENROLLMENT_MANIFEST.json')
        source_bytes+=p.stat().st_size
    save(LANE/'OFFHOST_BACKUP_VERIFICATION.json',{'status':'PASS','local_root':str(DEST),'source_files':len(cohort['files']),
         'source_bytes':source_bytes,'cache_dependency_result_files':len(checked),'additional_backup_bytes':manifest['bytes'],
         'manifest_sha256':sha(LANE/'OFFHOST_BACKUP_MANIFEST.json'),'elapsed_seconds':time.monotonic()-start,
         'all_local_file_sha256_recomputed':True,'runner_sha256':sha(Path(__file__))})
    print('OFFHOST_SOURCE_CACHE_BACKUP_PASS',flush=True)

if __name__=='__main__':main()
