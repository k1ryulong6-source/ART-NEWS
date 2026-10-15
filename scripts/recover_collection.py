"""Recover a displaced collection slot; never call a translation model."""
import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.workflow_health import collection_needs_requeue

repository = os.environ['GITHUB_REPOSITORY']
event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
cancelled = event.get('workflow_run') or {}
if (cancelled.get('name') != 'Refresh cultural news' or cancelled.get('head_branch') != 'main'
        or (cancelled.get('head_repository') or {}).get('full_name') != repository):
    raise SystemExit('Ignoring unverified collection event')
headers = {'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'],
           'Accept': 'application/vnd.github+json', 'User-Agent': 'Intermission-collection-recovery'}
base = f'https://api.github.com/repos/{repository}/actions/workflows/refresh.yml'
with urlopen(Request(base + '/runs?per_page=30', headers=headers), timeout=30) as response:
    rows = json.load(response)['workflow_runs']
if collection_needs_requeue(cancelled, rows):
    payload = json.dumps({'ref': 'main'}).encode()
    with urlopen(Request(base + '/dispatches', data=payload,
                         headers={**headers, 'Content-Type': 'application/json'}, method='POST'), timeout=30) as response:
        if response.status != 204: raise ValueError('collection_dispatch_not_confirmed')
    print('Displaced collection requeued once; active data writer retained.')
else:
    print('Replacement already active/completed, or evidence insufficient; no duplicate dispatch.')
