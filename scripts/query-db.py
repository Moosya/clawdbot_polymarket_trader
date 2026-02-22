#!/usr/bin/env python3
import sqlite3, sys
conn = sqlite3.connect('/opt/polymarket/data/trades.db')
cur = conn.cursor()
cur.execute(sys.argv[1])
results = cur.fetchall()
for row in results: print(row)
