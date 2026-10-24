import sqlite3
import subprocess
import sys
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from db_helpers import (
    list_users,
    list_recent_incidents,
    get_user_by_id,
    get_incidents_for_user,
)
from db import get_conn, init_db

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app, supports_credentials=True)
app.secret_key = "supersecret"  # change in production

# ----------------- INITIALIZE DB -----------------
init_db()

# ----------------- ROUTES -----------------

@app.route("/")
def index():
    return render_template("index.html")  # front login page


# -------- ABOUT PAGE --------
@app.route("/about")
def about():
    return render_template("about.html")


# -------- FORGOT PASSWORD --------
@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    return render_template("forgot_password.html")


# -------- SIGNUP (GET PAGE) --------
@app.route("/signup")
def signup():   # GET route for signup page
    return render_template("signup.html")


# -------- SIGNUP (POST DATA) --------
@app.route("/signup", methods=["POST"])
def signup_post():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    phone = data.get("phone")
    vehicle_no = data.get("vehicle_no")

    if not username or not email or not password or not vehicle_no:
        return jsonify({"success": False, "message": "All required fields must be filled"})

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, email, password_hash, phone, vehicle_no, role) VALUES (?, ?, ?, ?, ?, ?)",
            (username, email, generate_password_hash(password), phone, vehicle_no, "driver"),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "Email already exists"})
    finally:
        conn.close()

    return jsonify({"success": True, "message": "Account created successfully"})


# -------- LOGIN --------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return redirect(url_for("index"))

    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email=?", (email,))
    user = cur.fetchone()
    conn.close()

    if user and check_password_hash(user["password_hash"], password):
        session["user_id"] = user["id"]
        session["role"] = user["role"]

        redirect_url = "/admin" if user["role"] == "admin" else "/dashboard"
        return jsonify({"success": True, "role": user["role"], "redirect": redirect_url})
    else:
        return jsonify({"success": False, "message": "Invalid email or password"})


# -------- LOGOUT --------
@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    if request.method == "POST" and request.is_json:
        return jsonify({"success": True})
    return redirect(url_for("index"))  # go back to login page


# -------- DRIVER DASHBOARD --------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("index"))

    user_id = session["user_id"]
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id, username, email, phone, vehicle_no, role FROM users WHERE id=?", (user_id,))
    user = cur.fetchone()

    cur.execute("SELECT * FROM incidents WHERE user_id=? ORDER BY timestamp DESC", (user_id,))
    incidents = cur.fetchall()

    conn.close()

    return render_template("dashboard.html", user=user, incidents=incidents)


# -------- START MONITORING --------
@app.route("/start_monitoring", methods=["POST"])
def start_monitoring():
    if "user_id" not in session:
        return redirect(url_for("index"))

    user_id = str(session["user_id"])
    subprocess.Popen([sys.executable, "monitor.py", "--user_id", user_id])
    return redirect(url_for("dashboard"))


# -------- ADMIN LOGIN --------
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        return render_template("admin_login.html")

    username = request.form.get("username")
    password = request.form.get("password")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=? AND role='admin'", (username,))
    user = cur.fetchone()
    conn.close()

    if user and check_password_hash(user["password_hash"], password):
        session["user_id"] = user["id"]
        session["role"] = user["role"]
        return redirect(url_for("admin_dashboard"))
    else:
        return render_template("admin_login.html", error="Invalid admin credentials.")


# -------- ADMIN DASHBOARD --------
@app.route("/admin")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("index"))

    users = list_users()
    incidents = list_recent_incidents(10)
    return render_template("admin.html", users=users, incidents=incidents)


# -------- ADMIN: VIEW USERS --------
@app.route("/admin/users")
def admin_users():
    if session.get("role") != "admin":
        return redirect(url_for("index"))

    users = list_users()
    return render_template("admin_users.html", users=users)


# -------- ADMIN: VIEW USER DETAILS --------
@app.route("/admin/users/<int:user_id>")
def admin_user_details(user_id):
    if session.get("role") != "admin":
        return redirect(url_for("index"))

    user = get_user_by_id(user_id)
    incidents = get_incidents_for_user(user_id)
    return render_template("admin_user_details.html", user=user, incidents=incidents)


# -------- ADMIN: VIEW INCIDENTS (ALL USERS) --------
@app.route("/admin/incidents")
def admin_incidents():
    if session.get("role") != "admin":
        return redirect(url_for("index"))

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT incidents.*, users.username, users.vehicle_no "
        "FROM incidents JOIN users ON incidents.user_id = users.id "
        "ORDER BY timestamp DESC"
    )
    incidents = cur.fetchall()
    conn.close()
    return render_template("admin_incidents.html", incidents=incidents)


# ----------------- RUN APP -----------------
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5001))
    app.run(host="127.0.0.1", port=port, debug=True)

