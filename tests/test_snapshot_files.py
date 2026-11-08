import copy
import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.snapshot_files import read_snapshot, write_snapshot, encoded


class SnapshotFileTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / 'data/live.json'
        self.data = {'schema_version': 1, 'snapshot_at': '2026-11-08T00:00:00Z',
                     'content': [{'id': 'live-' + f'{i:024x}', 'article_hash': str(i),
                                  'article_blocks_json': json.dumps([{'type': 'paragraph', 'text': '原文 ' + str(i)}]),
                                  'editorial_blocks_json': '译文、引文、数字 2026', 'editorial_model': 'original-model'}
                                 for i in range(24)],
                     'events': [{'id': 'event-one', 'date': '2026-11-09'}],
                     'source_status': [{'id': 'source', 'status': 'success'}],
                     'editorial_usage': [{'day': '2026-11-08', 'calls': 17}]}

    def test_legacy_and_sharded_roundtrips_preserve_every_field_order_and_identity(self):
        self.data['content'].reverse()
        for threshold in (1_000_000, 0):
            before = copy.deepcopy(self.data)
            write_snapshot(self.path, self.data, legacy_bytes=threshold, shard_bytes=700)
            self.assertEqual(read_snapshot(self.path), before)
            self.assertEqual(self.data, before)
        manifest = json.loads(self.path.read_bytes())
        self.assertNotIn('content', manifest)
        self.assertTrue(all(p['bytes'] <= 700 for p in manifest['snapshot_storage']['parts']))

    def test_missing_corrupt_or_incomplete_parts_fail_closed(self):
        write_snapshot(self.path, self.data, legacy_bytes=0)
        original = self.path.read_bytes()
        manifest = json.loads(original); part = manifest['snapshot_storage']['parts'][0]
        file = self.path.parent / part['path']; raw = file.read_bytes()
        file.unlink()
        with self.assertRaises(FileNotFoundError): read_snapshot(self.path)
        file.write_bytes(raw + b' ')
        with self.assertRaisesRegex(ValueError, 'integrity'): read_snapshot(self.path)
        file.write_bytes(raw)
        manifest['snapshot_storage']['content_order'].pop()
        self.path.write_bytes(encoded(manifest))
        with self.assertRaisesRegex(ValueError, 'coverage'): read_snapshot(self.path)

    def test_duplicate_ids_unsafe_paths_and_unknown_versions_are_rejected(self):
        duplicate = copy.deepcopy(self.data); duplicate['content'].append(duplicate['content'][0])
        with self.assertRaisesRegex(ValueError, 'duplicate'): write_snapshot(self.path, duplicate, legacy_bytes=0)
        write_snapshot(self.path, self.data, legacy_bytes=0)
        raw = self.path.read_bytes()
        for name in ('../private.json', '/etc/passwd', 'snapshot-content/../private.json'):
            manifest = json.loads(raw); manifest['snapshot_storage']['parts'][0]['path'] = name
            self.path.write_bytes(encoded(manifest))
            with self.assertRaisesRegex(ValueError, 'path'): read_snapshot(self.path)
        manifest = json.loads(raw); manifest['snapshot_storage']['format'] = 'unknown-v2'
        self.path.write_bytes(encoded(manifest))
        with self.assertRaisesRegex(ValueError, 'manifest'): read_snapshot(self.path)

    def test_updates_change_only_the_affected_bucket_and_remove_obsolete_parts(self):
        write_snapshot(self.path, self.data, legacy_bytes=0, shard_bytes=700)
        folder = self.path.parent / 'snapshot-content'
        before = {p.name: p.read_bytes() for p in folder.glob('*.json')}
        updated = copy.deepcopy(self.data); updated['content'][0]['editorial_blocks_json'] = '更新译文'
        write_snapshot(self.path, updated, legacy_bytes=0, shard_bytes=700)
        after = {p.name: p.read_bytes() for p in folder.glob('*.json')}
        bucket = hashlib.sha256(updated['content'][0]['id'].encode()).hexdigest()[:2]
        self.assertTrue(all(name.startswith(bucket) for name in set(before) | set(after)
                            if before.get(name) != after.get(name)))
        self.assertEqual(read_snapshot(self.path), updated)
        updated['content'] = updated['content'][:1]
        write_snapshot(self.path, updated, legacy_bytes=0, shard_bytes=700)
        manifest = json.loads(self.path.read_bytes())
        self.assertEqual(len(list(folder.glob('*.json'))), len(manifest['snapshot_storage']['parts']))

    def test_oversized_single_article_does_not_truncate_or_replace_existing_snapshot(self):
        write_snapshot(self.path, self.data)
        before = self.path.read_bytes()
        bad = copy.deepcopy(self.data); bad['content'][0]['article_text'] = '原' * 2000
        with self.assertRaisesRegex(ValueError, 'single_article'):
            write_snapshot(self.path, bad, legacy_bytes=0, shard_bytes=700)
        self.assertEqual(self.path.read_bytes(), before)

    def test_storage_restores_shards_to_a_fresh_database(self):
        from backend.storage import Store
        write_snapshot(self.path, {'content': [], 'events': [], 'content_events': []}, legacy_bytes=0)
        store = Store(self.path.parent / 'restore.db')
        self.assertEqual(store.restore_public_snapshot(self.path), 0)
