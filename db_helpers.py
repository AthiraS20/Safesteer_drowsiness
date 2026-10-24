# backend/db_helpers.py
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / "safesteer.db"

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def log_incident(user_id, incident_type):
    """Insert one incident row for given user_id."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO incidents (user_id, type) VALUES (?, ?)", (user_id, incident_type))
    conn.commit()
    conn.close()

def get_incidents_for_user(user_id, limit=50):
    """Return recent incidents for a specific user."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, type, timestamp FROM incidents WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",
        (user_id, limit)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def get_user_by_id(user_id):
    """Fetch one user row by ID."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, email, phone, vehicle_no, role, created_at FROM users WHERE id=?",
        (user_id,)
    )
    row = cur.fetchone()
    conn.close()
    return row

def list_users():
    """Return all users with basic info."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, email, phone, vehicle_no, role, created_at FROM users ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

def list_recent_incidents(limit=20):
    """Return recent incidents across all users."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT incidents.id, incidents.timestamp, incidents.type, "
        "users.id as user_id, users.username, users.vehicle_no "
        "FROM incidents JOIN users ON incidents.user_id = users.id "
        "ORDER BY incidents.timestamp DESC LIMIT ?",
        (limit,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows
