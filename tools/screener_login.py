#!/usr/bin/env python3
"""
screener_login.py
One-time (occasional) launcher that captures a valid screener.in `sessionid`
WITHOUT you having to copy cookies by hand — and without this tool ever handling
your password.

Why this exists: on Windows, Chrome/Edge/Brave now use app-bound cookie
encryption, so browser_cookie3 can't read the screener.in cookie unprivileged
(it raises RequiresAdminError). This launcher sidesteps that entirely: it opens
screener.in in its OWN Playwright browser profile, YOU log in there (password or
Google SSO — your call, never automated here), and it reads the resulting
`sessionid` straight from the browser context and caches it to
tools/cache/screener_session.json.

The profile is PERSISTENT, so after the first login you usually stay logged in
and re-running this just refreshes the cached cookie in a second.

Modes (all cache to tools/cache/screener_session.json):
    py -3 tools/screener_login.py --use-profile   # Option B (recommended): reuse
        # your REAL default-browser profile's SSO session. No admin, no re-login.
        # The browser must be CLOSED (profile lock). Auto-detects your default
        # browser; override with --browser edge|chrome|brave and --profile.
    py -3 tools/screener_login.py --from-browser  # read the browser's cookie store
        # directly (needs an ADMIN terminal on Windows due to cookie encryption).
    py -3 tools/screener_login.py                 # last resort: open a fresh login
        # window and log in there once (a separate, persistent profile).

browser_cookie_helper.get_screener_sessionid() reads the cache this writes,
BEFORE it falls back to the (encryption-blocked) browser-cookie path.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

CACHE_DIR = Path(__file__).resolve().parent / "cache"
CACHE_FILE = CACHE_DIR / "screener_session.json"
PROFILE_DIR = CACHE_DIR / "pw_screener_profile"

SCREENER_BASE = "https://www.screener.in"
COOKIE_NAME = "sessionid"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
}


def _find_sessionid(cookies: list[dict]) -> str | None:
    """Pull the screener.in sessionid value out of a Playwright cookie list."""
    for c in cookies:
        if c.get("name") == COOKIE_NAME and "screener.in" in (c.get("domain") or ""):
            val = c.get("value")
            if val:
                return val
    return None


def verify_authenticated(sessionid: str) -> bool:
    """True iff the cookie is a *logged-in* session (not anonymous/expired).

    Reuses screener_scraper's own auth signal — a members-only page redirects to
    /login/ when the cookie is dead — so this matches exactly what the real
    scrapers require. Falls back to an inline check if the import is unavailable.
    """
    s = requests.Session()
    s.cookies.set(COOKIE_NAME, sessionid, domain="www.screener.in")
    try:
        r = s.get(f"{SCREENER_BASE}/screen/raw/", headers=_HEADERS,
                  params={"query": "Market Capitalization > 100000", "page": 0},
                  timeout=20, allow_redirects=True)
    except Exception:
        return False
    landed = r.url or ""
    hist = [h.headers.get("Location", "") for h in r.history]
    if any(seg in landed for seg in ("/login/", "/register/")) or \
            any(("/login/" in loc or "/register/" in loc) for loc in hist):
        return False
    # A login form served without a redirect also means the session is dead.
    if 'name="password"' in r.text and 'class="data-table"' not in r.text:
        return False
    return True


def save_session(sessionid: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    CACHE_FILE.write_text(json.dumps({
        "sessionid": sessionid,
        "captured_at": now.isoformat(),
        "captured_at_epoch": now.timestamp(),
        "source": "screener_login.py",
    }, indent=2), encoding="utf-8")
    return CACHE_FILE


def capture_session(timeout_s: int = 300, headless: bool = False) -> str | None:
    """Open screener.in in a persistent Playwright profile, wait for the user to
    log in, capture + verify + cache the sessionid. Returns the sessionid or None."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed. Run:  py -3 -m pip install playwright  "
              "&&  py -3 -m playwright install chromium", file=sys.stderr)
        return None

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    captured: str | None = None
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(PROFILE_DIR), headless=headless)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(f"{SCREENER_BASE}/login/", timeout=30_000)
        except Exception:
            pass  # a stale profile may already redirect away from /login/; that's fine

        print("─" * 68)
        print("  A screener.in window has opened.")
        print("  1. Log in there (username/password OR 'Login with Google').")
        print("  2. Leave the window open — this captures the session automatically")
        print(f"     and closes it. Waiting up to {timeout_s // 60} min…")
        print("─" * 68)

        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                sid = _find_sessionid(ctx.cookies())
            except Exception:
                sid = None
            if sid and verify_authenticated(sid):
                captured = sid
                break
            time.sleep(2)
        try:
            ctx.close()
        except Exception:
            pass

    if captured:
        path = save_session(captured)
        print(f"\n✓ Logged-in screener.in session captured and cached → {path}")
        print("  The dashboard + scrapers now pick this up automatically until it "
              "expires. Re-run this launcher anytime to refresh.")
        return captured

    print("\n✗ Timed out before a logged-in session was detected. "
          "Re-run and complete the login in the opened window.", file=sys.stderr)
    return None


