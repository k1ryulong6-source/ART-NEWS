"""Evidence of inventory, translation progress and bounded source checks.

An RSS reconciliation describes that one observed feed, never worldwide coverage.
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import re
import xml.etree.ElementTree as ET
from urllib.error import HTTPError
from .storage import now


def translation_progress(snapshot):
    rows = [r for r in snapshot.get('content', []) if not r.get('is_demo')]
    reviewed = [r for r in rows if r.get('editorial_status') == 'reviewed'
                and r.get('editorial_blocks_json') and r.get('editorial_title_zh')]
    direct = [r for r in rows if r.get('editorial_status') == 'translated' and r.get('editorial_blocks_json') and r.get('editorial_title_zh')]
    done = reviewed + direct
    pending = [r for r in rows if r.get('language') != 'zh' and r.get('article_blocks_json') and r not in done]
    return {'total': len(rows), 'foreign_total': sum(r.get('language') != 'zh' for r in rows),
            'reviewed': len(reviewed), 'reviewed_partial': sum(r.get('article_status') == 'partial' for r in reviewed),
            'direct_translated': len(direct), 'completed': len(done),
            'completed_partial': sum(r.get('article_status') == 'partial' for r in done),
            'native_chinese': sum(r.get('language') == 'zh' and bool(r.get('article_blocks_json')) for r in rows),
            'pending': len(pending), 'without_body': sum(not r.get('article_blocks_json') for r in rows),
            'pending_characters': sum(len(r.get('article_text') or '') for r in pending)}


def reconcile_rss(snapshot, source, payload):
    from .ingestion import rss_records, GEAR, GEAR_MULTILINGUAL
    records, _, _ = rss_records(source, payload)
    stored = {r['id'] for r in snapshot.get('content', []) if r['source_id'] == source['id']}
    accepted = {r['id']: r for r in records}
    missing = [{'id': r['id'], 'title_original': r['title_original'], 'url': r['canonical_url'],
                'published_at': r.get('published_at')} for key, r in accepted.items() if key not in stored]
    observed = ET.fromstring(payload.lstrip(b'\xef\xbb\xbf \t\r\n')).findall('.//item')
    excluded = []
    for item in observed:
        title, url = item.findtext('title'), item.findtext('link')
        reason = 'invalid_entry' if not title or not url else None
        labels = title or ''
        labels += ' ' + ' '.join(node.text or '' for node in item.findall('category'))
        if GEAR.search(labels) or GEAR_MULTILINGUAL.search(labels): reason = 'equipment_review'
        elif source.get('exclude_title_regex') and re.search(source['exclude_title_regex'], title or '', re.I): reason = 'source_config_filter'
        if reason: excluded.append({'title_original': title, 'reason': reason})
    timestamps = sorted(r['published_at'] for r in records if r.get('published_at'))
    return {'scope': 'observed_rss_only', 'status': 'checked', 'observed': len(observed),
            'eligible': len(accepted), 'in_inventory': len(accepted) - len(missing),
            'eligible_ids': list(accepted),
            'missing': missing, 'excluded': excluded,
            'oldest_publication': timestamps[0] if timestamps else None,
            'newest_publication': timestamps[-1] if timestamps else None}


def audit_sources(snapshot, config, fetcher, previous=None):
    previous_checks = {s['source_id']: s for s in (previous or {}).get('sources', [])}
    def check(source):
        result = {'source_id': source['id'], 'name': source['name'], 'checked_at': now(),
                  'reference_url': source.get('feed_url') or source['homepage_url']}
        if source.get('adapter') != 'rss':
            result.update(status='scope_not_independently_checked', scope='configured_calendar_pages',
                          observed=None, eligible=None, in_inventory=None, missing=None,
                          note='只读取配置页面；全站、整个影展和全年展览完整性未核验。')
            return result
        try:
            result.update(reconcile_rss(snapshot, source, fetcher(source['feed_url'])))
            old_ids = set(previous_checks.get(source['id'], {}).get('eligible_ids') or [])
            new_ids = set(result['eligible_ids'])
            result['previous_check_at'] = previous_checks.get(source['id'], {}).get('checked_at')
            result['overlap_with_previous'] = len(old_ids & new_ids) if old_ids else None
            result['continuity'] = 'possible_rollover_gap' if old_ids and new_ids and not old_ids & new_ids else 'overlap_observed' if old_ids else 'first_observation'
        except Exception as exc:
            result.update(status='failed', scope='observed_rss_only', observed=None, eligible=None,
                          in_inventory=None, missing=None,
                          error=type(exc).__name__ + (f' HTTP {exc.code}' if isinstance(exc, HTTPError) else ''))
        return result
    enabled = [s for s in config['sources'] if s.get('enabled')]
    with ThreadPoolExecutor(max_workers=4) as pool:
        return {'checked_at': now(), 'scope': 'bounded_source_list_comparison',
                'sources': list(pool.map(check, enabled)),
                'limitations': ['RSS只含当前列表，不代表全站历史文章。',
                                '读取失败与未独立检查的来源不能视为没有遗漏。',
                                '该核对不能证明世界重要资讯全部收齐。']}


def coverage_report(snapshot, config, audit=None, benchmarks=None):
    rows = [r for r in snapshot.get('content', []) if not r.get('is_demo')]
    statuses = {s['id']: s for s in snapshot.get('source_status', [])}
    checks = {s['source_id']: s for s in (audit or {}).get('sources', [])}
    inventory = {r['id'] for r in rows}
    checks = {identifier: {**check, 'missing_at_audit_count': len(check.get('missing') or []),
                          'missing': [r for r in check.get('missing') or [] if r['id'] not in inventory],
                          'in_inventory': sum(identifier in inventory for identifier in check['eligible_ids'])}
              if check.get('eligible_ids') else check for identifier, check in checks.items()}
    sources = []
    for source in config['sources']:
        if not source.get('enabled'): continue
        items = [r for r in rows if r['source_id'] == source['id']]
        state = statuses.get(source['id'], {})
        sources.append({'id': source['id'], 'name': source['name'], 'adapter': source.get('adapter'),
                        'language': source.get('language'), 'homepage_url': source['homepage_url'],
                        'progress': translation_progress({'content': items}),
                        'last_success_at': state.get('last_success_at'), 'last_run': state.get('last_run'),
                        'list_audit': checks.get(source['id'])})
    probes = []
    for item in (benchmarks or {}).get('items', []):
        matching = [r['id'] for r in rows if any(term.casefold() in (r.get('title_original') or '').casefold() for term in item['terms'])]
        events = [r['id'] for r in snapshot.get('events', []) if any(term.casefold() in (r.get('title_original') or '').casefold() for term in item['terms'])]
        probes.append({**item, 'related_content_ids': matching, 'related_event_ids': events,
                       'inventory_status': 'related_report_only' if matching and not events else 'related_record_found' if matching or events else 'not_found_in_inventory'})
    return {'snapshot_at': snapshot.get('snapshot_at'), 'progress': translation_progress(snapshot),
            'channels': dict(Counter(r['channel'] for r in rows)),
            'languages': dict(Counter(r.get('language') for r in rows)),
            'event_regions': dict(Counter(r.get('country') for r in snapshot.get('events', []))),
            'sources': sources, 'source_audit_at': (audit or {}).get('checked_at'),
            'benchmarks': probes, 'global_completeness': 'unknown',
            'known_gaps': ['来源是有限名单，未覆盖全球全部媒体、片方、美术馆和摄影机构。',
                           '近期RSS会滚动，即使设置每2小时检查仍可能错过高频来源的条目；没有全站历史回补。',
                           '官方活动只覆盖配置页面，日本以外上映、拉美／中东／东南亚展览仍明显不足。',
                           '没有持续独立编辑审核，跨来源重点清单仅是抽查样本。']}
