from flask import Flask, request, redirect, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import secrets
import qrcode
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_NAME = "attendance.db"

# ---------------- DATABASE SETUP ----------------
def init_db():

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Attendance table
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            time TEXT
        )
    """)

    # Student table
    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            token TEXT UNIQUE
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
    <h1>PRO QR Attendance System</h1>

    <p>Scan QR to mark attendance</p>

    <br>

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

        return "Invalid username or password"

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

    return redirect("/login")

# ---------------- ADD STUDENT ----------------
@app.route("/add_student", methods=["GET", "POST"])
@login_required
def add_student():

    if request.method == "POST":

        name = request.form["name"]

        token = secrets.token_hex(8)

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        c.execute(
            "INSERT INTO students (name, token) VALUES (?, ?)",
            (name, token)
        )

        conn.commit()
        conn.close()

        # Generate QR
        base_url = request.host_url + "mark/" + token

        img = qrcode.make(base_url)

        if not os.path.exists("static"):
            os.makedirs("static")

        file_path = f"static/{name}.png"

        img.save(file_path)

        return f"""
        <h2>Student Added Successfully</h2>

        <p>Name: {name}</p>

        <p>QR Generated:</p>

        <img src='/{file_path}' width='250'>
        """

    return """
    <h2>Add Student</h2>

    <form method="POST">

        <input name="name" placeholder="Student Name" required>

        <br><br>

        <button type="submit">Generate QR</button>

    </form>
    """

# ---------------- MARK ATTENDANCE ----------------
@app.route("/mark/<token>")
def mark(token):

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute(
        "SELECT name FROM students WHERE token = ?",
        (token,)
    )

    student = c.fetchone()

    if not student:
        conn.close()
        return "Invalid QR code"

    name = student[0]

    # Georgia Time UTC+4
    tbilisi_time = datetime.utcnow() + timedelta(hours=4)

    time_string = tbilisi_time.strftime("%Y-%m-%d %H:%M:%S")

    # Prevent duplicate attendance same day
    c.execute("""
        SELECT * FROM attendance
        WHERE name = ?
        AND date(time) = date('now', '+4 hours')
    """, (name,))

    existing = c.fetchone()

    if existing:
        conn.close()
        return f"{name} already marked attendance today!"

    # Save attendance
    c.execute(
        "INSERT INTO attendance (name, time) VALUES (?, ?)",
        (name, time_string)
    )

    conn.commit()
    conn.close()

    return f"""
    <h2>Attendance Marked Successfully</h2>

    <p>Name: {name}</p>

    <p>Time: {time_string}</p>
    """

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
@login_required
def dashboard():

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute(
        "SELECT name, time FROM attendance ORDER BY id DESC"
    )

    rows = c.fetchall()

    conn.close()

    html = """
    <h1>Admin Dashboard</h1>

    <a href='/add_student'>Add Student + Generate QR</a>

    <br><br>

    <a href='/download'>Download Excel Report</a>

    <br><br>

    <a href='/analytics'>Attendance Analytics</a>

    <br><br>

    <a href='/logout'>Logout</a>

    <br><br>

    <table border='1' cellpadding='10'>

    <tr>
        <th>Name</th>
        <th>Time</th>
    </tr>
    """

    for row in rows:

        html += f"""
        <tr>
            <td>{row[0]}</td>
            <td>{row[1]}</td>
        </tr>
        """

    html += "</table>"

    return html

# ---------------- EXCEL DOWNLOAD ----------------
@app.route("/download")
@login_required
def download():

    conn = sqlite3.connect(DB_NAME)

    df = pd.read_sql_query(
        "SELECT * FROM attendance",
        conn
    )

    file_name = "attendance.xlsx"

    df.to_excel(file_name, index=False)

    conn.close()

    return send_file(file_name, as_attachment=True)

# ---------------- ANALYTICS ----------------
@app.route("/analytics")
@login_required
def analytics():

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM attendance")
    total = c.fetchone()[0]

    c.execute("""
        SELECT name, COUNT(*)
        FROM attendance
        GROUP BY name
    """)

    rows = c.fetchall()

    conn.close()

    html = f"""
    <h1>Attendance Analytics</h1>

    <h3>Total Attendance Entries: {total}</h3>

    <table border='1' cellpadding='10'>

    <tr>
        <th>Name</th>
        <th>Total Count</th>
    </tr>
    """

    for row in rows:

        html += f"""
        <tr>
            <td>{row[0]}</td>
            <td>{row[1]}</td>
        </tr>
        """

    html += "</table>"

    return html

# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
