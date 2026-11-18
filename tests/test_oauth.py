"""OAuth (PKCE) sign-in and how credentials are attached to requests. Run: python -m pytest tests -q"""
import base64
import hashlib
import os
import sys
import threading
import time
import urllib.parse
import urllib.request

import pytest
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cp77mlt import nexus, oauth  # noqa: E402


@pytest.fixture
def client_id(monkeypatch):
    monkeypatch.setattr(oauth, "CLIENT_ID", "cp77mlt_test")
    return "cp77mlt_test"


def test_pkce_challenge_is_s256_of_verifier():
    verifier, challenge = oauth.make_pkce()
    assert 43 <= len(verifier) <= 128
    want = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    assert challenge == want


def test_authorize_url_has_pkce_and_loopback_redirect(client_id):
    q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(oauth.authorize_url("abc", "st8")).query))
    assert q["client_id"] == client_id and q["response_type"] == "code"
    assert q["code_challenge"] == "abc" and q["code_challenge_method"] == "S256" and q["state"] == "st8"
    assert q["redirect_uri"] == "http://127.0.0.1:51920/callback"


def test_login_not_configured_raises(monkeypatch):
    monkeypatch.setattr(oauth, "CLIENT_ID", None)
    with pytest.raises(oauth.OAuthError):
        oauth.login(lambda url: None)


def _fake_browser(state_override=None, error=None):
    """Acts as the browser: reads the authorize URL and calls the loopback redirect."""
    seen = {}

    def open_browser(url):
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        seen.update(q)
        params = {"state": state_override or q["state"]}
        params.update({"error": error} if error else {"code": "the-code"})

        def hit():
            time.sleep(0.2)
            urllib.request.urlopen(q["redirect_uri"] + "?" + urllib.parse.urlencode(params), timeout=5).read()
        threading.Thread(target=hit, daemon=True).start()
    return open_browser, seen


def test_login_exchanges_code_with_verifier(client_id, monkeypatch):
    sent = {}

    def fake_exchange(code, verifier):
        sent.update(code=code, verifier=verifier)
        return {"access_token": "AT", "refresh_token": "RT", "expires_at": time.time() + 3600}
    monkeypatch.setattr(oauth, "exchange_code", fake_exchange)
    open_browser, seen = _fake_browser()
    tok = oauth.login(open_browser, timeout=10)
    assert tok["access_token"] == "AT"
    assert sent["code"] == "the-code"
    want = base64.urlsafe_b64encode(hashlib.sha256(sent["verifier"].encode()).digest()).rstrip(b"=").decode()
    assert seen["code_challenge"] == want


def test_login_rejects_wrong_state(client_id, monkeypatch):
    monkeypatch.setattr(oauth, "exchange_code", lambda c, v: pytest.fail("must not exchange"))
    open_browser, _ = _fake_browser(state_override="forged")
    with pytest.raises(oauth.OAuthError):   # the forged reply is ignored, so the wait times out
        oauth.login(open_browser, timeout=2)


def test_login_reports_denied(client_id):
    open_browser, _ = _fake_browser(error="access_denied")
    with pytest.raises(oauth.OAuthError, match="access_denied"):
        oauth.login(open_browser, timeout=10)


def test_token_store_refreshes_before_expiry(monkeypatch):
    saved = []
    monkeypatch.setattr(oauth, "refresh", lambda t: {"access_token": "new", "refresh_token": "RT2",
                                                     "expires_at": time.time() + 3600})
    store = oauth.TokenStore({"access_token": "old", "refresh_token": "RT", "expires_at": time.time() + 30},
                             on_change=saved.append)
    assert store.access_token() == "new"
    assert saved and saved[0]["refresh_token"] == "RT2"
    assert store.access_token() == "new" and len(saved) == 1   # still valid: no second refresh


def _prepared(auth, url):
    return auth(requests.Request("GET", url).prepare())


def test_credentials_only_go_to_the_api_host():
    store = oauth.TokenStore({"access_token": "AT", "refresh_token": "RT", "expires_at": time.time() + 3600})
    for auth, hdr in ((nexus.KeyAuth("K"), "apikey"), (nexus.OAuthAuth(store), "Authorization")):
        assert hdr in _prepared(auth, "https://api.nexusmods.com/v1/users/validate.json").headers
        for other in ("https://search.nexusmods.com/mods", "https://file-metadata.nexusmods.com/x",
                      "https://cf-files.nexus-cdn.com/f.zip", "https://api.nexusmods.com.evil.example/"):
            assert hdr not in _prepared(auth, other).headers
    assert _prepared(nexus.OAuthAuth(store), "https://api.nexusmods.com/v2/graphql").headers["Authorization"] == "Bearer AT"


