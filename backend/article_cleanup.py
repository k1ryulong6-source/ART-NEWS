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
           '[data-component="newsletter-signup"],'
           '[data-component="social-media"],[data-alias="social-media__list"]')


def widget_nodes(soup, source):
    nodes = list(soup.select(WIDGETS))
    if source.get('id') == 'artexhibition':
        nodes.extend(soup.select('article.main-content > .main-content-header,article.main-content > .main-content-footer,article.main-content > .main-content-title,article.main-content > .article-time,.iframely-embed'))
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
    if source.get('id') == 'artexhibition':
        # This publisher appends a recommendation inside the event-info p.
        # Trim only its exact tail marker when followed by a verified own-site
        # embedded article card; preserve the event details before the marker.
        for card in soup.select('.news-detail > .iframely-embed'):
            link = card.select_one('a[data-iframely-url][href^="https://artexhibition.jp/topics/"]')
            paragraph = card.find_previous_sibling()
            if not link or not paragraph or paragraph.name != 'p':
                continue
            marker = next((n for n in paragraph.find_all(string=True)
                           if str(n).strip() == '＜あわせて読みたい＞'), None)
            if marker is not None and marker.parent is paragraph:
                for following in list(marker.next_siblings):
                    following.extract()
                marker.extract()
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
            for key in ('class', 'id', 'role', 'data-component', 'data-alias'):
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


def remap_ai_progress(row, fields, indexes, state, cfg=None):
    """Reindex accepted API units after proven deletions; never infer old text."""
    from .ai_translation import configuration, input_hash, source_units
    cfg = cfg or configuration()
    provider = state.get('provider') or ''
    if (not provider.startswith('contextual-api:gemini:') or state.get('id') != row['id']
            or state.get('source_hash') != row['article_hash']
            or state.get('input_hash') != input_hash(row, provider, cfg)
            or not isinstance(state.get('outputs'), dict)):
        return None
    _, old_units, _ = source_units(row, cfg['source_characters_per_unit'])
    cleaned_row = {**row, **fields}
    _, new_units, _ = source_units(cleaned_row, cfg['source_characters_per_unit'])
    old_units = dict(old_units)
    outputs = {}
    for key, text in new_units:
        old_key = key
        if key.startswith('block:'):
            parts = key.split(':')
            parts[1] = str(indexes[int(parts[1])])
            old_key = ':'.join(parts)
        if old_units.get(old_key) != text:
            return None
        translated = state['outputs'].get(old_key)
        if isinstance(translated, str):
            outputs[key] = translated
    return {**state, 'source_hash': fields['article_hash'],
            'input_hash': input_hash(cleaned_row, provider, cfg), 'outputs': outputs,
            'cleanup': {'from_source_hash': row['article_hash'], 'retained_units': len(outputs),
                        'removed_units': len(state['outputs']) - len(outputs)}}
