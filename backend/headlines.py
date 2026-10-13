"""Reviewed title-only sidecars, kept separate from full article translations."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_headlines(snapshot, directory=None):
    content = {row["id"]: row for row in snapshot.get("content", [])}
    result = {}
    for path in sorted(Path(directory or ROOT / "data/headlines").glob("*.json")):
        pack = json.loads(path.read_text(encoding="utf-8"))
        identifier = pack.get("id", "")
        title = pack.get("title_zh")
        review = pack.get("review") or {}
        if (pack.get("schema_version") != 1 or not re.fullmatch(r"live-[a-f0-9]{24}", identifier)
                or path.stem != identifier or not isinstance(pack.get("source_title"), str)
                or not isinstance(title, str) or not 1 <= len(title.strip()) <= 600
                or not re.search(r"[\u4e00-\u9fff]", title)
                or review.get("approved") is not True or review.get("issues") != []
                or not isinstance(review.get("method"), str) or not review["method"].strip()):
            raise ValueError(f"Invalid reviewed headline: {path.name}")
        row = content.get(identifier)
        # A refreshed headline must not silently inherit a translation of its old wording.
        if row and row["title_original"] == pack["source_title"]:
            result[identifier] = {"source_title": pack["source_title"], "title_zh": title.strip()}

    events = {row["id"]: row for row in snapshot.get("events", [])}
    for link in snapshot.get("content_events", []):
        event, row = events.get(link["event_id"]), content.get(link["content_id"])
        if not event or not row or event["title_original"] != row["title_original"]:
            continue
        if row.get("editorial_status") == "reviewed" and row.get("editorial_title_zh"):
            result[event["id"]] = {"source_title": event["title_original"], "title_zh": row["editorial_title_zh"]}
        elif row["id"] in result:
            result[event["id"]] = result[row["id"]]
    return result
