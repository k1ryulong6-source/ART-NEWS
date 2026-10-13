"""Create a portable static edition using the same frontend and demo records."""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build():
    bundle = {
        "dataset": json.loads((ROOT / "data/demo.json").read_text(encoding="utf-8")),
        "preferences": json.loads((ROOT / "config/preferences.json").read_text(encoding="utf-8")),
        "sources": json.loads((ROOT / "config/sources.json").read_text(encoding="utf-8")),
    }
    text = "window.CULTURE_BOOTSTRAP = " + json.dumps(bundle, ensure_ascii=False).replace("<", "\\u003c") + ";\n"
    (ROOT / "frontend/data.js").write_text(text, encoding="utf-8")
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    for name in ("index.html", "styles.css", "favicon.svg", "data.js", "core.js", "app.js"):
        shutil.copy2(ROOT / "frontend" / name, output / name)
    html = (output / "index.html").read_text(encoding="utf-8")
    html = html.replace('<link rel="stylesheet" href="styles.css">', '<style>' + (output / "styles.css").read_text(encoding="utf-8") + '</style>')
    favicon = (output / "favicon.svg").read_bytes()
    import base64
    html = html.replace('href="favicon.svg"', 'href="data:image/svg+xml;base64,' + base64.b64encode(favicon).decode('ascii') + '"')
    for name in ("data.js", "core.js", "app.js"):
        script = (output / name).read_text(encoding="utf-8").replace('</script', '<\\/script')
        html = html.replace(f'<script defer src="{name}"></script>', '')
        html = html.replace('</body>', '<script>' + script + '</script>\n</body>')
    (output / "culture-desk-preview.html").write_text(html, encoding="utf-8")
    print("Static edition built in dist/ (demo data; browser storage)")


if __name__ == "__main__":
    build()
