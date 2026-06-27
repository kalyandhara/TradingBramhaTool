#!/usr/bin/env python3
"""
sector_rotation.py
Sector-wise institutional liquidity-grab tracker.

Input:  a screener.in CSV/XLSX export of the FII/DII holding-change query
        (must include an "Industry" column — add it via Edit Columns
        before exporting). Default query this is built for:

  Market Capitalization > 1000 AND
  Current price > 30 AND
  (Change in FII holding > 0.5 OR Change in FII holding < -0.5)

Steps:
  1. Read the export, aggregate Change in FII/DII holding % by sector,
     weighted by market cap (not just stock count).
  2. Pull trailing-1Y NSE/BSE sectoral index returns via yfinance.
  3. Combine into a per-sector rotation bias:
       inflow + price strength   -> "confirmed bullish rotation"
       inflow + price weakness   -> "early accumulation / contrarian watch"
       outflow + price strength  -> "distribution into strength (caution)"
       outflow + price weakness  -> "confirmed bearish rotation"
  4. Export ranked sector table (top 5 highlighted) to Excel.

Run manually:  py -3 tools/sector_rotation.py path/to/export.csv
"""

import sys
import time
from pathlib import Path

import pandas as pd

try:
    import yfinance as yf
except ImportError:
    sys.exit("Run:  py -3 -m pip install yfinance")

try:
    import openpyxl
    from openpyxl.styles import PatternFill, Font
    from openpyxl.utils import get_column_letter
except ImportError:
    sys.exit("Run:  py -3 -m pip install openpyxl")

BASE_DIR = Path(__file__).resolve().parent.parent

