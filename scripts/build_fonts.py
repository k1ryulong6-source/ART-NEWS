"""Rebuild committed OFL webfonts; optional tooling, never needed by Pages.

Install fonttools[woff], download the upstream files listed in
frontend/fonts/README.md, then pass their directory via --source-dir.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'frontend/fonts'
FONTS = [
    ('mashanzheng', 'MaShanZheng-Regular.ttf', 'intermission-masthead-v1.woff2', 'Intermission Masthead'),
    ('notosanssc', 'NotoSansSC[wght].ttf', 'intermission-sans-v1.woff2', 'Intermission Sans'),
    ('newsreader', 'Newsreader[opsz,wght].ttf', 'intermission-news-v1.woff2', 'Intermission News'),
]


def common_characters():
    # Stable common Chinese coverage also serves future refreshes. Uncommon
    # new characters use the system serif fallback without dropping text.
    text = ''.join(chr(c) for c in range(32, 127))
    for lead in range(0xA1, 0xF8):
        for trail in range(0xA1, 0xFF):
            try:
                text += bytes([lead, trail]).decode('gb2312')
            except UnicodeDecodeError:
                pass
    text += ''.join(chr(c) for c in range(0x3000, 0x3100))
    text += '幕间休息艺术电影摄影原文待译文化新闻收藏资料中文全球日本'
    return ''.join(sorted(set(text)))


def build(source_dir):
    OUTPUT.mkdir(exist_ok=True)
    charset = OUTPUT / 'song-charset.txt'
    if not charset.exists():
        charset.write_text(common_characters(), encoding='utf-8')
    records = []
    for upstream, filename, output, family in FONTS:
        source = source_dir / filename
        font = TTFont(source)
        # Derivatives use their own internal family/PostScript names.
        for name_id, value in [(1, family), (4, family), (6, family.replace(' ', '')), (16, family)]:
            font['name'].setName(value, name_id, 3, 1, 0x409)
        options = subset.Options()
        options.flavor = 'woff2'
        options.layout_features = ['*']
        options.name_IDs = ['*']
        sub = subset.Subsetter(options=options)
        if upstream == 'mashanzheng':
            sub.populate(text='幕间休息')
        elif upstream == 'notosanssc':
            sub.populate(text=charset.read_text(encoding='utf-8'))
        else:
            sub.populate(unicodes=list(font.getBestCmap()))
        sub.subset(font)
        font.flavor = 'woff2'
        path = OUTPUT / output
        font.save(path)
        shutil.copyfile(source_dir / (upstream + '-OFL.txt'), OUTPUT / (upstream + '-OFL.txt'))
        record = {'file': output, 'family': family, 'upstream': f'https://github.com/google/fonts/tree/main/ofl/{upstream}',
                  'source_file': filename, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                  'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size,
                  'glyphs': len(font.getBestCmap()), 'license': upstream + '-OFL.txt'}
        records.append(record)
        print(output, record['bytes'], 'bytes', record['glyphs'], 'characters')
    (OUTPUT / 'manifest.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, required=True)
    build(parser.parse_args().source_dir)
