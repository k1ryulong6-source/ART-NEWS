"""Published cinema showtimes and streaming announcements, separate from news."""
import calendar
import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
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


def text(node):
    return ' '.join(node.get_text(' ', strip=True).split()) if node else ''


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


def film_dates(soup, source, get):
    from bs4 import BeautifulSoup
    if source['adapter'] == 'netflix':
        film_list = BeautifulSoup(get(source['film_evidence_url']), 'html.parser')
        films = {normalized(text(h)) for h in film_list.select('[data-sel=article-content] h3')}
        if not films:
            raise ValueError('netflix_film_reference_unavailable')
        for node in soup.select('[data-sel=article-content] [data-sel=f-item]'):
            title = text(node.find('h3'))
            stamp = node.find('time', datetime=True)
            description = text(node.find('p'))
            if not stamp or not title or (normalized(title) not in films and not re.search(r'\b(?:documentary film|feature film|animated film)\b', description, re.I)):
                continue
            day = date.fromisoformat(stamp['datetime'][:10]).isoformat()
            row = base(source, title, day, 'day', 'streaming_release')
            if re.search(r'\b(?:available|streaming|premier\w*)\s+(?:on Netflix\s+)?(?:globally|worldwide)\b', description, re.I):
                row['market'] = '全球'
            link = node.select_one('a[data-uia=play-on-netflix-link][href]')
            if link and re.fullmatch(r'https://www.netflix.com/watch/\d+(?:\?.*)?',link['href']):
                row['watch_url'] = link['href'].split('?')[0]
            yield row
    else:
        from .exhibition_sources import linked_url
        lineup = {}
        for a in soup.select('a[href*=lineup]'):
            url = linked_url(source['url'], a['href'], host_only=True)
            match = re.search(r'criterion-channel-s-([a-z]+)-(20\d{2})-lineup/?$', urlsplit(url or '').path)
            if match and match[1] in MONTHS:
                lineup[url] = (int(match[2]), MONTHS[match[1]])
        for url, (year, month) in sorted(lineup.items(), key=lambda record: record[1], reverse=True)[:2]:
            page = BeautifulSoup(get(url), 'html.parser')
            title = text(page.find('h1'))
            if title:
                yield {**base(source, title, f'{year}-{month:02}', 'month', 'streaming_release', url), 'program': True}


def apple_dates(payload, source):
    from .exhibition_sources import linked_url
    films = json.loads(payload)['results']['originals']
    for item in films:
        if item.get('showTypeKey') != 'films' or not item.get('title'):
            continue
        shown = (item.get('releaseDateDisplayString') or '').strip()
        match = re.fullmatch(r'([A-Za-z]+) (?:(\d{1,2}), )?(20\d{2})', shown)
        if not match or match[1].lower() not in MONTHS:
            continue
        month = MONTHS[match[1].lower()]
        day = date(int(match[3]), month, int(match[2] or 1)).isoformat()
        if not (item.get('releaseDateISOString') or '').startswith(day):
            continue
        precision = 'day' if match[2] else 'month'
        url = linked_url(source['url'], item.get('url'), host_only=True)
        yield base(source, item['title'], day if precision == 'day' else day[:7], precision, 'streaming_release', url)


def disney_dates(soup, source, get):
    from bs4 import BeautifulSoup
    from .exhibition_sources import linked_url
    agenda = {}
    for link in soup.select('a[href*=next-on-disney-plus]'):
        url = linked_url(source['url'],link['href'],host_only=True)
        match = re.fullmatch(r'/news/next-on-disney-plus-([a-z]+)-(20\d{2})/?',urlsplit(url or '').path)
        if match and match[1] in MONTHS:
            agenda[url] = (int(match[2]), MONTHS[match[1]])
    for url,(year,month) in sorted(agenda.items(),key=lambda item:item[1],reverse=True)[:2]:
        page = BeautifulSoup(get(url),'html.parser')
        day = None
        for node in page.select('.rich-text-container > h1, .rich-text-container > p'):
            label = text(node)
            if node.name == 'h1':
                match = re.search(r'\b([A-Z][a-z]+) (\d{1,2})$',label)
                day = date(year,month,int(match[2])).isoformat() if match and MONTHS.get(match[1].lower()) == month else None
                continue
            # Published catalogue films end in their production year. Episode, live and podcast rows use labels instead.
            item = re.fullmatch(r'(Disney\+|Hulu|Disney\+ and Hulu): (.+?)\s+\((?:19|20)\d{2}\)', label)
            if day and item and not re.search(r'\b(?:season|series|episode|podcast)\b',item[2],re.I):
                for platform in item[1].split(' and '):
                    yield {**base(source,item[2],day,'day','streaming_release',url),'platform':platform}


