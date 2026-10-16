import io
import json
import unittest
from urllib.error import HTTPError
from backend.gemini_access import inspect_access, DiagnosticGeminiTranslator
from backend.ai_translation import ServiceError, GeminiTranslator, configuration


class GeminiAccessTests(unittest.TestCase):
    def test_inspection_is_get_only_paginates_and_exposes_no_key_or_raw_fields(self):
        calls = []
        def opener(request, timeout):
            calls.append(request)
            self.assertEqual(request.get_method(), 'GET')
            self.assertIsNone(request.data)
            self.assertNotIn('private-key', request.full_url)
            self.assertEqual(request.get_header('X-goog-api-key'), 'private-key')
            value = {'models': [{'name': 'models/gemini-example', 'supportedGenerationMethods': ['generateContent'],
                                 'raw_secret': 'private-key'}]}
            if len(calls) == 1:
                value['nextPageToken'] = 'second-page'
            return io.BytesIO(json.dumps(value).encode())
        report = inspect_access('private-key', 'gemini-example', opener)
        self.assertEqual(report['status'], 'model_available')
        self.assertEqual(len(calls), 2)
        self.assertEqual(report['generation_requests'], 0)
        self.assertNotIn('private-key', json.dumps(report))

    def test_missing_model_and_failed_auth_are_distinct_without_echoing_error_body(self):
        report = inspect_access('private-key', 'gemini-missing', lambda *a, **kw: io.BytesIO(b'{"models":[]}'))
        self.assertEqual(report['status'], 'configured_model_unavailable')
        def denied(*args, **kwargs):
            raise HTTPError('https://example.org/', 403, 'private-key', {}, io.BytesIO(b'private-key'))
        report = inspect_access('private-key', 'gemini-missing', denied)
        self.assertEqual(report['http_status'], 403)
        self.assertNotIn('private-key', json.dumps(report))
        self.assertEqual(inspect_access('', 'gemini-missing')['status'], 'needs_configuration')

    def test_generation_diagnostic_redacts_key_and_preserves_http_status(self):
        key = 'fixture-private-key'
        def denied(request, timeout):
            self.assertEqual(request.get_method(), 'POST')
            self.assertNotIn(key, request.full_url)
            body = json.dumps({'error': {'message': 'Model missing; key=' + key}}).encode()
            raise HTTPError(request.full_url, 404, '', {}, io.BytesIO(body))
        provider = DiagnosticGeminiTranslator(key, configuration(), denied)
        with self.assertRaises(ServiceError):
            provider.request({'contents': []})
        self.assertEqual(provider.error_detail['http_status'], 404)
        self.assertEqual(provider.error_detail['category'], 'model_not_found')
        self.assertNotIn(key, json.dumps(provider.error_detail))

    def test_production_preserves_capacity_evidence_without_echoing_secrets_or_prompt(self):
        body = {'error': {'code': 503, 'status': 'UNAVAILABLE',
                         'message': 'This model is currently experiencing high demand. key=fixture-private-key; prompt=private-source',
                         'details': [{'metadata': {'project': 'private-account'}}]}}
        def unavailable(request, timeout):
            raise HTTPError(request.full_url, 503, '', {'Retry-After': '180'},
                            io.BytesIO(json.dumps(body).encode()))
        provider = GeminiTranslator('fixture-private-key', cfg=configuration())
        provider.opener = unavailable
        with self.assertRaises(ServiceError) as raised:
            provider.request({'contents': []})
        self.assertEqual(raised.exception.retry_seconds, 180)
        self.assertEqual(raised.exception.detail, {'http_status': 503, 'api_status': 'UNAVAILABLE',
                                                  'category': 'capacity_unavailable', 'message_evidence': 'high demand'})
        for secret in ('fixture-private-key', 'private-source', 'private-account'):
            self.assertNotIn(secret, json.dumps(raised.exception.detail))

    def test_unknown_or_malformed_error_does_not_invent_overload_or_discard_status(self):
        for body in [b'not-json', b'[]', b'{"error": []}',
                     b'{"error":{"status":"UNAVAILABLE","message":"internal routing error"}}']:
            def unavailable(request, timeout):
                raise HTTPError(request.full_url, 503, '', {}, io.BytesIO(body))
            provider = DiagnosticGeminiTranslator('fixture', configuration(), unavailable)
            with self.assertRaises(ServiceError) as raised:
                provider.request({})
            self.assertEqual(raised.exception.status, 503)
            self.assertNotEqual(raised.exception.detail['category'], 'capacity_unavailable')
            self.assertNotIn('message_evidence', raised.exception.detail)

    def test_quota_key_location_and_model_errors_remain_distinct(self):
        for code, message, category in [(429, 'You exceeded your current quota', 'quota_exceeded'),
                                        (403, 'Your API key was reported as leaked.', 'key_reported_leaked'),
                                        (400, 'API key not valid. Please pass a valid API key.', 'invalid_api_key'),
                                        (400, 'User location is not supported for the API use.', 'unsupported_location'),
                                        (404, 'The model is not found for API version v1beta', 'model_not_found')]:
            def denied(request, timeout):
                raise HTTPError(request.full_url, code, '', {},
                                io.BytesIO(json.dumps({'error': {'message': message}}).encode()))
            provider = DiagnosticGeminiTranslator('fixture', configuration(), denied)
            with self.assertRaises(ServiceError) as raised: provider.request({})
            self.assertEqual(raised.exception.detail['category'], category)
