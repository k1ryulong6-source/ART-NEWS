"""Bounded offline translation with source-bound checkpoints and no chat session."""
import hashlib
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from .storage import ROOT, now
from .editorial import checked_result, numbers
from .offline_model import configuration, provider_name
from .priority import rank_snapshot, priority_key, translation_batch


def digest(row, provider):
    return hashlib.sha256(json.dumps([provider, row['title_original'], row.get('excerpt_original'),
                                     row['article_hash'], configuration()['max_source_tokens']],
                                    ensure_ascii=False).encode()).hexdigest()


def machine_ready(row):
    return (str(row.get('article_translation_provider') or '').startswith('offline-m2m100:')
            and row.get('translation_status') == 'machine'
            and bool(row.get('article_translation_hash') and row.get('article_translation_json')
                     and row.get('translated_title_zh'))
            and row.get('translation_input_hash') == digest(row, row['article_translation_provider']))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def read_checkpoint(path):
    try:
        value = json.loads(path.read_text())
        if not isinstance(value, dict) or not isinstance(value.get('outputs'), dict) or any(not isinstance(text, str) for text in value['outputs'].values()):
            return {}
        return value
    except (OSError, ValueError):
        return {}


def build_units(row, provider):
    blocks = json.loads(row['article_blocks_json'])
    fields = [('title', row['title_original']), ('excerpt', row.get('excerpt_original') or '')]
    for index, block in enumerate(blocks):
        for field in (('caption', 'alt') if block['type'] == 'image' else ('text',)):
            fields.append((f'block:{index}:{field}', block.get(field) or ''))
    units, keys = [], {}
    for field, text in fields:
        parts = provider.split(text)
        keys[field] = []
        for index, part in enumerate(parts):
            key = f'{field}:{index}'
            units.append((key, part))
            keys[field].append(key)
    return blocks, units, keys


def assemble(original, keys, outputs):
    join = lambda field: ''.join(outputs[key] for key in keys[field])
    blocks = []
    for index, block in enumerate(original):
        result = {'index': index}
        for field in (('caption', 'alt') if block['type'] == 'image' else ('text',)):
            result[field] = join(f'block:{index}:{field}')
        blocks.append(result)
    return {'title_zh': join('title'), 'excerpt_zh': join('excerpt'), 'blocks': blocks, 'notes': []}


def run_autonomous(store, provider, directory=None, *, seconds=None, articles=None, characters=None, clock=time.monotonic):
    cfg = configuration()
    directory = Path(directory or ROOT / 'data/auto-translation-progress')
    directory.mkdir(parents=True, exist_ok=True)
    start = clock()
    time_limit = cfg['seconds_per_run'] if seconds is None else seconds
    article_limit = cfg['articles_per_run'] if articles is None else articles
    character_limit = cfg['characters_per_run'] if characters is None else characters
    snapshot = store.dataset('live')
    priorities = rank_snapshot(snapshot)
    rows = [row for row in snapshot['content'] if not row.get('is_demo') and row['language'] != 'zh'
            and row.get('article_blocks_json') and row.get('editorial_status') not in ('reviewed', 'translated')
            and not machine_ready(row)]
    for row in rows:
        row['translation_priority'] = priorities[row['id']]
    rows.sort(key=priority_key)
    deferred = []
    eligible = []
    for row in rows:
        path = directory / (row['id'] + '.json')
        previous = read_checkpoint(path)
        if previous.get('input_hash') == digest(row, provider.name) and previous.get('retry_after', '') > now():
            deferred.append(row['id'])
        else:
            eligible.append(row)
    selected, _ = translation_batch(eligible, article_limit, cfg['backlog_slots'])
    report = {'provider': provider.name, 'status': 'completed', 'started_at': now(), 'translated': [],
              'resumed': [], 'deferred': deferred, 'failed': [], 'unsupported': [], 'stale': [],
              'characters': 0, 'units': 0, 'pending_before': len(rows)}
    for row in selected:
        if not re.fullmatch(r'live-[a-f0-9]{24}', row['id']):
            raise ValueError('invalid_content_id')
        path = directory / (row['id'] + '.json')
        fingerprint = digest(row, provider.name)
        state = read_checkpoint(path)
        if state.get('input_hash') != fingerprint:
            state = {'schema_version': 1, 'id': row['id'], 'input_hash': fingerprint, 'provider': provider.name,
                     'source_hash': row['article_hash'], 'outputs': {}}
        if row['language'] not in cfg['supported_languages']:
            report['unsupported'].append(row['id'])
            continue
        if state.get('retry_after') and state['retry_after'] > now():
            report['deferred'].append(row['id'])
            continue
        original, units, keys = build_units(row, provider)
        if state['outputs']:
            report['resumed'].append(row['id'])
        exhausted = False
        try:
            for key, text in units:
                if key in state['outputs']:
                    continue
                if clock() - start >= time_limit or (report['characters'] and report['characters'] + len(text) > character_limit):
                    report['status'] = 'time_budget' if clock() - start >= time_limit else 'character_budget'
                    exhausted = True
                    break
                translated = provider.translate(text, row['language'])
                if not isinstance(translated, str) or not translated.strip():
                    raise ValueError('empty_translation')
                if not numbers(text) <= numbers(translated):
                    raise ValueError('numbers_missing:' + key)
                if len(translated) > max(2000, len(text) * 5):
                    raise ValueError('translation_expansion')
                state['outputs'][key] = translated
                state.pop('retry_after', None)
                state.pop('error', None)
                report['characters'] += len(text)
                report['units'] += 1
                # Each accepted unit survives cancellation or a failed later unit.
                write_json(path, state)
            if exhausted:
                write_json(path, state)
                break
            translation = assemble(original, keys, state['outputs'])
            checked = checked_result(row, translation)
            target = hashlib.sha256((provider.name + row['article_hash'] + row['title_original']).encode()).hexdigest()
            with store.connect() as db:
                changed = db.execute("UPDATE content SET article_translation_json=?,article_translation_hash=?,article_translation_provider=?,article_translation_at=?,translated_title_zh=?,translated_excerpt_zh=?,translation_provider=?,translation_status='machine',translation_input_hash=?,translation_generated_at=? WHERE id=? AND article_hash=? AND title_original=? AND coalesce(editorial_status,'') NOT IN ('reviewed','translated')",
                                     (json.dumps(checked['blocks'], ensure_ascii=False), target, provider.name, now(), checked['title_zh'],
                                      checked['excerpt_zh'], provider.name, fingerprint, now(), row['id'], row['article_hash'], row['title_original'])).rowcount
            report['translated' if changed else 'stale'].append(row['id'])
            path.unlink(missing_ok=True)
        except Exception as error:
            # Do not copy unverified foreign text into a supposedly finished
            # translation. Keep the original readable and retry this source later.
            state['error'] = str(error)[:160] if isinstance(error, ValueError) else type(error).__name__
            state['retry_after'] = (datetime.now(timezone.utc) + timedelta(hours=cfg['retry_hours'])).isoformat()
            write_json(path, state)
            report['failed'].append({'id': row['id'], 'reason': state['error']})
    report['finished_at'] = now()
    report['seconds'] = round(clock() - start, 2)
    report['pending_after'] = report['pending_before'] - len(report['translated'])
    if report['failed'] and report['status'] == 'completed':
        report['status'] = 'partial_failure'
    for path in directory.glob('*.json'):
        current = next((row for row in snapshot['content'] if row['id'] == path.stem), None)
        if current is None or current.get('editorial_status') in ('reviewed', 'translated') or machine_ready(current):
            path.unlink()
    return report
