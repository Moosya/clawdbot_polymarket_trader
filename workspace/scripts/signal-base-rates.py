#!/usr/bin/env python3
"""
Calculate and store historical base rates for each signal type
Used to improve confidence calibration
"""

import sqlite3
import json
from collections import defaultdict

TRADING_DB = '/home/clawdbot/polymarket_runtime/data/trading.db'
BASE_RATES_FILE = '/workspace/memory/signal-base-rates.json'

def calculate_base_rates():
    """Calculate historical win rates for each signal type"""
    conn = sqlite3.connect(TRADING_DB)
    cur = conn.cursor()
    
    # Get all closed positions grouped by signal type
    cur.execute("""
        SELECT 
            s.type as signal_type,
            COUNT(*) as total,
            SUM(CASE WHEN p.pnl > 0 THEN 1 ELSE 0 END) as wins
        FROM paper_positions p
        JOIN signals s ON p.signal_id = s.id
        WHERE p.status = 'closed'
        GROUP BY s.type
    """)
    
    results = cur.fetchall()
    conn.close()
    
    base_rates = {}
    for signal_type, total, wins in results:
        if total >= 5:  # Minimum sample size
            win_rate = wins / total
            base_rates[signal_type] = {
                'win_rate': win_rate,
                'total_samples': total,
                'wins': wins,
                'confidence': int(win_rate * 100),
                'last_updated': None
            }
    
    return base_rates

def get_base_rate(signal_type):
    """Get stored base rate for a signal type"""
    try:
        with open(BASE_RATES_FILE, 'r') as f:
            base_rates = json.load(f)
            return base_rates.get(signal_type, {}).get('win_rate', 0.65)  # Default 65%
    except:
        return 0.65  # Conservative default

def save_base_rates(base_rates):
    """Save base rates to file"""
    with open(BASE_RATES_FILE, 'w') as f:
        json.dump(base_rates, f, indent=2)
    print(f"💾 Saved base rates to {BASE_RATES_FILE}")

def main():
    print("📊 Calculating signal base rates...")
    base_rates = calculate_base_rates()
    
    if not base_rates:
        print("⏳ No closed positions yet - using defaults")
        base_rates = {
            'whale_cluster': {'win_rate': 0.65, 'total_samples': 0, 'wins': 0, 'confidence': 65},
            'smart_money_divergence': {'win_rate': 0.70, 'total_samples': 0, 'wins': 0, 'confidence': 70},
            'momentum_reversal': {'win_rate': 0.60, 'total_samples': 0, 'wins': 0, 'confidence': 60}
        }
    
    print("\nBase Rates:")
    for sig_type, rates in base_rates.items():
        print(f"  {sig_type}: {rates['win_rate']*100:.1f}% ({rates['wins']}/{rates['total_samples']})")
    
    save_base_rates(base_rates)

if __name__ == '__main__':
    main()
