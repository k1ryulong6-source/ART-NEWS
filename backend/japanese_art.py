"""Verified public news lists, and TAB's anonymous paginated article view.

Listing hydration contains metadata, not article bodies. For article pagination
read only the selected public page, never `paginated_contents` (all-page data).
"""
import html
import json
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
from .reading import image_fields, public_url


def next_fallback(soup, name):
    script = soup.find('script', id='__NEXT_DATA__')
    data = json.loads(script.string or script.get_text()) if script else {}
    for key, value in data.get('props', {}).get('pageProps', {}).get('fallback', {}).items():
        query = json.loads(key)
        if query.get('name') == name:
            return query.get('props', {}), value
    raise ValueError('publisher_public_list_structure_changed')


def published_instant(value):
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return stamp.astimezone(timezone.utc).isoformat() if stamp.tzinfo else None
    except (AttributeError, TypeError, ValueError):
        return None


def news_record(source, title, url, categories=(), excerpt='', published=None):
    from .ingestion import content_record, source_filtered, GEAR, GEAR_MULTILINGUAL
    if (not title or not public_url(url) or urlsplit(url).hostname != urlsplit(source['homepage_url']).hostname
            or GEAR.search(title) or GEAR_MULTILINGUAL.search(title) or source_filtered(source, title, categories)):
        return None
    record = content_record(source, title, url, excerpt=excerpt, published=published)
    # Photo-report is a reporting format, not evidence of a photography topic.
    if re.search(r'写真(?:家|展|集)|フォトブック|photograph|photobook', title, re.I):
        record['channel'] = 'photography'
    if 'インタビュー' in categories:
        record['kind'] = 'interview'
    if excerpt:
        record['excerpt_origin'] = 'public_page'
    return record


def artexhibition_records(source, payload):
    soup = BeautifulSoup(payload, 'html.parser')
    records = {}
    cards = soup.select('main .grid-tile article')
    if not cards:
        raise ValueError('artexhibition_public_list_structure_changed')
    for card in cards:
        anchor = card.select_one('h3.article-title a[href]')
        if not anchor:
            continue
        url = urljoin(source['feed_url'], anchor['href'])
        if not re.fullmatch(r'/topics/(?:[^/]+/)+\d{8}-AEJ\d+/', urlsplit(url).path):
            continue
        description = card.select_one('.body-txt')
        # Cards give a day only. Do not fabricate a publication clock: exact
        # publisher metadata is filled when fetching the article itself.
        record = news_record(source, anchor.get_text(' ', strip=True), url,
                             excerpt=description.get_text(' ', strip=True) if description else '')
        if record:
            image = card.select_one('figure img')
            if image:
                record.update(image_fields(source, image.get('src'), url, image.get('alt')))
            records[record['id']] = record
    return list(records.values()), [], []


def tokyo_art_beat_records(source, payload):
    soup = BeautifulSoup(payload, 'html.parser')
    props, result = next_fallback(soup, 'ArticleSearch')
    if props.get('condId') != 'latest' or not isinstance(result.get('data'), list):
        raise ValueError('tab_public_list_structure_changed')
    records = {}
    for item in result['data']:
        slug = item.get('slug', '')
        if not isinstance(slug, str) or not re.fullmatch(r'[\w-]+', slug):
            continue
        url = urljoin(source['homepage_url'], '/articles/-/' + slug)
        categories = [c.get('fields', {}).get('name', '') for c in item.get('categories', [])]
        record = news_record(source, item.get('title', ''), url, categories,
                             published=published_instant(item.get('publishedAt')))
        if record:
            image = (item.get('mainImage') or {}).get('fields', {})
            record.update(image_fields(source, image.get('file', {}).get('url'), url, image.get('description')))
            records[record['id']] = record
    return list(records.values()), [], []


def render_public_nodes(nodes, base):
    """Small inert rich-text renderer for the current anonymous page only."""
    parts = []
    tags = {'paragraph': 'p', 'heading-1': 'h2', 'heading-2': 'h2', 'heading-3': 'h3',
            'heading-4': 'h4', 'heading-5': 'h4', 'heading-6': 'h4',
            'blockquote': 'blockquote', 'unordered-list': 'ul', 'ordered-list': 'ol',
            'list-item': 'li'}
    for node in nodes:
        kind = node.get('nodeType')
        if kind == 'text':
            parts.append(html.escape(node.get('value', '')))
        elif kind in tags:
            tag = tags[kind]
            parts.append('<' + tag + '>' + render_public_nodes(node.get('content', []), base) + '</' + tag + '>')
        elif kind == 'hyperlink':
            text = render_public_nodes(node.get('content', []), base)
            url = public_url(node.get('data', {}).get('uri'), base)
            parts.append('<a href="' + html.escape(url, quote=True) + '">' + text + '</a>' if url else text)
        elif kind == 'embedded-asset-block':
            fields = node.get('data', {}).get('target', {}).get('fields', {})
            file = fields.get('file', {})
            file = file.get('en-US', file)
            url = public_url(file.get('url'), base)
            caption = fields.get('description', '') or ''
            caption = caption.get('en-US', '') if isinstance(caption, dict) else caption
            if not url or not file.get('contentType', '').startswith('image/'):
                raise ValueError('unsupported_public_asset')
            parts.append('<figure><img src="' + html.escape(url, quote=True) + '"><figcaption>'
                         + html.escape(caption) + '</figcaption></figure>')
        elif kind == 'embedded-entry-block':
            target = node.get('data', {}).get('target', {})
            entry_type = target.get('sys', {}).get('contentType', {}).get('sys', {}).get('id')
            if entry_type == 'article':
                continue  # An embedded recommendation card, not article prose.
            if entry_type != 'event':
                raise ValueError('unsupported_public_entry')
            fields = target.get('fields', {})
            def localized(key):
                value = fields.get(key) or {}
                return value.get('ja-JP') or value.get('en-US') if isinstance(value, dict) else value
            title, slug = localized('eventName'), localized('slug')
            url = public_url('/events/-/' + slug, base) if isinstance(slug, str) else None
            if not isinstance(title, str) or not url:
                raise ValueError('public_event_reference_missing')
            # Only card fields visible on the public page, not the embedded
            # entry's description/other unrendered rich text.
            dates = [localized(k) for k in ('scheduleStartsOn', 'scheduleEndsOn')]
            text = title + ' ' + ' — '.join(d for d in dates if isinstance(d, str))
            parts.append('<p><a href="' + html.escape(url, quote=True) + '">' + html.escape(text) + '</a></p>')
        elif kind == 'hr':
            parts.append('<hr>')
        else:
            # Unknown widgets/embeds must not silently yield a claimed full body.
            raise ValueError('unsupported_public_rich_text_node')
    return ''.join(parts)


