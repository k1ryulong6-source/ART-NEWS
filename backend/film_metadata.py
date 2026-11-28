"""Source-checked names and artwork for film works, independent of their showtimes."""
import json
import re
import time
import unicodedata
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from threading import Lock
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from .film_calendar import DATA, film_image as image_url, read_calendar, text as node_text
from .film_profiles import article_profiles, eiga_profile, prose
from .snapshot_files import encoded, replace_file

METADATA = DATA.with_name('film-metadata.json')
DOUBAN = 'https://m.douban.com'
WIKIDATA = 'https://www.wikidata.org/w/api.php'
TMDB = 'https://www.themoviedb.org'
APPLE = 'https://www.apple.com/tv-pr/originals.originals.json'
VERA = 'https://www.cinemavera.com/preview.html'
VERA_CURRENT = 'https://www.cinemavera.com/programs.html'
MOVIE_TYPES = {'cinema_release', 'cinema_screening', 'festival_screening', 'streaming_release'}
ART_FIELDS = ('poster_url', 'poster_source_url', 'artwork_url', 'artwork_source_url', 'artwork_kind')
VERSION = re.compile(r'(?:\s|[［【(])(?:[248]K|DCP|35mm|リストア版|デジタル復元|デジタルリマスター|修復版|上映版|〈.*再上映〉).*$', re.I)
PROGRAMME = re.compile(r'^\s*(?:[2-9２-９]本(?:立て|セット)|オールナイト|短編(?:特集|プログラム)|上映プログラム|.*(?:lineup|short films program(?:me)?|double feature)$)', re.I)
YEAR = r'(?:18|19|20)\d{2}'


def clean(value):
    return ' '.join((value or '').split())


def name_key(text):
    folded = unicodedata.normalize('NFKC', str(text or '')).casefold()
    return ''.join(char for char in unicodedata.normalize('NFKD', folded) if char.isalnum())


def work_title(title):
    return VERSION.sub('', clean(title)).strip(' 『』〈〉「」')


def is_programme(row):
    return bool(row.get('program') or PROGRAMME.search(row.get('title_original') or ''))


def film_key(row, *, include_programmes=False):
    if (row.get('event_type') not in MOVIE_TYPES or row.get('is_demo') or row.get('evidence_status') == 'unverified'
            or (not include_programmes and is_programme(row))):
        return None
    title = name_key(work_title(row.get('title_original')))
    proof = row.get('programme_url') or row.get('evidence_url')
    if not title or not proof:
        return None
    # An undifferentiated theatre schedule can screen two films with the same title in different programmes.
    edition = row['start_date'] if row.get('source_id') == 'cinema-vera' else ''
    return sha256(encoded([title, proof, edition])).hexdigest()[:24]


def read_metadata(path=METADATA):
    if not path.exists():
        return {'schema_version': 1, 'records': {}}
    payload = json.loads(path.read_bytes())
    if payload.get('schema_version') != 1 or not isinstance(payload.get('records'), dict):
        raise ValueError('invalid_film_metadata')
    return payload


def write_metadata(payload, path=METADATA):
    replace_file(path, encoded(payload))


def calendar_with_films(events=(), *, articles=(), links=(), calendar=None, metadata=None):
    calendar = read_calendar() if calendar is None else calendar
    metadata = read_metadata() if metadata is None else metadata
    event_urls = {row['id']: row['evidence_url'] for row in events if row.get('evidence_url') and film_key(row)}
    evidence = defaultdict(set)
    for link in links:
        if url := event_urls.get(link['event_id']):
            evidence[link['content_id']].add(url)
    archived = article_profiles(articles, evidence)
    works, published = [], {}
    for row in [*calendar['items'], *calendar.get('now_showing', []), *events]:
        if key := film_key(row, include_programmes=True):
            works.append((key, row))
            if profile := row.get('profile'):
                if len(profile.get('text', '')) > len(published.get(key, {}).get('text', '')):
                    published[key] = profile
    films, profiles = {}, {}
    for key, row in works:
        record = metadata['records'].get(key, {})
        if key not in profiles:
            url = row.get('programme_url') or row.get('evidence_url')
            saved = record.get('profile', {})
            profile = {**published.get(key, {}), **saved, **archived.get(url, {})}
            if saved.get('language') in ('zh', 'zh-CN'):
                profile.update(saved)
            if profile:
                profiles[key] = profile
        details = {field: record[field] for field in (
            'title_zh', 'original_title', 'year', 'douban_id', 'douban_url', 'match_source_url', *ART_FIELDS
        ) if record.get(field)}
        if key in profiles:
            details['profile_id'] = key
        if details:
            films[row['id']] = details
    return {**calendar, 'films': films, 'profiles': profiles, 'film_metadata_report': metadata.get('report')}


