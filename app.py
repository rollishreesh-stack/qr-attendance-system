from flask import Flask, request, redirect, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import secrets
import qrcode
import os
import zipfile

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_NAME = "attendance.db"

# ================= DATABASE =================
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

# ================= LOGIN =================
login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# ================= MODERN STYLE =================
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
    box-shadow:0px 2px 10px rgba(0,0,0,0.3);
}

.container{
    width:90%;
    max-width:1100px;
    margin:auto;
    margin-top:40px;
    margin-bottom:40px;
}

.card{
    background:white;
    color:black;
    padding:30px;
    border-radius:20px;
    margin-top:20px;
    box-shadow:0px 5px 20px rgba(0,0,0,0.3);
}

h1,h2,h3{
    text-align:center;
}

input,textarea{
    width:100%;
    padding:15px;
    margin-top:10px;
    border-radius:12px;
    border:1px solid #ccc;
    font-size:16px;
    box-sizing:border-box;
}

textarea{
    min-height:250px;
}

button{
    width:100%;
    padding:15px;
    margin-top:15px;
    background:#2563eb;
    border:none;
    color:white;
    font-size:16px;
    border-radius:12px;
    cursor:pointer;
    transition:0.3s;
}

button:hover{
    background:#1d4ed8;
    transform:scale(1.02);
}

a{
    text-decoration:none;
}

.stats{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
    gap:20px;
}

