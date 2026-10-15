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
from .geography import title_places

MAX_BYTES = 6_000_000
GEAR = re.compile(r"器材评测|购买指南|カメラレビュー|レンズレビュー|カメラ比較|機材レビュー|(?:(?:camera|lens|tripod|lighting gear).{0,25}(?:review|comparison|test|buying guide))|(?:(?:review|test|buying guide).{0,25}(?:camera|lens|tripod))", re.I)
GEAR_MULTILINGUAL = re.compile(r"(?:(?:test|comparatif|comparaison|guide d'achat|prueba|comparativa|guía de compra|teste|comparativo|guia de compra).{0,35}(?:appareil photo|objectif|cámara|câmera|lente|objetiva))|(?:(?:appareil photo|objectif|cámara|câmera|lente|objetiva).{0,35}(?:review|test|teste|comparatif|comparativa|comparativo|guia de compra))", re.I)
BUZZ = re.compile(r"behind.the.scenes|casting|cast joins|片場|舞台裏|撮影秘話|幕后|选角|趣闻|in talks to|reveló|detrás de cámaras", re.I)


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
    fixed = source.get("adapter") in ("eiga_releases", "top_exhibitions", "tate_exhibitions", "map_exhibitions", "zeitz_exhibitions", "diaphana_releases", "bfi_programme", "wpo_calls", "mmca_exhibitions")
    locations = [{"country": source["country"], "city": source.get("city"), "basis": "source_structured"}] if fixed and source.get("country") else title_places(title)
    countries = {place["country"] for place in locations}
    cities = {place["city"] for place in locations if place["city"]}
    from .reading import short_excerpt
    return {"excerpt_original": short_excerpt(excerpt) or None, "excerpt_origin": "rss" if excerpt else None, "id": stable_id(url), "source_id": source["id"], "canonical_url": url, "title_original": title.strip(), "title_zh": None, "summary_zh": summary, "raw_excerpt": excerpt[:1200], "body_hash": hashlib.sha256((title + excerpt + (summary or "")).encode()).hexdigest(), "channel": source["channels"][0], "kind": "industry_buzz" if BUZZ.search(title) else "news", "country": next(iter(countries)) if len(countries) == 1 else None, "city": next(iter(cities)) if len(cities) == 1 else None, "geography_status": "confirmed" if fixed else "mentioned" if locations else "unknown", "locations_json": json.dumps(locations, ensure_ascii=False), "language": source["language"], "evidence_status": "official_confirmed" if source["source_type"] == "official" else "media_reported", "published_at": published, "fetched_at": stamp, "updated_at": stamp, "summary_status": "ready" if summary else "pending", "summary_provider": "structured-fields" if summary else None, "summary_model": None, "summary_generated_at": stamp if summary else None, "is_demo": 0}


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
        if GEAR.search(title + " " + categories) or GEAR_MULTILINGUAL.search(title + " " + categories):
            continue
        if source.get("exclude_title_regex") and re.search(source["exclude_title_regex"], title, re.I):
            continue
        published = None
        try:
            parsed = parsedate_to_datetime(item.findtext("pubDate"))
            published = parsed.replace(tzinfo=parsed.tzinfo or timezone.utc).astimezone(timezone.utc).isoformat()
        except (TypeError, ValueError):
            pass
        record = content_record(source, title, link, excerpt, published)
        for rule in source.get('channel_rules', []):
            if rule['channel'] in source['channels'] and re.search(rule['pattern'], link + ' ' + categories, re.I):
                record['channel'] = rule['channel']
                break
        from .reading import rss_image
        record.update(rss_image(source, item, (item.findtext('description') or '') + (item.findtext('{http://purl.org/rss/1.0/modules/content/}encoded') or ''), record['canonical_url']))
        if source["language"] == "zh":
            record["title_zh"] = title.strip()
            if excerpt:
                record["summary_zh"] = "来源摘录：" + excerpt[:300]
                record["summary_status"] = "ready"
                record["summary_provider"] = "source-excerpt"
        if record["kind"] != "industry_buzz" and re.search(r"photobook|写真集|摄影集|livre photo|fotolibro|fotolivro", title + " " + categories, re.I):
            record["kind"] = "photobook"
        elif record["kind"] != "industry_buzz" and re.search(r"interview|インタビュー|访谈|entretien|entrevista", title + " " + categories, re.I):
            record["kind"] = "interview"
        records.append(record)
    return records, [], []


