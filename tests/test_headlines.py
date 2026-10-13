import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from backend.headlines import load_headlines
from backend.daily_translation import prepare_queue


class HeadlineTests(unittest.TestCase):
    def test_stale_title_and_unreviewed_copy_do_not_publish(self):
        with TemporaryDirectory() as tmp:
            directory = Path(tmp)
            identifier = 'live-' + 'a' * 24
            pack = {'schema_version': 1, 'id': identifier, 'source_title': 'Old title',
                    'title_zh': '已校译标题', 'review': {'approved': True, 'issues': [], 'method': '对照原文校对'}}
            path = directory / (identifier + '.json')
            path.write_text(json.dumps(pack))
            snapshot = {'content': [{'id': identifier, 'title_original': 'New title'}]}
            self.assertEqual(load_headlines(snapshot, directory), {})
            pack['review']['approved'] = False
            path.write_text(json.dumps(pack))
            with self.assertRaises(ValueError):
                load_headlines(snapshot, directory)

    def test_event_title_requires_exact_linked_original_and_full_body_remains_pending(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); directory = root / 'headlines'; directory.mkdir()
            identifier = 'live-' + 'b' * 24
            row = {'id': identifier, 'title_original': 'Exhibition', 'language': 'en', 'source_id': 'museum'}
            pack = {'schema_version': 1, 'id': identifier, 'source_title': 'Exhibition',
                    'title_zh': '展览', 'review': {'approved': True, 'issues': [], 'method': '对照原文校对'}}
            (directory / (identifier + '.json')).write_text(json.dumps(pack))
            snapshot = {'content': [row], 'events': [{'id': 'exact', 'title_original': 'Exhibition'},
                                                    {'id': 'other', 'title_original': 'Other exhibition'}],
                        'content_events': [{'content_id': identifier, 'event_id': 'exact'},
                                           {'content_id': identifier, 'event_id': 'other'}]}
            titles = load_headlines(snapshot, directory)
            self.assertEqual(titles['exact']['title_zh'], '展览')
            self.assertNotIn('other', titles)
            result = prepare_queue(snapshot, root)
            queue = json.loads((root / 'translation-queue.json').read_text())
            self.assertEqual(queue['pending_headlines'], 0)
            self.assertEqual(queue['reviewed'], 0)
            row['title_original'] = 'Changed title'
            prepare_queue(snapshot, root)
            queue = json.loads((root / 'translation-queue.json').read_text())
            self.assertEqual(queue['pending_headlines'], 1)
            self.assertIsNone(queue['headlines_next'][0]['input_path'])
