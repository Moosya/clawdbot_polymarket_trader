#!/usr/bin/env python3
"""
Trading Signal Analysis
Analyzes historical signal performance to improve algorithms
"""

import sqlite3
import json
from datetime import datetime, timedelta
from collections import defaultdict

TRADING_DB = '/workspace/polymarket_runtime/data/trading.db'

def analyze_signal_performance():
    """Analyze which signal types and confidence levels perform best"""
    conn = sqlite3.connect(TRADING_DB)
    cur = conn.cursor()
    
    # Get all closed positions with their originating signals
    cur.execute("""
        SELECT 
            s.type as signal_type,
            s.confidence,
            p.pnl,
            p.roi,
            p.entry_time,
            p.exit_time,
            p.close_reason
        FROM paper_positions p
        JOIN signals s ON p.signal_id = s.id
        WHERE p.status = 'closed'
    """)
    
    results = cur.fetchall()
    conn.close()
    
    if not results:
        return {
            'total_closed': 0,
            'message': 'No closed positions yet - need more data for analysis'
        }
    
    # Organize by signal type
    by_type = defaultdict(lambda: {'trades': 0, 'wins': 0, 'total_pnl': 0, 'confidences': []})
    by_confidence_bucket = defaultdict(lambda: {'trades': 0, 'wins': 0, 'total_pnl': 0})
    
    for signal_type, confidence, pnl, roi, entry_time, exit_time, close_reason in results:
        # By signal type
        by_type[signal_type]['trades'] += 1
        if pnl > 0:
            by_type[signal_type]['wins'] += 1
        by_type[signal_type]['total_pnl'] += pnl
        by_type[signal_type]['confidences'].append(confidence)
        
        # By confidence bucket (70-79, 80-89, 90-100)
        if confidence >= 90:
            bucket = '90-100%'
        elif confidence >= 80:
            bucket = '80-89%'
        else:
            bucket = '70-79%'
        
        by_confidence_bucket[bucket]['trades'] += 1
        if pnl > 0:
            by_confidence_bucket[bucket]['wins'] += 1
        by_confidence_bucket[bucket]['total_pnl'] += pnl
    
    # Calculate win rates and averages
    analysis = {
        'total_closed': len(results),
        'by_signal_type': {},
        'by_confidence': {},
        'recommendations': []
    }
    
    # Analyze by signal type
    for sig_type, stats in by_type.items():
        win_rate = stats['wins'] / stats['trades'] if stats['trades'] > 0 else 0
        avg_pnl = stats['total_pnl'] / stats['trades'] if stats['trades'] > 0 else 0
        
        analysis['by_signal_type'][sig_type] = {
            'trades': stats['trades'],
            'win_rate': round(win_rate, 3),
            'total_pnl': round(stats['total_pnl'], 2),
            'avg_pnl_per_trade': round(avg_pnl, 2),
            'avg_confidence': round(sum(stats['confidences']) / len(stats['confidences']), 1)
        }
    
    # Analyze by confidence bucket
    for bucket, stats in by_confidence_bucket.items():
        win_rate = stats['wins'] / stats['trades'] if stats['trades'] > 0 else 0
        avg_pnl = stats['total_pnl'] / stats['trades'] if stats['trades'] > 0 else 0
        
        analysis['by_confidence'][bucket] = {
            'trades': stats['trades'],
            'win_rate': round(win_rate, 3),
            'total_pnl': round(stats['total_pnl'], 2),
            'avg_pnl_per_trade': round(avg_pnl, 2)
        }
    
    # Generate recommendations
    recommendations = []
    
    # Check if high confidence signals actually perform better
    if '90-100%' in analysis['by_confidence'] and '70-79%' in analysis['by_confidence']:
        high_conf_wr = analysis['by_confidence']['90-100%']['win_rate']
        low_conf_wr = analysis['by_confidence']['70-79%']['win_rate']
        
        if high_conf_wr < low_conf_wr:
            recommendations.append({
                'severity': 'warning',
                'issue': 'Confidence miscalibration',
                'detail': f"90-100% confidence signals have {high_conf_wr:.1%} win rate vs {low_conf_wr:.1%} for 70-79%",
                'action': 'Review confidence calculation logic - may be inverted or need recalibration'
            })
    
    # Check for underperforming signal types
    for sig_type, stats in analysis['by_signal_type'].items():
        if stats['trades'] >= 5:  # Only if we have enough data
            if stats['win_rate'] < 0.4:  # Less than 40% win rate
                recommendations.append({
                    'severity': 'error',
                    'issue': f'{sig_type} underperforming',
                    'detail': f"Win rate: {stats['win_rate']:.1%}, Avg P&L: ${stats['avg_pnl_per_trade']:.2f}",
                    'action': f'Consider disabling {sig_type} or lowering position size until algorithm is fixed'
                })
            elif stats['win_rate'] > 0.7:  # Very high win rate
                recommendations.append({
                    'severity': 'success',
                    'issue': f'{sig_type} performing well',
                    'detail': f"Win rate: {stats['win_rate']:.1%}, Avg P&L: ${stats['avg_pnl_per_trade']:.2f}",
                    'action': f'Consider increasing position size or confidence threshold for {sig_type}'
                })
    
    analysis['recommendations'] = recommendations
    return analysis

