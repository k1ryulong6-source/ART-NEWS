"""Build the 幕間休息 promo film page.

promo/src/promo.html is the source. This script injects the site's own wordmark
outlines (from frontend/index.html), subsets the three OFL faces to the characters
the film uses, and writes:

  promo/index.html         standalone page (fonts from promo/fonts/)
  <--inline PATH>          optional single-file copy with fonts as data URIs

Usage:
  python promo/build.py [--serif-source NotoSerifTC[wght].ttf] [--sans-source NotoSansSC[wght].ttf]
                        [--inline out.html]

The upstream TTFs (google/fonts ofl/notoseriftc, ofl/notosanssc) are only needed to
re-subset after changing the film's text; without them the committed subsets in
promo/fonts/ are reused. The site's own Noto Sans SC subset lacks some kanji used in
Japanese titles, hence the upstream source for the sans face.
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


def wordmark_paths(symbol_id: str) -> tuple[str, str, str]:
    page = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    match = re.search(r'<symbol id="%s" viewBox="([^"]+)">(.*?)</symbol>' % re.escape(symbol_id), page, re.S)
    if not match:
        raise SystemExit(f"wordmark symbol {symbol_id} not found in frontend/index.html")
    paths = dict((cls or "ink", d) for cls, d in re.findall(r'<path(?: class="(wordmark-light)")? d="([^"]+)"', match.group(2)))
    return match.group(1), paths["ink"], paths["wordmark-light"]


def wordmark_svg(symbol_id: str, css_class: str) -> str:
    view_box, ink, light = wordmark_paths(symbol_id)
    _, _, width, height = (float(v) for v in view_box.split())
    return (f'<svg class="{css_class}" viewBox="{view_box}" style="aspect-ratio:{width:g}/{height:g}" '
            f'aria-hidden="true"><path d="{ink}"/><path class="light" d="{light}"/></svg>')


def edge_print(count: int, step: int, period: int) -> str:
    spans = []
    for i in range(count):
        k = i % period
        label = "幕間休息" if k == period // 2 else f"• {21 + k}&#8195;{21 + k}A"
        spans.append(f'<span style="left:{i * step}px">{label}</span>')
    return "".join(spans)


def strip_print() -> str:
    labels = ["幕間休息", "• 21", "21A"]
    return "".join(f'<span style="top:{i * 160 + 20}px">{labels[i % 3]}</span>' for i in range(13))


def used_text(page: str) -> str:
    text = re.sub(r"<style.*?</style>|<script.*?</script>", " ", page, flags=re.S)
    text = re.sub(r'\s(?:d|style|class|viewBox|href|src)="[^"]*"', " ", text)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    extra = "0123456789.,:;!?·•–—’‘“”()「」『』《》。，、；：！？－―・ ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
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


def coverage(font_path: Path, text: str) -> set[str]:
    from fontTools.ttLib import TTFont

    cmap = TTFont(str(font_path)).getBestCmap()
    return {c for c in text if ord(c) not in cmap and not c.isspace()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serif-source", type=Path, help="upstream NotoSerifTC[wght].ttf")
    parser.add_argument("--sans-source", type=Path, help="upstream NotoSansSC[wght].ttf")
    parser.add_argument("--inline", type=Path, help="also write a single-file copy with embedded fonts")
    args = parser.parse_args()

    page = (PROMO / "src" / "promo.html").read_text(encoding="utf-8")
    page = (page
            .replace("{{WORDMARK_H}}", wordmark_svg("wordmark", "wordmark-h"))
            .replace("{{WORDMARK_END}}", wordmark_svg("wordmark", "end-mark"))
            .replace("{{WORDMARK_V}}", wordmark_svg("wordmark-vertical", "wordmark-v"))
            .replace("{{EDGE_PRINT}}", edge_print(35, 120, 8))
            .replace("{{STRIP_PRINT}}", strip_print()))

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

    for key, path in fonts.items():
        # The Latin face only needs Latin; CJK falls through to the next face in the stack.
        wanted = "".join(c for c in text if ord(c) < 0x2000) if key == "FONT_NEWS" else text
        missing = "".join(sorted(coverage(path, wanted)))
        print(f"{path.name}: {path.stat().st_size:,} bytes; not covered: {missing or 'none'}")

    standalone = page
    for key, path in fonts.items():
        standalone = standalone.replace("{{%s}}" % key, f"fonts/{path.name}")
    head = '<!doctype html>\n<html lang="zh-Hant">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n</head>\n<body>\n'
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
