#!/usr/bin/env python3
"""
promoter_profit_surprise.py
Second screener angle: restrict the universe to GARP-quality growth
stocks (sustained sales growth + reasonable PEG), then rank by rising
FII + DII institutional conviction within that filtered window only.

Query (screener.in):
  PEG Ratio > 0 AND PEG Ratio < 2 AND
  Sales growth > 15 AND Sales growth 3Years > 15 AND Sales growth 5Years > 15 AND
  (Change in FII holding + Change in DII holding) > 1

NOTE: the gate was previously (promoter + FII) > 1, which silently
excluded stocks with strong FII/DII inflows but flat/falling promoter
holding (e.g. Aditya Infotech, Angel One, Data Patterns) — switched to
FII + DII since that's the actual institutional-conviction signal this
screen is meant to catch. Promoter change is still computed and shown,
just no longer part of the gate.

The GARP clauses (Sales, PEG, multi-year sales growth) are the quality
gate — only stocks that pass ALL of them are considered at all; ranking
by Combined Holding Change happens strictly inside that filtered window,
not across the broader market.

NOTE on DII: screener.in's default column template does not include
"Change in DII holding" even when it's referenced inside the query
expression — same constraint hit earlier with Industry. DII is instead
parsed from each company's quarterly Shareholding Pattern page (see
fetch_dii_change()) and folded into Combined Holding Change.

Run manually:
  py -3 tools/promoter_profit_surprise.py SESSIONID
"""

import sys
import time
from pathlib import Path
from datetime import datetime

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import screener_scraper as sc

try:
    import openpyxl
    from openpyxl.styles import PatternFill, Font
    from openpyxl.utils import get_column_letter
except ImportError:
    sys.exit("Run:  py -3 -m pip install openpyxl")

BASE_DIR = Path(__file__).resolve().parent.parent
import out_paths as _out

QUERY = (
    "PEG Ratio > 0 AND PEG Ratio < 2 AND\n"
    "Sales growth > 15 AND Sales growth 3Years > 15 AND Sales growth 5Years > 15 AND\n"
    "(Change in FII holding + Change in DII holding) > 1"
)

_GREEN = PatternFill("solid", fgColor="C6EFCE")
_AMBER = PatternFill("solid", fgColor="FFEB9C")
_RED = PatternFill("solid", fgColor="FFC7CE")


def fetch_holding_changes(session, slug: str) -> dict[str, float | None]:
    """Self-sources promoter/FII/DII holding change directly from each company's
    quarterly Shareholding Pattern page, rather than relying on screener.in's
    default raw-query columns — those vary depending on which fields the query
    references (FII has been silently dropped from the column set for some
    queries, the same way DII and Industry never appear at all)."""
    soup = sc.fetch_company_page(session, slug)
    if soup is None:
        return {"promoter": None, "fii": None, "dii": None}

    result = {}
    for key, label in (("promoter", "Promoter"), ("fii", "FII"), ("dii", "DII")):
        quarterly = sc._parse_quarterly_holding(soup, label)
        if len(quarterly) < 2:
            result[key] = None
            continue
        quarters_sorted = sorted(quarterly.keys(), key=lambda q: pd.Period(q, freq="Q"))
        latest, prev = quarters_sorted[-1], quarters_sorted[-2]
        result[key] = round(quarterly[latest] - quarterly[prev], 3)
    return result


def build_dataset(sessionid: str, query: str) -> pd.DataFrame:
    session = sc._session(sessionid)
    rows = sc.fetch_all_results(session, query)
    if not rows:
        sys.exit("No results — check the query or whether the cookie is still valid.")

    log = sc.log
    log.info("Fetching promoter/FII/DII holding change for %d companies...", len(rows))
    for i, row in enumerate(rows, 1):
        changes = fetch_holding_changes(session, row["_slug"])
        row["Change in promoter holding (computed)"] = changes["promoter"]
        row["Change in FII holding (computed)"] = changes["fii"]
        row["Change in DII holding (computed)"] = changes["dii"]
        time.sleep(1.5)
        if i % 25 == 0:
            log.info("  holding lookup %d/%d", i, len(rows))

    df = pd.DataFrame(rows).drop(columns=["_slug"], errors="ignore")
    for col in df.columns:
        if col == "Name":
            continue
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")

    promoter_col = "Change in promoter holding (computed)"
    fii_col = "Change in FII holding (computed)"
    dii_col = "Change in DII holding (computed)"
    profit_growth_col = next((c for c in df.columns if "profit growth" in c.lower()), None)

    df["Combined Holding Change"] = df[[fii_col, dii_col]].sum(axis=1, skipna=True)
    df = df.sort_values("Combined Holding Change", ascending=False).reset_index(drop=True)

    for key, col in (("promoter", promoter_col), ("FII", fii_col), ("DII", dii_col)):
        missing = df[col].isna().sum()
        if missing:
            log.warning("%d/%d stocks missing %s holding data (no shareholding pattern match)", missing, len(df), key)

    df.attrs["promoter_col"] = promoter_col
    df.attrs["fii_col"] = fii_col
    df.attrs["dii_col"] = dii_col
    df.attrs["profit_growth_col"] = profit_growth_col
    return df