def artwork_fields(image, page, kind):
    raw = image.get('data-src') or image.get('src') if image else None
    if raw and (url := image_url(raw, page)):
        return {'artwork_url': url, 'artwork_source_url': page, 'artwork_kind': kind}
    return {}


def bungeiza_artwork(row, soup, page, expected):
    anchor = urlsplit(page).fragment
    programme = soup.find(id=anchor)
    schedule = programme.find_next_sibling('div', class_='schedule-content') if programme else None
    if not schedule:
        return {}, None, ''
    images = programme.select('.schedule-box-img img[src$=".jpg"], .schedule-box-img img[src$=".png"]')
    if not images:
        images = programme.select('img[src$="-p.jpg"], img[src$="-p.png"]')
    if is_programme(row):
        announced = [programme.find('h1'), *schedule.select('.schedule-program > p')]
        if any(name_key(work_title(node_text(name))) == expected for name in announced):
            return artwork_fields(next(iter(images), None), page, 'programme'), None, ''
        return {}, None, ''

    # The venue can place several film titles and their credits inside one paragraph.
    credits = []
    for paragraph in schedule.select('p.nihon-date'):
        heading = []
        for child in paragraph.children:
            if child.name == 'small':
                title = name_key(work_title(' '.join(heading)))
                if title:
                    credits.append((title, node_text(child)))
                heading.clear()
            elif child.name == 'br':
                heading.clear()
            else:
                heading.append(str(child) if child.name is None else node_text(child))
    matching = [(index, description) for index, (title, description) in enumerate(credits, 1) if title == expected]
    if len(matching) != 1:
        return {}, None, ''
    index, details = matching[0]
    stem = f'/photo/{anchor.removeprefix("d")}-{index:02}-'
    if len(credits) == 1:
        poster = next((img for img in images if img['src'].endswith(('-p.jpg', '-p.png'))), None)
    else:
        poster = next((img for img in images if img['src'] in (stem+'p.jpg', stem+'p.png')), None)
    still = next((img for img in schedule.select('.schedule-content-img img[src]')
                  if img['src'] in (stem+'s1.jpg', stem+'s1.png')), None)
    fallback = artwork_fields(still, page, 'still')
    if not fallback and not poster and len(images) == 1:
        fallback = artwork_fields(images[0], page, 'programme')
    return fallback, poster, details


