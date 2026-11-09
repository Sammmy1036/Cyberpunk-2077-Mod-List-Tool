"""The Python API exposed to the web UI through pywebview (window.pywebview.api).

Every public method returns JSON-serialisable data. Slow work runs as a
background *task*; progress is pushed to the UI via window.cp.onTask(...).
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tempfile
import threading
import time
import uuid

from . import APP_NAME, APP_VERSION, NEXUS_PAGE, backups, core_mods, game, github, identify, logs, managers, nexus, nxm, ops, report, secure
from .config import Config, app_data_dir, documents_dir
from .scanner import TEMP_DISABLED_DIR, Mod, build_mod_list, dir_signature
from .scanner import component_path_key as scanner_key


log = logging.getLogger("cp77mlt")


def _err(msg: str) -> dict:
    return {"ok": False, "error": msg}


class Api:
    def __init__(self, config: Config | None = None):
        self._cfg = config or Config()
        self._window = None
        self._proc = game.ProcessWatcher()
        self._issue_cache = logs.IssueCache()
        self._mods: list[Mod] = []
        self._mods_by_key: dict[str, Mod] = {}
        self._sig = None
        self._scan_lock = threading.Lock()
        self._tasks: dict[str, dict] = {}
        self._nexus: nexus.NexusClient | None = None
        self._nexus_user: dict | None = None
        self._md5_cache: dict = {}
        self._updates_path = os.path.join(app_data_dir(), "updates.json")
        self._updates: dict[str, dict] = {}
        self._updates_checked: float | None = None
        self._load_updates()
        self._mo2: managers.MO2Instance | None = None
        self._launch_started: float | None = None
        self._launch_mark: float | None = None   # wall-clock time the game was last started (for "new errors")
        self._game_seen = False
        self._nxm_pending: list[str] = []
        self._nxm_errors: list[str] = []
        self._catalog_obj = None
        self._gh = github.GitHubClient(os.path.join(app_data_dir(), "github_cache.json"))
        self._tracked: set[int] | None = None
        self._init_mo2()

    # ------------------------------------------------------------------ utils
    def rpc(self, name: str, args: list | None = None):
        """Single dispatcher the UI falls back to if pywebview hasn't exposed a method yet."""
        if not isinstance(name, str) or name.startswith("_") or name in ("rpc", "attach"):
            return _err("Unknown action.")
        fn = getattr(self, name, None)
        if not callable(fn):
            return _err(f"Unknown action: {name}")
        return fn(*(args or []))

    def attach(self, window) -> None:
        self._window = window

    def _push(self, fn: str, payload: dict) -> None:
        """Best-effort push to the UI. Never blocks the caller: evaluate_js waits on the
        GUI thread, and calling it from inside a JS->Python call can stall the bridge.
        The UI also polls get_task(), so a lost push only delays an update."""
        if not self._window:
            return
        script = f"window.cp && window.cp.{fn}({json.dumps(payload)})"

        def send():
            try:
                self._window.evaluate_js(script)
            except Exception:
                pass
        threading.Thread(target=send, daemon=True).start()

    def _task(self, name: str, fn) -> dict:
        tid = uuid.uuid4().hex[:10]
        state = {"id": tid, "name": name, "progress": 0.0, "message": "", "done": False,
                 "result": None, "error": None, "cancel": False}
        self._tasks[tid] = state

        def progress(frac: float, msg: str = "") -> None:
            state["progress"], state["message"] = max(0.0, min(1.0, frac)), msg
            now = time.monotonic()
            if now - state.get("_last", 0) > 0.08 or frac >= 1:
                state["_last"] = now
                self._push("onTask", self._task_view(state))

        def run():
            try:
                state["result"] = fn(progress, lambda: state["cancel"])
            except InterruptedError:
                state["error"] = "Cancelled."
            except Exception as e:  # surfaced to the UI
                state["error"] = str(e) or e.__class__.__name__
                log.exception("Task %s failed", name)
            finally:
                state["done"], state["progress"] = True, 1.0
                self._push("onTask", self._task_view(state))

        threading.Thread(target=run, daemon=True, name=f"task-{name}").start()
        return {"ok": True, "task": tid, "name": name}

    @staticmethod
    def _task_view(s: dict) -> dict:
        return {k: s[k] for k in ("id", "name", "progress", "message", "done", "result", "error")}

    def get_task(self, tid: str) -> dict:
        s = self._tasks.get(tid)
        return self._task_view(s) if s else _err("Unknown task")

    def cancel_task(self, tid: str) -> dict:
        if tid in self._tasks:
            self._tasks[tid]["cancel"] = True
        return {"ok": True}

    @property
    def game_dir(self) -> str:  # not callable from JS (properties are skipped)
        return self._cfg.get("game_dir") or ""

    def _need_game(self):
        if not game.is_valid_game_dir(self.game_dir):
            raise RuntimeError("Set your Cyberpunk 2077 folder in Settings first.")

    def _guard_game_closed(self):
        self._proc.invalidate()
        if self._proc.game_running():
            raise RuntimeError("Close Cyberpunk 2077 first. Mod files can't be changed while the game is running.")

    # ------------------------------------------------------------- bootstrap
    def bootstrap(self) -> dict:
        gd = self.game_dir
        if not game.is_valid_game_dir(gd):
            # first run / moved install: try auto-detection
            found = game.find_game_dirs()
            if len(found) == 1:
                self._cfg.set("game_dir", found[0]["path"])
                gd = found[0]["path"]
        self._restore_nexus()
        return {
            "app": {"name": APP_NAME, "version": APP_VERSION, "nexus_page": NEXUS_PAGE},
            "settings": self._cfg.public(),
            "game": self.game_info(),
            "managers": self.manager_info(),
            "nexus": {"user": self._nexus_user, "sso": bool(nexus.NEXUS_APP_SLUG),
                      "api_key_page": nexus.API_KEY_PAGE},
        }

    def game_info(self) -> dict:
        gd = self.game_dir
        valid = game.is_valid_game_dir(gd)
        return {"dir": gd, "valid": valid,
                "version": game.game_version(gd) if valid else None,
                "store": game.detect_store(gd) if valid else None,
                "phantom_liberty": game.phantom_liberty_installed(gd) if valid else False}

    def game_icon(self) -> dict:
        """The game's own icon (extracted from Cyberpunk2077.exe) as a data URI for the launch button."""
        from . import icons
        gd = self.game_dir
        cache = os.path.join(app_data_dir(), "game_icon.png")
        uri = icons.game_icon_data_uri(os.path.join(gd, game.GAME_EXE_REL) if gd else "", cache)
        return {"ok": bool(uri), "uri": uri}

    def detect_game_dirs(self) -> list:
        return game.find_game_dirs()

    def set_game_dir(self, path: str) -> dict:
        path = os.path.normpath(path or "")
        if not game.is_valid_game_dir(path):
            # accept bin/x64 or the exe's folder by walking up
            probe = path
            for _ in range(3):
                probe = os.path.dirname(probe)
                if game.is_valid_game_dir(probe):
                    path = probe
                    break
            else:
                return _err("That folder doesn't contain bin\\x64\\Cyberpunk2077.exe.")
        self._cfg.set("game_dir", path)
        self._sig = None
        self._init_mo2()
        return {"ok": True, "game": self.game_info()}

    def browse_game_dir(self) -> dict:
        res = self._dialog("folder", title="Select your Cyberpunk 2077 folder")
        return self.set_game_dir(res) if res else {"ok": False}

    # ------------------------------------------------------------- settings
    def save_settings(self, values: dict) -> dict:
        allowed = {"auto_open_output", "auto_select_all_logs", "include_errors_in_output",
                   "include_disabled_in_output", "manager_mode", "launch_via", "mo2_profile",
                   "mo2_executable", "nexus_check_on_start", "output_dir", "auto_track", "include_grouped_in_output", "ask_report_path", "queue_include_disabled",
                   "backup_schedule", "backup_keep", "group_mod_files", "mods_view"}
        self._cfg.update({k: v for k, v in values.items() if k in allowed})
        if "group_mod_files" in values:
            self._sig = None
        if {"manager_mode", "mo2_profile"} & set(values):
            self._init_mo2()
            self._sig = None
        return {"ok": True, "settings": self._cfg.public()}

    def browse_output_dir(self) -> dict:
        res = self._dialog("folder", title="Where should the mod list be saved?")
        if res:
            self._cfg.set("output_dir", res)
        return {"ok": bool(res), "settings": self._cfg.public()}

    def set_manual_version(self, name: str, version: str) -> dict:
        mv = self._cfg.get("manual_versions") or {}
        if version.strip():
            mv[name] = version.strip()
        else:
            mv.pop(name, None)
        self._cfg.set("manual_versions", mv)
        return {"ok": True}

    # ------------------------------------------------------------- managers
    def _init_mo2(self) -> None:
        self._mo2 = None
        mode = self._cfg.get("manager_mode")
        if mode in ("none", "vortex"):
            return
        inst = self._cfg.get("mo2_instance")
        candidates = [inst] if inst else managers.find_mo2_instances()
        for c in candidates:
            try:
                mo2 = managers.MO2Instance(c, self._cfg.get("mo2_profile") or None)
            except (OSError, FileNotFoundError):
                continue
            # only pair with an instance pointing at our game folder (if we know it)
            if self.game_dir and mo2.game_path and \
                    os.path.normcase(mo2.game_path) != os.path.normcase(self.game_dir) and not inst:
                continue
            self._mo2 = mo2
            break

    def manager_info(self) -> dict:
        gd = self.game_dir
        vortex = managers.read_vortex_manifests(gd) if gd and self._cfg.get("manager_mode") in ("auto", "vortex") else {"files": {}, "manifests": []}
        return {
            "mode": self._cfg.get("manager_mode"),
            "vortex": {"detected": bool(vortex["manifests"]), "installed": managers.vortex_installed(),
                       "files": len(vortex["files"]), "manifests": vortex["manifests"]},
            "mo2": self._mo2.summary() if self._mo2 else None,
            "mo2_candidates": managers.find_mo2_instances(),
            "running": self._proc.state(),
        }

    def browse_mo2_instance(self) -> dict:
        res = self._dialog("folder", title="Select your MO2 instance folder (contains ModOrganizer.ini)")
        if not res:
            return {"ok": False}
        try:
            managers.MO2Instance(res)
        except FileNotFoundError:
            return _err("No ModOrganizer.ini found in that folder.")
        self._cfg.update({"mo2_instance": res, "mo2_profile": ""})
        if self._cfg.get("manager_mode") == "none":
            self._cfg.set("manager_mode", "auto")
        self._init_mo2()
        self._sig = None
        return {"ok": True, "managers": self.manager_info()}

    def clear_mo2_instance(self) -> dict:
        self._cfg.update({"mo2_instance": "", "mo2_profile": ""})
        self._init_mo2()
        self._sig = None
        return {"ok": True, "managers": self.manager_info()}

    # ------------------------------------------------------------- mods
    def _rescan(self) -> None:
        gd = self.game_dir
        mode = self._cfg.get("manager_mode")
        vortex = managers.read_vortex_manifests(gd) if mode in ("auto", "vortex") else None
        mo2_mods = []
        if self._mo2 and mode in ("auto", "mo2"):
            try:
                mo2_mods = self._mo2.mods()
            except OSError:
                mo2_mods = []
        mods = build_mod_list(gd, vortex, mo2_mods, self._cfg.get("nexus_links"),
                              groups=self._cfg.get("install_groups"),
                              group_by_link=bool(self._cfg.get("group_mod_files")))
        for m in mods:  # native plugins carry their own version (RedHotTools, Input Loader, ...)
            if m.source == "loose" and not m.version:
                for c in m.components:
                    if c.location == "red4ext" and not c.disabled:
                        base = os.path.join(gd, *c.rel_paths[0].split("/"))
                        dll = os.path.join(base, c.name + ".dll") if c.is_dir else base
                        v = game.file_version(dll) if os.path.isfile(dll) else None
                        if v and v != "0.0.0.0":
                            m.version = re.sub(r"(\.0)+$", "", v) if v.count(".") > 2 else v
                            break
        self._mods = mods
        self._mods_by_key = {m.key: m for m in mods}
        self._sig = dir_signature(gd)

    def _ensure_scan(self, force=False) -> None:
        self._need_game()
        with self._scan_lock:
            if force or self._sig is None or self._sig != dir_signature(self.game_dir):
                self._rescan()

    def get_mods(self, force: bool = False) -> dict:
        try:
            self._ensure_scan(force)
        except RuntimeError as e:
            return _err(str(e))
        links = self._cfg.get("nexus_links") or {}
        gh = self._cfg.get("github_links") or {}
        out = []
        for m in self._mods:
            d = m.to_dict()
            d["link"] = self._link_of(m, links)
            d["update"] = self._updates.get(m.key)
            d["tracked"] = (m.nexus_id in self._tracked) if (self._tracked is not None and m.nexus_id) else None
            d["github"] = gh.get(m.key)
            out.append(d)
        return {"ok": True, "mods": out, "summary": self._summary()}

    def _summary(self) -> dict:
        mods = self._mods
        return {"total": len(mods), "enabled": sum(m.enabled for m in mods),
                "disabled": sum(not m.enabled for m in mods),
                "loose": sum(m.source == "loose" for m in mods),
                "vortex": sum(m.source == "vortex" for m in mods),
                "mo2": sum(m.source == "mo2" for m in mods),
                "updates": sum(1 for k, u in self._updates.items() if u.get("update") and
                               (k.startswith("core:") or (k in self._mods_by_key and self._mods_by_key[k].enabled)))}

    def set_mods_enabled(self, keys: list[str], enable: bool) -> dict:
        try:
            self._need_game()
            self._guard_game_closed()
            self._ensure_scan()
        except RuntimeError as e:
            return _err(str(e))
        targets = [self._mods_by_key[k] for k in keys if k in self._mods_by_key]
        loose = [m for m in targets if m.source == "loose"]
        mo2 = [m for m in targets if m.source == "mo2"]
        vortex = [m for m in targets if m.source == "vortex"]
        result = {"ok": True, "moved": 0, "errors": [], "notes": []}
        if loose:
            r = ops.set_mods_enabled(self.game_dir, loose, enable)
            result["moved"] += r["moved"]
            result["errors"] += r["errors"]
        if mo2:
            if self._proc.state()["mo2"]:
                result["errors"].append("Mod Organizer 2 is running. Close it first, or toggle these mods in MO2 "
                                        "(it rewrites modlist.txt on exit).")
            elif self._mo2:
                n = self._mo2.set_enabled([m.manager_ref for m in mo2], enable)
                result["notes"].append(f"Updated {n} mod(s) in MO2 profile '{self._mo2.profile}'.")
        if vortex:
            result["notes"].append(f"{len(vortex)} mod(s) are managed by Vortex. Enable/disable them in Vortex so "
                                   "its deployment stays consistent.")
        with self._scan_lock:
            self._rescan()
        return result

    def set_all_enabled(self, enable: bool) -> dict:
        try:
            self._ensure_scan()
        except RuntimeError as e:
            return _err(str(e))
        keys = [m.key for m in self._mods if m.source == "loose" and (m.enabled != enable or m.partial)]
        return self.set_mods_enabled(keys, enable)

    def open_mod_folder(self, key: str) -> dict:
        m = self._mods_by_key.get(key)
        if not m:
            return _err("Mod not found.")
        if m.source == "mo2" and self._mo2:
            return self.open_path(os.path.join(self._mo2.mods_dir, m.manager_ref or ""))
        c = m.components[0]
        root = os.path.join(self.game_dir, TEMP_DISABLED_DIR) if c.disabled else self.game_dir
        p = os.path.join(root, *c.rel_paths[0].split("/"))
        return self.open_path(p if c.is_dir else os.path.dirname(p))

    # ------------------------------------------------------------- core mods
    def get_core(self) -> dict:
        try:
            self._need_game()
        except RuntimeError as e:
            return _err(str(e))
        core = core_mods.status(self.game_dir, self._cfg.get("manual_versions"))
        for c in core:
            c["update"] = self._updates.get(f"core:{c['name']}")
        return {"ok": True, "core": core}

    def set_core_enabled(self, enable: bool) -> dict:
        try:
            self._need_game()
            self._guard_game_closed()
        except RuntimeError as e:
            return _err(str(e))
        errors = core_mods.set_core_enabled(self.game_dir, enable)
        ops.cleanup_empty_dirs(os.path.join(self.game_dir, TEMP_DISABLED_DIR))
        return {"ok": not errors, "errors": errors, "core": self.get_core().get("core")}

    # ------------------------------------------------------------- logs
    def get_logs(self) -> dict:
        try:
            self._need_game()
        except RuntimeError as e:
            return _err(str(e))
        issues = self._issue_cache.issues(self.game_dir)
        out = []
        for name in logs.LOG_FILES:
            info = issues.get(name)
            if info:
                st = os.stat(info["path"])
                out.append({"name": name, "path": info["path"], "file": os.path.basename(info["path"]),
                            "errors": len(info["errors"]), "warnings": len(info["warnings"]),
                            "modified": st.st_mtime, "size": st.st_size})
        return {"ok": True, "logs": out}

    def read_log(self, name: str) -> dict:
        p = logs.available(self.game_dir).get(name)
        if not p:
            return _err("Log not found.")
        try:
            text = logs.read_text(p, limit=8 * 1024 * 1024)
        except OSError as e:
            return _err(str(e))
        lines = text.splitlines()
        return {"ok": True, "name": name, "path": p,
                "lines": [{"t": ln, "k": logs.classify(ln)} for ln in lines]}

    # ------------------------------------------------------------- report
    def generate_report(self, log_names: list[str]) -> dict:
        try:
            self._ensure_scan(force=True)
        except RuntimeError as e:
            return _err(str(e))
        gd = self.game_dir
        out_dir = self._cfg.get("output_dir") or documents_dir()
        path = os.path.join(out_dir, "Cyberpunk 2077 Mod List.txt")
        if self._cfg.get("ask_report_path"):
            try:
                chosen = self._dialog("save", title="Save mod list as", file_types=["Text file (*.txt)"],
                                      save_filename="Cyberpunk 2077 Mod List.txt", directory=out_dir)
            except Exception as e:
                log.exception("save dialog failed")
                return _err(f"Couldn't open the save dialog: {e}")
            if not chosen:
                return {"ok": False, "cancelled": True}
            path = chosen if chosen.lower().endswith(".txt") else chosen + ".txt"
        mgr = []
        if any(m.source == "vortex" for m in self._mods):
            mgr.append("Vortex")
        if any(m.source == "mo2" for m in self._mods):
            mgr.append(f"MO2 (profile: {self._mo2.profile})" if self._mo2 else "MO2")
        try:
            report.generate(path, game_dir=gd, game_version=game.game_version(gd),
                            phantom_liberty=game.phantom_liberty_installed(gd), store=game.detect_store(gd),
                            mods=self._mods, core=core_mods.status(gd, self._cfg.get("manual_versions")),
                            log_names=log_names, include_errors=self._cfg.get("include_errors_in_output"),
                            include_disabled=self._cfg.get("include_disabled_in_output"),
                            include_grouped=self._cfg.get("include_grouped_in_output"),
                            manager=", ".join(mgr) or None)
        except OSError as e:
            return _err(f"Couldn't write the mod list: {e}")
        if self._cfg.get("auto_open_output"):
            self.open_path(path)
        return {"ok": True, "path": path}

    def copy_report(self, path: str) -> dict:
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                return {"ok": True, "text": f.read()}
        except OSError as e:
            return _err(str(e))

    # ------------------------------------------------------------- nexus
    def _load_updates(self) -> None:
        try:
            with open(self._updates_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._updates = data.get("items", {})
            self._updates_checked = data.get("checked")
        except (OSError, ValueError):
            pass

    def _save_updates(self) -> None:
        try:
            tmp = self._updates_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"checked": self._updates_checked, "items": self._updates}, f)
            os.replace(tmp, self._updates_path)
        except OSError:
            pass

    def get_updates(self) -> dict:
        """Mods and frameworks with a newer version on Nexus, newest first."""
        try:
            self._ensure_scan()
        except RuntimeError as e:
            return _err(str(e))
        rows = []
        for key, u in self._updates.items():
            if not u.get("update"):
                continue
            if key.startswith("core:"):
                rows.append({"key": key, "name": key[5:], "source": "core", "core": True, **u})
                continue
            m = self._mods_by_key.get(key)
            if m and not m.enabled:
                continue  # disabled mods don't need updating until they're enabled again
            if m:  # skip stale entries for mods that were removed or updated outside the tool
                if m.version and nexus.version_newer(u.get("latest"), m.version) is False:
                    continue
                rows.append({"key": key, "name": m.name, "source": m.source, "core": False, **u})
        rows.sort(key=lambda r: -(r.get("updated") or 0))
        return {"ok": True, "updates": rows, "checked": self._updates_checked,
                "connected": bool(self._nexus), "premium": bool((self._nexus_user or {}).get("is_premium"))}

    def _restore_nexus(self) -> None:
        if self._nexus:
            return
        key = secure.unprotect(self._cfg.get("nexus_api_key"))
        if key:
            self._nexus = nexus.NexusClient(key, os.path.join(app_data_dir(), "nexus_cache.json"))
            try:
                self._nexus_user = self._nexus.validate()
                threading.Thread(target=self._refresh_tracked, daemon=True).start()
            except nexus.NexusError:
                self._nexus_user = None  # offline or revoked; keep key, UI shows reconnect

    def nexus_login_key(self, api_key: str) -> dict:
        api_key = (api_key or "").strip()
        if not api_key:
            return _err("Paste your personal API key.")
        client = nexus.NexusClient(api_key, os.path.join(app_data_dir(), "nexus_cache.json"))
        try:
            user = client.validate()
        except nexus.NexusError as e:
            return _err(str(e))
        self._nexus, self._nexus_user = client, user
        self._cfg.set("nexus_api_key", secure.protect(api_key))
        threading.Thread(target=self._refresh_tracked, daemon=True).start()
        return {"ok": True, "user": user}

    def nexus_sso(self) -> dict:
        def work(prog, _c):
            prog(0.1, "Waiting for you to authorise in the browser")
            key = nexus.sso_login(game.open_uri)
            r = self.nexus_login_key(key)
            if not r.get("ok"):
                raise RuntimeError(r.get("error"))
            return r
        return self._task("nexus-sso", work)

    def nexus_logout(self) -> dict:
        self._nexus, self._nexus_user, self._tracked = None, None, None
        self._cfg.set("nexus_api_key", "")
        return {"ok": True}

    def nexus_status(self) -> dict:
        if self._nexus and not self._nexus_user:
            try:
                self._nexus_user = self._nexus.validate()
            except nexus.NexusError as e:
                return {"ok": False, "user": None, "error": str(e), "has_key": True}
        return {"ok": True, "user": self._nexus_user, "has_key": bool(self._nexus),
                "rate": self._nexus.rate if self._nexus else None}

    def _client(self) -> nexus.NexusClient:
        if not self._nexus:
            raise RuntimeError("Log in to Nexus Mods first (Nexus page).")
        return self._nexus

    def nexus_link(self, key: str, text: str) -> dict:
        mod_id = nexus.parse_mod_id(text)
        if not mod_id:
            return _err("Paste a Nexus mod URL or ID.")
        links = self._cfg.get("nexus_links") or {}
        if key not in self._mods_by_key:
            return _err("Mod not found.")
        info = {"mod_id": mod_id, "method": "manual"}
        if self._nexus:
            try:
                data = self._nexus.mod(mod_id)
                if not data:
                    return _err(f"No Cyberpunk 2077 mod with ID {mod_id}.")
                info["name"] = data.get("name")
            except nexus.NexusError as e:
                return _err(str(e))
        for k in self._keys_for(key):   # every piece of a grouped mod
            prev = links.get(k) or {}
            if prev.get("mod_id") != mod_id:   # a different page: its version/file no longer apply
                prev = {x: v for x, v in prev.items() if x not in ("version", "file_id", "uploaded")}
            links[k] = {**prev, **info}
        self._cfg.set("nexus_links", links)
        self._updates.pop(key, None)
        if self._nexus and self._cfg.get("auto_track"):
            try:
                self._nexus.track(mod_id)
                if self._tracked is not None:
                    self._tracked.add(mod_id)
            except nexus.NexusError:
                pass
        with self._scan_lock:
            self._rescan()
        return {"ok": True, "link": links[key]}

    def nexus_unlink(self, key: str) -> dict:
        """Remove a Nexus link. Remembered as 'not this mod' so automatic matching won't relink it."""
        links = self._cfg.get("nexus_links") or {}
        rej = set(self._cfg.get("nexus_rejected") or [])
        for k in self._keys_for(key):
            old = links.pop(k, None)
            if old and old.get("mod_id"):
                rej.add(f"{k}|{old['mod_id']}")
        self._cfg.set("nexus_links", links, save=False)
        self._cfg.set("nexus_rejected", sorted(rej), save=False)
        self._cfg.save()
        self._updates.pop(key, None)
        with self._scan_lock:
            self._rescan()
        return {"ok": True}

    def nexus_tracked(self) -> dict:
        try:
            client = self._client()
            tracked = client.tracked()
            self._ensure_scan()
        except (RuntimeError, nexus.NexusError) as e:
            return _err(str(e))
        self._tracked = {t["mod_id"] for t in tracked}
        names = {}
        if self._catalog_obj:
            names = {m["mod_id"]: m["name"] for m in self._catalog_obj.mods}
        installed = {}
        for m in self._mods:
            if m.nexus_id:
                installed.setdefault(m.nexus_id, m)
        not_tracked = [{"key": m.key, "name": m.name, "mod_id": mid} for mid, m in installed.items()
                       if mid not in self._tracked]
        tracked_rows = [{"mod_id": mid, "name": names.get(mid) or (installed[mid].name if mid in installed else None),
                         "installed": mid in installed, "url": nexus.mod_url(mid)} for mid in sorted(self._tracked)]
        return {"ok": True, "tracked": tracked_rows, "not_tracked": not_tracked}

    def nexus_track(self, mod_id: int, track: bool = True) -> dict:
        try:
            client = self._client()
            client.track(int(mod_id)) if track else client.untrack(int(mod_id))
        except (RuntimeError, nexus.NexusError) as e:
            return _err(str(e))
        if self._tracked is not None:
            (self._tracked.add if track else self._tracked.discard)(int(mod_id))
        return {"ok": True}

    def nexus_track_installed(self) -> dict:
        try:
            client = self._client()
            self._ensure_scan()
            already = {t["mod_id"] for t in client.tracked()}
        except (RuntimeError, nexus.NexusError) as e:
            return _err(str(e))
        ids = sorted({m.nexus_id for m in self._mods if m.nexus_id and m.nexus_id not in already})

        def work(prog, cancelled):
            for i, mid in enumerate(ids, 1):
                if cancelled():
                    raise InterruptedError
                client.track(mid)
                prog(i / max(len(ids), 1), f"Tracking {mid}")
            return {"tracked": len(ids)}
        return self._task("track-all", work)

    def nexus_mod_info(self, mod_id: int) -> dict:
        try:
            d = self._client().mod(int(mod_id))
        except (RuntimeError, nexus.NexusError) as e:
            return _err(str(e))
        if not d:
            return _err("Not found.")
        return {"ok": True, "mod": {k: d.get(k) for k in ("mod_id", "name", "summary", "version", "author",
                                                          "picture_url", "updated_timestamp",
                                                          "endorsement_count")}}

    # ------------------------------------------------------------- status
    def get_running(self) -> dict:
        """Fast poll (every ~1.5 s) for the launch button."""
        st = self._proc.state()
        now = time.monotonic()
        if st["game"]:
            if not self._game_seen and not self._launch_mark:
                self._launch_mark = time.time() - 5   # game started outside the tool
            self._game_seen = True
            self._launch_started = None
        elif self._game_seen:          # game was running and has closed
            self._game_seen = False
        launching = bool(self._launch_started and now - self._launch_started < 150 and not st["game"])
        if self._launch_started and not launching:
            self._launch_started = None
        return {"game": st["game"], "launching": launching, "mo2": st["mo2"], "vortex": st["vortex"]}

    def get_status(self) -> dict:
        """Cheap poll for the status bar / dashboard (called every few seconds)."""
        gd = self.game_dir
        st = {"running": self.get_running(), "valid": game.is_valid_game_dir(gd)}
        self._process_inbox()
        st["nxm_tasks"] = self._drain_nxm_tasks()
        if not st["valid"]:
            return st
        changed = False
        try:
            changed = self._sig is not None and dir_signature(gd) != self._sig
            if self._sig is None or changed:
                with self._scan_lock:
                    self._rescan()
        except OSError:
            log.exception("rescan failed")
        try:
            issues = self._issue_cache.issues(gd)
        except Exception:
            log.exception("log scan failed")
            issues = {}
        try:
            core = core_mods.status(gd, self._cfg.get("manual_versions"))
        except Exception:
            log.exception("core status failed")
            core = []
        st["backup"] = self._backup_state()
        st["backup_task"] = self._maybe_scheduled_backup(st["running"])
        st.update({
            "changed": changed, "summary": self._summary(),
            "log_errors": sum(len(v["errors"]) for v in issues.values()),
            "log_warnings": sum(len(v["warnings"]) for v in issues.values()),
            "logs_with_errors": [k for k, v in issues.items() if v["errors"]],
            "log_errors_fresh": any(v["errors"] and self._launch_mark and os.path.getmtime(v["path"]) >= self._launch_mark
                                    for v in issues.values()),
            "core_ok": all(c["installed"] for c in core),
            "core_missing": [c["name"] for c in core if not c["installed"]],
        })
        return st

    # ------------------------------------------------------------- launch
    def launch_game(self) -> dict:
        try:
            self._need_game()
        except RuntimeError as e:
            return _err(str(e))
        run = self.get_running()
        if run["game"]:
            return _err("Cyberpunk 2077 is already running.")
        if run["launching"]:
            return _err("Cyberpunk 2077 is already starting. Give it a moment.")
        via = self._cfg.get("launch_via")
        mo2 = None
        if self._mo2 and self._mo2.exe and (via == "mo2" or (via == "auto" and any(m.source == "mo2" for m in self._mods))):
            title = self._cfg.get("mo2_executable") or self._mo2.default_game_executable()
            if title:
                mo2 = {"exe": self._mo2.exe, "shortcut": self._mo2.shortcut(title)}
        try:
            how = game.launch_game(self.game_dir, via, mo2)
        except Exception as e:
            log.exception("launch failed")
            return _err(f"Failed to launch: {e}")
        self._launch_started = time.monotonic()
        self._launch_mark = time.time() - 5
        self._proc.invalidate()
        log.info("Launched game via %s", how)
        return {"ok": True, "via": how}

    # ------------------------------------------------------------- presets / install
    EXPORT_FORMATS = {"zip": "Zip archive (*.zip)", "7z": "7z archive (*.7z)", "rar": "RAR archive (*.rar)"}

    def export_formats(self) -> list:
        return ops.export_formats()

    def export_preset(self, keys: list[str] | None = None, fmt: str = "zip") -> dict:
        try:
            self._ensure_scan()
        except RuntimeError as e:
            return _err(str(e))
        fmt = fmt if fmt in ops.export_formats() else "zip"
        stamp = time.strftime("%Y%m%d_%H%M%S")
        try:
            path = self._dialog("save", title="Save mod preset", file_types=[self.EXPORT_FORMATS[fmt]],
                                save_filename=f"Cyberpunk2077_Mod_Preset_{stamp}.{fmt}")
        except Exception as e:
            log.exception("save dialog failed")
            return _err(f"Couldn't open the save dialog: {e}")
        if not path:
            return {"ok": False}
        if not path.lower().endswith("." + fmt):
            path += "." + fmt
        mods = [self._mods_by_key[k] for k in keys if k in self._mods_by_key] if keys else \
            [m for m in self._mods if m.enabled and m.source != "mo2"]
        gd = self.game_dir
        return self._task("export", lambda prog, cancelled: ops.export_preset(gd, mods, path, prog, cancelled))

    def install_archive(self, kind: str = "mod", overwrite: bool = False) -> dict:
        try:
            self._need_game()
            self._guard_game_closed()
        except RuntimeError as e:
            return _err(str(e))
        path = self._dialog("open", title="Install mod preset" if kind == "preset" else "Install mod",
                            file_types=["Archives (*.zip;*.7z;*.rar)", "All files (*.*)"],
                            directory=self._install_start_dir())
        if not path:
            return {"ok": False}
        self._cfg.set("last_install_dir", os.path.dirname(path))
        gd = self.game_dir
        info = identify.parse_nexus_filename(path) if kind != "preset" else None

        def work(prog, _c):
            r = ops.install_archive(gd, path, None, prog, bool(overwrite) and kind == "preset")
            if kind != "preset":   # one archive = one mod (presets bundle many)
                self._remember_install_group(r["installed"])
            with self._scan_lock:
                self._rescan()
            if info:  # Nexus download filename -> link the new mod with exact version
                self._link_installed(r["installed"], info["mod_id"], None, info["version"], "installed",
                                     uploaded=info.get("timestamp"))
            return r
        return self._task("install", work)

    def _install_start_dir(self) -> str:
        """Where the Install mod dialog opens: the folder last installed from, else Downloads."""
        for d in (self._cfg.get("last_install_dir"), identify.downloads_dir()):
            if d and os.path.isdir(d):
                return d
        return ""

    def _remember_install_group(self, installed: list[str]) -> None:
        """Files installed from one archive are one mod, whatever folders they land in."""
        comps = identify.component_paths(installed)
        if len(comps) < 2:
            return
        keep = []
        for g in self._cfg.get("install_groups") or []:
            if comps & set(g):     # an update/reinstall of the same mod: merge with the old record
                comps |= set(g)
            else:
                keep.append(g)
        keep.append(sorted(comps))
        self._cfg.set("install_groups", keep[-3000:])

    @staticmethod
    def _members(m) -> list[str]:
        return list(m.members) if getattr(m, "members", None) else [m.key]

    def _keys_for(self, key: str) -> list[str]:
        m = self._mods_by_key.get(key)
        return self._members(m) if m else [key]

    def _link_of(self, m, links: dict | None = None) -> dict | None:
        links = self._cfg.get("nexus_links") if links is None else links
        for k in [m.key] + [k for k in self._members(m) if k != m.key]:
            if (links or {}).get(k):
                return links[k]
        return None

    def _link_installed(self, installed: list[str], mod_id: int, file_id, version, method: str,
                        uploaded: int | None = None) -> None:
        comps = identify.component_paths(installed)
        links = self._cfg.get("nexus_links") or {}
        with self._scan_lock:
            self._rescan()
        for m in self._mods:
            if m.source != "loose":
                continue
            for c in m.components:   # link the pre-grouping entries the archive actually touched
                if scanner_key(c) in comps:
                    links[c.member or m.key] = {"mod_id": mod_id, "file_id": file_id, "version": version,
                                                "method": method, **({"uploaded": uploaded} if uploaded else {})}
        self._cfg.set("nexus_links", links)
        with self._scan_lock:
            self._rescan()

    # ------------------------------------------------------------- identification
    def get_download_folders(self) -> dict:
        mo2_dl = self._mo2_downloads()
        return {"ok": True, "folders": identify.candidate_folders(self._cfg.get("download_folders"), mo2_dl),
                "extra": self._cfg.get("download_folders") or []}

    def add_download_folder(self) -> dict:
        res = self._dialog("folder", title="Folder where you keep downloaded mod archives")
        if res:
            lst = self._cfg.get("download_folders") or []
            if res not in lst:
                lst.append(res)
            self._cfg.set("download_folders", lst)
        return self.get_download_folders()

    def remove_download_folder(self, path: str) -> dict:
        self._cfg.set("download_folders", [p for p in (self._cfg.get("download_folders") or []) if p != path])
        return self.get_download_folders()

    def _mo2_downloads(self) -> str | None:
        if not self._mo2:
            return None
        v = managers._ini_value(self._mo2.ini.get("Settings", "download_directory", fallback=""))
        v = (v or os.path.join(self._mo2.base_dir, "downloads")).replace("%BASE_DIR%", self._mo2.base_dir)
        return os.path.normpath(v)

    def _unlinked_mods(self) -> list[Mod]:
        """Manual mods still waiting for a Nexus link. Disabled mods only count when the
        user chose to show them in the link queue (Settings > Linking mods to Nexus)."""
        gh = self._cfg.get("github_links") or {}
        with_disabled = bool(self._cfg.get("queue_include_disabled"))
        return [m for m in self._mods if m.source == "loose" and not m.nexus_id and m.key not in gh
                and (with_disabled or m.enabled)]

    def nexus_identify(self, keys: list[str] | None = None) -> dict:
        """Find which Nexus mod each manual install came from.
        Step 1 (offline): match against downloaded archives. Step 2 (login): name search."""
        try:
            self._ensure_scan()
        except RuntimeError as e:
            return _err(str(e))
        gd = self.game_dir
        if keys:  # explicit request (e.g. one mod's Find button) always runs
            targets = [m for m in self._mods if m.source == "loose" and m.key in keys]
        else:
            targets = self._unlinked_mods()
        folders = identify.candidate_folders(self._cfg.get("download_folders"), self._mo2_downloads())
        index = identify.ArchiveIndex(os.path.join(app_data_dir(), "archive_index.json"))
        seven = ops.find_7z()
        client = self._nexus

        def work(prog, cancelled):
            links = self._cfg.get("nexus_links") or {}
            suggestions = self._cfg.get("nexus_suggestions") or {}
            rejected = set(self._cfg.get("nexus_rejected") or [])
            # -- step 0: Nexus URLs the author wrote into the mod's own files (.xl, .reds, init.lua, ...)
            disabled_root0 = os.path.join(gd, TEMP_DISABLED_DIR)
            core_ids = {c["nexus_id"] for c in core_mods.CORE.values()}
            found_all, repos_all = {}, {}
            for i, m in enumerate(targets, 1):
                if cancelled():
                    raise InterruptedError
                prog(0.1 * i / max(len(targets), 1), f"Reading mod files {i}/{len(targets)}: {m.name}")
                repos_all[m.key] = {}
                found_all[m.key] = identify.urls_in_mod(m, gd, disabled_root0, repos=repos_all[m.key])
            # an ID referenced by many different mods is a shared requirement, not the mod itself
            ref_count: dict[int, int] = {}
            for f in found_all.values():
                for mid in f:
                    ref_count[mid] = ref_count.get(mid, 0) + 1
            common = {mid for mid, n in ref_count.items() if n >= 3}
            cat0 = None
            if client:
                try:
                    cat0 = self._catalog(lambda f, msg: prog(0.1 + 0.05 * f, msg), cancelled)
                except nexus.NexusError:
                    cat0 = None
            by_url = 0
            for m in targets:
                found = found_all.get(m.key) or {}
                if not found:
                    continue
                found = {k: v for k, v in found.items() if f"{m.key}|{k}" not in rejected}
                own, cands = identify.pick_own_id(found, core_ids | common, identify.local_names(m), cat0)
                if own is None and not cands:  # only framework/common links: try again allowing common ids
                    own, cands = identify.pick_own_id(found, core_ids, identify.local_names(m), cat0)
                if own:
                    name = next((x["name"] for x in cat0.mods if x["mod_id"] == own), None) if cat0 else None
                    links[m.key] = {"mod_id": own, "name": name, "method": "in_files"}
                    suggestions.pop(m.key, None)
                    by_url += 1
                elif cands:
                    names = {x["mod_id"]: x["name"] for x in cat0.mods} if cat0 else {}
                    suggestions[m.key] = {"local": m.name, "score": 0.9, "source": "in_files",
                                          "options": [{"mod_id": c, "name": names.get(c) or f"Mod {c}"} for c in cands[:4]]}
            # GitHub-only mods (no Nexus link in their files): link the repo they point to,
            # unless that repo is referenced by many mods (a shared library)
            gh_links = self._cfg.get("github_links") or {}
            repo_refs: dict[str, int] = {}
            for rp in repos_all.values():
                for r in rp:
                    repo_refs[r.lower()] = repo_refs.get(r.lower(), 0) + 1
            by_github = 0
            for m in targets:
                if m.key in links or m.key in gh_links:
                    continue
                own = [r for r in (repos_all.get(m.key) or {}) if repo_refs[r.lower()] < 3]
                if len(own) == 1:
                    gh_links[m.key] = {"repo": own[0], "method": "in_files"}
                    by_github += 1
            self._cfg.set("github_links", gh_links, save=False)
            # -- step 1: download archives
            paths = identify.find_archives(folders)
            archives = []
            for i, p in enumerate(paths, 1):
                if cancelled():
                    raise InterruptedError
                prog(0.15 + 0.45 * i / max(len(paths), 1), f"Reading downloads {i}/{len(paths)}: {os.path.basename(p)}")
                rec = index.entries(p, seven)
                if rec["components"]:
                    archives.append({"path": p, "components": set(rec["components"]),
                                     "info": identify.parse_nexus_filename(p)})
            index.save()
            matches = identify.match_downloads([m for m in targets if m.key not in links], archives)
            by_download = 0
            unresolved_md5 = []
            for key, mt in matches.items():
                if mt["info"]:
                    links[key] = {"mod_id": mt["info"]["mod_id"], "version": mt["info"]["version"],
                                  "name": mt["info"]["name"], "method": "download",
                                  "uploaded": mt["info"].get("timestamp"),
                                  "archive": os.path.basename(mt["archive"])}
                    suggestions.pop(key, None)
                    by_download += 1
                elif client:
                    unresolved_md5.append((key, mt["archive"]))
            # renamed downloads: Nexus MD5 lookup works on the archive itself
            for key, path in unresolved_md5:
                if cancelled():
                    raise InterruptedError
                try:
                    hits = client.md5_search(nexus.md5_file(path, self._md5_cache))
                except (OSError, nexus.NexusError):
                    continue
                if hits:
                    mod, fd = hits[0].get("mod") or {}, hits[0].get("file_details") or {}
                    if mod.get("mod_id"):
                        links[key] = {"mod_id": mod["mod_id"], "file_id": fd.get("file_id"),
                                      "version": fd.get("version") or fd.get("mod_version"),
                                      "name": mod.get("name"), "method": "download"}
                        by_download += 1
            # -- step 2: catalog name match, then verify against Nexus's file lists
            by_name, suggested, search_error, verified = 0, 0, None, 0
            rest = [m for m in targets if m.key not in links and m.key not in suggestions]
            if client and rest:
                try:
                    cat = self._catalog(lambda f, msg: prog(0.6 + 0.1 * f, msg), cancelled)
                except nexus.NexusError as e:
                    cat, search_error = None, str(e)
                disabled_root = os.path.join(gd, TEMP_DISABLED_DIR)
                done = [0]
                lock = threading.Lock()

                def one(m):
                    if cancelled():
                        return None
                    names = identify.local_names(m)
                    if cat:
                        cands = cat.candidates(names)
                        if not cands or cands[0][1] < 0.9:   # cached list may be incomplete: ask Nexus too
                            live = []
                            for term in identify.search_terms(m.name)[:1]:
                                try:
                                    live += client.any_search(term)
                                except nexus.NexusError:
                                    pass
                            if live:
                                extra = [(n, max(identify.similarity(x, n["name"]) for x in names)) for n in live]
                                byid = {c["mod_id"]: (c, sc) for c, sc in cands + extra}
                                cands = sorted(byid.values(), key=lambda t: -t[1])[:4]
                    else:  # catalog unavailable: per-name search
                        nodes = []
                        for term in identify.search_terms(m.name)[:1]:
                            try:
                                nodes += client.any_search(term)
                            except nexus.NexusError:
                                pass
                        cands = sorted(((n, max(identify.similarity(x, n["name"]) for x in names)) for n in nodes),
                                       key=lambda t: -t[1])[:4]
                    cands = [(c, sc) for c, sc in cands if f"{m.key}|{c['mod_id']}" not in rejected]
                    installed = identify.installed_files(m, gd, disabled_root)
                    best = None
                    for cand, sc in cands[:3]:
                        if sc < 0.5 or identify.numbers_conflict(m.name, cand["name"]):
                            continue
                        try:
                            files = (client.files(cand["mod_id"], ttl=7 * 86400) or {}).get("files", [])
                        except nexus.NexusError:
                            continue
                        files = sorted((f for f in files if f.get("content_preview_link")
                                        and f.get("category_name") not in ("DELETED",)),
                                       key=lambda f: -(f.get("uploaded_timestamp") or 0))[:10]
                        for f in files:
                            v = identify.verify_against_preview(m, client.content_preview(f["content_preview_link"]),
                                                                installed)
                            if v["coverage"] < 0.6 or v["precision"] < 0.2:
                                continue
                            rank = (v["coverage"], v["size_hits"], sc, f.get("uploaded_timestamp") or 0)
                            if best is None or rank > best[0]:
                                best = (rank, cand, f, v)
                    with lock:
                        done[0] += 1
                        prog(0.7 + 0.3 * done[0] / len(rest), f"Checking Nexus {done[0]}/{len(rest)}: {m.name}")
                    return m, cands, best

                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=6) as pool:
                    results = list(pool.map(one, rest))
                for res in results:
                    if not res:
                        continue
                    m, cands, best = res
                    if best:
                        _, cand, f, v = best
                        exact_ver = v["size_total"] and v["size_hits"] == v["size_total"]
                        links[m.key] = {"mod_id": cand["mod_id"], "name": cand["name"], "method": "verified",
                                        "file_id": f.get("file_id") if exact_ver else None,
                                        "version": (f.get("version") or f.get("mod_version")) if exact_ver else None}
                        suggestions.pop(m.key, None)
                        verified += 1
                    elif cands and cands[0][1] >= 0.97:
                        links[m.key] = {"mod_id": cands[0][0]["mod_id"], "name": cands[0][0]["name"], "method": "name"}
                        suggestions.pop(m.key, None)
                        by_name += 1
                    elif cands and cands[0][1] >= 0.55:
                        suggestions[m.key] = {"local": m.name, "score": round(cands[0][1], 2),
                                              "options": [{"mod_id": c["mod_id"], "name": c["name"]} for c, _ in cands[:4]]}
                        suggested += 1
            if client and self._cfg.get("auto_track"):
                try:
                    tracked = {t["mod_id"] for t in client.tracked()}
                    for lk in links.values():
                        if lk.get("mod_id") and lk["mod_id"] not in tracked:
                            client.track(lk["mod_id"])
                            tracked.add(lk["mod_id"])
                    self._tracked = tracked
                except nexus.NexusError:
                    pass
            self._cfg.update({"nexus_links": links, "nexus_suggestions": suggestions})
            with self._scan_lock:
                self._rescan()
            return {"checked": len(targets), "archives": len(archives), "by_download": by_download,
                    "verified": verified, "by_name": by_name, "by_url": by_url, "by_github": by_github, "suggested": sum(1 for m in targets if m.key in suggestions and m.key not in links), "logged_in": bool(client),
                    "search_error": search_error, "identified": by_url + by_download + verified + by_name,
                    "unlinked": sum(1 for m in targets if m.key not in links and m.key not in suggestions)}
        return self._task("identify", work)

    def _catalog(self, progress=None, cancelled=lambda: False):
        """Nexus's full Cyberpunk mod list, cached on disk for a week."""
        if self._catalog_obj is not None:
            return self._catalog_obj
        path = os.path.join(app_data_dir(), "nexus_catalog.json")
        data = None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if time.time() - data.get("fetched", 0) > 7 * 86400 or data.get("v") != 2:
                data = None   # v1 lists could have duplicates/gaps: rebuild once
        except (OSError, ValueError):
            data = None
        if data is None:
            mods = self._client().catalog(progress, cancelled)
            data = {"fetched": time.time(), "mods": mods, "v": 2}
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f)
            except OSError:
                pass
        self._catalog_obj = identify.Catalog(data["mods"])
        return self._catalog_obj

    def nexus_search(self, term: str) -> dict:
        """Search Nexus for the manual link box: local catalog if available, otherwise the API."""
        term = (term or "").strip()
        mid = nexus.parse_mod_id(term)
        try:
            client = self._client()
        except RuntimeError as e:
            return _err(str(e))
        if mid and ("nexusmods.com" in term or term.isdigit()):
            try:
                d = client.mod(mid)
            except nexus.NexusError as e:
                return _err(str(e))
            return {"ok": True, "results": [{"mod_id": mid, "name": d.get("name"), "version": d.get("version")}] if d else []}
        if len(term) < 2:
            return {"ok": True, "results": []}
        local, live = [], []
        try:
            cat = self._catalog_obj or (self._catalog() if os.path.exists(os.path.join(app_data_dir(), "nexus_catalog.json")) else None)
            if cat:
                local = cat.search(term, top=25)
        except nexus.NexusError:
            cat = None
        try:
            live = client.any_search(term)      # catches mods newer than (or missing from) the cached list
            if cat:
                cat.add(live)
        except nexus.NexusError as e:
            if not local:
                return _err(str(e))
        return {"ok": True, "results": identify.merge_ranked(term, local, live, top=20)}

    def _refresh_tracked(self) -> None:
        if self._nexus:
            try:
                self._tracked = {t["mod_id"] for t in self._nexus.tracked()}
            except nexus.NexusError:
                pass

    def app_logo(self) -> dict:
        from . import icons
        uri = icons.bundled_data_uri("mod_list_tool.png")
        return {"ok": bool(uri), "uri": uri}

    def get_suggestions(self) -> dict:
        sug = self._cfg.get("nexus_suggestions") or {}
        live = {k: v for k, v in sug.items() if k in self._mods_by_key and not self._mods_by_key[k].nexus_id}
        return {"ok": True, "suggestions": [{"key": k, **v} for k, v in sorted(live.items(), key=lambda kv: kv[1]["local"].lower())]}

    def resolve_suggestion(self, key: str, mod_id: int | None) -> dict:
        sug = self._cfg.get("nexus_suggestions") or {}
        item = sug.pop(key, None)
        if mod_id:
            links = self._cfg.get("nexus_links") or {}
            name = next((o["name"] for o in (item or {}).get("options", []) if o["mod_id"] == mod_id), None)
            links[key] = {"mod_id": int(mod_id), "name": name, "method": "confirmed"}
            self._cfg.set("nexus_links", links, save=False)
        elif item:
            rej = set(self._cfg.get("nexus_rejected") or [])
            rej.update(f"{key}|{o['mod_id']}" for o in item.get("options", []))
            self._cfg.set("nexus_rejected", sorted(rej), save=False)
        self._cfg.set("nexus_suggestions", sug)
        with self._scan_lock:
            self._rescan()
        return {"ok": True}

    # ------------------------------------------------------------- update checks
    def nexus_check_updates(self, keys: list[str] | None = None) -> dict:
        """Check Nexus-linked mods, frameworks and GitHub-linked mods for newer versions."""
        try:
            self._ensure_scan()
        except RuntimeError as e:
            return _err(str(e))
        client = self._nexus
        gh_links = self._cfg.get("github_links") or {}
        gh_mods = [m for m in self._mods if m.key in gh_links and (not keys or m.key in keys)]
        if not client and not gh_mods:
            return _err("Log in to Nexus Mods first (Nexus page), or link a mod to GitHub.")
        gd = self.game_dir
        disabled_root = os.path.join(gd, TEMP_DISABLED_DIR)
        mods = [m for m in self._mods if m.nexus_id and m.key not in gh_links and (not keys or m.key in keys)] if client else []
        core = [] if keys or not client else core_mods.status(gd, self._cfg.get("manual_versions"))
        links = self._cfg.get("nexus_links") or {}

        def work(prog, cancelled):
            n_gh = self._check_github(gh_mods, gh_links, disabled_root, cancelled)
            if not client:
                self._updates_checked = time.time()
                self._save_updates()
                return {"checked": len(gh_mods), "updates": n_gh, "rate": None, "linked": len(gh_mods),
                        "unlinked": len(self._unlinked_mods())}
            items = [(m.key, m.nexus_id, m.version or (self._link_of(m, links) or {}).get("version"), m) for m in mods] + \
                    [(f"core:{c['name']}", c["nexus_id"], c.get("version"), None) for c in core if c["installed"]]
            recent = set()
            try:  # one request says which mods changed this month; the rest can come from cache
                recent = {u["mod_id"] for u in client.updated("1m")}
            except nexus.NexusError:
                pass
            n_updates = n_gh
            for i, (key, mid, installed, m) in enumerate(items, 1):
                if cancelled():
                    raise InterruptedError
                label = key[5:] if key.startswith("core:") else m.name
                prog(i / max(len(items), 1), f"{i}/{len(items)}  {label}")
                ttl = 120 if mid in recent else 6 * 3600
                try:
                    d = client.mod(mid, ttl=ttl) or {}
                except nexus.NexusError as e:
                    if "rate limit" in str(e) or "rejected" in str(e):
                        raise
                    log.warning("mod %s lookup failed: %s", mid, e)
                    continue
                latest = d.get("version")
                basis = "exact" if installed else None
                likely = False
                if not installed and m is not None:
                    mtime = identify.newest_mtime(gd, m, disabled_root)
                    try:
                        est = client.estimate_installed(mid, mtime)
                    except nexus.NexusError:
                        est = None
                    if est and est.get("version"):
                        installed, basis = est["version"], "estimated"
                    elif mtime and d.get("updated_timestamp") and d["updated_timestamp"] > mtime + 3 * 86400:
                        likely = True
                newer = nexus.version_newer(latest, installed)
                update = bool(newer) or (newer is None and likely)
                file_id, outdated = None, []
                if update and m is not None and basis == "exact":
                    # The page version is the main file's; optional files have their own.
                    # Check each installed piece against the mod's file list instead.
                    res = self._file_check(client, m, mid, links, ttl)
                    if res is not None:
                        update, outdated = res["update"], res["outdated"]
                        latest, file_id = res.get("latest") or latest, res.get("file_id")
                self._updates[key] = {"mod_id": mid, "nexus_name": d.get("name"), "latest": latest,
                                      "installed": installed, "basis": basis or ("dates" if likely else None),
                                      "update": update, "updated": d.get("updated_timestamp"),
                                      "picture": d.get("picture_url"), "url": nexus.mod_url(mid),
                                      **({"file_id": file_id} if file_id else {}),
                                      **({"outdated": outdated} if outdated else {})}
                n_updates += update
            self._updates_checked = time.time()
            self._save_updates()
            return {"checked": len(items) + len(gh_mods), "updates": n_updates, "rate": client.rate,
                    "linked": len(mods), "unlinked": len(self._unlinked_mods())}
        return self._task("updates", work)

    def _file_check(self, client, m, mid: int, links: dict, ttl: int) -> dict | None:
        """Per-file update status for a linked mod (and each piece of a grouped mod).
        None when the file list can't tell, so the caller keeps the page-version result."""
        try:
            files = client.files(mid, ttl=ttl)
        except nexus.NexusError:
            return None
        pieces = [(k, links.get(k)) for k in self._members(m)]
        pieces = [(k, l) for k, l in pieces if l and l.get("mod_id") == mid and (l.get("version") or l.get("file_id"))]
        if not pieces:
            pieces = [(m.key, {"version": m.version})]
        verdicts = []
        for k, l in pieces:
            st = nexus.installed_file_status(files, l.get("version"), l.get("file_id"), l.get("uploaded"))
            if st is None:
                return None
            verdicts.append((k, st))
        stale = [(k, st) for k, st in verdicts if not st["current"]]
        if not stale:
            return {"update": False, "outdated": []}
        k0, st0 = next(((k, st) for k, st in stale if st.get("file_id")), stale[0])
        return {"update": True, "outdated": [k for k, _ in stale], "latest": st0.get("latest"),
                "file_id": st0.get("file_id")}

    def _check_github(self, gh_mods, gh_links, disabled_root, cancelled) -> int:
        n = 0
        for m in gh_mods:
            if cancelled():
                raise InterruptedError
            repo = gh_links[m.key]["repo"]
            try:
                rels = self._gh.releases(repo)
            except github.GitHubError as e:
                log.warning("GitHub %s: %s", repo, e)
                continue
            latest = next((r for r in rels if not r.get("prerelease")), rels[0] if rels else None)
            if not latest:
                continue
            installed = m.version or gh_links[m.key].get("version")
            basis = "exact" if installed else None
            if not installed:
                est = github.estimate_installed(rels, identify.newest_mtime(self.game_dir, m, disabled_root))
                if est:
                    installed, basis = github.version_of(est), "estimated"
            lv = github.version_of(latest)
            newer = nexus.version_newer(lv, installed)
            self._updates[m.key] = {"source": "github", "repo": repo, "latest": lv, "installed": installed,
                                    "basis": basis, "update": bool(newer), "updated": github.published_ts(latest),
                                    "url": latest.get("html_url") or f"https://github.com/{repo}/releases"}
            n += bool(newer)
        return n

    # ------------------------------------------------------------- GitHub links
    def github_link(self, key: str, text: str) -> dict:
        repo = github.parse_repo(text)
        if not repo:
            return _err("Paste a GitHub repository URL, like https://github.com/owner/repo.")
        if key not in self._mods_by_key:
            return _err("Mod not found.")
        try:
            info = self._gh.repo(repo)
        except github.GitHubError as e:
            return _err(str(e))
        if not info:
            return _err(f"GitHub repository {repo} wasn't found.")
        gl = self._cfg.get("github_links") or {}
        gl[key] = {"repo": info["repo"] or repo}
        self._cfg.set("github_links", gl)
        self._updates.pop(key, None)
        return {"ok": True, "repo": gl[key]["repo"]}

    def github_unlink(self, key: str) -> dict:
        gl = self._cfg.get("github_links") or {}
        gl.pop(key, None)
        self._cfg.set("github_links", gl)
        if (self._updates.get(key) or {}).get("source") == "github":
            self._updates.pop(key, None)
            self._save_updates()
        return {"ok": True}

    # ------------------------------------------------------------- mod details (side panel)
    def mod_details(self, key: str) -> dict:
        """Nexus page info (picture, summary, author...) and/or GitHub repo info for a mod."""
        m = self._mods_by_key.get(key)
        if not m:
            return _err("Mod not found.")
        out = {"ok": True, "nexus": None, "github": None}
        gl = (self._cfg.get("github_links") or {}).get(key)
        if gl:
            try:
                info = self._gh.repo(gl["repo"]) or {"repo": gl["repo"]}
                rel = self._gh.latest(gl["repo"])
                if rel:
                    info["latest"] = github.version_of(rel)
                    info["latest_date"] = github.published_ts(rel)
                out["github"] = info
            except github.GitHubError as e:
                out["github"] = {"repo": gl["repo"], "error": str(e)}
        if m.nexus_id and self._nexus:
            try:
                d = self._nexus.mod(m.nexus_id) or {}
                out["nexus"] = {k: d.get(k) for k in ("mod_id", "name", "summary", "version", "author", "picture_url",
                                                       "updated_timestamp", "endorsement_count", "contains_adult_content")}
                out["nexus"]["url"] = nexus.mod_url(m.nexus_id)
            except nexus.NexusError as e:
                out["nexus"] = {"mod_id": m.nexus_id, "error": str(e), "url": nexus.mod_url(m.nexus_id)}
        elif m.nexus_id:
            out["nexus"] = {"mod_id": m.nexus_id, "url": nexus.mod_url(m.nexus_id)}
        return out

    def mark_up_to_date(self, key: str) -> dict:
        u = self._updates.get(key)
        if not u:
            return _err("No update information for this mod.")
        if key.startswith("core:"):
            mv = self._cfg.get("manual_versions") or {}
            mv[key[5:]] = u.get("latest")
            self._cfg.set("manual_versions", mv)
        else:
            links = self._cfg.get("nexus_links") or {}
            stale = set(u.get("outdated") or [key])
            for k in self._keys_for(key):
                if k in stale:
                    links[k] = {**(links.get(k) or {"mod_id": u["mod_id"]}), "version": u.get("latest"),
                                **({"file_id": u["file_id"]} if u.get("file_id") else {})}
            self._cfg.set("nexus_links", links)
        u.update({"update": False, "installed": u.get("latest"), "basis": "exact"})
        self._save_updates()
        with self._scan_lock:
            self._rescan()
        return {"ok": True}

    # ------------------------------------------------------------- in-app updates
    def nxm_status(self) -> dict:
        return {"ok": True, **nxm.status(), "previous": self._cfg.get("nxm_previous_handler")}

    def nxm_set(self, enable: bool) -> dict:
        try:
            r = nxm.register(self._cfg) if enable else nxm.unregister(self._cfg)
        except OSError as e:
            return _err(f"Couldn't change the link handler: {e}")
        return r

    def nexus_update(self, key: str) -> dict:
        """Premium: download and install now. Free: open the Files tab; if this tool handles
        nxm links the Mod Manager Download button installs it here."""
        if (self._updates.get(key) or {}).get("source") == "github":
            return self._github_install(key)
        core_name = key[5:] if key.startswith("core:") else None
        m = None if core_name else self._mods_by_key.get(key)
        mod_id = core_mods.CORE[core_name]["nexus_id"] if core_name else (m.nexus_id if m else None)
        if not mod_id:
            return _err("This mod isn't linked to Nexus.")
        files_url = nexus.mod_url(mod_id, "files")
        if m and m.source in ("vortex", "mo2"):
            game.open_uri(files_url)
            return {"ok": True, "note": f"Opened the Files tab. Use 'Mod Manager Download' and {m.source.upper()} will update it."}
        if not (self._nexus_user or {}).get("is_premium"):
            game.open_uri(files_url)
            if nxm.status()["registered"]:
                return {"ok": True, "note": "Opened the Files tab. Click 'Mod Manager Download' on the file you want "
                                            "and it will be installed here automatically."}
            return {"ok": True, "needs_nxm": True,
                    "note": "Opened the Files tab. Free accounts can't download through the API directly. Turn on "
                            "'Install Mod Manager Downloads' in Settings to update with one click from the website."}
        try:
            self._guard_game_closed()
            client = self._client()
        except RuntimeError as e:
            return _err(str(e))
        upd = self._updates.get(key) or {}
        if upd.get("file_id"):    # the newer version of the exact file that's installed (main or optional)
            return self._download_and_install(mod_id, upd["file_id"], None, None, key)
        latest = client.latest_main_file(mod_id)
        if not latest:
            return _err("No main file found on the mod page. Open it on Nexus to pick a file.")
        return self._download_and_install(mod_id, latest["file_id"], None, None, key)

    def _download_and_install(self, mod_id: int, file_id: int, nkey, expires, key_hint: str | None) -> dict:
        client, gd = self._client(), self.game_dir

        def work(prog, cancelled):
            info = client.file_info(mod_id, file_id) or {}
            links = client.download_links(mod_id, file_id, nkey, expires)
            if not links:
                raise RuntimeError("Nexus returned no download link.")
            name = info.get("file_name") or f"{mod_id}-{file_id}.zip"
            tmpdir = tempfile.mkdtemp(prefix="cp77mlt_dl_")
            tmp = os.path.join(tmpdir, name)
            try:
                nexus.download(links[0]["URI"], tmp, lambda f, msg: prog(f * 0.5, f"Downloading {msg}"), cancelled)
                target = self._mods_by_key.get(key_hint) if key_hint and not key_hint.startswith("core:") else None
                if target is None and not (key_hint or "").startswith("core:"):
                    target = next((x for x in self._mods if x.source == "loose" and x.nexus_id == mod_id), None)
                r = ops.install_archive(gd, tmp, replace=target, progress=lambda f, msg: prog(0.5 + f * 0.5, msg))
                self._remember_install_group(r["installed"])
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
            version = info.get("version") or info.get("mod_version")
            core_name = next((n for n, c in core_mods.CORE.items() if c["nexus_id"] == mod_id), None)
            if core_name:
                self._updates.pop(f"core:{core_name}", None)
                mv = self._cfg.get("manual_versions") or {}
                if version:
                    mv[core_name] = version
                self._cfg.set("manual_versions", mv)
            else:
                self._link_installed(r["installed"], mod_id, file_id, version, "installed")
                for k, u in list(self._updates.items()):
                    if u.get("mod_id") == mod_id:
                        self._updates.pop(k, None)
            self._save_updates()
            with self._scan_lock:
                self._rescan()
            return {**r, "name": info.get("name") or name, "version": version}
        return self._task("update", work)

    def _github_install(self, key: str) -> dict:
        m = self._mods_by_key.get(key)
        gl = (self._cfg.get("github_links") or {}).get(key)
        if not m or not gl:
            return _err("This mod isn't linked to GitHub.")
        try:
            self._guard_game_closed()
            rel = self._gh.latest(gl["repo"])
        except (RuntimeError, github.GitHubError) as e:
            return _err(str(e))
        asset = github.pick_asset(rel or {}, m.name)
        if not asset:
            game.open_uri((rel or {}).get("html_url") or f"https://github.com/{gl['repo']}/releases")
            return {"ok": True, "note": "This release has no .zip/.7z download to install automatically. Opened the release page."}
        gd = self.game_dir

        def work(prog, cancelled):
            tmpdir = tempfile.mkdtemp(prefix="cp77mlt_gh_")
            tmp = os.path.join(tmpdir, asset["name"])
            try:
                nexus.download(asset["browser_download_url"], tmp, lambda f, msg: prog(f * 0.5, f"Downloading {msg}"), cancelled)
                r = ops.install_archive(gd, tmp, replace=m if m.source == "loose" else None,
                                        progress=lambda f, msg: prog(0.5 + f * 0.5, msg))
                self._remember_install_group(r["installed"])
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
            version = github.version_of(rel)
            gl2 = self._cfg.get("github_links") or {}
            gl2[key] = {**gl2.get(key, gl), "version": version}
            self._cfg.set("github_links", gl2)
            self._updates.pop(key, None)
            self._save_updates()
            with self._scan_lock:
                self._rescan()
            return {**r, "name": m.name, "version": version}
        return self._task("update", work)

    def _process_inbox(self) -> None:
        for url in nxm.take_all():
            p = nexus.parse_nxm(url)
            if not p:
                continue
            if p["game"] != nexus.GAME:
                nxm.forward(url, self._cfg.get("nxm_previous_handler"))
                continue
            if not self._nexus:
                self._nxm_errors.append("A Mod Manager Download arrived, but you're not connected to Nexus. "
                                        "Connect on the Nexus Mods page and click it again.")
                continue
            if self._proc.game_running():
                self._nxm_errors.append("Close Cyberpunk 2077, then click Mod Manager Download again.")
                continue
            r = self._download_and_install(p["mod_id"], p["file_id"], p["key"], p["expires"], None)
            if r.get("task"):
                self._nxm_pending.append(r["task"])

    def _drain_nxm_tasks(self) -> dict:
        out = {"tasks": self._nxm_pending[:], "errors": self._nxm_errors[:]}
        self._nxm_pending.clear()
        self._nxm_errors.clear()
        return out

    # ------------------------------------------------------------- browse Nexus
    @staticmethod
    def _card(d: dict) -> dict:
        return {k: d.get(k) for k in ("mod_id", "name", "summary", "picture_url", "author", "version",
                                      "endorsement_count", "updated_timestamp", "contains_adult_content",
                                      "category_id")}

    def nexus_browse(self, kind: str = "trending", term: str = "", offset: int = 0, count: int = 12) -> dict:
        """Mod cards for the Browse page: a Nexus feed, or a search."""
        try:
            client = self._client()
        except RuntimeError as e:
            return _err(str(e))
        try:
            if kind == "search":
                term = (term or "").strip()
                mid = nexus.parse_mod_id(term)
                if mid and ("nexusmods.com" in term or term.isdigit()):
                    ids = [mid]
                else:
                    cat = self._catalog()
                    live = []
                    try:
                        live = client.any_search(term) if term else []
                        cat.add(live)
                    except nexus.NexusError:
                        pass
                    ranked = identify.merge_ranked(term, cat.search(term, top=60), live, top=60) if term else []
                    ids = [x["mod_id"] for x in ranked][offset:offset + count]
                mods = self._fetch_mods(client, ids)
            else:
                mods, more = None, False
                if kind == "trending":   # published in the last 7 days, most endorsed first
                    try:
                        ranked = client.trending(days=7)
                        page = ranked[offset:offset + count]
                        cards = [x["card"] for x in page if x.get("card")]
                        mods = cards if len(cards) == len(page) else self._fetch_mods(client, [x["mod_id"] for x in page])
                        more = offset + count < len(ranked)
                    except nexus.NexusError:
                        mods = None
                elif kind in ("latest_added", "latest_updated"):
                    try:   # sorted listing with paging; falls back to Nexus's 10-item feed
                        ids = client.sorted_ids("createdAt" if kind == "latest_added" else "updatedAt", offset, count)
                        mods = self._fetch_mods(client, ids)
                        more = len(ids) == count
                    except nexus.NexusError:
                        mods = None
                if mods is None:
                    mods = client.feed(kind) if offset == 0 else []
        except nexus.NexusError as e:
            return _err(str(e))
        installed = {m.nexus_id: m.key for m in self._mods if m.nexus_id}
        cards = []
        for d in mods:
            if d.get("status") not in (None, "published"):
                continue
            c = self._card(d)
            c["installed_key"] = installed.get(d.get("mod_id"))
            c["tracked"] = (d.get("mod_id") in self._tracked) if self._tracked is not None else None
            cards.append(c)
        if kind == "search":
            more = len(cards) >= count and offset + count < 60
        return {"ok": True, "mods": cards, "more": bool(more)}

    @staticmethod
    def _fetch_mods(client, ids: list[int]) -> list[dict]:
        """Mod details for a list of IDs (parallel, cached), each tagged with the ID we asked for."""
        from concurrent.futures import ThreadPoolExecutor

        def one(i):
            try:
                d = client.mod(i)
            except nexus.NexusError:
                return None
            return {**d, "mod_id": d.get("mod_id") or i} if d else None
        with ThreadPoolExecutor(max_workers=6) as pool:
            return [d for d in pool.map(one, list(dict.fromkeys(ids))) if d]

    def nexus_mod_page(self, mod_id: int) -> dict:
        """Details + downloadable files for the Browse detail view."""
        try:
            client = self._client()
            d = client.mod(int(mod_id)) or {}
            files = (client.files(int(mod_id), ttl=1800) or {}).get("files", [])
        except (RuntimeError, nexus.NexusError) as e:
            return _err(str(e))
        keep = [f for f in files if f.get("category_name") in ("MAIN", "OPTIONAL", "UPDATE", "MISCELLANEOUS")]
        keep.sort(key=lambda f: ({"MAIN": 0, "UPDATE": 1, "OPTIONAL": 2}.get(f.get("category_name"), 3),
                                 -(f.get("uploaded_timestamp") or 0)))
        installed_key = next((m.key for m in self._mods if m.nexus_id == int(mod_id)), None)
        return {"ok": True, "mod": {**self._card(d), "description_len": len(d.get("description") or ""),
                                    "url": nexus.mod_url(int(mod_id))},
                "files": [{"file_id": f.get("file_id"), "name": f.get("name") or f.get("file_name"),
                           "version": f.get("version") or f.get("mod_version"), "category": f.get("category_name"),
                           "size_kb": f.get("size_kb") or f.get("size"), "uploaded": f.get("uploaded_timestamp"),
                           "description": re.sub(r"<[^>]+>", "", f.get("description") or "")[:300]} for f in keep[:12]],
                "installed_key": installed_key, "premium": bool((self._nexus_user or {}).get("is_premium")),
                "nxm": nxm.status()["registered"]}

    def nexus_install(self, mod_id: int, file_id: int) -> dict:
        """Install a file from the Browse page. Premium: direct. Free: the file's page (Mod Manager Download)."""
        mod_id, file_id = int(mod_id), int(file_id)
        if not (self._nexus_user or {}).get("is_premium"):
            game.open_uri(f"https://www.nexusmods.com/cyberpunk2077/mods/{mod_id}?tab=files&file_id={file_id}")
            if nxm.status()["registered"]:
                return {"ok": True, "note": "Opened the file on Nexus. Click 'Mod Manager Download' and it installs here."}
            return {"ok": True, "needs_nxm": True, "note": "Opened the file on Nexus. Free accounts can't download through the API."}
        try:
            self._need_game()
            self._guard_game_closed()
        except RuntimeError as e:
            return _err(str(e))
        hint = next((m.key for m in self._mods if m.nexus_id == mod_id and m.source == "loose"), None)
        return self._download_and_install(mod_id, file_id, None, None, hint)

    def open_nexus_window(self, url: str = "") -> dict:
        """Open a Nexus page in the user's default browser."""
        url = url if str(url).startswith("https://www.nexusmods.com/") else "https://www.nexusmods.com/games/cyberpunk2077/mods"
        game.open_uri(url)
        return {"ok": True}

    # ------------------------------------------------------------- backups of replaced files
    def backups_info(self) -> dict:
        if not game.is_valid_game_dir(self.game_dir):
            return {"ok": True, "size": 0, "files": 0, "sets": 0}
        return {"ok": True, **ops.backups_info(self.game_dir)}

    def open_backups(self) -> dict:
        dirs = ops.backup_dirs(self.game_dir)
        return self.open_path(dirs[0]) if dirs else _err("There are no backups yet.")

    def clear_backups(self) -> dict:
        try:
            self._need_game()
        except RuntimeError as e:
            return _err(str(e))
        ops.clear_backups(self.game_dir)
        ops.cleanup_empty_dirs(os.path.join(self.game_dir, TEMP_DISABLED_DIR))
        return {"ok": True}

    # ------------------------------------------------------------- mod backups
    def _backup_dir(self) -> str:
        return self._cfg.get("backup_dir") or backups.default_dir()

    def _backup_state(self, fresh: bool = False) -> dict:
        now = time.monotonic()
        cache = getattr(self, "_bk_cache", None)
        if fresh or not cache or now - cache[0] > 60:
            last = backups.latest(self._backup_dir())
            ts = last["created"] if last else None
            if not ts:
                ts = self._cfg.get("last_backup_ts")
            cache = (now, {"last": ts, "last_kind": last["kind"] if last else None,
                           "schedule": self._cfg.get("backup_schedule") or "off",
                           "running": bool(getattr(self, "_bk_task", None))})
            self._bk_cache = cache
        st = dict(cache[1])
        st["running"] = self._backup_running()
        return st

    def _backup_running(self) -> bool:
        tid = getattr(self, "_bk_task", None)
        return bool(tid and tid in self._tasks and not self._tasks[tid]["done"])

    def _maybe_scheduled_backup(self, running: dict) -> str | None:
        sched = self._cfg.get("backup_schedule") or "off"
        if sched == "off" or self._backup_running() or (running or {}).get("game") or (running or {}).get("launching"):
            return None
        if time.monotonic() - getattr(self, "_bk_checked", 0) < 60:
            return None
        self._bk_checked = time.monotonic()
        if not backups.is_due(sched, self._backup_state(fresh=True)["last"], time.time()):
            return None
        r = self.mod_backup_create("scheduled")
        return r.get("task") if r.get("ok") else None

    def mod_backups_list(self) -> dict:
        folder = self._backup_dir()
        return {"ok": True, "folder": folder, "custom_folder": bool(self._cfg.get("backup_dir")),
                "backups": backups.list_backups(folder), "schedule": self._cfg.get("backup_schedule") or "off",
                "keep": self._cfg.get("backup_keep") or 5, "state": self._backup_state(fresh=True)}

    def mod_backup_create(self, kind: str = "manual") -> dict:
        try:
            self._ensure_scan()
        except RuntimeError as e:
            return _err(str(e))
        if self._backup_running():
            return _err("A backup is already running.")
        gd, folder, mods = self.game_dir, self._backup_dir(), list(self._mods)
        kind = "scheduled" if kind == "scheduled" else "manual"
        keep = int(self._cfg.get("backup_keep") or 5)
        try:
            gv = game.game_version(gd)
        except Exception:
            gv = None

        def work(prog, cancelled):
            r = backups.create(gd, mods, folder, kind, gv, prog, cancelled)
            self._cfg.set("last_backup_ts", r["created"])
            if kind == "scheduled":
                r["pruned"] = len(backups.prune(folder, keep))
            self._bk_cache = None
            log.info("Mod backup (%s) written: %s (%d files)", kind, r["path"], r["files"])
            return r
        r = self._task("backup", work)
        self._bk_task = r.get("task")
        return r

    def mod_backup_restore(self, path: str, overwrite: bool = False) -> dict:
        try:
            self._need_game()
            self._guard_game_closed()
        except RuntimeError as e:
            return _err(str(e))
        if not os.path.isfile(path):
            return _err("That backup file no longer exists.")
        gd = self.game_dir

        def work(prog, _c):
            r = backups.restore(gd, path, bool(overwrite), prog)
            with self._scan_lock:
                self._rescan()
            return r
        return self._task("restore", work)

    def mod_backup_delete(self, path: str) -> dict:
        try:
            backups.delete(self._backup_dir(), path)
        except (ValueError, OSError) as e:
            return _err(str(e))
        self._bk_cache = None
        return {"ok": True}

    def mod_backup_browse_dir(self) -> dict:
        res = self._dialog("folder", title="Where should mod backups be saved?")
        if res:
            self._cfg.set("backup_dir", res)
            self._bk_cache = None
        return {"ok": bool(res), **self.mod_backups_list()}

    def mod_backup_reset_dir(self) -> dict:
        self._cfg.set("backup_dir", "")
        self._bk_cache = None
        return self.mod_backups_list()

    def open_mod_backups(self) -> dict:
        folder = self._backup_dir()
        os.makedirs(folder, exist_ok=True)
        return self.open_path(folder)

    # ------------------------------------------------------------- diagnostics
    def open_debug_log(self) -> dict:
        return self.open_path(os.path.join(app_data_dir(), "cp77mlt.log"))

    # ------------------------------------------------------------- shell
    # Browsers/editors are opened through the shell with a clean environment.
    # os.startfile/webbrowser.open would make them children of this process and,
    # in the onefile build, hand them our _MEI DLL path (same bug as the game launch).
    def open_url(self, url: str) -> dict:
        if not str(url).startswith(("https://", "http://")):
            return _err("Only web links can be opened.")
        game.open_uri(url)
        return {"ok": True}

    def open_path(self, path: str) -> dict:
        if not os.path.exists(path):
            return _err("That file or folder no longer exists.")
        try:
            game.open_uri(os.path.normpath(path))
            return {"ok": True}
        except OSError as e:
            return _err(str(e))

    def open_game_folder(self, sub: str = "") -> dict:
        p = os.path.join(self.game_dir, *[s for s in sub.split("/") if s])
        return self.open_path(p) if os.path.exists(p) else _err("Folder doesn't exist yet.")

    def _dialog(self, kind: str, title: str = "", file_types=None, save_filename: str = "", directory: str | None = None):
        if not self._window:
            return None
        import webview
        fd = getattr(webview, "FileDialog", None)
        mode = {"folder": fd.FOLDER if fd else webview.FOLDER_DIALOG,
                "open": fd.OPEN if fd else webview.OPEN_DIALOG,
                "save": fd.SAVE if fd else webview.SAVE_DIALOG}[kind]
        kw = {"directory": directory or self.game_dir or ""}
        if file_types:
            kw["file_types"] = tuple(file_types)
        if kind == "save":
            kw["save_filename"] = save_filename
        res = self._window.create_file_dialog(mode, **kw)
        if not res:
            return None
        return res if isinstance(res, str) else res[0]
