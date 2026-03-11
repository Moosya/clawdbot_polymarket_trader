#!/usr/bin/env python3
"""
Weekly Calibration Review
Runs every Monday, analyzes signal performance, suggests adjustments
"""

import sys
sys.path.insert(0, '/workspace/.local')

import sqlite3
import json
from datetime import datetime, timedelta
from collections import defaultdict

TRADING_DB = '/home/clawdbot/polymarket_runtime/data/trading.db'

def calculate_brier_score(forecast_prob, actual_outcome):
    """Brier score: (forecast - actual)^2"""
    return (forecast_prob - actual_outcome) ** 2

def get_calibration_data():
    """Get all closed positions with outcomes"""
    conn = sqlite3.connect(TRADING_DB)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            s.type as signal_type,
            s.confidence,
            p.pnl,
            p.market_question,
            p.exit_time
        FROM paper_positions p
        JOIN signals s ON p.signal_id = s.id
        WHERE p.status = 'closed'
        ORDER BY p.exit_time DESC
    """)
    
    results = cur.fetchall()
    conn.close()
    
    forecasts = []
    for signal_type, confidence, pnl, market, exit_time in results:
        forecast_prob = confidence / 100.0
        actual_outcome = 1 if pnl > 0 else 0
        brier = calculate_brier_score(forecast_prob, actual_outcome)
        
        forecasts.append({
            'signal_type': signal_type,
            'confidence': confidence,
            'forecast_prob': forecast_prob,
            'actual_outcome': actual_outcome,
            'brier_score': brier,
            'won': pnl > 0,
            'pnl': pnl
        })
    
    return forecasts

def analyze_by_signal_type(forecasts):
    """Break down performance by signal type"""
    by_type = defaultdict(list)
    for f in forecasts:
        by_type[f['signal_type']].append(f)
    
    results = {}
    for signal_type, type_forecasts in by_type.items():
        total = len(type_forecasts)
        wins = sum(1 for f in type_forecasts if f['won'])
        win_rate = wins / total if total > 0 else 0
        avg_confidence = sum(f['confidence'] for f in type_forecasts) / total if total > 0 else 0
        avg_brier = sum(f['brier_score'] for f in type_forecasts) / total if total > 0 else 0
        
        # Calibration gap
        gap = avg_confidence - (win_rate * 100)
        
        results[signal_type] = {
            'total': total,
            'wins': wins,
            'losses': total - wins,
            'win_rate': win_rate,
            'avg_confidence': avg_confidence,
            'calibration_gap': gap,
            'avg_brier': avg_brier,
            'overconfident': gap > 10
        }
    
    return results

def generate_recommendations(analysis):
    """Suggest confidence adjustments"""
    recommendations = []
    
    for signal_type, stats in analysis.items():
        if stats['total'] < 5:
            continue
        
        if stats['overconfident']:
            adjustment = -int(stats['calibration_gap'])
            recommendations.append({
                'signal_type': signal_type,
                'issue': f"Overconfident by {stats['calibration_gap']:.1f}pp",
                'current_avg': f"{stats['avg_confidence']:.1f}%",
                'actual_win_rate': f"{stats['win_rate']*100:.1f}%",
                'recommendation': f"Reduce confidence by {adjustment}pp",
                'adjustment': adjustment
            })
        elif stats['calibration_gap'] < -10:
            adjustment = int(abs(stats['calibration_gap']))
            recommendations.append({
                'signal_type': signal_type,
                'issue': f"Underconfident by {abs(stats['calibration_gap']):.1f}pp",
                'current_avg': f"{stats['avg_confidence']:.1f}%",
                'actual_win_rate': f"{stats['win_rate']*100:.1f}%",
                'recommendation': f"Increase confidence by {adjustment}pp",
                'adjustment': adjustment
            })
    
    return recommendations

def format_email_report(forecasts, analysis, recommendations):
    """Generate email-friendly report"""
    total = len(forecasts)
    wins = sum(1 for f in forecasts if f['won'])
    win_rate = wins / total if total > 0 else 0
    avg_brier = sum(f['brier_score'] for f in forecasts) / total if total > 0 else 0
    
    grade = '🌟 SUPERFORECASTER' if avg_brier < 0.10 else '⭐ GOOD' if avg_brier < 0.15 else '⚠️ NEEDS IMPROVEMENT'
    
    report = f"""Weekly Calibration Review - {datetime.now().strftime('%Y-%m-%d')}

OVERALL PERFORMANCE
Total: {total} positions | Win Rate: {win_rate*100:.1f}% | Brier: {avg_brier:.3f} {grade}

SIGNAL TYPE BREAKDOWN
"""
    
    for signal_type, stats in sorted(analysis.items(), key=lambda x: x[1]['avg_brier']):
        status = '✅' if not stats['overconfident'] else '⚠️'
        report += f"""
{status} {signal_type}: {stats['total']} trades, {stats['win_rate']*100:.1f}% win rate
   Predicted: {stats['avg_confidence']:.1f}% | Gap: {stats['calibration_gap']:+.1f}pp | Brier: {stats['avg_brier']:.3f}
"""
    
    if recommendations:
        report += "\nRECOMMENDED ADJUSTMENTS\n"
        for rec in recommendations:
            report += f"🔧 {rec['signal_type']}: {rec['recommendation']}\n"
    else:
        report += "\n✅ All signals well-calibrated!\n"
    
    return report

def main():
    forecasts = get_calibration_data()
    
    if len(forecasts) < 5:
        print(f"Not enough data ({len(forecasts)} positions)")
        return
    
    analysis = analyze_by_signal_type(forecasts)
    recommendations = generate_recommendations(analysis)
    report = format_email_report(forecasts, analysis, recommendations)
    
    print(report)
    
    # Save recommendations to file for auto-adjustment
    if recommendations:
        with open('/workspace/memory/calibration-adjustments.json', 'w') as f:
            json.dump(recommendations, f, indent=2)
        print("\n💾 Saved adjustments to memory/calibration-adjustments.json")

if __name__ == '__main__':
    main()