def write_excel_sheet(df: pd.DataFrame, xlsx_path: Path) -> None:
    if xlsx_path.exists():
        wb = openpyxl.load_workbook(xlsx_path)
    else:
        wb = openpyxl.Workbook()
        wb.remove(wb.active)

    sheet_name = "FII+DII GARP Conviction"
    for old_name in ("Promoter+FII Profit Surprise", "Promoter+FII GARP Conviction", sheet_name):
        if old_name in wb.sheetnames:
            del wb[old_name]
    ws = wb.create_sheet(sheet_name)

    ws["A1"] = "FII + DII conviction within GARP-quality growth filter"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    ws["A2"].font = Font(italic=True, color="5F5E5A")
    ws["A3"] = QUERY.replace("\n", " ")
    ws["A3"].font = Font(size=9, color="5F5E5A")
    ws["A4"] = ("Promoter/FII/DII holding change columns marked (computed) are self-sourced from "
                "each company's quarterly Shareholding Pattern page, not screener.in's raw-query "
                "columns — those vary by query and can silently drop fields. Combined Holding "
                "Change = FII + DII only (the screen's gate); Promoter change is shown for "
                "context but no longer part of the filter.")
    ws["A4"].font = Font(size=9, italic=True, color="5F5E5A")
    header_row = 6

    for col_idx, col_name in enumerate(df.columns, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=col_name)
        cell.font = Font(bold=True)

    profit_growth_col = df.attrs.get("profit_growth_col")
    for r, row in enumerate(df.itertuples(index=False), header_row + 1):
        for c, val in enumerate(row, 1):
            ws.cell(row=r, column=c, value=val)

    col_map = {name: idx + 1 for idx, name in enumerate(df.columns)}
    combined_idx = col_map["Combined Holding Change"]
    for r in range(header_row + 1, header_row + 1 + len(df)):
        val = ws.cell(row=r, column=combined_idx).value or 0
        ws.cell(row=r, column=combined_idx).fill = _GREEN if val >= 3 else (_AMBER if val >= 1 else _RED)
        if profit_growth_col and profit_growth_col in col_map:
            pg_val = ws.cell(row=r, column=col_map[profit_growth_col]).value or 0
            ws.cell(row=r, column=col_map[profit_growth_col]).fill = _GREEN if pg_val >= 50 else _AMBER

    ws.freeze_panes = ws.cell(row=header_row + 1, column=1).coordinate
    for col_idx, col_name in enumerate(df.columns, 1):
        col_letter = get_column_letter(col_idx)
        max_len = max(len(str(col_name)), *(len(str(v)) for v in df[col_name].head(50)))
        ws.column_dimensions[col_letter].width = min(max_len + 2, 35)

    wb.save(xlsx_path)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: py -3 tools/promoter_profit_surprise.py SESSIONID")

    sessionid = sys.argv[1]
    df = build_dataset(sessionid, QUERY)

    date_str = datetime.today().strftime("%Y%m%d")
    csv_path = _out.out_path(f"promoter_profit_surprise_{date_str}.csv")
    df.to_csv(csv_path, index=False)
    print(f"Saved -> {csv_path}  ({len(df)} rows)")

    xlsx_path = _out.out_path(f"sector_rotation_{date_str}.xlsx")
    write_excel_sheet(df, xlsx_path)
    print(f"Added 'FII+DII GARP Conviction' sheet -> {xlsx_path}")
