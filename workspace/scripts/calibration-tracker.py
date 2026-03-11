#!/usr/bin/env python3
"""
Calibration & Superforecaster Tracking
Measures whether our confidence predictions match actual outcomes
Uses Brier scores and calibration curves like Philip Tetlock's superforecasters
"""

import sqlite3
import json
from datetime import datetime
from collections import defaultdict
import math

TRADING_DB = '/home/clawdbot/polymarket_runtime/data/trading.db'

def calculate_brier_score(forecast_prob, actual_outcome):
    """
    Calculate Brier score for a single forecast
    forecast_prob: 0.0-1.0 (e.g., 0.75 for 75% confidence)
    actual_outcome: 1 if correct, 0 if wrong
    Lower scores are better (0 = perfect, 2 = worst possible)
    """
    return (forecast_prob - actual_outcome) ** 2

def get_calibration_data():
    """Extract all closed positions with their outcomes"""
    conn = sqlite3.connect(TRADING_DB)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            s.id as signal_id,
            s.type as signal_type,
            s.confidence,
            s.market_slug,
            s.created_at,
            p.pnl,
            p.roi,
            p.entry_time,
            p.exit_time,
            p.close_reason,
            p.market_question
        FROM paper_positions p
        JOIN signals s ON p.signal_id = s.id
        WHERE p.status = 'closed'
        ORDER BY p.exit_time DESC
    """)
    
    results = cur.fetchall()
    conn.close()
    
    forecasts = []
    for row in results:
        signal_id, signal_type, confidence, market_slug, created_at, pnl, roi, entry_time, exit_time, close_reason, market_question = row
        
        # Convert confidence to probability (70% = 0.70)
        forecast_prob = confidence / 100.0
        
        # Determine actual outcome (1 if won, 0 if lost)
        actual_outcome = 1 if pnl > 0 else 0
        
        # Calculate Brier score for this forecast
        brier = calculate_brier_score(forecast_prob, actual_outcome)
        
        forecasts.append({
            'signal_id': signal_id,
            'signal_type': signal_type,
            'confidence': confidence,
            'forecast_prob': forecast_prob,
            'actual_outcome': actual_outcome,
            'pnl': pnl,
            'roi': roi,
            'brier_score': brier,
            'market': market_question,
            'exit_time': exit_time
        })
    
    return forecasts

def analyze_calibration(forecasts):
    """
    Analyze whether our confidence levels are well-calibrated
    E.g., do 75% confidence trades actually win 75% of the time?
    """
    if not forecasts:
        return None
    
    # Group by confidence bucket
    buckets = defaultdict(lambda: {'correct': 0, 'total': 0, 'brier_scores': []})
    
    for f in forecasts:
        # Round to nearest 5% for buckets (70, 75, 80, 85, 90, 95, 100)
        bucket = round(f['confidence'] / 5) * 5
        
        buckets[bucket]['total'] += 1
        buckets[bucket]['correct'] += f['actual_outcome']
        buckets[bucket]['brier_scores'].append(f['brier_score'])
    
    calibration = {}
    for conf, data in sorted(buckets.items()):
        actual_win_rate = data['correct'] / data['total']
        predicted_win_rate = conf / 100.0
        calibration_error = abs(actual_win_rate - predicted_win_rate)
        avg_brier = sum(data['brier_scores']) / len(data['brier_scores'])
        
        calibration[conf] = {
            'trades': data['total'],
            'predicted_win_rate': predicted_win_rate,
            'actual_win_rate': actual_win_rate,
            'calibration_error': calibration_error,
            'avg_brier_score': avg_brier,
            'well_calibrated': calibration_error < 0.10  # Within 10 percentage points
        }
    
    return calibration

def calculate_overall_brier_score(forecasts):
    """Calculate mean Brier score across all forecasts"""
    if not forecasts:
        return None
    
    total_brier = sum(f['brier_score'] for f in forecasts)
    return total_brier / len(forecasts)

def tetlock_superforecaster_grade(avg_brier):
    """
    Grade forecasting ability using rough Tetlock benchmarks
    Brier scores from his research:
    - Random guessing: ~0.25
    - Average person: ~0.20
    - Good forecaster: ~0.15
    - Superforecaster: <0.10
    """
    if avg_brier is None:
        return "N/A - Need more data"
    elif avg_brier < 0.10:
        return "🏆 SUPERFORECASTER"
    elif avg_brier < 0.15:
        return "⭐ GOOD"
    elif avg_brier < 0.20:
        return "📊 AVERAGE"
    elif avg_brier < 0.25:
        return "⚠️  BELOW AVERAGE"
    else:
        return "❌ WORSE THAN RANDOM"

def identify_overconfidence_patterns(forecasts):
    """Find patterns where we're consistently overconfident"""
    issues = []
    
    # Group by signal type
    by_type = defaultdict(lambda: {'forecasts': [], 'overconfident_count': 0})
    
    for f in forecasts:
        by_type[f['signal_type']]['forecasts'].append(f)
        
        # Check if this was an overconfident prediction
        # (High confidence but lost money)
        if f['confidence'] >= 80 and f['actual_outcome'] == 0:
            by_type[f['signal_type']]['overconfident_count'] += 1
    
    # Analyze each signal type
    for sig_type, data in by_type.items():
        if len(data['forecasts']) < 3:
            continue  # Need more data
        
        avg_confidence = sum(f['confidence'] for f in data['forecasts']) / len(data['forecasts'])
        actual_win_rate = sum(f['actual_outcome'] for f in data['forecasts']) / len(data['forecasts'])
        
        overconfidence_ratio = data['overconfident_count'] / len(data['forecasts'])
        
        if avg_confidence > actual_win_rate * 100 + 15:  # More than 15pp overconfident
            issues.append({
                'signal_type': sig_type,
                'issue': 'overconfidence',
                'avg_confidence': avg_confidence,
                'actual_win_rate': actual_win_rate * 100,
                'gap': avg_confidence - (actual_win_rate * 100),
                'trades': len(data['forecasts']),
                'recommendation': f'Lower confidence threshold for {sig_type} by ~{int(avg_confidence - actual_win_rate * 100)}pp'
            })
    
    return issues

