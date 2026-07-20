"""
symbol_directory.py — TradingView-style symbol search directory for chart_server.py.

Builds an in-memory, searchable index combining:
  • NSE   — full live equity list (~2,300+ symbols) fetched from NSE archives,
            cached to disk for 24h, with a curated fallback if the fetch fails.
  • BSE   — small curated supplement (BSE-only names not already covered by NSE).
  • US    — major indices + curated large-cap stock list (NASDAQ/NYSE).
  • CRYPTO— Hyperliquid-tradable coins (curated, matches chart_server's roster).

Usage:
    from symbol_directory import search, is_known_equity_symbol

    results = search("sigma", limit=20)
    # -> [{"symbol": "SIGMAADV.NS", "display": "SIGMAADV", "name": "...",
    #      "type": "stock", "exchange": "NSE", "source": "yfinance"}, ...]
"""

from __future__ import annotations

import csv
import io
import json
import logging
import threading
import time
from pathlib import Path

import requests

log = logging.getLogger(__name__)

HERE       = Path(__file__).resolve().parent
CACHE_DIR  = HERE / "cache"
CACHE_FILE = CACHE_DIR / "nse_equity_list.json"
BSE_CACHE_FILE = CACHE_DIR / "bse_equity_list.json"
CACHE_TTL  = 24 * 3600  # refresh NSE/BSE lists once a day

NSE_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
# BSE has no stable "all listed" endpoint, but the daily equity bhavcopy CSV
# contains every scrip that traded that day (~4,900 rows) with a yfinance-
# compatible TckrSymb column. We try today then walk back a week to survive
# weekends and holidays.
BSE_BHAVCOPY_URL = (
    "https://www.bseindia.com/download/BhavCopy/Equity/"
    "BhavCopy_BSE_CM_0_0_0_{ymd}_F_0000.CSV"
)
BSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.bseindia.com/",
}

# RLock (not Lock) because get_symbol_lookup() and get_equity_symbol_set()
# both hold the lock while their builders call get_directory(), which itself
# acquires the same lock — a plain Lock would deadlock on the first call.
_lock      = threading.RLock()
_directory: list[dict] | None = None
_equity_symbol_set: set[str] | None = None   # bare tickers routed to yfinance
_symbol_lookup: dict[str, str] | None = None  # display/symbol -> canonical fetch symbol


# ── NSE: live fetch with disk cache + curated fallback ──────────────────────────

