"""Tests for the on-demand plan picker — B-109.

The UI itself is Streamlit and is verified by running the app. What is pinned
here is the part that decides WHAT the reader is offered, because that is where
a shortlist quietly turns into something else:

  * the picker's order is the SHORTLIST's order — re-sorting it alphabetically
    would hide which name the desk ranked first;
  * a name appears once, however many rows mention it;
  * an empty or column-less frame offers nothing rather than erroring.
"""
import pandas as pd
import pytest

import plan_on_demand as pod


def _sl(symbols, column="symbol"):
    return pd.DataFrame({column: symbols, "rank": range(1, len(symbols) + 1)})


def test_order_follows_the_ranking_not_the_alphabet():
    """The shortlist arrives ranked. A sorted picker would bury #1 under a Z."""
    assert pod.eligible_symbols(_sl(["ZOMATO", "ABB", "MARUTI"])) == \
        ["ZOMATO", "ABB", "MARUTI"]


def test_a_repeated_symbol_is_offered_once():
    assert pod.eligible_symbols(_sl(["ABB", "abb", "MARUTI", "ABB"])) == \
        ["ABB", "MARUTI"]


def test_symbols_are_normalised_for_the_council():
    assert pod.eligible_symbols(_sl([" tcs ", "infy"])) == ["TCS", "INFY"]


def test_blanks_and_nulls_are_dropped_not_stringified():
    """`str(None)` is "NONE" — offering that would send the council fetching a
    symbol that does not exist. Found by writing the test, not by reading."""
    assert pod.eligible_symbols(
        _sl(["ABB", "", "  ", None, float("nan")])) == ["ABB"]


def test_an_empty_shortlist_offers_nothing():
    assert pod.eligible_symbols(pd.DataFrame()) == []
    assert pod.eligible_symbols(None) == []


def test_a_frame_without_the_column_offers_nothing_rather_than_raising():
    """A stored shortlist whose schema changed must not take the page down."""
    assert pod.eligible_symbols(pd.DataFrame({"ticker": ["ABB"]})) == []


def test_a_different_column_can_be_named():
    assert pod.eligible_symbols(pd.DataFrame({"ticker": ["ABB"]}),
                                column="ticker") == ["ABB"]


def test_the_blurb_says_the_shortlist_does_not_plan():
    """The framing is the feature: this page ranks, and planning is a step the
    reader takes afterwards for one name."""
    assert "ranks" in pod.BLURB and "does not plan" in pod.BLURB