# NSE sectoral index proxies (Yahoo Finance tickers) keyed by screener.in's
# granular "Industry" label (NOT the broader "Sector" label — screener.in's
# Industry field is far more fine-grained, ~130+ distinct values observed in
# a real 484-stock export on 2026-06-20). Extend this map as new Industry
# labels show up in future exports; unmapped sectors are intentionally left
# as "unscored" rather than guessed, to avoid silently misclassifying bias.
SECTOR_INDEX_MAP = {
    # Banking & Financial Services
    "Private Sector Bank":                 "^NSEBANK",
    "Public Sector Bank":                  "^NSEBANK",
    "Other Bank":                          "^NSEBANK",
    "Non Banking Financial Company (NBFC)": "NIFTY_FIN_SERVICE.NS",
    "Housing Finance Company":             "NIFTY_FIN_SERVICE.NS",
    "Holding Company":                     "NIFTY_FIN_SERVICE.NS",
    "Investment Company":                  "NIFTY_FIN_SERVICE.NS",
    "Financial Institution":               "NIFTY_FIN_SERVICE.NS",
    "Financial Technology (Fintech)":      "NIFTY_FIN_SERVICE.NS",
    "Asset Management Company":            "NIFTY_FIN_SERVICE.NS",
    "Stockbroking & Allied":               "NIFTY_FIN_SERVICE.NS",
    "Other Financial Services":            "NIFTY_FIN_SERVICE.NS",
    "Financial Products Distributor":      "NIFTY_FIN_SERVICE.NS",
    "Microfinance Institutions":           "NIFTY_FIN_SERVICE.NS",
    "Insurance Distributors":              "NIFTY_FIN_SERVICE.NS",
    "Life Insurance":                      "NIFTY_FIN_SERVICE.NS",
    "General Insurance":                   "NIFTY_FIN_SERVICE.NS",
    "Exchange and Data Platform":          "NIFTY_FIN_SERVICE.NS",
    "Depositories, Clearing Houses and Other Intermediaries": "NIFTY_FIN_SERVICE.NS",
    "Ratings":                              "NIFTY_FIN_SERVICE.NS",

    # IT
    "Computers - Software & Consulting":   "^CNXIT",
    "IT Enabled Services":                 "^CNXIT",
    "Software Products":                  "^CNXIT",
    "Business Process Outsourcing (BPO)/ Knowledge Process Outsourcing (KPO)": "^CNXIT",

    # Pharma / Healthcare
    "Pharmaceuticals":                    "^CNXPHARMA",
    "Hospital":                           "^CNXPHARMA",
    "Healthcare Service Provider":        "^CNXPHARMA",
    "Healthcare Research, Analytics & Technology": "^CNXPHARMA",
    "Medical Equipment & Supplies":       "^CNXPHARMA",
    "Pharmacy Retail":                    "^CNXPHARMA",

    # Auto
    "Passenger Cars & Utility Vehicles":  "^CNXAUTO",
    "Auto Components & Equipments":       "^CNXAUTO",
    "2/3 Wheelers":                       "^CNXAUTO",
    "Commercial Vehicles":                "^CNXAUTO",
    "Construction Vehicles":              "^CNXAUTO",
    "Auto Dealer":                        "^CNXAUTO",
    "Tyres & Rubber Products":            "^CNXAUTO",

    # FMCG
    "Diversified FMCG":                   "^CNXFMCG",
    "Personal Care":                      "^CNXFMCG",
    "Packaged Foods":                     "^CNXFMCG",
    "Breweries & Distilleries":           "^CNXFMCG",
    "Edible Oil":                         "^CNXFMCG",
    "Dairy Products":                     "^CNXFMCG",
    "Other Beverages":                    "^CNXFMCG",
    "Other Food Products":                "^CNXFMCG",
    "Seafood":                            "^CNXFMCG",
    "Sugar":                              "^CNXFMCG",

    # Metals & Mining
    "Iron & Steel":                       "^CNXMETAL",
    "Iron & Steel Products":              "^CNXMETAL",
    "Aluminium":                          "^CNXMETAL",
    "Zinc":                               "^CNXMETAL",
    "Diversified Metals":                 "^CNXMETAL",
    "Ferro & Silica Manganese":           "^CNXMETAL",
    "Trading - Metals":                   "^CNXMETAL",
    "Castings & Forgings":                "^CNXMETAL",
    "Electrodes & Refractories":          "^CNXMETAL",
    "Industrial Minerals":                "^CNXMETAL",
    "Trading - Minerals":                 "^CNXMETAL",

    # Realty / Construction / Infra
    "Residential, Commercial Projects":   "^CNXREALTY",
    "Civil Construction":                 "^CNXINFRA",
    "Heavy Electrical Equipment":         "^CNXINFRA",
    "Other Electrical Equipment":         "^CNXINFRA",
    "Cables - Electricals":               "^CNXINFRA",
    "Industrial Products":                "^CNXINFRA",
    "Other Industrial Products":          "^CNXINFRA",
    "Compressors, Pumps & Diesel Engines": "^CNXINFRA",
    "Cement & Cement Products":           "^CNXINFRA",
    "Plastic Products - Industrial":      "^CNXINFRA",
    "Abrasives & Bearings":               "^CNXINFRA",

    # Energy / Power / Oil & Gas
    "Refineries & Marketing":             "^CNXENERGY",
    "Oil Exploration & Production":       "^CNXENERGY",
    "Power Generation":                   "^CNXENERGY",
    "Power Distribution":                 "^CNXENERGY",
    "Gas Transmission/Marketing":         "^CNXENERGY",
    "LPG/CNG/PNG/LNG Supplier":           "^CNXENERGY",
    "Industrial Gases":                   "^CNXENERGY",
    "Trading - Gas":                      "^CNXENERGY",
    "Petrochemicals":                     "^CNXENERGY",

    # Telecom
    "Telecom - Cellular & Fixed line services": "^CNXIT",
    "Telecom - Infrastructure":            "^CNXIT",
    "Telecom -  Equipment & Accessories":  "^CNXIT",

    # Consumer Durables / Retail
    "Household Appliances":               "^CNXCONSUM",
    "Consumer Electronics":               "^CNXCONSUM",
    "Furniture, Home Furnishing":         "^CNXCONSUM",
    "Ceramics":                            "^CNXCONSUM",
    "Speciality Retail":                  "^CNXCONSUM",
    "Diversified Retail":                 "^CNXCONSUM",
    "E-Retail/ E-Commerce":               "^CNXCONSUM",
    "Internet & Catalogue Retail":        "^CNXCONSUM",
    "Garments & Apparels":                "^CNXCONSUM",
    "Gems, Jewellery And Watches":        "^CNXCONSUM",

    # Chemicals
    "Specialty Chemicals":                "^CNXFMCG",
    "Commodity Chemicals":                "^CNXFMCG",
    "Dyes And Pigments":                  "^CNXFMCG",
    "Paints":                              "^CNXFMCG",
    "Fertilizers":                         "^CNXFMCG",
    "Pesticides & Agrochemicals":          "^CNXFMCG",
}

