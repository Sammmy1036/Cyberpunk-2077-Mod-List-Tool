"""Read-mostly integration with Vortex and Mod Organizer 2.

Vortex deploys files into the game folder (hardlinks by default) and records
every deployed file in ``vortex.deployment*.json`` manifests. We read those to
attribute loose files to the Vortex mod that owns them; we never move Vortex
files ourselves, because Vortex would flag them as externally modified.

MO2 keeps mods in its own ``mods`` folder and overlays them with a virtual
filesystem only while the game is launched through MO2. We read the instance,
the active profile's ``modlist.txt`` and each mod's ``meta.ini``. Toggling a
mod edits ``modlist.txt`` (only while MO2 is closed, since MO2 rewrites it).
"""
from __future__ import annotations

import configparser
import glob
import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# Vortex
# ---------------------------------------------------------------------------
_VORTEX_NAME_RE = re.compile(r"^(?P<name>.+?)-(?P<modid>\d+)-(?P<ver>[0-9][0-9A-Za-z\-]*?)-(?P<ts>\d{9,11})$")


def parse_vortex_folder_name(folder: str) -> dict:
    """'Appearance Menu Mod-790-2-6-1-1700000000' -> name / Nexus id / version."""
    m = _VORTEX_NAME_RE.match(folder)
    if not m:
        return {"name": folder, "mod_id": None, "version": None}
    return {"name": m.group("name").strip(), "mod_id": int(m.group("modid")),
            "version": m.group("ver").replace("-", ".")}


def vortex_installed() -> bool:
    if sys.platform != "win32":
        return False
    return os.path.isdir(os.path.join(os.environ.get("APPDATA", ""), "Vortex"))


def read_vortex_manifests(game_dir: str) -> dict:
    """Return {"files": {relpath_lower_posix: source_folder}, "staging": path|None, "manifests": [...]}."""
    result = {"files": {}, "staging": None, "manifests": []}
    if not game_dir:
        return result
    patterns = [os.path.join(game_dir, "vortex.deployment*.json"),
                os.path.join(game_dir, "*", "vortex.deployment*.json"),
                os.path.join(game_dir, "*", "*", "vortex.deployment*.json")]
    paths = []
    for p in patterns:
        paths.extend(glob.glob(p))
    for path in sorted(set(paths)):
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except (OSError, ValueError):
            continue
        prefix = os.path.relpath(os.path.dirname(path), game_dir).replace("\\", "/")
        prefix = "" if prefix == "." else prefix.strip("/") + "/"
        count = 0
        for entry in data.get("files", []) or []:
            rel = str(entry.get("relPath", "")).replace("\\", "/").lstrip("/")
            src = entry.get("source")
            if rel and src:
                result["files"][(prefix + rel).lower()] = src
                count += 1
        if data.get("stagingPath"):
            result["staging"] = data["stagingPath"]
        result["manifests"].append({"path": path, "files": count})
    return result


# ---------------------------------------------------------------------------
# Mod Organizer 2
# ---------------------------------------------------------------------------
def _ini_value(raw: str | None) -> str:
    if raw is None:
        return ""
    raw = raw.strip()
    if raw.startswith("@ByteArray(") and raw.endswith(")"):
        raw = raw[len("@ByteArray("):-1]
    if len(raw) >= 2 and raw[0] == raw[-1] == '"':
        raw = raw[1:-1]
    return raw.replace("\\\\", "\\")


def _read_ini(path: str) -> configparser.RawConfigParser:
    cp = configparser.RawConfigParser(strict=False, interpolation=None)
    cp.optionxform = str  # MO2 keys are case-sensitive
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            cp.read_file(f)
    except (OSError, configparser.Error):
        pass
    return cp


def find_mo2_instances(extra: list[str] | None = None) -> list[str]:
    """Folders containing a ModOrganizer.ini for Cyberpunk 2077."""
    candidates = list(extra or [])
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates += glob.glob(os.path.join(local, "ModOrganizer", "*"))
    out = []
    for c in candidates:
        ini = os.path.join(c, "ModOrganizer.ini")
        if os.path.isfile(ini):
            cp = _read_ini(ini)
            game = _ini_value(cp.get("General", "gameName", fallback="")).lower()
            if "cyberpunk" in game and os.path.normpath(c) not in out:
                out.append(os.path.normpath(c))
    return out


