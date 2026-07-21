"""block_deal_intel.py — turn raw bulk/block deal rows into a CEAVET summary.

The Market Intel page listed every deal as a flat table: true, complete, and
silent on what any of it meant. 128 NSE bulk rows tell you nothing at a glance
about which company an institution actually accumulated today.

This module aggregates deals per company above a value floor and emits a
six-part CEAVET read:

    C ontext      what kind of deal, on which venue, how big relative to CMP
    E vent        the mechanical fact — notably matched buy/sell quantities
    A nalysis     which institutional motive the pattern is consistent with
    V alue clues  ownership change, deal price vs CMP, buyer type
    E valuate     post-deal price action and volume confirmation
    T akeaway     a signal-strength verdict with what would confirm/kill it

Everything here is RULE-BASED and inspectable — no model, no opinion that is
not traceable to a named field. Where an input is missing (no price history
for a BSE-only scrip, deal too recent to have post-deal action) the section
says so rather than guessing. That matters more here than elsewhere in the
repo: a confident-sounding narrative over absent data is how you end up
trusting a "signal" that is really one broker crossing stock with itself.

NOT ADVICE. The takeaway grades the strength of the *signal*, not the merit of
an investment, and deliberately refuses to grade at all when the evidence is
just a negotiated transfer between two known parties.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

# Per-company aggregate deal value floor. 500 lakh = Rs 5 crore, which on a
# normal session narrows ~55 companies with deals to ~21 worth a second look.
MIN_DEAL_VALUE = 5_00_00_000.0

# Identical quantities rarely coincide by chance. Allowing a hair of tolerance
# catches transfers split across two ticket rows without matching genuinely
# unrelated trades.
QTY_MATCH_TOL = 0.005      # 0.5%
PRICE_MATCH_TOL = 0.002    # 0.2%

# Deal price vs CMP beyond this reads as a deliberate premium/discount rather
# than ordinary intraday drift.
PREMIUM_PCT = 2.0


# ── Counterparty classification ───────────────────────────────────────────────
# Ordered most-specific first: "HDFC MUTUAL FUND" must land on MUTUAL FUND, not
# on CORPORATE via its "LIMITED"-ish tail.
_CLIENT_PATTERNS: list[tuple[str, str]] = [
    (r"MUTUAL\s*FUND|ASSET\s*MANAGEMENT|\bAMC\b|\bMF\b",        "MUTUAL FUND"),
    (r"INSURANCE|\bLIC\b|LIFE\s*INSURANCE",                      "INSURANCE"),
    (r"\bFPI\b|\bFII\b|MAURITIUS|LUXEMBOURG|CAYMAN|\bODI\b|"
     r"SINGAPORE|IRELAND|GLOBAL\s*FUND|OFFSHORE",                "FPI / FII"),
    (r"ALTERNATIVE\s*INVESTMENT|\bAIF\b|PORTFOLIO\s*MANAG|\bPMS\b", "AIF / PMS"),
    (r"BROKING|SECURITIES|MARKETEDGE|STOCK\s*BROK|\bPROP\b",     "BROKER / PROP"),
    (r"PRIVATE\s*LIMITED|\bPVT\b|\bLLP\b|LIMITED|\bLTD\b|"
     r"ENTERPRISES|VYAPAAR|TRADING\s*CO",                        "CORPORATE"),
]

# Buyers whose participation is a genuine ownership signal, as opposed to
# intermediaries whose flow nets to roughly zero over a week.
INSTITUTIONAL = {"MUTUAL FUND", "INSURANCE", "FPI / FII", "AIF / PMS"}


def classify_client(name: str) -> str:
    """Bucket a counterparty name. Falls back to INDIVIDUAL, which is correct
    for the person-names that dominate bulk-deal rows."""
    n = (name or "").upper()
    for pattern, label in _CLIENT_PATTERNS:
        if re.search(pattern, n):
            return label
    return "INDIVIDUAL"


# ── Normalisation ─────────────────────────────────────────────────────────────

def normalize_deals(nse_bulk: pd.DataFrame | None = None,
                    nse_block: pd.DataFrame | None = None,
                    bse_bulk: pd.DataFrame | None = None,
                    bse_block: pd.DataFrame | None = None) -> pd.DataFrame:
    """Flatten NSE and BSE deal feeds into one schema.

    The two exchanges disagree on every column name and encode the side as
    BUY/SELL vs B/S, so downstream logic would otherwise carry a branch per
    venue. Returns columns: date, symbol, name, client, client_type, side,
    qty, price, value, exchange, deal_type.
    """
    rows: list[dict[str, Any]] = []

    def _add_nse(df, deal_type):
        if df is None or df.empty:
            return
        for _, r in df.iterrows():
            try:
                qty   = float(r.get("Quantity Traded", 0) or 0)
                price = float(r.get("Trade Price / Wght. Avg. Price", 0) or 0)
            except (TypeError, ValueError):
                continue
            side = str(r.get("Buy/Sell", "")).strip().upper()
            rows.append({
                "date": str(r.get("Date", "")).strip(),
                "symbol": str(r.get("Symbol", "")).strip().upper(),
                "name": str(r.get("Security Name", "")).strip(),
                "client": str(r.get("Client Name", "")).strip(),
                "side": "BUY" if side.startswith("B") else "SELL",
                "qty": qty, "price": price, "value": qty * price,
                "exchange": "NSE", "deal_type": deal_type,
            })

    def _add_bse(df, deal_type):
        if df is None or df.empty:
            return
        for _, r in df.iterrows():
            try:
                qty   = float(r.get("QUANTITY", 0) or 0)
                price = float(r.get("PRICE", 0) or 0)
            except (TypeError, ValueError):
                continue
            side = str(r.get("TRANSACTION_TYPE", "")).strip().upper()
            rows.append({
                "date": str(r.get("DEAL_DATE", "")).strip(),
                "symbol": str(r.get("ScripName", "")).strip().upper(),
                "name": str(r.get("ScripName", "")).strip(),
                "client": str(r.get("CLIENT_NAME", "")).strip(),
                "side": "BUY" if side.startswith("B") else "SELL",
                "qty": qty, "price": price, "value": qty * price,
                "exchange": "BSE", "deal_type": deal_type,
            })

    _add_nse(nse_bulk, "BULK")
    _add_nse(nse_block, "BLOCK")
    _add_bse(bse_bulk, "BULK")
    _add_bse(bse_block, "BLOCK")

    df = pd.DataFrame(rows)
    if not df.empty:
        df["client_type"] = df["client"].map(classify_client)
    return df


# ── Matched-transfer detection (the "E" in CEAVET) ────────────────────────────

def find_matched_transfers(deals: pd.DataFrame) -> list[dict[str, Any]]:
    """Pair buys against sells of (near) identical quantity on the same day.

    An exact quantity match across opposite sides is the fingerprint of a
    negotiated transfer: the two sides agreed the size beforehand and crossed
    it on-exchange. When the prices match too, it was almost certainly priced
    off-market. This distinction is the single most useful thing in the whole
    dataset, because a pure transfer changes the register without changing the
    float — it is NOT accumulation, however large the number looks.
    """
    out: list[dict[str, Any]] = []
    if deals is None or deals.empty:
        return out
    buys  = deals[deals["side"] == "BUY"]
    sells = deals[deals["side"] == "SELL"]
    used: set[int] = set()
    for bi, b in buys.iterrows():
        for si, s in sells.iterrows():
            if si in used or b["qty"] <= 0:
                continue
            if abs(b["qty"] - s["qty"]) / b["qty"] > QTY_MATCH_TOL:
                continue
            same_price = (b["price"] > 0 and
                          abs(b["price"] - s["price"]) / b["price"] <= PRICE_MATCH_TOL)
            used.add(si)
            out.append({
                "qty": b["qty"], "buyer": b["client"], "seller": s["client"],
                "buyer_type": b["client_type"], "seller_type": s["client_type"],
                "buy_price": b["price"], "sell_price": s["price"],
                "same_price": bool(same_price),
                # Same name on both sides of an identical quantity is one entity
                # crossing stock with itself — intraday inventory or wash-like
                # churn. It inflates the headline value while changing nothing,
                # so it has to be separable from a genuine two-party transfer.
                "same_client": (str(b["client"]).strip().upper()
                                == str(s["client"]).strip().upper()),
                "value": b["qty"] * b["price"],
            })
            break
    return out


# ── Per-company CEAVET summary ────────────────────────────────────────────────

def summarize_company(symbol: str, deals: pd.DataFrame,
                      price_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the six-part CEAVET read for one company's deals.

    `price_ctx` is optional and, when supplied, should carry: cmp, ret_since_pct,
    vol_ratio (deal-day volume / 20d average), bars_since. Absent it, the
    Evaluate section reports that confirmation is unavailable instead of
    inventing one.
    """
    d = deals
    buys  = d[d["side"] == "BUY"]
    sells = d[d["side"] == "SELL"]
    buy_val,  sell_val  = float(buys["value"].sum()),  float(sells["value"].sum())
    buy_qty,  sell_qty  = float(buys["qty"].sum()),    float(sells["qty"].sum())
    total_val = buy_val + sell_val
    net_qty   = buy_qty - sell_qty
    vwap = (float((d["price"] * d["qty"]).sum() / d["qty"].sum())
            if float(d["qty"].sum()) else 0.0)

    matches = find_matched_transfers(d)
    matched_qty = sum(m["qty"] for m in matches)
    # Share of the day's crossed quantity that was a pre-agreed transfer.
    transfer_ratio = (matched_qty / buy_qty) if buy_qty else 0.0
    self_cross_qty = sum(m["qty"] for m in matches if m["same_client"])
    self_cross_ratio = (self_cross_qty / buy_qty) if buy_qty else 0.0

    inst_buyers  = sorted(set(buys.loc[buys["client_type"].isin(INSTITUTIONAL), "client"]))
    inst_sellers = sorted(set(sells.loc[sells["client_type"].isin(INSTITUTIONAL), "client"]))
    buyer_types  = sorted(set(buys["client_type"]))
    venues     = sorted(set(d["exchange"]))
    deal_types = sorted(set(d["deal_type"]))

    cmp_ = (price_ctx or {}).get("cmp")
    prem_pct = None
    if cmp_ and vwap:
        prem_pct = (vwap - cmp_) / cmp_ * 100.0

    # ── C: context ────────────────────────────────────────────────────────────
    c = (f"{symbol}: {len(d)} {'/'.join(deal_types).lower()} deal(s) on "
         f"{'/'.join(venues)} totalling ₹{total_val/1e5:,.0f} lakh "
         f"(buy ₹{buy_val/1e5:,.0f}L vs sell ₹{sell_val/1e5:,.0f}L) at a "
         f"volume-weighted ₹{vwap:,.2f}.")
    if prem_pct is not None:
        c += (f" That is a {abs(prem_pct):.1f}% "
              f"{'premium to' if prem_pct >= 0 else 'discount to'} the ₹{cmp_:,.2f} CMP.")

    # ── E: the event ──────────────────────────────────────────────────────────
    if matches:
        m = matches[0]
        if m["same_client"]:
            e = (f"{len(matches)} matched buy/sell pair(s), and the counterparty is "
                 f"the SAME on both sides — {m['buyer']} both bought and sold "
                 f"{m['qty']:,.0f} shares"
                 f"{' at an identical price' if m['same_price'] else ''}. "
                 f"Nothing was transferred; the position simply round-tripped.")
        else:
            e = (f"{len(matches)} matched buy/sell pair(s) — {m['qty']:,.0f} shares moved "
                 f"from {m['seller']} ({m['seller_type']}) to {m['buyer']} ({m['buyer_type']})"
                 f"{' at an identical price on both sides' if m['same_price'] else ''}. "
                 f"Identical quantities do not occur by chance: this was a pre-agreed "
                 f"crossing, not competitive open-market buying.")
    else:
        e = ("No matched buy/sell quantities. The buy and sell sides are unrelated "
             "counterparties trading independently, which is the normal shape of "
             "genuine open-market absorption.")

    # ── A: institutional motive ───────────────────────────────────────────────
    if self_cross_ratio >= 0.5:
        a = ("The same counterparty appears on BOTH sides of matched quantities — "
             "one entity crossing stock with itself. This is intraday inventory "
             "movement or wash-like churn, not a transfer of ownership between "
             "two parties. It inflates the headline deal value while changing "
             "nothing about who owns the company.")
    elif transfer_ratio >= 0.8 and matches:
        a = ("Consistent with a negotiated transfer — promoter/PE stake sale, "
             "inter-scheme transfer, or a custodian moving stock between "
             "accounts. The register changes; the free float does not. Treat "
             "the headline value as a transfer, not as demand.")
    elif inst_buyers and not inst_sellers:
        a = (f"Consistent with institutional accumulation: {', '.join(inst_buyers[:3])} "
             f"on the buy side with no institutional seller opposite. Funds that "
             f"build in one visible print usually have a mandate reason "
             f"(index inclusion, fresh allocation, conviction add).")
    elif inst_sellers and not inst_buyers:
        a = (f"Consistent with institutional distribution or rebalancing: "
             f"{', '.join(inst_sellers[:3])} on the sell side, absorbed by "
             f"non-institutional buyers. Often portfolio rebalancing or "
             f"redemption-driven rather than a company-specific view.")
    elif inst_buyers and inst_sellers:
        a = ("Institutions on both sides — most consistent with a reshuffle "
             "between funds (one exiting, one entering) rather than a "
             "directional view on the company.")
    elif set(buyer_types) <= {"BROKER / PROP"}:
        a = ("Broker/proprietary desks only. This is usually intraday inventory "
             "or client facilitation, and carries no ownership signal.")
    else:
        a = ("Non-institutional counterparties (corporates/individuals). Could be "
             "anything from a genuine strategic buy to related-party churn — the "
             "names, not the size, are what matter here.")

    # ── V: actionable clues ───────────────────────────────────────────────────
    v_bits = [f"Net position change: {net_qty:+,.0f} shares "
              f"({'net accumulation' if net_qty > 0 else 'net distribution' if net_qty < 0 else 'flat — fully crossed'})."]
    if prem_pct is not None:
        if abs(prem_pct) >= PREMIUM_PCT:
            v_bits.append(
                f"Deal struck at a {abs(prem_pct):.1f}% "
                f"{'PREMIUM — buyer paid up for size, a conviction tell' if prem_pct > 0 else 'DISCOUNT — seller wanted out, size over price'}.")
        else:
            v_bits.append(f"Deal price within {abs(prem_pct):.1f}% of CMP — priced at market, no urgency either way.")
    else:
        v_bits.append("CMP unavailable for this scrip, so premium/discount could not be checked.")
    v_bits.append("Buyer type: " + ", ".join(f"{t}" for t in buyer_types) + ".")
    if price_ctx and price_ctx.get("vol_ratio"):
        v_bits.append(f"Deal-day volume ran {price_ctx['vol_ratio']:.1f}× the 20-day average.")
    v = " ".join(v_bits)

    # ── E: evaluation ─────────────────────────────────────────────────────────
    ret = (price_ctx or {}).get("ret_since_pct")
    bars = (price_ctx or {}).get("bars_since")
    if ret is None:
        e2 = ("No post-deal price action yet (deal is same-day, or price history "
              "unavailable for this scrip). Confirmation is pending — this is the "
              "section that decides whether the deal meant anything.")
    elif ret >= 2:
        e2 = (f"Price is {ret:+.1f}% since the deal over {bars} session(s) — the "
              f"buyer is in profit and the market has validated the print.")
    elif ret <= -2:
        e2 = (f"Price is {ret:+.1f}% since the deal over {bars} session(s) — it has "
              f"traded through the deal price. The buyer is underwater, which "
              f"weakens the signal considerably.")
    else:
        e2 = (f"Price is {ret:+.1f}% since the deal over {bars} session(s) — holding "
              f"around the deal level, neither confirmed nor invalidated.")

    # ── T: takeaway ───────────────────────────────────────────────────────────
    # Ordered so the disqualifying cases win: a pure transfer or a broker cross
    # is NOT upgraded by being large or by a friendly tape.
    if self_cross_ratio >= 0.5:
        strength, action = "NOISE", "IGNORE"
        t = ("Self-crossed by a single entity. The headline value is real but "
             "meaningless as a signal — no ownership changed hands. Size alone "
             "is exactly the trap this section exists to catch.")
    elif transfer_ratio >= 0.8 and matches and inst_buyers and not inst_sellers:
        # A negotiated transfer INTO an institution is not open-market demand,
        # but it is a real ownership change by a mandated buyer — the one
        # transfer case that deserves tracking rather than dismissal.
        strength, action = "INFORMATIVE", "TRACK ownership (not a demand signal)"
        t = (f"{', '.join(inst_buyers[:2])} took a negotiated block off a "
             f"non-institutional holder. No open-market demand was created, so "
             f"do not read the print as buying pressure — but an institution "
             f"choosing to size into this name is worth following through the "
             f"next shareholding disclosure. Entry decisions should come from "
             f"the chart, not from this deal.")
    elif transfer_ratio >= 0.8 and matches:
        strength, action = "LOW", "IGNORE as a demand signal"
        t = ("Ownership moved between two known parties at an agreed price; float "
             "and demand are unchanged. Worth noting WHO now owns it — if an "
             "institution took a large position, follow subsequent filings — but "
             "the deal itself is not a reason to act.")
    elif set(buyer_types) <= {"BROKER / PROP"}:
        strength, action = "NOISE", "IGNORE"
        t = "Intermediary flow. No ownership change worth tracking."
    elif inst_buyers and not inst_sellers and net_qty > 0 and (ret is None or ret > -2):
        strength, action = "HIGH", "WATCH for a follow-through entry"
        t = ("Institutional buyer, no institutional seller, net accumulation, and "
             "price has not broken the deal level. This is the configuration worth "
             "a place on the watchlist — confirm with the next shareholding "
             "disclosure and wait for the stock to hold above the deal price "
             "rather than chasing the print.")
    elif inst_sellers and not inst_buyers:
        strength, action = "BEARISH", "WAIT / avoid fresh longs"
        t = ("Institution reducing into non-institutional hands. Even when it is "
             "routine rebalancing, the supply overhang tends to cap rallies until "
             "it clears.")
    elif ret is not None and ret <= -2:
        strength, action = "WEAK", "IGNORE"
        t = ("Price has already traded below the deal price — whatever the buyer "
             "saw, the market has not agreed.")
    else:
        strength, action = "MODERATE", "WAIT for confirmation"
        t = ("Real size changed hands but the counterparty mix does not establish "
             "an institutional view. Let post-deal price action and the next "
             "shareholding pattern decide.")

    return {
        "symbol": symbol,
        "total_value": total_val, "buy_value": buy_val, "sell_value": sell_val,
        "net_qty": net_qty, "vwap": vwap, "premium_pct": prem_pct,
        "deal_count": len(d), "venues": venues, "deal_types": deal_types,
        "matches": matches, "transfer_ratio": transfer_ratio,
        "self_cross_ratio": self_cross_ratio,
        "inst_buyers": inst_buyers, "inst_sellers": inst_sellers,
        "buyer_types": buyer_types,
        "strength": strength, "action": action,
        "ceavet": {"C": c, "E": e, "A": a, "V": v, "E2": e2, "T": t},
    }


