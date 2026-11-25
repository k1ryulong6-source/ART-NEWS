"""Create a portable static edition using the same frontend and demo records."""
import json
import re
import base64
import shutil
import sys
from datetime import timedelta
from hashlib import sha256
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.snapshot_files import read_snapshot
from backend.headlines import load_headlines
from backend.coverage import coverage_report
from backend.priority import rank_snapshot, reference_time
from backend.presentation import browser_snapshot
from backend.exhibitions import read_catalog
from backend.exhibition_assets import description_counts, exhibition_entry, write_exhibition_files
from backend.exhibition_details import read_details
from backend.film_calendar import read_calendar


def build():
    bundle = {
        "dataset": json.loads((ROOT / "data/demo.json").read_text(encoding="utf-8")),
        "preferences": json.loads((ROOT / "config/preferences.json").read_text(encoding="utf-8")),
        "regions": json.loads((ROOT / "config/regions.json").read_text(encoding="utf-8")),
        "sources": json.loads((ROOT / "config/sources.json").read_text(encoding="utf-8")),
    }
    live_path = ROOT / "data/live.json"
    if live_path.exists():
        bundle["live"] = read_snapshot(live_path)
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
    bundle['film_calendar'] = read_calendar()
    calendar_data = json.dumps(bundle['film_calendar'], ensure_ascii=False, separators=(',', ':'))
    (output / 'film-calendar.json').write_text(calendar_data, encoding='utf-8')
    bundle['film_store'] = 'film-calendar.json?v=' + sha256(calendar_data.encode()).hexdigest()[:12]
    event_sources = {}
    for snapshot in (bundle.get('live', {}), bundle['dataset']):
        source_of = {row['id']: row.get('source_id') for row in snapshot.get('content', [])}
        for link in snapshot.get('content_events', []):
            if source := source_of.get(link['content_id']):
                event_sources.setdefault(link['event_id'], set()).add(source)
    bundle['calendar_event_sources'] = {event_id: sorted(sources) for event_id, sources in event_sources.items()}
    exhibition_catalog = read_catalog()
    exhibition_details = read_details()
    exhibition_revision, exhibition_items = write_exhibition_files(output / 'exhibitions', exhibition_catalog, exhibition_details, bundle.get('live', {}))
    bundle['japan_exhibitions'] = {**exhibition_catalog, 'items': exhibition_items, 'includes_legacy_events': True}
    bundle['exhibition_details'] = exhibition_details
    bundle['exhibition_store'] = 'exhibitions/catalogue.json?v=' + exhibition_revision
    bundle['exhibition_revision'] = exhibition_revision
    (output / 'japan-exhibitions.json').write_text(json.dumps(exhibition_catalog, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    if exhibition_catalog['coverage']:
        (output / 'reports').mkdir(exist_ok=True)
        bundle['exhibition_report'] = 'reports/japan-exhibitions.json'
        report = {'generated_at': exhibition_catalog['generated_at'], **exhibition_catalog['coverage'],
                  'public_descriptions': description_counts(exhibition_catalog, exhibition_details)}
        (output / bundle['exhibition_report']).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if bundle.get('automation', {}).get('operations'):
        (output / 'reports').mkdir(exist_ok=True)
        (output / 'reports/operations.json').write_text(json.dumps(bundle['automation']['operations'], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        for filename in ('acceptance.json', 'article-quality-report.json', 'autonomous-trial-report.json'):
            path = ROOT / 'data' / filename
            if path.exists(): shutil.copy2(path, output / 'reports' / filename)
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
    def bootstrap(value):
        return "window.CULTURE_BOOTSTRAP = " + json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace("<", "\\u003c") + ";\n"
    # The local app and single-file preview keep bodies inline; the site loads them on demand.
    text = bootstrap(bundle)
    (ROOT / "frontend/data.js").write_text(text, encoding="utf-8")
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    for name in ("index.html", "styles.css", "theme.css", "favicon.svg", "apple-touch-icon.png", "og-image.png", "core.js", "ui.js", "exhibitions.js", "calendar.js", "app.js"):
        shutil.copy2(ROOT / "frontend" / name, output / name)
    (output / 'exhibition-page.js').unlink(missing_ok=True)
    write_split_site(bundle, output, bootstrap)
    if (output / 'fonts').exists():
        shutil.rmtree(output / 'fonts')
    shutil.copytree(ROOT / 'frontend/fonts', output / 'fonts', ignore=shutil.ignore_patterns('slices.json'))
    html = (output / "index.html").read_text(encoding="utf-8")
    if site_url:
        html = html.replace('</head>', '<link rel="canonical" href="' + escape(site_url, quote=True) + '">\n</head>')
    public_html = version_assets(html, output)
    (output / 'index.html').write_text(public_html, encoding='utf-8')
    (output / 'exhibitions/index.html').write_text(exhibition_entry(public_html), encoding='utf-8')
    if 'live' in bundle:
        from backend.share_pages import write_share_pages
        write_share_pages(output, public_html, bundle['live'], site_url, bundle.get('headlines'))
    # The portable edition embeds its own fonts, without external requests.
    html = html.replace('href="exhibitions/"', 'href="#exhibitions"')
    html = html.replace('<link rel="preload" href="fonts/intermission-masthead-v1.woff2" as="font" type="font/woff2" crossorigin>', '')
    for name in ('styles.css', 'theme.css'):
        css = (output / name).read_text(encoding='utf-8')
        # One whole font embeds smaller than its unicode-range slices.
        css = re.sub(r'/\* sans-slices:begin.*?/\* sans-slices:end \*/', lambda _: "@font-face{font-family:'Intermission Sans';src:url(\"fonts/intermission-sans-v1.woff2\") format('woff2');font-weight:200 900;font-style:normal;font-display:swap}", css, flags=re.S)
        for font in sorted((output / 'fonts').glob('*.woff2')):
            css = css.replace('fonts/' + font.name, 'data:font/woff2;base64,' + base64.b64encode(font.read_bytes()).decode('ascii'))
        html = html.replace(f'<link rel="stylesheet" href="{name}">', '<style>' + css + '</style>')
    favicon = (output / "favicon.svg").read_bytes()
    html = html.replace('href="favicon.svg"', 'href="data:image/svg+xml;base64,' + base64.b64encode(favicon).decode('ascii') + '"')
    for name in ("data.js", "core.js", "ui.js", "exhibitions.js", "calendar.js", "app.js"):
        script = (text if name == "data.js" else (output / name).read_text(encoding="utf-8")).replace('</script', '<\\/script')
        html = html.replace(f'<script defer src="{name}"></script>', '')
        html = html.replace('</body>', '<script>' + script + '</script>\n</body>')
    (output / "culture-desk-preview.html").write_text(html, encoding="utf-8")
    print("Static edition built in dist/ (public live snapshot + separate demo; browser storage)")


def version_assets(html, output):
    versioned = {}
    for name in ('styles.css', 'theme.css', 'data.js', 'core.js', 'ui.js', 'exhibitions.js', 'calendar.js', 'app.js'):
        versioned[name] = sha256((output / name).read_bytes()).hexdigest()[:12]
    return re.sub(r'((?:src|href)="(?:\.\./)?)([^"/]+)(")',
                  lambda match: match[1] + match[2] + '?v=' + versioned[match[2]] + match[3] if match[2] in versioned else match[0], html)


def first_edition(snapshot, priorities, preferences, now):
    config = preferences.get('frontpage', {})
    # Keep a day of room for readers whose clocks differ from the build machine.
    cutoff = now - timedelta(hours=config.get('fallback_hours', 168) + 24)
    days = config.get('undated_event_days', 2)

    def belongs(row):
        if row.get('published_at'):
            try:
                return reference_time(row['published_at']) >= cutoff
            except (TypeError, ValueError):
                pass
        due = priorities.get(row['id'], {}).get('due') or {}
        return 0 <= due.get('days', 999) <= days

    recent = [row for row in snapshot['content'] if belongs(row)]
    identifiers = {row['id'] for row in recent}
    links = [link for link in snapshot['content_events'] if link['content_id'] in identifiers]
    return {**snapshot, 'content': recent, 'content_events': links}, identifiers


def write_split_site(bundle, output, bootstrap):
    """Publish the current edition first, with complete indexes and bodies available on demand."""
    from backend.presentation import split_bodies
    site = dict(bundle)
    site.pop('japan_exhibitions', None)
    site.pop('exhibition_details', None)
    site.pop('film_calendar', None)
    site['static_edition'] = True
    bodies, search = {}, {}
    if 'live' in site:
        live, bodies, search = split_bodies(site['live'])
        priorities, headlines = site['priorities'], site['headlines']
        recent, selected = first_edition(live, priorities, site['preferences'], reference_time())
        if len(recent['content']) < len(live['content']):
            archive = json.dumps({'schema_version': 1, 'live': live, 'priorities': priorities, 'headlines': headlines}, ensure_ascii=False, separators=(',', ':'))
            (output / 'news-archive.json').write_text(archive, encoding='utf-8')
            site['archive_store'] = 'news-archive.json?v=' + sha256(archive.encode()).hexdigest()[:12]
            site['live'] = recent
            site['priorities'] = {key: priorities[key] for key in selected if key in priorities}
            site['headlines'] = {key: value for key, value in headlines.items() if key in selected or key not in priorities}
        else:
            site['live'] = live
    if 'archive_store' not in site:
        (output / 'news-archive.json').unlink(missing_ok=True)
    store = output / 'bodies'
    store.mkdir(exist_ok=True)
    for path in store.glob('*.json'):
        if path.stem not in bodies: path.unlink()
    for row_id, body in bodies.items():
        data = json.dumps(body, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
        path = store / (row_id + '.json')
        if not path.exists() or path.read_text(encoding='utf-8') != data: path.write_text(data, encoding='utf-8')
    index = json.dumps(search, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    (output / 'search-index.json').write_text(index, encoding='utf-8')
    if bodies:
        site['body_store'] = {'bodies': 'bodies/', 'search': 'search-index.json?v=' + sha256(index.encode('utf-8')).hexdigest()[:12]}
    (output / 'data.js').write_text(bootstrap(site), encoding='utf-8')


if __name__ == "__main__":
    build()
