import requests

register_url = 'http://127.0.0.1:8000/api/auth/register'
chat_url = 'http://127.0.0.1:8000/api/chat/query'

import time
payload = {'email': f"test{int(time.time())}@example.com", 'password': 'password'}
try:
    r = requests.post(register_url, json=payload, timeout=10)
    print('register', r.status_code, r.text)
    if r.status_code == 200:
        token = r.json().get('access_token')
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        # use a non-greeting question to force LLM invocation
        r2 = requests.post(chat_url, json={'query': "What's the capital of France?"}, headers=headers, timeout=60)
        print('chat', r2.status_code, r2.text)
    else:
        print('Register failed; trying login to obtain token...')
        # Try login in case user already exists
        rlogin = requests.post('http://127.0.0.1:8000/api/auth/login', json=payload, timeout=10)
        print('login', rlogin.status_code, rlogin.text)
        if rlogin.status_code==200:
            token = rlogin.json().get('access_token')
            headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
            r2 = requests.post(chat_url, json={'query': 'hello'}, headers=headers, timeout=20)
            print('chat', r2.status_code, r2.text)
except Exception as e:
    print('error', str(e))
