"""Backend tests against a synthetic game folder. Run: python -m pytest tests -q"""
import json
import os
import sys
import zipfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cp77mlt import core_mods, logs, managers, nexus, ops, report  # noqa: E402
from cp77mlt.config import Config  # noqa: E402
from cp77mlt.scanner import TEMP_DISABLED_DIR, build_mod_list, norm_key  # noqa: E402


def touch(root, rel, data=b"x"):
    p = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode())
    return p


@pytest.fixture
def game(tmp_path):
    g = str(tmp_path / "Cyberpunk 2077")
    touch(g, "bin/x64/Cyberpunk2077.exe")
    # core frameworks
    for rel in ("red4ext/RED4ext.dll", "bin/x64/winmm.dll", "engine/tools/scc.exe",
                "bin/x64/plugins/cyber_engine_tweaks.asi",
                "red4ext/plugins/ArchiveXL/ArchiveXL.dll", "red4ext/plugins/TweakXL/TweakXL.dll",
                "red4ext/plugins/Codeware/Codeware.dll", "r6/scripts/EquipmentEx/EquipmentEx.reds",
                "archive/pc/mod/EquipmentEx.archive", "archive/pc/mod/EquipmentEx.archive.xl"):
        touch(g, rel)
    touch(g, "r6/scripts/EquipmentEx/EquipmentEx.Global.reds",
          'public static func Version() -> String = "1.2.7";')
    # one mod = 3 files in archive/pc/mod (v2 counted 3)
    touch(g, "archive/pc/mod/#CoolJacket.archive")
    touch(g, "archive/pc/mod/#CoolJacket.archive.xl")
    touch(g, "archive/pc/mod/CoolJacket.xl")
    # one mod spread over archive + CET + redscript (v2 counted 3)
    touch(g, "archive/pc/mod/VirtualAtelier.archive")
    touch(g, "bin/x64/plugins/cyber_engine_tweaks/mods/VirtualAtelier/init.lua")
    touch(g, "r6/scripts/VirtualAtelier/Atelier.reds")
    touch(g, "r6/tweaks/BetterLoot.yaml")
    touch(g, "archive/pc/mod/readme.txt")                  # ignored
    touch(g, "mods/NiceRedmod/info.json", json.dumps({"name": "Nice REDmod", "version": "2.1"}))
    touch(g, "mods/NiceRedmod/archives/nice.archive")
    # disabled mod
    touch(g, f"{TEMP_DISABLED_DIR}/archive/pc/mod/OldThing.archive")
    # Vortex-deployed mod
    touch(g, "archive/pc/mod/VortexMod.archive")
    touch(g, "r6/scripts/VortexMod/main.reds")
    touch(g, "vortex.deployment.json", json.dumps({
        "files": [{"relPath": "archive\\pc\\mod\\VortexMod.archive", "source": "Vortex Mod-1234-1-2-0-1700000000"},
                  {"relPath": "r6\\scripts\\VortexMod\\main.reds", "source": "Vortex Mod-1234-1-2-0-1700000000"}]}))
    # logs
    touch(g, "red4ext/logs/red4ext.log", "[info] loaded\n[error] Plugin X failed\n0 errors in config\n")
    touch(g, "r6/logs/redscript_rCURRENT.log", "INFO - redscript compiler v0.5.27\nWARN - something\n")
    return g


def test_grouping_counts_mods_not_files(game):
    mods = build_mod_list(game, managers.read_vortex_manifests(game))
    names = {m.name: m for m in mods}
    assert "CoolJacket" in {norm_key(n) and m.name for n, m in names.items()} or any(
        norm_key(m.name) == "cooljacket" for m in mods)
    cj = next(m for m in mods if norm_key(m.name) == "cooljacket")
    assert sum(len(c.rel_paths) for c in cj.components) == 3
    va = next(m for m in mods if norm_key(m.name) == "virtualatelier")
    assert set(va.locations()) == {"archive", "cet", "redscript"}
    assert "Nice REDmod" in names and names["Nice REDmod"].version == "2.1"
    vm = next(m for m in mods if m.source == "vortex")
    assert vm.nexus_id == 1234 and vm.version == "1.2.0" and vm.name == "Vortex Mod"
    assert len(vm.components) == 2
    old = next(m for m in mods if m.name == "OldThing")
    assert not old.enabled
    # core frameworks are never counted
    assert not any("equipmentex" in norm_key(m.name) or "archivexl" in norm_key(m.name) for m in mods)
    # CoolJacket, VirtualAtelier, BetterLoot, Nice REDmod, OldThing, Vortex Mod
    assert len(mods) == 6, [m.name for m in mods]
    assert sum(m.enabled for m in mods) == 5


def test_disable_enable_roundtrip_and_conflicts(game):
    mods = build_mod_list(game)
    va = next(m for m in mods if norm_key(m.name) == "virtualatelier")
    r = ops.set_mods_enabled(game, [va], enable=False)
    assert r["moved"] == 3 and not r["errors"]
    assert os.path.exists(os.path.join(game, TEMP_DISABLED_DIR, "r6", "scripts", "VirtualAtelier"))
    mods = build_mod_list(game)
    va = next(m for m in mods if norm_key(m.name) == "virtualatelier")
    assert not va.enabled
    # user reinstalls a newer copy while disabled -> enabling must NOT overwrite it (v2 deleted it)
    touch(game, "archive/pc/mod/VirtualAtelier.archive", b"NEWER")
    r = ops.set_mods_enabled(game, [va], enable=True)
    assert r["errors"] and open(os.path.join(game, "archive/pc/mod/VirtualAtelier.archive"), "rb").read() == b"NEWER"


def test_vortex_mods_are_not_moved(game):
    mods = build_mod_list(game, managers.read_vortex_manifests(game))
    vm = next(m for m in mods if m.source == "vortex")
    r = ops.set_mods_enabled(game, [vm], enable=False)
    assert r["moved"] == 0 and r["skipped"]
    assert os.path.exists(os.path.join(game, "archive/pc/mod/VortexMod.archive"))


