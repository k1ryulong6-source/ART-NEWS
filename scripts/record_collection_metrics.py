"""Count actual newly inserted records forward from a declared tracking start."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.storage import ROOT, now
from backend.autonomous_translation import write_json

parser = argparse.ArgumentParser()
parser.add_argument('--initialize', action='store_true')
args = parser.parse_args()
snapshot = json.loads((ROOT / 'data/live.json').read_text())
path = ROOT / 'data/collection-metrics.json'
current = {source['id']: source.get('last_run') or {} for source in snapshot.get('source_status', [])}
if path.exists():
    ledger = json.loads(path.read_text())
else:
    ledger = {'schema_version': 1, 'tracking_started_at': now(), 'days': {},
              'last_counted_run': {key: row.get('started_at') for key, row in current.items()},
              'note': '只统计启用监测后的实际入库；发布时间、fetched_at和首次恢复旧快照不是每日新增。首次接入来源的历史列表回补另记，不把搭建日当稳定日均。'}
if not args.initialize:
    for identifier, run in current.items():
        stamp = run.get('started_at')
        if not stamp or stamp <= (ledger['last_counted_run'].get(identifier) or '') or not run.get('finished_at'):
            continue
        day = run['finished_at'][:10]
        total = ledger['days'].setdefault(day, {'new_records': 0, 'first_source_run_records': 0, 'source_runs': 0, 'failed_source_runs': 0, 'by_source': {}})
        total['new_records'] += run.get('inserted_count', 0)
        if identifier not in ledger['last_counted_run']:
            total['first_source_run_records'] += run.get('inserted_count', 0)
        total['source_runs'] += 1
        total['failed_source_runs'] += int(run.get('status') == 'failed')
        total['by_source'][identifier] = total['by_source'].get(identifier, 0) + run.get('inserted_count', 0)
        ledger['last_counted_run'][identifier] = stamp
ledger['updated_at'] = now()
write_json(path, ledger)
print(json.dumps({'tracking_started_at': ledger['tracking_started_at'], 'days': ledger['days']}, ensure_ascii=False))