def event_record(source, content, kind, start, end=None, venue=None, city=None, country=None, timezone=None):
    date.fromisoformat(start)
    if end:
        date.fromisoformat(end)
        if end < start:
            raise ValueError("活动结束日期早于开始日期")
    url = content["canonical_url"]
    country = country or source.get("country")
    timezone = timezone or ("Asia/Tokyo" if country == "JP" else None)
    if not country or not timezone:
        raise ValueError("活动需要明确国家与当地时区")
    from zoneinfo import ZoneInfo
    ZoneInfo(timezone)
    return {"id": stable_id(source["id"] + url + kind + country), "title_original": content["title_original"], "title_zh": None, "channel": content["channel"], "event_type": kind, "country": country, "city": city, "venue": venue, "start_date": start, "end_date": end, "date_precision": "day", "date_text_original": start + ("〜" + end if end else ""), "timezone": timezone, "start_at": None, "end_at": None, "deadline_at": None, "time_status": None, "time_note": None, "eligibility_note": None, "booking_status": None, "price_text": None, "closure_note": None, "booking_url": None, "evidence_url": url, "evidence_status": content["evidence_status"], "verified_at": now(), "updated_at": now(), "is_demo": 0}


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
        from .reading import image_fields
        record.update(image_fields(source, image.get('data-src') or image.get('src'), url, title))
        event = event_record(source, record, "exhibition", dates[0], dates[1], "东京都写真美术馆", "东京")
        records.append(record); events.append(event); links.append({"content_id": record["id"], "event_id": event["id"]})
    if not records:
        raise ValueError("没有解析到带确切展期的展览，需核实结构")
    return records, events, links


MONTHS = {name: index for index, name in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1)}


def tate_records(source, payload):
    soup = BeautifulSoup(payload, "html.parser")
    records, events, links, seen = [], [], [], set()
    for anchor in soup.select('a[href*="/whats-on/tate-modern/"]'):
        title_node, dates = anchor.select_one(".card__title"), anchor.select_one(".event-info__date")
        tags, venue = anchor.select_one(".card-tags"), anchor.select_one(".event-info__venue")
        if not title_node or not dates or not tags or not venue or tags.get_text(" ", strip=True) != "Exhibition" or venue.get_text(" ", strip=True) != "Tate Modern":
            continue
        original = dates.get_text(" ", strip=True)
        match = re.fullmatch(r"(\d{1,2}) ([A-Za-z]{3})(?: (\d{4}))?\s*[–—-]\s*(\d{1,2}) ([A-Za-z]{3}) (\d{4})", original)
        if not match or match[2] not in MONTHS or match[5] not in MONTHS:
            continue
        # Inherit the explicitly printed year only for a non-cross-year range.
        if not match[3] and MONTHS[match[2]] > MONTHS[match[5]]:
            continue
        start = date(int(match[3] or match[6]), MONTHS[match[2]], int(match[1])).isoformat()
        end = date(int(match[6]), MONTHS[match[5]], int(match[4])).isoformat()
        url = canonical_url(urljoin(source["feed_url"], anchor["href"]))
        if url in seen:
            continue
        seen.add(url)
        title = title_node.get_text(" ", strip=True)
        summary = f"伦敦 Tate Modern 展览《{title}》，展期 {start} 至 {end}。展期来自场馆官网；票价、开放日及预约请核对原文。"
        record = content_record(source, title, url, summary=summary)
        from .reading import image_fields
        image = anchor.find('img')
        if image: record.update(image_fields(source, image.get('data-src') or image.get('src'), url, title))
        description = anchor.select_one(".card__description")
        if re.search(r"photograph", title + " " + (description.get_text() if description else ""), re.I):
            record["channel"] = "photography"
        event = event_record(source, record, "exhibition", start, end, "Tate Modern", "伦敦", "GB", "Europe/London")
        event["date_text_original"] = original
        records.append(record); events.append(event); links.append({"content_id": record["id"], "event_id": event["id"]})
    if not records:
        raise ValueError("没有解析到完整展期，需核实场馆页面结构")
    return records, events, links


