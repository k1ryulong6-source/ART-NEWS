#!/usr/bin/env python3
"""Backfill public exhibit introductions without re-reading accepted ones."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.exhibition_details import DETAILS, read_details, refresh_details, write_details
from backend.exhibitions import CATALOG, read_catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int, default=180)
    parser.add_argument('--catalogue', type=Path, default=CATALOG)
    parser.add_argument('--output', type=Path, default=DETAILS)
    args = parser.parse_args()
    if not 0 < args.limit <= 400:
        parser.error('limit must be between 1 and 400')
    result = refresh_details(read_catalog(args.catalogue), read_details(args.output), limit=args.limit)
    write_details(result, args.output)
    print(json.dumps(result['report'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
