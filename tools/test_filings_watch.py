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
