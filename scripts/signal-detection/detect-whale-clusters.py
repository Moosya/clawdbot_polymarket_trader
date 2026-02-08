#!/usr/bin/env python3
"""
Whale Clustering Signal Detector
Finds when multiple whales bet on the same market/outcome within a short timeframe
"""

import sqlite3
import json
from datetime import datetime, timedelta

# Configuration
WHALE_THRESHOLD = 2000  # Minimum trade size to be considered a whale
CLUSTER_WINDOW = 3600   # Time window in seconds (1 hour)
MIN_WHALES = 3          # Minimum number of whales to trigger signal
HIGH_CONFIDENCE_WHALES = 5  # 5+ whales = very strong signal
DB_PATH = '/workspace/polymarket_runtime/data/trades.db'

def detect_clusters(lookback_hours=2):
    """Detect whale clusters in the last N hours"""
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Get recent whale trades grouped by market and outcome
    query = """
    SELECT 
        marketSlug,
        marketQuestion,
        outcome,
        side,
        COUNT(*) as whale_count,
        SUM(sizeUsd) as total_size,
        AVG(price) as avg_price,
        MIN(timestamp) as first_trade,
        MAX(timestamp) as last_trade,
        GROUP_CONCAT(sizeUsd || '@' || datetime(timestamp, 'unixepoch'), ' | ') as trades
    FROM trades
    WHERE 
        sizeUsd >= ?
        AND timestamp > ?
    GROUP BY marketSlug, outcome, side
    HAVING whale_count >= ?
        AND (MAX(timestamp) - MIN(timestamp)) <= ?
    ORDER BY whale_count DESC, total_size DESC
    """
    
    cutoff_time = int((datetime.now() - timedelta(hours=lookback_hours)).timestamp())
    
    cur.execute(query, (WHALE_THRESHOLD, cutoff_time, MIN_WHALES, CLUSTER_WINDOW))
    clusters = cur.fetchall()
    
    conn.close()
    
    signals = []
    for cluster in clusters:
        (market_slug, market_question, outcome, side, whale_count, 
         total_size, avg_price, first_trade, last_trade, trades) = cluster
        
        time_span_minutes = (last_trade - first_trade) / 60
        
        signal = {
            'market_slug': market_slug,
            'market_question': market_question,
            'outcome': outcome,
            'side': side,
            'whale_count': whale_count,
            'total_size': round(total_size, 2),
            'avg_price': round(avg_price, 4),
            'time_span_minutes': round(time_span_minutes, 1),
            'first_trade': datetime.fromtimestamp(first_trade).strftime('%Y-%m-%d %H:%M:%S'),
            'last_trade': datetime.fromtimestamp(last_trade).strftime('%Y-%m-%d %H:%M:%S'),
            'confidence': calculate_confidence(whale_count, total_size, time_span_minutes)
        }
        
        signals.append(signal)
    
    return signals

def calculate_confidence(whale_count, total_size, time_span):
    """Calculate confidence score 0-100"""
    score = 0
    
    # More whales = higher confidence
    if whale_count >= 5:
        score += 50  # Very strong signal
    elif whale_count >= 4:
        score += 35
    else:  # 3 whales
        score += 20
    
    # Larger total size = higher confidence
    if total_size > 50000:
        score += 30
    elif total_size > 25000:
        score += 20
    elif total_size > 15000:
        score += 15
    elif total_size > 10000:
        score += 10
    
    # Faster clustering = MUCH higher confidence (coordinated action)
    if time_span < 1:  # Same minute = coordinated
        score += 25
    elif time_span < 5:  # Within 5 min = very fast
        score += 20
    elif time_span < 15:
        score += 15
    elif time_span < 30:
        score += 10
    
    return min(score, 100)

def format_alert(signals):
    """Format signals for Telegram alert"""
    if not signals:
        return None
    
    alert = "🐋 **WHALE CLUSTER DETECTED**\n\n"
    
    for i, sig in enumerate(signals[:5], 1):  # Top 5 signals
        confidence_emoji = "🔥" if sig['confidence'] >= 80 else "⚡" if sig['confidence'] >= 60 else "📊"
        
        alert += f"{confidence_emoji} **Signal #{i}** (Confidence: {sig['confidence']})\n"
        alert += f"**Market:** {sig['market_question'][:80]}...\n" if len(sig['market_question']) > 80 else f"**Market:** {sig['market_question']}\n"
        alert += f"**Direction:** {sig['side']} {sig['outcome']}\n"
        alert += f"**Whales:** {sig['whale_count']} traders | ${sig['total_size']:,.0f} total\n"
        alert += f"**Timing:** {sig['time_span_minutes']} min window\n"
        alert += f"**Avg Price:** {sig['avg_price']:.4f}\n"
        alert += f"🔗 polymarket.com/{sig['market_slug']}\n\n"
    
    return alert

if __name__ == "__main__":
    print("🔍 Scanning for whale clusters...")
    signals = detect_clusters(lookback_hours=2)
    
    if signals:
        print(f"\n✅ Found {len(signals)} cluster signal(s)!\n")
        alert = format_alert(signals)
        print(alert)
        
        # Save to file for heartbeat to pick up
        with open('/workspace/signals/whale-clusters.json', 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'signals': signals
            }, f, indent=2)
        
        print(f"📝 Saved {len(signals)} signals to whale-clusters.json")
    else:
        print("❌ No clusters detected in the last 2 hours.")
