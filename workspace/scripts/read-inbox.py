#!/usr/bin/env python3
"""Read recent emails from inbox using Gmail API"""
import sys
import os
sys.path.insert(0, '/workspace/.local')

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import pickle
import base64
from datetime import datetime, timedelta
import argparse

def get_email_body(msg_data):
    """Extract plain text body from email"""
    parts = msg_data['payload'].get('parts', [])
    body = ''
    
    if parts:
        for part in parts:
            if part['mimeType'] == 'text/plain':
                if 'data' in part['body']:
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                    break
    else:
        if 'body' in msg_data['payload'] and 'data' in msg_data['payload']['body']:
            body = base64.urlsafe_b64decode(msg_data['payload']['body']['data']).decode('utf-8', errors='ignore')
    
    return body

def main():
    parser = argparse.ArgumentParser(description='Read emails from inbox')
    parser.add_argument('--from', dest='from_addr', help='Filter by sender email')
    parser.add_argument('--days', type=int, default=3, help='Days to look back (default: 3)')
    parser.add_argument('--unread', action='store_true', help='Only show unread messages')
    parser.add_argument('--max', type=int, default=10, help='Max messages to retrieve (default: 10)')
    args = parser.parse_args()
    
    # Load credentials
    creds_path = '/workspace/.credentials/gmail-token.pickle'
    with open(creds_path, 'rb') as token:
        creds = pickle.load(token)
    
    service = build('gmail', 'v1', credentials=creds)
    
    # Build query
    query_parts = []
    
    if args.from_addr:
        query_parts.append(f'from:{args.from_addr}')
    
    if args.unread:
        query_parts.append('is:unread')
    
    days_ago = (datetime.now() - timedelta(days=args.days)).strftime('%Y/%m/%d')
    query_parts.append(f'after:{days_ago}')
    
    query = ' '.join(query_parts)
    
    # Get messages
    results = service.users().messages().list(userId='me', q=query, maxResults=args.max).execute()
    messages = results.get('messages', [])
    
    if not messages:
        print(f'No messages found matching: {query}')
        return
    
    print(f'Found {len(messages)} message(s)')
    print(f'Query: {query}')
    print('=' * 80)
    print()
    
    for i, msg in enumerate(messages, 1):
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        headers = msg_data['payload']['headers']
        
        from_addr = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No subject')
        date = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'No date')
        message_id = next((h['value'] for h in headers if h['name'].lower() == 'message-id'), 'No ID')
        
        # Check if unread
        labels = msg_data.get('labelIds', [])
        is_unread = 'UNREAD' in labels
        
        body = get_email_body(msg_data)
        
        print(f'[{i}] {"📧 UNREAD" if is_unread else "✓ Read"}')
        print(f'From: {from_addr}')
        print(f'Subject: {subject}')
        print(f'Date: {date}')
        print(f'Message-ID: {message_id}')
        print(f'\nBody:')
        print(body if body else '(No plain text body found)')
        print('=' * 80)
        print()

if __name__ == '__main__':
    main()
