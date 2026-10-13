"""Resumable paragraph translations, using the same persisted daily call budget."""
import hashlib
import json
import os
from datetime import datetime, timezone
from .storage import now
from .translation import PublicGoogleTranslator, TranslationBudgetReached


def chunks(text, size=900):
    result = []
    while text:
        end = min(size, len(text))
        if end < len(text):
            boundary = max(text.rfind(' ', 0, end), text.rfind('。', 0, end), text.rfind('. ', 0, end))
            if boundary > size // 2: end = boundary + 1
        result.append(text[:end]); text = text[end:]
    return result


def translate_articles(store, provider=None, call_limit=None, daily_limit=None):
    kind = os.getenv('TRANSLATION_PROVIDER', 'disabled')
    if provider is None and kind == 'disabled': return {'translated': 0, 'calls': 0, 'status': 'disabled'}
    if provider is None and kind != 'google-public': raise ValueError('未知翻译服务')
    provider = provider or PublicGoogleTranslator()
    cap = max(0, min(1200, int(call_limit if call_limit is not None else os.getenv('ARTICLE_TRANSLATION_LIMIT', '120'))))
    total_cap = int(daily_limit if daily_limit is not None else os.getenv('TRANSLATION_DAILY_LIMIT', '1000'))
    day = datetime.now(timezone.utc).date().isoformat()
    result = {'provider': provider.name, 'translated': 0, 'partial': 0, 'failed': 0, 'calls': 0, 'budget_exhausted': False}
    with store.connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS translation_usage(day TEXT PRIMARY KEY, calls INTEGER NOT NULL)')
        rows = [dict(r) for r in db.execute("SELECT * FROM content WHERE is_demo=0 AND language!='zh' AND article_blocks_json IS NOT NULL ORDER BY published_at DESC")]
    for row in rows:
        target_hash = hashlib.sha256((provider.name + (row['article_hash'] or '')).encode()).hexdigest()
        if row['article_translation_hash'] == target_hash: continue
        original = json.loads(row['article_blocks_json'])
        saved = json.loads(row['article_translation_json'] or '[]') if row['article_translation_provider'] == provider.name else []
        blocks = []
        exhausted = False
        failed = False
        for index, block in enumerate(original):
            if not block.get('text') or row['language'] == 'zh':
                blocks.append(block); continue
            previous = saved[index] if index < len(saved) else {}
            digest = hashlib.sha256(block['text'].encode()).hexdigest()
            old_parts = previous.get('translated_parts', []) if previous.get('source_hash') == digest else []
            parts = list(old_parts)
            source_parts = chunks(block['text'])
            for text in source_parts[len(parts):]:
                if failed or exhausted: break
                try:
                    if result['calls'] >= cap: raise TranslationBudgetReached()
                    with store.connect() as db:
                        db.execute('BEGIN IMMEDIATE')
                        usage = db.execute('SELECT calls FROM translation_usage WHERE day=?', (day,)).fetchone()
                        if (usage[0] if usage else 0) >= total_cap: raise TranslationBudgetReached()
                        db.execute('INSERT INTO translation_usage VALUES(?,1) ON CONFLICT(day) DO UPDATE SET calls=calls+1', (day,))
                    result['calls'] += 1
                    parts.append(provider.translate(text, row['language']))
                except TranslationBudgetReached:
                    exhausted = True; result['budget_exhausted'] = True
                except Exception:
                    failed = True
            complete = len(parts) == len(source_parts)
            translated = {**block, 'text': ''.join(parts) if complete else block['text'],
                          'source_hash': digest, 'translated_parts': parts, 'translated': complete}
            # Keep source links and captions; don't pretend untranslated passages are Chinese.
            blocks.append(translated)
        complete = all(b.get('translated', True) for b in blocks)
        with store.connect() as db:
            db.execute('UPDATE content SET article_translation_json=?,article_translation_hash=?,article_translation_provider=?,article_translation_at=? WHERE id=? AND article_hash=?',
                       (json.dumps(blocks, ensure_ascii=False), target_hash if complete else None, provider.name, now(), row['id'], row['article_hash']))
        result['translated' if complete else 'failed' if failed else 'partial'] += 1
        if exhausted: break
    return result
