"""Reduce browser transport duplication; the archived source snapshot stays whole."""
import json


def browser_snapshot(snapshot):
    content = []
    for row in snapshot.get('content', []):
        public = dict(row)
        try:
            blocks = json.loads(row.get('article_blocks_json') or '[]')
            text = '\n\n'.join(block['text'] for block in blocks if isinstance(block, dict) and block.get('type') in ('paragraph', 'heading', 'quote', 'list_item') and block.get('text'))
            # Only discard a duplicate when reconstruction is exactly equivalent.
            if len(blocks) <= 2000 and (row.get('article_text') or '') == text: public.pop('article_text', None)
        except (ValueError, TypeError, KeyError):
            pass
        # These are pipeline artifacts, not reader content or provenance.
        for key in ('article_translation_json', 'editorial_draft_json', 'editorial_review_json'):
            public.pop(key, None)
        content.append(public)
    return {**snapshot, 'content': content}
