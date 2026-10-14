import io
import json
import unittest
from urllib.error import HTTPError
from backend.gemini_access import inspect_access, DiagnosticGeminiTranslator
from backend.ai_translation import ServiceError, configuration


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
        self.assertIn('[redacted]', provider.error_detail['message'])
        self.assertNotIn(key, json.dumps(provider.error_detail))
