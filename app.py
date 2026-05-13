from flask import Flask, request, redirect, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import secrets
import qrcode
import os
import smtplib
from email.message import EmailMessage
import zipfile

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_NAME = "attendance.db"

# ---------------- EMAIL CONFIG ----------------
SENDER_EMAIL = "SRolli@seu.edu.ge"
SENDER_PASSWORD = "kqyy xhot chpp qdwj"

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
            email TEXT,
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

# ---------------- EMAIL FUNCTION ----------------
def send_email(receiver_email, student_name, qr_path):

    try:

        msg = EmailMessage()

        msg["Subject"] = "Your Attendance QR Code"
        msg["From"] = SENDER_EMAIL
        msg["To"] = receiver_email

        msg.set_content(f"""
Hello {student_name},

Your attendance QR code is attached.

Regards,
AIMCS
        """)

        with open(qr_path, "rb") as f:
            file_data = f.read()

        msg.add_attachment(
            file_data,
            maintype="image",
            subtype="png",
            filename=os.path.basename(qr_path)
        )

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)

        print("EMAIL SENT:", receiver_email)

    except Exception as e:
        print("EMAIL ERROR:", e)

# ---------------- PROFESSIONAL UI ----------------
STYLE = """
<style>

body{
    margin:0;
    padding:0;
    font-family:Arial;
    background:linear-gradient(135deg,#0f172a,#1e293b);
    color:white;
}

.navbar{
    background:#111827;
    padding:20px;
    text-align:center;
    font-size:28px;
    font-weight:bold;
    letter-spacing:1px;
}

.container{
    width:90%;
    max-width:1200px;
    margin:auto;
    margin-top:30px;
    background:white;
    color:black;
    padding:30px;
    border-radius:20px;
    box-shadow:0px 0px 25px rgba(0,0,0,0.3);
}

h1,h2,h3{
    text-align:center;
}

.card{
    background:#f8fafc;
    padding:25px;
    border-radius:18px;
    margin-top:20px;
    box-shadow:0px 5px 10px rgba(0,0,0,0.08);
}

button{
    width:100%;
    padding:14px;
    border:none;
    border-radius:12px;
    background:#2563eb;
    color:white;
    font-size:16px;
    margin-top:15px;
    cursor:pointer;
    transition:0.3s;
    font-weight:bold;
}

button:hover{
    background:#1d4ed8;
    transform:translateY(-2px);
}

input{
    width:100%;
    padding:14px;
    margin-top:12px;
    border-radius:10px;
    border:1px solid #cbd5e1;
    font-size:16px;
}

table{
    width:100%;
    border-collapse:collapse;
    margin-top:20px;
}

th{
    background:#2563eb;
    color:white;
    padding:14px;
}

td{
    padding:12px;
    border-bottom:1px solid #ddd;
}

.menu{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
    gap:15px;
    margin-top:25px;
}

.stats{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(250px,1fr));
    gap:20px;
}

.stat-card{
    background:#2563eb;
    color:white;
    padding:25px;
    border-radius:18px;
    text-align:center;
}

.success{
    color:green;
    text-align:center;
    font-weight:bold;
}

.error{
    color:red;
    text-align:center;
    font-weight:bold;
}

.footer{
    text-align:center;
    margin-top:30px;
    color:#94a3b8;
}

</style>
"""

# ---------------- HOME ----------------
@app.route("/")
def home():

    return f"""
    {STYLE}

    <div class='navbar'>
        🎓 AIMCS QR Attendance System
    </div>

    <div class='container'>

        <div class='card'>

            <h1>Smart Attendance Management</h1>

            <p style='text-align:center;font-size:18px;'>
            Bulk QR Generation • Email Automation • Attendance Analytics
            </p>

            <a href='/login'>
                <button>🔐 Admin Login</button>
            </a>

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

            login_user(User(1))

            return redirect("/dashboard")

        return f"""
        {STYLE}

        <div class='container'>
            <h2 class='error'>Invalid Credentials</h2>
        </div>
        """

    return f"""
    {STYLE}

    <div class='navbar'>
        🔐 Admin Portal
    </div>

    <div class='container'>

        <div class='card'>

            <h1>Login</h1>

            <form method='POST'>

                <input name='username' placeholder='Username' required>

                <input type='password' name='password' placeholder='Password' required>

                <button type='submit'>Login</button>

            </form>

        </div>

    </div>
    """

# ---------------- LOGOUT ----------------
@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect("/login")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
@login_required
def dashboard():

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM students")
    total_students = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM attendance")
    total_attendance = c.fetchone()[0]

    c.execute("""
        SELECT name, time
        FROM attendance
        ORDER BY id DESC
    """)

    rows = c.fetchall()

    conn.close()

    html = f"""
    {STYLE}

    <div class='navbar'>
        📊 Admin Dashboard
    </div>

    <div class='container'>

        <div class='stats'>

            <div class='stat-card'>
                <h1>{total_students}</h1>
                <h3>Total Students</h3>
            </div>

            <div class='stat-card'>
                <h1>{total_attendance}</h1>
                <h3>Total Attendance</h3>
            </div>

        </div>

        <div class='menu'>

            <a href='/bulk_upload'>
                <button>📂 Bulk Upload Students</button>
            </a>

            <a href='/download'>
                <button>⬇️ Download Attendance Excel</button>
            </a>

            <a href='/download_qrs'>
                <button>🧾 Download QR ZIP</button>
            </a>

            <a href='/analytics'>
                <button>📈 Analytics</button>
            </a>

            <a href='/logout'>
                <button>🚪 Logout</button>
            </a>

        </div>

        <div class='card'>

            <h2>Recent Attendance</h2>

            <table>

                <tr>
                    <th>Name</th>
                    <th>Date</th>
                    <th>Time</th>
                </tr>
    """

    for row in rows:

        name = row[0]
        full_time = row[1]

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

        <div class='footer'>
            AIMCS Professional Attendance System
        </div>

    </div>
    """

    return html

