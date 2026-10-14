"""Supplemental bounded exact-range transport; original acquisition stays sealed."""
import argparse
import concurrent.futures as cf
import datetime
import json
import os
from pathlib import Path
import shutil
import sys
import time
import urllib.error
import urllib.request

import acquire_sources as original
from runtime_common import LANE, frozen, read, save, sha, progress

DATA = original.DATA
SEGMENT = 4 << 20
SOCKET_TIMEOUT = 10
REQUEST_DEADLINE = 120
ATTEMPTS = 8
IntegrityError = original.IntegrityError
STOP = original.STOP
event = original.event


def response(cohort, begin, end):
    request = urllib.request.Request(cohort['source_url'], headers={
        'Range':f'bytes={begin}-{end}', 'If-Match':cohort['etag'], 'Accept-Encoding':'identity'})
    stream = urllib.request.urlopen(request, timeout=SOCKET_TIMEOUT)
    if (stream.status != 206 or
        stream.headers.get('Content-Range') != f'bytes {begin}-{end}/{cohort["archive_bytes"]}' or
        stream.headers.get('ETag') != cohort['etag'] or
        stream.headers.get('Content-Length') != str(end-begin+1) or
        stream.headers.get('Content-Encoding', 'identity') != 'identity'):
        stream.close()
        raise IntegrityError('source version, encoding, range or length mismatch')
    return stream


def validate_tail(cohort, row, partial, have):
    if not have:
        return
    count = min(4096, have)
    with partial.open('rb') as stream:
        stream.seek(have-count); tail = stream.read(count)
    with response(cohort, row['archive_data_offset']+have-count, row['archive_data_offset']+have-1) as stream:
        if stream.read(count+1) != tail:
            raise IntegrityError('resumed tail mismatch')
    event('SEGMENTED_TAIL_VALIDATED', member=row['source_member'], partial_bytes=have)


def acquire(cohort, row):
    path = DATA/'source'/row['user']/Path(row['source_member']).name
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt = path.with_name(path.name+'.receipt.json')
    partial = path.with_name(path.name+'.partial')
    cohort_hash = sha(LANE/'ENROLLMENT_MANIFEST.json')
    if path.exists():
        if not receipt.exists():
            raise IntegrityError('complete source without receipt; preserve for audit')
        meta = read(receipt)
        assert meta['cohort_sha256'] == cohort_hash and meta['source_member'] == row['source_member']
        assert meta['size'] == row['size'] == path.stat().st_size and sha(path) == meta['sha256']
        return row['size']
    have = partial.stat().st_size if partial.exists() else 0
    if have > row['size']:
        raise IntegrityError('oversized partial')
    validate_tail(cohort, row, partial, have)
    while have < row['size']:
        segment_end = min(row['size'], have+SEGMENT)
        succeeded = False
        for attempt in range(ATTEMPTS):
            if STOP.is_set():
                raise RuntimeError('cancelled after another file failure')
            have = partial.stat().st_size if partial.exists() else 0
            if have >= segment_end:
                succeeded = True
                break
            started = time.monotonic()
            try:
                if attempt:
                    validate_tail(cohort, row, partial, have)
                begin = row['archive_data_offset']+have
                end = row['archive_data_offset']+segment_end-1
                event('SEGMENTED_RANGE_STARTED', member=row['source_member'], begin=begin, end=end, attempt=attempt+1, partial_bytes=have)
                with response(cohort, begin, end) as stream, partial.open('ab', buffering=0) as output:
                    while have < segment_end:
                        if STOP.is_set():
                            raise RuntimeError('cancelled after another file failure')
                        if time.monotonic()-started >= REQUEST_DEADLINE:
                            raise TimeoutError('exact-range request deadline exceeded')
                        # read1 returns available data after at most one raw read;
                        # byte progress is visible even when a 64KiB read would wait.
                        data = stream.read1(min(64<<10, segment_end-have))
                        if not data:
                            raise OSError('truncated exact-range response')
                        if len(data) > segment_end-have:
                            raise IntegrityError('oversized exact-range response')
                        output.write(data); have += len(data)
                    if stream.read(1) != b'':
                        raise IntegrityError('extra exact-range response bytes')
                event('SEGMENTED_RANGE_COMPLETE', member=row['source_member'], partial_bytes=have, elapsed_seconds=time.monotonic()-started)
                succeeded = True
                break
            except IntegrityError:
                raise
            except urllib.error.HTTPError as error:
                if error.code not in [408,429,500,502,503,504]:
                    raise
                event('SEGMENTED_TRANSPORT_RETRY', member=row['source_member'], attempt=attempt+1, error=repr(error), partial_bytes=partial.stat().st_size if partial.exists() else 0)
            except (TimeoutError, OSError) as error:
                event('SEGMENTED_TRANSPORT_RETRY', member=row['source_member'], attempt=attempt+1, error=repr(error), partial_bytes=partial.stat().st_size if partial.exists() else 0)
            if attempt+1 < ATTEMPTS:
                STOP.wait(min(2**attempt,8))
        if not succeeded:
            raise TimeoutError('same-segment finite retry budget exhausted; preserve partial')
        have = partial.stat().st_size
    if STOP.is_set():
        raise RuntimeError('cancelled')
    assert partial.stat().st_size == row['size']
    digest = sha(partial)
    meta = {'source_member':row['source_member'], 'size':row['size'], 'sha256':digest,
            'cohort_sha256':cohort_hash, 'source_url':cohort['source_url'], 'etag':cohort['etag'],
            'archive_data_offset':row['archive_data_offset'], 'official_per_member_hash_available':False,
            'runner_sha256':sha(Path(__file__))}
    if receipt.exists():
        stored = read(receipt)
        # A crash between immutable receipt and rename may leave the original
        # producer hash; preserve it and validate all source identity fields.
        for key,value in meta.items():
            if key != 'runner_sha256':
                assert stored[key] == value, 'preserved receipt mismatch '+key
    else:
        save(receipt,meta)
    os.replace(partial,path)
    event('FILE_COMPLETE', member=row['source_member'], bytes=row['size'], sha256=digest, supplemental_runner_sha256=sha(Path(__file__)))
    return row['size']


