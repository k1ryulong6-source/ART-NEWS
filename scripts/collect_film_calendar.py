#!/usr/bin/env python3
"""Refresh public official film calendars without issuing any translation requests."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.film_calendar import REGISTRY, read_calendar, refresh, write_calendar
from backend.film_metadata import read_metadata, refresh_metadata, write_metadata
from backend.snapshot_files import read_snapshot

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--metadata-only', action='store_true', help='Keep the saved theatre schedules and fill film metadata')
    parser.add_argument('--metadata-limit', default=44, type=int)
    parser.add_argument('--metadata-seconds', default=240, type=int)
    args = parser.parse_args()
    registry = json.loads(REGISTRY.read_text(encoding='utf-8'))
    saved = read_calendar()
    result = saved if args.metadata_only else refresh(saved, registry['sources'],
                                                      verified_premieres=registry.get('verified_premieres', ()))
    if not args.metadata_only:
        write_calendar(result)
    snapshot = REGISTRY.parent.parent / 'data/live.json'
    events = read_snapshot(snapshot)['events'] if snapshot.exists() else []
    metadata = refresh_metadata(result, events, read_metadata(), limit=args.metadata_limit, seconds=args.metadata_seconds)
    write_metadata(metadata)
    print(json.dumps({'generated_at': result['generated_at'], 'items': len(result['items']),
                      'sources': result['sources'], 'metadata': metadata['report']}, ensure_ascii=False, indent=2))
