"""Create a portable static edition using the same frontend and demo records."""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.headlines import load_headlines
from backend.coverage import coverage_report
from backend.priority import rank_snapshot


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
    text = "window.CULTURE_BOOTSTRAP = " + json.dumps(bundle, ensure_ascii=False).replace("<", "\\u003c") + ";\n"
    (ROOT / "frontend/data.js").write_text(text, encoding="utf-8")
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    for name in ("index.html", "styles.css", "theme.css", "favicon.svg", "data.js", "core.js", "ui.js", "app.js"):
        shutil.copy2(ROOT / "frontend" / name, output / name)
    html = (output / "index.html").read_text(encoding="utf-8")
    for name in ('styles.css', 'theme.css'):
        html = html.replace(f'<link rel="stylesheet" href="{name}">', '<style>' + (output / name).read_text(encoding='utf-8') + '</style>')
    favicon = (output / "favicon.svg").read_bytes()
    import base64
    html = html.replace('href="favicon.svg"', 'href="data:image/svg+xml;base64,' + base64.b64encode(favicon).decode('ascii') + '"')
    for name in ("data.js", "core.js", "ui.js", "app.js"):
        script = (output / name).read_text(encoding="utf-8").replace('</script', '<\\/script')
        html = html.replace(f'<script defer src="{name}"></script>', '')
        html = html.replace('</body>', '<script>' + script + '</script>\n</body>')
    (output / "culture-desk-preview.html").write_text(html, encoding="utf-8")
    print("Static edition built in dist/ (public live snapshot + separate demo; browser storage)")


if __name__ == "__main__":
    build()
