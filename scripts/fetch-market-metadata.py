#!/usr/bin/env python3
"""
Fetch Market Metadata from Polymarket API
Gets endDate, full questions, and other important market info
"""

import sqlite3
import requests
import json
from datetime import datetime

TRADING_DB = '/workspace/polymarket_runtime/data/trading.db'
GAMMA_API = 'https://gamma-api.polymarket.com'

def fetch_event_metadata(event_slug):
    """Fetch event metadata from Polymarket API"""
    try:
        response = requests.get(f"{GAMMA_API}/events?slug={event_slug}")
        if response.status_code == 200:
            events = response.json()
            if events and len(events) > 0:
                return events[0]
    except Exception as e:
        print(f"Error fetching event {event_slug}: {e}")
    return None

def update_position_metadata():
    """Update all positions with market metadata"""
    conn = sqlite3.connect(TRADING_DB)
    cur = conn.cursor()
    
    # Get all positions with event_slug
    cur.execute("""
        SELECT id, market_question, notes
        FROM paper_positions
        WHERE status = 'open'
    """)
    
    positions = cur.fetchall()
    
    print(f"📊 Fetching metadata for {len(positions)} positions...\n")
    
    for pos_id, market_question, notes_str in positions:
        # Parse notes to get event_slug
        try:
            notes = json.loads(notes_str) if notes_str else {}
        except:
            notes = {}
        
        event_slug = notes.get('event_slug')
        
        if not event_slug:
            print(f"⚠️  Position #{pos_id}: No event_slug, skipping")
            continue
        
        print(f"Position #{pos_id}: {event_slug}")
        
        # Fetch event metadata
        event = fetch_event_metadata(event_slug)
        
        if event:
            end_date = event.get('endDate')
            if end_date:
                # Parse end date
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                days_until = (end_dt - datetime.now(end_dt.tzinfo)).days
                
                print(f"  End Date: {end_date}")
                print(f"  Days Until Close: {days_until}")
                
                # Update notes with metadata
                notes['end_date'] = end_date
                notes['days_until_close'] = days_until
                notes['full_title'] = event.get('title', market_question)
                
                cur.execute("""
                    UPDATE paper_positions
                    SET notes = ?
                    WHERE id = ?
                """, (json.dumps(notes), pos_id))
                
                if days_until < 7:
                    print(f"  ⚠️  WARNING: Market closing in {days_until} days!")
                elif days_until < 0:
                    print(f"  🚨 ALERT: Market should have closed {abs(days_until)} days ago!")
            else:
                print(f"  ⚠️  No endDate found")
        else:
            print(f"  ❌ Could not fetch event metadata")
        
        print()
    
    conn.commit()
    conn.close()
    
    print("✅ Metadata update complete")

if __name__ == '__main__':
    update_position_metadata()
