#!/usr/bin/env python3
"""Refresh the public Japan exhibition register without writing news data."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.exhibitions import CATALOG, build_catalog, config, read_catalog, write_catalog
from backend.exhibition_sources import scan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=CATALOG)
    args = parser.parse_args()
    prior = read_catalog(args.output)
    settings = config()
    observations, sources = scan(settings, prior.get('tab_known_areas'))
    result = build_catalog(prior, observations, sources, settings)
    write_catalog(result, args.output)
    audit = result['coverage']
    print(json.dumps({'checked_at': result['generated_at'], 'counts': audit['counts'],
                      'sources': {key: {k: entry[k] for k in ('complete', 'pages', 'collected')}
                                  for key, entry in audit['sources'].items()}}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
