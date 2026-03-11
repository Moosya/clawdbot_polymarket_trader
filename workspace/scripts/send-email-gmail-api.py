#!/usr/bin/env python3
"""
Send Email via Gmail API (not SMTP)
Uses HTTPS (port 443) to bypass DigitalOcean SMTP port blocking
"""

import sys
import os

# Add workspace packages to Python path (for sandbox environment)
sys.path.insert(0, '/workspace/.local')

import base64
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

def create_message(to, subject, body_text, body_html=None):
    """Create email message in Gmail API format"""
    if body_html:
        message = MIMEMultipart('alternative')
        part1 = MIMEText(body_text, 'plain')
        part2 = MIMEText(body_html, 'html')
        message.attach(part1)
        message.attach(part2)
    else:
        message = MIMEText(body_text)
    
    message['to'] = to
    message['subject'] = subject
    message['from'] = 'dreis.assistant@gmail.com'
    
    # Encode message
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw}

def send_email(to, subject, body, html=None):
    """
    Send email via Gmail API
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Plain text body
        html: Optional HTML body
    
    Returns:
        True if sent successfully, False otherwise
    """
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        import pickle
        
        SCOPES = [
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.compose',
            'https://www.googleapis.com/auth/gmail.labels'
        ]
        # Use workspace-relative paths (works in both sandbox and host)
        WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        CREDS_FILE = os.path.join(WORKSPACE, '.credentials', 'gmail-credentials.json')
        TOKEN_FILE = os.path.join(WORKSPACE, '.credentials', 'gmail-token.pickle')
        
        creds = None
        
        # Load existing token if available
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, need to authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                print("❌ Error: Gmail credentials not valid")
                return False
        
        # Build Gmail service
        service = build('gmail', 'v1', credentials=creds)
        
        # Create message
        message = create_message(to, subject, body, html)
        
        # Send
        result = service.users().messages().send(userId='me', body=message).execute()
        
        print(f"✅ Email sent successfully!")
        print(f"   To: {to}")
        print(f"   Subject: {subject}")
        print(f"   Message ID: {result['id']}")
        
        return True
        
    except ImportError:
        print("❌ Missing required packages")
        print("   Install with: pip install google-auth google-auth-oauthlib google-api-python-client")
        return False
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: send-email-gmail-api.py <to> <subject> <body> [html]")
        print("Example: send-email-gmail-api.py user@example.com 'Test' 'Plain text' '<b>HTML</b>'")
        sys.exit(1)
    
    to = sys.argv[1]
    subject = sys.argv[2]
    body = sys.argv[3]
    html = sys.argv[4] if len(sys.argv) > 4 else None
    
    success = send_email(to, subject, body, html)
    sys.exit(0 if success else 1)
