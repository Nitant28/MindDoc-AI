import requests
try:
    r = requests.post('http://127.0.0.1:11434/api/generate', json={'model':'qwen3-coder:480b-cloud','prompt':'Say hello in one sentence','max_tokens':40}, timeout=10)
    print('STATUS', r.status_code)
    print(r.text[:2000])
except Exception as e:
    print('ERR', e)
