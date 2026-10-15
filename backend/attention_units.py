"""Curated source units with live evidence; presentation belongs to CultureUI."""
import json
import re
from pathlib import Path
from .frontpage import display_title

ROOT = Path(__file__).resolve().parents[1]


def configuration():
    value = json.loads((ROOT / 'config/attention-units.json').read_text())
    identifiers = []
    for unit in value['units']:
        if not re.fullmatch(r'[a-z][a-z0-9-]{1,63}', unit.get('id', '')):
            raise ValueError('invalid_attention_unit_id')
        identifiers.append(unit['id'])
    if len(identifiers) != len(set(identifiers)):
        raise ValueError('duplicate_attention_unit_id')
    return value


def reserved_units(catalog, units=None):
    result = []
    for unit in (units or configuration())['units']:
        if not unit.get('enabled'):
            continue
        identifiers = {m['source_id'] for m in unit['members'] if m['source_id'] in catalog and catalog[m['source_id']].get('enabled', True)}
        if identifiers:
            result.append({'id': unit['id'], 'source_ids': identifiers, 'share': unit['body_share_of_new_slots']})
    return result


def attention_report(snapshot, config, audit=None, headlines=None, units=None):
    if headlines is None:
        from .headlines import load_headlines
        headlines = load_headlines({**snapshot, 'events': [e for e in snapshot.get('events', []) if e.get('title_original')]})
    catalog = {s['id']: s for s in config['sources']}
    states = {s['id']: s for s in snapshot.get('source_status', [])}
    checks = {s['source_id']: s for s in (audit or {}).get('sources', [])}
    rows = [r for r in snapshot.get('content', []) if not r.get('is_demo')]
    report = {'schema_version': 1, 'snapshot_at': snapshot.get('snapshot_at'), 'units': []}
    for unit in (units or configuration())['units']:
        if not unit.get('enabled'):
            continue
        members = []
        for selection in unit['members']:
            identifier = selection['source_id']
            source = catalog.get(identifier, {})
            state = states.get(identifier, {})
            items = sorted([r for r in rows if r['source_id'] == identifier], key=lambda r: r.get('published_at') or '', reverse=True)
            fetched = (state.get('last_run') or {}).get('status')
            status = 'missing_source' if not source else 'disabled' if not source.get('enabled') else fetched or 'not_yet_fetched'
            members.append({**selection, 'name': source.get('name', identifier),
                            'source_enabled': bool(source.get('enabled')), 'homepage_url': source.get('homepage_url'),
                            'rss_url': source.get('feed_url') if source.get('adapter') == 'rss' else None,
                            'source_language': source.get('language'), 'publisher_country': source.get('publisher_country'),
                            'editorial_focus': source.get('editorial_focus'),
                            'collection_status': status, 'last_successful_fetch_at': state.get('last_success_at'),
                            'latest_publication_at': max((r['published_at'] for r in items if r.get('published_at')), default=None),
                            'list_audit_status': checks.get(identifier, {}).get('status', 'not_checked'),
                            'article_count': len(items), 'with_body_count': sum(bool(r.get('article_blocks_json')) for r in items),
                            'ai_translated_count': sum(r.get('editorial_status') in ('reviewed', 'translated') and bool(r.get('editorial_blocks_json') and r.get('editorial_title_zh')) for r in items),
                            'recent_items': [{'id': r['id'], 'title': display_title(r, headlines or {}),
                                              'title_original': r.get('title_original'), 'published_at': r.get('published_at'),
                                              'reader_path': '#reader/' + r['id'], 'original_url': r.get('canonical_url'),
                                              'has_body': bool(r.get('article_blocks_json')), 'article_status': r.get('article_status'),
                                              'editorial_status': r.get('editorial_status'), 'original_language': r.get('language'),
                                              'reported_country': r.get('country'), 'geography_status': r.get('geography_status')}
                                             for r in items[:5]]})
        report['units'].append({**{k: v for k, v in unit.items() if k != 'members'}, 'members': members,
                                'source_count': len(members), 'enabled_source_count': sum(m['source_enabled'] for m in members),
                                'article_count': sum(m['article_count'] for m in members),
                                'with_body_count': sum(m['with_body_count'] for m in members),
                                'ai_translated_count': sum(m['ai_translated_count'] for m in members),
                                'scope_note': '来源精选与编辑关注范围；不代表国家艺术排名、单篇发生地或创作者国籍。'})
    return report
