import sqlite3
from datetime import datetime

DB_PATH = "arlo.db"

def get_conn():
return sqlite3.connect(DB_PATH)

def init_db():
conn = get_conn()
c = conn.cursor()

```
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    phone TEXT PRIMARY KEY,
    industry TEXT,
    created_at TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT,
    ref TEXT,
    cost REAL,
    price REAL,
    profit REAL,
    timestamp TEXT
)
""")

conn.commit()
conn.close()
```

def get_or_create_user(phone):

```
conn = get_conn()
c = conn.cursor()

c.execute("SELECT phone FROM users WHERE phone=?", (phone,))
user = c.fetchone()

if not user:
    now = datetime.now().isoformat()

    c.execute(
        "INSERT INTO users (phone, created_at) VALUES (?,?)",
        (phone, now)
    )

    conn.commit()

conn.close()
```

def save_quote(phone, ref, cost, price, profit):

```
conn = get_conn()
c = conn.cursor()

now = datetime.now().isoformat()

c.execute(
    "INSERT INTO quotes (phone, ref, cost, price, profit, timestamp) VALUES (?,?,?,?,?,?)",
    (phone, ref, cost, price, profit, now)
)

conn.commit()
conn.close()
```

def get_recent_quotes(phone, limit=3):

```
conn = get_conn()
c = conn.cursor()

c.execute(
    "SELECT ref, price, timestamp FROM quotes WHERE phone=? ORDER BY timestamp DESC LIMIT ?",
    (phone, limit)
)

rows = c.fetchall()

conn.close()

return rows
```
