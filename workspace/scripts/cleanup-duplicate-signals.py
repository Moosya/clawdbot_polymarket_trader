#!/usr/bin/env python3
"""
One-time cleanup: Remove duplicate signals from database explosion
Keeps only the most recent signal per (market_slug, type, date)
"""
import sqlite3
from datetime import datetime

TRADING_DB = '/opt/polymarket/data/trading.db'

print("🧹 Cleaning up duplicate signals...")
print("="*70)

conn = sqlite3.connect(TRADING_DB)
cur = conn.cursor()

# Get counts before
cur.execute("SELECT COUNT(*) FROM signals")
before_count = cur.fetchone()[0]
print(f"Signals before cleanup: {before_count:,}")

# Delete duplicates, keeping only the most recent per (market_slug, type, date)
# This SQL keeps the newest signal and deletes older duplicates
cur.execute("""
    DELETE FROM signals
    WHERE id NOT IN (
        SELECT MAX(id)
        FROM signals
        GROUP BY 
            market_slug,
            type,
            DATE(CASE 
                WHEN timestamp > 10000000000 THEN timestamp/1000 
                ELSE timestamp 
            END, 'unixepoch')
    )
""")

deleted = cur.rowcount
conn.commit()

# Get counts after
cur.execute("SELECT COUNT(*) FROM signals")
after_count = cur.fetchone()[0]

print(f"Signals after cleanup: {after_count:,}")
print(f"Deleted: {deleted:,} duplicates")
print(f"Savings: {(deleted/before_count*100):.1f}% reduction")

# Show remaining signal distribution
cur.execute("""
    SELECT 
        DATE(CASE WHEN timestamp > 10000000000 THEN timestamp/1000 ELSE timestamp END, 'unixepoch') as date,
        COUNT(*) as count
    FROM signals
    GROUP BY date
    ORDER BY date DESC
    LIMIT 10
""")

print(f"\n📊 Signals per day (after cleanup):")
for date, count in cur.fetchall():
    print(f"  {date}: {count} signals")

conn.close()
print("\n✅ Cleanup complete!")
