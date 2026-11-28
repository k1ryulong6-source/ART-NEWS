"""Dated Japanese releases, currently showing films and venue timetables from 映画.com."""
import re
from datetime import datetime, timedelta
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from .exhibition_sources import error_kind, linked_url
from .film_calendar import base, film_image, local_day, screening, text
from .film_profiles import prose
from .reading import public_url

MOVIE = re.compile(r'/movie/(\d+)/')
CARDS = '.list-block[id^="mv"]'
FULL_DAY = r'20\d{2}年\d{1,2}月\d{1,2}日'
PLATFORMS = {
    'netflix': 'Netflix', 'amazon prime video': 'Prime Video', 'prime video': 'Prime Video',
    'apple tv': 'Apple TV', 'apple tv+': 'Apple TV', 'disney+': 'Disney+',
    'ディズニープラス': 'Disney+', 'hulu': 'Hulu', 'u-next': 'U-NEXT', 'mubi': 'MUBI',
}


def image_fields(url, page, *, key='poster'):
    url = film_image(url, page)
    if not url:
        return {}
    return {key + '_url': url, key + '_source_url': page}


def poster_of(card, page):
    image = card.select_one('.img-box img, .movie-image img')
    return image_fields(image.get('data-src') or image.get('src'), page) if image else {}


def film_link(card, url, selector='.title a[href]'):
    link = card.select_one(selector)
    movie = linked_url(url, link.get('href'), host_only=True) if link else None
    return movie if movie and MOVIE.fullmatch(urlsplit(movie).path) else None


def screening_dates(soup, source, instant):
    """Use the date cell and check the time stamp against the published local time."""
    if text(soup.find('h1')) != source['venue']:
        raise ValueError('theatre_name_mismatch')
    zone = ZoneInfo(source['timezone'])
    for section in soup.select('section[id^="m"]:has(table.weekly-schedule)'):
        title = text(section.select_one('.movie-schedule h2, h2.title-xlarge'))
        programme = film_link(section, source['url'], '.movie-image a[href]')
        evidence = source['url'] + '#' + section['id']
        for cell in section.select('table.weekly-schedule td[data-date]'):
            if not re.fullmatch(r'\d{8}', cell['data-date']):
                continue
            day = datetime.strptime(cell['data-date'], '%Y%m%d').date()
            if day < instant.astimezone(zone).date():
                continue
            for slot in cell.select('[data-time]'):
                if not re.fullmatch(r'\d{9,11}', slot['data-time']):
                    continue
                timestamp = datetime.fromtimestamp(int(slot['data-time']), zone)
                booking = public_url(slot.get('href'), source['url'])
                if booking and re.fullmatch(r'\d{8}', urlsplit(booking).fragment) and urlsplit(booking).fragment != cell['data-date']:
                    booking = None
                row = screening(source, title, day, text(slot), proof=evidence, programme=programme, booking=booking)
                if row and datetime.fromisoformat(row['start_at']) == timestamp:
                    yield {**row, **poster_of(section, programme or evidence), 'evidence_status': 'media_reported'}


def current_films(soup, source, get):
    root = source['url']
    found = {}
    advertised = re.fullmatch(r'全\s*([\d,]+)\s*件', text(soup.select_one('.search-number')))
    if not advertised:
        raise ValueError('showing_total_missing')
    expected = int(advertised[1].replace(',', ''))
    visited = {root}
    for _ in range(32):
        cards = soup.select(CARDS)
        if not cards:
            raise ValueError('missing_showing_catalogue')
        for card in cards:
            movie = film_link(card, root)
            title = text(card.select_one('.title a'))
            if movie and title:
                key = 'eiga-showing-' + MOVIE.fullmatch(urlsplit(movie).path)[1]
                tickets = movie + 'theater/' if card.select_one('a[href$="/theater/"]') else None
                found[key] = {'id': key, 'title_original': title, 'event_type': 'cinema_release', 'channel': 'film',
                              'country': 'JP', 'source_id': source['id'], 'source_name': source['name'],
                              'evidence_url': movie, 'booking_url': tickets, 'evidence_status': 'media_reported',
                              **poster_of(card, movie)}
                if profile := prose(text(card.select_one('.txt-box > p.txt')), 'ja', movie):
                    found[key]['profile'] = profile
        next_link = next((a for a in soup.select('.pagination a[href]') if text(a) == '次へ'), None)
        if not next_link:
            if len(found) != expected:
                raise ValueError('showing_catalogue_count_mismatch')
            return list(found.values())
        page = linked_url(root, next_link['href'], host_only=True)
        if not page or page in visited or not re.fullmatch(r'/now/all/release/\d+/', urlsplit(page).path):
            raise ValueError('showing_pagination_changed')
        visited.add(page)
        soup = BeautifulSoup(get(page), 'html.parser')
    raise ValueError('showing_catalogue_not_exhausted')


