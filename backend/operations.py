"""Read-only operational evidence. No network, model calls, or private settings."""
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from .storage import ROOT
from .coverage import translation_progress
from .acceptance import snapshot_key


def operations_report(snapshot, evidence, instant=None):
    instant = instant or datetime.now(timezone.utc)
    ai, machine = evidence.get('ai') or {}, evidence.get('machine') or {}
    ledger, cfg = evidence.get('ledger'), evidence.get('config') or {}
    important, health = evidence.get('important') or {}, evidence.get('health') or {}
    rows = [r for r in snapshot.get('content', []) if not r.get('is_demo')]
    progress = translation_progress(snapshot)
    completed = [r for r in rows if r.get('editorial_status') in ('reviewed', 'translated')
                 and r.get('editorial_blocks_json') and r.get('editorial_title_zh')]
    api = [r for r in completed if str(r.get('editorial_provider') or '').startswith('contextual-api:')]
    warnings = []
    if ai.get('status') in ('service_wait', 'quota_wait', 'retry_wait', 'daily_limit', 'configuration_error', 'failed'):
        warnings.append('ai:' + ai['status'])
    if ai.get('failed'): warnings.append('ai:validation_failures')
    if machine.get('failed'): warnings.append('machine:validation_failures')
    core = important.get('core_source_problems') or []
    states = {s['id']: s for s in snapshot.get('source_status', [])}
    enabled_problems = []
    for source in (evidence.get('catalog') or {}).get('sources', []):
        if source.get('enabled'):
            state = states.get(source['id'], {})
            if (state.get('last_run') or {}).get('status') != 'success' or not state.get('last_success_at'):
                enabled_problems.append({'source_id': source['id'], 'reason': 'latest_collection_not_successful'})
    if core: warnings.append('coverage:core_source_problems')
    if enabled_problems: warnings.append('coverage:enabled_source_problems')
    if health.get('issues'): warnings.append('actions:stage_problems')
    if ledger is None: warnings.append('quota:ledger_unavailable')
    retry = ai.get('retry_after')
    try:
        waiting = bool(retry and datetime.fromisoformat(retry.replace('Z', '+00:00')) > instant)
    except (ValueError, TypeError):
        waiting = None
        warnings.append('ai:invalid_retry_time')
    day = instant.astimezone(ZoneInfo('America/Los_Angeles')).date().isoformat()
    usage = (ledger or {}).get('days', {}).get(day) or {}
    limit = cfg.get('requests_per_day')
    quota = {'day': day, 'timezone': 'America/Los_Angeles', 'daily_limit': limit,
             'requests': usage.get('requests', 0) if ledger is not None else None,
             'reserved_requests': usage.get('reserved_requests', 0) if ledger is not None else None,
             'input_tokens': usage.get('input_tokens', 0) if ledger is not None else None,
             'output_tokens': usage.get('output_tokens', 0) if ledger is not None else None,
             'unknown_usage_requests': usage.get('unknown_usage_requests', 0) if ledger is not None else None,
             'scope': 'repository_ledger_only_not_account_billing'}
    quota['remaining_unreserved'] = (max(0, limit - quota['requests'] - quota['reserved_requests'])
                                    if limit is not None and quota['requests'] is not None else None)
    project_reports = ai.get('projects') or []
    project_limits = cfg.get('project_daily_limits') or {'primary': limit, 'secondary': 500}
    quota['projects'] = []
    for identity, project_ledger in (('primary', ledger), ('secondary', evidence.get('ledger_secondary'))):
        lane = next((r for r in project_reports if r.get('id') == identity), {})
        configured = lane.get('configured', identity == 'primary') and lane.get('status') != 'duplicate_key'
        values = (project_ledger or {}).get('days', {}).get(day) or {}
        counts = {key: values.get(key, 0) if project_ledger is not None else None for key in
                  ('requests', 'reserved_requests', 'input_tokens', 'output_tokens', 'unknown_usage_requests')}
        if configured and project_ledger is None:
            warnings.append('quota:' + identity + '_ledger_unavailable')
        quota['projects'].append({'id': identity, 'configured': configured, 'day': day,
                                  'daily_limit': project_limits.get(identity), **counts})
    configured_budgets = [p for p in quota['projects'] if p['configured']]
    quota['combined'] = {key: (sum(p[key] for p in configured_budgets)
                              if all(type(p[key]) is int for p in configured_budgets) else None)
                         for key in ('daily_limit', 'requests', 'reserved_requests', 'input_tokens',
                                     'output_tokens', 'unknown_usage_requests')}
    quota['legacy_fields_project'] = 'primary'
    for lane in project_reports:
        if lane.get('configured') and lane.get('status') in (
                'service_wait', 'quota_wait', 'retry_wait', 'daily_limit', 'configuration_error', 'failed', 'duplicate_key'):
            warnings.append('ai:' + lane['id'] + ':' + lane['status'])
    baseline = evidence.get('baseline') or {}
    observation = None
    if baseline.get('observation_started_at'):
        started = datetime.fromisoformat(baseline['observation_started_at'].replace('Z', '+00:00'))
        hours = max(0, (instant - started).total_seconds() / 3600)
        before = baseline.get('baseline') or {}
        current_days = (evidence.get('metrics') or {}).get('days') or {}
        old_days = before.get('collection_days') or {}
        delta = lambda key: sum(d.get(key, 0) for d in current_days.values()) - sum(d.get(key, 0) for d in old_days.values())
        collected, backfill = delta('new_records'), delta('first_source_run_records')
        observation = {'started_at': started.isoformat(), 'baseline_snapshot_at': baseline.get('snapshot_at'),
                       'review_after': baseline.get('review_after'), 'elapsed_hours': round(hours, 2),
                       'full_24_hours_elapsed': hours >= 24,
                       'inventory_delta': len(rows) - before.get('content', len(rows)),
                       'pending_ai_delta': progress['pending'] - before.get('pending_ai_with_body', progress['pending']),
                       'collected_since_baseline_snapshot': collected,
                       'first_source_backfills': backfill, 'other_new_records': collected - backfill,
                       'note': 'Snapshot comparison; source backfills are not daily news output. No daily-rate extrapolation.'}
    return {'schema_version': 1, 'generated_at': instant.isoformat(), 'snapshot_at': snapshot.get('snapshot_at'), 'snapshot_key': snapshot_key(snapshot, evidence.get('catalog')),
            'status': 'attention' if warnings else 'ok', 'warnings': warnings,
            'translation': {**progress, 'api_completed': len(api), 'other_ai_completed': len(completed) - len(api),
                            'api_source_characters': sum(len(r.get('article_text') or '') for r in api),
                            'machine_count_scope': 'pending_AI_only; overlaps_pending_not_AI_completion'},
            'api': {**{key: ai.get(key) for key in ('status', 'model', 'error', 'started_at', 'finished_at', 'retry_after')},
                    'service_retry_policy': ai.get('service_retry_policy'),
                    'inline_service_retries': ai.get('inline_service_retries'),
                    'service_failures': ai.get('service_failures') or [],
                    'waiting_for_retry': waiting, 'last_run_requests': ai.get('requests'),
                    'projects': [{**{k: r.get(k) for k in ('id', 'configured', 'status', 'model', 'error', 'retry_after', 'requests_today')},
                                  'last_run_requests': r.get('requests'),
                                  'inline_service_retries': r.get('inline_service_retries'),
                                  'service_retry': r.get('service_retry'),
                                  'last_run_completed': len(r.get('translated') or []),
                                  'last_run_failed': r.get('failed') or []} for r in project_reports],
                    'last_run_completed': len(ai.get('translated') or []), 'last_run_failed': ai.get('failed') or []},
            'machine': {'status': machine.get('status'), 'last_run_completed': len(machine.get('translated') or []),
                        'last_run_failed': machine.get('failed') or [], 'finished_at': machine.get('finished_at')},
            'quota': quota, 'policy': {'execution': 'github-actions-only', 'chatgpt_translation_workers': False,
                                     'account_mode': cfg.get('account_mode'), 'paid_activation': cfg.get('paid_activation'),
                                     'backup_schedule': 'every_30_minutes_at_UTC_minutes_5_and_35; GitHub scheduling may be delayed',
                                     'requests_per_run': cfg.get('requests_per_run'),
                                     'requests_per_run_scope': 'per_project', 'parallel_projects_max': 2,
                                     'project_daily_limits': project_limits},
            'workflow_health': {'checked_at': health.get('checked_at'), 'stages': health.get('stages') or {},
                                'issues': health.get('issues') or []},
            'coverage': {'scope': important.get('scope', 'configured_sources_current_lists_only'),
                         'global_completeness': 'unknown', 'checked_at': important.get('checked_at'),
                         'core_source_problems': core, 'missing_important_items': important.get('missing_important_items') or [],
                         'enabled_source_problems': enabled_problems,
                         'priority_country_gaps': (important.get('editorial_regions') or {}).get('priority_country_gaps') or []},
            'observation': observation}


