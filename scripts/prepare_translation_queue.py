import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.snapshot_files import read_snapshot
from backend.daily_translation import prepare_queue
from backend.storage import ROOT

print(json.dumps(prepare_queue(read_snapshot(ROOT/'data/live.json')), ensure_ascii=False))
