"""Works out whether a Nexus failure is on Nexus's side or the user's, so the UI can say so.

Two sources feed it:
  * Nexus's public status page (Atlassian Statuspage), polled in the background.
  * What the app itself sees. The status page is updated by hand and covers the CDN as a whole,
    so a single dead download node (e.g. la-premium.nexus-cdn.com refusing connections) often
    never shows up there. When a Nexus host fails, we probe a neutral site: if the internet
    works, the problem is Nexus's; if not, it's the user's connection. A host that resolves to
    0.0.0.0 / 127.x is being blocked by a local DNS filter (Pi-hole, AdGuard, hosts file).
"""
from __future__ import annotations

import ipaddress
import socket
import threading
import time
from urllib.parse import urlparse

import requests

STATUS_PAGE = "https://nexusmods.statuspage.io"
STATUS_API = STATUS_PAGE + "/api/v2/summary.json"
# Neutral hosts used only to answer "is the internet up?". Windows' own connectivity check first.
PROBES = ("http://www.msftconnecttest.com/connecttest.txt", "https://www.google.com/generate_204",
          "https://1.1.1.1/")
STATUS_TTL = 300        # seconds between status-page polls
INCIDENT_TTL = 15 * 60  # how long an app-observed failure stays on screen without a newer one

_SEVERITY = {"operational": 0, "under_maintenance": 1, "degraded_performance": 2,
             "partial_outage": 3, "major_outage": 4}
_STATUS_WORDS = {"degraded_performance": "degraded performance", "partial_outage": "partial outage",
                 "major_outage": "major outage", "under_maintenance": "maintenance"}


class NexusServiceError(RuntimeError):
    """A failure with a plain-language diagnosis attached. str() is the user-facing message."""

    def __init__(self, diagnosis: dict):
        self.diagnosis = diagnosis
        super().__init__(diagnosis["message"])


