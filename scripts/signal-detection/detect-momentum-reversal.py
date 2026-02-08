#!/usr/bin/env python3
"""
Momentum Reversal Detector
Finds when price moves significantly but whales start betting opposite direction

Theory: Sharp price moves often overshoot. If whales enter opposite the momentum,
        they're likely catching the reversal before the crowd realizes.
"""

import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict

DB_PATH = '/workspace/polymarket_runtime/data/trades.db'
WHALE_THRESHOLD = 3000
LOOKBACK_HOURS = 6
MIN_PRICE_MOVE = 0.15  # 15% price change minimum
MIN_CONFIDENCE = 70

def detect_reversals(lookback_hours=LOOKBACK_HOURS):
    """Detect momentum reversal patterns"""
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Get all recent trades for each market to track price movement
    query = """
    SELECT 
        marketSlug,
        marketQuestion,
        outcome,
        side,
        price,
        sizeUsd,
        timestamp
    FROM trades
    WHERE timestamp > ?
    ORDER BY marketSlug, outcome, timestamp ASC
    """
    
    cutoff_time = int((datetime.now() - timedelta(hours=lookback_hours)).timestamp())
    cur.execute(query, (cutoff_time,))
    trades = cur.fetchall()
    conn.close()
    
    # Group trades by market+outcome
    market_data = defaultdict(list)
    for trade in trades:
        slug, question, outcome, side, price, size, ts = trade
        key = (slug, outcome)
        market_data[key].append({
            'question': question,
            'side': side,
            'price': price,
            'size': size,
            'timestamp': ts
        })
    
    signals = []
    
    for (slug, outcome), trades_list in market_data.items():
        if len(trades_list) < 5:  # Need enough data points
            continue
        
        # Calculate price movement
        early_trades = trades_list[:len(trades_list)//2]
        recent_trades = trades_list[len(trades_list)//2:]
        
        avg_early_price = sum(t['price'] for t in early_trades) / len(early_trades)
        avg_recent_price = sum(t['price'] for t in recent_trades) / len(recent_trades)
        
        price_move = avg_recent_price - avg_early_price
        
        # Check if price moved significantly
        if abs(price_move) < MIN_PRICE_MOVE:
            continue
        
        # Now check if whales are betting against the momentum
        recent_whale_trades = [t for t in recent_trades if t['size'] >= WHALE_THRESHOLD]
        
        if len(recent_whale_trades) < 2:
            continue
        
        # Calculate whale direction vs price momentum
        whale_buy_size = sum(t['size'] for t in recent_whale_trades if t['side'] == 'BUY')
        whale_sell_size = sum(t['size'] for t in recent_whale_trades if t['side'] == 'SELL')
        
        reversal = None
        
        # Price went UP, whales selling (bearish reversal)
        if price_move > MIN_PRICE_MOVE and whale_sell_size > whale_buy_size * 1.5:
            reversal = {
                'type': 'bearish_reversal',
                'signal': 'SELL',
                'price_move': price_move,
                'momentum': 'bullish',
                'whale_position': 'bearish',
                'whale_size': whale_sell_size,
                'explanation': f'Price rose +{price_move:.1%} but whales selling ${whale_sell_size:,.0f}'
            }
        
        # Price went DOWN, whales buying (bullish reversal)
        elif price_move < -MIN_PRICE_MOVE and whale_buy_size > whale_sell_size * 1.5:
            reversal = {
                'type': 'bullish_reversal',
                'signal': 'BUY',
                'price_move': price_move,
                'momentum': 'bearish',
                'whale_position': 'bullish',
                'whale_size': whale_buy_size,
                'explanation': f'Price fell {price_move:.1%} but whales buying ${whale_buy_size:,.0f}'
            }
        
        if reversal:
            confidence = calculate_reversal_score(
                reversal['whale_size'],
                len(recent_whale_trades),
                abs(price_move),
                avg_recent_price
            )
            
            if confidence >= MIN_CONFIDENCE:
                signal = {
                    'market_slug': slug,
                    'market_question': trades_list[0]['question'],
                    'outcome': outcome,
                    'reversal': reversal,
                    'whale_count': len(recent_whale_trades),
                    'current_price': avg_recent_price,
                    'confidence': confidence,
                    'timestamp': datetime.now().isoformat()
                }
                signals.append(signal)
    
    signals.sort(key=lambda x: x['confidence'], reverse=True)
    return signals

def calculate_reversal_score(whale_size, whale_count, price_move, current_price):
    """Calculate confidence for reversal signal"""
    score = 0
    
    # Whale size
    if whale_size > 40000:
        score += 35
    elif whale_size > 20000:
        score += 25
    elif whale_size > 10000:
        score += 15
    else:
        score += 10
    
    # Whale count
    if whale_count >= 4:
        score += 20
    elif whale_count >= 3:
        score += 15
    else:
        score += 10
    
    # Price move magnitude (bigger move = stronger reversal signal)
    if price_move > 0.30:  # 30%+ move
        score += 30
    elif price_move > 0.20:
        score += 20
    elif price_move > 0.15:
        score += 15
    else:
        score += 10
    
    # Price position (extremes mean more room to reverse)
    if current_price > 0.80 or current_price < 0.20:
        score += 15
    elif current_price > 0.70 or current_price < 0.30:
        score += 10
    
    return min(score, 100)

def format_signals(signals):
    """Format signals for output"""
    if not signals:
        return None
    
    output = f"🔄 **MOMENTUM REVERSAL** ({len(signals)} signal(s))\n\n"
    
    for sig in signals[:3]:
        rev = sig['reversal']
        emoji = "🔥" if sig['confidence'] >= 85 else "⚡"
        
        output += f"{emoji} **{rev['type'].replace('_', ' ').title()}** ({sig['confidence']}% confidence)\n"
        output += f"**Market:** {sig['market_question'][:70]}...\n"
        output += f"**Signal:** {rev['signal']} {sig['outcome']} @ {sig['current_price']:.2f}\n"
        output += f"**Whales:** {sig['whale_count']} traders, ${rev['whale_size']:,.0f}\n"
        output += f"**Analysis:** {rev['explanation']}\n"
        output += f"🔗 polymarket.com/{sig['market_slug']}\n\n"
    
    return output

if __name__ == "__main__":
    print("🔍 Scanning for momentum reversals...")
    signals = detect_reversals()
    
    if signals:
        print(f"\n✅ Found {len(signals)} reversal signal(s)!\n")
        print(format_signals(signals))
    else:
        print("❌ No reversal patterns detected.")
