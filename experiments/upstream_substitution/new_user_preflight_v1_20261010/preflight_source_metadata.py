"""Candidate metadata/index consistency and bounded HDF5 metadata-only probes.

No cohort selection and no signal/pose arrays, consumer predictions or Flips.
All candidate records are checked against the sealed official metadata/index.
One filename per available hand/user is probed for schema; this does NOT certify
every member's complete byte hash or sample validity.
"""
import argparse
import concurrent.futures
import csv
import hashlib
import io
import json
from pathlib import Path
import time
import urllib.request
import h5py

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
FINGERS=HERE.parents[3]
OFFICIAL=FINGERS/'emg2pose_handstate'
META=OFFICIAL/'data/official/emg2pose_dataset_mini/metadata.csv'
INDEX=OFFICIAL/'data/priority_pose_subset/raw/tar_index.jsonl'
URL='https://fb-ctrl-oss.s3.amazonaws.com/emg2pose/emg2pose_dataset.tar'
ETAG='"62df27ac9a04800702061bac0ac1af32-6897"'
ARCHIVE_BYTES=462824048640

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

class RangeMember(io.RawIOBase):
    def __init__(self,offset,size):
        super().__init__();self.offset=offset;self.size=size;self.pos=0;self.cache={};self.bytes_read=0;self.requests=0
    def readable(self):return True
    def seekable(self):return True
    def tell(self):return self.pos
    def seek(self,offset,whence=0):
        self.pos=offset if whence==0 else self.pos+offset if whence==1 else self.size+offset
        if self.pos<0:raise ValueError('negative seek')
        return self.pos
    def readinto(self,b):
        data=self.read(len(b));b[:len(data)]=data;return len(data)
    def read(self,n=-1):
        if n<0:raise ValueError('refuse unbounded archive member read')
        if self.pos>=self.size:return b''
        n=min(n,self.size-self.pos);output=[];end=self.pos+n
        while self.pos<end:
            page=self.pos//32768;start=page*32768
            if page not in self.cache:
                count=min(32768,self.size-start)
                if self.bytes_read+count>2_097_152:raise ValueError('metadata probe exceeded 2 MiB cap')
                first=self.offset+start;last=first+count-1
                request=urllib.request.Request(URL,headers={'Range':f'bytes={first}-{last}','If-Match':ETAG})
                with urllib.request.urlopen(request,timeout=20) as response:
                    assert response.status==206
                    assert response.headers.get('Content-Range')==f'bytes {first}-{last}/{ARCHIVE_BYTES}'
                    assert response.headers.get('ETag')==ETAG
                    chunk=response.read(count+1);assert len(chunk)==count
                self.cache[page]=chunk;self.bytes_read+=count;self.requests+=1
            count=min(end-self.pos,32768-(self.pos-start))
            output.append(self.cache[page][self.pos-start:self.pos-start+count]);self.pos+=count
        return b''.join(output)

