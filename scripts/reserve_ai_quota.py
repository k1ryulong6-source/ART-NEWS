"""Prepare a durable Git quota reservation before the CI inference step."""
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.storage import ROOT
from backend.ai_pool import reserve_pool

print(json.dumps(reserve_pool(os.environ['AI_RUN_RESERVATION'])))
