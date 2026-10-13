#!/usr/bin/env python3
"""Check the handoff bundle, config, demo records and executable SQL contract."""

import json
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def check_tasks():
    data = read_json("tasks.json")
    tasks = data["tasks"]
    by_id = {task["id"]: task for task in tasks}
    require(len(by_id) == len(tasks), "Duplicate task IDs")
    for task in tasks:
        require(task["status"] in data["status_values"], "Unknown task status")
        require(task["acceptance"], f"Missing acceptance: {task['id']}")
        date.fromisoformat(task["updated_at"])
        if task["status"] in ("doing", "done"):
            require(task["owner"], f"Missing task owner: {task['id']}")
        if task["status"] == "done":
            require(task["evidence"], f"Missing task evidence: {task['id']}")
        for dep in task["depends_on"]:
            require(dep in by_id, f"Missing dependency: {dep}")
            if task["status"] in ("doing", "done"):
                require(by_id[dep]["status"] == "done", f"Unfinished dependency: {dep}")
    visiting, visited = set(), set()

    def walk(task_id):
        require(task_id not in visiting, f"Task dependency cycle: {task_id}")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dep in by_id[task_id]["depends_on"]:
            walk(dep)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in by_id:
        walk(task_id)
    print(f"PASS: {len(tasks)} tasks; dependency graph is consistent")


def check_config():
    prefs = read_json("config/preferences.json")
    require("equipment_review" in prefs["excluded_topics"], "Equipment reviews must be excluded")
    require(0 <= prefs["industry_buzz"]["max_share"] <= 1, "Invalid buzz share")
    require(prefs["daily_selection_limit"] > 0, "Invalid selection limit")
    require(not prefs["industry_buzz"]["include_unverified_in_today"], "Unverified gossip cannot enter today")
    ZoneInfo(prefs["reading_timezone"])
    sources = read_json("config/sources.json")["sources"]
    require(len({source["id"] for source in sources}) == len(sources), "Duplicate source IDs")
    for source in sources:
        require(source["access_status"] in ("unverified", "reviewed"), "Invalid source status")
        if source["enabled"]:
            require(source["access_status"] == "reviewed", "Enabled source is not reviewed")
            require(source["verified_at"] and source["access_method"], "Enabled source lacks verification")
            if source["access_method"] in ("rss", "api"):
                require(source["feed_url"], "Enabled feed source lacks endpoint")
    print(f"PASS: preferences and {len(sources)} candidate sources")


def insert_record(connection, table, record):
    columns = list(record)
    # table and columns come only from this bundle's fixed schema/demo records.
    known = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    require(set(columns) <= known, f"Unknown columns for {table}")
    names = ", ".join(columns)
    placeholders = ", ".join("?" for _ in columns)
    connection.execute(f"INSERT INTO {table} ({names}) VALUES ({placeholders})", [record[c] for c in columns])


def check_sql_and_demo():
    demo = read_json("data/demo.json")
    require("虚构" in demo["notice"], "Demo notice is missing")
    with sqlite3.connect(":memory:") as connection:
        sql = (ROOT / "schema.sql").read_text(encoding="utf-8")
        connection.executescript(sql)
        connection.executescript(sql)
        require(connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1, "Foreign keys disabled")
        for table in ("sources", "content", "events", "content_events"):
            for record in demo[table]:
                if table in ("content", "events"):
                    require(record["is_demo"] == 1, "Unmarked demo record")
                if table == "events":
                    ZoneInfo(record["timezone"])
                    if record["date_precision"] == "day":
                        date.fromisoformat(record["start_date"])
                        if record.get("end_date"):
                            date.fromisoformat(record["end_date"])
                    elif record["date_precision"] == "month":
                        date.fromisoformat(record["start_date"] + "-01")
                    require("example.invalid" in record["evidence_url"], "Demo URL must be fictional")
                if table == "content":
                    require("example.invalid" in record["canonical_url"], "Demo URL must be fictional")
                    for field in ("published_at", "fetched_at", "updated_at"):
                        if record.get(field):
                            timestamp = datetime.fromisoformat(record[field].replace("Z", "+00:00"))
                            require(timestamp.tzinfo is not None, "Content timestamps must include timezone")
                insert_record(connection, table, record)
        require(not connection.execute("PRAGMA foreign_key_check").fetchall(), "Foreign key errors")
        release_rows = connection.execute(
            "SELECT country, start_date, timezone FROM events WHERE event_type='cinema_release' ORDER BY country"
        ).fetchall()
        require(len(release_rows) == 2, "Expected separate country releases")
        require(release_rows[0][1] != release_rows[1][1], "Country dates accidentally merged")
        require(any(row[0] == "JP" and row[2] == "Asia/Tokyo" for row in release_rows), "Missing Japan timezone")
        require(connection.execute("SELECT count(*) FROM content WHERE kind='industry_buzz'").fetchone()[0] == 1,
                "Expected a marked buzz example")
    print("PASS: SQL initializes twice; demo imports; country dates and foreign keys are valid")


def main():
    for relative in ("README.md", "AGENTS.md", "docs/HANDOFF.md", "docs/PRODUCT.md",
                     "docs/ARCHITECTURE.md", "docs/SOURCES.md", "docs/DECISIONS.md", "docs/NEXT_AI_PROMPT.md"):
        require((ROOT / relative).is_file(), f"Missing handoff document: {relative}")
    check_tasks()
    check_config()
    check_sql_and_demo()
    print("PASS: handoff foundation is consistent; application features are not implemented yet")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, sqlite3.Error) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
