"""Single bounded read-only official provenance lookup; no retries or messages."""
import json,hashlib,urllib.request,datetime
from pathlib import Path
HERE=Path(__file__).resolve().parent
out=HERE/'official_sources';out.mkdir(exist_ok=False)
requests={
    'commits':'https://api.github.com/repos/facebookresearch/emg2pose/commits?per_page=100',
    'releases':'https://api.github.com/repos/facebookresearch/emg2pose/releases?per_page=100',
    'issues':'https://api.github.com/repos/facebookresearch/emg2pose/issues?state=all&per_page=100',
    'tags':'https://api.github.com/repos/facebookresearch/emg2pose/tags?per_page=100',
}
receipts=[]
for name,url in requests.items():
    r={'name':name,'url':url,'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'first page only'}
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'CommonPose-provenance-audit','Accept':'application/vnd.github+json'})
        with urllib.request.urlopen(req,timeout=12) as f:
            b=f.read(2_000_001);assert len(b)<=2_000_000
            r.update(status='RETRIEVED',http_status=f.status,headers={k:f.headers.get(k) for k in ['ETag','Last-Modified','Link']},sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
        (out/(name+'.json')).write_bytes(b)
        data=json.loads(b);r['items']=len(data);r['complete_pagination']=not r['headers']['Link']
        if name=='commits':r['head_sha']=data[0]['sha'] if data else None
    except Exception as e:r.update(status='NOT_AUDITED_NETWORK_ERROR',error=str(e))
    receipts.append(r)
(HERE/'OFFICIAL_LOOKUP_RECEIPTS.json').write_text(json.dumps(receipts,indent=2)+'\n')
print(json.dumps([{k:r.get(k) for k in ['name','status','items','complete_pagination','head_sha']} for r in receipts]))
