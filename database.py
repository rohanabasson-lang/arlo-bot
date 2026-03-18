import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔥 FORCE NEW DB (avoids old schema issues)
DB_PATH = "arlo_quotes_v2.db"


def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    with get_conn() as conn:
        c = conn.cursor()

        c.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            project_name TEXT,
            labour REAL,
            materials REAL,
            equipment REAL,
            other REAL,
            overhead_pct REAL,
            margin_target REAL,
            total_cost REAL,
            price REAL,
            profit REAL,
            margin REAL,
            walkaway REAL
        )
        """)

        conn.commit()


def save_quote(data: dict):
    with get_conn() as conn:
        c = conn.cursor()

        c.execute("""
        INSERT INTO quotes (
            timestamp, project_name,
            labour, materials, equipment, other,
            overhead_pct, margin_target,
            total_cost, price, profit, margin, walkaway
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["timestamp"],
            data.get("project_name"),
            data.get("labour"),
            data.get("materials"),
            data.get("equipment"),
            data.get("other"),
            data.get("overhead_pct"),
            data.get("margin_target"),
            data["total_cost"],
            data["price"],
            data["profit"],
            data["margin"],
            data["walkaway"]
        ))

        conn.commit()


def get_recent_quotes(limit=5):
    with get_conn() as conn:
        c = conn.cursor()

        c.execute("""
        SELECT timestamp, project_name, price, margin
        FROM quotes
        ORDER BY id DESC
        LIMIT ?
        """, (limit,))

        rows = c.fetchall()

    return [
        {
            "timestamp": r[0],
            "project_name": r[1],
            "price": r[2],
            "margin": r[3]
        }
        for r in rows
    ]