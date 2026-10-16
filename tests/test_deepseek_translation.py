import json
import unittest

from backend.ai_pool import projects, provider_choice
from backend.ai_translation import ServiceError, configuration
from backend.deepseek_translation import DeepSeekTranslator, deepseek_configuration
from tests import test_ai_pool


class DeepSeekProviderTests(unittest.TestCase):
    def test_choice_defaults_to_deepseek_only_when_its_key_exists(self):
        self.assertEqual(provider_choice({}), 'gemini')
        self.assertEqual(provider_choice({'GEMINI_API_KEY': 'g'}), 'gemini')
        self.assertEqual(provider_choice({'DEEPSEEK_API_KEY': 'd', 'GEMINI_API_KEY': 'g'}), 'deepseek')
        self.assertEqual(provider_choice({'DEEPSEEK_API_KEY': 'd', 'AI_TRANSLATION_PROVIDER': 'gemini'}), 'gemini')
        self.assertEqual(provider_choice({'AI_TRANSLATION_PROVIDER': ' DeepSeek '}), 'deepseek')
        with self.assertRaises(ValueError):
            provider_choice({'AI_TRANSLATION_PROVIDER': 'other'})

    def test_deepseek_lane_has_own_ledger_cap_and_model_override(self):
        lanes = projects(configuration(), {'DEEPSEEK_API_KEY': 'd', 'GEMINI_API_KEY': 'g',
                                           'DEEPSEEK_MODEL': 'deepseek-v4-pro'})
        self.assertEqual([lane['id'] for lane in lanes], ['deepseek'])
        lane = lanes[0]
        self.assertEqual(lane['ledger'], 'data/ai-translation-ledger-deepseek.json')
        self.assertEqual(lane['cfg']['model'], 'deepseek-v4-pro')
        self.assertEqual(lane['cfg']['requests_per_day'], configuration()['deepseek']['requests_per_day'])
        self.assertEqual(lane['cfg']['account_mode'], 'user-authorized-prepaid')

    def test_request_disables_thinking_and_maps_usage(self):
        sent = []
        def transport(payload):
            sent.append(payload)
            return {'model': 'deepseek-flash', 'usage': {'prompt_tokens': 120, 'completion_tokens': 40},
                    'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(
                        {'outputs': {'a': '甲', 'b': '乙', 'extra': '多余'}})}}]}
        translator = DeepSeekTranslator('secret', transport=transport, cfg=deepseek_configuration())
        outputs, usage = translator.translate({'original_units': []}, ['a', 'b'])
        self.assertEqual(outputs, {'a': '甲', 'b': '乙'})
        self.assertEqual(usage, {'promptTokenCount': 120, 'candidatesTokenCount': 40})
        self.assertEqual(sent[0]['thinking'], {'type': 'disabled'})
        self.assertEqual(sent[0]['response_format'], {'type': 'json_object'})
        self.assertNotIn('secret', json.dumps(sent[0]))
        self.assertTrue(translator.name.startswith('contextual-api:deepseek:'))

    def test_missing_key_or_truncated_output_is_rejected(self):
        for choice in ({'finish_reason': 'length', 'message': {'content': '{}'}},
                       {'finish_reason': 'stop', 'message': {'content': '{"outputs": {"a": "甲"}}'}}):
            translator = DeepSeekTranslator('k', transport=lambda p, c=choice: {'choices': [c]},
                                            cfg=deepseek_configuration())
            with self.assertRaises(ValueError):
                translator.translate({}, ['a', 'b'])

    def test_invalid_model_name_is_rejected(self):
        with self.assertRaises(ValueError):
            DeepSeekTranslator('k', cfg={**deepseek_configuration(), 'model': 'gpt-4'})


class DeepSeekPoolTests(test_ai_pool.AIPoolTests):
    """Run the shared pool fixtures through the DeepSeek lane."""

    def deepseek_provider(self, project, transport=None):
        def answer(payload):
            document = json.loads(payload['messages'][1]['content'])
            outputs = {u['key']: '译文：' + u['text'] for u in document['original_units']
                       if u['key'] in document['requested_keys']}
            return {'model': 'deepseek-flash', 'usage': {'prompt_tokens': 200, 'completion_tokens': 80},
                    'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps({'outputs': outputs})}}]}
        return DeepSeekTranslator(project['key'], cfg=project['cfg'], transport=transport or answer)

    def test_deepseek_lane_translates_and_never_touches_gemini_ledgers(self):
        self.setup_pool(env={'DEEPSEEK_API_KEY': 'deep-test-key', 'GEMINI_API_KEY': 'first-test-key'})
        report = self.execute(self.deepseek_provider)
        self.assertEqual(report['translated'], [self.row['id']])
        self.assertEqual(report['translation_provider'], 'deepseek')
        self.assertEqual(report['account_mode'], 'user-authorized-prepaid')
        self.assertEqual(report['daily_request_limit'], configuration()['deepseek']['requests_per_day'])
        self.assertNotIn('deep-test-key', json.dumps(report))
        self.assertTrue((self.root / 'data/ai-translation-ledger-deepseek.json').exists())
        self.assertFalse((self.root / 'data/ai-translation-ledger.json').exists())
        published = [r for r in self.store.dataset('live')['content'] if r['id'] == self.row['id']][0]
        self.assertTrue(published['editorial_provider'].startswith('contextual-api:deepseek:'))

    def test_insufficient_balance_waits_instead_of_retrying(self):
        self.setup_pool(env={'DEEPSEEK_API_KEY': 'deep-test-key'})
        def no_balance(payload):
            raise ServiceError(402, 0, {'http_status': 402, 'category': 'insufficient_balance'})
        report = self.execute(lambda p: self.deepseek_provider(p, no_balance))
        self.assertEqual(report['status'], 'configuration_error')
        self.assertEqual(report['requests'], 1)
        self.assertEqual(report['translated'], [])


# Do not rerun every inherited Gemini pool test under this module.
for _name in [n for n in dir(test_ai_pool.AIPoolTests) if n.startswith('test_')]:
    setattr(DeepSeekPoolTests, _name, None)


if __name__ == '__main__':
    unittest.main()
