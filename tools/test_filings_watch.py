"""Tests for filings_watch — the always-on NSE filings listener for MY names.

What is pinned:
  * a name is mine for a stated reason, and a held name outranks a watched one;
  * a filing already sent is never sent again (the key survives re-polls);
  * filings on names that are not mine never reach the email;
  * the email says what the filing is and links the PDF, never invents an amount.
"""
import filings_watch as fw


def _row(sym, bucket="ORDER_WIN", when="29-Oct-2026 10:05:11",
         category="Bagging/Receiving of orders/contracts", amount=None, pdf="x.pdf"):
    return {"symbol": sym, "company": f"{sym} Ltd", "when": when, "bucket": bucket,
            "category": category, "headline": f"{sym} order win", "amount": amount,
            "pdf": pdf, "text": ""}


def test_held_outranks_watched_and_picked():
    names = fw.my_names(held=["HERANBA"], watched=["HERANBA", "TRF"],
                        picked=["TRF", "NAZARA"])
    assert names == {"HERANBA": "held", "TRF": "watchlist", "NAZARA": "pick"}


def test_symbols_are_normalised():
    names = fw.my_names(held=["heranba.ns "], watched=[], picked=[])
    assert names == {"HERANBA": "held"}


def test_only_my_unseen_filings_are_new():
    names = {"TRF": "watchlist"}
    rows = [_row("TRF"), _row("RELIANCE")]
    seen = set()
    first = fw.new_filings(rows, names, seen)
    assert [r["symbol"] for r in first] == ["TRF"]
    assert first[0]["why"] == "watchlist"
    # the same poll 30 minutes later sends nothing
    assert fw.new_filings(rows, names, seen) == []


def test_key_distinguishes_two_filings_same_day():
    a = _row("TRF", when="29-Oct-2026 10:05:11")
    b = _row("TRF", when="29-Oct-2026 14:40:02")
    assert fw.filing_key(a) != fw.filing_key(b)


def test_email_puts_held_first_and_never_invents_amount():
    rows = [{**_row("TRF"), "why": "watchlist"},
            {**_row("HERANBA", bucket="GOVERNANCE", category="Resignation"), "why": "held"}]
    subject, body = fw.render_email(rows)
    assert "2 filing" in subject
    assert body.index("HERANBA") < body.index("TRF")
    assert "x.pdf" in body
    assert "₹" not in body          # no amount in the text → none shown


# ── B-198: bulk / block deals on my names ─────────────────────────────────────
def _deal(sym, client="ABC FUND", side="BUY", qty=100000.0, deal_type="BULK"):
    return {"date": "30-OCT-2026", "symbol": sym, "name": f"{sym} Ltd", "client": client,
            "side": side, "qty": qty, "price": 50.0, "value": qty * 50.0,
            "exchange": "NSE", "deal_type": deal_type}


def test_only_my_unseen_deals_are_new():
    names = {"HERANBA": "held"}
    deals = [_deal("HERANBA"), _deal("RELIANCE")]
    seen = set()
    first = fw.new_deals(deals, names, seen)
    assert [d["symbol"] for d in first] == ["HERANBA"]
    assert first[0]["why"] == "held"
    assert fw.new_deals(deals, names, seen) == []


def test_two_tickets_same_client_same_day_are_two_deals():
    assert fw.deal_key(_deal("X", qty=100.0)) != fw.deal_key(_deal("X", qty=200.0))
    assert fw.deal_key(_deal("X", side="BUY")) != fw.deal_key(_deal("X", side="SELL"))


def test_email_carries_deals_section():
    subject, body = fw.render_email([], [{**_deal("HERANBA", side="SELL"), "why": "held"}])
    assert "1 deal" in subject and "on held" in subject
    assert "HERANBA (held) · BULK SELL" in body
    assert "ABC FUND" in body and "₹50" in body


def test_same_client_both_sides_is_marked_as_round_trip():
    deals = [{**_deal("PASHUPATI", client="HRTI PRIVATE LIMITED", side="BUY", qty=880197.0),
              "why": "pick"},
             {**_deal("PASHUPATI", client="HRTI PRIVATE LIMITED", side="SELL", qty=842978.0),
              "why": "pick"},
             {**_deal("PASHUPATI", client="SOME FUND", side="BUY"), "why": "pick"}]
    _, body = fw.render_email([], deals)
    assert body.count("bought AND sold") == 2      # both HRTI tickets, not the fund
    assert "net +37,219" in body
