"""Reduce browser transport duplication; the archived source snapshot stays whole."""
import json
import re
from .autonomous_translation import machine_ready
from .frontpage import headline_ready


def browser_snapshot(snapshot):
    content = []
    for row in snapshot.get('content', []):
        public = dict(row)
        public['headline_ready'] = headline_ready(row)
        public['machine_translation_ready'] = bool(machine_ready(row))
        try:
            blocks = json.loads(row.get('article_blocks_json') or '[]')
            text = '\n\n'.join(block['text'] for block in blocks if isinstance(block, dict) and block.get('type') in ('paragraph', 'heading', 'quote', 'list_item') and block.get('text'))
            # Only discard a duplicate when reconstruction is exactly equivalent.
            if len(blocks) <= 2000 and (row.get('article_text') or '') == text: public.pop('article_text', None)
        except (ValueError, TypeError, KeyError):
            pass
        # These are pipeline artifacts, not reader content or provenance.
        unused = ['editorial_draft_json', 'editorial_review_json']
        if not public['machine_translation_ready']:
            unused.append('article_translation_json')
        for key in unused:
            public.pop(key, None)
        content.append(public)
    return {**snapshot, 'content': content}


# Article bodies are most of the snapshot; the static site ships them per article.
BODY_FIELDS = ('article_blocks_json', 'editorial_blocks_json', 'article_translation_json', 'article_text')
# Pipeline bookkeeping no page view reads; it travels with the body so nothing is dropped.
DETAIL_FIELDS = ('body_hash', 'translation_input_hash', 'editorial_input_hash', 'fetched_at', 'article_fetched_at',
                 'article_translation_at', 'translation_generated_at', 'editorial_at', 'summary_generated_at',
                 'original_embed_checked_at', 'original_embed_reason', 'original_embed_status',
                 'article_extractor', 'original_resolved_url')
READABLE = ('paragraph', 'heading', 'quote', 'list_item')


def _blocks(value):
    try:
        blocks = json.loads(value or '[]')
    except (ValueError, TypeError):
        return []
    return [b for b in blocks if isinstance(b, dict)] if isinstance(blocks, list) else []


def _block_text(blocks, captions=False):
    return '\n\n'.join(str(b.get('text') or (b.get('caption') if captions else '') or '') for b in blocks[:2000]
                       if b.get('type') in READABLE + (('image',) if captions else ()) and (b.get('text') or (captions and b.get('caption'))))


def split_bodies(snapshot):
    """Return (index snapshot, {id: body fields}, {id: search text}) for a browser snapshot.

    The index row keeps flags the list views need (which bodies exist and a short
    preview) so cards, readiness checks and search work before any body loads.
    """
    import hashlib
    content, bodies, search = [], {}, {}
    for row in snapshot.get('content', []):
        body = {key: row[key] for key in BODY_FIELDS if isinstance(row.get(key), str) and row[key]}
        if not body or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', str(row.get('id') or '')):
            content.append(row)
            continue
        body.update({key: row[key] for key in DETAIL_FIELDS if row.get(key) is not None})
        public = {key: value for key, value in row.items() if key not in BODY_FIELDS + DETAIL_FIELDS}
        original = _blocks(row.get('article_blocks_json'))
        source_text = row['article_text'] if isinstance(row.get('article_text'), str) else _block_text(original)
        public['has_original_body'] = bool(source_text.strip() and original)
        public['has_editorial_body'] = 'editorial_blocks_json' in body
        public['has_translation_body'] = 'article_translation_json' in body
        preview = next((str(b.get('text') or '') for b in original if b.get('type') in ('paragraph', 'quote') and b.get('text')), '')
        if preview and not (row.get('excerpt_original') or row.get('summary_zh')):
            public['body_preview'] = preview[:400]
        encoded = json.dumps(body, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
        public['body_ref'] = hashlib.sha256(encoded.encode('utf-8')).hexdigest()[:12]
        bodies[row['id']] = body
        editorial = row.get('editorial_status') in ('reviewed', 'translated') and row.get('editorial_title_zh')
        reading = row.get('editorial_blocks_json') if editorial else row.get('article_translation_json') if row.get('machine_translation_ready') else None
        search[row['id']] = '\n\n'.join(filter(None, (source_text, _block_text(_blocks(reading), captions=True))))
        content.append(public)
    return {**snapshot, 'content': content}, bodies, search
