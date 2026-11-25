"""Persistent Japan exhibition inventory, conservative deduplication and coverage."""
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from zoneinfo import ZoneInfo

from .snapshot_files import encoded, replace_file
from .storage import ROOT

CATALOG = ROOT / 'data/exhibitions-jp.json'
CONFIG = ROOT / 'config/exhibitions-jp.json'
RECENT_DAYS = 14
MAX_BYTES = 24 * 1024 * 1024


def config():
    value = json.loads(CONFIG.read_text(encoding='utf-8'))
    codes = [item[0] for item in value['prefectures']]
    ids = [item['id'] for item in value['official_calendars']]
    if codes != [f'{n:02}' for n in range(1, 48)] or len(ids) != len(set(ids)):
        raise ValueError('invalid_exhibition_source_registry')
    if any(item['prefecture'] not in codes for item in value['official_calendars']):
        raise ValueError('invalid_exhibition_calendar_prefecture')
    return value


def read_catalog(path=CATALOG):
    if not path.exists():
        return {'schema_version': 1, 'generated_at': None, 'items': [], 'coverage': None}
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES:
        raise ValueError('exhibition_inventory_exceeds_file_limit')
    data = json.loads(raw)
    if data.get('schema_version') != 1 or not isinstance(data.get('items'), list):
        raise ValueError('invalid_exhibition_inventory')
    return data


def write_catalog(value, path=CATALOG):
    raw = encoded(value)
    if len(raw) > MAX_BYTES:
        raise ValueError('exhibition_inventory_exceeds_file_limit')
    replace_file(path, raw)


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFKC', value or '').casefold() if c.isalnum())


def title_key(title):
    title = unicodedata.normalize('NFKC', title)
    title = re.sub(r'^(?:特別展|企画展|展覧会|特別企画展|特別陳列)[\s:・「『(\[]*', '', title)
    return normalized(title)


def venue_key(row, aliases):
    return normalized(aliases.get(row['venue'], row['venue']))


def evidence_key(row):
    url = row['url'].rstrip('/')
    # A collection hub may keep the same URL even when the contents rotate.
    # Distinguish listings on such hubs so a private review keeps its edition.
    if row.get('shared_index_url'):
        url += '|' + title_key(row['title']) + '|' + (row['start'] or '')
    return row['source'], url


def schedule_agrees(a, b):
    if not a['start'] or not b['start'] or len(a['start']) != 10 or len(b['start']) != 10:
        return False
    # Same tour title in the same venue can recur. If both ends differ and the
    # ranges do not overlap, keep separate editions and separate visit logs.
    if a['start'] == b['start']:
        return True
    if a['end'] and a['end'] == b['end']:
        return True
    if not a['end'] or not b['end']:
        return False
    later_start, earlier_end = max(a['start'], b['start']), min(a['end'], b['end'])
    day = lambda x: datetime.fromisoformat(x).date()
    return later_start <= earlier_end and abs((day(a['start']) - day(b['start'])).days) <= 7 and abs((day(a['end']) - day(b['end'])).days) <= 7


def importance_flags(evidence):
    text = ' '.join(row['title'] + ' ' + ' '.join(row['labels']) for row in evidence)
    tags = {tag for row in evidence for tag in row['types']}
    signals = []
    if 'festival' in tags:
        signals.append('festival')
    if re.search(r'回顧展|大回顧|retrospective', text, re.I):
        signals.append('retrospective')
    if re.search(r'日本初の本格|過去最大|大規模|大回顧|(?:生誕|没後)\s*[1-9]\d{1,2}\s*周年', text):
        signals.append('milestone')
    if re.search(r'特別展|特別企画展|特別陳列|企画展', text):
        signals.append('special')
    if re.search(r'常設展|常設展示|permanent (?:collection|exhibition)', text, re.I):
        signals.append('permanent')
    return signals


def representative(identifier, evidence, today):
    # Preserve all links. Pick current venue evidence before directories, and
    # don't allow a stale/cached version of a venue calendar to set the schedule.
    recent_cutoff = (today - timedelta(days=RECENT_DAYS)).isoformat()
    current = [row for row in evidence if row['last_seen'][:10] >= recent_cutoff] or evidence
    # One latest observation per source in the conflict check, while keeping a
    # changed URL as an alias in the catalogue. Never suppress independent dates.
    current.sort(key=lambda row: (row['last_seen'], row['official'], bool(row['start'] and row['end'])), reverse=True)
    by_source = {}
    for row in current:
        by_source.setdefault(row['source'], row)
    checked = list(by_source.values())
    checked.sort(key=lambda row: (row['official'], bool(row['start'] and row['end']), bool(row['start']),
                                  bool(row['prefecture']), row['last_seen']), reverse=True)
    primary = checked[0]
    placed = next((row for row in checked if row['prefecture'] and row['venue']), primary)
    # Do not borrow a directory's date when the venue says it changed or is TBA.
    schedule = primary
    dates = {(row['start'], row['end']) for row in checked if row['start'] and row['end']}
    statuses = {row['status'] for row in checked}
    status = primary['status']
    if status == 'scheduled' and not primary['official'] and statuses & {'cancelled', 'postponed'}:
        status = 'needs_confirmation'
    start, end = schedule['start'], schedule['end']
    types = sorted({tag for row in checked for tag in row['types']} - {'other'}) or ['other']
    image = next((row for row in checked if row['image']), None)
    return {
        'id': identifier, 'country': 'JP', 'timezone': 'Asia/Tokyo', 'event_type': 'exhibition',
        'title_original': primary['title'], 'venue': placed['venue'], 'prefecture': placed['prefecture'],
        'area': placed['area'], 'start_date': start, 'end_date': end,
        'date_precision': ('day' if len(start) == 10 else 'month') if start else 'unknown',
        'date_text_original': schedule['date_text'], 'date_conflict': len(dates) > 1,
        'status': status, 'types': types, 'flags': importance_flags(checked),
        'official': primary['official'], 'image_url': image['image'] if image else None,
        'image_source': image['source'] if image else None,
        'evidence_url': primary['url'], 'source_id': primary['source'],
        'first_seen': min(row['first_seen'] for row in evidence), 'last_seen': max(row['last_seen'] for row in evidence),
        'evidence': sorted(evidence, key=evidence_key),
    }


