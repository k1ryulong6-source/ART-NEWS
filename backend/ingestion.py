"""Verified public sources -> metadata, short excerpts and local-date events."""
import argparse
import hashlib
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import date, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from bs4 import BeautifulSoup
from .storage import ROOT, Store, now

MAX_BYTES = 6_000_000
GEAR = re.compile(r"器材评测|购买指南|カメラレビュー|レンズレビュー|カメラ比較|機材レビュー|(?:(?:camera|lens|tripod|lighting gear).{0,25}(?:review|comparison|test|buying guide))|(?:(?:review|test|buying guide).{0,25}(?:camera|lens|tripod))", re.I)
BUZZ = re.compile(r"behind.the.scenes|casting|cast joins|片場|舞台裏|撮影秘話|幕后|选角|趣闻|in talks to", re.I)


def stable_id(value):
    return "live-" + hashlib.sha256(value.encode()).hexdigest()[:24]


def canonical_url(value):
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("来源链接必须是 HTTP(S)")
    query = [(key, val) for key, val in parse_qsl(parts.query) if not key.startswith("utm_") and key not in ("fbclid", "gclid")]
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", urlencode(query), ""))


def get_url(url, timeout=20):
    request = Request(url, headers={"User-Agent": "CultureDesk/0.2 personal cultural reader", "Accept": "application/rss+xml,application/xml,text/html;q=0.9"})
    for attempt in range(2):
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = response.read(MAX_BYTES + 1)
                if len(payload) > MAX_BYTES:
                    raise ValueError("来源响应超过 6 MB 上限")
                return payload
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt:
                raise
        except (URLError, TimeoutError):
            if attempt:
                raise
        time.sleep(.5)


def text_only(value, limit=1200):
    soup = BeautifulSoup(value or "", "html.parser")
    for element in soup(["script", "style"]):
        element.decompose()
    return " ".join(soup.get_text(" ", strip=True).split())[:limit]


def content_record(source, title, url, excerpt="", published=None, summary=None):
    stamp = now()
    url = canonical_url(url)
    return {"id": stable_id(url), "source_id": source["id"], "canonical_url": url, "title_original": title.strip(), "title_zh": None, "summary_zh": summary, "raw_excerpt": excerpt[:1200], "body_hash": hashlib.sha256((title + excerpt + (summary or "")).encode()).hexdigest(), "channel": source["channels"][0], "kind": "industry_buzz" if BUZZ.search(title) else "news", "country": source.get("country"), "city": source.get("city"), "language": source["language"], "evidence_status": "official_confirmed" if source["source_type"] == "official" else "media_reported", "published_at": published, "fetched_at": stamp, "updated_at": stamp, "summary_status": "ready" if summary else "pending", "summary_provider": "structured-fields" if summary else None, "summary_model": None, "summary_generated_at": stamp if summary else None, "is_demo": 0}


