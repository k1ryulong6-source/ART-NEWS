"""Audit public metadata without guessing missing facts or changing records."""
import argparse
from collections import Counter
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.ingestion import canonical_url, GEAR, GEAR_MULTILINGUAL
from backend.reading import public_url


def audit_payload(snapshot, catalog, reference=None):
    reference = reference or (snapshot.get('snapshot_at') or datetime.now(timezone.utc).isoformat())[:10]
    today = date.fromisoformat(reference)
    content, events, links = (snapshot.get(key, []) for key in ('content', 'events', 'content_events'))
    errors, warnings = [], []
    def problem(code, record, target=errors):
        target.append({'code': code, 'id': record.get('id'), 'source_id': record.get('source_id')})
    urls, ids = Counter(), Counter()
    for row in content:
        ids[row['id']] += 1
        try: urls[canonical_url(row['canonical_url'])] += 1
        except (ValueError, KeyError): problem('invalid_content_url',row)
        if row.get('is_demo'): problem('demo_in_live_content',row)
        if row.get('original_page_url') and not public_url(row['original_page_url']): problem('unsafe_original_page_url',row)
        if row.get('original_embed_status') not in (None,'available','blocked','unavailable','unchecked'): problem('invalid_original_page_status',row)
        from backend.articles import STATUSES
        if row.get('article_status') not in STATUSES | {None}: problem('invalid_article_status',row)
        if row.get('article_blocks_json'):
            try:
                blocks = json.loads(row['article_blocks_json'])
                if not isinstance(blocks,list) or not blocks or not row.get('article_text') or not row.get('article_source_url') or not row.get('article_fetched_at'): problem('article_without_body_or_provenance',row)
                for block in blocks:
                    if block.get('type') not in ('paragraph','heading','quote','list_item','image'): problem('invalid_article_block',row)
                    if block.get('type') == 'image' and not public_url(block.get('url')): problem('unsafe_article_image',row)
            except (ValueError,TypeError,AttributeError): problem('invalid_article_json',row)
        if row.get('article_translation_hash') and not row.get('article_translation_json'): problem('translation_without_body',row)
        if row.get('editorial_status') == 'reviewed':
            from backend.editorial import checked_result
            try:
                translated = json.loads(row.get('editorial_blocks_json') or 'null')
                if not isinstance(translated,list): raise ValueError()
                checked_result(row, {'title_zh':row['editorial_title_zh'],'excerpt_zh':row['editorial_excerpt_zh'] or '',
                                     'blocks':[{'index':i,**block} for i,block in enumerate(translated)]})
                review=json.loads(row.get('editorial_review_json') or '{}')
                if review.get('approved') is not True or review.get('issues') != []: problem('editorial_without_approved_review',row)
            except (ValueError,TypeError,KeyError): problem('invalid_editorial_translation',row)
        if row.get('image_url') and (not public_url(row['image_url']) or not row.get('image_credit') or not row.get('image_source_url')): problem('image_without_safe_url_or_attribution',row)
        if len(row.get('excerpt_original') or '') > 281: problem('excerpt_exceeds_short_reading_limit',row)
        if GEAR.search(row.get('title_original','')) or GEAR_MULTILINGUAL.search(row.get('title_original','')): problem('equipment_review',row)
        if row.get('published_at'):
            try:
                stamp = datetime.fromisoformat(row['published_at'].replace('Z','+00:00'))
                if stamp.tzinfo is None: problem('publication_without_timezone',row)
                if (stamp.date()-today).days > 1: problem('future_publication',row,warnings)
            except ValueError: problem('invalid_publication',row)
        try:
            locations=json.loads(row.get('locations_json') or '[]')
            if not isinstance(locations,list) or any(not isinstance(p,dict) or not p.get('country') for p in locations): problem('invalid_locations',row)
        except (ValueError,TypeError): problem('invalid_locations',row)
    errors.extend({'code':'duplicate_url','url':url} for url,count in urls.items() if count>1)
    errors.extend({'code':'duplicate_content_id','id':id} for id,count in ids.items() if count>1)
    event_ids=Counter()
    for row in events:
        event_ids[row['id']]+=1
        if row.get('is_demo'):problem('demo_in_live_event',row)
        try:
            zone=ZoneInfo(row['timezone']);canonical_url(row['evidence_url'])
            for field in ('start_at','end_at','deadline_at'):
                if row.get(field):
                    value=datetime.fromisoformat(row[field].replace('Z','+00:00'))
                    if value.tzinfo is None or value.astimezone(zone).date().isoformat() != row['start_date'] and field != 'end_at':problem('invalid_event_instant',row)
            if row.get('time_status')=='conflict':
                problem('conflicting_official_time',row,warnings)
                if row.get('deadline_at'):problem('conflict_has_invented_deadline',row)
            if row['date_precision']=='day':
                start=date.fromisoformat(row['start_date']);end=date.fromisoformat(row['end_date']) if row.get('end_date') else start
                if end<start:problem('reversed_event_range',row)
            elif row['date_precision']=='month':date.fromisoformat(row['start_date']+'-01')
            elif row['date_precision']!='unknown' or row.get('start_date') or row.get('end_date'):problem('invalid_date_precision',row)
        except (ValueError,KeyError,TypeError):problem('invalid_event_date_or_evidence',row)
    errors.extend({'code':'duplicate_event_id','id':id} for id,count in event_ids.items() if count>1)
    for link in links:
        if link.get('content_id') not in ids or link.get('event_id') not in event_ids:errors.append({'code':'broken_content_event_link',**link})
    old=0
    for row in content:
        try:old += bool(row.get('published_at') and (today-date.fromisoformat(row['published_at'][:10])).days>30)
        except ValueError:pass
    by_source=Counter(row['source_id'] for row in content)
    enabled=[row for row in catalog['sources'] if row['enabled']]
    states={row['id']:row for row in snapshot.get('source_status',[])}
    failed=[id for id,state in states.items() if state.get('enabled') and state.get('last_run',{} ) and state['last_run']['status']=='failed']
    missing=[row['id'] for row in enabled if not by_source[row['id']]]
    return {
        'schema_version': 1, 'as_of': reference, 'snapshot_at': snapshot.get('snapshot_at'),
        'counts': {
            'content': len(content), 'events': len(events), 'enabled_sources': len(enabled),
            'old_publications_over_30_days': old,
            'missing_publication_date': sum(not row.get('published_at') for row in content),
            'unknown_story_place': sum(row.get('geography_status') == 'unknown' for row in content),
            'source_images': sum(bool(row.get('image_url')) for row in content),
            'original_excerpts': sum(bool(row.get('excerpt_original')) for row in content),
            'machine_translated_titles': sum(bool(row.get('translated_title_zh')) for row in content),
            'machine_translated_excerpts': sum(bool(row.get('translated_excerpt_zh')) for row in content),
            'original_pages_without_blocking_header': sum(row.get('original_embed_status') == 'available' for row in content),
            'original_pages_blocked_by_publisher': sum(row.get('original_embed_status') == 'blocked' for row in content),
            'original_pages_unavailable_or_unchecked': sum(row.get('original_embed_status') in ('unavailable','unchecked',None) for row in content),
            'collected_article_bodies': sum(row.get('article_status') == 'collected' for row in content),
            'partial_article_bodies': sum(row.get('article_status') == 'partial' for row in content),
            'article_bodies_not_obtained': sum(not row.get('article_blocks_json') for row in content),
            'machine_translated_article_bodies': sum(bool(row.get('article_translation_hash')) for row in content),
            'ai_reviewed_article_translations': sum(row.get('editorial_status')=='reviewed' for row in content),
            'ai_direct_article_translations': sum(row.get('editorial_status')=='translated' for row in content),
            'ai_completed_article_translations': sum(row.get('editorial_status') in ('reviewed','translated') for row in content),
        },
        'languages': dict(Counter(row['language'] for row in content)),
        'event_countries': dict(Counter(row['country'] for row in events)),
        'event_types': dict(Counter(row['event_type'] for row in events)),
        'channels': dict(Counter(row['channel'] for row in content)),
        'source_content_counts': dict(by_source), 'failed_sources': failed,
        'article_source_counts': {source['id']: dict(Counter(row.get('article_status') or 'pending' for row in content if row['source_id'] == source['id'])) for source in enabled},
        'enabled_sources_without_content': missing, 'errors': errors, 'warnings': warnings,
        'notes': ['旧资料保留供探索和收藏，不冒充近期新闻。',
                  '抓取时间不替代发布时间；未标注地点和票价不补造。',
                  '媒体总部不代表报道地区；国家菜单不代表完整覆盖。'],
    }



def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path)
    parser.add_argument('--strict',action='store_true')
    args=parser.parse_args()
    report=audit_payload(json.loads((ROOT/'data/live.json').read_text()),json.loads((ROOT/'config/sources.json').read_text()))
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'counts':report['counts'],'errors':len(report['errors']),'warnings':len(report['warnings']),'failed_sources':report['failed_sources']},ensure_ascii=False))
    if args.strict and report['errors']:raise SystemExit(1)


if __name__=='__main__':main()
