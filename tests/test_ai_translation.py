import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from tests import test_autonomous_translation as fixtures
from backend.ai_translation import GeminiTranslator, ServiceError, configuration, run_ai, source_units, reserve_requests


class AITranslationTests(unittest.TestCase):
    # Reuse source/body storage fixture, not the offline worker tests.
    setUp = fixtures.AutonomousTranslationTests.setUp
    def run_ai_worker(self, provider, **overrides):
        cfg = {**configuration(), 'request_interval_seconds': 0, **overrides}
        return run_ai(self.store, provider, self.root / 'ai-progress', self.root / 'ledger.json',
                      cfg=cfg, sleep=lambda seconds: None)

    def provider(self, callback=None):
        def transport(payload):
            doc = json.loads(payload['contents'][0]['parts'][0]['text'])
            selected = set(doc['requested_keys'])
            outputs = {u['key']: '译文：' + u['text'] for u in doc['original_units'] if u['key'] in selected}
            if callback:
                callback(doc)
            return {'modelVersion': 'gemini-2.5-flash-lite-test', 'usageMetadata': {'promptTokenCount': 400, 'candidatesTokenCount': 80},
                    'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': json.dumps({'outputs': outputs})}]}}]}
        return GeminiTranslator('unit-test-no-real-key', transport=transport)

    def test_api_single_pass_publishes_AI_and_reuses_finished_work(self):
        provider = self.provider()
        report = self.run_ai_worker(provider)
        self.assertEqual(report['translated'], [self.row['id']])
        self.assertEqual(report['requests'], 1)
        row = self.store.dataset('live')['content'][0]
        self.assertEqual(row['editorial_status'], 'translated')
        self.assertIsNone(row['editorial_review_model'])
        self.assertEqual(row['article_blocks_json'], self.row['article_blocks_json'])
        self.assertEqual(row['editorial_model'], 'gemini-2.5-flash-lite-test')
        self.assertEqual(self.run_ai_worker(provider)['requests'], 0)

    def test_request_limit_and_checkpoints_survive_new_worker(self):
        provider = self.provider()
        first = self.run_ai_worker(provider, source_characters_per_chunk=25, requests_per_run=1)
        self.assertEqual(first['status'], 'run_limit')
        state = json.loads((self.root / 'ai-progress' / (self.row['id'] + '.json')).read_text())
        self.assertEqual(len(state['outputs']), 1)
        called = []
        report = self.run_ai_worker(self.provider(lambda doc: called.extend(doc['requested_keys'])))
        self.assertEqual(report['translated'], [self.row['id']])
        self.assertEqual(report['resumed'], [self.row['id']])
        self.assertFalse(set(state['outputs']) & set(called))
        self.assertEqual(report['requests_today'], 2)

    def test_daily_quota_stops_without_calling_or_resetting_ledger(self):
        self.run_ai_worker(self.provider(), source_characters_per_chunk=25, requests_per_run=1)
        calls = []
        report = self.run_ai_worker(self.provider(lambda doc: calls.append(doc)), requests_per_day=1)
        self.assertEqual(report['status'], 'daily_limit')
        self.assertEqual(calls, [])
        self.assertEqual(report['requests_today'], 1)

    def test_429_stops_all_articles_and_persists_global_retry(self):
        def limited(payload):
            raise ServiceError(429, 7200)
        provider = GeminiTranslator('fixture', transport=limited)
        report = self.run_ai_worker(provider)
        self.assertEqual(report['status'], 'quota_wait')
        self.assertEqual(report['requests'], 1)
        next_run = self.run_ai_worker(self.provider())
        self.assertEqual(next_run['status'], 'quota_wait')
        self.assertEqual(next_run['requests'], 0)

    def test_source_change_and_existing_AI_race_cannot_be_overwritten(self):
        def change(doc):
            with self.store.connect() as db:
                db.execute("UPDATE content SET editorial_status='reviewed',editorial_title_zh='已有译文' WHERE id=?", (self.row['id'],))
        result = self.run_ai_worker(self.provider(change))
        self.assertEqual(result['stale'], [self.row['id']])
        self.assertEqual(self.store.dataset('live')['content'][0]['editorial_title_zh'], '已有译文')

    def test_long_source_split_is_exact_and_all_source_context_is_supplied(self):
        row = {**self.row, 'article_blocks_json': json.dumps([{'type': 'paragraph', 'text': 'Long context 2026. ' * 1800}])}
        original, units, keys = source_units(row, 2500)
        self.assertEqual(''.join(dict(units)[key] for key in keys['block:0:text']), original[0]['text'])
        self.assertGreater(len(keys['block:0:text']), 1)
        docs = []
        self.run_ai_worker(self.provider(lambda doc: docs.append(doc)), source_characters_per_chunk=25)
        self.assertGreater(len(docs), 1)
        self.assertEqual(docs[0]['original_units'], docs[1]['original_units'])
        self.assertNotEqual(docs[0]['requested_keys'], docs[1]['requested_keys'])

    def test_truncated_output_is_not_published_and_secret_is_not_in_payload(self):
        def truncated(payload):
            self.assertNotIn('fixture-secret-value', json.dumps(payload))
            return {'candidates': [{'finishReason': 'MAX_TOKENS'}]}
        report = self.run_ai_worker(GeminiTranslator('fixture-secret-value', transport=truncated))
        self.assertEqual(report['translated'], [])
        self.assertEqual(len(report['failed']), 1)
        self.assertIsNone(self.store.dataset('live')['content'][0]['editorial_blocks_json'])

    def test_broken_ledger_fails_closed_and_paid_mode_is_disabled(self):
        (self.root / 'ledger.json').write_text('{bad')
        with self.assertRaises(ValueError):
            self.run_ai_worker(self.provider())
        with self.assertRaises(ValueError):
            self.run_ai_worker(self.provider(), paid_activation=True)

    def test_crashed_runner_reservation_is_not_forgotten_and_unused_normal_slots_release(self):
        path = self.root / 'ledger.json'
        cfg = {**configuration(), 'requests_per_day': 5, 'requests_per_run': 3, 'request_interval_seconds': 0}
        first = reserve_requests(path, 'killed-run', cfg)
        self.assertEqual(first['allocated'], 3)
        # That runner never reaches finalization. A new run only gets 2 slots.
        second = reserve_requests(path, 'new-run', cfg)
        self.assertEqual(second['allocated'], 2)
        report = run_ai(self.store, self.provider(), self.root / 'ai-progress', path, cfg=cfg,
                        reservation_id='new-run', sleep=lambda seconds: None)
        self.assertEqual(report['requests'], 1)
        ledger = json.loads(path.read_text())
        self.assertEqual(ledger['days'][first['day']]['reserved_requests'], 3)
        self.assertEqual(ledger['days'][first['day']]['requests'], 1)
        self.assertEqual(reserve_requests(path, 'third-run', cfg)['allocated'], 1)
        self.assertEqual(reserve_requests(path, 'fourth-run', cfg)['allocated'], 0)