def test_core_status_uses_key_files(game):
    st = {c["name"]: c for c in core_mods.status(game)}
    assert all(c["installed"] for c in st.values())
    assert st["EquipmentEx"]["version"] == "1.2.7"
    assert st["Redscript"]["version"] == "0.5.27"


def test_log_classification(game):
    iss = logs.extract_issues(os.path.join(game, "red4ext/logs/red4ext.log"))
    assert len(iss["errors"]) == 1  # '0 errors in config' is not an error (v2 flagged it)


def test_report_utf8_and_contents(game, tmp_path):
    touch(game, "archive/pc/mod/Ünïcødé_Mod.archive")
    mods = build_mod_list(game, managers.read_vortex_manifests(game))
    out = report.generate(str(tmp_path / "out" / "list.txt"), game_dir=game, game_version="2.3", phantom_liberty=True,
                          store="Steam", mods=mods, core=core_mods.status(game), log_names=["RED4ext"],
                          include_errors=True, include_disabled=True, manager="Vortex")
    text = open(out, encoding="utf-8-sig").read()
    assert "Ünïcødé_Mod" in text and "Total Mods Installed: 6 enabled, 1 disabled" in text
    assert "Plugin X failed" in text and "nexusmods.com/cyberpunk2077/mods/1234" in text


def test_zip_slip_blocked(game, tmp_path):
    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil, "w") as z:
        z.writestr("../../escape.txt", "pwned")
    with pytest.raises(ValueError):
        ops.extract_archive(str(evil), str(tmp_path / "x"))


def test_install_wrapped_archive_and_park_conflicts(game, tmp_path):
    arc = tmp_path / "mod.zip"
    with zipfile.ZipFile(arc, "w") as z:
        z.writestr("MyMod v2/archive/pc/mod/#CoolJacket.archive", "v2")
        z.writestr("MyMod v2/r6/scripts/New/n.reds", "x")
    r = ops.install_archive(game, str(arc))
    assert "archive/pc/mod/#CoolJacket.archive" in r["installed"]
    assert r["displaced"] == ["archive/pc/mod/#CoolJacket.archive"] and r["backup"]
    assert os.path.exists(os.path.join(r["backup"], "archive", "pc", "mod", "#CoolJacket.archive"))


def test_export_import_preset(game, tmp_path):
    mods = [m for m in build_mod_list(game) if m.enabled]
    out = str(tmp_path / "preset.zip")
    r = ops.export_preset(game, mods, out)
    assert r["files"] >= 7
    names = zipfile.ZipFile(out).namelist()
    assert "cp77mlt_preset.json" in names and "r6/scripts/VirtualAtelier/Atelier.reds" in names


def test_mo2_instance(tmp_path):
    inst = tmp_path / "mo2"
    touch(str(inst), "ModOrganizer.ini",
          "[General]\ngameName=Cyberpunk 2077\ngamePath=@ByteArray(C:\\\\Games\\\\Cyberpunk 2077)\n"
          "selected_profile=@ByteArray(Default)\n[customExecutables]\nsize=1\n1\\title=Cyberpunk 2077\n"
          "1\\binary=C:/Games/Cyberpunk 2077/bin/x64/Cyberpunk2077.exe\n")
    touch(str(inst), "profiles/Default/modlist.txt", "# header\n+Mod A\n-Mod B\n+Stuff_separator\n*DLC\n")
    touch(str(inst), "mods/Mod A/meta.ini", "[General]\nmodid=555\nversion=1.0.3\n")
    touch(str(inst), "mods/Mod A/archive/pc/mod/a.archive")
    m = managers.MO2Instance(str(inst))
    assert m.game_path == "C:\\Games\\Cyberpunk 2077"
    mods = m.mods()
    assert [x["name"] for x in mods] == ["Mod A", "Mod B"]
    assert mods[0]["mod_id"] == 555 and mods[0]["enabled"] and not mods[1]["enabled"]
    assert m.default_game_executable() == "Cyberpunk 2077"
    assert m.set_enabled(["Mod B"], True) == 1
    assert "+Mod B" in open(m.modlist_path).read()


def test_version_compare_and_parsing():
    assert nexus.version_newer("1.10.0", "1.9.2") is True
    assert nexus.version_newer("1.2", "1.2.0") is False
    assert nexus.version_newer("v2.0", "2.0") is False
    assert nexus.parse_mod_id("https://www.nexusmods.com/cyberpunk2077/mods/4198?tab=files") == 4198
    assert managers.parse_vortex_folder_name("Appearance Menu Mod-790-2-6-1-1699999999")["mod_id"] == 790


def test_config_roundtrip(tmp_path):
    c = Config(str(tmp_path / "s.json"))
    c.set("game_dir", "X")
    assert Config(str(tmp_path / "s.json")).get("game_dir") == "X"
    assert "nexus_api_key" not in c.public()


# ---------------------------------------------------------------- v3.1
from cp77mlt import identify  # noqa: E402
from cp77mlt.api import Api  # noqa: E402


def test_dialog_filters_are_valid_for_pywebview():
    """v3.0 export broke because '7-Zip archive (*.7z)' fails pywebview's filter regex."""
    from webview.util import parse_file_type
    for f in list(Api.EXPORT_FORMATS.values()) + ["Archives (*.zip;*.7z;*.rar)", "All files (*.*)"]:
        parse_file_type(f)


def test_nexus_filename_parse():
    i = identify.parse_nexus_filename(r"C:\dl\Virtual Atelier-2987-1-7-1-1760000000.zip")
    assert i == {"name": "Virtual Atelier", "mod_id": 2987, "version": "1.7.1", "timestamp": 1760000000}
    assert identify.parse_nexus_filename("random.zip") is None
    assert identify.parse_nexus_filename("Mod-1-2-1700000000(1).7z")["mod_id"] == 1


