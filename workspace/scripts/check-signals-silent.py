#!/usr/bin/env python3
"""
Silent signal checker - only outputs if high-confidence signals found
Use in heartbeat to avoid token waste on quiet periods
"""

import sys
import os

# Add scripts to path
sys.path.insert(0, '/workspace/scripts')

# Import the detection logic
import sqlite3
import json
from datetime import datetime, timedelta

DB_PATH = '/home/clawdbot/polymarket_runtime/data/trades.db'
WHALE_THRESHOLD = 2000
CLUSTER_WINDOW = 3600
MIN_WHALES = 3
MIN_CONFIDENCE_TO_ALERT = 80  # Only alert on very high confidence

def detect_clusters(lookback_hours=2):
    """Detect whale clusters"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
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
        MAX(timestamp) as last_trade
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
         total_size, avg_price, first_trade, last_trade) = cluster
        
        time_span_minutes = (last_trade - first_trade) / 60
        confidence = calculate_confidence(whale_count, total_size, time_span_minutes)
        
        # Only include high-confidence signals
        if confidence >= MIN_CONFIDENCE_TO_ALERT:
            signal = {
                'market_slug': market_slug,
                'market_question': market_question,
                'outcome': outcome,
                'side': side,
                'whale_count': whale_count,
                'total_size': round(total_size, 2),
                'avg_price': round(avg_price, 4),
                'time_span_minutes': round(time_span_minutes, 1),
                'confidence': confidence
            }
            signals.append(signal)
    
    return signals

def calculate_confidence(whale_count, total_size, time_span):
    """Calculate confidence score 0-100"""
    score = 0
    
    if whale_count >= 5:
        score += 50
    elif whale_count >= 4:
        score += 35
    else:
        score += 20
    
    if total_size > 50000:
        score += 30
    elif total_size > 25000:
        score += 20
    elif total_size > 15000:
        score += 15
    elif total_size > 10000:
        score += 10
    
    if time_span < 1:
        score += 25
    elif time_span < 5:
        score += 20
    elif time_span < 15:
        score += 15
    elif time_span < 30:
        score += 10
    
    return min(score, 100)

if __name__ == "__main__":
    signals = detect_clusters(lookback_hours=2)
    
    if signals:
        # Output alert-worthy signals
        print(f"🐋 **WHALE SIGNALS** ({len(signals)} high-confidence)\n")
        
        for sig in signals[:3]:  # Top 3
            emoji = "🔥" if sig['confidence'] >= 90 else "⚡"
            print(f"{emoji} **{sig['whale_count']} whales** → {sig['side']} {sig['outcome']} ({sig['confidence']}% confidence)")
            print(f"   ${sig['total_size']:,.0f} in {sig['time_span_minutes']:.0f}min")
            print(f"   {sig['market_question'][:70]}...")
            print(f"   🔗 polymarket.com/{sig['market_slug']}")
            print()
    else:
        # Silent - no output means HEARTBEAT_OK
        pass
