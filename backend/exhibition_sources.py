"""Read public Japanese exhibition listings and preserve their date and venue evidence."""
import json
import math
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup

from .japanese_art import next_fallback
from .reading import public_url

USER_AGENT = 'CultureDesk/0.3 ExhibitionCalendar (+https://mujianrest.work/)'
MAX_PAGE_BYTES = 6_000_000
SITE_DELAY_SECONDS = 1.15
HOST_BUDGET_SECONDS = 260
DATE = re.compile(r'(?:(?P<year>20\d{2})\s*[年./-]\s*|令和\s*(?P<era>元|\d{1,2})年\s*)?(?P<month>\d{1,2})\s*[月./-]\s*(?P<day>\d{1,2})(?:日|\b)')
RANGE = r'[〜～~–—―－-]'
NON_EXHIBITION = re.compile(r'トーク|ワークショップ|パーティー|パフォーマンス|音楽|公開制作・滞在制作')
CATEGORY = {
    'painting': r'絵画|絵図|油彩|日本画|浮世絵|水彩|ドローイング|版画|イラスト|painting|drawing|printmaking',
    'sculpture': r'彫刻|立体|sculpture',
    'installation': r'インスタレーション|空間芸術|installation|site.specific',
    'photography': r'写真|photograph',
    'media': r'映像|映画|メディアアート|デジタルアート|アニメーション|video art|media art',
    'design': r'デザイン|建築|陶芸|工芸|漆|民藝|染織|ガラス|テキスタイル|design|architecture|craft',
    'history': r'考古|歴史|民俗|古美術|仏教美術|文化財|heritage',
    'literature': r'漫画|マンガ|絵本|文学',
    'festival': r'芸術祭|ビエンナーレ|トリエンナーレ|アートフェスティバル|biennial|biennale|triennale',
}
ART_MARKER = re.compile(r'展覧会|個展|企画展|回顧展|作品展|美術展|コレクション展|公募展|展示|exhibition|retrospective', re.I)


def clean(value):
    return ' '.join(value.split()) if isinstance(value, str) else ''


def node_text(node):
    return clean(node.get_text(' ', strip=True)) if node else ''


def iso_day(value):
    try:
        return date.fromisoformat(value).isoformat() if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value or '') else None
    except (TypeError, ValueError):
        return None


def date_range(raw):
    """Use a printed year or an unambiguous same-year shortened end date."""
    normalized = unicodedata.normalize('NFKC', raw)
    # In date labels followed by a room or note, only parse the exhibited interval.
    normalized = re.split(r'\s*\|\s*|休館|入場|開館時間', normalized, maxsplit=1)[0]
    matches = list(DATE.finditer(normalized))
    if not matches:
        match = re.search(r'(20\d{2})年\s*(\d{1,2})月(?!\s*\d)', normalized)
        if match and 1 <= int(match[2]) <= 12 and not re.search(r'未定|未発表', normalized):
            return f'{match[1]}-{int(match[2]):02d}', None
        return None, None

    def year(match):
        if match['year']:
            return int(match['year'])
        if match['era']:
            return 2018 + (1 if match['era'] == '元' else int(match['era']))
        return None

    def day(y, m, d):
        try:
            return date(y, int(m), int(d)).isoformat()
        except (TypeError, ValueError):
            return None

    first = matches[0]
    if re.search(RANGE + r'\s*$', normalized[:first.start()]):
        return None, None
    y = year(first)
    if y is None and len(matches) > 1:
        second = matches[1]
        if re.search(RANGE, normalized[first.end():second.start()]) and (int(first['month']), int(first['day'])) <= (int(second['month']), int(second['day'])):
            y = year(second)
    start = day(y, first['month'], first['day'])
    if not start:
        return None, None
    end = None
    if len(matches) > 1:
        second = matches[1]
        if re.search(RANGE, normalized[first.end():second.start()]):
            between = normalized[first.end():second.start()]
            end = day(year(second) or (y + 1 if '翌年' in between else y), second['month'], second['day'])
    else:
        end_day = re.match(r'\s*(?:\([^)]{1,8}\)|\[[^\]]{1,8}\])?\s*' + RANGE + r'\s*(\d{1,2})日', normalized[first.end():])
        if end_day:
            end = day(y, first['month'], end_day[1])
    return start, end if end and end >= start else None


