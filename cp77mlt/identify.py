"""Work out which Nexus mod each manually installed mod came from.

Nexus's MD5 lookup matches the *downloaded archive*, not the files inside it,
so hashing installed files (v3.0's approach) almost never matches. Instead:

1. Download archives. Nexus names downloads ``<Name>-<modid>-<version>-<timestamp>.<ext>``.
   We scan the user's Downloads plus Vortex/MO2 download folders, list each
   archive's contents and match them against installed files. A match gives
   the mod ID *and* the exact installed version.
2. Name search (needs a Nexus login). Exact name matches are linked; close ones
   become suggestions the user confirms.
"""
from __future__ import annotations

import difflib
import glob
import json
import os
import re
import subprocess
import sys
import threading
import zipfile

from .scanner import LOCATIONS, Mod, norm_key

ARCHIVE_EXT = (".zip", ".7z", ".rar")
NEXUS_FILENAME = re.compile(r"^(?P<name>.+?)-(?P<modid>\d{1,7})-(?P<ver>\d[0-9A-Za-z\-]*?)-(?P<ts>\d{9,11})(?:\(\d+\))?$")
KNOWN_ROOTS = ("archive", "bin", "r6", "red4ext", "mods", "engine")
_LOC_PREFIXES = sorted((loc[1].lower() + "/" for loc in LOCATIONS), key=len, reverse=True)


def parse_nexus_filename(path: str) -> dict | None:
    stem = re.split(r"[\\/]", path)[-1]
    for ext in ARCHIVE_EXT:
        if stem.lower().endswith(ext):
            stem = stem[: -len(ext)]
            break
    m = NEXUS_FILENAME.match(stem.strip())
    if not m:
        return None
    return {"name": m.group("name").replace("_", " ").strip(), "mod_id": int(m.group("modid")),
            "version": m.group("ver").replace("-", "."), "timestamp": int(m.group("ts"))}


def downloads_dir() -> str:
    if sys.platform == "win32":
        try:
            import ctypes
            # FOLDERID_Downloads {374DE290-123F-4565-9164-39C4925E467B}, little-endian GUID layout
            guid = (ctypes.c_ubyte * 16).from_buffer_copy(
                b"\x90\xe2\x4d\x37\x3f\x12\x65\x45\x91\x64\x39\xc4\x92\x5e\x46\x7b")
            shell32, ole32 = ctypes.windll.shell32, ctypes.windll.ole32
            shell32.SHGetKnownFolderPath.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p,
                                                     ctypes.POINTER(ctypes.c_void_p)]
            ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
            ptr = ctypes.c_void_p()
            if shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(ptr)) == 0 and ptr.value:
                value = ctypes.wstring_at(ptr.value)
                ole32.CoTaskMemFree(ptr)
                if value:
                    return value
        except Exception:
            pass
    return os.path.join(os.path.expanduser("~"), "Downloads")


def candidate_folders(extra: list[str] | None = None, mo2_downloads: str | None = None) -> list[str]:
    folders = [downloads_dir()]
    appdata = os.environ.get("APPDATA")
    if appdata:
        folders.append(os.path.join(appdata, "Vortex", "downloads", "cyberpunk2077"))
        try:  # Vortex lets users move the downloads folder; its path is in the global state only, so also
            folders += glob.glob(os.path.join(appdata, "Vortex", "downloads", "*cyberpunk*"))
        except OSError:
            pass
    if mo2_downloads:
        folders.append(mo2_downloads)
    folders += list(extra or [])
    out = []
    for f in folders:
        f = os.path.normpath(f)
        if f and os.path.isdir(f) and f.lower() not in (o.lower() for o in out):
            out.append(f)
    return out


def find_archives(folders: list[str], max_depth: int = 2) -> list[str]:
    found = []
    for base in folders:
        base_depth = base.rstrip(os.sep).count(os.sep)
        for cur, dirs, files in os.walk(base):
            if cur.count(os.sep) - base_depth >= max_depth:
                dirs[:] = []
            for fn in files:
                if fn.lower().endswith(ARCHIVE_EXT):
                    found.append(os.path.join(cur, fn))
    return found


