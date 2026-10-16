"""A bounded editorial watch: core feed outages, missing important items, AI backlog."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.storage import ROOT, now
from backend.priority import classify, rank_snapshot, priority_key
from backend.autonomous_translation import write_json
from backend.editorial_regions import regional_coverage

snapshot = json.loads((ROOT / 'data/live.json').read_text())
policy = json.loads((ROOT / 'config/news-watch.json').read_text())
audit_path = ROOT / 'data/coverage-audit.json'
audit = json.loads(audit_path.read_text()) if audit_path.exists() else {'sources': []}
states = {source['id']: source for source in snapshot.get('source_status', [])}
checks = {source['source_id']: source for source in audit['sources']}
inventory = {row['id'] for row in snapshot['content']}
problems, missing = [], []
for identifier in policy['core_sources']:
    state, check = states.get(identifier, {}), checks.get(identifier, {})
    reason = []
    if (state.get('last_run') or {}).get('status') == 'failed':
        reason.append('latest_collection_failed')
    success = state.get('last_success_at')
    if not success or (datetime.now(timezone.utc) - datetime.fromisoformat(success)).total_seconds() > policy['source_stale_hours'] * 3600:
        reason.append('no_recent_success')
    if check.get('status') in ('failed', 'partial'):
        reason.append('list_audit_' + check['status'])
    if reason:
        problems.append({'source_id': identifier, 'reasons': reason, 'last_success_at': success})
for check in audit['sources']:
    for row in check.get('missing') or []:
        if row['id'] in inventory:
            continue
        priority = classify(row)
        if priority['importance'] == 'high':
            missing.append({**row, 'translation_priority': priority, 'reference_url': check['reference_url']})
priorities = rank_snapshot(snapshot)
important = [{key: row.get(key) for key in ('id', 'source_id', 'title_original', 'canonical_url', 'language', 'article_status', 'editorial_status')}
             | {'translation_priority': priorities[row['id']], 'has_original_body': bool(row.get('article_blocks_json'))}
             for row in snapshot['content'] if priorities[row['id']]['importance'] == 'high' and priorities[row['id']]['fresh']]
important.sort(key=priority_key)
report = {'checked_at': now(), 'list_audit_at': audit.get('checked_at'),
          'scope': 'configured_sources_current_lists_only', 'global_completeness': 'unknown',
          'core_source_problems': problems, 'missing_important_items': missing,
          'editorial_regions': regional_coverage(snapshot, json.loads((ROOT / 'config/sources.json').read_text()), audit),
          'fresh_important_items': important,
          'awaiting_AI_count': sum(row['language'] != 'zh' and row['editorial_status'] not in ('reviewed', 'translated') for row in important),
          'without_original_body_count': sum(not row['has_original_body'] for row in important),
          'limitations': ['关键词重要性为自动初判，不能替代编辑判断。', '未接入媒体、滚动列表历史及未独立核验官方页面存在盲区。']}
write_json(ROOT / 'data/important-news-audit.json', report)
print(json.dumps({key: len(report[key]) for key in ('core_source_problems', 'missing_important_items', 'fresh_important_items')}))
