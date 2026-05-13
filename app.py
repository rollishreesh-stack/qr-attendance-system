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

    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            time TEXT
        )
    """)

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

# ---------------- GLOBAL STYLE ----------------
STYLE = """
<style>

body{
    font-family: Arial;
    background: linear-gradient(135deg,#1e3c72,#2a5298);
    margin:0;
    padding:0;
    color:white;
}

/* MAIN CARD */
.container{
    width:90%;
    max-width:900px;
    margin:auto;
    margin-top:40px;
    background:white;
    color:black;
    padding:30px;
    border-radius:20px;
    box-shadow:0px 0px 20px rgba(0,0,0,0.3);
}

/* HEADINGS */
h1,h2,h3{
    text-align:center;
}

/* INPUTS */
input{
    width:100%;
    padding:12px;
    margin-top:10px;
    border-radius:10px;
    border:1px solid #ccc;
    font-size:16px;
}

/* BUTTONS */
button{
    width:100%;
    padding:12px;
    margin-top:20px;
    background:#2a5298;
    color:white;
    border:none;
    border-radius:10px;
    font-size:16px;
    cursor:pointer;
}

button:hover{
    background:#1e3c72;
}

/* LINKS */
a{
    text-decoration:none;
    color:#2a5298;
    font-weight:bold;
}

/* MENU */
.menu{
    display:flex;
    gap:20px;
    flex-wrap:wrap;
    margin-bottom:20px;
}

/* CARDS */
.card{
    background:#f5f5f5;
    padding:20px;
    border-radius:15px;
    margin-top:20px;
}

/* TABLE FIX (IMPORTANT) */
table{
    width:100%;
    border-collapse:collapse;
    margin-top:20px;
    background:white;
}

th{
    background:#2a5298;
    color:white;
    padding:12px;
    text-align:left;
}

td{
    padding:12px;
    border-bottom:1px solid #ddd;
    color:black;   /* ✅ FIX: ensures text is visible */
    background:white;  /* ✅ FIX: prevents blending */
}

/* SUCCESS / ERROR */
.success{
    color:green;
    font-weight:bold;
    text-align:center;
}

.error{
    color:red;
    font-weight:bold;
    text-align:center;
}

img{
    border-radius:20px;
    margin-top:20px;
}

</style>
"""

# ---------------- HOME ----------------
@app.route("/")
def home():

    return f"""
    {STYLE}

    <div class='container'>

    <h1>🎓 PRO QR Attendance System</h1>

    <div class='card'>

    <h3>Smart Attendance Platform</h3>

    <p>
    Scan QR codes to mark attendance instantly.
    </p>

    <center>
    <a href='/login'>
    <button>Admin Login</button>
    </a>
    </center>

    </div>

    </div>
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

        return f"""
        {STYLE}

        <div class='container'>

        <h2 class='error'>Invalid Username or Password</h2>

        <a href='/login'>
        <button>Try Again</button>
        </a>

        </div>
        """

    return f"""
    {STYLE}

    <div class='container'>

    <h1>🔐 Admin Login</h1>

    <form method='POST'>

    <input name='username' placeholder='Username' required>

    <input type='password' name='password' placeholder='Password' required>

    <button type='submit'>Login</button>

    </form>

    </div>
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
        {STYLE}

        <div class='container'>

        <h1>✅ Student Added</h1>

        <div class='card'>

        <h3>{name}</h3>

        <center>
        <img src='/{file_path}' width='250'>
        </center>

        </div>

        <a href='/dashboard'>
        <button>Back to Dashboard</button>
        </a>

        </div>
        """

    return f"""
    {STYLE}

    <div class='container'>

    <h1>➕ Add Student</h1>

    <form method='POST'>

    <input name='name' placeholder='Student Name' required>

    <button type='submit'>Generate QR</button>

    </form>

    </div>
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

        return f"""
        {STYLE}

        <div class='container'>

        <h2 class='error'>❌ Invalid QR Code</h2>

        </div>
        """

    name = student[0]

    tbilisi_time = datetime.utcnow() + timedelta(hours=4)

    time_string = tbilisi_time.strftime("%Y-%m-%d %H:%M:%S")

    c.execute("""
        SELECT * FROM attendance
        WHERE name = ?
        AND date(time) = date('now', '+4 hours')
    """, (name,))

    existing = c.fetchone()

    if existing:
        conn.close()

        return f"""
        {STYLE}

        <div class='container'>

        <h2 class='error'>
        ⚠️ {name} already marked attendance today!
        </h2>

        </div>
        """

    c.execute(
        "INSERT INTO attendance (name, time) VALUES (?, ?)",
        (name, time_string)
    )

    conn.commit()
    conn.close()

    return f"""
    {STYLE}

    <div class='container'>

    <h1 class='success'>✅ Attendance Marked</h1>

    <div class='card'>

    <h3>Name: {name}</h3>

    <h3>Time: {time_string}</h3>

    </div>

    </div>
    """

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
@login_required
def dashboard():

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT name, time FROM attendance ORDER BY id DESC")
    rows = c.fetchall()

    conn.close()

    html = f"""
    {STYLE}

    <div class='container'>

    <h1>📊 Admin Dashboard</h1>

    <div class='menu'>

    <a href='/add_student'><button>➕ Add Student</button></a>
    <a href='/download'><button>⬇️ Download Excel</button></a>
    <a href='/analytics'><button>📈 Analytics</button></a>
    <a href='/logout'><button>🚪 Logout</button></a>

    </div>

    <table>

    <tr>
        <th>Name</th>
        <th>Date</th>
        <th>Time</th>
    </tr>
    """

    for row in rows:
        name = row[0]
        full_time = row[1]   # "2026-05-13 18:45:12"

        # split into date + time
        date_part = full_time.split(" ")[0]
        time_part = full_time.split(" ")[1]

        html += f"""
        <tr>
            <td>{name}</td>
            <td>{date_part}</td>
            <td>{time_part}</td>
        </tr>
        """

    html += """
    </table>

    </div>
    """

    return html

# ---------------- DOWNLOAD ----------------
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
    {STYLE}

    <div class='container'>

    <h1>📈 Attendance Analytics</h1>

    <div class='card'>

    <h2>Total Attendance Entries: {total}</h2>

    </div>

    <table>

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

    html += """
    </table>

    <br>

    <a href='/dashboard'>
    <button>⬅️ Back Dashboard</button>
    </a>

    </div>
    """

    return html

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