def host_of(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


_probe_cache = {"t": 0.0, "ok": True}


def internet_ok(timeout: float = 4.0) -> bool:
    """Is the internet reachable at all? Cached for 30 s so a burst of failures probes once."""
    if time.time() - _probe_cache["t"] < 30:
        return _probe_cache["ok"]
    ok = False
    for url in PROBES:
        try:
            requests.head(url, timeout=timeout, allow_redirects=False)
            ok = True
            break
        except requests.RequestException:
            continue
    _probe_cache.update(t=time.time(), ok=ok)
    return ok


def sinkholed(host: str) -> bool:
    """True when DNS answers with a 'blocked' address (0.0.0.0, loopback) instead of a real one."""
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except OSError:
        return False
    addrs = {ipaddress.ip_address(i[4][0].split("%")[0]) for i in infos}
    return bool(addrs) and all(a.is_unspecified or a.is_loopback for a in addrs)


def _is_dns_failure(exc: BaseException) -> bool:
    text = repr(exc).lower()
    return any(s in text for s in ("getaddrinfo failed", "name or service not known", "failed to resolve",
                                    "nodename nor servname", "temporary failure in name resolution",
                                    "nameresolutionerror"))


def _short_reason(exc: BaseException | None, status: int | None) -> str:
    if status:
        return f"HTTP {status}"
    text = repr(exc).lower()
    if "10061" in text or "refused" in text:
        return "connection refused"
    if isinstance(exc, requests.Timeout) or "timed out" in text:
        return "timed out"
    if isinstance(exc, requests.exceptions.SSLError):
        return "secure connection failed"
    if "10054" in text or "reset" in text:
        return "connection reset"
    return exc.__class__.__name__ if exc else "error"


def diagnose(url: str, exc: BaseException | None = None, status: int | None = None,
             what: str = "Nexus Mods", probe=internet_ok, sinkhole=sinkholed, plural: bool = False) -> dict:
    """Classify one failed request. `where` is 'nexus', 'local' or 'offline'."""
    host = host_of(url)
    is_, isnt = ("are", "aren't") if plural else ("is", "isn't")
    reason = _short_reason(exc, status)
    base = {"host": host, "reason": reason, "time": time.time()}
    if status and status >= 500:
        return {**base, "where": "nexus", "title": f"{what} {is_} having problems",
                "message": f"{what} returned an error ({host}: HTTP {status}). This is a problem on Nexus's end, "
                           "not your PC. Try again in a little while."}
    if host and sinkhole(host):
        return {**base, "where": "local", "title": f"{host} is blocked on this PC",
                "message": f"{host} is being blocked by a DNS filter on your network (Pi-hole, AdGuard, a VPN's "
                           "ad blocker or your hosts file). Allow nexus-cdn.com and nexusmods.com there."}
    if not probe():
        return {**base, "where": "offline", "title": "No internet connection",
                "message": f"Couldn't reach {what}, and other sites aren't reachable either. "
                           "Check your internet connection."}
    if exc is not None and _is_dns_failure(exc):
        return {**base, "where": "local", "title": f"Couldn't look up {host}",
                "message": f"Your internet works, but your DNS couldn't find {host}. A DNS filter, VPN or your "
                           "router's DNS may be blocking it."}
    return {**base, "where": "nexus", "title": f"{what} {isnt} responding",
            "message": f"{what} {isnt} responding ({host}: {reason}). Your internet connection is working, so this "
                       "is a problem on Nexus's end. Try again in a little while."}


class Health:
    """Thread-safe store of the latest status-page summary and app-observed failures."""

    def __init__(self, fetch=None):
        self._lock = threading.Lock()
        self._status: dict | None = None
        self._status_t = 0.0
        self._incident: dict | None = None
        self._fetch = fetch or self._fetch_status_page
        self._poller: threading.Thread | None = None

    # -- status page ------------------------------------------------------------------
    @staticmethod
    def _fetch_status_page() -> dict | None:
        try:
            r = requests.get(STATUS_API, timeout=10)
            r.raise_for_status()
            data = r.json()
        except (requests.RequestException, ValueError):
            return None
        comps = [{"name": c.get("name", ""), "status": c.get("status", "")}
                 for c in data.get("components") or [] if not c.get("group")]
        incidents = [{"name": i.get("name", ""), "status": i.get("status", ""), "impact": i.get("impact", ""),
                      "url": i.get("shortlink") or STATUS_PAGE, "updated": i.get("updated_at")}
                     for i in data.get("incidents") or [] if i.get("status") not in ("resolved", "postmortem")]
        st = data.get("status") or {}
        return {"indicator": st.get("indicator", "none"), "description": st.get("description", ""),
                "components": comps, "incidents": incidents}

    def refresh(self, force: bool = False) -> None:
        if not force and time.time() - self._status_t < STATUS_TTL:
            return
        s = self._fetch()
        with self._lock:
            self._status_t = time.time()
            if s is not None:
                self._status = s

    def start_polling(self) -> None:
        if self._poller and self._poller.is_alive():
            return

        def loop():
            while True:
                self.refresh(force=True)
                time.sleep(STATUS_TTL)
        self._poller = threading.Thread(target=loop, daemon=True, name="nexus-status")
        self._poller.start()

    # -- app-observed failures -----------------------------------------------------------
    def record_failure(self, diagnosis: dict) -> None:
        with self._lock:
            self._incident = diagnosis

    def record_success(self, host: str = "") -> None:
        """A request to `host` worked; clear an observed failure for that host (any host if blank)."""
        with self._lock:
            if self._incident and (not host or self._incident.get("host") == host
                                   or self._incident.get("where") == "offline"):
                self._incident = None

    # -- what the UI shows -----------------------------------------------------------------
    def snapshot(self) -> dict:
        with self._lock:
            s, inc = self._status, self._incident
        if inc and time.time() - inc["time"] > INCIDENT_TTL:
            inc = None
        bad = [c for c in (s or {}).get("components", []) if _SEVERITY.get(c["status"], 0) > 0]
        worst = max((_SEVERITY.get(c["status"], 0) for c in bad), default=0)
        official = None
        if s and (bad or s["incidents"]):
            official = {"summary": ", ".join(f"{c['name']}: {_STATUS_WORDS.get(c['status'], c['status'])}" for c in bad)
                                   or s["description"],
                        "components": bad, "incidents": s["incidents"]}
        if inc and inc["where"] == "nexus":
            level = "down"
        elif inc:
            level = "local"
        elif worst >= 3 or (s and s["indicator"] in ("major", "critical")):
            level = "down"
        elif official:
            level = "degraded"
        else:
            level = "ok"
        return {"level": level, "observed": inc, "official": official, "status_page": STATUS_PAGE,
                "checked": self._status_t or None}


health = Health()