def _fetch_nse_live() -> list[dict] | None:
    try:
        r = requests.get(NSE_URL, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        reader = csv.DictReader(io.StringIO(r.text))
        entries = []
        for row in reader:
            sym  = (row.get("SYMBOL") or "").strip()
            name = (row.get("NAME OF COMPANY") or "").strip()
            if not sym or not name:
                continue
            entries.append({
                "symbol":   f"{sym}.NS",
                "display":  sym,
                "name":     name,
                "type":     "stock",
                "exchange": "NSE",
                "source":   "yfinance",
            })
        log.info("NSE live fetch OK — %d symbols", len(entries))
        return entries or None
    except Exception as e:
        log.warning("NSE live fetch failed: %s", e)
        return None


def _load_nse_list() -> list[dict]:
    CACHE_DIR.mkdir(exist_ok=True)

    if CACHE_FILE.exists():
        age = time.time() - CACHE_FILE.stat().st_mtime
        if age < CACHE_TTL:
            try:
                return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass

    entries = _fetch_nse_live()
    if entries:
        try:
            CACHE_FILE.write_text(json.dumps(entries), encoding="utf-8")
        except Exception as e:
            log.warning("Could not write NSE cache: %s", e)
        return entries

    # Live fetch failed — fall back to a stale cache if one exists at all.
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    log.warning("Using bundled curated NSE fallback list (%d symbols)",
                len(_NSE_FALLBACK))
    return list(_NSE_FALLBACK)


def refresh_nse_list() -> int:
    """Force a fresh NSE fetch (ignores cache age). Returns symbol count."""
    entries = _fetch_nse_live()
    if entries:
        try:
            CACHE_FILE.write_text(json.dumps(entries), encoding="utf-8")
        except Exception:
            pass
    with _lock:
        global _directory, _equity_symbol_set, _symbol_lookup
        _directory = None
        _equity_symbol_set = None
        _symbol_lookup = None
    return len(entries) if entries else 0


# ── BSE: daily bhavcopy → full listed-equity list ──────────────────────────────

def _fetch_bse_live() -> list[dict] | None:
    """Pull the latest available BSE equity bhavcopy CSV. Returns ~4,900
    entries with yfinance-compatible '.BO' symbols. Walks back up to 7 days
    to survive weekends and holidays."""
    from datetime import date, timedelta
    for offset in range(0, 8):
        d = date.today() - timedelta(days=offset)
        url = BSE_BHAVCOPY_URL.format(ymd=d.strftime("%Y%m%d"))
        try:
            r = requests.get(url, timeout=15, headers=BSE_HEADERS)
            if r.status_code != 200 or "csv" not in r.headers.get("content-type", "").lower() and "octet" not in r.headers.get("content-type", "").lower():
                continue
            reader = csv.DictReader(io.StringIO(r.text))
            entries = []
            seen = set()
            for row in reader:
                sym  = (row.get("TckrSymb") or "").strip()
                name = (row.get("FinInstrmNm") or "").strip()
                sers = (row.get("SctySrs") or "").strip().upper()
                instr = (row.get("FinInstrmTp") or "").strip().upper()
                # Keep only equity stocks (STK), skip debt / warrants / suspended
                if not sym or not name or instr != "STK":
                    continue
                # Series A/B/T are regular equity; skip Z (suspended), F (fixed
                # income), etc. Series can be blank for some rows — allow that.
                if sers and sers not in ("A", "B", "T", "M", "X", "P", "MT"):
                    continue
                key = sym.upper()
                if key in seen:
                    continue
                seen.add(key)
                entries.append({
                    "symbol":   f"{sym}.BO",
                    "display":  sym,
                    "name":     name,
                    "type":     "stock",
                    "exchange": "BSE",
                    "source":   "yfinance",
                })
            if entries:
                log.info("BSE bhavcopy fetch OK (%s) — %d symbols", d.isoformat(), len(entries))
                return entries
        except Exception as e:
            log.debug("BSE bhavcopy %s failed: %s", d.isoformat(), e)
            continue
    log.warning("BSE bhavcopy fetch failed for all recent dates")
    return None


def _load_bse_list() -> list[dict]:
    CACHE_DIR.mkdir(exist_ok=True)

    if BSE_CACHE_FILE.exists():
        age = time.time() - BSE_CACHE_FILE.stat().st_mtime
        if age < CACHE_TTL:
            try:
                return json.loads(BSE_CACHE_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass

    entries = _fetch_bse_live()
    if entries:
        try:
            BSE_CACHE_FILE.write_text(json.dumps(entries), encoding="utf-8")
        except Exception as e:
            log.warning("Could not write BSE cache: %s", e)
        return entries

    # Live fetch failed — fall back to a stale cache if one exists.
    if BSE_CACHE_FILE.exists():
        try:
            return json.loads(BSE_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    log.warning("Using bundled curated BSE fallback list (%d symbols)",
                len(_BSE_SUPPLEMENT))
    return list(_BSE_SUPPLEMENT)


def refresh_bse_list() -> int:
    """Force a fresh BSE fetch (ignores cache age). Returns symbol count."""
    entries = _fetch_bse_live()
    if entries:
        try:
            BSE_CACHE_FILE.write_text(json.dumps(entries), encoding="utf-8")
        except Exception:
            pass
    with _lock:
        global _directory, _equity_symbol_set, _symbol_lookup
        _directory = None
        _equity_symbol_set = None
        _symbol_lookup = None
    return len(entries) if entries else 0


# ── Curated fallback / supplement lists ──────────────────────────────────────────

_NSE_FALLBACK = [
    {"symbol": f"{s}.NS", "display": s, "name": n, "type": "stock",
     "exchange": "NSE", "source": "yfinance"}
    for s, n in [
        ("RELIANCE", "Reliance Industries Limited"),
        ("TCS", "Tata Consultancy Services Limited"),
        ("HDFCBANK", "HDFC Bank Limited"),
        ("INFY", "Infosys Limited"),
        ("ICICIBANK", "ICICI Bank Limited"),
        ("SBIN", "State Bank of India"),
        ("HINDUNILVR", "Hindustan Unilever Limited"),
        ("ITC", "ITC Limited"),
        ("KOTAKBANK", "Kotak Mahindra Bank Limited"),
        ("LT", "Larsen & Toubro Limited"),
        ("BHARTIARTL", "Bharti Airtel Limited"),
        ("AXISBANK", "Axis Bank Limited"),
        ("ASIANPAINT", "Asian Paints Limited"),
        ("MARUTI", "Maruti Suzuki India Limited"),
        ("WIPRO", "Wipro Limited"),
        ("HCLTECH", "HCL Technologies Limited"),
        ("SUNPHARMA", "Sun Pharmaceutical Industries Limited"),
        ("TITAN", "Titan Company Limited"),
        ("NTPC", "NTPC Limited"),
        ("POWERGRID", "Power Grid Corporation of India Limited"),
        ("BAJFINANCE", "Bajaj Finance Limited"),
        ("ONGC", "Oil and Natural Gas Corporation Limited"),
        ("COALINDIA", "Coal India Limited"),
        ("JSWSTEEL", "JSW Steel Limited"),
        ("TATASTEEL", "Tata Steel Limited"),
        ("M&M", "Mahindra & Mahindra Limited"),
        ("ULTRACEMCO", "UltraTech Cement Limited"),
        ("TECHM", "Tech Mahindra Limited"),
        ("ADANIENT", "Adani Enterprises Limited"),
        ("ADANIPORTS", "Adani Ports and Special Economic Zone Limited"),
        ("HINDALCO", "Hindalco Industries Limited"),
        ("DRREDDY", "Dr. Reddy's Laboratories Limited"),
        ("DIVISLAB", "Divi's Laboratories Limited"),
        ("CIPLA", "Cipla Limited"),
        ("BAJAJFINSV", "Bajaj Finserv Limited"),
        ("NESTLEIND", "Nestle India Limited"),
        ("GRASIM", "Grasim Industries Limited"),
        ("INDUSINDBK", "IndusInd Bank Limited"),
        ("TATAMOTORS", "Tata Motors Limited"),
        ("EICHERMOT", "Eicher Motors Limited"),
        ("HEROMOTOCO", "Hero MotoCorp Limited"),
        ("BRITANNIA", "Britannia Industries Limited"),
        ("SHREECEM", "Shree Cement Limited"),
        ("UPL", "UPL Limited"),
        ("SBILIFE", "SBI Life Insurance Company Limited"),
        ("HDFCLIFE", "HDFC Life Insurance Company Limited"),
        ("BPCL", "Bharat Petroleum Corporation Limited"),
        ("IOC", "Indian Oil Corporation Limited"),
        ("VEDL", "Vedanta Limited"),
        ("GAIL", "GAIL (India) Limited"),
        ("PIDILITIND", "Pidilite Industries Limited"),
        ("DABUR", "Dabur India Limited"),
        ("GODREJCP", "Godrej Consumer Products Limited"),
        ("HAVELLS", "Havells India Limited"),
        ("SIEMENS", "Siemens Limited"),
        ("DLF", "DLF Limited"),
        ("PNB", "Punjab National Bank"),
        ("BANKBARODA", "Bank of Baroda"),
        ("CANBK", "Canara Bank"),
        ("ZOMATO", "Eternal Limited"),
        ("PAYTM", "One97 Communications Limited"),
        ("NYKAA", "FSN E-Commerce Ventures Limited"),
        ("IRCTC", "Indian Railway Catering and Tourism Corporation Limited"),
        ("TRENT", "Trent Limited"),
        ("BEL", "Bharat Electronics Limited"),
        ("HAL", "Hindustan Aeronautics Limited"),
        ("SIGNATURE", "Signatureglobal (India) Limited"),
        ("SIGACHI", "Sigachi Industries Limited"),
        ("SIGIND", "Signet Industries Limited"),
        ("SIGMA", "Sigma Solve Limited"),
        ("SIGMAADV", "SIGMA ADVANCED SYSTEMS LIMITED"),
    ]
]

# BSE-only supplement — small curated starter set (BSE has no reliable public
# bulk symbol API reachable from this server; expand manually as needed).
_BSE_SUPPLEMENT = [
    {"symbol": f"{s}.BO", "display": s, "name": n, "type": "stock",
     "exchange": "BSE", "source": "yfinance"}
    for s, n in [
        ("RELIANCE", "Reliance Industries Limited"),
        ("TCS", "Tata Consultancy Services Limited"),
        ("SENSEX", "S&P BSE Sensex"),
    ]
]

# US indices (yfinance "^" tickers) — always routed to yfinance.
_US_INDICES = [
    {"symbol": s, "display": s, "name": n, "type": "index",
     "exchange": "INDEX", "source": "yfinance"}
    for s, n in [
        ("^GSPC", "S&P 500"),
        ("^DJI",  "Dow Jones Industrial Average"),
        ("^IXIC", "NASDAQ Composite"),
        ("^NDX",  "NASDAQ 100"),
        ("^RUT",  "Russell 2000"),
        ("^VIX",  "CBOE Volatility Index"),
        ("^FTSE", "FTSE 100"),
        ("^N225", "Nikkei 225"),
        ("^NSEI", "Nifty 50"),
        ("^NSEBANK", "Nifty Bank"),
    ]
]

# US stocks — curated large-cap roster across sectors (bare ticker, no suffix).
_US_STOCKS = [
    {"symbol": s, "display": s, "name": n, "type": "stock",
     "exchange": "NASDAQ" if ex == "Q" else "NYSE", "source": "yfinance"}
    for s, n, ex in [
        ("AAPL", "Apple Inc.", "Q"), ("MSFT", "Microsoft Corporation", "Q"),
        ("GOOGL", "Alphabet Inc. Class A", "Q"), ("GOOG", "Alphabet Inc. Class C", "Q"),
        ("AMZN", "Amazon.com Inc.", "Q"), ("NVDA", "NVIDIA Corporation", "Q"),
        ("META", "Meta Platforms Inc.", "Q"), ("TSLA", "Tesla Inc.", "Q"),
        ("AVGO", "Broadcom Inc.", "Q"), ("ORCL", "Oracle Corporation", "N"),
        ("ADBE", "Adobe Inc.", "Q"), ("CRM", "Salesforce Inc.", "N"),
        ("AMD", "Advanced Micro Devices Inc.", "Q"), ("INTC", "Intel Corporation", "Q"),
        ("CSCO", "Cisco Systems Inc.", "Q"), ("QCOM", "QUALCOMM Incorporated", "Q"),
        ("IBM", "International Business Machines Corp.", "N"),
        ("NFLX", "Netflix Inc.", "Q"), ("UBER", "Uber Technologies Inc.", "N"),
        ("PYPL", "PayPal Holdings Inc.", "Q"), ("SHOP", "Shopify Inc.", "N"),
        ("JPM", "JPMorgan Chase & Co.", "N"), ("BAC", "Bank of America Corp.", "N"),
        ("WFC", "Wells Fargo & Company", "N"), ("GS", "The Goldman Sachs Group Inc.", "N"),
        ("MS", "Morgan Stanley", "N"), ("C", "Citigroup Inc.", "N"),
        ("V", "Visa Inc.", "N"), ("MA", "Mastercard Incorporated", "N"),
        ("AXP", "American Express Company", "N"), ("BRK-B", "Berkshire Hathaway Inc. Class B", "N"),
        ("JNJ", "Johnson & Johnson", "N"), ("PFE", "Pfizer Inc.", "N"),
        ("UNH", "UnitedHealth Group Incorporated", "N"), ("LLY", "Eli Lilly and Company", "N"),
        ("ABBV", "AbbVie Inc.", "N"), ("MRK", "Merck & Co. Inc.", "N"),
        ("TMO", "Thermo Fisher Scientific Inc.", "N"), ("ABT", "Abbott Laboratories", "N"),
        ("WMT", "Walmart Inc.", "N"), ("PG", "Procter & Gamble Company", "N"),
        ("KO", "The Coca-Cola Company", "N"), ("PEP", "PepsiCo Inc.", "Q"),
        ("COST", "Costco Wholesale Corporation", "Q"), ("MCD", "McDonald's Corporation", "N"),
        ("NKE", "NIKE Inc.", "N"), ("SBUX", "Starbucks Corporation", "Q"),
        ("HD", "The Home Depot Inc.", "N"), ("LOW", "Lowe's Companies Inc.", "N"),
        ("DIS", "The Walt Disney Company", "N"), ("CMCSA", "Comcast Corporation", "Q"),
        ("XOM", "Exxon Mobil Corporation", "N"), ("CVX", "Chevron Corporation", "N"),
        ("BA", "The Boeing Company", "N"), ("CAT", "Caterpillar Inc.", "N"),
        ("GE", "General Electric Company", "N"), ("F", "Ford Motor Company", "N"),
        ("GM", "General Motors Company", "N"), ("T", "AT&T Inc.", "N"),
        ("VZ", "Verizon Communications Inc.", "N"), ("PLTR", "Palantir Technologies Inc.", "N"),
        ("COIN", "Coinbase Global Inc.", "Q"), ("SQ", "Block Inc.", "N"),
        ("SNOW", "Snowflake Inc.", "N"), ("ASML", "ASML Holding N.V.", "Q"),
        ("TSM", "Taiwan Semiconductor Manufacturing Co.", "N"),
        ("MU", "Micron Technology Inc.", "Q"), ("TXN", "Texas Instruments Inc.", "Q"),
    ]
]

# Hyperliquid-tradable crypto roster (mirrors chart_server's /api/symbols).
_CRYPTO = [
    {"symbol": s, "display": s, "name": n, "type": "crypto",
     "exchange": "CRYPTO", "source": "hyperliquid"}
    for s, n in [
        ("BTC", "Bitcoin"), ("ETH", "Ethereum"), ("SOL", "Solana"),
        ("AVAX", "Avalanche"), ("ARB", "Arbitrum"), ("OP", "Optimism"),
        ("MATIC", "Polygon"), ("DOGE", "Dogecoin"), ("LINK", "Chainlink"),
        ("UNI", "Uniswap"), ("AAVE", "Aave"), ("APT", "Aptos"),
        ("SUI", "Sui"), ("INJ", "Injective"), ("TIA", "Celestia"),
        ("JUP", "Jupiter"), ("WIF", "dogwifhat"), ("PEPE", "Pepe"),
        ("BNB", "BNB"), ("TON", "Toncoin"), ("SEI", "Sei"),
        ("NEAR", "NEAR Protocol"), ("FTM", "Fantom"), ("ATOM", "Cosmos"),
        ("DOT", "Polkadot"), ("LTC", "Litecoin"), ("XRP", "XRP"),
        ("ADA", "Cardano"), ("TRUMP", "Official Trump"), ("HYPE", "Hyperliquid"),
    ]
]


# ── Directory assembly ───────────────────────────────────────────────────────────

def _build_directory() -> list[dict]:
    nse = _load_nse_list()
    seen = {e["symbol"] for e in nse}
    # NSE is added first so the display-ticker lookup (built via setdefault)
    # prefers .NS on dual-listed collisions like 'RELIANCE'. BSE-only tickers
    # (DOLPHMED, ADON, GALLANTT, …) still route to .BO because there's no NSE
    # entry for their display ticker.
    bse_live = _load_bse_list()
    bse = [e for e in bse_live if e["symbol"] not in seen]
    return nse + bse + _US_INDICES + _US_STOCKS + _CRYPTO


def get_directory() -> list[dict]:
    global _directory
    with _lock:
        if _directory is None:
            _directory = _build_directory()
        return _directory


def get_equity_symbol_set() -> set[str]:
    """Bare/base tickers (without suffix) that should route to yfinance, not crypto."""
    global _equity_symbol_set
    with _lock:
        if _equity_symbol_set is None:
            s = set()
            for e in get_directory():
                if e["source"] == "yfinance":
                    s.add(e["symbol"].upper())
                    s.add(e["display"].upper())
            _equity_symbol_set = s
        return _equity_symbol_set


def is_known_equity_symbol(symbol: str) -> bool:
    return symbol.upper() in get_equity_symbol_set()


def _build_symbol_lookup() -> dict[str, str]:
    """Map every known display ticker AND canonical symbol (both upper-cased)
    to the canonical, correctly-suffixed fetch symbol. Directory order (NSE
    before BSE before US/crypto) means setdefault() prefers NSE on any
    display-ticker collision (e.g. 'RELIANCE' -> 'RELIANCE.NS', not '.BO')."""
    lookup: dict[str, str] = {}
    for e in get_directory():
        lookup.setdefault(e["symbol"].upper(), e["symbol"])
        lookup.setdefault(e["display"].upper(), e["symbol"])
    # Common shortcuts users type instead of the yfinance index symbol.
    # Without these, "NIFTY" falls through to the search fallback and lands on
    # look-alike names (e.g. NIFTY1.BO, a Kotak mutual fund unit) which have
    # thin history and are not what the user meant.
    _ALIASES = {
        "NIFTY":      "^NSEI",
        "NIFTY50":    "^NSEI",
        "NIFTY 50":   "^NSEI",
        "NSEI":       "^NSEI",
        "BANKNIFTY":  "^NSEBANK",
        "BANK NIFTY": "^NSEBANK",
        "NSEBANK":    "^NSEBANK",
        "SENSEX":     "^BSESN",
    }
    for alias, canonical in _ALIASES.items():
        lookup.setdefault(alias.upper(), canonical)
    return lookup


def get_symbol_lookup() -> dict[str, str]:
    global _symbol_lookup
    with _lock:
        if _symbol_lookup is None:
            _symbol_lookup = _build_symbol_lookup()
        return _symbol_lookup


def resolve_symbol(symbol: str) -> str:
    """
    Map a bare, user-typed ticker (e.g. 'IFCI') to its canonical fetch symbol
    (e.g. 'IFCI.NS'). This is what makes typing an NSE/BSE ticker directly
    (without picking it from the search dropdown first) work correctly —
    without it, a bare NSE display ticker gets routed to yfinance by
    is_known_equity_symbol() but fetched with no '.NS' suffix, which yfinance
    silently returns empty/garbage data for (manifesting as an indefinitely
    "Loading..." chart). Already-qualified symbols (suffixed, '^'-prefixed,
    or simply not in our directory — e.g. a Hyperliquid coin) pass through
    unchanged.
    """
    s = symbol.strip().upper()
    if not s:
        return s
    return get_symbol_lookup().get(s, s)


# ── Search / ranking ─────────────────────────────────────────────────────────────

def search(query: str, limit: int = 20) -> list[dict]:
    """
    TradingView-style ranked search across symbol/display/name.
    Priority: exact ticker > ticker startswith > ticker contains > name contains.
    """
    q = (query or "").strip().upper()
    if not q:
        return []

    directory = get_directory()
    scored: list[tuple[int, int, dict]] = []

    for e in directory:
        disp = e["display"].upper()
        name = e["name"].upper()

        if disp == q:
            score = 0
        elif disp.startswith(q):
            score = 1
        elif q in disp:
            score = 2
        elif name.startswith(q):
            score = 3
        elif q in name:
            score = 4
        else:
            continue

        scored.append((score, len(disp), e))

    scored.sort(key=lambda t: (t[0], t[1]))
    return [e for _, _, e in scored[:limit]]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = search("sigma", limit=10)
    for r in results:
        print(r)
    print(f"\nTotal directory size: {len(get_directory())}")
