"""Nexus Mods sign-in with OAuth 2.0 (authorization code + PKCE).

Flow (https://modding.wiki/en/api/oauth2-guide):
1. Make a random code_verifier and its SHA-256 code_challenge.
2. Open https://users.nexusmods.com/oauth/authorize in the user's browser.
3. Nexus redirects back to a loopback address on this PC (REDIRECT_URI) with ?code=...&state=...
4. Exchange the code (plus the verifier) at /oauth/token for an access token and refresh token.

The app is a public client: there is no client secret, PKCE protects the exchange. Tokens are
stored only on the user's PC, encrypted with Windows DPAPI (see secure.py), and sent only to
users.nexusmods.com and api.nexusmods.com.

CLIENT_ID is issued by Nexus Mods when the application is registered. Until it's set, the
"Log in with Nexus Mods" button is hidden and testing builds use a personal API key.
"""
from __future__ import annotations

import base64
import hashlib
import html
import secrets
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

from . import APP_NAME, APP_VERSION

CLIENT_ID: str | None = None          # issued by Nexus Mods on registration
AUTH_URL = "https://users.nexusmods.com/oauth/authorize"
TOKEN_URL = "https://users.nexusmods.com/oauth/token"
USERINFO_URL = "https://users.nexusmods.com/oauth/userinfo"
REDIRECT_HOST = "127.0.0.1"
REDIRECT_PORT = 51920                 # fixed so the redirect URI can be registered exactly
REDIRECT_PATH = "/callback"
REDIRECT_URI = f"http://{REDIRECT_HOST}:{REDIRECT_PORT}{REDIRECT_PATH}"
SCOPE = ""                            # set to whatever scope Nexus assigns the client
REFRESH_MARGIN = 120                  # refresh this many seconds before the access token expires

_HEADERS = {"Application-Name": APP_NAME, "Application-Version": APP_VERSION,
            "User-Agent": f"{APP_NAME.replace(' ', '')}/{APP_VERSION}"}


class OAuthError(Exception):
    pass


def configured() -> bool:
    return bool(CLIENT_ID)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def make_pkce() -> tuple[str, str]:
    """(code_verifier, code_challenge) per RFC 7636, S256."""
    verifier = _b64url(secrets.token_bytes(32))          # 43 chars
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def authorize_url(challenge: str, state: str) -> str:
    q = {"client_id": CLIENT_ID, "response_type": "code", "scope": SCOPE, "redirect_uri": REDIRECT_URI,
         "state": state, "code_challenge_method": "S256", "code_challenge": challenge}
    return AUTH_URL + "?" + urllib.parse.urlencode(q)


def _token_request(form: dict) -> dict:
    try:
        r = requests.post(TOKEN_URL, data=form, headers={**_HEADERS, "Accept": "application/json"}, timeout=20)
    except requests.RequestException as e:
        raise OAuthError(f"Couldn't reach Nexus Mods to sign in: {e}") from e
    try:
        body = r.json()
    except ValueError:
        body = {}
    if r.status_code != 200 or not body.get("access_token"):
        msg = body.get("error_description") or body.get("error") or f"HTTP {r.status_code}"
        raise OAuthError(f"Nexus Mods sign-in failed: {msg}")
    return _normalize(body)


def _normalize(body: dict, previous_refresh: str | None = None) -> dict:
    return {"access_token": body["access_token"],
            "refresh_token": body.get("refresh_token") or previous_refresh,
            "expires_at": time.time() + int(body.get("expires_in") or 3600)}


def exchange_code(code: str, verifier: str) -> dict:
    return _token_request({"grant_type": "authorization_code", "client_id": CLIENT_ID,
                           "redirect_uri": REDIRECT_URI, "code": code, "code_verifier": verifier})


def refresh(token: dict) -> dict:
    rt = token.get("refresh_token")
    if not rt:
        raise OAuthError("Your Nexus Mods sign-in expired. Log in again.")
    new = _token_request({"grant_type": "refresh_token", "client_id": CLIENT_ID, "refresh_token": rt})
    if not new.get("refresh_token"):
        new["refresh_token"] = rt
    return new