# Display rank: signal first, churn last. Sorting purely by deal value puts a
# ₹71,094L self-cross at the top of the page and buries the ₹27,801L mutual-fund
# block below it — the exact inversion this module exists to correct. Value only
# breaks ties within a tier.
STRENGTH_RANK = {
    "HIGH": 0, "INFORMATIVE": 1, "MODERATE": 2, "BEARISH": 3,
    "WEAK": 4, "LOW": 5, "NOISE": 6,
}
ACTIONABLE_STRENGTHS = ("HIGH", "INFORMATIVE", "MODERATE", "BEARISH")


def sort_key(summary: dict[str, Any]) -> tuple:
    return (STRENGTH_RANK.get(summary.get("strength"), 9),
            -float(summary.get("total_value") or 0.0))


def summarize_all(deals: pd.DataFrame,
                  min_value: float = MIN_DEAL_VALUE,
                  price_ctx_fn=None) -> list[dict[str, Any]]:
    """CEAVET summaries for every company clearing `min_value`.

    Ordered by signal strength first and deal value second, so anything graded
    NOISE sinks to the bottom regardless of how large the headline number is.

    `price_ctx_fn(symbol)` may return a price-context dict or None; any
    exception it raises is swallowed so one unfetchable scrip cannot take down
    the whole summary.
    """
    if deals is None or deals.empty:
        return []
    totals = deals.groupby("symbol")["value"].sum().sort_values(ascending=False)
    out = []
    for symbol, total in totals.items():
        if total < min_value:
            continue
        ctx = None
        if price_ctx_fn is not None:
            try:
                ctx = price_ctx_fn(symbol)
            except Exception:
                ctx = None
        out.append(summarize_company(symbol, deals[deals["symbol"] == symbol], ctx))
    out.sort(key=sort_key)
    return out
