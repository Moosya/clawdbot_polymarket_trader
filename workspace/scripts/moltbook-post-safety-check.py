#!/usr/bin/env python3
"""
Moltbook Post Safety Check
Scans proposed post content for potential leaks of trading secrets
ALWAYS run before posting to Moltbook
"""

import re

# Forbidden keywords that might reveal our edge
FORBIDDEN_KEYWORDS = [
    # Signal detection specifics
    'whale cluster', 'smart money divergence', 'momentum reversal',
    '70%', '80%', '$2000', '$2,000',
    
    # Methods
    'grok validation', 'grok check', 'x.ai api',
    'gmail api', 'auto-trader',
    
    # Database/system internals
    'trading.db', 'trades.db', 'sqlite',
    'paper_positions', 'signals table',
    
    # Specific thresholds
    'auto-trade threshold', 'alert threshold', 'whale threshold',
    
    # Implementation details
    'detect-whale-clusters.py', 'detect-smart-money',
    'aggregate-signals', 'position monitor',
    
    # Performance metrics (specific numbers)
    'win rate', 'p&l', 'roi', 'sharpe ratio',
]

# Warning patterns (phrases that might be problematic)
WARNING_PATTERNS = [
    r'we (detect|identify|track|monitor)',
    r'our (system|algorithm|strategy|method)',
    r'(threshold|filter|criteria) (is|of|at) \d+',
    r'(automatically|auto) (trade|execute|open|close)',
    r'signal (detection|generation|validation)',
]

def check_post_safety(content):
    """
    Check if post content might leak trading secrets
    Returns: (is_safe, issues_found)
    """
    content_lower = content.lower()
    issues = []
    
    # Check forbidden keywords
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword.lower() in content_lower:
            issues.append(f"❌ Forbidden keyword: '{keyword}'")
    
    # Check warning patterns
    for pattern in WARNING_PATTERNS:
        matches = re.finditer(pattern, content_lower, re.IGNORECASE)
        for match in matches:
            issues.append(f"⚠️  Suspicious pattern: '{match.group()}'")
    
    # Additional checks
    # Check for specific numbers that might be thresholds
    number_mentions = re.findall(r'(\d+)%', content)
    if any(int(n) in [70, 75, 80] for n in number_mentions):
        issues.append("⚠️  Mentions threshold-like percentage (70%, 75%, 80%)")
    
    # Check for dollar amounts that might be our filters
    dollar_mentions = re.findall(r'\$(\d{1,3}(?:,\d{3})*)', content)
    if any(amt in ['2000', '2,000'] for amt in dollar_mentions):
        issues.append("⚠️  Mentions $2,000 (our whale threshold)")
    
    is_safe = len(issues) == 0
    
    return is_safe, issues


def suggest_safe_alternative(content):
    """Suggest a safer version of the content"""
    suggestions = []
    
    content_lower = content.lower()
    
    if 'whale' in content_lower:
        suggestions.append("💡 Instead of 'whale trading', say 'large trades' or 'institutional activity'")
    
    if any(word in content_lower for word in ['detect', 'identify', 'track']):
        suggestions.append("💡 Instead of specifics, ask general questions: 'How do forecasters typically...?'")
    
    if re.search(r'\d+%', content):
        suggestions.append("💡 Avoid specific percentages - use 'high confidence' or 'significant'")
    
    if 'our' in content_lower or 'we' in content_lower:
        suggestions.append("💡 Make it hypothetical: 'If someone wanted to...' or 'In theory...'")
    
    return suggestions


if __name__ == '__main__':
    import sys
    
    print("🔒 Moltbook Post Safety Checker")
    print("=" * 70)
    print("\nThis tool checks if your post might leak trading secrets.")
    print("Always run this before posting to public platforms!")
    print("\n" + "=" * 70 + "\n")
    
    if len(sys.argv) > 1:
        # Content provided as argument
        content = ' '.join(sys.argv[1:])
    else:
        # Interactive mode
        print("Enter your proposed post (Ctrl+D when done):")
        content = sys.stdin.read()
    
    is_safe, issues = check_post_safety(content)
    
    print("\n" + "=" * 70)
    print("📝 YOUR POST:")
    print("-" * 70)
    print(content)
    print("-" * 70)
    
    if is_safe:
        print("\n✅ SAFE TO POST - No obvious leaks detected")
        print("\n⚠️  But still consider:")
        print("   • Could competitors infer anything from context?")
        print("   • Is this giving away strategic thinking?")
        print("   • When in doubt, ask Drei first!")
    else:
        print("\n❌ POTENTIALLY UNSAFE - Issues found:")
        for issue in issues:
            print(f"   {issue}")
        
        suggestions = suggest_safe_alternative(content)
        if suggestions:
            print("\n💡 Suggestions:")
            for suggestion in suggestions:
                print(f"   {suggestion}")
        
        print("\n🛑 DO NOT POST without reviewing and revising!")
        print("   Either remove specifics or ask Drei for approval.")
        
        sys.exit(1)
