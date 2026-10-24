import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "safesteer.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 1. Rename old table
cur.execute("ALTER TABLE incidents RENAME TO incidents_old")

# 2. Create new incidents table with localtime timestamp
cur.execute("""
CREATE TABLE incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    type TEXT CHECK(type IN ('Drowsiness','Phone Usage','Driver Unresponsive')) NOT NULL,
    timestamp DATETIME DEFAULT (datetime('now','localtime')),
    FOREIGN KEY(user_id) REFERENCES users(id)
)
""")

# 3. Copy old data into new table
cur.execute("""
INSERT INTO incidents (id, user_id, type, timestamp)
SELECT id, user_id, type, timestamp FROM incidents_old
""")

# 4. Drop old table
cur.execute("DROP TABLE incidents_old")

conn.commit()
conn.close()
print("✅ Migration complete. Incidents now use localtime timestamps.")
