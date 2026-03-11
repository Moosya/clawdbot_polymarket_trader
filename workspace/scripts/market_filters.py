#!/usr/bin/env python3
"""
Market Filtering Utilities
Common filters to skip unwanted markets
"""

import re
import calendar
from datetime import datetime, timedelta

def should_skip_market(market_question, market_slug):
    """
    Check if a market should be skipped based on various criteria
    Returns: (should_skip, reason)
    
    Philosophy: Only trade markets where whale activity signals insider information,
    not just rich gamblers. Skip sports, entertainment, weather, and short-term gambling.
    """
    
    slug_lower = market_slug.lower()
    question_lower = market_question.lower()
    
    # Filter 1: Markets about past years
    current_year = datetime.now().year
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
    
    if any(pattern in question_lower for pattern in high_freq_patterns):
        return True, "High-frequency market"
    
    # Filter 3: Sports markets (no insider edge - just rich gamblers)
    sports_slug_patterns = [
        'nfl-', 'nba-', 'mlb-', 'nhl-', 'cbb-', 'cfb-',  # US sports
        'epl-', 'lal-', 'ser-', 'bun-', 'lig-',  # Top European soccer leagues
        'ucl-', 'uel-', 'uefa-', 'elc-', 'cdr-',  # Champions/Europa/Conference League, Copa del Rey
        'fifa-', 'wc-', 'euro-',  # International tournaments
        'atp-', 'wta-', 'ufc-', 'f1-', 'nascar-', 'pga-',  # Individual sports
        'super-bowl', 'world-cup', 'olympics'
    ]
    
    sports_question_patterns = [
        ' vs ', ' vs. ', ' v ', ' v. ',  # Match indicators
        'win on 20',  # "Will X win on 2026-03-02?"
        'win the championship', 'win the cup', 'playoff',
        'total points', 'over/under', 'spread',
        'premier league', 'champions league', 'world series', 'la liga'
    ]
    
    if any(pattern in slug_lower for pattern in sports_slug_patterns):
        return True, "Sports market (no information edge)"
    
    if any(pattern in question_lower for pattern in sports_question_patterns):
        # Make sure it's actually sports, not political
        if not any(x in question_lower for x in ['election', 'president', 'policy', 'senate']):
            return True, "Sports market (no information edge)"
    
    # Filter 4: Esports (same as sports - rich gamers, not informed traders)
    esports_patterns = ['cs2-', 'dota2-', 'lol-', 'valorant-', 'csgo-', 'overwatch-']
    
    if any(pattern in slug_lower for pattern in esports_patterns):
        return True, "Esports market (no information edge)"
    
    # Filter 5: Entertainment/Celebrity (random rich people betting)
    entertainment_patterns = [
        'musk', 'tweet', 'elon', 'celebrity', 'kardashian',
        'oscar', 'grammy', 'emmy', 'golden globe',
        'box office', 'movie', 'album', 'song',
        'tiktok', 'instagram', 'youtube subscriber'
    ]
    
    if any(pattern in question_lower for pattern in entertainment_patterns):
        return True, "Entertainment market (no information edge)"
    
    # Filter 6: Weather (literally impossible to have insider information)
    weather_patterns = ['temperature', 'weather', 'rain', 'snow', 'hurricane', 'tornado', 'celsius', 'fahrenheit']
    
    if any(pattern in question_lower for pattern in weather_patterns):
        return True, "Weather market (no insider information)"
    
    # Filter 7: Expired markets (deadline has passed)
    # Check for date patterns in slug: march-3, march-4, march-5, etc.
    current_date = datetime.now()
    
    # Pattern: month-day in slug (e.g., "march-3", "february-28")
    for month_num in range(1, 13):
        month_name = calendar.month_name[month_num].lower()
        month_abbr = calendar.month_abbr[month_num].lower()
        
        # Check full month name (march-3, april-15)
        for day in range(1, 32):
            pattern = f"{month_name}-{day}"
            if pattern in slug_lower:
                # Parse the date and check if it's passed
                try:
                    market_date = datetime(current_date.year, month_num, day)
                    if market_date < current_date:
                        days_ago = (current_date - market_date).days
                        return True, f"Expired market (deadline {days_ago} days ago)"
                except ValueError:
                    pass  # Invalid date (e.g., feb-30)
    
    # Filter 8: High-frequency markets (resolve within hours/same day - too fast for our 10-15min cycle)
    
    # Pattern 1: "Up or Down" markets (hourly/daily price predictions)
    if 'up or down' in question_lower:
        # Check for same-day or hourly resolution
        if any(x in question_lower for x in ['3pm', '2pm', '1pm', '4pm', '5pm', 'march 6', 'march 7', 'march 8', 'march 9']):
            return True, "High-frequency market (resolves too quickly for our cycle)"
        # Generic "up or down" on current/next day
        today = datetime.now().strftime('%B %d').lower()  # e.g., "march 6"
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%B %d').lower()
        if today in question_lower or tomorrow in question_lower or 'today' in question_lower:
            return True, "High-frequency market (resolves same-day)"
    
    # Pattern 2: Hourly timestamps in question (1AM ET, 2PM ET, etc.)
    hourly_patterns = ['1am et', '2am et', '3am et', '4am et', '5am et', '6am et', 
                       '7am et', '8am et', '9am et', '10am et', '11am et', '12am et',
                       '1pm et', '2pm et', '3pm et', '4pm et', '5pm et', '6pm et',
                       '7pm et', '8pm et', '9pm et', '10pm et', '11pm et', '12pm et']
    
    if any(pattern in question_lower for pattern in hourly_patterns):
        return True, "High-frequency market (hourly resolution)"
    
    # Pattern 3: Stock ticker symbols with same-day resolution
    # NFLX, AAPL, TSLA, etc. + "up or down" or "by end of"
    if re.search(r'\([A-Z]{3,5}\)', market_question):  # Matches (NFLX), (AAPL), etc.
        if 'up or down' in question_lower or 'by end of' in question_lower or 'close' in question_lower:
            return True, "High-frequency stock market (same-day resolution)"
    
    # Pattern 4: Slug patterns for crypto gambling
    crypto_gambling_patterns = ['updown-5m', 'updown-10m', 'updown-15m', 'updown-30m', 'updown-1h']
    
    if any(pattern in slug_lower for pattern in crypto_gambling_patterns):
        return True, "Crypto short-term gambling (no edge)"
    
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
