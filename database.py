import sqlite3
from datetime import datetime

DB_PATH = "arlo.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

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
        phone TEXT NOT NULL,
        ref TEXT NOT NULL,
        direct_cost REAL NOT NULL,
        protected_cost REAL NOT NULL,
        price REAL NOT NULL,
        profit REAL NOT NULL,
        margin REAL NOT NULL,
        raw_input TEXT,
        timestamp TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def get_or_create_user(phone: str):
    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE phone = ?", (phone,))
    row = c.fetchone()

    if row is None:
        now = datetime.now().isoformat()
        c.execute(
            "INSERT INTO users (phone, industry, created_at) VALUES (?, ?, ?)",
            (phone, None, now)
        )
        conn.commit()
        c.execute("SELECT * FROM users WHERE phone = ?", (phone,))
        row = c.fetchone()

    conn.close()
    return dict(row)


def update_user_industry(phone: str, industry: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "UPDATE users SET industry = ? WHERE phone = ?",
        (industry, phone)
    )
    conn.commit()
    conn.close()


def save_quote(phone: str, ref: str, direct_cost: float, protected_cost: float,
               price: float, profit: float, margin: float, raw_input: str):
    conn = get_conn()
    c = conn.cursor()
    ts = datetime.now().isoformat()

    c.execute("""
    INSERT INTO quotes (
        phone, ref, direct_cost, protected_cost, price, profit, margin, raw_input, timestamp
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        phone, ref, direct_cost, protected_cost, price, profit, margin, raw_input, ts
    ))

    conn.commit()
    conn.close()


def get_recent_quotes(phone: str, limit: int = 3):
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    SELECT ref, direct_cost, protected_cost, price, profit, margin, raw_input, timestamp
    FROM quotes
    WHERE phone = ?
    ORDER BY timestamp DESC
    LIMIT ?
    """, (phone, limit))

    rows = c.fetchall()
    conn.close()

    return [dict(r) for r in rows]