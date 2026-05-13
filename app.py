from flask import Flask, request, redirect, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import sqlite3
from datetime import datetime, timedelta
import qrcode
import secrets
import os
import smtplib
from email.message import EmailMessage
import pandas as pd
import zipfile

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_NAME = "attendance.db"

# =====================================================
# EMAIL CONFIG
# =====================================================
# IMPORTANT:
# 1. Enable 2-Step Verification in Gmail
# 2. Generate App Password:
# https://myaccount.google.com/apppasswords
# 3. Paste credentials below

SENDER_EMAIL = "SRolli@seu.edu.ge"
SENDER_PASSWORD = "mxmjdkiuplsclcjy"

# =====================================================
# DATABASE SETUP
# =====================================================
def init_db():

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        token TEXT UNIQUE
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS attendance(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        time TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# =====================================================
# LOGIN SYSTEM
# =====================================================
login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):

    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):

    return User(user_id)

# =====================================================
# SEND EMAIL FUNCTION
# =====================================================
def send_email(receiver_email, student_name, qr_path):

    try:

        print(f"Sending email to {receiver_email}")

        msg = EmailMessage()

        msg["Subject"] = "Your Attendance QR Code"
        msg["From"] = SENDER_EMAIL
        msg["To"] = receiver_email

        msg.set_content(f"""
Hello {student_name},

Your attendance QR code is attached.

Please scan it during attendance.

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

        server = smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465
        )

        server.login(
            SENDER_EMAIL,
            SENDER_PASSWORD
        )

        server.send_message(msg)

        server.quit()

        print(f"SUCCESS: Email sent to {receiver_email}")

        return True

    except Exception as e:

        print("EMAIL FAILED")
        print(e)

        return False

# =====================================================
# MODERN PROFESSIONAL UI
# =====================================================
STYLE = """
<style>

*{
    margin:0;
    padding:0;
    box-sizing:border-box;
}

body{
    font-family:Arial;
    background:#0f172a;
    color:white;
}

.navbar{
    background:#111827;
    padding:22px;
    text-align:center;
    font-size:28px;
    font-weight:bold;
    box-shadow:0 4px 10px rgba(0,0,0,0.3);
}

.container{
    width:92%;
    max-width:1200px;
    margin:auto;
    margin-top:35px;
    margin-bottom:40px;
}

.card{
    background:white;
    color:black;
    padding:30px;
    border-radius:22px;
    margin-top:25px;
    box-shadow:0 10px 25px rgba(0,0,0,0.25);
}

.hero{
    text-align:center;
    padding:45px;
}

.hero h1{
    font-size:50px;
    color:#2563eb;
}

.hero p{
    margin-top:15px;
    font-size:18px;
    color:#475569;
}

textarea{
    width:100%;
    height:260px;
    margin-top:20px;
    border-radius:15px;
    border:1px solid #cbd5e1;
    padding:18px;
    font-size:16px;
    resize:none;
}

button{
    width:100%;
    padding:16px;
    border:none;
    border-radius:14px;
    background:#2563eb;
    color:white;
    font-size:17px;
    font-weight:bold;
    margin-top:20px;
    cursor:pointer;
    transition:0.3s;
}

button:hover{
    background:#1d4ed8;
    transform:translateY(-2px);
}

.menu{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(250px,1fr));
    gap:18px;
    margin-top:25px;
}

.stats{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(250px,1fr));
    gap:20px;
}

