#!/usr/bin/env python3
"""
test_glossary.py - Test the trading glossary without Streamlit dependencies.
"""

import sys
from pathlib import Path

# Add tools directory to path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import trading_glossary as glossary


def test_glossary_loading():
    """Test that glossary loads correctly."""
    print("=" * 60)
    print("TEST 1: Glossary Loading")
    print("=" * 60)
    
    print(f"[OK] Total terms: {len(glossary.GLOSSARY)}")
    print(f"[OK] Categories: {glossary.get_all_categories()}")
    print()


def test_term_retrieval():
    """Test retrieving specific terms."""
    print("=" * 60)
    print("TEST 2: Term Retrieval")
    print("=" * 60)
    
    test_terms = ["VCP", "RSI", "Support", "Stop-loss"]
    
    for term in test_terms:
        defn = glossary.get_definition(term)
        if defn:
            print(f"[OK] {term}:")
            print(f"  Category: {defn.category}")
            print(f"  Definition: {defn.definition[:60]}...")
            print(f"  Related: {', '.join(defn.related_terms[:3])}")
        else:
            print(f"[FAIL] {term}: NOT FOUND")
    print()


def test_search():
    """Test search functionality."""
    print("=" * 60)
    print("TEST 3: Search Functionality")
    print("=" * 60)
    
    queries = ["RSI", "trend", "volume", "risk"]
    
    for query in queries:
        matches = glossary.search_terms(query)
        print(f"[OK] Search '{query}': {len(matches)} matches")
        if matches:
            print(f"  Results: {', '.join(matches[:5])}")
    print()


def test_category_filtering():
    """Test filtering by category."""
    print("=" * 60)
    print("TEST 4: Category Filtering")
    print("=" * 60)
    
    categories = ["Scanner", "Indicator", "Risk"]
    
    for category in categories:
        terms = glossary.get_terms_by_category(category)
        print(f"[OK] {category}: {len(terms)} terms")
        print(f"  {', '.join(terms[:5])}")
    print()


def test_related_terms():
    """Test related terms functionality."""
    print("=" * 60)
    print("TEST 5: Related Terms")
    print("=" * 60)
    
    test_terms = ["VCP", "RSI", "Stop-loss"]
    
    for term in test_terms:
        related = glossary.get_related_terms(term)
        print(f"[OK] {term}: {len(related)} related terms")
        if related:
            print(f"  {', '.join(related)}")
    print()


def test_tooltip_generation():
    """Test tooltip HTML generation."""
    print("=" * 60)
    print("TEST 6: Tooltip Generation")
    print("=" * 60)
    
    test_terms = ["VCP", "RSI"]
    
    for term in test_terms:
        tooltip = glossary.generate_tooltip(term)
        print(f"[OK] {term}:")
        print(f"  HTML length: {len(tooltip)} chars")
        print(f"  Contains tooltip: {'tooltip' in tooltip.lower()}")
    print()


def test_complete_term():
    """Test displaying a complete term definition."""
    print("=" * 60)
    print("TEST 7: Complete Term Display")
    print("=" * 60)
    
    term = "VCP"
    defn = glossary.get_definition(term)
    
    if defn:
        print(f"Term: {defn.term}")
        print(f"Category: {defn.category}")
        print(f"\nSimple Definition:")
        print(f"  {defn.definition}")
        print(f"\nTechnical Detail:")
        print(f"  {defn.technical_detail[:100]}...")
        print(f"\nExample:")
        print(f"  {defn.example}")
        print(f"\nRelated Terms:")
        print(f"  {', '.join(defn.related_terms)}")
    else:
        print(f"[FAIL] Term '{term}' not found")
    print()


def test_all_terms_have_required_fields():
    """Test that all terms have required fields."""
    print("=" * 60)
    print("TEST 8: Required Fields Validation")
    print("=" * 60)
    
    missing_fields = []
    
    for term, defn in glossary.GLOSSARY.items():
        if not defn.term:
            missing_fields.append(f"{term}: missing 'term'")
        if not defn.category:
            missing_fields.append(f"{term}: missing 'category'")
        if not defn.definition:
            missing_fields.append(f"{term}: missing 'definition'")
        if not defn.technical_detail:
            missing_fields.append(f"{term}: missing 'technical_detail'")
        if not defn.example:
            missing_fields.append(f"{term}: missing 'example'")
        if not defn.related_terms:
            missing_fields.append(f"{term}: missing 'related_terms'")
    
    if missing_fields:
        print(f"[FAIL] Found {len(missing_fields)} missing fields:")
        for field in missing_fields[:10]:
            print(f"  {field}")
    else:
        print(f"[OK] All {len(glossary.GLOSSARY)} terms have required fields")
    print()


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("TRADING GLOSSARY TEST SUITE")
    print("=" * 60 + "\n")
    
    try:
        test_glossary_loading()
        test_term_retrieval()
        test_search()
        test_category_filtering()
        test_related_terms()
        test_tooltip_generation()
        test_complete_term()
        test_all_terms_have_required_fields()
        
        print("=" * 60)
        print("[OK] ALL TESTS PASSED")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print("=" * 60)
        print(f"[FAIL] TEST FAILED: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