def _detect_default_browser() -> str | None:
    """Read the Windows default https handler → 'chrome' | 'edge' | 'brave' | 'firefox'."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice")
        progid = str(winreg.QueryValueEx(key, "ProgId")[0]).lower()
    except Exception:
        return None
    if "chrome" in progid:
        return "chrome"
    if "edge" in progid or "msedge" in progid:
        return "edge"
    if "brave" in progid:
        return "brave"
    if "firefox" in progid or "mozilla" in progid:
        return "firefox"
    return None


def _find_brave_exe() -> str | None:
    import os
    for base in (os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                 os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
                 os.environ.get("LOCALAPPDATA", "")):
        if not base:
            continue
        exe = Path(base) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe"
        if exe.exists():
            return str(exe)
    return None


def _browser_profile_config(browser: str):
    """Return (user_data_dir, playwright_channel, executable_path) for a browser,
    or None if unsupported for the real-profile path."""
    import os
    la = os.environ.get("LOCALAPPDATA", "")
    if not la:
        return None
    table = {
        "chrome": (Path(la) / "Google" / "Chrome" / "User Data", "chrome", None),
        "edge":   (Path(la) / "Microsoft" / "Edge" / "User Data", "msedge", None),
        "brave":  (Path(la) / "BraveSoftware" / "Brave-Browser" / "User Data", None, _find_brave_exe()),
    }
    return table.get(browser)


def capture_from_real_profile(browser: str | None = None, profile: str = "Default",
                              headless: bool = False) -> str | None:
    """Option B — open your REAL browser profile with Playwright so it reuses the
    existing (SSO) screener.in session, then read + cache the sessionid. No admin
    and no re-login; the browser just has to be CLOSED (profile lock).

    Sidesteps Windows app-bound cookie encryption because the browser itself
    hands Playwright the decrypted cookies (we don't decrypt the DB offline).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed. Run:  py -3 -m pip install playwright  "
              "&&  py -3 -m playwright install chromium", file=sys.stderr)
        return None

    browser = browser or _detect_default_browser() or "chrome"
    if browser == "firefox":
        print("Your default browser is Firefox — Playwright can't load a Firefox "
              "profile via the Chromium path. Good news: Firefox has no app-bound "
              "encryption, so just run:  py -3 tools/screener_login.py --from-browser",
              file=sys.stderr)
        return None

    cfg = _browser_profile_config(browser)
    if cfg is None:
        print(f"Unsupported browser for real-profile reuse: {browser!r}.", file=sys.stderr)
        return None
    user_data_dir, channel, exe = cfg
    if not user_data_dir.exists():
        print(f"No {browser} profile found at {user_data_dir}", file=sys.stderr)
        return None
    if channel is None and exe is None:
        print(f"Could not locate the {browser} executable. Try --browser chrome or edge.",
              file=sys.stderr)
        return None

    print(f"Reusing your {browser} profile '{profile}' — make sure {browser} is fully "
          f"CLOSED (check the system tray), then this reads its screener.in session…")
    captured: str | None = None
    with sync_playwright() as p:
        launch_kwargs: dict = dict(
            user_data_dir=str(user_data_dir),
            headless=headless,
            args=[f"--profile-directory={profile}"],
        )
        if channel:
            launch_kwargs["channel"] = channel
        if exe:
            launch_kwargs["executable_path"] = exe
        try:
            ctx = p.chromium.launch_persistent_context(**launch_kwargs)
        except Exception as e:  # noqa: BLE001
            print(f"\n✗ Could not open the {browser} profile: {type(e).__name__}: "
                  f"{str(e)[:120]}\n  Most likely {browser} is still running — close it "
                  "completely (including background/tray) and retry.", file=sys.stderr)
            return None
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            try:
                page.goto(f"{SCREENER_BASE}/", timeout=30_000)
            except Exception:
                pass
            captured = _find_sessionid(ctx.cookies())
        finally:
            try:
                ctx.close()
            except Exception:
                pass

    if not captured:
        print(f"\n✗ No screener.in session cookie in that {browser} profile. Log into "
              f"screener.in in {browser} (profile '{profile}') once, then retry. "
              "If you use a non-default profile, pass --profile \"Profile 1\".",
              file=sys.stderr)
        return None
    if not verify_authenticated(captured):
        print(f"\n✗ Found a sessionid in {browser} but it's not a logged-in session "
              "(anonymous or expired). Log into screener.in there, then retry.",
              file=sys.stderr)
        return None

    path = save_session(captured)
    print(f"\n✓ Reused your {browser} screener.in session (no admin, no re-login) → {path}")
    print("  Restart the dashboard to pick it up.")
    return captured


