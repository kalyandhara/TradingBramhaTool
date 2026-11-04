"""Tests for the B-112 filing-PDF probe's pure parts.

Pinned: which filings enter which group; the text-layer threshold counts
characters, not whitespace; the verdict divides by the right denominators.
"""
import re

import filing_pdf_probe as p


def test_groups():
    gen = {"category": "General Updates"}
    assert p.group_of(gen, None, False) == "generic"
    assert p.group_of(gen, "ORDER_WIN", True) == "generic"
    deal = {"category": "Bagging/Receiving of orders/contracts"}
    assert p.group_of(deal, "ORDER_WIN", False) == "deal"
    assert p.group_of(deal, "ORDER_WIN", True) is None      # API text already has it
    assert p.group_of(deal, "RESULTS", False) is None


def test_text_layer_ignores_whitespace():
    assert not p.has_text(" \n" * 500 + "x" * 199)
    assert p.has_text("x" * 200)


def test_verdict_denominators():
    v = p.verdict({"fetched": 10, "text_pdfs": 8, "deal_text_pdfs": 4, "deal_recovered": 2})
    assert v["text_layer"] == 0.8 and v["text_layer_pass"]
    assert v["recovery"] == 0.5 and v["recovery_pass"]
    assert not p.verdict({"fetched": 0, "text_pdfs": 0, "deal_text_pdfs": 0,
                          "deal_recovered": 0})["text_layer_pass"]


def test_context_window():
    assert p.context("a contract worth Rs. 126 crore from X", re.compile(r"Rs\. 126 crore"),
                     width=5) == "orth Rs. 126 crore from"
