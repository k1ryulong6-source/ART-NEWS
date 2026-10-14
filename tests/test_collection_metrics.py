import json
import runpy
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from backend.storage import ROOT


class CollectionMetricsTests(unittest.TestCase):
    def test_restore_is_not_new_and_repeated_run_is_not_counted_twice(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'data').mkdir()
            script = ROOT / 'scripts/record_collection_metrics.py'
            path = root / 'data/live.json'
            old = {'id': 'existing', 'last_run': {'started_at': '2026-10-13T00:00:00+00:00',
                    'finished_at': '2026-10-13T00:01:00+00:00', 'inserted_count': 500, 'status': 'success'}}
            path.write_text(json.dumps({'source_status': [old]}))
            def run(initialize=False):
                with patch('backend.storage.ROOT', root), patch('sys.argv', ['metrics'] + (['--initialize'] if initialize else [])):
                    runpy.run_path(str(script), run_name='metrics_test')
            run(True)
            run()
            self.assertEqual(json.loads((root / 'data/collection-metrics.json').read_text())['days'], {})
            new = {'id': 'new-source', 'last_run': {'started_at': '2026-10-14T00:00:00+00:00',
                   'finished_at': '2026-10-14T00:01:00+00:00', 'inserted_count': 80, 'status': 'success'}}
            path.write_text(json.dumps({'source_status': [old, new]}))
            run()
            run()
            day = json.loads((root / 'data/collection-metrics.json').read_text())['days']['2026-10-14']
            self.assertEqual(day['new_records'], 80)
            self.assertEqual(day['first_source_run_records'], 80)
            self.assertEqual(day['source_runs'], 1)
