"""Game install discovery, version info, process state and launching."""
from __future__ import annotations

import glob
import json
import logging
import os
import re
import subprocess
import sys
import threading
import time

GAME_EXE_REL = os.path.join("bin", "x64", "Cyberpunk2077.exe")
STEAM_APP_ID = "1091500"
GOG_GAME_ID = "1423049311"

IS_WIN = sys.platform == "win32"
log = logging.getLogger("cp77mlt")


def is_valid_game_dir(path: str) -> bool:
    return bool(path) and os.path.isfile(os.path.join(path, GAME_EXE_REL))


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------
def _reg_value(hive_name: str, key: str, value: str):
    if not IS_WIN:
        return None
    try:
        import winreg
        hive = getattr(winreg, hive_name)
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(hive, key, 0, winreg.KEY_READ | view) as k:
                    return winreg.QueryValueEx(k, value)[0]
            except OSError:
                continue
    except Exception:
        pass
    return None


def _steam_library_paths() -> list[str]:
    roots = []
    steam = _reg_value("HKEY_CURRENT_USER", r"Software\Valve\Steam", "SteamPath") or \
        _reg_value("HKEY_LOCAL_MACHINE", r"SOFTWARE\Valve\Steam", "InstallPath")
    if steam:
        roots.append(os.path.normpath(steam))
        vdf = os.path.join(steam, "steamapps", "libraryfolders.vdf")
        try:
            with open(vdf, "r", encoding="utf-8", errors="replace") as f:
                for m in re.finditer(r'"path"\s+"([^"]+)"', f.read()):
                    roots.append(os.path.normpath(m.group(1).replace("\\\\", "\\")))
        except OSError:
            pass
    return list(dict.fromkeys(roots))


def find_game_dirs() -> list[dict]:
    """Return candidate installs: [{path, store}] (deduplicated, valid only)."""
    found: list[dict] = []

    for lib in _steam_library_paths():
        found.append({"path": os.path.join(lib, "steamapps", "common", "Cyberpunk 2077"), "store": "Steam"})

    gog = _reg_value("HKEY_LOCAL_MACHINE", rf"SOFTWARE\GOG.com\Games\{GOG_GAME_ID}", "path")
    if gog:
        found.append({"path": gog, "store": "GOG"})

    if IS_WIN:
        manifests = os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"),
                                 "Epic", "EpicGamesLauncher", "Data", "Manifests", "*.item")
        for item in glob.glob(manifests):
            try:
                with open(item, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "cyberpunk 2077" in str(data.get("DisplayName", "")).lower():
                    found.append({"path": data.get("InstallLocation", ""), "store": "Epic"})
            except (OSError, ValueError):
                continue

    for p in (r"C:\Program Files (x86)\Steam\steamapps\common\Cyberpunk 2077",
              r"C:\Program Files (x86)\GOG Galaxy\Games\Cyberpunk 2077",
              r"C:\GOG Games\Cyberpunk 2077",
              r"C:\Program Files\Epic Games\Cyberpunk2077"):
        found.append({"path": p, "store": None})

    out, seen = [], set()
    for c in found:
        p = os.path.normpath(c["path"]) if c["path"] else ""
        if p and p.lower() not in seen and is_valid_game_dir(p):
            seen.add(p.lower())
            out.append({"path": p, "store": c["store"] or detect_store(p)})
    return out


def detect_store(game_dir: str) -> str:
    if not game_dir:
        return "Unknown"
    low = game_dir.lower()
    if os.path.exists(os.path.join(game_dir, "bin", "x64", "steam_api64.dll")) or "steamapps" in low:
        return "Steam"
    if glob.glob(os.path.join(game_dir, "goggame-*.info")):
        return "GOG"
    if os.path.isdir(os.path.join(game_dir, ".egstore")) or "epic games" in low:
        return "Epic"
    return "Unknown"


# ---------------------------------------------------------------------------
# Info
# ---------------------------------------------------------------------------
def _file_version_ctypes(path: str) -> str | None:
    """VERSIONINFO via version.dll directly (no pywin32 needed)."""
    import ctypes
    from ctypes import wintypes
    ver = ctypes.WinDLL("version", use_last_error=True)
    ver.GetFileVersionInfoSizeW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
    ver.GetFileVersionInfoSizeW.restype = wintypes.DWORD
    ver.GetFileVersionInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
    ver.GetFileVersionInfoW.restype = wintypes.BOOL
    ver.VerQueryValueW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p),
                                   ctypes.POINTER(wintypes.UINT)]
    ver.VerQueryValueW.restype = wintypes.BOOL

    class VS_FIXEDFILEINFO(ctypes.Structure):
        _fields_ = [(n, wintypes.DWORD) for n in (
            "dwSignature", "dwStrucVersion", "dwFileVersionMS", "dwFileVersionLS", "dwProductVersionMS",
            "dwProductVersionLS", "dwFileFlagsMask", "dwFileFlags", "dwFileOS", "dwFileType", "dwFileSubtype",
            "dwFileDateMS", "dwFileDateLS")]

    size = ver.GetFileVersionInfoSizeW(path, None)
    if not size:
        return None
    buf = ctypes.create_string_buffer(size)
    if not ver.GetFileVersionInfoW(path, 0, size, buf):
        return None
    ptr, length = ctypes.c_void_p(), wintypes.UINT()
    if not ver.VerQueryValueW(buf, "\\", ctypes.byref(ptr), ctypes.byref(length)) or not length.value:
        return None
    fi = ctypes.cast(ptr, ctypes.POINTER(VS_FIXEDFILEINFO)).contents
    ms, ls = fi.dwProductVersionMS, fi.dwProductVersionLS
    if not ms and not ls:
        ms, ls = fi.dwFileVersionMS, fi.dwFileVersionLS
    return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"


