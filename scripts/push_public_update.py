"""Commit must already exist. Save public evidence and safely retry a normal push."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.storage import ROOT
from backend.public_sync import push_public_update

print(json.dumps(push_public_update(ROOT)))
