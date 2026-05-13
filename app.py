from flask import Flask, request, redirect, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import secrets
import qrcode
import os
import smtplib
import zipfile
from email.message import EmailMessage

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_NAME = "attendance.db"

# ---------------- EMAIL CONFIG ----------------
# IMPORTANT:
# Use your Gmail + App Password
# Generate App Password:
# https://myaccount.google.com/apppasswords

SENDER_EMAIL = "YOUR_EMAIL@gmail.com"
SENDER_PASSWORD = "YOUR_APP_PASSWORD"

# ---------------- DATABASE SETUP ----------------
def init_db():

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # attendance table
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            time TEXT
        )
    """)

    # students table
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

Attached is your personal attendance QR Code.

Please keep it safe and scan it during attendance.

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

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)

        return True

    except Exception as e:
        print("EMAIL ERROR:", e)
        return False

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
    max-width:1000px;
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
    transition:0.3s;
}

button:hover{
    background:#1e3c72;
    transform:scale(1.02);
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

/* TABLE */
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
    color:black;
    background:white;
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

.stats{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
    gap:20px;
    margin-top:20px;
}

.stat-card{
    background:#2a5298;
    color:white;
    padding:25px;
    border-radius:15px;
    text-align:center;
    box-shadow:0px 5px 15px rgba(0,0,0,0.2);
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

# ---------------- ADD SINGLE STUDENT ----------------
@app.route("/add_student", methods=["GET", "POST"])
@login_required
def add_student():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]

        token = secrets.token_hex(8)

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        c.execute(
            "INSERT INTO students (name, email, token) VALUES (?, ?, ?)",
            (name, email, token)
        )

        conn.commit()
        conn.close()

        # QR generation
        base_url = request.host_url + "mark/" + token

        img = qrcode.make(base_url)

        if not os.path.exists("static/qrcodes"):
            os.makedirs("static/qrcodes")

        safe_name = name.replace(" ", "_")

        file_path = f"static/qrcodes/{safe_name}.png"

        img.save(file_path)

        # send email
        send_email(email, name, file_path)

        return f"""
        {STYLE}

        <div class='container'>

        <h1>✅ Student Added</h1>

        <div class='card'>

        <h3>{name}</h3>
        <h3>{email}</h3>

        <center>
        <img src='/{file_path}' width='250'>
        </center>

        </div>

        <a href='/dashboard'>
        <button>Back Dashboard</button>
        </a>

        </div>
        """

    return f"""
    {STYLE}

    <div class='container'>

    <h1>➕ Add Student</h1>

    <form method='POST'>

    <input name='name' placeholder='Student Name' required>

    <input name='email' placeholder='Student Email' required>

    <button type='submit'>Generate QR</button>

    </form>

    </div>
    """

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

        success_count = 0

        for index, row in df.iterrows():

            name = str(row["Name"])
            email = str(row["Email"])

            token = secrets.token_hex(8)

            try:

                c.execute(
                    "INSERT INTO students (name, email, token) VALUES (?, ?, ?)",
                    (name, email, token)
                )

                qr_link = request.host_url + "mark/" + token

                img = qrcode.make(qr_link)

                safe_name = name.replace(" ", "_")

                file_path = f"static/qrcodes/{safe_name}.png"

                img.save(file_path)

                # send email
                send_email(email, name, file_path)

                success_count += 1

            except Exception as e:
                print("ERROR:", e)

        conn.commit()
        conn.close()

        return f"""
        {STYLE}

        <div class='container'>

        <h1>✅ Bulk Upload Complete</h1>

        <div class='card'>

        <h2>{success_count} Students Added Successfully</h2>

        </div>

        <a href='/download_qrs'>
        <button>⬇️ Download All QR Codes ZIP</button>
        </a>

        <a href='/dashboard'>
        <button>⬅️ Back Dashboard</button>
        </a>

        </div>
        """

    return f"""
    {STYLE}

    <div class='container'>

    <h1>📂 Bulk Upload Students</h1>

    <div class='card'>

    <h3>Excel Format Required:</h3>

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

    </div>

    <form method='POST' enctype='multipart/form-data'>

    <input type='file' name='file' required>

    <button type='submit'>Upload Excel</button>

    </form>

    </div>
    """

# ---------------- DOWNLOAD ALL QR ZIP ----------------
@app.route("/download_qrs")
@login_required
def download_qrs():

    zip_name = "all_qr_codes.zip"

    with zipfile.ZipFile(zip_name, "w") as zipf:

        for root, dirs, files in os.walk("static/qrcodes"):

            for file in files:

                file_path = os.path.join(root, file)

                zipf.write(file_path)

    return send_file(zip_name, as_attachment=True)

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

    c.execute("SELECT COUNT(*) FROM students")
    total_students = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM attendance")
    total_attendance = c.fetchone()[0]

    c.execute("SELECT name, time FROM attendance ORDER BY id DESC")
    rows = c.fetchall()

    conn.close()

    html = f"""
    {STYLE}

    <div class='container'>

    <h1>📊 Admin Dashboard</h1>

    <div class='stats'>

        <div class='stat-card'>
            <h2>{total_students}</h2>
            <h3>Total Students</h3>
        </div>

        <div class='stat-card'>
            <h2>{total_attendance}</h2>
            <h3>Total Attendance</h3>
        </div>

    </div>

    <div class='menu'>

    <a href='/add_student'><button>➕ Add Student</button></a>

    <a href='/bulk_upload'><button>📂 Bulk Upload</button></a>

    <a href='/download'><button>⬇️ Download Excel</button></a>

    <a href='/download_qrs'><button>🧾 Download All QRs</button></a>

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
    """

    return html

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
    app.run(host="0.0.0.0", port=5000, debug=True)
