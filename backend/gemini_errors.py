"""Public-safe Gemini error evidence, never raw provider bodies or metadata."""
import json
import re


STATUSES = {'INVALID_ARGUMENT', 'UNAUTHENTICATED', 'PERMISSION_DENIED', 'NOT_FOUND',
            'RESOURCE_EXHAUSTED', 'INTERNAL', 'UNAVAILABLE', 'DEADLINE_EXCEEDED',
            'FAILED_PRECONDITION', 'CANCELLED', 'UNKNOWN'}
# Only literal, recognized phrases are retained. Error bodies can echo prompts,
# credentials, URLs or account IDs; redacting just the current key is not enough.
PHRASES = (
    ({503}, 'capacity_unavailable', r'high demand|temporarily overloaded|model is overloaded|server is overloaded|insufficient (?:serving )?capacity'),
    ({400, 401, 403}, 'key_reported_leaked', r'API key was reported as leaked'),
    ({400, 401, 403}, 'invalid_api_key', r'API key not valid|invalid API key'),
    ({429}, 'quota_exceeded', r'quota exceeded|exceeded your current quota|rate limit exceeded'),
    ({400, 403}, 'unsupported_location', r'user location is not supported|unsupported location'),
    ({404}, 'model_not_found', r'model (?:is )?(?:not found|missing)|not found for API version'),
)


def error_detail(error):
    detail = {'http_status': error.code, 'category': 'unclassified_http_error'}
    try:
        raw = error.read(64_001)
        if len(raw) > 64_000:
            return detail
        value = json.loads(raw).get('error', {})
        if not isinstance(value, dict):
            return detail
        status = value.get('status')
        if isinstance(status, str) and status in STATUSES:
            detail['api_status'] = status
        if error.code == 503 and status == 'UNAVAILABLE':
            detail['category'] = 'service_unavailable'
        message = value.get('message', '')
        if isinstance(message, str):
            for codes, category, pattern in PHRASES:
                match = re.search(pattern, message, re.I) if error.code in codes else None
                if match:
                    detail.update(category=category, message_evidence=match.group())
                    break
    except (ValueError, TypeError, AttributeError, OSError):
        pass
    return detail
