import json
import asyncio
import unittest
import httpx
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from backend.autonomous_translation import digest
from backend.operations import operations_report, load_operations


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.instant = datetime(2026, 10, 15, 6, tzinfo=timezone.utc)
        blocks = json.dumps([{'type': 'paragraph', 'text': 'A public article.'}])
        base = {'id': 'example', 'language': 'en', 'title_original': 'Title', 'article_hash': 'hash',
                'article_blocks_json': blocks, 'article_text': 'A public article.', 'article_status': 'collected'}
        api = {**base, 'editorial_status': 'translated', 'editorial_title_zh': 'API译文',
               'editorial_blocks_json': blocks, 'editorial_provider': 'contextual-api:gemini:model:direct-v1'}
        historic = {**api, 'editorial_provider': 'chatgpt-direct', 'editorial_status': 'reviewed'}
        machine = {**base, 'article_translation_provider': 'offline-m2m100:fixture', 'translation_status': 'machine',
                   'article_translation_json': blocks, 'article_translation_hash': 'saved', 'translated_title_zh': '机翻'}
        machine['translation_input_hash'] = digest(machine, machine['article_translation_provider'])
        self.snapshot = {'snapshot_at': self.instant.isoformat(), 'content': [api, historic,
                         {**base, 'language': 'zh'}, machine, base, {**base, 'article_blocks_json': None}]}
        self.evidence = {'ai': {'status': 'service_wait', 'error': 'ai_http_503', 'requests': 3,
                               'translated': ['done'], 'failed': [{'id': 'bad', 'reason': 'ai_numbers_missing'}],
                               'retry_after': '2026-10-15T07:00:00+00:00'},
                         'machine': {'translated': ['machine'], 'failed': []},
                         'ledger': {'days': {'2026-10-14': {'requests': 100, 'reserved_requests': 40,
                                                         'input_tokens': 1000, 'output_tokens': 200, 'unknown_usage_requests': 2}}},
                         'config': {'requests_per_day': 500, 'requests_per_run': 40,
                                    'paid_activation': False, 'account_mode': 'free-project-only'},
                         'important': {'core_source_problems': [{'source_id': 'offline'}], 'editorial_regions': {
                             'priority_country_gaps': [{'country': 'FR', 'channel': 'art'}]}},
                         'health': {'stages': {'translation': {'status': 'healthy'}}, 'issues': []},
                         'metrics': {'days': {'one': {'new_records': 20, 'first_source_run_records': 10}}},
                         'baseline': {'observation_started_at': '2026-10-14T18:00:00+00:00',
                                      'baseline': {'content': 3, 'pending_ai_with_body': 1,
                                                   'collection_days': {'one': {'new_records': 5, 'first_source_run_records': 3}}}}}

    def test_ai_machine_native_and_pending_counts_are_not_added_together(self):
        report = operations_report(self.snapshot, self.evidence, self.instant)
        progress = report['translation']
        self.assertEqual((progress['completed'], progress['api_completed'], progress['other_ai_completed']), (2, 1, 1))
        self.assertEqual((progress['native_chinese'], progress['pending'], progress['machine_completed'], progress['without_body']), (1, 2, 1, 1))
        self.assertEqual(report['api']['last_run_completed'], 1)
        self.assertFalse(report['policy']['chatgpt_translation_workers'])

    def test_cloudflare_usage_is_separate_from_gemini_quota(self):
        self.snapshot['content'].append({**self.snapshot['content'][0],
            'editorial_provider':'contextual-api:cloudflare:qwen:direct-v1'})
        self.evidence['cloudflare']={'status':'completed','configured':True,'translated':['cf'],
            'requests':1,'neurons':{'estimated_neurons':42,'timezone':'UTC'}}
        report=operations_report(self.snapshot,self.evidence,self.instant)
        self.assertEqual(report['translation']['api_provider_counts'],{'gemini':1,'cloudflare':1})
        self.assertEqual(report['cloudflare']['last_run_completed'],1)
        self.assertEqual(report['cloudflare']['neurons']['estimated_neurons'],42)
        self.assertEqual(report['quota']['combined']['requests'],100)

    def test_green_actions_does_not_hide_service_wait_or_source_gaps(self):
        report = operations_report(self.snapshot, self.evidence, self.instant)
        self.assertEqual(report['workflow_health']['stages']['translation']['status'], 'healthy')
        self.assertEqual(report['status'], 'attention')
        self.assertIn('ai:service_wait', report['warnings'])
        self.assertIn('ai:validation_failures', report['warnings'])
        self.assertTrue(report['api']['waiting_for_retry'])
        self.assertEqual(report['coverage']['global_completeness'], 'unknown')
        self.assertEqual(len(report['coverage']['priority_country_gaps']), 1)

    def test_partial_day_backfills_and_reserved_quota_remain_distinct(self):
        report = operations_report(self.snapshot, self.evidence, self.instant)
        self.assertEqual(report['quota']['day'], '2026-10-14')
        self.assertEqual(report['quota']['remaining_unreserved'], 360)
        self.assertEqual(report['quota']['unknown_usage_requests'], 2)
        window = report['observation']
        self.assertEqual(window['elapsed_hours'], 12)
        self.assertFalse(window['full_24_hours_elapsed'])
        self.assertEqual((window['collected_since_baseline_snapshot'], window['first_source_backfills'], window['other_new_records']), (15, 7, 8))

    def test_two_project_usage_is_separate_and_legacy_fields_stay_primary(self):
        self.evidence['ai']['projects'] = [
            {'id': 'primary', 'configured': True, 'status': 'service_wait', 'requests': 1, 'translated': []},
            {'id': 'secondary', 'configured': True, 'status': 'completed', 'requests': 2, 'translated': ['a', 'b']}]
        self.evidence['ledger_secondary'] = {'days': {'2026-10-14': {'requests': 70, 'reserved_requests': 10,
            'input_tokens': 500, 'output_tokens': 100, 'unknown_usage_requests': 1}}}
        report = operations_report(self.snapshot, self.evidence, self.instant)
        self.assertEqual(report['quota']['requests'], 100)
        self.assertEqual(report['quota']['legacy_fields_project'], 'primary')
        self.assertEqual(report['quota']['combined']['requests'], 170)
        self.assertEqual(report['quota']['combined']['daily_limit'], 1000)
        self.assertEqual(report['api']['projects'][1]['last_run_completed'], 2)
        self.assertIn('ai:primary:service_wait', report['warnings'])

    def test_missing_configured_secondary_ledger_is_unknown_and_unconfigured_not_added(self):
        report = operations_report(self.snapshot, self.evidence, self.instant)
        self.assertEqual(report['quota']['combined']['daily_limit'], 500)
        self.evidence['ai']['projects'] = [{'id': 'secondary', 'configured': True, 'status': 'failed'}]
        report = operations_report(self.snapshot, self.evidence, self.instant)
        self.assertIsNone(report['quota']['combined']['requests'])
        self.assertIn('quota:secondary_ledger_unavailable', report['warnings'])

    def test_missing_or_malformed_evidence_is_unknown_never_zero_cost(self):
        with TemporaryDirectory() as td:
            root = Path(td); (root / 'data').mkdir()
            (root / 'data/ai-translation-ledger.json').write_text('[]')
            report = load_operations(self.snapshot, root, self.instant)
            self.assertIsNone(report['quota']['requests'])
            self.assertIsNone(report['quota']['remaining_unreserved'])
            self.assertIn('evidence:unavailable:ledger', report['warnings'])
            self.assertEqual(report['status'], 'attention')

    def test_report_api_is_read_only_and_does_not_export_credentials(self):
        from backend.app import create_app
        self.evidence['config']['api_key'] = 'fixture-private-value'
        self.assertNotIn('fixture-private-value', json.dumps(operations_report(self.snapshot, self.evidence, self.instant)))
        with TemporaryDirectory() as td:
            app = create_app(Path(td) / 'news.db')
            async def check():
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                    response = await client.get('/api/operations')
                    public = await client.get('/reports/operations.json')
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()['translation'], public.json()['translation'])
                    self.assertEqual((await client.post('/api/operations', json={})).status_code, 405)
            asyncio.run(check())

    def test_transient_retry_evidence_remains_distinct_from_translation_failures(self):
        ai = self.evidence['ai']
        ai.update(service_retry_policy='bounded-exponential-v1', inline_service_retries=1,
                  service_failures=[{'error': 'ai_http_503', 'delay_seconds': 60, 'project': 'primary'}])
        ai['projects'] = [{'id': 'primary', 'configured': True, 'status': 'service_wait',
                           'inline_service_retries': 1, 'service_retry': {'consecutive_failures': 2}}]
        report = operations_report(self.snapshot, self.evidence, self.instant)
        self.assertEqual(report['api']['inline_service_retries'], 1)
        self.assertEqual(report['api']['projects'][0]['service_retry']['consecutive_failures'], 2)
        self.assertEqual(report['api']['service_failures'][0]['delay_seconds'], 60)
        self.assertEqual(len(report['api']['last_run_failed']), 1)
