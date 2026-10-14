"""Read configured public feeds and reconcile against the public inventory."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.storage import ROOT
from backend.ingestion import get_url
from backend.coverage import audit_sources

snapshot = json.loads((ROOT / 'data/live.json').read_text())
config = json.loads((ROOT / 'config/sources.json').read_text())
path = ROOT / 'data/coverage-audit.json'
previous = json.loads(path.read_text()) if path.exists() else None
report = audit_sources(snapshot, config, get_url, previous)
path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'checked_sources': sum(r['status'] == 'checked' for r in report['sources']),
                  'failed_sources': [r['source_id'] for r in report['sources'] if r['status'] == 'failed'],
                  'missing_list_entries': sum(len(r.get('missing') or []) for r in report['sources'])}))
