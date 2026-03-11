#!/usr/bin/env python3
"""
Analyze Family Expense Reports
Reads Google Sheets links or CSV/Excel attachments and generates summary
"""

import sys
import os
sys.path.insert(0, '/workspace/.local')

import pandas as pd
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import pickle
import re
from datetime import datetime


def read_google_sheet(sheet_url):
    """Read data from shared Google Sheet"""
    # Extract sheet ID from URL
    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', sheet_url)
    if not match:
        raise ValueError(f"Invalid Google Sheets URL: {sheet_url}")
    
    sheet_id = match.group(1)
    
    # Load credentials
    TOKEN_FILE = '/workspace/.credentials/gmail-token.pickle'
    with open(TOKEN_FILE, 'rb') as token:
        creds = pickle.load(token)
    
    # Build Sheets service
    service = build('sheets', 'v4', credentials=creds)
    
    # Read data (assumes data is in first sheet)
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range='A:Z'  # Get all columns
    ).execute()
    
    values = result.get('values', [])
    if not values:
        raise ValueError("Sheet is empty")
    
    # Convert to DataFrame
    df = pd.DataFrame(values[1:], columns=values[0])
    return df


def read_csv_file(file_path):
    """Read CSV file"""
    return pd.read_csv(file_path)


def read_excel_file(file_path):
    """Read Excel file"""
    return pd.read_excel(file_path)


def analyze_expenses(df, person_name):
    """Analyze expense data and generate summary"""
    
    # Standardize column names (handle variations)
    df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]
    
    # Required columns
    required = ['amount', 'your_category', 'why/who/what', 'planned?']
    missing = [col for col in required if col not in df.columns]
    if missing:
        return {
            'error': f"Missing required columns: {', '.join(missing)}",
            'columns_found': list(df.columns)
        }
    
    # Clean amount column (remove $, commas)
    df['amount_clean'] = df['amount'].astype(str).str.replace('$', '').str.replace(',', '')
    df['amount_clean'] = pd.to_numeric(df['amount_clean'], errors='coerce')
    
    # Total spending
    total = df['amount_clean'].sum()
    
    # By category
    category_totals = df.groupby('your_category')['amount_clean'].sum().sort_values(ascending=False)
    
    # Planned vs Unplanned
    planned = df[df['planned?'].str.lower().str.contains('yes', na=False)]['amount_clean'].sum()
    unplanned = df[df['planned?'].str.lower().str.contains('no', na=False)]['amount_clean'].sum()
    
    # Top 5 purchases
    top_5 = df.nlargest(5, 'amount_clean')[['amount', 'your_category', 'why/who/what']]
    
    # Data quality checks
    vague_descriptions = df[
        df['why/who/what'].str.lower().str.contains('stuff|things|needed|shopping|idk', na=False, case=False)
    ]
    
    missing_categories = df[df['your_category'].isna() | (df['your_category'].str.strip() == '')]
    
    # Generate summary
    summary = {
        'person': person_name,
        'total_spending': f"${total:,.2f}",
        'planned': f"${planned:,.2f} ({planned/total*100:.1f}%)",
        'unplanned': f"${unplanned:,.2f} ({unplanned/total*100:.1f}%)",
        'top_categories': {cat: f"${amt:,.2f}" for cat, amt in category_totals.head(5).items()},
        'top_5_purchases': top_5.to_dict('records'),
        'quality_issues': {
            'vague_descriptions': len(vague_descriptions),
            'missing_categories': len(missing_categories),
            'total_transactions': len(df)
        }
    }
    
    return summary


def generate_consolidated_report(summaries):
    """Generate consolidated report for all family members"""
    
    report = "# Family Expense Report Summary\n\n"
    report += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    report += "---\n\n"
    
    for summary in summaries:
        if 'error' in summary:
            report += f"## ❌ {summary['person']} - Error\n\n"
            report += f"**Issue:** {summary['error']}\n\n"
            if 'columns_found' in summary:
                report += f"**Columns found:** {', '.join(summary['columns_found'])}\n\n"
            continue
        
        report += f"## {summary['person']}\n\n"
        report += f"**Total Spending:** {summary['total_spending']}\n\n"
        
        report += f"### Planned vs Unplanned\n"
        report += f"- ✅ Planned: {summary['planned']}\n"
        report += f"- ⚠️ Unplanned: {summary['unplanned']}\n\n"
        
        report += f"### Top Categories\n"
        for cat, amt in summary['top_categories'].items():
            report += f"- **{cat}:** {amt}\n"
        report += "\n"
        
        report += f"### Top 5 Purchases\n"
        for i, purchase in enumerate(summary['top_5_purchases'], 1):
            report += f"{i}. **{purchase['amount']}** - {purchase['your_category']} - {purchase['why/who/what']}\n"
        report += "\n"
        
        # Quality check
        issues = summary['quality_issues']
        if issues['vague_descriptions'] > 0 or issues['missing_categories'] > 0:
            report += f"### ⚠️ Data Quality Issues\n"
            if issues['vague_descriptions'] > 0:
                report += f"- {issues['vague_descriptions']} vague descriptions (\"stuff\", \"things\", etc.)\n"
            if issues['missing_categories'] > 0:
                report += f"- {issues['missing_categories']} missing categories\n"
            report += "\n"
        
        report += "---\n\n"
    
    # Overall family totals
    total_family = sum([
        float(s['total_spending'].replace('$','').replace(',','')) 
        for s in summaries if 'total_spending' in s
    ])
    
    report += f"## 👨‍👩‍👧‍👦 Family Total: ${total_family:,.2f}\n\n"
    
    return report


if __name__ == '__main__':
    # Example usage
    print("Family Expense Report Analyzer")
    print("=" * 50)
    print("\nUsage:")
    print("  python3 analyze-family-expenses.py <person> <file_or_url>")
    print("\nExample:")
    print("  python3 analyze-family-expenses.py Sasha expenses.csv")
    print("  python3 analyze-family-expenses.py Alek https://docs.google.com/spreadsheets/d/...")