def merge_observations(previous, observations, settings, instant):
    aliases = settings['venue_aliases']
    groups = {}
    source_index = {}
    titles, schedules = defaultdict(set), defaultdict(set)
    today = instant.astimezone(ZoneInfo('Asia/Tokyo')).date()
    stamp = instant.isoformat()

    def place(row):
        return row['prefecture'], venue_key(row, aliases)

    def index(identifier, row):
        source_index[evidence_key(row)] = identifier
        pref, venue = place(row)
        if pref and venue:
            titles[pref, venue, title_key(row['title'])].add(identifier)
            if row['start'] and row['end']:
                schedules[pref, venue, row['start'], row['end']].add(identifier)

    for item in previous:
        if item['id'] in groups:
            raise ValueError('duplicate_exhibition_inventory_id')
        groups[item['id']] = {evidence_key(row): row for row in item['evidence']}
        for row in item['evidence']:
            index(item['id'], row)
    for row in sorted(observations, key=lambda x: (not x['official'], evidence_key(x))):
        key = evidence_key(row)
        identifier = source_index.get(key)
        pref, venue = place(row)
        name = title_key(row['title'])
        if identifier is None and pref and venue and name:
            exact = {aid for aid in titles[pref, venue, name]
                     if any(place(old) == (pref, venue) and title_key(old['title']) == name and schedule_agrees(old, row)
                            for old in groups[aid].values())}
            if len(exact) == 1:
                identifier = exact.pop()
            elif not exact and len(name) >= 10 and row['start'] and row['end']:
                def fuzzy(old):
                    other = title_key(old['title'])
                    return (len(other) >= 10 and place(old) == (pref, venue)
                            and old['start'] == row['start'] and old['end'] == row['end']
                            and re.findall(r'\d+', name) == re.findall(r'\d+', other)
                            and SequenceMatcher(None, name, other, autojunk=False).ratio() >= .92)
                matches = {aid for aid in schedules[pref, venue, row['start'], row['end']]
                           if any(fuzzy(old) for old in groups[aid].values())}
                if len(matches) == 1:
                    identifier = matches.pop()
        if identifier is None:
            identifier = 'jp-ex-' + hashlib.sha256('\n'.join(key).encode()).hexdigest()[:20]
            groups[identifier] = {}
        previous_row = groups[identifier].get(key)
        current = {**row, 'first_seen': previous_row['first_seen'] if previous_row else stamp, 'last_seen': stamp}
        groups[identifier][key] = current
        index(identifier, current)
    return [representative(aid, list(group.values()), today) for aid, group in sorted(groups.items())]


def build_catalog(previous, observations, reports, settings, instant=None):
    instant = instant or datetime.now(timezone.utc)
    today = instant.astimezone(ZoneInfo('Asia/Tokyo')).date().isoformat()
    items = merge_observations(previous['items'], observations, settings, instant)
    active = [item for item in items if item['date_precision'] == 'day'
              and (item['end_date'] or item['start_date']) >= today
              and item['status'] not in {'cancelled', 'postponed', 'needs_confirmation'}]
    with_region = defaultdict(list)
    for item in items:
        with_region[item['prefecture']].append(item)
    actives = Counter(item['prefecture'] for item in active)
    directory = reports['internet-museum']['prefectures']
    official_sources = [value for value in reports.values() if value.get('prefecture')]
    areas = []
    for code, original, label, region in settings['prefectures']:
        rows = with_region[code]
        calendars = [value for value in official_sources if value['prefecture'] == code]
        areas.append({'code': code, 'name': label, 'original': original, 'region': region,
                      'directory': directory[code], 'total': len(rows), 'active_or_upcoming': actives[code],
                      'venues': len({venue_key(row, settings['venue_aliases']) for row in rows if row['venue']}),
                      'official_calendars': len(calendars), 'official_calendars_checked': sum(r['complete'] for r in calendars)})
    sources = {key: {k: v for k, v in report.items() if k != 'known_areas'} for key, report in reports.items()}
    coverage = {'scope': 'public_listings_and_configured_calendars', 'as_of': today,
                'prefectures': areas, 'sources': sources, 'counts': {
                    'catalogue': len(items), 'active_or_upcoming': len(active),
                    'source_observations_this_run': len(observations),
                    'prefectures_checked': sum(bool(area['directory']['pages']) for area in areas),
                    'prefectures_directory_complete': sum(area['directory']['complete'] for area in areas),
                    'prefectures_with_active_or_upcoming': sum(bool(n) for pref, n in actives.items() if pref),
                    'unresolved_prefecture': len(with_region[None]),
                    'official_calendars_checked': sum(source['complete'] for source in official_sources),
                    'official_calendars_total': len(official_sources),
                    'type_actives': dict(Counter(kind for item in active for kind in item['types'])),
                }}
    return {'schema_version': 1, 'generated_at': instant.isoformat(),
            'items': items, 'coverage': coverage, 'tab_known_areas': reports['tokyo-art-beat']['known_areas']}
