import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "arlo_quotes.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    try:
        with get_conn() as conn:
            c = conn.cursor()

            c.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                phone_number TEXT,
                company_name TEXT,
                client_name TEXT,
                project_name TEXT,
                labour REAL DEFAULT 0,
                materials REAL DEFAULT 0,
                equipment REAL DEFAULT 0,
                other REAL DEFAULT 0,
                overhead_pct REAL DEFAULT 0,
                margin_target REAL DEFAULT 0,
                total_cost REAL NOT NULL,
                price REAL NOT NULL,
                profit REAL NOT NULL,
                margin REAL NOT NULL,
                walkaway REAL NOT NULL
            )
            """)

            c.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON quotes(timestamp)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_phone ON quotes(phone_number)")

            conn.commit()

        logger.info("Database initialized")

    except Exception as e:
        logger.error(f"DB init failed: {e}")
        raise


def save_quote(data: dict):
    try:
        with get_conn() as conn:
            c = conn.cursor()

            c.execute("""
            INSERT INTO quotes (
                timestamp, phone_number, company_name, client_name, project_name,
                labour, materials, equipment, other,
                overhead_pct, margin_target,
                total_cost, price, profit, margin, walkaway
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["timestamp"],
                data.get("phone_number"),
                data.get("company_name"),
                data.get("client_name"),
                data.get("project_name"),
                data.get("labour", 0),
                data.get("materials", 0),
                data.get("equipment", 0),
                data.get("other", 0),
                data.get("overhead_pct", 0),
                data.get("margin_target", 0),
                data["total_cost"],
                data["price"],
                data["profit"],
                data["margin"],
                data["walkaway"]
            ))

            conn.commit()

        logger.info("Quote saved")

    except Exception as e:
        logger.error(f"Save failed: {e}")
        raise


def get_recent_quotes(phone_number=None, limit=5):
    try:
        with get_conn() as conn:
            c = conn.cursor()

            if phone_number:
                c.execute("""
                SELECT timestamp, company_name, client_name, project_name, price, margin
                FROM quotes
                WHERE phone_number = ?
                ORDER BY id DESC
                LIMIT ?
                """, (phone_number, limit))
            else:
                c.execute("""
                SELECT timestamp, company_name, client_name, project_name, price, margin
                FROM quotes
                ORDER BY id DESC
                LIMIT ?
                """, (limit,))

            rows = c.fetchall()

        return [
            {
                "timestamp": r[0],
                "company_name": r[1],
                "client_name": r[2],
                "project_name": r[3],
                "price": r[4],
                "margin": r[5]
            }
            for r in rows
        ]

    except Exception as e:
        logger.error(f"Fetch failed: {e}")
        return []