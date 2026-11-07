"""Nexus Mods API (v1 REST) client.

Login options:
* Personal API key from https://next.nexusmods.com/settings/api-keys (works today).
* Nexus SSO ("Log in with Nexus" in the browser). This needs an application
  slug that Nexus issues to registered apps; set NEXUS_APP_SLUG once you have
  one and the SSO button appears in the UI.

Free accounts can identify, track and check for updates. Downloading files
through the API is a Nexus Premium feature; free users are sent to the
Files tab instead (Vortex/MO2 handle the "Mod Manager Download" button).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import uuid

import requests

from . import APP_NAME, APP_VERSION

API = "https://api.nexusmods.com/v1"
GRAPHQL = "https://api.nexusmods.com/v2/graphql"
LEGACY_SEARCH = "https://search.nexusmods.com/mods"
GAME_NUMERIC_ID = 3333  # Nexus game id for cyberpunk2077 (used by the website search and file previews)
GAME = "cyberpunk2077"
NEXUS_APP_SLUG: str | None = None  # e.g. "cp77mlt" once registered with Nexus
API_KEY_PAGE = "https://next.nexusmods.com/settings/api-keys"


class NexusError(Exception):
    pass


# Identifies the app on every request, as the Nexus API Acceptable Use Policy asks. Requests to
# hosts other than the API (website search, file previews, downloads) get these but never the key.
APP_HEADERS = {
    "Application-Name": APP_NAME,
    "Application-Version": APP_VERSION,
    "User-Agent": f"{APP_NAME.replace(' ', '')}/{APP_VERSION}",
}


class NexusClient:
    def __init__(self, api_key: str, cache_path: str | None = None):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "apikey": api_key,
            **APP_HEADERS,
            "Accept": "application/json",
        })
        self.rate = {"daily": None, "hourly": None}
        self.cache_path = cache_path
        self._cache_lock = threading.Lock()
        self._cache = self._load_cache()

    # -- plumbing ---------------------------------------------------------------
    def _load_cache(self) -> dict:
        if self.cache_path and os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, ValueError):
                pass
        return {}

    def _save_cache(self) -> None:
        if not self.cache_path:
            return
        with self._cache_lock:
            tmp = self.cache_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._cache, f)
            os.replace(tmp, self.cache_path)

    def _req(self, method: str, path: str, **kw):
        try:
            r = self.session.request(method, API + path, timeout=20, **kw)
        except requests.RequestException as e:
            raise NexusError(f"Could not reach Nexus Mods: {e}") from e
        for hdr, key in (("X-RL-Daily-Remaining", "daily"), ("X-RL-Hourly-Remaining", "hourly")):
            if hdr in r.headers:
                try:
                    self.rate[key] = int(r.headers[hdr])
                except ValueError:
                    pass
        if r.status_code == 401:
            raise NexusError("Nexus rejected the API key. Log in again.")
        if r.status_code == 403:
            raise NexusError("Nexus refused this request (Premium may be required).")
        if r.status_code == 404:
            return None
        if r.status_code == 429:
            raise NexusError("Nexus API rate limit reached. Try again later.")
        if r.status_code >= 400:
            raise NexusError(f"Nexus API error {r.status_code}: {r.text[:200]}")
        if not r.content:
            return {}
        try:
            return r.json()
        except ValueError:
            return {}

    def _cached(self, key: str, ttl: int, fetch):
        now = time.time()
        with self._cache_lock:
            hit = self._cache.get(key)
        if hit and now - hit["t"] < ttl:
            return hit["v"]
        val = fetch()
        with self._cache_lock:
            self._cache[key] = {"t": now, "v": val}
        self._save_cache()
        return val

    # -- endpoints ------------------------------------------------------------
    def validate(self) -> dict:
        data = self._req("GET", "/users/validate.json")
        if not data:
            raise NexusError("API key could not be validated.")
        return {"name": data.get("name"), "user_id": data.get("user_id"),
                "is_premium": bool(data.get("is_premium")), "is_supporter": bool(data.get("is_supporter")),
                "avatar": data.get("profile_url")}

    def mod(self, mod_id: int, ttl: int = 3600) -> dict | None:
        return self._cached(f"mod:{mod_id}", ttl, lambda: self._req("GET", f"/games/{GAME}/mods/{mod_id}.json"))

    def files(self, mod_id: int, ttl: int = 3600) -> dict | None:
        return self._cached(f"files:{mod_id}", ttl,
                            lambda: self._req("GET", f"/games/{GAME}/mods/{mod_id}/files.json"))

    def md5_search(self, md5: str) -> list:
        return self._cached(f"md5:{md5}", 30 * 86400,
                            lambda: self._req("GET", f"/games/{GAME}/mods/md5_search/{md5}.json") or [])

    def tracked(self) -> list[dict]:
        data = self._req("GET", "/user/tracked_mods.json") or []
        return [d for d in data if d.get("domain_name") == GAME]

    def track(self, mod_id: int) -> None:
        self._req("POST", "/user/tracked_mods.json", params={"domain_name": GAME}, data={"mod_id": mod_id})

    def untrack(self, mod_id: int) -> None:
        self._req("DELETE", "/user/tracked_mods.json", params={"domain_name": GAME}, data={"mod_id": mod_id})

    def updated(self, period: str = "1m") -> list[dict]:
        return self._cached(f"updated:{period}", 900,
                            lambda: self._req("GET", f"/games/{GAME}/mods/updated.json", params={"period": period}) or [])

    def download_links(self, mod_id: int, file_id: int, key: str | None = None,
                       expires: int | None = None) -> list[dict]:
        """Premium: no key needed. Free accounts: key/expires from an nxm:// link."""
        params = {"key": key, "expires": expires} if key else None
        data = self._req("GET", f"/games/{GAME}/mods/{mod_id}/files/{file_id}/download_link.json", params=params)
        return data or []

    def file_info(self, mod_id: int, file_id: int) -> dict | None:
        for f in (self.files(mod_id) or {}).get("files", []):
            if f.get("file_id") == file_id:
                return f
        return None

    # v2 GraphQL name search. The schema is undocumented and has changed shape over time,
    # so try the known filter syntaxes and remember whichever one the server accepts.
    _SEARCH_VARIANTS = [
        "filter: { gameDomainName: [{ value: $g, op: EQUALS }], name: [{ value: $t, op: WILDCARD }] }",
        "filter: { gameDomain: { value: $g, op: EQUALS }, name: { value: $t, op: WILDCARD } }",
        "filter: { gameDomainName: [{ value: $g, op: EQUALS }], nameStemmed: [{ value: $t, op: MATCHES }] }",
    ]
    _search_variant: int | None = None

    def search(self, term: str, count: int = 10) -> list[dict]:
        def run(idx: int):
            q = ("query Search($g: String!, $t: String!) { mods(" + self._SEARCH_VARIANTS[idx]
                 + f", count: {count}) {{ nodes {{ modId name version updatedAt }} }} }}")
            wildcard = f"*{term}*" if "WILDCARD" in self._SEARCH_VARIANTS[idx] else term
            try:
                r = self.session.post(GRAPHQL, json={"query": q, "variables": {"g": GAME, "t": wildcard}}, timeout=20)
            except requests.RequestException as e:
                raise NexusError(f"Could not reach Nexus Mods: {e}") from e
            if r.status_code == 429:
                raise NexusError("Nexus API rate limit reached. Try again later.")
            try:
                body = r.json()
            except ValueError:
                return None
            nodes = ((body.get("data") or {}).get("mods") or {}).get("nodes")
            if body.get("errors") or nodes is None:
                return None
            return [{"mod_id": n.get("modId"), "name": n.get("name"), "version": n.get("version")}
                    for n in nodes if n.get("modId")]

        def cached():
            order = [self._search_variant] if self._search_variant is not None else []
            order += [i for i in range(len(self._SEARCH_VARIANTS)) if i not in order]
            for idx in order:
                res = run(idx)
                if res is not None:
                    NexusClient._search_variant = idx
                    return res
            raise NexusError("Nexus name search is unavailable right now.")
        return self._cached(f"search:{term.lower()}", 7 * 86400, cached)

    # -- catalog: every Cyberpunk mod's id + name, for local fuzzy matching --------------
    _CATALOG_FILTERS = [
        "filter: { gameDomainName: [{ value: $g, op: EQUALS }] }",
        "filter: { gameDomain: { value: $g, op: EQUALS } }",
    ]

    _CATALOG_SORTS = ["", "sort: [{ createdAt: { direction: ASC } }]", "sort: [{ createdAt: { direction: DESC } }]",
                      "sort: [{ updatedAt: { direction: DESC } }]", "sort: [{ endorsements: { direction: DESC } }]"]

    def _catalog_pass(self, filt: str, sort: str, page_size: int, progress, cancelled, base: int, total_hint):
        out, offset, total = {}, 0, None
        while True:
            if cancelled():
                raise InterruptedError
            args = filt + (", " + sort if sort else "")
            q = ("query Cat($g: String!, $o: Int!) { mods(" + args +
                 f", count: {page_size}, offset: $o) {{ totalCount nodes {{ modId name version }} }} }}")
            r = self.session.post(GRAPHQL, json={"query": q, "variables": {"g": GAME, "o": offset}}, timeout=30)
            body = r.json()
            mods = (body.get("data") or {}).get("mods")
            if body.get("errors") or not mods:
                if out:          # e.g. the server's paging window ends (often at 10,000 results)
                    return out, total
                raise NexusError(str(body.get("errors") or "no data")[:200])
            nodes = mods.get("nodes") or []
            total = mods.get("totalCount") or total
            for n in nodes:
                if n.get("modId"):
                    out[n["modId"]] = {"mod_id": n["modId"], "name": n.get("name") or "", "version": n.get("version")}
            offset += len(nodes)
            if progress and (total or total_hint):
                t = total or total_hint
                progress(min((base + len(out)) / t, 1.0), f"Downloading the Nexus mod list ({base + len(out):,} of {t:,})")
            if not nodes or (total and offset >= total):
                return out, total

    def catalog(self, progress=None, cancelled=lambda: False, page_size: int = 100) -> list[dict]:
        """All mods for the game via GraphQL (paged). Doesn't use the v1 request quota.

        Offset paging over a shifting order can repeat some mods and skip others, and the server
        may stop paging at a fixed window. So results are de-duplicated by ID, and if fewer mods
        came back than Nexus reports, extra passes in other sort orders fill the gaps."""
        last_err = None
        for filt in self._CATALOG_FILTERS:
            merged: dict[int, dict] = {}
            total = None
            try:
                for sort in self._CATALOG_SORTS:
                    try:
                        got, t = self._catalog_pass(filt, sort, page_size, progress, cancelled, 0, total)
                    except NexusError:
                        if not sort:
                            raise       # the base query itself failed: try the next filter syntax
                        continue        # this sort isn't supported: try the next one
                    total = total or t
                    merged.update(got)
                    if total and len(merged) >= total:
                        break
                return list(merged.values())
            except InterruptedError:
                raise
            except (requests.RequestException, ValueError, NexusError) as e:
                last_err = e
                continue
        raise NexusError(f"Couldn't download the Nexus mod list: {last_err}")

    def sorted_ids(self, field: str, offset: int, count: int) -> list[int]:
        """Mod IDs newest-first by createdAt/updatedAt, for paged New / Recently updated lists."""
        def fetch():
            for filt in self._CATALOG_FILTERS:
                q = ("query L($g: String!, $o: Int!) { mods(" + filt + f", sort: [{{ {field}: {{ direction: DESC }} }}]"
                     + f", count: {count}, offset: $o) {{ nodes {{ modId }} }} }}")
                try:
                    r = self.session.post(GRAPHQL, json={"query": q, "variables": {"g": GAME, "o": offset}}, timeout=20)
                    body = r.json()
                except (requests.RequestException, ValueError):
                    continue
                nodes = ((body.get("data") or {}).get("mods") or {}).get("nodes")
                if nodes is not None and not body.get("errors"):
                    return [n["modId"] for n in nodes if n.get("modId")]
            raise NexusError("Paged listing unavailable.")
        return self._cached(f"sorted:{field}:{offset}:{count}", 600, fetch)

    def legacy_search(self, term: str) -> list[dict]:
        """The website's search endpoint; fallback when GraphQL search is unavailable."""
        def fetch():
            try:
                r = requests.get(LEGACY_SEARCH, params={"terms": term, "game_id": GAME_NUMERIC_ID, "include_adult": 1,
                                                        "blocked_tags": "", "blocked_authors": ""},
                                 headers=APP_HEADERS, timeout=20)
                data = r.json()
            except (requests.RequestException, ValueError):
                return []
            return [{"mod_id": int(x["mod_id"]), "name": x.get("name", ""), "version": None}
                    for x in data.get("results", []) if x.get("mod_id")]
        return self._cached(f"lsearch:{term.lower()}", 7 * 86400, fetch)

    def any_search(self, term: str) -> list[dict]:
        res = []
        try:
            res = self.search(term, count=20)
        except NexusError:
            pass
        if not res:
            res = self.legacy_search(term)
        seen, out = set(), []
        for r in res:
            if r["mod_id"] not in seen:
                seen.add(r["mod_id"])
                out.append(r)
        return out

    def content_preview(self, url: str) -> list[tuple[str, int | None]]:
        """File list of an uploaded archive from Nexus's content preview (CDN, no API quota)."""
        def fetch():
            try:
                r = requests.get(url, headers=APP_HEADERS, timeout=20)
                if r.status_code != 200:
                    return []
                tree = r.json()
            except (requests.RequestException, ValueError):
                return []
            out = []

            def walk(node):
                for ch in node.get("children", []) or []:
                    if ch.get("type") == "directory" or ch.get("children"):
                        walk(ch)
                    else:
                        out.append([ch.get("path") or ch.get("name") or "", parse_size(ch.get("size"))])
            walk(tree if isinstance(tree, dict) else {"children": tree})
            return out
        return [tuple(x) for x in self._cached(f"preview:{url}", 90 * 86400, fetch)]

    def estimate_installed(self, mod_id: int, installed_mtime: float) -> dict | None:
        """Guess which file version is installed from file timestamps.

        Archives keep their files' modification times, so installed files are
        dated at or slightly before the upload they came from. Pick the newest
        upload that isn't more than a day older than the newest installed file.
        """
        if not installed_mtime:
            return None
        files = [f for f in (self.files(mod_id) or {}).get("files", [])
                 if f.get("category_name") in ("MAIN", "UPDATE", "OLD_VERSION") and f.get("uploaded_timestamp")]
        if not files:
            return None
        files.sort(key=lambda f: f["uploaded_timestamp"])
        candidates = [f for f in files if f["uploaded_timestamp"] <= installed_mtime + 86400 * 2]
        # files modified before upload by more than ~180 days are probably re-saved/untrustworthy
        pick = candidates[-1] if candidates else None
        if pick and installed_mtime - pick["uploaded_timestamp"] > 400 * 86400:
            return None
        return pick

    def feed(self, kind: str) -> list[dict]:
        """trending | latest_added | latest_updated (10 mods each, with pictures and summaries)."""
        if kind not in ("trending", "latest_added", "latest_updated"):
            raise NexusError("Unknown list.")
        return self._cached(f"feed:{kind}", 600, lambda: self._req("GET", f"/games/{GAME}/mods/{kind}.json") or [])

    def latest_main_file(self, mod_id: int) -> dict | None:
        data = self.files(mod_id) or {}
        files = data.get("files", [])
        main = [f for f in files if f.get("category_name") == "MAIN"] or \
               [f for f in files if f.get("category_name") not in ("OLD_VERSION", "ARCHIVED", "DELETED")]
        return max(main, key=lambda f: f.get("uploaded_timestamp", 0)) if main else None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def parse_size(v) -> int | None:
    """'8.86 kB' / '12.3 MB' / 12345 -> bytes."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v)
    m = re.match(r"\s*([\d.,]+)\s*([kKmMgG]?i?[bB])?", str(v))
    if not m:
        return None
    num = float(m.group(1).replace(",", ""))
    unit = (m.group(2) or "b").lower()[0]
    return int(num * {"b": 1, "k": 1024, "m": 1024 ** 2, "g": 1024 ** 3}[unit])


def parse_nxm(url: str) -> dict | None:
    """nxm://cyberpunk2077/mods/4198/files/123456?key=..&expires=..&user_id=.."""
    from urllib.parse import parse_qs, urlparse
    try:
        u = urlparse(url)
    except ValueError:
        return None
    if u.scheme.lower() != "nxm":
        return None
    parts = [p for p in u.path.split("/") if p]
    if len(parts) < 4 or parts[0] != "mods" or parts[2] != "files":
        return None
    q = parse_qs(u.query)
    try:
        return {"game": u.netloc.lower(), "mod_id": int(parts[1]), "file_id": int(parts[3]),
                "key": (q.get("key") or [None])[0], "expires": int((q.get("expires") or [0])[0]) or None,
                "user_id": (q.get("user_id") or [None])[0]}
    except ValueError:
        return None


