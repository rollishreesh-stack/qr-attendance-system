from flask import Flask, request, redirect, send_file, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import sqlite3
from datetime import datetime, timedelta
import secrets
import qrcode
import os
import zipfile
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_NAME = "attendance.db"

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # students
    c.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        token TEXT UNIQUE
    )
    """)

    # attendance
    c.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        time TEXT
    )
    """)

    # admins (NEW)
    c.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    # default admin
    c.execute("SELECT * FROM admins WHERE username='admin'")
    if not c.fetchone():
        c.execute(
            "INSERT INTO admins(username,password) VALUES (?,?)",
            ("admin", generate_password_hash("admin123"))
        )

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

# ================= STYLE (UPGRADED UI) =================
STYLE = """
<style>
body{
    margin:0;
    font-family:Arial;
    background:linear-gradient(135deg,#0f172a,#1e293b);
    color:white;
}

.header{
    background:#111827;
    padding:18px;
    text-align:center;
    font-size:24px;
    font-weight:bold;
    animation:fadeIn 0.5s ease;
}

.container{
    width:90%;
    max-width:1000px;
    margin:auto;
    margin-top:30px;
}

.card{
    background:white;
    color:black;
    padding:25px;
    border-radius:15px;
    margin-top:20px;
    box-shadow:0 5px 15px rgba(0,0,0,0.3);
    animation:fadeIn 0.5s ease;
}

button{
    width:100%;
    padding:12px;
    margin-top:10px;
    background:#2563eb;
    color:white;
    border:none;
    border-radius:10px;
}

textarea,input{
    width:100%;
    padding:10px;
    border-radius:10px;
}

.stats{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
    gap:15px;
}

.box{
    background:#2563eb;
    padding:20px;
    text-align:center;
    border-radius:12px;
}

@keyframes fadeIn{
    from{opacity:0;transform:translateY(10px);}
    to{opacity:1;transform:translateY(0);}
}
</style>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<script src="https://cdn.jsdelivr.net/npm/@emailjs/browser@4/dist/email.min.js"></script>
<script>
emailjs.init("-oGl3hn1HEMpvxh2T");
</script>
"""

# ================= LOGIN PAGE =================
@app.route("/", methods=["GET","POST"])
def login():

    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        c.execute("SELECT * FROM admins WHERE username=?", (u,))
        admin = c.fetchone()
        conn.close()

        if admin and check_password_hash(admin[2], p):
            session["admin"] = True
            return redirect("/dashboard")

        return "Invalid login"

    return f"""
    {STYLE}
    <div class='header'>LOGIN</div>

    <div class='container'>
        <div class='card'>
            <form method='POST'>
                <input name='username' placeholder='Username'>
                <input type='password' name='password' placeholder='Password'>
                <button>Login</button>
            </form>
        </div>
    </div>
    """

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():

    if not session.get("admin"):
        return redirect("/")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM students")
    students = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM attendance")
    attendance = c.fetchone()[0]

    conn.close()

    return f"""
    {STYLE}
    <div class='header'>📊 DASHBOARD</div>

    <div class='container'>

        <div class='stats'>
            <div class='box'>Students<br><h2>{students}</h2></div>
            <div class='box'>Attendance<br><h2>{attendance}</h2></div>
        </div>

        <div class='card'>
            <canvas id="chart"></canvas>
        </div>

        <div class='card'>
            <a href='/bulk'><button>➕ Bulk QR</button></a>
            <a href='/scanner'><button>📷 Scanner</button></a>
            <a href='/download'><button>⬇ Excel</button></a>
            <a href='/download_qrs'><button>📦 QR ZIP</button></a>
            <a href='/logout'><button>🚪 Logout</button></a>
        </div>

    </div>

    <script>
    new Chart(document.getElementById("chart"), {{
        type:"bar",
        data:{{
            labels:["Students","Attendance"],
            datasets:[{{data:[{students},{attendance}]} }]
        }}
    }});
    </script>
    """

# ================= BULK QR =================
@app.route("/bulk", methods=["GET","POST"])
def bulk():

    if request.method == "POST":

        data = request.form["data"]
        lines = data.strip().split("\n")

        os.makedirs("static/qrs", exist_ok=True)

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        js = []

        for line in lines:

            if "," not in line:
                continue

            name,email = line.split(",",1)
            token = secrets.token_hex(8)

            c.execute("INSERT INTO students(name,email,token) VALUES (?,?,?)",
                      (name,email,token))

            link = request.host_url + "mark/" + token
            img = "https://api.qrserver.com/v1/create-qr-code/?data=" + link

            qrcode.make(link).save(f"static/qrs/{name}.png")

            js.append(f"{name},{email},{link},{img}")

        conn.commit()
        conn.close()

        js_data = "\n".join(js)

        return f"""
        {STYLE}
        <div class='header'>DONE</div>

        <div class='container'>
            <div class='card'>
                <h2>QR Generated</h2>

                <script>
                const users = `{js_data}`.split("\\n");

                users.forEach(u=>{{
                    let p=u.split(",");

                    emailjs.send("service_iuneir8","template_uyhe7xo",{{
                        name:p[0],
                        email:p[1],
                        qr_link:p[2],
                        qr_image:p[3]
                    }});
                }});
                </script>
            </div>
        </div>
        """

    return f"""
    {STYLE}
    <div class='header'>BULK QR</div>

    <div class='container'>
        <div class='card'>
            <textarea name='data'></textarea>
            <button>Generate</button>
        </div>
    </div>
    """

# ================= SCANNER =================
@app.route("/scanner")
def scanner():

    return f"""
    {STYLE}
    <div class='header'>SCANNER</div>

    <div class='container'>
        <div class='card'>
            <script src="https://unpkg.com/html5-qrcode"></script>
            <div id="reader"></div>
        </div>
    </div>

    <script>
    function onScanSuccess(text){{
        window.location.href=text;
    }}

    new Html5QrcodeScanner("reader",{{fps:10,qrbox:250}})
        .render(onScanSuccess);
    </script>
    """

# ================= MARK =================
@app.route("/mark/<token>")
def mark(token):

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT name FROM students WHERE token=?", (token,))
    data = c.fetchone()

    if not data:
        return "Invalid"

    name = data[0]
    now = datetime.utcnow() + timedelta(hours=4)

    c.execute("SELECT * FROM attendance WHERE name=?",(name,))
    if c.fetchone():
        return "Already marked"

    c.execute("INSERT INTO attendance(name,time) VALUES (?,?)",
              (name,str(now)))

    conn.commit()
    conn.close()

    return f"<h2>Marked {name}</h2>"

# ================= DOWNLOAD =================
@app.route("/download")
def download():

    conn = sqlite3.connect(DB_NAME)
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

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
