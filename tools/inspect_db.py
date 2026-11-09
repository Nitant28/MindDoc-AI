import sqlite3

conn = sqlite3.connect('minddoc.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('TABLES:', cur.fetchall())
for q,label in [
    ("SELECT id,email,tenant_id FROM users", 'USERS'),
    ("SELECT id,name FROM tenants", 'TENANTS'),
    ("SELECT id,filename,tenant_id FROM documents", 'DOCS'),
]:
    try:
        cur.execute(q)
        print(label+':', cur.fetchall())
    except Exception as e:
        print(label+' ERROR:', e)
conn.close()
