import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.error import HTTPError
from backend.storage import Store
from backend.ingestion import run_ingestion


class SourceResilienceTests(unittest.TestCase):
    def test_failed_sibling_does_not_erase_successfully_fetched_new_news(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'config').mkdir()
            source = {'id': 'multi', 'name': 'Multi', 'language': 'en', 'channels': ['film'],
                      'source_type': 'media', 'homepage_url': 'https://example.org', 'enabled': True,
                      'access_status': 'reviewed', 'access_method': 'rss', 'adapter': 'rss',
                      'verified_at': '2026-10-14',
                      'feed_url': 'https://example.org/first',
                      'pages': [{'url': 'https://example.org/first'}, {'url': 'https://example.org/second'}]}
            (root / 'config/sources.json').write_text(json.dumps({'sources': [source]}))
            store = Store(root / 'news.db')
            def fetch(url):
                if url.endswith('second'): raise HTTPError(url, 503, 'Unavailable', None, None)
                return b'<rss><channel><item><title>European Film Awards 2026 winners</title><link>https://example.org/awards</link></item></channel></rss>'
            with patch('backend.ingestion.ROOT', root):
                result = run_ingestion(store, fetcher=fetch)[0]
            self.assertEqual(result['status'], 'partial')
            self.assertEqual(result['inserted'], 1)
            self.assertEqual(len(store.dataset('live')['content']), 1)
            state = next(s for s in store.source_status() if s['id'] == 'multi')
            self.assertEqual(state['last_run']['status'], 'failed')
            self.assertEqual(state['last_run']['inserted_count'], 1)
            self.assertIsNone(state['last_success_at'])
