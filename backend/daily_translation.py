"""Small GitHub-readable inputs and validated ChatGPT-authored translation packs."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from .storage import ROOT, now
from .editorial import checked_result, publish_translation
from .headlines import load_headlines
from .priority import rank_snapshot, priority_key, policy, translation_batch

PROVIDER = 'chatgpt-direct:context-review-v1'


def import_packs(store, directory=None):
    directory = Path(directory or ROOT / 'data/translations')
    with store.connect() as db:
        rows = {r['id']: dict(r) for r in db.execute('SELECT * FROM content WHERE is_demo=0')}
    report = {'imported': [], 'unchanged': [], 'stale': [], 'invalid': []}
    for path in sorted(directory.glob('*.json')):
        if path.name.startswith('_'): continue
        try:
            if path.stat().st_size > 1_000_000: raise ValueError('translation_pack_too_large')
            pack = json.loads(path.read_text())
            id = pack.get('id')
            if pack.get('schema_version') != 1 or not re.fullmatch(r'live-[a-f0-9]{24}', id or '') or path.stem != id:
                raise ValueError('invalid_pack_identity')
            row = rows.get(id)
            if not row or not row.get('article_blocks_json'): raise ValueError('original_body_missing')
            if pack.get('source_hash') != row['article_hash'] or pack.get('source_title') != row['title_original']:
                report['stale'].append(id); continue
            if row['language'] == 'zh': raise ValueError('source_already_chinese')
            checked_result(row, pack.get('translation'))
            review = pack.get('review')
            direct = pack.get('quality_mode') == 'direct-ai'
            if not isinstance(review, dict) or review.get('issues') != [] or (direct and (review.get('status') != 'not_requested' or review.get('approved') is not False)) or (not direct and review.get('approved') is not True):
                raise ValueError('bilingual_review_not_approved')
            if pack.get('execution') not in ('interactive', 'scheduled'):
                raise ValueError('invalid_ai_provenance')
            digest = hashlib.sha256(json.dumps(pack, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            previous = json.loads(row.get('editorial_review_json') or '{}')
            if row.get('editorial_status') in ('reviewed','translated') and previous.get('pack_hash') == digest:
                report['unchanged'].append(id); continue
            review = {**review, 'pack_hash': digest, 'execution': pack['execution'], 'ai_not_human': True}
            changed = publish_translation(store, row, pack['translation'], PROVIDER,
                                          str(pack.get('draft_model') or 'ChatGPT direct translation')[:100],
                                          None if direct else 'ChatGPT bilingual second pass', review)
            report['imported' if changed else 'stale'].append(id)
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            report['invalid'].append({'file': path.name, 'reason': str(exc)[:160]})
    return report


def prepare_queue(snapshot, output=None):
    output = Path(output or ROOT / 'data')
    inputs = output / 'translation-input'
    inputs.mkdir(parents=True, exist_ok=True)
    sources = {s['id']: s.get('name', s['id']) for s in snapshot.get('sources', [])}
    priorities = rank_snapshot(snapshot)
    pending = []
    for row in snapshot['content']:
        if not row.get('article_blocks_json') or row.get('is_demo') or row['language'] == 'zh': continue
        original = {'schema_version': 1, 'id': row['id'], 'source_id': row['source_id'],
                    'source_name': sources.get(row['source_id'], row['source_id']), 'channel': row['channel'],
                    'language': row['language'], 'title_original': row['title_original'],
                    'excerpt_original': row.get('excerpt_original'), 'published_at': row.get('published_at'),
                    'article_hash': row['article_hash'], 'source_url': row.get('article_source_url') or row['canonical_url'],
                    'article_status': row['article_status'], 'blocks': json.loads(row['article_blocks_json'])}
        (inputs / (row['id'] + '.json')).write_text(json.dumps(original, ensure_ascii=False, indent=2) + '\n')
        if row.get('editorial_status') in ('reviewed','translated'): continue
        candidate = {k: original[k] for k in ('id','source_id','channel','language','title_original','published_at','article_hash')}
        candidate.update(input_path='data/translation-input/' + row['id'] + '.json',
                         characters=len(row.get('article_text') or ''), blocks=len(original['blocks']),
                         article_status=row['article_status'], translation_priority=priorities[row['id']])
        pending.append(candidate)
    # A bounded shortlist avoids downloading the entire 6+ MB snapshot in a task.
    # Rotate sources/channels; older items get a dedicated share instead of starving.
    pending.sort(key=priority_key)
    # The shortlist is a starting order, never the complete translation scope.
    # Every pending original is also accessible through small, exhaustive pages.
    queue_directory = output / 'translation-queue'
    queue_directory.mkdir(parents=True, exist_ok=True)
    pages = []
    backlog_all = list(pending)
    for offset in range(0, len(backlog_all), 30):
        filename = f'{offset // 30 + 1:04d}.json'
        page = {'schema_version': 1, 'snapshot_at': snapshot.get('snapshot_at'),
                'items': backlog_all[offset:offset + 30]}
        (queue_directory / filename).write_text(json.dumps(page, ensure_ascii=False, indent=2) + '\n')
        pages.append({'path': 'data/translation-queue/' + filename, 'count': len(page['items'])})
    for path in queue_directory.glob('*.json'):
        if path.name not in {p['path'].split('/')[-1] for p in pages}: path.unlink()
    headlines = load_headlines(snapshot, output / 'headlines')
    headline_pending = []
    for row in sorted(snapshot['content'], key=lambda r: r.get('published_at') or '', reverse=True):
        if row.get('is_demo') or row['language'] == 'zh' or row.get('title_zh') or row.get('editorial_status') in ('reviewed','translated') or row['id'] in headlines:
            continue
        headline_pending.append({'id': row['id'], 'source_id': row['source_id'], 'language': row['language'],
                                 'title_original': row['title_original'], 'excerpt_original': row.get('excerpt_original'),
                                 'input_path': 'data/translation-input/' + row['id'] + '.json' if row.get('article_blocks_json') else None})
    settings = policy(); limit = settings['shortlist_limit']
    selected, backlog_ids = translation_batch(pending, limit, settings['backlog_slots'])
    queue = {'schema_version': 1, 'snapshot_at': snapshot.get('snapshot_at'),
             'mode': 'chatgpt-direct', 'pending': len(pending),
             'reviewed': sum(r.get('editorial_status') == 'reviewed' for r in snapshot['content']),
             'direct_translated': sum(r.get('editorial_status') == 'translated' for r in snapshot['content']),
             'quality_mode': 'direct-ai', 'priority_policy_path': 'config/translation-priority.json',
             'pending_priority_counts': dict(Counter(r['translation_priority']['priority'] for r in pending)),
             'backlog_ids': backlog_ids,
             'frontpage_priority_ids': [identifier for identifier, rank in sorted(priorities.items(), key=lambda item: item[1].get('headline_order', 999)) if 'headline_order' in rank],
             'frontpage_waiting_ids': [row['id'] for row in pending if 'headline_order' in row['translation_priority']],
             'originals_without_body': sum(not r.get('article_blocks_json') for r in snapshot['content']),
             'instructions_path': 'docs/DAILY_TRANSLATION.md', 'glossary_path': 'config/translation.json',
             'pending_headlines': len(headline_pending), 'headlines_next': headline_pending[:120],
             'scope': 'all_existing_and_new_articles', 'pending_pages': pages,
             'pending_characters': sum(row['characters'] for row in pending),
             'blocked_without_body': [{'id': r['id'], 'title_original': r['title_original'],
                                       'source_id': r['source_id'], 'article_status': r.get('article_status'),
                                       'reason': r.get('article_reason')}
                                      for r in snapshot['content'] if not r.get('article_blocks_json') and not r.get('is_demo')],
             'next': selected}
    output.mkdir(exist_ok=True)
    (output / 'translation-queue.json').write_text(json.dumps(queue, ensure_ascii=False, indent=2) + '\n')
    return {'pending': len(pending), 'shortlist': len(selected), 'input_files': len(list(inputs.glob('*.json')))}