def test_component_paths_strip_wrapper_and_group_stems():
    cp = identify.component_paths(["Wrapper/archive/pc/mod/#Foo.archive", "Wrapper/archive/pc/mod/#Foo.archive.xl",
                                   "Wrapper/r6/scripts/Foo/a/b.reds", "readme.txt", "Bare.archive"])
    assert cp == {"archive/pc/mod/#foo", "r6/scripts/foo", "archive/pc/mod/bare"}


def test_match_downloads_links_with_version(game, tmp_path):
    dl = tmp_path / "Downloads"
    dl.mkdir()
    with zipfile.ZipFile(dl / "Virtual Atelier-2987-1-6-0-1750000000.zip", "w") as z:
        z.writestr("archive/pc/mod/VirtualAtelier.archive", "x")
        z.writestr("bin/x64/plugins/cyber_engine_tweaks/mods/VirtualAtelier/init.lua", "x")
        z.writestr("r6/scripts/VirtualAtelier/Atelier.reds", "x")
    with zipfile.ZipFile(dl / "Unrelated-5-1-0-1750000000.zip", "w") as z:
        z.writestr("archive/pc/mod/Other.archive", "x")
    mods = [m for m in build_mod_list(game) if m.source == "loose"]
    idx = identify.ArchiveIndex(str(tmp_path / "idx.json"))
    archives = [{"path": p, "components": set(idx.entries(p, None)["components"]), "info": identify.parse_nexus_filename(p)}
                for p in identify.find_archives([str(dl)])]
    res = identify.match_downloads(mods, archives)
    va = next(m for m in mods if norm_key(m.name) == "virtualatelier")
    assert res[va.key]["info"]["mod_id"] == 2987 and res[va.key]["info"]["version"] == "1.6.0"
    assert len(res) == 1


def test_name_matching():
    assert identify.search_terms("#zzVirtualAtelier_v1.2") == ["Virtual Atelier"]
    best, score = identify.best_name_match("LimitedHUD", [{"name": "Limited HUD", "mod_id": 1}, {"name": "HUD Painter", "mod_id": 2}])
    assert best["mod_id"] == 1 and score == 1.0
    assert identify.name_score("clearwindows", "Clear Car Windows") < 0.999


def test_parse_nxm():
    p = nexus.parse_nxm("nxm://cyberpunk2077/mods/4198/files/123456?key=abc&expires=1700000000&user_id=9")
    assert p == {"game": "cyberpunk2077", "mod_id": 4198, "file_id": 123456, "key": "abc",
                 "expires": 1700000000, "user_id": "9"}
    assert nexus.parse_nxm("https://x") is None


def test_estimate_installed_version():
    c = nexus.NexusClient.__new__(nexus.NexusClient)
    c.files = lambda mid, ttl=0: {"files": [
        {"category_name": "OLD_VERSION", "version": "1.0", "uploaded_timestamp": 1_700_000_000},
        {"category_name": "OLD_VERSION", "version": "1.1", "uploaded_timestamp": 1_720_000_000},
        {"category_name": "MAIN", "version": "1.2", "uploaded_timestamp": 1_740_000_000}]}
    assert c.estimate_installed(1, 1_719_990_000)["version"] == "1.1"   # files dated just before the 1.1 upload
    assert c.estimate_installed(1, 1_750_000_000)["version"] == "1.2"


def test_catalog_candidates_handle_compound_names():
    cat = identify.Catalog([{"mod_id": i, "name": n} for i, n in enumerate(
        ["Clear Car Windows", "Limited HUD", "Kiroshi Opticals Retexture 4K", "Virtual Car Dealer", "Entity Builder"])])
    assert cat.candidates(["clearwindows"])[0][0]["name"] == "Clear Car Windows"
    assert cat.candidates(["virtualcardealer"])[0][1] == 1.0
    assert cat.candidates(["#Kiroshi_Opticals_Retexture"])[0][0]["mod_id"] == 2


def test_verify_against_preview_picks_files_and_sizes(game):
    mods = build_mod_list(game)
    va = next(m for m in mods if norm_key(m.name) == "virtualatelier")
    inst = identify.installed_files(va, game, os.path.join(game, TEMP_DISABLED_DIR))
    good = [("VA/archive/pc/mod/VirtualAtelier.archive", 1), ("VA/bin/x64/plugins/cyber_engine_tweaks/mods/VirtualAtelier/init.lua", 1),
            ("VA/r6/scripts/VirtualAtelier/Atelier.reds", 1)]
    v = identify.verify_against_preview(va, good, inst)
    assert v["coverage"] == 1.0 and v["size_hits"] == v["size_total"] == 3
    other = [("archive/pc/mod/SomethingElse.archive", 5000)]
    assert identify.verify_against_preview(va, other, inst)["coverage"] == 0


def test_nexus_url_inside_mod_files(game):
    touch(game, "archive/pc/mod/#CoolJacket.archive.xl",
          "# Cool Jacket by someone\n# https://www.nexusmods.com/cyberpunk2077/mods/12345\n"
          "# requires ArchiveXL: https://www.nexusmods.com/cyberpunk2077/mods/4198\n")
    mods = build_mod_list(game)
    cj = next(m for m in mods if norm_key(m.name) == "cooljacket")
    found = identify.urls_in_mod(cj, game, os.path.join(game, TEMP_DISABLED_DIR))
    assert found == {12345: 1, 4198: 1}
    own, _ = identify.pick_own_id(found, {4198}, identify.local_names(cj), None)
    assert own == 12345
    # two unrelated non-framework links and no catalog: ambiguous -> no automatic pick
    own, cands = identify.pick_own_id({1: 1, 2: 1}, set(), ["X"], None)
    assert own is None and set(cands) == {1, 2}


def test_rpc_dispatcher(tmp_path):
    api = Api(Config(str(tmp_path / "s.json")))
    assert api.rpc("export_formats", [])[:2] == ["zip", "7z"]
    assert api.rpc("_rescan", [])["ok"] is False and api.rpc("nope", [])["ok"] is False