def exhibition_types(title, tags):
    text = ' '.join([title, *tags])
    return [kind for kind, pattern in CATEGORY.items() if re.search(pattern, text, re.I)] or ['other']


def observation(source, *, url, title, venue='', prefecture=None, area='', raw_date='', dates=None,
                tags=(), image=None, official=False, status_text=''):
    if not url or not title or len(title) > 400 or len(venue) > 220:
        raise ValueError('invalid_exhibition_card')
    start, end = dates if dates is not None else date_range(raw_date)
    if end and (not start or end < start):
        end = None
    status = 'cancelled' if re.search(r'開催中止|中止のお知らせ|^[【\[（(]?中止[】\]）)]', status_text + ' ' + title) else (
        'postponed' if re.search(r'開催延期|延期のお知らせ|^[【\[（(]?延期[】\]）)]', status_text + ' ' + title) else (
            'tentative' if re.search(r'予定|未定|[（(]仮[）)]', raw_date + ' ' + title) else 'scheduled'))
    return {
        'source': source, 'url': url, 'title': title, 'venue': venue, 'prefecture': prefecture,
        'area': area, 'start': start, 'end': end, 'date_text': raw_date[:240],
        'types': exhibition_types(title, tags), 'labels': list(dict.fromkeys(clean(t)[:60] for t in tags if clean(t))),
        'official': official, 'status': status, 'image': image,
    }


def linked_url(base, href, *, host_only=False):
    value = public_url(href, base) if href else None
    if value and host_only and urlsplit(value).hostname != urlsplit(base).hostname:
        return None
    return value


def prefecture_of(label, config):
    return next((code for code, name, *_ in config['prefectures'] if label == name), None)


def parse_museum_page(payload, url, prefecture, config):
    soup = BeautifulSoup(payload, 'html.parser')
    count = soup.select_one('.c-listHeader_col_contentSearch')
    match = re.fullmatch(r'全\s*([\d,]+)\s*件', node_text(count))
    label = next(name for code, name, *_ in config['prefectures'] if code == prefecture)
    if not match or not soup.title or label not in soup.title.get_text():
        raise ValueError('prefecture_list_structure_changed')
    total = int(match[1].replace(',', ''))
    cards = soup.select('.c-eventItem')
    if (not total and cards) or (total and not cards):
        raise ValueError('prefecture_list_page_count_mismatch')
    rows, unread = [], 0
    for card in cards:
        a = card.select_one('.c-eventItem_museum a[href]')
        venue, _, area = node_text(card.select_one('.c-eventItem_event')).partition('|')
        href = linked_url(url, a['href'], host_only=True) if a else None
        if not href or not re.fullmatch(r'/event/\d+/?', urlsplit(href).path) or not node_text(a):
            unread += 1
            continue
        if area and prefecture_of(clean(area), config) != prefecture:
            unread += 1
            continue
        raw_date = node_text(card.select_one('.c-eventItem_duration'))
        image = card.select_one('.c-eventItem_image img')
        rows.append(observation('internet-museum', url=href, title=node_text(a), venue=clean(venue),
                                prefecture=prefecture, raw_date=raw_date,
                                image=linked_url(url, image.get('data-src') or image.get('src')) if image else None,
                                status_text=node_text(card.select_one('.c-periodRemain'))))
    return rows, total, unread


