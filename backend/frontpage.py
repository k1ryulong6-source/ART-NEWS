"""Mirror CultureCore.frontpageRows for the public edition, without changing layout."""
import json
import math
from datetime import date, datetime
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


def current(row, related, instant, preferences):
    today = instant.astimezone(ZoneInfo(preferences.get('reading_timezone') or 'UTC')).date()
    try:
        age = (today - date.fromisoformat((row.get('published_at') or '')[:10])).days
        return -1 <= age <= preferences.get('recent_news_days', 30)
    except ValueError:
        pass
    for event in related:
        if event.get('date_precision') != 'day':
            continue
        exact = event.get('deadline_at') if event.get('event_type') == 'call_deadline' else event.get('start_at')
        if exact:
            try:
                if datetime.fromisoformat(exact.replace('Z', '+00:00')) <= instant:
                    continue
            except (ValueError, TypeError):
                pass
        try:
            local = instant.astimezone(ZoneInfo(event['timezone'])).date()
            start = (date.fromisoformat(event['start_date']) - local).days
            end = (date.fromisoformat(event.get('end_date') or event['start_date']) - local).days
            if (0 <= start <= 120 if event.get('event_type') == 'call_deadline' else start <= 14 and end >= 0):
                return True
        except (KeyError, ValueError, TypeError):
            pass
    return False


def frontpage_rows(snapshot, priorities, instant, preferences=None, headlines=None):
    preferences = preferences or json.loads((ROOT / 'config/preferences.json').read_text())
    if headlines is None:
        from .headlines import load_headlines
        # Priority callers may provide minimal event metadata rather than display titles.
        headlines = load_headlines({**snapshot, 'events': [e for e in snapshot.get('events', []) if e.get('title_original')]})
    available = [r for r in snapshot.get('content', []) if not r.get('is_demo')]
    titles = {r['id']: display_title(r, headlines) for r in available}
    events = {r['id']: r for r in snapshot.get('events', [])}
    related = {}
    for link in snapshot.get('content_events', []):
        if link['event_id'] in events:
            related.setdefault(link['content_id'], []).append(events[link['event_id']])
    limit = preferences.get('daily_selection_limit') or 10
    buzz = preferences.get('industry_buzz') or {'enabled': True, 'max_share': 0.1}
    interests = preferences.get('interests', []) + preferences.get('followed_entities', [])
    synonyms = {'电影': ['film', 'cinema', 'película'], '艺术': ['art', 'exhibition'],
                '摄影': ['photograph', '写真'], '摄影集': ['photobook', '写真集'],
                '电影访谈': ['interview'], '街头摄影': ['street photography']}
    scored = []
    for row in available:
        if row.get('evidence_status') == 'unverified' or not buzz.get('enabled') and row.get('kind') == 'industry_buzz':
            continue
        if not current(row, related.get(row['id'], []), instant, preferences):
            continue
        text = ' '.join([row.get('title_original') or '', titles[row['id']], row.get('summary_zh') or '']).lower()
        score = sum(any(term.lower() in text for term in [x, *synonyms.get(x, [])]) for x in interests if x) * 4
        if preferences.get('news_scope') == 'follow_city' and row.get('city') == preferences.get('default_city'):
            score += 2
        score -= priorities.get(row['id'], {}).get('recommendation_penalty', 0)
        scored.append({**row, 'score': score})
    scored.sort(key=lambda r: r.get('published_at') or '', reverse=True)
    scored.sort(key=lambda r: -r['score'])
    balanced, source_counts, channel_counts = [], {}, {}
    while scored:
        index = max(range(len(scored)), key=lambda i: scored[i]['score'] - source_counts.get(scored[i].get('source_id'), 0) * 6 - channel_counts.get(scored[i].get('channel'), 0) * 4)
        row = scored.pop(index)
        balanced.append(row)
        source_counts[row.get('source_id')] = source_counts.get(row.get('source_id'), 0) + 1
        channel_counts[row.get('channel')] = channel_counts.get(row.get('channel'), 0) + 1
    selected, deferred = [], []
    share = buzz.get('max_share', 0.1)
    for row in balanced:
        if row.get('kind') == 'industry_buzz':
            if len(deferred) < math.floor(limit * share):
                deferred.append(row)
        elif len(selected) < limit:
            selected.append(row)
    allowed = min(len(deferred), limit if share == 1 else math.floor(len(selected) * share / (1 - share))) if buzz.get('enabled') and share > 0 else 0
    selected = (selected[:limit - allowed] + deferred[:allowed])[:limit]
    def ordered(rows):
        rows = sorted(rows, key=lambda r: r.get('published_at') or '', reverse=True)
        def key(row):
            rank = priorities.get(row['id'], {})
            return (int(rank.get('priority', 'P2')[1]), {'high': 0, 'medium': 1, 'normal': 2}.get(rank.get('importance'), 2), (rank.get('due') or {}).get('days', 999))
        return sorted(rows, key=key)
    lead = next((r for r in ordered(selected) if r.get('kind') != 'industry_buzz' and r.get('evidence_status') != 'unverified'), selected[0] if selected else None)
    if not lead:
        return []
    # selectToday returns clones, so the browser's original-object pool includes all originals.
    pool = [r for r in selected + ordered(available) if r['id'] != lead['id'] and r.get('evidence_status') != 'unverified']
    seen, result = {titles[lead['id']]}, [lead]
    for channel, count in [('film', 5), ('art', 5), ('photography', 5), ('industry_buzz', 4)]:
        matching = []
        for row in pool:
            if not (row.get('kind') == 'industry_buzz' if channel == 'industry_buzz' else row.get('kind') != 'industry_buzz' and row.get('channel') == channel):
                continue
            title = titles[row['id']]
            if title not in seen:
                seen.add(title)
                matching.append(row)
        result.extend(matching[:count])
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
