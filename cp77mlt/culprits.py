"""Work out which installed mod a log line is about.

Framework logs usually name the file that caused a problem, e.g.

    [error] [WorldStreaming] Marmur_bank_removal.xl: The target node #389 has type ...
    ERROR - At r6/scripts/OldHud/hud.reds:12:5: function 'GetHUD' not found
    [error] Plugin 'Foo' failed to load

so a line is matched, in this order, against:
1. game-relative paths of installed mod files/folders (r6/scripts/OldHud/...),
2. file names (Marmur_bank_removal.xl, Foo.yaml, Bar.archive) that belong to exactly one mod,
3. a folder name in a path (.../cyber_engine_tweaks/mods/Foo/init.lua, red4ext/plugins/Foo/...),
4. a quoted or bracketed name equal to a CET / RED4ext / REDmod folder ('Foo', [Foo]).
Core frameworks are never blamed: they aren't in the mod list.
"""
from __future__ import annotations

import os
import re

from .scanner import TEMP_DISABLED_DIR, Mod

FILE_EXT = ("archive.xl", "archive", "xl", "reds", "yaml", "yml", "tweak", "lua", "dll", "asi", "xml", "json")
_FILE_TOKEN = re.compile(r"[^\s/\\:'\"`\[\]<>|(),;]+\.(?:" + "|".join(re.escape(e) for e in FILE_EXT) + r")(?![\w.])", re.I)
_QUOTED = re.compile(r"'([^'\n]{3,80})'|\"([^\"\n]{3,80})\"|\[([^\]\n]{3,80})\]")
# Folders whose direct children are one mod each
_PARENTS = ("cyber_engine_tweaks/mods/", "red4ext/plugins/", "r6/scripts/", "r6/tweaks/", "archive/pc/mod/", "mods/")
# Names too generic to identify a mod on their own
_GENERIC = {"init.lua", "info.json", "config.json", "settings.json", "db.sqlite3", "main.reds", "module.reds"}
_MAX_DIR_FILES = 3000


class ModIndex:
    def __init__(self, game_dir: str, mods: list[Mod]):
        self.paths: dict[str, str] = {}          # 'r6/scripts/oldhud' -> key
        self.names: dict[str, set[str]] = {}     # 'marmur_bank_removal.xl' -> {key}
        self.folders: dict[str, set[str]] = {}   # 'oldhud' -> {key}   (dir components)
        self.labels: dict[str, set[str]] = {}    # 'foo' -> {key}      (CET/RED4ext/REDmod folder names)
        disabled_root = os.path.join(game_dir, TEMP_DISABLED_DIR) if game_dir else ""
        for m in mods:
            if m.source == "mo2":
                for f in m.files:
                    self._add_file(f.replace("\\", "/"), m.key)
                continue
            for c in m.components:
                for rel in c.rel_paths:
                    low = rel.lower()
                    self.paths[low] = m.key
                    if c.is_dir:
                        self.folders.setdefault(c.name.lower(), set()).add(m.key)
                        if c.location in ("cet", "red4ext", "redmod"):
                            self.labels.setdefault(c.name.lower(), set()).add(m.key)
                        if game_dir:
                            self._walk(os.path.join(disabled_root if c.disabled else game_dir, *rel.split("/")), m.key)
                    else:
                        self._add_file(low, m.key)

    def _add_file(self, rel: str, key: str) -> None:
        base = rel.rsplit("/", 1)[-1].lower()
        if base and base not in _GENERIC:
            self.names.setdefault(base, set()).add(key)

    def _walk(self, path: str, key: str) -> None:
        n = 0
        for _cur, _dirs, files in os.walk(path):
            for fn in files:
                self._add_file(fn, key)
                n += 1
                if n >= _MAX_DIR_FILES:
                    return

    @staticmethod
    def _one(keys: set[str] | None) -> str | None:
        return next(iter(keys)) if keys and len(keys) == 1 else None

    def match(self, line: str) -> str | None:
        low = line.lower().replace("\\", "/")
        # 1) a game-relative path to an installed mod file/folder
        best = None
        for p, key in self.paths.items():
            i = low.find(p)
            if i >= 0 and (i + len(p) == len(low) or not low[i + len(p)].isalnum()):
                if best is None or len(p) > len(best[0]):
                    best = (p, key)
        if best:
            return best[1]
        # 2) a file name that belongs to exactly one mod
        for tok in _FILE_TOKEN.findall(low):
            k = self._one(self.names.get(tok))
            if k:
                return k
        # 3) a mod folder inside a known parent folder
        for parent in _PARENTS:
            for mt in re.finditer(re.escape(parent) + r"([^/\s:'\"]+)", low):
                k = self._one(self.folders.get(mt.group(1)))
                if k:
                    return k
        # 4) 'Name' / "Name" / [Name] equal to a plugin, CET or REDmod folder
        for mt in _QUOTED.finditer(low):
            tok = next(g for g in mt.groups() if g).strip()
            k = self._one(self.labels.get(tok))
            if k:
                return k
        return None


def summarize(index: ModIndex, issues: dict[str, dict], mods_by_key: dict[str, Mod]) -> list[dict]:
    """Mods named in log errors/warnings, most errors first.
    issues: logs.IssueCache().issues() -> {log name: {path, errors[], warnings[]}}"""
    out: dict[str, dict] = {}
    for log_name, data in issues.items():
        for kind in ("errors", "warnings"):
            for line in data.get(kind) or []:
                key = index.match(line)
                if not key or key not in mods_by_key:
                    continue
                c = out.setdefault(key, {"key": key, "name": mods_by_key[key].name, "errors": 0, "warnings": 0,
                                         "logs": [], "lines": [], "log_mtime": 0.0})
                c[kind] += 1
                if log_name not in c["logs"]:
                    c["logs"].append(log_name)
                if kind == "errors" and len(c["lines"]) < 20:
                    c["lines"].append(line)
                try:
                    c["log_mtime"] = max(c["log_mtime"], os.path.getmtime(data["path"]))
                except (OSError, KeyError):
                    pass
    return sorted(out.values(), key=lambda c: (-c["errors"], -c["warnings"], c["name"].lower()))
