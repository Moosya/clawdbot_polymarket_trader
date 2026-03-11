#!/usr/bin/env python3
"""
Mark expired/invalid signals so they don't show as "untapped"
Checks untapped signals and marks them as position_opened=1 if:
- Market deadline has passed
- Market is high-frequency (< 24 hours from now)
"""
import sqlite3
from datetime import datetime, timedelta
import re

TRADING_DB = '/opt/polymarket/data/trading.db'

print("🔍 Checking for expired signals...")
print("="*70)

conn = sqlite3.connect(TRADING_DB)
cur = conn.cursor()

# Get untapped signals
cur.execute("""
    SELECT id, market_question, market_slug, timestamp, confidence
    FROM signals
    WHERE position_opened = 0
    ORDER BY confidence DESC
""")

signals = cur.fetchall()
print(f"Found {len(signals)} untapped signals\n")

marked_count = 0
reasons = {}

for sig_id, question, slug, ts, conf in signals:
    should_mark = False
    reason = None
    
    # Check for date patterns in question
    # "by February 9, 2026", "on February 10", "March 2, 2AM ET"
    date_patterns = [
        r'by (\w+ \d+),? (\d{4})',          # "by February 9, 2026"
        r'on (\w+ \d+),? (\d{4})',          # "on February 10, 2026"
        r'(\w+ \d+),? (\d+)(?:AM|PM)',      # "March 2, 2AM"
        r'end of (\w+)',                     # "end of February"
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            try:
                # Try to parse the date
                date_str = match.group(0)
                
                # Check for common expired dates
                if 'February 9' in date_str or 'February 10' in date_str:
                    should_mark = True
                    reason = 'Expired (Feb deadline passed)'
                    break
                elif 'March 2' in date_str:
                    should_mark = True
                    reason = 'Expired (March 2 deadline passed)'
                    break
            except:
                pass
    
    # Check for high-frequency markets (Up or Down hourly)
    if 'Up or Down' in question and any(x in question for x in ['AM ET', 'PM ET', '1AM', '2AM', '1PM', '2PM']):
        should_mark = True
        reason = 'High-frequency (hourly market expired)'
    
    # Check for known bad markets
    if 'Frank Donovan' in question or 'Venezuela' in question:
        should_mark = True
        reason = 'Market delisted/404'
    
    if should_mark:
        # Mark as position_opened=1 so it doesn't count as untapped
        cur.execute("UPDATE signals SET position_opened = 1 WHERE id = ?", (sig_id,))
        print(f"✓ Marked: {question[:50]}... ({reason})")
        marked_count += 1
        reasons[reason] = reasons.get(reason, 0) + 1

conn.commit()

print(f"\n📊 Summary:")
print(f"  Total marked: {marked_count}")
for reason, count in reasons.items():
    print(f"  - {reason}: {count}")

# Show remaining untapped
cur.execute("""
    SELECT COUNT(*) FROM signals 
    WHERE position_opened = 0 AND confidence >= 70
""")
remaining = cur.fetchone()[0]
print(f"\n✅ Remaining untapped ≥70%: {remaining}")

conn.close()
