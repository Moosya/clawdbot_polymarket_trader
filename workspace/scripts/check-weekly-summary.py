#!/usr/bin/env python3
"""
Weekly Summary Heartbeat Check
Called by heartbeat to check if Monday and send weekly Polymarket summary
"""

import os
import json
from datetime import datetime
import subprocess

STATE_FILE = '/workspace/memory/heartbeat-state.json'


def load_state():
    """Load heartbeat state"""
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, 'r') as f:
        return json.load(f)


def save_state(state):
    """Save heartbeat state"""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def is_monday():
    """Check if today is Monday"""
    return datetime.now().weekday() == 0  # 0 = Monday


def already_sent_this_week():
    """Check if weekly summary already sent this week"""
    state = load_state()
    last_sent = state.get('last_weekly_summary')
    
    if not last_sent:
        return False
    
    # Check if last_sent is this week
    last_sent_date = datetime.fromisoformat(last_sent)
    today = datetime.now()
    
    # If last sent was this week (same Monday or later), skip
    # Get start of this week (Monday 00:00)
    days_since_monday = today.weekday()
    week_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = week_start.replace(day=week_start.day - days_since_monday)
    
    return last_sent_date >= week_start


def send_weekly_summary():
    """Run the weekly summary script"""
    try:
        result = subprocess.run(
            ['python3', '/workspace/scripts/weekly-polymarket-summary.py'],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            # Mark as sent
            state = load_state()
            state['last_weekly_summary'] = datetime.now().isoformat()
            save_state(state)
            
            print("✅ Weekly Polymarket summary sent")
            return True
        else:
            print(f"❌ Weekly summary failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending weekly summary: {e}")
        return False


if __name__ == '__main__':
    # Check if it's Monday
    if not is_monday():
        print("Not Monday - skipping weekly summary")
        exit(0)
    
    # Check if already sent this week
    if already_sent_this_week():
        print("Weekly summary already sent this week")
        exit(0)
    
    # Send the summary
    print("📊 Sending weekly Polymarket summary...")
    success = send_weekly_summary()
    exit(0 if success else 1)
