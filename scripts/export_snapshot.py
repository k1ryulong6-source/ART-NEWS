"""Export only public live content, never preferences, bookmarks or credentials."""
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.storage import ROOT, Store, now

store = Store(os.getenv("CULTURE_DESK_DB", ROOT / "runtime/culture-desk.db"))
snapshot = store.dataset("live")
snapshot["snapshot_at"] = now()
snapshot["source_status"] = store.source_status()
with store.connect() as db:
    db.execute("CREATE TABLE IF NOT EXISTS summary_usage(day TEXT PRIMARY KEY, calls INTEGER NOT NULL)")
    snapshot["processing_usage"] = [dict(row) for row in db.execute("SELECT * FROM summary_usage ORDER BY day DESC LIMIT 7")]
for record in snapshot["content"]:
    record.pop("raw_excerpt", None)
snapshot.pop("sources", None)
snapshot["sources"] = [{key: row[key] for key in ("id", "name", "homepage_url", "source_type")} for row in store.source_status()]
(ROOT / "data/live.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Public snapshot: {len(snapshot['content'])} articles, {len(snapshot['events'])} events")
