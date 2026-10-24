# migrate_incidents.py
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / "safesteer.db"

def migrate():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys=off;")

    # Create new table with no restrictive CHECK so we can store Driver Unresponsive etc.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS incidents_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
    """)

    # If old incidents table exists, copy existing rows
    try:
        cur.execute("INSERT INTO incidents_new (id, user_id, type, timestamp) SELECT id, user_id, type, timestamp FROM incidents;")
    except Exception:
        # ignore if old table doesn't exist
        pass

    cur.execute("DROP TABLE IF EXISTS incidents;")
    cur.execute("ALTER TABLE incidents_new RENAME TO incidents;")
    conn.commit()
    conn.close()
    print("Migration complete: incidents table replaced (now accepts any text in type).")

if __name__ == "__main__":
    migrate()
