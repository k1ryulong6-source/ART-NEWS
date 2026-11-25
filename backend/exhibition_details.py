"""Public exhibition introductions with provenance and a bounded backfill."""
import json
import re
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote, urlsplit
from zoneinfo import ZoneInfo

from .snapshot_files import encoded, replace_file
from .storage import ROOT

DETAILS = ROOT / 'data/exhibition-details.json'
MAX_INTRO = 24000
SOURCE_ORDER = {'artexhibition': 0, 'tokyo-art-beat': 1, 'internet-museum': 2}
INTRO_SCOPES = {
    'artexhibition': 'main article.main-content',
    'internet-museum': '.l-mainOverview .c-body_text',
    'tokyo-photo-museum': '.exhibition_box5',
    'national-art-center': '.outline',
    'hokkaido-modern': '.article-wrap .element_grp_text',
    'aomori-museum': '.js-articleBody .moduleBody',
    'yokohama-museum': '.overviewBox',
    'kanazawa-21': '.section__body .content > article',
    'kyoto-kyocera': 'main .cont_desc',
    'fukuoka-art-museum': '#ex_single_info',
    'okinawa-museum': '.about_exhibition',
    'osaka-nakanoshima': '.product-contents',
    'hiroshima-moca': 'main .textblock, .overview .textblock',
    'tokushima-modern': '.text-beginning > div',
}
NOISE = 'script,style,nav,aside,form,button,table,.main-content-header,.main-content-footer,.exhibition-detail,.official,.related,.share'


def read_details(path=DETAILS):
    if not path.exists():
        return {'schema_version': 1, 'generated_at': None, 'entries': {}}
    value = json.loads(path.read_text(encoding='utf-8'))
    if value.get('schema_version') != 1 or not isinstance(value.get('entries'), dict):
        raise ValueError('invalid_exhibition_details')
    return value


def write_details(value, path=DETAILS):
    raw = encoded(value)
    if len(raw) >= 32 * 1024 * 1024:
        raise ValueError('exhibition_details_exceeds_file_limit')
    replace_file(path, raw)


def source_order(row):
    return not row['official'], SOURCE_ORDER.get(row['source'], 9), row['url']


def pick_intro(item, data):
    """Use an introduction only while its actual source belongs to this event."""
    stored = data.get(item['id'], {})
    evidence = item.get('evidence') or []
    if stored.get('paragraphs') and any(stored['url'] == row['url'] for row in evidence):
        return stored
    if excerpt := next((row for row in sorted(evidence, key=source_order) if row.get('intro_excerpt')), None):
        return {'status': 'excerpt', 'paragraphs': [excerpt['intro_excerpt']], 'url': excerpt['url'], 'source': excerpt['source']}
    return {'status': 'missing'}


def _paragraphs(value):
    parts, seen, size = [], set(), 0
    for line in value:
        line = ' '.join(line.split())
        if not line or line in seen:
            continue
        if size + len(line) > MAX_INTRO:
            return parts, 'excerpt'
        seen.add(line)
        parts.append(line)
        size += len(line)
    return parts, 'introduction'


def _scope_lines(scope):
    from bs4 import NavigableString, Tag
    for tag in scope.select(NOISE):
        if tag.parent:
            tag.decompose()
    # Some public descriptions are divs with line breaks instead of paragraphs.
    if not scope.select_one('p, blockquote'):
        for br in scope.find_all('br'):
            br.replace_with('\n')
        return scope.get_text().splitlines()
    # Keep text on either side of nested paragraphs in malformed publisher markup.
    lines, parts = [], []
    current = None
    for node in scope.descendants:
        if isinstance(node, Tag) and node.name == 'br':
            if parts:
                lines.append(' '.join(parts))
                parts = []
        elif type(node) is NavigableString and node.strip():
            block = node.find_parent(['p', 'blockquote'])
            if block is None:
                continue
            if block is not current and parts:
                lines.append(' '.join(parts))
                parts = []
            current = block
            parts.append(node.strip())
    if parts:
        lines.append(' '.join(parts))
    return lines


