from flask import Flask, request, redirect, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import sqlite3
from datetime import datetime, timedelta
import os
import secrets
import qrcode
import pandas as pd
import zipfile

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB = "attendance.db"

# ================= ENV =================
SENDGRID_API_KEY = os.environ.get("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")
SENDER_EMAIL = os.environ.get("SRolli@seu.edu.ge")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH")

# ================= DB =================
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        token TEXT UNIQUE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS attendance(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        time TEXT
    )""")

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

# ================= UI =================
STYLE = """
<style>
body{
    margin:0;
    font-family:Arial;
    background:linear-gradient(135deg,#0f172a,#1e293b);
    color:white;
}

.nav{
    padding:20px;
    text-align:center;
    font-size:26px;
    font-weight:bold;
    background:#111827;
}

.container{
    width:90%;
    max-width:1100px;
    margin:auto;
    margin-top:30px;
}

.card{
    background:white;
    color:black;
    padding:25px;
    border-radius:15px;
    margin-top:20px;
}

button{
    padding:12px;
    width:100%;
    margin-top:10px;
    border:none;
    background:#2563eb;
    color:white;
    border-radius:10px;
    cursor:pointer;
}

textarea,input{
    width:100%;
    padding:12px;
    margin-top:10px;
    border-radius:10px;
    border:1px solid #ccc;
}

table{
    width:100%;
    margin-top:15px;
    border-collapse:collapse;
}

th,td{
    padding:10px;
    border-bottom:1px solid #ddd;
}

th{
    background:#2563eb;
    color:white;
}

h1,h2{
    text-align:center;
}
</style>
"""

# ================= EMAIL =================
def send_email(email, name, qr_path):
    try:
        msg = Mail(
            from_email=SENDER_EMAIL,
            to_emails=email,
            subject="Your QR Code",
            html_content=f"<h3>Hello {name}</h3><p>Your QR is ready.</p>"
        )

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(msg)

        print("EMAIL SENT:", email)
        return True

    except Exception as e:
        print("EMAIL ERROR:", e)
        return False

# ================= HOME (FIXED 404) =================
@app.route("/")
def home():
    return f"""
    {STYLE}
    <div class='nav'>🎓 QR Attendance System</div>
    <div class='container'>
        <div class='card'>
            <h1>Welcome</h1>
            <p style='text-align:center;'>Bulk QR + Email + Attendance System</p>
            <a href='/login'><button>Admin Login</button></a>
        </div>
    </div>
    """

# ================= LOGIN =================
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        return redirect("/dashboard")

    return f"""
    {STYLE}
    <div class='nav'>Login</div>
    <div class='container'>
        <div class='card'>
            <form method='POST'>
                <input name='password' placeholder='Enter password'>
                <button>Login</button>
            </form>
        </div>
    </div>
    """

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM students")
    s = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM attendance")
    a = c.fetchone()[0]

    conn.close()

    return f"""
    {STYLE}
    <div class='nav'>Dashboard</div>

    <div class='container'>
        <div class='card'>
            <h2>Students: {s} | Attendance: {a}</h2>
        </div>

        <div class='card'>
            <a href='/bulk'><button>Bulk QR Generator</button></a>
            <a href='/download'><button>Download Excel</button></a>
            <a href='/download_qrs'><button>Download QR ZIP</button></a>
        </div>
    </div>
    """

# ================= BULK =================
@app.route("/bulk", methods=["GET","POST"])
def bulk():

    if request.method == "POST":

        data = request.form["data"].strip().split("\n")

        conn = sqlite3.connect(DB)
        c = conn.cursor()

        os.makedirs("static/qrs", exist_ok=True)

        success = 0

        for row in data:
            try:
                name, email = row.split(",")

                token = secrets.token_hex(8)

                c.execute("INSERT INTO students(name,email,token) VALUES (?,?,?)",
                          (name,email,token))

                qr = qrcode.make(request.host_url + "mark/" + token)

                path = f"static/qrs/{name}.png"
                qr.save(path)

                send_email(email,name,path)

                success += 1

            except:
                pass

        conn.commit()
        conn.close()

        return f"<h2>Done: {success}</h2><a href='/dashboard'>Back</a>"

    return f"""
    {STYLE}
    <div class='nav'>Bulk QR</div>
    <div class='container'>
        <div class='card'>
            <form method='POST'>
                <textarea name='data' placeholder='Name,Email'></textarea>
                <button>Generate</button>
            </form>
        </div>
    </div>
    """

# ================= MARK =================
@app.route("/mark/<token>")
def mark(token):

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT name FROM students WHERE token=?", (token,))
    s = c.fetchone()

    if not s:
        return "Invalid QR"

    name = s[0]

    time = datetime.utcnow() + timedelta(hours=4)
    t = time.strftime("%Y-%m-%d %H:%M:%S")

    c.execute("INSERT INTO attendance(name,time) VALUES (?,?)", (name,t))

    conn.commit()
    conn.close()

    return f"<h2>Attendance marked for {name}</h2>"

# ================= DOWNLOAD =================
@app.route("/download")
def download():
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query("SELECT * FROM attendance", conn)

    file = "attendance.xlsx"
    df.to_excel(file,index=False)

    return send_file(file,as_attachment=True)

# ================= ZIP =================
@app.route("/download_qrs")
def zip_qr():

    z = zipfile.ZipFile("qrs.zip","w")

    for f in os.listdir("static/qrs"):
        z.write("static/qrs/"+f)

    z.close()

    return send_file("qrs.zip",as_attachment=True)

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0",port=5000)
