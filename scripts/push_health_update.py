"""Save a derived health report with bounded race recovery; no model calls."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.storage import ROOT
from backend.health_sync import push_health_update

print(json.dumps(push_health_update(ROOT)))
