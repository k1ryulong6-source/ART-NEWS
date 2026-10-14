"""Bounded real translation verification, using the durable production quota ledger."""
import json
import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.ai_translation import configuration, reserve_requests, run_ai
from backend.gemini_access import DiagnosticGeminiTranslator, inspect_access
from backend.autonomous_translation import write_json
from backend.storage import Store, now

cfg = {**configuration(), 'requests_per_run': 2, 'seconds_per_run': 120}
key = os.getenv('GEMINI_API_KEY', '')
reservation_id = os.environ['AI_RUN_RESERVATION']
ledger_path = ROOT / 'data/ai-translation-ledger.json'
if sys.argv[1:] == ['--reserve']:
    access = inspect_access(key, cfg['model'])
    write_json(ROOT / 'runtime/gemini-verification-access.json', access)
    if access['status'] != 'model_available':
        print(json.dumps({'status': access['status'], 'generation_requests': 0}))
        raise SystemExit(1)
    # One explicit diagnostic retry after confirming availability; do not reset counts.
    previous = json.loads((ROOT / 'data/ai-translation-status.json').read_text())
    ledger = json.loads(ledger_path.read_text())
    if previous.get('status') == 'configuration_error':
        ledger.pop('retry_after', None)
        write_json(ledger_path, ledger)
    result = reserve_requests(ledger_path, reservation_id, cfg)
    print(json.dumps({'reserved_requests': result['allocated'], 'generation_requests': 0}))
else:
    access = json.loads((ROOT / 'runtime/gemini-verification-access.json').read_text())
    if access['status'] != 'model_available' or not key:
        raise SystemExit('Configured model not available; no generation request made.')
    provider = DiagnosticGeminiTranslator(key, cfg)
    report = run_ai(Store(os.getenv('CULTURE_DESK_DB', ROOT / 'runtime/culture-desk.db')), provider,
                    cfg=cfg, reservation_id=reservation_id)
    report['verification_run'] = True
    report['finished_at'] = now()
    if provider.error_detail:
        report['error_detail'] = provider.error_detail
    write_json(ROOT / 'data/ai-translation-status.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report['status'] in ('failed', 'configuration_error'):
        raise SystemExit(1)