class MO2Instance:
    def __init__(self, path: str, profile: str | None = None):
        self.path = os.path.normpath(path)
        self.ini_path = os.path.join(self.path, "ModOrganizer.ini")
        if not os.path.isfile(self.ini_path):
            raise FileNotFoundError(f"No ModOrganizer.ini in {path}")
        self.ini = _read_ini(self.ini_path)
        g = lambda s, k, d="": _ini_value(self.ini.get(s, k, fallback=d))  # noqa: E731
        self.game_name = g("General", "gameName")
        self.game_path = os.path.normpath(g("General", "gamePath")) if g("General", "gamePath") else ""
        base = g("Settings", "base_directory") or self.path

        def resolve(value: str, default: str) -> str:
            v = (value or default).replace("%BASE_DIR%", base)
            return os.path.normpath(v if os.path.isabs(v) else os.path.join(base, v))

        self.base_dir = os.path.normpath(base)
        self.mods_dir = resolve(g("Settings", "mod_directory"), os.path.join(base, "mods"))
        self.profiles_dir = resolve(g("Settings", "profiles_directory"), os.path.join(base, "profiles"))
        self.overwrite_dir = resolve(g("Settings", "overwrite_directory"), os.path.join(base, "overwrite"))
        self.profile = profile or g("General", "selected_profile") or "Default"
        exe = os.path.join(self.path, "ModOrganizer.exe")
        self.exe = exe if os.path.isfile(exe) else None
        self.is_portable = os.path.isfile(os.path.join(self.path, "portable.txt"))
        self.instance_name = "" if self.is_portable else os.path.basename(self.path)

    # -- profiles & executables -------------------------------------------
    def profiles(self) -> list[str]:
        try:
            return sorted(d for d in os.listdir(self.profiles_dir)
                          if os.path.isfile(os.path.join(self.profiles_dir, d, "modlist.txt")))
        except OSError:
            return []

    def executables(self) -> list[dict]:
        out = []
        if not self.ini.has_section("customExecutables"):
            return out
        sec = self.ini["customExecutables"]
        try:
            size = int(sec.get("size", "0"))
        except ValueError:
            size = 0
        for i in range(1, size + 1):
            title = _ini_value(sec.get(f"{i}\\title"))
            binary = _ini_value(sec.get(f"{i}\\binary"))
            if title:
                out.append({"title": title, "binary": binary})
        return out

    def default_game_executable(self) -> str | None:
        exes = self.executables()
        for e in exes:
            if e["binary"].lower().endswith("cyberpunk2077.exe"):
                return e["title"]
        return exes[0]["title"] if exes else None

    def shortcut(self, title: str) -> str:
        return f"moshortcut://{self.instance_name}:{title}"

    # -- mods ------------------------------------------------------------------
    @property
    def modlist_path(self) -> str:
        return os.path.join(self.profiles_dir, self.profile, "modlist.txt")

    def _read_modlist(self) -> list[str]:
        try:
            with open(self.modlist_path, "r", encoding="utf-8-sig", errors="replace") as f:
                return f.read().splitlines()
        except OSError:
            return []

    def mods(self) -> list[dict]:
        """Mods in priority order (highest first) with enabled state and meta.ini data."""
        out = []
        for line in self._read_modlist():
            if not line or line[0] not in "+-" or line.rstrip().endswith("_separator"):
                continue
            name = line[1:]
            folder = os.path.join(self.mods_dir, name)
            meta = _read_ini(os.path.join(folder, "meta.ini"))
            gm = lambda k: _ini_value(meta.get("General", k, fallback=""))  # noqa: E731
            try:
                mod_id = int(gm("modid") or 0) or None
            except ValueError:
                mod_id = None
            out.append({
                "name": name,
                "enabled": line[0] == "+",
                "folder": folder,
                "mod_id": mod_id,
                "version": gm("version") or None,
                "newest_version": gm("newestVersion") or None,
                "installation_file": gm("installationFile") or None,
                "files": _list_files(folder),
            })
        return out

    def set_enabled(self, names: list[str], enabled: bool) -> int:
        """Flip +/- for the given mods in modlist.txt. Caller must ensure MO2 is closed."""
        wanted = set(names)
        lines = self._read_modlist()
        changed = 0
        for i, line in enumerate(lines):
            if line and line[0] in "+-" and line[1:] in wanted:
                new = ("+" if enabled else "-") + line[1:]
                if new != line:
                    lines[i] = new
                    changed += 1
        if changed:
            tmp = self.modlist_path + ".cp77mlt.tmp"
            with open(tmp, "w", encoding="utf-8", newline="\r\n") as f:
                f.write("\n".join(lines) + "\n")
            os.replace(tmp, self.modlist_path)
        return changed

    def summary(self) -> dict:
        return {"path": self.path, "profile": self.profile, "profiles": self.profiles(),
                "game_path": self.game_path, "exe": self.exe, "portable": self.is_portable,
                "executables": self.executables(), "default_executable": self.default_game_executable()}


def _list_files(folder: str, limit: int = 5000) -> list[str]:
    out = []
    for root, _dirs, files in os.walk(folder):
        for fn in files:
            if fn.lower() == "meta.ini":
                continue
            out.append(os.path.relpath(os.path.join(root, fn), folder).replace("\\", "/"))
            if len(out) >= limit:
                return out
    return out