def file_version(path: str) -> str | None:
    """Windows VERSIONINFO product version, e.g. '2.3.1.0'."""
    if not IS_WIN or not os.path.isfile(path):
        return None
    try:
        return _file_version_ctypes(path)
    except Exception:
        log.exception("Reading version of %s failed", path)
    try:  # last resort: pywin32, if present
        import win32api
        info = win32api.GetFileVersionInfo(path, "\\")
        ms, ls = info.get("ProductVersionMS", 0), info.get("ProductVersionLS", 0)
        return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
    except Exception:
        return None


def game_version(game_dir: str) -> str:
    return file_version(os.path.join(game_dir, GAME_EXE_REL)) or "Unknown"


def phantom_liberty_installed(game_dir: str) -> bool:
    ep1 = os.path.join(game_dir, "archive", "pc", "ep1")
    try:
        if os.path.isdir(ep1) and any(f.lower().endswith(".archive") for f in os.listdir(ep1)):
            return True
    except OSError:
        pass
    return os.path.exists(os.path.join(game_dir, "r6", "cache", "tweakdb_ep1.bin"))


# ---------------------------------------------------------------------------
# Process state (cached; psutil scans are not free)
# ---------------------------------------------------------------------------
def _process_names_windows() -> set[str]:
    """Lower-case exe names of running processes via the Toolhelp snapshot API."""
    import ctypes
    from ctypes import wintypes

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
                    ("szExeFile", ctypes.c_wchar * 260)]

    k32 = ctypes.windll.kernel32
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    k32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    k32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    snap = k32.CreateToolhelp32Snapshot(0x2, 0)  # TH32CS_SNAPPROCESS
    if not snap or snap == wintypes.HANDLE(-1).value:
        raise OSError("CreateToolhelp32Snapshot failed")
    names = set()
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = k32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            names.add(entry.szExeFile.lower())
            ok = k32.Process32NextW(snap, ctypes.byref(entry))
    finally:
        k32.CloseHandle(snap)
    return names


def running_process_names() -> set[str]:
    if IS_WIN:
        try:
            return _process_names_windows()
        except Exception:
            log.exception("Toolhelp process scan failed; falling back to psutil")
    import psutil
    return {(p.info.get("name") or "").lower() for p in psutil.process_iter(["name"])}


