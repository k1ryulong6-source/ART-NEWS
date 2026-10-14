"""Inspect the configured Secret without making a generation request."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.gemini_access import inspect_access
from backend.ai_translation import configuration
from backend.storage import now

report = inspect_access(os.getenv('GEMINI_API_KEY', ''), configuration()['model'])
report['checked_at'] = now()
path = ROOT / 'runtime/gemini-access.json'
path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
if report['status'] not in ('model_available', 'configured_model_unavailable'):
    raise SystemExit(1)