def load_operations(snapshot, root=ROOT, instant=None):
    files = {'ai': 'data/ai-translation-status.json', 'machine': 'data/auto-translation-status.json',
             'ledger': 'data/ai-translation-ledger.json', 'config': 'config/ai-translation.json',
             'health': 'data/automation-health.json', 'important': 'data/important-news-audit.json',
             'metrics': 'data/collection-metrics.json', 'baseline': 'data/ai-free-trial-baseline.json', 'catalog': 'config/sources.json'}
    evidence, unreadable = {}, []
    for key, name in files.items():
        try:
            evidence[key] = json.loads((root / name).read_text())
            if not isinstance(evidence[key], dict):
                raise ValueError('expected_report_object')
        except (OSError, ValueError):
            evidence[key] = None
            unreadable.append(key)
    try:
        secondary = root / 'data/ai-translation-ledger-secondary.json'
        evidence['ledger_secondary'] = json.loads(secondary.read_text()) if secondary.exists() else None
        if evidence['ledger_secondary'] is not None and not isinstance(evidence['ledger_secondary'], dict):
            raise ValueError('expected_report_object')
    except (OSError, ValueError):
        evidence['ledger_secondary'] = None
        unreadable.append('ledger_secondary')
    report = operations_report(snapshot, evidence, instant)
    if unreadable:
        report['status'] = 'attention'
        report['warnings'].extend('evidence:unavailable:' + key for key in unreadable)
    return report
