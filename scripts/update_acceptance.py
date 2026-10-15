"""Recompute completion after data changes. No messages and no model calls."""
import json
import sys
from urllib.request import urlopen
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.storage import ROOT
from backend.operations import load_operations
from backend.attention_units import attention_report
from backend.acceptance import acceptance_report


def optional(name):
    try: return json.loads((ROOT / 'data' / name).read_text())
    except (OSError, ValueError): return None


snapshot = optional('live.json')
operations = load_operations(snapshot)
trial = optional('autonomous-trial-report.json') or {}
quality = optional('article-quality-report.json') or {}
if quality.get('complete') and operations['translation']['pending'] == 0 and (operations.get('observation') or {}).get('full_24_hours_elapsed'):
    try:
        with urlopen('https://mujianrest.work/reports/operations.json', timeout=15) as response:
            public = json.loads(response.read(500_000))
        trial['publication_verified'] = public.get('snapshot_key') == operations['snapshot_key']
    except Exception:
        trial['publication_verified'] = False
report = acceptance_report(operations, quality, trial,
                           attention_report(snapshot, json.loads((ROOT / 'config/sources.json').read_text()), optional('coverage-audit.json')),
                           optional('translation-queue.json'))
(ROOT / 'data/acceptance.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'all_ready': report['all_ready'], 'gates': report['gates']}, ensure_ascii=False))
