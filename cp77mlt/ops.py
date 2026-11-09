"""File operations: enable/disable loose mods, presets, and installing archives.

Safety rules (v2 could lose data on several of these paths):
* Never delete a user's file to make room. Anything displaced is moved to
  ``Temporarily Disabled Mods/_Backups (replaced files)/<timestamp>/``.
* Never extract outside the game folder (archive entries are path-checked).
* Never touch files Vortex deployed; MO2 mods are toggled in modlist.txt.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from typing import Callable

from .scanner import TEMP_DISABLED_DIR, Mod

Progress = Callable[[float, str], None]
KNOWN_ROOTS = ("archive", "bin", "r6", "red4ext", "mods", "engine")
PRESET_MANIFEST = "cp77mlt_preset.json"


def _noop(_f: float, _m: str) -> None:
    pass


def _p(root: str, rel: str) -> str:
    return os.path.join(root, *rel.split("/"))


def superseded_dir(game_dir: str) -> str:
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return os.path.join(game_dir, TEMP_DISABLED_DIR, BACKUP_DIR_NAME, stamp)


BACKUP_DIR_NAME = "_Backups (replaced files)"
LEGACY_BACKUP_DIRS = ("_superseded",)


def backup_dirs(game_dir: str) -> list[str]:
    base = os.path.join(game_dir, TEMP_DISABLED_DIR)
    return [os.path.join(base, n) for n in (BACKUP_DIR_NAME,) + LEGACY_BACKUP_DIRS if os.path.isdir(os.path.join(base, n))]


def backups_info(game_dir: str) -> dict:
    size, count, sets = 0, 0, 0
    for d in backup_dirs(game_dir):
        try:
            sets += sum(1 for e in os.scandir(d) if e.is_dir())
        except OSError:
            pass
        for cur, _ds, fns in os.walk(d):
            for fn in fns:
                try:
                    size += os.path.getsize(os.path.join(cur, fn))
                    count += 1
                except OSError:
                    pass
    return {"size": size, "files": count, "sets": sets, "path": os.path.join(game_dir, TEMP_DISABLED_DIR, BACKUP_DIR_NAME)}


def clear_backups(game_dir: str) -> int:
    n = 0
    for d in backup_dirs(game_dir):
        shutil.rmtree(d, ignore_errors=True)
        n += 1
    return n


def prune_backups(game_dir: str, keep: int) -> int:
    """Keep the replaced files of the newest ``keep`` installs/updates, delete older ones.
    keep < 0 keeps everything; 0 keeps nothing. Returns how many sets were deleted."""
    if keep is None or keep < 0:
        return 0
    base = os.path.join(game_dir, TEMP_DISABLED_DIR, BACKUP_DIR_NAME)
    try:
        sets = sorted((e.path for e in os.scandir(base) if e.is_dir()), reverse=True)  # names are timestamps
    except OSError:
        return 0
    old = sets[keep:]
    for d in old:
        shutil.rmtree(d, ignore_errors=True)
    if keep == 0:
        for d in backup_dirs(game_dir):    # legacy _superseded too
            shutil.rmtree(d, ignore_errors=True)
    cleanup_empty_dirs(os.path.join(game_dir, TEMP_DISABLED_DIR))
    return len(old)


def _park(game_dir: str, path: str, rel: str, bucket: str | None = None) -> str:
    """Move an existing file/folder out of the way (never delete)."""
    dest = _p(bucket or superseded_dir(game_dir), rel)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.move(path, dest)
    return dest


# ---------------------------------------------------------------------------
# Enable / disable loose mods
# ---------------------------------------------------------------------------
def set_mods_enabled(game_dir: str, mods: list[Mod], enable: bool, progress: Progress = _noop) -> dict:
    disabled_root = os.path.join(game_dir, TEMP_DISABLED_DIR)
    bucket = superseded_dir(game_dir)
    done, errors, skipped = 0, [], []
    work = [(m, c, rel) for m in mods for c in m.components for rel in c.rel_paths
            if c.disabled == enable]  # only components that need to move
    for i, (m, c, rel) in enumerate(work, 1):
        progress(i / max(len(work), 1), m.name)
        if m.source != "loose":
            skipped.append(f"{m.name}: managed by {m.source.upper()}")
            continue
        src = _p(disabled_root if enable else game_dir, rel)
        dst = _p(game_dir if enable else disabled_root, rel)
        if not os.path.exists(src):
            continue
        try:
            if os.path.exists(dst):
                if enable:
                    # A live copy exists (probably reinstalled since): keep it, leave ours parked
                    errors.append(f"{m.name}: '{rel}' already exists in the game folder; kept the installed copy.")
                    continue
                _park(game_dir, dst, rel, bucket)  # stale parked copy -> superseded
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            done += 1
        except OSError as e:
            errors.append(f"{m.name}: could not move '{rel}': {e}")
    cleanup_empty_dirs(disabled_root)
    return {"moved": done, "errors": errors, "skipped": sorted(set(skipped))}


def cleanup_empty_dirs(root: str) -> None:
    if not os.path.isdir(root):
        return
    for cur, dirs, files in os.walk(root, topdown=False):
        if cur != root and not dirs and not files:
            try:
                os.rmdir(cur)
            except OSError:
                pass
    try:
        if not os.listdir(root):
            os.rmdir(root)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Archive reading (zip / 7z / rar)
# ---------------------------------------------------------------------------
def find_7z() -> str | None:
    exe = shutil.which("7z") or shutil.which("7z.exe")
    if exe:
        return exe
    for p in (r"C:\Program Files\7-Zip\7z.exe", r"C:\Program Files (x86)\7-Zip\7z.exe"):
        if os.path.isfile(p):
            return p
    return None


def find_rar() -> str | None:
    exe = shutil.which("rar") or shutil.which("rar.exe")
    if exe:
        return exe
    for p in (r"C:\Program Files\WinRAR\rar.exe", r"C:\Program Files (x86)\WinRAR\rar.exe"):
        if os.path.isfile(p):
            return p
    return None


def extract_archive(archive: str, dest: str, progress: Progress = _noop) -> None:
    """Extract any supported archive into dest with path-traversal protection."""
    ext = archive.lower()
    os.makedirs(dest, exist_ok=True)
    dest_real = os.path.realpath(dest)

    def safe(name: str) -> str:
        target = os.path.realpath(os.path.join(dest, name))
        if not (target == dest_real or target.startswith(dest_real + os.sep)):
            raise ValueError(f"Unsafe path in archive: {name}")
        return target

    if ext.endswith(".zip") or zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zf:
            members = [m for m in zf.infolist() if not m.is_dir()]
            for i, m in enumerate(members, 1):
                target = safe(m.filename)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with zf.open(m) as s, open(target, "wb") as d:
                    shutil.copyfileobj(s, d, 1024 * 1024)
                ts = _dt.datetime(*m.date_time).timestamp()
                os.utime(target, (ts, ts))
                progress(i / len(members), m.filename)
        return
    if ext.endswith(".7z"):
        try:
            import py7zr
            with py7zr.SevenZipFile(archive, "r") as z:
                for name in z.getnames():
                    safe(name)
                progress(0.1, "Extracting 7z archive")
                z.extractall(dest)
            progress(1.0, "Done")
            return
        except ImportError:
            pass
        except Exception as e:
            if not find_7z():  # e.g. BCJ2/unsupported filters: fall through to 7-Zip if present
                raise RuntimeError(f"Could not extract 7z archive: {e}") from e
    seven = find_7z()
    if not seven:
        raise RuntimeError("Extracting this archive needs 7-Zip (free at 7-zip.org). "
                           "Install it, or re-pack the archive as .zip.")
    listing = subprocess.run([seven, "l", "-slt", "-ba", archive], capture_output=True, text=True,
                             errors="replace", creationflags=_no_window())
    for line in listing.stdout.splitlines():
        if line.startswith("Path = "):
            safe(line[7:])
    progress(0.2, "Extracting with 7-Zip")
    r = subprocess.run([seven, "x", archive, f"-o{dest}", "-y"], capture_output=True, text=True,
                       errors="replace", creationflags=_no_window())
    if r.returncode != 0:
        raise RuntimeError(f"7-Zip failed: {r.stderr.strip() or r.stdout.strip()}")
    progress(1.0, "Done")


def _no_window() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


def _layout_root(extracted: str) -> tuple[str, str | None]:
    """Find the folder that maps onto the game root. Returns (root, loose_kind)."""
    cur = extracted
    for _ in range(3):
        entries = [e for e in os.listdir(cur) if e.lower() not in ("fomod", PRESET_MANIFEST.lower())]
        if any(e.lower() in KNOWN_ROOTS for e in entries):
            return cur, None
        dirs = [e for e in entries if os.path.isdir(os.path.join(cur, e))]
        if len(dirs) == 1 and len(entries) == 1:
            cur = os.path.join(cur, dirs[0])
            continue
        break
    # No recognised layout: loose .archive files go to archive/pc/mod
    files = [e for e in os.listdir(cur) if os.path.isfile(os.path.join(cur, e))]
    if files and all(f.lower().endswith((".archive", ".xl", ".txt", ".md")) for f in files):
        return cur, "archive"
    return cur, "unknown"


def plan_install(extracted: str) -> list[tuple[str, str]]:
    """[(source_abs, dest_rel)] for every file to install."""
    root, loose = _layout_root(extracted)
    plan = []
    if loose == "archive":
        for f in os.listdir(root):
            if f.lower().endswith((".archive", ".xl")):
                plan.append((os.path.join(root, f), f"archive/pc/mod/{f}"))
        return plan
    if loose == "unknown":
        raise ValueError("This archive doesn't use the game-folder layout (archive/, bin/, r6/, red4ext/, mods/). "
                         "It may need a FOMOD installer or manual steps; use Vortex/MO2 or follow the mod's instructions.")
    for cur, _dirs, files in os.walk(root):
        for fn in files:
            src = os.path.join(cur, fn)
            rel = os.path.relpath(src, root).replace("\\", "/")
            if rel.split("/", 1)[0].lower() in KNOWN_ROOTS:
                plan.append((src, rel))
    return plan


def _replaced_components(mod: Mod, new_rels: list[str]) -> list:
    """Which of an installed mod's components an update archive replaces.

    A grouped mod (e.g. a main file plus optional files from the same Nexus page) is
    made of several entries; an update for one file must not remove the others. So only
    the entries that share at least one component with the new archive are replaced."""
    if len(mod.members) < 2:
        return list(mod.components)
    from .identify import component_paths
    from .scanner import component_path_key
    new = component_paths(new_rels)
    hit = {c.member for c in mod.components if component_path_key(c) in new}
    return [c for c in mod.components if c.member in hit]


def install_archive(game_dir: str, archive: str, replace: Mod | None = None,
                    progress: Progress = _noop, overwrite: bool = False) -> dict:
    """Install a mod archive into the game folder.

    If ``replace`` is given (an update), the old mod's files are moved to the
    superseded folder first. Any other file that would be overwritten is
    parked there too, so nothing is ever lost — unless ``overwrite`` is set
    (the user chose it for a preset), in which case clashing files are
    replaced in place.
    """
    tmp = tempfile.mkdtemp(prefix="cp77mlt_")
    bucket = superseded_dir(game_dir)
    try:
        progress(0.05, "Extracting")
        extract_archive(archive, tmp, lambda f, m: progress(0.05 + f * 0.45, m))
        plan = plan_install(tmp)
        if not plan:
            raise ValueError("No installable files found in the archive.")
        if replace and replace.source == "loose":
            for c in _replaced_components(replace, [rel for _src, rel in plan]):
                for rel in c.rel_paths:
                    live = _p(os.path.join(game_dir, TEMP_DISABLED_DIR) if c.disabled else game_dir, rel)
                    if os.path.exists(live):
                        _park(game_dir, live, rel, bucket)
        installed, displaced = [], []
        for i, (src, rel) in enumerate(plan, 1):
            dst = _p(game_dir, rel)
            if os.path.exists(dst):
                if overwrite and os.path.isfile(dst):
                    os.remove(dst)
                else:
                    _park(game_dir, dst, rel, bucket)
                displaced.append(rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            installed.append(rel)
            progress(0.5 + 0.5 * i / len(plan), rel)
        parked = (displaced and not overwrite) or replace
        return {"installed": installed, "displaced": displaced, "overwritten": bool(overwrite and displaced),
                "backup": bucket if parked else None}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------
def export_preset(game_dir: str, mods: list[Mod], save_path: str, progress: Progress = _noop,
                  cancelled: Callable[[], bool] = lambda: False) -> dict:
    files: list[str] = []
    for m in mods:
        if m.source == "mo2":
            continue
        for c in m.components:
            if c.disabled:
                continue
            for rel in c.rel_paths:
                p = _p(game_dir, rel)
                if os.path.isdir(p):
                    for cur, _d, fns in os.walk(p):
                        files += [os.path.relpath(os.path.join(cur, f), game_dir).replace("\\", "/") for f in fns]
                elif os.path.isfile(p):
                    files.append(rel)
    if not files:
        raise ValueError("Nothing to export: the selected mods have no enabled files in the game folder.")
    manifest = {"tool": "Cyberpunk 2077 Mod List Tool", "created": _dt.datetime.now().isoformat(timespec="seconds"),
                "mods": [{"name": m.name, "nexus_id": m.nexus_id, "version": m.version, "source": m.source}
                         for m in mods if m.source != "mo2"]}
    ext = os.path.splitext(save_path)[1].lower()
    tmp_out = save_path + ".partial"
    try:
        if ext == ".7z" and _has_py7zr() and not find_7z():
            import py7zr
            with py7zr.SevenZipFile(tmp_out, "w") as z:
                z.writestr(json.dumps(manifest, indent=2), PRESET_MANIFEST)
                for i, rel in enumerate(files, 1):
                    if cancelled():
                        raise InterruptedError
                    z.write(_p(game_dir, rel), rel)
                    progress(i / len(files), rel)
        elif ext in (".7z", ".rar"):
            _export_with_cli(game_dir, files, manifest, tmp_out, ext, progress)
        else:
            with zipfile.ZipFile(tmp_out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
                z.writestr(PRESET_MANIFEST, json.dumps(manifest, indent=2))
                for i, rel in enumerate(files, 1):
                    if cancelled():
                        raise InterruptedError
                    z.write(_p(game_dir, rel), rel)
                    progress(i / len(files), rel)
        os.replace(tmp_out, save_path)
        return {"files": len(files), "mods": len(manifest["mods"]), "path": save_path}
    except BaseException:
        try:
            os.remove(tmp_out)
        except OSError:
            pass
        raise


def _has_py7zr() -> bool:
    """True only if py7zr really imports (a build can find the package but miss its compiled parts)."""
    try:
        import py7zr  # noqa: F401
        return True
    except Exception:
        return False


def export_formats() -> list[str]:
    """Formats this PC can write: zip always; 7z via py7zr or 7-Zip; rar via WinRAR."""
    out = ["zip"]
    if _has_py7zr() or find_7z():
        out.append("7z")
    if find_rar():
        out.append("rar")
    return out


def _export_with_cli(game_dir: str, files: list[str], manifest: dict, out_path: str, ext: str, progress: Progress) -> None:
    """Pack with 7-Zip's 7z.exe or WinRAR's rar.exe using a UTF-8 list file (relative to the game folder)."""
    tool = find_7z() if ext == ".7z" else find_rar()
    if not tool:
        raise RuntimeError("7-Zip wasn't found. Install 7-Zip (7-zip.org) or choose .zip." if ext == ".7z"
                           else "WinRAR's rar.exe wasn't found. Choose .zip or .7z instead.")
    work = tempfile.mkdtemp(prefix="cp77mlt_pack_")
    try:
        listfile = os.path.join(work, "files.txt")
        with open(listfile, "w", encoding="utf-8", newline="\r\n") as f:
            f.write("\n".join(rel.replace("/", "\\") for rel in files) + "\n")
        man = os.path.join(work, PRESET_MANIFEST)
        with open(man, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        progress(0.2, "Packing with " + ("7-Zip" if ext == ".7z" else "WinRAR"))
        if ext == ".7z":
            cmds = [[tool, "a", "-t7z", "-y", "-scsUTF-8", out_path, f"@{listfile}"],
                    [tool, "a", "-t7z", "-y", out_path, man]]
        else:
            # WinRAR names archives by extension, so pack to a real .rar in the temp folder.
            # The list file is UTF-8 (-scfl); older WinRAR builds that reject that get UTF-16 (-scul).
            rar_out = os.path.join(work, "preset.rar")
            list16 = os.path.join(work, "files16.txt")
            with open(list16, "w", encoding="utf-16", newline="\r\n") as f:
                f.write("\n".join(rel.replace("/", "\\") for rel in files) + "\n")
            cmds = [[tool, "a", "-y", "-idq", "-scfl", rar_out, f"@{listfile}"],
                    [tool, "a", "-y", "-idq", "-ep", rar_out, man]]
        for i, cmd in enumerate(cmds):
            r = subprocess.run(cmd, cwd=game_dir, capture_output=True, text=True, errors="replace",
                               creationflags=_no_window())
            if r.returncode > 1 and ext == ".rar" and i == 0:   # retry once with a UTF-16 list file
                alt = [tool, "a", "-y", "-idq", "-scul", rar_out, f"@{list16}"]
                r = subprocess.run(alt, cwd=game_dir, capture_output=True, text=True, errors="replace",
                                   creationflags=_no_window())
            if r.returncode > 1:   # 0 ok, 1 warnings
                raise RuntimeError(_pack_error(ext, r.returncode, (r.stdout + "\n" + r.stderr)))
            progress(0.6 + 0.4 * i, "Adding preset info")
        if ext == ".rar":
            shutil.move(rar_out, out_path)
        for cand in (out_path, out_path + ext):     # rar/7z may append the extension to ".partial"
            if os.path.exists(cand):
                if cand != out_path:
                    os.replace(cand, out_path)
                break
        else:
            raise RuntimeError("The archive wasn't created.")
        if os.path.getsize(out_path) < 64:
            raise RuntimeError("The archive came out empty.")
    finally:
        shutil.rmtree(work, ignore_errors=True)


_RAR_CODES = {2: "a fatal error", 3: "a damaged file", 5: "a write error (is the disk full?)",
              6: "a file it couldn't open (is the game or another program using it?)",
              7: "an unsupported option (update WinRAR)", 8: "not enough memory", 9: "it couldn't create the archive",
              10: "no files to add", 11: "a wrong password", 255: "it was cancelled"}


def _pack_error(ext: str, code: int, output: str) -> str:
    """Readable packer error. WinRAR's own output starts with a banner that says nothing useful."""
    lines = [ln.strip() for ln in output.splitlines() if ln.strip() and not re.match(
        r"^(RAR|UNRAR|7-Zip)\b.*Copyright|^Trial version|^Type 'rar -\?'|^Evaluation copy", ln.strip(), re.I)]
    tool = "7-Zip" if ext == ".7z" else "WinRAR"
    why = _RAR_CODES.get(code, f"error code {code}") if ext == ".rar" else f"error code {code}"
    detail = (" " + " ".join(lines)[-300:]) if lines else ""
    return f"{tool} stopped with {why}.{detail} Choose .zip to export without it."


def import_preset(game_dir: str, archive: str, progress: Progress = _noop, overwrite: bool = False) -> dict:
    return install_archive(game_dir, archive, None, progress, overwrite)
