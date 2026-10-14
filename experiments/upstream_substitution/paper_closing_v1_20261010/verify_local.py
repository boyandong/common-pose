"""Independent stdlib verification of support, integration, seals and provenance."""
import csv
import argparse
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent/'paper_supplement_v1_20261009'
OUT = HERE/'results'
METHODS = {'class_empirical','margin','entropy','boundary_distance','full','no_tta','class_model'}


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(4 << 20), b''): h.update(b)
    return h.hexdigest()


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))


def close(a, b):
    assert math.isclose(float(a), float(b), abs_tol=2e-12), (a, b)


def main():
    global OUT
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',type=Path,default=OUT)
    ap.add_argument('--receipt',type=Path,default=HERE/'LOCAL_VERIFICATION.json')
    args=ap.parse_args()
    OUT=args.output
    manifest = json.loads((HERE/'INPUT_MANIFEST.json').read_text())
    for name, value in manifest['files'].items(): assert sha(SOURCE/name) == value, name
    transfer = json.loads((SOURCE/'RESULT_TRANSFER_MANIFEST.json').read_text())['files']
    for name, value in transfer.items(): assert sha(SOURCE/name) == value, name
    original = manifest['original_record_manifest']['files']
    for name in ['CLASSWISE_ROWS.csv','DEPLOYMENT_USER_ROWS.csv']:
        assert sha(SOURCE/'existing_record_analysis'/name) == original[name]['sha256']
        assert sha(OUT/('ORIGINAL_'+name)) == original[name]['sha256']
    run = json.loads((OUT/'RUN_MANIFEST.json').read_text())
    assert sha(HERE/'local_closing.py') == run['code_sha256']
    for name, value in run['files'].items(): assert sha(OUT/name) == value, name
    raw = rows(SOURCE/'comparative_analysis/RISK_COVERAGE_ROWS.csv')
    risks, populations, by_user = {}, defaultdict(set), defaultdict(list)
    for r in raw:
        split, c, u, m, cov = r['split'], r['contract'], r['user'], r['method'], float(r['nominal_coverage'])
        metric = 'ordinary_risk' if c == 'U' else 'fixed_common_risk'
        risks[split,c,cov,u,m] = float(r[metric]) if r[metric] else None
        populations[split,c].add(u)
        if cov >= .3: by_user[split,c,u,m].append((cov, risks[split,c,cov,u,m]))
    common = {}
    for r in rows(OUT/'CURVE_USER_SUPPORT.csv'):
        split,c,cov = r['split'],r['contract'],float(r['coverage'])
        names = sorted(u for u in populations[split,c] if all(risks[split,c,cov,u,m] is not None for m in METHODS))
        assert '|'.join(names) == r['common_users']
        assert int(r['n_all_methods_common']) == len(names)
        for m in METHODS:
            assert int(r['n_defined_'+m]) == sum(risks[split,c,cov,u,m] is not None for u in populations[split,c])
        common[split,c,cov] = names
    for r in rows(OUT/'POINTWISE_COMPARABLE_CURVES.csv'):
        key = r['split'],r['contract'],float(r['coverage'])
        names = common[key]
        assert int(r['n_users']) == len(names)
        if not names: assert r['median_risk'] == ''
        else: close(r['median_risk'], statistics.median(risks[*key,u,r['method']] for u in names))
    areas = {}
    for r in rows(OUT/'TARGET_AREA_USER_ROWS.csv'):
        key = r['split'],r['contract'],r['user'],r['method']
        points = sorted(by_user[key])
        assert len(points) == 71
        if all(v is not None for _,v in points):
            a = sum((x2-x1)*(y1+y2)/2 for (x1,y1),(x2,y2) in zip(points,points[1:]))
            close(r['area_30_100'], a); close(r['normalized_area_30_100'], a/.7)
            areas[key] = a
        else:
            assert r['area_30_100'] == ''
            areas[key] = None
    summary = json.loads((OUT/'TARGET_AREA_SUMMARY.json').read_text())['summary']
    audit = json.loads((HERE/'AUDIT_SNAPSHOT.json').read_text())['secondary_auc_30_100']
    effects = defaultdict(list)
    for r in rows(OUT/'TARGET_AREA_PAIRED_EFFECTS.csv'):
        split,c,u,comp = r['split'],r['contract'],r['user'],r['comparison']
        baseline = comp.removeprefix('full_vs_')
        a,b = areas[split,c,u,baseline], areas[split,c,u,'full']
        if a is None or b is None: assert r['area_reduction'] == ''
        else:
            close(r['area_reduction'],a-b)
            effects[split+'_'+c+'__'+comp].append(a-b)
    checked = 0
    for key, values in effects.items():
        s = summary[key]
        close(s['median'],statistics.median(values)); assert s['n'] == len(values)
        assert s['positive_users'] == sum(v>0 for v in values)
        cohort, comparison = key.split('__')
        split,c = cohort.split('_')
        old = audit[c+'_'+split][comparison.removeprefix('full_vs_')]
        close(s['median'],old['median_unnormalized_auc_reduction'])
        assert s['positive_users'] == old['positive_users']
        checked += 1
    result = {'status':'PASS','transfer_hashes':len(transfer),'support_points':len(common),
        'area_users_methods':len(areas),'area_summaries_vs_prior_independent_audit':checked,
        'FINAL_B_1pct_common_users':len(common['FINAL','B',.01]),
        'scope':'independent input/output seals, exact user sets, trapezoid sums, effect signs/medians; not neural inference'}
    args.receipt.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__': main()
