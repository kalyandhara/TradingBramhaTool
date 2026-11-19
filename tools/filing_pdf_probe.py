#!/usr/bin/env python3
"""filing_pdf_probe.py — B-112's DATA PROBE: are deal amounts recoverable from
the filing PDFs, before anyone builds an extractor?

`nse_filings_feed.amount_from` reads an amount only when the filing's one-line
API text states one, and most material filings carry the figure only in the
attached PDF ("₹126 Cr contract" filed as "General Updates — Reg. 30"). B-112
asked three questions, in the order that can kill it:

  1. TEXT LAYER   Are the attachments text PDFs, or scans that need OCR?
  2. RECOVERY     Over the extracted text, how often does the SAME regex find
                  an amount, on the filings whose API text had none?
  3. PRECISION    When it finds one, is it the deal amount, or a face value
                  ("Rs. 2 each"), share capital, or page furniture?

── The bars, committed here BEFORE the first run ─────────────────────────────
Build the extractor only if ALL THREE pass. Precision is judged by hand on a
fixed random sample of recoveries (the probe prints them with context), because
deciding "is this the deal amount" is exactly what nothing here can automate.
"""
from __future__ import annotations

import argparse
import io
import json
import random
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# ── pre-committed (2026-10-30, before the first run) ─────────────────────────
TEXT_LAYER_BAR = 0.80        # ≥80% of fetched PDFs carry extractable text
RECOVERY_BAR = 0.50          # regex finds an amount on ≥50% of text PDFs in the deal buckets
PRECISION_BAR = 0.80         # ≥80% of a hand-checked sample are the deal amount
MIN_TEXT_CHARS = 200         # fewer non-space characters than this = no text layer
PRECISION_SAMPLE = 20
MAX_PAGES = 6                # the amount, when present, is on the first pages
PER_GROUP = 60               # PDFs per group; two groups
SEED = 112
DEAL_BUCKETS = ("ORDER_WIN", "M&A", "FUND_RAISE", "CAPACITY")
GENERIC = re.compile(r"^\s*(general updates|updates)\s*$", re.I)
IST = timezone(timedelta(hours=5, minutes=30))


def group_of(row: dict, bucket: str | None, has_amount: bool) -> str | None:
    """`deal`: a deal-type bucket whose API text gave no amount.
    `generic`: filed under a generic label, whatever the text says.
    None: not part of the probe."""
    if GENERIC.match(row.get("category", "")):
        return "generic"
    if bucket in DEAL_BUCKETS and not has_amount:
        return "deal"
    return None


def has_text(text: str) -> bool:
    return len(re.sub(r"\s+", "", text or "")) >= MIN_TEXT_CHARS


def context(text: str, amount_re, width: int = 70) -> str | None:
    m = amount_re.search(text or "")
    if not m:
        return None
    a, b = max(0, m.start() - width), min(len(text), m.end() + width)
    return re.sub(r"\s+", " ", text[a:b]).strip()


def amount_context(text: str, amount: str | None, width: int = 70) -> str | None:
    """Context around the figure `amount_from` CHOSE (it may skip earlier
    per-unit prices), found by its digits. v1 showed the regex's first match,
    which was the same thing only while the regex took the first match."""
    if not amount:
        return None
    m = re.search(r"\d[\d,.]*", amount)
    return context(text, re.compile(re.escape(m.group(0)))) if m else None


def verdict(stats: dict) -> dict:
    tl = stats["text_pdfs"] / stats["fetched"] if stats["fetched"] else 0.0
    rec = (stats["deal_recovered"] / stats["deal_text_pdfs"]
           if stats["deal_text_pdfs"] else 0.0)
    return {"text_layer": tl, "text_layer_pass": tl >= TEXT_LAYER_BAR,
            "recovery": rec, "recovery_pass": rec >= RECOVERY_BAR}


def extract(pdf: bytes) -> tuple[str, int]:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf))
    pages = len(reader.pages)
    text = "\n".join((reader.pages[i].extract_text() or "")
                     for i in range(min(pages, MAX_PAGES)))
    return text, pages


