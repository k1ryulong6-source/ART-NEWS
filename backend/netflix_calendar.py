"""Discover dated Netflix originals from the public schedule and a release guide."""
import json
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from .exhibition_sources import error_kind, linked_url
from .exhibitions import normalized
from .film_calendar import MONTHS, base, text
from .film_profiles import prose
from .japan_film_calendar import image_fields
from .streaming_premieres import EARLIER, add_proof

ANIMATION = re.compile(r'\b(?:animated|animation|anime|cartoons?|stop.motion)\b', re.I)
NON_SCRIPTED = re.compile(r'\b(?:stand.?up|reality (?:show|series|competition|dating|tv)|podcast|talk show|'
                          r'variety show|(?:game|quiz) show|live (?:event|sports|show)|competition (?:program|show|series)|'
                          r'dating (?:experiment|show)|unscripted|bonus content|magic special|WWE Raw|'
                          r'World Cup.{0,40}Final Draw|awards ceremony|My Next Guest Needs No Introduction|'
                          r'Love Is Blind|The Great British Baking Show|Hot Ones|Salish.s 12 Games of Christmas|'
                          r'one.man show|standup comedy|celebrity prank)\b', re.I)
EARLIER_WINDOW = re.compile(r'\b(?:library addition|catalogue addition|previously (?:aired|streamed)|'
                            r'previously released on|streaming again|regional expansion|re.release)\b', re.I)
THEATRICAL = re.compile(r'\bin (?:select )?(?:theat(?:er|re)s|cinemas|IMAX)\b|\btheatrical (?:release|run)\b', re.I)
SEASON = re.compile(r'Season (\d{1,2})', re.I)
MONTH_ARTICLE = re.compile(r'/coming-soon/whats-coming-to-netflix-in-([a-z]+)-(20\d\d)/?')
DATED_HEADING = re.compile(r"(?:What[’']s )?Coming(?: to Netflix)? on ([A-Za-z]+) (\d{1,2})(?:st|nd|rd|th)", re.I)
ORIGINAL = re.compile(r'(.+?)\s+\(([^()]+)\)\s+Netflix Original\s*[–—-]\s*(.+)', re.I)
WATCH = re.compile(r'https://www\.netflix\.com/title/(\d+)(?:\?[^#]*)?')
FILM_ID = 2694103
SERIES_ID = 2170013


def series_season(label):
    edition = SEASON.fullmatch(label)
    if edition and 1 <= int(edition[1]):
        return int(edition[1])
    return 1 if label.casefold() == 'limited series' else None


def next_props(soup):
    script = soup.find(id='__NEXT_DATA__')
    if script is None or not script.string:
        raise ValueError('missing_netflix_public_data')
    return json.loads(script.string)['props']


def public_schedule(soup):
    page = next_props(soup)['pageProps']
    report = page['data']
    if not isinstance(report.get('data'), list):
        raise ValueError('invalid_netflix_public_schedule')
    records = {}
    for row in report['data']:
        title = row.get('title1')
        if not title:
            continue
        day = datetime.fromtimestamp(row['startTime'] / 1000, timezone.utc).date().isoformat()
        season = None
        if row.get('collection') == FILM_ID:
            season = 0
        elif row.get('collection') == SERIES_ID and row.get('genre') != 100199:
            edition = row.get('title2') or ''
            season = series_season(edition) or (1 if edition == title else None)
        records[normalized(title), day] = (season, row)
    return records, page.get('countryCode'), report.get('totalItems')


def guide_month(soup, url):
    match = MONTH_ARTICLE.fullmatch(urlsplit(url).path)
    month, year = MONTHS[match[1]], int(match[2])
    scope = soup.select_one('#article-body .entry-inner')
    if not scope:
        raise ValueError('missing_netflix_monthly_article')
    images = [(normalized(img.get('alt') or ''), img.get('data-src') or img.get('src'))
              for img in scope.select('figure img[alt]')]
    current = None
    records = {}
    for part in scope.select(':scope > h4, :scope > ul'):
        if part.name == 'h4':
            found = DATED_HEADING.fullmatch(text(part))
            current = date(year, month, int(found[2])).isoformat() if found and MONTHS.get(found[1].lower()) == month else None
            continue
        if not current:
            continue
        for li in part.select(':scope > li'):
            found = ORIGINAL.fullmatch(text(li))
            if not found:
                continue
            title, edition, summary = found.groups()
            season = 0 if edition == str(year) else series_season(edition)
            if season is not None:
                work = normalized(title)
                image = next((src for label, src in images if src and src.startswith('https://') and
                              (label == work or (len(work) >= 9 and label.startswith(work)))), None)
                records[work, current] = (title, season, summary, url, image)
    return records


