#!/usr/bin/env python3
import sqlite3
from datetime import datetime, timedelta

DB_PATH = '/workspace/projects/mission-control/data/mission-control.db'

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Check if weekly review task already exists
cur.execute("SELECT id FROM tasks WHERE name = 'Weekly Superforecaster Calibration Review'")
existing = cur.fetchone()

if existing:
    print(f"✓ Weekly review task already exists (ID: {existing[0]})")
else:
    # Calculate next_run (7 days from now in milliseconds)
    next_run_ms = int((datetime.now() + timedelta(days=7)).timestamp() * 1000)
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Insert weekly review task
    cur.execute("""
        INSERT INTO tasks (
            name, description, schedule, next_run, enabled, type, 
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'Weekly Superforecaster Calibration Review',
        'Comprehensive calibration analysis using Tetlock superforecasting principles: Brier scores, calibration curves, overconfidence detection, and signal performance review',
        'Weekly (Every Sunday)',
        next_run_ms,
        1,  # enabled
        'recurring',
        now_str,
        now_str
    ))
    
    conn.commit()
    task_id = cur.lastrowid
    next_run_human = datetime.fromtimestamp(next_run_ms / 1000).strftime('%Y-%m-%d %H:%M EST')
    
    print(f"✓ Added Weekly Superforecaster Calibration Review task (ID: {task_id})")
    print(f"  Next run: {next_run_human}")

conn.close()
