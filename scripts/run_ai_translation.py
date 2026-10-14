"""Primary AI worker. Missing credentials are reported, never replaced by fake output."""
import json
import os
import sys
import subprocess
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.storage import ROOT, Store, now
from backend.ai_translation import GeminiTranslator, run_ai
from backend.autonomous_translation import write_json

key = os.getenv('GEMINI_API_KEY', '')
last_checkpoint = time.monotonic()
def checkpoint():
    global last_checkpoint
    if os.getenv('GITHUB_ACTIONS') != 'true' or time.monotonic() - last_checkpoint < 60:
        return
    # Once a minute, persist accepted chunks independently of the final export.
    # A finished-copy checkpoint restores the temporary DB without another call.
    subprocess.run(['git', 'add', 'data/ai-translation-progress', 'data/ai-translation-ledger.json'], cwd=ROOT, check=True, capture_output=True)
    if subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=ROOT).returncode:
        for command in (['git', 'commit', '-m', 'Checkpoint accepted AI translation progress'],
                        ['git', 'pull', '--rebase', 'origin', 'main'], ['git', 'push', 'origin', 'HEAD:main']):
            subprocess.run(command, cwd=ROOT, check=True, capture_output=True)
    last_checkpoint = time.monotonic()

if not key:
    report = {'status': 'needs_configuration', 'provider': 'gemini', 'finished_at': now(),
              'translated': [], 'reason': 'GEMINI_API_KEY secret not configured'}
else:
    try:
        report = run_ai(Store(os.getenv('CULTURE_DESK_DB', ROOT / 'runtime/culture-desk.db')), GeminiTranslator(key),
                        reservation_id=os.getenv('AI_RUN_RESERVATION') or None, checkpoint_sink=checkpoint)
    except Exception as error:
        report = {'status': 'failed', 'finished_at': now(), 'translated': [], 'error': type(error).__name__}
write_json(ROOT / 'data/ai-translation-status.json', report)
print(json.dumps(report, ensure_ascii=False, indent=2))
if report['status'] in ('failed', 'configuration_error'):
    raise SystemExit(1)