def probe(row):
    began=time.monotonic();reader=RangeMember(row['archive_data_offset'],row['size'])
    try:
        with h5py.File(reader,'r') as h:
            ts=h['emg2pose/timeseries']
            fields=ts.dtype.fields
            assert fields is not None and {'emg','joint_angles','time'}<=set(fields)
            assert len(ts.shape)==1 and ts.shape[0]>1870
            assert fields['emg'][0].subdtype[1]==(16,)
            assert fields['joint_angles'][0].subdtype[1]==(20,)
            record={'status':'METADATA_SCHEMA_PASS','user':row['user'],'side':row['side'],
                    'source_member':row['source_member'],'rows':int(ts.shape[0]),
                    'emg_shape':[int(ts.shape[0]),16],'joint_angle_shape':[int(ts.shape[0]),20],
                    'time_dtype':str(fields['time'][0]),'metadata_bytes_fetched':reader.bytes_read,
                    'range_requests':reader.requests,'elapsed_seconds':time.monotonic()-began,
                    'no_timeseries_array_reads':True}
    except Exception as e:
        record={'status':'PROBE_FAILED','user':row['user'],'side':row['side'],
                'source_member':row['source_member'],'error':type(e).__name__,'detail':str(e),
                'metadata_bytes_fetched':reader.bytes_read,'range_requests':reader.requests,
                'elapsed_seconds':time.monotonic()-began}
    return record

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=4)
    ap.add_argument('--manifest-only',action='store_true');ap.add_argument('--probe-limit',type=int)
    ap.add_argument('--retry-transport-failures',action='store_true',
                    help='One retry of the same members that failed solely with SSL transport EOF')
    args=ap.parse_args()
    exposure=json.loads((HERE/'HISTORICAL_ACCESS_ADJUDICATION.json').read_text())
    eligible=set(exposure['candidate_users']);assert len(eligible)==127
    original=json.loads((BASE/'paper_closing_v1_20261010/prospective_inventory/AUDIT.json').read_text())
    assert sha(META)==original['metadata_sha256'] and sha(INDEX)==original['tar_index_sha256']
    prior=json.loads((BASE/'final_untouched_cohort_audit_v1/ELIGIBLE_USER_REGISTRY.json').read_text())
    sessions={r['user_id']:r['preflight_session_id'] for r in prior['users'] if r['user_id'] in eligible}
    with META.open(encoding='utf-8-sig',newline='') as f:
        records=[r for r in csv.DictReader(f) if r['user'] in eligible and r['session']==sessions[r['user']]]
    wanted={'emg2pose_data/'+r['filename']+'.hdf5':r for r in records};assert len(wanted)==len(records)
    index={}
    with INDEX.open(encoding='utf-8') as f:
        for line in f:
            r=json.loads(line)
            if r['name'] in wanted:index[r['name']]=r
    assert set(index)==set(wanted)
    files=[]
    for name,r in sorted(wanted.items()):
        entry=index[name];assert entry['typeflag']=='0' and entry['size']>0
        header=int(entry['offset']);offset=header+512;size=int(entry['size'])
        assert header%512==0 and offset+size<=ARCHIVE_BYTES
        assert r['side'] in ['left','right'] and float(r['end'])>float(r['start'])
        files.append({'user':r['user'],'session':r['session'],'side':r['side'],
                      'source_member':name,'archive_header_offset':header,'archive_data_offset':offset,
                      'size':size,'duration_seconds':float(r['end'])-float(r['start']),
                      'official_split':r['split'],'stage':r['stage']})
    assert {r['user'] for r in files}==eligible
    for user in eligible:
        rr=[r for r in files if r['user']==user]
        old=next(r for r in prior['users'] if r['user_id']==user)
        assert sum(r['size'] for r in rr)==old['preflight_session_archive_bytes']
        assert len(rr)==old['preflight_session_recording_count']
    manifest={'status':'CANDIDATE_SOURCE_MANIFEST_ONLY_NOT_ENROLLMENT','candidate_users':len(eligible),
              'records':len(files),'bytes':sum(r['size'] for r in files),'source_url':URL,
              'etag':ETAG,'archive_bytes':ARCHIVE_BYTES,'metadata_sha256':sha(META),'tar_index_sha256':sha(INDEX),
              'exposure_adjudication_sha256':sha(HERE/'HISTORICAL_ACCESS_ADJUDICATION.json'),
              'files':files,'no_enrollment_selection':True}
    (HERE/'CANDIDATE_SOURCE_PREFLIGHT_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    chosen=[]
    for user in sorted(eligible):
        for side in ['left','right']:
            rr=[r for r in files if r['user']==user and r['side']==side]
            assert rr,(user,side)
            chosen.append(min(rr,key=lambda r:r['source_member']))
    if args.manifest_only:
        print(json.dumps({k:v for k,v in manifest.items() if k in ['status','candidate_users','records','bytes']}));return
    if args.probe_limit:chosen=chosen[:args.probe_limit]
    original_receipt=None
    if args.retry_transport_failures:
        assert not args.probe_limit
        original_receipt=json.loads((HERE/'SOURCE_METADATA_PREFLIGHT.json').read_text())
        assert original_receipt['probe_records']==254
        bad=original_receipt['failed_probes']
        assert bad and all(r['error']=='URLError' and 'SSL: UNEXPECTED_EOF_WHILE_READING' in r['detail'] for r in bad)
        members={r['source_member'] for r in bad}
        chosen=[r for r in chosen if r['source_member'] in members]
        assert len(chosen)==len(bad)
    began=time.monotonic();results=[]
    # h5py serializes operations with a process-wide lock; separate processes
    # let bounded metadata network I/O overlap without any model/data inference.
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        for r in pool.map(probe,chosen):
            results.append(r)
            print('METADATA_PROBE',len(results),len(chosen),r['user'],r['side'],r['status'],flush=True)
            progress_name='SOURCE_METADATA_RETRY_PROGRESS.json' if args.retry_transport_failures else 'SOURCE_METADATA_PROGRESS.json'
            (HERE/progress_name).write_text(json.dumps({'status':'RUNNING',
                'completed':len(results),'planned':len(chosen),'failed':sum(x['status']!='METADATA_SCHEMA_PASS' for x in results),
                'updated_at_epoch':time.time(),'no_timeseries_array_reads':True})+'\n')
    receipt={'status':'SAMPLED_METADATA_PREFLIGHT_PASS' if all(r['status']=='METADATA_SCHEMA_PASS' for r in results) else 'SAMPLED_METADATA_PREFLIGHT_INCOMPLETE',
             'probe_records':len(results),'intended_full_hand_sample_records':254,
             'all_candidate_hand_samples_checked':len(results)==254,'candidate_users':127,
             'failed_probes':[r for r in results if r['status']!='METADATA_SCHEMA_PASS'],
             'results':results,'bytes_fetched':sum(r['metadata_bytes_fetched'] for r in results),
             'elapsed_seconds':time.monotonic()-began,'code_sha256':sha(Path(__file__)),
             'scope':'one lexicographic source filename per available hand/user; HDF5 dtype and shape metadata only; no complete member hashes, timestamps, sample validity, predictions or outcomes'}
    name='SOURCE_METADATA_TRANSPORT_RETRY.json' if args.retry_transport_failures else 'SOURCE_METADATA_PROBE_LIMITED.json' if args.probe_limit else 'SOURCE_METADATA_PREFLIGHT.json'
    (HERE/name).write_text(json.dumps(receipt,indent=2)+'\n')
    if args.retry_transport_failures:
        assert not (HERE/'SOURCE_METADATA_PREFLIGHT_COMPLETE.json').exists()
        merged={r['source_member']:r for r in original_receipt['results']}
        merged.update({r['source_member']:r for r in results})
        final={**original_receipt,'results':list(merged.values()),
               'failed_probes':[r for r in merged.values() if r['status']!='METADATA_SCHEMA_PASS'],
               'status':'SAMPLED_METADATA_PREFLIGHT_PASS' if all(r['status']=='METADATA_SCHEMA_PASS' for r in merged.values()) else 'SAMPLED_METADATA_PREFLIGHT_INCOMPLETE',
               'transport_retry_only':True,'same_source_members':True,'maximum_transport_attempts_per_failed_member':2,
               'initial_receipt_sha256':sha(HERE/'SOURCE_METADATA_PREFLIGHT.json'),
               'retry_receipt_sha256':sha(HERE/name),'retry_code_sha256':sha(Path(__file__))}
        (HERE/'SOURCE_METADATA_PREFLIGHT_COMPLETE.json').write_text(json.dumps(final,indent=2)+'\n')
    (HERE/progress_name).write_text(json.dumps({'status':'COMPLETE','completed':len(chosen),
        'planned':len(chosen),'failed':len(receipt['failed_probes']),'updated_at_epoch':time.time(),
        'no_timeseries_array_reads':True})+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k not in ['results','failed_probes']}),flush=True)

if __name__=='__main__':main()
