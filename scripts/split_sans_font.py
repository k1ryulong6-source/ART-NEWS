"""Split the Chinese sans font into unicode-range slices so pages fetch only the characters they show.

Run once when the font or its character set changes (needs `fonttools[woff]`):
    python scripts/split_sans_font.py
The slice membership is written to frontend/fonts/sans-v1/slices.json and reused on later
runs, so routine article collection never changes the slices or invalidates browser caches.
Pass --reorder to rebuild the slices from current character frequencies in data/live.json.
"""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / 'frontend/fonts'
SOURCE = FONTS / 'intermission-sans-v1.woff2'
OUTPUT = FONTS / 'sans-v1'
THEME = ROOT / 'frontend/theme.css'
BEGIN, END = '/* sans-slices:begin (scripts/split_sans_font.py) */', '/* sans-slices:end */'
# First slice: ASCII, the other symbols site text uses, and the most frequent ideographs.
# Unused kana and symbols get slices of their own; the remaining ideographs follow by frequency.
FIRST_HAN = 1500
SIZES = ((3000, 40), (None, 120))


def is_han(code):
    return 0x3400 <= code <= 0x9FFF or 0xF900 <= code <= 0xFAFF or 0x20000 <= code <= 0x2FA1F


def frequencies(codes):
    live = json.loads((ROOT / 'data/live.json').read_text(encoding='utf-8'))
    counts = collections.Counter()
    for row in live.get('content', []):
        text = ''.join(str(row.get(key) or '') for key in ('editorial_title_zh', 'translated_title_zh', 'title_zh', 'summary_zh', 'editorial_excerpt_zh', 'translated_excerpt_zh'))
        for key in ('editorial_blocks_json', 'article_translation_json'):
            try:
                text += ''.join(str(b.get('text') or b.get('caption') or '') for b in json.loads(row.get(key) or '[]') if isinstance(b, dict))
            except (ValueError, TypeError, AttributeError):
                pass
        if row.get('language') == 'zh':
            text += str(row.get('article_text') or '')
        counts.update(ord(c) for c in text if ord(c) in codes)
    # Interface strings count too: they appear on every page.
    for name in ('index.html', 'app.js', 'ui.js', 'core.js'):
        counts.update({ord(c): 1000 for c in (FONTS.parent / name).read_text(encoding='utf-8') if ord(c) in codes})
    return counts


def plan(codes):
    counts = frequencies(codes)
    han = sorted((c for c in codes if is_han(c)), key=lambda c: (-counts[c], c))
    other = [c for c in codes if not is_han(c)]
    used = [c for c in other if c < 0x80 or counts[c]]
    kana = [c for c in other if c not in used and 0x3040 <= c <= 0x30FF]
    rest = [c for c in other if c not in used and c not in kana]
    slices = [sorted(used + han[:FIRST_HAN])] + [sorted(group) for group in (kana, rest) if group]
    start = FIRST_HAN
    for limit, size in SIZES:
        stop = len(han) if limit is None else min(limit, len(han))
        while start < stop:
            slices.append(sorted(han[start:min(start + size, stop)]))
            start = min(start + size, stop)
    return slices


def ranges(codes):
    out, start, prev = [], None, None
    for code in sorted(codes) + [None]:
        if start is not None and code == prev + 1:
            prev = code
            continue
        if start is not None:
            out.append(f'U+{start:X}' if start == prev else f'U+{start:X}-{prev:X}')
        start = prev = code
    return ','.join(out)


def main():
    from fontTools import subset
    from fontTools.ttLib import TTFont
    parser = argparse.ArgumentParser()
    parser.add_argument('--reorder', action='store_true')
    args = parser.parse_args()
    codes = set(TTFont(SOURCE).getBestCmap())
    record = OUTPUT / 'slices.json'
    if record.exists() and not args.reorder:
        slices = [s['codes'] for s in json.loads(record.read_text(encoding='utf-8'))['slices']]
        missing = codes - {c for s in slices for c in s}
        if missing:
            slices.append(sorted(missing))
    else:
        slices = plan(codes)
    OUTPUT.mkdir(exist_ok=True)
    for path in OUTPUT.glob('*.woff2'):
        path.unlink()
    rules, entries = [], []
    for index, members in enumerate(slices):
        font = TTFont(SOURCE)
        options = subset.Options()
        options.flavor = 'woff2'
        options.layout_features = ['*']
        options.name_IDs = ['*']
        options.notdef_outline = True
        sub = subset.Subsetter(options=options)
        sub.populate(unicodes=members)
        sub.subset(font)
        font.flavor = 'woff2'
        path = OUTPUT / f'{index:02d}.woff2'
        font.save(path)
        entries.append({'file': path.name, 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'codes': members})
        rules.append("@font-face{font-family:'Intermission Sans';src:url(\"fonts/sans-v1/%s\") format('woff2');font-weight:200 900;font-style:normal;font-display:swap;unicode-range:%s}" % (path.name, ranges(members)))
    record.write_text(json.dumps({'source': SOURCE.name, 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'slices': entries}, ensure_ascii=False) + '\n', encoding='utf-8')
    theme = THEME.read_text(encoding='utf-8')
    block = BEGIN + '\n' + '\n'.join(rules) + '\n' + END
    if BEGIN in theme:
        theme = re.sub(re.escape(BEGIN) + '.*?' + re.escape(END), lambda _: block, theme, flags=re.S)
    else:
        theme = re.sub(r"@font-face\{font-family:'Intermission Sans';src:url\(\"fonts/intermission-sans-v1\.woff2\"\)[^}]*\}", lambda _: block, theme, count=1)
    THEME.write_text(theme, encoding='utf-8')
    print(len(entries), 'slices,', sum(e['bytes'] for e in entries), 'bytes')


if __name__ == '__main__':
    main()
