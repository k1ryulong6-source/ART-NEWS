"""Push accepted public data; rebuild only known derived conflicts, never bodies."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from .snapshot_files import read_snapshot, encoded

REPORTS = {'data/acceptance.json', 'data/article-quality-report.json',
           'data/quality.json', 'data/important-news-audit.json'}
GIT_FILE_LIMIT = 100 * 1024 * 1024


def safe_git_error(text):
    text = re.sub(r'https?://[^\s/@]+:[^\s/@]+@', 'https://[redacted]@', text or '')
    text = re.sub(r'\b(?:gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+|AIza[A-Za-z0-9_-]{20,})', '[redacted]', text)
    text = re.sub(r'(?i)(authorization:\s*(?:bearer|basic)\s+)\S+', r'\1[redacted]', text)
    return text[-6000:]


def push_error_category(text):
    value = text.lower()
    if 'gh001' in value or 'exceeds github' in value or 'large files detected' in value:
        return 'git_file_too_large'
    if 'authentication failed' in value or 'could not read username' in value:
        return 'git_authentication_failed'
    if 'permission' in value or '403' in value or 'protected branch' in value:
        return 'git_permission_denied'
    if 'non-fast-forward' in value or 'fetch first' in value:
        return 'git_remote_advanced'
    return 'git_push_failed'


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
        data = read_snapshot(snapshot)
        if not isinstance(data.get('content'), list): raise ValueError('invalid_public_snapshot')
        (archive / 'accepted-public-snapshot.json').write_bytes(encoded(data))
    environment = {**os.environ, 'GIT_EDITOR': 'true'}
    def git(*args, check=True, input=None):
        return subprocess.run(['git', *args], cwd=root, env=environment,
                              check=check, text=True, capture_output=True, input=input)
    diagnostics = {'status': 'pending', 'attempts': []}
    def record(value):
        diagnostics['attempts'].append(value)
        (archive / 'git-push-report.json').write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2) + '\n')
    committed = git('show', 'HEAD:data/live.json', check=False)
    if committed.returncode == 0:
        manifest = json.loads(committed.stdout)
        parts = (manifest.get('snapshot_storage') or {}).get('parts') or []
        if parts:
            tracked = set(git('ls-tree', '-r', '--name-only', 'HEAD', '--', 'data/snapshot-content').stdout.splitlines())
            missing = ['data/' + part['path'] for part in parts if 'data/' + part['path'] not in tracked]
            dirty = git('diff', '--quiet', 'HEAD', '--', 'data/snapshot-content', check=False).returncode
            if missing or dirty:
                diagnostics['status'] = 'failed'
                record({'category': 'snapshot_parts_not_committed', 'missing': missing, 'modified': bool(dirty)})
                raise RuntimeError('snapshot_parts_not_committed; accepted snapshot archived; remote left unchanged')
    for attempt in range(attempts):
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
        objects = git('rev-list', '--objects', 'origin/main..HEAD').stdout
        large = []
        if objects.strip():
            sizes = git('cat-file', '--batch-check=%(objecttype) %(objectsize) %(objectname) %(rest)', input=objects).stdout
            for line in sizes.splitlines():
                fields = line.split(' ', 3)
                if len(fields) >= 3 and fields[0] == 'blob' and int(fields[1]) > GIT_FILE_LIMIT:
                    large.append({'path': fields[3] if len(fields) == 4 else fields[2], 'bytes': int(fields[1])})
        if large:
            diagnostics['status'] = 'failed'
            record({'attempt': attempt + 1, 'category': 'git_file_too_large', 'files': large})
            raise RuntimeError('git_file_too_large; see runtime/public-update-evidence/git-push-report.json; accepted snapshot archived')
        result = git('push', 'origin', 'HEAD:main', check=False)
        if result.returncode == 0:
            diagnostics['status'] = 'pushed'
            record({'attempt': attempt + 1, 'category': 'success'})
            return {'status': 'pushed', 'commit': git('rev-parse', 'HEAD').stdout.strip(),
                    'accepted_snapshot_archive': str(archive / 'accepted-public-snapshot.json')}
        category = push_error_category(result.stderr)
        diagnostics['status'] = 'failed'
        detail = safe_git_error(result.stderr)
        record({'attempt': attempt + 1, 'category': category, 'returncode': result.returncode, 'detail': detail})
        print('Public snapshot push failed: ' + category + '\n' + detail, file=sys.stderr)
        if category in {'git_file_too_large', 'git_authentication_failed', 'git_permission_denied'}:
            break
    raise RuntimeError('push_not_confirmed; accepted snapshot archived; no force push attempted')
