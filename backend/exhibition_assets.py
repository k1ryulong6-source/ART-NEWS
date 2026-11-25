"""Small, independent exhibition browsing files and individually loaded readers."""
import json
import re
from collections import Counter
from hashlib import sha256

from .exhibition_details import pick_intro

ID = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}')
LIST_FIELDS = ('id', 'title_original', 'title_zh', 'country', 'city', 'venue', 'prefecture', 'area',
               'timezone', 'start_date', 'end_date', 'date_precision', 'date_conflict', 'status',
               'types', 'flags', 'official', 'image_url', 'image_source', 'first_seen', 'last_seen', 'is_demo')


def public_items(catalogue, events=(), legacy_images=None):
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
    return items


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
    identifiers = {entry['source'] for entry in row.get('evidence') or []} | {row.get('image_source'), description.get('source')}
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
    items = public_items(catalogue, snapshot.get('events', []), images)
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
    return sha256(index.read_bytes() + json.dumps(revision).encode()).hexdigest()[:12]
