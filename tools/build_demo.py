"""Build docs/demo.html: the real UI (cp77mlt/web) + a sample-data backend + a guided tour, in one file.

    python tools/build_demo.py
Open docs/demo.html in any browser. Host it on GitHub Pages to share it.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "cp77mlt", "web")
DEMO = os.path.join(ROOT, "tools", "demo")


def read(*p):
    with open(os.path.join(*p), encoding="utf-8") as f:
        return f.read()


def main() -> str:
    html = read(WEB, "index.html")
    css = read(WEB, "app.css") + "\n" + read(DEMO, "tour.css")
    js = read(WEB, "app.js")
    html = html.replace('<link rel="stylesheet" href="app.css">', f"<style>\n{css}\n</style>")
    html = html.replace('<script src="app.js"></script>',
                        f"<script>\n{read(DEMO, 'mock.js')}\n</script>\n<script>\n{js}\n</script>\n<script>\n{read(DEMO, 'tour.js')}\n</script>")
    html = html.replace("<title>Cyberpunk 2077 Mod List Tool</title>", "<title>Cyberpunk 2077 Mod List Tool: interactive demo</title>")
    assert 'src="app.js"' not in html and 'href="app.css"' not in html, "assets not inlined"
    out = os.path.join(ROOT, "docs", "demo.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    return out


if __name__ == "__main__":
    print("Wrote", main())
