"""Archive verified receipts and sizes without repeating expensive array hashing."""
from server_common import HERE,sha,dump
import json

rows=[]
fit=json.loads((HERE/'FACTORIAL_FIT_RECEIPT.json').read_text())
for r in fit['conditions']:
    p=HERE/'training'/(r['consumer']+'.npz')
    rows.append({'path':str(p),'bytes':p.stat().st_size,'sha256':r['training_npz_sha256'],'hash_source':'fit_receipt_independently_rehashed_by_verify_server'})
for folder in ['factorial_decisions','sensitivity_decisions','score_field_ablation/decisions']:
    for receipt in sorted((HERE/folder).rglob('*.json')):
        p=receipt.with_suffix('.npz');r=json.loads(receipt.read_text())
        rows.append({'path':str(p),'bytes':p.stat().st_size,'sha256':r['sha256'],'hash_source':'array_receipt_independently_rehashed_by_verifier'})
for p in sorted((HERE/'threshold_data').rglob('*.npz')):
    rows.append({'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'hash_source':'archival_rehash'})
dump(HERE/'RETAINED_ARRAY_INVENTORY.json',{'files':len(rows),'bytes':sum(r['bytes'] for r in rows),'inventory':rows,'not_a_new_rehash_of_all_large_arrays':True})
print(len(rows),sum(r['bytes'] for r in rows),flush=True)