_GREEN = PatternFill("solid", fgColor="C6EFCE")
_RED = PatternFill("solid", fgColor="FFC7CE")
_AMBER = PatternFill("solid", fgColor="FFEB9C")
_GREY = PatternFill("solid", fgColor="D9D9D9")


def load_export(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path)

    df.columns = [c.strip() for c in df.columns]

    fii_col = next((c for c in df.columns if "fii" in c.lower() and "hold" in c.lower()), None)
    cap_col = next((c for c in df.columns if "mar cap" in c.lower() or "market cap" in c.lower()), None)
    ind_col = next((c for c in df.columns if "industry" in c.lower() or "sector" in c.lower()), None)

    missing = [name for name, col in
               [("FII holding change", fii_col), ("Market Cap", cap_col), ("Industry", ind_col)]
               if col is None]
    if missing:
        sys.exit(
            f"Export is missing required column(s): {', '.join(missing)}.\n"
            "Add 'Industry' via Edit Columns on screener.in before exporting, "
            "and make sure Market Cap + Change in FII holding % are included."
        )

    df = df.rename(columns={fii_col: "fii_chg", cap_col: "mar_cap", ind_col: "industry"})
    df["fii_chg"] = pd.to_numeric(df["fii_chg"], errors="coerce")
    df["mar_cap"] = pd.to_numeric(df["mar_cap"], errors="coerce")
    return df.dropna(subset=["fii_chg", "mar_cap", "industry"])


def aggregate_by_sector(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["weighted_fii"] = df["fii_chg"] * df["mar_cap"]

    grouped = df.groupby("industry").agg(
        stock_count=("fii_chg", "size"),
        total_mar_cap=("mar_cap", "sum"),
        weighted_fii_sum=("weighted_fii", "sum"),
    )
    grouped["fii_rotation_score"] = grouped["weighted_fii_sum"] / grouped["total_mar_cap"]
    return grouped.sort_values("fii_rotation_score", ascending=False).reset_index()


def fetch_sector_index_1y_return(ticker: str) -> float | None:
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=True)
    except Exception:
        return None
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    close = df["Close"] if "Close" in df.columns else df.iloc[:, 0]
    try:
        first, last = float(close.iloc[0]), float(close.iloc[-1])
        return round((last / first - 1) * 100, 2)
    except Exception:
        return None


def classify_bias(fii_score: float, index_1y_return: float | None) -> str:
    if index_1y_return is None:
        return "unscored (no index data)"
    inflow = fii_score > 0
    strong = index_1y_return > 0
    if inflow and strong:
        return "confirmed bullish rotation"
    if inflow and not strong:
        return "early accumulation / contrarian watch"
    if not inflow and strong:
        return "distribution into strength (caution)"
    return "confirmed bearish rotation"


