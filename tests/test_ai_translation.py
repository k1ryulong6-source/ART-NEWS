import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from datetime import datetime, timedelta, timezone
from tests import test_autonomous_translation as fixtures
from backend.ai_translation import GeminiTranslator, ServiceError, configuration, run_ai, source_units, reserve_requests


class AITranslationTests(unittest.TestCase):
    # Reuse source/body storage fixture, not the offline worker tests.
    setUp = fixtures.AutonomousTranslationTests.setUp
    def run_ai_worker(self, provider, **overrides):
        cfg = {**configuration(), 'request_interval_seconds': 0, 'transient_retry': {**configuration().get('transient_retry', {}), 'inline_retries_per_run': 0}, **overrides}
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

    def test_generation_controls_match_model_family_without_extra_review_or_calls(self):
        for model, expected in [('gemini-3.5-flash-lite', {'thinkingLevel': 'MINIMAL'}),
                                ('gemini-2.5-flash-lite', {'thinkingBudget': 0})]:
            observed = []
            def transport(payload):
                observed.append(payload['generationConfig']['thinkingConfig'])
                schema = payload['generationConfig']['responseJsonSchema']
                self.assertFalse(schema['additionalProperties'])
                self.assertEqual(schema['properties']['outputs']['required'], ['title'])
                return {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': '{"outputs":{"title":"标题"}}'}]}}]}
            provider = GeminiTranslator('fixture', transport=transport, cfg={**configuration(), 'model': model})
            provider.translate({'original_units': [{'key': 'title', 'text': 'Title'}]}, ['title'])
            self.assertEqual(observed, [expected])

    def test_failed_json_and_truncated_output_preserve_usage_without_publishing(self):
        for reason in ('STOP', 'MAX_TOKENS'):
            def malformed(payload):
                return {'usageMetadata': {'promptTokenCount': 200, 'candidatesTokenCount': 50, 'thoughtsTokenCount': 7},
                        'candidates': [{'finishReason': reason, 'content': {'parts': [{'text': '{bad json'}]}}]}
            result = self.run_ai_worker(GeminiTranslator('fixture', transport=malformed))
            self.assertEqual((result['input_tokens'], result['output_tokens']), (200, 57))
            self.assertEqual(result['unknown_usage_requests_today'], 0)
            self.assertEqual(result['translated'], [])
            self.assertIsNone(self.store.dataset('live')['content'][0]['editorial_blocks_json'])
            for path in (self.root / 'ai-progress').glob('*.json'):
                path.unlink()

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

    def test_one_failed_numeric_unit_does_not_discard_other_paid_outputs(self):
        requested = []
        def broken(payload):
            doc = json.loads(payload['contents'][0]['parts'][0]['text'])
            requested.extend(doc['requested_keys'])
            self.assertTrue(all('numeric_literals' in unit for unit in doc['original_units']))
            outputs = {u['key']: '译文：' + u['text'] for u in doc['original_units'] if u['key'] in doc['requested_keys']}
            outputs['block:0:text:0'] = '故意省略原文数字的无效输出。'
            return {'usageMetadata': {'promptTokenCount': 300, 'candidatesTokenCount': 100},
                    'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': json.dumps({'outputs': outputs})}]}}]}
        report = self.run_ai_worker(GeminiTranslator('fixture', transport=broken))
        self.assertEqual(len(report['failed']), 1)
        self.assertEqual(report['input_tokens'], 300)
        path = self.root / 'ai-progress' / (self.row['id'] + '.json')
        state = json.loads(path.read_text())
        self.assertEqual(set(state['outputs']), {'title:0', 'excerpt:0'})
        self.assertIsNone(self.store.dataset('live')['content'][0]['editorial_status'])
        # Simulate the next scheduled run after the existing per-article cooldown.
        state['retry_after'] = '2000-01-01T00:00:00+00:00'; path.write_text(json.dumps(state))
        called = []
        resumed = self.run_ai_worker(self.provider(lambda doc: called.extend(doc['requested_keys'])))
        self.assertEqual(called, ['block:0:text:0'])
        self.assertEqual(resumed['translated'], [self.row['id']])
        self.assertEqual(resumed['requests_today'], 2)

    def test_assembled_failure_only_removes_keys_of_the_failed_field(self):
        def broken(payload):
            doc = json.loads(payload['contents'][0]['parts'][0]['text'])
            outputs = {u['key']: '译文：' + u['text'] for u in doc['original_units'] if u['key'] in doc['requested_keys']}
            outputs['block:0:text:0'] = 'Changed English copy includes 2026 and 600, but no Chinese characters.'
            return {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': json.dumps({'outputs': outputs})}]}}]}
        result = self.run_ai_worker(GeminiTranslator('fixture', transport=broken))
        self.assertEqual(result['translated'], [])
        path = self.root / 'ai-progress' / (self.row['id'] + '.json')
        state = json.loads(path.read_text())
        self.assertEqual(set(state['outputs']), {'title:0', 'excerpt:0'})

    def test_headline_validation_retry_is_30_minutes_and_adopts_old_cooldown_once(self):
        with self.store.connect() as db:
            db.execute('UPDATE content SET published_at=? WHERE id=?',
                       (datetime.now(timezone.utc).isoformat(), self.row['id']))
        def bad(payload):
            doc = json.loads(payload['contents'][0]['parts'][0]['text'])
            outputs = {u['key']: '译文：' + u['text'] for u in doc['original_units'] if u['key'] in doc['requested_keys']}
            outputs['block:0:text:0'] = '缺失数字的译文'
            return {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': json.dumps({'outputs': outputs})}]}}]}
        result = self.run_ai_worker(GeminiTranslator('fixture', transport=bad))
        self.assertEqual(len(result['failed']), 1)
        path = self.root / 'ai-progress' / (self.row['id'] + '.json')
        state = json.loads(path.read_text())
        minutes = (datetime.fromisoformat(state['retry_after']) - datetime.now(timezone.utc)).total_seconds() / 60
        self.assertTrue(29 <= minutes <= 31)
        self.assertEqual(state['retry_policy'], 'headline')
        self.assertEqual(self.run_ai_worker(self.provider())['requests'], 0)
        # A pre-policy 6h cooldown on a newly promoted headline is adopted once.
        state.pop('retry_policy')
        state['retry_after'] = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
        path.write_text(json.dumps(state))
        requested = []
        resumed = self.run_ai_worker(self.provider(lambda doc: requested.extend(doc['requested_keys'])))
        self.assertEqual(requested, ['block:0:text:0'])
        self.assertEqual(resumed['translated'], [self.row['id']])

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

    def test_503_retry_does_not_pretend_the_daily_quota_is_exhausted(self):
        def unavailable(payload):
            raise ServiceError(503)
        first = self.run_ai_worker(GeminiTranslator('fixture', transport=unavailable))
        self.assertEqual(first['status'], 'service_wait')
        later = self.run_ai_worker(self.provider())
        self.assertEqual(later['status'], 'service_wait')
        self.assertEqual(later['error'], 'ai_http_503')
        self.assertEqual(later['requests'], 0)

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
        with self.assertRaises(ValueError):
            self.run_ai_worker(self.provider(), headline_retry_minutes=0)

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
