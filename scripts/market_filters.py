#!/usr/bin/env python3
"""
Market Filtering Utilities
Common filters to skip unwanted markets
"""

import re
from datetime import datetime

def should_skip_market(market_question, market_slug):
    """
    Check if a market should be skipped based on various criteria
    Returns: (should_skip, reason)
    """
    
    # Filter 1: Markets about past years
    current_year = datetime.now().year
    # Look for 4-digit years in the question
    years_in_question = re.findall(r'\b(20\d{2})\b', market_question)
    
    for year_str in years_in_question:
        year = int(year_str)
        if year < current_year:
            return True, f"Market about past year ({year})"
    
    # Filter 2: High-frequency markets (already handled elsewhere but include for completeness)
    high_freq_patterns = [
        'next hour', 'next minute', 'within 1 hour', 'in the next hour',
        'hourly', 'minute by minute', 'real-time'
    ]
    
    slug_lower = market_slug.lower()
    question_lower = market_question.lower()
    
    if any(pattern in question_lower for pattern in high_freq_patterns):
        return True, "High-frequency market"
    
    # Filter 3: Sports markets (no information edge)
    sports_patterns = [
        'nfl-', 'nba-', 'mlb-', 'nhl-', 'ufc-', 'fifa-', 'super-bowl',
        'world-cup', 'olympics', 'premier-league', 'champions-league'
    ]
    
    if any(pattern in slug_lower for pattern in sports_patterns):
        return True, "Sports market"
    
    return False, None

if __name__ == '__main__':
    # Test cases
    test_cases = [
        ("Will the U.S. collect between $100b and $200b in revenue in 2025?", "us-revenue-2025"),
        ("Will Trump win the 2028 election?", "trump-2028"),
        ("Will Bitcoin hit $100k in the next hour?", "btc-100k-next-hour"),
        ("Will the Lakers win tonight?", "nba-lakers-vs-celtics"),
        ("Will the PPLE party win in 2026?", "pple-win-2026"),
    ]
    
    current_year = datetime.now().year
    print(f"Current year: {current_year}\n")
    
    for question, slug in test_cases:
        should_skip, reason = should_skip_market(question, slug)
        status = "❌ SKIP" if should_skip else "✅ OK"
        print(f"{status}: {question}")
        if reason:
            print(f"   Reason: {reason}")
        print()
