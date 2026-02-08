#!/usr/bin/env python3
"""
Resolve Polymarket Event URLs
The trade feed gives us condition IDs (market slugs) but the website URLs use event slugs.
This script queries Polymarket's API to find the correct event slug for each market.
"""

import sqlite3
import requests
import json
import time

TRADING_DB = '/workspace/polymarket_runtime/data/trading.db'
GAMMA_API = 'https://gamma-api.polymarket.com'

def search_event_by_market_question(question):
    """Search for an event by market question"""
    # Try searching events by title keywords
    keywords = question.split()[:5]  # Use first 5 words
    search_term = ' '.join(keywords)
    
    try:
        # Search events
        response = requests.get(f"{GAMMA_API}/events?limit=100&active=true")
        if response.status_code == 200:
            events = response.json()
            
            # Look for matching event by checking market questions
            for event in events:
                for market in event.get('markets', []):
                    if market.get('question', '').lower() == question.lower():
                        return event.get('slug'), event.get('id')
        
        # Try with closed events too
        response = requests.get(f"{GAMMA_API}/events?limit=100&closed=true")
        if response.status_code == 200:
            events = response.json()
            
            for event in events:
                for market in event.get('markets', []):
                    if market.get('question', '').lower() == question.lower():
                        return event.get('slug'), event.get('id')
    
    except Exception as e:
        print(f"Error searching for event: {e}")
    
    return None, None

def update_position_urls():
    """Update positions with correct event URLs"""
    conn = sqlite3.connect(TRADING_DB)
    cur = conn.cursor()
    
    # Get all unique markets from positions
    cur.execute("""
        SELECT DISTINCT market_slug, market_question
        FROM paper_positions
    """)
    
    markets = cur.fetchall()
    
    print(f"🔍 Resolving URLs for {len(markets)} markets...\n")
    
    resolved_count = 0
    
    for market_slug, market_question in markets:
        print(f"Searching: {market_question[:60]}...")
        
        event_slug, event_id = search_event_by_market_question(market_question)
        
        if event_slug:
            url = f"https://polymarket.com/event/{event_slug}"
            print(f"  ✅ Found: {url}")
            
            # Update notes JSON with event_url
            cur.execute("SELECT notes FROM paper_positions WHERE market_slug = ?", (market_slug,))
            row = cur.fetchone()
            notes_obj = {}
            if row and row[0]:
                try:
                    notes_obj = json.loads(row[0])
                except:
                    pass
            
            notes_obj['event_slug'] = event_slug
            notes_obj['event_url'] = url
            
            cur.execute("""
                UPDATE paper_positions 
                SET notes = ?
                WHERE market_slug = ?
            """, (json.dumps(notes_obj), market_slug))
            
            resolved_count += 1
        else:
            print(f"  ⚠️  Not found - will use search fallback")
            # Store fallback search URL
            search_url = f"https://polymarket.com/search?q={market_question[:50]}"
            
            cur.execute("SELECT notes FROM paper_positions WHERE market_slug = ?", (market_slug,))
            row = cur.fetchone()
            notes_obj = {}
            if row and row[0]:
                try:
                    notes_obj = json.loads(row[0])
                except:
                    pass
            
            notes_obj['event_url'] = search_url
            
            cur.execute("""
                UPDATE paper_positions 
                SET notes = ?
                WHERE market_slug = ?
            """, (json.dumps(notes_obj), market_slug))
        
        print()
        time.sleep(0.5)  # Rate limit
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Resolved {resolved_count}/{len(markets)} event URLs")
    print(f"⚠️  {len(markets) - resolved_count} markets will use search fallback")

if __name__ == '__main__':
    update_position_urls()