def mod_url(mod_id: int, tab: str | None = None) -> str:
    return f"https://www.nexusmods.com/{GAME}/mods/{mod_id}" + (f"?tab={tab}" if tab else "")


def parse_mod_id(text: str) -> int | None:
    text = (text or "").strip()
    m = re.search(r"nexusmods\.com/(?:games/)?cyberpunk2077/mods/(\d+)", text, re.I)
    if m:
        return int(m.group(1))
    return int(text) if text.isdigit() else None


def _vtuple(v: str) -> tuple:
    parts = re.findall(r"\d+|[a-zA-Z]+", (v or "").lstrip("vV"))
    return tuple((0, int(p)) if p.isdigit() else (-1, p.lower()) for p in parts)


def version_newer(latest: str | None, installed: str | None) -> bool | None:
    """True if latest > installed, False if not, None if unknown."""
    if not latest or not installed:
        return None
    a, b = _vtuple(latest), _vtuple(installed)
    if not a or not b:
        return None if latest.strip() == installed.strip() else True
    # pad numerically so 1.2 == 1.2.0
    n = max(len(a), len(b))
    a += ((0, 0),) * (n - len(a))
    b += ((0, 0),) * (n - len(b))
    return a > b


def md5_file(path: str, cache: dict | None = None) -> str:
    st = os.stat(path)
    key = f"{path}|{st.st_size}|{st.st_mtime_ns}"
    if cache is not None and key in cache:
        return cache[key]
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    digest = h.hexdigest()
    if cache is not None:
        cache[key] = digest
    return digest