def parse_tab_page(payload, url, config, expected_area=None):
    query, result = next_fallback(BeautifulSoup(payload, 'html.parser'), 'EventSearch')
    data, paginator = result.get('data'), result.get('paginator') or {}
    total = paginator.get('total')
    if (query.get('excludeClosed') is not True or query.get('localAreaId') != expected_area
            or not isinstance(data, list) or type(total) is not int or total < len(data)
            or (total > 0 and not data)):
        raise ValueError('tab_event_list_structure_changed')
    rows, areas, unread, listed = [], {}, 0, set()
    for item in data:
        venue = (item.get('venue') or {}).get('fields') or {}
        place = venue.get('localArea') or {}
        area_id = (place.get('sys') or {}).get('id')
        name = clean((place.get('fields') or {}).get('name'))
        prefecture = prefecture_of(name, config) or ('13' if name in config['tab_tokyo_areas'] else None)
        if isinstance(area_id, str) and re.fullmatch(r'[A-Za-z0-9_-]{2,80}', area_id):
            areas[area_id] = {'name': name, 'prefecture': prefecture}
        slug, title = item.get('slug'), clean(item.get('eventName'))
        if not isinstance(slug, str) or not re.fullmatch(r'[\w%-]+(?:/[\w%-]+){0,4}', slug) or not title:
            unread += 1
            continue
        href = urljoin(url, '/events/-/' + quote(slug, safe='/%-._'))
        listed.add(href)
        tags = [clean((x.get('fields') or {}).get('name')) for x in item.get('categories') or []]
        kinds = exhibition_types(title, tags)
        # Programmes such as a talk or concert sometimes carry a medium tag.
        # Keep hybrids with exhibition evidence, skip only explicit ancillary events.
        if tags and any(NON_EXHIBITION.fullmatch(tag) for tag in tags) and not ART_MARKER.search(title):
            if all(NON_EXHIBITION.fullmatch(tag) for tag in tags) or re.match(NON_EXHIBITION.pattern, title):
                continue
        if (kinds == ['other'] and tags and set(tags) <= {'自然・科学'}) or (
                NON_EXHIBITION.fullmatch(title) and not ART_MARKER.search(title)):
            continue
        start, end = (iso_day(item.get(k)) for k in ('scheduleStartsOn', 'scheduleEndsOn'))
        image = ((item.get('imageposter') or {}).get('fields') or {}).get('file') or {}
        rows.append(observation('tokyo-art-beat', url=href, title=title, venue=clean(venue.get('fullName')),
                                prefecture=prefecture, area=name, dates=(start, end),
                                raw_date=' 〜 '.join(filter(None, (start, end))), tags=tags,
                                image=linked_url(url, image.get('url'))))
    return rows, total, areas, listed, unread


def parse_aepage(payload, url, config):
    soup = BeautifulSoup(payload, 'html.parser')
    cards = soup.select('main article:has(.exhibition-detail-cont)')
    if not cards:
        raise ValueError('art_navi_exhibition_list_structure_changed')
    rows, unread = [], 0
    for card in cards:
        a = card.select_one('.article-title a[href]')
        target = linked_url(url, a['href'], host_only=True) if a else None
        if not target or not re.fullmatch(r'/exhibitions/\d{8}-AEJ\d+/?', urlsplit(target).path) or not node_text(a):
            unread += 1
            continue
        fields = {node_text(li.select_one('h4')): li for li in card.select('.exhibition-detail-cont > li')}
        dates = fields.get('会期')
        raw_date = node_text(dates).removeprefix('会期').strip()
        venue = node_text(fields.get('会場')).removeprefix('会場').strip()
        area = node_text(card.select_one('.article-detail > span:not([class])'))
        tags = [node_text(tag).lstrip('#') for tag in card.select('.tag-name')]
        img = card.select_one('figure img')
        row = observation('artexhibition', url=target, title=node_text(a), venue=venue,
                          prefecture=prefecture_of(area, config), area=area, raw_date=raw_date, tags=tags,
                          image=linked_url(url, img.get('data-src') or img.get('src')) if img else None)
        intro = node_text(card.select_one('.body-txt'))
        if intro:
            row['intro_excerpt'] = intro[:800]
        rows.append(row)
    nxt = soup.select_one('a.next.page-numbers[href]')
    follow = linked_url(url, nxt['href'], host_only=True) if nxt else None
    if nxt and (not follow or not re.fullmatch(r'/exhibitions/page/\d+/?', urlsplit(follow).path)):
        raise ValueError('art_navi_exhibition_pagination_changed')
    return rows, follow, unread


