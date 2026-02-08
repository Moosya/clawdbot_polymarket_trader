#!/usr/bin/env python3
"""
Paper Trading Tracker
Log hypothetical positions based on signals and track P&L over time
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

POSITIONS_FILE = '/workspace/signals/paper-positions.json'
DB_PATH = '/workspace/polymarket_runtime/data/trades.db'
PORTFOLIO_SIZE = 1000  # $1000 total paper portfolio
DEFAULT_POSITION_SIZE = 50  # $50 per position (5% risk management)

def load_positions():
    """Load existing positions"""
    if Path(POSITIONS_FILE).exists():
        with open(POSITIONS_FILE, 'r') as f:
            return json.load(f)
    return {
        'positions': [],
        'closed_positions': [],
        'stats': {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0,
            'roi': 0.0
        }
    }

def save_positions(data):
    """Save positions to file"""
    with open(POSITIONS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def open_position(signal_type, market_slug, market_question, outcome, direction, 
                  entry_price, confidence, size=DEFAULT_POSITION_SIZE):
    """Open a new paper trading position"""
    data = load_positions()
    
    position = {
        'id': f"{signal_type}-{market_slug}-{datetime.now().timestamp()}",
        'signal_type': signal_type,
        'market_slug': market_slug,
        'market_question': market_question,
        'outcome': outcome,
        'direction': direction,
        'entry_price': round(entry_price, 4),
        'entry_time': datetime.now().isoformat(),
        'size': size,
        'confidence': confidence,
        'status': 'open',
        'exit_price': None,
        'exit_time': None,
        'pnl': None,
        'roi': None
    }
    
    data['positions'].append(position)
    data['stats']['total_trades'] += 1
    save_positions(data)
    
    return position

def close_position(position_id, exit_price, reason='manual'):
    """Close a position and calculate P&L"""
    data = load_positions()
    
    position = None
    for i, pos in enumerate(data['positions']):
        if pos['id'] == position_id:
            position = data['positions'].pop(i)
            break
    
    if not position:
        return None
    
    # Calculate P&L
    if position['direction'] == 'BUY':
        pnl = (exit_price - position['entry_price']) * position['size']
    else:  # SELL
        pnl = (position['entry_price'] - exit_price) * position['size']
    
    roi = pnl / position['size']
    
    position.update({
        'status': 'closed',
        'exit_price': round(exit_price, 4),
        'exit_time': datetime.now().isoformat(),
        'pnl': round(pnl, 2),
        'roi': round(roi, 4),
        'close_reason': reason
    })
    
    data['closed_positions'].append(position)
    
    # Update stats
    data['stats']['total_pnl'] += pnl
    if pnl > 0:
        data['stats']['wins'] += 1
    else:
        data['stats']['losses'] += 1
    
    if data['stats']['total_trades'] > 0:
        total_invested = data['stats']['total_trades'] * DEFAULT_POSITION_SIZE
        data['stats']['roi'] = data['stats']['total_pnl'] / total_invested
        data['stats']['win_rate'] = data['stats']['wins'] / data['stats']['total_trades']
    
    save_positions(data)
    return position

def get_current_price(market_slug, outcome):
    """Get latest price from database"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    query = """
    SELECT price FROM trades
    WHERE marketSlug = ? AND outcome = ?
    ORDER BY timestamp DESC
    LIMIT 1
    """
    
    cur.execute(query, (market_slug, outcome))
    result = cur.fetchone()
    conn.close()
    
    return result[0] if result else None

def update_open_positions():
    """Update P&L for all open positions based on current prices"""
    data = load_positions()
    
    for pos in data['positions']:
        current_price = get_current_price(pos['market_slug'], pos['outcome'])
        if current_price:
            if pos['direction'] == 'BUY':
                unrealized_pnl = (current_price - pos['entry_price']) * pos['size']
            else:
                unrealized_pnl = (pos['entry_price'] - current_price) * pos['size']
            
            pos['current_price'] = round(current_price, 4)
            pos['unrealized_pnl'] = round(unrealized_pnl, 2)
            pos['unrealized_roi'] = round(unrealized_pnl / pos['size'], 4)
    
    save_positions(data)
    return data

def get_stats():
    """Get current performance stats"""
    data = update_open_positions()
    
    # Calculate total unrealized P&L
    total_unrealized = sum(pos.get('unrealized_pnl', 0) for pos in data['positions'])
    
    stats = data['stats'].copy()
    stats['open_positions'] = len(data['positions'])
    stats['total_unrealized_pnl'] = round(total_unrealized, 2)
    stats['combined_pnl'] = round(stats['total_pnl'] + total_unrealized, 2)
    
    return stats

def format_stats():
    """Format stats for display"""
    stats = get_stats()
    data = load_positions()
    
    output = "📊 **PAPER TRADING PERFORMANCE**\n\n"
    output += f"**Overall Stats:**\n"
    output += f"• Total Trades: {stats['total_trades']}\n"
    output += f"• Win Rate: {stats.get('win_rate', 0):.1%}\n"
    output += f"• Realized P&L: ${stats['total_pnl']:,.2f}\n"
    output += f"• Unrealized P&L: ${stats['total_unrealized_pnl']:,.2f}\n"
    output += f"• Combined P&L: ${stats['combined_pnl']:,.2f}\n"
    output += f"• ROI: {stats.get('roi', 0):.1%}\n\n"
    
    if data['positions']:
        output += f"**Open Positions ({len(data['positions'])}):**\n"
        for pos in data['positions'][:5]:  # Show top 5
            pnl_emoji = "📈" if pos.get('unrealized_pnl', 0) > 0 else "📉"
            output += f"{pnl_emoji} {pos['direction']} {pos['outcome']} @ {pos['entry_price']:.2f}\n"
            output += f"   {pos['market_question'][:60]}...\n"
            if 'unrealized_pnl' in pos:
                output += f"   P&L: ${pos['unrealized_pnl']:,.2f} ({pos['unrealized_roi']:.1%})\n"
            output += "\n"
    
    return output

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  stats              - Show current performance")
        print("  open <type> <slug> <question> <outcome> <direction> <price> <confidence>")
        print("  close <position_id> <exit_price>")
        print("  update             - Update all open positions with current prices")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'stats':
        print(format_stats())
    
    elif command == 'open' and len(sys.argv) >= 9:
        pos = open_position(
            signal_type=sys.argv[2],
            market_slug=sys.argv[3],
            market_question=sys.argv[4],
            outcome=sys.argv[5],
            direction=sys.argv[6],
            entry_price=float(sys.argv[7]),
            confidence=int(sys.argv[8])
        )
        print(f"✅ Opened position: {pos['id']}")
        print(f"   {pos['direction']} {pos['outcome']} @ {pos['entry_price']}")
    
    elif command == 'close' and len(sys.argv) >= 4:
        pos = close_position(sys.argv[2], float(sys.argv[3]))
        if pos:
            print(f"✅ Closed position: {pos['id']}")
            print(f"   P&L: ${pos['pnl']:,.2f} ({pos['roi']:.1%})")
        else:
            print("❌ Position not found")
    
    elif command == 'update':
        data = update_open_positions()
        print(f"✅ Updated {len(data['positions'])} open positions")
    
    else:
        print("❌ Invalid command")
