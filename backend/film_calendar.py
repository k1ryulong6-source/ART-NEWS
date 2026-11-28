"""Published cinema showtimes and streaming announcements, separate from news."""
import calendar
import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
from threading import Lock
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from .exhibitions import normalized
from .snapshot_files import encoded, replace_file
from .storage import ROOT

DATA = ROOT / 'data/film-calendar.json'
REGISTRY = ROOT / 'config/film-calendar.json'
MONTHS = {name.lower(): n for n, name in enumerate(calendar.month_name) if n}


def read_calendar(path=DATA):
    if not path.exists():
        return {'schema_version': 1, 'generated_at': None, 'items': [], 'sources': {}}
    value = json.loads(path.read_bytes())
    if value.get('schema_version') != 1 or not isinstance(value.get('items'), list) or not isinstance(value.get('sources'), dict):
        raise ValueError('invalid_film_calendar')
    return value


def calendar_event_allowed(row):
    if row.get('event_type') != 'streaming_release':
        return True
    proof = urlsplit(row.get('premiere_source_url') or '')
    return (row.get('premiere_basis') in ('official_announcement', 'verified_release', 'reported_premiere')
            and proof.scheme == 'https' and bool(proof.hostname) and bool(row.get('platform'))
            and row.get('date_precision') == 'day' and re.fullmatch(r'\d{4}-\d{2}-\d{2}', row.get('start_date') or '')
            and not row.get('program'))


def text(node):
    return ' '.join(node.get_text(' ', strip=True).split()) if node else ''


def film_image(value, page):
    from .reading import public_url

    if not isinstance(value, str) or re.search(
            r'/(?:noimg(?:/|\.)|no_poster_image\.|npw\.gif$|placeholder(?:/|\.)|default[-_](?:movie|poster))',
            urlsplit(value).path, re.I):
        return None
    if value.startswith('http://') and urlsplit(value).hostname == urlsplit(page).hostname:
        value = 'https://' + value.removeprefix('http://')
    return public_url(value, page)


def local_day(label, reference, month=None):
    value = unicodedata.normalize('NFKC', label)
    exact = re.search(r'(20\d{2})[-年/](\d{1,2})[-月/](\d{1,2})', value)
    if exact:
        return date(*map(int, exact.groups()))
    md = re.search(r'(\d{1,2})[/月](\d{1,2})', value)
    lone = re.fullmatch(r'\s*(\d{1,2})(?:日|\s*\(.*?\))?\s*', value)
    if md:
        month, day = map(int, md.groups())
    elif lone and month:
        day = int(lone[1])
    else:
        return None
    candidates = []
    for year in (reference.year - 1, reference.year, reference.year + 1):
        try:
            candidates.append(date(year, month, day))
        except ValueError:
            pass
    return min(candidates, key=lambda option: abs((option-reference).days)) if candidates else None