def parse_official(payload, calendar, detail_url=None):
    soup = BeautifulSoup(payload, 'html.parser')
    cards = soup.select(calendar['card'])
    if not cards:
        raise ValueError('official_calendar_structure_changed')
    rows, unread, excluded = [], 0, 0
    for card in cards:
        labels = node_text(card.select_one(calendar['label'])) if calendar.get('label') else ''
        if calendar.get('only_label') and not re.search(calendar['only_label'], labels):
            excluded += 1
            continue
        a = card.select_one(calendar['link']) if calendar.get('link') else card
        url = detail_url or (linked_url(calendar['url'], a.get('href'), host_only=True) if a else None)
        paths = calendar['link_path']
        if not url or not urlsplit(url).path.startswith(tuple(paths) if isinstance(paths, list) else paths) or url == calendar['url']:
            unread += 1
            continue
        title = node_text(card.select_one(calendar['title']))
        if not title:
            unread += 1
            continue
        raw, dates = '', None
        if attr := calendar.get('date_attr'):
            values = [iso_day(node.get(attr)) for node in card.select(f'[{attr}]')]
            if len(values) == 2 and all(values):
                dates = tuple(values)
                raw = ' 〜 '.join(values)
        else:
            date_node = card.select_one(calendar['dates'])
            raw = node_text(date_node)
            exact = [iso_day(node.get('datetime')) for node in date_node.select('time[datetime]')] if date_node else []
            if len(exact) == 2 and all(exact):
                dates = tuple(exact)
        image = card.select_one('img')
        record = observation(calendar['id'], url=url, title=title, venue=calendar['venue'],
                             prefecture=calendar['prefecture'], raw_date=raw, dates=dates, official=True,
                             tags=[labels, calendar.get('medium', '')], status_text=labels,
                             image=linked_url(calendar['url'], image.get('data-src') or image.get('src')) if image else None)
        if urlsplit(url).path in calendar.get('shared_index_paths', []):
            record['shared_index_url'] = True
        rows.append(record)
    return rows, unread, excluded


def official_index_links(payload, calendar):
    scope = BeautifulSoup(payload, 'html.parser').select_one(calendar['detail_index'])
    if not scope:
        raise ValueError('official_exhibition_index_changed')
    return list(dict.fromkeys(url for node in scope.select(calendar['detail_link'])
                              if (url := linked_url(calendar['url'], node.get('href'), host_only=True))
                              and urlsplit(url).path.startswith(calendar['link_path'])))


class PublicHost:
    """Limit requests to one verified host and respect unavailable/rate-limited sites."""
    def __init__(self, root):
        self.hostname = urlsplit(root).hostname
        self.origin = f'https://{self.hostname}'
        self.robots = RobotFileParser()
        self.robots.set_url(self.origin + '/robots.txt')
        self.delay = SITE_DELAY_SECONDS
        self.deadline = time.monotonic() + HOST_BUDGET_SECONDS
        self.last = 0
        self.blocked = None
        try:
            self.robots.parse(self._get(self.robots.url).decode(errors='replace').splitlines())
            self.delay = max(self.delay, self.robots.crawl_delay(USER_AGENT) or 0)
            if self.delay > 10:
                self.blocked = 'source_crawl_delay_exceeds_job_budget'
        except HTTPError as error:
            if error.code in (404, 410):
                self.robots.allow_all = True
            else:
                self.blocked = f'robots_http_{error.code}'
        except (OSError, ValueError):
            self.blocked = 'robots_unavailable'

    def _get(self, url):
        with urlopen(Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'text/html,text/plain;q=0.9'}), timeout=12) as response:
            if urlsplit(response.url).hostname != self.hostname:
                raise ValueError('unexpected_source_redirect')
            payload = response.read(MAX_PAGE_BYTES + 1)
            if len(payload) > MAX_PAGE_BYTES:
                raise ValueError('exhibition_list_too_large')
            return payload

    def __call__(self, url):
        if self.blocked:
            raise ValueError(self.blocked)
        if time.monotonic() >= self.deadline:
            self.blocked = 'source_time_budget_reached'
            raise ValueError(self.blocked)
        if urlsplit(url).hostname != self.hostname or not self.robots.can_fetch(USER_AGENT, url):
            raise ValueError('source_crawl_disallowed')
        time.sleep(max(0.0, self.delay - (time.monotonic() - self.last)))
        self.last = time.monotonic()
        try:
            return self._get(url)
        except HTTPError as error:
            if error.code in (403, 429):
                self.blocked = f'http_{error.code}'
            raise