.stat-box{
    background:#2563eb;
    padding:25px;
    border-radius:15px;
    text-align:center;
    color:white;
    box-shadow:0px 5px 15px rgba(0,0,0,0.3);
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
    background:white;
    color:black;
    padding:12px;
    border-bottom:1px solid #ddd;
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

.hero{
    text-align:center;
    padding:30px;
}

.hero h1{
    font-size:42px;
}

.hero p{
    font-size:18px;
    color:#d1d5db;
}

</style>

<!-- EMAILJS -->
<script src="https://cdn.jsdelivr.net/npm/@emailjs/browser@4/dist/email.min.js"></script>

<script>
(function(){
emailjs.init("-oGl3hn1HEMpvxh2T");
})();
</script>
"""

# ================= HOME =================
@app.route("/")
def home():

    return f"""
    {STYLE}

    <div class='navbar'>
    🎓 AIMCS QR Attendance System
    </div>

    <div class='container'>

        <div class='card hero'>

            <h1>Professional QR Attendance Platform</h1>

            <p>
            Bulk QR Generation • Attendance Analytics • Email Delivery • Excel Export
            </p>

            <a href='/login'>
            <button>Admin Login</button>
            </a>

        </div>

    </div>
    """

# ================= LOGIN =================
@app.route("/login", methods=["GET","POST"])
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

            <div class='card'>

                <h2 class='error'>Invalid Credentials</h2>

                <a href='/login'>
                <button>Try Again</button>
                </a>

            </div>

        </div>
        """

    return f"""
    {STYLE}

    <div class='navbar'>🔐 Admin Login</div>

    <div class='container'>

        <div class='card'>

            <form method='POST'>

                <input
                name='username'
                placeholder='Username'
                required>

                <input
                type='password'
                name='password'
                placeholder='Password'
                required>

                <button type='submit'>
                Login
                </button>

            </form>

        </div>

    </div>
    """

# ================= DASHBOARD =================
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
    LIMIT 10
    """)

    recent = c.fetchall()

    conn.close()

    rows = ""

    for row in recent:

        rows += f"""
        <tr>
            <td>{row[0]}</td>
            <td>{row[1]}</td>
        </tr>
        """

    return f"""
    {STYLE}

    <div class='navbar'>📊 Dashboard</div>

    <div class='container'>

        <div class='stats'>

            <div class='stat-box'>
                <h2>{total_students}</h2>
                <p>Total Students</p>
            </div>

            <div class='stat-box'>
                <h2>{total_attendance}</h2>
                <p>Total Attendance</p>
            </div>

        </div>

        <div class='card'>

            <a href='/bulk_generate'>
            <button>➕ Bulk QR Generator</button>
            </a>

            <a href='/download'>
            <button>⬇️ Download Excel</button>
            </a>

            <a href='/download_qrs'>
            <button>📦 Download All QR Codes</button>
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
                    <th>Time</th>
                </tr>

                {rows}

            </table>

        </div>

    </div>
    """

# ================= BULK GENERATE =================
@app.route("/bulk_generate", methods=["GET","POST"])
@login_required
def bulk_generate():

    if request.method == "POST":

        data = request.form["students"]

        lines = data.strip().split("\\n")

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        os.makedirs("static/qrs", exist_ok=True)

        success = 0

        for line in lines:

            try:

                name, email = line.split(",")

                name = name.strip()
                email = email.strip()

                token = secrets.token_hex(8)

                c.execute("""
                INSERT INTO students(name,email,token)
                VALUES (?,?,?)
                """, (name,email,token))

                qr_link = request.host_url + "mark/" + token

                img = qrcode.make(qr_link)

                safe_name = name.replace(" ","_")

                qr_path = f"static/qrs/{safe_name}.png"

                img.save(qr_path)

                success += 1

            except Exception as e:
                print(e)

        conn.commit()
        conn.close()

        return f"""
        {STYLE}

        <div class='navbar'>✅ QR Generation Completed</div>

        <div class='container'>

            <div class='card'>

                <h2 class='success'>
                Successfully Generated {success} QR Codes
                </h2>

                <p style='text-align:center;'>
                Emails are being sent automatically using EmailJS.
                </p>

                <script>

                const students = `{data}`.trim().split('\\n');

                students.forEach(student => {{

                    let parts = student.split(',');

                    let name = parts[0].trim();
                    let email = parts[1].trim();

                    emailjs.send(
                        "service_iuneir8",
                        "template_uyhe7xo",
                        {{
                            name:name,
                            email:email
                        }}
                    );

                }});

                </script>

                <a href='/dashboard'>
                <button>Back to Dashboard</button>
                </a>

            </div>

        </div>
        """

    return f"""
    {STYLE}

    <div class='navbar'>📨 Bulk QR Generator</div>

    <div class='container'>

        <div class='card'>

            <h2>Paste Students List</h2>

            <p>
            Enter one student per line in this format:
            </p>

            <pre>
John Doe,john@gmail.com
Sara Khan,sara@gmail.com
Mike Ross,mike@gmail.com
            </pre>

            <form method='POST'>

                <textarea
                name='students'
                placeholder='Name,Email'
                required></textarea>

                <button type='submit'>
                Generate QR & Send Emails
                </button>

            </form>

        </div>

    </div>
    """

# ================= MARK ATTENDANCE =================
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
        return f"""
        {STYLE}

        <div class='container'>

            <div class='card'>

                <h2 class='error'>Invalid QR Code</h2>

            </div>

        </div>
        """

    name = student[0]

    current = datetime.utcnow() + timedelta(hours=4)

    time_string = current.strftime("%Y-%m-%d %H:%M:%S")

    c.execute("""
    SELECT * FROM attendance
    WHERE name=?
    AND date(time)=date('now','+4 hours')
    """,(name,))

    existing = c.fetchone()

    if existing:

        conn.close()

        return f"""
        {STYLE}

        <div class='container'>

            <div class='card'>

                <h2 class='error'>
                ⚠️ {name} already marked attendance today
                </h2>

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
            ✅ Attendance Marked Successfully
            </h1>

            <h2>{name}</h2>

            <h3>{time_string}</h3>

        </div>

    </div>
    """

# ================= DOWNLOAD EXCEL =================
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

    return send_file(file_name, as_attachment=True)

# ================= DOWNLOAD QR ZIP =================
@app.route("/download_qrs")
@login_required
def download_qrs():

    zip_name = "qrcodes.zip"

    with zipfile.ZipFile(zip_name,"w") as zipf:

        for root,dirs,files in os.walk("static/qrs"):

            for file in files:

                zipf.write(
                    os.path.join(root,file)
                )

    return send_file(zip_name, as_attachment=True)

# ================= LOGOUT =================
@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect("/login")

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
