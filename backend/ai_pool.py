"""AI translation lanes: DeepSeek and two free Gemini projects share disjoint articles in parallel."""
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .ai_translation import configuration, GeminiTranslator, reserve_requests, run_ai, selected_rows, next_quota_day
from .deepseek_translation import DeepSeekTranslator, deepseek_configuration
from .autonomous_translation import write_json
from .quota_repair import apply_verified_repairs
from .storage import ROOT, now
from .ai_retry import POLICY as SERVICE_RETRY_POLICY


PROJECTS = (
    ('primary', 'GEMINI_API_KEY', 'data/ai-translation-ledger.json'),
    ('secondary', 'GEMINI_API_KEY_SECONDARY', 'data/ai-translation-ledger-secondary.json'),
)
DEEPSEEK = ('deepseek', 'DEEPSEEK_API_KEY', 'data/ai-translation-ledger-deepseek.json')


def provider_choice(environ=None):
    """AI_TRANSLATION_PROVIDER=deepseek|gemini forces one; otherwise every configured lane runs."""
    environ = os.environ if environ is None else environ
    choice = environ.get('AI_TRANSLATION_PROVIDER', '').strip().lower()
    if choice in ('deepseek', 'gemini'):
        return choice
    if choice not in ('', 'both'):
        raise ValueError('unknown_ai_translation_provider')
    return 'both' if environ.get(DEEPSEEK[1], '').strip() else 'gemini'


def continue_today(cfg, reports, pending_after, instant=None):
    """One explicitly authorized Pacific quota day; no empty or endless loop."""
    day = (instant or datetime.now(timezone.utc)).astimezone(ZoneInfo('America/Los_Angeles')).date().isoformat()
    return (cfg.get('drain_until_quota_day') == day and pending_after > 0
            and any(r.get('status') in ('run_limit', 'completed', 'partial_failure') and (r.get('requests') or 0) > 0
                    and type(r.get('requests_today')) is int
                    and r['requests_today'] < r.get('daily_request_limit', 0) for r in reports))


def projects(cfg=None, environ=None):
    cfg = cfg or configuration()
    environ = os.environ if environ is None else environ
    choice = provider_choice(environ)
    result = []
    if choice in ('deepseek', 'both'):
        # Listed first so the top-ranked (headline) article goes to the fastest lane.
        identity, variable, path = DEEPSEEK
        key = environ.get(variable, '').strip()
        project_cfg = deepseek_configuration(cfg, environ)
        if type(project_cfg['requests_per_day']) is not int or project_cfg['requests_per_day'] <= 0:
            raise ValueError('invalid_project_daily_limit')
        result.append({'id': identity, 'key': key, 'ledger': path, 'provider': 'deepseek',
                       'status': 'ready' if key else 'not_configured', 'cfg': project_cfg})
        if choice == 'deepseek':
            return result
    budgets = cfg.get('project_daily_limits', {'primary': cfg['requests_per_day'], 'secondary': 500})
    seen = set()
    for identity, variable, path in PROJECTS:
        limit = budgets[identity]
        if type(limit) is not int or not 0 < limit <= 500:
            raise ValueError('invalid_project_daily_limit')
        if identity == 'primary':
            # Never raise the original project's protection through a pool setting.
            limit = min(limit, cfg['requests_per_day'])
        key = environ.get(variable, '').strip()
        status = 'ready' if key else 'not_configured'
        if key and key in seen:
            status = 'duplicate_key'
        if key:
            seen.add(key)
        result.append({'id': identity, 'key': key, 'ledger': path, 'status': status, 'provider': 'gemini',
                       'cfg': {**cfg, 'requests_per_day': limit}})
    return result


def reserve_pool(reservation_id, *, root=ROOT, cfg=None, environ=None):
    root = Path(root)
    reports = []
    for project in projects(cfg, environ):
        report = {'id': project['id'], 'status': project['status']}
        if project['status'] == 'ready':
            try:
                path = root / project['ledger']
                # Legacy operator evidence applies only to the original ledger.
                released = (apply_verified_repairs(path, root / 'data/ai-translation-repairs')
                            if project['id'] == 'primary' else [])
                entry = reserve_requests(path, reservation_id, project['cfg'])
                report.update(reservation=reservation_id, verified_unused_released=released, **entry)
            except (OSError, ValueError, KeyError, TypeError) as error:
                report.update(status='failed', error=type(error).__name__)
        reports.append(report)
    return {'projects': reports}


