from flask import Flask, request, redirect, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from werkzeug.security import check_password_hash
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import secrets
import qrcode
import os
import zipfile

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_NAME = "attendance.db"

# ================= ENV CONFIG =================
import os
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH")

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
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

# ================= LOGIN =================
login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# ================= EMAIL =================
def send_email(receiver_email, student_name, qr_path):

    try:
        msg = Mail(
            from_email=SENDER_EMAIL,
            to_emails=receiver_email,
            subject="Your QR Attendance Code",
            html_content=f"""
            <h2>Hello {student_name}</h2>
            <p>Your QR code is attached for attendance system.</p>
            """
        )

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(msg)

        print("EMAIL SENT:", receiver_email, response.status_code)
        return True

    except Exception as e:
        print("EMAIL ERROR:", e)
        return False

# ================= LOGIN PAGE =================
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":
        password = request.form["password"]

        if check_password_hash(ADMIN_PASSWORD_HASH, password):
            user = User(1)
            login_user(user)
            return redirect("/dashboard")

        return "Wrong password"

    return """
    <h2>Admin Login</h2>
    <form method='POST'>
        <input name='password' type='password' placeholder='Password'>
        <button type='submit'>Login</button>
    </form>
    """

# ================= DASHBOARD =================
@app.route("/dashboard")
@login_required
def dashboard():

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM students")
    students = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM attendance")
    attendance = c.fetchone()[0]

    conn.close()

    return f"""
    <h1>Dashboard</h1>

    <div style='display:flex;gap:20px;'>
        <div>Students: {students}</div>
        <div>Attendance: {attendance}</div>
    </div>

    <br>

    <a href='/bulk_generate'>Bulk QR Generator</a><br>
    <a href='/download'>Download Excel</a><br>
    <a href='/download_qrs'>Download QR ZIP</a><br>
    <a href='/logout'>Logout</a>
    """

# ================= BULK GENERATION =================
@app.route("/bulk_generate", methods=["GET","POST"])
@login_required
def bulk_generate():

    if request.method == "POST":

        data = request.form["students"]
        lines = data.strip().split("\n")

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        os.makedirs("static/qrcodes", exist_ok=True)

        success = 0
        failed = 0

        for line in lines:

            try:
                name, email = line.split(",")

                name = name.strip()
                email = email.strip()

                token = secrets.token_hex(8)

                c.execute("""
                INSERT OR IGNORE INTO students(name,email,token)
                VALUES (?,?,?)
                """, (name, email, token))

                qr_link = request.host_url + "mark/" + token
                img = qrcode.make(qr_link)

                qr_path = f"static/qrcodes/{name}.png"
                img.save(qr_path)

                if send_email(email, name, qr_path):
                    success += 1
                else:
                    failed += 1

            except Exception as e:
                print("ERROR:", e)
                failed += 1

        conn.commit()
        conn.close()

        return f"Success: {success}, Failed: {failed}"

    return """
    <h2>Bulk Upload</h2>
    <form method='POST'>
        <textarea name='students' placeholder='Name,Email'></textarea>
        <button type='submit'>Generate</button>
    </form>
    """

# ================= MARK ATTENDANCE =================
@app.route("/mark/<token>")
def mark(token):

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT name FROM students WHERE token=?", (token,))
    student = c.fetchone()

    if not student:
        return "Invalid QR"

    name = student[0]

    time_now = datetime.utcnow() + timedelta(hours=4)
    time_string = time_now.strftime("%Y-%m-%d %H:%M:%S")

    c.execute("""
    SELECT * FROM attendance
    WHERE name=? AND date(time)=date('now','+4 hours')
    """, (name,))

    if c.fetchone():
        return "Already marked"

    c.execute("INSERT INTO attendance(name,time) VALUES (?,?)", (name, time_string))

    conn.commit()
    conn.close()

    return f"Attendance marked: {name}"

# ================= DOWNLOAD EXCEL =================
@app.route("/download")
@login_required
def download():

    conn = sqlite3.connect(DB_NAME)

    df = pd.read_sql_query("SELECT * FROM attendance", conn)

    file = "attendance.xlsx"
    df.to_excel(file, index=False)

    conn.close()

    return send_file(file, as_attachment=True)

# ================= DOWNLOAD QR ZIP =================
@app.route("/download_qrs")
@login_required
def download_qrs():

    zipf = zipfile.ZipFile("qrs.zip", "w")

    for root, dirs, files in os.walk("static/qrcodes"):
        for file in files:
            zipf.write(os.path.join(root, file))

    zipf.close()

    return send_file("qrs.zip", as_attachment=True)

# ================= LOGOUT =================
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
