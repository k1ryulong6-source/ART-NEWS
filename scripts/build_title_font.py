"""Build the small self-hosted title face used by the masthead wordmark and the cover page.

The title face is a subset of Noto Serif TC (SIL OFL 1.1), a thin Ming/Song style in
traditional characters, limited to the characters the cover and the wordmark set and
to weights 200–400. Daily builds never need this script; it documents how the
committed WOFF2 was made.

    python -m pip install 'fonttools[woff]'
    python scripts/build_title_font.py --source /path/to/NotoSerifTC[wght].ttf \
        [--source-sans-tc /path/to/NotoSansTC[wght].ttf]

The optional sans companion (Noto Sans TC, same design as the body face) carries the
traditional characters of section names that the simplified body subset lacks, so a
name such as 一種關注 in the navigation stays in the body typeface.
"""
import argparse
import hashlib
import json
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / 'frontend/fonts'
OUTPUT = 'intermission-title-v1.woff2'
SANS_TC_OUTPUT = 'intermission-sans-tc-v1.woff2'
SANS_TC_CHARS = '種關'
CHARS = '幕間休息藝術電影攝翻頁放映與展期圈內一種關注〇一二三四五六七八九十年月日星期第號0123456789・·'


def build(source, chars, output, family, weights, license_name, upstream):
    font = instantiateVariableFont(TTFont(source), {'wght': weights})
    options = subset.Options()
    options.flavor = 'woff2'
    options.layout_features = ['vert', 'vrt2', 'kern', 'palt', 'vpal']
    options.name_IDs = ['*']
    sub = subset.Subsetter(options)
    sub.populate(text=chars)
    sub.subset(font)
    for record in font['name'].names:
        if record.nameID in (1, 4, 16):
            record.string = family
        elif record.nameID == 6:
            record.string = family.replace(' ', '')
    out = FONTS / output
    font.flavor = 'woff2'
    font.save(out)
    manifest = json.loads((FONTS / 'manifest.json').read_text(encoding='utf-8'))
    manifest = [item for item in manifest if item['file'] != output] + [{
        'file': output, 'family': family,
        'upstream': upstream,
        'source_file': source.name,
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
        'bytes': out.stat().st_size, 'glyphs': len(font.getGlyphOrder()),
        'license': license_name}]
    (FONTS / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--source-sans-tc', type=Path)
    args = parser.parse_args()
    build(args.source, CHARS, OUTPUT, 'Intermission Title', (200, 400), 'notoseriftc-OFL.txt',
          'https://github.com/google/fonts/tree/main/ofl/notoseriftc')
    if args.source_sans_tc:
        build(args.source_sans_tc, SANS_TC_CHARS, SANS_TC_OUTPUT, 'Intermission Sans TC', (200, 900),
              'notosanstc-OFL.txt', 'https://github.com/google/fonts/tree/main/ofl/notosanstc')


if __name__ == '__main__':
    main()
