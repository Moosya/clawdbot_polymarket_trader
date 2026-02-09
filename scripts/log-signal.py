#!/usr/bin/env python3
"""
Log a trading signal to signal_history for performance tracking
"""
import sqlite3
import json
import sys
from pathlib import Path
from datetime import datetime
import hashlib

# Detect base directory and database location
if Path("/opt/polymarket/data/trading.db").exists():
    DB_PATH = Path("/opt/polymarket/data/trading.db")
    BASE_DIR = Path("/opt/polymarket")
elif Path("/workspace/polymarket_runtime/data/trading.db").exists():
    DB_PATH = Path("/workspace/polymarket_runtime/data/trading.db")
    BASE_DIR = Path("/workspace")
else:
    DB_PATH = Path("/workspace/data/trading.db")
    BASE_DIR = Path("/workspace")

def generate_signal_id(signal_type, market_slug, detected_at):
    """Generate unique signal ID"""
    data = f"{signal_type}:{market_slug}:{detected_at}"
    return hashlib.md5(data.encode()).hexdigest()[:12]

def log_signal(signal_type, market_slug, market_name, confidence, recommendation, 
               entry_price, reasoning=None, market_end_date=None):
    """
    Log a trading signal for later performance tracking
    
    Args:
        signal_type: whale_cluster, smart_money_divergence, momentum_reversal
        market_slug: Polymarket market slug
        market_name: Human-readable market name
        confidence: 0-100 confidence score
        recommendation: BUY_YES, BUY_NO, SELL_YES, SELL_NO
        entry_price: Recommended entry price
        reasoning: Optional JSON string with signal details
        market_end_date: Market end date (ISO format)
    
    Returns:
        signal_id if successful, None otherwise
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        schema_paths = [
            Path(__file__).parent / "signal-tracking-schema.sql",
            BASE_DIR / "scripts" / "signal-tracking-schema.sql"
        ]
        
        schema_sql = None
        for schema_path in schema_paths:
            if schema_path.exists():
                schema_sql = schema_path.read_text()
                break
        
        if not schema_sql:
            print(f"⚠️  Schema file not found, creating basic table", file=sys.stderr)
            # Create minimal schema if file not found
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS signal_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id TEXT UNIQUE NOT NULL,
                    signal_type TEXT NOT NULL,
                    market_slug TEXT NOT NULL,
                    market_name TEXT NOT NULL,
                    market_end_date TEXT,
                    detected_at INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    recommendation TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    reasoning TEXT,
                    outcome_known INTEGER DEFAULT 0,
                    outcome_checked_at INTEGER,
                    market_result TEXT,
                    final_price REAL,
                    signal_correct INTEGER,
                    edge REAL,
                    position_opened INTEGER DEFAULT 0,
                    position_id INTEGER,
                    actual_pnl REAL,
                    created_at INTEGER DEFAULT (strftime('%s', 'now')),
                    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
                );
                CREATE INDEX IF NOT EXISTS idx_signal_type ON signal_history(signal_type);
                CREATE INDEX IF NOT EXISTS idx_outcome_known ON signal_history(outcome_known);
            """)
        else:
            cursor.executescript(schema_sql)
        
        detected_at = int(datetime.now().timestamp())
        signal_id = generate_signal_id(signal_type, market_slug, detected_at)
        
        # Check if signal already exists
        cursor.execute("SELECT id FROM signal_history WHERE signal_id = ?", (signal_id,))
        if cursor.fetchone():
            print(f"⚠️  Signal {signal_id} already logged", file=sys.stderr)
            return signal_id
        
        # Insert signal
        cursor.execute("""
            INSERT INTO signal_history (
                signal_id, signal_type, market_slug, market_name,
                detected_at, confidence, recommendation, entry_price,
                reasoning, market_end_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            signal_id, signal_type, market_slug, market_name,
            detected_at, confidence, recommendation, entry_price,
            reasoning, market_end_date
        ))
        
        conn.commit()
        conn.close()
        
        return signal_id
        
    except Exception as e:
        print(f"❌ Error logging signal: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    if len(sys.argv) < 7:
        print("Usage: log-signal.py <signal_type> <market_slug> <market_name> <confidence> <recommendation> <entry_price> [reasoning_json] [market_end_date]")
        print("\nExample:")
        print('  log-signal.py smart_money_divergence "btc-up-or-down" "Bitcoin Up or Down" 85 BUY_YES 0.52 \'{"volume_ratio": 3.2}\' "2026-02-10T20:00:00Z"')
        sys.exit(1)
    
    signal_type = sys.argv[1]
    market_slug = sys.argv[2]
    market_name = sys.argv[3]
    confidence = float(sys.argv[4])
    recommendation = sys.argv[5]
    entry_price = float(sys.argv[6])
    reasoning = sys.argv[7] if len(sys.argv) > 7 else None
    market_end_date = sys.argv[8] if len(sys.argv) > 8 else None
    
    signal_id = log_signal(
        signal_type, market_slug, market_name, confidence,
        recommendation, entry_price, reasoning, market_end_date
    )
    
    if signal_id:
        print(f"✅ Signal logged: {signal_id}")
        print(f"   Type: {signal_type}")
        print(f"   Market: {market_name}")
        print(f"   Confidence: {confidence}%")
        print(f"   Recommendation: {recommendation} @ {entry_price}")
    else:
        sys.exit(1)