# ---------------------------------------------------------------------------
# Archive listings (cached by path+size+mtime)
# ---------------------------------------------------------------------------
def _list_archive(path: str, seven: str | None) -> list[str]:
    low = path.lower()
    try:
        if low.endswith(".zip"):
            with zipfile.ZipFile(path) as z:
                return [n for n in z.namelist() if not n.endswith("/")]
        if low.endswith(".7z"):
            try:
                import py7zr
                with py7zr.SevenZipFile(path, "r") as z:
                    return [i.filename for i in z.list() if not i.is_directory]
            except ImportError:
                pass
    except Exception:
        if not seven:
            return []
    if seven:
        kw = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if sys.platform == "win32" else {}
        try:
            r = subprocess.run([seven, "l", "-slt", "-ba", path], capture_output=True, text=True,
                               errors="replace", timeout=60, **kw)
        except (OSError, subprocess.TimeoutExpired):
            return []
        names, cur, is_dir = [], None, False
        for line in r.stdout.splitlines() + [""]:
            if line.startswith("Path = "):
                cur = line[7:]
            elif line.startswith("Attributes = ") and "D" in line[13:].split(" ")[0]:
                is_dir = True
            elif not line.strip() and cur is not None:
                if not is_dir:
                    names.append(cur)
                cur, is_dir = None, False
        return names
    return []


def component_paths(entries: list[str]) -> set[str]:
    """Map archive entries onto game-relative *component* paths, e.g.
    'MyMod/r6/scripts/Foo/a.reds' -> 'r6/scripts/foo';  'x/archive/pc/mod/a.archive' -> 'archive/pc/mod/a'."""
    out = set()
    for raw in entries:
        parts = raw.replace("\\", "/").strip("/").split("/")
        low = [p.lower() for p in parts]
        start = next((i for i, p in enumerate(low[:4]) if p in KNOWN_ROOTS), None)
        if start is None:
            if len(parts) == 1 and low[0].endswith((".archive", ".xl")):  # bare archive mod
                low = ["archive", "pc", "mod", low[0]]
                start = 0
            else:
                continue
        rel = "/".join(low[start:])
        for pre in _LOC_PREFIXES:
            if rel.startswith(pre):
                first = rel[len(pre):].split("/", 1)
                name = first[0]
                if len(first) == 1:  # loose file: group by stem like the scanner does
                    from .scanner import stem_of
                    name = stem_of(name).lower()
                out.add(pre + name)
                break
    return out


class ArchiveIndex:
    def __init__(self, cache_path: str):
        self.cache_path = cache_path
        self._lock = threading.Lock()
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                self._cache = json.load(f)
        except (OSError, ValueError):
            self._cache = {}

    def save(self) -> None:
        with self._lock:
            tmp = self.cache_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._cache, f)
            os.replace(tmp, self.cache_path)

    def entries(self, path: str, seven: str | None) -> dict:
        try:
            st = os.stat(path)
        except OSError:
            return {"components": [], "size": 0}
        sig = f"{st.st_size}|{st.st_mtime_ns}"
        with self._lock:
            hit = self._cache.get(path)
        if hit and hit.get("sig") == sig:
            return hit
        comps = sorted(component_paths(_list_archive(path, seven)))
        rec = {"sig": sig, "components": comps, "size": st.st_size, "mtime": st.st_mtime}
        with self._lock:
            self._cache[path] = rec
        return rec


def mod_component_keys(m: Mod) -> set[str]:
    keys = set()
    for c in m.components:
        loc_rel = next(loc[1] for loc in LOCATIONS if loc[0] == c.location).lower()
        keys.add(f"{loc_rel}/{c.name.lower()}")
    return keys


def match_downloads(mods: list[Mod], archives: list[dict]) -> dict[str, dict]:
    """archives: [{path, components:set, info: parse_nexus_filename()|None}] -> {mod.key: match}"""
    by_comp: dict[str, list[int]] = {}
    for i, a in enumerate(archives):
        for cp in a["components"]:
            by_comp.setdefault(cp, []).append(i)
    out = {}
    for m in mods:
        keys = mod_component_keys(m)
        if not keys:
            continue
        hits: dict[int, int] = {}
        for k in keys:
            for i in by_comp.get(k, ()):
                hits[i] = hits.get(i, 0) + 1
        best = None
        for i, n in hits.items():
            a = archives[i]
            coverage = n / len(keys)                       # how much of the installed mod the archive explains
            precision = n / max(len(a["components"]), 1)   # how much of the archive is this mod
            if coverage < 0.6 or precision < 0.3:
                continue
            score = (coverage + precision, (a["info"] or {}).get("timestamp", 0))
            if best is None or score > best[0]:
                best = (score, a)
        if best:
            a = best[1]
            out[m.key] = {"archive": a["path"], "info": a["info"], "coverage": best[0][0]}
    return out


