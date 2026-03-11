#!/usr/bin/env python3
"""
Send Family Expense Report Reminder
Called by heartbeat or cron on 1st and 15th of each month
"""

import sys
import os
sys.path.insert(0, '/workspace/.local')

import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import pickle
from datetime import datetime
import json

# Family emails
FAMILY_EMAILS = [
    'alek.bergners@icloud.com',      # Yosh
    'anton.bergners@icloud.com',     # Tosh
    'sasha.bergners@icloud.com',     # Sasha
    'alina.bergners@me.com'          # Alina
]

CC_EMAIL = 'moosya@me.com'  # Drei

STATE_FILE = '/workspace/memory/expense-reminder-state.json'


def load_state():
    """Load reminder state to avoid duplicate sends"""
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, 'r') as f:
        return json.load(f)


def save_state(state):
    """Save reminder state"""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def already_sent_today():
    """Check if reminder already sent today"""
    state = load_state()
    today = datetime.now().strftime('%Y-%m-%d')
    return state.get('last_sent') == today


def mark_sent():
    """Mark reminder as sent today"""
    state = load_state()
    state['last_sent'] = datetime.now().strftime('%Y-%m-%d')
    state['last_sent_timestamp'] = datetime.now().isoformat()
    save_state(state)


def should_send_today():
    """Check if today is 1st or 15th"""
    day = datetime.now().day
    return day in [1, 15]


def get_next_month_due_date():
    """Calculate next report due date (5th of next month)"""
    now = datetime.now()
    if now.month == 12:
        next_month = 1
        next_year = now.year + 1
    else:
        next_month = now.month + 1
        next_year = now.year
    
    # Month names
    months = ['', 'January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December']
    
    # Current month for "X spending report due"
    current_month = months[now.month]
    next_month_name = months[next_month]
    
    return current_month, f"{next_month_name} 5th"