def page_movie(row, soup, page):
    """Read the identified film or programme's artwork, credits and introduction."""
    host = urlsplit(page).hostname
    expected = name_key(work_title(row.get('title_original')))
    info, poster, details = {}, None, ''
    if host == 'eiga.com':
        details = node_text(soup.select_one('p.data'))
        if expected and name_key(work_title(node_text(soup.find('h1')))) == expected:
            if profile := eiga_profile(soup, page):
                info['profile'] = profile
        poster = soup.select_one('.poster-img img, div.pict-area img, img[itemprop=image], .movie-poster img')
        hero = soup.select_one('.hero-img img')
        if hero and name_key(hero.get('alt')) == expected:
            info.update(artwork_fields(hero, page, 'still'))
        if not poster:
            for block in soup.select('script[type="application/ld+json"]'):
                try:
                    data = json.loads(block.string or '')
                except ValueError:
                    continue
                for movie in data if isinstance(data, list) else [data]:
                    if movie.get('@type') == 'Movie' and name_key(movie.get('name')) == expected:
                        image = movie.get('image')
                        info['poster_url'] = image_url(image.get('url') if isinstance(image, dict) else image, page)
    elif host == 'www.apple.com' and urlsplit(page).path.startswith('/tv-pr/originals/'):
        if name_key(node_text(soup.select_one('h1.description-title'))) == expected:
            if profile := prose(node_text(soup.select_one('.description-copy')), 'en', page):
                info['profile'] = profile
    elif host == 'www.imageforum.co.jp':
        details = ' '.join(map(node_text, soup.select('p.text, .movie-data, .movieDetail')))[:7000]
        poster = soup.select_one('img.wp-post-image')
    elif host == 'www.eurospace.co.jp':
        details = node_text(soup.select_one('p.work-caption'))
        poster = soup.select_one('img[src*="_chirashi."]')
        info.update(artwork_fields(soup.select_one('img[src*="_bamensha."]'), page, 'still'))
    elif host == 'www.shin-bungeiza.com':
        info, poster, details = bungeiza_artwork(row, soup, page, expected)
    elif host == 'www.cinemavera.com':
        period = re.findall(r'\d{4}/\d{2}/\d{2}', node_text(soup.select_one('ul.subject .schedule')))
        dates = [value.replace('/', '-') for value in period]
        if len(dates) != 2 or not dates[0] <= row['start_date'] <= dates[1]:
            return info
        films = []
        for block in soup.select('ul.films[id]'):
            heading = node_text(block.select_one('h3')).strip('『』')
            label = re.sub(r'\s*[（(]\d+分[^)）]*[)）]\s*$', '', heading)
            if name_key(work_title(label)) == expected:
                films.append(block)
        if len(films) != 1:
            return info
        details = node_text(films[0].select_one('li.txt'))
        page += '#' + films[0]['id']
        info.update(artwork_fields(films[0].select_one('li.img img[src*="/files/"]'), page, 'still'))
        info['programme_start'], info['programme_end'] = dates
    elif host == 'diaphana.fr':
        poster = soup.select_one('img[src*="affiche"], img[class*="affiche"]')
        details = node_text(soup.select_one('.film-infos, .film-details'))
    elif host in ('whatson.bfi.org.uk', 'www.bfi.org.uk'):
        heading = node_text(soup.find('h1'))
        if name_key(work_title(heading)) != expected:
            return info
        poster = soup.select_one('img[src*="poster"], img[alt*="poster" i]')
        details = node_text(soup.select_one('.film-details, .event-details'))
    if poster:
        info['poster_url'] = image_url(poster.get('data-src') or poster.get('src'), page)
    if info.get('poster_url'):
        info['poster_source_url'] = page
    details = unicodedata.normalize('NFKC', details)
    original = re.search(r'(?:原題(?:または英題)?|Original title)\s*:\s*([^/|©()]{2,115}?)(?=\s*(?:日本語|字幕|劇場公開日|製作|配給|配信|[/|©()]|$))',
                         details, flags=re.I)
    year = re.search(rf'({YEAR})\s*年(?:製作|作品|公開)|(?:^|[（(])\s*({YEAR})[年・/／)]|公開[：:]\s*({YEAR})年', details)
    if host == 'www.eurospace.co.jp':
        year = re.search(rf'\b({YEAR})年?\s*/', details)
    if original:
        info['original_title'] = clean(original[1])
    if year:
        info['year'] = int(next(value for value in year.groups() if value))
    if info.get('year') or info.get('original_title'):
        info['identity_source_url'] = page
    return info


def parse_douban_results(page):
    from bs4 import BeautifulSoup
    result = {}
    for link in BeautifulSoup(page, 'html.parser').select('a[href^="/movie/subject/"]'):
        match = re.fullmatch(r'/movie/subject/(\d+)/?', link['href'])
        title = node_text(link.select_one('.subject-title'))
        if match and title:
            result[match[1]] = title
    return result