# ---------------------------------------------------------------------------
# Name matching
# ---------------------------------------------------------------------------
def search_terms(name: str) -> list[str]:
    s = re.sub(r"^[^A-Za-z0-9]+", "", name)
    s = re.sub(r"^(?:zz+|z_)", "", s, flags=re.I)
    s = re.sub(r"[_\-.]+", " ", s)
    s = re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", s)   # CamelCase -> words
    s = re.sub(r"\b[vV]?\d+(?:\s\d+)*\s*$", "", s).strip()                 # trailing version
    words = s.split()
    terms = [" ".join(words)] if words else []
    if len(words) > 3:
        terms.append(" ".join(words[:3]))
    return [t for t in dict.fromkeys(terms) if len(t) >= 3]


def name_score(local: str, remote: str) -> float:
    a, b = norm_key(local), norm_key(remote)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    if a in b or b in a:
        ratio = max(ratio, 0.8 * min(len(a), len(b)) / max(len(a), len(b)) + 0.15)
    return ratio


def best_name_match(local: str, nodes: list[dict]) -> tuple[dict | None, float]:
    best, score = None, 0.0
    for n in nodes:
        s = name_score(local, n.get("name", ""))
        if s > score:
            best, score = n, s
    return best, score


def newest_mtime(game_dir: str, m: Mod, disabled_root: str) -> float:
    newest = 0.0
    for c in m.components:
        root = disabled_root if c.disabled else game_dir
        for rel in c.rel_paths:
            p = os.path.join(root, *rel.split("/"))
            if os.path.isdir(p):
                for cur, _d, fns in os.walk(p):
                    for fn in fns:
                        try:
                            newest = max(newest, os.path.getmtime(os.path.join(cur, fn)))
                        except OSError:
                            pass
            else:
                try:
                    newest = max(newest, os.path.getmtime(p))
                except OSError:
                    pass
    return newest


# ---------------------------------------------------------------------------
# Catalog matching + content verification
# ---------------------------------------------------------------------------
_STOP = {"the", "a", "an", "of", "and", "for", "mod", "mods", "by", "to", "in", "on", "with", "v", "cp", "cp77",
         "cp2077", "cyberpunk", "2077", "edition", "version", "fix", "patch", "addon", "add", "archive", "xl"}


def words(name: str) -> list[str]:
    s = re.sub(r"^[^A-Za-z0-9]+", "", name or "")
    s = re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])", " ", s)
    return [w for w in re.split(r"[^A-Za-z0-9]+", s.lower()) if w]


def tokens(name: str) -> set[str]:
    return {w for w in words(name) if w not in _STOP and len(w) > 1 and not w.isdigit()}


def numbers(name: str) -> set[str]:
    return {w.lstrip("0") or "0" for w in words(name) if w.isdigit() and w not in ("2077",)}


def numbers_conflict(local: str, remote: str) -> bool:
    """'H8 Megabuilding' vs 'H10 Megabuilding': different numbers mean different mods."""
    a, b = numbers(local), numbers(remote)
    return bool(a) and bool(b) and a != b


def similarity(local: str, remote: str) -> float:
    if numbers_conflict(local, remote):
        return 0.3 * _similarity(local, remote)
    return _similarity(local, remote)


def _similarity(local: str, remote: str) -> float:
    a, b = norm_key(local), norm_key(remote)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    seq = difflib.SequenceMatcher(None, a, b).ratio()
    ta, tb = tokens(local), tokens(remote)
    jac = len(ta & tb) / len(ta | tb) if ta and tb else 0.0
    cover = len(ta & tb) / len(ta) if ta else 0.0     # how much of the local name the remote name explains
    contain = 0.0
    if len(a) >= 5 and (a in b or b in a):
        contain = 0.6 + 0.35 * min(len(a), len(b)) / max(len(a), len(b))
    return max(0.55 * seq + 0.25 * jac + 0.2 * cover, contain)


