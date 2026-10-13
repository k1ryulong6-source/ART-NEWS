"""Manual refresh, supervised scheduler, locks and personal deadline notifications."""
import argparse
import json
import os
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from .storage import ROOT, Store, now
from .ingestion import run_ingestion
from .enrichment import run_enrichment
from .timing import instant_passed


def notify(store, reference=None):
    created = 0
    with store.connect() as db:
        events = db.execute("SELECT events.* FROM events JOIN bookmarks ON bookmarks.event_id=events.id WHERE events.is_demo=0 AND events.date_precision='day' AND bookmarks.status!='seen'").fetchall()
        for event in events:
            event = dict(event)
            if reference is None and instant_passed(event):
                continue
            today = reference or datetime.now(ZoneInfo(event["timezone"])).date().isoformat()
            checks = [("starting", event["start_date"], "即将开始", 1), ("ending", event["end_date"], "即将结束", 7)]
            if event["event_type"] == "call_deadline":
                checks = [("deadline", event["start_date"], "即将截止", 7)]
            for kind, target, label, window in checks:
                if not target:
                    continue
                delta = (datetime.fromisoformat(target).date() - datetime.fromisoformat(today).date()).days
                if event.get("time_status") == "conflict" and delta == 0:
                    continue
                if 0 <= delta <= window:
                    id = event["id"] + ":" + kind + ":" + target
                    title = f"{event['title_zh'] or event['title_original']}：{'今天' if delta == 0 else str(delta)+'天后'}{label[2:]}"
                    created += db.execute("INSERT OR IGNORE INTO notifications(id,event_id,title,created_at) VALUES(?,?,?,?)", (id, event["id"], title, now())).rowcount
                    db.execute("UPDATE notifications SET title=? WHERE id=?", (title, id))
    return created


def refresh(store, source_ids=None):
    stamp = now()
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute("SELECT value FROM job_state WHERE id='refresh-lock'").fetchone()
        if existing and datetime.fromisoformat(existing[0]) > datetime.now(timezone.utc):
            return {"status": "busy"}
        expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        db.execute("INSERT INTO job_state VALUES('refresh-lock',?) ON CONFLICT(id) DO UPDATE SET value=excluded.value", (expiry,))
    try:
        sources = run_ingestion(store, source_ids)
        from .reading import enrich_reading
        from .translation import run_translation
        reading = enrich_reading(store, int(os.getenv('READING_PAGE_LIMIT', '20')))
        from .articles import collect_articles
        articles = collect_articles(store, int(os.getenv('ARTICLE_PAGE_LIMIT', '60')))
        try:
            translations = run_translation(store)
            from .article_translation import translate_articles
            translations['articles'] = translate_articles(store)
        except Exception as exc:
            translations = {'status': 'configuration_error', 'error': type(exc).__name__}
        try:
            summaries = run_enrichment(store)
        except Exception as exc:
            summaries = {"status": "configuration_error", "error": type(exc).__name__}
        reminders = notify(store)
        from .mail import send_notifications
        email = send_notifications(store)
        result = {"status": "completed", "started_at": stamp, "finished_at": now(), "sources": sources, "summaries": summaries, "reading": reading, "articles": articles, "translations": translations, "new_notifications": reminders, "email": email}
        with store.connect() as db:
            db.execute("INSERT INTO job_state VALUES('last-refresh',?) ON CONFLICT(id) DO UPDATE SET value=excluded.value", (json.dumps(result),))
        return result
    finally:
        with store.connect() as db:
            db.execute("DELETE FROM job_state WHERE id='refresh-lock'")


def schedule(store, interval_hours=12, stop_after=None):
    if interval_hours < 1:
        raise ValueError("刷新间隔至少为一小时")
    runs = 0
    while True:
        print(json.dumps(refresh(store), ensure_ascii=False), flush=True)
        runs += 1
        if stop_after and runs >= stop_after:
            return
        # Short waits allow signals to stop the supervised process cleanly.
        next_run = time.monotonic() + interval_hours * 3600
        while time.monotonic() < next_run:
            time.sleep(max(0, min(30, next_run - time.monotonic())))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--schedule", action="store_true")
    parser.add_argument("--interval-hours", type=float, default=12)
    parser.add_argument("--source", action="append")
    args = parser.parse_args()
    store = Store(os.getenv("CULTURE_DESK_DB", ROOT / "runtime/culture-desk.db"))
    if args.schedule:
        schedule(store, args.interval_hours)
    else:
        print(json.dumps(refresh(store, args.source), ensure_ascii=False, indent=2))