def write_sector_company_sheet(df: pd.DataFrame, xlsx_path: Path) -> None:
    """Raw company-level sheet, grouped by sector — the source data behind the
    aggregated Sector Rotation sheet, kept as sheet 1 so a reader can drill
    from a sector's score back to the individual stocks behind it."""
    company_df = df.sort_values(["industry", "fii_chg"], ascending=[True, False]).reset_index(drop=True)
    stock_counts = company_df.groupby("industry")["fii_chg"].transform("size")
    company_df = company_df.assign(stocks_in_sector=stock_counts)
    company_df = company_df.rename(columns={
        "industry": "Industry", "mar_cap": "Mar Cap", "fii_chg": "Change in FII holding %",
        "stocks_in_sector": "Stocks in sector",
    })[["Industry", "Stocks in sector", "Name", "Mar Cap", "Change in FII holding %"]]

    if xlsx_path.exists():
        wb = openpyxl.load_workbook(xlsx_path)
    else:
        wb = openpyxl.Workbook()
        wb.remove(wb.active)

    sheet_name = "Sector-wise Stocks"
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(sheet_name, 0)

    for col_idx, col_name in enumerate(company_df.columns, 1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font = Font(bold=True)
    for r, row in enumerate(company_df.itertuples(index=False), 2):
        for c, val in enumerate(row, 1):
            ws.cell(row=r, column=c, value=val)
    ws.freeze_panes = "A2"

    for col_idx, col_name in enumerate(company_df.columns, 1):
        col_letter = get_column_letter(col_idx)
        max_len = max(len(str(col_name)), *(len(str(ws.cell(r, col_idx).value or ""))
                                              for r in range(2, len(company_df) + 2)))
        ws.column_dimensions[col_letter].width = min(max_len + 2, 35)

    wb.save(xlsx_path)


def run(export_path: Path) -> None:
    df = load_export(export_path)
    sector_table = aggregate_by_sector(df)

    # Cache by ticker (many Industries share the same index proxy) and pace
    # calls — yfinance/Yahoo silently returns empty data under rapid
    # back-to-back requests rather than raising, so a delay is required.
    ticker_return_cache: dict[str, float | None] = {}
    index_returns, biases = [], []
    for industry in sector_table["industry"]:
        ticker = SECTOR_INDEX_MAP.get(industry)
        if ticker is None:
            ret = None
        elif ticker in ticker_return_cache:
            ret = ticker_return_cache[ticker]
        else:
            ret = fetch_sector_index_1y_return(ticker)
            ticker_return_cache[ticker] = ret
            time.sleep(1.5)
        index_returns.append(ret)
        biases.append(classify_bias(
            sector_table.loc[sector_table["industry"] == industry, "fii_rotation_score"].iloc[0],
            ret,
        ))

    sector_table["index_ticker"] = sector_table["industry"].map(SECTOR_INDEX_MAP)
    sector_table["index_1y_return_%"] = index_returns
    sector_table["rotation_bias"] = biases

    out_path = BASE_DIR / f"sector_rotation_{pd.Timestamp.today().strftime('%Y%m%d')}.xlsx"

    # Merge into the existing workbook (Rotation Map / Promoter+FII sheets from the
    # other tools may already live here) rather than overwriting the whole file —
    # pd.ExcelWriter's default mode recreates the file from scratch and silently
    # destroys any sheets written by sector_rotation_trail.py / promoter_profit_surprise.py.
    if out_path.exists():
        wb = openpyxl.load_workbook(out_path)
    else:
        wb = openpyxl.Workbook()
        wb.remove(wb.active)

    sheet_name = "Sector Rotation"
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(sheet_name, 0)

    for col_idx, col_name in enumerate(sector_table.columns, 1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font = Font(bold=True)
    for r, row in enumerate(sector_table.itertuples(index=False), 2):
        for c, val in enumerate(row, 1):
            ws.cell(row=r, column=c, value=val)
    ws.freeze_panes = "A2"

    col_map = {name: idx + 1 for idx, name in enumerate(sector_table.columns)}
    bias_col = col_map["rotation_bias"]
    for row_idx in range(2, len(sector_table) + 2):
        val = ws.cell(row=row_idx, column=bias_col).value
        fill = {
            "confirmed bullish rotation": _GREEN,
            "early accumulation / contrarian watch": _AMBER,
            "distribution into strength (caution)": _AMBER,
            "confirmed bearish rotation": _RED,
        }.get(val, _GREY)
        ws.cell(row=row_idx, column=bias_col).fill = fill

    for col_name, col_idx in col_map.items():
        col_letter = get_column_letter(col_idx)
        max_len = max(len(str(ws.cell(r, col_idx).value or ""))
                      for r in range(1, len(sector_table) + 2))
        ws.column_dimensions[col_letter].width = min(max_len + 2, 35)

    wb.save(out_path)

    # Written last so its create_sheet(..., 0) lands as the true first sheet,
    # ahead of "Sector Rotation" above.
    write_sector_company_sheet(df, out_path)

    print(f"Saved -> {out_path}")
    print("\nTop 5 sectors by FII rotation score:")
    print(sector_table.head(5).to_string(index=False))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: py -3 tools/sector_rotation.py <screener_export.csv|xlsx>")
    run(Path(sys.argv[1]))