def test_numbered_sibling_mods_never_match():
    """H8MegabuildingUnlocked was linked to the H10 mod's page."""
    assert identify.numbers_conflict("H8MegabuildingUnlocked", "H10 Megabuilding Unlocked")
    assert identify.similarity("H8MegabuildingUnlocked", "H10 Megabuilding Unlocked") < 0.5
    assert identify.similarity("H10MegabuildingUnlocked", "H10 Megabuilding Unlocked") == 1.0
    cat = identify.Catalog([{"mod_id": 10, "name": "H10 Megabuilding Unlocked"}])
    own, cands = identify.pick_own_id({10: 3}, set(), ["H8MegabuildingUnlocked"], cat)
    assert own is None   # the H10 URL copied into H8's .xl is offered, not auto-linked


def test_unlink_is_remembered(game, tmp_path):
    api = Api(Config(str(tmp_path / "s.json")))
    api.set_game_dir(game)
    api.get_mods()
    key = next(m.key for m in api._mods if norm_key(m.name) == "cooljacket")
    api._cfg.set("nexus_links", {key: {"mod_id": 99, "method": "in_files"}})
    api.nexus_unlink(key)
    assert key not in api._cfg.get("nexus_links") and f"{key}|99" in api._cfg.get("nexus_rejected")


def test_github_helpers():
    from cp77mlt import github
    assert github.parse_repo("https://github.com/psiberx/cp2077-red-hot-tools/releases/tag/v1.0") == "psiberx/cp2077-red-hot-tools"
    assert github.parse_repo("owner/repo") == "owner/repo" and github.parse_repo("nope") is None
    assert github.version_of({"tag_name": "v1.2.3"}) == "1.2.3"
    rels = [{"tag_name": "v1.0", "published_at": "2024-01-01T00:00:00Z"}, {"tag_name": "v1.1", "published_at": "2025-01-01T00:00:00Z"}]
    assert github.version_of(github.estimate_installed(rels, github.published_ts(rels[0]) + 3600)) == "1.0"
    a = github.pick_asset({"assets": [{"name": "Source.zip"}, {"name": "RedHotTools-1.1.zip"}]}, "RedHotTools")
    assert a["name"] == "RedHotTools-1.1.zip"


def test_catalog_dedupes_and_merges_live_results():
    cat = identify.Catalog([{"mod_id": 1, "name": "H10 Megabuilding Unlocked"}, {"mod_id": 1, "name": "H10 Megabuilding Unlocked"},
                            {"mod_id": 2, "name": "Interact with H10 Megabuilding"}])
    assert len(cat.mods) == 2
    assert [m["mod_id"] for m in cat.search("H10 Megabuilding")].count(1) == 1
    cat.add([{"mod_id": 3, "name": "Corpo Apt Room Unlock"}])           # missing from the cached list
    assert cat.search("Corpo Apt Room Unlock")[0]["mod_id"] == 3
    ranked = identify.merge_ranked("Corpo Apt Room Unlock", [{"mod_id": 9, "name": "Corpo SOFAs"}],
                                   [{"mod_id": 3, "name": "Corpo Apt Room Unlock"}, {"mod_id": 9, "name": "Corpo SOFAs"}])
    assert [m["mod_id"] for m in ranked] == [3, 9]


def test_report_can_omit_grouped_section(game, tmp_path):
    mods = build_mod_list(game)
    out = report.generate(str(tmp_path / "l.txt"), game_dir=game, game_version="2.3", phantom_liberty=True, store="Steam",
                          mods=mods, core=core_mods.status(game), log_names=[], include_errors=False,
                          include_disabled=True, manager=None, include_grouped=False)
    text = open(out, encoding="utf-8-sig").read()
    assert "Installed Mods (" not in text and "Folder Listing" in text


def test_disabled_mods_not_offered_updates(game, tmp_path):
    api = Api(Config(str(tmp_path / "s.json")))
    api.set_game_dir(game)
    api.get_mods()
    off = next(m for m in api._mods if not m.enabled)
    on = next(m for m in api._mods if m.enabled and m.source == "loose")
    api._updates = {off.key: {"update": True, "latest": "2"}, on.key: {"update": True, "latest": "2"}}
    keys = [r["key"] for r in api.get_updates()["updates"]]
    assert on.key in keys and off.key not in keys
    assert api._summary()["updates"] == 1


def test_stub_files_are_never_listed(game):
    from cp77mlt.scanner import raw_listing
    touch(game, "mods/placeholder.stub")
    touch(game, "archive/pc/mod/thing.stub")
    listing = raw_listing(game, include_disabled=True)
    assert not any(n.endswith(".stub") for items in listing.values() for n, _ in items)
    assert not any("stub" in m.name.lower() for m in build_mod_list(game))


def test_rar_export_passes_utf8_list(game, tmp_path, monkeypatch):
    """v3.0 passed -scul (UTF-16) for a UTF-8 list, so WinRAR reported 'No files'."""
    fake = tmp_path / "rar.py"
    fake.write_text(
        "import sys, os\n"
        "args = sys.argv[1:]\n"
        "out = [a for a in args[1:] if not a.startswith(('-', '@'))][0]\n"
        "lst = [a for a in args if a.startswith('@')]\n"
        "if lst:\n"
        "    assert '-scfl' in args, 'list charset must be UTF-8'\n"
        "    names = open(lst[0][1:], encoding='utf-8').read().split()\n"
        "    assert names and all(os.path.exists(n) for n in names), names\n"
        "open(out, 'ab').write(b'x' * 100)\n")
    if sys.platform == "win32":
        wrapper = tmp_path / "rar.cmd"
        wrapper.write_text(f'@"{sys.executable}" "{fake}" %*\r\n')
    else:
        wrapper = tmp_path / "rar"
        wrapper.write_text(f'#!/bin/sh\n"{sys.executable}" "{fake}" "$@"\n')
        wrapper.chmod(0o755)
    monkeypatch.setattr(ops, "find_rar", lambda: str(wrapper))
    mods = [m for m in build_mod_list(game) if m.enabled]
    out = str(tmp_path / "preset.rar")
    r = ops.export_preset(game, mods, out)
    assert os.path.exists(out) and r["files"] > 3


