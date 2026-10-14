"""Versioned public original-article API for Babel's reader, with no personal state."""
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlsplit
from .storage import ROOT
from .autonomous_translation import machine_ready

PROTOCOL = 'intermission-article-v1'
CONTENT_ID = re.compile(r'live-[a-f0-9]{24}\Z')


def integrations():
    return json.loads((ROOT / 'config/integrations.json').read_text())


def public_url(value):
    try:
        url = urlsplit(value or '')
        return value if url.scheme in ('https', 'http') and url.hostname and not url.username and not url.password else None
    except ValueError:
        return None


def article_payload(row, sources, site_url=None):
    if row.get('is_demo') or not CONTENT_ID.fullmatch(row['id']):
        return None
    try:
        blocks = json.loads(row.get('article_blocks_json') or '[]')
    except (ValueError, TypeError):
        return None
    text = row.get('article_text') or '\n\n'.join(b.get('text', '') for b in blocks if b.get('type') != 'image')
    if not blocks or not text.strip() or not re.fullmatch(r'[a-f0-9]{64}', row.get('article_hash') or ''):
        return None
    source = sources.get(row['source_id'], {})
    site_url = site_url or integrations().get('site_url', 'https://k1ryulong6-source.github.io/ART-NEWS/')
    if not public_url(site_url) or urlsplit(site_url).query or urlsplit(site_url).fragment:
        raise ValueError('invalid_public_site_url')
    reference = None
    if row.get('editorial_status') in ('reviewed', 'translated') and row.get('editorial_blocks_json') and row.get('editorial_title_zh'):
        reference = {'kind': 'ai-reviewed' if row['editorial_status'] == 'reviewed' else 'ai-direct',
                     'title': row['editorial_title_zh'], 'blocks': json.loads(row['editorial_blocks_json']),
                     'model': row.get('editorial_model')}
    elif machine_ready(row):
        reference = {'kind': 'machine', 'title': row['translated_title_zh'],
                     'blocks': json.loads(row['article_translation_json']), 'model': row.get('article_translation_provider')}
    return {'protocol': PROTOCOL, 'schema_version': 1, 'id': row['id'],
            'source_hash': row['article_hash'], 'title': row['title_original'],
            'language': row['language'], 'text': text, 'blocks': blocks,
            'source': {'name': source.get('name') or row['source_id'],
                       'url': public_url(row.get('article_source_url') or row.get('original_page_url') or row['canonical_url']),
                       'author': row.get('article_author'), 'published_at': row.get('published_at')},
            'news_url': site_url.rstrip('/') + '/#reader/' + row['id'],
            'access': 'public-partial' if row.get('article_status') == 'partial' else 'collected',
            'collected_at': row.get('article_fetched_at'), 'translation_zh': reference}


def export_articles(snapshot, config, directory):
    directory = Path(directory)
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True)
    sources = {source['id']: source for source in config['sources']}
    items = []
    site_url = integrations().get('site_url')
    for row in snapshot.get('content', []):
        payload = article_payload(row, sources, site_url=site_url)
        if payload:
            (directory / (row['id'] + '.json')).write_text(json.dumps(payload, ensure_ascii=False) + '\n', encoding='utf-8')
            items.append({'id': row['id'], 'language': row['language'], 'source_hash': row['article_hash']})
    (directory / 'index.json').write_text(json.dumps({'protocol': PROTOCOL, 'snapshot_at': snapshot.get('snapshot_at'),
                                                     'count': len(items), 'items': items}, ensure_ascii=False) + '\n', encoding='utf-8')
    return len(items)
