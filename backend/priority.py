"""Explainable priority: cultural importance, expiry, freshness and backlog."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]


def policy():
    return json.loads((ROOT / 'config/translation-priority.json').read_text())


def reference_time(value=None):
    if value is None: return datetime.now(timezone.utc)
    if isinstance(value, str): value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def classify(row, events=(), reference=None, rules=None):
    rules = rules or policy(); instant = reference_time(reference)
    text = ' '.join(str(row.get(k) or '') for k in ('title_original', 'title_zh', 'editorial_title_zh'))
    reasons = []; importance = 'normal'
    if re.search(rules['major_events_pattern'], text, re.I):
        importance = 'high'; reasons.append('重大影展／奖项相关信号，自动初判')
    if re.search(rules['major_impact_pattern'], text, re.I):
        importance = 'high'; reasons.append('机构／行业重大变化相关信号，自动初判')
    if importance == 'normal' and re.search(rules['new_work_pattern'], text, re.I):
        importance = 'medium'; reasons.append('新作／上映／展览相关资讯')
    exhibit_rules = rules.get('exhibition_preference', {})
    exhibit_events = [event for event in events if event.get('event_type') == 'exhibition']
    exhibition = bool(exhibit_events) or row.get('kind') == 'exhibition' or (
        row.get('channel') in ('art', 'photography') and
        bool(re.search(exhibit_rules.get('exhibition_pattern', r'(?!)'), text, re.I)))
    countries = {event.get('country') for event in exhibit_events if event.get('country') and event.get('country') != 'GLOBAL'}
    if not countries and row.get('country') and row['country'] != 'GLOBAL': countries.add(row['country'])
    preferred = exhibit_rules.get('preferred_country', 'JP')
    exhibit_region = 'japan' if preferred in countries else 'outside_japan' if countries else 'unknown'
    if exhibition and re.search(exhibit_rules.get('major_pattern', r'(?!)'), text, re.I):
        importance = 'high'; reasons.append('重大双年展／奖项展／重要回顾展相关信号，自动初判')
    override = rules.get('manual_overrides', {}).get(row['id'])
    if override and override.get('importance') in ('high', 'medium', 'normal'):
        importance = override['importance']
    age_hours = None
    try:
        published = reference_time(row.get('published_at')) if row.get('published_at') else None
        if published:
            elapsed = (instant - published).total_seconds() / 3600
            if elapsed >= -2: age_hours = max(0, elapsed)
            else: reasons.append('发布时间在未来，未计作新鲜度依据')
    except (ValueError, TypeError): pass
    deadlines = []; active = False
    for event in events:
        if event.get('date_precision') != 'day': continue
        try:
            local = instant.astimezone(ZoneInfo(event['timezone'])).date()
            start = datetime.fromisoformat(event['start_date']).date()
            end = datetime.fromisoformat(event.get('end_date') or event['start_date']).date()
            if event.get('event_type') == 'exhibition' and start <= local <= end: active = True
            if event.get('event_type') == 'call_deadline': targets = [('截止', start, event.get('deadline_at'))]
            elif event.get('event_type') == 'exhibition': targets = [('开幕', start, event.get('start_at')), ('闭展', end, event.get('end_at'))]
            else: targets = [('上映／放映／上线', start, event.get('start_at'))]
            for label, day, exact in targets:
                delta = (day - local).days
                if delta < 0 or exact and reference_time(exact) <= instant: continue
                if delta <= rules['soon_days']:
                    deadlines.append({'days': delta, 'label': label, 'event_id': event['id'],
                                      'date': day.isoformat(), 'timezone': event['timezone']})
        except (KeyError, TypeError, ValueError): continue
    due = min(deadlines, key=lambda item: item['days']) if deadlines else None
    fresh = age_hours is not None and age_hours <= rules['fresh_hours']
    archive = age_hours is not None and age_hours > rules['archive_days'] * 24 and not active and not due
    if due: reasons.append(f"关联活动明确日期：{due['days']}天内{due['label']}（{due['timezone']}）")
    if due and due['days'] <= rules['urgent_days'] or importance == 'high' and fresh: rank = 'P0'
    elif due or importance == 'high' and not archive: rank = 'P1'
    elif archive: rank = 'P3'
    else: rank = 'P2'
    if fresh: reasons.append(f"来源发布时间在{rules['fresh_hours']}小时内")
    if archive: reasons.append('超过近期新闻窗口，仍保留待译')
    deprioritized = exhibition and exhibit_region == 'outside_japan' and importance != 'high'
    if deprioritized:
        rank = exhibit_rules.get('ordinary_outside_priority', 'P3')
        reasons.append('用户偏好：非日本普通展览降为资料优先级；临近开闭展仍记录，不据此提升')
    elif exhibition and exhibit_region == 'outside_japan' and importance == 'high':
        reasons.append('非日本重大展览／重要新闻保留原优先规则')
    elif exhibition and exhibit_region == 'unknown':
        reasons.append('展览地区未确定，未按语言或媒体所在地降级')
    if override:
        if override.get('priority') in rules['labels']:
            rank = override['priority']; deprioritized = False
        if override.get('importance') in ('high','medium','normal'): importance = override['importance']
        reasons.append('人工指定：' + override.get('reason','未补充理由'))
    return {'priority': rank, 'label': rules['labels'][rank], 'importance': importance,
            'time_sensitive': bool(due), 'due': due, 'fresh': fresh, 'archive': archive,
            'reasons': reasons or ['一般资讯；未确认临近活动日期'],
            'source_title': row.get('title_original'), 'model_route': 'fast-direct',
            'exhibition': exhibition, 'exhibition_region': exhibit_region if exhibition else None,
            'exhibition_deprioritized': deprioritized,
            'recommendation_penalty': exhibit_rules.get('homepage_penalty', 12) if deprioritized else 0}


def rank_snapshot(snapshot, reference=None):
    rules = policy(); instant = reference_time(reference)
    events = {r['id']: r for r in snapshot.get('events', [])}; related = {}
    for link in snapshot.get('content_events', []):
        if link['event_id'] in events: related.setdefault(link['content_id'], []).append(events[link['event_id']])
    return {row['id']: classify(row, related.get(row['id'], []), instant, rules)
            for row in snapshot.get('content', []) if not row.get('is_demo')}


def priority_key(row):
    rank = row.get('translation_priority', {})
    try: recency = -reference_time(row['published_at']).timestamp() if row.get('published_at') else 0
    except (ValueError,TypeError): recency = 0
    return (int(rank.get('priority','P2')[1]), {'high':0,'medium':1,'normal':2}.get(rank.get('importance'),2),
            (rank.get('due') or {}).get('days', 999),
            not rank.get('fresh',False), recency, row.get('id',''))