def test_backups_info_and_clear(game, tmp_path):
    arc = tmp_path / "m.zip"
    with zipfile.ZipFile(arc, "w") as z:
        z.writestr("archive/pc/mod/#CoolJacket.archive", "v2")
    ops.install_archive(game, str(arc))
    info = ops.backups_info(game)
    assert info["files"] == 1 and "_Backups (replaced files)" in info["path"]
    ops.clear_backups(game)
    assert ops.backups_info(game)["files"] == 0


def test_preset_overwrite_replaces_in_place(game, tmp_path):
    arc = tmp_path / "preset.zip"
    with zipfile.ZipFile(arc, "w") as z:
        z.writestr("archive/pc/mod/#CoolJacket.archive", "from-preset")
    r = ops.install_archive(game, str(arc), None, overwrite=True)
    assert r["overwritten"] and r["backup"] is None
    with open(os.path.join(game, "archive", "pc", "mod", "#CoolJacket.archive")) as f:
        assert f.read() == "from-preset"
    assert not ops.backup_dirs(game)  # nothing parked


def test_mod_backup_roundtrip_schedule_and_prune(game, tmp_path):
    from cp77mlt import backups
    mods = build_mod_list(game)
    folder = str(tmp_path / "bk")
    r = backups.create(game, mods, folder, "manual", "2.3")
    with zipfile.ZipFile(r["path"]) as z:
        names = z.namelist()
    assert backups.MANIFEST in names and "archive/pc/mod/#CoolJacket.archive" in names
    assert "red4ext/RED4ext.dll" in names and not any(n.startswith("engine/") for n in names)
    lst = backups.list_backups(folder)
    assert len(lst) == 1 and lst[0]["kind"] == "manual" and lst[0]["mods"] >= 1
    # restore after the mod changed: original content comes back, changed copy kept
    p = os.path.join(game, "archive", "pc", "mod", "#CoolJacket.archive")
    with open(p, "w") as f:
        f.write("changed")
    rr = backups.restore(game, r["path"], overwrite=False)
    assert rr["restored"] == r["files"] and rr["backup"]
    with open(p) as f:
        assert f.read() != "changed"
    # scheduling + pruning keeps manual backups
    import time as _t
    for i in range(3):
        _t.sleep(1.05)
        backups.create(game, mods, folder, "scheduled")
    assert len(backups.prune(folder, 2)) == 1
    kinds = [b["kind"] for b in backups.list_backups(folder)]
    assert kinds.count("scheduled") == 2 and kinds.count("manual") == 1
    assert backups.is_due("daily", None, 1e9) and not backups.is_due("off", None, 1e9)
    assert not backups.is_due("weekly", 1e9 - 3600, 1e9)
    with pytest.raises(ValueError):
        backups.delete(folder, str(tmp_path / "random.zip"))


def test_window_state_roundtrip():
    from types import SimpleNamespace
    from cp77mlt import winstate

    class Ev:
        def __init__(self): self.fns = []
        def __iadd__(self, f): self.fns.append(f); return self
        def set(self, *a):
            for f in self.fns: f(*a)

    class Cfg(dict):
        def set(self, k, v): self[k] = v

    assert winstate.initial(None) == {"width": 1320, "height": 840}
    assert winstate.initial({"x": -32000, "y": -32000, "width": 50, "height": 50}) == {"width": 1320, "height": 840}
    geo = winstate.initial({"x": 2000, "y": 150, "width": 1500, "height": 900})
    assert geo == {"width": 1500, "height": 900, "x": 2000, "y": 150}
    win = SimpleNamespace(events=SimpleNamespace(**{n: Ev() for n in
                          ("moved", "resized", "maximized", "minimized", "restored", "shown", "closing")}), move=lambda x, y: None)
    cfg = Cfg()
    winstate.Tracker(cfg, win, geo)
    win.events.moved.set(2100, 200); win.events.resized.set(1400, 880)
    win.events.minimized.set(); win.events.moved.set(-32000, -32000); win.events.restored.set()
    win.events.maximized.set(); win.events.resized.set(2560, 1400)
    win.events.closing.set()
    assert cfg["window"] == {"x": 2100, "y": 200, "width": 1400, "height": 880, "maximized": True}
    win.events.restored.set(); win.events.closing.set()
    assert cfg["window"]["maximized"] is False
    scr = [SimpleNamespace(x=0, y=0, width=1920, height=1080)]
    assert winstate.visible(100, 100, 1320, scr) and not winstate.visible(2500, 100, 1320, scr)


def test_unlinked_count_respects_disabled_setting(game, tmp_path):
    from cp77mlt.api import Api
    api = Api(Config(str(tmp_path / "s.json")))
    api._cfg.set("game_dir", game)
    api._ensure_scan()
    loose = [m for m in api._mods if m.source == "loose" and not m.nexus_id]
    disabled = [m for m in loose if not m.enabled]
    assert disabled, "fixture should include a disabled manual mod"
    assert len(api._unlinked_mods()) == len(loose) - len(disabled)
    api._cfg.set("queue_include_disabled", True)
    assert len(api._unlinked_mods()) == len(loose)
    api._cfg.set("github_links", {loose[0].key: {"repo": "a/b"}})
    assert len(api._unlinked_mods()) == len(loose) - 1


# --- grouping pieces of one mod / optional-file updates / install folder ----------------
def _amm(game):
    touch(game, "bin/x64/plugins/cyber_engine_tweaks/mods/AppearanceMenuMod/init.lua")
    touch(game, "archive/pc/mod/AMM_Props.archive")
    touch(game, "archive/pc/mod/AMM_Collab.archive")