def museum_record(source, title, url, start, end, original):
    summary = f"{source['city']} {source['venue']} 展览《{title}》，展期 {start} 至 {end}。日期来自场馆官网；票价、开放日与预约请核对原文。"
    record = content_record(source, title, url, summary=summary)
    event = event_record(source, record, "exhibition", start, end, source["venue"], source["city"], source["country"], source["timezone"])
    event["date_text_original"] = original
    return record, event, {"content_id": record["id"], "event_id": event["id"]}


def map_records(source, payload):
    soup = BeautifulSoup(payload, "html.parser")
    records, events, links, seen = [], [], [], set()
    visitor_info = soup.select_one(".footer__top__info")
    visitor_text = visitor_info.get_text(" ", strip=True) if visitor_info else ""
    for card in soup.select("article.rds-card"):
        category = card.select_one(".rds-card__category-location")
        title, dates, anchor = card.select_one(".rds-card__title"), card.select_one(".rds-card__date"), card.select_one('a[href*="/exhibition/"]')
        if not category or category.get_text(" ", strip=True) != "Exhibitions | MAP Bengaluru" or not title or not dates or not anchor:
            continue
        original = dates.get_text(" ", strip=True)
        match = re.fullmatch(r"([A-Za-z]{3}) (\d{1,2}), (\d{4})\s*[-–]\s*([A-Za-z]{3}) (\d{1,2}), (\d{4})", original)
        if not match or match[1] not in MONTHS or match[4] not in MONTHS:
            continue
        start, end = date(int(match[3]), MONTHS[match[1]], int(match[2])).isoformat(), date(int(match[6]), MONTHS[match[4]], int(match[5])).isoformat()
        url = canonical_url(urljoin(source["feed_url"], anchor["href"]))
        if url in seen:
            continue
        seen.add(url)
        record, event, link = museum_record(source, title.get_text(" ", strip=True), url, start, end, original)
        if "Monday · Closed" in visitor_text:
            event["closure_note"] = "馆方访问说明：周一闭馆；节假日及特别安排请出行前核对官网。"
        if "Free entry to all exhibitions on Tuesdays" in visitor_text:
            event["price_text"] = "馆方说明周二所有展览免费；其他日期票价以官网为准。"
        records.append(record); events.append(event); links.append(link)
    if not records:
        raise ValueError("MAP 未发现带完整日期的现场展览")
    return records, events, links


