#!/usr/bin/env python3
"""
Auto-Trading Engine
Reads signals, opens paper positions automatically for confidence ≥70%
Alerts on Telegram for confidence ≥80%
"""

import json
import sqlite3
import requests
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from market_filters import should_skip_market


# Load environment variables from .env file
def load_env_file(env_path='/workspace/.env'):
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env_file()

# Configuration
SIGNALS_FILE = '/workspace/signals/aggregated-signals.json'
TRADING_DB = '/workspace/polymarket_runtime/data/trading.db'  # Shared with dashboard
POSITION_SIZE = 50  # $50 per trade (5% of $1000 portfolio)
AUTO_TRADE_THRESHOLD = 70  # Auto-trade on ≥70% confidence
ALERT_THRESHOLD = 80  # Alert on Telegram for ≥80%
MISSION_CONTROL_API = 'http://localhost:3001/api/activities'

def translate_to_polymarket_action(signal_action, outcome):
    """
    Translate detector signal into Polymarket action.
    Polymarket doesn't support shorting - you can only BUY Yes or BUY No.
    To bet against an outcome, you BUY the opposite outcome.
    """
    if signal_action == 'BUY':
        return ('BUY', outcome)
    elif signal_action == 'SELL':
        # Bet against this outcome = BUY the opposite
        opposite = 'Yes' if outcome == 'No' else 'No'
        return ('BUY', opposite)
    else:
        return ('BUY', outcome)  # Default to BUY


def load_signals():
    """Load aggregated signals from file"""
    if not Path(SIGNALS_FILE).exists():
        return {'top_signals': []}
    
    with open(SIGNALS_FILE, 'r') as f:
        return json.load(f)

def get_db():
    """Get database connection"""
    return sqlite3.connect(TRADING_DB)

def check_market_timing(event_slug):
    """Check if market is in valid time window (7 days to 6 months)"""
    try:
        response = requests.get(f"https://gamma-api.polymarket.com/events?slug={event_slug}", timeout=5)
        if response.status_code == 200:
            events = response.json()
            if events and len(events) > 0:
                end_date = events[0].get('endDate')
                if end_date:
                    end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    now = datetime.now(timezone.utc)
                    days_until = (end_dt - now).days
                    
                    if days_until < 0:
                        print(f"   ⏭️  Market already closed {abs(days_until)} days ago")
                        return False, days_until
                    elif days_until < 7:
                        print(f"   ⏭️  Market closes in {days_until} days (too soon - high volatility)")
                        return False, days_until
                    elif days_until > 180:
                        print(f"   ⏭️  Market closes in {days_until} days (too far - capital locked up)")
                        return False, days_until
                    
                    return True, days_until
        
        # If we can't get timing info, allow but warn
        print(f"   ⚠️  Could not fetch market timing")
        return True, None
        
    except Exception as e:
        print(f"   ⚠️  Market timing check error: {e}")
        return True, None

def validate_market(market_slug):
    """Verify market exists on Polymarket before trading"""
    try:
        url = f"https://polymarket.com/event/{market_slug}"
        response = requests.head(url, timeout=5, allow_redirects=True)
        
        # Check if market page exists (200 OK)
        if response.status_code == 200:
            return True
        
        # 404 = market doesn't exist or was delisted
        if response.status_code == 404:
            print(f"   ⚠️  Market validation failed: 404 Not Found")
            return False
        
        # Other errors - assume valid but log
        print(f"   ⚠️  Market validation returned {response.status_code}")
        return True  # Allow trade but log warning
        
    except Exception as e:
        print(f"   ⚠️  Market validation error: {e}")
        return True  # Don't block on validation errors

def has_open_position(market_slug, outcome):
    """Check if we already have an open position on this market/outcome"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT COUNT(*) FROM paper_positions
        WHERE market_slug = ? AND outcome = ? AND status = 'open'
    """, (market_slug, outcome))
    
    count = cur.fetchone()[0]
    conn.close()
    
    return count > 0

