import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from backend.storage import Store
from backend.ingestion import content_record
from backend.articles import collect_articles
from backend.autonomous_translation import run_autonomous, machine_ready
from backend.offline_model import provider_name
from backend.coverage import translation_progress
from backend.presentation import browser_snapshot


class FixtureTranslator:
    name = provider_name()

    def __init__(self):
        self.calls = 0

    def split(self, text):
        return [text[offset:offset + 50] for offset in range(0, len(text), 50)]

    def translate(self, text, language):
        self.calls += 1
        return '译文：' + text


class AutonomousTranslationTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.store = Store(self.root / 'news.db')
        source = {'id': 'film-stage', 'name': 'Film Stage', 'homepage_url': 'https://thefilmstage.com',
                  'channels': ['film'], 'language': 'en', 'source_type': 'media', 'access_status': 'reviewed',
                  'access_method': 'rss', 'verified_at': '2026-10-13', 'enabled': True, 'adapter': 'rss'}
        self.store.register_sources([source])
        self.store.ingest_records([content_record(source, 'Festival 2026', 'https://thefilmstage.com/autonomous', excerpt='Festival introduction.')], [], [])
        html = '<div class="entry-content"><p>The festival starts in 2026 and tickets cost 600 yen. ' + 'Many artists discuss their work. ' * 6 + '</p></div>'
        collect_articles(self.store, 1, getter=lambda url, source: (html, url))
        self.row = self.store.dataset('live')['content'][0]
        self.store.save_bookmark('content', self.row['id'])
        self.directory = self.root / 'progress'

    def run_worker(self, provider, **limits):
        return run_autonomous(self.store, provider, self.directory, seconds=100, articles=5, **limits)

    def test_budget_checkpoint_resumes_and_completed_machine_copy_is_not_AI(self):
        provider = FixtureTranslator()
        first = self.run_worker(provider, characters=15)
        self.assertEqual(first['translated'], [])
        self.assertEqual(first['status'], 'character_budget')
        self.assertTrue((self.directory / (self.row['id'] + '.json')).exists())
        saved_calls = provider.calls
        second = self.run_worker(provider, characters=5000)
        self.assertEqual(second['translated'], [self.row['id']])
        self.assertEqual(second['resumed'], [self.row['id']])
        current = self.store.dataset('live')['content'][0]
        self.assertTrue(machine_ready(current))
        self.assertEqual(current['article_text'], self.row['article_text'])
        self.assertEqual(current['article_blocks_json'], self.row['article_blocks_json'])
        self.assertEqual(len(self.store.bookmarks()), 1)
        self.assertEqual(self.run_worker(provider, characters=5000)['units'], 0)
        self.assertGreater(provider.calls, saved_calls)
        progress = translation_progress({'content': [current]})
        self.assertEqual((progress['completed'], progress['machine_completed'], progress['without_chinese_body']), (0, 1, 0))
        transport = browser_snapshot({'content': [current]})['content'][0]
        self.assertTrue(transport['machine_translation_ready'])
        self.assertIn('article_translation_json', transport)

    def test_existing_AI_is_never_replaced_by_machine_translation(self):
        with self.store.connect() as db:
            db.execute("UPDATE content SET editorial_status='translated',editorial_title_zh='AI标题',editorial_blocks_json=?", ('[{"type":"paragraph","text":"AI全文"}]',))
        provider = FixtureTranslator()
        self.assertEqual(self.run_worker(provider, characters=5000)['translated'], [])
        self.assertEqual(provider.calls, 0)
        current = self.store.dataset('live')['content'][0]
        self.assertEqual(current['editorial_title_zh'], 'AI标题')
        self.assertIsNone(current['article_translation_hash'])

    def test_numeric_failure_defers_only_that_source_and_changed_source_resets_backoff(self):
        provider = FixtureTranslator()
        provider.translate = lambda text, language: '漏数字的译文'
        failed = self.run_worker(provider, characters=5000)
        self.assertEqual(len(failed['failed']), 1)
        self.assertFalse(machine_ready(self.store.dataset('live')['content'][0]))
        provider = FixtureTranslator()
        deferred = self.run_worker(provider, characters=5000)
        self.assertEqual(deferred['deferred'], [self.row['id']])
        self.assertEqual(provider.calls, 0)
        with self.store.connect() as db:
            db.execute("UPDATE content SET title_original='Festival 2027' WHERE id=?", (self.row['id'],))
        self.assertEqual(self.run_worker(provider, characters=5000)['translated'], [self.row['id']])

    def test_changed_source_during_translation_cannot_receive_a_stale_body(self):
        provider = FixtureTranslator()
        original_translate = provider.translate
        def race(text, language):
            with self.store.connect() as db:
                db.execute("UPDATE content SET article_hash='new-source-hash' WHERE id=?", (self.row['id'],))
            return original_translate(text, language)
        provider.translate = race
        result = self.run_worker(provider, characters=5000)
        self.assertEqual(result['stale'], [self.row['id']])
        self.assertIsNone(self.store.dataset('live')['content'][0]['article_translation_hash'])
