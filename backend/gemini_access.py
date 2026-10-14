"""Read-only model discovery. Never infer, expose keys, or publish raw responses."""
import json
import re
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def inspect_access(key, configured_model, opener=urlopen):
    report = {'provider': 'gemini', 'configured_model': configured_model,
              'generation_requests': 0, 'models': []}
    if not key:
        return {**report, 'status': 'needs_configuration'}
    page_token = None
    try:
        for _ in range(5):
            query = {'pageSize': 1000}
            if page_token:
                query['pageToken'] = page_token
            request = Request('https://generativelanguage.googleapis.com/v1beta/models?' + urlencode(query),
                              headers={'x-goog-api-key': key, 'User-Agent': 'Intermission-model-check'})
            with opener(request, timeout=30) as response:
                raw = response.read(4_000_001)
            if len(raw) > 4_000_000:
                return {**report, 'status': 'invalid_catalog'}
            value = json.loads(raw)
            for item in value.get('models', []):
                name = item.get('name', '')
                if re.fullmatch(r'models/gemini-[a-zA-Z0-9._-]{1,120}', name):
                    report['models'].append({'name': name.removeprefix('models/'),
                        'generate_content': 'generateContent' in item.get('supportedGenerationMethods', [])})
            page_token = value.get('nextPageToken')
            if not page_token:
                break
        if page_token:
            return {**report, 'status': 'catalog_incomplete'}
        available = any(m['name'] == configured_model and m['generate_content'] for m in report['models'])
        return {**report, 'status': 'model_available' if available else 'configured_model_unavailable'}
    except HTTPError as error:
        # Raw messages can echo request details. Publish only the HTTP code.
        return {**report, 'status': 'access_error', 'http_status': error.code}
    except Exception as error:
        return {**report, 'status': 'inspection_failed', 'error': type(error).__name__}
