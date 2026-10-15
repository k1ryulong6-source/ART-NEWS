"""Bounded, read-only source audit; preserves every original and translation."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.storage import ROOT
from backend.quality_audit import audit_quality

parser = argparse.ArgumentParser()
parser.add_argument('--limit', type=int, default=20)
args = parser.parse_args()
report = audit_quality(json.loads((ROOT / 'data/live.json').read_text()),
                       json.loads((ROOT / 'config/sources.json').read_text()), ROOT / 'data/article-quality', args.limit)
(ROOT / 'data/article-quality-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in report.items()}, ensure_ascii=False))
