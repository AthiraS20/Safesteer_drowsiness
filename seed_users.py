from werkzeug.security import generate_password_hash
from db import get_conn, init_db

def upsert_user(username, email, raw_password, role, vehicle_no="", phone=""):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, email, password_hash, phone, vehicle_no, role) VALUES (?, ?, ?, ?, ?, ?)",
            (username, email, generate_password_hash(raw_password), phone, vehicle_no, role),
        )
        conn.commit()
        print(f"✅ Inserted: {email} ({role})")
    except Exception as e:
        # likely UNIQUE(email) conflict; update password/fields if needed
        print(f"ℹ Skipped (maybe exists): {email}  -> {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    # Admin (for company)
    upsert_user(
        username="Admin",
        email="admin@safesteer.com",
        raw_password="admin123",
        role="admin",
        vehicle_no=""
    )
    # Demo Driver
    upsert_user(
        username="Demo Driver",
        email="driver@safesteer.com",
        raw_password="1234",
        role="driver",
        vehicle_no="TN01AB1234",
        phone="9876543210"
    )
    print("Done seeding.")
