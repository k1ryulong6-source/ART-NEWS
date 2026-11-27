"""Small, independent exhibition browsing files and individually loaded readers."""
import json
import re
from collections import Counter
from hashlib import sha256

from .exhibition_details import pick_intro
from .exhibition_priority import add_recommendations
from .exhibitions import config, venue_key

ID = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}')
LIST_FIELDS = ('id', 'title_original', 'title_zh', 'country', 'city', 'venue', 'prefecture', 'area',
               'timezone', 'start_date', 'end_date', 'date_precision', 'date_conflict', 'status',
               'types', 'flags', 'official', 'image_url', 'image_source', 'first_seen', 'last_seen', 'is_demo',
               'venue_id', 'venue_name', 'evidence_url', 'source_id', 'evidence_status',
               'recommendation', 'duplicate_group', 'related_event')


def venue_reference(row, aliases):
    name = row.get('venue')
    country = row.get('country')
    place = row.get('prefecture') if country == 'JP' else row.get('city')
    if not name or not country or country == 'GLOBAL' or not place:
        return {}
    key = venue_key(row, aliases)
    if key in ('', '未定', '会場未定', '未発表', '複数会場', '各会場', 'オンライン', 'online', 'tba'):
        return {}
    identifier = sha256(f'{country}\0{place}\0{key}'.encode()).hexdigest()[:24]
    return {'venue_id': 'venue-' + identifier, 'venue_name': aliases.get(name, name)}


def public_items(catalogue, events=(), legacy_images=None, *, details=None):
    items = {row['id']: row for row in catalogue['items'] if ID.fullmatch(row['id'])}
    known_urls = {entry['url'].rstrip('/') for row in items.values() for entry in row.get('evidence', [])}
    for event in events:
        if (event.get('event_type') != 'exhibition' or event.get('is_demo') or event['id'] in items or not ID.fullmatch(event['id'])
                or str(event.get('evidence_url') or '').rstrip('/') in known_urls):
            continue
        row = {**event, 'official': event.get('evidence_status') == 'official_confirmed', 'status': 'scheduled',
               'types': ['photography' if event.get('channel') == 'photography' else 'other']}
        if legacy_images and (image := legacy_images.get(row['id'])):
            row['image_url'], row['image_source'] = image
        items[row['id']] = row
    aliases = config()['venue_aliases']
    items = {key: {**row, **venue_reference(row, aliases)} for key, row in items.items()}
    add_recommendations(items, introductions=details['entries'] if details else None)
    return items


def exhibition_entry(template):
    """Open earlier /exhibitions/ links in the standard publication shell."""
    routing = '''<base href="../">
  <script>
    var exhibitionId = new URLSearchParams(location.search).get('id') || '';
    var exhibitionRoute = /^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$/.test(exhibitionId) ? '#exhibition/' + exhibitionId : '#exhibitions';
    history.replaceState(null, '', document.baseURI + exhibitionRoute);
  </script>'''
    return (template.replace('<head>', '<head>\n  ' + routing, 1)
            .replace('<title>幕间休息</title>', '<title>展览 · 幕间休息</title>', 1)
            .replace('正在载入头版…', '正在载入展览…', 1))


def compact_list(catalogue, items):
    rows = []
    for item in items.values():
        row = {key: item[key] for key in LIST_FIELDS if item.get(key) is not None}
        evidence = item.get('evidence') or []
        row['source_count'] = len({e['source'] for e in evidence})
        if row.get('date_conflict'):
            row['evidence'] = [{key: e[key] for key in ('status', 'start', 'end', 'last_seen')} for e in evidence]
        rows.append(row)
    return {'schema_version': 1, 'generated_at': catalogue['generated_at'], 'items': rows, 'coverage': catalogue['coverage'],
            'includes_legacy_events': True}


def detail_view(row, details, coverage):
    description = pick_intro(row, details['entries'])
    description = {key: value for key, value in description.items() if key != 'failed'}
    sources = (coverage or {}).get('sources', {})
    evidence = (row.get('evidence') or []) + (row.get('related_sources') or [])
    identifiers = {entry.get('source') for entry in evidence} | {row.get('image_source'), description.get('source')}
    names = {sid: sources[sid]['name'] for sid in identifiers if sid in sources}
    prefecture = next((area['name'] for area in (coverage or {}).get('prefectures', []) if area['code'] == row.get('prefecture')), None)
    return {'schema_version': 1, 'item': {**row, 'prefecture_name': prefecture}, 'description': description, 'sources': names}


def fill_detail_images(items, details):
    for key, row in items.items():
        if not row.get('image_url'):
            detail = pick_intro(row, details['entries'])
            if detail.get('image'):
                items[key] = {**row, 'image_url': detail['image'], 'image_source': detail['source']}


def description_counts(catalogue, details):
    counts = Counter(pick_intro(row, details['entries'])['status'] for row in catalogue['items'])
    return {status: counts[status] for status in ('introduction', 'excerpt', 'missing')}


def write_exhibition_files(directory, catalogue, details, snapshot):
    directory.mkdir(exist_ok=True)
    content = {r['id']: r for r in snapshot.get('content', []) if r.get('image_url')}
    images = {link['event_id']: (content[link['content_id']]['image_url'], content[link['content_id']].get('source_id'))
              for link in snapshot.get('content_events', []) if link['content_id'] in content}
    items = public_items(catalogue, snapshot.get('events', []), images, details=details)
    fill_detail_images(items, details)
    index = directory / 'catalogue.json'
    index.write_text(json.dumps(compact_list(catalogue, items), ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    readers = directory / 'items'
    readers.mkdir(exist_ok=True)
    for aid, row in items.items():
        public = detail_view(row, details, catalogue['coverage'])
        (readers / (aid + '.json')).write_text(json.dumps(public, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    for path in readers.glob('*.json'):
        if path.stem not in items:
            path.unlink()
    revision = {'catalogue': catalogue['generated_at'], 'details': details['generated_at'], 'snapshot': snapshot.get('snapshot_at')}
    return sha256(index.read_bytes() + json.dumps(revision).encode()).hexdigest()[:12], list(items.values())