def sso_login(open_browser, timeout: float = 300.0) -> str:
    """Nexus SSO over websocket. Requires NEXUS_APP_SLUG. Returns the API key."""
    if not NEXUS_APP_SLUG:
        raise NexusError("SSO is not configured for this build.")
    try:
        import websocket  # websocket-client
    except ImportError as e:
        raise NexusError("websocket-client is not installed.") from e
    ws = websocket.create_connection("wss://sso.nexusmods.com", timeout=timeout)
    try:
        req_id = str(uuid.uuid4())
        ws.send(json.dumps({"id": req_id, "token": None, "protocol": 2}))
        open_browser(f"https://www.nexusmods.com/sso?id={req_id}&application={NEXUS_APP_SLUG}")
        deadline = time.time() + timeout
        while time.time() < deadline:
            msg = json.loads(ws.recv())
            if not msg.get("success"):
                raise NexusError(msg.get("error") or "SSO failed.")
            key = (msg.get("data") or {}).get("api_key")
            if key:
                return key
        raise NexusError("Timed out waiting for Nexus login.")
    finally:
        ws.close()


def download(url: str, dest: str, progress=None, cancelled=lambda: False) -> str:
    with requests.get(url, stream=True, timeout=60, headers=APP_HEADERS) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0))
        done = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                if cancelled():
                    raise InterruptedError
                f.write(chunk)
                done += len(chunk)
                if progress and total:
                    progress(done / total, f"{done / 1e6:.1f} / {total / 1e6:.1f} MB")
    return dest
