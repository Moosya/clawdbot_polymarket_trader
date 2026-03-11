#!/usr/bin/env python3
"""
Smart Money Divergence Detector
Finds when whales bet OPPOSITE direction from crowd sentiment (market odds)

Theory: If market is at 0.70 YES (crowd bullish) but whales buying NO,
        whales likely know something the crowd doesn't
"""

import sqlite3
import json
import sys
from datetime import datetime, timedelta
from collections import defaultdict

# Add path for market filters
sys.path.insert(0, '/home/clawdbot/clawd/scripts')
from market_filters import should_skip_market

DB_PATH = '/home/clawdbot/polymarket_runtime/data/trades.db'
WHALE_THRESHOLD = 3000  # Higher threshold for divergence signals
LOOKBACK_HOURS = 4
MIN_DIVERGENCE_SCORE = 70  # Minimum confidence to alert

def detect_divergence(lookback_hours=LOOKBACK_HOURS):
    """Detect smart money divergence patterns"""
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Get recent whale trades with price context
    query = """
    SELECT 
        marketSlug,
        COALESCE(marketQuestion, 'Unknown') as marketQuestion,
        outcome,
        side,
        price,
        sizeUsd,
        timestamp
    FROM trades
    WHERE 
        sizeUsd >= ?
        AND timestamp > ?
    ORDER BY timestamp DESC
    """
    
    cutoff_time = int((datetime.now() - timedelta(hours=lookback_hours)).timestamp())
    cur.execute(query, (WHALE_THRESHOLD, cutoff_time))
    trades = cur.fetchall()
    conn.close()
    
    # Analyze divergence by market+outcome
    market_analysis = defaultdict(lambda: {
        'trades': [],
        'whale_direction': None,
        'market_price': None,
        'total_size': 0
    })
    
    for trade in trades:
        slug, question, outcome, side, price, size, ts = trade
        key = (slug, outcome)
        market_analysis[key]['trades'].append({
            'side': side,
            'price': price,
            'size': size,
            'timestamp': ts
        })
        market_analysis[key]['market_price'] = price
        market_analysis[key]['total_size'] += size
        if 'question' not in market_analysis[key]:
            market_analysis[key]['question'] = question
            market_analysis[key]['outcome'] = outcome
    
    signals = []
    
    for (slug, outcome), data in market_analysis.items():
        if len(data['trades']) < 2:  # Need multiple whales for pattern
            continue
        
        # Determine whale consensus direction
        buy_size = sum(t['size'] for t in data['trades'] if t['side'] == 'BUY')
        sell_size = sum(t['size'] for t in data['trades'] if t['side'] == 'SELL')
        
        # Latest market price (from most recent trade)
        latest_price = data['trades'][0]['price']
        
        # Check for divergence
        divergence = None
        
        # Scenario 1: Market bullish (price > 0.60), whales selling
        if latest_price > 0.60 and sell_size > buy_size * 1.5:
            divergence = {
                'type': 'bearish_divergence',
                'signal': 'SELL',
                'crowd_sentiment': 'bullish',
                'whale_sentiment': 'bearish',
                'market_price': latest_price,
                'whale_size': sell_size,
                'explanation': f'Market at {latest_price:.2f} (crowd bullish) but whales selling ${sell_size:,.0f}'
            }
        
        # Scenario 2: Market bearish (price < 0.40), whales buying
        elif latest_price < 0.40 and buy_size > sell_size * 1.5:
            divergence = {
                'type': 'bullish_divergence',
                'signal': 'BUY',
                'crowd_sentiment': 'bearish',
                'whale_sentiment': 'bullish',
                'market_price': latest_price,
                'whale_size': buy_size,
                'explanation': f'Market at {latest_price:.2f} (crowd bearish) but whales buying ${buy_size:,.0f}'
            }
        
        if divergence:
            # Apply market filters BEFORE creating signal
            should_skip, reason = should_skip_market(data['question'], slug)
            if should_skip:
                continue  # Skip sports/entertainment/expired markets
            
            confidence = calculate_divergence_score(
                divergence['whale_size'],
                len(data['trades']),
                abs(divergence['market_price'] - 0.5),
                buy_size / (sell_size + 1) if divergence['signal'] == 'BUY' else sell_size / (buy_size + 1)
            )
            
            if confidence >= MIN_DIVERGENCE_SCORE:
                signal = {
                    'market_slug': slug,
                    'market_question': data['question'],
                    'outcome': outcome,
                    'divergence': divergence,
                    'whale_count': len(data['trades']),
                    'confidence': confidence,
                    'timestamp': datetime.now().isoformat()
                }
                signals.append(signal)
    
    # Sort by confidence
    signals.sort(key=lambda x: x['confidence'], reverse=True)
    return signals