def check_open_position_health():
    """Check if open positions are showing concerning patterns"""
    conn = sqlite3.connect(TRADING_DB)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN notes LIKE '%unrealized_pnl%' THEN 1 ELSE 0 END) as with_prices
        FROM paper_positions
        WHERE status = 'open'
    """)
    
    total, with_prices = cur.fetchone()
    
    # Get positions with price data
    cur.execute("""
        SELECT market_question, notes
        FROM paper_positions
        WHERE status = 'open' AND notes LIKE '%unrealized_pnl%'
    """)
    
    positions = []
    total_unrealized = 0
    
    for market_question, notes in cur.fetchall():
        try:
            notes_data = json.loads(notes)
            if 'price_data' in notes_data:
                unrealized_pnl = notes_data['price_data']['unrealized_pnl']
                total_unrealized += unrealized_pnl
                
                if unrealized_pnl < -20:  # Position down more than $20
                    positions.append({
                        'market': market_question[:60],
                        'unrealized_pnl': unrealized_pnl
                    })
        except:
            pass
    
    conn.close()
    
    warnings = []
    
    if total > 0 and with_prices < total:
        warnings.append(f"{total - with_prices} positions missing price updates")
    
    if total_unrealized < -50:
        warnings.append(f"Total unrealized loss: ${total_unrealized:.2f}")
    
    if len(positions) >= 2:
        warnings.append(f"{len(positions)} positions with losses >$20")
    
    return {
        'total_open': total,
        'positions_with_prices': with_prices,
        'total_unrealized_pnl': round(total_unrealized, 2),
        'concerning_positions': positions[:3],  # Top 3 worst
        'warnings': warnings
    }

def format_analysis_report():
    """Generate human-readable analysis report"""
    print("📊 TRADING SIGNAL ANALYSIS")
    print("=" * 60)
    print()
    
    # Historical performance
    perf = analyze_signal_performance()
    
    if perf['total_closed'] == 0:
        print("⚠️  No closed positions yet - insufficient data for analysis")
        print()
    else:
        print(f"📈 Historical Performance ({perf['total_closed']} closed positions)")
        print()
        
        # By signal type
        if perf['by_signal_type']:
            print("By Signal Type:")
            for sig_type, stats in perf['by_signal_type'].items():
                emoji = "✅" if stats['win_rate'] >= 0.6 else "⚠️" if stats['win_rate'] >= 0.4 else "❌"
                print(f"  {emoji} {sig_type}:")
                print(f"     Trades: {stats['trades']}, Win Rate: {stats['win_rate']:.1%}")
                print(f"     Total P&L: ${stats['total_pnl']:.2f}, Avg: ${stats['avg_pnl_per_trade']:.2f}")
            print()
        
        # By confidence
        if perf['by_confidence']:
            print("By Confidence Level:")
            for bucket, stats in sorted(perf['by_confidence'].items(), reverse=True):
                emoji = "✅" if stats['win_rate'] >= 0.6 else "⚠️" if stats['win_rate'] >= 0.4 else "❌"
                print(f"  {emoji} {bucket}: {stats['trades']} trades, {stats['win_rate']:.1%} win rate, ${stats['avg_pnl_per_trade']:.2f} avg")
            print()
        
        # Recommendations
        if perf['recommendations']:
            print("🎯 Recommendations:")
            for rec in perf['recommendations']:
                if rec['severity'] == 'error':
                    emoji = "🚨"
                elif rec['severity'] == 'warning':
                    emoji = "⚠️"
                else:
                    emoji = "💡"
                
                print(f"  {emoji} {rec['issue']}")
                print(f"     {rec['detail']}")
                print(f"     → {rec['action']}")
            print()
    
    # Open positions health
    health = check_open_position_health()
    print(f"🔍 Open Positions Health")
    print(f"   Total open: {health['total_open']}")
    print(f"   With current prices: {health['positions_with_prices']}")
    print(f"   Total unrealized P&L: ${health['total_unrealized_pnl']:.2f}")
    
    if health['warnings']:
        print()
        print("   ⚠️  Warnings:")
        for warning in health['warnings']:
            print(f"      • {warning}")
    
    if health['concerning_positions']:
        print()
        print("   📉 Positions with large losses:")
        for pos in health['concerning_positions']:
            print(f"      • {pos['market']}: ${pos['unrealized_pnl']:.2f}")
    
    print()
    print("=" * 60)
    
    # Return summary for logging
    summary = f"Analyzed {perf['total_closed']} closed positions"
    if perf.get('recommendations'):
        summary += f", {len(perf['recommendations'])} recommendations"
    if health['warnings']:
        summary += f", {len(health['warnings'])} warnings"
    
    return summary

if __name__ == '__main__':
    summary = format_analysis_report()
    print(f"\n✅ {summary}")