def title_language(title):
    if re.search(r'[\u3040-\u30ff\u3400-\u9fff]', title):
        return 'ja'
    if re.search(r'[\u0400-\u04ff]', title):
        return 'ru'
    if re.search(r'[\uac00-\ud7af]', title):
        return 'ko'
    return 'en'


def claim_values(entity, key):
    return [claim['mainsnak']['datavalue']['value'] for claim in entity.get('claims', {}).get(key, [])
            if claim.get('rank') != 'deprecated' and claim.get('mainsnak', {}).get('datavalue')]


def wikidata_matches(entities, title, year=None, *, exact_ids=()):
    matches = []
    for identifier, entity in entities.items():
        labels = [entry['value'] for entry in entity.get('labels', {}).values()]
        aliases = [entry['value'] for entries in entity.get('aliases', {}).values() for entry in entries]
        if identifier not in exact_ids and name_key(title) not in {name_key(name) for name in labels + aliases}:
            continue
        years = [int(value['time'][1:5]) for value in claim_values(entity, 'P577')
                 if isinstance(value, dict) and re.match(r'^\+\d{4}-', value.get('time', ''))]
        if not years or (year and abs(min(years) - year) > 1):
            continue
        ids = claim_values(entity, 'P4529')
        posters = claim_values(entity, 'P4947')
        if ids or posters:
            matches.append({'id': str(ids[0]) if len(set(ids)) == 1 else None,
                            'tmdb': str(posters[0]) if len(set(posters)) == 1 else None,
                            'lookup_names': list(dict.fromkeys(entity['labels'][language]['value']
                                                 for language in ('en', 'mul', 'zh-hans', 'zh') if language in entity.get('labels', {}))),
                            'year': min(years), 'source': 'https://www.wikidata.org/wiki/' + identifier})
    if year and len(matches) > 1:
        matches = [match for match in matches if match['year'] == year]
    return matches[0] if len(matches) == 1 else {}