def store_signal(signal_type, confidence, market_slug, market_question, 
                outcome, direction, price, details):
    """Store signal in database"""
    conn = get_db()
    cur = conn.cursor()
    
    timestamp = int(datetime.now().timestamp() * 1000)
    
    cur.execute("""
        INSERT INTO signals 
        (type, confidence, market_slug, market_question, outcome, direction, price, details, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (signal_type, confidence, market_slug, market_question, outcome, direction, price, 
          json.dumps(details), timestamp))
    
    signal_id = cur.lastrowid
    conn.commit()
    conn.close()
    
    return signal_id

def open_position(signal_id, signal_type, confidence, market_slug, market_question,
                 outcome, direction, price, reasoning, event_slug=None):
    """Open a paper trading position"""
    conn = get_db()
    cur = conn.cursor()
    
    entry_time = int(datetime.now().timestamp() * 1000)
    
    # Build notes object with reasoning
    notes_obj = {'reasoning': reasoning}
    
    # Add event info if available
    if event_slug:
        notes_obj['event_slug'] = event_slug
        notes_obj['event_url'] = f"https://polymarket.com/event/{event_slug}"
        
        # Try to get timing info
        try:
            response = requests.get(f"https://gamma-api.polymarket.com/events?slug={event_slug}", timeout=3)
            if response.status_code == 200:
                events = response.json()
                if events and len(events) > 0:
                    event = events[0]
                    notes_obj['end_date'] = event.get('endDate')
                    notes_obj['full_title'] = event.get('title')
                    
                    # Calculate days until close
                    if event.get('endDate'):
                        end_dt = datetime.fromisoformat(event['endDate'].replace('Z', '+00:00'))
                        days_until = (end_dt - datetime.now(timezone.utc)).days
                        notes_obj['days_until_close'] = days_until
        except:
            pass  # Don't block on metadata fetch failure
    
    cur.execute("""
        INSERT INTO paper_positions
        (signal_id, market_slug, market_question, outcome, direction, 
         entry_price, entry_time, size, confidence, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
    """, (signal_id, market_slug, market_question, outcome, direction,
          price, entry_time, POSITION_SIZE, confidence, json.dumps(notes_obj)))
    
    position_id = cur.lastrowid
    
    # Mark signal as traded
    cur.execute("UPDATE signals SET position_opened = 1 WHERE id = ?", (signal_id,))
    
    conn.commit()
    conn.close()
    
    return position_id

def log_to_mission_control(action, details, status='success'):
    """Post activity to Mission Control"""
    try:
        requests.post(MISSION_CONTROL_API, json={
            'type': 'trading',
            'action': action,
            'details': json.dumps(details),
            'status': status
        }, timeout=5)
    except Exception as e:
        print(f"⚠️  Failed to log to Mission Control: {e}")

def format_reasoning(signal):
    """Generate human-readable trading reasoning"""
    signal_type = signal['type']
    conf = signal['confidence']
    details = signal.get('details', {})
    
    if signal_type == 'whale_cluster':
        whale_count = details.get('whale_count', 0)
        total_size = details.get('total_size', 0)
        time_span = details.get('time_span_minutes', 0)
        return f"{conf}% confidence: {whale_count} whales, ${total_size:,.0f} in {time_span:.0f} min"
    
    elif signal_type == 'smart_money_divergence':
        divergence = details.get('divergence', {})
        whale_size = divergence.get('whale_size', 0)
        return f"{conf}% confidence: Whales betting ${whale_size:,.0f} against crowd sentiment"
    
    elif signal_type == 'momentum_reversal':
        reversal = details.get('reversal', {})
        price_move = reversal.get('price_move', 0)
        whale_size = reversal.get('whale_size', 0)
        return f"{conf}% confidence: Price moved {price_move*100:.1f}%, whales counter-positioned ${whale_size:,.0f}"
    
    return f"{conf}% confidence signal"

def process_signal(signal):
    """Process a single signal - store, trade if needed, alert if needed"""
    signal_type = signal['type']
    confidence = signal['confidence']
    market_slug = signal['market_slug']
    market_question = signal['market_question']
    # Parse signal and translate to Polymarket action (BUY only)
    signal_parts = signal['signal'].split()
    raw_action = signal_parts[0]  # BUY or SELL from detector
    raw_outcome = ' '.join(signal_parts[1:])  # Rest is outcome
    direction, outcome = translate_to_polymarket_action(raw_action, raw_outcome)
    price = signal['price']
    details = signal.get('details', {})
    
    # Filter out unwanted markets (past years, high-frequency, sports)
    should_skip, skip_reason = should_skip_market(market_question, market_slug)
    if should_skip:
        print(f"⏭️  Skipping {market_slug} - {skip_reason}")
        return None
    
    # Filter out high-frequency markets (too fast for ~30min heartbeat)
    # These markets expire before we can react effectively
    high_freq_patterns = [
        # Time-based patterns (any asset)
        '15 min',
        '15min',
        '5 min',
        '5min',
        '10 min',
        '10min',
        '1 hour',
        '1hr',
        '1h',
        '30 min',
        '30min',
        '2 hour',
        '2hr',
        '2h',
        # Generic short-term patterns
        'up or down',  # Hourly directional bets
        'higher or lower',
        'updown',
        # Specific slugs
        'btc-updown',
        'eth-updown',
    ]
    
    # Filter out sports markets (no information asymmetry/whale edge)
    # Focus on markets where insider knowledge provides advantage
    sports_patterns = [
        'nba',
        'nfl', 
        'nhl',
        'mlb',
        'premier league',
        'champions league',
        'world cup',
        'soccer',
        'football',
        'basketball',
        'baseball',
        'hockey',
        'vs.',  # Common in sports matchups
        'spread:',  # Sports betting spreads
    ]
    
    question_lower = market_question.lower()
    slug_lower = market_slug.lower()
    
    if any(pattern in slug_lower or pattern in question_lower for pattern in high_freq_patterns):
        print(f"⏭️  Skipping {market_slug} - High-frequency market (too fast for our ~30min cycle)")
        return None
    
    if any(pattern in slug_lower or pattern in question_lower for pattern in sports_patterns):
        print(f"⏭️  Skipping {market_slug} - Sports market (no information edge)")
        return None
    
    # Check if we already have a position
    if has_open_position(market_slug, outcome):
        print(f"⏭️  Skipping {market_slug} - already have open position")
        return None
    
    # Store signal
    signal_id = store_signal(signal_type, confidence, market_slug, market_question,
                            outcome, direction, price, details)
    
    print(f"📊 Signal stored: {signal_type} {confidence}% - {market_question}")
    
    # Auto-trade if confidence ≥70%
    if confidence >= AUTO_TRADE_THRESHOLD:
        # Validate market exists before opening position
        if not validate_market(market_slug):
            print(f"   ⏭️  Skipping position - Market does not exist or is delisted")
            return None
        
        # GROK VALIDATION: Check news context before trading
        from grok_validator import validate_signal_with_grok
        grok_result = validate_signal_with_grok(market_question, market_slug, confidence, outcome)
        
        if not grok_result['should_trade']:
            print(f"   🛑 Grok validation failed: {grok_result['reasoning']}")
            if grok_result['grok_available']:
                print(f"      Full assessment: {grok_result['full_response'][:200]}...")
            return None
        
        # Update reasoning with Grok insights
        reasoning = format_reasoning(signal)
        if grok_result['grok_available']:
            reasoning = f"{reasoning} | Grok: {grok_result['reasoning']}"
        position_id = open_position(signal_id, signal_type, confidence, market_slug,
                                    market_question, outcome, direction, price, reasoning)
        
        print(f"   ✅ Opened position #{position_id}: {direction} {outcome} @ ${price:.2f}")
        print(f"      Reasoning: {reasoning}")
        
        # Log to Mission Control with market context
        # Truncate long market names for readability
        market_short = market_question[:60] + "..." if len(market_question) > 60 else market_question
        log_to_mission_control(
            f"Opened position: {direction} {outcome} @ ${price:.2f} (${POSITION_SIZE}) - {market_short}",
            {
                'position_id': position_id,
                'signal_type': signal_type,
                'confidence': confidence,
                'market': market_question,
                'size': POSITION_SIZE,
                'reasoning': reasoning
            }
        )
        
        # Return for potential alert
        return {
            'position_id': position_id,
            'confidence': confidence,
            'signal_type': signal_type,
            'market_slug': market_slug,
            'market_question': market_question,
            'direction': direction,
            'outcome': outcome,
            'price': price,
            'reasoning': reasoning
        }
    
    return None

def run():
    """Main auto-trading loop"""
    print("🤖 Auto-Trader Running...")
    print(f"   Position size: ${POSITION_SIZE}")
    print(f"   Auto-trade threshold: ≥{AUTO_TRADE_THRESHOLD}%")
    print(f"   Alert threshold: ≥{ALERT_THRESHOLD}%")
    print()
    
    # Load signals
    data = load_signals()
    signals = data.get('top_signals', [])
    
    if not signals:
        print("   No signals detected")
        return []
    
    print(f"   Processing {len(signals)} signals...")
    print()
    
    # Process each signal
    alerts = []
    for signal in signals:
        result = process_signal(signal)
        if result and result['confidence'] >= ALERT_THRESHOLD:
            alerts.append(result)
    
    print()
    print(f"✅ Auto-trader complete: {len(alerts)} high-confidence positions opened")
    
    return alerts

if __name__ == '__main__':
    alerts = run()
    
    # Output alerts for heartbeat to detect
    if alerts:
        print()
        print("🚨 HIGH CONFIDENCE ALERTS:")
        for alert in alerts:
            print(f"   {alert['confidence']}% {alert['signal_type']}: {alert['direction']} {alert['outcome']}")
            print(f"   {alert['market_question']}")
            print(f"   {alert['reasoning']}")
            print(f"   https://polymarket.com/event/{alert['market_slug']}")
            print()
