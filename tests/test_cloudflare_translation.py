import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from urllib.error import URLError
from backend.cloudflare_translation import (MODEL, SCALE, CloudflareTranslator, NeuronBudget,
    configuration, load_budget, reserve_neurons, reserve_cloudflare, run_cloudflare, utc_day)
from backend.ai_translation import ProviderBudgetError, ServiceError
from backend.autonomous_translation import write_json
from backend.storage import Store
from backend.cloudflare_translation import restore_completed
from tests import test_ai_translation as fixtures


class CloudflareTests(unittest.TestCase):
    setUp = fixtures.AITranslationTests.setUp

    def cfg(self, **kw):
        return {**configuration(), 'request_interval_seconds': 0,
                'transient_retry': {**configuration()['transient_retry'], 'inline_retries_per_run': 0}, **kw}

    def env(self):
        return {'CLOUDFLARE_API_TOKEN': 'fixture-never-real', 'CLOUDFLARE_ACCOUNT_ID': 'a' * 32}

    def transport(self, payload):
        doc = json.loads(payload['messages'][1]['content'].removesuffix('\n/no_think'))
        units = {u['key']: '译文：' + u['text'] for u in doc['original_units']}
        outputs = {k: units[k] for k in doc['requested_keys']}
        return {'success': True, 'result': {'choices': [{'finish_reason': 'stop',
            'message': {'content': json.dumps({'outputs': outputs})}}],
            'usage': {'prompt_tokens': 400, 'completion_tokens': 80}}}

    def run_worker(self, identity='test-1', transport=None, cfg=None, probe=True):
        with patch('backend.cloudflare_translation.configuration', return_value=cfg or self.cfg()):
            reserve_cloudflare(identity, root=self.root, environ=self.env(), probe=probe)
            return run_cloudflare(self.store, identity, root=self.root, environ=self.env(), probe=probe,
                                  transport=transport or self.transport,
                                  worker_options={'sleep': lambda _: None})

    def test_full_single_pass_and_token_based_neurons_without_second_review(self):
        report = self.run_worker()
        self.assertEqual(report['requests'], 1)
        self.assertEqual(report['translated'], [self.row['id']])
        self.assertEqual(report['neurons']['estimated_neurons'], (400 * 4625 + 80 * 30475) / SCALE)
        self.assertEqual(report['neurons']['reserved_neurons'], 0)
        self.assertEqual(report['neurons']['unknown_neurons_upper_bound'], 0)
        row = self.store.dataset('live')['content'][0]
        self.assertEqual(row['editorial_model'], MODEL)
        self.assertEqual(row['article_blocks_json'], self.row['article_blocks_json'])
        self.assertIsNone(row['editorial_review_model'])
        self.assertEqual(self.run_worker('test-2')['requests'], 0)

    def test_unknown_usage_keeps_conservative_charge_even_after_release(self):
        def timeout(_): raise URLError('fixture')
        report = self.run_worker(transport=timeout)
        self.assertEqual(report['requests'], 1)
        self.assertGreater(report['neurons']['unknown_neurons_upper_bound'], 0)
        self.assertEqual(report['neurons']['reserved_neurons'], 0)
        self.assertEqual(report['neurons']['estimated_neurons'], 0)

    def test_malformed_output_still_records_actual_tokens_and_no_full_copy(self):
        def malformed(payload):
            r = self.transport(payload)
            r['result']['choices'][0]['message']['content'] = '{bad json'
            return r
        r = self.run_worker(transport=malformed)
        self.assertEqual(r['translated'], [])
        self.assertEqual(r['input_tokens'], 400)
        self.assertGreater(r['neurons']['estimated_neurons'], 0)
        self.assertEqual(r['neurons']['unknown_neurons_upper_bound'], 0)

    def test_crashed_reservation_is_not_available_to_a_new_run(self):
        path = self.root / 'neurons.json'; cfg = self.cfg(neurons_per_day=3000, neurons_per_run=2000)
        first = reserve_neurons(path, 'crashed', cfg)
        second = reserve_neurons(path, 'next', cfg)
        self.assertEqual(first['remaining_micro_neurons'], 2000 * SCALE)
        self.assertEqual(second['remaining_micro_neurons'], 1000 * SCALE)
        self.assertEqual(load_budget(path)['days'][utc_day()]['reserved_micro_neurons'], 3000 * SCALE)
        reserve_neurons(path, 'next', cfg)
        self.assertEqual(load_budget(path)['days'][utc_day()]['reserved_micro_neurons'], 3000 * SCALE)

    def test_neuron_limit_stops_before_generation_and_request_increment(self):
        report = self.run_worker(cfg=self.cfg(neurons_per_day=1))
        self.assertEqual(report['status'], 'daily_limit')
        self.assertEqual(report['requests'], 0)
        self.assertEqual(report['neurons']['requests'], 0)

    def test_auth_failure_stops_and_does_not_print_credentials(self):
        def forbidden(_): raise ServiceError(403)
        r = self.run_worker(transport=forbidden)
        self.assertEqual(r['status'], 'configuration_error')
        self.assertEqual(r['requests'], 1)
        self.assertNotIn(self.env()['CLOUDFLARE_API_TOKEN'], json.dumps(r))
        self.assertNotIn(self.env()['CLOUDFLARE_ACCOUNT_ID'], json.dumps(r))

    def test_truncated_output_never_publishes(self):
        def truncated(payload):
            r = self.transport(payload);r['result']['choices'][0]['finish_reason'] = 'length';return r
        r = self.run_worker(transport=truncated)
        self.assertEqual(r['translated'], [])
        self.assertGreater(r['neurons']['estimated_neurons'], 0)

    def test_complete_original_context_is_sent_but_only_missing_units_return(self):
        seen = []
        def transport(payload):
            doc = json.loads(payload['messages'][1]['content'].removesuffix('\n/no_think'))
            seen.append(doc)
            return self.transport(payload)
        r = self.run_worker(transport=transport, cfg=self.cfg(source_characters_per_chunk=25))
        self.assertEqual(r['requests'], 2)
        self.assertTrue(all(len(d['original_units']) >= 3 for d in seen))
        self.assertFalse(set(seen[0]['requested_keys']) & set(seen[1]['requested_keys']))
        self.assertEqual(r['translated'], [])
        r = self.run_worker('resume', transport=transport)
        self.assertEqual(r['translated'], [self.row['id']])
        self.assertIn(self.row['id'], r['resumed'])

    def test_context_not_truncated_and_failed_preflight_does_not_charge(self):
        cfg = self.cfg();path = self.root / 'neurons.json';reserve_neurons(path, 'r', cfg)
        p = CloudflareTranslator('fixture', 'a'*32, NeuronBudget(path,'r',cfg),cfg, self.transport)
        with self.assertRaisesRegex(ValueError, 'full_context'):
            p.prepare_request({'original_units':[{'key':'b','text':'文'*20000}]},['b'])
        self.assertEqual(load_budget(path)['days'][utc_day()]['requests'],0)

    def test_missing_credentials_and_unverified_production_do_not_call(self):
        r=run_cloudflare(self.store,'none',root=self.root,environ={},transport=lambda _:self.fail())
        self.assertEqual(r['status'],'not_configured')
        with patch('backend.cloudflare_translation.configuration',return_value=self.cfg(verified_enabled=False)):
            r=run_cloudflare(self.store,'none',root=self.root,environ=self.env(),transport=lambda _:self.fail())
        self.assertEqual(r['status'],'awaiting_verification')

    def test_healthy_gemini_skips_qwen_and_releases_unused_budget(self):
        write_json(self.root/'data/ai-translation-status.json',{'status':'completed'})
        r=self.run_worker(probe=False,cfg=self.cfg(verified_enabled=True))
        self.assertEqual(r['status'],'primary_available')
        self.assertEqual(r['requests'],0)
        self.assertEqual(r['neurons']['reserved_neurons'],0)

    def test_request_days_use_utc_only_for_cloudflare(self):
        from backend.ai_translation import reserve_requests
        class FrozenDatetime:
            @staticmethod
            def now(zone):
                return datetime(2026,10,16,0,30,tzinfo=timezone.utc).astimezone(zone)
        with patch('backend.ai_translation.datetime', FrozenDatetime):
            cf=reserve_requests(self.root/'cf-requests.json','cf',self.cfg())
            gemini=reserve_requests(self.root/'gemini-requests.json','gemini',
                                   fixtures.configuration())
        self.assertEqual(cf['day'],'2026-10-16')
        self.assertEqual(gemini['day'],'2026-10-15')

    def test_mid_run_activation_waits_for_a_committed_reservation(self):
        with patch('backend.cloudflare_translation.configuration',return_value=self.cfg(verified_enabled=True)):
            r=run_cloudflare(self.store,'unreserved',root=self.root,environ=self.env(),
                             transport=lambda _:self.fail('unreserved request'))
        self.assertEqual(r['status'],'awaiting_reservation')
        self.assertEqual(r['requests'],0)

    def test_isolated_probe_checkpoint_recovers_without_overwriting_new_sources(self):
        snapshot=self.store.dataset('live')
        r=self.run_worker()
        self.assertEqual(r['translated'],[self.row['id']])
        path=self.root/'before.json';write_json(path,snapshot)
        restored=Store(self.root/'restored.db');restored.restore_public_snapshot(path)
        report=restore_completed(restored,self.root)
        self.assertEqual(report['restored'],[self.row['id']])
        row=restored.dataset('live')['content'][0]
        self.assertEqual(row['editorial_model'],MODEL)
        self.assertEqual(restore_completed(restored,self.root)['restored'],[])
        checkpoint=self.root/'data/cloudflare-translation-progress'/(self.row['id']+'.json')
        state=json.loads(checkpoint.read_text());state['source_hash']='outdated';write_json(checkpoint,state)
        other=Store(self.root/'other.db');other.restore_public_snapshot(path)
        self.assertEqual(restore_completed(other,self.root)['restored'],[])

    def test_explicit_validation_retry_keeps_accepted_units(self):
        def copied(payload):
            r=self.transport(payload)
            outputs=json.loads(r['result']['choices'][0]['message']['content'])['outputs']
            outputs['block:0:text:0']=json.loads(self.row['article_blocks_json'])[0]['text']
            r['result']['choices'][0]['message']['content']=json.dumps({'outputs':outputs})
            return r
        first=self.run_worker(transport=copied)
        self.assertEqual(first['status'],'partial_failure')
        write_json(self.root/'data/cloudflare-verification-report.json',first)
        seen=[]
        def good(payload):
            doc=json.loads(payload['messages'][1]['content'].removesuffix('\n/no_think'))
            seen.extend(doc['requested_keys'])
            return self.transport(payload)
        with patch('backend.cloudflare_translation.configuration',return_value=self.cfg()):
            reserve_cloudflare('retry-unit',root=self.root,environ=self.env(),probe=True)
            report=run_cloudflare(self.store,'retry-unit',root=self.root,environ=self.env(),probe=True,
                                  retry_validation=True,transport=good,worker_options={'sleep':lambda _:None})
        self.assertEqual(report['translated'],[self.row['id']])
        self.assertEqual(seen,['block:0:text:0'])
        self.assertEqual(report['validation_retry_id'],self.row['id'])
