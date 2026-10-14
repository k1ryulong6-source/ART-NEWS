"""A real background worker, independent of ChatGPT and external model APIs."""
import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.storage import ROOT, Store, now
from backend.offline_model import OfflineTranslator
from backend.autonomous_translation import run_autonomous, write_json

parser = argparse.ArgumentParser()
parser.add_argument('--model-dir', type=Path)
parser.add_argument('--seconds', type=int)
parser.add_argument('--articles', type=int)
parser.add_argument('--characters', type=int)
args = parser.parse_args()
store = Store(os.getenv('CULTURE_DESK_DB', ROOT / 'runtime/culture-desk.db'))
try:
    report = run_autonomous(store, OfflineTranslator(args.model_dir), seconds=args.seconds,
                            articles=args.articles, characters=args.characters)
except Exception as error:
    report = {'status': 'failed', 'finished_at': now(), 'error': type(error).__name__, 'translated': []}
write_json(ROOT / 'data/auto-translation-status.json', report)
print(json.dumps(report, ensure_ascii=False, indent=2))
if report['status'] == 'failed':
    raise SystemExit(1)