.stat-card{
    background:linear-gradient(135deg,#2563eb,#1e40af);
    padding:30px;
    border-radius:20px;
    text-align:center;
}

.stat-card h1{
    font-size:42px;
}

table{
    width:100%;
    border-collapse:collapse;
    margin-top:20px;
}

th{
    background:#2563eb;
    color:white;
    padding:15px;
}

td{
    padding:14px;
    border-bottom:1px solid #e2e8f0;
    color:black;
}

.success{
    color:green;
    font-weight:bold;
    text-align:center;
    font-size:24px;
}

.error{
    color:red;
    font-weight:bold;
    text-align:center;
    font-size:24px;
}

.footer{
    text-align:center;
    margin-top:35px;
    color:#94a3b8;
}

.info-box{
    background:#eff6ff;
    padding:20px;
    border-radius:15px;
    margin-top:20px;
    color:black;
}

</style>
"""

# =====================================================
# HOME
# =====================================================
@app.route("/")
def home():

    return f"""
    {STYLE}

    <div class='navbar'>
        🎓 AIMCS QR Attendance System
    </div>

    <div class='container'>

        <div class='card hero'>

            <h1>Professional Attendance Platform</h1>

            <p>
            Bulk QR Generation • Smart Analytics • Auto Email System
            </p>

            <a href='/login'>
                <button>
                    🔐 Admin Login
                </button>
            </a>

        </div>

    </div>
    """

# =====================================================
# LOGIN
# =====================================================
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":

            login_user(User(1))

            return redirect("/dashboard")

    return f"""
    {STYLE}

    <div class='navbar'>
        🔐 Admin Login
    </div>

    <div class='container'>

        <div class='card'>

            <h1 style='text-align:center;'>Login</h1>

            <form method='POST'>

                <input
                    name='username'
                    placeholder='Username'
                    style='width:100%;padding:15px;margin-top:20px;border-radius:12px;border:1px solid #ccc;'
                    required
                >

                <input
                    type='password'
                    name='password'
                    placeholder='Password'
                    style='width:100%;padding:15px;margin-top:20px;border-radius:12px;border:1px solid #ccc;'
                    required
                >

                <button type='submit'>
                    Login
                </button>

            </form>

        </div>

    </div>
    """

# =====================================================
# LOGOUT
# =====================================================
@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect("/login")

# =====================================================
# DASHBOARD
# =====================================================
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
    SELECT name,time
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

            <a href='/bulk_generate'>
                <button>
                    🚀 Bulk QR Generator
                </button>
            </a>

            <a href='/download'>
                <button>
                    ⬇ Download Attendance Excel
                </button>
            </a>

            <a href='/download_qrs'>
                <button>
                    🧾 Download All QR Codes ZIP
                </button>
            </a>

            <a href='/logout'>
                <button>
                    🚪 Logout
                </button>
            </a>

        </div>

        <div class='card'>

            <h2 style='text-align:center;'>
            Recent Attendance
            </h2>

            <table>

                <tr>
                    <th>Name</th>
                    <th>Date</th>
                    <th>Time</th>
                </tr>
    """

    for row in rows:

        name = row[0]

        date_part = row[1].split(" ")[0]
        time_part = row[1].split(" ")[1]

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

# =====================================================
# BULK QR GENERATOR
# =====================================================
@app.route("/bulk_generate", methods=["GET","POST"])
@login_required
def bulk_generate():

    if request.method == "POST":

        data = request.form["students"]

        lines = data.strip().split("\\n")

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        if not os.path.exists("static/qrcodes"):
            os.makedirs("static/qrcodes")

        success = 0
        failed = 0

        for line in lines:

            try:

                parts = line.split(",")

                if len(parts) < 2:
                    failed += 1
                    continue

                name = parts[0].strip()
                email = parts[1].strip()

                token = secrets.token_hex(8)

                c.execute("""
                INSERT OR IGNORE INTO students
                (name,email,token)
                VALUES (?,?,?)
                """, (name,email,token))

                qr_link = request.host_url + "mark/" + token

                img = qrcode.make(qr_link)

                safe_name = (
                    name.replace(" ","_")
                    .replace("/","")
                    .replace("\\\\","")
                )

                qr_path = f"static/qrcodes/{safe_name}.png"

                img.save(qr_path)

                # SEND EMAIL
                mail_status = send_email(
                    email,
                    name,
                    qr_path
                )

                if mail_status:
                    success += 1
                else:
                    failed += 1

            except Exception as e:

                print("ERROR:",e)

                failed += 1

        conn.commit()
        conn.close()

        return f"""
        {STYLE}

        <div class='container'>

            <div class='card'>

                <h1 class='success'>
                ✅ {success} Emails Sent Successfully
                </h1>

                <h2 style='text-align:center;margin-top:15px;color:red;'>
                ❌ Failed: {failed}
                </h2>

                <div class='info-box'>

                    <h3>Check Terminal Logs</h3>

                    <p style='margin-top:10px;'>
                    If emails failed, verify:
                    </p>

                    <ul style='margin-top:10px;padding-left:20px;'>

                        <li>Gmail App Password</li>
                        <li>2-Step Verification Enabled</li>
                        <li>Correct Email Address</li>
                        <li>Internet Connection</li>

                    </ul>

                </div>

                <a href='/dashboard'>
                    <button>
                        ⬅ Back Dashboard
                    </button>
                </a>

            </div>

        </div>
        """

    return f"""
    {STYLE}

    <div class='navbar'>
        🚀 Bulk QR Generator
    </div>

    <div class='container'>

        <div class='card'>

            <h1 style='text-align:center;'>
            Paste Student Data
            </h1>

            <div class='info-box'>

                <h3>Paste Format:</h3>

                <p style='margin-top:10px;'>

                John,john@gmail.com
                <br>
                Sarah,sarah@gmail.com
                <br>
                Mike,mike@gmail.com

                </p>

            </div>

            <form method='POST'>

                <textarea
                    name='students'
                    placeholder='Paste all students here...'
                    required
                ></textarea>

                <button type='submit'>
                    🚀 Generate & Send All QR Codes
                </button>

            </form>

        </div>

    </div>
    """

# =====================================================
# DOWNLOAD ALL QR ZIP
# =====================================================
@app.route("/download_qrs")
@login_required
def download_qrs():

    zip_name = "all_qrs.zip"

    with zipfile.ZipFile(zip_name,"w") as zipf:

        for root,dirs,files in os.walk("static/qrcodes"):

            for file in files:

                path = os.path.join(root,file)

                zipf.write(path)

    return send_file(zip_name,as_attachment=True)

# =====================================================
# MARK ATTENDANCE
# =====================================================
@app.route("/mark/<token>")
def mark(token):

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    SELECT name
    FROM students
    WHERE token=?
    """,(token,))

    student = c.fetchone()

    if not student:

        return f"""
        {STYLE}

        <div class='container'>

            <div class='card'>

                <h1 class='error'>
                Invalid QR Code
                </h1>

            </div>

        </div>
        """

    name = student[0]

    tbilisi_time = datetime.utcnow() + timedelta(hours=4)

    time_string = tbilisi_time.strftime("%Y-%m-%d %H:%M:%S")

    c.execute("""
    SELECT *
    FROM attendance
    WHERE name=?
    AND date(time)=date('now','+4 hours')
    """,(name,))

    existing = c.fetchone()

    if existing:

        return f"""
        {STYLE}

        <div class='container'>

            <div class='card'>

                <h1 class='error'>
                Attendance Already Marked Today
                </h1>

            </div>

        </div>
        """

    c.execute("""
    INSERT INTO attendance(name,time)
    VALUES (?,?)
    """,(name,time_string))

    conn.commit()
    conn.close()

    return f"""
    {STYLE}

    <div class='container'>

        <div class='card'>

            <h1 class='success'>
            Attendance Marked Successfully
            </h1>

            <h2 style='text-align:center;margin-top:20px;'>
            {name}
            </h2>

            <p style='text-align:center;margin-top:10px;'>
            {time_string}
            </p>

        </div>

    </div>
    """

# =====================================================
# DOWNLOAD ATTENDANCE EXCEL
# =====================================================
@app.route("/download")
@login_required
def download():

    conn = sqlite3.connect(DB_NAME)

    df = pd.read_sql_query(
        "SELECT * FROM attendance",
        conn
    )

    file_name = "attendance.xlsx"

    df.to_excel(file_name,index=False)

    conn.close()

    return send_file(
        file_name,
        as_attachment=True
    )

# =====================================================
# RUN
# =====================================================
if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
