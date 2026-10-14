import copy
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from backend.babel_export import article_payload, export_articles


class BabelExportTests(unittest.TestCase):
    def setUp(self):
        self.row = {'id': 'live-' + 'a' * 24, 'source_id': 'one', 'title_original': 'Original title',
                    'language': 'ja', 'canonical_url': 'https://example.org/news', 'article_status': 'partial',
                    'article_hash': 'b' * 64, 'article_text': 'Original paragraph.\n\nQuotation.',
                    'article_blocks_json': json.dumps([{'type': 'paragraph', 'text': 'Original paragraph.'},
                        {'type': 'quote', 'text': 'Quotation.'}, {'type': 'image', 'url': 'https://example.org/photo.jpg', 'caption': 'Source caption', 'credit': 'Photographer'}]),
                    'editorial_status': 'translated', 'editorial_title_zh': '中文参考标题', 'editorial_model': 'actual-model',
                    'editorial_blocks_json': json.dumps([{'type': 'paragraph', 'text': '中文译文'}]),
                    'bookmarks': ['private'], 'editorial_draft_json': 'private-process', 'summary_zh': 'Not full text'}

    def test_original_language_body_images_and_reference_keep_separate_provenance(self):
        before = copy.deepcopy(self.row)
        result = article_payload(self.row, {'one': {'name': 'Publisher'}})
        self.assertEqual(self.row, before)
        self.assertEqual((result['title'], result['language'], result['text']),
                         ('Original title', 'ja', self.row['article_text']))
        self.assertEqual(result['blocks'][2]['credit'], 'Photographer')
        self.assertEqual(result['access'], 'public-partial')
        self.assertEqual(result['translation_zh']['kind'], 'ai-direct')
        self.assertEqual(result['translation_zh']['model'], 'actual-model')
        self.assertNotIn('bookmarks', result)
        self.assertNotIn('editorial_draft_json', result)

    def test_all_saved_articles_export_individually_and_missing_bodies_are_not_faked(self):
        with TemporaryDirectory() as tmp:
            missing = {**self.row, 'id': 'live-' + 'c' * 24, 'article_blocks_json': None, 'article_text': None}
            demo = {**self.row, 'id': 'demo', 'is_demo': True}
            self.assertEqual(export_articles({'content': [self.row, missing, demo]}, {'sources': [{'id': 'one'}]}, tmp), 1)
            directory = Path(tmp)
            self.assertEqual(json.loads((directory / 'index.json').read_text())['count'], 1)
            result = json.loads((directory / (self.row['id'] + '.json')).read_text())
            self.assertEqual(result['source_hash'], self.row['article_hash'])
            export_articles({'content': []}, {'sources': []}, tmp)
            self.assertEqual(len(list(directory.glob('live-*.json'))), 0)

    def test_body_above_babel_manual_limit_is_never_truncated(self):
        long = '原文保留。' * 10000
        row = {**self.row, 'article_text': long, 'article_blocks_json': json.dumps([{'type': 'paragraph', 'text': long}])}
        self.assertEqual(article_payload(row, {})['text'], long)