def screening(source, title, day, clock, *, proof=None, booking=None, screen=None, programme=None):
    stamp = re.match(r'^([0-2]?\d)[:：]([0-5]\d)(?!\d)', unicodedata.normalize('NFKC', clock))
    if not title or not day or not stamp:
        return None
    hour, minute = map(int, stamp.groups())
    when = datetime.combine(day, time(hour % 24, minute), ZoneInfo(source['timezone'])) + timedelta(days=hour // 24)
    record = base(source, title, when.date().isoformat(), 'day', 'cinema_screening', proof)
    return {**record, 'start_at': when.isoformat(), 'venue': source['venue'], 'city': source['city'],
            'auditorium': screen, 'booking_url': booking, 'programme_url': programme}


def base(source, title, start, precision, kind, proof=None):
    return {'title_original': title, 'start_date': start, 'date_precision': precision, 'event_type': kind,
            'channel': 'film', 'country': source.get('country', 'GLOBAL'), 'timezone': source['timezone'],
            'source_id': source['id'], 'source_name': source['name'], 'platform': source.get('platform'),
            'evidence_status': 'official_confirmed', 'evidence_url': proof or source['url']}


def parse_screenings(soup, source, today):
    from .exhibition_sources import linked_url
    adapter = source['adapter']
    if adapter == 'eurospace':
        for day in soup.select('article:has(.scrolltable)'):
            date_value = local_day(text(day.find('h3')), today)
            for table in day.select('.scrolltable'):
                clocks = table.select('tr.time td')
                films = clocks[0].parent.find_next_sibling('tr').find_all('td', recursive=False) if clocks and clocks[0].parent.find_next_sibling('tr') else []
                screen = str(table.previous_sibling).strip()
                for clock, film in zip(clocks, films, strict=False):
                    link = film.find('a', href=True)
                    yield screening(source, text(link), date_value, text(clock), screen=screen if screen in ('スクリーン1','スクリーン2') else None,
                                    programme=linked_url(source['url'], link['href']) if link else None)
    elif adapter == 'image_forum':
        for day in soup.select('.schedule-day-box'):
            date_value = local_day(text(day.select_one('.schedule-day-title')), today)
            for film in day.select('.schebox a[href]'):
                yield screening(source, text(film.find('p')), date_value, text(film.find('div')),
                                programme=linked_url(source['url'], film['href']))
    elif adapter == 'cinema_vera':
        month = None
        for row in soup.select('table.pctime tr'):
            day = local_day(text(row.select_one('td.date .day')), today, month)
            if not day:
                continue
            month = day.month
            for cell in row.select('td:has(.film)'):
                title = re.sub(r'\s*[(（]\d+分[)）]\s*$', '', text(cell.select_one('.film')))
                yield screening(source, title, day, text(cell.select_one('.time')))
    elif adapter == 'bungeiza':
        for program in soup.select('.schedule-box[id^=d]'):
            iso = re.match(r'd(20\d{2}-\d{2}-\d{2})-', program['id'])
            content = program.find_next_sibling('div', class_='schedule-content')
            if not iso or not content:
                continue
            day = date.fromisoformat(iso[1])
            for node in content.select('.schedule-content-txt > h2, .schedule-program'):
                if node.name == 'h2':
                    shown = text(node.find('em') or node)
                    day = local_day(shown, day, day.month) if day else None
                elif day:
                    title = text(node.find('p', recursive=False)) or text(program.find('h1'))
                    for slot in node.select('li'):
                        a = slot.find('a', href=True)
                        yield screening(source, title, day, text(slot), proof=source['url']+'#'+program['id'],
                                        booking=linked_url(source['url'], a['href']) if a else None)


def record_id(row):
    key = (
        row['source_id'], normalized(row['title_original']), row['start_date'], row.get('start_at'),
        row.get('venue'), row.get('auditorium'), row.get('platform'), row.get('market')
    )
    if row.get('streaming_season'):
        key += (row['streaming_season'],)
    return 'film-' + sha256(json.dumps(key, ensure_ascii=False).encode()).hexdigest()[:24]


def premiere_work(row):
    return row['platform'], normalized(row.get('premiere_title') or row['title_original']), row.get('streaming_season', 0)


def refresh(previous, sources, *, verified_premieres=(), instant=None, fetch_factory=None):
    from bs4 import BeautifulSoup
    from .exhibition_sources import PublicHost, error_kind
    from .japan_film_calendar import current_films, release_dates, screening_dates
    from .netflix_calendar import read_netflix
    from .streaming_premieres import apple_dates, press_dates, verified_dates
    fetch_factory = fetch_factory or PublicHost
    instant = instant or datetime.now(timezone.utc)
    reports = {source['id']: previous['sources'][source['id']] for source in sources
               if source['id'] in previous['sources']}
    items = {row['id']: row for row in previous['items'] if calendar_event_allowed(row)
             and row.get('premiere_basis') != 'verified_release'}
    now_showing = previous.get('now_showing', [])
    hosts = {}
    source_hosts = {source['id']: {urlsplit(source[key]).hostname: source[key] for key in
                    ('url', 'guide_url', 'media_url') if source.get(key)} for source in sources}
    host_locks = {hostname: Lock() for domains in source_hosts.values() for hostname in domains}
    press_adapters = ('apple', 'disney', 'netflix_news', 'netflix_calendar')

    def read(source):
        instant_here = instant.astimezone(ZoneInfo(source['timezone'])).date()
        domains = source_hosts[source['id']]
        adapter = source['adapter']
        coverage = {}

        def get(url):
            hostname = urlsplit(url).hostname
            if hostname not in domains:
                raise ValueError('source_host_mismatch')
            with host_locks[hostname]:
                if hostname not in hosts:
                    hosts[hostname] = fetch_factory(domains[hostname])
                return hosts[hostname](url)

        try:
            if adapter == 'apple':
                rows = apple_dates(get(source['data_url']), get(source['press_url']), source, get, coverage)
            elif adapter == 'netflix_calendar':
                rows = read_netflix(source, get, instant_here, previous['items'], coverage)
            else:
                soup = BeautifulSoup(get(source['url']), 'html.parser')
                if adapter == 'eiga_showing':
                    rows = current_films(soup, source, get)
                elif adapter == 'eiga_releases':
                    rows, coverage = release_dates(soup, source, get, instant_here, previous['items'])
                elif adapter == 'eiga_venue':
                    rows = screening_dates(soup, source, instant)
                elif adapter in ('disney', 'netflix_news'):
                    rows = press_dates(soup, source, get, coverage)
                else:
                    rows = parse_screenings(soup, source, instant_here)
            records = {(row.get('id') or record_id(row)): row for row in rows if row and calendar_event_allowed(row)}
            if not records and (adapter not in press_adapters or coverage.get('failed_pages')):
                raise ValueError('no_verified_film_events')
            return source, records, None, coverage
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            return source, {}, error_kind(error), coverage

    with ThreadPoolExecutor(max_workers=6) as pool:
        for source, rows, error, coverage in pool.map(read, sources):
            identifier = source['id']
            proof = {'name':source['name'], 'url':source['url'], 'checked_at':instant.isoformat(),
                     'status':'failed' if error else 'success','verified_this_run':len(rows), **coverage}
            if error:
                proof['reason'] = error
                proof['last_success_at'] = reports.get(identifier, {}).get('last_success_at')
            else:
                proof['last_success_at'] = instant.isoformat()
                if source['adapter'] == 'eiga_showing':
                    now_showing = list(rows.values())
                    reports[identifier] = proof
                    continue
                if source.get('venue'):
                    # Current theatre timetables supersede saved sessions only in their published date window.
                    days = [row['start_date'] for row in rows.values()]
                    first, last = min(days), max(days)
                    today = instant.astimezone(ZoneInfo(source['timezone'])).date().isoformat()
                    items = {key: row for key, row in items.items() if row['source_id'] != identifier
                             or not max(first,today) <= row['start_date'] <= last or key in rows}
                elif source['adapter'] == 'eiga_releases':
                    confirmed = {(row['evidence_url'], row['event_type']) for row in rows.values()}
                    today = instant.astimezone(ZoneInfo(source['timezone'])).date().isoformat()
                    items = {key: row for key, row in items.items() if row['source_id'] != identifier
                             or row['start_date'] < today or (row['evidence_url'], row['event_type']) not in confirmed or key in rows}
                elif source['adapter'] in press_adapters:
                    today = instant.astimezone(ZoneInfo(source['timezone'])).date().isoformat()
                    revised = {premiere_work(row) for row in rows.values()}
                    items = {key: row for key, row in items.items() if row['source_id'] != identifier
                             or row['start_date'] < today or row.get('premiere_basis') == 'verified_release'
                             or premiere_work(row) not in revised or key in rows}
                items.update({key: {**row,'id':key} for key,row in rows.items()})
            reports[identifier] = proof

    # A curated proof can preserve the dedicated work page and its existing metadata.
    premieres = {}
    proof_rank = {'reported_premiere': 0, 'official_announcement': 1, 'verified_release': 2}
    for row in [*items.values(), *verified_dates(verified_premieres, sources, previous['items'])]:
        if row['event_type'] != 'streaming_release' or not calendar_event_allowed(row):
            continue
        identifier = row.get('id') or record_id(row)
        key = (*premiere_work(row), row['start_date'])
        if duplicate := premieres.get(key):
            prior = items.pop(duplicate)
            if duplicate != identifier:
                items.pop(identifier, None)
            if proof_rank[prior['premiere_basis']] > proof_rank[row['premiere_basis']]:
                row = {**row, **prior}
                identifier = duplicate
            else:
                row = {**prior, **row}
        premieres[key] = identifier
        items[identifier] = {**row, 'id': identifier}
    return {'schema_version':1,'generated_at':instant.isoformat(),'sources':reports,'now_showing':now_showing,
            'items':sorted(items.values(),key=lambda row:(row['start_date'],row.get('start_at',''),row['id']))}


def write_calendar(value, path=DATA):
    replace_file(path, encoded(value))
