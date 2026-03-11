#!/usr/bin/env python3
"""
iCloud Storage Tracker & Nag Generator
Compare week-over-week usage, generate personalized messages
"""

import json
from datetime import datetime, timedelta

TRACKING_FILE = '/workspace/clawd/memory/icloud-storage-tracking.json'

def load_tracking():
    with open(TRACKING_FILE, 'r') as f:
        return json.load(f)

def save_tracking(data):
    with open(TRACKING_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def add_report(new_usage):
    """
    Add new weekly report and generate comparison
    
    new_usage format:
    {
      "date": "2026-03-03",
      "members": {
        "Sasha": 705.2,
        "Andrei": 628.0,
        ...
      }
    }
    """
    data = load_tracking()
    
    # Get previous report
    prev_report = data['reports'][-1]
    prev_members = prev_report['members']
    
    # Calculate total and changes
    new_members = new_usage['members']
    total_used = sum(new_members.values())
    percent_full = int((total_used / data['total_capacity_gb']) * 100)
    
    # Build new report
    new_report = {
        'date': new_usage['date'],
        'total_used_gb': int(total_used),
        'percent_full': percent_full,
        'members': new_members
    }
    
    data['reports'].append(new_report)
    data['last_report_date'] = new_usage['date']
    
    # Calculate next Monday
    report_date = datetime.strptime(new_usage['date'], '%Y-%m-%d')
    days_until_monday = (7 - report_date.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    next_reminder = report_date + timedelta(days=days_until_monday)
    data['next_reminder'] = next_reminder.strftime('%Y-%m-%d')
    
    save_tracking(data)
    
    # Generate messages
    messages = []
    
    # Overall status
    messages.append(f"📊 **iCloud Storage Update ({new_usage['date']})**")
    messages.append(f"Family: {total_used:.0f} GB / {data['total_capacity_gb']} GB ({percent_full}%)")
    messages.append("")
    
    # Per-person changes
    messages.append("**Week-over-week changes:**")
    
    for name in sorted(new_members.keys(), key=lambda n: new_members[n], reverse=True):
        current = new_members[name]
        previous = prev_members.get(name, 0)
        delta = current - previous
        
        if delta > 0:
            emoji = "📈" if delta > 10 else "⬆️"
            trend = f"+{delta:.1f} GB"
            color = "🔴"
        elif delta < 0:
            emoji = "📉"
            trend = f"{delta:.1f} GB"
            color = "🟢"
        else:
            emoji = "➡️"
            trend = "no change"
            color = "⚪"
        
        messages.append(f"{color} **{name}**: {current:.1f} GB ({trend}) {emoji}")
    
    messages.append("")
    messages.append("*(Send individual DMs with their status)*")
    
    return "\n".join(messages)

def generate_individual_message(name, current, delta):
    """Generate personalized message for each person"""
    
    if delta > 0:
        if delta > 50:
            tone = f"🚨 **{name}**, your iCloud usage jumped by {delta:.1f} GB this week! You're at {current:.1f} GB now. Family storage is critically full - please clean up photos/videos ASAP."
        elif delta > 10:
            tone = f"⚠️ **{name}**, you're up {delta:.1f} GB this week (now {current:.1f} GB). Family storage is almost full - time to delete old stuff."
        else:
            tone = f"📈 **{name}**, you went up {delta:.1f} GB this week (now {current:.1f} GB). Small increase but we're running out of space."
    elif delta < 0:
        tone = f"🎉 **{name}**, thanks for cleaning up! You freed {abs(delta):.1f} GB (now {current:.1f} GB). Appreciate it!"
    else:
        tone = f"➡️ **{name}**, your usage stayed flat at {current:.1f} GB this week."
    
    return tone

def should_remind_today():
    """Check if today is Monday and reminder is due"""
    data = load_tracking()
    today = datetime.now().strftime('%Y-%m-%d')
    next_reminder = data.get('next_reminder')
    
    is_monday = datetime.now().weekday() == 0
    is_due = today >= next_reminder if next_reminder else True
    
    return is_monday and is_due

if __name__ == '__main__':
    # Example: Add new report
    new_data = {
        'date': '2026-03-03',
        'members': {
            'Sasha': 705.2,
            'Andrei': 628.0,
            'Alina': 560.0,
            'Anton': 185.0,
            'Alek': 150.0,
            'Magdalena': 35.0
        }
    }
    
    print(add_report(new_data))
