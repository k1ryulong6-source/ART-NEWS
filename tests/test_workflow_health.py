import unittest
from datetime import datetime, timezone
from backend.workflow_health import stage_health


class WorkflowHealthTests(unittest.TestCase):
    def row(self, status='completed', conclusion='success', created='2026-10-15T01:00:00Z', updated='2026-10-15T01:30:00Z'):
        return {'id': created, 'status': status, 'conclusion': conclusion, 'created_at': created, 'updated_at': updated}

    def check(self, rows):
        return stage_health(rows, datetime(2026, 10, 15, 2, tzinfo=timezone.utc))

    def test_cancelled_pending_does_not_hide_actual_older_running_worker(self):
        queued = self.row(conclusion='cancelled', created='2026-10-15T01:45:00Z')
        active = self.row(status='in_progress', conclusion=None)
        report, issue = self.check([queued, active, self.row()])
        self.assertEqual(report['status'], 'running')
        self.assertEqual(report['active_run']['id'], active['id'])
        self.assertIsNone(issue)

    def test_worker_success_after_queue_cancellation_is_healthy(self):
        report, issue = self.check([self.row(conclusion='cancelled', created='2026-10-15T01:15:00Z'), self.row()])
        self.assertEqual(report['status'], 'healthy')
        self.assertIsNone(issue)

    def test_cancelled_without_active_or_subsequent_success_still_fails(self):
        report, issue = self.check([self.row(conclusion='cancelled', created='2026-10-15T01:45:00Z'), self.row()])
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(issue, ':failed')

    def test_real_failure_and_no_recent_success_are_not_hidden(self):
        report, issue = self.check([self.row(conclusion='failure'), self.row(status='in_progress', conclusion=None)])
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(issue, ':failed')
        report, issue = self.check([])
        self.assertEqual(report['status'], 'stale')
        self.assertEqual(issue, ':no_recent_success')
