"""Collect public article bodies for our own reader. Never execute publisher HTML."""
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.parse import urlsplit, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener
from bs4 import BeautifulSoup
from trafilatura import extract
from .reading import public_url
from .storage import ROOT, now

ARTICLE_FIELDS = ('article_blocks_json', 'article_text', 'article_status', 'article_reason',
                  'article_fetched_at', 'article_checked_at', 'article_source_url',
                  'article_author', 'article_extractor', 'article_hash',
                  'article_translation_json', 'article_translation_hash',
                  'article_translation_provider', 'article_translation_at')
STATUSES = {'collected', 'partial', 'restricted', 'unavailable', 'no_body', 'pending'}
SELECTORS = ('[itemprop="articleBody"]', '.entry-content', '.article-body', '.article-content',
             '.post-content', '.news-detail-body', '.news-body')
NOISE = ('script,style,noscript,iframe,nav,footer,aside,button,svg,'
         '.sharedaddy,.share-buttons,.social-share,.related-posts,.related-articles,'
         '.newsletter,.advertisement,.ads,.ad-container,.comments,#comments')


def allowed_url(url, source):
    url = public_url(url)
    if not url:
        return None
    host = urlsplit(url).hostname.removeprefix('www.')
    home = urlsplit(source['homepage_url']).hostname.removeprefix('www.')
    return url if host == home or host.endswith('.' + home) or host in source.get('original_hosts', []) else None


def fetch_page(url, source):
    class VerifiedRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            if not allowed_url(newurl, source):
                raise ValueError('unverified_redirect')
            return super().redirect_request(req, fp, code, msg, headers, newurl)
    request = Request(url, headers={'User-Agent': 'CultureDesk/0.8 public article reader', 'Accept': 'text/html'})
    with build_opener(VerifiedRedirect()).open(request, timeout=15) as response:
        payload = response.read(6_000_001)
        if len(payload) > 6_000_000:
            raise ValueError('response_too_large')
        if response.headers.get_content_type() not in ('text/html', 'application/xhtml+xml'):
            raise ValueError('not_html')
        return payload, response.url


def clean_text(value):
    return re.sub(r'\s+', ' ', value).strip()


def fetch_public_json(url, source):
    class VerifiedRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            if not allowed_url(newurl, source): raise ValueError('unverified_redirect')
            return super().redirect_request(req, fp, code, msg, headers, newurl)
    request = Request(url, headers={'User-Agent': 'CultureDesk/0.8 public article reader', 'Accept': 'application/json'})
    with build_opener(VerifiedRedirect()).open(request, timeout=15) as response:
        payload = response.read(6_000_001)
        if len(payload) > 6_000_000: raise ValueError('response_too_large')
        if response.headers.get_content_type() != 'application/json': raise ValueError('not_json')
        return json.loads(payload)


def fetch_article(url, source, getter=None, json_getter=None):
    """Only an explicitly verified publisher API can recover a missing permalink."""
    try:
        return (getter or fetch_page)(url, source)
    except HTTPError as error:
        if error.code != 404 or not source.get('public_wordpress_rest'): raise
    origin = urlsplit(source['homepage_url'])
    endpoint = origin.scheme + '://' + origin.netloc + '/wp-json/wp/v2/posts'
    slug = urlsplit(url).path.rstrip('/').split('/')[-1]
    records = (json_getter or fetch_public_json)(endpoint + '?' + urlencode({'slug': slug, 'per_page': 10}), source)
    if not isinstance(records, list): raise ValueError('public_api_not_post_list')
    for post in records:
        if not isinstance(post, dict) or post.get('link', '').rstrip('/') != url.rstrip('/'): continue
        body = post.get('content') or {}
        if post.get('status') != 'publish' or body.get('protected') is not False: continue
        if not isinstance(post.get('id'), int) or not isinstance(body.get('rendered'), str): continue
        return '<div class="entry-content">' + body['rendered'] + '</div>', endpoint + '/' + str(post['id'])
    raise ValueError('matching_public_unprotected_post_not_found')


