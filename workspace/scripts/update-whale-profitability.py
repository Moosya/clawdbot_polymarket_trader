#!/usr/bin/env python3
"""
Daily Whale Profitability Update
Checks for newly resolved markets and updates whale stats
"""

from trader_performance import TraderPerformance

if __name__ == '__main__':
    print("🐋 Daily Whale Profitability Update")
    print("=" * 70)
    print()
    
    tp = TraderPerformance()
    
    # Check for newly resolved markets (fast, only checks ~10-50 candidates)
    new_resolutions = tp.update_resolutions(limit=100)
    
    if new_resolutions > 0:
        print()
        print(f"✅ Updated stats for {new_resolutions} newly resolved markets")
        print()
        
        # Show top 5 updated whales
        rankings = tp.get_trader_rankings(min_closed=1)
        
        print("📊 Top 5 Profitable Whales (updated):")
        print("-" * 70)
        for i, (trader, stats) in enumerate(rankings[:5], 1):
            trader_short = f"{trader[:8]}...{trader[-4:]}"
            print(f"{i}. {trader_short}: ${stats['total_pnl']:+,.0f} " +
                  f"({stats['win_rate']:.0%} win rate, " +
                  f"{stats['trade_count']} trades + {stats['resolution_count']} resolutions)")
    else:
        print("✅ No new resolved markets found (all up to date)")
    
    print()
    print("=" * 70)
