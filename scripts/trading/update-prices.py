#!/usr/bin/env python3
"""
Price Updater - Fetches current market prices and updates P&L for open positions
Runs every ~30 minutes to keep paper trading P&L accurate
"""

import sqlite3
import requests
import json
from datetime import datetime

# Configuration
TRADING_DB = '/workspace/polymarket_runtime/data/trading.db'
POLYMARKET_API = 'https://gamma-api.polymarket.com'

def get_db():
    """Get database connection"""
    return sqlite3.connect(TRADING_DB)

def get_open_positions():
    """Fetch all open positions that need price updates"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, market_slug, outcome, entry_price, direction, size
        FROM paper_positions
        WHERE status = 'open'
    """)
    
    positions = cur.fetchall()
    conn.close()
    
    return positions

def fetch_market_price(market_slug, outcome):
    """
    Fetch current price for a specific market/outcome from Polymarket API
    Returns None if market not found or API error
    """
    try:
        # Try to get market data from Polymarket
        url = f"{POLYMARKET_API}/markets/{market_slug}"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            print(f"   ⚠️  Market {market_slug} returned {response.status_code}")
            return None
        
        data = response.json()
        
        # Parse outcome prices
        # Polymarket returns prices as array or JSON string
        if 'outcomePrices' in data:
            prices = data['outcomePrices']
            if isinstance(prices, str):
                prices = json.loads(prices)
            
            # Get outcome tokens
            tokens = data.get('tokens', [])
            
            # Match outcome to price
            for i, token in enumerate(tokens):
                if token.get('outcome') == outcome:
                    price = float(prices[i]) if i < len(prices) else None
                    return price
        
        # Fallback: try clobTokenIds approach
        if 'clobTokenIds' in data:
            # For binary markets, typically [Yes, No]
            outcomes = ['Yes', 'No']
            prices = data.get('outcomePrices', [])
            
            for i, out in enumerate(outcomes):
                if out == outcome and i < len(prices):
                    return float(prices[i])
        
        return None
        
    except Exception as e:
        print(f"   ⚠️  Error fetching price for {market_slug}: {e}")
        return None

def update_position_price(position_id, current_price, entry_price, direction, size):
    """
    Update current price and calculate unrealized P&L for a position
    P&L = (current - entry) × size for BUY
    P&L = (entry - current) × size for SELL
    """
    # Calculate unrealized P&L
    if direction == 'BUY':
        unrealized_pnl = (current_price - entry_price) * size
    else:  # SELL
        unrealized_pnl = (entry_price - current_price) * size
    
    unrealized_roi = unrealized_pnl / size if size > 0 else 0
    
    # Update database
    conn = get_db()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            UPDATE paper_positions
            SET current_price = ?,
                unrealized_pnl = ?,
                unrealized_roi = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (current_price, unrealized_pnl, unrealized_roi, position_id))
        
        conn.commit()
    except sqlite3.OperationalError as e:
        # Columns don't exist yet - need to run migration
        print(f"   ⚠️  Database schema needs update: {e}")
        print(f"   Run: cat scripts/add-price-tracking.sql | sqlite3 data/trading.db")
    finally:
        conn.close()
    
    return unrealized_pnl, unrealized_roi

def run_update():
    """Main update loop"""
    print("💰 Price Updater Running...")
    print(f"   Timestamp: {datetime.now().isoformat()}")
    print()
    
    positions = get_open_positions()
    
    if not positions:
        print("   No open positions to update")
        return
    
    print(f"   Updating prices for {len(positions)} open positions...")
    print()
    
    updated = 0
    failed = 0
    
    for pos in positions:
        position_id, market_slug, outcome, entry_price, direction, size = pos
        
        print(f"📊 Position #{position_id}: {direction} {outcome}")
        print(f"   Market: {market_slug}")
        print(f"   Entry: ${entry_price:.4f}")
        
        # Fetch current price
        current_price = fetch_market_price(market_slug, outcome)
        
        if current_price is None:
            print(f"   ❌ Could not fetch current price")
            failed += 1
            print()
            continue
        
        print(f"   Current: ${current_price:.4f}")
        
        # Calculate P&L
        if direction == 'BUY':
            pnl = (current_price - entry_price) * size
        else:
            pnl = (entry_price - current_price) * size
        
        roi = (pnl / size * 100) if size > 0 else 0
        
        pnl_emoji = "📈" if pnl >= 0 else "📉"
        print(f"   {pnl_emoji} P&L: ${pnl:.2f} ({roi:+.1f}%)")
        
        # Update database
        try:
            update_position_price(position_id, current_price, entry_price, direction, size)
            updated += 1
        except Exception as e:
            print(f"   ❌ Failed to update database: {e}")
            failed += 1
        
        print()
    
    print("─" * 50)
    print(f"✅ Update complete: {updated} updated, {failed} failed")
    print()
    
    return {
        'updated': updated,
        'failed': failed,
        'timestamp': datetime.now().isoformat()
    }

if __name__ == '__main__':
    result = run_update()
    
    # Exit with success if at least some positions updated
    if result['updated'] > 0 or result['failed'] == 0:
        exit(0)
    else:
        exit(1)
