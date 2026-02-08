#!/usr/bin/env python3
"""Apply trading schema to trades.db"""

import sqlite3

DB_PATH = '/workspace/polymarket_runtime/data/trading.db'  # Shared with dashboard
SCHEMA_FILE = '/workspace/projects/polymarket/schema-trading.sql'

def apply_schema():
    with open(SCHEMA_FILE, 'r') as f:
        schema_sql = f.read()
    
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()
    
    print("✅ Trading schema applied successfully")
    print("   - signals table")
    print("   - paper_positions table")
    print("   - portfolio_snapshots table")

if __name__ == '__main__':
    apply_schema()
