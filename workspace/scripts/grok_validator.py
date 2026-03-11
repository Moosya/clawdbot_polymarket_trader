#!/usr/bin/env python3
"""
Grok-based signal validation using X.AI API
Consults latest news context before opening positions
"""

import os
import requests
import json
import re
from typing import Dict, Optional


# Load environment variables from .env file
import os
if os.path.exists('/workspace/.env'):
    with open('/workspace/.env', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

GROK_API_KEY = os.getenv('XAI_API_KEY')
GROK_API_URL = 'https://api.x.ai/v1/chat/completions'

def call_grok(prompt: str, temperature: float = 0.3) -> Optional[str]:
    """Call Grok API with given prompt"""
    if not GROK_API_KEY:
        print("⚠️  Warning: XAI_API_KEY not set, skipping Grok validation")
        return None
    
    headers = {
        'Authorization': f'Bearer {GROK_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': 'grok-4-1-fast-reasoning',
        'messages': [
            {'role': 'system', 'content': 'You are a prediction market analyst with access to the latest news on X. Provide probability estimates based on current information from reputable sources.'},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': temperature,
        'max_tokens': 500
    }
    
    try:
        response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"⚠️  Grok API error: {e}")
        return None

def validate_signal_with_grok(market_question: str, market_slug: str, 
                              current_confidence: float, outcome: str) -> Dict:
    """
    Validate trading signal using Grok's news context
    Returns dict with: probability, reasoning, should_trade
    """
    prompt = f"""Based on the latest news from accurate sources on X/Twitter, analyze this prediction market:

Market Question: {market_question}
Betting on outcome: {outcome}
Algorithmic confidence: {current_confidence}%

Please provide your assessment in this exact format:
PROBABILITY: [0-100]%
KEY FACTORS: [bullet points of relevant news]
CONCERNS: [any ambiguities, definitional issues, or red flags]
RECOMMENDATION: [TRADE/HOLD/SKIP]

Focus on facts from reputable sources and be specific about timing and definitions."""

    response = call_grok(prompt)
    if not response:
        # Grok unavailable, proceed with algorithmic signal only
        return {
            'probability': current_confidence,
            'reasoning': 'Grok validation unavailable',
            'should_trade': current_confidence >= 70,
            'grok_available': False
        }
    
    # Parse Grok response
    probability = parse_probability(response)
    concerns = extract_concerns(response)
    recommendation = extract_recommendation(response)
    
    # Decision logic
    should_trade = decide_trade(probability, current_confidence, concerns, recommendation)
    
    reasoning = f"{current_confidence}% algo, {probability}% Grok"
    if concerns:
        reasoning += f" | Concerns: {concerns[:100]}"
    
    return {
        'probability': probability,
        'reasoning': reasoning,
        'should_trade': should_trade,
        'grok_available': True,
        'full_response': response
    }

def parse_probability(text: str) -> float:
    """Extract probability from Grok response"""
    match = re.search(r'PROBABILITY:\s*(\d+(?:\.\d+)?)', text)
    if match:
        return float(match.group(1))
    # Fallback: look for any percentage
    match = re.search(r'(\d+(?:\.\d+)?)%', text)
    return float(match.group(1)) if match else 50.0

def extract_concerns(text: str) -> str:
    """Extract concerns section"""
    match = re.search(r'CONCERNS:\s*(.+?)(?=RECOMMENDATION:|$)', text, re.DOTALL)
    if match:
        concerns = match.group(1).strip()
        # Look for red flags
        red_flags = ['partial', 'ambiguous', 'unclear', 'definition', 'depends on']
        if any(flag in concerns.lower() for flag in red_flags):
            return concerns[:200]  # Truncate
    return ""

def extract_recommendation(text: str) -> str:
    """Extract recommendation"""
    match = re.search(r'RECOMMENDATION:\s*(\w+)', text)
    return match.group(1).upper() if match else "HOLD"

def decide_trade(grok_prob: float, algo_prob: float, concerns: str, recommendation: str) -> bool:
    """Decision tree for whether to trade"""
    # Strong Grok red flags = no trade
    if concerns and len(concerns) > 50:
        return False
    
    # Grok says skip/hold = respect it
    if recommendation in ['SKIP', 'HOLD']:
        return False
    
    # Large disagreement (>30%) = no trade
    if abs(grok_prob - algo_prob) > 30:
        return False
    
    # Both agree high confidence = trade
    if algo_prob >= 70 and grok_prob >= 60:
        return True
    
    # Grok very confident, algo moderate = trade
    if grok_prob >= 75 and algo_prob >= 60:
        return True
    
    return False
