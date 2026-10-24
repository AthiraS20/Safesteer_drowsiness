import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "safesteer.db"
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
UPDATE incidents
SET type = 'Driver Unresponsive'
WHERE type LIKE 'Driver Unresponsive%'
""")

conn.commit()
conn.close()
print("✅ Old incident types normalized.")
