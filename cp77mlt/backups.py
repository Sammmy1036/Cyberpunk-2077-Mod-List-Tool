"""Full mod backups: zip snapshots of manually installed mods and core frameworks.

A backup holds every file of every loose (manually installed) mod, enabled or
disabled, plus the core frameworks, stored at their game-relative paths
(disabled files under ``Temporarily Disabled Mods/``). Vortex and MO2 mods are
left out: those managers keep their own copies and redeploy them.

Files the game itself owns (``engine/``) are never backed up or restored, so an
old backup can't roll back game files after a patch.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import shutil
import tempfile
import zipfile
from typing import Callable

from . import core_mods
from .ops import _park, _p, extract_archive, superseded_dir
from .scanner import TEMP_DISABLED_DIR, Mod

Progress = Callable[[float, str], None]
MANIFEST = "cp77mlt_backup.json"
NAME_RE = re.compile(r"^CP2077 Mods (\d{4}-\d{2}-\d{2} \d{2}\.\d{2}\.\d{2})(?: \((manual|scheduled)\))?\.zip$", re.I)
SCHEDULES = {"off": 0, "daily": 86400, "weekly": 7 * 86400, "monthly": 30 * 86400}
STORE_EXT = (".archive", ".zip", ".7z", ".rar", ".png", ".jpg", ".dds", ".bk2", ".wem", ".opus")


def default_dir() -> str:
    from .config import documents_dir
    return os.path.join(documents_dir(), "Cyberpunk 2077 Mod Backups")


def _noop(_f: float, _m: str) -> None:
    pass


def _walk(root: str, rel: str) -> list[str]:
    p = _p(root, rel)
    if os.path.isdir(p):
        out = []
        for cur, _d, fns in os.walk(p):
            out += [os.path.relpath(os.path.join(cur, f), root).replace("\\", "/") for f in fns]
        return out
    return [rel] if os.path.isfile(p) else []


def collect(game_dir: str, mods: list[Mod]) -> list[str]:
    """Game-relative paths to back up (disabled ones prefixed with the disabled folder)."""
    files: set[str] = set()
    dis = TEMP_DISABLED_DIR.replace("\\", "/")
    for m in mods:
        if m.source != "loose":
            continue
        for c in m.components:
            root = os.path.join(game_dir, TEMP_DISABLED_DIR) if c.disabled else game_dir
            for rel in c.rel_paths:
                for f in _walk(root, rel):
                    files.add(f"{dis}/{f}" if c.disabled else f)
    for info in core_mods.CORE.values():
        for rel in info["move"]:
            if rel.startswith("engine/"):
                continue
            files.update(_walk(game_dir, rel))
            files.update(f"{dis}/{f}" for f in _walk(os.path.join(game_dir, TEMP_DISABLED_DIR), rel))
    return sorted(f for f in files if not f.lower().startswith("engine/"))


def create(game_dir: str, mods: list[Mod], folder: str, kind: str = "manual", game_version: str | None = None,
           progress: Progress = _noop, cancelled: Callable[[], bool] = lambda: False) -> dict:
    files = collect(game_dir, mods)
    if not files:
        raise ValueError("There are no manually installed mods or core frameworks to back up.")
    os.makedirs(folder, exist_ok=True)
    now = _dt.datetime.now()
    path = os.path.join(folder, f"CP2077 Mods {now.strftime('%Y-%m-%d %H.%M.%S')} ({kind}).zip")
    manifest = {"tool": "Cyberpunk 2077 Mod List Tool", "created": now.isoformat(timespec="seconds"),
                "kind": kind, "game_version": game_version, "files": len(files),
                "mods": sorted({m.name for m in mods if m.source == "loose"}, key=str.lower)}
    tmp = path + ".partial"
    try:
        with zipfile.ZipFile(tmp, "w") as z:
            z.writestr(MANIFEST, json.dumps(manifest, indent=2))
            for i, rel in enumerate(files, 1):
                if cancelled():
                    raise InterruptedError
                comp = zipfile.ZIP_STORED if rel.lower().endswith(STORE_EXT) else zipfile.ZIP_DEFLATED
                z.write(_p(game_dir, rel), rel, compress_type=comp)
                progress(i / len(files), rel)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
    return {"path": path, "files": len(files), "mods": len(manifest["mods"]), "size": os.path.getsize(path),
            "created": now.timestamp(), "kind": kind}


def _read_manifest(path: str) -> dict:
    try:
        with zipfile.ZipFile(path) as z:
            return json.loads(z.read(MANIFEST).decode("utf-8"))
    except Exception:
        return {}


def list_backups(folder: str) -> list[dict]:
    out = []
    try:
        entries = list(os.scandir(folder))
    except OSError:
        return out
    for e in entries:
        m = NAME_RE.match(e.name)
        if not (m and e.is_file()):
            continue
        try:
            ts = _dt.datetime.strptime(m.group(1), "%Y-%m-%d %H.%M.%S").timestamp()
            size = e.stat().st_size
        except (ValueError, OSError):
            continue
        man = _read_manifest(e.path)
        out.append({"path": e.path, "name": e.name, "created": ts, "size": size,
                    "kind": m.group(2) or man.get("kind") or "manual",
                    "mods": len(man.get("mods") or []), "files": man.get("files"),
                    "game_version": man.get("game_version")})
    out.sort(key=lambda b: b["created"], reverse=True)
    return out


def latest(folder: str) -> dict | None:
    lst = list_backups(folder)
    return lst[0] if lst else None


def prune(folder: str, keep: int) -> list[str]:
    """Delete the oldest *scheduled* backups beyond ``keep``. Manual backups are never pruned."""
    removed = []
    if keep < 1:
        return removed
    sched = [b for b in list_backups(folder) if b["kind"] == "scheduled"]
    for b in sched[keep:]:
        try:
            os.remove(b["path"])
            removed.append(b["path"])
        except OSError:
            pass
    return removed


def is_due(schedule: str, last_ts: float | None, now: float) -> bool:
    every = SCHEDULES.get(schedule or "off", 0)
    return bool(every) and (not last_ts or now - last_ts >= every)


def delete(folder: str, path: str) -> None:
    if os.path.dirname(os.path.abspath(path)) != os.path.abspath(folder) or not NAME_RE.match(os.path.basename(path)):
        raise ValueError("That file isn't a backup made by this tool.")
    os.remove(path)


def restore(game_dir: str, path: str, overwrite: bool = False, progress: Progress = _noop) -> dict:
    """Put every file from a backup back at its path.

    Existing files are moved to the replaced-files backup folder, or deleted when
    ``overwrite`` is set. Mods installed after the backup are left alone.
    """
    tmp = tempfile.mkdtemp(prefix="cp77mlt_restore_")
    bucket = superseded_dir(game_dir)
    try:
        progress(0.02, "Extracting")
        extract_archive(path, tmp, lambda f, m: progress(0.02 + f * 0.48, m))
        files = []
        for cur, _d, fns in os.walk(tmp):
            for fn in fns:
                rel = os.path.relpath(os.path.join(cur, fn), tmp).replace("\\", "/")
                if rel != MANIFEST and not rel.lower().startswith("engine/"):
                    files.append(rel)
        if not files:
            raise ValueError("This backup is empty.")
        restored, replaced = [], []
        for i, rel in enumerate(sorted(files), 1):
            dst = _p(game_dir, rel)
            if os.path.exists(dst):
                if overwrite and os.path.isfile(dst):
                    os.remove(dst)
                else:
                    _park(game_dir, dst, rel, bucket)
                replaced.append(rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(_p(tmp, rel), dst)
            restored.append(rel)
            progress(0.5 + 0.5 * i / len(files), rel)
        return {"restored": len(restored), "replaced": len(replaced), "overwrite": overwrite,
                "backup": bucket if (replaced and not overwrite) else None}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
