import sqlite3

DB_PATH = "pricing_construction.db"


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT UNIQUE
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS quotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        roof_m2 REAL,
        fascia_m REAL,
        barge_m REAL,
        quote REAL,
        total_cost REAL,
        margin REAL,
        original_text TEXT
    )
    """)

    conn.commit()
    conn.close()


def get_or_create_user(phone):
    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT id FROM users WHERE phone=?", (phone,))
    row = c.fetchone()

    if row:
        user_id = row[0]
    else:
        c.execute("INSERT INTO users (phone) VALUES (?)", (phone,))
        conn.commit()
        user_id = c.lastrowid

    conn.close()
    return user_id


def save_quote(user_id, roof_m2, fascia_m, barge_m, quote, total_cost, margin, original_text):
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    INSERT INTO quotes (
        user_id,
        roof_m2,
        fascia_m,
        barge_m,
        quote,
        total_cost,
        margin,
        original_text
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        roof_m2,
        fascia_m,
        barge_m,
        quote,
        total_cost,
        margin,
        original_text
    ))

    conn.commit()
    conn.close()


def get_recent_quotes(limit=10):
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    SELECT ts, roof_m2, fascia_m, barge_m, quote, margin
    FROM quotes
    ORDER BY ts DESC
    LIMIT ?
    """, (limit,))

    rows = c.fetchall()
    conn.close()

    return rows