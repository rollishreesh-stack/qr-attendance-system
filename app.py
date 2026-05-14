from flask import Flask, request, redirect, send_file, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import pandas as pd
import secrets
import qrcode
import os
import zipfile

# ================= APP =================
app = Flask(__name__)
app.secret_key = "supersecretkey"

# ================= DATABASE =================
DATABASE_URL = os.environ.get("DATABASE_URL")

engine = create_engine(DATABASE_URL)

# ================= INIT DB =================
def init_db():

    with engine.connect() as conn:

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS admins(
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS students(
            id SERIAL PRIMARY KEY,
            name TEXT,
            email TEXT,
            token TEXT UNIQUE
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS attendance(
            id SERIAL PRIMARY KEY,
            name TEXT,
            time TEXT
        )
        """))

        # default admin
        admin = conn.execute(
            text("SELECT * FROM admins WHERE username='admin'")
        ).fetchone()

        if not admin:

            conn.execute(
                text("""
                INSERT INTO admins(username,password)
                VALUES (:u,:p)
                """),
                {
                    "u":"admin",
                    "p":generate_password_hash("admin123")
                }
            )

        conn.commit()

init_db()

# ================= LOGIN =================
login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self,id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# ================= STYLE =================
STYLE = """
<style>

body{
    margin:0;
    font-family:Arial;
    background:#0f172a;
    color:white;
    overflow-x:hidden;
}

/* SIDEBAR */
.sidebar{
    position:fixed;
    left:0;
    top:0;
    width:240px;
    height:100%;
    background:#111827;
    padding-top:20px;
    box-shadow:4px 0 15px rgba(0,0,0,0.4);
}

.sidebar h2{
    text-align:center;
    color:#60a5fa;
}

.sidebar a{
    display:block;
    color:white;
    text-decoration:none;
    padding:15px 25px;
    transition:0.3s;
}

.sidebar a:hover{
    background:#2563eb;
    transform:translateX(5px);
}

/* MAIN */
.main{
    margin-left:260px;
    padding:30px;
}

/* HEADER */
.title{
    font-size:34px;
    font-weight:bold;
    margin-bottom:20px;
}

/* CARDS */
.card{
    background:white;
    color:black;
    padding:25px;
    border-radius:18px;
    margin-top:20px;
    box-shadow:0 5px 20px rgba(0,0,0,0.3);
    animation:fadeIn 0.7s ease;
}

@keyframes fadeIn{
    from{
        opacity:0;
        transform:translateY(20px);
    }
    to{
        opacity:1;
        transform:translateY(0);
    }
}

/* BUTTONS */
button{
    width:100%;
    padding:13px;
    border:none;
    border-radius:10px;
    background:#2563eb;
    color:white;
    cursor:pointer;
    transition:0.3s;
    margin-top:10px;
}

button:hover{
    background:#1d4ed8;
    transform:scale(1.02);
}

/* INPUTS */
textarea,input{
    width:100%;
    padding:12px;
    border-radius:10px;
    border:1px solid #ccc;
    margin-top:10px;
}

/* STATS */
.stats{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
    gap:20px;
}

.box{
    background:linear-gradient(135deg,#2563eb,#1d4ed8);
    padding:25px;
    border-radius:18px;
    text-align:center;
    box-shadow:0 5px 20px rgba(0,0,0,0.3);
    animation:fadeIn 0.5s ease;
}

/* TABLE */
table{
    width:100%;
    border-collapse:collapse;
    margin-top:20px;
}

th{
    background:#2563eb;
    color:white;
    padding:12px;
}

td{
    background:white;
    color:black;
    padding:12px;
    border-bottom:1px solid #ddd;
}

canvas{
    background:white;
    border-radius:15px;
    padding:20px;
}

</style>

<!-- EMAILJS -->
<script src="https://cdn.jsdelivr.net/npm/@emailjs/browser@4/dist/email.min.js"></script>

<script>
(function(){
    emailjs.init("-oGl3hn1HEMpvxh2T");
})();
</script>

<!-- CHART -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<!-- QR SCANNER -->
<script src="https://unpkg.com/html5-qrcode"></script>
"""

# ================= LOGIN PAGE =================
@app.route("/", methods=["GET","POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        with engine.connect() as conn:

            admin = conn.execute(
                text("SELECT * FROM admins WHERE username=:u"),
                {"u":username}
            ).fetchone()

            if admin and check_password_hash(admin[2],password):

                user = User(admin[0])
                login_user(user)

                return redirect("/dashboard")

        return "<h2>Invalid Login</h2>"

    return f"""
    {STYLE}

    <div style='display:flex;justify-content:center;align-items:center;height:100vh;'>

        <div class='card' style='width:400px;'>

            <h1 style='text-align:center;'>🎓 AIMCS Login</h1>

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
@login_required
def dashboard():

    with engine.connect() as conn:

        students = conn.execute(
            text("SELECT COUNT(*) FROM students")
        ).scalar()

        attendance = conn.execute(
            text("SELECT COUNT(*) FROM attendance")
        ).scalar()

        rows = conn.execute(
            text("""
            SELECT name, COUNT(*) 
            FROM attendance
            GROUP BY name
            """)
        ).fetchall()

    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]

    return f"""
    {STYLE}

    <div class='sidebar'>

        <h2>🎓 AIMCS</h2>

        <a href='/dashboard'>📊 Dashboard</a>
        <a href='/bulk'>➕ Bulk QR</a>
        <a href='/scanner'>📷 QR Scanner</a>
        <a href='/download'>⬇ Excel</a>
        <a href='/download_qrs'>📦 QR ZIP</a>
        <a href='/logout'>🚪 Logout</a>

    </div>

    <div class='main'>

        <div class='title'>
            QR Attendance Dashboard
        </div>

        <div class='stats'>

            <div class='box'>
                <h2>{students}</h2>
                <p>Total Students</p>
            </div>

            <div class='box'>
                <h2>{attendance}</h2>
                <p>Total Attendance</p>
            </div>

        </div>

        <div class='card'>

            <h2>Attendance Analytics</h2>

            <canvas id='chart'></canvas>

        </div>

    </div>

    <script>

    const ctx = document.getElementById('chart');

    new Chart(ctx, {{
        type:'bar',
        data:{{
            labels:{labels},
            datasets:[{{
                label:'Attendance Count',
                data:{values}
            }}]
        }}
    }});

    </script>
    """

# ================= BULK =================
@app.route("/bulk", methods=["GET","POST"])
@login_required
def bulk():

    if request.method == "POST":

        data = request.form["data"]
        lines = data.strip().split("\\n")

        success = 0
        js_students = []

        os.makedirs("static/qrs", exist_ok=True)

        with engine.connect() as conn:

            for line in lines:

                try:

                    line = line.strip()

                    if not line or "," not in line:
                        continue

                    name, email = line.split(",",1)

                    token = secrets.token_hex(8)

                    conn.execute(
                        text("""
                        INSERT INTO students(name,email,token)
                        VALUES (:n,:e,:t)
                        """),
                        {
                            "n":name,
                            "e":email,
                            "t":token
                        }
                    )

                    qr_link = request.host_url + "mark/" + token

                    qr_image = "https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=" + qr_link

                    img = qrcode.make(qr_link)

                    img.save(f"static/qrs/{name}.png")

                    js_students.append(
                        f"{name},{email},{qr_link},{qr_image}"
                    )

                    success += 1

                except Exception as e:
                    print(e)

            conn.commit()

        js_data = "\\n".join(js_students)

        return f"""
        {STYLE}

        <div class='main'>

            <div class='card'>

                <h1>{success} QR Generated</h1>

                <script>

                const students = `{js_data}`.split('\\n');

                students.forEach(s => {{

                    let p = s.split(",");

                    emailjs.send(
                        "service_iuneir8",
                        "template_uyhe7xo",
                        {{
                            name:p[0],
                            email:p[1],
                            qr_link:p[2],
                            qr_image:p[3]
                        }}
                    );

                }});

                </script>

                <a href='/dashboard'>
                    <button>Back Dashboard</button>
                </a>

            </div>

        </div>
        """

    return f"""
    {STYLE}

    <div class='main'>

        <div class='card'>

            <h2>Bulk QR Generator</h2>

            <p>Format: Name,Email</p>

            <form method='POST'>

                <textarea name='data'></textarea>

                <button>Generate QR</button>

            </form>

        </div>

    </div>
    """

# ================= QR SCANNER =================
@app.route("/scanner")
@login_required
def scanner():

    return f"""
    {STYLE}

    <div class='main'>

        <div class='card'>

            <h2>📷 Mobile QR Scanner</h2>

            <div id="reader"></div>

        </div>

    </div>

    <script>

    function onScanSuccess(decodedText) {{
        window.location.href = decodedText;
    }}

    let scanner = new Html5QrcodeScanner(
        "reader",
        {{ fps: 10, qrbox: 250 }}
    );

    scanner.render(onScanSuccess);

    </script>
    """

# ================= MARK =================
@app.route("/mark/<token>")
def mark(token):

    with engine.connect() as conn:

        result = conn.execute(
            text("""
            SELECT name FROM students
            WHERE token=:t
            """),
            {"t":token}
        ).fetchone()

        if not result:
            return "Invalid QR"

        name = result[0]

        now = datetime.utcnow() + timedelta(hours=4)

        time_str = now.strftime("%Y-%m-%d %H:%M:%S")

        existing = conn.execute(
            text("""
            SELECT * FROM attendance
            WHERE name=:n
            """),
            {"n":name}
        ).fetchone()

        if existing:
            return f"{name} already marked"

        conn.execute(
            text("""
            INSERT INTO attendance(name,time)
            VALUES (:n,:t)
            """),
            {
                "n":name,
                "t":time_str
            }
        )

        conn.commit()

    return f"""
    {STYLE}

    <div class='main'>

        <div class='card'>

            <h1>✅ Attendance Marked</h1>

            <h2>{name}</h2>

            <h3>{time_str}</h3>

        </div>

    </div>
    """

# ================= DOWNLOAD =================
@app.route("/download")
@login_required
def download():

    with engine.connect() as conn:

        df = pd.read_sql(
            text("SELECT * FROM attendance"),
            conn
        )

    file = "attendance.xlsx"

    df.to_excel(file,index=False)

    return send_file(file,as_attachment=True)

# ================= ZIP =================
@app.route("/download_qrs")
@login_required
def zip_qr():

    z = zipfile.ZipFile("qrs.zip","w")

    for f in os.listdir("static/qrs"):
        z.write("static/qrs/"+f)

    z.close()

    return send_file("qrs.zip",as_attachment=True)

# ================= LOGOUT =================
@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect("/")

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
