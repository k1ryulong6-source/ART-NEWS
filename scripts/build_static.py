"""Create a portable static edition using the same frontend and demo records."""
import json
import base64
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.headlines import load_headlines
from backend.coverage import coverage_report
from backend.priority import rank_snapshot
from backend.presentation import browser_snapshot


def build():
    bundle = {
        "dataset": json.loads((ROOT / "data/demo.json").read_text(encoding="utf-8")),
        "preferences": json.loads((ROOT / "config/preferences.json").read_text(encoding="utf-8")),
        "regions": json.loads((ROOT / "config/regions.json").read_text(encoding="utf-8")),
        "sources": json.loads((ROOT / "config/sources.json").read_text(encoding="utf-8")),
    }
    live_path = ROOT / "data/live.json"
    if live_path.exists():
        bundle["live"] = json.loads(live_path.read_text(encoding="utf-8"))
        bundle["headlines"] = load_headlines(bundle["live"])
        bundle['priorities'] = rank_snapshot(bundle['live'])
        def optional_data(name):
            path = ROOT / 'data' / name
            return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
        bundle['coverage'] = coverage_report(bundle['live'], bundle['sources'],
                                             optional_data('coverage-audit.json'), optional_data('coverage-benchmarks.json'))
        bundle['coverage']['important_news'] = optional_data('important-news-audit.json')
        bundle['coverage']['collection_metrics'] = optional_data('collection-metrics.json')
        bundle['automation'] = {'translation': optional_data('auto-translation-status.json'),
                                'ai': optional_data('ai-translation-status.json'),
                                'health': optional_data('automation-health.json')}
    # Compute all reporting from the full archive, then compact transport only.
    from backend.babel_export import export_articles, integrations
    output = ROOT / 'dist'
    output.mkdir(exist_ok=True)
    bundle['integrations'] = integrations()
    if 'live' in bundle:
        export_articles(bundle['live'], bundle['sources'], output / 'integrations/babel')
    for key in ('live', 'dataset'): bundle[key] = browser_snapshot(bundle[key])
    text = "window.CULTURE_BOOTSTRAP = " + json.dumps(bundle, ensure_ascii=False, separators=(',', ':')).replace("<", "\\u003c") + ";\n"
    (ROOT / "frontend/data.js").write_text(text, encoding="utf-8")
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    for name in ("index.html", "styles.css", "theme.css", "favicon.svg", "data.js", "core.js", "ui.js", "app.js"):
        shutil.copy2(ROOT / "frontend" / name, output / name)
    if (output / 'fonts').exists():
        shutil.rmtree(output / 'fonts')
    shutil.copytree(ROOT / 'frontend/fonts', output / 'fonts')
    html = (output / "index.html").read_text(encoding="utf-8")
    # The portable edition embeds its own fonts, without external requests.
    html = html.replace('<link rel="preload" href="fonts/intermission-masthead-v1.woff2" as="font" type="font/woff2" crossorigin>', '')
    for name in ('styles.css', 'theme.css'):
        css = (output / name).read_text(encoding='utf-8')
        for font in sorted((output / 'fonts').glob('*.woff2')):
            css = css.replace('fonts/' + font.name, 'data:font/woff2;base64,' + base64.b64encode(font.read_bytes()).decode('ascii'))
        html = html.replace(f'<link rel="stylesheet" href="{name}">', '<style>' + css + '</style>')
    favicon = (output / "favicon.svg").read_bytes()
    html = html.replace('href="favicon.svg"', 'href="data:image/svg+xml;base64,' + base64.b64encode(favicon).decode('ascii') + '"')
    for name in ("data.js", "core.js", "ui.js", "app.js"):
        script = (output / name).read_text(encoding="utf-8").replace('</script', '<\\/script')
        html = html.replace(f'<script defer src="{name}"></script>', '')
        html = html.replace('</body>', '<script>' + script + '</script>\n</body>')
    (output / "culture-desk-preview.html").write_text(html, encoding="utf-8")
    print("Static edition built in dist/ (public live snapshot + separate demo; browser storage)")


if __name__ == "__main__":
    build()
