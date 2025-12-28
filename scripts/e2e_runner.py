import requests
import json
import time

BASE = "http://127.0.0.1:8002/api"

def register(email, password):
    try:
        r = requests.post(f"{BASE}/auth/register", json={"email": email, "password": password})
        return r.status_code, r.text
    except Exception as e:
        return None, str(e)

def login(email, password):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]

def upload(token, filename, content):
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": (filename, content)}
    r = requests.post(f"{BASE}/documents/upload", headers=headers, files=files)
    return r.status_code, r.text

def query(token, question, session_id=None, document_id=None):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"query": question}
    if session_id:
        payload["session_id"] = session_id
    if document_id:
        payload["document_id"] = document_id
    r = requests.post(f"{BASE}/chat/query", headers=headers, data=json.dumps(payload))
    return r.status_code, r.text

if __name__ == '__main__':
    email = 'e2e_user@example.com'
    password = 'Password123!'
    print('Registering...')
    print(register(email, password))
    time.sleep(0.5)
    print('Logging in...')
    token = None
    try:
        token = login(email, password)
        print('Token:', token[:40] + '...')
    except Exception as e:
        print('Login failed:', e)
        exit(1)

    print('Uploading test doc...')
    status, text = upload(token, 'test_e2e.txt', 'This is a short test document about Paris being the capital of France.')
    print('Upload:', status, text)

    print('Querying chat about Paris...')
    status, text = query(token, 'What is the capital of France?')
    print('Query:', status, text)
