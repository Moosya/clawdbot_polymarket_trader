#!/usr/bin/env python3
"""
Calculate Trader Performance
Matches BUY/SELL pairs to determine which traders are profitable
"""

import sqlite3
from collections import defaultdict
from datetime import datetime

TRADES_DB = '/workspace/polymarket_runtime/data/trades.db'
MIN_TRADES = 1  # Minimum closed positions to be ranked (lowered from 5 due to recent data)

def calculate_trader_performance():
    """Calculate P&L for all traders with closed positions"""
    
    conn = sqlite3.connect(TRADES_DB)
    cur = conn.cursor()
    
    # Get all trades, grouped by trader
    cur.execute("""
        SELECT trader, marketSlug, outcome, side, price, sizeUsd, timestamp
        FROM trades
        WHERE sizeUsd >= 1000
        ORDER BY trader, marketSlug, outcome, timestamp
    """)
    
    trades = cur.fetchall()
    
    # Group trades by trader -> market -> outcome
    trader_positions = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    
    for trader, market, outcome, side, price, size, timestamp in trades:
        trader_positions[trader][market][outcome].append({
            'side': side,
            'price': price,
            'size': size,
            'timestamp': timestamp
        })
    
    # Calculate P&L for each trader
    trader_stats = {}
    
    for trader, markets in trader_positions.items():
        closed_positions = 0
        total_pnl = 0
        wins = 0
        total_volume = 0
        
        for market, outcomes in markets.items():
            for outcome, trades_list in outcomes.items():
                # Simple matching: pair first BUY with first SELL, etc.
                buys = [t for t in trades_list if t['side'] == 'BUY']
                sells = [t for t in trades_list if t['side'] == 'SELL']
                
                # Match buy/sell pairs
                for i in range(min(len(buys), len(sells))):
                    buy_price = buys[i]['price']
                    sell_price = sells[i]['price']
                    size = min(buys[i]['size'], sells[i]['size'])
                    
                    # P&L = (sell_price - buy_price) * size
                    pnl = (sell_price - buy_price) * size
                    
                    total_pnl += pnl
                    closed_positions += 1
                    total_volume += size
                    
                    if pnl > 0:
                        wins += 1
        
        if closed_positions >= MIN_TRADES:
            win_rate = wins / closed_positions if closed_positions > 0 else 0
            roi = (total_pnl / total_volume) if total_volume > 0 else 0
            
            trader_stats[trader] = {
                'closed_positions': closed_positions,
                'total_pnl': round(total_pnl, 2),
                'wins': wins,
                'losses': closed_positions - wins,
                'win_rate': round(win_rate, 3),
                'roi': round(roi, 3),
                'total_volume': round(total_volume, 2)
            }
    
    conn.close()
    
    # Sort by total P&L
    sorted_traders = sorted(
        trader_stats.items(),
        key=lambda x: x[1]['total_pnl'],
        reverse=True
    )
    
    return sorted_traders

def format_top_traders(limit=10):
    """Format top traders for display"""
    traders = calculate_trader_performance()
    
    if not traders:
        print(f"📊 No traders with {MIN_TRADES}+ closed positions yet")
        print("   (Need traders with both BUY and SELL to calculate P&L)")
        return
    
    print(f"💎 TOP PROFITABLE TRADERS (Min {MIN_TRADES} closed positions)")
    print("=" * 80)
    print()
    
    for i, (trader, stats) in enumerate(traders[:limit], 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "💰"
        trader_short = f"{trader[:6]}...{trader[-4:]}"
        
        print(f"{emoji} #{i} {trader_short}")
        print(f"   Total P&L: ${stats['total_pnl']:+,.2f}")
        print(f"   Win Rate: {stats['win_rate']:.1%} ({stats['wins']}W/{stats['losses']}L)")
        print(f"   ROI: {stats['roi']:+.1%}")
        print(f"   Volume: ${stats['total_volume']:,.0f} ({stats['closed_positions']} positions)")
        print()
    
    print("=" * 80)
    print(f"Total traders ranked: {len(traders)}")

if __name__ == '__main__':
    format_top_traders()
