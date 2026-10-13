"""Explicit event instants, independent of reader timezone and date-only guesses."""
from datetime import datetime, timezone


def event_instant(event):
    value = event.get('deadline_at') if event.get('event_type') == 'call_deadline' else event.get('start_at')
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('活动时刻必须包含时区')
    return parsed


def instant_passed(event, now=None):
    value = event_instant(event)
    return bool(value and value <= (now or datetime.now(timezone.utc)))