class _Resp:
    def __init__(self, status, body=None):
        self.status_code, self._body, self.headers = status, body or {}, {}
        self.content = b"{}" if body is not None else b""
        self.text = ""

    def json(self):
        return self._body


def test_401_refreshes_token_once_and_retries(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(oauth, "refresh", lambda t: {"access_token": "fresh", "refresh_token": "RT",
                                                     "expires_at": time.time() + 3600})
    store = oauth.TokenStore({"access_token": "stale", "refresh_token": "RT", "expires_at": time.time() + 3600})
    c = nexus.NexusClient(nexus.OAuthAuth(store), str(tmp_path / "c.json"))

    def fake_request(method, url, **kw):
        calls.append(store.token["access_token"])
        return _Resp(401) if len(calls) == 1 else _Resp(200, {"name": "Sam"})
    monkeypatch.setattr(c.session, "request", fake_request)
    assert c._req("GET", "/users/validate.json") == {"name": "Sam"}
    assert calls == ["stale", "fresh"]


def test_client_sends_app_headers(tmp_path):
    c = nexus.NexusClient("K", str(tmp_path / "c.json"))
    assert c.session.headers["Application-Name"] == "Cyberpunk 2077 Mod List Tool"
    assert c.session.headers["Application-Version"]
    assert "apikey" not in c.session.headers      # added per request, only for the API host
    assert not hasattr(c, "catalog")              # no bulk mod-list download


# ---------------------------------------------------------------- app-level behaviour
@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "cfg"))
    from cp77mlt.api import Api
    from cp77mlt.config import Config
    return Api(Config(str(tmp_path / "s.json")))


def _no_network(monkeypatch):
    hits = []

    def boom(*a, **k):
        hits.append(a)
        raise AssertionError("network request at launch")
    monkeypatch.setattr(requests.Session, "request", boom)
    monkeypatch.setattr(requests, "get", boom)
    monkeypatch.setattr(requests, "post", boom)
    return hits


def test_launch_makes_no_nexus_requests(api, monkeypatch, client_id):
    import json as _json
    from cp77mlt import secure
    api._cfg.update({"nexus_oauth": secure.protect(_json.dumps({"access_token": "AT", "refresh_token": "RT",
                                                                  "expires_at": time.time() + 3600})),
                     "nexus_user": {"name": "Sam", "is_premium": True}})
    hits = _no_network(monkeypatch)
    boot = api.bootstrap()
    assert boot["nexus"]["user"]["name"] == "Sam" and boot["nexus"]["oauth"] is True
    assert boot["nexus"]["key_login"] is False
    assert api._nexus is not None and api._nexus.auth.kind == "oauth"
    assert "nexus_oauth" not in boot["settings"] and "nexus_api_key" not in boot["settings"]
    assert hits == []


def test_personal_key_only_without_oauth_client(api, monkeypatch, client_id):
    r = api.nexus_login_key("abc")
    assert r["ok"] is False and "Log in with Nexus Mods" in r["error"]


def test_account_checked_once_when_nexus_page_opens(api, monkeypatch):
    class C:
        rate = {}
        n = 0

        def validate(self):
            C.n += 1
            return {"name": "Sam"}
    api._nexus = C()
    monkeypatch.setattr(nexus.health, "refresh_async", lambda: None)
    assert api.nexus_status()["user"]["name"] == "Sam"
    api.nexus_status()
    assert C.n == 1


def test_name_lookups_are_per_id_and_capped(api):
    asked = []

    class C:
        def mod(self, mid, ttl=0):
            asked.append(mid)
            return {"name": f"Mod {mid}"}
    api._learn_names([{"mod_id": 1, "name": "Known"}])
    api._lookup_names(C(), set(range(1, 400)))
    assert 1 not in asked and len(asked) == api.NAME_LOOKUP_LIMIT
    assert api._names().search("Mod 5")[0]["mod_id"] == 5