class MovieLookup:
    def __init__(self, fetch_factory=None):
        from .exhibition_sources import PublicHost
        self.fetch_factory = fetch_factory or PublicHost
        self.hosts = {}
        self.cache = {}
        self.errors = defaultdict(int)
        self.wikidata_last = 0
        self.wikidata_unavailable = False
        self.locks = {}

    def get(self, url):
        url = urlunsplit(urlsplit(url)._replace(fragment=''))
        hostname = urlsplit(url).hostname
        with self.locks.setdefault(hostname, Lock()):
            if url not in self.cache:
                try:
                    if hostname not in self.hosts:
                        self.hosts[hostname] = self.fetch_factory(url)
                    self.cache[url] = self.hosts[hostname](url)
                except (OSError, ValueError):
                    self.errors[hostname] += 1
                    self.cache[url] = b''
            return self.cache[url]

    def wikidata(self, title, year):
        def request_unlocked(**params):
            url = WIKIDATA + '?' + urlencode({'format': 'json', 'maxlag': 5, **params})
            if self.wikidata_unavailable:
                return {}
            if url in self.cache:
                return self.cache[url]
            # Use Wikimedia's documented machine API with a named client and sequential requests.
            time.sleep(max(0, .75 - (time.monotonic() - self.wikidata_last)))
            self.wikidata_last = time.monotonic()
            try:
                with urlopen(Request(url, headers={'User-Agent': 'CultureDesk/0.4 FilmCalendar (+https://mujianrest.work/)',
                                                   'Accept': 'application/json'}), timeout=9) as response:
                    if response.url != url:
                        return {}
                    result = json.loads(response.read(3_000_000))
                if result.get('error', {}).get('code') in ('maxlag', 'ratelimited'):
                    self.wikidata_unavailable = True
                self.cache[url] = result
            except (OSError, ValueError) as exc:
                if isinstance(exc, HTTPError) and exc.code in (403, 429):
                    self.wikidata_unavailable = True
                self.errors['www.wikidata.org'] += 1
                self.cache[url] = {}
            return self.cache[url]
        def request(**params):
            with self.locks.setdefault('www.wikidata.org', Lock()):
                return request_unlocked(**params)
        found = request(action='wbsearchentities', search=title, language=title_language(title), type='item', limit=7)
        ids = [row['id'] for row in found.get('search', [])
               if re.fullmatch(r'Q\d+', row['id']) and name_key(row.get('match', {}).get('text')) == name_key(title)]
        if not ids:
            return {}
        result = request(action='wbgetentities', ids='|'.join(ids), props='labels|aliases|claims',
                         languages='mul|en|ja|zh|zh-hans|fr|en-gb|es|it|ko|de|ru')
        return wikidata_matches(result.get('entities', {}), title, year, exact_ids=set(ids))

    def douban(self, title):
        url = DOUBAN + '/search?' + urlencode({'type': '1002', 'query': title})
        return parse_douban_results(self.get(url)), url

    def source_facts(self, row):
        from bs4 import BeautifulSoup
        from .reading import public_url
        page = public_url(row.get('programme_url') or row.get('evidence_url'))
        if not page:
            return {}
        source = row.get('source_id')
        if source == 'apple-tv':
            try:
                items = json.loads(self.get(APPLE))['results']['originals']
            except (ValueError, KeyError, TypeError):
                return {}
            item = next((item for item in items if item.get('showTypeKey') == 'films'
                         and name_key(item.get('title')) == name_key(row['title_original'])), None)
            if item:
                art = item.get('image') or {}
                poster = public_url((art.get('dirpath') or '') + (art.get('name') or ''), APPLE) if art.get('name') else None
                return {**page_movie(row, BeautifulSoup(self.get(page), 'html.parser'), page),
                        'poster_url': poster, 'poster_source_url': page, 'year': int(row['start_date'][:4]),
                        'identity_source_url': page}
            return {}
        if source == 'cinema-vera':
            for programme in (VERA_CURRENT, VERA):
                found = page_movie(row, BeautifulSoup(self.get(programme), 'html.parser'), programme)
                if found:
                    return found
            return {}
        if source == 'disney-hulu' and urlsplit(page).hostname == 'press.disneyplus.com':
            soup = BeautifulSoup(self.get(page), 'html.parser')
            years = set()
            for node in soup.select('.rich-text-container > p'):
                item = re.fullmatch(rf'(?:Disney\+|Hulu|Disney\+ and Hulu): (.+?)\s+\(({YEAR})\)', node_text(node))
                if item and name_key(item[1]) == name_key(row['title_original']):
                    years.add(int(item[2]))
            return {'year': next(iter(years)), 'identity_source_url': page} if len(years) == 1 else {}
        if urlsplit(page).hostname not in ('eiga.com', 'www.eurospace.co.jp', 'www.imageforum.co.jp',
                                         'www.shin-bungeiza.com', 'www.cinemavera.com',
                                         'diaphana.fr', 'whatson.bfi.org.uk', 'www.bfi.org.uk'):
            return {}
        return page_movie(row, BeautifulSoup(self.get(page), 'html.parser'), page)

    def resolve(self, row, *, related=None):
        published = {key: row[key] for key in ART_FIELDS if row.get(key)}
        facts = {**self.source_facts(row), **published}
        if is_programme(row):
            return facts
        if related:
            facts = {**{key: value for key, value in related.items() if key != 'profile'},
                     **{key: value for key, value in facts.items() if value}}
        title = facts.get('original_title') or work_title(row['title_original'])
        year = facts.get('year') or row.get('film_year')
        # Official programme titles sometimes include a separate foreign title.
        latin_alias = re.fullmatch(r'(.+?[\u3040-\u30ff])\s+([A-Za-z][A-Za-z0-9 .!’’:\-]+)', title)
        if latin_alias:
            title = clean(latin_alias[2])
        matches, result_url = self.douban(title)
        cross_reference = self.wikidata(title, year)
        subject = cross_reference.get('id')
        if subject and subject not in matches:
            matches, result_url = self.douban(f'{title} {year or cross_reference["year"]}')
            for alternate in cross_reference.get('lookup_names', []):
                if subject in matches:
                    break
                if name_key(alternate) != name_key(title):
                    matches, result_url = self.douban(alternate)
        if not subject and len(matches) == 1 and (facts.get('original_title') or len(name_key(title)) >= 12):
            # The complete source title must return a single film; repeat with an independently documented year when present.
            subject = next(iter(matches))
            if year:
                dated, _ = self.douban(f'{title} {year}')
                if next(iter(dated), None) != subject:
                    subject = None
        if not subject and cross_reference:
            for alternate in cross_reference.get('lookup_names', []):
                if name_key(alternate) == name_key(title):
                    continue
                dated, dated_url = self.douban(f'{alternate} {cross_reference["year"]}')
                if len(dated) == 1:
                    candidate = next(iter(dated))
                    undated, _ = self.douban(alternate)
                    if candidate in undated:
                        subject, matches, result_url = candidate, dated, dated_url
                        break
        if subject in matches:
            facts.update(douban_id=subject, douban_url=f'https://movie.douban.com/subject/{subject}/',
                         match_source_url=result_url)
            translated = matches[subject]
            if re.search(r'[\u3400-\u9fff]', translated) and not re.search(r'[\u3040-\u30ff\uac00-\ud7af]', translated):
                facts['title_zh'] = translated
        if not facts.get('poster_url') and (tmdb := cross_reference.get('tmdb')) and tmdb.isdecimal():
            from bs4 import BeautifulSoup
            from .reading import public_url
            page = f'{TMDB}/movie/{tmdb}'
            soup = BeautifulSoup(self.get(page), 'html.parser')
            poster = soup.select_one('meta[property="og:image"][content*="/w500/"]')
            if poster and (url := public_url(poster['content'])) and urlsplit(url).hostname == 'media.themoviedb.org':
                facts.update(poster_url=url, poster_source_url=page)
        if cross_reference:
            facts['wikidata_url'] = cross_reference['source']
            facts['year'] = year or cross_reference['year']
        if facts.get('original_title') and not facts.get('identity_source_url'):
            facts.pop('original_title')
        return facts


