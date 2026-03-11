#!/usr/bin/env python3
"""
Memory Alignment Review - Active Learning System
Cleans stale memories, identifies contradictions, consolidates learnings
"""

import os
import re
from datetime import datetime, timedelta
from pathlib import Path

MEMORY_DIR = Path('/workspace/memory')
MEMORY_FILE = Path('/workspace/MEMORY.md')

def parse_memory_file(file_path):
    """Extract key facts and decisions from a memory file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    facts = []
    current_section = None
    
    # Extract sections and their content
    for line in content.split('\n'):
        if line.startswith('## '):
            current_section = line.replace('## ', '').strip()
        elif line.strip() and current_section:
            # Store facts with their section context
            facts.append({
                'section': current_section,
                'content': line.strip(),
                'file': file_path.name
            })
    
    return facts

def identify_contradictions(recent_facts, older_facts):
    """Find statements that contradict each other"""
    contradictions = []
    
    # Look for direct contradictions in similar sections
    for recent in recent_facts:
        for older in older_facts:
            if recent['section'] == older['section']:
                # Simple heuristic: if both talk about same topic but say opposite things
                recent_text = recent['content'].lower()
                older_text = older['content'].lower()
                
                # Check for negation patterns
                if ('not' in recent_text and 'not' not in older_text) or \
                   ('not' in older_text and 'not' not in recent_text):
                    # Same keywords but opposite meaning
                    recent_words = set(re.findall(r'\w+', recent_text))
                    older_words = set(re.findall(r'\w+', older_text))
                    overlap = recent_words & older_words
                    
                    if len(overlap) > 3:  # Significant overlap
                        contradictions.append({
                            'recent': recent,
                            'older': older,
                            'overlap': overlap
                        })
    
    return contradictions

def identify_outdated_info(daily_files):
    """Find information that's been superseded"""
    outdated = []
    
    # Patterns that indicate something is outdated
    outdated_patterns = [
        r'(?i)temporary',
        r'(?i)workaround',
        r'(?i)todo:',
        r'(?i)fixme:',
        r'(?i)needs.*fix',
        r'(?i)broken',
        r'(?i)failing'
    ]
    
    for file_path in daily_files:
        # Skip recent files (last 7 days)
        file_date = datetime.strptime(file_path.stem, '%Y-%m-%d')
        if datetime.now() - file_date < timedelta(days=7):
            continue
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        for pattern in outdated_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                # Get surrounding context (line)
                start = content.rfind('\n', 0, match.start()) + 1
                end = content.find('\n', match.end())
                line = content[start:end].strip()
                
                if line:
                    outdated.append({
                        'file': file_path.name,
                        'pattern': pattern,
                        'line': line
                    })
    
    return outdated

def extract_key_learnings(recent_days=7):
    """Extract important learnings from recent memory files"""
    daily_files = sorted(MEMORY_DIR.glob('????-??-??.md'), reverse=True)
    
    learnings = []
    cutoff_date = datetime.now() - timedelta(days=recent_days)
    
    for file_path in daily_files:
        try:
            file_date = datetime.strptime(file_path.stem, '%Y-%m-%d')
            if file_date < cutoff_date:
                continue
        except ValueError:
            continue
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Look for explicit learnings sections or bullet points marked as important
        learning_patterns = [
            r'### (?:Lessons?|Learning|Key Takeaways?)',
            r'(?:^|\n)- .*(?:learned|lesson|insight|discovered).*',
            r'✅.*',
            r'💡.*'
        ]
        
        for pattern in learning_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                # Get surrounding context
                start = max(0, content.rfind('\n', 0, match.start()) + 1)
                end = content.find('\n\n', match.end())
                if end == -1:
                    end = len(content)
                
                context = content[start:end].strip()
                if len(context) > 20:  # Skip trivial matches
                    learnings.append({
                        'date': file_date.strftime('%Y-%m-%d'),
                        'content': context
                    })
    
    return learnings

def generate_report():
    """Generate comprehensive alignment report"""
    report = []
    report.append("🧠 MEMORY ALIGNMENT REVIEW\n")
    report.append("=" * 60)
    report.append("")
    
    # Get daily files
    daily_files = sorted(MEMORY_DIR.glob('????-??-??.md'), reverse=True)
    
    if not daily_files:
        report.append("⚠️  No daily memory files found")
        return "\n".join(report)
    
    # Recent vs older comparison
    recent_files = daily_files[:7]  # Last week
    older_files = daily_files[7:30] if len(daily_files) > 7 else []
    
    report.append(f"📊 Memory Files: {len(daily_files)} total ({len(recent_files)} recent, {len(older_files)} older)")
    report.append("")
    
    # Extract facts
    recent_facts = []
    for f in recent_files:
        recent_facts.extend(parse_memory_file(f))
    
    older_facts = []
    for f in older_files[:5]:  # Don't parse all, just sample
        older_facts.extend(parse_memory_file(f))
    
    # Check for contradictions
    contradictions = identify_contradictions(recent_facts, older_facts)
    
    if contradictions:
        report.append(f"⚠️  CONTRADICTIONS DETECTED: {len(contradictions)}")
        report.append("")
        for i, c in enumerate(contradictions[:3], 1):  # Show top 3
            report.append(f"   {i}. Recent ({c['recent']['file']}): {c['recent']['content'][:60]}...")
            report.append(f"      vs Older ({c['older']['file']}): {c['older']['content'][:60]}...")
            report.append(f"      → ACTION NEEDED: Review and resolve")
            report.append("")
    else:
        report.append("✅ No contradictions detected")
        report.append("")
    
    # Check for outdated info
    outdated = identify_outdated_info(daily_files)
    
    if outdated:
        report.append(f"🗑️  OUTDATED INFO: {len(outdated)} items")
        report.append("")
        for item in outdated[:5]:  # Show top 5
            report.append(f"   • {item['file']}: {item['line'][:70]}...")
        report.append("")
        if len(outdated) > 5:
            report.append(f"   ... and {len(outdated) - 5} more")
            report.append("")
    else:
        report.append("✅ No obviously outdated information")
        report.append("")
    
    # Extract key learnings
    learnings = extract_key_learnings(recent_days=7)
    
    if learnings:
        report.append(f"💡 KEY LEARNINGS (Last 7 Days): {len(learnings)}")
        report.append("")
        for learning in learnings[:5]:  # Show top 5
            report.append(f"   • {learning['date']}: {learning['content'][:80]}...")
        report.append("")
        
        # Suggest MEMORY.md update
        if MEMORY_FILE.exists():
            report.append("📝 SUGGESTION: Consider adding recent learnings to MEMORY.md")
        else:
            report.append("⚠️  MEMORY.md doesn't exist - should create it")
        report.append("")
    
    # Summary
    report.append("=" * 60)
    issues = len(contradictions) + len(outdated)
    
    if issues == 0:
        report.append("✅ Memory is well-aligned and up-to-date")
    elif issues < 5:
        report.append(f"⚠️  {issues} minor issues detected - review recommended")
    else:
        report.append(f"🚨 {issues} issues detected - cleanup needed")
    
    return "\n".join(report)

if __name__ == '__main__':
    print(generate_report())