# ---------------- BULK UPLOAD ----------------
@app.route("/bulk_upload", methods=["GET", "POST"])
@login_required
def bulk_upload():

    if request.method == "POST":

        file = request.files["file"]

        df = pd.read_excel(file)

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        if not os.path.exists("static/qrcodes"):
            os.makedirs("static/qrcodes")

        success = 0

        for index, row in df.iterrows():

            name = str(row["Name"]).strip()
            email = str(row["Email"]).strip()

            token = secrets.token_hex(8)

            try:

                c.execute(
                    "INSERT INTO students (name, email, token) VALUES (?, ?, ?)",
                    (name, email, token)
                )

                qr_link = request.host_url + "mark/" + token

                img = qrcode.make(qr_link)

                safe_name = name.replace(" ", "_")

                qr_path = f"static/qrcodes/{safe_name}.png"

                img.save(qr_path)

                # EMAIL SEND
                send_email(email, name, qr_path)

                success += 1

            except Exception as e:
                print("ERROR:", e)

        conn.commit()
        conn.close()

        return f"""
        {STYLE}

        <div class='container'>

            <h1 class='success'>
            ✅ {success} QR Codes Generated & Emails Sent
            </h1>

            <a href='/dashboard'>
                <button>⬅️ Back Dashboard</button>
            </a>

        </div>
        """

    return f"""
    {STYLE}

    <div class='navbar'>
        📂 Bulk Upload
    </div>

    <div class='container'>

        <div class='card'>

            <h2>Upload Excel File</h2>

            <table>

                <tr>
                    <th>Name</th>
                    <th>Email</th>
                </tr>

                <tr>
                    <td>John</td>
                    <td>john@gmail.com</td>
                </tr>

            </table>

            <form method='POST' enctype='multipart/form-data'>

                <input type='file' name='file' required>

                <button type='submit'>
                    🚀 Generate All QR Codes
                </button>

            </form>

        </div>

    </div>
    """

# ---------------- DOWNLOAD QRS ZIP ----------------
@app.route("/download_qrs")
@login_required
def download_qrs():

    zip_name = "all_qrs.zip"

    with zipfile.ZipFile(zip_name, "w") as zipf:

        for root, dirs, files in os.walk("static/qrcodes"):

            for file in files:

                path = os.path.join(root, file)

                zipf.write(path)

    return send_file(zip_name, as_attachment=True)

# ---------------- MARK ATTENDANCE ----------------
@app.route("/mark/<token>")
def mark(token):

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute(
        "SELECT name FROM students WHERE token=?",
        (token,)
    )

    student = c.fetchone()

    if not student:

        conn.close()

        return f"""
        {STYLE}

        <div class='container'>
            <h2 class='error'>Invalid QR</h2>
        </div>
        """

    name = student[0]

    tbilisi_time = datetime.utcnow() + timedelta(hours=4)

    time_string = tbilisi_time.strftime("%Y-%m-%d %H:%M:%S")

    c.execute("""
        SELECT * FROM attendance
        WHERE name=?
        AND date(time)=date('now','+4 hours')
    """, (name,))

    existing = c.fetchone()

    if existing:

        conn.close()

        return f"""
        {STYLE}

        <div class='container'>
            <h2 class='error'>
            ⚠️ Attendance Already Marked Today
            </h2>
        </div>
        """

    c.execute(
        "INSERT INTO attendance (name,time) VALUES (?,?)",
        (name, time_string)
    )

    conn.commit()
    conn.close()

    return f"""
    {STYLE}

    <div class='container'>

        <h1 class='success'>
        ✅ Attendance Marked Successfully
        </h1>

        <div class='card'>

            <h2>{name}</h2>

            <h3>{time_string}</h3>

        </div>

    </div>
    """

# ---------------- DOWNLOAD EXCEL ----------------
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

    c.execute("""
        SELECT name, COUNT(*)
        FROM attendance
        GROUP BY name
    """)

    rows = c.fetchall()

    conn.close()

    html = f"""
    {STYLE}

    <div class='navbar'>
        📈 Analytics
    </div>

    <div class='container'>

        <div class='card'>

            <table>

                <tr>
                    <th>Name</th>
                    <th>Total Attendance</th>
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

            <a href='/dashboard'>
                <button>⬅️ Back Dashboard</button>
            </a>

        </div>

    </div>
    """

    return html

# ---------------- RUN ----------------
if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
