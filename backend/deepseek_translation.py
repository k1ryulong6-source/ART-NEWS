"""DeepSeek (OpenAI-compatible) direct translation; same contract as GeminiTranslator."""
import json
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from . import ai_retry
from .ai_translation import INSTRUCTION, ServiceError, configuration

# Only the HTTP code maps to a category; provider bodies may echo prompts or account data.
CATEGORIES = {400: 'invalid_request', 401: 'invalid_api_key', 402: 'insufficient_balance',
              422: 'invalid_parameters', 429: 'rate_limited', 500: 'server_error',
              503: 'service_unavailable'}


def deepseek_configuration(cfg=None, environ=None):
    """Merge the DeepSeek block over the shared limits; DEEPSEEK_MODEL may override the model."""
    cfg = cfg or configuration()
    merged = {**cfg, **cfg['deepseek'], 'provider': 'deepseek'}
    merged.pop('project_daily_limits', None)
    model = (environ or {}).get('DEEPSEEK_MODEL', '').strip()
    if model:
        merged['model'] = model
    return merged


class DeepSeekTranslator:
    def __init__(self, key, transport=None, cfg=None):
        self.cfg = cfg or deepseek_configuration()
        self.key = key
        self.model = self.cfg['model']
        if not re.fullmatch(r'deepseek-[a-z0-9.-]+', self.model):
            raise ValueError('invalid_model')
        self.base_url = self.cfg.get('base_url', 'https://api.deepseek.com').rstrip('/')
        if not re.fullmatch(r'https://[a-z0-9.-]+(/[a-z0-9/]*)?', self.base_url):
            raise ValueError('invalid_base_url')
        self.name = 'contextual-api:deepseek:' + self.model + ':direct-v1'
        self.transport = transport or self.request
        self.actual_model = None
        self.last_usage = None

    def request(self, payload):
        # The secret is a header, never a URL, snapshot, log, or browser asset.
        request = Request(self.base_url + '/chat/completions',
                          data=json.dumps(payload, ensure_ascii=False).encode(),
                          headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.key})
        try:
            with urlopen(request, timeout=180) as response:
                raw = response.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise ValueError('response_too_large')
                return json.loads(raw)
        except HTTPError as error:
            retry = (error.headers or {}).get('Retry-After', '')
            detail = {'http_status': error.code, 'category': CATEGORIES.get(error.code, 'unclassified_http_error')}
            raise ServiceError(error.code, ai_retry.retry_after_seconds(retry), detail) from None

    def translate(self, document, keys):
        self.last_usage = None
        payload = {'model': self.model,
                   'messages': [{'role': 'system', 'content': INSTRUCTION},
                                {'role': 'user', 'content': json.dumps({**document, 'requested_keys': keys},
                                                                       ensure_ascii=False)}],
                   'response_format': {'type': 'json_object'},
                   # Direct single-pass translation; no paid reasoning tokens.
                   'thinking': {'type': 'disabled'},
                   'temperature': 0.1,
                   'max_tokens': self.cfg['max_output_tokens'],
                   'stream': False}
        response = self.transport(payload)
        usage = response.get('usage') or {}
        self.last_usage = {'promptTokenCount': usage.get('prompt_tokens'),
                           'candidatesTokenCount': usage.get('completion_tokens')}
        self.actual_model = response.get('model')
        choices = response.get('choices') or []
        if not choices or choices[0].get('finish_reason') != 'stop':
            raise ValueError('ai_output_incomplete')
        # JSON mode occasionally appends text after the object; keep only the first object.
        content = ((choices[0].get('message') or {}).get('content') or '').strip()
        value = json.JSONDecoder().raw_decode(content)[0]
        outputs = value.get('outputs') if isinstance(value, dict) else None
        if not isinstance(outputs, dict) or not set(keys) <= set(outputs):
            raise ValueError('ai_unit_coverage_mismatch')
        # JSON mode does not enforce a schema; ignore any extra keys the model invents.
        return {key: outputs[key] for key in keys}, self.last_usage
