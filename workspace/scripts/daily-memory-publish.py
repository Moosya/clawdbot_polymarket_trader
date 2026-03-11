#!/usr/bin/env python3
"""
Daily Memory Publisher
Extracts learnings from events.jsonl and creates budget-model-friendly summary
Cost: $0 (no AI, just pattern extraction)
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

EVENTS_LOG = Path('memory/events.jsonl')
OUTPUT_DIR = Path('memory/daily-learnings')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_todays_events():
    """Load events from today"""
    if not EVENTS_LOG.exists():
        return []
    
    today = datetime.now().date()
    events = []
    
    with open(EVENTS_LOG, 'r') as f:
        for line in f:
            try:
                event = json.loads(line.strip())
                event_time = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                if event_time.date() == today:
                    events.append(event)
            except (json.JSONDecodeError, KeyError):
                continue
    
    return events

def extract_learnings(events):
    """Extract patterns and learnings from events"""
    
    learnings = {
        'date': datetime.now().date().isoformat(),
        'total_events': len(events),
        'task_counts': defaultdict(int),
        'error_patterns': [],
        'success_patterns': [],
        'performance_metrics': {},
        'key_decisions': [],
        'lessons_learned': []
    }
    
    for event in events:
        task = event.get('task', 'unknown')
        learnings['task_counts'][task] += 1
        
        # Track errors
        if event.get('exit_code', 0) != 0:
            learnings['error_patterns'].append({
                'task': task,
                'command': event.get('command', ''),
                'error': event.get('output', '')[:200]
            })
        
        # Track successes
        elif 'success' in event.get('output', '').lower():
            learnings['success_patterns'].append({
                'task': task,
                'duration_ms': event.get('duration_ms', 0)
            })
        
        # Extract trading-specific learnings
        if 'trading' in task or 'signal' in task:
            output = event.get('output', '')
            if 'HIGH CONFIDENCE' in output:
                learnings['key_decisions'].append({
                    'type': 'high_confidence_signal',
                    'timestamp': event['timestamp'],
                    'details': output[:500]
                })
            elif 'HEARTBEAT_OK' in output:
                learnings['performance_metrics']['signals_checked'] = \
                    learnings['performance_metrics'].get('signals_checked', 0) + 1
    
    # Generate actionable lessons
    if len(learnings['error_patterns']) > 2:
        learnings['lessons_learned'].append(
            f"High error rate today ({len(learnings['error_patterns'])} errors) - investigate recurring issues"
        )
    
    if learnings['task_counts'].get('check-signals', 0) > 0:
        learnings['lessons_learned'].append(
            f"Checked signals {learnings['task_counts']['check-signals']} times today - routine monitoring working"
        )
    
    return learnings

def create_budget_friendly_summary(learnings):
    """Create plain English summary that budget models can easily parse"""
    
    summary = f"""# Daily Learnings: {learnings['date']}

## Quick Stats
- Total events logged: {learnings['total_events']}
- Tasks executed: {len(learnings['task_counts'])}
- Errors encountered: {len(learnings['error_patterns'])}
- Successful completions: {len(learnings['success_patterns'])}

## What Happened Today
"""
    
    for task, count in learnings['task_counts'].items():
        summary += f"- {task}: {count} times\n"
    
    if learnings['key_decisions']:
        summary += "\n## Important Decisions\n"
        for decision in learnings['key_decisions']:
            summary += f"- [{decision['timestamp']}] {decision['type']}\n"
    
    if learnings['error_patterns']:
        summary += "\n## Errors to Remember\n"
        for error in learnings['error_patterns'][:3]:  # Top 3 only
            summary += f"- {error['task']}: {error['error'][:100]}...\n"
    
    if learnings['lessons_learned']:
        summary += "\n## Lessons Learned\n"
        for lesson in learnings['lessons_learned']:
            summary += f"- {lesson}\n"
    
    summary += "\n---\n*Auto-generated summary. No AI cost incurred.*\n"
    
    return summary

def main():
    """Generate today's learning summary"""
    
    events = load_todays_events()
    
    if not events:
        print("ℹ️  No events logged today")
        return
    
    learnings = extract_learnings(events)
    
    # Save JSON for programmatic access
    today = datetime.now().date().isoformat()
    json_path = OUTPUT_DIR / f"{today}.json"
    with open(json_path, 'w') as f:
        json.dump(learnings, f, indent=2)
    
    # Save markdown for human/budget-model reading
    summary = create_budget_friendly_summary(learnings)
    md_path = OUTPUT_DIR / f"{today}.md"
    with open(md_path, 'w') as f:
        f.write(summary)
    
    print(f"✅ Daily learnings published:")
    print(f"   JSON: {json_path}")
    print(f"   Summary: {md_path}")
    print(f"\n📊 Stats:")
    print(f"   Events: {learnings['total_events']}")
    print(f"   Tasks: {len(learnings['task_counts'])}")
    print(f"   Lessons: {len(learnings['lessons_learned'])}")

if __name__ == '__main__':
    main()