def capture_from_default_browser() -> str | None:
    """Read the screener.in sessionid from your DEFAULT browser's existing SSO
    session — no login window, no re-login. On Windows this needs an ELEVATED
    (admin) terminal, because Chrome/Edge/Brave encrypt their cookie store.
    """
    try:
        import browser_cookie_helper as bch
    except ImportError:
        print("browser_cookie_helper not importable.", file=sys.stderr)
        return None

    print("Reading the screener.in session from your default browser…")
    sid, source = bch.read_from_local_browsers(surface_errors=True)
    if not sid:
        print("\n✗ Could not read the cookie from any local browser.\n"
              "  On Windows this almost always means Chrome/Edge/Brave cookie "
              "encryption needs elevation.\n"
              "  → Re-run this in an ADMIN terminal:\n"
              "      py -3 tools/screener_login.py --from-browser\n"
              "  (Right-click your terminal → 'Run as administrator'.)\n"
              "  Make sure you're logged into screener.in in that browser first.",
              file=sys.stderr)
        return None

    if not verify_authenticated(sid):
        print(f"\n✗ Found a sessionid in {source}, but it's not a logged-in "
              "session (anonymous or expired). Log into screener.in in that "
              "browser, then re-run.", file=sys.stderr)
        return None

    path = save_session(sid)
    print(f"\n✓ Reused your {source} screener.in session (no re-login) → {path}")
    print("  Restart the dashboard to pick it up.")
    return sid


def _force_utf8_console() -> None:
    """Windows consoles default to cp1252, which can't encode the box-drawing /
    check-mark / ellipsis glyphs used in this launcher's status output — printing
    them raises UnicodeEncodeError and aborts the tool before login can happen.
    Reconfigure stdout/stderr to UTF-8 (best-effort) so the launcher never dies on
    a status print. errors='replace' keeps it safe even if the terminal font lacks
    a glyph."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main() -> int:
    _force_utf8_console()
    ap = argparse.ArgumentParser(description="Capture a screener.in sessionid.")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--use-profile", action="store_true",
                      help="Option B: reuse your REAL browser profile's SSO session (no "
                           "admin, no re-login). The browser must be CLOSED. Recommended.")
    mode.add_argument("--from-browser", action="store_true",
                      help="Read the cookie from your default browser's store directly "
                           "(needs an admin terminal on Windows).")
    ap.add_argument("--browser", choices=["chrome", "edge", "brave"], default=None,
                    help="Which browser for --use-profile (default: your Windows default).")
    ap.add_argument("--profile", default="Default",
                    help='Browser profile dir for --use-profile (default "Default"; '
                         'e.g. "Profile 1").')
    ap.add_argument("--headless", action="store_true",
                    help="Run --use-profile / login-window mode without a visible window.")
    ap.add_argument("--timeout", type=int, default=300, help="Seconds to wait for login (default 300).")
    args = ap.parse_args()

    if args.use_profile:
        sid = capture_from_real_profile(browser=args.browser, profile=args.profile,
                                        headless=args.headless)
    elif args.from_browser:
        sid = capture_from_default_browser()
    else:
        sid = capture_session(timeout_s=args.timeout, headless=args.headless)
    return 0 if sid else 1


if __name__ == "__main__":
    raise SystemExit(main())
