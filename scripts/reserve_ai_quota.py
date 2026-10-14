"""Prepare a durable Git quota reservation before the CI inference step."""
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.storage import ROOT
from backend.ai_translation import reserve_requests

if os.getenv('GEMINI_API_KEY'):
    reservation_id = os.environ['AI_RUN_RESERVATION']
    result = reserve_requests(ROOT / 'data/ai-translation-ledger.json', reservation_id)
    print(json.dumps({'reservation': reservation_id, **result}))
else:
    print('No AI key: no requests reserved or made.')
