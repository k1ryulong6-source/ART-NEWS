"""Push accepted public data; rebuild only known derived conflicts, never bodies."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPORTS = {'data/acceptance.json', 'data/article-quality-report.json',
           'data/quality.json', 'data/important-news-audit.json'}


def derived_path(path):
    return (path in REPORTS or path == 'data/translation-queue.json'
            or bool(re.fullmatch(r'data/translation-queue/\d{4}\.json', path))
            or bool(re.fullmatch(r'data/article-quality/live-[a-f0-9]{24}\.json', path)))


def regenerate_evidence(root, conflicts):
    def script(name, *args):
        subprocess.run([sys.executable, str(root / 'scripts' / name), *args], cwd=root, check=True)
    script('prepare_translation_queue.py')
    script('audit_data.py', '--output', 'data/quality.json', '--strict')
    script('audit_important_news.py')
    script('audit_article_quality.py', '--limit', '0')
    script('update_acceptance.py')


def push_public_update(root, regenerate=None, attempts=4):
    root = Path(root).resolve()
    archive = root / 'runtime/public-update-evidence'
    archive.mkdir(parents=True, exist_ok=True)
    snapshot = root / 'data/live.json'
    if snapshot.exists():
        data = json.loads(snapshot.read_text())
        if not isinstance(data.get('content'), list): raise ValueError('invalid_public_snapshot')
        shutil.copy2(snapshot, archive / 'accepted-public-snapshot.json')
    environment = {**os.environ, 'GIT_EDITOR': 'true'}
    def git(*args, check=True):
        return subprocess.run(['git', *args], cwd=root, env=environment,
                              check=check, text=True, capture_output=True)
    for _ in range(attempts):
        git('fetch', 'origin', 'main')
        result = git('rebase', 'origin/main', check=False)
        while result.returncode:
            conflicts = git('diff', '--name-only', '--diff-filter=U').stdout.splitlines()
            if not conflicts or any(not derived_path(p) for p in conflicts):
                raise RuntimeError('unresolved_public_data_conflict; accepted snapshot archived; no body overwritten')
            for path in conflicts:
                if path.startswith('data/article-quality/'):
                    # Contradictory checks require a new public check, not a
                    # guessed winner. Preserve both pieces of evidence separately.
                    for stage in ('2', '3'):
                        old = git('show', ':' + stage + ':' + path, check=False)
                        (archive / (Path(path).stem + '-stage' + stage + '.json')).write_text(old.stdout)
                    git('rm', '--', path)
            (regenerate or regenerate_evidence)(root, conflicts)
            for path in ('data/acceptance.json', 'data/article-quality-report.json',
                         'data/quality.json', 'data/important-news-audit.json',
                         'data/translation-queue.json', 'data/translation-queue', 'data/translation-input'):
                if (root / path).exists(): git('add', '--', path)
            result = git('rebase', '--continue', check=False)
        result = git('push', 'origin', 'HEAD:main', check=False)
        if result.returncode == 0:
            return {'status': 'pushed', 'commit': git('rev-parse', 'HEAD').stdout.strip(),
                    'accepted_snapshot_archive': str(archive / 'accepted-public-snapshot.json')}
    raise RuntimeError('push_not_confirmed; accepted snapshot archived; no force push attempted')
