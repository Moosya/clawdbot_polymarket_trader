#!/usr/bin/env python3
"""
Cheap Grok calls using grok-3-mini for frequent position monitoring
"""

import os
import requests
from typing import Optional


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

def call_grok_mini(prompt: str, temperature: float = 0.3) -> Optional[str]:
    """Call Grok mini model (cheaper, for frequent checks)"""
    if not GROK_API_KEY:
        return None
    
    headers = {
        'Authorization': f'Bearer {GROK_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': 'grok-3-mini',  # Cheaper model for monitoring
        'messages': [
            {'role': 'system', 'content': 'You monitor prediction markets and detect breaking news.'},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': temperature,
        'max_tokens': 300  # Less tokens needed for monitoring
    }
    
    try:
        response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"⚠️  Grok Mini API error: {e}")
        return None
