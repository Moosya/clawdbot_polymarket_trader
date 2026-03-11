#!/usr/bin/env python3
"""
Active Position Monitoring with Hybrid Grok Strategy
- Mini model for triage (cheap surveillance)
- Reasoning model for critical exit decisions (when change detected)
"""

import sqlite3
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from grok_validator_mini import call_grok_mini
from grok_validator import call_grok

# Use environment variable or relative path for production compatibility
TRADING_DB = os.getenv('TRADING_DB_PATH', os.path.join(os.getcwd(), 'data', 'trading.db'))

def get_open_positions():
    """Get all open positions"""
    conn = sqlite3.connect(TRADING_DB)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, market_slug, market_question, outcome, direction, 
               entry_price, entry_time, notes
        FROM paper_positions
        WHERE status = 'open'
        ORDER BY entry_time DESC
    """)
    
    positions = []
    for row in cur.fetchall():
        pos_id, slug, question, outcome, direction, price, entry_time, notes = row
        positions.append({
            'id': pos_id,
            'slug': slug,
            'question': question,
            'outcome': outcome,
            'direction': direction,
            'price': price,
            'entry_time': entry_time,
            'notes': notes
        })
    
    conn.close()
    return positions

def triage_position(position):
    """Quick check with mini model: has anything changed?"""
    prompt = f"""Quick status check on this open trading position:

Market: {position['question']}
Our position: {position['direction']} {position['outcome']} @ ${position['price']:.2f}
Entry: {datetime.fromtimestamp(position['entry_time']/1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

Reply in ONE line:
STATUS: [NO_CHANGE / POSSIBLE_CHANGE / RESOLVED]
HEADLINE: [if changed, brief headline of what happened]"""

    response = call_grok_mini(prompt, temperature=0.1)
    if not response:
        return 'NO_CHANGE', None
    
    # Parse
    import re
    status_match = re.search(r'STATUS:\s*(\w+)', response, re.IGNORECASE)
    status = status_match.group(1).upper() if status_match else 'NO_CHANGE'
    
    needs_reasoning = status in ['POSSIBLE_CHANGE', 'RESOLVED', 'CHANGED']
    
    return status, response if needs_reasoning else None

def deep_analysis_with_reasoning(position):
    """Use reasoning model for critical exit decision"""
    prompt = f"""CRITICAL POSITION ANALYSIS - Use your reasoning capabilities.

Market: {position['question']}
Our Position: {position['direction']} {position['outcome']} @ ${position['price']:.2f}
Entry Time: {datetime.fromtimestamp(position['entry_time']/1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

Based on latest news from X/Twitter, provide a DETAILED analysis:

CURRENT_PROBABILITY: [0-100]%
KEY_DEVELOPMENTS: [what changed since entry]
MARKET_STATUS: [ACTIVE / RESOLVED / UNCLEAR]
REASONING: [detailed thought process]
RECOMMENDATION: [HOLD / EXIT / EXIT_NOW / ADD]
CONFIDENCE: [how certain are you?]

Think step-by-step about:
1. What new information emerged?
2. How does it affect the outcome probability?
3. Is the market resolved or about to resolve?
4. Should we exit to preserve capital or hold for upside?"""

    response = call_grok(prompt, temperature=0.2)
    if not response:
        return None
    
    # Parse
    import re
    prob_match = re.search(r'CURRENT_PROBABILITY:\s*(\d+)', response)
    rec_match = re.search(r'RECOMMENDATION:\s*(\w+)', response)
    status_match = re.search(r'MARKET_STATUS:\s*(\w+)', response)
    
    current_prob = float(prob_match.group(1)) if prob_match else None
    recommendation = rec_match.group(1).upper() if rec_match else "HOLD"
    market_status = status_match.group(1).upper() if status_match else "ACTIVE"
    
    return {
        'current_probability': current_prob,
        'recommendation': recommendation,
        'market_status': market_status,
        'full_response': response
    }

def main():
    print("🔍 Monitoring Open Positions (Hybrid Strategy)\n")
    
    positions = get_open_positions()
    if not positions:
        print("   No open positions to monitor")
        return
    
    print(f"   Found {len(positions)} open position(s)\n")
    
    alerts = []
    
    for pos in positions:
        print(f"📊 Position #{pos['id']}: {pos['direction']} {pos['outcome']}")
        print(f"   {pos['question'][:70]}...")
        
        # Step 1: Cheap triage with mini model
        status, triage_response = triage_position(pos)
        
        if status == 'NO_CHANGE':
            print(f"   ✓ No changes detected (mini model)\n")
            continue
        
        # Step 2: Detected change - use reasoning model for decision
        print(f"   ⚠️  Change detected: {status}")
        print(f"   🧠 Running deep analysis (reasoning model)...")
        
        result = deep_analysis_with_reasoning(pos)
        
        if not result:
            print("   ⚠️  Reasoning model unavailable\n")
            continue
        
        # Determine alert level
        if result['market_status'] == 'RESOLVED' or result['recommendation'] == 'EXIT_NOW':
            alerts.append({
                'position': pos,
                'action': 'EXIT_NOW',
                'reason': 'Market resolved or critical exit signal',
                'details': result['full_response'],
                'priority': 'URGENT'
            })
            print(f"   🚨 URGENT: {result['recommendation']}")
            
        elif result['recommendation'] == 'EXIT':
            alerts.append({
                'position': pos,
                'action': 'EXIT',
                'reason': 'Probability changed significantly',
                'details': result['full_response'],
                'priority': 'HIGH'
            })
            print(f"   ⚠️  Recommend EXIT")
            
        elif result['recommendation'] == 'ADD':
            alerts.append({
                'position': pos,
                'action': 'ADD',
                'reason': 'Confidence increased',
                'details': result['full_response'],
                'priority': 'MEDIUM'
            })
            print(f"   ✅ Consider ADDING to position")
        else:
            print(f"   ✓ HOLD (despite news)")
        
        if result['current_probability']:
            print(f"   Current probability: {result['current_probability']}%")
        
        print()
    
    # Output alerts
    if alerts:
        print("=" * 60)
        print("🚨 POSITION MANAGEMENT ALERTS:")
        print("=" * 60)
        for alert in alerts:
            pos = alert['position']
            print(f"\n[{alert['priority']}] Position #{pos['id']}: {alert['action']}")
            print(f"Market: {pos['question']}")
            print(f"Position: {pos['direction']} {pos['outcome']} @ ${pos['price']:.2f}")
            print(f"Reason: {alert['reason']}")
            print(f"\n🧠 Grok Reasoning Analysis:")
            print(alert['details'])
            print("-" * 60)

if __name__ == '__main__':
    main()
