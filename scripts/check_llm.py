import os
import sys
import requests

# Ensure project root is on sys.path so `app` package can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.core.config import settings

print('deepseek_api_key present:', bool(settings.deepseek_api_key))
print('gemini_api_key present:', bool(settings.gemini_api_key))

base = 'https://api.deepseek.com'
headers = {'Authorization': f'Bearer {settings.deepseek_api_key}'}

# Try a simple GET to the base URL
try:
    r = requests.get(base, headers=headers, timeout=10)
    print('GET base status:', r.status_code)
    print('GET base text (first 200 chars):', r.text[:200])
except Exception as e:
    print('GET base error:', repr(e))

# Try POST to likely OpenAI-compatible chat endpoint
try:
    url = base.rstrip('/') + '/v1/chat/completions'
    payload = {
        'model': 'gpt-4o-mini',
        'messages': [{'role': 'user', 'content': 'Say hi'}],
        'max_tokens': 10
    }
    r = requests.post(url, json=payload, headers=headers, timeout=15)
    print('POST /v1/chat/completions status:', r.status_code)
    print('POST response:', r.text[:1000])
except Exception as e:
    print('POST /v1/chat/completions error:', repr(e))
