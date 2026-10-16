"""Restore the public snapshot and budget ledger into a fresh CI/local database."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.storage import ROOT, Store

path = ROOT / "data/live.json"
if not path.exists():
    print("No public snapshot yet")
    sys.exit(0)
store = Store(os.getenv("CULTURE_DESK_DB", ROOT / "runtime/culture-desk.db"))
count = store.restore_public_snapshot(path)
print(f"Restored {count} public records; existing data and daily budget retained")
from backend.cloudflare_translation import restore_completed
recovered = restore_completed(store)
print(f"Restored {len(recovered['restored'])} complete Cloudflare copies without API requests")
