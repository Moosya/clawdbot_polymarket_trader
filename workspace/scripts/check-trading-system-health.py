#!/usr/bin/env python3
"""
Trading System Health Check
Verifies that all components of the trading pipeline are working
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = 'polymarket_runtime/data/trading.db'

def check_database_exists():
    """Check if database file exists"""
    return Path(DB_PATH).exists()

def check_tables_exist():
    """Check if all required tables exist"""
    required_tables = ['trades', 'signals', 'paper_positions']
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [row[0] for row in cursor.fetchall()]
    
    missing = [t for t in required_tables if t not in existing_tables]
    
    conn.close()
    
    return existing_tables, missing

def check_recent_trades(hours=12):
    """Check if trades have been collected recently"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if trades table exists first
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
    if not cursor.fetchone():
        conn.close()
        return None, "trades table does not exist"
    
    # Check for recent trades
    cutoff = int((datetime.now() - timedelta(hours=hours)).timestamp())
    cursor.execute("SELECT COUNT(*) FROM trades WHERE timestamp > ?", (cutoff,))
    count = cursor.fetchone()[0]
    
    # Get total trades
    cursor.execute("SELECT COUNT(*) FROM trades")
    total = cursor.fetchone()[0]
    
    # Get most recent trade timestamp
    cursor.execute("SELECT MAX(timestamp) FROM trades")
    latest = cursor.fetchone()[0]
    
    conn.close()
    
    if latest:
        latest_dt = datetime.fromtimestamp(latest)
        age_hours = (datetime.now() - latest_dt).total_seconds() / 3600
    else:
        latest_dt = None
        age_hours = None
    
    return {
        'recent_count': count,
        'total_count': total,
        'latest_timestamp': latest_dt,
        'hours_since_last': age_hours
    }, None

def check_recent_signals(hours=24):
    """Check if signals have been generated recently"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cutoff = int((datetime.now() - timedelta(hours=hours)).timestamp())
    cursor.execute("SELECT COUNT(*) FROM signals WHERE timestamp > ?", (cutoff,))
    recent = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM signals")
    total = cursor.fetchone()[0]
    
    conn.close()
    
    return {'recent_count': recent, 'total_count': total}

def check_open_positions():
    """Check current open positions"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM paper_positions WHERE status='open'")
    open_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM paper_positions")
    total = cursor.fetchone()[0]
    
    conn.close()
    
    return {'open': open_count, 'total': total}

def main():
    print("🏥 Trading System Health Check")
    print("=" * 60)
    print()
    
    issues = []
    warnings = []
    
    # 1. Database exists
    print("1️⃣  Checking database...")
    if check_database_exists():
        print("   ✅ Database file exists")
    else:
        print("   ❌ Database file missing!")
        issues.append("Database file not found")
        return  # Can't continue without database
    
    # 2. Tables exist
    print("\n2️⃣  Checking database schema...")
    existing, missing = check_tables_exist()
    print(f"   Existing tables: {', '.join(existing)}")
    if missing:
        print(f"   ❌ Missing tables: {', '.join(missing)}")
        issues.append(f"Missing required tables: {', '.join(missing)}")
    else:
        print("   ✅ All required tables present")
    
    # 3. Recent trades
    print("\n3️⃣  Checking trade collection...")
    trade_data, error = check_recent_trades(12)
    if error:
        print(f"   ❌ {error}")
        issues.append(error)
    elif trade_data:
        recent = trade_data['recent_count']
        total = trade_data['total_count']
        latest = trade_data['latest_timestamp']
        age = trade_data['hours_since_last']
        
        print(f"   Trades in last 12h: {recent}")
        print(f"   Total trades: {total:,}")
        if latest:
            print(f"   Most recent: {latest.strftime('%Y-%m-%d %H:%M:%S')} ({age:.1f}h ago)")
        
        if recent == 0 and total > 0:
            warnings.append(f"No trades collected in last 12h (last was {age:.1f}h ago)")
            print(f"   ⚠️  No recent trades (last {age:.1f}h ago)")
        elif recent == 0 and total == 0:
            issues.append("No trades have ever been collected")
            print(f"   ❌ No trades in database at all")
        elif age and age > 2:
            warnings.append(f"Trade collection may be stale ({age:.1f}h since last)")
            print(f"   ⚠️  Trades are {age:.1f}h old")
        else:
            print("   ✅ Trade collection active")
    
    # 4. Signal generation
    print("\n4️⃣  Checking signal generation...")
    signal_data = check_recent_signals(24)
    print(f"   Signals in last 24h: {signal_data['recent_count']}")
    print(f"   Total signals: {signal_data['total_count']}")
    
    if signal_data['recent_count'] == 0 and signal_data['total_count'] > 0:
        warnings.append("No signals generated in last 24h")
        print("   ⚠️  No recent signals")
    elif signal_data['total_count'] == 0:
        # This might be OK if we just started or markets are quiet
        print("   ℹ️  No signals yet (may be normal)")
    else:
        print("   ✅ Signal generation active")
    
    # 5. Position status
    print("\n5️⃣  Checking positions...")
    pos_data = check_open_positions()
    print(f"   Open positions: {pos_data['open']}")
    print(f"   Total positions: {pos_data['total']}")
    print("   ✅ Position tracking active")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    
    if issues:
        print("\n🚨 CRITICAL ISSUES:")
        for issue in issues:
            print(f"   • {issue}")
    
    if warnings:
        print("\n⚠️  WARNINGS:")
        for warning in warnings:
            print(f"   • {warning}")
    
    if not issues and not warnings:
        print("\n✅ All systems operational!")
    
    # Exit code
    if issues:
        print("\n❌ System has critical issues - needs attention")
        return 2
    elif warnings:
        print("\n⚠️  System working but has warnings")
        return 1
    else:
        print("\n✅ System healthy")
        return 0

if __name__ == '__main__':
    exit(main())
