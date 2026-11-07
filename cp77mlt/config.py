"""Persistent settings stored as JSON in %APPDATA%.

v2 stored everything in HKCU\\Software\\Cyberpunk2077ModListTool. On first run we
migrate those values once so existing users keep their game path and options.
"""
from __future__ import annotations

import copy
import json
import os
import sys
import threading

APP_DIR_NAME = "Cyberpunk2077ModListTool"
LEGACY_REGISTRY_KEY = r"Software\Cyberpunk2077ModListTool"

DEFAULTS: dict = {
    "game_dir": "",
    "auto_open_output": False,
    "auto_select_all_logs": True,
    "include_errors_in_output": True,
    "include_disabled_in_output": False,
    "include_grouped_in_output": True,   # the "Installed Mods" (grouped, with Nexus links) section
    "output_dir": "",               # empty = Documents
    "ask_report_path": False,       # ask for a file name/location each time a mod list is generated
    "manual_versions": {},          # {"EquipmentEx": "1.2.6"}
    "manager_mode": "auto",         # auto | none | vortex | mo2
    "mo2_instance": "",             # folder containing ModOrganizer.ini
    "mo2_profile": "",
    "mo2_executable": "",           # MO2 executable title used to launch the game
    "launch_via": "auto",           # auto | exe | store | mo2
    "nexus_api_key": "",            # DPAPI-protected (see secure.py)
    "nexus_links": {},              # mod key -> {mod_id, file_id, version, name}
    "nexus_check_on_start": False,
    "install_records": {},          # mod key -> {mod_id, file_id, version, files[]}
    "nexus_suggestions": {},        # mod key -> {local, options[], score} awaiting user confirmation
    "nexus_rejected": [],           # "modkey|nexus_id" pairs the user said aren't a match
    "download_folders": [],         # extra folders with downloaded mod archives
    "nxm_previous_handler": "",
    "auto_track": True,
    "queue_include_disabled": False,  # list disabled mods in the Nexus link queue
    "backup_dir": "",                 # mod backups folder ("" = Documents\Cyberpunk 2077 Mod Backups)
    "backup_schedule": "off",         # off | daily | weekly | monthly
    "backup_keep": 5,                 # scheduled backups to keep (manual ones are never pruned)
    "last_backup_ts": None,
    "window": None,                   # last position/size/maximized state of the main window
    "github_links": {},             # mod key -> {repo: "owner/name", version?}             # track mods on Nexus when they get linked     # nxm handler before we registered (restored on unregister)
    "migrated_from_registry": False,
}


def app_data_dir() -> str:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    path = os.path.join(base, APP_DIR_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def documents_dir() -> str:
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            # CSIDL_PERSONAL = 5 (My Documents); honours folder redirection/OneDrive
            if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0 and buf.value:
                return buf.value
        except Exception:
            pass
    return os.path.join(os.path.expanduser("~"), "Documents")


class Config:
    def __init__(self, path: str | None = None):
        self.path = path or os.path.join(app_data_dir(), "settings.json")
        self._lock = threading.RLock()
        self.data = copy.deepcopy(DEFAULTS)
        self.load()

    # -- persistence -------------------------------------------------------
    def load(self) -> None:
        with self._lock:
            if os.path.exists(self.path):
                try:
                    with open(self.path, "r", encoding="utf-8") as f:
                        stored = json.load(f)
                    if isinstance(stored, dict):
                        self.data.update(stored)
                except (OSError, ValueError):
                    # Corrupt file: keep a copy for diagnosis and continue with defaults
                    try:
                        os.replace(self.path, self.path + ".corrupt")
                    except OSError:
                        pass
            if not self.data.get("migrated_from_registry"):
                self._migrate_registry()
                self.data["migrated_from_registry"] = True
                self.save()

    def save(self) -> None:
        with self._lock:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, self.path)  # atomic on Windows and POSIX

    def _migrate_registry(self) -> None:
        if sys.platform != "win32":
            return
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, LEGACY_REGISTRY_KEY, 0, winreg.KEY_READ)
        except OSError:
            return

        def get(name, default=None):
            try:
                return winreg.QueryValueEx(key, name)[0]
            except OSError:
                return default

        try:
            gd = get("GameDir")
            if gd and not self.data.get("game_dir"):
                self.data["game_dir"] = gd
            for reg_name, cfg_name in (("AutoOpenOutput", "auto_open_output"),
                                       ("AutoSelectAllLogs", "auto_select_all_logs"),
                                       ("IncludeErrorsInOutput", "include_errors_in_output"),
                                       ("IncludeDisabledInOutput", "include_disabled_in_output")):
                v = get(reg_name)
                if v is not None:
                    self.data[cfg_name] = bool(v)
            for mod in ("EquipmentEx", "Redscript"):
                v = get(f"{mod}_Version")
                if v:
                    self.data["manual_versions"][mod] = v
        finally:
            winreg.CloseKey(key)

    # -- access ------------------------------------------------------------
    def get(self, key, default=None):
        with self._lock:
            return copy.deepcopy(self.data.get(key, DEFAULTS.get(key, default)))

    def set(self, key, value, save: bool = True) -> None:
        with self._lock:
            self.data[key] = value
            if save:
                self.save()

    def update(self, values: dict) -> None:
        with self._lock:
            for k, v in values.items():
                if k in DEFAULTS:
                    self.data[k] = v
            self.save()

    def public(self) -> dict:
        """Settings safe to hand to the UI (never the API key)."""
        with self._lock:
            out = {k: copy.deepcopy(v) for k, v in self.data.items()
                   if k not in ("nexus_api_key", "install_records", "nexus_links", "nexus_suggestions",
                                "nexus_rejected", "nxm_previous_handler", "github_links")}
            out["output_dir_effective"] = self.data.get("output_dir") or documents_dir()
            return out