def refresh_metadata(calendar, events, previous, *, instant=None, limit=44, seconds=240, lookup=None):
    lookup = lookup or MovieLookup()
    instant = instant or datetime.now(timezone.utc)
    today = instant.astimezone(ZoneInfo('Asia/Tokyo')).date().isoformat()
    retry_after = (instant - timedelta(days=7)).isoformat()
    deadline = time.monotonic() + seconds
    records = dict(previous['records'])
    groups = defaultdict(list)
    vera_titles = defaultdict(list)
    japanese_releases = {}
    for row in [*calendar['items'], *events]:
        if identifier := film_key(row, include_programmes=True):
            groups[identifier].append(row)
            if row.get('source_id') == 'cinema-vera':
                vera_titles[name_key(work_title(row['title_original']))].append((identifier, row['start_date']))
            if row.get('event_type') == 'cinema_release' and row.get('country') == 'JP':
                japanese_releases[name_key(work_title(row['title_original']))] = row
    upcoming, archive = [], []
    for identifier, rows in groups.items():
        prior = records.get(identifier, {})
        has_poster = prior.get('poster_url') or any(row.get('poster_url') for row in rows)
        complete_programme = is_programme(rows[0]) and any(record.get('artwork_url') for record in [prior,*rows])
        profile_source = rows[0].get('source_id') == 'apple-tv' or urlsplit(
            rows[0].get('programme_url') or rows[0].get('evidence_url') or '').hostname == 'eiga.com'
        needs_profile = profile_source and not any(item.get('profile', {}).get('text') for item in (prior, *rows))
        if complete_programme or (prior.get('title_zh') and has_poster and not needs_profile) or prior.get('checked_at', '') > retry_after:
            continue
        future = [row for row in rows if row['start_date'] >= today[:7 if row.get('date_precision') == 'month' else 10]]
        if future:
            row = min(future, key=lambda row: row['start_date'])
            upcoming.append((identifier, row))
        else:
            row = max(rows, key=lambda row: row['start_date'])
            archive.append((identifier, row))
    def priority(item):
        identifier, row = item
        prior = records.get(identifier, {})
        missing_picture = not any(record.get('poster_url') or record.get('artwork_url') for record in (row, prior))
        return (not missing_picture, bool(prior.get('checked_at')), row['start_date'])

    upcoming.sort(key=priority)
    archive.sort(key=lambda item: (not records.get(item[0], {}).get('checked_at'), item[1]['start_date']), reverse=True)
    old_quota = min(len(archive), max(1, limit // 10)) if upcoming else limit
    now = instant.isoformat()
    front_quota = max(0, limit - old_quota)
    batch = [*upcoming[:front_quota], *archive[:old_quota], *upcoming[front_quota:], *archive[old_quota:]]

    def resolve(candidate):
        identifier, row = candidate
        title = name_key(work_title(row['title_original']))
        evidence = japanese_releases.get(title)
        related = None
        if evidence and evidence['id'] != row['id'] and row.get('country') == 'JP' and row['start_date'][:7] == evidence['start_date'][:7]:
            related = lookup.source_facts(evidence)
        try:
            facts = lookup.resolve(row, related=related)
        except (KeyError, TypeError, ValueError, AttributeError):
            facts = {}
        return identifier, row, title, facts

    updated = 0
    with ThreadPoolExecutor(max_workers=5) as pool:
        for offset in range(0, len(batch), 5):
            if updated >= limit or time.monotonic() >= deadline:
                break
            window = [item for item in batch[offset:offset+5] if records.get(item[0], {}).get('checked_at') != now]
            for identifier, row, title, facts in pool.map(resolve, window[:limit-updated]):
                equivalent = {identifier}
                if facts.get('programme_start') and facts.get('programme_end'):
                    equivalent.update(key for key, day in vera_titles[title]
                                      if facts['programme_start'] <= day <= facts['programme_end'])
                for key in equivalent:
                    previous_record = records.get(key, {})
                    merged = {**previous_record, **{name: value for name, value in facts.items() if value},
                              'source_title': row['title_original'], 'checked_at': now}
                    if facts.get('profile'):
                        saved = previous_record.get('profile', {})
                        profile = facts['profile']
                        if saved.get('language') in ('zh', 'zh-CN') and profile.get('language') not in ('zh', 'zh-CN'):
                            profile = {key: value for key, value in profile.items() if key not in ('text', 'language', 'source_url')}
                        merged['profile'] = {**saved, **profile}
                    records[key] = merged
                updated += 1
    films = {key: rows for key, rows in groups.items() if not is_programme(rows[0])}
    def with_published_art(identifier, rows):
        artwork = {field: row[field] for row in rows for field in ART_FIELDS if row.get(field)}
        return {**artwork, **records.get(identifier, {})}

    available = [with_published_art(key, rows) for key, rows in films.items()]
    programmes = [with_published_art(key, groups[key]) for key in groups.keys() - films.keys()]
    active = [with_published_art(key, rows) for key, rows in films.items()
              if any(row['start_date'] >= today[:len(row['start_date'])] for row in rows)]
    report = {'checked_at': instant.isoformat(), 'looked_up_this_run': updated, 'works': len(films),
              'with_douban_title': sum(bool(record.get('title_zh')) for record in available),
              'with_poster': sum(bool(record.get('poster_url')) for record in available),
              'with_artwork': sum(bool(record.get('poster_url') or record.get('artwork_url')) for record in available),
              'programmes_with_artwork': sum(bool(record.get('artwork_url')) for record in programmes),
              'active_works': len(active), 'active_with_douban_title': sum(bool(record.get('title_zh')) for record in active),
              'active_with_poster': sum(bool(record.get('poster_url')) for record in active),
              'active_with_artwork': sum(bool(record.get('poster_url') or record.get('artwork_url')) for record in active),
              'active_checked': sum(bool(record.get('checked_at')) for record in active),
              'request_failures': dict(lookup.errors)}
    return {'schema_version': 1, 'report': report, 'records': records}
