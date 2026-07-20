"""
browser_cookie_helper.py
Read the screener.in `sessionid` cookie straight from the user's local
default browser, so the dashboard never has to prompt for it.

Works with any login method (username/password or Google SSO) because the
cookie is set the same way in the browser regardless.
"""

from __future__ import annotations

try:
    import browser_cookie3
except ImportError:  # pragma: no cover
    browser_cookie3 = None

SCREENER_DOMAIN = "screener.in"
COOKIE_NAME = "sessionid"

_BROWSER_LOADERS = [
    ("Chrome",  "chrome"),
    ("Edge",    "edge"),
    ("Brave",   "brave"),
    ("Firefox", "firefox"),
    ("Chromium","chromium"),
    ("Opera",   "opera"),
]


def get_screener_sessionid() -> tuple[str | None, str | None]:
    """Return (sessionid_value, source_browser_name) or (None, None)."""
    if browser_cookie3 is None:
        return None, None

    for label, attr in _BROWSER_LOADERS:
        loader = getattr(browser_cookie3, attr, None)
        if loader is None:
            continue
        try:
            jar = loader(domain_name=SCREENER_DOMAIN)
        except Exception:
            continue
        for cookie in jar:
            if cookie.name == COOKIE_NAME and SCREENER_DOMAIN in (cookie.domain or ""):
                if cookie.value:
                    return cookie.value, label
    return None, None
