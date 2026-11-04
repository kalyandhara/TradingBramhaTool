#!/usr/bin/env python3
"""
confluence_scoring.py — Category-weighted confluence scoring system.

Implements multi-dimensional confluence analysis where scanner categories
have different weights based on their trading value:
  • Entry scanners: 2.0x weight (highest value — actionable setups)
  • Momentum scanners: 1.8x weight (strong confirmation)
  • Trend scanners: 1.5x weight (context/confirmation)
  • Pattern scanners: 1.2x weight (geometric confirmation)
  • Risk scanners: -1.0x weight (negative signal — penalty)
  • Neutral scanners: 0.0x weight (informational only, no vote)

This prevents a stock with 3 weak pattern hits from ranking higher than
a stock with 1 Entry + 1 Trend hit (which has better edge).

Example:
    Stock A: Pullback Entry (Entry, 2.0) + Stage 2 Uptrend (Trend, 1.5) = 3.5
    Stock B: Darvas (1.2) + Triangle (1.2) + VCP (1.2) = 3.6
    Stock C: HM Buy (Entry, 2.0) + Bearish Reversal (Risk, -1.0) = 1.0

    Ranking: B (3.6) > A (3.5) > C (1.0)

    Without weighting, all would score 2-3 based on raw count alone.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import pandas as pd

log = logging.getLogger(__name__)

# ── Category Weights ──────────────────────────────────────────────────────────
# Calibrated based on scanner edge measurements and practical trading value.
# Entry scanners provide the highest edge, Risk scanners are contraindicators.

CATEGORY_WEIGHTS: dict[str, float] = {
    "Entry": 2.0,      # Highest value — actionable trade setups
    "Momentum": 1.8,   # Strong continuation signals
    "Trend": 1.5,      # Context/confirmation
    "Pattern": 1.2,    # Geometric confirmation (slower, less actionable)
    "Risk": -1.0,      # Penalty — evidence AGAINST the trade
    "Neutral": 0.0,    # Informational only (e.g., bilateral coils)
}


@dataclass
class ConfluenceScore:
    """Multi-dimensional confluence score for a symbol."""

    symbol: str
    raw_hits: int                          # Total scanner count (unweighted)
    weighted_score: float                  # Category-weighted score
    scanners: list[str]                    # Scanner names that fired
    categories: list[str]                  # Categories represented
    category_breakdown: dict[str, int]     # Hits per category
    max_individual_score: float            # Best single scanner score

    # Quality metrics
    has_entry: bool                        # At least one Entry scanner fired
    has_risk: bool                         # At least one Risk scanner fired (penalty)
    category_diversity: int                # Number of unique categories

    def __post_init__(self):
        """Calculate derived metrics."""
        self.category_diversity = len(set(self.categories))


def calculate_weighted_confluence(
    scanner_hits: list[dict],
    scanner_registry: dict[str, dict],
) -> ConfluenceScore:
    """
    Calculate category-weighted confluence score for a single symbol.

    Args:
        scanner_hits: List of scanner result dicts for this symbol.
                     Each must have 'scanner' and 'score' keys.
        scanner_registry: The SCANNERS dict from scanner_templates.py
                         Maps scanner name → {fn, category, description}

    Returns:
        ConfluenceScore with weighted metrics

    Example:
        >>> hits = [
        ...     {"scanner": "Pullback Entry", "score": 78.5},
        ...     {"scanner": "Stage 2 Uptrend", "score": 82.0},
        ... ]
        >>> score = calculate_weighted_confluence(hits, sc.SCANNERS)
        >>> score.weighted_score  # 2.0 + 1.5 = 3.5
        3.5
    """
    symbol = scanner_hits[0].get("symbol", "UNKNOWN") if scanner_hits else "UNKNOWN"

    scanners = []
    categories = []
    category_breakdown: dict[str, int] = {}
    weighted_score = 0.0
    max_individual_score = 0.0

    for hit in scanner_hits:
        scanner_name = hit.get("scanner") or hit.get("pattern_type")
        if not scanner_name:
            continue

        # Get category from registry
        scanner_spec = scanner_registry.get(scanner_name, {})
        category = scanner_spec.get("category", "Unknown")

        # Get weight for this category
        weight = CATEGORY_WEIGHTS.get(category, 0.0)

        # Accumulate
        scanners.append(scanner_name)
        categories.append(category)
        category_breakdown[category] = category_breakdown.get(category, 0) + 1
        weighted_score += weight

        # Track best individual score
        individual_score = hit.get("score", 0)
        if individual_score > max_individual_score:
            max_individual_score = individual_score

    return ConfluenceScore(
        symbol=symbol,
        raw_hits=len(scanner_hits),
        weighted_score=weighted_score,
        scanners=scanners,
        categories=categories,
        category_breakdown=category_breakdown,
        max_individual_score=max_individual_score,
        has_entry="Entry" in categories,
        has_risk="Risk" in categories,
        category_diversity=0,  # Set by __post_init__
    )


def aggregate_weighted_confluence(
    all_results: dict[str, dict[str, list[dict]]],
    scanner_registry: dict[str, dict],
) -> pd.DataFrame:
    """
    Aggregate weighted confluence across all batch results.

    Args:
        all_results: Batch results dict
                    {batch_name: {scanner_name: [hits...]}}
        scanner_registry: SCANNERS dict from scanner_templates.py

    Returns:
        DataFrame with columns:
            - symbol
            - raw_hits (unweighted count)
            - weighted_score (category-weighted)
            - scanners (comma-separated)
            - categories (comma-separated)
            - category_breakdown (dict as string)
            - max_score (best individual scanner score)
            - has_entry (bool)
            - has_risk (bool)
            - category_diversity (unique category count)

        Sorted by weighted_score DESC, then max_score DESC
    """
    # Group all hits by symbol
    symbol_hits: dict[str, list[dict]] = {}

    for batch_name, batch_results in all_results.items():
        for scanner_name, hits in batch_results.items():
            for hit in hits:
                sym = hit.get("symbol")
                if not sym:
                    continue

                if sym not in symbol_hits:
                    symbol_hits[sym] = []

                # Ensure scanner name is present
                if "scanner" not in hit and "pattern_type" in hit:
                    hit["scanner"] = hit["pattern_type"]
                elif "scanner" not in hit:
                    hit["scanner"] = scanner_name

                symbol_hits[sym].append(hit)

    # Calculate weighted scores for each symbol
    rows = []
    for sym, hits in symbol_hits.items():
        confluence = calculate_weighted_confluence(hits, scanner_registry)

        rows.append({
            "symbol": sym,
            "raw_hits": confluence.raw_hits,
            "weighted_score": confluence.weighted_score,
            "scanners": ", ".join(confluence.scanners),
            "categories": ", ".join(sorted(set(confluence.categories))),
            "category_breakdown": str(confluence.category_breakdown),
            "max_score": confluence.max_individual_score,
            "has_entry": confluence.has_entry,
            "has_risk": confluence.has_risk,
            "category_diversity": confluence.category_diversity,
        })

    df = pd.DataFrame(rows)

    if not df.empty:
        # Sort by weighted score first, then by max individual score
        df = df.sort_values(
            ["weighted_score", "max_score"],
            ascending=[False, False]
        ).reset_index(drop=True)

    return df


def get_confluence_summary(df: pd.DataFrame) -> dict[str, Any]:
    """
    Generate summary statistics for weighted confluence analysis.

    Args:
        df: DataFrame from aggregate_weighted_confluence()

    Returns:
        Dict with summary metrics
    """
    if df.empty:
        return {
            "total_symbols": 0,
            "avg_raw_hits": 0.0,
            "avg_weighted_score": 0.0,
            "high_conviction_count": 0,
            "entry_signal_count": 0,
            "risk_flag_count": 0,
        }

    return {
        "total_symbols": len(df),
        "avg_raw_hits": float(df["raw_hits"].mean()),
        "avg_weighted_score": float(df["weighted_score"].mean()),
        "max_weighted_score": float(df["weighted_score"].max()),
        "high_conviction_count": int((df["weighted_score"] >= 3.0).sum()),
        "entry_signal_count": int(df["has_entry"].sum()),
        "risk_flag_count": int(df["has_risk"].sum()),
        "avg_category_diversity": float(df["category_diversity"].mean()),
    }


def filter_by_weighted_score(
    df: pd.DataFrame,
    min_weighted_score: float = 3.0,
    require_entry: bool = False,
    exclude_risk: bool = False,
) -> pd.DataFrame:
    """
    Filter confluence DataFrame by weighted score thresholds.

    Args:
        df: DataFrame from aggregate_weighted_confluence()
        min_weighted_score: Minimum weighted confluence score
        require_entry: If True, only keep symbols with at least one Entry scanner
        exclude_risk: If True, exclude symbols with Risk scanners

    Returns:
        Filtered DataFrame
    """
    filtered = df.copy()

    # Score threshold
    filtered = filtered[filtered["weighted_score"] >= min_weighted_score]

    # Entry requirement
    if require_entry:
        filtered = filtered[filtered["has_entry"]]

    # Risk exclusion
    if exclude_risk:
        filtered = filtered[~filtered["has_risk"]]

    return filtered.reset_index(drop=True)


# ── Named Confluence Patterns ─────────────────────────────────────────────────
# Specific scanner combinations that represent high-probability setups.
# Each pattern has a name, required scanners, and a quality threshold.

CONFLUENCE_PATTERNS = {
    "Pullback King": {
        "description": "Perfect pullback setup with trend confirmation",
        "required_scanners": ["Pullback Entry"],
        "required_categories": ["Entry", "Trend"],
        "min_weighted_score": 3.5,
        "notes": "Entry + Trend context = high-quality pullback",
    },
    "Momentum Breakout": {
        "description": "Breakout with momentum confirmation",
        "required_scanners": ["Breakout Retest"],
        "required_categories": ["Entry", "Momentum"],
        "min_weighted_score": 3.5,
        "notes": "Breakout backed by momentum leaders",
    },
    "Hidden Gem": {
        "description": "Low-confluence HM Buy (undiscovered opportunity)",
        "required_scanners": ["HM Buy (Hilega Milega)"],
        "max_raw_hits": 2,
        "max_weighted_score": 2.5,
        "notes": "Single strong Entry signal, not crowded",
    },
    "Triple Threat": {
        "description": "Entry + Trend + Momentum alignment",
        "required_categories": ["Entry", "Trend", "Momentum"],
        "min_category_diversity": 3,
        "min_weighted_score": 5.0,
        "notes": "All three major signal types agree",
    },
    "Risk-Off Warning": {
        "description": "Entry signal with risk flag — proceed with caution",
        "required_categories": ["Entry", "Risk"],
        "has_risk": True,
        "notes": "Conflicting signals — trade smaller or wait",
    },
}


def detect_confluence_patterns(
    df: pd.DataFrame,
    patterns: dict[str, dict] = None,
) -> pd.DataFrame:
    """
    Detect named confluence patterns in the results.

    Args:
        df: DataFrame from aggregate_weighted_confluence()
        patterns: Pattern definitions (default: CONFLUENCE_PATTERNS)

    Returns:
        DataFrame with additional 'matched_patterns' column
    """
    if patterns is None:
        patterns = CONFLUENCE_PATTERNS

    df = df.copy()
    df["matched_patterns"] = ""

    for idx, row in df.iterrows():
        matched = []
        scanners_list = [s.strip() for s in row["scanners"].split(",")]
        categories_list = [c.strip() for c in row["categories"].split(",")]

        for pattern_name, pattern_def in patterns.items():
            # Check required scanners
            required_scanners = pattern_def.get("required_scanners", [])
            if required_scanners and not all(s in scanners_list for s in required_scanners):
                continue

            # Check required categories
            required_categories = pattern_def.get("required_categories", [])
            if required_categories and not all(c in categories_list for c in required_categories):
                continue

            # Check weighted score
            min_weighted = pattern_def.get("min_weighted_score", 0)
            if row["weighted_score"] < min_weighted:
                continue

            max_weighted = pattern_def.get("max_weighted_score", float("inf"))
            if row["weighted_score"] > max_weighted:
                continue

            # Check raw hits
            max_hits = pattern_def.get("max_raw_hits", float("inf"))
            if row["raw_hits"] > max_hits:
                continue

            # Check category diversity
            min_diversity = pattern_def.get("min_category_diversity", 0)
            if row["category_diversity"] < min_diversity:
                continue

            # Check risk flag requirement
            if pattern_def.get("has_risk") and not row["has_risk"]:
                continue

            matched.append(pattern_name)

        if matched:
            df.at[idx, "matched_patterns"] = ", ".join(matched)

    return df


# ── Example Usage ─────────────────────────────────────────────────────────────

def _demo():
    """Demonstration of weighted confluence scoring."""
    import scanner_templates as sc

    # Mock batch results
    all_results = {
        "entry_setups": {
            "Pullback Entry": [
                {"symbol": "RELIANCE", "score": 78.5},
                {"symbol": "TCS", "score": 72.0},
            ],
            "HM Buy (Hilega Milega)": [
                {"symbol": "TCS", "score": 85.0},
            ],
        },
        "trend_context": {
            "Stage 2 Uptrend": [
                {"symbol": "RELIANCE", "score": 82.0},
                {"symbol": "TCS", "score": 88.0},
            ],
        },
        "risk_flags": {
            "RSI Divergence Bear": [
                {"symbol": "INFY", "score": 65.0},
            ],
        },
        "patterns": {
            "Darvas Box": [
                {"symbol": "INFY", "score": 70.0},
            ],
        },
    }

    # Calculate weighted confluence
    df = aggregate_weighted_confluence(all_results, sc.SCANNERS)

    print("\n=== Weighted Confluence Results ===")
    print(df.to_string())

    print("\n=== Summary ===")
    summary = get_confluence_summary(df)
    for k, v in summary.items():
        print(f"{k}: {v}")

    print("\n=== High Conviction (weighted_score >= 3.0) ===")
    high_conviction = filter_by_weighted_score(df, min_weighted_score=3.0)
    print(high_conviction[["symbol", "raw_hits", "weighted_score", "categories"]].to_string())

    print("\n=== Pattern Matches ===")
    df_with_patterns = detect_confluence_patterns(df)
    matched = df_with_patterns[df_with_patterns["matched_patterns"] != ""]
    if not matched.empty:
        print(matched[["symbol", "weighted_score", "matched_patterns"]].to_string())
    else:
        print("No pattern matches found")


if __name__ == "__main__":
    _demo()
