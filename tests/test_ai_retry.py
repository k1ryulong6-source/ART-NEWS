import json
import unittest
from datetime import datetime, timedelta, timezone
from urllib.error import URLError

from backend import ai_retry
from backend.ai_translation import configuration, run_ai, ServiceError, GeminiTranslator, reserve_requests
from tests import test_ai_translation as fixtures


class RetryPolicyTests(unittest.TestCase):
    def test_exponential_wait_persists_caps_and_obeys_server_header(self):
        cfg = {**configuration(), 'transient_retry': {**ai_retry.DEFAULTS, 'jitter_seconds': 0}}
        ledger = {}; instant = datetime(2026, 10, 16, 12, tzinfo=timezone.utc)
        waits = [ai_retry.schedule(ledger, cfg, 'primary', 'ai_http_503', instant=instant)['delay_seconds'] for _ in range(8)]
        self.assertEqual(waits, [60, 120, 240, 480, 960, 1800, 1800, 1800])
        server = ai_retry.schedule(ledger, cfg, 'primary', 'ai_http_503', 7200, instant)
        self.assertEqual(server['delay_seconds'], 7200)
        self.assertEqual(ledger['retry_after'], '2026-10-16T14:00:00+00:00')
        ai_retry.recovered(ledger)
        self.assertNotIn('service_retry', ledger)
        self.assertNotIn('retry_after', ledger)
        self.assertEqual(ai_retry.schedule(ledger, cfg, 'primary', 'ai_http_503')['consecutive_failures'], 1)

    def test_jitter_is_bounded_and_repeatable(self):
        cfg = configuration()
        a = ai_retry.schedule({}, cfg, 'primary', 'ai_http_503')
        b = ai_retry.schedule({}, cfg, 'primary', 'ai_http_503')
        self.assertEqual(a['delay_seconds'], b['delay_seconds'])
        self.assertTrue(60 <= a['delay_seconds'] <= 75)

    def test_retry_after_supports_http_date_and_seconds_without_shortening(self):
        instant = datetime(2026, 10, 16, 12, tzinfo=timezone.utc)
        self.assertEqual(ai_retry.retry_after_seconds('123', instant), 123)
        self.assertEqual(ai_retry.retry_after_seconds('Fri, 16 Oct 2026 12:10:00 GMT', instant), 600)
        self.assertEqual(ai_retry.retry_after_seconds('Fri, 16 Oct 2026 11:10:00 GMT', instant), 0)
        self.assertEqual(ai_retry.retry_after_seconds('invalid', instant), 0)

    def test_invalid_limits_fail_closed(self):
        for values in [{'inline_retries_per_run': 3}, {'initial_seconds': 0}, {'maximum_seconds': 99999}, {'jitter_seconds': True}]:
            with self.assertRaises(ValueError): ai_retry.configuration({'transient_retry': values})