def local_names(m: Mod, game_dir: str | None = None) -> list[str]:
    names = [m.name] + [c.name for c in m.components]
    return list(dict.fromkeys(n for n in names if n))


def _grams(name: str, n: int = 4) -> set[str]:
    k = norm_key(name)
    return {k[i:i + n] for i in range(max(len(k) - n + 1, 1))} if k else set()


class Catalog:
    """In-memory index of every Nexus mod name for fast fuzzy candidate lookup.
    Character 4-grams find 'clearwindows' -> 'Clear Car Windows' where word tokens can't."""

    def __init__(self, mods: list[dict]):
        uniq: dict[int, dict] = {}
        for md in mods:                      # catalog pages can repeat mods
            uniq.setdefault(md["mod_id"], md)
        self.mods = list(uniq.values())
        mods = self.mods
        self.grams: dict[str, list[int]] = {}
        for i, md in enumerate(mods):
            for g in _grams(md["name"]):
                self.grams.setdefault(g, []).append(i)

    def candidates(self, names: list[str], top: int = 4, floor: float = 0.45) -> list[tuple[dict, float]]:
        hits: dict[int, int] = {}
        for n in names:
            for g in _grams(n):
                post = self.grams.get(g, ())
                if len(post) > 2500:          # near-universal fragments carry no signal
                    continue
                for i in post:
                    hits[i] = hits.get(i, 0) + 1
        pool = sorted(hits, key=lambda i: -hits[i])[:300]
        scored = []
        for i in pool:
            md = self.mods[i]
            sc = max(similarity(n, md["name"]) for n in names)
            if sc >= floor:
                scored.append((md, sc))
        scored.sort(key=lambda x: -x[1])
        return scored[:top]

    def search(self, term: str, top: int = 15) -> list[dict]:
        if term.strip().isdigit():
            mid = int(term)
            return [m for m in self.mods if m["mod_id"] == mid][:1]
        return [md for md, _ in self.candidates([term], top=top, floor=0.3)]

    def add(self, mods: list[dict]) -> None:
        """Merge mods found by live search (newer than the cached list, or missed by paging)."""
        have = {m["mod_id"] for m in self.mods}
        for md in mods:
            if md.get("mod_id") and md["mod_id"] not in have:
                have.add(md["mod_id"])
                i = len(self.mods)
                self.mods.append(md)
                for g in _grams(md["name"]):
                    self.grams.setdefault(g, []).append(i)


def merge_ranked(term: str, *lists: list[dict], top: int = 20) -> list[dict]:
    """Combine result lists, drop duplicate IDs, rank by name similarity to the term."""
    seen: dict[int, dict] = {}
    for lst in lists:
        for md in lst:
            if md.get("mod_id") and md["mod_id"] not in seen:
                seen[md["mod_id"]] = md
    ranked = sorted(seen.values(), key=lambda m: -similarity(term, m.get("name") or ""))
    return ranked[:top]


def installed_files(m: Mod, game_dir: str, disabled_root: str) -> dict[str, int]:
    """{game-relative lower path: size} for a loose mod's files."""
    out = {}
    for c in m.components:
        root = disabled_root if c.disabled else game_dir
        for rel in c.rel_paths:
            p = os.path.join(root, *rel.split("/"))
            if os.path.isdir(p):
                for cur, _d, fns in os.walk(p):
                    for fn in fns:
                        fp = os.path.join(cur, fn)
                        try:
                            out[os.path.relpath(fp, root).replace("\\", "/").lower()] = os.path.getsize(fp)
                        except OSError:
                            pass
            elif os.path.isfile(p):
                out[rel.lower()] = os.path.getsize(p)
    return out


