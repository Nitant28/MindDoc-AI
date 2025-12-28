import os
import sys
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.core.config import settings

key = settings.deepseek_api_key
print('DEEPSEEK key present:', bool(key))

attempts = []

# 1) Direct requests to DeepSeek (OpenAI-compatible path)
try:
    url = 'https://api.deepseek.com/v1/chat/completions'
    headers = {'Authorization': f'Bearer {key}'}
    payload = {'model': 'gpt-4o-mini', 'messages': [{'role': 'user', 'content': 'Hello from test'}], 'max_tokens': 5}
    r = requests.post(url, json=payload, headers=headers, timeout=10)
    attempts.append(('deepseek_requests', r.status_code, r.text[:400]))
except Exception as e:
    attempts.append(('deepseek_requests', 'error', repr(e)))

# 2) openai client with api_base pointed to DeepSeek
try:
    import openai
    openai.api_key = key
    openai.api_base = 'https://api.deepseek.com/v1'
    # Try ChatCompletion (older API shape)
    try:
        resp = openai.ChatCompletion.create(model='gpt-4o-mini', messages=[{'role': 'user', 'content': 'Hello'}], max_tokens=5)
        attempts.append(('openai_deepseek_chatcompletion', 'ok', str(resp)[:400]))
    except Exception as e:
        attempts.append(('openai_deepseek_chatcompletion', 'error', repr(e)))
except Exception as e:
    attempts.append(('openai_client_init', 'error', repr(e)))

# 3) Try OpenRouter base (some providers accept keys on OpenRouter)
try:
    url = 'https://api.openrouter.ai/v1/chat/completions'
    headers = {'Authorization': f'Bearer {key}'}
    payload = {'model': 'gpt-4o-mini', 'messages': [{'role': 'user', 'content': 'Hello from OpenRouter test'}], 'max_tokens': 5}
    r = requests.post(url, json=payload, headers=headers, timeout=10)
    attempts.append(('openrouter_requests', r.status_code, r.text[:400]))
except Exception as e:
    attempts.append(('openrouter_requests', 'error', repr(e)))

# 4) Try openai client default base with key
try:
    import openai as openai2
    openai2.api_key = key
    try:
        resp = openai2.ChatCompletion.create(model='gpt-4o-mini', messages=[{'role':'user','content':'Hello'}], max_tokens=5)
        attempts.append(('openai_default', 'ok', str(resp)[:400]))
    except Exception as e:
        attempts.append(('openai_default', 'error', repr(e)))
except Exception as e:
    attempts.append(('openai_default_init', 'error', repr(e)))

print('\nAttempts:')
for a in attempts:
    print(a[0], '|', a[1])
    if isinstance(a[2], str):
        print(' ->', a[2])

# Summary suggestion
if any(a[1] == 'ok' for a in attempts):
    print('\nOne provider accepted the key. Good.')
else:
    print('\nNo provider accepted the key with these attempts. The key may be invalid for these endpoints.')
    print('You can:')
    print('- Provide a valid OpenAI-compatible API key (OPENAI_API_KEY)')
    print('- Provide a valid OpenRouter key and endpoint')
    print('- Or I can continue using the local fallback responses (already enabled)')
