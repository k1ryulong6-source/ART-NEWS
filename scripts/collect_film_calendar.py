#!/usr/bin/env python3
"""Refresh public official film calendars without issuing any translation requests."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.film_calendar import REGISTRY, read_calendar, refresh, write_calendar

if __name__ == '__main__':
    registry = json.loads(REGISTRY.read_text(encoding='utf-8'))
    result = refresh(read_calendar(), registry['sources'])
    write_calendar(result)
    print(json.dumps({'generated_at':result['generated_at'],'items':len(result['items']), 'sources':result['sources']},ensure_ascii=False,indent=2))
