#!/usr/bin/env python3
"""
Update Position Prices
Fetches current prices for open positions and calculates unrealized P&L
Run this periodically (every 5-10 minutes) to keep dashboard updated
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

TRADING_DB = '/workspace/polymarket_runtime/data/trading.db'
TRADES_DB = '/workspace/polymarket_runtime/data/trades.db'

def get_current_price(market_slug, outcome):
    """Get latest price from trades database"""
    try:
        conn = sqlite3.connect(TRADES_DB)
        cur = conn.cursor()
        
        # Get most recent trade for this market/outcome
        cur.execute("""
            SELECT price FROM trades
            WHERE marketSlug = ? AND outcome = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (market_slug, outcome))
        
        result = cur.fetchone()
        conn.close()
        
        return result[0] if result else None
    except Exception as e:
        print(f"⚠️  Error fetching price for {market_slug}: {e}")
        return None

def update_open_positions():
    """Update current prices and P&L for all open positions"""
    conn = sqlite3.connect(TRADING_DB)
    cur = conn.cursor()
    
    # Get all open positions with their existing notes
    cur.execute("""
        SELECT id, market_slug, outcome, direction, entry_price, size, notes
        FROM paper_positions
        WHERE status = 'open'
    """)
    
    positions = cur.fetchall()
    updated_count = 0
    
    print(f"🔄 Updating prices for {len(positions)} open positions...")
    
    for pos_id, market_slug, outcome, direction, entry_price, size, existing_notes in positions:
        current_price = get_current_price(market_slug, outcome)
        
        if current_price is None:
            print(f"   ⚠️  No price data for {market_slug}")
            continue
        
        # Calculate unrealized P&L
        if direction == 'BUY':
            unrealized_pnl = (current_price - entry_price) * (size / entry_price)
        else:  # SELL
            unrealized_pnl = (entry_price - current_price) * (size / entry_price)
        
        # Parse existing notes to preserve reasoning
        notes_obj = {}
        if existing_notes:
            try:
                notes_obj = json.loads(existing_notes)
            except:
                # If it's not JSON, treat it as reasoning text
                notes_obj = {'reasoning': existing_notes}
        
        # Update price data
        notes_obj['price_data'] = {
            'current_price': round(current_price, 4),
            'unrealized_pnl': round(unrealized_pnl, 2),
            'last_updated': datetime.now().isoformat()
        }
        
        # Save back to database
        cur.execute("""
            UPDATE paper_positions
            SET notes = ?,
            updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (json.dumps(notes_obj), pos_id))
        
        updated_count += 1
        
        pnl_indicator = "📈" if unrealized_pnl > 0 else "📉" if unrealized_pnl < 0 else "➡️ "
        print(f"   {pnl_indicator} Position #{pos_id}: ${entry_price:.2f} → ${current_price:.2f} (P&L: ${unrealized_pnl:+.2f})")
    
    conn.commit()
    conn.close()
    
    print(f"✅ Updated {updated_count} positions")
    return updated_count

def get_portfolio_summary():
    """Calculate total portfolio stats"""
    conn = sqlite3.connect(TRADING_DB)
    cur = conn.cursor()
    
    # Get all positions with price data
    cur.execute("""
        SELECT notes, pnl, status
        FROM paper_positions
    """)
    
    total_realized = 0
    total_unrealized = 0
    open_count = 0
    
    for notes_json, realized_pnl, status in cur.fetchall():
        if status == 'closed' and realized_pnl:
            total_realized += realized_pnl
        elif status == 'open' and notes_json:
            try:
                notes = json.loads(notes_json)
                if 'price_data' in notes:
                    total_unrealized += notes['price_data']['unrealized_pnl']
                    open_count += 1
            except:
                pass
    
    conn.close()
    
    return {
        'realized_pnl': round(total_realized, 2),
        'unrealized_pnl': round(total_unrealized, 2),
        'total_pnl': round(total_realized + total_unrealized, 2),
        'open_positions': open_count
    }

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'summary':
        stats = get_portfolio_summary()
        print(f"\n💰 Portfolio Summary:")
        print(f"   Realized P&L: ${stats['realized_pnl']:+.2f}")
        print(f"   Unrealized P&L: ${stats['unrealized_pnl']:+.2f}")
        print(f"   Total P&L: ${stats['total_pnl']:+.2f}")
        print(f"   Open Positions: {stats['open_positions']}")
    else:
        update_open_positions()
        stats = get_portfolio_summary()
        print(f"\n💰 Total P&L: ${stats['total_pnl']:+.2f} (Realized: ${stats['realized_pnl']:+.2f}, Unrealized: ${stats['unrealized_pnl']:+.2f})")
