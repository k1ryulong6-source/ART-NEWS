"""Short public reading excerpts and publisher-provided image links."""
import ipaddress
import re
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup


READING_FIELDS = ('excerpt_original', 'excerpt_origin', 'image_url', 'image_credit', 'image_alt', 'image_source_url')
TRANSLATION_FIELDS = ('translated_title_zh', 'translated_excerpt_zh', 'translation_provider', 'translation_status', 'translation_input_hash', 'translation_generated_at')


def public_url(value, base=None):
    if not isinstance(value, str) or not value.strip():
        return None
    url = urljoin(base or '', value.strip())
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password:
        return None
    host = parts.hostname.lower()
    if host == 'localhost' or host.endswith(('.localhost', '.local')):
        return None
    try:
        if not ipaddress.ip_address(host).is_global:
            return None
    except ValueError:
        pass
    return url


def short_excerpt(value):
    soup = BeautifulSoup(value or '', 'html.parser')
    for node in soup(['script', 'style', 'noscript']):
        node.decompose()
    text = ' '.join(soup.get_text(' ', strip=True).split())
    text = re.sub(r'\s*The post .+ appeared first on .+$', '', text, flags=re.I)
    words = text.split()
    clipped = ' '.join(words[:55]) if len(words) > 55 else text
    if len(clipped) > 280:
        clipped = clipped[:280].rsplit(' ', 1)[0] if ' ' in clipped[:280] else clipped[:280]
    return clipped.rstrip() + ('…' if len(clipped) < len(text) else '')


def image_fields(source, url, article_url, alt=None, credit=None):
    url = public_url(url, article_url)
    if not url:
        return {}
    return {'image_url': url, 'image_credit': (credit or source['name'])[:300], 'image_alt': (alt or '')[:300], 'image_source_url': article_url}


def rss_image(source, item, html, article_url):
    ns = '{http://search.yahoo.com/mrss/}'
    for node in list(item.iter(ns + 'content')) + list(item.iter(ns + 'thumbnail')) + list(item.iter('enclosure')):
        kind = node.get('type', '')
        if node.tag == 'enclosure' and not kind.startswith('image/'):
            continue
        if kind and not kind.startswith('image/') or node.get('medium') not in (None, 'image'):
            continue
        fields = image_fields(source, node.get('url'), article_url, credit=item.findtext('.//' + ns + 'credit'))
        if fields:
            return fields
    soup = BeautifulSoup(html or '', 'html.parser')
    for img in soup.select('img'):
        if any(img.get(key, '').isdigit() and int(img[key]) < 40 for key in ('width', 'height')):
            continue
        fields = image_fields(source, img.get('data-src') or img.get('src'), article_url, img.get('alt'))
        if fields:
            return fields
    return {}


def page_fields(source, url, payload):
    soup = BeautifulSoup(payload, 'html.parser')
    def meta(name):
        node = soup.find('meta', property=name) or soup.find('meta', attrs={'name': name})
        return node.get('content', '') if node else ''
    excerpt = short_excerpt(meta('og:description') or meta('description'))
    if not excerpt or excerpt == short_excerpt(meta('og:title')):
        for node in soup.select('.entry-content p, .article-content p, .news-detail-body p, article p'):
            candidate = short_excerpt(str(node))
            if len(candidate) > 40:
                excerpt = candidate
                break
    fields = image_fields(source, meta('og:image') or meta('twitter:image'), url, meta('og:image:alt'))
    if excerpt:
        fields.update(excerpt_original=excerpt, excerpt_origin='page_metadata')
    return fields


def enrich_reading(store, limit=20, getter=None):
    from .ingestion import get_url
    from .storage import ROOT
    import json
    getter = getter or get_url
    catalog = {s['id']: s for s in json.loads((ROOT / 'config/sources.json').read_text())['sources'] if s['enabled'] and s.get('adapter') == 'rss'}
    with store.connect() as db:
        records = [dict(row) for row in db.execute("SELECT * FROM content WHERE is_demo=0 AND (coalesce(excerpt_original,'')='' OR image_url IS NULL) ORDER BY published_at DESC") if row['source_id'] in catalog]
    from concurrent.futures import ThreadPoolExecutor
    def collect(row):
        source = catalog[row['source_id']]
        url = public_url(row['canonical_url'])
        domain = urlsplit(source['homepage_url']).hostname.removeprefix('www.')
        if not url or not (urlsplit(url).hostname.removeprefix('www.') == domain or urlsplit(url).hostname.endswith('.' + domain)):
            return 'skipped'
        try:
            fields = page_fields(source, url, getter(url))
            fields = {key: value for key, value in fields.items() if value and not row.get(key)}
            if fields:
                with store.connect() as db:
                    db.execute('UPDATE content SET ' + ','.join(key + '=?' for key in fields) + ' WHERE id=?', [*fields.values(), row['id']])
                return 'enriched'
            return 'unchanged'
        except Exception:
            return 'failed'
    result = {'attempted': 0, 'enriched': 0, 'failed': 0}
    with ThreadPoolExecutor(max_workers=3) as pool:
        for status in pool.map(collect, records[:max(0, min(300, limit))]):
            if status == 'skipped':
                continue
            result['attempted'] += 1
            if status in ('enriched', 'failed'):
                result[status] += 1
    return result
