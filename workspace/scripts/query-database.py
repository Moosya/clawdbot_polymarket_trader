#!/usr/bin/env python3
"""
Simple database query helper for budget models
Usage: python3 scripts/query-database.py "SELECT * FROM table"
"""

import sys
import sqlite3

DB_PATH = 'polymarket_runtime/data/trading.db'

def query_db(sql):
    """Execute a read-only query and return results"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        if not rows:
            print("No results found")
            return
        
        # Print column headers
        columns = [description[0] for description in cursor.description]
        print(" | ".join(columns))
        print("-" * (sum(len(c) for c in columns) + len(columns) * 3))
        
        # Print rows
        for row in rows:
            values = [str(row[col]) for col in columns]
            print(" | ".join(values))
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/query-database.py 'SELECT * FROM table'")
        sys.exit(1)
    
    query_db(sys.argv[1])
