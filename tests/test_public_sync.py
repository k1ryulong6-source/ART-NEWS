import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from backend.public_sync import push_public_update


class PublicSyncTests(unittest.TestCase):
    def git(self, root, *args):
        return subprocess.check_output(['git', *args], cwd=root, text=True, stderr=subprocess.PIPE)

    def write(self, root, name, value):
        path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False) + '\n')

    def commit(self, root, message):
        self.git(root, 'add', 'data', 'README.md')
        self.git(root, 'commit', '-m', message)

    def setUp(self):
        self.tmp = TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name); self.remote = self.base / 'remote.git'
        self.git(self.base, 'init', '--bare', '--initial-branch=main', str(self.remote))
        self.worker = self.base / 'worker'; self.editor = self.base / 'editor'
        self.git(self.base, 'clone', str(self.remote), str(self.worker))
        for key, value in [('user.name', 'Fixture'), ('user.email', 'fixture@example.org')]:
            self.git(self.worker, 'config', key, value)
        self.write(self.worker, 'data/live.json', {'content': [{'id': 'one', 'article_hash': 'base'}]})
        self.write(self.worker, 'data/acceptance.json', {'all_ready': False, 'stamp': 'base'})
        (self.worker / 'README.md').write_text('base')
        self.commit(self.worker, 'base'); self.git(self.worker, 'push', 'origin', 'main')
        self.git(self.base, 'clone', str(self.remote), str(self.editor))
        for key, value in [('user.name', 'Fixture'), ('user.email', 'fixture@example.org')]:
            self.git(self.editor, 'config', key, value)

    def changes(self, body_conflict=False):
        self.write(self.worker, 'data/live.json', {'content': [{'id': 'one', 'article_hash': 'base', 'editorial_title_zh': '已译'}]})
        self.write(self.worker, 'data/acceptance.json', {'all_ready': False, 'stamp': 'worker'})
        self.commit(self.worker, 'accepted work')
        (self.editor / 'README.md').write_text('new frontend code')
        self.write(self.editor, 'data/acceptance.json', {'all_ready': False, 'stamp': 'editor'})
        if body_conflict:
            self.write(self.editor, 'data/live.json', {'content': [{'id': 'one', 'article_hash': 'new-source'}]})
        self.commit(self.editor, 'editor change'); self.git(self.editor, 'push', 'origin', 'main')

    def regenerate(self, root, conflicts):
        self.assertIn('data/acceptance.json', conflicts)
        self.assertEqual(json.loads((root / 'data/live.json').read_text())['content'][0]['editorial_title_zh'], '已译')
        self.write(root, 'data/acceptance.json', {'all_ready': False, 'stamp': 'regenerated'})

    def test_real_rebase_regenerates_report_and_preserves_accepted_body_and_frontend(self):
        self.changes()
        result = push_public_update(self.worker, regenerate=self.regenerate)
        self.assertEqual(result['status'], 'pushed')
        saved = json.loads(self.git(self.remote, 'show', 'main:data/live.json'))
        self.assertEqual(saved['content'][0]['editorial_title_zh'], '已译')
        self.assertEqual(self.git(self.remote, 'show', 'main:README.md'), 'new frontend code')
        self.assertEqual(json.loads(Path(result['accepted_snapshot_archive']).read_text()), saved)

    def test_real_body_conflict_is_never_auto_overwritten_and_accepted_work_is_archived(self):
        self.changes(body_conflict=True)
        with self.assertRaisesRegex(RuntimeError, 'unresolved_public_data_conflict'):
            push_public_update(self.worker, regenerate=self.regenerate)
        saved = json.loads(self.git(self.remote, 'show', 'main:data/live.json'))
        self.assertEqual(saved['content'][0]['article_hash'], 'new-source')
        archive = json.loads((self.worker / 'runtime/public-update-evidence/accepted-public-snapshot.json').read_text())
        self.assertEqual(archive['content'][0]['editorial_title_zh'], '已译')

    def test_conflicting_quality_checks_are_archived_and_require_a_new_check(self):
        path = 'data/article-quality/live-' + 'a' * 24 + '.json'
        self.write(self.worker, path, {'status': 'base'})
        self.commit(self.worker, 'base proof'); self.git(self.worker, 'push', 'origin', 'main')
        self.git(self.editor, 'pull', '--ff-only')
        self.write(self.worker, path, {'status': 'passed'})
        self.write(self.worker, 'data/acceptance.json', {'stamp': 'worker'})
        self.commit(self.worker, 'worker proof')
        self.write(self.editor, path, {'status': 'issues'})
        self.commit(self.editor, 'editor proof'); self.git(self.editor, 'push', 'origin', 'main')
        def regenerate(root, conflicts): self.write(root, 'data/acceptance.json', {'all_ready': False})
        push_public_update(self.worker, regenerate=regenerate)
        self.assertFalse((self.worker / path).exists())
        self.assertEqual(len(list((self.worker / 'runtime/public-update-evidence').glob('*-stage*.json'))), 2)
