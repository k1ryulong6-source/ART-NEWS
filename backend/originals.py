"""Check publisher embedding rules without copying or proxying article bodies."""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from .reading import public_url
from .storage import ROOT, now

SITE_ORIGIN = 'https://k1ryulong6-source.github.io'
ORIGINAL_FIELDS = ('original_page_url', 'original_embed_status', 'original_embed_reason', 'original_embed_checked_at', 'original_resolved_url')


def origin(url):
    parts = urlsplit(url)
    return parts.scheme + '://' + parts.netloc.lower()


def ancestor_matches(rule, parent, document):
    if rule == '*':
        return True
    if rule == "'self'":
        return origin(parent) == origin(document)
    if rule == "'none'":
        return False
    if rule in ('https:', 'http:'):
        return parent.startswith(rule)
    target = urlsplit(parent)
    value = rule if '://' in rule else urlsplit(document).scheme + '://' + rule
    try:
        candidate = urlsplit(value)
        host = candidate.hostname or ''
        host_ok = host == '*' or host == target.hostname or host.startswith('*.') and target.hostname.endswith(host[1:])
        port_ok = candidate.netloc.endswith(':*') or (candidate.port or (443 if candidate.scheme == 'https' else 80)) == (target.port or (443 if target.scheme == 'https' else 80))
        return candidate.scheme == target.scheme and host_ok and port_ok
    except ValueError:
        return False


def embedding_rule(headers, document, parent=SITE_ORIGIN):
    # Each enforced CSP response header is independently binding. Report-only
    # policies do not block a frame; frame-ancestors takes precedence over XFO.
    policies = headers.get_all('Content-Security-Policy', [])
    directives = []
    for policy in policies:
        for part in re.split(r'[;,]', policy):
            words = part.strip().split()
            if words and words[0].lower() == 'frame-ancestors':
                directives.append(words[1:])
    if directives:
        if any(not rules or not any(ancestor_matches(rule, parent, document) for rule in rules) for rules in directives):
            return 'blocked', 'publisher_frame_ancestors'
        return 'available', 'publisher_headers_allow'
    xfo = ','.join(headers.get_all('X-Frame-Options', [])).upper()
    if 'DENY' in xfo or 'SAMEORIGIN' in xfo and origin(parent) != origin(document):
        return 'blocked', 'publisher_x_frame_options'
    return 'available', 'no_blocking_response_header'


def check_page(url):
    request = Request(url, headers={'User-Agent': 'CultureDesk/0.7 original page reader'}, method='GET')
    with urlopen(request, timeout=12) as response:
        resolved = public_url(response.url)
        if not resolved:
            return {'original_embed_status': 'unavailable', 'original_embed_reason': 'unsafe_redirect'}
        status, reason = embedding_rule(response.headers, resolved)
        # No article body is read, stored, translated or republished here.
        return {'original_embed_status': status, 'original_embed_reason': reason, 'original_resolved_url': resolved}


def check_originals(store, limit=20, checker=None):
    checker = checker or check_page
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    catalog = {s['id']: s for s in json.loads((ROOT / 'config/sources.json').read_text())['sources']}
    with store.connect() as db:
        # Never use embedding status to discard sources or records.
        rows = [dict(r) for r in db.execute("SELECT * FROM content WHERE is_demo=0 AND (original_embed_checked_at IS NULL OR original_embed_checked_at<?) ORDER BY original_embed_checked_at ASC,published_at DESC", (cutoff,))]
    def check(row):
        source = catalog.get(row['source_id'])
        url = public_url(row.get('original_page_url') or row['canonical_url'])
        source_host = urlsplit(source['homepage_url']).hostname.removeprefix('www.') if source else None
        target_host = urlsplit(url).hostname.removeprefix('www.') if url else None
        extra_hosts = source.get('original_hosts', []) if source else []
        if not source_host or not url or not (target_host == source_host or target_host.endswith('.' + source_host) or target_host in extra_hosts):
            fields = {'original_embed_status': 'unchecked', 'original_embed_reason': 'source_host_not_verified'}
        else:
            try:
                fields = checker(url)
            except Exception as exc:
                fields = {'original_embed_status': 'unavailable', 'original_embed_reason': 'http_' + str(exc.code) if isinstance(exc, HTTPError) else 'network_unavailable'}
        fields.update(original_page_url=url, original_embed_checked_at=now())
        with store.connect() as db:
            db.execute('UPDATE content SET ' + ','.join(k + '=?' for k in fields) + ' WHERE id=?', [*fields.values(), row['id']])
        return fields['original_embed_status']
    result = {'available': 0, 'blocked': 0, 'unavailable': 0, 'unchecked': 0}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for status in pool.map(check, rows[:max(0, min(600, limit))]):
            result[status] += 1
    return result