def main():
    parser = argparse.ArgumentParser();parser.add_argument('--attempt-id',required=True)
    args = parser.parse_args()
    assert args.attempt_id.replace('_','').isalnum()
    sys.stdout = (LANE/f'acquisition_segmented_{args.attempt_id}.stdout.log').open('x',encoding='utf-8',buffering=1)
    sys.stderr = (LANE/f'acquisition_segmented_{args.attempt_id}.stderr.log').open('x',encoding='utf-8',buffering=1)
    import msvcrt
    lock = (LANE/'ACQUISITION_SEGMENTED.lock').open('a+b')
    lock.seek(0)
    if not lock.read(1):
        lock.write(b'1');lock.flush()
    lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    started = time.monotonic();done=0;total=0
    try:
        cohort = frozen(dependencies=False)
        seal = read(LANE/'SEGMENTED_TRANSPORT_CODE_SEAL_20261010.json')
        assert seal['files'][Path(__file__).name] == sha(Path(__file__))
        assert seal['cohort_sha256'] == sha(LANE/'ENROLLMENT_MANIFEST.json')
        assert seal['protocol_sha256'] == sha(LANE/'SCIENTIFIC_SPEC.md')
        remaining = sum(r['size'] for r in cohort['files'] if not (DATA/'source'/r['user']/Path(r['source_member']).name).exists())
        assert shutil.disk_usage(DATA).free >= remaining+15_000_000_000
        progress('ACQUISITION_RUNNING',required_files=cohort['total_files'],completed_files=0,supplemental_attempt=args.attempt_id)
        with cf.ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(acquire,cohort,r):r for r in cohort['files']}
            for future in cf.as_completed(futures):
                try:
                    total += future.result()
                except BaseException:
                    STOP.set()
                    for pending in futures:
                        pending.cancel()
                    progress('ACQUISITION_FAILED',completed_files=done,failed_member=futures[future]['source_member'],supplemental_attempt=args.attempt_id)
                    raise
                done += 1
                if done%10 == 0 or done == cohort['total_files']:
                    progress('ACQUISITION_RUNNING',required_files=cohort['total_files'],completed_files=done,completed_bytes=total,elapsed_seconds=time.monotonic()-started,supplemental_attempt=args.attempt_id)
                    print('ACQUIRED',done,cohort['total_files'],total,flush=True)
        assert total == cohort['total_bytes']
        save(LANE/'ACQUISITION_COMPLETE.json',{'status':'COMPLETE','files':done,'bytes':total,'cohort_sha256':sha(LANE/'ENROLLMENT_MANIFEST.json'),
             'runner_sha256':sha(Path(__file__)),'transport_amendment_seal_sha256':sha(LANE/'SEGMENTED_TRANSPORT_CODE_SEAL_20261010.json'), 'elapsed_seconds':time.monotonic()-started})
        progress('ACQUISITION_COMPLETE',files=done,bytes=total)
        terminal = {'status':'COMPLETE','exit_code':0,'files':done,'bytes':total}
    except BaseException as error:
        terminal = {'status':'FAILED_PRESERVE_AND_INSPECT','exit_code':1,'error_type':type(error).__name__,'reason':str(error),'files':done,'bytes':total}
        raise
    finally:
        if 'terminal' in locals():
            save(LANE/f'ACQUISITION_SEGMENTED_TERMINAL_{args.attempt_id}.json',{**terminal,'pid':os.getpid(),'finished_local_time':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'elapsed_seconds':time.monotonic()-started})
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1);lock.close()


if __name__=='__main__':main()
