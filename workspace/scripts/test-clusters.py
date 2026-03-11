#!/usr/bin/env python3
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('/home/clawdbot/polymarket_runtime/data/trades.db')
cur = conn.cursor()

# Look for clusters in last 24 hours with lower threshold
query = """
SELECT 
    marketQuestion,
    outcome,
    side,
    COUNT(*) as whale_count,
    SUM(sizeUsd) as total_size,
    MIN(timestamp) as first_trade,
    MAX(timestamp) as last_trade
FROM trades
WHERE 
    sizeUsd >= 2000
    AND timestamp > ?
GROUP BY marketSlug, outcome, side
HAVING whale_count >= 3
    AND (MAX(timestamp) - MIN(timestamp)) <= 3600
ORDER BY whale_count DESC
LIMIT 10
"""

cutoff = int((datetime.now() - timedelta(hours=24)).timestamp())
cur.execute(query, (cutoff,))

results = cur.fetchall()
print(f"Found {len(results)} clusters in last 24h:\n")

for row in results:
    market, outcome, side, count, total, first, last = row
    span = (last - first) / 60
    print(f'✅ {count} whales | ${total:,.0f} | {span:.0f}min | {side} {outcome}')
    print(f'   {market[:80]}')
    print()
