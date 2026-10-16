"""Build the 幕間休息 promo film page ("一束光").

promo/src/promo.html is the source. This script fills in:

  {{WORDMARK}}    the site's wordmark outline (frontend/index.html), split per character
  {{SEATS}}       cinema seat silhouettes for the opening shot
  {{FONT_*}}      subsets of the site's OFL faces, cut to the characters the film uses

and writes promo/index.html (fonts from promo/fonts/), plus an optional single-file
copy with the fonts embedded.

Usage:
  python promo/build.py [--serif-source NotoSerifTC[wght].ttf] [--sans-source NotoSansSC[wght].ttf]
                        [--inline out.html]

The upstream font TTFs (google/fonts ofl/notoseriftc, ofl/notosanssc) are needed only
when the film's text changes; otherwise the committed subsets are reused.
"""
from __future__ import annotations

import argparse
import base64
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMO = ROOT / "promo"
FONTS = PROMO / "fonts"
SITE_FONTS = ROOT / "frontend" / "fonts"



# ── Wordmark ───────────────────────────────────────────────────────────────────
def wordmark_svg() -> str:
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
    return (f'<svg class="mark" viewBox="{view_box}" style="aspect-ratio:{width:g}/{height:g}" '
            f'aria-hidden="true">{"".join(parts)}</svg>')


# ── Cinema seats ───────────────────────────────────────────────────────────────
def seats() -> str:
    """Three rows of seat backs, darker and larger towards the camera, rim-lit from the
    screen on the left."""
    rows = [(150, 64, 54, 92, "#0d0b0a"), (205, 84, 70, 118, "#080706"), (268, 110, 92, 150, "#050404")]
    out = ['<defs><linearGradient id="rim" x1="0" x2="1"><stop offset="0" stop-color="#e9e2d3" stop-opacity=".28"/>'
           '<stop offset=".6" stop-color="#e9e2d3" stop-opacity=".06"/><stop offset="1" stop-color="#e9e2d3" stop-opacity="0"/></linearGradient></defs>']
    for index, (base, height, width, gap, fill) in enumerate(rows):
        x = -width / 2 + (index * 37) % gap
        while x < 1920 + width:
            top = base - height
            path = (f"M{x:.0f} 300V{top + 18:.0f}Q{x:.0f} {top:.0f} {x + 18:.0f} {top:.0f}"
                    f"H{x + width - 18:.0f}Q{x + width:.0f} {top:.0f} {x + width:.0f} {top + 18:.0f}V300Z")
            out.append(f'<path d="{path}" fill="{fill}"/>')
            out.append(f'<path d="M{x + 4:.0f} {top + 14:.0f}Q{x + 4:.0f} {top + 2:.0f} {x + 18:.0f} {top + 2:.0f}H{x + width * .6:.0f}" '
                       f'fill="none" stroke="url(#rim)" stroke-width="2"/>')
            x += gap
    return "".join(out)


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
    parser.add_argument("--serif-source", type=Path, help="upstream NotoSerifTC[wght].ttf")
    parser.add_argument("--sans-source", type=Path, help="upstream NotoSansSC[wght].ttf")
    parser.add_argument("--inline", type=Path, help="also write a single-file copy with embedded fonts")
    args = parser.parse_args()

    page = (PROMO / "src" / "promo.html").read_text(encoding="utf-8")
    page = page.replace("{{WORDMARK}}", wordmark_svg()).replace("{{SEATS}}", seats())

    text = used_text(page)
    FONTS.mkdir(exist_ok=True)
    fonts = {
        "FONT_TITLE": FONTS / "promo-title.woff2",
        "FONT_SANS": FONTS / "promo-sans.woff2",
        "FONT_NEWS": FONTS / "promo-news.woff2",
    }
    if args.serif_source:
        subset(args.serif_source, fonts["FONT_TITLE"], text)
    if args.sans_source:
        subset(args.sans_source, fonts["FONT_SANS"], text)
    subset(SITE_FONTS / "intermission-news-v1.woff2", fonts["FONT_NEWS"], text)
    latin = "".join(c for c in text if ord(c) < 0x2000)
    print(f"{fonts['FONT_SANS'].name}: not covered {not_covered(fonts['FONT_SANS'], text) or 'none'}")
    print(f"{fonts['FONT_NEWS'].name}: Latin not covered {not_covered(fonts['FONT_NEWS'], latin) or 'none'}")

    standalone = page
    for key, path in fonts.items():
        standalone = standalone.replace("{{%s}}" % key, f"fonts/{path.name}")
    head = ('<!doctype html>\n<html lang="zh-Hant">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n</head>\n<body>\n')
    (PROMO / "index.html").write_text(head + standalone + "</body>\n</html>\n", encoding="utf-8")
    print("wrote promo/index.html")

    if args.inline:
        inline = page
        for key, path in fonts.items():
            data = base64.b64encode(path.read_bytes()).decode("ascii")
            inline = inline.replace("{{%s}}" % key, f"data:font/woff2;base64,{data}")
        args.inline.write_text(inline, encoding="utf-8")
        print(f"wrote {args.inline} ({args.inline.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