def tab_article_pages(payload, url, source, getter):
    """Keep visible page-one DOM; follow verified public page routes boundedly.

    /pageN is client rendered. Its selected `paginated_content` was compared to
    the anonymous browser view. Never render the all-page hydration field or a
    subscription article; a missing/changed page returns a labelled partial.
    """
    soup = BeautifulSoup(payload, 'lxml')
    root = soup.select_one('.articleDetail')
    if not root:
        return payload
    body = BeautifulSoup('<html><head></head><body><div class="culture-tab-body"></div></body></html>', 'lxml')
    target = body.select_one('.culture-tab-body')
    sponsor = root.select_one('.articleDetailHead .prTag')
    if sponsor:
        target.append(sponsor.extract())
    image = root.select_one('.articleMainImage-wrap')
    if image:
        figure = body.new_tag('figure')
        img, caption = image.find('img'), image.select_one('.articleFigcaption')
        if img:
            figure.append(img.extract())
            if caption:
                caption.name = 'figcaption'
                figure.append(caption.extract())
            target.append(figure)
    for fragment in root.select(':scope > .detailContent:not(.marginContent)'):
        # In-body event references retain their title/date/link, but not reader
        # rating, bookmark controls, thumbnails or a separate related rail.
        for card in list(fragment.select('a.relatedLink')):
            label = ' '.join(n.get_text(' ', strip=True) for n in card.select('.eventName,.venueName,.eventDate'))
            replacement = body.new_tag('p')
            link = body.new_tag('a', href=card.get('href', ''))
            link.string = label
            replacement.append(link)
            card.replace_with(replacement)
        for widget in list(fragment.select('.mylistButton,.articleContents,.ad-area2')):
            widget.decompose()
        target.append(fragment.extract())
    partial = False
    try:
        props, result = next_fallback(soup, 'ArticleDetail')
        row = result['data'][0]
        total = row.get('paginated_content_total') or 1
        if total == 1 and root.select_one('.pagenation'):
            raise ValueError('public_pagination_metadata_missing')
        if total > 1 and (row.get('articleType') == 'Page nation' or root.select_one('.pagenation')):
            slug = urlsplit(url).path.rstrip('/').split('/')[-1]
            restricted = any(re.search(r'"isAccessibleForFree"\s*:\s*(?:false|"false")', s.get_text())
                             for s in soup.select('script[type="application/ld+json"]'))
            if (restricted or not root.select_one('.pagenation') or row.get('articleType') != 'Page nation' or row.get('slug') != slug
                    or props.get('slug') != slug or not 1 < total <= 12):
                raise ValueError('unverified_public_pagination')
            for page in range(2, total + 1):
                page_url = url.rstrip('/') + '/page' + str(page)
                page_payload, resolved = getter(page_url, source)
                if resolved.rstrip('/') != page_url:
                    raise ValueError('public_page_redirect_changed')
                query, page_result = next_fallback(BeautifulSoup(page_payload, 'html.parser'), 'ArticleDetail')
                current = page_result['data'][0]
                selected = current.get('paginated_content', {})
                if (query.get('slug') != slug or query.get('q') != ['page' + str(page)]
                        or current.get('slug') != slug or current.get('articleType') != 'Page nation'
                        or current.get('paginated_content_total') != total
                        or current.get('paginated_content_current') != page - 1
                        or selected.get('page') != page - 1):
                    raise ValueError('public_page_identity_changed')
                fragment = render_public_nodes(selected['content'], page_url)
                target.append(BeautifulSoup(fragment, 'html.parser'))
    except Exception:
        partial = True
    if partial:
        target['data-public-pagination-incomplete'] = 'true'
    # Preserve public author / publication / accessibility metadata for extraction.
    for tag in soup.select('head meta,script[type="application/ld+json"]'):
        body.head.append(tag.extract())
    return str(body)
