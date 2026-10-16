"""Bounded project-local transient recovery; quota and server waits stay intact."""
import hashlib
import math
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime


POLICY = 'bounded-exponential-v1'
TRANSIENT_HTTP = {500, 502, 503, 504}
DEFAULTS = {'initial_seconds': 60, 'maximum_seconds': 1800, 'jitter_seconds': 15,
            'inline_retries_per_run': 2, 'inline_wait_limit_seconds': 180}


def configuration(cfg):
    values = {**DEFAULTS, **cfg.get('transient_retry', {})}
    if (any(type(value) is not int for value in values.values())
            or not 15 <= values['initial_seconds'] <= values['maximum_seconds'] <= 3600
            or not 0 <= values['jitter_seconds'] <= 60
            or not 0 <= values['inline_retries_per_run'] <= 2
            or not 0 <= values['inline_wait_limit_seconds'] <= 300):
        raise ValueError('invalid_transient_retry_limits')
    return values


def retry_after_seconds(value, instant=None):
    """HTTP Retry-After permits either seconds or a UTC HTTP-date."""
    value = value.strip() if isinstance(value, str) else ''
    if value.isdigit():
        return int(value)
    try:
        stamp = parsedate_to_datetime(value)
        if stamp.tzinfo is None:
            return 0
        return max(0, math.ceil((stamp - (instant or datetime.now(timezone.utc))).total_seconds()))
    except (TypeError, ValueError, OverflowError):
        return 0


def schedule(ledger, cfg, identity, error, server_seconds=0, instant=None):
    values = configuration(cfg)
    previous = ledger.get('service_retry') or {}
    failures = previous.get('consecutive_failures', 0)
    if type(failures) is not int or failures < 0:
        raise ValueError('invalid_service_retry_state')
    failures += 1
    jitter = int(hashlib.sha256((identity + ':' + str(failures)).encode()).hexdigest()[:8], 16)
    jitter %= values['jitter_seconds'] + 1
    base = values['initial_seconds'] * 2 ** min(failures - 1, 16)
    delay = max(server_seconds, min(values['maximum_seconds'], base + jitter))
    stamp = instant or datetime.now(timezone.utc)
    plan = {'policy': POLICY, 'consecutive_failures': failures, 'delay_seconds': delay,
            'server_retry_seconds': server_seconds, 'error': error,
            'failed_at': stamp.isoformat(), 'retry_after': (stamp + timedelta(seconds=delay)).isoformat()}
    ledger.update(service_retry=plan, retry_after=plan['retry_after'],
                  retry_status='service_wait', retry_error=error)
    return plan


def recovered(ledger):
    """Only a response from the endpoint resets consecutive service failures."""
    if 'service_retry' not in ledger and ledger.get('retry_status') != 'service_wait':
        return
    for key in ('retry_after', 'retry_status', 'retry_error', 'service_retry'):
        ledger.pop(key, None)
    ledger['last_service_recovery_at'] = datetime.now(timezone.utc).isoformat()
