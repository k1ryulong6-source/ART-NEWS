"""Retry only the monitor's derived report; never replace collection or AI data."""
import json
import os
import subprocess
import sys
from pathlib import Path
from .public_sync import safe_git_error

REPORT = 'data/automation-health.json'


def push_health_update(root, *, regenerate=None, attempts=4, runner=subprocess.run):
    root = Path(root)
    environment = {**os.environ, 'GIT_EDITOR': 'true'}
    archive = root / 'runtime/health-update-evidence'
    archive.mkdir(parents=True, exist_ok=True)
    evidence = {'attempts': [], 'status': 'pending'}
    def save():
        (archive / 'push-report.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    def git(*args, check=True):
        result = runner(['git', *args], cwd=root, env=environment, text=True, capture_output=True)
        if check and result.returncode:
            evidence.update(status='failed', error=safe_git_error(result.stderr))
            save()
            raise RuntimeError('health_git_command_failed:' + args[0])
        return result
    changed = git('diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD').stdout.splitlines()
    if changed != [REPORT] or git('status', '--porcelain', '--untracked-files=no').stdout.strip():
        raise ValueError('health_retry_requires_only_own_committed_report')
    for attempt in range(attempts):
        git('fetch', 'origin', 'main')
        result = git('rebase', 'origin/main', check=False)
        while result.returncode:
            conflicts = git('diff', '--name-only', '--diff-filter=U').stdout.splitlines()
            if conflicts != [REPORT]:
                evidence.update(status='failed', unexpected_conflicts=conflicts)
                save()
                raise RuntimeError('health_retry_refuses_unrelated_conflict')
            # Under rebase, ours is the fetched main. Recompute the disposable
            # report on that tree instead of choosing stale monitoring evidence.
            git('checkout', '--ours', '--', REPORT)
            if regenerate:
                regenerate(root)
            else:
                runner([sys.executable, '-S', str(root / 'scripts/automation_health.py')],
                       cwd=root, env=environment, check=True)
            git('add', '--', REPORT)
            result = git('rebase', '--continue', check=False)
        result = git('push', 'origin', 'HEAD:main', check=False)
        evidence['attempts'].append({'attempt': attempt + 1, 'returncode': result.returncode,
                                     'detail': safe_git_error(result.stderr)})
        if result.returncode == 0:
            evidence['status'] = 'pushed'; save()
            return {'status': 'pushed', 'attempts': attempt + 1}
        save()
        if not any(reason in result.stderr.lower() for reason in ('non-fast-forward', 'fetch first', 'cannot lock ref')):
            break
    evidence['status'] = 'failed'; save()
    raise RuntimeError('health_push_not_confirmed; see runtime/health-update-evidence/push-report.json')
