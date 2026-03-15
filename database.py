import sqlite3
from datetime import datetime

DB_PATH = "pricing.db"


def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():

    conn = get_conn()

    c = conn.cursor()

    c.execute("""

    CREATE TABLE IF NOT EXISTS quotes(

        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        ref TEXT,
        from_number TEXT,
        text TEXT,
        quote REAL,
        cost REAL,
        margin REAL

    )

    """)

    conn.commit()

    return conn


def add_quote(conn, data):

    c = conn.cursor()

    c.execute("""

    INSERT INTO quotes(
    ts, ref, from_number, text, quote, cost, margin)

    VALUES (?,?,?,?,?,?,?)

    """, (

        datetime.now().isoformat(),
        data["ref"],
        data["from"],
        data["text"],
        data["quote"],
        data["cost"],
        data["margin"]

    ))

    conn.commit()