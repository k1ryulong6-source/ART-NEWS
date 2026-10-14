"""Draw the 幕间休息 wordmark and favicon from the self-hosted Noto Sans SC outlines.

The wordmark is Noto Sans SC at weight 900 with tightened spacing; the contours of
the 日 inside 间 are emitted as a separate path (class "wordmark-light") so the
theme can print it in the accent colour. Output is printed for pasting into
frontend/index.html (the <symbol id="wordmark">) and written to frontend/favicon.svg.

Optional tooling only: python -m pip install 'fonttools[woff]'
"""
import re
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]
ASCENT, GAP = 880, 80


def glyph_paths(text):
    font = instantiateVariableFont(TTFont(ROOT / 'frontend/fonts/intermission-sans-v1.woff2'), {'wght': 900})
    glyphs, cmap = font.getGlyphSet(), font.getBestCmap()
    ink, light, x = [], [], 0
    for char in text:
        name = cmap[ord(char)]
        bounds = BoundsPen(glyphs); glyphs[name].draw(bounds); x0, y0, x1, y1 = bounds.bounds
        pen = RecordingPen(); glyphs[name].draw(pen)
        contour = []
        for op, args in pen.value:
            contour.append((op, args))
            if op not in ('closePath', 'endPath'):
                continue
            xs = [p[0] for _, a in contour for p in a]; ys = [p[1] for _, a in contour for p in a]
            inner = char == '间' and x0 + 180 < min(xs) and max(xs) < x1 - 180 and y0 + 60 < min(ys) and max(ys) < y1 - 200
            (light if inner else ink).append(path_data(contour, x - x0))
            contour = []
        x += (x1 - x0) + GAP
    return ''.join(ink), ''.join(light), x - GAP


def path_data(contour, dx):
    out = []
    for op, args in contour:
        points = [(px + dx, ASCENT - py) for px, py in args]
        if op == 'moveTo':
            out.append('M%d %d' % tuple(map(round, points[0])))
        elif op == 'lineTo':
            out.append('L%d %d' % tuple(map(round, points[0])))
        elif op == 'qCurveTo':
            for i in range(len(points) - 1):
                c = points[i]
                e = points[i + 1] if i == len(points) - 2 else ((points[i][0] + points[i + 1][0]) / 2, (points[i][1] + points[i + 1][1]) / 2)
                out.append('Q%d %d %d %d' % (round(c[0]), round(c[1]), round(e[0]), round(e[1])))
        elif op == 'curveTo':
            out.append('C' + ' '.join('%d %d' % (round(a), round(b)) for a, b in points))
        elif op == 'closePath':
            out.append('Z')
    return ''.join(out)


def view_box(ink, light, width):
    ys = [int(v) for v in re.findall(r'-?\d+', ink + light)[1::2]]
    return 0, min(ys), width, max(ys) - min(ys)


def main():
    ink, light, width = glyph_paths('幕间休息')
    x, y, w, h = view_box(ink, light, width)
    sys.stdout.write(f'<symbol id="wordmark" viewBox="{x} {y} {w} {h}"><path d="{ink}"/><path class="wordmark-light" d="{light}"/></symbol>\n')
    ink, light, width = glyph_paths('间')
    x, y, w, h = view_box(ink, light, width)
    side = max(w, h) + 220; left, top = x - (side - w) // 2, y - (side - h) // 2
    (ROOT / 'frontend/favicon.svg').write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{left} {top} {side} {side}"><rect x="{left}" y="{top}" width="{side}" height="{side}" fill="#151412"/>'
        f'<path fill="#f3efe4" d="{ink}"/><path fill="#c4281c" d="{light}"/></svg>\n', encoding='utf-8')


if __name__ == '__main__':
    main()