def run_pool(store, reservation_id, *, root=ROOT, cfg=None, environ=None,
             provider_factory=None, checkpoint_sink=None, io_lock=None, worker_options=None):
    root, cfg = Path(root), cfg or configuration()
    if cfg['account_mode'] != 'free-project-only' or cfg.get('paid_activation') is not False:
        raise ValueError('paid_mode_not_authorized_or_implemented')
    lock = io_lock or threading.RLock()
    specs = projects(cfg, environ)
    reports, runnable = {}, []
    for project in specs:
        identity = project['id']
        if project['status'] != 'ready':
            reports[identity] = {'id': identity, 'status': project['status'], 'configured': bool(project['key']),
                                 'requests': 0, 'translated': [], 'failed': []}
            continue
        try:
            ledger = json.loads((root / project['ledger']).read_text())
            reservation = ledger['reservations'][reservation_id]
            if reservation['status'] != 'reserved':
                raise ValueError('missing_ai_request_reservation')
            retry = ledger.get('retry_after', '')
            waiting = bool(retry and datetime.fromisoformat(retry.replace('Z', '+00:00')) > datetime.now(timezone.utc))
            if reservation['remaining'] > 0 and not waiting:
                runnable.append(project)
            elif reservation['remaining'] <= 0 and not waiting:
                project['empty_budget'] = True
        except (OSError, ValueError, KeyError, TypeError):
            # Let run_ai fail closed for this project; the other can still run.
            pass

    snapshot = store.dataset('live')
    # Only copies already present in the imported, saved snapshot can be
    # removed. Do this before starting either worker; never delete the other
    # worker's newly completed recovery checkpoint from the temporary DB.
    saved = {r['id'] for r in snapshot['content'] if r.get('editorial_status') in ('reviewed', 'translated')}
    with lock:
        for path in (root / 'data/ai-translation-progress').glob('*.json'):
            if path.stem in saved:
                path.unlink(missing_ok=True)
    pending = [r for r in snapshot['content'] if not r.get('is_demo') and r['language'] != 'zh'
               and r.get('article_blocks_json') and r.get('editorial_status') not in ('reviewed', 'translated')]
    ordered = selected_rows(pending, snapshot, len(pending)) if pending else []
    assignments = {p['id']: {r['id'] for r in ordered[offset::len(runnable)]}
                   for offset, p in enumerate(runnable)}
    started = now()

    def worker(project):
        identity, path = project['id'], root / project['ledger']
        try:
            translator = DeepSeekTranslator if project['provider'] == 'deepseek' else GeminiTranslator
            provider = (provider_factory(project) if provider_factory
                        else translator(project['key'], cfg=project['cfg']))
            report = run_ai(store, provider, root / 'data/ai-translation-progress', path,
                            cfg=project['cfg'], reservation_id=reservation_id,
                            eligible_ids=assignments.get(identity, set()), io_lock=lock,
                            checkpoint_sink=checkpoint_sink, **(worker_options or {}))
            if project.get('empty_budget'):
                report.update(status='daily_limit', retry_after=next_quota_day())
        except Exception as error:
            # No key, response body or arbitrary exception text enters public data.
            spent = None
            try:
                entry = json.loads(path.read_text())['reservations'][reservation_id]
                spent = entry['allocated'] - entry['remaining']
            except (OSError, ValueError, KeyError, TypeError):
                pass
            report = {'status': 'failed', 'error': type(error).__name__, 'requests': spent,
                      'translated': [], 'failed': [], 'finished_at': now()}
        report.update(id=identity, configured=True)
        with lock:
            write_json(root / ('data/ai-translation-projects/' + identity + '.json'), report)
        return report

    # Non-runnable, configured projects also finalize their unused reservation
    # through run_ai, without receiving any article assignments or API calls.
    with ThreadPoolExecutor(max_workers=len(specs)) as pool:
        futures = {p['id']: pool.submit(worker, p) for p in specs if p['status'] == 'ready'}
        for identity, future in futures.items():
            reports[identity] = future.result()
    lanes = [reports[p['id']] for p in specs]
    active = [r for r in lanes if r.get('configured') and r['status'] != 'duplicate_key']
    statuses = {r['status'] for r in active}
    waiting_states = {'service_wait', 'quota_wait', 'retry_wait', 'daily_limit'}
    if not active:
        status = 'needs_configuration'
    elif len(active) == 1:
        status = active[0]['status']
    elif statuses <= waiting_states:
        status = next(s for s in ('service_wait', 'quota_wait', 'retry_wait', 'daily_limit') if s in statuses)
    elif statuses <= {'failed', 'configuration_error'}:
        status = 'failed'
    elif statuses & (waiting_states | {'failed', 'configuration_error', 'partial_failure'}):
        status = 'partial_failure'
    else:
        status = 'run_limit' if 'run_limit' in statuses else 'completed'
    lane_cfg = specs[0]['cfg']
    providers = list(dict.fromkeys(p['provider'] for p in specs if p['status'] == 'ready')) or [specs[0]['provider']]
    report = {'status': status, 'provider': 'contextual-api:' + specs[0]['provider'] + ':' + lane_cfg['model'] + ':direct-v1',
              'model': lane_cfg['model'], 'translation_provider': '+'.join(providers), 'account_mode': lane_cfg['account_mode'], 'pool_mode': 'parallel_disjoint_articles',
              'started_at': started, 'finished_at': now(), 'projects': lanes,
              'pending_before': len(pending), 'configured_projects': len(active)}
    report['service_retry_policy'] = SERVICE_RETRY_POLICY
    report['inline_service_retries'] = sum(r.get('inline_service_retries', 0) for r in active)
    report['service_failures'] = [{**failure, 'project': r['id']}
                                for r in active for failure in r.get('service_failures', [])]
    for field in ('translated', 'resumed', 'deferred', 'stale'):
        report[field] = list(dict.fromkeys(i for r in active for i in r.get(field, [])))
    report['failed'] = [{**item, 'project': r['id']} for r in active for item in r.get('failed', [])]
    for field in ('requests', 'input_tokens', 'output_tokens', 'requests_today', 'unknown_usage_requests_today'):
        values = [r.get(field) for r in active]
        report[field] = sum(values) if all(type(v) is int for v in values) else None
    report['daily_request_limit'] = sum(p['cfg']['requests_per_day'] for p in specs
                                        if p['id'] in {r['id'] for r in active})
    report['pending_after'] = len(pending) - len(report['translated'])
    report['continue_recommended'] = continue_today(cfg, active, report['pending_after'])
    report['seconds'] = max((r.get('seconds', 0) for r in active), default=0)
    if len(active) == 1:
        for field in ('retry_after', 'error'):
            if field in active[0]: report[field] = active[0][field]
    elif statuses <= waiting_states:
        retries = [r['retry_after'] for r in active if r.get('retry_after')]
        if retries: report['retry_after'] = min(retries)
    return report
