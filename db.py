# db.py
import sqlite3
from pathlib import Path

# Path to DB file (stored in project root as safesteer.db)
DB_PATH = Path(__file__).resolve().parent / "safesteer.db"

def get_conn():
    """Open DB connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with users + incidents tables"""
    conn = get_conn()
    cur = conn.cursor()

    # Users table (drivers + admin)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            phone TEXT,
            vehicle_no TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','driver')) DEFAULT 'driver',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # Incidents table (allows 'Drowsiness', 'Phone Usage', 'Drowsiness (Mayday)', 'Driver Unresponsive', etc.)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """
    )

    # Ensure existing incidents table does not have restrictive CHECK constraint
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='incidents'")
    row = cur.fetchone()
    if row and row["sql"] and "CHECK" in row["sql"].upper():
        cur.execute("PRAGMA foreign_keys=off;")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS incidents_unconstrained (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            """
        )
        cur.execute(
            "INSERT INTO incidents_unconstrained (id, user_id, type, timestamp) SELECT id, user_id, type, timestamp FROM incidents;"
        )
        cur.execute("DROP TABLE incidents;")
        cur.execute("ALTER TABLE incidents_unconstrained RENAME TO incidents;")
        cur.execute("PRAGMA foreign_keys=on;")

    conn.commit()
    conn.close()