def extract_article(payload, url, source):
    soup = BeautifulSoup(payload, 'lxml')
    author = None
    node = soup.find('meta', attrs={'name': 'author'})
    if node:
        author = node.get('content', '').strip()[:500] or None
    if source.get('id') == 'mistermotley':
        byline = soup.select_one('.single-article--active .article-footer a[href*="/authors/"]')
        if byline: author = clean_text(byline.get_text())[:500] or author
    paywall = False
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or script.get_text())
        except (ValueError, TypeError):
            continue
        def visit(value):
            nonlocal paywall, author
            if isinstance(value, list):
                for item in value: visit(item)
            elif isinstance(value, dict):
                kinds = value.get('@type', [])
                kinds = [kinds] if isinstance(kinds, str) else kinds
                if any(k in ('Article', 'NewsArticle', 'BlogPosting', 'ReportageNewsArticle') for k in kinds):
                    if value.get('isAccessibleForFree') in (False, 'false', 'False'):
                        paywall = True
                    people = value.get('author', [])
                    people = people if isinstance(people, list) else [people]
                    names = [p.get('name', '') if isinstance(p, dict) else p for p in people]
                    author = ', '.join(n for n in names if isinstance(n, str))[:500] or author
                if '@graph' in value: visit(value['@graph'])
        visit(data)
    # Extract rendered public markup only, not hidden subscription text in JSON-LD.
    from .article_cleanup import remove_widgets
    remove_widgets(soup, source)
    for node in soup.select(NOISE):
        if node.attrs is not None: node.decompose()
    for node in soup.select('[hidden], [aria-hidden="true"]') if source['source_type'] != 'official' else []:
        if node.attrs is not None: node.decompose()
    for node in soup.select('[style]') if source['source_type'] != 'official' else []:
        if node.attrs is not None and re.search(r'display\s*:\s*none|visibility\s*:\s*hidden', node.get('style', ''), re.I):
            if node.attrs is not None: node.decompose()
    blocks = []
    roots = []
    for selector in source.get('article_selectors', []) + list(SELECTORS):
        roots = [n for n in soup.select(selector) if len(n.get_text(' ', strip=True)) >= 100]
        if roots:
            break
    extractor = 'publisher-body-selector'
    if roots:
        root = max(roots, key=lambda n: len(n.get_text(' ', strip=True)))
        # Some official exhibit descriptions use a plain text div with <br>.
        if not root.find(['p', 'h2', 'h3', 'h4', 'li', 'blockquote']):
            for line in root.get_text('\n', strip=True).splitlines():
                text = clean_text(line)
                if text: blocks.append({'type': 'paragraph', 'text': text})

        for node in root.find_all(['p', 'h2', 'h3', 'h4', 'li', 'blockquote', 'img']):
            # Image captions are already included with their image block.
            if node.name != 'img' and node.find_parent('figcaption'):
                continue
            if node.name != 'img' and any(p.name in ('p', 'li', 'blockquote') for p in node.parents if p is not root):
                continue
            if node.name == 'img':
                src = node.get('data-src') or node.get('data-lazy-src') or node.get('src')
                image = public_url(src, url)
                if not image or any(node.get(k, '').isdigit() and int(node[k]) < 60 for k in ('width', 'height')):
                    continue
                figure = node.find_parent('figure')
                caption = figure.find('figcaption') if figure else None
                blocks.append({'type': 'image', 'url': image, 'alt': node.get('alt', '')[:500],
                               'caption': caption.get_text(' ', strip=True)[:1000] if caption else '', 'credit': source['name']})
            else:
                text = clean_text(node.get_text(' ', strip=True))
                if text:
                    kind = 'heading' if node.name.startswith('h') else 'quote' if node.name == 'blockquote' else 'list_item' if node.name == 'li' else 'paragraph'
                    block = {'type': kind, 'text': text}
                    links = [{'text': clean_text(a.get_text(' ', strip=True)), 'url': public_url(a.get('href'), url)} for a in node.select('a[href]')]
                    if any(link['url'] for link in links):
                        block['links'] = [link for link in links if link['url']]
                    blocks.append(block)
    else:
        extractor = 'trafilatura-2.3.1'
        xml = extract(str(soup), url=url, output_format='xml', include_comments=False,
                      include_tables=True, include_images=True, include_links=True, include_formatting=True)
        if xml:
            tree = BeautifulSoup(xml, 'xml')
            main = tree.find('main')
            if main:
                for node in main.find_all(['p', 'head', 'item', 'quote', 'cell', 'graphic']):
                    if node.name != 'graphic' and any(p.name in ('p', 'item', 'quote', 'cell') for p in node.parents if p is not main):
                        continue
                    if node.name == 'graphic':
                        image = public_url(node.get('src'), url)
                        if image: blocks.append({'type': 'image', 'url': image, 'alt': node.get('alt', ''), 'caption': '', 'credit': source['name']})
                    else:
                        text = clean_text(node.get_text(' ', strip=True))
                        if text:
                            block = {'type': 'heading' if node.name == 'head' else 'list_item' if node.name == 'item' else 'quote' if node.name == 'quote' else 'paragraph', 'text': text}
                            links = [{'text': clean_text(a.get_text(' ', strip=True)), 'url': public_url(a.get('target'), url)} for a in node.find_all('ref')]
                            if any(link['url'] for link in links): block['links'] = [link for link in links if link['url']]
                            blocks.append(block)
    text = '\n\n'.join(b['text'] for b in blocks if b.get('text'))
    # A challenge/login/consent screen is not an article body.
    page_title = soup.title.get_text(' ', strip=True) if soup.title else ''
    challenge = re.search(r'just a moment|access denied|security verification|checking your browser|robot or human', page_title, re.I)
    if challenge:
        blocks, text = [], ''
    if len(text) < 100:
        return {'article_status': 'restricted' if paywall or challenge else 'no_body',
                'article_reason': 'subscription_required' if paywall else 'access_challenge' if challenge else 'body_not_found'}
    reason = 'public_visible_body' if paywall else 'public_body_extracted'
    status = 'partial' if paywall else 'collected'
    if len(text) > 200_000 or len(blocks) > 2000:
        blocks = blocks[:2000]
        kept, length = [], 0
        for block in blocks:
            length += len(block.get('text', ''))
            if length > 200_000: break
            kept.append(block)
        blocks = kept
        text = '\n\n'.join(b['text'] for b in blocks if b.get('text'))
        status, reason = 'partial', 'size_limit'
    return {'article_blocks_json': json.dumps(blocks, ensure_ascii=False), 'article_text': text,
            'article_status': status, 'article_reason': reason, 'article_author': author,
            'article_extractor': extractor,
            'article_hash': hashlib.sha256(json.dumps(blocks, ensure_ascii=False).encode()).hexdigest()}


