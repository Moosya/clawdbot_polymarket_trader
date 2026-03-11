#!/usr/bin/env python3
"""
Check expense report submissions and send follow-up if needed
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
FAMILY_EMAILS = {
    'Yosh (Alek)': 'alek.bergners@icloud.com',
    'Tosh (Anton)': 'anton.bergners@icloud.com',
    'Sasha': 'sasha.bergners@icloud.com',
    'Alina': 'alina.bergners@me.com'
}

CC_EMAIL = 'moosya@me.com'
TRACKING_FILE = '/workspace/memory/expense-submissions-tracking.json'
TOKEN_PATH = '/workspace/.credentials/gmail-token.pickle'

def load_tracking():
    with open(TRACKING_FILE, 'r') as f:
        return json.load(f)

def get_gmail_service():
    """Get authenticated Gmail API service"""
    with open(TOKEN_PATH, 'rb') as token:
        creds = pickle.load(token)
    return build('gmail', 'v1', credentials=creds)

def send_follow_up_reminder(name, email, period, due_date):
    """Send gentle follow-up about expense report"""
    
    service = get_gmail_service()
    
    # Create message
    message = MIMEMultipart()
    message['to'] = email
    message['cc'] = CC_EMAIL
    message['from'] = 'me'
    message['subject'] = f'Expense Report Follow-up - {period}'
    
    body = f"""Hi {name.split('(')[0].strip()},

Just checking in on your expense report for {period}.

We haven't received it yet - if you've already sent it, my apologies for the duplicate! 

If not, here's a quick reminder:
• Due date: {due_date}
• We're 9 days away from the deadline

If you're having any issues or questions about the expense report, please let me know! 

Otherwise, please submit when you get a chance.

Thanks!
- Frank (via Drei's email system)
"""
    
    message.attach(MIMEText(body, 'plain'))
    
    # Send
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId='me', body={'raw': raw}).execute()
    
    print(f"✅ Sent follow-up to {name} ({email})")

def send_follow_ups():
    """Send follow-ups to anyone who hasn't submitted"""
    
    tracking = load_tracking()
    period = tracking['current_period']
    due_date = tracking['due_date']
    
    pending = []
    
    for name, status in tracking['submissions'].items():
        if not status['submitted']:
            email = FAMILY_EMAILS[name]
            send_follow_up_reminder(name, email, period, due_date)
            pending.append(name)
    
    if pending:
        print(f"\n📧 Sent follow-ups to: {', '.join(pending)}")
    else:
        print("✅ All reports submitted!")
    
    # Update tracking
    tracking['reminder_sent_dates'].append(datetime.now().isoformat())
    with open(TRACKING_FILE, 'w') as f:
        json.dump(tracking, f, indent=2)

if __name__ == '__main__':
    send_follow_ups()