def error_kind(error):
    if isinstance(error, HTTPError):
        return f'http_{error.code}'
    if isinstance(error, ValueError) and re.fullmatch(r'[a-z][a-z0-9_]{1,90}', str(error)):
        return str(error)
    return type(error).__name__


def museum_scan(source, config, get):
    rows, reports = {}, {}
    for code, *_ in config['prefectures']:
        report = {'pages': 0, 'listed': None, 'collected': 0, 'errors': [], 'complete': False}
        local = {}
        expected = 1
        for number in range(1, source['max_pages_per_prefecture'] + 1):
            if number > expected:
                break
            params = {'area': 'pref-' + code}
            if number > 1:
                params['page'] = number
            url = source['url'] + '?' + urlencode(params)
            try:
                chunk, total, unread = parse_museum_page(get(url), url, code, config)
                report['pages'] += 1
                if report['listed'] is None:
                    report['listed'] = total
                elif report['listed'] != total:
                    report['errors'].append('directory_total_changed_mid_scan')
                expected = max(expected, math.ceil(total / 20))
                if unread:
                    report['errors'].append(f'unread_cards_{unread}')
                if number > 1 and chunk and all(r['url'] in local for r in chunk):
                    report['errors'].append('duplicate_pagination')
                    break
                local.update((r['url'], r) for r in chunk)
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
                report['errors'].append(error_kind(error))
                if number == 1:
                    break
        report['collected'] = len(local)
        report['expected_pages'] = expected if report['listed'] is not None else None
        if expected > source['max_pages_per_prefecture']:
            report['errors'].append('page_budget_reached')
        report['complete'] = not report['errors'] and report['listed'] == len(local) and report['pages'] == expected
        if not report['complete'] and not report['errors']:
            report['errors'].append('directory_count_mismatch')
        rows.update(local)
        reports[code] = report
    return list(rows.values()), {'name': source['name'], 'url': source['url'],
                                 'complete': all(report['complete'] for report in reports.values()),
                                 'pages': sum(report['pages'] for report in reports.values()),
                                 'collected': len(rows), 'prefectures': reports}


def tab_scan(source, config, get, known_areas):
    rows, errors, listed, excluded = {}, [], set(), set()
    areas = {identifier: {'name': name, 'prefecture': prefecture_of(name, config) or ('13' if name in config['tab_tokyo_areas'] else None)}
             for identifier, name in config['tab_area_index'].items()}
    areas.update(known_areas)
    visited, pages, total = set(), 0, None
    area_reports = {}
    def collect(url, area_id=None):
        nonlocal total, pages
        try:
            chunk, bound, found, urls, unread = parse_tab_page(get(url), url, config, area_id)
            pages += 1
            rows.update((r['url'], r) for r in chunk)
            areas.update(found)
            listed.update(urls)
            excluded.update(urls - {r['url'] for r in chunk})
            if unread:
                errors.append({'area': area_id, 'issue': f'unread_cards_{unread}'})
            if area_id:
                area_reports[area_id] = {'listed': bound, 'unique': len(urls), 'complete': len(urls) == bound and not unread}
                if len(urls) != bound:
                    errors.append({'area': area_id, 'issue': 'area_count_mismatch'})
            else:
                total = bound
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            errors.append({'area': area_id, 'issue': error_kind(error)})
    collect(source['url'])
    # The published nationwide view has a 1,000-item cap. Its own area search
    # partitions the same public catalogue, with an independently reported total.
    # Recheck known areas after a request failure as well, while retaining gaps.
    need_areas = total is None or len(listed) < total
    while need_areas:
        remaining = sorted(set(areas) - visited)
        if not remaining or len(visited) >= source['max_areas']:
            break
        area_id = remaining[0]
        if not re.fullmatch(r'[A-Za-z0-9_-]{2,80}', area_id):
            break
        visited.add(area_id)
        collect(source['url'] + '/localAreaId/' + area_id, area_id)
    if total is not None and len(listed) != total:
        errors.append({'area': None, 'issue': 'nationwide_count_mismatch'})
    return list(rows.values()), {'name': source['name'], 'url': source['url'], 'complete': total == len(listed) and not errors,
                                 'pages': pages, 'listed': total, 'observed': len(listed), 'collected': len(rows),
                                 'excluded': len(excluded), 'errors': errors, 'areas': area_reports,
                                 'known_areas': areas}