def guide_calendar(soup):
    cards = soup.select('article[data-release-kind][data-release-origin]')
    if not cards:
        raise ValueError('missing_netflix_guide_cards')
    records, excluded = {}, set()
    for card in cards:
        if card['data-release-origin'] != 'original':
            continue
        title = text(card.select_one('.won-upcoming__card-title-text'))
        time = card.select_one('time[datetime]')
        link = card.select_one('a.won-upcoming__action--queue[href]')
        if not title or not time:
            continue
        day = datetime.fromisoformat(time['datetime']).date().isoformat()
        key = normalized(title), day
        kind = card['data-release-kind']
        badge = text(card.select_one('.won-upcoming__badge-type'))
        if kind not in ('movie', 'series') or badge not in ('Movie', 'Series'):
            excluded.add(key)
            continue
        if not link or not (watch := WATCH.fullmatch(link['href'])):
            continue
        captions = [p.strip() for p in text(card.select_one('.won-upcoming__title-meta')).split('·')]
        season = series_season(captions[0]) if kind == 'series' else 0
        year = next((value for value in captions if re.fullmatch(r'20\d\d', value)), '')
        if season is None or (season <= 1 and year != day[:4]):
            continue
        image = card.select_one('img[data-won-poster-src]')
        records[key] = (title, watch[1], image['data-won-poster-src'] if image else None)
    return records, excluded


def press_work(soup, identifier):
    props = next_props(soup)
    state = props.get('apolloState', {})
    show = state.get('NetflixOriginal:' + identifier, {})
    if show.get('status') != 200 or not show.get('isOriginalInCoverageCountry'):
        return {}
    description = text(BeautifulSoup(show.get('description') or show.get('logline') or '', 'html.parser'))
    photo = soup.select_one('meta[property="og:image"][content]')
    genres = ' '.join(g.get('name', '') for g in show.get('coreGenres({"locale":"en"})', []) if isinstance(g, dict))
    return {'title': show.get('title'), 'type': show.get('titleType'), 'blurb': description, 'genres': genres,
            'image': photo['content'] if photo else None, 'theatrical': bool(show.get('theatricalReleases'))}