def test_pieces_linked_to_one_nexus_mod_count_once(game):
    _amm(game)
    loose = {m.key: m for m in build_mod_list(game)}
    before = len(loose)
    links = {"loose:appearancemenumod": {"mod_id": 790, "name": "Appearance Menu Mod", "version": "2.6"},
             "loose:ammprops": {"mod_id": 790, "version": "1.1"},       # optional file, own lower version
             "loose:ammcollab": {"mod_id": 790, "version": "1.0"}}
    mods = build_mod_list(game, links=links)
    assert len(mods) == before - 2
    amm = next(m for m in mods if m.nexus_id == 790)
    assert amm.name == "Appearance Menu Mod" and amm.version == "2.6"
    assert set(amm.locations()) == {"cet", "archive"} and len(amm.members) == 3
    assert amm.key == "loose:appearancemenumod"            # CET folder is the anchor
    assert amm.to_dict()["grouped"] is True
    # setting off: listed separately again
    assert len(build_mod_list(game, links=links, group_by_link=False)) == before


def test_install_groups_merge_differently_named_files(game):
    _amm(game)
    n = len(build_mod_list(game))
    groups = [["bin/x64/plugins/cyber_engine_tweaks/mods/appearancemenumod", "archive/pc/mod/amm_props",
               "archive/pc/mod/amm_collab"]]
    mods = build_mod_list(game, groups=groups)
    assert len(mods) == n - 2
    amm = next(m for m in mods if "cet" in m.locations())
    assert sum(len(c.rel_paths) for c in amm.components) == 3 and amm.enabled


def test_install_records_group_and_install_dir(game, tmp_path, monkeypatch):
    from cp77mlt.api import Api
    api = Api(Config(str(tmp_path / "s.json")))
    api._cfg.set("game_dir", game)
    api._remember_install_group(["bin/x64/plugins/cyber_engine_tweaks/mods/X/init.lua", "archive/pc/mod/X_a.archive"])
    api._remember_install_group(["archive/pc/mod/X_a.archive", "r6/scripts/X2/a.reds"])   # update of the same mod
    api._remember_install_group(["archive/pc/mod/Solo.archive"])                         # single piece: nothing to record
    g = api._cfg.get("install_groups")
    assert len(g) == 1 and set(g[0]) == {"bin/x64/plugins/cyber_engine_tweaks/mods/x", "archive/pc/mod/x_a", "r6/scripts/x2"}
    dl = tmp_path / "dl"
    dl.mkdir()
    monkeypatch.setattr(identify, "downloads_dir", lambda: str(dl))
    assert api._install_start_dir() == str(dl)              # never the game folder by default
    other = tmp_path / "mods"
    other.mkdir()
    api._cfg.set("last_install_dir", str(other))
    assert api._install_start_dir() == str(other)


def test_optional_file_with_lower_version_is_not_an_update():
    files = {"files": [
        {"file_id": 1, "version": "2.5", "category_name": "OLD_VERSION", "uploaded_timestamp": 100},
        {"file_id": 2, "version": "2.6", "category_name": "MAIN", "uploaded_timestamp": 200},
        {"file_id": 3, "version": "1.1", "category_name": "OPTIONAL", "uploaded_timestamp": 150},
        {"file_id": 4, "version": "1.0", "category_name": "OLD_VERSION", "uploaded_timestamp": 90},
        {"file_id": 5, "version": "1.1", "category_name": "OPTIONAL", "uploaded_timestamp": 160}],
        "file_updates": [{"old_file_id": 1, "new_file_id": 2}, {"old_file_id": 4, "new_file_id": 5}]}
    st = nexus.installed_file_status
    assert st(files, "1.1")["current"] is True                 # optional by version
    assert st(files, None, 3)["current"] is True               # optional by file id
    assert st(files, None, None, 150)["current"] is True       # by upload timestamp in the download name
    old = st(files, None, 4)
    assert old["current"] is False and old["file_id"] == 5 and old["latest"] == "1.1"
    assert st(files, None, 1)["file_id"] == 2
    assert st(files, "2.5") is None                            # only an old version has it: unknown -> page check
    assert st(files, "2.6")["current"] is True


def test_update_check_respects_optional_files(game, tmp_path):
    from cp77mlt.api import Api
    _amm(game)

    class FakeClient:
        rate = {}

        def updated(self, _p):
            return []

        def mod(self, mid, ttl=0):
            return {"version": "2.6", "name": "AMM"}

        def files(self, mid, ttl=0):
            return {"files": [{"file_id": 2, "version": "2.6", "category_name": "MAIN"},
                              {"file_id": 3, "version": "1.1", "category_name": "OPTIONAL"}]}

    api = Api(Config(str(tmp_path / "s.json")))
    api._cfg.set("game_dir", game)
    api._cfg.set("nexus_links", {"loose:ammprops": {"mod_id": 790, "version": "1.1"}})
    api._updates = {}
    api._nexus = FakeClient()
    api._save_updates = lambda: None
    api._ensure_scan()
    r = api.nexus_check_updates(["loose:ammprops"])
    import time as _t
    for _ in range(100):
        if api.get_task(r["task"])["done"]:
            break
        _t.sleep(0.02)
    assert api.get_task(r["task"])["error"] is None
    assert api._updates["loose:ammprops"]["update"] is False


def test_update_of_one_piece_keeps_the_others(game, tmp_path):
    _amm(game)
    links = {"loose:appearancemenumod": {"mod_id": 790}, "loose:ammprops": {"mod_id": 790}}
    amm = next(m for m in build_mod_list(game, links=links) if m.nexus_id == 790)
    keep = ops._replaced_components(amm, ["archive/pc/mod/AMM_Props.archive"])
    assert {c.member for c in keep} == {"loose:ammprops"}


# --- trending (7 days) / tracked cache ------------------------------------------------
class _Resp:
    def __init__(self, body):
        self._b = body

    def json(self):
        return self._b


