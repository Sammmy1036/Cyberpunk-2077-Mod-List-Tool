"""Optional handler for Nexus "Mod Manager Download" (nxm://) links.

Free Nexus accounts can only download through the API with the one-time key in
an nxm:// link, which the website creates when you click "Mod Manager Download".
Registering this tool as the nxm handler lets free users update mods in-app.

* Registration is per-user (HKCU) and remembers the previous handler (Vortex,
  MO2, ...). Links for other games are forwarded to it, and unregistering
  restores it.
* A second instance started by the browser drops the link in an inbox folder,
  focuses the running window and exits; the running instance picks it up.
"""
from __future__ import annotations

import os
import sys
import time
import uuid

from .config import app_data_dir

KEY = r"Software\Classes\nxm"


def inbox_dir() -> str:
    p = os.path.join(app_data_dir(), "nxm_inbox")
    os.makedirs(p, exist_ok=True)
    return p


def drop(url: str) -> None:
    path = os.path.join(inbox_dir(), f"{time.time():.3f}-{uuid.uuid4().hex[:6]}.nxm")
    with open(path, "w", encoding="utf-8") as f:
        f.write(url.strip())


def take_all() -> list[str]:
    out = []
    try:
        names = sorted(os.listdir(inbox_dir()))
    except OSError:
        return out
    for n in names:
        p = os.path.join(inbox_dir(), n)
        try:
            with open(p, "r", encoding="utf-8") as f:
                out.append(f.read().strip())
            os.remove(p)
        except OSError:
            continue
    return out


def own_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" "%1"'
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    script = os.path.abspath(sys.argv[0])
    return f'"{pyw if os.path.exists(pyw) else sys.executable}" "{script}" "%1"'


def _read_command() -> str | None:
    if sys.platform != "win32":
        return None
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY + r"\shell\open\command") as k:
            return winreg.QueryValueEx(k, "")[0]
    except OSError:
        pass
    try:  # machine-wide registration (some Vortex installs)
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"nxm\shell\open\command") as k:
            return winreg.QueryValueEx(k, "")[0]
    except OSError:
        return None


def status() -> dict:
    cmd = _read_command() or ""
    low = cmd.lower()
    owner = ("this tool" if "cyberpunk" in low and "mod list tool" in low or "cyberpunk2077modlisttool" in low
             else "Vortex" if "vortex" in low else "Mod Organizer 2" if "nxmhandler" in low or "modorganizer" in low
             else ("another app" if cmd else None))
    return {"registered": owner == "this tool", "owner": owner, "command": cmd}


def register(cfg) -> dict:
    if sys.platform != "win32":
        return {"ok": False, "error": "nxm links can only be registered on Windows."}
    import winreg
    current = _read_command()
    if current and "cyberpunk" not in current.lower():
        cfg.set("nxm_previous_handler", current)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, KEY) as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "URL:NXM Protocol")
        winreg.SetValueEx(k, "URL Protocol", 0, winreg.REG_SZ, "")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, KEY + r"\shell\open\command") as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, own_command())
    return {"ok": True, **status()}


def unregister(cfg) -> dict:
    if sys.platform != "win32":
        return {"ok": True}
    import winreg
    prev = cfg.get("nxm_previous_handler")
    if prev:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, KEY + r"\shell\open\command") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, prev)
    else:
        for sub in (r"\shell\open\command", r"\shell\open", r"\shell", ""):
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, KEY + sub)
            except OSError:
                pass
    return {"ok": True, **status()}


def refresh_path(cfg) -> bool:
    """If this tool owns nxm:// but the registered exe path is stale (moved, or switched
    from the portable exe to the installed one), point it at the running exe again."""
    if sys.platform != "win32":
        return False
    try:
        if status()["registered"] and (_read_command() or "").lower() != own_command().lower():
            register(cfg)  # keeps the remembered previous handler
            return True
    except OSError:
        pass
    return False


def forward(url: str, previous_command: str | None) -> bool:
    """Hand a non-Cyberpunk link to the handler that owned nxm before us."""
    if not previous_command:
        return False
    import shlex
    from .game import spawn_detached
    cmd = previous_command.replace("%1", url)
    try:
        args = shlex.split(cmd, posix=False)
        args = [a.strip('"') for a in args]
        spawn_detached(args)
        return True
    except (OSError, ValueError):
        return False
