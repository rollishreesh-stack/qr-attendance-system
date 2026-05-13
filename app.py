from flask import Flask, request, redirect, send_file, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import secrets
import qrcode
import os
import hashlib
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB = "attendance.db"

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            token TEXT UNIQUE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            date TEXT,
            time TEXT,
            status TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ================= LOGIN SYSTEM =================
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
    margin:0;
    font-family:'Segoe UI', sans-serif;
    background: linear-gradient(135deg,#0f172a,#1e3a8a,#2563eb);
    color:#fff;
}

/* MAIN CONTAINER */
.container{
    width:90%;
    max-width:1100px;
    margin:40px auto;
    background: rgba(255,255,255,0.08);
    backdrop-filter: blur(12px);
    border-radius:20px;
    padding:25px;
    box-shadow:0 10px 40px rgba(0,0,0,0.4);
}

/* HEADINGS */
h1,h2,h3{
    text-align:center;
    margin-bottom:15px;
}

/* BUTTONS */
button{
    padding:12px 18px;
    border:none;
    border-radius:12px;
    cursor:pointer;
    background: linear-gradient(45deg,#3b82f6,#06b6d4);
    color:white;
    font-weight:bold;
    transition:0.3s;
}

button:hover{
    transform:scale(1.05);
    box-shadow:0 5px 20px rgba(0,0,0,0.3);
}

/* MENU */
.menu{
    display:flex;
    gap:10px;
    flex-wrap:wrap;
    justify-content:center;
    margin-bottom:20px;
}

/* CARDS */
.card{
    background: rgba(255,255,255,0.12);
    padding:15px;
    border-radius:15px;
    margin:10px 0;
}

/* TABLE */
table{
    width:100%;
    border-collapse:collapse;
    margin-top:20px;
    overflow:hidden;
    border-radius:12px;
}

th{
    background:#2563eb;
    padding:12px;
    text-align:left;
}

td{
    padding:12px;
    background:rgba(255,255,255,0.08);
}

/* LINKS */
a{
    color:#60a5fa;
    text-decoration:none;
    font-weight:bold;
}

a:hover{
    color:white;
}

/* STATUS */
.success{
    color:#22c55e;
    font-weight:bold;
}

.error{
    color:#ef4444;
    font-weight:bold;
}

</style>
"""

# ================= SECURITY (QR ENCRYPTION) =================
def generate_secure_token(name):
    raw = name + str(datetime.utcnow()) + secrets.token_hex(5)
    return hashlib.sha256(raw.encode()).hexdigest()

# ================= HOME =================
@app.route("/")
def home():
    return "<h1>QR Attendance PRO System</h1><a href='/login'>Admin Login</a>"

# ================= ADD STUDENT (QR GENERATION) =================
@app.route("/add_student", methods=["POST"])
@login_required
def add_student():

    name = request.form["name"]
    token = generate_secure_token(name)

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("INSERT INTO students (name, token) VALUES (?,?)", (name, token))
    conn.commit()
    conn.close()

    qr_url = request.host_url + "mark/" + token

    img = qrcode.make(qr_url)

    if not os.path.exists("static"):
        os.makedirs("static")

    path = f"static/{name}.png"
    img.save(path)

    return jsonify({
        "name": name,
        "qr": path,
        "token": token
    })

# ================= MARK ATTENDANCE =================
@app.route("/mark/<token>")
def mark(token):

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT name FROM students WHERE token=?", (token,))
    user = c.fetchone()

    if not user:
        return "Invalid QR"

    name = user[0]

    now = datetime.utcnow() + timedelta(hours=4)

    date = now.date().strftime("%Y-%m-%d")
    time = now.strftime("%H:%M:%S")

    status = "LATE" if now.hour >= 9 else "ON TIME"

    # prevent duplicate
    c.execute("SELECT * FROM attendance WHERE name=? AND date=?", (name, date))
    if c.fetchone():
        return "Already marked today"

    c.execute(
        "INSERT INTO attendance (name, date, time, status) VALUES (?,?,?,?)",
        (name, date, time, status)
    )

    conn.commit()
    conn.close()

    return f"{name} marked {status} at {time}"

# ================= API (MOBILE APP READY) =================
@app.route("/api/attendance")
def api():

    conn = sqlite3.connect(DB)
    df = pd.read_sql_query("SELECT * FROM attendance", conn)
    return jsonify(df.to_dict(orient="records"))

# ================= ATTENDANCE GRAPH =================
@app.route("/graph")
@login_required
def graph():

    conn = sqlite3.connect(DB)
    df = pd.read_sql_query("SELECT name FROM attendance", conn)
    conn.close()

    counts = df["name"].value_counts()

    plt.figure()
    counts.plot(kind="bar")
    plt.title("Attendance Graph")

    file = "static/graph.png"
    plt.savefig(file)

    return send_file(file, mimetype="image/png")

# ================= DASHBOARD =================
@app.route("/dashboard")
@login_required
def dashboard():

    conn = sqlite3.connect(DB)
    df = pd.read_sql_query("SELECT * FROM attendance", conn)
    conn.close()

    html = f"""
{STYLE}

<div class='container'>

<h1>📊 Smart Attendance Dashboard</h1>

<div class='menu'>

<a href='/add_student'><button>➕ Add Student</button></a>
<a href='/graph'><button>📈 Graph</button></a>
<a href='/download'><button>⬇️ Excel</button></a>
<a href='/logout'><button>🚪 Logout</button></a>

</div>

<div class='card'>
<h3>Live Attendance Records</h3>
</div>

<table>
<tr>
<th>Name</th>
<th>Date</th>
<th>Time</th>
<th>Status</th>
</tr>
"""

# ================= EXCEL DOWNLOAD =================
@app.route("/download")
@login_required
def download():

    conn = sqlite3.connect(DB)
    df = pd.read_sql_query("SELECT * FROM attendance", conn)

    file = "attendance.xlsx"
    df.to_excel(file, index=False)

    return send_file(file, as_attachment=True)

# ================= FACE RECOGNITION READY HOOK =================
@app.route("/face")
def face():
    return "Face recognition module ready (connect OpenCV / DeepFace here)"

# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        if request.form["username"] == "admin":
            user = User(1)
            login_user(user)
            return redirect("/dashboard")

    return "<form method='POST'><input name='username'><button>Login</button></form>"

# ================= LOGOUT =================
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
