import json
import threading
import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from backend.ai_pool import reserve_pool, run_pool, continue_today
from backend.ai_translation import GeminiTranslator, ServiceError, configuration
from backend.articles import collect_articles
from backend.ingestion import content_record
from tests import test_autonomous_translation as fixtures


class AIPoolTests(unittest.TestCase):
    setUp = fixtures.AutonomousTranslationTests.setUp

    def setup_pool(self, *, second_article=False, env=None, **limits):
        self.cfg = {**configuration(), 'request_interval_seconds': 0, 'transient_retry': {**configuration().get('transient_retry', {}), 'inline_retries_per_run': 0}, **limits}
        self.env = {'GEMINI_API_KEY': 'first-test-key', 'GEMINI_API_KEY_SECONDARY': 'second-test-key'} if env is None else env
        (self.root / 'data').mkdir(exist_ok=True)
        if second_article:
            source = {'id': 'film-stage', 'language': 'en', 'channels': ['film'], 'source_type': 'media'}
            self.store.ingest_records([content_record(source, 'Second festival 2027',
                'https://thefilmstage.com/second', excerpt='A different festival.')], [], [])
            collect_articles(self.store, 2, getter=lambda u, s: ('<div class="entry-content"><p>' +
                'Artists gather in 2027. ' * 15 + '</p></div>', u))

    def provider(self, project, callback=None):
        def transport(payload):
            document = json.loads(payload['contents'][0]['parts'][0]['text'])
            outputs = {u['key']: '译文：' + u['text'] for u in document['original_units']
                       if u['key'] in document['requested_keys']}
            if callback:
                callback(project['id'], document, outputs)
            return {'modelVersion': 'test-model', 'usageMetadata': {'promptTokenCount': 200, 'candidatesTokenCount': 80},
                    'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': json.dumps({'outputs': outputs})}]}}]}
        return GeminiTranslator(project['key'], cfg=project['cfg'], transport=transport)

    def execute(self, factory=None, attempt='test:1', **options):
        reserve_pool(attempt, root=self.root, cfg=self.cfg, environ=self.env)
        return run_pool(self.store, attempt, root=self.root, cfg=self.cfg, environ=self.env,
                        provider_factory=factory or self.provider, worker_options={'sleep': lambda _: None}, **options)

    def test_projects_run_concurrently_on_disjoint_articles_and_reuse_completed_work(self):
        self.setup_pool(second_article=True)
        barrier = threading.Barrier(2)
        calls = []
        def observe(identity, document, outputs):
            calls.append((identity, document['source_url']))
            barrier.wait(timeout=5)
        report = self.execute(lambda p: self.provider(p, observe))
        self.assertEqual(len(report['translated']), 2)
        self.assertEqual(report['requests'], 2)
        self.assertEqual(len({url for _, url in calls}), 2)
        self.assertEqual({identity for identity, _ in calls}, {'primary', 'secondary'})
        self.assertEqual(report['daily_request_limit'], 1000)
        self.assertNotIn('first-test-key', json.dumps(report))
        self.assertNotIn('second-test-key', json.dumps(report))
        for filename in ('ai-translation-ledger.json', 'ai-translation-ledger-secondary.json'):
            ledger = json.loads((self.root / 'data' / filename).read_text())
            self.assertEqual(ledger['reservations']['test:1']['status'], 'closed')
            self.assertEqual(sum(day['requests'] for day in ledger['days'].values()), 1)
        self.assertEqual(self.execute(attempt='test:2')['requests'], 0)

    def test_unconfigured_secondary_makes_no_calls_and_creates_no_ledger(self):
        self.setup_pool(env={'GEMINI_API_KEY': 'first-test-key'})
        report = self.execute()
        self.assertEqual(report['configured_projects'], 1)
        self.assertEqual(report['projects'][1]['status'], 'not_configured')
        self.assertEqual(report['translated'], [self.row['id']])
        self.assertFalse((self.root / 'data/ai-translation-ledger-secondary.json').exists())

    def test_duplicate_key_cannot_create_another_quota(self):
        self.setup_pool(env={'GEMINI_API_KEY': 'same-key', 'GEMINI_API_KEY_SECONDARY': 'same-key'})
        report = self.execute()
        self.assertEqual(report['daily_request_limit'], 500)
        self.assertEqual(report['projects'][1]['status'], 'duplicate_key')
        self.assertEqual(report['requests'], 1)
        self.assertFalse((self.root / 'data/ai-translation-ledger-secondary.json').exists())

    def test_503_is_project_local_and_other_project_takes_remaining_article_next_batch(self):
        self.check_project_error_isolation(503, 'service_wait')

    def test_short_failure_retries_only_its_project_while_other_finishes(self):
        self.setup_pool(second_article=True, transient_retry={
            **configuration()['transient_retry'], 'inline_retries_per_run': 2, 'jitter_seconds': 0})
        attempts = {'primary': 0, 'secondary': 0}
        def factory(project):
            good = self.provider(project)
            def transport(payload):
                attempts[project['id']] += 1
                if project['id'] == 'primary' and attempts['primary'] == 1:
                    raise ServiceError(503)
                return good.transport(payload)
            return GeminiTranslator(project['key'], cfg=project['cfg'], transport=transport)
        report = self.execute(factory)
        self.assertEqual(len(report['translated']), 2)
        self.assertEqual(attempts, {'primary': 2, 'secondary': 1})
        self.assertEqual(report['requests'], 3)
        self.assertEqual(report['inline_service_retries'], 1)
        self.assertEqual(report['service_failures'][0]['project'], 'primary')
        self.assertEqual(report['projects'][1]['inline_service_retries'], 0)

    def test_429_is_project_local_and_preserves_both_request_counts(self):
        self.check_project_error_isolation(429, 'quota_wait')

    def check_project_error_isolation(self, code, expected_status):
        self.setup_pool(second_article=True)
        def factory(project):
            if project['id'] == 'primary':
                def unavailable(*args): raise ServiceError(code)
                return GeminiTranslator(project['key'], cfg=project['cfg'], transport=unavailable)
            return self.provider(project)
        first = self.execute(factory)
        self.assertEqual(first['status'], 'partial_failure')
        self.assertEqual(len(first['translated']), 1)
        second = self.execute(attempt='test:2')
        self.assertEqual(second['requests'], 1)
        self.assertEqual(len(second['translated']), 1)
        primary, secondary = second['projects']
        self.assertEqual((primary['status'], primary['requests']), (expected_status, 0))
        self.assertEqual(len(secondary['translated']), 1)
        self.assertNotEqual(first['translated'], second['translated'])

    def test_shared_git_checkpoint_serializes_files_while_both_workers_infer(self):
        self.setup_pool(second_article=True, source_characters_per_chunk=25)
        lock = threading.RLock()
        calls = []
        def checkpoint():
            with lock:
                for filename in ('ai-translation-ledger.json', 'ai-translation-ledger-secondary.json'):
                    data = json.loads((self.root / 'data' / filename).read_text())
                    self.assertTrue(all(d.get('reserved_requests', 0) >= 0 for d in data['days'].values()))
                for path in (self.root / 'data/ai-translation-progress').glob('*.json'):
                    self.assertIsInstance(json.loads(path.read_text())['outputs'], dict)
                calls.append(True)
        report = self.execute(checkpoint_sink=checkpoint, io_lock=lock)
        self.assertEqual(len(report['translated']), 2)
        self.assertGreater(len(calls), 2)

    def test_old_primary_usage_and_reservations_survive_secondary_budget(self):
        self.setup_pool()
        day = datetime.now(ZoneInfo('America/Los_Angeles')).date().isoformat()
        path = self.root / 'data/ai-translation-ledger.json'
        original = {'schema_version': 1, 'days': {day: {'requests': 500, 'reserved_requests': 0,
                    'input_tokens': 12345, 'output_tokens': 6789, 'unknown_usage_requests': 2}}, 'reservations': {}}
        path.write_text(json.dumps(original))
        report = self.execute()
        self.assertEqual(report['projects'][0]['status'], 'daily_limit')
        self.assertEqual(report['projects'][0]['requests'], 0)
        self.assertEqual(report['projects'][1]['translated'], [self.row['id']])
        self.assertEqual(json.loads(path.read_text())['days'], original['days'])

    def test_broken_primary_ledger_fails_closed_without_blocking_secondary(self):
        self.setup_pool()
        path = self.root / 'data/ai-translation-ledger.json'
        path.write_text('{broken ledger')
        report = self.execute()
        self.assertEqual(report['projects'][0]['status'], 'failed')
        self.assertEqual(report['projects'][1]['translated'], [self.row['id']])
        self.assertEqual(path.read_text(), '{broken ledger')
        self.assertIsNone(report['requests'])

    def test_valid_partial_units_transfer_between_projects_without_retranslation(self):
        self.setup_pool(env={'GEMINI_API_KEY': 'first-test-key'})
        def broken(identity, document, outputs): outputs['block:0:text:0'] = '缺少原文数字的译文'
        first = self.execute(lambda p: self.provider(p, broken))
        self.assertEqual(len(first['failed']), 1)
        path = self.root / 'data/ai-translation-progress' / (self.row['id'] + '.json')
        state = json.loads(path.read_text())
        self.assertEqual(set(state['outputs']), {'title:0', 'excerpt:0'})
        state['retry_after'] = '2000-01-01T00:00:00+00:00'
        path.write_text(json.dumps(state))
        self.env = {'GEMINI_API_KEY_SECONDARY': 'second-test-key'}
        requested = []
        second = self.execute(lambda p: self.provider(p, lambda i,d,o: requested.extend(d['requested_keys'])), attempt='test:2')
        self.assertEqual(requested, ['block:0:text:0'])
        self.assertEqual(second['translated'], [self.row['id']])

    def test_no_credentials_is_explicitly_not_configured(self):
        self.setup_pool(env={})
        report = self.execute()
        self.assertEqual(report['status'], 'needs_configuration')
        self.assertEqual(report['requests'], 0)
        self.assertEqual(report['daily_request_limit'], 0)

    def test_drain_only_chains_useful_work_on_the_authorized_quota_day(self):
        cfg = {'drain_until_quota_day': '2026-10-15'}
        instant = datetime(2026, 10, 16, 6, tzinfo=timezone.utc)
        lane = {'status': 'run_limit', 'requests': 20, 'requests_today': 100, 'daily_request_limit': 500}
        self.assertTrue(continue_today(cfg, [lane], 20, instant))
        # A fast batch can reach its article count before its time budget.
        self.assertTrue(continue_today(cfg, [{**lane, 'status': 'completed'}], 20, instant))
        self.assertTrue(continue_today(cfg, [{**lane, 'status': 'partial_failure'}], 20, instant))
        self.assertFalse(continue_today(cfg, [lane], 0, instant))
        self.assertFalse(continue_today(cfg, [{**lane, 'requests': 0}], 20, instant))
        self.assertFalse(continue_today(cfg, [{**lane, 'status': 'service_wait'}], 20, instant))
        self.assertFalse(continue_today(cfg, [{**lane, 'requests_today': 500}], 20, instant))
        self.assertFalse(continue_today(cfg, [lane], 20, datetime(2026, 10, 16, 8, tzinfo=timezone.utc)))
