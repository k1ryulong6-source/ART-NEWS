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
            ZoneInfo(row['timezone']);canonical_url(row['evidence_url'])
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
        },
        'languages': dict(Counter(row['language'] for row in content)),
        'event_countries': dict(Counter(row['country'] for row in events)),
        'event_types': dict(Counter(row['event_type'] for row in events)),
        'channels': dict(Counter(row['channel'] for row in content)),
        'source_content_counts': dict(by_source), 'failed_sources': failed,
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
