"""Cyberpunk 2077 Mod List Tool - entry point.

Run with:  pythonw Cyberpunk2077ModListTool.pyw
Build with: pyinstaller Cyberpunk2077ModListTool.spec
"""
from __future__ import annotations

import os
import sys

from cp77mlt import APP_NAME, APP_VERSION
from cp77mlt.api import Api

if getattr(sys, "frozen", False):
    BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

WEB_INDEX = os.path.join(BASE_DIR, "cp77mlt", "web", "index.html")
ICON_PATH = os.path.join(BASE_DIR, "Cyberpunk 2077 Mod List Tool.ico")
MUTEX_NAME = "Local\\Cyberpunk2077ModListTool.SingleInstance"


def acquire_single_instance():
    """Named mutex instead of v2's lock file in %TEMP% (which could go stale)."""
    if sys.platform != "win32":
        return True
    import ctypes
    k32 = ctypes.windll.kernel32
    handle = k32.CreateMutexW(None, False, MUTEX_NAME)
    if k32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS -> focus the running window
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, APP_NAME)
        if hwnd:
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
        return False
    return handle  # keep a reference for the process lifetime


def setup_logging() -> None:
    import logging
    from logging.handlers import RotatingFileHandler
    from cp77mlt.config import app_data_dir
    h = RotatingFileHandler(os.path.join(app_data_dir(), "cp77mlt.log"), maxBytes=512 * 1024, backupCount=2,
                            encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger("cp77mlt")
    root.setLevel(logging.INFO)
    root.addHandler(h)
    root.info("Starting %s v%s", APP_NAME, APP_VERSION)


def main() -> int:
    # Run by the uninstaller: give nxm:// links back to the previous handler (Vortex, MO2, ...)
    if "--unregister-nxm" in sys.argv:
        from cp77mlt import nxm
        from cp77mlt.config import Config
        try:
            if nxm.status()["registered"]:
                nxm.unregister(Config())
        except Exception:
            pass
        return 0
    # Started by the browser for a Nexus "Mod Manager Download" link: queue it for the running app
    nxm_links = [a for a in sys.argv[1:] if a.lower().startswith("nxm://")]
    if nxm_links:
        from cp77mlt import nxm
        for url in nxm_links:
            nxm.drop(url)
    mutex = acquire_single_instance()
    if not mutex:
        return 0
    setup_logging()

    import webview

    from cp77mlt import winstate

    api = Api()
    try:
        from cp77mlt import nxm
        nxm.refresh_path(api._cfg)
    except Exception:
        pass
    geo = winstate.initial(api._cfg.get("window"))  # reopen where it was last closed
    window = webview.create_window(
        APP_NAME, url=WEB_INDEX, js_api=api, min_size=(winstate.MIN_W, winstate.MIN_H),
        background_color="#08080A", text_select=False, **geo,
    )
    api.attach(window)
    winstate.Tracker(api._cfg, window, geo)
    debug = "--debug" in sys.argv
    kwargs = {"debug": debug, "private_mode": False,
              "storage_path": os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                                           "Cyberpunk2077ModListTool", "webview")}
    if os.path.exists(ICON_PATH):
        kwargs["icon"] = ICON_PATH
    try:
        webview.start(**kwargs)
    except TypeError:  # older pywebview without icon/storage_path
        webview.start(debug=debug)
    return 0


if __name__ == "__main__":
    print(f"{APP_NAME} v{APP_VERSION}")
    sys.exit(main())
