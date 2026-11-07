"""Remember the main window's position, size and maximized state between runs.

pywebview reports and accepts window geometry in logical pixels, so saved values
round-trip on scaled displays. Positions are checked against the connected
monitors after the window opens; if the saved spot is no longer visible (a
monitor was unplugged), the window is centered on the primary screen instead.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

MIN_W, MIN_H = 1100, 700
DEFAULT_W, DEFAULT_H = 1320, 840
OFFSCREEN = -30000  # Windows parks minimized windows at about (-32000, -32000)


def initial(saved: dict | None) -> dict:
    """create_window kwargs from the saved state (x/y only when present and sane)."""
    out = {"width": DEFAULT_W, "height": DEFAULT_H}
    if not isinstance(saved, dict):
        return out
    try:
        w, h = int(saved.get("width") or 0), int(saved.get("height") or 0)
        if MIN_W <= w <= 10000 and MIN_H <= h <= 10000:
            out.update(width=w, height=h)
        x, y = saved.get("x"), saved.get("y")
        if x is not None and y is not None and int(x) > OFFSCREEN and int(y) > OFFSCREEN:
            out.update(x=int(x), y=int(y))
        if saved.get("maximized"):
            out["maximized"] = True
    except (TypeError, ValueError):
        pass
    return out


def visible(x: int, y: int, width: int, screens) -> bool:
    """True when the title bar (a strip near the top-left) sits on some screen."""
    px, py = x + min(120, width // 2), y + 12
    for s in screens or []:
        try:
            if s.x <= px < s.x + s.width and s.y <= py < s.y + s.height:
                return True
        except AttributeError:
            continue
    return False


class Tracker:
    """Follows window events and writes the last normal (un-maximized) bounds to config on close."""

    def __init__(self, cfg, window, start: dict):
        self.cfg, self.window = cfg, window
        self.x, self.y = start.get("x"), start.get("y")
        self.w, self.h = start["width"], start["height"]
        self.maximized = bool(start.get("maximized"))
        self.minimized = False
        ev = window.events
        ev.moved += self._moved
        ev.resized += self._resized
        ev.maximized += self._max
        ev.minimized += self._min
        ev.restored += self._restored
        ev.shown += self._shown
        ev.closing += self.save

    def _normal(self) -> bool:
        return not (self.maximized or self.minimized)

    def _moved(self, x, y, *_):
        if self._normal() and x > OFFSCREEN and y > OFFSCREEN:
            self.x, self.y = int(x), int(y)

    def _resized(self, w, h, *_):
        if self._normal() and w >= MIN_W // 2 and h >= MIN_H // 2:
            self.w, self.h = int(w), int(h)

    def _max(self, *_):
        self.maximized, self.minimized = True, False

    def _min(self, *_):
        self.minimized = True

    def _restored(self, *_):
        if self.minimized:
            self.minimized = False  # back to whatever it was before minimizing
        else:
            self.maximized = False

    def _shown(self, *_):
        if self.x is None or self.maximized:
            return
        try:
            import webview
            screens = webview.screens
        except Exception:
            return
        if screens and not visible(self.x, self.y, self.w, screens):
            s = screens[0]
            nx, ny = s.x + max(0, (s.width - self.w) // 2), s.y + max(0, (s.height - self.h) // 2)
            log.info("Saved window position (%s, %s) is off-screen; centering", self.x, self.y)
            try:
                self.window.move(nx, ny)
                self.x, self.y = nx, ny
            except Exception:
                log.exception("couldn't move window on screen")

    def state(self) -> dict:
        st = {"width": self.w, "height": self.h, "maximized": self.maximized}
        if self.x is not None and self.y is not None:
            st.update(x=self.x, y=self.y)
        return st

    def save(self, *_):
        try:
            self.cfg.set("window", self.state())
        except Exception:
            log.exception("couldn't save window position")
