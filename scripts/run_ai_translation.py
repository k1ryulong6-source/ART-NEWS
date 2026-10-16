"""Primary AI worker. Missing credentials are reported, never replaced by fake output."""
import json
import os
import sys
import subprocess
import time
import threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.storage import ROOT, Store, now
from backend.ai_pool import run_pool
from backend.autonomous_translation import write_json

last_checkpoint = time.monotonic()
io_lock = threading.RLock()
def checkpoint():
    with io_lock:
        persist_checkpoint()

def persist_checkpoint():
    global last_checkpoint
    if os.getenv('GITHUB_ACTIONS') != 'true' or time.monotonic() - last_checkpoint < 60:
        return
    # Once a minute, persist accepted chunks independently of the final export.
    # A finished-copy checkpoint restores the temporary DB without another call.
    paths = [p for p in ('data/ai-translation-progress', 'data/ai-translation-ledger.json',
                        'data/ai-translation-ledger-secondary.json', 'data/ai-translation-ledger-deepseek.json',
                        'data/ai-translation-projects') if (ROOT / p).exists()]
    subprocess.run(['git', 'add', *paths], cwd=ROOT, check=True, capture_output=True)
    if subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=ROOT).returncode:
        for command in (['git', 'commit', '-m', 'Checkpoint accepted AI translation progress'],
                        ['git', 'pull', '--rebase', 'origin', 'main'], ['git', 'push', 'origin', 'HEAD:main']):
            subprocess.run(command, cwd=ROOT, check=True, capture_output=True)
    last_checkpoint = time.monotonic()

try:
    report = run_pool(Store(os.getenv('CULTURE_DESK_DB', ROOT / 'runtime/culture-desk.db')),
                      reservation_id=os.environ['AI_RUN_RESERVATION'], checkpoint_sink=checkpoint, io_lock=io_lock)
except Exception as error:
    report = {'status': 'failed', 'finished_at': now(), 'translated': [], 'error': type(error).__name__}
write_json(ROOT / 'data/ai-translation-status.json', report)
print(json.dumps(report, ensure_ascii=False, indent=2))
if report['status'] in ('failed', 'configuration_error'):
    raise SystemExit(1)
