#!/usr/bin/env python3
"""
Weekly Polymarket Trading Summary
Generates comprehensive report covering:
1. Trading activities (P&L, signals, stats)
2. Platform changes/improvements
3. TODOs for future development

Runs every Monday morning, sends email to Drei
"""

import sys
import os
sys.path.insert(0, '/workspace/.local')

import sqlite3
import json
from datetime import datetime, timedelta
from collections import defaultdict
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import pickle


def get_db_connection(db_path):
    """Get database connection"""
    return sqlite3.connect(db_path)


def get_trading_stats():
    """Get trading statistics for the past week"""
    # Auto-detect database location (production vs sandbox)
    if os.path.exists('/opt/polymarket/data/trading.db'):
        db_path = '/opt/polymarket/data/trading.db'  # Production
    else:
        db_path = '/workspace/polymarket_runtime/data/trading.db'  # Sandbox fallback
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Get positions opened this week
    cursor.execute('''
        SELECT 
            COUNT(*) as total_positions,
            SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) as open_positions,
            SUM(CASE WHEN status = 'CLOSED' THEN 1 ELSE 0 END) as closed_positions,
            AVG(confidence) as avg_confidence
        FROM paper_positions
        WHERE datetime(created_at) > datetime('now', '-7 days')
    ''')
    
    positions = cursor.fetchone()
    
    # Get signals detected this week
    cursor.execute('''
        SELECT 
            type,
            COUNT(*) as count,
            AVG(confidence) as avg_confidence
        FROM signals
        WHERE datetime(created_at) > datetime('now', '-7 days')
        GROUP BY type
    ''')
    
    signals = cursor.fetchall()
    
    # Get P&L (paper trading) - both realized and unrealized
    # Realized (closed positions)
    cursor.execute('''
        SELECT 
            COALESCE(SUM(pnl), 0) as realized_pnl,
            COUNT(*) as closed_count
        FROM paper_positions
        WHERE status = 'CLOSED'
          AND datetime(exit_time, 'unixepoch') > datetime('now', '-7 days')
    ''')
    
    realized = cursor.fetchone()
    
    # Unrealized (open positions)
    cursor.execute('''
        SELECT 
            COALESCE(SUM(unrealized_pnl), 0) as unrealized_pnl,
            COUNT(*) as open_count
        FROM paper_positions
        WHERE status = 'OPEN'
    ''')
    
    unrealized = cursor.fetchone()
    
    # Total P&L
    total_pnl = realized[0] + unrealized[0]
    pnl = (total_pnl, realized[0], unrealized[0], realized[1])
    
    conn.close()
    
    return {
        'positions': {
            'total': positions[0] or 0,
            'open': positions[1] or 0,
            'closed': positions[2] or 0,
            'avg_confidence': positions[3] or 0
        },
        'signals': [{'type': s[0], 'count': s[1], 'avg_confidence': s[2]} for s in signals],
        'pnl': {
            'total': pnl[0],
            'realized': pnl[1],
            'unrealized': pnl[2],
            'closed_count': pnl[3]
        }
    }