def collect_articles(store, limit=40, getter=None, force=False):
    catalog = {s['id']: s for s in json.loads((ROOT / 'config/sources.json').read_text())['sources'] if s['enabled']}
    stamp = now()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    refresh_cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    with store.connect() as db:
        rows = [dict(r) for r in db.execute('SELECT * FROM content WHERE is_demo=0 ORDER BY article_checked_at ASC,published_at DESC') if r['source_id'] in catalog]
    if not force:
        rows = [r for r in rows if not r['article_checked_at'] or r['article_checked_at'] < (refresh_cutoff if r['article_status'] in ('collected', 'partial') else cutoff)]
    from .priority import rank_snapshot, priority_key
    priorities = rank_snapshot(store.dataset('live'))
    # A large backlog of stale body rechecks must not delay a new major headline.
    fresh = [r for r in rows if not r.get('article_blocks_json')]
    for row in fresh:
        row['translation_priority'] = priorities[row['id']]
    fresh.sort(key=priority_key)
    rechecks = [r for r in rows if r.get('article_blocks_json')]
    from .editorial_regions import body_batch
    rows = body_batch(fresh, rechecks, catalog, limit)
    result = {k: 0 for k in ('attempted', 'collected', 'partial', 'restricted', 'unavailable', 'no_body')}
    per_source = {}
    def collect(row):
        source = catalog[row['source_id']]
        url = allowed_url(row.get('original_page_url') or row['canonical_url'], source)
        try:
            if not url: raise ValueError('unverified_source_url')
            payload, resolved = fetch_article(url, source, getter=getter)
            if not allowed_url(resolved, source): raise ValueError('unverified_redirect')
            fields = extract_article(payload, resolved, source)
            if fields.get('article_blocks_json'):
                fields.update(article_source_url=resolved, article_fetched_at=stamp)
                if '/wp-json/wp/v2/posts/' in resolved:
                    fields['article_reason'] = 'public_publisher_api_after_permalink_404'
        except HTTPError as exc:
            fields = {'article_status': 'restricted' if exc.code in (401, 403, 402) else 'unavailable', 'article_reason': 'http_' + str(exc.code)}
        except Exception as exc:
            fields = {'article_status': 'unavailable', 'article_reason': str(exc) if isinstance(exc, ValueError) else 'network_unavailable'}
        fields['article_checked_at'] = stamp
        if row.get('article_blocks_json') and not fields.get('article_blocks_json'):
            # A temporary failure cannot erase a saved body or its translation.
            fields['article_status'] = row['article_status']
            fields['article_reason'] = 'cached_body_after_' + fields['article_reason']
        if fields.get('article_hash') and fields['article_hash'] != row.get('article_hash'):
            from .article_cleanup import subset_indexes, remap_translations
            indexes = subset_indexes(json.loads(row.get('article_blocks_json') or '[]'),
                                     json.loads(fields['article_blocks_json']))
            try:
                retained = remap_translations(row, fields, indexes) if indexes is not None else {}
            except (ValueError, TypeError, KeyError):
                indexes, retained = None, {}
            for k in ARTICLE_FIELDS:
                if k.startswith('article_translation_'): fields[k] = None
            from .editorial import EDITORIAL_FIELDS
            for k in EDITORIAL_FIELDS: fields[k] = None
            if indexes is not None:
                # Pure widget removal must not erase/retranslate a valid AI body.
                for k in EDITORIAL_FIELDS:
                    fields[k] = row.get(k)
                for k in ARTICLE_FIELDS:
                    if k.startswith('article_translation_'): fields[k] = row.get(k)
                fields.update(retained)
        with store.connect() as db:
            db.execute('UPDATE content SET ' + ','.join(k+'=?' for k in fields) + ' WHERE id=?', [*fields.values(), row['id']])
        return row['source_id'], fields['article_status']
    with ThreadPoolExecutor(max_workers=4) as pool:
        for sid, status in pool.map(collect, rows[:max(0, min(2000, limit))]):
            result['attempted'] += 1
            result[status] += 1
            counts = per_source.setdefault(sid, {})
            counts[status] = counts.get(status, 0) + 1
    result['sources'] = per_source
    return result
