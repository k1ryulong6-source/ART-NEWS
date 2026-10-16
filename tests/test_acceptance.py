import copy
import unittest
from datetime import datetime, timezone
from backend.acceptance import acceptance_report, snapshot_key


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.instant = datetime(2026, 10, 16, 8, tzinfo=timezone.utc)
        self.ops = {'snapshot_key': 'same', 'observation': {'full_24_hours_elapsed': True},
                    'translation': {'pending': 0, 'without_body': 0}, 'quota': {'requests': 200},
                    'workflow_health': {'stages': {s: {'status': 'healthy'} for s in ('collection', 'translation', 'publication')}},
                    'coverage': {'checked_at': self.instant.isoformat(), 'core_source_problems': [],
                                 'enabled_source_problems': [], 'priority_country_gaps': [], 'missing_important_items': []}}
        self.quality = {'complete': True, 'snapshot_key': 'same', 'local_issues': []}
        self.trial = {'complete': True, 'resumed_articles': 3, 'publication_verified': True}
        self.attention = {'units': [{'id': 'a-kind-of-attention', 'members': [
            {'source_id': 'local', 'collection_status': 'success', 'last_successful_fetch_at': self.instant.isoformat()}]}]}

    def report(self, **changes):
        args = dict(operations=self.ops, quality=self.quality, trial=self.trial,
                    attention=self.attention, instant=self.instant)
        args.update(changes)
        return acceptance_report(**args)

    def test_only_all_four_verified_gates_can_complete(self):
        self.assertTrue(self.report()['all_ready'])
        self.assertFalse(acceptance_report({})['all_ready'])

    def test_partial_day_or_no_actual_resume_does_not_complete(self):
        self.ops['observation']['full_24_hours_elapsed'] = False
        self.assertFalse(self.report()['gates']['unattended_24h']['passed'])
        self.ops['observation']['full_24_hours_elapsed'] = True
        self.trial['resumed_articles'] = 0
        self.assertFalse(self.report()['all_ready'])

    def test_changed_snapshot_rejects_previous_quality_pass(self):
        self.quality['snapshot_key'] = 'old'
        self.assertFalse(self.report()['gates']['article_quality']['passed'])
        one = {'content': [{'id': 'a', 'article_hash': 'original'}]}
        two = copy.deepcopy(one); two['content'][0]['article_hash'] = 'new'
        self.assertNotEqual(snapshot_key(one), snapshot_key(two))
        self.assertNotEqual(snapshot_key(one, {'sources': []}), snapshot_key(one, {'sources': [{'id': 'added'}]}))

    def test_backlog_missing_bodies_and_coverage_stay_open(self):
        self.ops['translation'].update(pending=1, without_body=1)
        self.ops['coverage']['priority_country_gaps'] = [{'country': 'CH', 'channel': 'art'}]
        result = self.report()
        self.assertFalse(result['gates']['full_text_translation']['passed'])
        self.assertFalse(result['gates']['coverage_gaps']['passed'])

    def test_expired_attention_source_does_not_count_as_healthy(self):
        self.attention['units'][0]['members'][0]['last_successful_fetch_at'] = '2026-10-15T00:00:00Z'
        self.assertFalse(self.report()['gates']['coverage_gaps']['passed'])