def rss_records(source, payload):
    root = ET.fromstring(payload.lstrip(b"\xef\xbb\xbf \t\r\n"))
    items = root.findall(".//item")
    if not items:
        raise ValueError("RSS 未包含 item，需重新核实来源结构")
    records = []
    for item in items:
        title, link = item.findtext("title"), item.findtext("link")
        if not title or not link:
            continue
        excerpt = text_only(item.findtext("description") or item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded"))
        categories = " ".join(x.text or "" for x in item.findall("category"))
        if GEAR.search(title + " " + categories):
            continue
        published = None
        try:
            parsed = parsedate_to_datetime(item.findtext("pubDate"))
            published = parsed.replace(tzinfo=parsed.tzinfo or timezone.utc).astimezone(timezone.utc).isoformat()
        except (TypeError, ValueError):
            pass
        record = content_record(source, title, link, excerpt, published)
        if source["language"] == "zh":
            record["title_zh"] = title.strip()
            if excerpt:
                record["summary_zh"] = "来源摘录：" + excerpt[:300]
                record["summary_status"] = "ready"
                record["summary_provider"] = "source-excerpt"
        if re.search(r"photobook|写真集|摄影集", title, re.I):
            record["kind"] = "photobook"
        elif re.search(r"interview|インタビュー|访谈", title, re.I):
            record["kind"] = "interview"
        records.append(record)
    return records, [], []


def event_record(source, content, kind, start, end=None, venue=None, city=None):
    date.fromisoformat(start)
    if end:
        date.fromisoformat(end)
        if end < start:
            raise ValueError("活动结束日期早于开始日期")
    url = content["canonical_url"]
    return {"id": stable_id(source["id"] + url + kind + "JP"), "title_original": content["title_original"], "title_zh": None, "channel": content["channel"], "event_type": kind, "country": "JP", "city": city, "venue": venue, "start_date": start, "end_date": end, "date_precision": "day", "date_text_original": start + ("〜" + end if end else ""), "timezone": "Asia/Tokyo", "price_text": None, "closure_note": None, "booking_url": None, "evidence_url": url, "evidence_status": content["evidence_status"], "verified_at": now(), "updated_at": now(), "is_demo": 0}


def eiga_records(source, payload):
    soup = BeautifulSoup(payload, "html.parser")
    records, events, links = [], [], []
    for block in soup.select("div.list-block"):
        title_link = block.select_one("h3.title a")
        heading = block.find_previous("h2")
        if not title_link or not heading:
            continue
        match = re.search(r"(\d{4})年\s*(\d{1,2})月(\d{1,2})日", heading.get_text(" ", strip=True))
        if not match:
            continue
        start = "-".join([match[1], match[2].zfill(2), match[3].zfill(2)])
        excerpt_node = block.select_one("p.txt")
        excerpt = excerpt_node.get_text(" ", strip=True)[:500] if excerpt_node else ""
        streaming = bool(re.search(r"(?:Netflix|Amazon Prime|Disney|配信)", excerpt)) and not block.select_one('a[href$="/theater/"]')
        # Missing cinema links alone is insufficient to infer a streaming release.
        if not streaming and not block.select_one('a[href$="/theater/"]'):
            continue
        kind = "streaming_release" if streaming else "cinema_release"
        title = title_link.get_text(" ", strip=True)
        summary = f"《{title}》在日本的{'流媒体上线' if streaming else '院线上映'}日期为 {start}。日期来自映画.com 上映安排，请在出行前核对原文。"
        record = content_record(source, title, urljoin(source["feed_url"], title_link["href"]), excerpt, summary=summary)
        event = event_record(source, record, kind, start)
        records.append(record); events.append(event); links.append({"content_id": record["id"], "event_id": event["id"]})
    if not records:
        raise ValueError("没有解析到上映安排，页面结构可能变化")
    return records, events, links


def top_records(source, payload):
    soup = BeautifulSoup(payload, "html.parser")
    records, events, links, seen = [], [], [], set()
    for anchor in soup.select('a[href*="/exhibition/"]'):
        dates = [node.get("data-date") for node in anchor.select("[data-date]")]
        image = anchor.find("img")
        if len(dates) != 2 or not image or not image.get("alt"):
            continue
        url = urljoin(source["feed_url"], anchor["href"])
        if url in seen:
            continue
        seen.add(url)
        title = image["alt"]
        summary = f"东京都写真美术馆展览《{title}》，展期 {dates[0]} 至 {dates[1]}。展期取自场馆官网；票价、休馆日与预约以原文为准。"
        record = content_record(source, title, url, summary=summary)
        record["city"] = "东京"
        event = event_record(source, record, "exhibition", dates[0], dates[1], "东京都写真美术馆", "东京")
        records.append(record); events.append(event); links.append({"content_id": record["id"], "event_id": event["id"]})
    if not records:
        raise ValueError("没有解析到带确切展期的展览，需核实结构")
    return records, events, links


ADAPTERS = {"rss": rss_records, "eiga_releases": eiga_records, "top_exhibitions": top_records}


def run_ingestion(store, source_ids=None, fetcher=get_url):
    config = json.loads((ROOT / "config/sources.json").read_text())
    disabled = store.preferences().get("disabled_sources", [])
    for source in config["sources"]:
        if source["id"] in disabled:
            source["enabled"] = False
    store.register_sources(config["sources"])
    results = []
    for source in config["sources"]:
        if not source.get("enabled") or source["access_status"] != "reviewed" or (source_ids and source["id"] not in source_ids):
            continue
        run_id = store.begin_run(source["id"])
        try:
            records, events, links = ADAPTERS[source.get("adapter", "rss")](source, fetcher(source["feed_url"]))
            counts = store.ingest_records(records, events, links)
            store.finish_run(run_id, "success", len(records), counts["inserted"])
            results.append({"source": source["id"], "status": "success", "fetched": len(records), "events": len(events), **counts})
        except Exception as exc:
            # Record exception type/status only; URLs and request headers may carry credentials.
            message = type(exc).__name__ + (f" HTTP {exc.code}" if isinstance(exc, HTTPError) else "")
            store.finish_run(run_id, "failed", error=message)
            results.append({"source": source["id"], "status": "failed", "error": message})
    return results


if __name__ == "__main__":
    import os
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="append")
    args = parser.parse_args()
    store = Store(os.getenv("CULTURE_DESK_DB", ROOT / "runtime/culture-desk.db"))
    print(json.dumps(run_ingestion(store, args.source), ensure_ascii=False, indent=2))
