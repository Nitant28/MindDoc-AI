import os
import time
import requests

BASE = 'http://127.0.0.1:8000'
register_url = BASE + '/api/auth/register'
login_url = BASE + '/api/auth/login'
upload_url = BASE + '/api/documents/upload'
list_url = BASE + '/api/documents/list'
edit_url = BASE + '/api/documents/edit'
delete_url = BASE + '/api/documents/delete'
chat_url = BASE + '/api/chat/query'

email = f'test_e2e_{int(time.time())}@example.com'
password = 'password'

print('Registering user', email)
try:
    r = requests.post(register_url, json={'email': email, 'password': password}, timeout=10)
    print('register', r.status_code, r.text)
    if r.status_code != 200:
        r = requests.post(login_url, json={'email': email, 'password': password}, timeout=10)
        print('login', r.status_code, r.text)
    token = r.json().get('access_token')
    headers = {'Authorization': f'Bearer {token}'}

    # Upload a PDF
    print('Uploading sample PDF')
    with open('scripts/sample.pdf','rb') as f:
        files = {'file': ('sample.pdf', f, 'application/pdf')}
        r2 = requests.post(upload_url, files=files, headers=headers, timeout=20)
        print('upload', r2.status_code, r2.text)

    # List documents
    r3 = requests.get(list_url, headers=headers, timeout=10)
    print('list', r3.status_code, r3.text)
    docs = r3.json() if r3.status_code==200 else []
    if docs:
        doc_id = docs[0]['id']
        # Edit filename
        print('Editing document filename')
        r4 = requests.put(f"{BASE}/api/documents/edit/{doc_id}", params={'filename':'renamed.pdf'}, headers=headers, timeout=10)
        print('edit', r4.status_code, r4.text)
        # Chat with document context
        print('Chat using document id')
        r5 = requests.post(chat_url, json={'query': "What's the capital of France?", 'document_id': doc_id}, headers={**headers, 'Content-Type':'application/json'}, timeout=30)
        print('chat doc', r5.status_code, r5.text)
        # Delete
        print('Deleting document')
        r6 = requests.delete(f"{BASE}/api/documents/delete/{doc_id}", headers=headers, timeout=10)
        print('delete', r6.status_code, r6.text)
    else:
        print('No docs to test edit/delete/chat')

except Exception as e:
    print('Error during e2e test', e)