def zeitz_records(source, payload):
    soup = BeautifulSoup(payload, "html.parser")
    records, events, links, seen = [], [], [], set()
    for card in soup.select("article.zeitz-card"):
        category = card.select_one(".zeitz-card__subtitle")
        title, dates, anchor = card.select_one(".zeitz-card__title"), card.select_one(".zeitz-card__date"), card.select_one('a[href*="/exhibition/"]')
        if not category or category.get_text(strip=True) != "EXHIBITIONS" or not title or not dates or not anchor:
            continue
        name = title.get_text(" ", strip=True)
        # An exhibition-season announcement is not an individual exhibition.
        if re.search(r"announces|exhibition season", name, re.I):
            continue
        original = dates.get_text(" ", strip=True)
        match = re.fullmatch(r"(\d{1,2}) ([A-Za-z]{3}) (\d{4})\s*[-–]\s*(\d{1,2}) ([A-Za-z]{3}) (\d{4})", original)
        if not match or match[2] not in MONTHS or match[5] not in MONTHS:
            continue
        start, end = date(int(match[3]), MONTHS[match[2]], int(match[1])).isoformat(), date(int(match[6]), MONTHS[match[5]], int(match[4])).isoformat()
        url = canonical_url(urljoin(source["feed_url"], anchor["href"]))
        if url in seen:
            continue
        seen.add(url)
        record, event, link = museum_record(source, name, url, start, end, original)
        records.append(record); events.append(event); links.append(link)
    if not records:
        raise ValueError("Zeitz 未发现带完整日期的单展")
    return records, events, links


ADAPTERS = {"rss": rss_records, "eiga_releases": eiga_records, "top_exhibitions": top_records, "tate_exhibitions": tate_records, "map_exhibitions": map_records, "zeitz_exhibitions": zeitz_records}


def run_ingestion(store, source_ids=None, fetcher=get_url):
    from .programmes import diaphana_records, bfi_records, wpo_records, mmca_records
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    extra_adapters = {"diaphana_releases": diaphana_records, "bfi_programme": bfi_records, "wpo_calls": wpo_records, "mmca_exhibitions": mmca_records}
    config = json.loads((ROOT / "config/sources.json").read_text())
    disabled = store.preferences().get("disabled_sources", [])
    for source in config["sources"]:
        if source["id"] in disabled:
            source["enabled"] = False
    store.register_sources(config["sources"])
    results = []
    from .editorial_regions import ordered_sources
    for source in ordered_sources(config["sources"]):
        if not source.get("enabled") or source["access_status"] != "reviewed" or (source_ids and source["id"] not in source_ids):
            continue
        run_id = store.begin_run(source["id"])
        try:
            method = source.get("adapter", "rss")
            handler = extra_adapters.get(method) or ADAPTERS[method]
            pages = source.get("pages") or [{"url": source["feed_url"]}]
            if method == "bfi_programme":
                local = datetime.now(ZoneInfo(source["timezone"])).date()
                first, last = date.fromisoformat(source["season_start"]), date.fromisoformat(source["season_end"])
                start = min(last, max(first, local))
                pages = [{"url": source["url_template"].format(day=(start+timedelta(days=i)).strftime("%Y%m%d"))} for i in range(3) if start+timedelta(days=i) <= last]
            records_by_id, events_by_id, relations, page_errors = {}, {}, set(), []
            for page in pages[:6]:
                current = {**source, **page, "feed_url": page["url"]}
                try:
                    records, events, links = handler(current, fetcher(page["url"]))
                except Exception as exc:
                    message = type(exc).__name__ + (f" HTTP {exc.code}" if isinstance(exc, HTTPError) else "")
                    page_errors.append({'url': page['url'], 'error': message})
                    continue
                records_by_id.update({r["id"]: r for r in records})
                events_by_id.update({e["id"]: e for e in events})
                relations.update((l["content_id"], l["event_id"]) for l in links)
            records, events = list(records_by_id.values()), list(events_by_id.values())
            links = [{"content_id": c, "event_id": e} for c, e in sorted(relations)]
            counts = store.ingest_records(records, events, links)
            # A failed page does not discard successful siblings. The source run
            # remains failed in durable history until every configured page works.
            status = 'partial' if records and page_errors else 'failed' if page_errors else 'success'
            error = '; '.join(e['error'] for e in page_errors) or None
            store.finish_run(run_id, 'failed' if page_errors else 'success', len(records), counts['inserted'], error)
            result = {"source": source["id"], "status": status, "fetched": len(records), "events": len(events), **counts}
            if page_errors:
                result.update(error=error, page_errors=page_errors)
            results.append(result)
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
