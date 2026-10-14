"""Read actual Actions runs and publish bounded, non-secret health evidence."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.autonomous_translation import write_json
from backend.storage import ROOT, now

repository = os.getenv('GITHUB_REPOSITORY', 'k1ryulong6-source/ART-NEWS')
token = os.getenv('GITHUB_TOKEN', '')
stages = {'collection': 'refresh.yml', 'translation': 'autotranslate.yml', 'publication': 'pages.yml'}
report = {'checked_at': now(), 'repository': repository, 'stages': {}, 'issues': []}
for name, workflow in stages.items():
    try:
        url = f'https://api.github.com/repos/{repository}/actions/workflows/{workflow}/runs?per_page=30'
        request = Request(url, headers={'Accept': 'application/vnd.github+json',
                                       'Authorization': 'Bearer ' + token, 'User-Agent': 'Intermission-health'})
        with urlopen(request, timeout=30) as response:
            rows = json.loads(response.read())['workflow_runs']
        fields = lambda row: {key: row[key] for key in ('id', 'event', 'status', 'conclusion', 'html_url', 'created_at', 'updated_at')}
        latest = rows[0] if rows else None
        success = next((row for row in rows if row['conclusion'] == 'success'), None)
        stale = not success or (datetime.now(timezone.utc) - datetime.fromisoformat(success['updated_at'].replace('Z', '+00:00'))).total_seconds() > 6 * 3600
        failed = latest and latest['conclusion'] in ('failure', 'cancelled', 'timed_out', 'action_required')
        active = latest and latest['status'] != 'completed' and (datetime.now(timezone.utc) - datetime.fromisoformat(latest['created_at'].replace('Z', '+00:00'))).total_seconds() < 6 * 3600
        report['stages'][name] = {'latest': fields(latest) if latest else None,
                                 'last_success': fields(success) if success else None,
                                 'status': 'failed' if failed else 'running' if active else 'stale' if stale else 'healthy'}
        if failed or (stale and not active):
            report['issues'].append(name + (':failed' if failed else ':no_recent_success'))
    except Exception as error:
        report['stages'][name] = {'status': 'unknown', 'error': type(error).__name__}
        report['issues'].append(name + ':unverified')
write_json(ROOT / 'data/automation-health.json', report)
print(json.dumps(report, ensure_ascii=False, indent=2))
