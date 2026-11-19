"""crt_sweep_overlap.py — the coverage arithmetic and the pre-registered verdict."""
from __future__ import annotations

import crt_sweep_overlap as ov

DATES = [f"2026-01-{d:02d}" for d in range(1, 31)]


def _row(sweeps, crt):
    return {"symbol": "X", "dates": DATES, "sweeps": sweeps,
            "crt": [{"start": s, "end": e, "pierce_atr": 0.5} for s, e in crt]}


def test_covered_only_inside_the_widened_week():
    r = _row(["2026-01-12"], [("2026-01-05", "2026-01-09"), ("2026-01-20", "2026-01-24")])
    cov = ov.coverage([r])
    assert cov["crt_events"] == 2 and cov["sweep_events"] == 1
    assert cov["by_tol"][0]["crt_covered"] == 0          # sweep is 3 days after week 1
    assert cov["by_tol"][2]["crt_covered"] == 0
    assert cov["by_tol"][5]["crt_covered"] == 1          # within 5 trading days
    assert cov["by_tol"][5]["sweeps_in_crt"] == 1


def test_verdict_applies_the_registered_bar():
    base = {"crt_events": 200, "sweep_events": 50,
            "by_tol": {5: {"crt_covered_pct": 80.0}}}
    assert ov.verdict(base).startswith("SUBSET")
    base["by_tol"][5]["crt_covered_pct"] = 79.9
    assert ov.verdict(base).startswith("NOT A SUBSET")
    base["crt_events"] = 149
    assert ov.verdict(base).startswith("TOO RARE")
