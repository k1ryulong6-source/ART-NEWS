"""Remove identified publisher widgets; never classify prose by topic or keywords."""
import json
from collections import Counter

# Exact component names, not substring selectors such as [class*=related] or
# paragraph keyword filters: a report may itself discuss newsletters or ads.
WIDGETS = ('.condensed-newsletter-signup,.theme-newsletter-signup,'
           '.newsletter-signup,.newsletter-form,.nova-js-newsletter-capture,.article-related-links,'
           '.related-stories,.related-content,.jp-relatedposts,.yarpp-related,.rp4wp-related-posts,'
           '.post-navigation,.entry-footer,.cookie-banner,.cookie-notice,'
           '.ad-slot,.advertising,.subscription-prompt,'
           '[role="navigation"],[role="search"],'
           '[data-component="newsletter-signup"]')


def widget_nodes(soup, source):
    nodes = list(soup.select(WIDGETS))
    if source.get('id') == 'monopol':
        nodes.extend(soup.select('#block-monopol-plus-paywall-curtain'))
    if source.get('id') == 'mistermotley':
        nodes.extend(soup.select('.article-footer'))
    if source.get('id') == 'rapadura':
        nodes.extend(soup.select('.meta-share,.meta-tags'))
    # Lenscratch's recommendation rail has no semantic widget class. Verify
    # both the heading container and adjacent card-list structure before removal.
    if source.get('id') == 'lenscratch':
        for title in soup.select('.title-block'):
            heading = title.find(['h2', 'h3'])
            cards = title.find_next_sibling()
            if (heading and heading.get_text(' ', strip=True) == 'Recommended'
                    and cards and cards.name == 'ul'
                    and 'news-block-columns-5' in cards.get('class', [])):
                nodes.extend([title, cards])
    # Nested newsletter components represent one widget, not repeated evidence.
    return [node for node in nodes if not any(parent in nodes for parent in node.parents)]


def remove_widgets(soup, source):
    for node in widget_nodes(soup, source):
        if node.attrs is not None:
            node.decompose()


def widget_block_runs(payload, url, source):
    from bs4 import BeautifulSoup
    from .articles import extract_article
    soup = BeautifulSoup(payload, 'lxml')
    runs = []
    marker = 'CultureDesk widget extraction boundary. ' * 5
    for widget in widget_nodes(soup, source):
        clone = BeautifulSoup(str(widget), 'lxml')
        for tag in clone.find_all(True):
            for key in ('class', 'id', 'role', 'data-component'):
                tag.attrs.pop(key, None)
        fragment = '<div class="article-body"><p>' + marker + '</p>' + str(clone.body or clone) + '</div>'
        extracted = extract_article(fragment, url, {**source, 'article_selectors': ['.article-body']})
        blocks = json.loads(extracted.get('article_blocks_json') or '[]')
        blocks = [b for b in blocks if b.get('text') != marker.strip()]
        if blocks: runs.append(blocks)
    return runs


def widget_deletions_only(payload, url, source, original, indexes):
    """A shortened page is insufficient proof: every removed block needs DOM evidence."""
    encode = lambda block: json.dumps(block, ensure_ascii=False, sort_keys=True)
    available = Counter(encode(b) for run in widget_block_runs(payload, url, source) for b in run)
    kept = set(indexes)
    removed = Counter(encode(b) for i, b in enumerate(original) if i not in kept)
    return bool(removed) and not (removed - available)


def cached_widget_indexes(payload, url, source, original):
    """Project complete widget runs only; ambiguous repeated runs are kept."""
    runs = [json.dumps(run, ensure_ascii=False, sort_keys=True)
            for run in widget_block_runs(payload, url, source) if len(run) >= 2]
    removed = set()
    for key, evidence_count in Counter(runs).items():
        run = json.loads(key)
        matches = [i for i in range(len(original) - len(run) + 1) if original[i:i + len(run)] == run]
        if len(matches) <= evidence_count:
            for start in matches:
                removed.update(range(start, start + len(run)))
    return [i for i in range(len(original)) if i not in removed] if removed else None


def subset_indexes(original, cleaned):
    """Only accept deletion of complete blocks, with all retained content exact."""
    if not cleaned or len(cleaned) >= len(original):
        return None
    indexes, cursor = [], 0
    for block in cleaned:
        while cursor < len(original) and original[cursor] != block:
            cursor += 1
        if cursor == len(original):
            return None
        indexes.append(cursor)
        cursor += 1
    return indexes


def remap_translations(row, fields, indexes):
    """Keep proven block-aligned translations without any model call or review."""
    from .editorial import checked_result, fingerprint
    from .autonomous_translation import digest
    result = {}
    original = json.loads(row['article_blocks_json'])
    cleaned_row = {**row, **fields}
    if row.get('editorial_status') in ('reviewed', 'translated'):
        old = json.loads(row.get('editorial_blocks_json') or '[]')
        if len(old) != len(original):
            raise ValueError('existing_ai_alignment_unproven')
        translated = [{**old[j], 'index': i} for i, j in enumerate(indexes)]
        checked = checked_result(cleaned_row, {
            'title_zh': row['editorial_title_zh'],
            'excerpt_zh': row.get('editorial_excerpt_zh') or '',
            'blocks': translated,
            'notes': json.loads(row.get('editorial_notes_json') or '[]')})
        result['editorial_blocks_json'] = json.dumps(checked['blocks'], ensure_ascii=False)
        # The cleaned content gets a new input fingerprint; provenance stays true.
        result['editorial_input_hash'] = fingerprint(cleaned_row, row['editorial_provider'])
        result['editorial_draft_json'] = None
    if row.get('article_translation_json') and row.get('article_translation_hash'):
        old = json.loads(row['article_translation_json'])
        # Never promote a partial machine checkpoint to a complete translation.
        if len(old) == len(original):
            result['article_translation_json'] = json.dumps([old[i] for i in indexes], ensure_ascii=False)
            provider = row.get('article_translation_provider') or ''
            if provider.startswith('offline-m2m100:'):
                result['article_translation_hash'] = digest(cleaned_row, provider)
                result['translation_input_hash'] = result['article_translation_hash']
            else:
                # Legacy machine providers have a different input hash contract;
                # keep their text as a partial draft, not a claimed valid body.
                result['article_translation_hash'] = None
    return result
