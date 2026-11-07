"""GitHub-hosted mods (e.g. RedHotTools): link a mod to a repo, check releases, install assets.

Uses the public REST API without a token (60 requests/hour per IP), with
results cached so normal use stays far below that.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time

import requests

from . import APP_NAME, APP_VERSION

API = "https://api.github.com"
_REPO_RE = re.compile(r"github\.com[/:]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?(?:[/?#]|$)", re.I)
_URL_RE = re.compile(rb"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", re.I)
ARCHIVE_EXT = (".zip", ".7z", ".rar")


class GitHubError(Exception):
    pass


def parse_repo(text: str) -> str | None:
    """'https://github.com/psiberx/cp2077-red-hot-tools/releases' or 'owner/repo' -> 'owner/repo'."""
    text = (text or "").strip()
    m = _REPO_RE.search(text)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", text):
        return text
    return None


def repos_in_bytes(data: bytes) -> set[str]:
    out = set()
    for m in _URL_RE.finditer(data):
        owner, repo = m.group(1).decode(), m.group(2).decode().removesuffix(".git")
        if owner.lower() not in ("sponsors", "orgs", "topics", "features") and repo:
            out.add(f"{owner}/{repo}")
    return out


class GitHubClient:
    def __init__(self, cache_path: str | None = None):
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/vnd.github+json",
                                     "User-Agent": f"{APP_NAME.replace(' ', '')}/{APP_VERSION}"})
        self.cache_path = cache_path
        self._lock = threading.Lock()
        self._cache = {}
        if cache_path and os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except (OSError, ValueError):
                self._cache = {}

    def _get(self, path: str, ttl: int):
        now = time.time()
        with self._lock:
            hit = self._cache.get(path)
        if hit and now - hit["t"] < ttl:
            return hit["v"]
        try:
            r = self.session.get(API + path, timeout=20)
        except requests.RequestException as e:
            raise GitHubError(f"Could not reach GitHub: {e}") from e
        if r.status_code == 404:
            val = None
        elif r.status_code == 403 and r.headers.get("X-RateLimit-Remaining") == "0":
            if hit:
                return hit["v"]
            raise GitHubError("GitHub's hourly limit for unauthenticated requests was reached. Try again later.")
        elif r.status_code >= 400:
            raise GitHubError(f"GitHub error {r.status_code}")
        else:
            val = r.json()
        with self._lock:
            self._cache[path] = {"t": now, "v": val}
            if self.cache_path:
                try:
                    tmp = self.cache_path + ".tmp"
                    with open(tmp, "w", encoding="utf-8") as f:
                        json.dump(self._cache, f)
                    os.replace(tmp, self.cache_path)
                except OSError:
                    pass
        return val

    def repo(self, repo: str) -> dict | None:
        d = self._get(f"/repos/{repo}", 86400)
        if not d:
            return None
        return {"repo": d.get("full_name"), "description": d.get("description"), "stars": d.get("stargazers_count"),
                "url": d.get("html_url"), "owner_avatar": (d.get("owner") or {}).get("avatar_url"),
                "updated": d.get("pushed_at")}

    def releases(self, repo: str) -> list[dict]:
        rel = self._get(f"/repos/{repo}/releases?per_page=30", 3600) or []
        return [r for r in rel if not r.get("draft")]

    def latest(self, repo: str) -> dict | None:
        rels = [r for r in self.releases(repo) if not r.get("prerelease")] or self.releases(repo)
        return rels[0] if rels else None


def version_of(release: dict) -> str:
    tag = release.get("tag_name") or release.get("name") or ""
    m = re.search(r"\d+(?:\.\d+)+[0-9A-Za-z.\-]*", tag)
    return m.group(0) if m else tag


def published_ts(release: dict) -> float:
    s = release.get("published_at") or release.get("created_at")
    if not s:
        return 0.0
    from datetime import datetime
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def pick_asset(release: dict, mod_name: str = "") -> dict | None:
    assets = [a for a in release.get("assets", []) if a.get("name", "").lower().endswith(ARCHIVE_EXT)]
    assets = [a for a in assets if "source" not in a["name"].lower() and "pdb" not in a["name"].lower()
              and "debug" not in a["name"].lower()] or assets
    if not assets:
        return None
    key = re.sub(r"[^a-z0-9]", "", mod_name.lower())
    assets.sort(key=lambda a: (key and key in re.sub(r"[^a-z0-9]", "", a["name"].lower())) * -1)
    return assets[0]


def estimate_installed(releases: list[dict], installed_mtime: float) -> dict | None:
    """Newest release published no later than ~2 days after the installed files' dates."""
    if not installed_mtime:
        return None
    dated = sorted(((published_ts(r), r) for r in releases), key=lambda x: x[0])
    cands = [r for ts, r in dated if ts and ts <= installed_mtime + 2 * 86400]
    return cands[-1] if cands else None
