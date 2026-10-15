"""Create a portable static edition using the same frontend and demo records."""
import json
import base64
import shutil
import sys
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

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
        from backend.operations import load_operations
        bundle['automation']['operations'] = load_operations(bundle['live'])
    # Compute all reporting from the full archive, then compact transport only.
    from backend.babel_export import export_articles, integrations
    output = ROOT / 'dist'
    output.mkdir(exist_ok=True)
    if bundle.get('automation', {}).get('operations'):
        (output / 'reports').mkdir(exist_ok=True)
        (output / 'reports/operations.json').write_text(json.dumps(bundle['automation']['operations'], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if bundle.get('coverage', {}).get('editorial_regions'):
        (output / 'reports').mkdir(exist_ok=True)
        (output / 'reports/regional-coverage.json').write_text(json.dumps(bundle['coverage']['editorial_regions'], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if bundle.get('coverage', {}).get('attention_units'):
        report = bundle['coverage']['attention_units']
        (output / 'reports/attention-units').mkdir(parents=True, exist_ok=True)
        (output / 'reports/attention-units.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        for unit in report['units']:
            (output / 'reports/attention-units' / (unit['id'] + '.json')).write_text(json.dumps(unit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        expected = {u['id'] + '.json' for u in report['units']}
        for path in (output / 'reports/attention-units').glob('*.json'):
            if path.name not in expected:
                path.unlink()
    bundle['integrations'] = integrations()
    site_url = bundle['integrations'].get('site_url')
    domain = bundle['integrations'].get('custom_domain')
    if domain:
        site = urlsplit(site_url or '')
        if site.scheme != 'https' or site.hostname != domain or site.netloc != domain or site.path not in ('', '/') or site.query or site.fragment:
            raise ValueError('custom_domain_must_match_https_site_url')
        (output / 'CNAME').write_text(domain + '\n', encoding='utf-8')
    else:
        (output / 'CNAME').unlink(missing_ok=True)
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
    if site_url:
        html = html.replace('</head>', '<link rel="canonical" href="' + escape(site_url, quote=True) + '">\n</head>')
        (output / 'index.html').write_text(html, encoding='utf-8')
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
