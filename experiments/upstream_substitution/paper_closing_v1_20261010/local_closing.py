"""Recompute post-V1 closing tables/figures from hash-identified result inputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = HERE.parent / 'paper_supplement_v1_20261009'
METHODS = ['class_empirical', 'margin', 'entropy', 'boundary_distance', 'full', 'no_tta', 'class_model']
METRICS = {'U': 'ordinary_risk', 'B': 'fixed_common_risk'}
INPUTS = [
    'comparative_analysis/RISK_COVERAGE_ROWS.csv', 'comparative_analysis/PAIRED_EFFECTS.csv',
    'comparative_analysis/CLASSWISE_30_ROWS.csv', 'comparative_analysis/DEPLOYMENT_30_ROWS.csv',
    'comparative_analysis/SUMMARY.json', 'comparative_analysis/REPRODUCTION_ADMISSION.json',
    'comparative_analysis/TTA_COST.json', 'existing_record_analysis/DEPLOYMENT_USER_ROWS.csv',
    'existing_record_analysis/CLASSWISE_ROWS.csv', 'SUPPLEMENT_SPEC.md',
]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(4 << 20), b''):
            h.update(block)
    return h.hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')


def table(path, rows):
    pd.DataFrame(rows).to_csv(path, index=False, encoding='utf-8-sig', float_format='%.17g')


def stats(values, expected):
    a = np.asarray(values, dtype=float)
    a = a[np.isfinite(a)]
    s = {'n': len(a), 'n_missing': expected - len(a)}
    if not len(a):
        return {**s, 'median': None, 'ci95': None, 'positive_users': 0}
    rng = np.random.default_rng(20261009)
    boot = np.median(a[rng.integers(0, len(a), (20000, len(a)))], axis=1)
    return {**s, 'median': float(np.median(a)), 'ci95': np.quantile(boot, [.025, .975]).tolist(),
            'q25': float(np.quantile(a, .25)), 'q75': float(np.quantile(a, .75)),
            'min': float(a.min()), 'max': float(a.max()), 'positive_users': int(np.sum(a > 0))}


def read_csv(path):
    return pd.read_csv(path, dtype={'user': str, 'common_classes': str})


def freeze_inputs(source):
    transfer = json.loads((source / 'RESULT_TRANSFER_MANIFEST.json').read_text())['files']
    original = json.loads((source / 'existing_record_analysis/ARTIFACT_MANIFEST.json').read_text())
    files = {}
    for name in INPUTS:
        value = digest(source / name)
        if name in transfer and value != transfer[name]:
            raise ValueError('Original transfer seal differs: ' + name)
        files[name] = value
    # Original-record results have their own manifest; preserve it as an input.
    files['existing_record_analysis/ARTIFACT_MANIFEST.json'] = digest(source / 'existing_record_analysis/ARTIFACT_MANIFEST.json')
    dump(HERE / 'INPUT_MANIFEST.json', {'source_lane': source.name, 'files': files,
         'source_archive': {'filename': 'paper_supplement_results_20261010.tar.gz',
         'sha256': '0eb0a5bff49fc92efbfeaf896255db719e5453445b5125cf86a13c2105979168'},
         'audit_snapshot_sha256': digest(HERE / 'AUDIT_SNAPSHOT.json'),
         'closing_spec_sha256': digest(HERE / 'CLOSING_SPEC.md'),
         'original_record_manifest': original})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, default=SOURCE)
    ap.add_argument('--output', type=Path, default=HERE / 'results')
    ap.add_argument('--freeze-inputs', action='store_true')
    args = ap.parse_args()
    if args.freeze_inputs:
        if (HERE / 'INPUT_MANIFEST.json').exists():
            raise ValueError('Refuse overwrite input seal')
        freeze_inputs(args.source)
    manifest = json.loads((HERE / 'INPUT_MANIFEST.json').read_text())
    for name, expected in manifest['files'].items():
        if digest(args.source / name) != expected:
            raise ValueError('Input hash differs: ' + name)
    if digest(HERE / 'AUDIT_SNAPSHOT.json') != manifest['audit_snapshot_sha256']:
        raise ValueError('Audit snapshot hash differs')
    if digest(HERE / 'CLOSING_SPEC.md') != manifest['closing_spec_sha256']:
        raise ValueError('Closing protocol differs')
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError('Refuse overwrite a nonempty output directory')
    args.output.mkdir(parents=True, exist_ok=True)
    out = args.output
    df = read_csv(args.source / INPUTS[0])
    if df.duplicated(['split', 'contract', 'user', 'method', 'nominal_coverage']).any():
        raise ValueError('Duplicate curve key')
    support, comparable, interval_rows, auc_rows, effects, summaries = [], [], [], [], [], {}
    counts_by_split = {'DEV': 19, 'FINAL': 20}
    for split, expected in counts_by_split.items():
        fig, axes = plt.subplots(2, 2, figsize=(12, 7), gridspec_kw={'height_ratios': [3, 1]}, sharex='col')
        fig_fixed, ax_fixed = plt.subplots(1, 2, figsize=(12, 4))
        for col, (contract, metric) in enumerate(METRICS.items()):
            part = df[(df['split'] == split) & (df['contract'] == contract)]
            users = sorted(part['user'].unique())
            if len(users) != expected or set(part['method']) != set(METHODS):
                raise ValueError('Cohort/method inventory differs')
            wide = part.pivot(index=['nominal_coverage', 'user'], columns='method', values=metric)[METHODS]
            interval = wide.loc[wide.index.get_level_values(0) >= .3]
            complete = interval.notna().all(axis=1).groupby(level='user').all()
            common_users = sorted(complete[complete].index.tolist())
            omitted = sorted(set(users) - set(common_users))
            for cov, frame in wide.groupby(level='nominal_coverage'):
                good = frame.notna().all(axis=1)
                shared = frame[good]
                names = sorted(shared.index.get_level_values('user').tolist())
                support.append({'split': split, 'contract': contract, 'coverage': cov,
                    'metric': metric, 'n_all_methods_common': len(names), 'common_users': '|'.join(names),
                    'omitted_users': '|'.join(sorted(set(users)-set(names))),
                    **{'n_defined_'+m: int(frame[m].notna().sum()) for m in METHODS}})
                for m in METHODS:
                    risk = float(shared[m].median()) if len(shared) else np.nan
                    comparable.append({'split': split, 'contract': contract, 'method': m,
                        'coverage': cov, 'metric': metric, 'n_users': len(names), 'median_risk': risk})
                    if cov >= .3:
                        fixed = frame[frame.index.get_level_values('user').isin(common_users)]
                        interval_rows.append({'split': split, 'contract': contract, 'method': m,
                            'coverage': cov, 'metric': metric, 'n_users': len(fixed),
                            'median_risk': float(fixed[m].median()) if len(fixed) else np.nan})
            ax, n_ax, fixed_ax = axes[0, col], axes[1, col], ax_fixed[col]
            for m in METHODS:
                points = [r for r in comparable if r['split'] == split and r['contract'] == contract and r['method'] == m]
                fixed_points = [r for r in interval_rows if r['split'] == split and r['contract'] == contract and r['method'] == m]
                ax.plot([r['coverage'] for r in points], [r['median_risk'] for r in points], label=m, lw=2 if m=='full' else 1)
                fixed_ax.plot([r['coverage'] for r in fixed_points], [r['median_risk'] for r in fixed_points], label=m, lw=2 if m=='full' else 1)
            nrows = [r for r in support if r['split'] == split and r['contract'] == contract]
            n_ax.step([r['coverage'] for r in nrows], [r['n_all_methods_common'] for r in nrows], where='mid')
            n_ax.set(xlabel='Accepted coverage', ylabel='Shared users', ylim=(-.5, expected+1))
            ax.set(title=f'{split} {contract}: pointwise shared users', ylabel='Median target Flip risk')
            fixed_ax.set(title=f'{split} {contract}: fixed {len(common_users)}/{expected} users', xlabel='Accepted coverage', ylabel='Median target Flip risk')
            ax.legend(fontsize=7); fixed_ax.legend(fontsize=7)
            user_areas = {}
            for (u, m), group in part.groupby(['user', 'method']):
                g = group[group['nominal_coverage'] >= .3].sort_values('nominal_coverage')
                if len(g) != 71 or not np.allclose(g['nominal_coverage'], np.arange(30, 101)/100):
                    raise ValueError('Area grid differs')
                value = float(np.trapz(g[metric].to_numpy(), g['nominal_coverage'].to_numpy())) if u in common_users else np.nan
                user_areas[u, m] = value
                auc_rows.append({'split': split, 'contract': contract, 'user': u, 'method': m,
                    'metric': metric, 'area_30_100': value, 'normalized_area_30_100': value/.7,
                    'included_fixed_interval_users': u in common_users})
            for m in METHODS:
                if m == 'full': continue
                vals = []
                for u in users:
                    value = user_areas[u, m] - user_areas[u, 'full']
                    vals.append(value)
                    effects.append({'split': split, 'contract': contract, 'user': u,
                        'comparison': 'full_vs_'+m, 'area_reduction': value, 'normalized_area_reduction': value/.7})
                summaries[split+'_'+contract+'__full_vs_'+m] = stats(vals, expected)
            summaries[split+'_'+contract+'__interval_population'] = {'users': common_users, 'excluded_users': omitted,
                'n': len(common_users), 'interpretation': 'fixed all-method/all-coverage intersection on 30%-100%'}
        fig.tight_layout(); fig_fixed.tight_layout()
        for ext in ['png', 'pdf']:
            fig.savefig(out / (split+'_COMPARABLE_DENSE.'+ext), dpi=200)
            fig_fixed.savefig(out / (split+'_FIXED_USERS_30_100.'+ext), dpi=200)
        plt.close(fig); plt.close(fig_fixed)
    table(out/'CURVE_USER_SUPPORT.csv', support)
    table(out/'POINTWISE_COMPARABLE_CURVES.csv', comparable)
    table(out/'FIXED_USERS_30_100_CURVES.csv', interval_rows)
    table(out/'TARGET_AREA_USER_ROWS.csv', auc_rows)
    table(out/'TARGET_AREA_PAIRED_EFFECTS.csv', effects)
    dump(out/'TARGET_AREA_SUMMARY.json', {'status': 'LATE_DELIVERED_SECONDARY_SUPPLEMENT',
        'integration': 'per-user trapezoids on 0.30..1.00 in 0.01 steps; area and area/0.70 both reported',
        'bootstrap_user_draws': 20000, 'bootstrap_seed': 20261009, 'summary': summaries})
    classes = read_csv(args.source/'comparative_analysis/CLASSWISE_30_ROWS.csv')
    reference = classes[classes['grouping'] == 'reference_class'].copy()
    reference['no_service'] = reference['accepted_support'] == 0
    reference['supported_at_30'] = reference['accepted_support'] >= 30
    reference['baseline_supported'] = reference['baseline_support'] >= 30
    table(out/'CLASSWISE_30_REFERENCE_DETAIL.csv', reference.to_dict('records'))
    class_summary = reference.groupby(['split','contract','method','class']).agg(
        users=('user','nunique'), baseline_supported_users=('baseline_supported','sum'),
        supported_users=('supported_at_30','sum'), no_service_users=('no_service','sum'),
        median_class_coverage=('class_coverage','median'), median_observed_risk=('accepted_risk','median')).reset_index()
    table(out/'CLASS_SUPPORT_30_SUMMARY.csv', class_summary.to_dict('records'))
    for name, target in [('PAIRED_EFFECTS.csv','USER_EFFECTS_30.csv'), ('DEPLOYMENT_30_ROWS.csv','RECONSTRUCTED_DEPLOYMENT_30.csv')]:
        shutil.copyfile(args.source/'comparative_analysis'/name, out/target)
    for name in ['DEPLOYMENT_USER_ROWS.csv','CLASSWISE_ROWS.csv']:
        shutil.copyfile(args.source/'existing_record_analysis'/name, out/('ORIGINAL_'+name))
    admission = json.loads((args.source/'comparative_analysis/REPRODUCTION_ADMISSION.json').read_text())
    audit = json.loads((HERE/'AUDIT_SNAPSHOT.json').read_text())
    drift = max(abs(r[k]) for r in admission['rows'] for k in ['ordinary_drift','dynamic_balanced_drift'])
    dump(out/'REPRODUCTION_LINEAGE.json', {'FINAL_frozen_model': {'max_aggregate_risk_drift': drift,
        'n_endpoints': len(admission['rows']), 'per_block_identity': 'UNAVAILABLE'},
        'DEV_refit_and_tie_changes': audit['dev_refit_and_tie_drift_vs_historical_at_30'],
        'attribution': 'refit/environment/features/ties cannot be separately attributed from existing records',
        'original_confirmation': 'historical final_joint_confirmation_v1',
        'reconstructed_comparisons': 'post-V1 20261009 supplement on already examined users',
        'closing': 'post-V1 20261010 reporting/robustness; not new confirmation'})
    dump(out/'RUN_MANIFEST.json', {'status': 'LOCAL_CLOSING_COMPLETE', 'input_manifest_sha256': digest(HERE/'INPUT_MANIFEST.json'),
        'code_sha256': digest(__file__), 'python': platform.python_version(),
        'libraries': {'numpy': np.__version__, 'pandas': pd.__version__, 'matplotlib': matplotlib.__version__},
        'files': {p.name: digest(p) for p in sorted(out.iterdir()) if p.is_file()}})
    print(json.dumps({'status': 'LOCAL_CLOSING_COMPLETE', 'area_user_rows': len(auc_rows),
        'area_effect_rows': len(effects), 'curve_support_rows': len(support), 'output': str(out)}))


if __name__ == '__main__':
    main()
