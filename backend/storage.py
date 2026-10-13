"""Small SQLite repository. Every connection explicitly enables foreign keys."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
STATUSES = {"want_to_see", "planning", "seen"}


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
            existing = {row[1] for row in db.execute("PRAGMA table_info(content)")}
            for column in ("raw_excerpt", "body_hash"):
                if column not in existing:
                    db.execute(f"ALTER TABLE content ADD COLUMN {column} TEXT")
            for column, default in (("geography_status", "unknown"), ("locations_json", "[]")):
                if column not in existing:
                    db.execute(f"ALTER TABLE content ADD COLUMN {column} TEXT NOT NULL DEFAULT '{default}'")
            from .reading import READING_FIELDS, TRANSLATION_FIELDS
            from .originals import ORIGINAL_FIELDS
            from .articles import ARTICLE_FIELDS
            from .editorial import EDITORIAL_FIELDS
            for column in READING_FIELDS + TRANSLATION_FIELDS + ORIGINAL_FIELDS + ARTICLE_FIELDS + EDITORIAL_FIELDS:
                if column not in existing:
                    db.execute(f"ALTER TABLE content ADD COLUMN {column} TEXT")
            source_columns = {row[1] for row in db.execute("PRAGMA table_info(sources)")}
            for column in ("publisher_country", "coverage"):
                if column not in source_columns:
                    db.execute(f"ALTER TABLE sources ADD COLUMN {column} TEXT")
            event_columns = {row[1] for row in db.execute("PRAGMA table_info(events)")}
            for column in ("start_at", "end_at", "deadline_at", "time_note", "time_status", "eligibility_note", "booking_status"):
                if column not in event_columns:
                    db.execute(f"ALTER TABLE events ADD COLUMN {column} TEXT")
            db.execute("CREATE TABLE IF NOT EXISTS preferences (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS job_state(id TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS notifications(id TEXT PRIMARY KEY, event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE, title TEXT NOT NULL, created_at TEXT NOT NULL, read INTEGER NOT NULL DEFAULT 0, emailed INTEGER NOT NULL DEFAULT 0)")
            demo = json.loads((ROOT / "data/demo.json").read_text(encoding="utf-8"))
            for table in ("sources", "content", "events", "content_events"):
                columns_allowed = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
                for record in demo[table]:
                    record = {k: v for k, v in record.items() if k in columns_allowed}
                    columns = list(record)
                    db.execute(f"INSERT OR IGNORE INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})", list(record.values()))

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def dataset(self, mode="demo"):
        demo = 1 if mode == "demo" else 0
        with self.connect() as db:
            content = [dict(row) for row in db.execute("SELECT * FROM content WHERE is_demo=? ORDER BY published_at DESC", (demo,))]
            events = [dict(row) for row in db.execute("SELECT * FROM events WHERE is_demo=? ORDER BY start_date", (demo,))]
            ids = {record["id"] for record in content}
            event_ids = {record["id"] for record in events}
            links = [dict(row) for row in db.execute("SELECT * FROM content_events") if row["content_id"] in ids and row["event_id"] in event_ids]
            sources = [dict(row) for row in db.execute("SELECT * FROM sources")]
        reference = "2026-10-13" if demo else datetime.now(ZoneInfo(self.preferences().get("reading_timezone", "UTC"))).date().isoformat()
        return {"schema_version": 1, "mode": mode, "reference_date": reference, "content": content, "events": events, "content_events": links, "sources": sources}

    def preferences(self):
        with self.connect() as db:
            row = db.execute("SELECT value FROM preferences WHERE id=1").fetchone()
        defaults = json.loads((ROOT / "config/preferences.json").read_text(encoding="utf-8"))
        saved = json.loads(row[0]) if row else {}
        return {**defaults, **saved, "news_scope": saved.get("news_scope", defaults["news_scope"])}

    def save_preferences(self, preferences):
        with self.connect() as db:
            db.execute("INSERT INTO preferences VALUES(1,?) ON CONFLICT(id) DO UPDATE SET value=excluded.value", (json.dumps(preferences, ensure_ascii=False),))
        return preferences

    def bookmarks(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM bookmarks ORDER BY created_at DESC")]

    def save_bookmark(self, target_type, target_id, status="want_to_see", note=""):
        if target_type not in ("content", "event") or status not in STATUSES:
            raise ValueError("无效收藏类型或状态")
        table = "content" if target_type == "content" else "events"
        column = "content_id" if target_type == "content" else "event_id"
        stamp = now()
        with self.connect() as db:
            if not db.execute(f"SELECT id FROM {table} WHERE id=?", (target_id,)).fetchone():
                raise KeyError("内容不存在")
            old = db.execute(f"SELECT id FROM bookmarks WHERE {column}=?", (target_id,)).fetchone()
            bookmark_id = old[0] if old else str(uuid4())
            if old:
                db.execute("UPDATE bookmarks SET status=?,note=?,updated_at=? WHERE id=?", (status, note, stamp, bookmark_id))
            else:
                db.execute(f"INSERT INTO bookmarks (id,{column},status,note,created_at,updated_at) VALUES(?,?,?,?,?,?)", (bookmark_id, target_id, status, note, stamp, stamp))
            return dict(db.execute("SELECT * FROM bookmarks WHERE id=?", (bookmark_id,)).fetchone())

    def delete_bookmark(self, bookmark_id):
        with self.connect() as db:
            return db.execute("DELETE FROM bookmarks WHERE id=?", (bookmark_id,)).rowcount > 0

    def import_data(self, preferences, bookmarks):
        # Validate every reference before writing anything; import is atomic.
        stamp = now()
        with self.connect() as db:
            for item in bookmarks:
                has_content = bool(item.get("content_id"))
                has_event = bool(item.get("event_id"))
                if has_content == has_event or item.get("status") not in STATUSES:
                    raise ValueError("导入收藏格式无效")
                table, key = ("content", "content_id") if has_content else ("events", "event_id")
                if not db.execute(f"SELECT id FROM {table} WHERE id=?", (item[key],)).fetchone():
                    raise ValueError("导入收藏引用了当前不存在的内容；请先恢复对应内容库")
            db.execute("INSERT INTO preferences VALUES(1,?) ON CONFLICT(id) DO UPDATE SET value=excluded.value", (json.dumps(preferences, ensure_ascii=False),))
            for item in bookmarks:
                key = "content_id" if item.get("content_id") else "event_id"
                old = db.execute(f"SELECT id FROM bookmarks WHERE {key}=?", (item[key],)).fetchone()
                if old:
                    db.execute("UPDATE bookmarks SET status=?,note=?,updated_at=? WHERE id=?", (item["status"], item.get("note", ""), stamp, old[0]))
                else:
                    db.execute(f"INSERT INTO bookmarks(id,{key},status,note,created_at,updated_at) VALUES(?,?,?,?,?,?)", (str(uuid4()), item[key], item["status"], item.get("note", ""), stamp, stamp))
        return len(bookmarks)

    def register_sources(self, sources):
        with self.connect() as db:
            for source in sources:
                row = {key: source.get(key) for key in ("id", "name", "homepage_url", "source_type", "access_status", "access_method", "verified_at", "notes", "publisher_country", "coverage")}
                row["enabled"] = int(source.get("enabled", False))
                columns = list(row)
                update = ",".join(f"{key}=excluded.{key}" for key in columns if key != "id")
                db.execute(f"INSERT INTO sources ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)}) ON CONFLICT(id) DO UPDATE SET {update}", list(row.values()))
                if source.get("adapter") == "rss":
                    # Correct archived records too, even when a feed no longer
                    # includes them. Keep cached summaries and bookmarks intact.
                    from .geography import title_places
                    for article in db.execute("SELECT id,title_original FROM content WHERE source_id=? AND is_demo=0", (source["id"],)).fetchall():
                        locations = title_places(article["title_original"])
                        countries = {place["country"] for place in locations}
                        cities = {place["city"] for place in locations if place["city"]}
                        db.execute("UPDATE content SET country=?,city=?,geography_status=?,locations_json=? WHERE id=?", (next(iter(countries)) if len(countries) == 1 else None, next(iter(cities)) if len(cities) == 1 else None, "mentioned" if locations else "unknown", json.dumps(locations, ensure_ascii=False), article["id"]))

    def ingest_records(self, content, events, links):
        inserted, updated = 0, 0
        with self.connect() as db:
            for record in content:
                old = db.execute("SELECT * FROM content WHERE canonical_url=?", (record["canonical_url"],)).fetchone()
                if old:
                    if old["is_demo"]:
                        raise ValueError("真实记录不得覆盖示例")
                    record["id"] = old["id"]
                    from .reading import READING_FIELDS, TRANSLATION_FIELDS
                    from .originals import ORIGINAL_FIELDS
                    from .articles import ARTICLE_FIELDS
                    from .editorial import EDITORIAL_FIELDS
                    original_changed = bool(record.get('original_page_url') and record['original_page_url'] != old['original_page_url'])
                    for field in ARTICLE_FIELDS:
                        if original_changed:
                            record[field] = None
                        elif field not in record:
                            record[field] = old[field]
                    for field in ORIGINAL_FIELDS:
                        if original_changed and field != 'original_page_url':
                            record[field] = None
                        elif not record.get(field) and old[field]:
                            record[field] = old[field]
                    # Missing RSS metadata must not erase a previously read page introduction.
                    for field in READING_FIELDS:
                        if not record.get(field) and old[field]:
                            record[field] = old[field]
                    reading_changed = old['title_original'] != record['title_original'] or (old['excerpt_original'] or '') != (record.get('excerpt_original') or '')
                    for field in EDITORIAL_FIELDS:
                        if original_changed or reading_changed:
                            record[field] = None
                        elif field not in record:
                            record[field] = old[field]
                    if reading_changed:
                        for field in TRANSLATION_FIELDS:
                            record[field] = None
                    if old["body_hash"] == record["body_hash"]:
                        for field in READING_FIELDS + ORIGINAL_FIELDS + ARTICLE_FIELDS + EDITORIAL_FIELDS + (TRANSLATION_FIELDS if reading_changed else ()):
                            if field in record:
                                db.execute(f"UPDATE content SET {field}=? WHERE id=?", (record[field], old['id']))
                        db.execute("UPDATE content SET fetched_at=?,raw_excerpt=? WHERE id=?", (record["fetched_at"], record.get("raw_excerpt"), old["id"]))
                        for field in ("country", "city", "geography_status", "locations_json", "kind"):
                            if field in record:
                                db.execute(f"UPDATE content SET {field}=? WHERE id=?", (record[field], old["id"]))
                        if not old["summary_zh"] and record.get("summary_zh"):
                            db.execute("UPDATE content SET title_zh=?,summary_zh=?,summary_status=?,summary_provider=?,summary_generated_at=? WHERE id=?", (record.get("title_zh"), record["summary_zh"], record["summary_status"], record.get("summary_provider"), record.get("summary_generated_at"), old["id"]))
                        continue
                    updated += 1
                else:
                    inserted += 1
                cols = list(record)
                values = ",".join(f"{key}=excluded.{key}" for key in cols if key != "id")
                db.execute(f"INSERT INTO content ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)}) ON CONFLICT(id) DO UPDATE SET {values}", list(record.values()))
            for record in events:
                cols = list(record)
                update = ",".join(f"{key}=excluded.{key}" for key in cols if key != "id")
                db.execute(f"INSERT INTO events ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)}) ON CONFLICT(id) DO UPDATE SET {update}", list(record.values()))
            for link in links:
                db.execute("INSERT OR IGNORE INTO content_events VALUES(?,?)", (link["content_id"], link["event_id"]))
        return {"inserted": inserted, "updated": updated}

    def begin_run(self, source_id):
        run_id = str(uuid4())
        with self.connect() as db:
            db.execute("INSERT INTO ingest_runs(id,source_id,started_at,status) VALUES(?,?,?,'running')", (run_id, source_id, now()))
        return run_id

    def restore_public_snapshot(self, path):
        if not Path(path).exists():
            return 0
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.register_sources(json.loads((ROOT / "config/sources.json").read_text())["sources"])
        with self.connect() as db:
            existing = db.execute("SELECT count(*) FROM content WHERE is_demo=0").fetchone()[0]
            db.execute("CREATE TABLE IF NOT EXISTS summary_usage(day TEXT PRIMARY KEY, calls INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS translation_usage(day TEXT PRIMARY KEY, calls INTEGER NOT NULL)")
            db.execute('CREATE TABLE IF NOT EXISTS editorial_usage(day TEXT PRIMARY KEY,calls INTEGER NOT NULL)')
            for item in data.get('editorial_usage', []):
                db.execute('INSERT INTO editorial_usage VALUES(?,?) ON CONFLICT(day) DO UPDATE SET calls=max(calls,excluded.calls)', (item['day'],item['calls']))
            for item in data.get('translation_usage', []):
                db.execute("INSERT INTO translation_usage VALUES(?,?) ON CONFLICT(day) DO UPDATE SET calls=max(calls,excluded.calls)", (item['day'], item['calls']))
            for item in data.get("processing_usage", []):
                db.execute("INSERT INTO summary_usage VALUES(?,?) ON CONFLICT(day) DO UPDATE SET calls=max(calls,excluded.calls)", (item["day"], item["calls"]))
            known_sources = {row[0] for row in db.execute("SELECT id FROM sources")}
            for source in data.get("source_status", []):
                if source["id"] not in known_sources:
                    continue
                key = "source-history:" + source["id"]
                previous = db.execute("SELECT value FROM job_state WHERE id=?", (key,)).fetchone()
                history = json.loads(previous[0]) if previous else {}
                history["last_success_at"] = max(filter(None, (history.get("last_success_at"), source.get("last_success_at"))), default=None)
                incoming = source.get("last_run")
                if incoming and incoming.get("started_at", "") >= (history.get("last_run") or {}).get("started_at", ""):
                    history["last_run"] = incoming
                db.execute("INSERT INTO job_state VALUES(?,?) ON CONFLICT(id) DO UPDATE SET value=excluded.value", (key, json.dumps(history)))
        if existing:
            return 0
        return self.ingest_records(data["content"], data["events"], data["content_events"])["inserted"]

    def finish_run(self, run_id, status, count=0, inserted=0, error=None):
        with self.connect() as db:
            db.execute("UPDATE ingest_runs SET finished_at=?,status=?,fetched_count=?,inserted_count=?,error=? WHERE id=?", (now(), status, count, inserted, error, run_id))

    def source_status(self):
        with self.connect() as db:
            sources = [dict(row) for row in db.execute("SELECT * FROM sources WHERE source_type!='demo'")]
            for source in sources:
                last = db.execute("SELECT started_at,finished_at,status,fetched_count,inserted_count,error FROM ingest_runs WHERE source_id=? ORDER BY started_at DESC LIMIT 1", (source["id"],)).fetchone()
                successful = db.execute("SELECT finished_at FROM ingest_runs WHERE source_id=? AND status='success' ORDER BY finished_at DESC LIMIT 1", (source["id"],)).fetchone()
                saved = db.execute("SELECT value FROM job_state WHERE id=?", ("source-history:" + source["id"],)).fetchone()
                history = json.loads(saved[0]) if saved else {}
                current = dict(last) if last else None
                restored = history.get("last_run")
                source["last_run"] = restored if restored and restored.get("started_at", "") > (current or {}).get("started_at", "") else current or restored
                source["last_success_at"] = max(filter(None, (successful[0] if successful else None, history.get("last_success_at"))), default=None)
        return sources
