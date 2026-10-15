"""Read real Actions artifacts for the trial. Never generate a translation."""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.storage import ROOT, now

repo = os.getenv('GITHUB_REPOSITORY', 'k1ryulong6-source/ART-NEWS')
baseline = json.loads((ROOT / 'data/ai-free-trial-baseline.json').read_text())
start = datetime.fromisoformat(baseline['observation_started_at'])
end = datetime.fromisoformat(baseline['review_after'])
target = ROOT / 'data/autonomous-trial-report.json'
if target.exists():
    previous = json.loads(target.read_text())
    if previous.get('complete') and previous.get('started_at') == start.isoformat():
        print('First full-day artifact audit already verified; retained without new network/model calls.')
        raise SystemExit(0)
    if '--if-due' in sys.argv and previous.get('started_at') == start.isoformat():
        try:
            checked = datetime.fromisoformat(previous['checked_at'])
            if previous.get('completed_runs', 0) > 0 and (datetime.now(timezone.utc) - checked).total_seconds() < 6 * 3600:
                (ROOT / 'data/trial-runs').mkdir(exist_ok=True)
                print('Trial artifact audit not due; no new network/model calls.')
                raise SystemExit(0)
        except (ValueError, KeyError, TypeError): pass
directory = ROOT / 'data/trial-runs'; directory.mkdir(exist_ok=True)
env = dict(os.environ)
if env.get('GITHUB_TOKEN'): env['GH_TOKEN'] = env['GITHUB_TOKEN']


def gh(*args):
    return subprocess.check_output(['gh', *args], env=env, text=True, stderr=subprocess.PIPE, timeout=120)


errors, reports = [], []
try:
    date_filter = start.date().isoformat() + '..' + end.date().isoformat()
    runs = []
    for page in range(1, 21):
        batch = json.loads(gh('api', f'repos/{repo}/actions/workflows/autotranslate.yml/runs?per_page=100&page={page}&created={date_filter}'))['workflow_runs']
        runs.extend(batch)
        if len(batch) < 100: break
    else:
        errors.append({'reason': 'run_list_limit_more_evidence_required'})
except Exception as error:
    runs = []; errors.append({'reason': type(error).__name__})
expected = []
deadline = time.monotonic() + 300
for run in runs:
    created = datetime.fromisoformat(run['created_at'].replace('Z', '+00:00'))
    if not start <= created <= end or run.get('conclusion') == 'cancelled':
        continue
    id = str(run['id'])
    if not id.isdigit(): continue
    expected.append(id)
    if run['status'] != 'completed':
        errors.append({'run_id': id, 'reason': 'window_run_still_active'}); continue
    if time.monotonic() >= deadline:
        errors.append({'reason': 'audit_time_budget_remaining_runs_not_verified'}); break
    path = directory / (id + '.json')
    try:
        if path.exists(): report = json.loads(path.read_text())
        else:
            with TemporaryDirectory(prefix='culture-trial-') as td:
                gh('run', 'download', id, '--repo', repo, '--name', 'translation-checkpoints-and-report', '--dir', td)
                files = list(Path(td).rglob('ai-translation-status.json'))
                if len(files) != 1 or files[0].stat().st_size > 200_000: raise ValueError('status_artifact_unverified')
                ai = json.loads(files[0].read_text())
            report = {'run_id': id, 'url': run['html_url'], 'created_at': run['created_at'],
                      'conclusion': run['conclusion'], 'ai': ai}
            path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        reports.append(report)
    except Exception as error:
        errors.append({'run_id': id, 'reason': type(error).__name__})
translated = sum(len(r['ai'].get('translated') or []) for r in reports)
failures = sum(len(r['ai'].get('failed') or []) for r in reports)
hours = (datetime.now(timezone.utc) - start).total_seconds() / 3600
report = {'schema_version': 1, 'checked_at': now(), 'started_at': start.isoformat(),
          'window_end': end.isoformat(),
          'scope': 'completed_non_cancelled_automatic_runs; verification_and_inflight_usage_are_separate',
          'elapsed_hours': round(hours, 2), 'full_24_hours_elapsed': hours >= 24,
          'completed_runs': len(reports), 'expected_runs': len(expected), 'unverified_runs': errors,
          'requests': sum(r['ai'].get('requests', 0) for r in reports),
          'translated_article_events': translated, 'validation_failures': failures,
          'article_validation_failure_fraction': round(failures / (translated + failures), 4) if translated + failures else None,
          'resumed_articles': len({id for r in reports for id in (r['ai'].get('resumed') or [])}),
          'resumed_article_events': sum(len(r['ai'].get('resumed') or []) for r in reports),
          'service_aborted_runs': sum(r['ai'].get('status') in ('service_wait', 'quota_wait', 'configuration_error', 'failed') for r in reports),
          'complete': hours >= 24 and bool(reports) and not errors,
          'limitations': ['Not a request-level failure rate or an account billing statement.',
                         'Article events can include repeated attempts; cumulative published output is in operations.json.']}
target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False))