def get_whale_activity():
    """Get whale trading activity for the week"""
    # Auto-detect database location (production vs sandbox)
    if os.path.exists('/opt/polymarket/data/trades.db'):
        db_path = '/opt/polymarket/data/trades.db'  # Production
    else:
        db_path = '/workspace/polymarket_runtime/data/trades.db'  # Sandbox fallback
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            COUNT(*) as total_trades,
            COUNT(DISTINCT marketSlug) as unique_markets,
            COUNT(DISTINCT trader) as unique_whales,
            SUM(sizeUsd) as total_volume,
            AVG(sizeUsd) as avg_trade_size
        FROM trades
        WHERE sizeUsd >= 2000
          AND datetime(timestamp, 'unixepoch') > datetime('now', '-7 days')
    ''')
    
    activity = cursor.fetchone()
    conn.close()
    
    return {
        'trades': activity[0] or 0,
        'markets': activity[1] or 0,
        'whales': activity[2] or 0,
        'volume': activity[3] or 0,
        'avg_size': activity[4] or 0
    }


def get_system_changes():
    """Get recent system changes from git commits"""
    import subprocess
    
    try:
        # Get commits from last week
        result = subprocess.run(
            ['git', 'log', '--since=7.days.ago', '--pretty=format:%h|%s|%cr'],
            cwd='/workspace/projects/polymarket',
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    hash, message, time = line.split('|', 2)
                    commits.append({'hash': hash, 'message': message, 'time': time})
            return commits
        return []
    except Exception as e:
        return [{'error': str(e)}]


def get_todos():
    """Get current TODOs from various sources"""
    todos = []
    
    # Check CURRENT_ISSUES.md
    if os.path.exists('/workspace/CURRENT_ISSUES.md'):
        with open('/workspace/CURRENT_ISSUES.md', 'r') as f:
            content = f.read()
            # Extract high priority issues
            if '🟡 HIGH:' in content:
                todos.append({
                    'priority': 'HIGH',
                    'source': 'CURRENT_ISSUES.md',
                    'items': 'See CURRENT_ISSUES.md for details'
                })
    
    # Hard-coded known TODOs
    todos.extend([
        {
            'priority': 'HIGH',
            'item': 'Deploy signal filtering (remove sports/entertainment)',
            'status': 'Ready to deploy'
        },
        {
            'priority': 'MEDIUM',
            'item': 'Improve Grok prompt (force JSON output or AI interpreter)',
            'status': 'Needs design decision'
        },
        {
            'priority': 'MEDIUM',
            'item': 'Implement backup strategy (git + encrypted secrets)',
            'status': 'Plan created, needs execution'
        },
        {
            'priority': 'LOW',
            'item': 'Upgrade to Claude Sonnet 4.6',
            'status': 'Waiting for OpenClaw support'
        }
    ])
    
    return todos


def generate_html_report(stats, whale_activity, changes, todos):
    """Generate HTML email report"""
    
    html = """
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333;">

<h1 style="color: #2c5282;">📊 Weekly Polymarket Summary</h1>
<p style="color: #718096;">Week of {week_start} - {week_end}</p>

<hr style="border: none; border-top: 2px solid #e2e8f0; margin: 30px 0;">

<h2 style="color: #2c5282;">1️⃣ Trading Performance</h2>

<div style="background-color: #f7fafc; border-left: 4px solid #4299e1; padding: 15px; margin: 20px 0;">
    <h3 style="margin-top: 0; color: #2c5282;">Positions</h3>
    <ul>
        <li><strong>Total opened this week:</strong> {positions_total}</li>
        <li><strong>Currently open:</strong> {positions_open}</li>
        <li><strong>Closed this week:</strong> {positions_closed}</li>
        <li><strong>Avg confidence:</strong> {avg_confidence:.1f}%</li>
    </ul>
</div>

<div style="background-color: #f0fff4; border-left: 4px solid #68d391; padding: 15px; margin: 20px 0;">
    <h3 style="margin-top: 0; color: #2c5282;">P&L (Paper Trading)</h3>
    <ul>
        <li><strong>Total P&L:</strong> <span style="color: {pnl_color}; font-weight: bold;">${pnl_total:.2f}</span></li>
        <li><strong>Realized:</strong> ${pnl_realized:.2f} ({pnl_closed_count} trades closed)</li>
        <li><strong>Unrealized:</strong> <span style="color: {unrealized_color};">${pnl_unrealized:.2f}</span> (open positions)</li>
    </ul>
</div>

<h3 style="color: #2c5282;">Signals Detected</h3>
<table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
    <tr style="background-color: #f7fafc;">
        <th style="padding: 10px; border: 1px solid #e2e8f0; text-align: left;">Signal Type</th>
        <th style="padding: 10px; border: 1px solid #e2e8f0; text-align: right;">Count</th>
        <th style="padding: 10px; border: 1px solid #e2e8f0; text-align: right;">Avg Confidence</th>
    </tr>
    {signals_rows}
</table>

<h3 style="color: #2c5282;">Whale Activity</h3>
<ul>
    <li><strong>Whale trades (≥$2k):</strong> {whale_trades:,}</li>
    <li><strong>Unique markets:</strong> {whale_markets:,}</li>
    <li><strong>Unique whales:</strong> {whale_count:,}</li>
    <li><strong>Total volume:</strong> ${whale_volume:,.0f}</li>
    <li><strong>Avg trade size:</strong> ${whale_avg:,.0f}</li>
</ul>

<hr style="border: none; border-top: 2px solid #e2e8f0; margin: 30px 0;">

<h2 style="color: #2c5282;">2️⃣ Platform Changes This Week</h2>

{changes_section}

<hr style="border: none; border-top: 2px solid #e2e8f0; margin: 30px 0;">

<h2 style="color: #2c5282;">3️⃣ TODOs & Future Improvements</h2>

{todos_section}

<hr style="border: none; border-top: 2px solid #e2e8f0; margin: 30px 0;">

<p style="color: #718096; font-size: 14px; margin-top: 30px;">
    Generated automatically by Frank 🦀<br/>
    Questions? Reply to this email.
</p>

</body>
</html>
"""
    
    # Calculate week range
    now = datetime.now()
    week_start = (now - timedelta(days=7)).strftime('%B %d')
    week_end = now.strftime('%B %d, %Y')
    
    # Build signals table
    signals_rows = ''
    if stats['signals']:
        for signal in stats['signals']:
            signals_rows += f"""
    <tr>
        <td style="padding: 10px; border: 1px solid #e2e8f0;">{signal['type']}</td>
        <td style="padding: 10px; border: 1px solid #e2e8f0; text-align: right;">{signal['count']}</td>
        <td style="padding: 10px; border: 1px solid #e2e8f0; text-align: right;">{signal['avg_confidence']:.1f}%</td>
    </tr>
"""
    else:
        signals_rows = '<tr><td colspan="3" style="padding: 10px; border: 1px solid #e2e8f0; text-align: center; color: #718096;">No signals detected this week</td></tr>'
    
    # Build changes section
    if changes:
        changes_section = '<ul>'
        for change in changes:
            if 'error' in change:
                changes_section += f'<li style="color: #e53e3e;">Error fetching changes: {change["error"]}</li>'
            else:
                changes_section += f'<li><code>{change["hash"]}</code> - {change["message"]} <em style="color: #718096;">({change["time"]})</em></li>'
        changes_section += '</ul>'
    else:
        changes_section = '<p style="color: #718096;">No changes this week</p>'
    
    # Build TODOs section
    todos_section = ''
    priorities = {'HIGH': [], 'MEDIUM': [], 'LOW': []}
    for todo in todos:
        priorities[todo['priority']].append(todo)
    
    for priority, items in priorities.items():
        if items:
            color = {'HIGH': '#fc8181', 'MEDIUM': '#f6ad55', 'LOW': '#68d391'}[priority]
            todos_section += f'<div style="background-color: #fff5f5; border-left: 4px solid {color}; padding: 15px; margin: 15px 0;">'
            todos_section += f'<h3 style="margin-top: 0; color: #2c5282;">🔴 {priority} Priority</h3><ul>'
            for item in items:
                item_text = item.get('item') or item.get('items', 'Unknown item')
                todos_section += f'<li><strong>{item_text}</strong>'
                if 'status' in item:
                    todos_section += f' - <em>{item["status"]}</em>'
                todos_section += '</li>'
            todos_section += '</ul></div>'
    
    # Determine P&L colors
    pnl_color = '#48bb78' if stats['pnl']['total'] >= 0 else '#f56565'
    unrealized_color = '#48bb78' if stats['pnl']['unrealized'] >= 0 else '#f56565'
    
    return html.format(
        week_start=week_start,
        week_end=week_end,
        positions_total=stats['positions']['total'],
        positions_open=stats['positions']['open'],
        positions_closed=stats['positions']['closed'],
        avg_confidence=stats['positions']['avg_confidence'],
        pnl_total=stats['pnl']['total'],
        pnl_realized=stats['pnl']['realized'],
        pnl_unrealized=stats['pnl']['unrealized'],
        pnl_closed_count=stats['pnl']['closed_count'],
        pnl_color=pnl_color,
        unrealized_color=unrealized_color,
        signals_rows=signals_rows,
        whale_trades=whale_activity['trades'],
        whale_markets=whale_activity['markets'],
        whale_count=whale_activity['whales'],
        whale_volume=whale_activity['volume'],
        whale_avg=whale_activity['avg_size'],
        changes_section=changes_section,
        todos_section=todos_section
    )


def send_summary_email(html_content):
    """Send weekly summary email"""
    TOKEN_FILE = '/workspace/.credentials/gmail-token.pickle'
    with open(TOKEN_FILE, 'rb') as token:
        creds = pickle.load(token)
    
    service = build('gmail', 'v1', credentials=creds)
    
    message = MIMEMultipart('alternative')
    message['to'] = 'moosya@me.com'
    message['subject'] = f'📊 Weekly Polymarket Summary - {datetime.now().strftime("%B %d, %Y")}'
    message['from'] = 'dreis.assistant@gmail.com'
    
    # Text version (simplified)
    text_body = "Weekly Polymarket Summary - see HTML version for full details"
    
    part1 = MIMEText(text_body, 'plain')
    part2 = MIMEText(html_content, 'html')
    message.attach(part1)
    message.attach(part2)
    
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    result = service.users().messages().send(userId='me', body={'raw': raw}).execute()
    
    print(f"✅ Weekly summary sent!")
    print(f"   To: moosya@me.com")
    print(f"   Message ID: {result['id']}")


if __name__ == '__main__':
    print("Generating Weekly Polymarket Summary...")
    print("=" * 50)
    
    try:
        # Gather data
        print("📊 Getting trading stats...")
        stats = get_trading_stats()
        
        print("🐋 Getting whale activity...")
        whale_activity = get_whale_activity()
        
        print("🔧 Getting system changes...")
        changes = get_system_changes()
        
        print("📋 Getting TODOs...")
        todos = get_todos()
        
        # Generate report
        print("📝 Generating report...")
        html_report = generate_html_report(stats, whale_activity, changes, todos)
        
        # Send email
        print("📧 Sending email...")
        send_summary_email(html_report)
        
        print("\n✅ Weekly summary complete!")
        
    except Exception as e:
        print(f"\n❌ Error generating summary: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
