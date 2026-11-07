"""Framework log discovery, reading and error extraction."""
from __future__ import annotations

import glob
import os
import re
import threading

LOG_FILES = {
    "ArchiveXL":           ("red4ext/plugins/ArchiveXL/ArchiveXL.log", "red4ext/plugins/ArchiveXL/ArchiveXL-*.log"),
    "Codeware":            ("red4ext/plugins/Codeware/Codeware.log", "red4ext/plugins/Codeware/Codeware-*.log"),
    "Cyber Engine Tweaks": ("bin/x64/plugins/cyber_engine_tweaks/cyber_engine_tweaks.log", None),
    "Input Loader":        ("red4ext/logs/input_loader.log", "red4ext/logs/input_loader-*.log"),
    "Mod Settings":        ("red4ext/logs/mod_settings.log", "red4ext/logs/mod_settings-*.log"),
    "RED4ext":             ("red4ext/logs/red4ext.log", "red4ext/logs/red4ext-*.log"),
    "Redscript":           ("r6/logs/redscript_rCURRENT.log", "r6/logs/redscript_r*.log"),
    "TweakXL":             ("red4ext/plugins/TweakXL/TweakXL.log", "red4ext/plugins/TweakXL/TweakXL-*.log"),
}

# Tagged severities used by spdlog-based frameworks ([error]) and redscript (ERROR -)
_ERR = re.compile(r"\[(?:error|critical|fatal)\]|^\s*(?:\[[^\]]*\]\s*)*(?:ERROR|CRITICAL|FATAL)\b|"
                  r"\bunhandled exception\b|\bfailed to (?:load|compile|initialize|find|open|resolve)\b", re.I)
_WARN = re.compile(r"\[warn(?:ing)?\]|^\s*(?:\[[^\]]*\]\s*)*WARN(?:ING)?\b", re.I)
_WARN_FALSE = re.compile(r"warningVolume|warningLevel|warningSetting", re.I)


def _p(game_dir: str, rel: str) -> str:
    return os.path.join(game_dir, *rel.split("/"))


def resolve(game_dir: str, name: str) -> str | None:
    """Current log file for a framework (falls back to the newest rotated log)."""
    main, pattern = LOG_FILES[name]
    path = _p(game_dir, main)
    if os.path.isfile(path) and os.path.getsize(path) > 0:
        return path
    if pattern:
        files = glob.glob(_p(game_dir, pattern))
        if files:
            return max(files, key=os.path.getmtime)
    return path if os.path.isfile(path) else None


def available(game_dir: str) -> dict[str, str]:
    out = {}
    for name in LOG_FILES:
        p = resolve(game_dir, name) if game_dir else None
        if p:
            out[name] = p
    return out


def read_text(path: str, limit: int | None = None) -> str:
    with open(path, "rb") as f:
        raw = f.read() if limit is None else f.read(limit)
    for enc in ("utf-8-sig", "utf-16"):
        try:
            if enc == "utf-16" and not raw.startswith((b"\xff\xfe", b"\xfe\xff")):
                continue
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("cp1252", errors="replace")


def classify(line: str) -> str | None:
    if _ERR.search(line):
        return "error"
    if _WARN.search(line) and not _WARN_FALSE.search(line):
        return "warning"
    return None


def extract_issues(path: str) -> dict:
    errors, warnings = [], []
    try:
        for line in read_text(path).splitlines():
            kind = classify(line)
            if kind == "error":
                errors.append(line.strip())
            elif kind == "warning":
                warnings.append(line.strip())
    except OSError as e:
        errors.append(f"Could not read log: {e}")
    return {"errors": errors, "warnings": warnings}


class IssueCache:
    """Re-parses a log only when its mtime/size changes, so polling is cheap."""

    def __init__(self):
        self._lock = threading.Lock()
        self._cache: dict[str, tuple[tuple, dict]] = {}

    def issues(self, game_dir: str) -> dict[str, dict]:
        out = {}
        for name, path in available(game_dir).items():
            try:
                st = os.stat(path)
                sig = (st.st_mtime_ns, st.st_size)
            except OSError:
                continue
            with self._lock:
                hit = self._cache.get(path)
            if not hit or hit[0] != sig:
                hit = (sig, extract_issues(path))
                with self._lock:
                    self._cache[path] = hit
            out[name] = {"path": path, **hit[1]}
        return out