def send_reminder():
    """Send expense reminder email"""
    
    # Load credentials
    TOKEN_FILE = '/workspace/.credentials/gmail-token.pickle'
    with open(TOKEN_FILE, 'rb') as token:
        creds = pickle.load(token)
    
    service = build('gmail', 'v1', credentials=creds)
    
    current_month, due_date = get_next_month_due_date()
    
    html_body = f"""
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333;">

<h2 style="color: #2c5282;">💳 Monthly Expense Report Reminder</h2>

<p>Hi everyone,</p>

<p>This is your <strong>twice-monthly reminder</strong> to track and submit your spending report.</p>

<div style="background-color: #fff5f5; border-left: 4px solid #fc8181; padding: 15px; margin: 20px 0;">
    <p style="margin: 0; font-weight: bold;">📅 Important Dates:</p>
    <ul style="margin: 10px 0;">
        <li><strong>{current_month} spending report due:</strong> <span style="color: #e53e3e;">{due_date}</span></li>
        <li><strong>Late = $0 spending limit</strong> for the following month (no exceptions)</li>
    </ul>
</div>

<h3 style="color: #2c5282;">📋 How to Submit (5 minutes):</h3>

<ol>
    <li><strong>Go to <a href="https://card.apple.com" style="color: #3182ce;">card.apple.com</a></strong> on your laptop</li>
    <li><strong>Export transactions</strong> for the month → CSV format</li>
    <li><strong>Open in Google Sheets</strong> (sheets.google.com → Import)</li>
    <li><strong>Add 4 columns:</strong>
        <ul>
            <li><strong>Your Category</strong> (Groceries, Dining Out, etc.)</li>
            <li><strong>Why/Who/What</strong> ("Birthday gift for Dad", not just "shopping")</li>
            <li><strong>Planned?</strong> (Yes/No)</li>
            <li><strong>Notes</strong> (optional)</li>
        </ul>
    </li>
    <li><strong>Share with Frank:</strong>
        <ul>
            <li><strong>Option 1:</strong> Click "Share" in Google Sheets → Add <a href="mailto:dreis.assistant@gmail.com" style="color: #3182ce;">dreis.assistant@gmail.com</a> as <strong>Viewer</strong> → Send me the link</li>
            <li><strong>Option 2:</strong> Email the CSV/Excel file to <a href="mailto:dreis.assistant@gmail.com" style="color: #3182ce;">dreis.assistant@gmail.com</a></li>
        </ul>
    </li>
</ol>

<div style="background-color: #f0fff4; border-left: 4px solid #68d391; padding: 15px; margin: 20px 0;">
    <p style="margin: 0;"><strong>✅ Need the detailed template?</strong></p>
    <p style="margin: 5px 0;">Reply to this email asking for the template!</p>
</div>

<h3 style="color: #2c5282;">💡 Quick Tips:</h3>

<table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
    <tr>
        <td style="padding: 10px; background-color: #f7fafc; border: 1px solid #e2e8f0; width: 30%;">
            <strong>❌ Vague:</strong>
        </td>
        <td style="padding: 10px; background-color: #f7fafc; border: 1px solid #e2e8f0;">
            "Shopping"
        </td>
    </tr>
    <tr>
        <td style="padding: 10px; background-color: #ffffff; border: 1px solid #e2e8f0;">
            <strong>✅ Specific:</strong>
        </td>
        <td style="padding: 10px; background-color: #ffffff; border: 1px solid #e2e8f0;">
            "Birthday gift for Dad"
        </td>
    </tr>
</table>

<p style="margin-top: 30px; color: #718096; font-size: 14px;">
    <strong>Why we're doing this:</strong> This isn't busywork—it's about us staying on top of things together. 
    Financial awareness is a life skill.
</p>

<p style="margin-top: 20px;">
    Questions? Reply to this email!<br/>
    <br/>
    Cheers,<br/>
    <strong>Frank 🦀</strong>
</p>

</body>
</html>
"""
    
    text_body = f"""💳 Monthly Expense Report Reminder

Hi everyone,

This is your twice-monthly reminder to track and submit your spending report.

📅 IMPORTANT:
• {current_month} spending report due: {due_date}
• Late = $0 spending limit for the following month (no exceptions)

📋 HOW TO SUBMIT (5 minutes):
1. Go to card.apple.com on your laptop
2. Export transactions → CSV format
3. Open in Google Sheets
4. Add columns: Your Category, Why/Who/What, Planned?, Notes
5. Share with dreis.assistant@gmail.com or email CSV

💡 Be specific: "Birthday gift for Dad" not just "shopping"

Questions? Reply to this email!

Cheers,
Frank 🦀
"""
    
    # Create message
    message = MIMEMultipart('alternative')
    message['to'] = ', '.join(FAMILY_EMAILS)
    message['cc'] = CC_EMAIL
    message['subject'] = f'💳 Expense Report Reminder - {current_month} Due {due_date}'
    message['from'] = 'dreis.assistant@gmail.com'
    
    part1 = MIMEText(text_body, 'plain')
    part2 = MIMEText(html_body, 'html')
    message.attach(part1)
    message.attach(part2)
    
    # Send
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    result = service.users().messages().send(userId='me', body={'raw': raw}).execute()
    
    print(f"✅ Expense reminder sent!")
    print(f"   To: {len(FAMILY_EMAILS)} family members")
    print(f"   CC: {CC_EMAIL}")
    print(f"   Subject: {current_month} Due {due_date}")
    print(f"   Message ID: {result['id']}")
    
    return True


if __name__ == '__main__':
    print("Family Expense Reminder")
    print("=" * 50)
    
    # Check if today is 1st or 15th
    if not should_send_today():
        print(f"❌ Today is {datetime.now().strftime('%B %d')} - not 1st or 15th")
        print("   No reminder needed")
        sys.exit(0)
    
    # Check if already sent today
    if already_sent_today():
        print(f"✅ Reminder already sent today")
        sys.exit(0)
    
    # Send reminder
    try:
        send_reminder()
        mark_sent()
    except Exception as e:
        print(f"❌ Failed to send reminder: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