def platform_name(raw):
    raw = raw.strip()
    return PLATFORMS.get(raw.casefold(), raw) if raw else None


def date_notice(description, today):
    for pattern in (rf'^([^。]{{2,55}}?)で\s*({FULL_DAY})から配信', rf'^({FULL_DAY})から([^。]{{2,55}}?)で配信'):
        if match := re.search(pattern, description):
            platform, date = match.groups() if not match[1][0].isdigit() else match.groups()[::-1]
            return local_day(date, today), platform_name(platform)
    return None, None


def release_dates(soup, source, get, today, previous):
    root = source['url']
    pages = [source['week_url'], root]
    for link in soup.select('.nav-tab a[href]'):
        href = linked_url(root, link.get('href'), host_only=True)
        if href and re.fullmatch(r'/coming/20\d{2}(?:0[1-9]|1[0-2])/', urlsplit(href).path):
            if href not in pages:
                pages.append(href)
    known = {(row['evidence_url'], row.get('listing_date', row['start_date'])): row
             for row in previous if row.get('source_id') == source['id']}
    records = {}
    unchecked, failed_pages = set(), {}
    requests_left = source.get('detail_limit', 105)
    for url in pages:
        try:
            page = soup if url == root else BeautifulSoup(get(url), 'html.parser')
        except (OSError, ValueError) as error:
            failed_pages[url] = error_kind(error)
            continue
        for card in page.select(CARDS):
            movie = film_link(card, root)
            title = text(card.select_one('.title a'))
            heading = text(card.find_previous_sibling('h2', class_='title-square'))
            listed_day = local_day(heading.replace(' ', ''), today)
            if not movie or not title or not listed_day or listed_day < today - timedelta(days=7):
                continue
            description = text(card.select_one('.txt-box > p.txt'))
            day, platform = date_notice(description, today)
            kind = 'streaming_release' if day else None
            date_evidence = url
            poster = poster_of(card, movie)
            prior = known.get((movie, listed_day.isoformat()))
            if not kind and prior:
                day, kind, platform = datetime.fromisoformat(prior['start_date']).date(), prior['event_type'], prior.get('platform')
                date_evidence = prior.get('date_source_url', url)
            if not kind and card.select_one('a[href$="/theater/"]'):
                day, kind = listed_day, 'cinema_release'
            conflicting_date = kind == 'streaming_release' and day != listed_day and date_evidence != movie
            if requests_left and (not kind or conflicting_date):
                requests_left -= 1
                try:
                    detail = BeautifulSoup(get(movie), 'html.parser')
                except (OSError, ValueError):
                    detail = None
                info = text(detail.select_one('p.data')) if detail else ''
                streaming = re.search(rf'配信開始日\s*[：:]\s*({FULL_DAY})', info)
                cinema = re.search(rf'劇場公開日\s*[：:]\s*({FULL_DAY})', info)
                if cinema and not kind:
                    kind, day, date_evidence = 'cinema_release', local_day(cinema[1], today), movie
                elif streaming:
                    kind, day, date_evidence = 'streaming_release', local_day(streaming[1], today), movie
                    company = re.search(r'配信\s*[：:]\s*(.+?)(?=\s*配信開始日|$)', info)
                    platform = platform_name(company[1]) if company else platform
            if not kind or not day:
                unchecked.add(movie)
                continue
            if day < today - timedelta(days=7):
                continue
            if kind == 'streaming_release' and re.search(r'シーズン\s*\d|[Ss]eason\s+\d', title):
                continue
            row = {**base(source, title, day.isoformat(), 'day', kind, movie), **poster,
                   'date_source_url': date_evidence, 'listing_date': listed_day.isoformat(), 'evidence_status': 'media_reported'}
            if profile := prose(description, 'ja', movie):
                row['profile'] = profile
            if kind == 'streaming_release':
                row.update(platform=platform, market='日本')
            records[(movie, day, kind, platform)] = row
    confirmed = {movie for movie, *_ in records}
    return list(records.values()), {'unclassified':len(unchecked - confirmed), 'failed_pages':failed_pages}
