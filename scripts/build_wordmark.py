"""Draw the 幕間休息 wordmarks and favicon from the self-hosted title face.

The title face (fonts/intermission-title-v1.woff2, Noto Serif TC subset) gives the thin
traditional Ming letterforms. The contours of the 日 inside 間 are emitted as a
separate path (class "wordmark-light") so the theme can print it in the accent
colour. Two symbols are printed for frontend/index.html — "wordmark" (horizontal,
masthead and footer) and "wordmark-vertical" (cover page) — and the favicon is
written to frontend/favicon.svg.

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
FACE = ROOT / 'frontend/fonts/intermission-title-v1.woff2'
TEXT = '幕間休息'


def glyph_paths(text, weight, gap, vertical=False):
    font = instantiateVariableFont(TTFont(FACE), {'wght': weight})
    glyphs, cmap = font.getGlyphSet(), font.getBestCmap()
    ink, light, offset = [], [], 0
    for char in text:
        name = cmap[ord(char)]
        bounds = BoundsPen(glyphs); glyphs[name].draw(bounds); x0, y0, x1, y1 = bounds.bounds
        pen = RecordingPen(); glyphs[name].draw(pen)
        dx, dy = (-x0 + (1000 - (x1 - x0)) / 2, offset - (880 - y1)) if vertical else (offset - x0, 0)
        contour = []
        for op, args in pen.value:
            contour.append((op, args))
            if op not in ('closePath', 'endPath'):
                continue
            xs = [p[0] for _, a in contour for p in a]; ys = [p[1] for _, a in contour for p in a]
            w, h = x1 - x0, y1 - y0
            inner = char == '間' and x0 + .25 * w < min(xs) and max(xs) < x1 - .25 * w and y0 + .05 * h < min(ys) and max(ys) < y1 - .3 * h
            (light if inner else ink).append(path_data(contour, dx, dy))
            contour = []
        offset += ((y1 - y0) if vertical else (x1 - x0)) + gap
    return ''.join(ink), ''.join(light)


def path_data(contour, dx, dy):
    out = []
    for op, args in contour:
        points = [(px + dx, 880 - py + dy) for px, py in args]
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


def box(ink, light):
    numbers = [int(v) for v in re.findall(r'-?\d+', ink + light)]
    xs, ys = numbers[0::2], numbers[1::2]
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def symbol(name, ink, light):
    x, y, w, h = box(ink, light)
    return f'<symbol id="{name}" viewBox="{x} {y} {w} {h}"><path d="{ink}"/><path class="wordmark-light" d="{light}"/></symbol>'


def main():
    sys.stdout.write(symbol('wordmark', *glyph_paths(TEXT, 300, 260)) + '\n')
    sys.stdout.write(symbol('wordmark-vertical', *glyph_paths(TEXT, 200, 300, vertical=True)) + '\n')
    ink, light = glyph_paths('間', 400, 0)
    x, y, w, h = box(ink, light)
    side = max(w, h) + 260; left, top = x - (side - w) // 2, y - (side - h) // 2
    (ROOT / 'frontend/favicon.svg').write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{left} {top} {side} {side}"><rect x="{left}" y="{top}" width="{side}" height="{side}" fill="#b3261e"/>'
        f'<path fill="#f6efe2" d="{ink}{light}"/></svg>\n', encoding='utf-8')


if __name__ == '__main__':
    main()
