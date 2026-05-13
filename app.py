from flask import Flask, request, redirect
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_NAME = "attendance.db"

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            time TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- LOGIN SYSTEM ----------------
login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# ---------------- HOME ----------------
@app.route("/")
def home():
    return """
    <h2>QR Attendance System</h2>
    <p>Scan QR to mark attendance</p>
    <a href='/login'>Admin Login</a>
    """

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":

            user = User(1)
            login_user(user)

            return redirect("/dashboard")

        return "Invalid login"

    return """
    <h2>Admin Login</h2>

    <form method="POST">
        <input name="username" placeholder="Username" required>
        <br><br>

        <input type="password" name="password" placeholder="Password" required>
        <br><br>

        <button type="submit">Login</button>
    </form>
    """

# ---------------- LOGOUT ----------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return "Logged out"

# ---------------- MARK ATTENDANCE ----------------
@app.route("/mark")
def mark():

    name = request.args.get("name")

    if not name:
        return "No name provided"

    tbilisi_time = datetime.utcnow() + timedelta(hours=4)

    time_string = tbilisi_time.strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        SELECT * FROM attendance
        WHERE name = ? AND date(time) = date('now','+4 hours')
    """, (name,))

    existing = c.fetchone()

    if existing:
        conn.close()
        return f"{name} already marked attendance today!"

    c.execute(
        "INSERT INTO attendance (name, time) VALUES (?, ?)",
        (name, time_string)
    )

    conn.commit()
    conn.close()

    return f"Attendance marked for {name} at {time_string}"

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
@login_required
def dashboard():

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT name, time FROM attendance ORDER BY id DESC")

    rows = c.fetchall()

    conn.close()

    html = """
    <h2>Admin Dashboard</h2>

    <a href='/logout'>Logout</a>
    <br><br>

    <table border='1' cellpadding='10'>
    <tr>
        <th>Name</th>
        <th>Time</th>
    </tr>
    """

    for r in rows:
        html += f"""
        <tr>
            <td>{r[0]}</td>
            <td>{r[1]}</td>
        </tr>
        """

    html += "</table>"

    return html

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

