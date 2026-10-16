"""Build the 幕間休息 promo film page ("明日新聞台", an atompunk television advert).

promo/src/promo.html is the source. This script fills in:

  {{WORDMARK:cls}} the site's wordmark outline (frontend/index.html), split per character
  {{DOTS}}        land dots for the opening globe, from Natural Earth 110m (world-atlas)
  {{FONT_*}}      subsets of the site's OFL faces, cut to the characters the film uses
  {{SCORE}}       the score (promo/score.mp3, made by promo/score.py)

and writes promo/index.html (fonts from promo/fonts/), plus an optional single-file
copy with the fonts embedded.

Usage:
  python promo/build.py [--land land-110m.json]
                        [--serif-source NotoSerifTC[wght].ttf] [--sans-source NotoSansSC[wght].ttf]
                        [--retro-source ZCOOLQingKeHuangYou-Regular.ttf] [--righteous Righteous-Regular.ttf]
                        [--inline out.html]

ZCOOL QingKe HuangYou (google/fonts ofl/zcoolqingkehuangyou, OFL, no reserved name) is
subset; Righteous (ofl/righteous, OFL with reserved font name) is copied unmodified.

land-110m.json: https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/land-110m.json (ISC; Natural
Earth data, public domain); without it the committed promo/land-dots.json is reused.

The upstream font TTFs (google/fonts ofl/notoseriftc, ofl/notosanssc) are needed only
when the film's text changes; otherwise the committed subsets are reused.
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMO = ROOT / "promo"
FONTS = PROMO / "fonts"
SITE_FONTS = ROOT / "frontend" / "fonts"



# ── Wordmark ───────────────────────────────────────────────────────────────────
def wordmark_svg(css_class: str = "mark") -> str:
    page = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    match = re.search(r'<symbol id="wordmark" viewBox="([^"]+)">(.*?)</symbol>', page, re.S)
    if not match:
        raise SystemExit("wordmark symbol not found in frontend/index.html")
    view_box = match.group(1)
    paths = dict((cls or "ink", d) for cls, d in re.findall(r'<path(?: class="(wordmark-light)")? d="([^"]+)"', match.group(2)))
    # Split the single ink path into its subpaths and file each under its character by
    # where it starts: 幕 < 1050 ≤ 間 < 2200 ≤ 休 < 3400 ≤ 息.
    groups: list[list[str]] = [[], [], [], []]
    for sub in re.findall(r"M[^M]+", paths["ink"]):
        x = float(re.match(r"M\s*(-?[\d.]+)", sub).group(1))
        groups[0 if x < 1050 else 1 if x < 2200 else 2 if x < 3400 else 3].append(sub)
    parts = []
    for i, subs in enumerate(groups):
        inner = f'<path class="ink" d="{"".join(subs)}"/>'
        if i == 1:
            inner += f'<path class="light" d="{paths["wordmark-light"]}"/>'
        parts.append(f'<g class="c{i}">{inner}</g>')
    _, _, width, height = (float(v) for v in view_box.split())
    return (f'<svg class="{css_class}" viewBox="{view_box}" style="aspect-ratio:{width:g}/{height:g}" '
            f'aria-hidden="true">{"".join(parts)}</svg>')


# ── Land dots for the globe ──────────────────────────────────────────────────────
DOTS_FILE = PROMO / "land-dots.json"
STEP = 2.0


def topo_rings(topo: dict) -> list:
    scale, translate = topo["transform"]["scale"], topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        points = []
        for dx, dy in arc:
            x += dx
            y += dy
            points.append((x * scale[0] + translate[0], y * scale[1] + translate[1]))
        arcs.append(points)

    def ring(indices: list) -> list:
        out: list = []
        for index in indices:
            points = arcs[index] if index >= 0 else arcs[~index][::-1]
            out.extend(points[1:] if out else points)
        return out

    rings = []
    for geometry in topo["objects"]["land"]["geometries"]:
        polygons = geometry["arcs"] if geometry["type"] == "MultiPolygon" else [geometry["arcs"]]
        for polygon in polygons:
            rings.extend(ring(r) for r in polygon)
    return rings


def land_dots(path: Path) -> list:
    import numpy as np

    rings = topo_rings(json.loads(path.read_text(encoding="utf-8")))
    lons = np.arange(-180 + STEP / 2, 180, STEP)
    lats = np.arange(84 - STEP / 2, -60, -STEP)
    grid_lon, grid_lat = np.meshgrid(lons, lats)
    px, py = grid_lon.ravel(), grid_lat.ravel()
    inside = np.zeros(px.shape, dtype=bool)
    for ring in rings:                          # even-odd rule over every ring
        pts = np.array(ring)
        x1, y1 = pts[:-1, 0][:, None], pts[:-1, 1][:, None]
        x2, y2 = pts[1:, 0][:, None], pts[1:, 1][:, None]
        crosses = ((y1 > py) != (y2 > py)) & (px < (x2 - x1) * (py - y1) / np.where(y2 == y1, 1e-12, y2 - y1) + x1)
        inside ^= (crosses.sum(axis=0) % 2).astype(bool)
    dots: list = []
    for lon, lat in zip(px[inside], py[inside]):
        dots += [round(float(lon), 1), round(float(lat), 1)]
    return dots


# ── Fonts ──────────────────────────────────────────────────────────────────────
def used_text(page: str) -> str:
    text = re.sub(r"<style.*?</style>", " ", page, flags=re.S)
    text = re.sub(r'\s(?:d|style|class|viewBox|href|src)="[^"]*"', " ", text)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    extra = "0123456789.,:;!?·•–—’‘“”«»„()「」『』《》。，、；：！？－―・…　 ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    return "".join(sorted(set(text + extra) - {"\n", "\t"}))


def subset(source: Path, target: Path, text: str) -> None:
    from fontTools import subset as ft_subset

    options = ft_subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.name_legacy = True
    options.notdef_outline = True
    font = ft_subset.load_font(str(source), options)
    subsetter = ft_subset.Subsetter(options)
    subsetter.populate(text=text)
    subsetter.subset(font)
    ft_subset.save_font(font, str(target), options)


def not_covered(font_path: Path, text: str) -> str:
    from fontTools.ttLib import TTFont

    cmap = TTFont(str(font_path)).getBestCmap()
    return "".join(sorted({c for c in text if ord(c) not in cmap and not c.isspace()}))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--land", type=Path, help="world-atlas land-110m.json")
    parser.add_argument("--serif-source", type=Path, help="upstream NotoSerifTC[wght].ttf")
    parser.add_argument("--sans-source", type=Path, help="upstream NotoSansSC[wght].ttf")
    parser.add_argument("--retro-source", type=Path, help="upstream ZCOOLQingKeHuangYou-Regular.ttf")
    parser.add_argument("--righteous", type=Path, help="upstream Righteous-Regular.ttf (copied unmodified)")
    parser.add_argument("--inline", type=Path, help="also write a single-file copy with embedded fonts")
    args = parser.parse_args()

    if args.land:
        DOTS_FILE.write_text(json.dumps(land_dots(args.land), separators=(",", ":")) + "\n", encoding="utf-8")
    dots = DOTS_FILE.read_text(encoding="utf-8").strip()

    page = (PROMO / "src" / "promo.html").read_text(encoding="utf-8")
    page = re.sub(r"\{\{WORDMARK:([\w-]+)\}\}", lambda m: wordmark_svg(m.group(1)), page)
    page = page.replace("{{DOTS}}", dots)

    text = used_text(page.replace(dots, ""))
    FONTS.mkdir(exist_ok=True)
    fonts = {
        "FONT_TITLE": FONTS / "promo-title.woff2",
        "FONT_SANS": FONTS / "promo-sans.woff2",
        "FONT_NEWS": FONTS / "promo-news.woff2",
        "FONT_RETRO": FONTS / "promo-retro.woff2",
        "FONT_RIGHTEOUS": FONTS / "Righteous-Regular.ttf",
    }
    if args.serif_source:
        subset(args.serif_source, fonts["FONT_TITLE"], text)
    if args.sans_source:
        subset(args.sans_source, fonts["FONT_SANS"], text)
    if args.retro_source:
        subset(args.retro_source, fonts["FONT_RETRO"], text)
    if args.righteous:
        fonts["FONT_RIGHTEOUS"].write_bytes(args.righteous.read_bytes())
    subset(SITE_FONTS / "intermission-news-v1.woff2", fonts["FONT_NEWS"], text)
    latin = "".join(c for c in text if ord(c) < 0x2000)
    print(f"{fonts['FONT_SANS'].name}: not covered {not_covered(fonts['FONT_SANS'], text) or 'none'}")
    print(f"{fonts['FONT_NEWS'].name}: Latin not covered {not_covered(fonts['FONT_NEWS'], latin) or 'none'}")

    score = PROMO / "score.mp3"
    standalone = page.replace("{{SCORE}}", score.name)
    for key, path in fonts.items():
        standalone = standalone.replace("{{%s}}" % key, f"fonts/{path.name}")
    head = ('<!doctype html>\n<html lang="zh-Hant">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n</head>\n<body>\n')
    (PROMO / "index.html").write_text(head + standalone + "</body>\n</html>\n", encoding="utf-8")
    print("wrote promo/index.html")

    if args.inline:
        inline = page.replace("{{SCORE}}", "data:audio/mpeg;base64," + base64.b64encode(score.read_bytes()).decode("ascii"))
        for key, path in fonts.items():
            data = base64.b64encode(path.read_bytes()).decode("ascii")
            mime = "font/ttf" if path.suffix == ".ttf" else "font/woff2"
            inline = inline.replace("{{%s}}" % key, f"data:{mime};base64,{data}")
        args.inline.write_text(inline, encoding="utf-8")
        print(f"wrote {args.inline} ({args.inline.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
