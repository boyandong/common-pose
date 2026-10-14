"""Report verified frozen outcomes without selecting methods, users or seeds."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics

LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[2]
ARCHIVE = Path('D:/CommonPose_confirmation_N80_20261010/results')
OLD = LANE.parent / 'paper_closing_v1_20261010/manuscript_closing/MANUSCRIPT_CLOSING.md'
OLD_SHA = 'ed07a402de253bc26c17faaae6cc0f63d8729535e3ab742eb5a9c98140102f99'
PREREQUISITES = ['PIPELINE_EXECUTION_COMPLETE.json', 'OFFHOST_BACKUP_VERIFICATION.json',
                 'INDEPENDENT_RESULT_VERIFICATION.json']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def number(value):
    return None if value in ('', None) else float(value)


def display(value, scale=1):
    return 'missing' if value is None else f'{value * scale:.3f}'


def median(values):
    valid = [v for v in values if v is not None]
    return statistics.median(valid) if valid else None


def probability(value):
    return 'missing' if value is None else f'{value:.8g}'


def table(headers, rows):
    lines = ['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |']
    lines.extend('| ' + ' | '.join(str(v) for v in row) + ' |' for row in rows)
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check-ready', action='store_true')
    args = ap.parse_args()
    missing = [name for name in PREREQUISITES if not (LANE / name).is_file()]
    if args.check_ready:
        print(json.dumps({'prerequisite_receipts_present': not missing, 'missing': missing,
                          'new_outcome_values_read': False, 'report_generated': False}))
        return
    assert not missing, 'Verified experiment and complete backup required: ' + ', '.join(missing)
    complete = read(LANE / 'PIPELINE_EXECUTION_COMPLETE.json')
    independent = read(LANE / 'INDEPENDENT_RESULT_VERIFICATION.json')
    backup = read(LANE / 'OFFHOST_BACKUP_VERIFICATION.json')
    assert complete['status'] == 'FROZEN_EXPERIMENT_INDEPENDENTLY_VERIFIED_AND_BACKED_UP'
    assert independent['status'] == backup['status'] == 'PASS'
    assert complete['independent_verification_sha256'] == sha(LANE / 'INDEPENDENT_RESULT_VERIFICATION.json')
    assert complete['backup_verification_sha256'] == sha(LANE / 'OFFHOST_BACKUP_VERIFICATION.json')
    assert sha(OLD) == OLD_SHA, 'Historical manuscript changed'
    provenance = {}

    def checked(name):
        p = ARCHIVE / name
        entries = read(LANE / 'OFFHOST_BACKUP_MANIFEST.json')['files']
        matches = [r for r in entries if r['local_relative'] == 'results/' + name]
        assert len(matches) == 1 and p.stat().st_size == matches[0]['bytes']
        assert sha(p) == matches[0]['sha256'], name
        provenance[name] = sha(p)
        return p

    def rows(name):
        with checked(name).open(encoding='utf-8-sig', newline='') as f:
            return list(csv.DictReader(f))

    result = read(checked('PRIMARY_RESULT.json'))
    assert sha(ARCHIVE / 'PRIMARY_RESULT.json') == independent['result_sha256']
    assert result['joint_decision'] == independent['joint_decision'] == complete['joint_decision']
    assert result['alpha_per_endpoint'] == .025 and result['enrolled_users'] == 80
    cohort = read(checked('ENROLLMENT_MANIFEST.json'))
    assert result['source_seals']['cohort'] == sha(ARCHIVE / 'ENROLLMENT_MANIFEST.json')
    assert result['source_seals']['protocol'] == sha(checked('SCIENTIFIC_SPEC.md'))
    qualification = read(checked('SOURCE_QUALIFICATION.json'))
    assert qualification['status'] == 'PASS' and not qualification['bad_users']
    assert set(qualification['valid_block_totals']) == set(cohort['enrolled_users'])
    assert backup['source_files'] == cohort['total_files'] == 2768
    assert backup['source_bytes'] == cohort['total_bytes'] == 50213536592
    primary = rows('PRIMARY_USER_EFFECTS.csv')
    risks = rows('RISK_COVERAGE_ROWS.csv')
    deploy = rows('DEPLOYMENT_ROWS.csv')
    for name in ['CLASSWISE_ROWS.csv', 'SEED_RISK_ROWS.csv', 'SEED_EFFECTS.csv',
                 'WITHIN_PREDICTED_CLASS_ROWS.csv', 'CANONICAL_SUPPORT_ROWS.csv']:
        checked(name)
    assert len(primary) == 160 and len(risks) == 7840 and len(deploy) == 1120
    pi = {(r['contract'], r['user']): r for r in primary}
    assert len(pi) == 160
    for c in ['U', 'B']:
        assert {r['user'] for r in primary if r['contract'] == c} == set(cohort['enrolled_users'])
    parts = ['# CommonPose prospective N80 strong-baseline confirmation',
             'This separate confirmation followed the prospectively frozen protocol. '
             'Old FINAL results informed the design and remain supplementary evidence. '
             'The historical manuscript is retained at Git '
             '`1fc75512698c92d4bd11cf52e660c8814b1ac127`.',
             'Flip measures disagreement between one frozen consumer on measured and '
             'predicted pose. It is not independently labelled gesture accuracy. '
             'Checkpoint-specific upstream training membership is unresolved. The '
             'historical exposure audit covers saved local provenance, not all possible prior access.',
             '## Enrollment, source flow and verification',
             f"All 80 frozen enrolled users passed structural qualification. All {cohort['total_files']} "
             f"sources ({cohort['total_bytes']} bytes) were downloaded through the local computer, "
             'transferred and checked on the server, and retained locally. Source/cache/dependency '
             'backup verification passed. Transfer hashes establish version and copy consistency; '
             'official per-member ground-truth hashes were unavailable.',
             '## Prespecified primary results',
             'Canonical seed 20261009; 30% rank acceptance, rounded up within each user. '
             'U compares full with boundary_distance ordinary Flip risk; B compares full with '
             'class_model equal-weight risk on the seven-method support intersection fixed '
             'before effects. Positive effects are comparator minus full. Each two-sided exact '
             'sign test uses alpha .025; both must succeed for a positive joint conclusion. '
             'The 20,000-draw paired-user 95% bootstrap intervals are descriptive, not simultaneous.',
             f"Joint decision: **{result['joint_decision']}**."]
    summary = []
    for c in ['U', 'B']:
        s = result['primary'][c]
        rr = [r for r in primary if r['contract'] == c]
        ci = s['descriptive_ci95']
        summary.append([c, s['enrolled'], s['complete_pairs'], s['missing_pairs'],
                        f"{s['positive']}/{s['zero']}/{s['negative']}", s['n_nonzero'],
                        display(median([number(r['baseline_risk']) for r in rr]), 100),
                        display(median([number(r['full_risk']) for r in rr]), 100),
                        display(s['median'], 100),
                        'missing' if ci is None else f'[{ci[0]*100:.3f}, {ci[1]*100:.3f}]',
                        probability(s['sign_p_two_sided']), probability(s['conditional_subset_sign_p']),
                        s['formal_decision']])
    parts.append(table(['Endpoint', 'Enrolled', 'Complete', 'Missing', '+/0/-', 'Nonzero',
                        'Baseline median risk %', 'Full median risk %', 'Effect median pp',
                        'Descriptive CI pp', 'Formal p', 'Conditional subset p', 'Decision'], summary))
    parts.append('Zero effects remain in descriptive medians and leave only the sign-test '
                 'denominator. Missing effects are not zero or imputed. Any missing primary pair '
                 'makes full-cohort confirmation EVIDENCE_INSUFFICIENT; conditional subset p '
                 'values cannot replace it. No users were added or replaced based on effects.')
    parts.append('## Every enrolled user')
    user_rows = []
    for u in sorted(cohort['enrolled_users']):
        row = [u]
        for c in ['U', 'B']:
            r = pi[c, u]
            row.extend(display(number(r[k]), 100) for k in ['baseline_risk', 'full_risk', 'effect'])
        user_rows.append(row)
    parts.append(table(['User', 'U baseline %', 'U full %', 'U effect pp',
                        'B baseline %', 'B full %', 'B effect pp'], user_rows))
    parts.extend(['## All seven methods and fixed-threshold deployment',
                  'These summaries are descriptive. B fixed-common risk conditions on supported '
                  'classes and cannot establish service for omitted classes. Original DEV thresholds '
                  'are distinct from equal-budget ranks and may achieve different coverage per user.'])
    methods = ['class_empirical', 'margin', 'entropy', 'boundary_distance', 'full', 'no_tta', 'class_model']
    method_rows = []
    for c in ['U', 'B']:
        metric = 'ordinary_risk' if c == 'U' else 'fixed_common_risk'
        for method in methods:
            rank = [r for r in risks if r['contract'] == c and r['method'] == method and float(r['nominal_coverage']) == .3]
            threshold = [r for r in deploy if r['contract'] == c and r['method'] == method]
            assert len(rank) == len(threshold) == 80
            rank_values = [number(r[metric]) for r in rank]
            dv = [number(r[metric]) for r in threshold]
            coverage = [float(r['coverage']) for r in threshold]
            method_rows.append([c, method, sum(x is not None for x in rank_values),
                                display(median(rank_values), 100), sum(x is not None for x in dv),
                                display(median(dv), 100), display(median(coverage), 100),
                                f'{min(coverage)*100:.3f} to {max(coverage)*100:.3f}'])
    parts.append(table(['Endpoint', 'Method', 'Rank defined /80', 'Rank risk median %',
                        'Threshold defined /80', 'Threshold risk median %',
                        'Threshold coverage median %', 'Threshold coverage range %'], method_rows))
    parts.extend(['## All twenty tie seeds',
                  'Seeds 20261009 through 20261028 change ties only. They are not independent '
                  'users or alternate primary analyses. Canonical B class sets remain fixed. '
                  'Missing frozen-set risk remains undefined. No best seed is selected.'])
    seed_rows = []
    for c in ['U', 'B']:
        for method in [m for m in methods if m != 'full']:
            ss = [result['conditional_seed_descriptions'][f'{c}|{seed}|{method}'] for seed in range(20261009, 20261029)]
            med = [s['median'] for s in ss if s['median'] is not None]
            seed_rows.append([c, method, sum(s['missing_pairs'] == 0 for s in ss),
                              'missing' if not med else f'{min(med)*100:.3f} to {max(med)*100:.3f}',
                              f"{min(s['positive'] for s in ss)} to {max(s['positive'] for s in ss)}",
                              f"{min(s['n_nonzero'] for s in ss)} to {max(s['n_nonzero'] for s in ss)}"])
    parts.append(table(['Endpoint', 'Comparator', 'Complete-cohort seeds /20',
                        'Effect median range pp', 'Positive-user range', 'Nonzero-pair range'], seed_rows))
    parts.extend(['## Reproducibility and retained detail',
                  f"Independent verification checked {independent['exact_rescored_vectors']} frozen score vectors, "
                  f"{independent['seed_rows']} seed-risk rows, {independent['curve_rows']} coverage rows, "
                  f"{independent['class_rows']} class rows and {independent['effect_rows']} paired effects. "
                  'It separately derived support sets, ordering, integer risk counts, signs and '
                  'bootstrap summaries; it did not independently rerun neural inference.',
                  'Full seven-coverage curves, per-class counts/omissions, original-threshold '
                  'deployment, within-predicted-class controls, all seed rows and all primary '
                  'users remain in the hash-verified result archive. Source, base/TTA/feature/score '
                  'caches, dependencies and receipt backups remain private. Score-only remains '
                  'deferred. Negative or incomplete results do not authorize changing the frozen method.'])
    dest = LANE / 'manuscript_confirmation'
    dest.mkdir(exist_ok=False)
    report = dest / 'MANUSCRIPT_CONFIRMATION.md'
    report.write_text('\n\n'.join(parts) + '\n', encoding='utf-8')
    provenance.update({n: sha(LANE / n) for n in PREREQUISITES})
    provenance['historical_manuscript'] = sha(OLD)
    (dest / 'BUILD_MANIFEST.json').write_text(json.dumps({
        'status': 'VERIFIED_PROSPECTIVE_REPORT_BUILT', 'joint_decision': result['joint_decision'],
        'renderer_sha256': sha(Path(__file__)), 'input_sha256': provenance,
        'report_sha256': sha(report), 'scientific_protocol_changed': False,
        'independent_gesture_accuracy_claim': False, 'upstream_membership': 'UNRESOLVED'
    }, indent=2) + '\n')
    print(json.dumps({'report': str(report), 'joint_decision': result['joint_decision']}))


if __name__ == '__main__':
    main()
