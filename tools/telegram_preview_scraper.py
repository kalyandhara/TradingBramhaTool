#!/usr/bin/env python3
"""
telegram_preview_scraper.py
Fetch recent posts from a public Telegram channel's t.me/s/<name> HTML preview.

No auth, no API — just the public web preview. Long posts are truncated by
Telegram's preview; use MTProto (Telethon) if full history is required.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from datetime import datetime
from html import unescape
from typing import List, Optional
from urllib.request import Request, urlopen


TICKER_STOPWORDS = {
    "THE", "AND", "FOR", "BUY", "SELL", "SL", "TGT", "CMP", "NSE", "BSE",
    "SEBI", "IPO", "PSU", "NIFTY", "BANK", "USD", "INR", "GST", "RBI",
    "PE", "PB", "RSI", "EMA", "SMA", "MACD", "VWAP", "ATR", "ROE",
    "HTF", "LTF", "TF", "OB", "FVG", "BOS", "CHOCH", "PDH", "PDL",
    "ATH", "ATL", "YOY", "QOQ", "EPS", "TA", "FA", "IMO", "IMHO",
    "OPEN", "HIGH", "LOW", "CLOSE", "VOL", "PA", "SR", "AI",
}

_SPLIT_RE = re.compile(r'<div class="tgme_widget_message_wrap', re.DOTALL)
_BODY_RE = re.compile(
    r'<div class="tgme_widget_message_text[^"]*"[^>]*>(?P<body>.*?)</div>\s*<div class="tgme_widget_message_(?:footer|reply|bubble)',
    re.DOTALL,
)
_BODY_FALLBACK_RE = re.compile(
    r'<div class="tgme_widget_message_text[^"]*"[^>]*>(?P<body>.*?)</div>',
    re.DOTALL,
)
_URL_RE = re.compile(r'tgme_widget_message_date"[^>]*href="([^"]+)"')
_DT_RE = re.compile(r'<time[^>]+datetime="([^"]+)"')
_TAG_RE = re.compile(r"<[^>]+>")
_TICKER_RE = re.compile(r"\b([A-Z][A-Z0-9&]{2,14})\b")


@dataclass
class TgPost:
    url: Optional[str]
    posted_at: Optional[str]
    text: str
    tickers: List[str]

    def to_dict(self):
        return asdict(self)


_REACTIONS_RE = re.compile(r"(?:[☀-➿\U0001F300-\U0001FAFF]\d+\s*)+$")


def _clean(html_fragment: str) -> str:
    txt = html_fragment.replace("<br/>", "\n").replace("<br>", "\n")
    txt = _TAG_RE.sub("", txt)
    txt = unescape(txt).strip()
    # Strip trailing reaction runs like "❤35👍13"
    txt = _REACTIONS_RE.sub("", txt).rstrip()
    return txt


def _extract_tickers(text: str) -> List[str]:
    found = []
    seen = set()
    for m in _TICKER_RE.finditer(text):
        tok = m.group(1)
        if tok in TICKER_STOPWORDS or tok in seen:
            continue
        # Ignore all-digit or purely numeric-looking
        if tok.isdigit():
            continue
        # Prefer 3+ char alpha-heavy tokens
        if sum(c.isalpha() for c in tok) < 3:
            continue
        seen.add(tok)
        found.append(tok)
    return found


def fetch_channel(username: str, timeout: int = 15) -> List[TgPost]:
    """Return recent posts from t.me/s/<username> (newest last, as page renders)."""
    username = username.lstrip("@").strip()
    url = f"https://t.me/s/{username}"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=timeout) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    posts: List[TgPost] = []
    chunks = _SPLIT_RE.split(html)[1:]  # skip pre-first-message preamble
    for chunk in chunks:
        bm = _BODY_RE.search(chunk) or _BODY_FALLBACK_RE.search(chunk)
        if not bm:
            continue
        body = _clean(bm.group("body"))
        if not body:
            continue
        um = _URL_RE.search(chunk)
        dm = _DT_RE.search(chunk)
        posts.append(TgPost(
            url=um.group(1) if um else None,
            posted_at=dm.group(1) if dm else None,
            text=body,
            tickers=_extract_tickers(body),
        ))
    return posts


def posts_to_signal_drafts(posts: List[TgPost], channel_label: str) -> List[dict]:
    """Convert scraped posts into pre-filled signal-draft dicts (one per ticker mention)."""
    drafts = []
    for p in posts:
        try:
            posted_date = datetime.fromisoformat(p.posted_at.replace("Z", "+00:00")).date() \
                if p.posted_at else None
        except Exception:
            posted_date = None
        for tkr in p.tickers[:3]:  # cap to first 3 tickers per post to avoid noise
            drafts.append({
                "symbol": tkr,
                "channel": channel_label,
                "posted_date": posted_date,
                "strategy": "",
                "signal_source": "OTHER",
                "timeframe": "",
                "confidence": 5,
                "notes": p.text + (f"\n\nSource: {p.url}" if p.url else ""),
                "metadata": {"source_url": p.url, "posted_at": p.posted_at},
            })
    return drafts


if __name__ == "__main__":
    import sys
    ch = sys.argv[1] if len(sys.argv) > 1 else "FinanceWithSunil"
    posts = fetch_channel(ch)
    print(f"Fetched {len(posts)} posts from @{ch}")
    sys.stdout.reconfigure(encoding="utf-8")
    for p in posts[-5:]:
        print(f"\n[{p.posted_at}] {p.url}")
        print(f"tickers: {p.tickers}")
        print(p.text[:200])
