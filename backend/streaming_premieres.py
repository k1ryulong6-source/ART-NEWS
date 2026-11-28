"""Verify a film's first streaming date from a release announcement."""
import json
import re
from datetime import date, datetime
from urllib.parse import urlsplit
from xml.etree import ElementTree

from bs4 import BeautifulSoup

from .exhibition_sources import error_kind, linked_url
from .film_calendar import MONTHS, base, local_day, text
from .film_profiles import prose
from .japan_film_calendar import image_fields

WORDS = {**MONTHS, **{name[:3]: number for name, number in MONTHS.items()}}
MONTH_WORD = '|'.join(WORDS)
DATE = re.compile(rf'\b({MONTH_WORD})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(20\d{{2}}))?\b'
                  rf'|\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({MONTH_WORD})(?:,?\s+(20\d{{2}}))?\b', re.I)
PREMIERE = re.compile(r'\b(?:premier(?:e[sd]?|ing)|debut(?:s|ed|ing)?)\b', re.I)
RELEASE = re.compile(r'\b(?:premier\w*|debut\w*|trailers?|first look|releas\w*|films?|movies?|documentar\w*)\b', re.I)
FILM = re.compile(r'\b(?:films?|movies?|documentar(?:y|ies))\b', re.I)
SERIES = re.compile(r'\b(?:limited series|documentary series|docuseries|new series|season \d+|episode \d+)\b', re.I)
FIRST_ONLINE = re.compile(r'\b(?:first (?:online|streaming)|(?:online|streaming) (?:premiere|debut))\b', re.I)
SCOPE = re.compile(r'\b(?:global(?:ly)?|worldwide|only on|exclusively on)\b', re.I)
NETFLIX_LAUNCH = re.compile(r'\b(?:new (?:Netflix )?(?:film|movie|documentary)|Netflix Original|'
                            r'first look|unveil\w*|first trailer|teaser (?:poster|trailer)|releases (?:the )?trailer)\b', re.I)
EARLIER = re.compile(r'\b(?:pvod|previously (?:streamed|available|released online)|'
                     r'already (?:streaming|available (?:online|on))|streaming again|'
                     r'returns? to (?:streaming|the catalogue|the library|Netflix|Disney\+|Hulu|Apple TV)|'
                     r'(?:available|released) (?:to rent|for digital purchase|on digital))\b', re.I)
LOCAL_WINDOW = re.compile(r'\b(?:first time in|in (?:select|additional|new) (?:markets|territories|countries))\b', re.I)
QUOTED = re.compile(r'“([^”]+)”|‘([^’]+)’|"([^"]+)"|\x27([^\x27]+)\x27')


def released_on(value, reference, service_at):
    match = min(DATE.finditer(value), key=lambda match: abs(match.start() - service_at), default=None)
    if not match:
        return None
    month, day, year = match.group(1, 2, 3) if match[1] else match.group(5, 4, 6)
    number = WORDS[month.lower()]
    try:
        return date(int(year), number, int(day)) if year else local_day(f'{number}/{day}', reference)
    except ValueError:
        return None


def title_pattern(title):
    folded = title.replace('’', "'").strip()
    return re.compile(r'(?<!\w)' + re.escape(folded).replace("'", "['’]") + r'(?!\w)', re.I)


def press_premiere(paragraphs, title, platform, reference, *, require_first_online=False):
    """Only take a date from a statement that names the film, service and premiere."""
    name = title_pattern(title)
    service = re.compile(r'(?<!\w)(?:on|via)\s+' + re.escape(platform) + r'(?!\w|\s+in\b)', re.I)
    if any(name.search(p) and EARLIER.search(p) for p in paragraphs):
        return None
    for paragraph in paragraphs:
        for sentence in re.split(r'(?<=[.!?])\s+(?=[A-Z“‘])', paragraph):
            if not (film := name.search(sentence)):
                continue
            verbs = list(PREMIERE.finditer(sentence, film.end()))
            for index, verb in enumerate(verbs):
                stop = min(verb.end() + 100, verbs[index + 1].start()) if index + 1 < len(verbs) else verb.end() + 100
                start = max(film.end(), verb.start() - 20)
                statement = sentence[start:stop]
                confirmed = FIRST_ONLINE.search(statement) or (not require_first_online and SCOPE.search(statement))
                if (confirmed and (platform_ref := service.search(statement)) and not LOCAL_WINDOW.search(statement)
                        and (day := released_on(sentence[verb.end():stop], reference, start + platform_ref.start() - verb.end()))):
                    return day
    return None


def press_pages(urls, get, coverage, limit=12):
    for url in list(urls)[:limit]:
        try:
            yield url, BeautifulSoup(get(url), 'html.parser')
        except (OSError, ValueError) as error:
            coverage.setdefault('failed_pages', {})[url] = error_kind(error)


def add_proof(row, url, *, title=None, basis='official_announcement'):
    return {**row, 'premiere_source_url': url, 'premiere_basis': basis,
            'premiere_title': title or row['title_original']}


