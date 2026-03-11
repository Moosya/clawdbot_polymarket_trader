#!/usr/bin/env python3
"""
Memory Validation Script
Checks daily logs for hallucination markers before compaction
"""

import re
import os
from datetime import datetime, timedelta
from pathlib import Path

MEMORY_DIR = Path('/workspace/memory')
HALLUCINATION_PATTERNS = [
    r'\bprobably\b',
    r'\bseems\s+(like|to\s+be)\b',
    r'\bmight\s+be\b',
    r'\bI\s+think\b',
    r'\bsuggests\s+that\b',
    r'\blikely\b',
    r'\bappears\s+to\b',
    r'\bperhaps\b',
    r'\bmaybe\b',
    r'\bcould\s+be\b'
]

def check_file(filepath):
    """Check a single file for hallucination markers"""
    issues = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for line_num, line in enumerate(lines, 1):
        # Check if line contains model tag (budget models)
        is_budget_log = any(model in line.lower() for model in ['haiku', 'gpt4mini', 'gpt-4o-mini', 'deepseek'])
        
        if is_budget_log:
            for pattern in HALLUCINATION_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append({
                        'line': line_num,
                        'text': line.strip(),
                        'pattern': pattern,
                        'file': filepath.name
                    })
    
    return issues

def main():
    """Check recent daily logs for hallucinations"""
    
    if not MEMORY_DIR.exists():
        print("✅ No memory directory found - nothing to validate")
        return 0
    
    # Check last 7 days of logs
    issues_found = []
    files_checked = 0
    
    for days_ago in range(7):
        date = datetime.now() - timedelta(days=days_ago)
        filename = f"{date.strftime('%Y-%m-%d')}.md"
        filepath = MEMORY_DIR / filename
        
        if filepath.exists():
            files_checked += 1
            issues = check_file(filepath)
            issues_found.extend(issues)
    
    print(f"🔍 Memory Validation Report")
    print(f"   Files checked: {files_checked}")
    print(f"   Issues found: {len(issues_found)}")
    print()
    
    if issues_found:
        print("⚠️  HALLUCINATION MARKERS DETECTED:")
        print()
        
        for issue in issues_found:
            print(f"📁 {issue['file']} (line {issue['line']})")
            print(f"   Pattern: {issue['pattern']}")
            print(f"   Text: {issue['text'][:80]}...")
            print()
        
        print("❌ Validation FAILED - budget models wrote speculation to daily logs")
        print("   Action required: Review and clean up before compaction")
        return 1
    else:
        print("✅ Validation PASSED - no hallucination markers found")
        print("   Daily logs contain facts only")
        return 0

if __name__ == '__main__':
    exit(main())
