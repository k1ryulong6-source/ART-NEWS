import copy
import unittest
from backend.quota_repair import release_verified_unused


class QuotaRepairTests(unittest.TestCase):
    def setUp(self):
        self.ledger = {'days': {'2026-10-15': {'requests': 13, 'input_tokens': 100, 'output_tokens': 50,
                                             'unknown_usage_requests': 2, 'reserved_requests': 43}},
                       'reservations': {'123:1': {'day': '2026-10-15', 'allocated': 40, 'remaining': 40, 'status': 'reserved'},
                                        '999:1': {'day': '2026-10-15', 'allocated': 3, 'remaining': 3, 'status': 'reserved'}}}
        self.proof = {'reservation_id': '123:1', 'run_conclusion': 'failure', 'day': '2026-10-15', 'allocated': 40,
                      'evidence_url': 'https://github.com/example/project/actions/runs/123',
                      'report': {'requests': 0, 'account_mode': 'free-project-only', 'finished_at': '2026-10-15T08:00:00Z'}}

    def test_verified_zero_only_releases_unused_slots_without_resetting_usage_or_unknown_reservations(self):
        before = copy.deepcopy(self.ledger['days']['2026-10-15'])
        self.assertEqual(release_verified_unused(self.ledger, [self.proof]), ['123:1'])
        usage = self.ledger['days']['2026-10-15']
        self.assertEqual(usage['reserved_requests'], 3)
        for field in ('requests', 'input_tokens', 'output_tokens', 'unknown_usage_requests'):
            self.assertEqual(usage[field], before[field])
        self.assertEqual(self.ledger['reservations']['999:1']['remaining'], 3)
        self.assertEqual(release_verified_unused(self.ledger, [self.proof]), [])

    def test_partial_usage_or_a_nonzero_report_is_never_refunded(self):
        before = copy.deepcopy(self.ledger)
        proof = {**self.proof, 'report': {**self.proof['report'], 'requests': 1}}
        self.assertEqual(release_verified_unused(self.ledger, [proof]), [])
        self.assertEqual(self.ledger, before)
        self.ledger['reservations']['123:1']['remaining'] = 39
        self.assertEqual(release_verified_unused(self.ledger, [self.proof]), [])
