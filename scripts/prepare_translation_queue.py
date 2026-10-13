import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.daily_translation import prepare_queue
from backend.storage import ROOT

print(json.dumps(prepare_queue(json.loads((ROOT/'data/live.json').read_text())), ensure_ascii=False))
