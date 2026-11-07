"""Core framework detection.

v2 required *every* file in a hard-coded list to exist, so any framework update
that added/removed a bundle file reported the framework as "Not Installed".
Now each framework has one or two key files; versions are read automatically
where possible and fall back to a user-entered value.
"""
from __future__ import annotations

import glob
import os
import re
import shutil

from .game import file_version
from .scanner import TEMP_DISABLED_DIR

CORE = {
    "RED4ext": {
        "nexus_id": 2380, "key": ["red4ext/RED4ext.dll", "bin/x64/winmm.dll"],
        "version_from": "red4ext/RED4ext.dll",
        "move": ["red4ext/RED4ext.dll", "bin/x64/winmm.dll"],
        "desc": "Native plugin loader required by ArchiveXL, TweakXL and Codeware.",
    },
    "Redscript": {
        "nexus_id": 1511, "key": ["engine/tools/scc.exe"],
        "version_from": "engine/tools/scc_lib.dll",
        "move": ["engine/tools/scc.exe", "engine/tools/scc_lib.dll", "engine/config/base/scripts.ini",
                 "r6/config/cybercmd/scc.toml"],
        "desc": "Script compiler for .reds mods.",
    },
    "Cyber Engine Tweaks": {
        "nexus_id": 107, "key": ["bin/x64/plugins/cyber_engine_tweaks.asi"],
        "version_from": "bin/x64/plugins/cyber_engine_tweaks.asi",
        "move": ["bin/x64/plugins/cyber_engine_tweaks.asi", "bin/x64/version.dll", "bin/x64/global.ini"],
        "desc": "Lua scripting framework and in-game overlay.",
    },
    "ArchiveXL": {
        "nexus_id": 4198, "key": ["red4ext/plugins/ArchiveXL/ArchiveXL.dll"],
        "version_from": "red4ext/plugins/ArchiveXL/ArchiveXL.dll",
        "move": ["red4ext/plugins/ArchiveXL", "r6/config/redsUserHints/ArchiveXL.toml"],
        "desc": "Loads custom resources, appearances and world edits.",
    },
    "TweakXL": {
        "nexus_id": 4197, "key": ["red4ext/plugins/TweakXL/TweakXL.dll"],
        "version_from": "red4ext/plugins/TweakXL/TweakXL.dll",
        "move": ["red4ext/plugins/TweakXL"],
        "desc": "Loads TweakDB edits from r6/tweaks.",
    },
    "Codeware": {
        "nexus_id": 7780, "key": ["red4ext/plugins/Codeware/Codeware.dll"],
        "version_from": "red4ext/plugins/Codeware/Codeware.dll",
        "move": ["red4ext/plugins/Codeware"],
        "desc": "Redscript library many UI and gameplay mods depend on.",
    },
    "EquipmentEx": {
        "nexus_id": 6945, "key": ["r6/scripts/EquipmentEx"],
        "version_from": None,
        "move": ["r6/scripts/EquipmentEx", "archive/pc/mod/EquipmentEx.archive",
                 "archive/pc/mod/EquipmentEx.archive.xl", "r6/config/redsUserHints/EquipmentEX.toml"],
        "desc": "Outfit system used by many clothing mods.",
    },
}


def _p(game_dir: str, rel: str) -> str:
    return os.path.join(game_dir, *rel.split("/"))


def _exists_ci(game_dir: str, rel: str) -> bool:
    """Case-insensitive existence check (game files differ in case across stores)."""
    path = _p(game_dir, rel)
    if os.path.exists(path):
        return True
    parent, name = os.path.split(path)
    try:
        return any(n.lower() == name.lower() for n in os.listdir(parent))
    except OSError:
        return False


def _cet_version(game_dir: str) -> str | None:
    log = _p(game_dir, "bin/x64/plugins/cyber_engine_tweaks/cyber_engine_tweaks.log")
    try:
        with open(log, "rb") as f:
            head = f.read(64 * 1024).decode("utf-8", errors="replace")
        m = re.search(r"CET version v?([\d.]+)", head)
        return m.group(1) if m else None
    except OSError:
        return None


def _redscript_version(game_dir: str) -> str | None:
    logs = sorted(glob.glob(_p(game_dir, "r6/logs/redscript_r*.log")), key=os.path.getmtime, reverse=True)
    for log in logs[:2]:
        try:
            with open(log, "rb") as f:
                head = f.read(16 * 1024).decode("utf-8", errors="replace")
            m = re.search(r"redscript(?: compiler)?\s+v?(\d+\.\d+\.\d+[\w.\-]*)", head, re.I)
            if m:
                return m.group(1)
        except OSError:
            continue
    return None


def _equipmentex_version(game_dir: str) -> str | None:
    folder = _p(game_dir, "r6/scripts/EquipmentEx")
    for path in glob.glob(os.path.join(folder, "*.reds")):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            m = re.search(r'Version\(\)\s*->\s*String\s*(?:=|\{\s*return)\s*"([^"]+)"', text)
            if m:
                return m.group(1)
        except OSError:
            continue
    return None


def _clean_version(v: str | None) -> str | None:
    if not v or v == "0.0.0.0":
        return None
    return re.sub(r"(\.0)+$", "", v) if v.count(".") > 2 else v


def status(game_dir: str, manual_versions: dict | None = None) -> list[dict]:
    manual_versions = manual_versions or {}
    out = []
    for name, info in CORE.items():
        installed = bool(game_dir) and all(_exists_ci(game_dir, k) for k in info["key"])
        disabled = bool(game_dir) and not installed and all(
            _exists_ci(os.path.join(game_dir, TEMP_DISABLED_DIR), k) for k in info["key"])
        version, version_source = None, None
        if installed:
            if info["version_from"]:
                version = _clean_version(file_version(_p(game_dir, info["version_from"])))
                version_source = "file" if version else None
            if not version:
                extra = {"Cyber Engine Tweaks": _cet_version, "Redscript": _redscript_version,
                         "EquipmentEx": _equipmentex_version}.get(name)
                version = extra(game_dir) if extra else None
                version_source = "detected" if version else None
            if not version and manual_versions.get(name):
                version, version_source = manual_versions[name], "manual"
        out.append({"name": name, "installed": installed, "disabled": disabled,
                    "version": version, "version_source": version_source,
                    "nexus_id": info["nexus_id"], "desc": info["desc"]})
    return out


def set_core_enabled(game_dir: str, enable: bool) -> list[str]:
    """Move core framework files to/from the disabled folder. Returns error strings."""
    errors = []
    disabled_root = os.path.join(game_dir, TEMP_DISABLED_DIR)
    for name, info in CORE.items():
        for rel in info["move"]:
            live, parked = _p(game_dir, rel), _p(disabled_root, rel)
            src, dst = (parked, live) if enable else (live, parked)
            if not os.path.exists(src):
                continue
            if os.path.exists(dst):
                errors.append(f"{name}: '{rel}' already exists at the destination; left both copies untouched.")
                continue
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.move(src, dst)
            except OSError as e:
                errors.append(f"{name}: could not move '{rel}': {e}")
    return errors