def main() -> int:
    ap = argparse.ArgumentParser(description="B-112 filing-PDF data probe")
    ap.add_argument("--days", type=int, default=5)
    ap.add_argument("--out", required=True, help="JSON results path")
    ap.add_argument("--urls-from", default=None,
                    help="re-score the exact PDFs of an earlier run's JSON (v2 used this, "
                         "so a regex fix is judged on the same documents)")
    a = ap.parse_args()

    import nse_filings_feed as ff
    import nse_shareholding_fetch as nsf

    session = nsf._new_session()
    if a.urls_from:
        prior = json.loads(Path(a.urls_from).read_text(encoding="utf-8"))["results"]
        picked = {g: [{"symbol": r["symbol"], "category": r["category"],
                       "bucket": r["bucket"], "pdf": r["pdf"]}
                      for r in prior if r["group"] == g] for g in ("deal", "generic")}
        print(f"re-scoring {sum(map(len, picked.values()))} PDFs from {a.urls_from}")
    else:
        raw = ff.fetch(a.days, session=session, today=datetime.now(IST).date())
        if not raw:
            print("NSE announcements did not answer"); return 2
        groups: dict[str, list[dict]] = {"deal": [], "generic": []}
        for r in raw:
            if not r.get("pdf", "").lower().endswith(".pdf"):
                continue
            b = ff.bucket_of(r["category"], r["text"])
            g = group_of(r, b, ff.amount_from(r["text"]) is not None)
            if g:
                groups[g].append({**r, "bucket": b})
        rng = random.Random(SEED)
        picked = {g: rng.sample(rows, min(PER_GROUP, len(rows))) for g, rows in groups.items()}
        print(f"{len(raw)} filings over {a.days} days · eligible: deal {len(groups['deal'])}, "
              f"generic {len(groups['generic'])} · sampling {sum(map(len, picked.values()))}")

    results = []
    for g, rows in picked.items():
        for r in rows:
            rec = {"group": g, "symbol": r["symbol"], "category": r["category"],
                   "bucket": r["bucket"], "pdf": r["pdf"]}
            try:
                resp = session.get(r["pdf"], headers=nsf.HEADERS, timeout=40)
                rec["http"] = resp.status_code
                rec["bytes"] = len(resp.content)
                if resp.status_code == 200 and resp.content[:4] == b"%PDF":
                    text, pages = extract(resp.content)
                    rec.update(pages=pages, chars=len(re.sub(r"\s+", "", text)),
                               text_layer=has_text(text),
                               amount=ff.amount_from(text) if has_text(text) else None,
                               context=amount_context(text, ff.amount_from(text)))
                else:
                    rec["error"] = "not a PDF" if resp.status_code == 200 else f"HTTP {resp.status_code}"
            except Exception as exc:
                rec["error"] = f"{type(exc).__name__}: {exc}"[:160]
            results.append(rec)
            time.sleep(0.4)                     # be polite to nsearchives

    fetched = [r for r in results if "pages" in r]
    deal_text = [r for r in fetched if r["group"] == "deal" and r["text_layer"]]
    stats = {
        "sampled": len(results), "fetched": len(fetched),
        "failed": len(results) - len(fetched),
        "text_pdfs": sum(r["text_layer"] for r in fetched),
        "deal_text_pdfs": len(deal_text),
        "deal_recovered": sum(r["amount"] is not None for r in deal_text),
        "generic_text_pdfs": sum(r["text_layer"] for r in fetched if r["group"] == "generic"),
        "generic_recovered": sum(r["amount"] is not None for r in fetched
                                 if r["group"] == "generic" and r["text_layer"]),
        "median_kb": (sorted(r["bytes"] for r in fetched)[len(fetched) // 2] / 1024
                      if fetched else None),
        "max_kb": max((r["bytes"] for r in fetched), default=0) / 1024,
    }
    v = verdict(stats)
    recovered = [r for r in fetched if r.get("amount")]
    hand = random.Random(SEED).sample(recovered, min(PRECISION_SAMPLE, len(recovered)))
    Path(a.out).write_text(json.dumps({"run": datetime.now().isoformat(timespec="seconds"),
                                       "stats": stats, "verdict": v,
                                       "precision_sample": hand, "results": results},
                                      ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"stats": stats, "verdict": v}, indent=1))
    print(f"\nPRECISION SAMPLE ({len(hand)}) — judge each by hand:")
    for i, r in enumerate(hand, 1):
        print(f"{i:>2}. {r['symbol']:<12} {r['group']:<7} {r['amount']!s:<22} … {r['context']}")
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.exit(main())
