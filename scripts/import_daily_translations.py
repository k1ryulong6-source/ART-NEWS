"""Import reviewed ChatGPT packs without sending anything to a model API."""
import json
import argparse
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.storage import ROOT, Store
from backend.daily_translation import import_packs

parser = argparse.ArgumentParser()
parser.add_argument('--report', type=Path)
args = parser.parse_args()
store = Store(os.getenv('CULTURE_DESK_DB', ROOT / 'runtime/culture-desk.db'))
store.restore_public_snapshot(ROOT / 'data/live.json')
report = import_packs(store)
print(json.dumps(report, ensure_ascii=False, indent=2))
if args.report: args.report.write_text(json.dumps(report, ensure_ascii=False))
if report['invalid']:
    raise SystemExit(1)
