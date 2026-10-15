"""Bounded source-vs-cache checks. Never rewrite articles or call a model."""
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from .articles import allowed_url, fetch_article, extract_article, SELECTORS, NOISE, clean_text
from .article_cleanup import remove_widgets
from .editorial import checked_result
from .reading import public_url
from .storage import ROOT, now
from .acceptance import snapshot_key


def inspect_cached(row):
    issues = []
    try:
        blocks = json.loads(row.get('article_blocks_json') or '[]')
        if not blocks:
            return ['body_missing']
        if hashlib.sha256(row['article_blocks_json'].encode()).hexdigest() != row.get('article_hash'):
            issues.append('source_hash_mismatch')
        for block in blocks:
            if block.get('type') == 'image':
                if not public_url(block.get('url')):
                    issues.append('invalid_image_url')
            elif not isinstance(block.get('text'), str) or not block['text'].strip():
                issues.append('empty_text_block')
        if row.get('editorial_status') in ('reviewed', 'translated'):
            translated = json.loads(row.get('editorial_blocks_json') or '[]')
            checked_result(row, {'title_zh': row.get('editorial_title_zh'), 'excerpt_zh': row.get('editorial_excerpt_zh') or '',
                                'blocks': [{**b, 'index': i} for i, b in enumerate(translated)], 'notes': []})
    except (ValueError, TypeError, KeyError) as error:
        issues.append('invalid_cached_body:' + str(error)[:100])
    return sorted(set(issues))


def compare_public_markup(payload, url, source, extracted):
    soup = BeautifulSoup(payload, 'lxml')
    remove_widgets(soup, source)
    for node in soup.select(NOISE):
        if node.attrs is not None: node.decompose()
    if source['source_type'] != 'official':
        for node in soup.select('[hidden],[aria-hidden="true"],[style]'):
            if node.attrs is not None and (node.has_attr('hidden') or node.get('aria-hidden') == 'true'
                    or re.search(r'display\s*:\s*none|visibility\s*:\s*hidden', node.get('style', ''), re.I)):
                node.decompose()
    roots = []
    for selector in source.get('article_selectors', []) + list(SELECTORS):
        roots = [n for n in soup.select(selector) if len(n.get_text(' ', strip=True)) >= 100]
        if roots: break
    if not roots:
        return ['publisher_body_boundary_unverified']
    root = max(roots, key=lambda n: len(n.get_text(' ', strip=True)))
    blocks = json.loads(extracted.get('article_blocks_json') or '[]')
    text = clean_text(' '.join(b.get('text', '') + ' ' + b.get('caption', '') for b in blocks))
    missing = 0
    for node in root.find_all(['p', 'h2', 'h3', 'h4', 'li', 'blockquote']):
        if node.find_parent('figcaption') or any(p.name in ('p', 'li', 'blockquote') for p in node.parents if p is not root):
            continue
        expected = clean_text(node.get_text(' ', strip=True))
        if len(expected) >= 30 and expected not in text: missing += 1
    issues = ['public_paragraphs_not_extracted:' + str(missing)] if missing else []
    for figure in root.find_all('figure'):
        caption, image = figure.find('figcaption'), figure.find('img')
        if caption and image and clean_text(caption.get_text(' ', strip=True)):
            image_url = public_url(image.get('data-src') or image.get('data-lazy-src') or image.get('src'), url)
            stored = next((b for b in blocks if b.get('type') == 'image' and b.get('url') == image_url), None)
            if not stored or clean_text(stored.get('caption', '')) != clean_text(caption.get_text(' ', strip=True)):
                issues.append('public_image_caption_not_extracted')
    return sorted(set(issues))


def content_signature(blocks):
    # Image resize/tracking queries do not change the underlying article text.
    return [(b.get('type'), b.get('text'), b.get('caption'), b.get('alt'),
             urlsplit(b.get('url', '')).path if b.get('type') == 'image' else None) for b in blocks]


def audit_quality(snapshot, catalog, directory, limit=20, getter=None):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    sources = {s['id']: s for s in catalog['sources'] if s.get('enabled')}
    rows = [r for r in snapshot['content'] if not r.get('is_demo')]
    states, candidates, local = {}, [], []
    stamp = now(); instant = datetime.now(timezone.utc)
    for row in rows:
        problems = inspect_cached(row)
        if problems: local.append({'id': row['id'], 'issues': problems})
        if not row.get('article_blocks_json') or row['source_id'] not in sources: continue
        path = directory / (row['id'] + '.json')
        try: state = json.loads(path.read_text())
        except (OSError, ValueError): state = {}
        if state.get('source_hash') != row['article_hash'] or state.get('source_title') != row['title_original']:
            state = {}
        states[row['id']] = state
        if state.get('next_check_at', '') <= stamp:
            candidates.append(row)
    # Round-robin publishers; unseen sources and oldest checks come first.
    groups = {}
    for row in sorted(candidates, key=lambda r: (states[r['id']].get('checked_at', ''), r['id'])):
        groups.setdefault(row['source_id'], []).append(row)
    selected = []
    budget = max(0, min(limit, 100))
    while groups and len(selected) < budget:
        for source_id in list(groups):
            if len(selected) >= budget: break
            selected.append(groups[source_id].pop(0))
            if not groups[source_id]: del groups[source_id]

    def verify(row):
        state = {'schema_version': 1, 'id': row['id'], 'source_id': row['source_id'],
                 'source_hash': row['article_hash'], 'source_title': row['title_original'], 'checked_at': stamp}
        try:
            source = sources[row['source_id']]
            url = allowed_url(row.get('original_page_url') or row['canonical_url'], source)
            if not url: raise ValueError('unverified_source_url')
            raw, resolved = fetch_article(url, source, getter=getter)
            if not allowed_url(resolved, source): raise ValueError('unverified_redirect')
            fields = extract_article(raw, resolved, source)
            if not fields.get('article_blocks_json'): raise ValueError(fields.get('article_reason', 'body_not_found'))
            issues = compare_public_markup(raw, resolved, source, fields)
            if content_signature(json.loads(fields['article_blocks_json'])) != content_signature(json.loads(row['article_blocks_json'])):
                issues.append('source_content_changed_since_collection')
            state.update(status='issues' if issues else 'passed', issues=sorted(set(issues)),
                         public_status=fields['article_status'])
        except Exception as error:
            state.update(status='unavailable', issues=[str(error)[:120]])
        state['next_check_at'] = (instant + timedelta(hours=168 if state['status'] == 'passed' else 6)).isoformat()
        return state

    for state in ThreadPoolExecutor(max_workers=4).map(verify, selected):
        (directory / (state['id'] + '.json')).write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
        states[state['id']] = state
    verified = [s for s in states.values() if s.get('status') == 'passed' and s.get('next_check_at', '') > stamp]
    unresolved = [s for s in states.values() if s.get('status') in ('issues', 'unavailable')]
    return {'schema_version': 1, 'checked_at': stamp, 'snapshot_at': snapshot.get('snapshot_at'), 'snapshot_key': snapshot_key(snapshot, catalog),
            'scope': 'program_structure_and_public_markup_only_not_semantic_review',
            'total': len(rows), 'bodies': len(states), 'local_issues': local,
            'remote_checked_this_run': len(selected), 'remote_verified': len(verified),
            'remote_unchecked': len(states) - len(verified) - len(unresolved),
            'remote_unresolved': unresolved, 'all_current_bodies_verified': len(verified) == len(states) and bool(states),
            'complete': not local and len(verified) == len(states) and bool(states)}
