"""Only background Cloudflare API; no session worker or paid activation."""
import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.cloudflare_translation import reserve_cloudflare, run_cloudflare
from backend.autonomous_translation import write_json
from backend.storage import ROOT, Store, now

parser = argparse.ArgumentParser()
parser.add_argument('--reserve', action='store_true')
parser.add_argument('--probe', action='store_true')
args = parser.parse_args()
identity = os.environ['AI_RUN_RESERVATION']
if args.reserve:
    report = reserve_cloudflare(identity, probe=args.probe)
else:
    try:
        report = run_cloudflare(Store(os.getenv('CULTURE_DESK_DB', ROOT / 'runtime/culture-desk.db')),
                                identity, probe=args.probe,
                                retry_validation=os.getenv('CF_RETRY_VALIDATION') == 'true',
                                sample_id=os.getenv('CF_PROBE_SAMPLE_ID') or None)
    except Exception as error:
        report = {'status': 'failed', 'error': type(error).__name__, 'finished_at': now(),
                  'translated': [], 'requests': None}
    name = 'cloudflare-verification-report.json' if args.probe else 'cloudflare-translation-status.json'
    write_json(ROOT / 'data' / name, report)
print(json.dumps(report, ensure_ascii=False, indent=2))
if report['status'] in ('failed', 'configuration_error'):
    raise SystemExit(1)
