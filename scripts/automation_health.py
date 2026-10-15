"""Read actual Actions runs and publish bounded, non-secret health evidence."""
import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.autonomous_translation import write_json
from backend.storage import ROOT, now
from backend.workflow_health import stage_health

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
        report['stages'][name], issue = stage_health(rows)
        if issue:
            report['issues'].append(name + issue)
    except Exception as error:
        report['stages'][name] = {'status': 'unknown', 'error': type(error).__name__}
        report['issues'].append(name + ':unverified')
ai_path = ROOT / 'data/ai-translation-status.json'
if ai_path.exists():
    try:
        ai = json.loads(ai_path.read_text())
        report['ai_translation'] = {key: ai.get(key) for key in ('status', 'finished_at', 'retry_after', 'requests', 'model')}
        report['ai_translation']['translated_count'] = len(ai.get('translated', []))
        if ai.get('status') in ('failed', 'configuration_error'):
            report['issues'].append('ai_translation:' + ai['status'])
    except (ValueError, TypeError):
        report['ai_translation'] = {'status': 'unknown'}
write_json(ROOT / 'data/automation-health.json', report)
print(json.dumps(report, ensure_ascii=False, indent=2))
