"""Re-fetch identified widget-contaminated bodies, accepting pure deletions only.

No model calls. Default is a dry run. The original snapshot remains in Git.
"""
import argparse
import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.articles import allowed_url, fetch_page, extract_article
from backend.article_cleanup import subset_indexes, remap_translations, cached_widget_indexes, widget_deletions_only
from backend.editorial import checked_result
from backend.storage import ROOT, Store, now


def contaminated(row):
    blocks = json.loads(row.get('article_blocks_json') or '[]')
    texts = {b.get('text', '').strip() for b in blocks}
    return ((row['source_id'] == 'artnet' and 'Sign up for our daily newsletter.' in texts)
            or (row['source_id'] in ('artnews', 'variety-film', 'deadline-film')
                and 'Related Articles' in texts)
            or (row['source_id'] == 'lenscratch' and 'Recommended' in texts))


def clean_saved_bodies(store, apply=False, limit=100, getter=None, pack_directory=None):
    catalog = {s['id']: s for s in json.loads((ROOT / 'config/sources.json').read_text())['sources'] if s['enabled']}
    with store.connect() as db:
        rows = [dict(r) for r in db.execute('SELECT * FROM content WHERE is_demo=0')]
    candidates = [r for r in rows if r['source_id'] in catalog and contaminated(r)]
    report = {'schema_version': 1, 'at': now(), 'mode': 'apply' if apply else 'dry-run',
              'candidates': len(candidates), 'changed': [], 'unchanged': [], 'deferred': [],
              'failed': [], 'removed_blocks': 0, 'removed_characters': 0,
              'preserved_ai': 0, 'preserved_machine': 0, 'updated_packs': []}
    packs = Path(pack_directory or ROOT / 'data/translations')

    def prepare(row):
        try:
            source = catalog[row['source_id']]
            url = allowed_url(row.get('article_source_url') or row['canonical_url'], source)
            if not url:
                raise ValueError('unverified_source_url')
            payload, resolved = (getter or fetch_page)(url, source)
            if not allowed_url(resolved, source):
                raise ValueError('unverified_redirect')
            fields = extract_article(payload, resolved, source)
            old = json.loads(row['article_blocks_json'])
            new = json.loads(fields.get('article_blocks_json') or '[]')
            if old == new:
                return row, None, 'unchanged'
            indexes = subset_indexes(old, new)
            if indexes is None or not widget_deletions_only(payload, resolved, source, old, indexes):
                # Do not mix newly edited prose into an existing translation.
                # Remove only complete widget runs proven against fetched DOM.
                indexes = cached_widget_indexes(payload, resolved, source, old)
                if indexes is None:
                    return row, None, 'not_proven_pure_deletion'
                new = [old[i] for i in indexes]
                fields = {k: row.get(k) for k in ('article_status', 'article_reason', 'article_author', 'article_extractor')}
                fields['article_blocks_json'] = json.dumps(new, ensure_ascii=False)
                fields['article_text'] = '\n\n'.join(b['text'] for b in new if b.get('text'))
                fields['article_hash'] = hashlib.sha256(fields['article_blocks_json'].encode()).hexdigest()
            fields.update(remap_translations(row, fields, indexes))
            # A cleanup must not silently turn an old public excerpt into a
            # purported full article, or erase previously identified authorship.
            if row['article_status'] == 'partial':
                fields.update(article_status='partial', article_reason=row['article_reason'])
            fields['article_author'] = row.get('article_author') or fields.get('article_author')
            pack_path = packs / (row['id'] + '.json')
            pack = None
            if pack_path.exists():
                existing = json.loads(pack_path.read_text())
                if existing.get('source_hash') == row['article_hash'] and existing.get('source_title') == row['title_original']:
                    checked_result(row, existing['translation'])
                    pack = {**existing, 'source_hash': fields['article_hash'],
                            'translation': {**existing['translation'], 'blocks': [
                                {**existing['translation']['blocks'][j], 'index': i}
                                for i, j in enumerate(indexes)]}}
                    checked_result({**row, **fields}, pack['translation'])
                    # Only update pack_hash when this actual pack supplied the
                    # existing AI body; preserve all historical review/model data.
                    review = json.loads(row.get('editorial_review_json') or '{}')
                    old_digest = hashlib.sha256(json.dumps(existing, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
                    if review.get('pack_hash') == old_digest:
                        review['pack_hash'] = hashlib.sha256(json.dumps(pack, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
                        fields['editorial_review_json'] = json.dumps(review, ensure_ascii=False)
            return row, (fields, indexes, pack_path, pack), None
        except Exception as exc:
            return row, None, 'failed:' + str(exc)[:160]

    for row, result, reason in ThreadPoolExecutor(max_workers=4).map(prepare, candidates[:max(0, min(200, limit))]):
        if reason:
            if reason == 'unchanged': report['unchanged'].append(row['id'])
            else: report['failed' if reason.startswith('failed:') else 'deferred'].append({'id': row['id'], 'reason': reason})
            continue
        fields, indexes, pack_path, pack = result
        if apply:
            with store.connect() as db:
                changed = db.execute('UPDATE content SET ' + ','.join(k + '=?' for k in fields)
                                     + ' WHERE id=? AND article_hash=?',
                                     [*fields.values(), row['id'], row['article_hash']]).rowcount
            if not changed:
                report['deferred'].append({'id': row['id'], 'reason': 'source_changed_during_cleanup'})
                continue
            if pack is not None:
                pack_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + '\n')
        report['changed'].append(row['id'])
        report['removed_blocks'] += len(json.loads(row['article_blocks_json'])) - len(indexes)
        report['removed_characters'] += len(row.get('article_text') or '') - len(fields['article_text'])
        report['preserved_ai'] += int(row.get('editorial_status') in ('reviewed', 'translated'))
        report['preserved_machine'] += int(bool(fields.get('article_translation_hash')))
        if pack is not None: report['updated_packs'].append(row['id'])
    report['status'] = 'partial' if report['failed'] or report['deferred'] else 'completed'
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--limit', type=int, default=100)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    store = Store(os.getenv('CULTURE_DESK_DB', ROOT / 'runtime/culture-desk.db'))
    result = clean_saved_bodies(store, apply=args.apply, limit=args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