def test_trending_is_last_7_days_ranked_by_endorsements(monkeypatch):
    import time as _t
    now = _t.time()
    iso = lambda days: _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime(now - days * 86400))  # noqa: E731
    nodes = [{"modId": 1, "name": "new low", "createdAt": iso(1), "endorsements": 5},
             {"modId": 2, "name": "new high", "createdAt": iso(3), "endorsements": 900, "summary": "s",
              "pictureUrl": "p", "author": "a", "version": "1", "updatedAt": iso(2), "adultContent": False, "status": "PUBLISHED"},
             {"modId": 3, "name": "old classic", "createdAt": iso(400), "endorsements": 99999}]
    calls = []

    def post(url, json=None, timeout=None):
        calls.append(json["variables"]["o"])
        return _Resp({"data": {"mods": {"nodes": nodes if json["variables"]["o"] == 0 else []}}})
    c = nexus.NexusClient("k")
    monkeypatch.setattr(c.session, "post", post)
    res = c.trending(days=7)
    assert [x["mod_id"] for x in res] == [2, 1]        # all-time hit (3) excluded, ranked by endorsements
    assert res[0]["card"]["name"] == "new high" and res[0]["card"]["status"] == "published"
    assert calls == [0]                                # stopped paging once mods got older than 7 days
    c.trending(days=7)
    assert calls == [0]                                # cached


def test_to_timestamp_formats():
    assert nexus.to_timestamp("2026-11-01T00:00:00Z") == nexus.to_timestamp("2026-11-01T00:00:00+00:00") == 1793491200.0
    assert nexus.to_timestamp(1793491200) == nexus.to_timestamp(1793491200000) == 1793491200.0
    assert nexus.to_timestamp(None) is None and nexus.to_timestamp("garbage") is None


def test_tracked_list_is_cached_between_page_visits(monkeypatch):
    c = nexus.NexusClient("k")
    hits = []

    def req(method, path, **kw):
        hits.append(method)
        return [{"mod_id": 1, "domain_name": "cyberpunk2077"}] if method == "GET" else {}
    monkeypatch.setattr(c, "_req", req)
    for _ in range(5):
        c.tracked()
    assert hits == ["GET"]
    c.track(2)
    assert {d["mod_id"] for d in c.tracked()} == {1, 2} and hits == ["GET", "POST"]
    c.untrack(1)
    assert {d["mod_id"] for d in c.tracked()} == {2}
    c.tracked(fresh=True)
    assert hits.count("GET") == 2


# --- naming the mod behind a log error -------------------------------------------------
def test_log_lines_are_attributed_to_mods(game):
    from cp77mlt import culprits
    touch(game, "archive/pc/mod/Marmur_bank_removal.archive")
    touch(game, "archive/pc/mod/Marmur_bank_removal.xl")
    touch(game, "bin/x64/plugins/cyber_engine_tweaks/mods/NiceCET/init.lua")
    touch(game, "red4ext/plugins/CoolPlugin/CoolPlugin.dll")
    touch(game, "archive/pc/mod/Clothes/sub_folder_item.archive")
    mods = build_mod_list(game)
    by = {m.key: m for m in mods}
    idx = culprits.ModIndex(game, mods)
    name = lambda line: by[idx.match(line)].name if idx.match(line) else None  # noqa: E731
    assert name("[2026-11-08 22:38:26.759] [30504] [error] [WorldStreaming] Marmur_bank_removal.xl: "
                "The target node #389 has type worldCookedStaticMeshNode, but the mod expects worldStaticMeshNode.") \
        == "Marmur_bank_removal"
    assert norm_key(name("ERROR - At r6/scripts/VirtualAtelier/Atelier.reds:12:5: function 'X' not found")) == "virtualatelier"
    assert name(r"[error] C:\Games\Cyberpunk 2077\bin\x64\plugins\cyber_engine_tweaks\mods\NiceCET\init.lua:3: attempt to index nil") == "NiceCET"
    assert name("[error] Plugin 'CoolPlugin' failed to load") == "CoolPlugin"
    assert name("[error] Can't load sub_folder_item.archive") == "Clothes"
    assert name("[error] r6/tweaks/BetterLoot.yaml: unknown record") == "BetterLoot"
    assert name("[error] [ArchiveXL] EquipmentEx.archive.xl: something") is None      # core frameworks never blamed
    assert name("[error] [WorldStreaming] something unrelated happened") is None
    assert name("[error] mods/AnyCET/init.lua failed") is None                          # generic file name only


def test_culprit_summary_counts_per_mod(game):
    from cp77mlt import culprits
    mods = build_mod_list(game)
    issues = {"Redscript": {"path": "x", "errors": ["ERROR - r6/scripts/VirtualAtelier/a.reds: bad", "ERROR - r6/tweaks/BetterLoot.yaml bad",
                                                    "ERROR - r6/scripts/VirtualAtelier/b.reds: bad"], "warnings": []}}
    out = culprits.summarize(culprits.ModIndex(game, mods), issues, {m.key: m for m in mods})
    assert [(norm_key(c["name"]), c["errors"]) for c in out] == [("virtualatelier", 2), ("betterloot", 1)]
    assert out[0]["logs"] == ["Redscript"] and len(out[0]["lines"]) == 2


def test_report_names_mod_next_to_error(game, tmp_path):
    touch(game, "r6/logs/redscript_rCURRENT.log", "ERROR - At r6/scripts/VirtualAtelier/Atelier.reds:1:1: oops\n")
    mods = build_mod_list(game)
    out = report.generate(str(tmp_path / "r.txt"), game_dir=game, game_version="2.3", phantom_liberty=True, store="Steam",
                          mods=mods, core=[], log_names=[], include_errors=True, include_disabled=False, manager=None)
    text = open(out, encoding="utf-8-sig").read()
    assert "Mods named in these errors:" in text and "oops   <-- VirtualAtelier" in text


