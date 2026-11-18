"""Find on Nexus end to end with a fake Nexus client: name search + file check, no bulk mod list."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_backend import game  # noqa: E402,F401  (pytest fixture)

from cp77mlt.api import Api  # noqa: E402
from cp77mlt.config import Config  # noqa: E402
from cp77mlt.scanner import norm_key  # noqa: E402


class FakeNexus:
    rate = {}
    include_adult = False

    def __init__(self):
        self.searched, self.mods_asked = [], []

    def validate(self):
        return {"name": "Sam"}

    def md5_search(self, md5):
        return []

    def any_search(self, term):
        self.searched.append(term)
        return [{"mod_id": 77, "name": "Cool Jacket", "version": "1.0"}] if "cool" in term.lower() else []

    def files(self, mid, ttl=0):
        return {"files": [{"file_id": 770, "category_name": "MAIN", "version": "1.0", "uploaded_timestamp": 1,
                           "content_preview_link": f"https://file-metadata.nexusmods.com/x/{mid}"}]}

    def content_preview(self, url):
        return [("archive/pc/mod/#CoolJacket.archive", 1), ("archive/pc/mod/#CoolJacket.archive.xl", 1),
                ("archive/pc/mod/CoolJacket.xl", 1)]

    def mod(self, mid, ttl=0):
        self.mods_asked.append(mid)
        return {"name": f"Mod {mid}"}

    def tracked(self, fresh=False):
        return []

    def track(self, mid):
        pass

    def catalog(self, *a, **k):
        raise AssertionError("the full mod list must never be downloaded")


def _wait(api, r):
    for _ in range(200):
        t = api.get_task(r["task"])
        if t.get("done"):
            return t
        time.sleep(0.05)
    raise AssertionError("task did not finish")


def test_find_on_nexus_matches_by_search_and_files(game, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "cfg"))
    api = Api(Config(str(tmp_path / "s.json")))
    api.set_game_dir(game)
    api.get_mods()
    fake = FakeNexus()
    api._nexus, api._nexus_user = fake, {"name": "Sam"}
    key = next(m.key for m in api._mods if norm_key(m.name) == "cooljacket")
    t = _wait(api, api.nexus_identify([key]))
    assert not t.get("error"), t.get("error")
    link = api._cfg.get("nexus_links").get(key)
    assert link and link["mod_id"] == 77 and link["method"] == "verified"
    assert fake.searched and len(fake.searched) <= 2
    # the name it found is kept locally for later searches
    assert any(m["mod_id"] == 77 for m in api._names().mods)
    assert not os.path.exists(os.path.join(str(tmp_path / "cfg"), "nexus_catalog.json"))