class RetryWorkerTests(unittest.TestCase):
    setUp = fixtures.AITranslationTests.setUp
    provider = fixtures.AITranslationTests.provider

    def execute(self, provider, *, reservation=None, **limits):
        cfg = {**configuration(), 'request_interval_seconds': 0,
               'transient_retry': {**ai_retry.DEFAULTS, 'jitter_seconds': 0}, **limits}
        elapsed = [0]; waits = []
        def sleep(seconds):
            waits.append(seconds); elapsed[0] += seconds
        if reservation: reserve_requests(self.root / 'ledger.json', reservation, cfg)
        result = run_ai(self.store, provider, self.root / 'progress', self.root / 'ledger.json',
                        cfg=cfg, reservation_id=reservation, clock=lambda: elapsed[0], sleep=sleep)
        return result, waits

    def test_short_503_recovers_in_same_batch_and_each_attempt_counts(self):
        good = self.provider(); count = [0]
        def transport(payload):
            count[0] += 1
            if count[0] <= 2: raise ServiceError(503)
            return good.transport(payload)
        result, waits = self.execute(GeminiTranslator('fixture', transport=transport), reservation='run:1')
        self.assertEqual(result['translated'], [self.row['id']])
        self.assertEqual(result['requests'], 3)
        self.assertEqual(result['inline_service_retries'], 2)
        self.assertEqual([w for w in waits if w], [60, 120])
        self.assertEqual(result['unknown_usage_requests_today'], 2)
        ledger = json.loads((self.root / 'ledger.json').read_text())
        self.assertNotIn('service_retry', ledger)
        self.assertEqual(ledger['reservations']['run:1']['actual_requests'], 3)
        self.assertEqual(ledger['reservations']['run:1']['remaining'], 0)
        self.assertEqual(sum(v['reserved_requests'] for v in ledger['days'].values()), 0)

    def test_persistent_503_stops_after_two_retries_and_keeps_checkpoint(self):
        def bad(payload): raise ServiceError(503)
        result, waits = self.execute(GeminiTranslator('fixture', transport=bad))
        self.assertEqual(result['requests'], 3)
        self.assertEqual(result['status'], 'service_wait')
        self.assertEqual(len(result['service_failures']), 3)
        self.assertEqual(result['service_failures'][-1]['delay_seconds'], 240)
        self.assertFalse(result['service_failures'][-1]['inline_retry'])
        ledger = json.loads((self.root / 'ledger.json').read_text())
        self.assertEqual(ledger['service_retry']['consecutive_failures'], 3)
        checkpoint = self.root / 'progress' / (self.row['id'] + '.json')
        self.assertTrue(checkpoint.exists())
        again, _ = self.execute(self.provider())
        self.assertEqual(again['requests'], 0)
        self.assertEqual(again['retry_after'], ledger['retry_after'])

    def test_completed_units_not_requested_again_after_transient_failure(self):
        good = self.provider(); calls = []
        def transport(payload):
            doc = json.loads(payload['contents'][0]['parts'][0]['text']); calls.append(doc['requested_keys'])
            if len(calls) == 2: raise ServiceError(502)
            return good.transport(payload)
        result, waits = self.execute(GeminiTranslator('fixture', transport=transport), source_characters_per_chunk=25)
        self.assertEqual(result['translated'], [self.row['id']])
        self.assertEqual(result['inline_service_retries'], 1)
        self.assertEqual(calls[1], calls[2])
        self.assertFalse(set(calls[0]) & set(key for group in calls[1:] for key in group))

    def test_server_wait_429_auth_and_legacy_wait_are_never_bypassed(self):
        for code, seconds, status in [(503, 600, 'service_wait'), (429, 7200, 'quota_wait'), (403, 0, 'configuration_error')]:
            with self.subTest(code=code):
                (self.root / 'ledger.json').unlink(missing_ok=True)
                def blocked(payload): raise ServiceError(code, seconds)
                result, waits = self.execute(GeminiTranslator('fixture', transport=blocked))
                self.assertEqual((result['requests'], result['status']), (1, status))
                self.assertFalse(any(waits))
                self.assertGreaterEqual((datetime.fromisoformat(result['retry_after']) - datetime.now(timezone.utc)).total_seconds(), seconds - 2)
        # Old ledgers did not record whether Google supplied Retry-After.
        # Keep their remaining wait instead of guessing that it is safe to cut.
        ledger = json.loads((self.root / 'ledger.json').read_text())
        stamp = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        ledger.update(retry_status='service_wait', retry_error='ai_http_503', retry_after=stamp)
        (self.root / 'ledger.json').write_text(json.dumps(ledger))
        result, _ = self.execute(self.provider())
        self.assertEqual(result['requests'], 0)
        self.assertEqual(result['retry_after'], stamp)

    def test_retries_respect_request_daily_and_time_budgets(self):
        def bad(payload): raise ServiceError(504)
        for limits in [{'requests_per_run': 1}, {'requests_per_day': 1}, {'seconds_per_run': 120}]:
            with self.subTest(limits=limits):
                (self.root / 'ledger.json').unlink(missing_ok=True)
                result, waits = self.execute(GeminiTranslator('fixture', transport=bad), **limits)
                self.assertEqual(result['requests'], 1)
                self.assertEqual(result['inline_service_retries'], 0)
                self.assertFalse(any(waits))

    def test_network_timeout_uses_same_bounded_recovery(self):
        good = self.provider(); calls = [0]
        def transport(payload):
            calls[0] += 1
            if calls[0] == 1: raise URLError('fixture temporary network failure')
            return good.transport(payload)
        result, waits = self.execute(GeminiTranslator('fixture', transport=transport))
        self.assertEqual(result['requests'], 2)
        self.assertEqual(result['translated'], [self.row['id']])
        self.assertEqual(result['service_failures'][0]['error'], 'URLError')

    def test_safe_service_evidence_survives_inline_recovery_and_final_wait(self):
        detail = {'http_status': 503, 'api_status': 'UNAVAILABLE', 'category': 'capacity_unavailable',
                  'message_evidence': 'high demand'}
        good = self.provider(); calls = [0]
        def transient(payload):
            calls[0] += 1
            if calls[0] == 1: raise ServiceError(503, detail=detail)
            return good.transport(payload)
        result, _ = self.execute(GeminiTranslator('fixture', transport=transient))
        self.assertEqual(result['translated'], [self.row['id']])
        self.assertEqual(result['service_failures'][0]['provider_error'], detail)
        self.setUp()  # A fresh untranslated article for the persistent outage case.
        def down(payload): raise ServiceError(503, detail=detail)
        result, _ = self.execute(GeminiTranslator('fixture', transport=down), requests_per_run=1)
        self.assertEqual(result['error_detail'], detail)
        ledger = json.loads((self.root / 'ledger.json').read_text())
        self.assertEqual(ledger['service_retry']['provider_error'], detail)
        self.assertEqual(ledger['last_api_error']['category'], 'capacity_unavailable')
