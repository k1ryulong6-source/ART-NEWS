"""Lossless public snapshots: legacy JSON or an integrity-checked content manifest."""
import hashlib
import json
import re
from pathlib import Path

FORMAT = 'content-shards-v1'
DIRECTORY = 'snapshot-content'
SHARD_BYTES = 4 * 1024 * 1024
LEGACY_BYTES = 8 * 1024 * 1024
PART_PATH = re.compile(r'snapshot-content/[a-f0-9]{2}-[0-9]{4}\.json')


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')


def replace_file(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == payload:
        return
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_bytes(payload)
    temporary.replace(path)


def read_snapshot(path):
    path = Path(path)
    data = json.loads(path.read_bytes())
    storage = data.get('snapshot_storage') if isinstance(data, dict) else None
    if storage is None:
        if not isinstance(data, dict) or not isinstance(data.get('content'), list):
            raise ValueError('invalid_public_snapshot')
        return data
    if not isinstance(storage, dict) or storage.get('format') != FORMAT or 'content' in data:
        raise ValueError('invalid_snapshot_manifest')
    parts, order = storage.get('parts'), storage.get('content_order')
    if (not isinstance(parts, list) or not isinstance(order, list)
            or any(not isinstance(aid, str) or not aid for aid in order)
            or len(order) != len(set(order))):
        raise ValueError('invalid_snapshot_content_order')
    records, seen = {}, set()
    for part in parts:
        name = part.get('path') if isinstance(part, dict) else None
        if not isinstance(name, str) or not PART_PATH.fullmatch(name) or name in seen:
            raise ValueError('invalid_snapshot_part_path')
        seen.add(name)
        file = path.parent / name
        # A manifest must never make the loader read outside its data directory.
        if not file.resolve().is_relative_to(path.parent.resolve()):
            raise ValueError('invalid_snapshot_part_path')
        raw = file.read_bytes()
        if len(raw) != part.get('bytes') or hashlib.sha256(raw).hexdigest() != part.get('sha256'):
            raise ValueError('snapshot_part_integrity_mismatch:' + name)
        rows = json.loads(raw)
        if not isinstance(rows, list) or len(rows) != part.get('count'):
            raise ValueError('snapshot_part_count_mismatch:' + name)
        for row in rows:
            aid = row.get('id') if isinstance(row, dict) else None
            if not isinstance(aid, str) or not aid or aid in records:
                raise ValueError('duplicate_or_invalid_snapshot_id')
            records[aid] = row
    if len(records) != storage.get('content_count') or set(records) != set(order):
        raise ValueError('snapshot_content_coverage_mismatch')
    result = {key: value for key, value in data.items() if key != 'snapshot_storage'}
    result['content'] = [records[aid] for aid in order]
    return result


def write_snapshot(path, data, *, legacy_bytes=LEGACY_BYTES, shard_bytes=SHARD_BYTES):
    """Bound every tracked file without dropping, projecting or translating fields."""
    path = Path(path)
    if not isinstance(data, dict) or not isinstance(data.get('content'), list) or 'snapshot_storage' in data:
        raise ValueError('invalid_public_snapshot')
    if type(shard_bytes) is not int or shard_bytes < 128 or type(legacy_bytes) is not int or legacy_bytes < 0:
        raise ValueError('invalid_snapshot_file_limit')
    packed = encoded(data)
    if len(packed) <= legacy_bytes:
        replace_file(path, packed)
        return {'format': 'legacy-json', 'articles': len(data['content']), 'parts': 0, 'bytes': len(packed)}
    order, buckets = [], {}
    for row in data['content']:
        aid = row.get('id') if isinstance(row, dict) else None
        if not isinstance(aid, str) or not aid:
            raise ValueError('invalid_snapshot_article_id')
        order.append(aid)
        bucket = hashlib.sha256(aid.encode('utf-8')).hexdigest()[:2]
        buckets.setdefault(bucket, []).append(row)
    if len(order) != len(set(order)):
        raise ValueError('duplicate_snapshot_article_id')
    parts, planned = [], {}
    for bucket, rows in sorted(buckets.items()):
        chunk, size, number = [], 3, 0
        for row in sorted(rows, key=lambda row: row['id']):
            item_size = len(encoded(row))
            if item_size + 3 > shard_bytes:
                raise ValueError('snapshot_single_article_exceeds_shard_limit:' + row['id'])
            if chunk and size + item_size > shard_bytes:
                planned[f'{DIRECTORY}/{bucket}-{number:04d}.json'] = encoded(chunk)
                chunk, size, number = [], 3, number + 1
            chunk.append(row)
            size += item_size
        if chunk:
            planned[f'{DIRECTORY}/{bucket}-{number:04d}.json'] = encoded(chunk)
    for name, raw in planned.items():
        parts.append({'path': name, 'sha256': hashlib.sha256(raw).hexdigest(),
                      'bytes': len(raw), 'count': len(json.loads(raw))})
    manifest = {key: value for key, value in data.items() if key != 'content'}
    manifest['snapshot_storage'] = {'format': FORMAT, 'content_count': len(order),
                                    'content_order': order, 'parts': parts}
    payload = encoded(manifest)
    if len(payload) > max(LEGACY_BYTES, legacy_bytes):
        raise ValueError('snapshot_metadata_exceeds_file_limit')
    # Validate and prepare everything before replacing the manifest; never leave
    # it pointing to an incompletely written set. CI commits all paths together.
    for name, raw in planned.items():
        replace_file(path.parent / name, raw)
    replace_file(path, payload)
    folder = path.parent / DIRECTORY
    if folder.exists():
        for old in folder.glob('*.json'):
            name = old.relative_to(path.parent).as_posix()
            if PART_PATH.fullmatch(name) and name not in planned:
                old.unlink()
    return {'format': FORMAT, 'articles': len(order), 'parts': len(parts),
            'manifest_bytes': len(payload), 'largest_part_bytes': max(map(len, planned.values()), default=0)}