class ProcessWatcher:
    NAMES = {"game": "cyberpunk2077.exe", "mo2": "modorganizer.exe", "vortex": "vortex.exe"}

    def __init__(self, ttl: float = 1.5):
        self.ttl = ttl
        self._lock = threading.Lock()
        self._stamp = 0.0
        self._state = {k: False for k in self.NAMES}

    def state(self) -> dict:
        with self._lock:
            if time.monotonic() - self._stamp < self.ttl:
                return dict(self._state)
            try:
                names = running_process_names()
                self._state = {k: v in names for k, v in self.NAMES.items()}
            except Exception:
                log.exception("Process detection failed")
            self._stamp = time.monotonic()
            return dict(self._state)

    def invalidate(self) -> None:
        with self._lock:
            self._stamp = 0.0

    def game_running(self) -> bool:
        return self.state()["game"]


# ---------------------------------------------------------------------------
# Launching
# ---------------------------------------------------------------------------
def _clean_child_env() -> dict:
    """Environment for programs we spawn, stripped of PyInstaller onefile state.

    Without this the game inherits the tool's _MEI temp dir in its DLL search
    path, keeps files in it locked, and closing the tool while the game runs
    shows PyInstaller's "Failed to remove temporary directory" warning.
    """
    env = dict(os.environ)
    meipass = getattr(sys, "_MEIPASS", None)
    for k in ("_MEIPASS2", "_PYI_APPLICATION_HOME_DIR", "_PYI_ARCHIVE_FILE",
              "_PYI_PARENT_PROCESS_LEVEL", "_PYI_SPLASH_IPC", "TCL_LIBRARY", "TK_LIBRARY",
              "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        env.pop(k, None)
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    if meipass:
        mp = os.path.normcase(os.path.normpath(meipass))
        parts = [p for p in env.get("PATH", "").split(os.pathsep)
                 if p and not os.path.normcase(os.path.normpath(p)).startswith(mp)]
        env["PATH"] = os.pathsep.join(parts)
    return env


def spawn_detached(args: list[str], cwd: str | None = None) -> None:
    """Start an external program fully detached from this (possibly frozen) process."""
    kwargs: dict = {"cwd": cwd, "env": _clean_child_env(), "close_fds": True,
                    "stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if IS_WIN:
        kwargs["creationflags"] = (subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        import ctypes
        k32 = ctypes.windll.kernel32
        meipass = getattr(sys, "_MEIPASS", None)
        k32.SetDllDirectoryW(None)  # child must not inherit the _MEI DLL directory
        try:
            subprocess.Popen(args, **kwargs)
        finally:
            if meipass:
                k32.SetDllDirectoryW(meipass)
    else:
        kwargs["start_new_session"] = True
        subprocess.Popen(args, **kwargs)


def open_uri(uri: str) -> None:
    """Open a URL, file or folder with the shell, in a clean environment."""
    if IS_WIN:
        if "://" in uri:
            # explorer.exe mangles URLs with query strings (?tab=files) and can show an
            # "open with" dialog; url.dll's handler opens the default browser/protocol app.
            windir = os.environ.get("SystemRoot", r"C:\Windows")
            spawn_detached([os.path.join(windir, "System32", "rundll32.exe"), "url.dll,FileProtocolHandler", uri])
        else:
            spawn_detached(["explorer.exe", uri])
    elif sys.platform == "darwin":
        spawn_detached(["open", uri])
    else:
        spawn_detached(["xdg-open", uri])


def launch_game(game_dir: str, via: str = "auto", mo2: dict | None = None) -> str:
    """Launch the game. Returns a short description of how it was launched."""
    if via in ("auto", "mo2") and mo2 and mo2.get("exe") and mo2.get("shortcut"):
        spawn_detached([mo2["exe"], mo2["shortcut"]], cwd=os.path.dirname(mo2["exe"]))
        return "Mod Organizer 2"
    store = detect_store(game_dir)
    if via == "store" and store == "Steam":  # opt-in; default is the exe, like v2
        open_uri(f"steam://rungameid/{STEAM_APP_ID}")
        return "Steam"
    exe = os.path.join(game_dir, GAME_EXE_REL)
    if not os.path.isfile(exe):
        raise FileNotFoundError("Cyberpunk2077.exe not found in the selected game folder.")
    spawn_detached([exe], cwd=os.path.dirname(exe))
    return "executable"