def test_replaced_files_are_pruned_to_the_last_updates(game):
    base = os.path.join(game, TEMP_DISABLED_DIR, ops.BACKUP_DIR_NAME)
    for stamp in ("20260101-000000", "20260201-000000", "20260301-000000", "20260401-000000"):
        touch(base, f"{stamp}/archive/pc/mod/Old.archive")
    assert ops.prune_backups(game, 2) == 2
    assert sorted(os.listdir(base)) == ["20260301-000000", "20260401-000000"]
    assert ops.prune_backups(game, -1) == 0 and len(os.listdir(base)) == 2
    ops.prune_backups(game, 0)
    assert not os.path.exists(base)
    assert os.path.exists(os.path.join(game, TEMP_DISABLED_DIR, "archive", "pc", "mod", "OldThing.archive"))  # disabled mods untouched


def test_update_task_prunes_replaced_files(game, tmp_path):
    from cp77mlt.api import Api
    api = Api(Config(str(tmp_path / "s.json")))
    api._cfg.set("game_dir", game)
    api._cfg.set("replaced_keep", 1)
    base = os.path.join(game, TEMP_DISABLED_DIR, ops.BACKUP_DIR_NAME)
    for stamp in ("20260101-000000", "20260201-000000"):
        touch(base, f"{stamp}/archive/pc/mod/Old.archive")
    r = api._task("update", lambda prog, c: {})
    import time as _t
    for _ in range(100):
        if api.get_task(r["task"])["done"]:
            break
        _t.sleep(0.02)
    assert os.listdir(base) == ["20260201-000000"]


def _fake_rar(tmp_path, body):
    fake = tmp_path / "rar.py"
    fake.write_text("import sys, os\nargs = sys.argv[1:]\nout = [a for a in args[1:] if not a.startswith(('-', '@'))][0]\n" + body)
    if sys.platform == "win32":
        w = tmp_path / "rar.cmd"
        w.write_text(f'@"{sys.executable}" "{fake}" %*\r\n')
    else:
        w = tmp_path / "rar"
        w.write_text(f'#!/bin/sh\n"{sys.executable}" "{fake}" "$@"\n')
        w.chmod(0o755)
    return str(w)


def test_rar_export_retries_with_utf16_list(game, tmp_path, monkeypatch):
    rar = _fake_rar(tmp_path, "if '-scfl' in args:\n    print('RAR 7.12 x64   Copyright (c) 1993-2025 Alexander Roshal')\n    sys.exit(7)\n"
                              "lst = [a for a in args if a.startswith('@')]\n"
                              "if lst:\n    assert open(lst[0][1:], encoding='utf-16').read().split()\n"
                              "open(out, 'ab').write(b'x' * 100)\n")
    monkeypatch.setattr(ops, "find_rar", lambda: rar)
    out = str(tmp_path / "p.rar")
    assert ops.export_preset(game, [m for m in build_mod_list(game) if m.enabled], out)["files"] > 3
    assert os.path.exists(out)


def test_rar_failure_message_is_readable(game, tmp_path, monkeypatch):
    rar = _fake_rar(tmp_path, "print('RAR 7.12 x64   Copyright (c) 1993-2025 Alexander Roshal   23 Jun 2025')\n"
                              "print('Trial version             Type \\'rar -?\\' for help')\nsys.exit(6)\n")
    monkeypatch.setattr(ops, "find_rar", lambda: rar)
    with pytest.raises(RuntimeError) as e:
        ops.export_preset(game, [m for m in build_mod_list(game) if m.enabled], str(tmp_path / "p.rar"))
    msg = str(e.value)
    assert "couldn't open" in msg and "Copyright" not in msg and "Choose .zip" in msg
    assert not os.path.exists(str(tmp_path / "p.rar.partial"))


def test_debug_log_keeps_only_last_24_hours(tmp_path):
    import time as _t
    p = tmp_path / "cp77mlt.log"
    now = _t.time()
    stamp = lambda age_h: _t.strftime("%Y-%m-%d %H:%M:%S", _t.localtime(now - age_h * 3600))  # noqa: E731
    p.write_text(f"{stamp(50)},1 ERROR cp77mlt: Task export failed\nTraceback (most recent call last):\n  old frame\n"
                 f"{stamp(1)},2 INFO cp77mlt: Starting\n{stamp(0.5)},3 ERROR cp77mlt: new\n  new frame\n", encoding="utf-8")
    old = tmp_path / "cp77mlt.log.1"
    old.write_text("ancient", encoding="utf-8")
    os.utime(old, (now - 72 * 3600, now - 72 * 3600))
    logs.trim_debug_log(str(p), 24, now)
    text = p.read_text(encoding="utf-8")
    assert "export failed" not in text and "old frame" not in text
    assert "Starting" in text and "new frame" in text
    assert not old.exists()


def test_manual_grouping_of_off_nexus_mods(game, tmp_path):
    from cp77mlt.api import Api
    api = Api(Config(str(tmp_path / "s.json")))
    api._cfg.set("game_dir", game)
    api._ensure_scan()
    n = len(api._mods)
    keys = [m.key for m in api._mods if norm_key(m.name) in ("cooljacket", "betterloot")]
    r = api.group_mods(keys, "Jacket Pack")
    assert r["ok"] and len(api._mods) == n - 1
    g = api._mods_by_key[r["key"]]
    assert g.name == "Jacket Pack" and g.manual_group and set(g.locations()) == {"archive", "tweak"}
    api._sig = None
    api._ensure_scan(force=True)                       # survives a rescan
    assert any(m.name == "Jacket Pack" for m in api._mods)
    vortex = next(m.key for m in api._mods if m.source == "vortex")
    assert api.group_mods([vortex, r["key"]])["ok"] is False
    assert api.ungroup_mod(r["key"])["ok"] and len(api._mods) == n
    other = next(m.key for m in api._mods if m.source == "loose")
    assert api.ungroup_mod(other)["ok"] is False      # nothing to ungroup