def parse_detail(payload, evidence):
    from bs4 import BeautifulSoup
    from .exhibition_sources import clean, linked_url, node_text
    from .japanese_art import next_fallback
    source, url = evidence['source'], evidence['url']
    soup = BeautifulSoup(payload, 'html.parser')
    for script in soup.select('script[type="application/ld+json"]'):
        if re.search(r'"isAccessibleForFree"\s*:\s*(?:false|"false")', script.get_text(), re.I):
            raise ValueError('exhibition_detail_not_public')
    if source == 'tokyo-art-beat':
        query, result = next_fallback(soup, 'EventDetail')
        slug = unquote(urlsplit(url).path.partition('/events/-/')[2]).rstrip('/')
        row = next((row for row in result.get('data', []) if row.get('slug') == slug), None)
        if not row or query.get('slug') != slug or clean(row.get('eventName')) != evidence['title']:
            raise ValueError('detail_identity_changed')
        intro = row.get('description')
        paragraphs, status = _paragraphs(intro.splitlines() if isinstance(intro, str) else [])
        poster = ((row.get('imageposter') or {}).get('fields') or {}).get('file') or {}
        image = linked_url(url, poster.get('url'))
        official = linked_url(url, row.get('showsWebpage'))
    else:
        scopes = soup.select(INTRO_SCOPES[source])
        if not scopes:
            raise ValueError('exhibition_intro_structure_changed')
        if source in ('artexhibition', 'internet-museum'):
            heading = soup.select_one('main .main-content-title' if source == 'artexhibition' else '.l-mainOverview h1')
            expected = clean(evidence['title'])
            if heading and node_text(heading) != expected:
                raise ValueError('detail_identity_changed')
        meta = soup.select_one('meta[property="og:image"]')
        hero = soup.select_one('figure.eyecatch img' if source == 'artexhibition' else
                               '.main_img img' if source == 'tokyo-photo-museum' else '.about_exhibition img' if source == 'okinawa-museum' else 'main .main_visual img')
        image = linked_url(url, hero.get('data-src') or hero.get('src')) if hero else evidence.get('image')
        if not image and meta and source in ('hiroshima-moca', 'osaka-nakanoshima', 'aomori-museum'):
            image = linked_url(url, meta.get('content'))
        official_link = soup.select_one('main article .official a[href]') if source == 'artexhibition' else None
        official = linked_url(url, official_link['href']) if official_link else None
        paragraphs, status = _paragraphs(line for scope in scopes for line in _scope_lines(scope))
    if not paragraphs or sum(len(line) for line in paragraphs) < 35:
        raise ValueError('exhibition_intro_unavailable')
    return {'status': status, 'paragraphs': paragraphs, 'image': image, 'official_url': official,
            'url': url, 'source': source, 'language': 'ja'}


def _candidate_plan(items, entries, today, instant, limit, per_host):
    def order(item):
        start, end = item.get('start_date'), item.get('end_date')
        approaching = bool(end and today <= end <= (datetime.fromisoformat(today) + timedelta(days=7)).date().isoformat())
        active = bool(end and end >= today)
        significant = bool(set(item.get('flags', [])) & {'festival', 'retrospective', 'milestone', 'special'})
        return not active, not (approaching or significant), not item.get('official'), start or '9999', item['id']
    jobs = defaultdict(deque)
    used = defaultdict(int)
    for item in sorted(items, key=order):
        current = entries.get(item['id'], {})
        if current.get('status') == 'introduction' and pick_intro(item, entries).get('status') == 'introduction':
            continue
        attempted = current.get('failed', {})
        for source in sorted(item.get('evidence', []), key=source_order):
            if source['source'] not in INTRO_SCOPES and source['source'] != 'tokyo-art-beat':
                continue
            host = urlsplit(source['url']).hostname
            if not host or (source['source'] == 'fukuoka-art-museum' and source.get('shared_index_url')):
                continue
            failed_at = attempted.get(source['url'])
            if failed_at and datetime.fromisoformat(failed_at) + timedelta(days=5) > instant:
                continue
            if used[host] < per_host:
                jobs[host].append((item['id'], source))
                used[host] += 1
                break
    selected = defaultdict(list)
    while jobs and limit:
        for host in list(jobs):
            if not limit:
                break
            selected[host].append(jobs[host].popleft())
            limit -= 1
            if not jobs[host]:
                del jobs[host]
    return selected


def refresh_details(catalog, previous, *, limit=180, per_host=70, fetch_factory=None, instant=None):
    from .exhibition_sources import PublicHost, error_kind
    fetch_factory = fetch_factory or PublicHost
    instant = instant or datetime.now(timezone.utc)
    stamp = instant.isoformat()
    today = instant.astimezone(ZoneInfo('Asia/Tokyo')).date().isoformat()
    entries = dict(previous['entries'])
    jobs = _candidate_plan(catalog['items'], entries, today, instant, limit, per_host)
    errors = defaultdict(int)

    def run(tasks):
        get = fetch_factory(tasks[0][1]['url'])
        results = []
        for identifier, evidence in tasks:
            try:
                results.append((identifier, evidence['url'], parse_detail(get(evidence['url']), evidence), None))
            except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
                results.append((identifier, evidence['url'], None, error_kind(error)))
        return results

    saved = 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        for results in pool.map(run, jobs.values()):
            for identifier, url, detail, error in results:
                old = entries.get(identifier, {})
                failed = dict(old.get('failed', {}))
                if detail:
                    failed.pop(url, None)
                    entries[identifier] = {**detail, 'checked_at': stamp, 'failed': failed}
                    saved += 1
                else:
                    errors[error] += 1
                    failed[url] = stamp
                    entries[identifier] = {**old, 'failed': failed}
    statuses = defaultdict(int)
    for item in catalog['items']:
        statuses[pick_intro(item, entries)['status']] += 1
    report = {'planned': sum(map(len, jobs.values())), 'saved': saved, 'errors': dict(errors), 'inventory': dict(statuses)}
    return {'schema_version': 1, 'generated_at': stamp, 'entries': entries, 'report': report}
