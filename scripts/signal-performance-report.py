#!/usr/bin/env python3
"""
Generate signal performance report
Shows accuracy by signal type, confidence levels, and overall metrics
"""
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta

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

def print_section(title):
    """Print section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def get_overall_stats(cursor):
    """Get overall signal statistics"""
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN outcome_known = 1 THEN 1 ELSE 0 END) as resolved,
            SUM(CASE WHEN signal_correct = 1 THEN 1 ELSE 0 END) as correct,
            AVG(confidence) as avg_confidence,
            AVG(CASE WHEN outcome_known = 1 THEN edge END) as avg_edge,
            SUM(CASE WHEN position_opened = 1 THEN 1 ELSE 0 END) as traded
        FROM signal_history
    """)
    return cursor.fetchone()

def get_performance_by_type(cursor):
    """Get performance metrics grouped by signal type"""
    cursor.execute("""
        SELECT * FROM signal_performance_summary
        ORDER BY accuracy_pct DESC NULLS LAST
    """)
    return cursor.fetchall()

def get_performance_by_confidence(cursor):
    """Get performance by confidence buckets"""
    cursor.execute("""
        SELECT 
            CASE 
                WHEN confidence >= 90 THEN '90-100%'
                WHEN confidence >= 80 THEN '80-89%'
                WHEN confidence >= 70 THEN '70-79%'
                ELSE '<70%'
            END as confidence_bucket,
            COUNT(*) as total,
            SUM(CASE WHEN outcome_known = 1 THEN 1 ELSE 0 END) as resolved,
            SUM(CASE WHEN signal_correct = 1 THEN 1 ELSE 0 END) as correct,
            CAST(SUM(CASE WHEN signal_correct = 1 THEN 1 ELSE 0 END) AS REAL) / 
                NULLIF(SUM(CASE WHEN outcome_known = 1 THEN 1 ELSE 0 END), 0) * 100 as accuracy,
            AVG(CASE WHEN outcome_known = 1 THEN edge END) as avg_edge
        FROM signal_history
        WHERE outcome_known = 1
        GROUP BY confidence_bucket
        ORDER BY confidence_bucket DESC
    """)
    return cursor.fetchall()

def get_recent_signals(cursor, days=7):
    """Get recent signals"""
    cutoff = int((datetime.now() - timedelta(days=days)).timestamp())
    cursor.execute("""
        SELECT 
            signal_type,
            market_name,
            confidence,
            recommendation,
            entry_price,
            market_result,
            signal_correct,
            edge,
            datetime(detected_at, 'unixepoch') as detected
        FROM signal_history
        WHERE detected_at >= ?
        ORDER BY detected_at DESC
        LIMIT 20
    """, (cutoff,))
    return cursor.fetchall()

def generate_report():
    """Generate comprehensive signal performance report"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='signal_history'")
        if not cursor.fetchone():
            print("⚠️  No signal history found. Start logging signals with log-signal.py")
            return
        
        print_section("🎯 SIGNAL PERFORMANCE REPORT")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Overall Stats
        total, resolved, correct, avg_conf, avg_edge, traded = get_overall_stats(cursor)
        
        if total == 0:
            print("📊 No signals logged yet")
            return
        
        accuracy = (correct / resolved * 100) if resolved > 0 else 0
        
        print("📊 OVERALL STATISTICS")
        print(f"   Total Signals: {total}")
        print(f"   Resolved: {resolved} ({resolved/total*100:.1f}%)")
        print(f"   Pending: {total - resolved}")
        print(f"   Traded: {traded}")
        print(f"   Avg Confidence: {avg_conf:.1f}%")
        
        if resolved > 0:
            print(f"\n   🎯 Accuracy: {accuracy:.1f}% ({correct}/{resolved})")
            print(f"   📈 Avg Edge: {avg_edge:+.3f}")
        
        # Performance by Signal Type
        print_section("📈 PERFORMANCE BY SIGNAL TYPE")
        
        type_data = get_performance_by_type(cursor)
        
        if type_data:
            print(f"{'Type':<25} {'Count':<8} {'Resolved':<10} {'Accuracy':<12} {'Avg Edge':<12} {'Traded':<8}")
            print("-" * 80)
            
            for row in type_data:
                sig_type, total, avg_conf, resolved, correct, accuracy, avg_edge, opened, pnl = row
                acc_str = f"{accuracy:.1f}%" if accuracy is not None else "N/A"
                edge_str = f"{avg_edge:+.3f}" if avg_edge is not None else "N/A"
                pnl_str = f"${pnl:.2f}" if pnl else "$0.00"
                
                print(f"{sig_type:<25} {total:<8} {resolved:<10} {acc_str:<12} {edge_str:<12} {opened:<8}")
                if pnl:
                    print(f"{'':25} {'':8} {'':10} {'':12} Total P&L: {pnl_str}")
        else:
            print("No resolved signals yet")
        
        # Performance by Confidence Level
        if resolved > 0:
            print_section("🎲 PERFORMANCE BY CONFIDENCE LEVEL")
            
            conf_data = get_performance_by_confidence(cursor)
            
            if conf_data:
                print(f"{'Confidence':<15} {'Total':<8} {'Resolved':<10} {'Correct':<10} {'Accuracy':<12} {'Avg Edge':<12}")
                print("-" * 75)
                
                for bucket, total, resolved, correct, accuracy, avg_edge in conf_data:
                    acc_str = f"{accuracy:.1f}%" if accuracy is not None else "N/A"
                    edge_str = f"{avg_edge:+.3f}" if avg_edge is not None else "N/A"
                    print(f"{bucket:<15} {total:<8} {resolved:<10} {correct:<10} {acc_str:<12} {edge_str:<12}")
        
        # Recent Signals
        print_section("📅 RECENT SIGNALS (Last 7 Days)")
        
        recent = get_recent_signals(cursor, days=7)
        
        if recent:
            for sig_type, market, conf, rec, entry, result, correct, edge, detected in recent:
                status_emoji = "✅" if correct == 1 else "❌" if correct == 0 else "⏳"
                result_str = f"→ {result}" if result else "(pending)"
                edge_str = f"edge: {edge:+.3f}" if edge is not None else ""
                
                print(f"{status_emoji} [{detected}] {sig_type}")
                print(f"   {market[:60]}")
                print(f"   {conf:.0f}% confident: {rec} @ {entry:.2f} {result_str} {edge_str}")
                print()
        else:
            print("No signals in the last 7 days")
        
        # Pending Signals
        cursor.execute("SELECT COUNT(*) FROM signal_history WHERE outcome_known = 0")
        pending_count = cursor.fetchone()[0]
        
        if pending_count > 0:
            print_section(f"⏳ PENDING SIGNALS ({pending_count})")
            print("Run `python3 update-signal-outcomes.py` to check for resolved markets\n")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error generating report: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    generate_report()
