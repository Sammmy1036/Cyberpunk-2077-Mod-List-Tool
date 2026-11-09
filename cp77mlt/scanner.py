"""Discover installed mods and group their files into real mods.

v2 counted every top-level file, so one mod shipping ``Foo.archive`` +
``Foo.archive.xl`` + ``r6/scripts/Foo`` counted as three. Here:

1. Every location has rules for what a single "component" is (a folder, or a
   group of loose files sharing a stem such as Foo.archive/Foo.archive.xl/Foo.xl).
2. Files deployed by Vortex are attributed to the Vortex mod that owns them.
3. Remaining loose components with the same normalised name across locations
   (archive + CET + redscript + ...) are merged into one mod.
4. Loose mods that are known to be one mod are merged into a single entry:
   files installed together from one archive by this tool (``groups``) and,
   unless turned off, separate pieces linked to the same Nexus mod page
   (e.g. AMM's CET folder + its archive/pc/mod files).
5. MO2 mods (virtual, not in the game folder) are listed from the MO2 profile.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

TEMP_DISABLED_DIR = "Temporarily Disabled Mods"

# key, relative path, label, grouping rule
#   "dir"   -> each sub-folder is a component, loose files are ignored
#   "stem"  -> sub-folders are components; loose files with allowed extensions are grouped by stem
LOCATIONS = [
    ("archive",   "archive/pc/mod",                              "Archive",       "stem", (".archive", ".xl")),
    ("redmod",    "mods",                                        "REDmod",        "dir",  ()),
    ("cet",       "bin/x64/plugins/cyber_engine_tweaks/mods",    "CET",           "dir",  ()),
    ("redscript", "r6/scripts",                                  "Redscript",     "stem", (".reds",)),
    ("tweak",     "r6/tweaks",                                   "TweakXL",       "stem", (".yaml", ".yml", ".tweak")),
    ("red4ext",   "red4ext/plugins",                             "RED4ext",       "stem", (".dll",)),
    ("input",     "r6/input",                                    "Input Loader",  "stem", (".xml",)),
    ("asi",       "bin/x64/plugins",                             "ASI",           "stem", (".asi",)),
]
LOCATION_BY_KEY = {loc[0]: loc for loc in LOCATIONS}

# Components that belong to core frameworks and are never treated as user mods.
CORE_COMPONENTS = {
    "red4ext/plugins/archivexl": "ArchiveXL",
    "red4ext/plugins/codeware": "Codeware",
    "red4ext/plugins/tweakxl": "TweakXL",
    "r6/scripts/equipmentex": "EquipmentEx",
    "archive/pc/mod/equipmentex": "EquipmentEx",       # stem group EquipmentEx.archive(.xl)
    "bin/x64/plugins/cyber_engine_tweaks": "Cyber Engine Tweaks",  # asi stem group
}

IGNORED_NAMES = {"desktop.ini", "thumbs.db", ".ds_store", "__folder_managed_by_vortex"}
IGNORED_EXT = (".log", ".tmp", ".bak", ".txt", ".md", ".json", ".ini", ".png", ".jpg", ".stub")
HIDDEN_EXT = (".stub",)  # placeholder files (e.g. in mods/) that are never mods and never listed


def stem_of(filename: str) -> str:
    low = filename.lower()
    for ext in (".archive.xl", ".archive", ".xl", ".reds", ".yaml", ".yml", ".tweak", ".dll", ".xml", ".asi"):
        if low.endswith(ext):
            return filename[: -len(ext)]
    return os.path.splitext(filename)[0]


def norm_key(name: str) -> str:
    """Normalised name used to merge components of the same mod across folders."""
    s = stem_of(name).lower()
    s = re.sub(r"^[^a-z0-9]+", "", s)       # load-order prefixes such as '#', '!', '_'
    return re.sub(r"[^a-z0-9]", "", s)


@dataclass
class Component:
    location: str            # LOCATIONS key
    rel_paths: list[str]     # posix paths relative to the tree root (game dir or disabled dir)
    name: str                # display name (folder name or stem)
    is_dir: bool
    disabled: bool
    size: int = 0
    member: str = ""         # key of the loose entry it belonged to before grouping

    @property
    def id(self) -> str:
        return f"{self.location}:{self.name.lower()}"


@dataclass
class Mod:
    key: str
    name: str
    source: str = "loose"              # loose | vortex | mo2
    components: list[Component] = field(default_factory=list)
    enabled: bool = True
    partial: bool = False
    nexus_id: int | None = None
    version: str | None = None
    manager_ref: str | None = None     # vortex staging folder / mo2 mod name
    files: list[str] = field(default_factory=list)  # for MO2 mods (virtual)
    members: list[str] = field(default_factory=list)  # keys of the loose entries merged into this one

    def locations(self) -> list[str]:
        return sorted({c.location for c in self.components})

    def to_dict(self) -> dict:
        return {
            "key": self.key, "name": self.name, "source": self.source,
            "enabled": self.enabled, "partial": self.partial,
            "nexus_id": self.nexus_id, "version": self.version,
            "manager_ref": self.manager_ref,
            "locations": self.locations(),
            "size": sum(c.size for c in self.components),
            "components": [{"location": c.location, "name": c.name, "is_dir": c.is_dir,
                            "disabled": c.disabled, "paths": c.rel_paths, "size": c.size}
                           for c in self.components],
            "files": self.files[:200],
            "members": self.members or [self.key],
            "grouped": len(self.members) > 1,
            "file_count": len(self.files) if self.source == "mo2" else
            sum(len(c.rel_paths) if not c.is_dir else _count_files_hint(c) for c in self.components),
        }


def _count_files_hint(c: Component) -> int:
    return getattr(c, "_file_count", 1)


def _dir_stats(path: str) -> tuple[int, int, list[str]]:
    size, count, sample = 0, 0, []
    for root, _d, files in os.walk(path):
        for fn in files:
            fp = os.path.join(root, fn)
            try:
                size += os.path.getsize(fp)
            except OSError:
                pass
            count += 1
            if len(sample) < 400:
                sample.append(fp)
    return size, count, sample


def scan_components(tree_root: str, disabled: bool) -> list[Component]:
    comps: list[Component] = []
    for key, rel, _label, rule, exts in LOCATIONS:
        base = os.path.join(tree_root, *rel.split("/"))
        try:
            entries = list(os.scandir(base))
        except OSError:
            continue
        stems: dict[str, Component] = {}
        for e in entries:
            low = e.name.lower()
            if low in IGNORED_NAMES or low.startswith("vortex.deployment"):
                continue
            rel_path = f"{rel}/{e.name}"
            if e.is_dir(follow_symlinks=False):
                if key == "asi":  # bin/x64/plugins sub-folders belong to their .asi
                    continue
                if key == "redscript" and low == "cache":
                    continue
                size, count, _ = _dir_stats(e.path)
                c = Component(key, [rel_path], e.name, True, disabled, size)
                c._file_count = count  # type: ignore[attr-defined]
                comps.append(c)
            elif rule == "stem":
                if not low.endswith(exts) or low.endswith(IGNORED_EXT):
                    continue
                stem = stem_of(e.name)
                c = stems.get(stem.lower())
                if c is None:
                    c = stems[stem.lower()] = Component(key, [], stem, False, disabled, 0)
                    comps.append(c)
                c.rel_paths.append(rel_path)
                try:
                    c.size += e.stat().st_size
                except OSError:
                    pass
    return comps


def component_path_key(c: Component) -> str:
    """'r6/scripts/foo', 'archive/pc/mod/coolthing' (same shape as identify.component_paths)."""
    return f"{LOCATION_BY_KEY[c.location][1]}/{c.name}".lower()


def version_key(v: str | None) -> tuple:
    parts = re.findall(r"\d+|[a-zA-Z]+", (v or "").lstrip("vV"))
    t = [(0, int(p)) if p.isdigit() else (-1, p.lower()) for p in parts]
    while t and t[-1] == (0, 0):   # 1.2 == 1.2.0
        t.pop()
    return tuple(t)


_PRIMARY_LOC = {"cet": 0, "redmod": 0, "red4ext": 1, "redscript": 2, "tweak": 3, "input": 3, "asi": 3, "archive": 4}


def _merge_groups(mods: dict[str, "Mod"], groups: list[list[str]] | None, links: dict | None,
                  by_link: bool) -> None:
    """Merge loose mods that belong together (in place). See module docstring, step 4."""
    loose = [m for m in mods.values() if m.source == "loose"]
    parent = {m.key: m.key for m in loose}

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    owner = {}
    for m in loose:
        for c in m.components:
            owner.setdefault(component_path_key(c), m.key)
    for g in groups or []:
        keys = {owner[p.lower()] for p in g if p.lower() in owner}
        first = next(iter(keys), None)
        for k in keys:
            union(first, k)
    via_link = set()
    if by_link:
        by_id: dict[int, str] = {}
        for m in loose:
            if m.nexus_id:
                if m.nexus_id in by_id:
                    union(by_id[m.nexus_id], m.key)
                    via_link.add(m.nexus_id)
                else:
                    by_id[m.nexus_id] = m.key

    clusters: dict[str, list[Mod]] = {}
    for m in loose:
        clusters.setdefault(find(m.key), []).append(m)
    for members in clusters.values():
        if len(members) < 2:
            continue

        def rank(m):
            best = min((_PRIMARY_LOC.get(c.location, 5) - (0.5 if c.is_dir else 0) for c in m.components), default=9)
            return (best, -sum(c.size for c in m.components), m.key)
        members.sort(key=rank)
        primary = members[0]
        for m in members[1:]:
            primary.components.extend(m.components)
            primary.nexus_id = primary.nexus_id or m.nexus_id
            del mods[m.key]
        primary.members = sorted(m.key for m in members)
        versions = [m.version for m in members if m.version]
        if versions:
            primary.version = max(versions, key=version_key)
        if primary.nexus_id in via_link:
            name = next(((links or {}).get(m.key, {}).get("name") for m in members
                         if (links or {}).get(m.key, {}).get("name")), None)
            if name:
                primary.name = str(name)


def component_core_name(c: Component) -> str | None:
    loc_rel = LOCATION_BY_KEY[c.location][1]
    return CORE_COMPONENTS.get(f"{loc_rel}/{c.name}".lower())


def _read_redmod_info(game_dir: str, c: Component) -> dict:
    root = os.path.join(game_dir, TEMP_DISABLED_DIR) if c.disabled else game_dir
    try:
        with open(os.path.join(root, *c.rel_paths[0].split("/"), "info.json"), "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def build_mod_list(game_dir: str, vortex: dict | None = None, mo2_mods: list[dict] | None = None,
                   links: dict | None = None, groups: list[list[str]] | None = None,
                   group_by_link: bool = True) -> list[Mod]:
    """Scan the game folder (+ disabled folder) and return grouped mods.

    ``groups``: lists of component paths (identify.component_paths) that were installed
    together from one archive. ``group_by_link``: merge loose entries linked to the same
    Nexus mod into one."""
    if not game_dir:
        return []
    comps = scan_components(game_dir, disabled=False)
    comps += scan_components(os.path.join(game_dir, TEMP_DISABLED_DIR), disabled=True)
    comps = [c for c in comps if not component_core_name(c)]

    vortex_files = (vortex or {}).get("files", {})
    mods: dict[str, Mod] = {}

    # Index Vortex files by the component path they would belong to:
    # "archive/pc/mod/x.archive" -> itself, "r6/scripts/Foo/a/b.reds" -> "r6/scripts/foo"
    vindex: dict[str, dict[str, int]] = {}
    if vortex_files:
        loc_prefixes = sorted((loc[1].lower() + "/" for loc in LOCATIONS), key=len, reverse=True)
        for f, src in vortex_files.items():
            for pre in loc_prefixes:
                if f.startswith(pre):
                    first = f[len(pre):].split("/", 1)[0]
                    comp_path = pre + first
                    bucket = vindex.setdefault(comp_path, {})
                    bucket[src] = bucket.get(src, 0) + 1
                    break

    # 1) Vortex attribution: a component belongs to the Vortex mod owning most of its files
    remaining: list[Component] = []
    for c in comps:
        owner = None
        if vindex and not c.disabled:
            votes: dict[str, int] = {}
            for rp in c.rel_paths:
                for src, n in vindex.get(rp.lower(), {}).items():
                    votes[src] = votes.get(src, 0) + n
            if votes:
                owner = max(votes, key=votes.get)
        if owner:
            from .managers import parse_vortex_folder_name
            key = "vortex:" + owner.lower()
            m = mods.get(key)
            if m is None:
                info = parse_vortex_folder_name(owner)
                m = mods[key] = Mod(key=key, name=info["name"], source="vortex",
                                    nexus_id=info["mod_id"], version=info["version"], manager_ref=owner)
            m.components.append(c)
        else:
            remaining.append(c)

    # 2) Merge loose components by normalised name across locations
    for c in remaining:
        nk = norm_key(c.name) or c.name.lower()
        key = "loose:" + nk
        m = mods.get(key)
        if m is None:
            m = mods[key] = Mod(key=key, name=c.name)
        m.components.append(c)
        c.member = key
        # Prefer the most descriptive display name: REDmod info > folder name > stem
        if c.location == "redmod":
            info = _read_redmod_info(game_dir, c)
            if info.get("name"):
                m.name = str(info["name"])
            if info.get("version"):
                m.version = str(info["version"])
        elif c.is_dir and m.components[0] is not c and not m.components[0].is_dir:
            m.name = c.name

    # 3) Apply user/identified Nexus links
    def apply_links():
        for key, link in (links or {}).items():
            m = mods.get(key)
            if m and link.get("mod_id"):
                m.nexus_id = m.nexus_id or int(link["mod_id"])
                m.version = m.version or link.get("version")
    apply_links()

    # 4) Merge loose entries known to be one mod
    _merge_groups(mods, groups, links, group_by_link)

    for m in mods.values():
        states = {c.disabled for c in m.components}
        m.enabled = states == {False}
        m.partial = len(states) > 1

    # 5) MO2 mods (virtual)
    for mm in mo2_mods or []:
        key = "mo2:" + mm["name"].lower()
        mods[key] = Mod(key=key, name=mm["name"], source="mo2", enabled=mm["enabled"],
                        nexus_id=mm.get("mod_id"), version=mm.get("version"),
                        manager_ref=mm["name"], files=mm.get("files", []))
    apply_links()

    return sorted(mods.values(), key=lambda m: m.name.lower())


def raw_listing(game_dir: str, include_disabled: bool) -> dict:
    """Per-folder top-level listing (the classic v2 report layout)."""
    out = {}
    for key, rel, label, _rule, _exts in LOCATIONS:
        items = []
        for disabled, root in ((False, game_dir), (True, os.path.join(game_dir, TEMP_DISABLED_DIR))):
            if disabled and not include_disabled:
                continue
            base = os.path.join(root, *rel.split("/"))
            try:
                for e in os.scandir(base):
                    if e.name.lower() in IGNORED_NAMES or e.name.lower().startswith("vortex.deployment"):
                        continue
                    if not e.is_dir() and e.name.lower().endswith(HIDDEN_EXT):
                        continue
                    if key == "redmod" and not e.is_dir():   # REDmods are folders; loose files here aren't mods
                        continue
                    c = Component(key, [f"{rel}/{e.name}"], e.name if e.is_dir() else stem_of(e.name),
                                  e.is_dir(), disabled)
                    if component_core_name(c):
                        continue
                    if key == "asi" and (e.is_dir() or not e.name.lower().endswith(".asi")):
                        continue
                    if key == "cet" and not e.is_dir():
                        continue
                    items.append((e.name, disabled))
            except OSError:
                continue
        out[rel] = sorted(items, key=lambda x: x[0].lower())
    return out


def dir_signature(game_dir: str) -> str:
    """Cheap change detector: mtimes of every watched folder (live + disabled)."""
    parts = []
    for root in (game_dir, os.path.join(game_dir, TEMP_DISABLED_DIR)):
        for _k, rel, *_ in LOCATIONS:
            p = os.path.join(root, *rel.split("/"))
            try:
                parts.append(f"{os.stat(p).st_mtime_ns}")
            except OSError:
                parts.append("-")
    for name in os.listdir(game_dir) if os.path.isdir(game_dir) else []:
        if name.lower().startswith("vortex.deployment"):
            try:
                parts.append(str(os.stat(os.path.join(game_dir, name)).st_mtime_ns))
            except OSError:
                pass
    return "|".join(parts)
