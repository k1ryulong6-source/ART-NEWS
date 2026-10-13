"""Cached machine translation of public titles/excerpts; separate from AI summaries."""
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from .storage import now


class TranslationBudgetReached(Exception):
    pass


class PublicGoogleTranslator:
    name = 'google-public'

    def translate(self, text, language):
        query = urlencode({'client': 'gtx', 'sl': language if language in ('en', 'ja', 'fr', 'es', 'pt', 'de', 'ko') else 'auto', 'tl': 'zh-CN', 'dt': 't', 'q': text})
        request = Request('https://translate.googleapis.com/translate_a/single?' + query, headers={'User-Agent': 'CultureDesk/0.6'})
        with urlopen(request, timeout=15) as response:
            raw = response.read(100001)
            if len(raw) > 100000:
                raise ValueError('翻译响应过大')
            data = json.loads(raw)
        result = ''.join(part[0] or '' for part in data[0]).strip()
        if not result or len(result) > 2000:
            raise ValueError('翻译结果为空或过长')
        return result


def input_hash(row, provider):
    return hashlib.sha256(json.dumps([provider, row['title_original'], row.get('excerpt_original') or '', row['language']], ensure_ascii=False).encode()).hexdigest()


def run_translation(store, provider=None, daily_limit=None, workers=3):
    kind = os.getenv('TRANSLATION_PROVIDER', 'google-public')
    if provider is None and kind == 'disabled':
        return {'provider': 'disabled', 'translated': 0, 'failed': 0}
    if provider is None and kind != 'google-public':
        raise ValueError('未知翻译服务')
    provider = provider or PublicGoogleTranslator()
    limit = max(0, min(1200, int(daily_limit if daily_limit is not None else os.getenv('TRANSLATION_DAILY_LIMIT', '1000'))))
    day = datetime.now(timezone.utc).date().isoformat()
    with store.connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS translation_usage(day TEXT PRIMARY KEY, calls INTEGER NOT NULL)')
        rows = [dict(r) for r in db.execute("SELECT * FROM content WHERE is_demo=0 AND language!='zh' ORDER BY published_at DESC")]
    rows = [r for r in rows if r.get('translation_input_hash') != input_hash(r, provider.name)]
    def reserve():
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            usage = db.execute('SELECT calls FROM translation_usage WHERE day=?', (day,)).fetchone()
            if (usage[0] if usage else 0) >= limit:
                raise TranslationBudgetReached()
            db.execute('INSERT INTO translation_usage VALUES(?,1) ON CONFLICT(day) DO UPDATE SET calls=calls+1', (day,))
    def translate(row):
        try:
            reserve()
            title = provider.translate(row['title_original'][:600], row['language'])
            excerpt = None
            if row.get('excerpt_original'):
                reserve()
                excerpt = provider.translate(row['excerpt_original'], row['language'])
            with store.connect() as db:
                changed = db.execute("UPDATE content SET translated_title_zh=?,translated_excerpt_zh=?,translation_provider=?,translation_status=?,translation_input_hash=?,translation_generated_at=? WHERE id=? AND title_original=? AND coalesce(excerpt_original,'')=?", (title, excerpt, provider.name, 'translated' if excerpt else 'title_only', input_hash(row, provider.name), now(), row['id'], row['title_original'], row.get('excerpt_original') or '')).rowcount
            return 'translated' if changed else 'changed_during_request'
        except TranslationBudgetReached:
            return 'budget_exhausted'
        except Exception:
            # A network failure preserves previous translations and source data.
            return 'failed'
    counts = {'provider': provider.name, 'translated': 0, 'failed': 0, 'budget_exhausted': 0, 'changed_during_request': 0}
    # Bounded groups let a quota stop the queue without launching more requests.
    with ThreadPoolExecutor(max_workers=max(1, min(4, workers))) as pool:
        for start in range(0, len(rows), 12):
            for status in pool.map(translate, rows[start:start + 12]):
                counts[status] += 1
            if counts['budget_exhausted']:
                break
    return counts
