"""Four explicit completion gates; incomplete evidence can never mean done."""
from datetime import datetime, timezone
import hashlib
import json


def snapshot_key(snapshot, catalog=None):
    rows = [(r['id'], r.get('title_original'), r.get('article_hash'), r.get('editorial_status'),
             r.get('editorial_title_zh'), r.get('editorial_blocks_json')) for r in snapshot.get('content', []) if not r.get('is_demo')]
    rows.sort(key=lambda row: json.dumps(row, ensure_ascii=False, sort_keys=True))
    return hashlib.sha256(json.dumps([rows, catalog], ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def acceptance_report(operations, quality=None, trial=None, attention=None, queue=None, instant=None):
    quality, trial, attention, queue = quality or {}, trial or {}, attention or {}, queue or {}
    instant = instant or datetime.now(timezone.utc)
    progress, health = operations.get('translation') or {}, operations.get('workflow_health') or {}
    coverage = operations.get('coverage') or {}
    stages = health.get('stages') or {}
    unattended = []
    if not (operations.get('observation') or {}).get('full_24_hours_elapsed'): unattended.append('24_hour_window_not_finished')
    if not trial.get('complete'): unattended.append('actual_run_reports_not_fully_verified')
    if not trial.get('resumed_articles'): unattended.append('actual_checkpoint_resume_not_verified')
    if not trial.get('publication_verified'): unattended.append('current_public_snapshot_not_verified')
    if (operations.get('quota') or {}).get('requests') is None: unattended.append('request_ledger_unverified')
    for name in ('collection', 'translation', 'publication'):
        if stages.get(name, {}).get('status') not in ('healthy', 'running'):
            unattended.append('stage_not_verified:' + name)
    if (operations.get('api') or {}).get('status') in ('failed', 'configuration_error'):
        unattended.append('api_configuration_or_worker_failure')
    content = []
    if not quality.get('complete'): content.append('not_all_current_bodies_passed_public_markup_checks')
    if not quality.get('snapshot_key') or quality.get('snapshot_key') != operations.get('snapshot_key'):
        content.append('quality_evidence_not_for_current_snapshot')
    if quality.get('local_issues'): content.append('cached_body_or_missing_body_issues')
    translation = []
    if progress.get('pending') is None or progress['pending'] > 0: translation.append('foreign_full_text_backlog_remains')
    if progress.get('without_body') is None or progress['without_body'] > 0: translation.append('original_bodies_missing')
    if queue.get('frontpage_waiting_ids'): translation.append('headlines_waiting_for_AI')
    sources = []
    if coverage.get('core_source_problems'): sources.append('core_source_failures')
    if coverage.get('enabled_source_problems'): sources.append('enabled_source_collection_not_verified')
    if coverage.get('priority_country_gaps'): sources.append('priority_country_field_gaps')
    if coverage.get('missing_important_items'): sources.append('known_important_items_missing')
    if not coverage.get('checked_at'): sources.append('coverage_not_verified')
    units = attention.get('units') or []
    unit = next((u for u in units if u.get('id') == 'a-kind-of-attention'), None)
    if not unit or not unit.get('members'): sources.append('attention_unit_not_verified')
    else:
        for member in unit['members']:
            stamp = member.get('last_successful_fetch_at')
            try: age = (instant - datetime.fromisoformat(stamp.replace('Z', '+00:00'))).total_seconds() / 3600
            except (ValueError, TypeError, AttributeError): age = 999
            if member.get('collection_status') != 'success' or age > 6:
                sources.append('attention_source_not_current:' + str(member.get('source_id')))
    gates = {name: {'passed': not reasons, 'open_reasons': reasons} for name, reasons in [
        ('unattended_24h', unattended), ('article_quality', content), ('full_text_translation', translation), ('coverage_gaps', sources)]}
    return {'schema_version': 1, 'checked_at': instant.isoformat(), 'snapshot_at': operations.get('snapshot_at'), 'snapshot_key': operations.get('snapshot_key'),
            'all_ready': all(g['passed'] for g in gates.values()), 'gates': gates,
            'scope': 'point_in_time_acceptance_of_configured_sources_and_collected_public_text',
            'limitations': ['Not a claim of worldwide completeness or access to subscription-only text.',
                            'Program structure/source checks are not semantic or human translation review.'],
            'counts': {k: progress.get(k) for k in ('total', 'completed', 'api_completed', 'pending', 'without_body')},
            'quality': {k: quality.get(k) for k in ('remote_verified', 'remote_unchecked', 'complete')},
            'trial': {k: trial.get(k) for k in ('complete', 'completed_runs', 'requests', 'resumed_articles', 'validation_failures', 'service_aborted_runs')}}
