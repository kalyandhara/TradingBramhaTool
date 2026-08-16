#!/usr/bin/env python3
"""
sbc_confluence.py — per-instrument actionable confluence (Steps 1-4).

Turns the SBC engine outputs into a single tradeable verdict for one
instrument, the way the reference tool's "6-Condition Analysis" does — here
across the four steps whose engines we have:

  Step 1 — Panchanga      (sbc_panchang: Bhadra / tithi filter)
  Step 2 — SBC Canvas     (sbc_scoring vedhas: market fear/stress level)
  Step 3 — Trading Signals(sbc_scoring sector score for the instrument)
  Step 4 — Nama Nakshatra (this module: the nakshatra's activity nature)

Each step returns PASS / CAUTION / FAIL. Their confluence gives a verdict
(PROCEED / CAUTION / STAND ASIDE), a position-size band, and the trade
direction — plus the next reversal window as the timing gate.

KEY: instrument-specific inverted logic. Safe-haven assets (Gold, Silver, USD,
JPY, CHF) INVERT the market — malefic vedhas = fear = a safe-haven BID (bullish
for them). A bearish Nama (fierce/Ugra nakshatra) is likewise fear → the
safe-haven price often RISES. Risk assets (equities, crypto, most FX) read the
normal way: malefic-dominant = risk-off = bearish.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional

import sbc_nama as nama
import sbc_scoring as sbcs
import sbc_panchang as sbcp

# --- Instrument classification ---------------------------------------------
SAFE_HAVEN = {
    "Gold", "Silver", "USD/INR", "Yen JPY", "Swiss CHF", "Dollar USD",
}


def is_safe_haven(instrument: str) -> bool:
    return instrument in SAFE_HAVEN


# --- Nakshatra activity nature (7-fold muhurta classification) --------------
# Ugra/Tikshna = fierce/sharp -> bearish/fear tendency; Mridu/Kshipra = soft/
# swift -> positive; Sthira = fixed/stable; Chara = movable/volatile;
# Mishra = mixed. Used for the Nama step's directional lean.
NAKSHATRA_NATURE: Dict[str, str] = {
    # Kshipra (swift/light)
    "Ashwini": "Kshipra", "Pushya": "Kshipra", "Hasta": "Kshipra",
    # Mridu (tender/soft)
    "Mrigashira": "Mridu", "Chitra": "Mridu", "Anuradha": "Mridu",
    "Revati": "Mridu",
    # Sthira (fixed)
    "Rohini": "Sthira", "Uttara Phalguni": "Sthira",
    "Uttara Ashadha": "Sthira", "Uttara Bhadrapada": "Sthira",
    # Chara (movable)
    "Punarvasu": "Chara", "Swati": "Chara", "Shravana": "Chara",
    "Dhanishta": "Chara", "Shatabhisha": "Chara",
    # Ugra (fierce/cruel)
    "Bharani": "Ugra", "Magha": "Ugra", "Purva Phalguni": "Ugra",
    "Purva Ashadha": "Ugra", "Purva Bhadrapada": "Ugra",
    # Mishra (mixed)
    "Krittika": "Mishra", "Vishakha": "Mishra",
    # Tikshna (sharp/dreadful)
    "Ardra": "Tikshna", "Ashlesha": "Tikshna", "Jyeshtha": "Tikshna",
    "Mula": "Tikshna",
}
NATURE_TENDENCY = {"Mridu": 0.7, "Kshipra": 0.5, "Sthira": 0.2, "Chara": 0.0,
                   "Mishra": -0.1, "Tikshna": -0.5, "Ugra": -0.7}
NATURE_LABEL = {"Ugra": "Fierce (Ugra)", "Tikshna": "Sharp (Tikshna)",
                "Mridu": "Tender (Mridu)", "Kshipra": "Swift (Kshipra)",
                "Sthira": "Fixed (Sthira)", "Chara": "Movable (Chara)",
                "Mishra": "Mixed (Mishra)"}

PASS, CAUTION, FAIL = "PASS", "CAUTION", "FAIL"


@dataclass
class StepResult:
    name: str
    status: str                # PASS | CAUTION | FAIL
    headline: str
    detail: str


@dataclass
class Confluence:
    instrument: str
    nakshatra: str
    safe_haven: bool
    direction: str             # BULLISH | BEARISH | NEUTRAL
    steps: List[StepResult]
    green: int
    caution: int
    fail: int
    verdict: str               # PROCEED | CAUTION | STAND ASIDE
    size_band: str
    rationale: str


def _step_panchanga(inst: str, safe: bool, pan: sbcp.Panchang) -> StepResult:
    if pan.bhadra_active:
        hl = "Bhadra/Vishti Karana ACTIVE — blocks new official positions"
        if safe:
            hl = ("Bhadra ACTIVE — " + inst +
                  " gets +fear-buying bull, but avoid leveraged entries")
        return StepResult("Panchanga", CAUTION, hl,
                          f"Bhadra active · {pan.tithi_name} · {pan.vara}")
    if pan.tithi_name.endswith("Ashtami") and pan.paksha == "Krishna":
        return StepResult("Panchanga", CAUTION,
                          "Krishna Ashtami — weak for fresh longs; trade light",
                          f"{pan.tithi_name} · {pan.vara}")
    return StepResult("Panchanga", PASS, "Panchanga clear for entries",
                      f"{pan.tithi_name} · {pan.vara}")


def _step_sbc_canvas(inst: str, safe: bool,
                     bias: sbcs.MarketBias) -> StepResult:
    mal, ben = bias.malefic_count, bias.benefic_count
    fear = mal >= ben
    if safe:
        if fear:
            return StepResult(
                "SBC Canvas", PASS,
                f"{mal} malefic vedhas → fear/stress → {inst} BULLISH "
                "(safe-haven bid)",
                f"{mal} malefic · {ben} benefic · safe-haven inversion applies")
        return StepResult(
            "SBC Canvas", CAUTION,
            f"Calm grid ({ben} benefic ≥ {mal} malefic) — safe-haven bid weak",
            f"{mal} malefic · {ben} benefic")
    # risk asset
    if not fear:
        return StepResult(
            "SBC Canvas", PASS,
            f"{ben} benefic vedhas → risk-on → {inst} supported",
            f"{ben} benefic · {mal} malefic")
    return StepResult(
        "SBC Canvas", FAIL,
        f"{mal} malefic vedhas → risk-off/stress → {inst} pressured",
        f"{mal} malefic · {ben} benefic")


def _step_trading_signals(inst: str, safe: bool,
                          sc: Optional[sbcs.SectorScore],
                          bias: sbcs.MarketBias) -> StepResult:
    pl = " ".join(sc.hitting_planets) if sc and sc.hitting_planets \
        else "no direct vedha"
    nak = sc.nakshatra if sc else "?"
    score = sc.score if sc else 0.0
    if score > 0:
        return StepResult("Trading Signals", PASS,
                          f"Sector score {score:+.2f} — {inst} support",
                          f"{nak} · {pl}")
    # safe-haven hedge: a fear-dominant grid supports the haven even with no
    # direct vedha on its nakshatra (the classic "malefic vedha hedge").
    if safe and bias.malefic_count >= bias.benefic_count:
        return StepResult(
            "Trading Signals", PASS,
            f"Mild support via safe-haven hedge — {bias.malefic_count} "
            f"malefic vedha hedge (fear bid)",
            f"{nak} · {pl} · direct score {score:+.2f}")
    if score < 0:
        st = CAUTION if safe else FAIL
        return StepResult("Trading Signals", st,
                          f"Sector score {score:+.2f} ({sc.label if sc else '-'})",
                          f"{nak} · {pl}")
    return StepResult("Trading Signals", CAUTION,
                      "Sector score flat (no direct vedha) — low conviction",
                      f"{nak} · {pl}")


def _step_nama(inst: str, safe: bool, nak: str) -> StepResult:
    nature = NAKSHATRA_NATURE.get(nak, "Chara")
    tend = NATURE_TENDENCY[nature]
    label = NATURE_LABEL[nature]
    if safe:
        if tend < 0:
            return StepResult(
                "Nama Nakshatra", CAUTION,
                f"{label} — bearish nama suppresses {inst}'s commodity signal; "
                "safe-haven demand captured in Step 2",
                f"{nak} · bearish nama = fear → {inst} price often RISES")
        return StepResult("Nama Nakshatra", PASS,
                          f"{label} — supportive nama for {inst}",
                          f"{nak} · tendency {tend:+.1f}")
    if tend > 0.1:
        return StepResult("Nama Nakshatra", PASS,
                          f"{label} — bullish nama tendency for {inst}",
                          f"{nak} · tendency {tend:+.1f}")
    if tend < 0:
        return StepResult("Nama Nakshatra", FAIL,
                          f"{label} — bearish nama tendency for {inst}",
                          f"{nak} · tendency {tend:+.1f}")
    return StepResult("Nama Nakshatra", CAUTION,
                      f"{label} — neutral/volatile nama", f"{nak}")


def evaluate(instrument: str, planets, vedas, bias, panchang) -> Confluence:
    """Run Steps 1-4 for one instrument and produce the confluence verdict."""
    safe = is_safe_haven(instrument)
    res = nama.resolve_nakshatra(instrument)
    nak = res[0] if res else "?"
    sc = next((s for s in sbcs.sector_scores(vedas, [instrument])
               if s.sector == instrument), None)

    steps = [
        _step_panchanga(instrument, safe, panchang),
        _step_sbc_canvas(instrument, safe, bias),
        _step_trading_signals(instrument, safe, sc, bias),
        _step_nama(instrument, safe, nak),
    ]
    green = sum(1 for s in steps if s.status == PASS)
    caution = sum(1 for s in steps if s.status == CAUTION)
    fail = sum(1 for s in steps if s.status == FAIL)

    # direction: safe-haven bull when fear dominates; else follow bias
    if safe:
        direction = "BULLISH" if bias.malefic_count >= bias.benefic_count \
            else "NEUTRAL"
    else:
        direction = ("BULLISH" if bias.label == "BULLISH"
                     else "BEARISH" if bias.label == "BEARISH" else "NEUTRAL")

    if green >= 3 and fail == 0:
        verdict, size = "PROCEED", "50–75% size" if green == 3 else "full size"
    elif green >= 3:
        verdict, size = "PROCEED (guarded)", "50% size"
    elif green == 2:
        verdict, size = "CAUTION", "25–50% size"
    else:
        verdict, size = "STAND ASIDE", "no fresh entry"

    rationale = (f"{green}/4 green · {caution} caution · {fail} fail. "
                 f"{'Safe-haven inversion applied. ' if safe else ''}"
                 f"Bias thesis: {instrument} {direction}.")
    return Confluence(instrument=instrument, nakshatra=nak, safe_haven=safe,
                      direction=direction, steps=steps, green=green,
                      caution=caution, fail=fail, verdict=verdict,
                      size_band=size, rationale=rationale)


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    from sarvatobhadra_chakra import compute_planets
    planets = compute_planets()
    vedas = sbcs.cast_vedas(planets)
    bias = sbcs.market_bias(vedas)
    pan = sbcp.compute_panchang()
    for inst in ["Gold", "NIFTY 50", "Bitcoin", "Silver"]:
        c = evaluate(inst, planets, vedas, bias, pan)
        print(f"\n=== {inst} ({c.nakshatra}) — {c.verdict} · {c.size_band} "
              f"· {c.direction} ===")
        print(f"  {c.rationale}")
        for s in c.steps:
            print(f"   [{s.status:7s}] {s.name}: {s.headline}")
