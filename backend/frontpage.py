"""Mirror CultureCore.frontpageRows for the public edition, without changing layout."""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]


def display_title(row, headlines):
    if row.get('editorial_status') in ('reviewed', 'translated') and row.get('editorial_blocks_json') and row.get('editorial_title_zh'):
        return row['editorial_title_zh']
    translated = headlines.get(row['id'], {}).get('title_zh') or row.get('title_zh')
    if not translated and str(row.get('article_translation_provider') or '').startswith('offline-m2m100:'):
        from .autonomous_translation import machine_ready
        if machine_ready(row):
            translated = row.get('translated_title_zh')
    return translated or row.get('title_original') or '标题未取得'


def frontpage_rows(snapshot, priorities, instant, preferences=None, headlines=None):
    preferences = preferences or json.loads((ROOT / 'config/preferences.json').read_text())
    if headlines is None:
        from .headlines import load_headlines
        headlines = load_headlines({**snapshot, 'events': [e for e in snapshot.get('events', []) if e.get('title_original')]})
    cfg = preferences.get('frontpage') or {}
    lead_hours, fallback_hours = cfg.get('lead_hours', 72), cfg.get('fallback_hours', 168)
    decay = cfg.get('freshness_decay_hours', 2)
    importance = cfg.get('importance_boost', {'high': 24, 'medium': 8, 'normal': 0})
    urgency = cfg.get('priority_boost', {'P0': 12, 'P1': 6, 'P2': 0, 'P3': -12})
    known, undated = [], []
    for original in snapshot.get('content', []):
        if original.get('is_demo') or original.get('evidence_status') == 'unverified':
            continue
        row = dict(original)
        rank = priorities.get(row['id'], {})
        age = None
        try:
            published = datetime.fromisoformat((row.get('published_at') or '').replace('Z', '+00:00'))
            published = published.replace(tzinfo=ZoneInfo('UTC')) if published.tzinfo is None else published
            elapsed = (instant - published).total_seconds() / 3600
            if elapsed < -2 or elapsed > fallback_hours:
                continue
            age = max(0, elapsed)
        except (ValueError, TypeError):
            due = rank.get('due') or {}
            if not (0 <= due.get('days', 999) <= cfg.get('undated_event_days', 2)):
                continue
        score = importance.get(rank.get('importance'), 0) + urgency.get(rank.get('priority'), 0)
        score -= (age if age is not None else fallback_hours) / decay
        score -= rank.get('recommendation_penalty', 0)
        row.update(frontpage_score=score, frontpage_age_hours=age,
                   frontpage_basis='published_at' if age is not None else 'confirmed_upcoming_event')
        (known if age is not None else undated).append(row)
    eligible = [r for r in known if r.get('kind') != 'industry_buzz']
    recent = [r for r in eligible if r['frontpage_age_hours'] <= lead_hours]
    lead_pool = recent or eligible or [r for r in undated if r.get('kind') != 'industry_buzz']
    if not lead_pool:
        return []
    order = lambda r: (-r['frontpage_score'], r['frontpage_age_hours'] if r['frontpage_age_hours'] is not None else fallback_hours, r['id'])
    lead = min(lead_pool, key=order)
    result, seen_ids = [lead], {lead['id']}
    seen_titles = {display_title(lead, headlines)}
    counts = {lead.get('source_id'): 1}
    for channel, count in [('film', 5), ('art', 5), ('photography', 5), ('industry_buzz', 4)]:
        if channel == 'industry_buzz' and not (preferences.get('industry_buzz') or {}).get('enabled', True):
            continue
        matches = lambda r: (r.get('kind') == 'industry_buzz' if channel == 'industry_buzz' else r.get('kind') != 'industry_buzz' and r.get('channel') == channel)
        # Unknown publication dates never outrank a dated report in the desk.
        candidates = [r for r in known if matches(r)] or [r for r in undated if matches(r)]
        for _ in range(count):
            candidates = [r for r in candidates if r['id'] not in seen_ids and display_title(r, headlines) not in seen_titles]
            if not candidates:
                break
            row = min(candidates, key=lambda r: (-(r['frontpage_score'] - counts.get(r.get('source_id'), 0) * cfg.get('source_repeat_penalty', 6)), *order(r)[1:]))
            seen_ids.add(row['id']); seen_titles.add(display_title(row, headlines))
            counts[row.get('source_id')] = counts.get(row.get('source_id'), 0) + 1
            result.append(row)
    return result


def headline_slots(snapshot, priorities, instant):
    rows = frontpage_rows(snapshot, priorities, instant)
    if not rows:
        return []
    result = [(rows[0]['id'], 'lead')]
    for channel in ('film', 'art', 'photography'):
        row = next((r for r in rows[1:] if r.get('channel') == channel and r.get('kind') != 'industry_buzz'), None)
        if row:
            result.append((row['id'], channel))
    return result