def verify_against_preview(m: Mod, preview: list[tuple[str, int | None]], installed: dict[str, int]) -> dict:
    """Compare an uploaded file's content list with what's installed.
    coverage: share of the mod's components found in the upload; size_hits: files whose sizes match."""
    comps = component_paths([p for p, _ in preview])
    keys = mod_component_keys(m)
    if not keys or not comps:
        return {"coverage": 0.0, "precision": 0.0, "size_hits": 0, "size_total": 0}
    inter = keys & comps
    # file-level size comparison (sizes in previews are rounded, so allow 2%)
    by_name: dict[str, int] = {}
    for p, size in preview:
        if size:
            by_name[p.replace("\\", "/").lower().rsplit("/", 1)[-1]] = size
    hits = total = 0
    for path, size in installed.items():
        name = path.rsplit("/", 1)[-1]
        if name in by_name:
            total += 1
            ref = by_name[name]
            if abs(ref - size) <= max(1100, ref * 0.02):
                hits += 1
    return {"coverage": len(inter) / len(keys), "precision": len(inter) / len(comps),
            "size_hits": hits, "size_total": total}


# ---------------------------------------------------------------------------
# Nexus URLs written inside the mod's own files
# ---------------------------------------------------------------------------
TEXT_EXT = (".xl", ".yaml", ".yml", ".reds", ".lua", ".json", ".txt", ".md", ".ini", ".toml", ".xml", ".tweak", ".cfg")
_URL_RE = re.compile(rb"nexusmods\.com/(?:games/)?cyberpunk2077/mods/(\d{1,7})", re.I)


def urls_in_mod(m: Mod, game_dir: str, disabled_root: str, max_files: int = 400,
                repos: dict | None = None) -> dict[int, int]:
    """Count Nexus mod IDs referenced in a mod's text files ({mod_id: occurrences})."""
    found: dict[int, int] = {}
    seen = 0

    def scan(fp: str):
        nonlocal seen
        if seen >= max_files or not fp.lower().endswith(TEXT_EXT):
            return
        seen += 1
        try:
            if os.path.getsize(fp) > 2 * 1024 * 1024:
                return
            with open(fp, "rb") as f:
                data = f.read()
        except OSError:
            return
        if b"\x00" in data[:4096] and data[:2] in (b"\xff\xfe", b"\xfe\xff"):
            data = data.decode("utf-16", errors="ignore").encode("utf-8", errors="ignore")
        for mt in _URL_RE.finditer(data):
            mid = int(mt.group(1))
            found[mid] = found.get(mid, 0) + 1
        if repos is not None:
            from .github import repos_in_bytes
            for r in repos_in_bytes(data):
                repos[r] = repos.get(r, 0) + 1

    for c in m.components:
        root = disabled_root if c.disabled else game_dir
        for rel in c.rel_paths:
            p = os.path.join(root, *rel.split("/"))
            if os.path.isdir(p):
                for cur, _d, fns in os.walk(p):
                    for fn in fns:
                        scan(os.path.join(cur, fn))
            else:
                scan(p)
    return found


def pick_own_id(found: dict[int, int], exclude: set[int], names: list[str], catalog: "Catalog | None") -> tuple[int | None, list[int]]:
    """From IDs found in a mod's files, pick the mod's own page.
    Returns (chosen_id or None, remaining_candidates)."""
    ids = [i for i in found if i not in exclude]
    if not ids:
        return None, []
    by_id = {m["mod_id"]: m["name"] for m in catalog.mods} if catalog is not None else {}
    # a link whose page name has a different number (H10 vs our H8) is a sibling mod, not this one
    if by_id:
        ids = [i for i in ids if not any(numbers_conflict(n, by_id.get(i, "")) for n in names[:1])]
        if not ids:
            return None, [i for i in found if i not in exclude]
    if len(ids) == 1:
        if by_id and by_id.get(ids[0]) and max(similarity(n, by_id[ids[0]]) for n in names) < 0.25:
            return None, ids   # the only link points somewhere unrelated (e.g. a credit): ask
        return ids[0], ids
    if catalog is not None:
        scored = sorted(((max(similarity(n, by_id.get(i, "")) for n in names), i) for i in ids), reverse=True)
        if scored[0][0] >= 0.6 and (len(scored) == 1 or scored[0][0] - scored[1][0] >= 0.15):
            return scored[0][1], [i for _, i in scored]
        return None, [i for _, i in scored]
    ranked = sorted(ids, key=lambda i: -found[i])
    if found[ranked[0]] >= 2 * found[ranked[1]]:
        return ranked[0], ranked
    return None, ranked