def read_netflix(source, get, today, previous, coverage):
    """Keep source-reported premieres identifiable and verify against Netflix when available."""
    failed = coverage.setdefault('failed_pages', {})

    def load(url, parse):
        try:
            return parse(BeautifulSoup(get(url), 'html.parser'))
        except (OSError, ValueError, KeyError, TypeError, OverflowError) as error:
            failed[url] = error_kind(error)
            return None

    schedule, region, listed = load(source['url'], public_schedule) or ({}, None, None)
    guide, excluded = load(source['guide_url'], guide_calendar) or ({}, set())
    coverage.update(official_schedule_market=region, official_index_listed=listed,
                    official_index_candidates=sum(season is not None for season, _ in schedule.values()))
    months = []
    index = load(source['guide_index_url'], lambda soup: soup)
    if index:
        for link in index.select('a[href]'):
            url = linked_url(source['guide_index_url'], link['href'], host_only=True)
            match = MONTH_ARTICLE.fullmatch(urlsplit(url or '').path)
            if match and match[1] in MONTHS:
                months.append((date(int(match[2]), MONTHS[match[1]], 1), url))
    first_month = today.replace(day=1)
    # Keep the preceding month's history and the next published month available for comparison.
    lower = (first_month - timedelta(days=1)).replace(day=1)
    upper = (first_month + timedelta(days=32)).replace(day=1)
    monthly = {}
    for _, url in sorted(set(months)):
        month, year = MONTH_ARTICLE.fullmatch(urlsplit(url).path).groups()
        if lower <= date(int(year), MONTHS[month], 1) <= upper:
            monthly.update(load(url, lambda soup: guide_month(soup, url)) or {})
    coverage['guide_monthly_candidates'] = len(monthly)
    coverage['guide_calendar_candidates'] = len(guide)

    known = {(row.get('netflix_title_id'), row.get('streaming_season', 0), row['start_date']): row for row in previous
             if row.get('source_id') == source['id'] and row.get('netflix_title_id')}
    confirmed = {(normalized(row['premiere_title']), row['start_date']): row for row in previous
                 if row.get('source_id') == source['id'] and row.get('premiere_basis') == 'official_announcement'}
    seen = set()
    media_checks = 0
    formats = Counter()
    for key in sorted(monthly.keys() | (schedule.keys() & guide.keys()), key=lambda k: (k[1], k[0])):
        work, day = key
        title, identifier, image = guide.get(key, (None, None, None))
        caption, published_season, summary, article, article_image = monthly.get(
            key, (None, None, '', source['guide_url'], None))
        confirmed_row = confirmed.get(key, {})
        default_season = confirmed_row.get('streaming_season', 0) if confirmed_row else published_season
        season, official_item = schedule.get(key, (default_season, {}))
        if (season is None or key in excluded or (work, season) in seen
                or NON_SCRIPTED.search(' '.join((title or caption or '', summary)))
                or EARLIER.search(summary) or EARLIER_WINDOW.search(summary)):
            continue
        title = title or caption or official_item['title1']
        if not identifier and official_item and not season:
            identifier = str(official_item['videoID'])
            image = image or official_item.get('image')
        identifier = identifier or confirmed_row.get('netflix_title_id')
        watch = f'https://www.netflix.com/title/{identifier}' if identifier else None
        press_url = source['media_url'] + identifier if identifier else None
        prev = known.get((identifier, season, day), {}) or confirmed_row
        facts = {}
        if press_url and day >= today.isoformat() and not prev.get('netflix_press_checked') and media_checks < source['media_limit']:
            media_checks += 1
            facts = load(press_url, lambda soup: press_work(soup, identifier)) or {}
            if facts and normalized(facts['title'] or '') != work:
                facts = {}
        description = facts.get('blurb') or summary
        if NON_SCRIPTED.search(description) or EARLIER.search(description) or EARLIER_WINDOW.search(description):
            continue
        seen.add((work, season))
        animated = (identifier in source.get('animation_ids', []) or
                    ANIMATION.search(' '.join((summary, description, facts.get('genres') or ''))))
        format_ = ('animated_series' if animated else 'series') if season else ('animated_film' if animated else 'film')
        primary = source['url'] if official_item else article
        row = {**base(source, title, day, 'day', 'streaming_release', primary),
               'streaming_format': format_, 'evidence_status': 'official_confirmed' if official_item else 'media_reported'}
        if season:
            row['streaming_season'] = season
        if identifier:
            row.update(netflix_title_id=identifier, watch_url=watch)
        if not season and (facts.get('theatrical') or THEATRICAL.search(description) or THEATRICAL.search(summary)):
            row['streaming_path'] = 'theatrical'
        if press_url and facts:
            row['programme_url'] = press_url
            row['netflix_press_checked'] = True
        photo_url, photo_source = next(((url, via) for url, via in (
            (facts.get('image'), press_url), (official_item.get('image'), source['url']),
            (image, source['guide_url']), (article_image, article)) if url), (None, None))
        artwork = image_fields(photo_url, photo_source, key='artwork')
        if artwork:
            row.update(artwork)
        if description and (profile := prose(description, 'en', press_url if facts.get('blurb') else article)):
            row['profile'] = profile
        row = {**prev, **row}
        if not official_item and prev.get('premiere_basis') == 'official_announcement':
            primary = prev['premiere_source_url']
            official_item = True
        formats[row['streaming_format']] += 1
        yield add_proof(row, primary, basis='official_announcement' if official_item else 'reported_premiere')
    coverage.update(by_format=dict(formats), media_attempted=media_checks)
