import hashlib
import json
import unittest
from tempfile import TemporaryDirectory
from backend.articles import extract_article
from backend.quality_audit import inspect_cached, audit_quality, compare_public_markup


class QualityAuditTests(unittest.TestCase):
    def setUp(self):
        self.source = {'id': 'public', 'name': 'Public', 'enabled': True, 'source_type': 'media',
                       'homepage_url': 'https://example.org', 'article_selectors': ['.entry-content']}
        self.url = 'https://example.org/story'
        self.prose = 'A long public paragraph about a photographer and an exhibition with dates and quotations. ' * 4
        self.html = '<div class="entry-content"><p>' + self.prose + '</p><figure><img src="/image.jpg"><figcaption>A public caption</figcaption></figure></div>'
        self.row = {'id': 'first', 'source_id': 'public', 'title_original': 'Original title', 'canonical_url': self.url,
                    **extract_article(self.html, self.url, self.source)}

    def test_original_integrity_and_caption_omission_are_detected(self):
        self.assertEqual(inspect_cached(self.row), [])
        bad = {**self.row, 'article_hash': 'changed'}
        self.assertIn('source_hash_mismatch', inspect_cached(bad))
        blocks = json.loads(self.row['article_blocks_json']); blocks[-1]['caption'] = ''
        fields = {**self.row, 'article_blocks_json': json.dumps(blocks)}
        self.assertIn('public_image_caption_not_extracted', compare_public_markup(self.html, self.url, self.source, fields))

    def test_omitted_visible_paragraph_fails_and_widget_text_is_not_required(self):
        extra = '<p>' + 'A second meaningful public paragraph discusses the artist and her work. ' * 3 + '</p>'
        html = self.html.replace('</div>', extra + '<aside><p>Unrelated</p></aside></div>')
        self.assertIn('public_paragraphs_not_extracted:1', compare_public_markup(html, self.url, self.source, self.row))

    def test_bounded_runs_resume_without_refetching_passes(self):
        other = {**self.row, 'id': 'second'}
        snapshot = {'content': [self.row, other]}
        calls = []
        def get(url, source):
            calls.append(url); return self.html, url
        with TemporaryDirectory() as directory:
            first = audit_quality(snapshot, {'sources': [self.source]}, directory, limit=1, getter=get)
            self.assertEqual(first['remote_verified'], 1)
            self.assertFalse(first['complete'])
            second = audit_quality(snapshot, {'sources': [self.source]}, directory, limit=1, getter=get)
            self.assertTrue(second['complete'])
            self.assertEqual(len(calls), 2)

    def test_network_failure_never_becomes_verified_or_changes_original(self):
        original = dict(self.row)
        with TemporaryDirectory() as directory:
            def fail(*args): raise ValueError('http_403')
            result = audit_quality({'content': [self.row]}, {'sources': [self.source]}, directory, getter=fail)
        self.assertFalse(result['complete'])
        self.assertEqual(result['remote_unresolved'][0]['status'], 'unavailable')
        self.assertEqual(self.row, original)