def calculate_divergence_score(whale_size, whale_count, price_extremity, ratio):
    """
    Calculate confidence score for divergence signal
    
    Factors:
    - Larger whale positions = higher confidence
    - More whales = higher confidence
    - More extreme price = stronger divergence signal
    - Higher buy/sell ratio = stronger conviction
    """
    score = 0
    
    # Whale size factor
    if whale_size > 50000:
        score += 35
    elif whale_size > 25000:
        score += 25
    elif whale_size > 15000:
        score += 20
    else:
        score += 10
    
    # Whale count factor
    if whale_count >= 5:
        score += 25
    elif whale_count >= 3:
        score += 15
    else:
        score += 5
    
    # Price extremity (how far from 0.5)
    if price_extremity > 0.35:  # Price > 0.85 or < 0.15
        score += 25
    elif price_extremity > 0.25:  # Price > 0.75 or < 0.25
        score += 20
    elif price_extremity > 0.15:  # Price > 0.65 or < 0.35
        score += 15
    else:
        score += 5
    
    # Ratio strength (how lopsided whale bets are)
    if ratio > 5:
        score += 15
    elif ratio > 3:
        score += 10
    elif ratio > 2:
        score += 5
    
    return min(score, 100)

def format_signals(signals):
    """Format signals for output"""
    if not signals:
        return None
    
    output = f"💰 **SMART MONEY DIVERGENCE** ({len(signals)} signal(s))\n\n"
    
    for sig in signals[:3]:  # Top 3
        div = sig['divergence']
        emoji = "🔥" if sig['confidence'] >= 85 else "⚡"
        
        output += f"{emoji} **{div['type'].replace('_', ' ').title()}** ({sig['confidence']}% confidence)\n"
        output += f"**Market:** {sig['market_question'][:70]}...\n"
        output += f"**Signal:** {div['signal']} {sig['outcome']}\n"
        output += f"**Whales:** {sig['whale_count']} traders, ${div['whale_size']:,.0f}\n"
        output += f"**Analysis:** {div['explanation']}\n"
        output += f"🔗 polymarket.com/{sig['market_slug']}\n\n"
    
    return output

def save_signals_to_db(signals):
    """Save signals to trading database (with deduplication)"""
    if not signals:
        return
    
    TRADING_DB = '/home/clawdbot/polymarket_runtime/data/trading.db'
    
    try:
        conn = sqlite3.connect(TRADING_DB)
        cur = conn.cursor()
        
        inserted_count = 0
        skipped_count = 0
        
        for sig in signals:
            # Check if signal already exists for this market today
            # Handle both second and millisecond timestamps
            cur.execute("""
                SELECT id FROM signals 
                WHERE market_slug = ? 
                AND type = 'smart_money_divergence'
                AND (
                    DATE(timestamp, 'unixepoch') = DATE('now')
                    OR DATE(timestamp/1000, 'unixepoch') = DATE('now')
                )
                LIMIT 1
            """, (sig['market_slug'],))
            
            if cur.fetchone():
                skipped_count += 1
                continue  # Skip duplicate
            
            # Extract data from nested 'divergence' dict
            divergence = sig.get('divergence', {})
            direction = f"{divergence.get('signal', 'BUY')} {sig['outcome']}"
            market_price = divergence.get('market_price', 0)
            whale_size = divergence.get('whale_size', 0)
            div_type = divergence.get('type', 'unknown')
            explanation = divergence.get('explanation', 'No explanation')
            
            # Insert new signal
            cur.execute("""
                INSERT INTO signals (
                    timestamp, type, market_slug, market_question, 
                    outcome, confidence, direction, price, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(datetime.now().timestamp()),
                'smart_money_divergence',
                sig['market_slug'],
                sig['market_question'],
                sig['outcome'],
                sig['confidence'],
                direction,
                market_price,
                json.dumps({
                    'whale_count': sig['whale_count'],
                    'total_whale_size': whale_size,
                    'divergence_type': div_type,
                    'explanation': explanation
                })
            ))
            inserted_count += 1
        
        conn.commit()
        conn.close()
        
        if inserted_count > 0:
            print(f"✅ Saved {inserted_count} new signals to trading.db")
        if skipped_count > 0:
            print(f"⏭️  Skipped {skipped_count} duplicate signals (already exist today)")
        
    except Exception as e:
        print(f"⚠️ Failed to save to database: {e}")

if __name__ == "__main__":
    print("🔍 Scanning for smart money divergence...")
    signals = detect_divergence()
    
    if signals:
        print(f"\n✅ Found {len(signals)} divergence signal(s)!\n")
        print(format_signals(signals))
        
        # Save to database
        save_signals_to_db(signals)
    else:
        print("❌ No divergence patterns detected.")

