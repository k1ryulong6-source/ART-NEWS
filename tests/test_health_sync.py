import json
import subprocess
import unittest
from backend.health_sync import push_health_update
from tests import test_public_sync as fixtures


class HealthSyncTests(unittest.TestCase):
    setUp = fixtures.PublicSyncTests.setUp
    git = fixtures.PublicSyncTests.git
    write = fixtures.PublicSyncTests.write
    commit = fixtures.PublicSyncTests.commit

    def reports(self):
        self.write(self.worker, 'data/automation-health.json', {'status': 'base'})
        self.commit(self.worker, 'base monitoring evidence')
        self.git(self.worker, 'push', 'origin', 'main')
        self.git(self.editor, 'pull', '--ff-only')
        self.write(self.worker, 'data/automation-health.json', {'status': 'healthy', 'stamp': 'worker'})
        self.commit(self.worker, 'own report only')

    def test_real_push_race_recomputes_only_health_and_preserves_new_article_data(self):
        self.reports(); raced = [False]; regenerated = []
        def runner(args, **kwargs):
            if args[:2] == ['git', 'push'] and not raced[0]:
                raced[0] = True
                self.write(self.editor, 'data/live.json', {'content': [{'id': 'one', 'article_hash': 'new-public-original'}]})
                self.write(self.editor, 'data/automation-health.json', {'stamp': 'another-monitor'})
                self.commit(self.editor, 'new collection and concurrent report')
                self.git(self.editor, 'push', 'origin', 'main')
            return subprocess.run(args, **kwargs)
        def regenerate(root):
            original = json.loads((root / 'data/live.json').read_text())
            self.assertEqual(original['content'][0]['article_hash'], 'new-public-original')
            regenerated.append(True)
            self.write(root, 'data/automation-health.json', {'status': 'healthy', 'stamp': 'recomputed'})
        result = push_health_update(self.worker, runner=runner, regenerate=regenerate)
        self.assertEqual(result, {'status': 'pushed', 'attempts': 2})
        self.assertEqual(len(regenerated), 1)
        original = json.loads(self.git(self.remote, 'show', 'main:data/live.json'))
        self.assertEqual(original['content'][0]['article_hash'], 'new-public-original')
        health = json.loads(self.git(self.remote, 'show', 'main:data/automation-health.json'))
        self.assertEqual(health['stamp'], 'recomputed')

    def test_unrelated_work_is_not_rebased_or_pushed(self):
        self.reports()
        before = self.git(self.remote, 'rev-parse', 'main')
        (self.worker / 'README.md').write_text('unsaved frontend work')
        with self.assertRaisesRegex(ValueError, 'only_own_committed_report'):
            push_health_update(self.worker)
        self.assertEqual(self.git(self.remote, 'rev-parse', 'main'), before)
        self.assertEqual((self.worker / 'README.md').read_text(), 'unsaved frontend work')

    def test_persistent_remote_failure_is_bounded_and_keeps_diagnostic_evidence(self):
        self.reports()
        hook = self.remote / 'hooks/pre-receive'; hook.write_text('#!/bin/sh\necho "permission denied" >&2\nexit 1\n'); hook.chmod(0o755)
        with self.assertRaisesRegex(RuntimeError, 'health_push_not_confirmed'):
            push_health_update(self.worker)
        report = json.loads((self.worker / 'runtime/health-update-evidence/push-report.json').read_text())
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(len(report['attempts']), 1)
