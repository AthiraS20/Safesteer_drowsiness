import os
import sys
import json
import time
import signal
import sqlite3
import threading
import subprocess
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

# ----------------- MONITOR PROCESS MANAGEMENT -----------------
active_monitors = {}
PID_STORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".active_monitors.json")

def _load_pids():
    if os.path.exists(PID_STORE_FILE):
        try:
            with open(PID_STORE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_pid(user_id, pid):
    pids = _load_pids()
    pids[str(user_id)] = pid
    try:
        with open(PID_STORE_FILE, "w") as f:
            json.dump(pids, f)
    except Exception:
        pass

def _get_saved_pid(user_id):
    pids = _load_pids()
    return pids.get(str(user_id))

def _get_all_saved_pids():
    return _load_pids()

def _remove_saved_pid(user_id):
    pids = _load_pids()
    if str(user_id) in pids:
        del pids[str(user_id)]
        try:
            with open(PID_STORE_FILE, "w") as f:
                json.dump(pids, f)
        except Exception:
            pass

def _clear_all_saved_pids():
    if os.path.exists(PID_STORE_FILE):
        try:
            os.remove(PID_STORE_FILE)
        except Exception:
            pass

def _kill_pid_tree(pid):
    if not pid:
        return
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, check=False)
        else:
            try:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.3)
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    except Exception as e:
        print(f"[SafeSteer] Error terminating PID {pid}: {e}")

def is_monitoring_active(user_id):
    """Check if monitoring process is currently running for given user"""
    u_str = str(user_id)
    proc = active_monitors.get(u_str)
    if proc is not None and proc.poll() is None:
        return True
    saved_pid = _get_saved_pid(u_str)
    if saved_pid:
        if sys.platform == "win32":
            try:
                res = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {saved_pid}"],
                    capture_output=True,
                    text=True
                )
                if str(saved_pid) in res.stdout:
                    return True
            except Exception:
                pass
        else:
            try:
                os.kill(saved_pid, 0)
                return True
            except OSError:
                pass
        _remove_saved_pid(u_str)
    return False

def stop_monitoring(user_id=None):
    """Stops the monitoring process for a user or for all users (e.g. on driver logout)"""
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. Write stop flag signal file(s) for monitor.py loop detection
    if user_id:
        flag_file = os.path.join(base_dir, f".monitor_stop_{user_id}")
        try:
            with open(flag_file, "w") as f:
                f.write("stop")
        except Exception:
            pass
    else:
        flag_file = os.path.join(base_dir, ".monitor_stop_all")
        try:
            with open(flag_file, "w") as f:
                f.write("stop")
        except Exception:
            pass

    # 2. Gather target processes to terminate
    targets = []
    if user_id:
        u_str = str(user_id)
        if u_str in active_monitors:
            targets.append((u_str, active_monitors.pop(u_str)))
        saved_pid = _get_saved_pid(u_str)
        if saved_pid:
            targets.append((u_str, saved_pid))
    else:
        for u_str, proc in list(active_monitors.items()):
            targets.append((u_str, proc))
        active_monitors.clear()
        for u_str, pid in _get_all_saved_pids().items():
            targets.append((u_str, pid))
        _clear_all_saved_pids()

    # 3. Terminate target processes and their subprocess trees
    for u_str, item in targets:
        pid = None
        if hasattr(item, "pid"):
            if item.poll() is None:
                pid = item.pid
                try:
                    item.terminate()
                except Exception:
                    pass
        elif isinstance(item, int):
            pid = item

        if pid:
            _kill_pid_tree(pid)
            _remove_saved_pid(u_str)

    # 4. On Windows, close any orphaned OpenCV "Driver Monitoring System" window as failsafe
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/FI", "WINDOWTITLE eq Driver Monitoring System*"],
                capture_output=True,
                check=False
            )
        except Exception:
            pass

    # 5. Background cleanup of flag files
    def _cleanup_flags():
        time.sleep(1)
        try:
            for fname in os.listdir(base_dir):
                if fname.startswith(".monitor_stop_"):
                    try:
                        os.remove(os.path.join(base_dir, fname))
                    except Exception:
                        pass
        except Exception:
            pass
    threading.Thread(target=_cleanup_flags, daemon=True).start()

def start_monitoring_process(user_id):
    """Starts the monitor process for a user, stopping any existing monitor first."""
    u_str = str(user_id)
    stop_monitoring(u_str)
    time.sleep(0.3)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    flag_file = os.path.join(base_dir, f".monitor_stop_{u_str}")
    all_flag = os.path.join(base_dir, ".monitor_stop_all")
    for f in (flag_file, all_flag):
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

    proc = subprocess.Popen([sys.executable, "monitor.py", "--user_id", u_str])
    active_monitors[u_str] = proc
    _save_pid(u_str, proc.pid)
    return proc

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

    if request.is_json:
        data = request.get_json() or {}
        email = data.get("email")
        password = data.get("password")
    else:
        email = request.form.get("email")
        password = request.form.get("password")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email=?", (email,))
    user = cur.fetchone()
    conn.close()

    if user and check_password_hash(user["password_hash"], password):
        stop_monitoring()  # Stop any stale monitor processes before new session
        session["user_id"] = user["id"]
        session["role"] = user["role"]

        redirect_url = "/admin" if user["role"] == "admin" else "/dashboard"
        if request.is_json:
            return jsonify({"success": True, "role": user["role"], "redirect": redirect_url})
        return redirect(redirect_url)
    else:
        if request.is_json:
            return jsonify({"success": False, "message": "Invalid email or password"})
        return render_template("index.html", error="Invalid email or password")


# -------- LOGOUT --------
@app.route("/logout", methods=["GET", "POST"])
def logout():
    user_id = session.get("user_id")
    if user_id:
        stop_monitoring(str(user_id))
    else:
        stop_monitoring()  # Stop any active monitors
    session.clear()
    if request.method == "POST" and request.is_json:
        return jsonify({"success": True, "message": "Logged out and monitoring stopped"})
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

    is_monitoring = is_monitoring_active(user_id)

    return render_template("dashboard.html", user=user, incidents=incidents, is_monitoring=is_monitoring)


# -------- START MONITORING --------
@app.route("/start_monitoring", methods=["POST"])
def start_monitoring():
    if "user_id" not in session:
        return redirect(url_for("index"))

    user_id = str(session["user_id"])
    start_monitoring_process(user_id)
    if request.is_json:
        return jsonify({"success": True, "message": "Monitoring started"})
    return redirect(url_for("dashboard"))


# -------- STOP MONITORING --------
@app.route("/stop_monitoring", methods=["POST", "GET"])
def stop_monitoring_route():
    if "user_id" not in session:
        return redirect(url_for("index"))

    user_id = str(session["user_id"])
    stop_monitoring(user_id)
    if request.is_json:
        return jsonify({"success": True, "message": "Monitoring stopped"})
    return redirect(url_for("dashboard"))


# -------- MONITORING STATUS API --------
@app.route("/monitoring_status")
def monitoring_status():
    if "user_id" not in session:
        return jsonify({"active": False})
    user_id = str(session["user_id"])
    return jsonify({"active": is_monitoring_active(user_id)})


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