def netflix_news_dates(soup, source, get):
    from bs4 import BeautifulSoup
    from .exhibition_sources import linked_url
    stories = {}
    for link in soup.select('a[href^="/en/news/"]'):
        headline = text(link)
        if re.search(r'\b(?:premier\w+|debuts?)\b',headline,re.I):
            url = linked_url(source['url'],link['href'],host_only=True)
            if url:
                stories[url] = headline
    for url,headline in list(stories.items())[:8]:
        quoted = re.search(r"'([^']+)'|‘([^’]+)’|“([^”]+)”", headline)
        if not quoted:
            continue
        title = next(group.rstrip(' ,') for group in quoted.groups() if group)
        page = BeautifulSoup(get(url),'html.parser')
        published = text(page.select_one('[class*=ArticleDateWrapper]'))
        try:
            posted = datetime.strptime(published,'%d %B %Y').date()
        except ValueError:
            continue
        paragraphs = [text(node) for node in page.select('[class*=ArticleCopy] p')]
        introduction = ' '.join(paragraphs[:2])
        if not re.search(r'\b(?:documentary|feature|original|animated) film\b|\ba documentary\b|\bmovie\b',introduction,re.I) or re.search(r'\b(?:limited|documentary|animated|drama) series\b',introduction,re.I):
            continue
        for paragraph in paragraphs:
            when = re.search(r'\bpremier\w*\b.{0,60}?([A-Z][a-z]+)\s+(\d{1,2})(?:, (20\d{2}))?\b',paragraph)
            if title not in paragraph or not when or when[1].lower() not in MONTHS:
                continue
            day = local_day(f'{MONTHS[when[1].lower()]}/{when[2]}',posted) if not when[3] else date(int(when[3]),MONTHS[when[1].lower()],int(when[2]))
            if day and day >= posted:
                row = base(source,title,day.isoformat(),'day','streaming_release',url)
                if re.search(r'\b(?:globally|worldwide)\b',paragraph,re.I):
                    row['market'] = '全球'
                yield row
                break


def record_id(row):
    key = (
        row['source_id'], normalized(row['title_original']), row['start_date'], row.get('start_at'),
        row.get('venue'), row.get('auditorium'), row.get('platform'), row.get('market')
    )
    return 'film-' + sha256(json.dumps(key, ensure_ascii=False).encode()).hexdigest()[:24]


def refresh(previous, sources, *, instant=None, fetch_factory=None):
    from bs4 import BeautifulSoup
    from .exhibition_sources import PublicHost, error_kind
    fetch_factory = fetch_factory or PublicHost
    instant = instant or datetime.now(timezone.utc)
    reports = dict(previous['sources'])
    items = {row['id']: row for row in previous['items']}

    def read(source):
        instant_here = instant.astimezone(ZoneInfo(source['timezone'])).date()
        try:
            get = fetch_factory(source['url'])
            if source['adapter'] == 'apple':
                rows = apple_dates(get(source['data_url']), source)
            else:
                soup = BeautifulSoup(get(source['url']), 'html.parser')
                if source['adapter'] == 'disney':
                    rows = disney_dates(soup, source, get)
                elif source['adapter'] == 'netflix_news':
                    rows = netflix_news_dates(soup, source, get)
                elif source.get('platform'):
                    rows = film_dates(soup, source, get)
                else:
                    rows = parse_screenings(soup, source, instant_here)
            records = {record_id(row): row for row in rows if row}
            if not records:
                raise ValueError('no_verified_film_events')
            return source, records, None
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            return source, {}, error_kind(error)

    with ThreadPoolExecutor(max_workers=6) as pool:
        for source, rows, error in pool.map(read, sources):
            identifier = source['id']
            proof = {'name':source['name'], 'url':source['url'], 'checked_at':instant.isoformat(),
                     'status':'failed' if error else 'success','verified_this_run':len(rows)}
            if error:
                proof['reason'] = error
                proof['last_success_at'] = reports.get(identifier, {}).get('last_success_at')
            else:
                proof['last_success_at'] = instant.isoformat()
                if source.get('venue'):
                    # Current theatre timetables supersede saved sessions only in their published date window.
                    days = [row['start_date'] for row in rows.values()]
                    first, last = min(days), max(days)
                    today = instant.astimezone(ZoneInfo(source['timezone'])).date().isoformat()
                    items = {key: row for key, row in items.items() if row['source_id'] != identifier
                             or not max(first,today) <= row['start_date'] <= last or key in rows}
                items.update({key: {**row,'id':key} for key,row in rows.items()})
            reports[identifier] = proof
    return {'schema_version':1,'generated_at':instant.isoformat(),'sources':reports,
            'items':sorted(items.values(),key=lambda row:(row['start_date'],row.get('start_at',''),row['id']))}


def write_calendar(value, path=DATA):
    replace_file(path, encoded(value))
