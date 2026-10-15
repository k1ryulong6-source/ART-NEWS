"""Distinguish an active worker from a superseded, cancelled queue entry."""
from datetime import datetime, timezone


def collection_needs_requeue(cancelled, rows):
    """Do not duplicate a replacement, retry an old event, or hide a real failure."""
    if cancelled.get('conclusion') != 'cancelled' or not rows: return False
    if any(r.get('status') in ('queued', 'pending', 'in_progress', 'waiting', 'requested') for r in rows): return False
    cutoff = cancelled.get('created_at')
    if not cutoff: return False
    if any(r.get('created_at', '') > cutoff and r.get('conclusion') in ('success', 'failure', 'timed_out', 'action_required') for r in rows): return False
    if any(r.get('conclusion') == 'success' and r.get('updated_at', '') >= cutoff for r in rows): return False
    return True


def stage_health(rows, instant=None):
    instant = instant or datetime.now(timezone.utc)
    fields = lambda row: {key: row.get(key) for key in ('id', 'event', 'status', 'conclusion', 'html_url', 'created_at', 'updated_at')}
    timestamp = lambda row, key: datetime.fromisoformat(row[key].replace('Z', '+00:00'))
    latest = rows[0] if rows else None
    success = next((r for r in rows if r.get('conclusion') == 'success'), None)
    active = next((r for r in rows if r.get('status') != 'completed' and (instant - timestamp(r, 'created_at')).total_seconds() < 6 * 3600), None)
    stale = not success or (instant - timestamp(success, 'updated_at')).total_seconds() > 6 * 3600
    meaningful = next((r for r in rows if r.get('conclusion') not in ('cancelled', 'skipped', 'neutral')), None)
    failed = bool(meaningful and meaningful.get('conclusion') in ('failure', 'timed_out', 'action_required'))
    result = {'latest': fields(latest) if latest else None, 'last_success': fields(success) if success else None,
              'active_run': fields(active) if active else None,
              'latest_meaningful': fields(meaningful) if meaningful else None,
              'queue_warning': 'latest_entry_cancelled' if latest and latest.get('conclusion') == 'cancelled' else None,
              'status': 'failed' if failed else 'running' if active else 'stale' if stale else 'healthy'}
    return result, ':failed' if failed else ':no_recent_success' if stale and not active else None
