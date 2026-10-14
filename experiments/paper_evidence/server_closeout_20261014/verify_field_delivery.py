"""Validate the complete received field package and independently recount summaries."""
import csv
import hashlib
import json
import math
import tarfile
from pathlib import Path,PurePosixPath
import numpy as np

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
    with p.open() as f:return list(csv.DictReader(f))
def median(x):
    x=sorted(x);n=len(x)
    return x[n//2] if n%2 else (x[n//2-1]+x[n//2])/2
def quantile_sorted(x,q):
    pos=(len(x)-1)*q;i=math.floor(pos);j=math.ceil(pos)
    return x[i]+(x[j]-x[i])*(pos-i)

def main():
    delivery=HERE/'verified_remote'/'field_delivery';r=json.loads((delivery/'FINAL_DELIVERY.json').read_text())
    p=delivery/'verified_score_fields.tar.gz';assert sha(p)==r['package_sha256'] and p.stat().st_size==r['bytes']
    dest=delivery/'results';dest.mkdir(exist_ok=False)
    with tarfile.open(p) as t:
        for m in t.getmembers():
            name=PurePosixPath(m.name);assert m.isfile() and not name.is_absolute() and '..' not in name.parts
            target=dest.joinpath(*name.parts);target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(t.extractfile(m).read())
    out=dest/'score_field_ablation';manifest=json.loads((out/'DELIVERY_MANIFEST.json').read_text())
    assert len(manifest)==r['files'] and all(sha(dest/n)==h for n,h in manifest.items())
    assert len(list((out/'models').glob('*.joblib')))==42
    v=json.loads((out/'INDEPENDENT_VERIFICATION.json').read_text());assert v['status']=='PASS'
    rows=read(out/'USER_METRICS.csv');lookup={(x['cohort'],x['consumer'],x['user'],x['removed_group'],x['retention']):x for x in rows if x['mode']=='offline_equal_coverage'}
    checks=0;ci_checks=0
    for c in read(out/'FIELD_REMOVAL_CONTRASTS.csv'):
        users=sorted({x['user'] for x in rows if x['cohort']==c['cohort'] and x['consumer']==c['consumer']});paired=[]
        for u in users:
            a=lookup[(c['cohort'],c['consumer'],u,c['removed_group'],c['retention'])];b=lookup[(c['cohort'],c['consumer'],u,'original_full',c['retention'])]
            if a[c['metric']] and b[c['metric']]:paired.append((u,100*(float(a[c['metric']])-float(b[c['metric']]))))
        assert len(paired)==int(c['paired_users']);checks+=1
        if not paired:assert not c['median_reduction_pp'];continue
        assert abs(median([v for u,v in paired])-float(c['median_reduction_pp']))<1e-12;checks+=1
        if c['cohort']=='N80' and c['retention']=='0.3' and c['metric']=='U':
            seed=int.from_bytes(hashlib.sha256(('20261014|N80|'+'|'.join(u for u,v in paired)).encode()).digest()[:8],'little')
            x=np.array([v for u,v in paired]);ix=np.random.default_rng(seed).integers(len(x),size=(10000,len(x)))
            ordered=np.sort(x[ix],axis=1);n=len(x);draws=ordered[:,n//2] if n%2 else (ordered[:,n//2-1]+ordered[:,n//2])/2;draws.sort()
            assert abs(quantile_sorted(draws,.025)-float(c['CI95_low_pp']))<1e-10
            assert abs(quantile_sorted(draws,.975)-float(c['CI95_high_pp']))<1e-10;checks+=2;ci_checks+=1
    assert ci_checks==42
    result={'status':'PASS_COMPLETE_LOCAL_DELIVERY','package_sha256':r['package_sha256'],'contained_files_verified':len(manifest),'new_models':42,'remote_independent_checks':v['checks'],'local_summary_checks':checks,'primary_intervals_independently_recomputed':42}
    (delivery/'LOCAL_DELIVERY_VERIFICATION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
