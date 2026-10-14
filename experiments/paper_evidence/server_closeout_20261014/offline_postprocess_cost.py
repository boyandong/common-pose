"""Complete bounded offline feature/reference and scoring cost phases."""
from server_common import *
from threadpoolctl import threadpool_limits

SPEC={'scope':'same_first_three_sorted_N80_records_offline_CPU_only',
    'selection':'same GPU_COST_RECEIPT selected_files; no performance selection',
    'consumers':6,'warmups_per_cell':1,'timed_repeats_per_cell':2,'threads':2,
    'feature_time_includes_measured_reference_evaluation':True,
    'scorer':'original Full/U bit7, unchanged model',
    'online_latency_verified':False,'population_cost_distribution_verified':False}

def main():
    dest=HERE/'OFFLINE_POSTPROCESS_COST.csv';assert not dest.exists()
    dump(HERE/'POSTPROCESS_COST_PRESEAL.json',{'spec':SPEC,'script_sha256':sha(__file__)})
    gpu=json.loads((HERE/'GPU_COST_RECEIPT.json').read_text())
    admission=json.loads((N80/'CACHE_ADMISSION.json').read_text())
    chosen=sorted(admission['files'],key=lambda r:(r['user'],r['source_member']))[:3]
    assert [r['source_member'] for r in chosen]==gpu['selected_files']
    assert len({r['user'] for r in chosen})==1
    raw,_=ec.load_user(chosen[0]['user']);cs=conditions()
    fit=json.loads((HERE/'FACTORIAL_FIT_RECEIPT.json').read_text());inst={r['consumer']:r for r in fit['conditions']}
    rows=[]
    with threadpool_limits(limits=2):
        for record in chosen:
            stem=Path(record['path']).stem;ix=raw['file']==stem;assert ix.any()
            d={k:v[ix] if isinstance(v,np.ndarray) and len(v)==len(ix) else v for k,v in raw.items()}
            for c in cs:
                tag=c['lane']+'__'+c['name'];m=inst[tag]['models']['U_7'];assert sha(m['path'])==m['sha256'];model=joblib.load(m['path'])
                _,x=ec.features(d,c);model.predict_proba(x[:,m['columns']])
                for repeat in range(2):
                    start=time.monotonic();_,x=ec.features(d,c);feature_s=time.monotonic()-start
                    start=time.monotonic();risk=model.predict_proba(x[:,m['columns']])[:,1];score_s=time.monotonic()-start
                    assert np.isfinite(risk).all()
                    rows.append({'file':record['source_member'],'consumer':tag,'repeat':repeat,'input_blocks':len(x),'feature_and_reference_seconds':feature_s,'score_seconds':score_s,'scorer_sha256':m['sha256'],'scope':'offline_feature_reference_and_scoring_not_causal_latency'})
    assert len(rows)==36;table(dest,rows)
    dump(HERE/'POSTPROCESS_COST_RECEIPT.json',{'status':'COMPLETE','rows':36,'csv_sha256':sha(dest),'spec':SPEC})

if __name__=='__main__':main()
