#!/usr/bin/env python3
"""
Whale Clustering Signal Detector
Finds when multiple whales bet on the same market/outcome within a short timeframe
"""

import sqlite3
import json
from datetime import datetime, timedelta

# Configuration
WHALE_THRESHOLD = 100  # Lowered from 2000 for testing
CLUSTER_WINDOW = 3600   # Time window in seconds (1 hour)
MIN_WHALES = 3          # Minimum number of whales to trigger signal
HIGH_CONFIDENCE_WHALES = 5  # 5+ whales = very strong signal

# Database paths
TRADES_DB = '/home/clawdbot/polymarket_runtime/data/trades.db'  # Read trades from here
SIGNALS_DB = '/home/clawdbot/polymarket_runtime/data/trading.db'  # Write signals here

def detect_clusters(lookback_hours=2):
    """Detect whale clusters in the last N hours"""
    
    # Connect to trades database
    trades_conn = sqlite3.connect(TRADES_DB)
    trades_cur = trades_conn.cursor()
    
    # Get current timestamp
    now = int(datetime.now().timestamp())
    lookback_time = now - (lookback_hours * 3600)
    
    # Get recent whale trades grouped by market and outcome
    query = """
    SELECT 
        marketSlug,
        marketQuestion,
        outcome,
        side,
        COUNT(DISTINCT trader) as whale_count,
        SUM(sizeUsd) as total_volume,
        AVG(price) as avg_price,
        MAX(timestamp) as last_trade_time
    FROM trades
    WHERE sizeUsd >= ?
      AND timestamp >= ?
    GROUP BY marketSlug, outcome, side
    HAVING whale_count >= ?
    ORDER BY whale_count DESC, total_volume DESC
    """
    
    trades_cur.execute(query, (WHALE_THRESHOLD, lookback_time, MIN_WHALES))
    clusters = trades_cur.fetchall()
    
    signals = []
    
    for cluster in clusters:
        market_slug, market_question, outcome, side, whale_count, total_volume, avg_price, last_trade = cluster
        
        # Calculate confidence based on whale count
        if whale_count >= HIGH_CONFIDENCE_WHALES:
            confidence = 85
        elif whale_count >= MIN_WHALES + 1:
            confidence = 75
        else:
            confidence = 65
        
        signal = {
            'type': 'whale_cluster',
            'confidence': confidence,
            'market_slug': market_slug,
            'market_question': market_question or 'Unknown',
            'outcome': outcome,
            'direction': side,  # BUY or SELL
            'price': round(avg_price, 3),
            'details': json.dumps({
                'whale_count': whale_count,
                'total_volume': round(total_volume, 2),
                'avg_price': round(avg_price, 3),
                'lookback_hours': lookback_hours,
                'threshold': WHALE_THRESHOLD
            }),
            'timestamp': int(datetime.now().timestamp())
        }
        
        signals.append(signal)
    
    trades_conn.close()
    
    # Save signals to signals database
    if signals:
        signals_conn = sqlite3.connect(SIGNALS_DB)
        signals_cur = signals_conn.cursor()
        
        for signal in signals:
            signals_cur.execute("""
                INSERT INTO signals (type, confidence, market_slug, market_question, outcome, direction, price, details, timestamp, position_opened, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, datetime('now'))
            """, (
                signal['type'],
                signal['confidence'],
                signal['market_slug'],
                signal['market_question'],
                signal['outcome'],
                signal['direction'],
                signal['price'],
                signal['details'],
                signal['timestamp']
            ))
        
        signals_conn.commit()
        signals_conn.close()
    
    return signals

if __name__ == '__main__':
    signals = detect_clusters(lookback_hours=2)
    print(json.dumps(signals, indent=2))
