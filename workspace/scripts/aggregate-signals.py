#!/usr/bin/env python3
"""
Unified Signal Aggregator
Runs all signal detectors and combines results
"""

import sys
import json
from datetime import datetime
import importlib.util

def load_module(filepath, module_name):
    """Load a Python file as a module"""
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load detectors
whale_detector = load_module('/workspace/scripts/detect-whale-clusters.py', 'whale_detector')
divergence_detector = load_module('/workspace/scripts/detect-smart-money-divergence.py', 'divergence_detector')
reversal_detector = load_module('/workspace/scripts/detect-momentum-reversal.py', 'reversal_detector')

def aggregate_all_signals():
    """Run all detectors and combine signals"""
    
    all_signals = {
        'timestamp': datetime.now().isoformat(),
        'whale_clusters': [],
        'smart_money_divergence': [],
        'momentum_reversals': [],
        'top_signals': []
    }
    
    print("🔍 Running all signal detectors...\n")
    
    # Whale Clustering
    print("1️⃣ Checking whale clusters...")
    try:
        whale_signals = whale_detector.detect_clusters(lookback_hours=2)
        all_signals['whale_clusters'] = whale_signals
        print(f"   ✅ Found {len(whale_signals)} whale cluster signal(s)")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Smart Money Divergence
    print("2️⃣ Checking smart money divergence...")
    try:
        divergence_signals = divergence_detector.detect_divergence(lookback_hours=4)
        all_signals['smart_money_divergence'] = divergence_signals
        print(f"   ✅ Found {len(divergence_signals)} divergence signal(s)")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Momentum Reversals
    print("3️⃣ Checking momentum reversals...")
    try:
        reversal_signals = reversal_detector.detect_reversals(lookback_hours=6)
        all_signals['momentum_reversals'] = reversal_signals
        print(f"   ✅ Found {len(reversal_signals)} reversal signal(s)")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Combine and rank all signals
    combined = []
    
    for sig in whale_signals:
        combined.append({
            'type': 'whale_cluster',
            'confidence': sig['confidence'],
            'market_slug': sig['market_slug'],
            'market_question': sig['market_question'],
            'signal': f"{sig['side']} {sig['outcome']}",
            'price': sig['avg_price'],
            'details': sig
        })
    
    for sig in divergence_signals:
        combined.append({
            'type': 'smart_money_divergence',
            'confidence': sig['confidence'],
            'market_slug': sig['market_slug'],
            'market_question': sig['market_question'],
            'signal': f"{sig['divergence']['signal']} {sig['outcome']}",
            'price': sig['divergence']['market_price'],
            'details': sig
        })
    
    for sig in reversal_signals:
        combined.append({
            'type': 'momentum_reversal',
            'confidence': sig['confidence'],
            'market_slug': sig['market_slug'],
            'market_question': sig['market_question'],
            'signal': f"{sig['reversal']['signal']} {sig['outcome']}",
            'price': sig['current_price'],
            'details': sig
        })
    
    # Sort by confidence
    combined.sort(key=lambda x: x['confidence'], reverse=True)
    all_signals['top_signals'] = combined[:10]  # Top 10
    
    # Save to file
    with open('/workspace/signals/aggregated-signals.json', 'w') as f:
        json.dump(all_signals, f, indent=2)
    
    return all_signals

def format_summary(signals):
    """Format signals for quick view"""
    output = "\n" + "="*60 + "\n"
    output += "🎯 TRADING SIGNALS SUMMARY\n"
    output += "="*60 + "\n\n"
    
    total = len(signals['whale_clusters']) + len(signals['smart_money_divergence']) + len(signals['momentum_reversals'])
    
    if total == 0:
        output += "❌ No high-confidence signals detected\n"
        return output
    
    output += f"📊 Total Signals: {total}\n"
    output += f"   • Whale Clusters: {len(signals['whale_clusters'])}\n"
    output += f"   • Smart Money Divergence: {len(signals['smart_money_divergence'])}\n"
    output += f"   • Momentum Reversals: {len(signals['momentum_reversals'])}\n\n"
    
    if signals['top_signals']:
        output += "🔥 TOP SIGNALS:\n\n"
        for i, sig in enumerate(signals['top_signals'][:5], 1):
            emoji = "🔥" if sig['confidence'] >= 85 else "⚡" if sig['confidence'] >= 70 else "📊"
            output += f"{emoji} #{i} - {sig['type'].replace('_', ' ').title()} ({sig['confidence']}%)\n"
            output += f"   Market: {sig['market_question'][:65]}...\n"
            output += f"   Signal: {sig['signal']} @ {sig['price']:.2f}\n"
            output += f"   🔗 polymarket.com/{sig['market_slug']}\n\n"
    
    return output

if __name__ == "__main__":
    signals = aggregate_all_signals()
    print(format_summary(signals))
    print(f"💾 Saved full results to /workspace/signals/aggregated-signals.json")