def needs_refresh(token: dict) -> bool:
    return time.time() >= (token.get("expires_at") or 0) - REFRESH_MARGIN


def userinfo(token: dict) -> dict:
    """Account name, avatar and membership from the OpenID userinfo endpoint."""
    try:
        r = requests.get(USERINFO_URL, headers={**_HEADERS, "Accept": "application/json",
                                                "Authorization": f"Bearer {token['access_token']}"}, timeout=20)
        r.raise_for_status()
        d = r.json()
    except (requests.RequestException, ValueError) as e:
        raise OAuthError(f"Couldn't read your Nexus Mods account: {e}") from e
    roles = [str(x).lower() for x in d.get("membership_roles") or []]
    return {"name": d.get("name") or d.get("preferred_username"), "user_id": d.get("sub"),
            "is_premium": any("premium" in x for x in roles), "is_supporter": "supporter" in roles,
            "avatar": d.get("avatar") or d.get("picture")}


_PAGE = """<!doctype html><meta charset="utf-8"><title>{title}</title>
<body style="font-family:Segoe UI,sans-serif;background:#111;color:#eee;display:grid;place-items:center;height:90vh">
<div style="text-align:center"><h2>{title}</h2><p>{text}</p></div></body>"""


def login(open_browser, cancelled=lambda: False, timeout: float = 300.0) -> dict:
    """Run the browser sign-in and return the token dict. Blocks until done, cancelled or timed out."""
    if not configured():
        raise OAuthError("Nexus Mods sign-in isn't set up in this build yet.")
    verifier, challenge = make_pkce()
    state = secrets.token_urlsafe(24)
    result: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (http.server API)
            u = urllib.parse.urlsplit(self.path)
            if u.path != REDIRECT_PATH:
                self.send_error(404)
                return
            q = dict(urllib.parse.parse_qsl(u.query))
            if q.get("state") != state:
                ok, text = False, "This sign-in link doesn't match the one the app opened. Try again from the app."
            elif q.get("error"):
                ok, text = False, html.escape(q.get("error_description") or q["error"])
                result["error"] = q.get("error_description") or q["error"]
            elif q.get("code"):
                ok, text = True, f"You're signed in. You can close this tab and go back to {html.escape(APP_NAME)}."
                result["code"] = q["code"]
            else:
                ok, text = False, "Nexus didn't send a sign-in code."
            body = _PAGE.format(title="Signed in" if ok else "Sign-in failed", text=text).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_a):
            pass

    try:
        server = HTTPServer((REDIRECT_HOST, REDIRECT_PORT), Handler)
    except OSError as e:
        raise OAuthError(f"Couldn't listen for the sign-in reply on port {REDIRECT_PORT}. "
                         f"Close anything using that port and try again. ({e})") from e
    server.timeout = 0.5
    try:
        open_browser(authorize_url(challenge, state))
        deadline = time.time() + timeout
        while "code" not in result and "error" not in result:
            if cancelled():
                raise InterruptedError
            if time.time() > deadline:
                raise OAuthError("Timed out waiting for you to approve the sign-in in your browser.")
            server.handle_request()
    finally:
        server.server_close()
    if "error" in result:
        raise OAuthError(f"Nexus Mods sign-in was not approved: {result['error']}")
    return exchange_code(result["code"], verifier)


class TokenStore:
    """Holds the current token, refreshes it when it's about to expire and reports changes so the
    caller can persist them. Thread-safe: several API workers may share one client."""

    def __init__(self, token: dict, on_change=None):
        self._token = dict(token)
        self._on_change = on_change
        self._lock = threading.Lock()

    def access_token(self, force_refresh: bool = False) -> str:
        with self._lock:
            if force_refresh or needs_refresh(self._token):
                self._token = refresh(self._token)
                if self._on_change:
                    self._on_change(dict(self._token))
            return self._token["access_token"]

    @property
    def token(self) -> dict:
        with self._lock:
            return dict(self._token)
