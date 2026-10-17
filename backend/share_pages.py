"""Per-article entry pages for sharing and search engines.

The site routes articles by hash (#reader/<id>), which link previews and crawlers
cannot see. Each published article therefore gets dist/a/<id>/index.html: the normal
front page with its own title, summary, image and canonical URL, which hands the
reader straight to #reader/<id>.
"""
import json
import re
import shutil
from html import escape
from urllib.parse import urlsplit

ARTICLE_ID = re.compile(r'live-[a-f0-9]{24}')
# Bounded so each 30-minute publish stays small; newest articles first.
MAX_PAGES = 5000
SUMMARY_CHARS = 120


def _editorial_ready(row):
    return row.get('editorial_status') in ('reviewed', 'translated') and bool(row.get('editorial_blocks_json') and row.get('editorial_title_zh'))


def _machine_ready(row):
    return row.get('machine_translation_ready') is not False and str(row.get('article_translation_provider') or '').startswith('offline-m2m100:') \
        and row.get('translation_status') == 'machine' and bool(row.get('article_translation_hash') and row.get('article_translation_json') and row.get('translated_title_zh'))


def display_title(row, headlines=None):
    """Mirror of CultureCore.displayTitle."""
    pack = (headlines or {}).get(row.get('id')) or {}
    reviewed = pack.get('title_zh') if pack.get('source_title') == row.get('title_original') else None
    return ((row.get('editorial_title_zh') if _editorial_ready(row) else None) or reviewed or row.get('title_zh')
            or (row.get('translated_title_zh') if _machine_ready(row) else None) or row.get('title_original') or '幕间休息')


def summary(row):
    """Mirror of CultureCore.readingSummary, shortened for link previews."""
    text = ((row.get('editorial_excerpt_zh') if _editorial_ready(row) else None) or row.get('summary_zh')
            or (row.get('translated_excerpt_zh') if _machine_ready(row) else None) or row.get('excerpt_original') or '')
    if not text:
        try:
            blocks = json.loads(row.get('article_blocks_json') or '[]')
            text = next((b.get('text') or '' for b in blocks if isinstance(b, dict) and b.get('type') in ('paragraph', 'quote') and b.get('text')), '')
        except (ValueError, TypeError, AttributeError):
            text = ''
    text = ' '.join(str(text).split())
    return text if len(text) <= SUMMARY_CHARS else text[:SUMMARY_CHARS - 1] + '…'


def _image(row, site_url):
    try:
        url = urlsplit(row.get('image_url') or '')
        if url.scheme == 'https' and url.hostname and not url.username and not url.password:
            return row['image_url']
    except ValueError:
        pass
    return site_url + 'og-image.png'


def _set_meta(html, attribute, key, value):
    pattern = re.compile(r'<meta %s="%s" content="[^"]*">' % (attribute, re.escape(key)))
    tag = '<meta %s="%s" content="%s">' % (attribute, key, escape(value, quote=True))
    return pattern.sub(lambda _: tag, html, count=1) if pattern.search(html) else html.replace('</head>', '  ' + tag + '\n</head>', 1)


def article_page(template, row, site_url, headlines=None):
    title, description = display_title(row, headlines), summary(row)
    url = site_url + 'a/' + row['id'] + '/'
    image = _image(row, site_url)
    html = template.replace('<head>', '<head>\n  <base href="../../">\n  <script>if(!location.hash)history.replaceState(null,"",document.baseURI+"#reader/%s")</script>' % row['id'], 1)
    html = re.sub(r'<title>[^<]*</title>', lambda _: '<title>%s · 幕间休息</title>' % escape(title), html, count=1)
    html = re.sub(r'<link rel="canonical" href="[^"]*">', '', html)
    html = html.replace('</head>', '  <link rel="canonical" href="%s">\n</head>' % escape(url, quote=True), 1)
    for attribute, key, value in (('name', 'description', description or title), ('property', 'og:type', 'article'),
                                  ('property', 'og:title', title), ('property', 'og:description', description or '幕间休息 · 艺术、电影与摄影新闻'),
                                  ('property', 'og:url', url), ('property', 'og:image', image), ('name', 'twitter:title', title),
                                  ('name', 'twitter:description', description), ('name', 'twitter:image', image)):
        html = _set_meta(html, attribute, key, value)
    if image != site_url + 'og-image.png':
        html = re.sub(r'\s*<meta property="og:image:(width|height)" content="[^"]*">', '', html)
    if row.get('published_at'):
        html = _set_meta(html, 'property', 'article:published_time', row['published_at'])
    # Readable without scripts; the app replaces it with the full reader.
    original = row.get('original_page_url') or row.get('canonical_url') or ''
    link = ' · <a href="%s" rel="noopener">原文</a>' % escape(original, quote=True) if original.startswith(('https://', 'http://')) else ''
    body = '<article class="reader-page"><h1>%s</h1>%s<p><a href="#reader/%s">阅读全文</a>%s</p></article>' % (
        escape(title), '<p>%s</p>' % escape(description) if description else '', row['id'], link)
    return html.replace('<main id="main" tabindex="-1"></main>', '<main id="main" tabindex="-1">%s</main>' % body, 1)


def shareable(rows):
    rows = [row for row in rows if ARTICLE_ID.fullmatch(str(row.get('id') or '')) and not row.get('is_demo')]
    rows.sort(key=lambda row: str(row.get('published_at') or row.get('fetched_at') or ''), reverse=True)
    return rows[:MAX_PAGES]


def sitemap(rows, site_url):
    entries = ['  <url><loc>%s</loc></url>' % escape(site_url)]
    for row in rows:
        lastmod = str(row.get('updated_at') or row.get('published_at') or '')[:10]
        entries.append('  <url><loc>%sa/%s/</loc>%s</url>' % (escape(site_url), row['id'], '<lastmod>%s</lastmod>' % lastmod if re.fullmatch(r'\d{4}-\d{2}-\d{2}', lastmod) else ''))
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(entries) + '\n</urlset>\n'


def write_share_pages(output, template, snapshot, site_url, headlines=None):
    """Write a/<id>/index.html, sitemap.xml and robots.txt; return the page count."""
    if not site_url:
        return 0
    site_url = site_url.rstrip('/') + '/'
    rows = shareable(snapshot.get('content', []))
    root = output / 'a'
    if root.exists():
        shutil.rmtree(root)
    for row in rows:
        folder = root / row['id']
        folder.mkdir(parents=True)
        (folder / 'index.html').write_text(article_page(template, row, site_url, headlines), encoding='utf-8')
    (output / 'sitemap.xml').write_text(sitemap(rows, site_url), encoding='utf-8')
    (output / 'robots.txt').write_text('User-agent: *\nAllow: /\n\nSitemap: %ssitemap.xml\n' % site_url, encoding='utf-8')
    return len(rows)
