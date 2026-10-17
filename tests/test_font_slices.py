import json, re, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / 'frontend/fonts'


class SansSliceTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((FONTS / 'sans-v1/slices.json').read_text(encoding='utf-8'))

    def test_every_slice_has_one_rule_and_ranges_do_not_overlap(self):
        theme = (ROOT / 'frontend/theme.css').read_text(encoding='utf-8')
        rules = re.findall(r"url\(\"fonts/sans-v1/(\d+\.woff2)\"\)[^}]*unicode-range:([^}]+)\}", theme)
        self.assertEqual([name for name, _ in rules], [s['file'] for s in self.record['slices']])
        seen = set()
        for _, ranges in rules:
            for part in ranges.split(','):
                lo, _, hi = part.removeprefix('U+').partition('-')
                codes = set(range(int(lo, 16), int(hi or lo, 16) + 1))
                self.assertFalse(seen & codes); seen |= codes
        self.assertEqual(seen, {c for s in self.record['slices'] for c in s['codes']})
        for entry in self.record['slices']:
            self.assertEqual((FONTS / 'sans-v1' / entry['file']).stat().st_size, entry['bytes'])

    def test_slices_cover_exactly_the_whole_font(self):
        try:
            from fontTools.ttLib import TTFont
        except ImportError:
            self.skipTest('fonttools not installed')
        whole = set(TTFont(FONTS / 'intermission-sans-v1.woff2').getBestCmap())
        union = set()
        for entry in self.record['slices']:
            self.assertLessEqual(set(entry['codes']), set(TTFont(FONTS / 'sans-v1' / entry['file']).getBestCmap()))
            union |= set(entry['codes'])
        self.assertEqual(union, whole)
