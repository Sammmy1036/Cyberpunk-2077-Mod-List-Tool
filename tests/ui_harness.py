"""Drive the real web UI + real Api against a fake game folder in headless Chrome.

python tests/ui_harness.py <outdir>   -> screenshots of every page
The pywebview bridge is replaced by a tiny HTTP shim; Nexus calls are stubbed.
"""
import json
import os
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

from cp77mlt.api import Api  # noqa: E402
from cp77mlt.config import Config  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/shots"
os.makedirs(OUT, exist_ok=True)
tmp = tempfile.mkdtemp()


def touch(rel, data="x" * 2000):
    p = os.path.join(G, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(data)


G = os.path.join(tmp, "Cyberpunk 2077")
os.environ["XDG_CONFIG_HOME"] = os.path.join(tmp, "cfg")
os.environ["HOME"] = tmp
touch("bin/x64/Cyberpunk2077.exe")
touch("bin/x64/steam_api64.dll")
touch("archive/pc/ep1/ep1.archive")
for rel in ("red4ext/RED4ext.dll", "bin/x64/winmm.dll", "engine/tools/scc.exe", "bin/x64/plugins/cyber_engine_tweaks.asi",
            "red4ext/plugins/ArchiveXL/ArchiveXL.dll", "red4ext/plugins/TweakXL/TweakXL.dll",
            "r6/scripts/EquipmentEx/EquipmentEx.reds"):
    touch(rel)
touch("bin/x64/plugins/cyber_engine_tweaks/cyber_engine_tweaks.log", "[info] CET version v1.35.0\n")
touch("r6/logs/redscript_rCURRENT.log", "INFO - redscript compiler v0.5.27\n" + "INFO - compiled\n" * 30 +
      "ERROR - At r6/scripts/OldHud/hud.reds:12:5: function 'GetHUD' not found\nWARN - unused variable\n" + "INFO - done\n" * 10)
touch("mods/redmod.stub", "")
touch("red4ext/logs/red4ext.log", "[2026-11-06 20:01:02.123] [RED4ext] [info] RED4ext (v1.27.0) is initializing...\n" * 8 +
      "[2026-11-06 20:01:03.000] [RED4ext] [warning] Plugin 'Foo' targets an older runtime\n")
# loose mods
for n in ("#Kiroshi_Opticals_Retexture", "PanamCompanion", "NightCityLUT", "AlleywayCrowd"):
    touch(f"archive/pc/mod/{n}.archive", "x" * 900000)
    touch(f"archive/pc/mod/{n}.archive.xl")
touch("archive/pc/mod/ImmersiveRippers_Extra.archive.xl", "")
touch("mods/ImmersiveRippers/archives/readme.txt", "Get updates: https://www.nexusmods.com/cyberpunk2077/mods/6060\n"
      "Needs ArchiveXL https://www.nexusmods.com/cyberpunk2077/mods/4198\n")
touch("archive/pc/mod/VirtualAtelier.archive", "x" * 4000000)
touch("bin/x64/plugins/cyber_engine_tweaks/mods/VirtualAtelier/init.lua")
touch("r6/scripts/VirtualAtelier/Atelier.reds")
touch("r6/scripts/OldHud/hud.reds")
touch("r6/tweaks/BetterLootMarkers.yaml")
# one Nexus mod installed by hand as differently named pieces (main + optional file)
touch("bin/x64/plugins/cyber_engine_tweaks/mods/PoliceOverhaul/init.lua")
touch("r6/scripts/PoliceOverhaul/main.reds")
touch("archive/pc/mod/NCPD_Optional_Uniforms.archive", "x" * 300000)
touch("mods/ImmersiveRippers/info.json", json.dumps({"name": "Immersive Rippers", "version": "1.4"}))
touch("mods/ImmersiveRippers/archives/x.archive")
touch("Temporarily Disabled Mods/archive/pc/mod/RainbowCarPaint.archive")
touch("Temporarily Disabled Mods/r6/scripts/RainbowCarPaint/x.reds")
# Vortex
touch("archive/pc/mod/AMM_Props.archive", "x" * 9000000)
touch("bin/x64/plugins/cyber_engine_tweaks/mods/AppearanceMenuMod/init.lua")
touch("archive/pc/mod/BetterVehicleHandling.archive")
touch("vortex.deployment.json", json.dumps({"files": [
    {"relPath": "archive\\pc\\mod\\AMM_Props.archive", "source": "Appearance Menu Mod-790-2-6-1-1699999999"},
    {"relPath": "bin\\x64\\plugins\\cyber_engine_tweaks\\mods\\AppearanceMenuMod\\init.lua", "source": "Appearance Menu Mod-790-2-6-1-1699999999"},
    {"relPath": "archive\\pc\\mod\\BetterVehicleHandling.archive", "source": "Better Vehicle Handling-5000-3-0-1700000000"}]}))

# Nexus-named downloads for identification
import zipfile  # noqa: E402
os.makedirs(os.path.join(tmp, "Downloads"))
with zipfile.ZipFile(os.path.join(tmp, "Downloads", "Panam Companion-12345-2-0-1-1750000000.zip"), "w") as z:
    z.writestr("archive/pc/mod/PanamCompanion.archive", "x")
    z.writestr("archive/pc/mod/PanamCompanion.archive.xl", "x")
with zipfile.ZipFile(os.path.join(tmp, "Downloads", "Night City LUT-777-1-3-1750000000.zip"), "w") as z:
    z.writestr("NCLUT/archive/pc/mod/NightCityLUT.archive", "x")
    z.writestr("NCLUT/archive/pc/mod/NightCityLUT.archive.xl", "x")
cfg = Config(os.path.join(tmp, "settings.json"))
cfg.set("game_dir", G)
cfg.set("nexus_links", {"loose:virtualatelier": {"mod_id": 2987, "version": "1.6.0", "name": "Virtual Atelier", "method": "md5"},
                         "loose:policeoverhaul": {"mod_id": 4321, "version": "3.2", "name": "Police Overhaul", "method": "manual"},
                         "loose:ncpdoptionaluniforms": {"mod_id": 4321, "version": "1.0", "method": "manual"}})
api = Api(cfg)


class FakeNexus:
    rate = {"daily": 19874, "hourly": 499}

    def validate(self):
        return {"name": "Sammmy1036", "user_id": 1, "is_premium": True, "avatar": ""}

    def mod(self, mid, ttl=0):
        import time; time.sleep(0.25)  # simulate network so progress is visible
        if mid in (3100, 6060):
            return {"mod_id": mid, "name": {3100: "Kiroshi Opticals Retexture 4K", 6060: "Immersive Rippers"}[mid],
                    "version": "4.2", "author": "modder", "summary": "Sharper, cleaner optics overlay textures for every Kiroshi model.",
                    "picture_url": f"/thumb.svg?{mid}", "endorsement_count": 5120, "updated_timestamp": 1760000000, "status": "published"}
        if mid == 3101:
            return {"name": "Kiroshi Optics Overhaul", "version": "1.0", "author": "someone", "summary": "Sharper optics HUD."}
        return {790: {"name": "Appearance Menu Mod", "version": "2.8.0", "updated_timestamp": 1761000000},
                2987: {"name": "Virtual Atelier", "version": "1.7.1", "updated_timestamp": 1760000000},
                4198: {"name": "ArchiveXL", "version": "1.24.0"}}.get(mid, {"name": f"Mod {mid}", "version": "1.0"})

    def updated(self, p):
        return []

    def tracked(self):
        return [{"mod_id": m, "domain_name": "cyberpunk2077"} for m in sorted(self._tracked | {107})]

    def md5_search(self, md5):
        return []

    CAT = [{"mod_id": 901, "name": "Alleyway Crowds Expanded"}, {"mod_id": 902, "name": "Crowd Density"},
           {"mod_id": 555, "name": "Better Loot Markers"}, {"mod_id": 3100, "name": "Kiroshi Opticals Retexture 4K"},
           {"mod_id": 3101, "name": "Kiroshi Optics Overhaul"}, {"mod_id": 4400, "name": "Rainbow Car Paint Pack"},
           {"mod_id": 2987, "name": "Virtual Atelier"}, {"mod_id": 790, "name": "Appearance Menu Mod"}, {"mod_id": 6060, "name": "Immersive Rippers"}]
    _tracked = {790}

    def sorted_ids(self, field, offset, count):
        ids = [3100, 790, 2987, 6060, 901, 555, 4400, 3101, 902, 777, 12345, 5000, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
        return ids[offset:offset + count]

    def feed(self, kind):
        base = [(3100, "Kiroshi Opticals Retexture 4K", "Sharper, cleaner optics overlay textures."),
                (790, "Appearance Menu Mod", "Spawn NPCs, change appearances, decorate."),
                (2987, "Virtual Atelier", "In-game clothing store framework."),
                (6060, "Immersive Rippers", "Ripperdocs with more personality."),
                (901, "Alleyway Crowds Expanded", "Busier back streets."), (555, "Better Loot Markers", "Clearer loot icons.")]
        return [{"mod_id": i, "name": n, "summary": t, "author": "modder", "version": "1.0", "endorsement_count": 1234 * (k + 1),
                 "updated_timestamp": 1760000000, "picture_url": f"/thumb.svg?{i}", "status": "published"} for k, (i, n, t) in enumerate(base)]

    def trending(self, days=7):
        return [{"mod_id": c["mod_id"], "endorsements": c["endorsement_count"], "created": 0, "card": c}
                for c in sorted(self.feed("trending"), key=lambda c: -c["endorsement_count"])]

    def catalog(self, progress=None, cancelled=None):
        return self.CAT

    def any_search(self, term):
        return self.search(term)

    def content_preview(self, url):
        mid = int(url.rsplit("/", 1)[-1])
        return {3100: [("archive/pc/mod/#Kiroshi_Opticals_Retexture.archive", 900000),
                       ("archive/pc/mod/#Kiroshi_Opticals_Retexture.archive.xl", 2000)],
                4400: [("Temporarily/archive/pc/mod/RainbowCarPaint.archive", 2000), ("r6/scripts/RainbowCarPaint/x.reds", 2000)]}.get(mid, [])

    def track(self, mid):
        self._tracked.add(mid)

    def untrack(self, mid):
        self._tracked.discard(mid)

    def search(self, term, count=10):
        return {"Alleyway Crowd": [{"mod_id": 901, "name": "Alleyway Crowds Expanded", "version": "1.0"},
                                   {"mod_id": 902, "name": "Crowd Density", "version": "2.0"}],
                "Better Loot Markers": [{"mod_id": 555, "name": "Better Loot Markers", "version": "3.1"}]}.get(term, [])

    def files(self, mid, ttl=0):
        return {"files": [{"file_id": mid * 10, "category_name": "MAIN", "version": "4.2", "uploaded_timestamp": 1,
                           "content_preview_link": f"https://file-metadata.nexusmods.com/x/{mid}"}]}

    def estimate_installed(self, mid, mtime):
        return None


if "--nexus" in sys.argv:
    api._nexus = FakeNexus()
    api._nexus_user = FakeNexus().validate()

from cp77mlt import game as _game  # noqa: E402
_game.launch_game = lambda *a, **k: "Cyberpunk2077.exe"   # don't actually spawn anything
FAKE_RUN = {"game": False}
_orig_state = api._proc.state
api._proc.state = lambda: {**_orig_state(), "game": FAKE_RUN["game"]}
EXPORT_TO = os.path.join(tmp, "out", "my_preset")
os.makedirs(os.path.dirname(EXPORT_TO))
api._dialog = lambda kind, **kw: EXPORT_TO if kind == "save" else None


class FakeGH:
    def repo(self, r):
        return {"repo": r, "description": "Hot reload for archives, scripts and tweaks", "stars": 210}

    def releases(self, r):
        return [{"tag_name": "v1.3.0", "published_at": "2026-10-01T00:00:00Z", "html_url": "https://github.com/x/y/releases/1",
                 "assets": [{"name": "RedHotTools-1.3.0.zip", "browser_download_url": "https://x"}]}]

    def latest(self, r):
        return self.releases(r)[0]


api._gh = FakeGH()
touch("red4ext/plugins/RedHotTools/RedHotTools.dll")
WEB = os.path.join(ROOT, "cp77mlt", "web")


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=WEB, **k)

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/thumb.svg"):
            body = open(os.path.join(ROOT, "tests", "thumb.svg"), "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def do_POST(self):
        name = self.path.rsplit("/", 1)[-1]
        args = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"[]")
        try:
            res = getattr(api, name)(*args)
        except Exception as e:  # surface to test
            res = {"ok": False, "error": f"PY {e!r}"}
        body = json.dumps(res).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)


srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
port = srv.server_address[1]

SHIM = """
window.pywebview = { api: new Proxy({}, { get: (_, name) => async (...args) => {
  const r = await fetch('/api/' + name, {method: 'POST', body: JSON.stringify(args)}); return r.json(); } }) };
"""

from playwright.sync_api import sync_playwright  # noqa: E402

_GREY = """/*preview*/
.slab { background: %(bg)s; color: #fff; }
.slab::after { border-color: rgba(255,255,255,.28); }
.slab-logo .mark { background: #fff; }
.slab-title { border-left-color: rgba(255,255,255,.85); }
.slab-meta::after, .slab-stripe::after { display: none; }
.slab-stripe { background: var(--black); }
"""
PREVIEWS = {"current": "", "grey_mid": _GREY % {"bg": "#3A3B41"}, "grey_dark": _GREY % {"bg": "#26272C"}} \
    if os.environ.get("HDR_PREVIEW") else {}

errors = []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1320, "height": 840})
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errors.append(m.text))
    pg.add_init_script(SHIM)
    pg.goto(f"http://127.0.0.1:{port}/index.html")
    pg.wait_for_timeout(60)
    pg.screenshot(path=f"{OUT}/0_splash.png")
    pg.wait_for_timeout(3500)
    pg.screenshot(path=f"{OUT}/0_overview_before_identify.png")
    pg.click("#updFind"); pg.wait_for_timeout(4500)
    pg.screenshot(path=f"{OUT}/1_overview.png")
    for name, css in PREVIEWS.items():
        pg.add_style_tag(content=css) if css else None
        pg.wait_for_timeout(250)
        pg.screenshot(path=f"{OUT}/hdr_{name}.png")
        if css:
            pg.evaluate("document.querySelectorAll('style').forEach(s => { if (s.textContent.includes('/*preview*/')) s.remove(); })")
    links = api._cfg.get("nexus_links")
    print("linked:", {k: (v["mod_id"], v.get("version"), v["method"]) for k, v in links.items()})
    print("suggestions:", list(api._cfg.get("nexus_suggestions")))
    pg.click("#launchBtn"); pg.wait_for_timeout(500)
    pg.locator(".rail").screenshot(path=f"{OUT}/1b_launching.png")
    FAKE_RUN["game"] = True; pg.wait_for_timeout(2200)
    pg.locator(".rail").screenshot(path=f"{OUT}/1c_running.png")
    pg.wait_for_timeout(5200)
    pg.locator(".status").screenshot(path=f"{OUT}/1d_footer_running.png")
    second = api.launch_game()
    print("second launch blocked:", second)
    FAKE_RUN["game"] = False; pg.wait_for_timeout(2200)
    pg.click("button.nav[data-page=mods]"); pg.wait_for_timeout(700)
    pg.screenshot(path=f"{OUT}/2_mods.png")
    pg.click("#segView button[data-v=folders]"); pg.wait_for_timeout(400)
    pg.screenshot(path=f"{OUT}/2_mods_by_folder.png")
    pg.click("#segView button[data-v=mods]"); pg.wait_for_timeout(300)
    pg.locator("tr.row", has_text="Police Overhaul").click(); pg.wait_for_timeout(500)
    pg.screenshot(path=f"{OUT}/2_grouped_drawer.png")
    pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
    pg.click("#thName"); pg.wait_for_timeout(250)
    print("SORT HEADER:", pg.inner_text("#thName")); pg.click("#thName"); pg.wait_for_timeout(250)
    pg.click("#btnMore"); pg.wait_for_timeout(300); pg.click("#bBackups"); pg.wait_for_timeout(600)
    pg.click("#bkNow"); pg.wait_for_timeout(3000)
    pg.click("#btnMore"); pg.wait_for_timeout(300); pg.click("#bBackups"); pg.wait_for_timeout(700)
    pg.screenshot(path=f"{OUT}/2b_backups.png")
    pg.click("#modal [data-close]"); pg.wait_for_timeout(200)
    pg.click("#btnMore"); pg.wait_for_timeout(300); pg.click("#bImport"); pg.wait_for_timeout(400)
    pg.screenshot(path=f"{OUT}/2c_preset_choice.png")
    pg.click("#modal [data-close]"); pg.wait_for_timeout(200)
    pg.click("tr.row >> nth=2"); pg.wait_for_timeout(500)
    pg.screenshot(path=f"{OUT}/3_drawer.png")
    pg.keyboard.press("Escape")
    # toggle a mod off through the UI and verify on disk
    row = pg.locator("tr.row", has_text="NightCityLUT")
    row.locator(".switch").click(); pg.wait_for_timeout(600)
    moved = os.path.exists(os.path.join(G, "Temporarily Disabled Mods", "archive", "pc", "mod", "NightCityLUT.archive.xl"))
    pg.locator(".pick").nth(0).check(); pg.locator(".pick").nth(1).check(); pg.wait_for_timeout(200)
    pg.screenshot(path=f"{OUT}/4_bulk.png")
    pg.click("button.nav[data-page=core]"); pg.wait_for_timeout(600)
    pg.screenshot(path=f"{OUT}/5_core.png")
    pg.click("button.nav[data-page=logs]"); pg.wait_for_timeout(600)
    pg.screenshot(path=f"{OUT}/6_logs.png")
    # linked mod side panel with Nexus preview (from overview)
    pg.click("button.nav[data-page=mods]"); pg.wait_for_timeout(600)
    pg.locator("tr.row", has_text="Kiroshi").click(); pg.wait_for_timeout(900)
    pg.screenshot(path=f"{OUT}/3b_drawer_linked.png")
    pg.locator("tr.row", has_text="OldHud").click(); pg.wait_for_timeout(500)
    pg.fill("#dSearch input", "kiroshi"); pg.keyboard.press("Enter"); pg.wait_for_timeout(800)
    pg.locator("#drawer").screenshot(path=f"{OUT}/3d_drawer_search.png")
    pg.locator("tr.row", has_text="RedHotTools").click(); pg.wait_for_timeout(500)
    pg.fill("#dGh", "https://github.com/psiberx/cp2077-red-hot-tools"); pg.click("#dGhBtn"); pg.wait_for_timeout(1200)
    pg.screenshot(path=f"{OUT}/3c_drawer_github.png")
    print("github link:", api._cfg.get("github_links"), "update:", api._updates.get("loose:redhottools", {}).get("latest"))
    pg.keyboard.press("Escape")
    pg.click("button.nav[data-page=browse]"); pg.wait_for_timeout(1000)
    pg.screenshot(path=f"{OUT}/4b_browse.png")
    pg.click("#bwKind button[data-k=latest_added]"); pg.wait_for_timeout(900)
    n1 = pg.locator(".card").count()
    pg.click("#bwMore"); pg.wait_for_timeout(900)
    print("browse new: first page", n1, "after load more", pg.locator(".card").count())
    pg.screenshot(path=f"{OUT}/4a_browse_more.png", full_page=True)
    try:
        pg.locator(".card").first.click(timeout=4000)
    except Exception:
        box = pg.locator(".card").first.bounding_box()
        print("card box:", box, "covered by:", pg.evaluate(
            "([x,y]) => { const e = document.elementFromPoint(x, y); return e && (e.id || e.className || e.tagName); }",
            [box["x"] + 20, box["y"] + 20] if box else [0, 0]))
        raise
    pg.wait_for_timeout(900)
    pg.screenshot(path=f"{OUT}/4c_browse_detail.png")
    pg.keyboard.press("Escape")
    pg.click("button.nav[data-page=nexus]"); pg.wait_for_timeout(1200)
    pg.screenshot(path=f"{OUT}/7_nexus.png", full_page=False)
    pg.locator("#queuePanel").screenshot(path=f"{OUT}/7b_queue.png")
    pg.locator(".queue-row [data-find]").first.click(); pg.wait_for_timeout(500)
    opened = pg.locator(".queue-row .lsearch").count()
    pg.locator(".queue-row [data-find]").first.click(); pg.wait_for_timeout(300)
    print("FIND TOGGLE open->closed:", opened, "->", pg.locator(".queue-row .lsearch").count())
    pg.locator(".queue-row .qname").first.click(); pg.wait_for_timeout(700)
    pg.screenshot(path=f"{OUT}/7e_queue_name_drawer.png")
    pg.keyboard.press("Escape"); pg.evaluate("typeof closeDrawer==='function' && closeDrawer()"); pg.wait_for_timeout(300)
    pg.locator(".queue-row [data-find]").last.click(); pg.wait_for_timeout(600)
    pg.locator(".queue-row .lsearch input").last.fill("kiroshi optics"); pg.keyboard.press("Enter"); pg.wait_for_timeout(700)
    pg.locator(".queue-row .lrow").first.click(); pg.wait_for_timeout(700)
    pg.locator("#queuePanel").screenshot(path=f"{OUT}/7d_queue_search.png")
    pg.locator("#tracked").screenshot(path=f"{OUT}/7e_tracking.png")
    # export through the UI
    pg.click("button.nav[data-page=mods]"); pg.wait_for_timeout(600)
    pg.click("#btnMore"); pg.click("#bExport"); pg.wait_for_timeout(300)
    pg.screenshot(path=f"{OUT}/7c_export.png")
    pg.click("#fmtSeg button[data-f=zip]"); pg.click("#expGo"); pg.wait_for_timeout(1500)
    print("export written:", os.path.exists(EXPORT_TO + ".zip"))
    pg.click("button.nav[data-page=settings]"); pg.wait_for_timeout(800)
    pg.screenshot(path=f"{OUT}/8_settings.png", full_page=True)
    pg.click("button.nav[data-page=overview]"); pg.wait_for_timeout(800)
    pg.click("#genBtn"); pg.wait_for_timeout(800)
    pg.screenshot(path=f"{OUT}/9_generated.png")
    pg.set_viewport_size({"width": 1100, "height": 700}); pg.wait_for_timeout(300)
    pg.screenshot(path=f"{OUT}/10_small.png")
    pg.locator(".rail").screenshot(path=f"{OUT}/11_rail_small.png")
    pg.set_viewport_size({"width": 2560, "height": 1400}); pg.wait_for_timeout(400)
    pg.locator(".rail").screenshot(path=f"{OUT}/11_rail_tall.png")
    pg.screenshot(path=f"{OUT}/12_tall.png")
    b.close()

print("disabled via UI:", moved)
print("updates persisted:", os.path.exists(api._updates_path))
print("JS errors:", errors)
print("report exists:", os.path.exists(os.path.join(os.path.expanduser("~"), "Documents", "Cyberpunk 2077 Mod List.txt")))
