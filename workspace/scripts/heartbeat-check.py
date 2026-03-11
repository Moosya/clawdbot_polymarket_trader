#!/usr/bin/env python3
import sys
sys.path.insert(0, '/workspace/.local')
import pickle
from googleapiclient.discovery import build
import sqlite3
from datetime import datetime, timedelta
import json
import os

# Use correct database paths
TRADES_DB = '/home/clawdbot/polymarket_runtime/data/trades.db'
TRADING_DB = '/home/clawdbot/polymarket_runtime/data/trading.db'
STATE_FILE = 'memory/heartbeat-state.json'

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_state(state):
    os.makedirs('memory', exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def check_email():
    try:
        state = load_state()
        last_check = state.get('last_email_check', None)
        
        TOKEN_PATH = '/workspace/.credentials/gmail-token.pickle'
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
        service = build('gmail', 'v1', credentials=creds)
        
        current_time = int(datetime.now().timestamp())
        
        # If first check, use timestamp from 1 hour ago
        if last_check is None:
            last_check = current_time - 3600
        
        # Get ALL messages since last check (read or unread)
        query = f'after:{last_check}'
        results = service.users().messages().list(userId='me', q=query, maxResults=20).execute()
        all_new = results.get('messages', [])
        
        # Filter out my own sent messages
        important_new = []
        for msg_info in all_new:
            msg = service.users().messages().get(userId='me', id=msg_info['id']).execute()
            headers = msg['payload']['headers']
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            
            # Skip if it's from me
            if 'stiles.mesas_3r@icloud.com' in sender.lower() or 'moosya@me.com' in sender.lower() or 'dreis.assistant@gmail.com' in sender.lower():
                continue
            
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No subject')
            from_name = sender.split('<')[0].strip()
            
            # Flag family expense submissions
            if 'anton.bergners' in sender.lower() or 'alek.bergners' in sender.lower() or 'sasha.bergners' in sender.lower() or 'alina.bergners' in sender.lower():
                important_new.append(f"📊 {from_name}: {subject[:40]}")
            else:
                important_new.append(f"{from_name}: {subject[:40]}")
        
        # Update last check time
        state['last_email_check'] = current_time
        save_state(state)
        
        if important_new:
            return '⚠️', f'{len(important_new)} new: ' + '; '.join(important_new[:3])
        else:
            hours_ago = (current_time - last_check) / 3600
            if hours_ago < 2:
                mins = int(hours_ago * 60)
                return '✅', f'no new (checked {mins}min ago)'
            else:
                return '✅', f'no new (checked {int(hours_ago)}hr ago)'
                
    except Exception as e:
        return '❌', f'Error: {str(e)[:50]}'

def check_collector():
    try:
        import sys
        sys.path.insert(0, '/home/clawdbot/clawd/scripts')
        from market_filters import should_skip_market
        
        conn = sqlite3.connect(TRADES_DB)
        cur = conn.cursor()
        
        # Get count in last hour (non-filtered markets only)
        one_hour_ago = int((datetime.now() - timedelta(hours=1)).timestamp())
        cur.execute("SELECT timestamp, marketQuestion, marketSlug, sizeUsd FROM trades WHERE timestamp >= ? AND sizeUsd >= 2000", (one_hour_ago,))
        recent_trades = cur.fetchall()
        
        # Filter out sports/entertainment/weather
        tradeable_trades = [(t, q, s, size) for t, q, s, size in recent_trades if not should_skip_market(q, s)[0]]
        whale_count = len(tradeable_trades)
        whale_volume = sum(size for _, _, _, size in tradeable_trades)
        
        # Get most recent TRADEABLE trade (skip sports, entertainment, weather, etc.)
        cur.execute("SELECT timestamp, marketQuestion, marketSlug, eventSlug, sizeUsd FROM trades ORDER BY timestamp DESC LIMIT 100")
        all_recent = cur.fetchall()
        
        last_trade = None
        last_slug = None
        last_event_slug = None
        for ts, question, slug, event_slug, size in all_recent:
            should_skip, _ = should_skip_market(question, slug)
            if not should_skip:
                last_trade = (ts, question, size)
                last_slug = slug
                last_event_slug = event_slug or slug  # Fallback to marketSlug if eventSlug is null
                break
        
        # Fallback to absolute last trade if all recent are filtered
        if not last_trade:
            cur.execute("SELECT timestamp, marketQuestion, marketSlug, eventSlug, sizeUsd FROM trades ORDER BY timestamp DESC LIMIT 1")
            row = cur.fetchone()
            if row:
                last_trade = (row[0], row[1], row[4])
                last_slug = row[2]
                last_event_slug = row[3] or row[2]  # Fallback to marketSlug if eventSlug is null
        
        conn.close()
        
        if not last_trade:
            return '❌', 'No trades in DB'
        
        last_ts, last_question, last_size = last_trade
        age_minutes = (datetime.now().timestamp() - last_ts) / 60
        
        # Format market name (first 30 chars)
        market_name = last_question[:30] if last_question else 'Unknown'
        
        # Build URL using eventSlug (correct URL format)
        market_url = ""
        if last_event_slug:
            # Check for suspicious slug patterns (long number suffixes, multiple dashes)
            if len(last_event_slug) < 100 and last_event_slug.count('-') < 15:
                market_url = f"polymarket.com/event/{last_event_slug}"
        
        # Build informative message
        if age_minutes < 30:
            msg = f'{int(whale_count or 0)} whales/hr (${int(whale_volume or 0)/1000:.0f}k), last: {market_name} (${last_size/1000:.0f}k {age_minutes:.0f}m ago)'
            if market_url:
                msg += f' → {market_url}'
            return '✅', msg
        elif age_minutes < 60:
            return '⚠️', f'{age_minutes:.0f}m stale, {int(whale_count or 0)} whales/hr'
        else:
            return '❌', f'{age_minutes/60:.1f}hr stale - collector stopped?'
    except Exception as e:
        return '❌', f'Error: {str(e)[:50]}'

def check_signals():
    try:
        state = load_state()
        last_check = state.get('last_signals_check', int((datetime.now() - timedelta(hours=1)).timestamp()))
        current_time = int(datetime.now().timestamp())
        
        conn = sqlite3.connect(TRADING_DB)
        cur = conn.cursor()
        
        # Get signals since LAST heartbeat, excluding obvious expired markets
        # Handle both second and millisecond timestamp formats
        cur.execute("""
            SELECT COUNT(*), MAX(confidence) 
            FROM signals 
            WHERE (
                (timestamp < 10000000000 AND timestamp >= ?)
                OR (timestamp >= 10000000000 AND timestamp/1000 >= ?)
            )
            AND market_question NOT LIKE '%February%'
            AND market_question NOT LIKE '%Feb %'
            AND market_question NOT LIKE '%Feb. %'
        """, (last_check, last_check))
        new_count, max_conf = cur.fetchone()
        
        # Update last check time
        state['last_signals_check'] = current_time
        save_state(state)
        
        # Check for ACTIONABLE untapped signals (≥70%, not expired, no position)
        # Only count recent signals (last 7 days) to avoid stale expired markets
        week_ago = int((datetime.now() - timedelta(days=7)).timestamp())
        cur.execute("""
            SELECT COUNT(*) 
            FROM signals
            WHERE confidence >= 70
            AND position_opened = 0
            AND (
                (timestamp < 10000000000 AND timestamp >= ?)
                OR (timestamp >= 10000000000 AND timestamp/1000 >= ?)
            )
            AND market_question NOT LIKE '%February%'
            AND market_question NOT LIKE '%Feb %'
            AND market_question NOT LIKE '%2AM ET%'
            AND market_question NOT LIKE '%1PM ET%'
        """, (week_ago, week_ago))
        untapped = cur.fetchone()[0]
        
        conn.close()
        
        # Calculate time since last check
        minutes_since_last = (current_time - last_check) / 60
        check_window = f"last {int(minutes_since_last)}min" if minutes_since_last < 60 else f"last {int(minutes_since_last/60)}hr"
        
        # Determine status and message
        if new_count > 0:
            if untapped > 0:
                return '⚠️', f'{new_count} new ({check_window}, max {max_conf or 0}%), {untapped} actionable'
            else:
                return '✅', f'{new_count} new ({check_window}, max {max_conf or 0}%)'
        else:
            if untapped > 0:
                return '⚠️', f'0 new ({check_window}), {untapped} actionable'
            else:
                return '✅', f'0 new ({check_window})'
                
    except Exception as e:
        return '❌', f'Error: {str(e)[:50]}'

def check_system():
    try:
        import os
        import subprocess
        
        log = '/home/clawdbot/polymarket_runtime/logs/dashboard-out.log'
        
        if not os.path.exists(log) or os.path.getsize(log) == 0:
            return '⚠️', 'no logs found'
        
        # Get last 100 lines to analyze
        result = subprocess.run(['tail', '-100', log], capture_output=True, text=True, timeout=5)
        log_lines = result.stdout.split('\n')
        
        # Find latest scan number
        scan_num = None
        for line in reversed(log_lines):
            if 'scan #' in line.lower() or 'Running scan #' in line:
                try:
                    scan_num = line.split('#')[1].split()[0].rstrip('...')
                    break
                except:
                    pass
        
        # Count errors in last 100 lines
        error_count = sum(1 for line in log_lines if 'error' in line.lower() or 'failed' in line.lower())
        
        # Check for recent activity (last line timestamp)
        last_line = log_lines[-1] if log_lines[-1] else log_lines[-2]
        
        # Build status message
        scan_info = f"scan #{scan_num}" if scan_num else "running"
        error_info = f", {error_count} errors" if error_count > 0 else ""
        
        if error_count > 10:
            return '⚠️', f'{scan_info}, {error_count} errors in tail'
        else:
            return '✅', f'{scan_info}{error_info}'
            
    except Exception as e:
        return '❌', f'Error: {str(e)[:50]}'

# Run checks
email_status, email_detail = check_email()
collector_status, collector_detail = check_collector()
signals_status, signals_detail = check_signals()
system_status, system_detail = check_system()

# Format output
from datetime import datetime
import pytz
est = pytz.timezone('America/New_York')
now_est = datetime.now(est).strftime('%I:%M %p')

print(f"🦞 Heartbeat {now_est} EST: email {email_status}, collector {collector_status}, signals {signals_status}, system {system_status}")

# Always show details for informative monitoring
print(f"\nCollector: {collector_detail}")
print(f"Signals: {signals_detail}")
print(f"System: {system_detail}")

# Show warnings if needed with CONTEXT and ACTIONS
if email_status == '⚠️' and 'new:' in email_detail:
    print(f"Email: {email_detail}")
    print("  → Action: Check inbox and respond")

if collector_status == '⚠️':
    print("  ℹ️ Collector: Trade flow slowed (30-60min since last)")
    print("  → Action: Monitor - if persists >1hr, check dashboard logs")
elif collector_status == '❌':
    print("  🚨 Collector: No trades for >1 hour - may have stopped")
    print("  → Action: Check dashboard PM2 status and logs")
    
if '⚠️' in signals_status and 'untapped' in signals_detail:
    # Parse untapped count
    import re
    untapped_match = re.search(r'(\d+) untapped', signals_detail)
    untapped_count = int(untapped_match.group(1)) if untapped_match else 0
    
    if untapped_count > 10:
        print("  🚨 Auto-trader: High untapped count suggests processing stopped")
        print("  → Action: Check /tmp/auto-trader.log for errors")
    else:
        print(f"  ℹ️ {untapped_count} untapped (likely expired/filtered - correctly skipped)")
        print("  → Action: None needed")

if system_status == '⚠️':
    print("  ℹ️ System: Dashboard logs show minor issues or errors")
    print("  → Action: Review if errors increase")
elif system_status == '❌':
    print("  🚨 System: Dashboard not logging or stopped")
    print("  → Action: Check PM2 and restart dashboard")