def apple_dates(payload, news, source, get, coverage):
    originals = json.loads(payload)['results']['originals']
    films = {}
    for item in originals:
        if item.get('showTypeKey') != 'films' or not item.get('title'):
            continue
        label = (item.get('releaseDateDisplayString') or '').strip()
        match = re.fullmatch(r'([A-Za-z]+) (\d{1,2}), (20\d{2})', label)
        if not match or match[1].lower() not in MONTHS:
            continue
        day = date(int(match[3]), MONTHS[match[1].lower()], int(match[2]))
        if (item.get('releaseDateISOString') or '').startswith(day.isoformat()):
            films[item['title']] = day, item
    # The Originals index supplies current dates. Old announcements can contain superseded dates.
    try:
        feed = ElementTree.fromstring(news)
    except ElementTree.ParseError as error:
        raise ValueError('invalid_apple_press_feed') from error
    entries = feed.findall('{*}entry')
    if not entries or not films:
        raise ValueError('missing_apple_press_entries')
    announcements = {}
    for entry in entries:
        headline = entry.findtext('{*}title') or ''
        url = linked_url(source['url'], entry.findtext('{*}id'), host_only=True)
        if url and RELEASE.search(headline):
            titles = [title for title in films if title_pattern(title).search(headline)]
            if titles:
                announcements[url] = titles
    seen = set()
    for url, page in press_pages(announcements, get, coverage):
        paragraphs = [text(node) for node in page.select('.body-copy p, p.body-copy, .post-subhead')]
        for title in announcements[url]:
            day, item = films[title]
            if title in seen or press_premiere(paragraphs, title, source['platform'], day) != day:
                continue
            work = linked_url(source['url'], item.get('url'), host_only=True)
            if not work:
                continue
            row = base(source, title, day.isoformat(), 'day', 'streaming_release', work)
            image = item.get('image') or {}
            if image.get('dirpath') and image.get('name'):
                row.update(image_fields(image['dirpath'] + image['name'], work))
            seen.add(title)
            yield add_proof(row, url)


def press_dates(soup, source, get, coverage):
    netflix = source['adapter'] == 'netflix_news'
    path_prefix = '/en/news/' if netflix else '/news/'
    stories = {}
    for link in soup.select('a[href]'):
        url = linked_url(source['url'], link['href'], host_only=True)
        path = urlsplit(url or '').path
        if not path.startswith(path_prefix) or path == path_prefix or '/' in path[len(path_prefix):].strip('/'):
            continue
        headline = text(link)
        stories.setdefault(url, headline)
        if not stories[url] and headline:
            stories[url] = headline
    if not stories:
        raise ValueError('missing_streaming_press_index')
    candidates = {url: title for url, headline in stories.items() if RELEASE.search(headline)
                  and not SERIES.search(headline) and (title := quoted_title(headline))}
    for url, page in press_pages(candidates, get, coverage):
        selectors = ('[class*=ArticleCopy] p' if netflix
                     else '.inc_rich_article .rich-text-container > :is(p, ul, .summary)')
        paragraphs = [text(node) for node in page.select(selectors)]
        intro = ' '.join(paragraphs[:3])
        title = candidates[url]
        if not FILM.search(intro) or SERIES.search(intro):
            continue
        if netflix:
            platform = source['platform']
            try:
                posted = datetime.strptime(text(page.select_one('[class*=ArticleDateWrapper]')), '%d %B %Y').date()
            except ValueError:
                continue
        else:
            original = re.search(r'\b(Disney\+|Hulu) [Oo]riginal (?:feature |documentary )?(?:film|movie)\b', intro)
            if not original:
                continue
            platform = original[1]
            try:
                posted = datetime.strptime(text(page.select_one('.publish-date-standalone')), '%B %d, %Y').date()
            except ValueError:
                continue
        day = press_premiere(paragraphs, title, platform, posted,
                             require_first_online=netflix and not NETFLIX_LAUNCH.search(stories[url] + ' ' + intro))
        if not day or day < posted:
            continue
        row = base(source, title, day.isoformat(), 'day', 'streaming_release', url)
        row['platform'] = platform
        card = page.select_one('meta[property="og:image"][content]')
        if card and (artwork := image_fields(card['content'], url, key='artwork')):
            row.update(artwork, artwork_kind='still')
        if profile := prose(' '.join(paragraphs[1:3]), 'en', url):
            row['profile'] = profile
        yield add_proof(row, url)


def quoted_title(headline):
    found = QUOTED.search(headline)
    return next(part.rstrip(' ,') for part in found.groups() if part) if found else None


def verified_dates(entries, sources, previous):
    """Reuse the work record and stable ID when a separate announcement verifies its premiere."""
    work = {(row['source_id'], row['evidence_url'], row['start_date'], row.get('platform')): row for row in previous
            if row['event_type'] == 'streaming_release'}
    source_by_id = {source['id']: source for source in sources}
    for entry in entries:
        if (source := source_by_id.get(entry['source_id'])) is None:
            continue
        key = entry['source_id'], entry['work_url'], entry['start_date'], entry['platform']
        row = work.get(key) or base(source, entry['title'], entry['start_date'], 'day', 'streaming_release', entry['work_url'])
        row = {**row, 'platform': entry['platform'], 'market': entry.get('market') or row.get('market')}
        yield add_proof(row, entry['premiere_url'], title=entry.get('official_title'), basis='verified_release')
