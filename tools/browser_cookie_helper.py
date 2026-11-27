"""
browser_cookie_helper.py
Read the screener.in `sessionid` cookie straight from the user's local
default browser, so the dashboard never has to prompt for it.

Works with any login method (username/password or Google SSO) because the
cookie is set the same way in the browser regardless.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

try:
    import browser_cookie3
except ImportError:  # pragma: no cover
    browser_cookie3 = None

SCREENER_DOMAIN = "screener.in"
COOKIE_NAME = "sessionid"

# Cache written by screener_login.py (a Playwright login-capture launcher). We
# read this FIRST because on Windows, Chrome/Edge/Brave app-bound cookie
# encryption makes browser_cookie3 raise RequiresAdminError — so the direct
# browser read below usually fails, and this cache is the reliable path.
_CACHE_FILE = Path(__file__).resolve().parent / "cache" / "screener_session.json"
# screener.in sessions are long-lived; cap how long we trust the cache before
# treating it as stale. If the server expired it sooner, the scraper's own
# auth check surfaces a clear "re-grab it" error downstream.
_CACHE_MAX_AGE_S = 20 * 24 * 3600  # 20 days


def _read_cached_sessionid() -> str | None:
    """Return a non-stale sessionid saved by screener_login.py, or None."""
    try:
        data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None
    sid = data.get("sessionid")
    ts = data.get("captured_at_epoch") or 0
    if sid and (time.time() - float(ts)) < _CACHE_MAX_AGE_S:
        return sid
    return None

_BROWSER_LOADERS = [
    ("Chrome",  "chrome"),
    ("Edge",    "edge"),
    ("Brave",   "brave"),
    ("Firefox", "firefox"),
    ("Chromium","chromium"),
    ("Opera",   "opera"),
]


def read_from_local_browsers(surface_errors: bool = False) -> tuple[str | None, str | None]:
    """Read the screener.in sessionid straight from a local browser's cookie
    store (reuses your existing SSO session — no re-login).

    On Windows, Chrome/Edge/Brave use app-bound cookie encryption, so the
    loaders raise RequiresAdminError unless this runs elevated. Set
    `surface_errors=True` to print the per-browser failure reason (used by the
    `--from-browser` launcher mode to tell the user to run as admin)."""
    if browser_cookie3 is None:
        if surface_errors:
            print("browser_cookie3 is not installed.")
        return None, None

    for label, attr in _BROWSER_LOADERS:
        loader = getattr(browser_cookie3, attr, None)
        if loader is None:
            continue
        try:
            jar = loader(domain_name=SCREENER_DOMAIN)
        except Exception as e:  # noqa: BLE001
            if surface_errors:
                print(f"  {label:9} — {type(e).__name__}: {str(e)[:80]}")
            continue
        for cookie in jar:
            if cookie.name == COOKIE_NAME and SCREENER_DOMAIN in (cookie.domain or ""):
                if cookie.value:
                    return cookie.value, label
    return None, None


#: A verified sessionid is trusted for this long before it is re-checked, so a
#: page re-render does not cost an HTTP round-trip every time.
_VERIFY_TTL_S = 6 * 3600
_verified: dict = {"sid": None, "at": 0.0}


def _cached_any_age() -> str | None:
    try:
        return json.loads(_CACHE_FILE.read_text(encoding="utf-8")).get("sessionid")
    except Exception:
        return None


def invalidate_cache() -> None:
    """Forget the in-memory verification (call when a scrape hits the login page)."""
    _verified.update(sid=None, at=0.0)


def get_screener_sessionid() -> tuple[str | None, str | None]:
    """Return (sessionid_value, source) or (None, None) — with no user action
    whenever possible.

    Order:
      1. the saved session (tools/cache/screener_session.json), kept for as long as
         screener.in still accepts it (checked, not aged out);
      2. a SILENT headless refresh from the persistent login profile that
         screener_login.py created (cache/pw_screener_profile) — no window;
      3. a direct read of the local browsers' cookie stores.
    Only if all three fail does the page need the one-click "Connect" login."""
    now = time.time()
    if _verified["sid"] and now - _verified["at"] < _VERIFY_TTL_S:
        return _verified["sid"], "saved login"
    try:
        import screener_login as sl
    except Exception:  # pragma: no cover
        sl = None
    cached = _cached_any_age()
    if cached and (sl is None or sl.verify_authenticated(cached)):
        _verified.update(sid=cached, at=now)
        return cached, "saved login"
    if sl is not None:
        sid = sl.refresh_silently()
        if sid:
            _verified.update(sid=sid, at=now)
            return sid, "auto-refreshed login"
    sid, src = read_from_local_browsers()
    if sid:
        _verified.update(sid=sid, at=now)
    return sid, src
