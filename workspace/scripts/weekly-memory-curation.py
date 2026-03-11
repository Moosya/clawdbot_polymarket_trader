#!/usr/bin/env python3
"""
Weekly Memory Curation
Uses mid-tier model to review 7 days of learnings and update MEMORY.md
Cost: ~$0.50/week (1-2 Sonnet calls)
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

DAILY_LEARNINGS_DIR = Path('/workspace/memory/daily-learnings')
MEMORY_FILE = Path('/workspace/MEMORY.md')

def load_weekly_learnings():
    """Load last 7 days of daily learnings"""
    learnings = []
    
    for days_ago in range(7):
        date = (datetime.now() - timedelta(days=days_ago)).date().isoformat()
        json_path = DAILY_LEARNINGS_DIR / f"{date}.json"
        
        if json_path.exists():
            with open(json_path, 'r') as f:
                learnings.append(json.load(f))
    
    return learnings

def generate_curation_prompt(weekly_learnings):
    """Generate prompt for mid-tier model to curate memory"""
    
    prompt = """# Weekly Memory Curation Task

You are curating 7 days of learnings into long-term memory (MEMORY.md).

## This Week's Data

"""
    
    for learning in weekly_learnings:
        prompt += f"\n### {learning['date']}\n"
        prompt += f"- Events: {learning['total_events']}\n"
        prompt += f"- Tasks: {dict(learning['task_counts'])}\n"
        prompt += f"- Errors: {len(learning['error_patterns'])}\n"
        
        if learning['lessons_learned']:
            prompt += "- Lessons:\n"
            for lesson in learning['lessons_learned']:
                prompt += f"  - {lesson}\n"
    
    prompt += """

## Your Task

1. Read the current MEMORY.md file
2. Identify patterns/learnings worth preserving long-term
3. Update MEMORY.md with:
   - New learnings (if significant)
   - Corrections to outdated info
   - Pattern recognition (e.g., "task X fails when Y happens")
   
## Rules

- ONLY add significant learnings (not routine operations)
- Be concise - MEMORY.md should stay readable
- Update existing sections rather than always appending
- Remove outdated information
- Focus on actionable knowledge for future sessions

## Output Format

Provide the updated MEMORY.md content (full file).
"""
    
    return prompt

def main():
    """Run weekly curation (uses mid-tier model)"""
    
    weekly_learnings = load_weekly_learnings()
    
    if not weekly_learnings:
        print("ℹ️  No learnings to curate this week")
        return
    
    prompt = generate_curation_prompt(weekly_learnings)
    
    # Save prompt for manual review or automated execution
    prompt_path = Path('/tmp/weekly-curation-prompt.txt')
    with open(prompt_path, 'w') as f:
        f.write(prompt)
    
    print(f"✅ Weekly curation prompt ready:")
    print(f"   Prompt: {prompt_path}")
    print(f"   Days reviewed: {len(weekly_learnings)}")
    print(f"\n📋 Next step:")
    print(f"   Run with Sonnet/GPT-4o to update MEMORY.md")
    print(f"   Estimated cost: ~$0.30-0.50")

if __name__ == '__main__':
    main()