def format_calibration_report():
    """Generate calibration report with Tetlock-style metrics"""
    print("\n🎯 CALIBRATION & SUPERFORECASTER ANALYSIS")
    print("=" * 70)
    print()
    
    forecasts = get_calibration_data()
    
    if not forecasts:
        print("⚠️  No closed positions yet - need data to measure calibration")
        print("\n📚 Superforecasting Principles to Apply:")
        print("   • Think in granular probabilities (not just high/medium/low)")
        print("   • Update forecasts as new information emerges")
        print("   • Use base rates (outside view) before specifics (inside view)")
        print("   • Track your track record to identify biases")
        print("   • Avoid narrative fallacy - don't let stories override data")
        print("=" * 70)
        return "No data yet for calibration analysis"
    
    # Overall Brier score
    avg_brier = calculate_overall_brier_score(forecasts)
    grade = tetlock_superforecaster_grade(avg_brier)
    
    print(f"📊 Overall Performance ({len(forecasts)} resolved forecasts)")
    print(f"   Brier Score: {avg_brier:.4f}")
    print(f"   Grade: {grade}")
    print()
    
    # Brier score interpretation
    if avg_brier < 0.15:
        print("   💡 Strong forecasting! Predictions are well-calibrated.")
    elif avg_brier < 0.25:
        print("   💡 Room for improvement. Focus on calibration and updating.")
    else:
        print("   ⚠️  Predictions are poorly calibrated. Review confidence logic.")
    print()
    
    # Calibration by confidence level
    calibration = analyze_calibration(forecasts)
    
    print("🎯 Calibration by Confidence Level")
    print("   (Are 75% confidence trades winning 75% of the time?)")
    print()
    
    for conf, data in sorted(calibration.items()):
        status = "✅" if data['well_calibrated'] else "⚠️"
        predicted = data['predicted_win_rate'] * 100
        actual = data['actual_win_rate'] * 100
        error = data['calibration_error'] * 100
        
        print(f"   {status} {conf}% confidence ({data['trades']} trades)")
        print(f"      Predicted: {predicted:.1f}% | Actual: {actual:.1f}% | Error: {error:.1f}pp")
        print(f"      Avg Brier: {data['avg_brier_score']:.4f}")
        
        if not data['well_calibrated']:
            if actual < predicted:
                print(f"      → OVERCONFIDENT: Lower threshold or improve signal")
            else:
                print(f"      → UNDERCONFIDENT: Can raise threshold")
        print()
    
    # Overconfidence patterns
    issues = identify_overconfidence_patterns(forecasts)
    
    if issues:
        print("⚠️  Overconfidence Patterns Detected:")
        print()
        for issue in issues:
            print(f"   • {issue['signal_type']}")
            print(f"     Predicting {issue['avg_confidence']:.1f}% but winning {issue['actual_win_rate']:.1f}%")
            print(f"     Gap: {issue['gap']:.1f} percentage points ({issue['trades']} trades)")
            print(f"     → {issue['recommendation']}")
            print()
    
    # Tetlock principles reminder
    print("📚 Superforecaster Checklist:")
    print("   ✓ Track calibration regularly (weekly)")
    print("   ✓ Update forecasts as new info emerges (we do this with price updates)")
    print("   ✓ Think in precise probabilities (use 1% increments when possible)")
    print("   ✓ Start with base rates, then adjust for specifics")
    print("   ✓ Post-mortem each outcome - what did we miss?")
    print("   ✓ Combine multiple independent signals (ensemble thinking)")
    print("   ✓ Avoid narrative fallacy - patterns != proof")
    print()
    print("=" * 70)
    
    return f"Analyzed {len(forecasts)} forecasts, Brier={avg_brier:.4f}, Grade={grade}"

if __name__ == '__main__':
    summary = format_calibration_report()
    print(f"\n✅ {summary}")