def aej_scan(source, config, get):
    rows, seen, errors = {}, set(), []
    url = source['url']
    while url and len(seen) < source['max_pages']:
        if url in seen:
            errors.append({'url': url, 'issue': 'duplicate_pagination'})
            break
        try:
            chunk, nxt, unread = parse_aepage(get(url), url, config)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            errors.append({'url': url, 'issue': error_kind(error)})
            break
        if chunk and all(item['url'] in rows for item in chunk):
            errors.append({'url': url, 'issue': 'duplicate_pagination_content'})
            break
        if unread:
            errors.append({'url': url, 'issue': f'unread_cards_{unread}'})
        seen.add(url)
        rows.update((r['url'], r) for r in chunk)
        url = nxt
    if url and len(seen) >= source['max_pages']:
        errors.append({'url': url, 'issue': 'page_budget_reached'})
    return list(rows.values()), {'name': source['name'], 'url': source['url'], 'complete': not url and not errors,
                                 'pages': len(seen), 'collected': len(rows), 'errors': errors}


def scan(config, known_areas=None, fetch_factory=PublicHost):
    """Parallelize across hosts only. A failing site leaves the other lanes intact."""
    directories = config['directories']
    def official(calendar):
        count = {'name': calendar['venue'], 'url': calendar['url'], 'prefecture': calendar['prefecture'],
                 'pages': 0, 'collected': 0, 'complete': False, 'errors': []}
        get = fetch_factory(calendar['url'])
        rows = {}
        count['excluded'] = 0
        pages = calendar.get('pages', [calendar['url']])
        if calendar.get('detail_index'):
            try:
                pages = official_index_links(get(calendar['url']), calendar)
                count['pages'] += 1
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
                count['errors'].append(error_kind(error))
                pages = []
        for url in pages:
            try:
                chunk, unread, excluded = parse_official(get(url), calendar, url if calendar.get('detail_index') else None)
                count['pages'] += 1
                count['excluded'] += excluded
                if unread:
                    count['errors'].append(f'unread_cards_{unread}')
                for row in chunk:
                    key = (row['url'], row['title'], row['start']) if row.get('shared_index_url') else row['url']
                    rows[key] = row
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
                count['errors'].append(error_kind(error))
        count.update(collected=len(rows), complete=bool(count['pages']) and not count['errors'])
        return list(rows.values()), count
    with ThreadPoolExecutor(max_workers=6) as pool:
        jobs = {}
        for sid, method in (('internet-museum', museum_scan), ('tokyo-art-beat', tab_scan), ('artexhibition', aej_scan)):
            src = directories[sid]
            def run(source, scanner):
                args = (known_areas or {},) if scanner is tab_scan else ()
                return scanner(source, config, fetch_factory(source['url']), *args)
            jobs[sid] = pool.submit(run, src, method)
        jobs.update({calendar['id']: pool.submit(official, calendar) for calendar in config['official_calendars']})
        results = {sid: job.result() for sid, job in jobs.items()}
    return [row for rows, _ in results.values() for row in rows], {sid: report for sid, (_, report) in results.items()}
